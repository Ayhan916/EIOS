"""Document Parser Agent — PDF/HTML → structured text chunks.

Supports:
  - PDF via Docling (primary) — tables as Markdown, section-aware, OCR
  - PDF via PyMuPDF (fallback) — fast, no table support
  - HTML via BeautifulSoup — main content extraction
  - Plain text fallback

Docling produces structured Markdown where tables are preserved as
Markdown tables, sections are headed with ##, and images appear as
<!-- image --> placeholders. Semantic chunking splits on section
boundaries rather than word count alone.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

_CHUNK_SIZE = 800       # target words per chunk
_CHUNK_OVERLAP = 80     # overlap words

# ── Docling singleton ─────────────────────────────────────────────────────────
_docling_converter = None


def _get_docling_converter():
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter
        logger.info("doc_parser.docling_init")
        _docling_converter = DocumentConverter()
        logger.info("doc_parser.docling_ready")
    return _docling_converter


@dataclass
class ParsedDocument:
    title: str | None
    language: str
    pages: int
    file_hash: str
    chunks: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)  # section headings found


@dataclass
class ParseResult:
    ok: bool
    document: ParsedDocument | None = None
    error: str | None = None


def parse_pdf(content: bytes) -> ParseResult:
    """Parse PDF bytes — tries Docling first, falls back to PyMuPDF."""
    result = parse_pdf_docling(content)
    if result.ok:
        return result
    logger.warning("doc_parser.docling_failed_fallback", error=result.error)
    return _parse_pdf_pymupdf(content)


def parse_pdf_docling(content: bytes) -> ParseResult:
    """Parse PDF using Docling — preserves tables, sections, structure."""
    try:
        import tempfile, os
        from docling.datamodel.base_models import DocumentStream

        file_hash = hashlib.sha256(content).hexdigest()[:16]
        converter = _get_docling_converter()

        # Feed bytes via DocumentStream (no temp file needed)
        buf = io.BytesIO(content)
        source = DocumentStream(name="document.pdf", stream=buf)
        result = converter.convert(source)
        doc = result.document

        # Export to Markdown — tables become | col | col | rows
        markdown = doc.export_to_markdown()
        pages = len(list(doc.pages)) if doc.pages else 1

        # Extract sections from Markdown headings
        sections = re.findall(r"^#{1,3}\s+(.+)$", markdown, re.MULTILINE)

        # Detect language
        language = _detect_language(markdown[:3000])

        # Extract title: first H1 or H2
        title_match = re.search(r"^#{1,2}\s+(.+)$", markdown, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else None

        # Semantic chunking: split on section boundaries, keep tables intact
        chunks = _chunk_markdown(markdown)

        logger.info(
            "doc_parser.docling_done",
            pages=pages,
            chunks=len(chunks),
            sections=len(sections),
            hash=file_hash,
        )
        return ParseResult(
            ok=True,
            document=ParsedDocument(
                title=title,
                language=language,
                pages=pages,
                file_hash=file_hash,
                chunks=chunks,
                sections=sections[:50],
            ),
        )
    except Exception as exc:
        logger.error("doc_parser.docling_error", error=str(exc))
        return ParseResult(ok=False, error=str(exc))


def _parse_pdf_pymupdf(content: bytes) -> ParseResult:
    """PyMuPDF fallback — fast, no table support."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ParseResult(ok=False, error="PyMuPDF not installed — run: pip install pymupdf")

    try:
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        doc = fitz.open(stream=content, filetype="pdf")
        pages = doc.page_count

        full_text_parts: list[str] = []
        sections: list[str] = []

        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if not spans:
                        continue
                    line_text = " ".join(s["text"] for s in spans).strip()
                    if not line_text:
                        continue
                    # Detect headings by font size
                    max_size = max(s.get("size", 10) for s in spans)
                    if max_size >= 14 and len(line_text) < 120:
                        sections.append(line_text)
                        full_text_parts.append(f"\n## {line_text}\n")
                    else:
                        full_text_parts.append(line_text)

        doc.close()
        full_text = " ".join(full_text_parts)

        # Detect language (heuristic)
        language = _detect_language(full_text[:2000])

        # Extract title from first page or metadata
        title = _extract_title(full_text_parts[:20])

        chunks = _chunk_text(full_text)
        logger.info("doc_parser.pdf_done", pages=pages, chunks=len(chunks), hash=file_hash)
        return ParseResult(
            ok=True,
            document=ParsedDocument(
                title=title,
                language=language,
                pages=pages,
                file_hash=file_hash,
                chunks=chunks,
                sections=sections[:50],
            ),
        )
    except Exception as exc:
        logger.error("doc_parser.pdf_error", error=str(exc))
        return ParseResult(ok=False, error=str(exc))


