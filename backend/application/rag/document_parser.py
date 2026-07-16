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
    chunk_pages: list[int] = field(default_factory=list)  # page_number per chunk (0 = unknown)
    parse_layout: dict = field(default_factory=dict)  # {page_no: [{type, bbox}]}


@dataclass
class ParseResult:
    ok: bool
    document: ParsedDocument | None = None
    error: str | None = None


def parse_pdf(
    content: bytes,
    parse_engine: str = "docling",
    ocr_enabled: bool = True,
    extract_tables: bool = True,
    describe_pictures: bool = False,
) -> ParseResult:
    """Parse PDF bytes — routes to selected engine, falls back to PyMuPDF on failure."""
    if parse_engine == "pymupdf":
        return _parse_pdf_pymupdf(content)
    if parse_engine == "pdfplumber":
        result = _parse_pdf_pdfplumber(content)
        if result.ok:
            return result
        logger.warning("doc_parser.pdfplumber_failed_fallback", error=result.error)
        return _parse_pdf_pymupdf(content)
    # default: docling
    result = parse_pdf_docling(content, ocr_enabled=ocr_enabled, extract_tables=extract_tables, describe_pictures=describe_pictures)
    if result.ok:
        return result
    logger.warning("doc_parser.docling_failed_fallback", error=result.error)
    return _parse_pdf_pymupdf(content)


def parse_pdf_docling(
    content: bytes,
    ocr_enabled: bool = True,
    extract_tables: bool = True,
    describe_pictures: bool = False,
) -> ParseResult:
    """Parse PDF using Docling — preserves tables, sections, structure.

    describe_pictures: run SmolVLM-256M on each figure and inline the description
    as text — allows Copilot to answer questions about charts and diagrams.
    First call downloads ~500 MB from HuggingFace (cached afterwards).
    """
    try:
        from docling.datamodel.base_models import DocumentStream
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        file_hash = hashlib.sha256(content).hexdigest()[:16]

        # Use singleton only when all options are defaults
        if ocr_enabled and extract_tables and not describe_pictures:
            converter = _get_docling_converter()
        else:
            opts = PdfPipelineOptions()
            opts.do_ocr = ocr_enabled
            opts.do_table_structure = extract_tables
            if describe_pictures:
                from docling.datamodel.pipeline_options import PictureDescriptionVlmOptions
                opts.generate_picture_images = True
                opts.do_picture_description = True
                opts.picture_description_options = PictureDescriptionVlmOptions(
                    repo_id="HuggingFaceTB/SmolVLM-256M-Instruct",
                )
                logger.info("doc_parser.picture_description_enabled", model="SmolVLM-256M-Instruct")
            converter = DocumentConverter(
                format_options={"pdf": PdfFormatOption(pipeline_options=opts)}
            )

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

        # Page-aware chunking: track which PDF page each chunk originates from
        chunks, chunk_pages = _chunk_markdown_page_aware(doc, markdown, pages)

        # Extract layout bounding boxes per page
        parse_layout = _extract_layout(doc)

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
                chunk_pages=chunk_pages,
                sections=sections[:50],
                parse_layout=parse_layout,
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


def _parse_pdf_pdfplumber(content: bytes) -> ParseResult:
    """pdfplumber parser — best for table-heavy PDFs."""
    try:
        import pdfplumber
    except ImportError:
        return ParseResult(ok=False, error="pdfplumber not installed — run: pip install pdfplumber")

    try:
        file_hash = hashlib.sha256(content).hexdigest()[:16]
        full_text_parts: list[str] = []
        sections: list[str] = []
        pages = 0

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                # Extract tables as Markdown-style text
                for table in page.extract_tables():
                    if not table:
                        continue
                    rows = []
                    for i, row in enumerate(table):
                        cells = [str(c or "").strip() for c in row]
                        rows.append("| " + " | ".join(cells) + " |")
                        if i == 0:
                            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
                    full_text_parts.append("\n".join(rows))
                if text:
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        if len(line) < 100 and line[0].isupper():
                            sections.append(line)
                    full_text_parts.append(text)

        full_text = "\n\n".join(full_text_parts)
        language = _detect_language(full_text[:2000])
        title = _extract_title(full_text_parts[:5])
        chunks = _chunk_text(full_text)

        logger.info("doc_parser.pdfplumber_done", pages=pages, chunks=len(chunks), hash=file_hash)
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
        logger.error("doc_parser.pdfplumber_error", error=str(exc))
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


