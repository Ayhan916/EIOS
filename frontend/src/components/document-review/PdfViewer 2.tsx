"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from "lucide-react";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

// A highlight region on a specific PDF page
export interface PdfHighlight {
  page: number;          // 1-indexed
  color: string;         // CSS color (with opacity), e.g. "rgba(34,197,94,0.3)"
  label?: string;
  // Normalized coordinates (0..1) relative to page width/height
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

interface Props {
  blobUrl: string | null;
  loading?: boolean;
  highlights?: PdfHighlight[];
  targetPage?: number;           // jump to this page when it changes
  onPageChange?: (page: number, total: number) => void;
}

export default function PdfViewer({ blobUrl, loading, highlights = [], targetPage, onPageChange }: Props) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.2);
  const [pageInput, setPageInput] = useState<string>("1");
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Jump to targetPage when it changes externally
  useEffect(() => {
    if (targetPage && targetPage !== currentPage) {
      goToPage(targetPage);
    }
  }, [targetPage]); // eslint-disable-line react-hooks/exhaustive-deps

  const goToPage = useCallback((page: number) => {
    const clamped = Math.max(1, Math.min(page, numPages || 1));
    setCurrentPage(clamped);
    setPageInput(String(clamped));
    const el = pageRefs.current.get(clamped);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [numPages]);

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    onPageChange?.(1, numPages);
  }, [onPageChange]);

  // Track which page is currently in view via IntersectionObserver
  useEffect(() => {
    if (!containerRef.current || numPages === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        let maxRatio = 0;
        let visiblePage = currentPage;
        entries.forEach((entry) => {
          if (entry.intersectionRatio > maxRatio) {
            maxRatio = entry.intersectionRatio;
            const pageNum = parseInt((entry.target as HTMLElement).dataset.page ?? "1");
            visiblePage = pageNum;
          }
        });
        if (maxRatio > 0.1) {
          setCurrentPage(visiblePage);
          setPageInput(String(visiblePage));
          onPageChange?.(visiblePage, numPages);
        }
      },
      { root: containerRef.current, threshold: [0.1, 0.5, 0.9] }
    );
    pageRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [numPages, currentPage, onPageChange]);

  const highlightsForPage = (page: number) =>
    highlights.filter((h) => h.page === page);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 bg-gray-900">
        <div className="flex flex-col items-center gap-2">
          <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">PDF wird geladen…</span>
        </div>
      </div>
    );
  }

  if (!blobUrl) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500 bg-gray-900">
        <div className="text-center">
          <p className="text-sm">PDF nicht verfügbar</p>
          <p className="text-xs mt-1 opacity-60">Originaldatei nicht gefunden</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-800 border-b border-gray-700 shrink-0">
        {/* Page navigation */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            className="p-1 rounded hover:bg-gray-700 text-gray-400 disabled:opacity-30"
          >
            <ChevronLeft size={16} />
          </button>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <span>Seite</span>
            <input
              className="w-10 text-center bg-gray-700 text-gray-200 rounded px-1 py-0.5 outline-none focus:ring-1 focus:ring-blue-500"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") goToPage(parseInt(pageInput) || 1);
              }}
              onBlur={() => goToPage(parseInt(pageInput) || 1)}
            />
            <span>von {numPages}</span>
          </div>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= numPages}
            className="p-1 rounded hover:bg-gray-700 text-gray-400 disabled:opacity-30"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Zoom */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.2))}
            className="p-1 rounded hover:bg-gray-700 text-gray-400"
          >
            <ZoomOut size={14} />
          </button>
          <span className="text-xs text-gray-400 w-10 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(3, s + 0.2))}
            className="p-1 rounded hover:bg-gray-700 text-gray-400"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setScale(1.2)}
            className="p-1 rounded hover:bg-gray-700 text-gray-400"
            title="Zoom zurücksetzen"
          >
            <RotateCw size={14} />
          </button>
        </div>
      </div>

      {/* Scrollable page area */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-auto flex flex-col items-center gap-4 py-4 px-2"
        style={{ background: "#1f2937" }}
      >
        <Document
          file={blobUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <div className="text-gray-400 text-sm py-8">Dokument wird geladen…</div>
          }
          error={
            <div className="text-red-400 text-sm py-8">Fehler beim Laden des Dokuments</div>
          }
        >
          {Array.from({ length: numPages }, (_, i) => i + 1).map((pageNum) => {
            const pageHighlights = highlightsForPage(pageNum);
            return (
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
                />
                {/* Overlay highlights */}
                {pageHighlights.length > 0 && (
                  <PageHighlightOverlay
                    highlights={pageHighlights}
                    scale={scale}
                    pageNum={pageNum}
                    blobUrl={blobUrl}
                  />
                )}
                {/* Page number badge */}
                <div className="absolute bottom-1 right-2 text-xs text-gray-400 bg-black/40 rounded px-1.5 py-0.5 pointer-events-none">
                  {pageNum}
                </div>
              </div>
            );
          })}
        </Document>
      </div>
    </div>
  );
}

// Overlay that renders highlight rectangles on top of a PDF page
function PageHighlightOverlay({
  highlights,
  scale,
  pageNum,
  blobUrl,
}: {
  highlights: PdfHighlight[];
  scale: number;
  pageNum: number;
  blobUrl: string;
}) {
  const [pageSize, setPageSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    // Get the rendered canvas size to calculate overlay dimensions
    pdfjs.getDocument(blobUrl).promise.then((doc) =>
      doc.getPage(pageNum).then((page) => {
        const viewport = page.getViewport({ scale });
        setPageSize({ width: viewport.width, height: viewport.height });
      })
    );
  }, [blobUrl, pageNum, scale]);

  if (!pageSize) return null;

  return (
    <div
      className="absolute inset-0 pointer-events-none"
      style={{ width: pageSize.width, height: pageSize.height }}
    >
      {highlights.map((h, i) => {
        if (h.x === undefined) return null;
        return (
          <div
            key={i}
            className="absolute rounded"
            title={h.label}
            style={{
              left: h.x * pageSize.width,
              top: (h.y ?? 0) * pageSize.height,
              width: (h.width ?? 0.2) * pageSize.width,
              height: (h.height ?? 0.02) * pageSize.height,
              background: h.color,
              border: `1px solid ${h.color.replace(/[\d.]+\)$/, "0.8)")}`,
            }}
          />
        );
      })}
    </div>
  );
}