def parse_html(content: bytes | str, url: str = "") -> ParseResult:
    """Parse HTML content into structured chunks."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return ParseResult(ok=False, error="beautifulsoup4 not installed — run: pip install beautifulsoup4 lxml")

    try:
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

        file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        soup = BeautifulSoup(content, "lxml")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
            tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Extract main content
        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        text = main.get_text(separator=" ", strip=True)
        text = re.sub(r"\s{3,}", "  ", text)

        sections = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:50]]
        language = _detect_language(text[:2000])
        chunks = _chunk_text(text)

        logger.info("doc_parser.html_done", url=url, chunks=len(chunks), hash=file_hash)
        return ParseResult(
            ok=True,
            document=ParsedDocument(
                title=title,
                language=language,
                pages=1,
                file_hash=file_hash,
                chunks=chunks,
                sections=sections,
            ),
        )
    except Exception as exc:
        logger.error("doc_parser.html_error", error=str(exc))
        return ParseResult(ok=False, error=str(exc))


def parse_text(content: str) -> ParseResult:
    """Parse plain text."""
    file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    chunks = _chunk_text(content)
    language = _detect_language(content[:2000])
    return ParseResult(
        ok=True,
        document=ParsedDocument(
            title=None,
            language=language,
            pages=1,
            file_hash=file_hash,
            chunks=chunks,
            sections=[],
        ),
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _chunk_markdown(markdown: str) -> list[str]:
    """Semantic chunking for Docling Markdown output.

    Strategy:
    - Split on H1/H2/H3 headings → one section per candidate chunk
    - Tables are never split (kept as a whole unit)
    - Sections longer than _CHUNK_SIZE words are further split by paragraph
    - Adjacent small sections are merged until close to _CHUNK_SIZE
    """
    # Split into blocks: headings start new sections, tables are atomic
    lines = markdown.split("\n")
    sections: list[str] = []
    current: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # New section heading → flush current
        if re.match(r"^#{1,3}\s+", line):
            if current:
                sections.append("\n".join(current).strip())
            current = [line]

        # Table start → collect entire table as one atomic block
        elif line.startswith("|"):
            table_lines = []
            while i < len(lines) and (lines[i].startswith("|") or lines[i].strip() == ""):
                if lines[i].startswith("|"):
                    table_lines.append(lines[i])
                i += 1
            table_block = "\n".join(table_lines)
            # If table fits in current chunk, append; else flush first
            combined = "\n".join(current) + "\n" + table_block
            if len(combined.split()) <= _CHUNK_SIZE:
                current.append(table_block)
            else:
                if current:
                    sections.append("\n".join(current).strip())
                current = [table_block]
            continue
        else:
            current.append(line)
        i += 1

    if current:
        sections.append("\n".join(current).strip())

    # Remove empty sections and image-only sections
    sections = [s for s in sections if len(s.split()) > 10 and not re.fullmatch(r"(\s*<!--\s*image\s*-->\s*)+", s)]

    # Merge small adjacent sections, split oversized ones
    chunks: list[str] = []
    buffer = ""

    for section in sections:
        word_count = len(section.split())

        # Oversized section → split by paragraph
        if word_count > _CHUNK_SIZE:
            if buffer:
                chunks.append(buffer.strip())
                buffer = ""
            paragraphs = re.split(r"\n{2,}", section)
            para_buf = ""
            for para in paragraphs:
                if len((para_buf + " " + para).split()) <= _CHUNK_SIZE:
                    para_buf = (para_buf + "\n\n" + para).strip()
                else:
                    if para_buf:
                        chunks.append(para_buf.strip())
                    para_buf = para
            if para_buf:
                chunks.append(para_buf.strip())
            continue

        # Fits in buffer → merge
        if len((buffer + "\n\n" + section).split()) <= _CHUNK_SIZE:
            buffer = (buffer + "\n\n" + section).strip()
        else:
            if buffer:
                chunks.append(buffer.strip())
            buffer = section

    if buffer:
        chunks.append(buffer.strip())

    return [c for c in chunks if len(c.split()) > 10]


def _chunk_text(text: str) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + _CHUNK_SIZE, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())
        if end >= len(words):
            break
        start = end - _CHUNK_OVERLAP
    return chunks


def _detect_language(text: str) -> str:
    """Heuristic: count German vs English stopwords."""
    de_words = {"der", "die", "das", "und", "ist", "mit", "für", "von", "im", "auf", "des", "dem", "den", "als", "bei", "zur", "zum"}
    en_words = {"the", "and", "for", "with", "this", "that", "are", "was", "from", "have", "has", "been", "their"}
    lower = text.lower()
    words = set(lower.split()[:200])
    de_score = len(words & de_words)
    en_score = len(words & en_words)
    return "de" if de_score >= en_score else "en"


def _extract_title(first_parts: list[str]) -> str | None:
    """Try to find a title in the first lines."""
    for part in first_parts:
        part = part.strip().lstrip("#").strip()
        if 10 < len(part) < 200 and not part.startswith(("www.", "http")):
            return part
    return None
