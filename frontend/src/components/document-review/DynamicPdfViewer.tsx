"use client";

import dynamic from "next/dynamic";
import type { PdfHighlight, LayoutElement, ChunkBand } from "./PdfViewer";

// Prevent pdfjs-dist from running on the server (DOMMatrix is not defined in Node.js)
const PdfViewer = dynamic(() => import("./PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-gray-900 text-gray-500">
      <div className="flex flex-col items-center gap-2">
        <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs">PDF-Viewer wird geladen…</span>
      </div>
    </div>
  ),
});

export type { PdfHighlight, LayoutElement, ChunkBand };
export default PdfViewer;
