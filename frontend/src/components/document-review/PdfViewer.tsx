"use client";

// Polyfill URL.parse — required by pdfjs-dist v4, missing in older browsers / Safari < 18
if (typeof URL !== "undefined" && typeof URL.parse !== "function") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (URL as any).parse = (url: string, base?: string): URL | null => {
    try { return new URL(url, base); } catch { return null; }
  };
}

import { useState, useCallback, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from "lucide-react";

// Worker is served from /public
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

export interface PdfHighlight {
  page: number;
  color: string;
  label?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

interface Props {
  blobUrl: string | null;
  loading?: boolean;
  highlights?: PdfHighlight[];
  /** When this changes (by id), search for text and jump to matching page */
  searchQuery?: { text: string; id: number };
  /** Highlight these keywords in the text layer without triggering page navigation */
  highlightTerms?: string[];
  targetPage?: number;
  onPageChange?: (page: number, total: number) => void;
  /** Called with the page number where searchQuery text was found (or null) */
  onSearchResult?: (page: number | null) => void;
}

export default function PdfViewer({
  blobUrl,
  loading,
  highlights = [],
  searchQuery,
  highlightTerms,
  targetPage,
  onPageChange,
  onSearchResult,
}: Props) {
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [pageInput, setPageInput] = useState("1");
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const pdfDocRef = useRef<pdfjs.PDFDocumentProxy | null>(null);
  const pendingScrollPage = useRef<number | null>(null);
  // Ref so search closure always calls the latest goToPage (avoids stale numPages capture)
  const goToPageRef = useRef<(page: number) => void>(() => {});

  const goToPage = useCallback(
    (page: number) => {
      const clamped = numPages > 0 ? Math.max(1, Math.min(page, numPages)) : page;
      setCurrentPage(clamped);
      setPageInput(String(clamped));
      const el = pageRefs.current.get(clamped);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        pendingScrollPage.current = null;
      } else {
        // Pages not yet rendered — store and retry when numPages populates
        pendingScrollPage.current = clamped;
      }
    },
    [numPages],
  );

  // Keep ref pointing to latest goToPage
  useEffect(() => { goToPageRef.current = goToPage; }, [goToPage]);

  // Execute pending scroll once pages are available
  useEffect(() => {
    if (numPages > 0 && pendingScrollPage.current !== null) {
      const target = Math.max(1, Math.min(pendingScrollPage.current, numPages));
      pendingScrollPage.current = null;
      setCurrentPage(target);
      setPageInput(String(target));
      requestAnimationFrame(() => {
        pageRefs.current.get(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }, [numPages]);

  // Load pdfjs doc separately for text search
  useEffect(() => {
    if (!blobUrl) return;
    pdfjs.getDocument(blobUrl).promise.then((doc) => {
      pdfDocRef.current = doc;
    });
    return () => { pdfDocRef.current = null; };
  }, [blobUrl]);

  // Run text search when searchQuery changes
  useEffect(() => {
    if (!searchQuery?.text) return;

    const run = async (attempt = 0): Promise<void> => {
      // Wait up to 8s for pdfDocRef to be populated (PDF still loading)
      if (!pdfDocRef.current) {
        if (attempt < 16) {
          setTimeout(() => run(attempt + 1), 500);
        } else {
          onSearchResult?.(null);
        }
        return;
      }

      const doc = pdfDocRef.current;
      // Extract meaningful words (>3 chars) for fuzzy matching
      const words = searchQuery.text
        .slice(0, 200)
        .toLowerCase()
        .replace(/[^a-z0-9äöüß\s]/g, " ")
        .split(/\s+/)
        // Keep numeric tokens at any length, text tokens need ≥ 4 chars
        .filter((w) => w.length >= 2 && (/^\d/.test(w) ? w.length >= 2 : w.length >= 4));

      if (words.length === 0) { onSearchResult?.(null); return; }

      let bestPage = -1;
      let bestScore = 0;

      for (let i = 1; i <= doc.numPages; i++) {
        const page = await doc.getPage(i);
        const tc = await page.getTextContent();
        const pageText = tc.items
          .map((item) => ("str" in item ? (item as { str: string }).str : ""))
          .join(" ")
          .toLowerCase()
          .replace(/[^a-z0-9äöüß\s]/g, " ");

        const hits = words.filter((w) => pageText.includes(w)).length;
        const score = hits / words.length;

        if (score > bestScore) {
          bestScore = score;
          bestPage = i;
        }
      }

      if (bestScore >= 0.3 && bestPage > 0) {
        goToPageRef.current(bestPage);
        onSearchResult?.(bestPage);
      } else {
        onSearchResult?.(null);
      }
    };

    run();
  }, [searchQuery?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Jump when targetPage changes externally
  useEffect(() => {
    if (targetPage) goToPageRef.current(targetPage);
  }, [targetPage]); // eslint-disable-line react-hooks/exhaustive-deps

  const onDocumentLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      onPageChange?.(1, numPages);
    },
    [onPageChange],
  );

  // Track visible page
  useEffect(() => {
    if (!containerRef.current || numPages === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        let maxRatio = 0;
        let visiblePage = currentPage;
        entries.forEach((entry) => {
          if (entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            visiblePage = parseInt((entry.target as HTMLElement).dataset.page ?? "1");
          }
        });
        if (maxRatio > 0.1) {
          setCurrentPage(visiblePage);
          setPageInput(String(visiblePage));
          onPageChange?.(visiblePage, numPages);
        }
      },
      { root: containerRef.current, threshold: [0.1, 0.5, 0.9] },
    );
    pageRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [numPages]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900 text-gray-500">
        <div className="flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">PDF wird geladen…</span>
        </div>
      </div>
    );
  }

  if (!blobUrl) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900 text-gray-500">
        <div className="text-center">
          <p className="text-sm">PDF nicht verfügbar</p>
          <p className="text-xs mt-1 opacity-60">Originaldatei nicht gefunden</p>
        </div>
      </div>
    );
  }

  const highlightsForPage = (page: number) => highlights.filter((h) => h.page === page);

  // highlightTerms takes priority (direct navigation path); fall back to searchQuery keywords
  const highlightKeywords = highlightTerms && highlightTerms.length > 0
    ? highlightTerms
    : searchQuery?.text
      ? searchQuery.text
          .slice(0, 200)
          .toLowerCase()
          .replace(/[^a-z0-9äöüß\s]/g, " ")
          .split(/\s+/)
          .filter(w => w.length >= 3 && (/^\d/.test(w) ? w.length >= 2 : w.length >= 4))
          .slice(0, 8)
      : [];

  const customTextRenderer = highlightKeywords.length > 0
    ? ({ str }: { str: string }) => {
        if (!str.trim()) return str;
        const lower = str.toLowerCase();
        const matched = highlightKeywords.some(kw => lower.includes(kw));
        if (!matched) return str;
        let result = str;
        for (const kw of highlightKeywords) {
          const idx = lower.indexOf(kw);
          if (idx >= 0) {
            result =
              result.slice(0, idx) +
              `<mark style="background:#fef08a;color:#1a1a1a;border-radius:2px;padding:0 1px">` +
              result.slice(idx, idx + kw.length) +
              `</mark>` +
              result.slice(idx + kw.length);
            break;
          }
        }
        return result;
      }
    : undefined;

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700 shrink-0">
        <div className="flex items-center gap-1">
          <button onClick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} className="p-1 rounded hover:bg-gray-700 text-gray-400 disabled:opacity-30">
            <ChevronLeft size={16} />
          </button>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <span>Seite</span>
            <input
              className="w-10 text-center bg-gray-700 text-gray-200 rounded px-1 py-0.5 outline-none focus:ring-1 focus:ring-blue-500"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && goToPage(parseInt(pageInput) || 1)}
              onBlur={() => goToPage(parseInt(pageInput) || 1)}
            />
            <span>von {numPages}</span>
          </div>
          <button onClick={() => goToPage(currentPage + 1)} disabled={currentPage >= numPages} className="p-1 rounded hover:bg-gray-700 text-gray-400 disabled:opacity-30">
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="flex items-center gap-1">
          <button onClick={() => setScale((s) => Math.max(0.5, +(s - 0.2).toFixed(1)))} className="p-1 rounded hover:bg-gray-700 text-gray-400"><ZoomOut size={14} /></button>
          <span className="text-xs text-gray-400 w-10 text-center">{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale((s) => Math.min(3, +(s + 0.2).toFixed(1)))} className="p-1 rounded hover:bg-gray-700 text-gray-400"><ZoomIn size={14} /></button>
          <button onClick={() => setScale(1.2)} className="p-1 rounded hover:bg-gray-700 text-gray-400" title="Reset"><RotateCw size={14} /></button>
        </div>
      </div>

      {/* Pages */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-auto flex flex-col items-center gap-4 py-4 px-2"
        style={{ background: "#1f2937" }}
      >
        <Document
          file={blobUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={<div className="text-gray-400 text-sm py-8">Dokument wird geladen…</div>}
          error={<div className="text-red-400 text-sm py-8">Fehler beim Laden</div>}
        >
          {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => (
            <div
              key={pageNum}
              data-page={pageNum}
              ref={(el) => {
                if (el) pageRefs.current.set(pageNum, el);
                else pageRefs.current.delete(pageNum);
              }}
              className="relative shadow-2xl"
              style={{ lineHeight: 0 }}
            >
              <Page
                pageNumber={pageNum}
                scale={scale}
                renderTextLayer
                renderAnnotationLayer
                customTextRenderer={customTextRenderer}
              />
              {highlightsForPage(pageNum).map((h, i) =>
                h.x !== undefined ? (
                  <HighlightBox key={i} highlight={h} scale={scale} pageNum={pageNum} blobUrl={blobUrl} />
                ) : null,
              )}
              <div className="absolute bottom-1 right-2 text-xs text-gray-400 bg-black/40 rounded px-1.5 py-0.5 pointer-events-none">
                {pageNum}
              </div>
            </div>
          ))}
        </Document>
      </div>
    </div>
  );
}

function HighlightBox({ highlight, scale, pageNum, blobUrl }: { highlight: PdfHighlight; scale: number; pageNum: number; blobUrl: string }) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  useEffect(() => {
    pdfjs.getDocument(blobUrl).promise
      .then((doc) => doc.getPage(pageNum))
      .then((page) => {
        const vp = page.getViewport({ scale });
        setSize({ width: vp.width, height: vp.height });
      });
  }, [blobUrl, pageNum, scale]);
  if (!size || highlight.x === undefined) return null;
  return (
    <div
      className="absolute rounded pointer-events-none"
      title={highlight.label}
      style={{
        left: highlight.x * size.width,
        top: (highlight.y ?? 0) * size.height,
        width: (highlight.width ?? 0.2) * size.width,
        height: (highlight.height ?? 0.02) * size.height,
        background: highlight.color,
      }}
    />
  );
}