def _chunk_markdown_page_aware(doc: object, markdown: str, total_pages: int) -> tuple[list[str], list[int]]:
    """Chunk Markdown and assign each chunk a PDF page number.

    Strategy:
    1. Build a page-boundary map: character offsets in the full markdown where
       each page starts, derived from Docling's element provenance.
    2. Chunk the markdown as before.
    3. For each chunk, look up which page its content starts on.
    """
    # Build page-start offsets from Docling element provenance
    # Each element has prov[0].page_no and its text appears somewhere in markdown
    page_offsets: list[tuple[int, int]] = []  # (char_offset, page_no)
    try:
        for item, _level in doc.iterate_items():  # type: ignore[attr-defined]
            provs = getattr(item, "prov", None)
            if not provs:
                continue
            page_no = getattr(provs[0], "page_no", None)
            if page_no is None:
                continue
            # Get text of this element to locate it in the markdown
            item_text = ""
            if hasattr(item, "text"):
                item_text = item.text or ""
            elif hasattr(item, "export_to_markdown"):
                try:
                    item_text = item.export_to_markdown()
                except Exception:
                    pass
            if len(item_text) >= 10:
                pos = markdown.find(item_text[:40])
                if pos >= 0:
                    page_offsets.append((pos, page_no))
    except Exception:
        pass

    page_offsets.sort(key=lambda x: x[0])

    def page_at_offset(char_pos: int) -> int:
        """Return the PDF page number for a given character offset."""
        if not page_offsets:
            return 1
        result = page_offsets[0][1]
        for offset, pno in page_offsets:
            if offset <= char_pos:
                result = pno
            else:
                break
        return result

    # Chunk the flat markdown (existing logic)
    chunks = _chunk_markdown(markdown)

    # Map each chunk to its dominant page (midpoint of the chunk, not its start)
    chunk_pages: list[int] = []
    search_from = 0
    for chunk in chunks:
        # Find where this chunk appears in the full markdown
        pos = markdown.find(chunk[:60], search_from)
        if pos < 0:
            pos = markdown.find(chunk[:30])
        if pos >= 0:
            # Use the midpoint so that a chunk spanning pages lands on the correct one
            mid = pos + len(chunk) // 2
            page_no = page_at_offset(mid)
            search_from = pos + len(chunk)
        else:
            page_no = chunk_pages[-1] if chunk_pages else 1
        chunk_pages.append(page_no)

    return chunks, chunk_pages


def _extract_layout(doc: object) -> dict:
    """Extract per-page bounding boxes from Docling document.

    Returns: {page_no: [{type, l, t, r, b, page_h}]}
    Types: "text" | "table" | "figure" | "unknown"
    Coords: Docling points (origin = bottom-left of page).
    """
    layout: dict[str, list] = {}
    try:
        for item, _level in doc.iterate_items():  # type: ignore[attr-defined]
            provs = getattr(item, "prov", None)
            if not provs:
                continue
            prov = provs[0]
            page_no = getattr(prov, "page_no", None)
            bbox = getattr(prov, "bbox", None)
            if page_no is None or bbox is None:
                continue

            class_name = type(item).__name__
            if "Table" in class_name:
                el_type = "table"
            elif "Figure" in class_name or "Picture" in class_name:
                el_type = "figure"
            elif "Text" in class_name or "Section" in class_name or "Title" in class_name or "Paragraph" in class_name:
                el_type = "text"
            else:
                el_type = "unknown"

            # Get page height for coordinate conversion (PDF origin = bottom-left)
            page_h = None
            try:
                pages = getattr(doc, "pages", {})
                page_obj = pages.get(page_no) if isinstance(pages, dict) else None
                if page_obj:
                    size = getattr(page_obj, "size", None)
                    page_h = getattr(size, "height", None)
            except Exception:
                pass

            key = str(page_no)
            if key not in layout:
                layout[key] = []
            layout[key].append({
                "type": el_type,
                "l": round(float(bbox.l), 2),
                "t": round(float(bbox.t), 2),
                "r": round(float(bbox.r), 2),
                "b": round(float(bbox.b), 2),
                "page_h": round(float(page_h), 2) if page_h else None,
            })
    except Exception as exc:
        logger.warning("doc_parser.layout_extract_failed", error=str(exc))
    return layout
