"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Group as PanelGroup, Panel, Separator as PanelResizeHandle } from "react-resizable-panels";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Database,
  Edit3,
  FileText,
  Layers,
  RefreshCw,
  Save,
  Search,
  Trash2,
  X,
  Zap,
  Activity,
  AlertTriangle,
} from "lucide-react";

import DynamicPdfViewer from "@/components/document-review/DynamicPdfViewer";
import {
  getFileReview,
  updateClassification,
  approveDocument,
  deleteChunk,
  updateChunk,
  testRetrieval,
  reclassifyFile,
  ReviewData,
  ReviewChunk,
  ReviewMetric,
  ReviewSignal,
} from "@/lib/api/documents";

// ── Constants ─────────────────────────────────────────────────────────────────

const PIPELINE_STEPS = [
  { key: "parsing",    icon: FileText,   label: "Parsing",        desc: "Docling PDF→Markdown" },
  { key: "classifying",icon: Layers,     label: "Klassifizierung",desc: "doc_type · company · year" },
  { key: "analyzing",  icon: Activity,   label: "Analyse",        desc: "KPIs · Risiken · Ziele" },
  { key: "chunking",   icon: Database,   label: "Chunking",       desc: "800-Wort-Fenster · 80 Overlap" },
  { key: "embedding",  icon: Zap,        label: "Embedding",      desc: "multilingual-e5-large 1024d" },
  { key: "indexing",   icon: Search,     label: "Indexierung",    desc: "pgvector · Cosine · GIN" },
  { key: "metrics",    icon: BarChart3,  label: "Metriken",       desc: "ESG · Finanz · Signale" },
] as const;
type StepKey = (typeof PIPELINE_STEPS)[number]["key"];

const CHUNK_COLORS = [
  "#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6",
  "#ec4899","#14b8a6","#f97316","#6366f1","#84cc16",
];

// ── Quality Score ─────────────────────────────────────────────────────────────

function computeQualityScore(data: ReviewData): number {
  let score = 0;
  if (data.parsed_text && data.parsed_text.length > 500) score += 20;
  else if (data.parsed_text) score += 10;
  if (data.doc_type) score += 10;
  if (data.company_name) score += 10;
  if (data.report_year) score += 10;
  const chunks = data.chunks.length;
  if (chunks > 0) score += 15;
  if (chunks > 10) score += 5;
  const kpis = data.extracted_kpis ? Object.keys(data.extracted_kpis).length : 0;
  if (kpis > 0) score += 10;
  if (kpis > 5) score += 5;
  if (data.metrics.length > 0) score += 10;
  if (data.signals.length > 0) score += 5;
  return Math.min(100, score);
}

function QualityBadge({ score }: { score: number }) {
  const cls =
    score >= 80 ? "bg-green-100 text-green-800 border-green-200"
    : score >= 50 ? "bg-yellow-100 text-yellow-800 border-yellow-200"
    : "bg-red-100 text-red-800 border-red-200";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${cls}`}>
      Q {score}
    </span>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(s: string) {
  if (["done", "ok", "completed"].includes(s)) return "text-green-600 bg-green-50";
  if (["parsing", "analyzing", "indexing", "processing"].includes(s)) return "text-blue-600 bg-blue-50 animate-pulse";
  if (["failed", "error"].includes(s)) return "text-red-600 bg-red-50";
  return "text-gray-500 bg-gray-50";
}

function reviewBadge(s: string) {
  if (s === "approved") return "bg-green-100 text-green-800 border-green-200";
  if (s === "in_review") return "bg-yellow-100 text-yellow-800 border-yellow-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

function wordCount(text: string) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}
function estimateTokens(words: number) {
  return Math.round(words * 1.33);
}

// ── EditableField ─────────────────────────────────────────────────────────────

function EditableField({ label, value, onSave, readOnly }: { label: string; value: string; onSave?: (v: string) => void; readOnly?: boolean }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  if (readOnly) return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <span className="text-sm text-gray-700">{value || "–"}</span>
    </div>
  );
  if (!editing) return (
    <div className="flex items-center gap-2 group">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-800 flex-1">{value || "–"}</span>
      <button onClick={() => { setDraft(value); setEditing(true); }} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-100">
        <Edit3 size={12} className="text-gray-400" />
      </button>
    </div>
  );
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-28 shrink-0">{label}</span>
      <input autoFocus className="text-sm border border-blue-300 rounded px-2 py-0.5 flex-1 outline-none focus:ring-2 focus:ring-blue-200" value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { onSave?.(draft); setEditing(false); } if (e.key === "Escape") setEditing(false); }} />
      <button onClick={() => { onSave?.(draft); setEditing(false); }} className="p-1 rounded text-green-600 hover:bg-green-50"><Save size={12} /></button>
      <button onClick={() => setEditing(false)} className="p-1 rounded text-gray-400 hover:bg-gray-100"><X size={12} /></button>
    </div>
  );
}

// ── ChunkCard ─────────────────────────────────────────────────────────────────

function ChunkCard({ chunk, index, color, onDelete, onEdit, onFindInPdf }: {
  chunk: ReviewChunk; index: number; color: string;
  onDelete: () => void; onEdit: (c: string) => void; onFindInPdf: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(chunk.content);
  const words = wordCount(chunk.content);
  const tokens = estimateTokens(words);
  const oversized = words > 900;

  return (
    <div className={`border rounded-lg bg-white shadow-sm ${oversized ? "border-orange-300" : "border-gray-200"}`}>
      <div className="flex items-start gap-2 p-3 cursor-pointer hover:bg-gray-50" onClick={() => setExpanded(e => !e)}>
        <div className="w-2.5 h-2.5 rounded-full mt-1 shrink-0" style={{ background: color }} />
        {expanded ? <ChevronDown size={14} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={14} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-mono text-gray-400">#{index + 1}</span>
            <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{chunk.chunk_level}</span>
            {chunk.doc_class && <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">{chunk.doc_class}</span>}
            <span className="text-xs text-gray-400">{words} Wörter · ~{tokens} Token</span>
            {oversized && <span className="text-xs text-orange-600 bg-orange-50 rounded px-1.5 py-0.5 flex items-center gap-0.5"><AlertTriangle size={10} /> zu groß</span>}
          </div>
          <p className="text-xs text-gray-600 truncate">{chunk.content.slice(0, 100)}…</p>
        </div>
        <div className="flex gap-1 shrink-0" onClick={e => e.stopPropagation()}>
          <button onClick={onFindInPdf} title="Im PDF finden" className="p-1 rounded hover:bg-purple-50 text-gray-400 hover:text-purple-500"><Search size={12} /></button>
          <button onClick={() => { setDraft(chunk.content); setEditing(true); setExpanded(true); }} className="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-500"><Edit3 size={12} /></button>
          <button onClick={onDelete} className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"><Trash2 size={12} /></button>
        </div>
      </div>
      {expanded && !editing && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <p className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed">{chunk.content}</p>
        </div>
      )}
      {editing && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <textarea autoFocus className="w-full text-xs text-gray-700 border border-blue-300 rounded p-2 resize-y outline-none focus:ring-2 focus:ring-blue-200 mt-1" rows={8} value={draft} onChange={e => setDraft(e.target.value)} />
          <div className="flex gap-2 mt-2">
            <button onClick={() => { onEdit(draft); setEditing(false); }} className="flex items-center gap-1 text-xs bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700"><Save size={11} /> Speichern</button>
            <button onClick={() => setEditing(false)} className="text-xs text-gray-500 hover:text-gray-700">Abbrechen</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── RetrievalPanel ────────────────────────────────────────────────────────────

function RetrievalPanel({ fileId }: { fileId: string }) {
  const [query, setQuery] = useState("");
  const [minSim, setMinSim] = useState(0.25);
  const [results, setResults] = useState<{ chunk_id: string; similarity: number; chunk_level: string; doc_class: string | null; content_preview: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try { const r = await testRetrieval(fileId, query, 8, minSim); setResults(r.results); }
    catch { /* ignore */ }
    finally { setLoading(false); }
  };

  const simIcon = (s: number) =>
    s >= minSim + 0.2 ? "✅" : s >= minSim ? "⚠️" : "❌";

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-200" placeholder="Suchanfrage eingeben…" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && run()} />
        <button onClick={run} disabled={loading || !query.trim()} className="flex items-center gap-1.5 bg-blue-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-50">
          <Search size={14} />{loading ? "…" : "Testen"}
        </button>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Min. Similarity</span>
        <input type="range" min={0.1} max={0.9} step={0.05} value={minSim} onChange={e => setMinSim(parseFloat(e.target.value))} className="flex-1" />
        <span className="text-xs font-mono text-gray-600 w-8">{minSim.toFixed(2)}</span>
      </div>
      {results.length > 0 && (
        <div className="space-y-2">
          {results.map(r => {
            const pct = Math.round(r.similarity * 100);
            return (
              <div key={r.chunk_id} className="border border-gray-200 rounded-lg p-3 bg-white">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm">{simIcon(r.similarity)}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, background: r.similarity >= minSim + 0.2 ? "#22c55e" : r.similarity >= minSim ? "#f59e0b" : "#ef4444" }} />
                  </div>
                  <span className="text-xs font-semibold text-gray-700 w-10 text-right">{pct}%</span>
                  <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{r.chunk_level}</span>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">{r.content_preview}</p>
              </div>
            );
          })}
        </div>
      )}
      {results.length === 0 && !loading && query && (
        <p className="text-xs text-gray-400 text-center py-4">Keine Treffer über Schwellenwert {minSim}</p>
      )}
    </div>
  );
}

// ── KPI Table ─────────────────────────────────────────────────────────────────

function KpiTable({ kpis }: { kpis: Record<string, unknown> }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-3 py-2 text-gray-500 font-medium">KPI</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Wert</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(kpis).map(([k, v], i) => (
            <tr key={k} className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}>
              <td className="px-3 py-2 text-gray-600">{k}</td>
              <td className="px-3 py-2 text-right font-mono font-medium text-gray-800">{String(v ?? "–")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── MetricsTable ──────────────────────────────────────────────────────────────

function MetricsTable({ metrics }: { metrics: ReviewMetric[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-3 py-2 text-gray-500 font-medium">KPI</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Wert</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Einheit</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Jahr</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Periode</th>
            <th className="text-center px-3 py-2 text-gray-500 font-medium">Konfidenz</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, i) => (
            <tr key={m.id} className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}>
              <td className="px-3 py-2 text-gray-600">{m.metric_type}</td>
              <td className="px-3 py-2 text-right font-mono font-semibold text-gray-800">{m.value.toLocaleString("de-DE")}</td>
              <td className="px-3 py-2 text-right text-gray-500">{m.unit}</td>
              <td className="px-3 py-2 text-right text-gray-600">{m.year}</td>
              <td className="px-3 py-2 text-right text-gray-500">{m.period}</td>
              <td className="px-3 py-2 text-center">
                <span className={`rounded px-1.5 py-0.5 ${m.confidence === "exact" ? "bg-green-50 text-green-700" : m.confidence === "estimated" ? "bg-yellow-50 text-yellow-700" : "bg-gray-100 text-gray-500"}`}>
                  {m.confidence}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── SignalsTable ──────────────────────────────────────────────────────────────

function SignalsTable({ signals }: { signals: ReviewSignal[] }) {
  const sev = (s: string) =>
    s === "critical" ? "text-red-700 bg-red-50" : s === "high" ? "text-orange-700 bg-orange-50" : s === "medium" ? "text-yellow-700 bg-yellow-50" : "text-green-700 bg-green-50";
  return (
    <div className="space-y-2">
      {signals.map(s => (
        <div key={s.id} className="bg-white border border-gray-200 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-xs rounded px-1.5 py-0.5 ${sev(s.severity)}`}>{s.severity}</span>
            <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{s.dimension}</span>
            <span className={`text-xs rounded px-1.5 py-0.5 ${s.direction === "positive" ? "text-green-700 bg-green-50" : s.direction === "negative" ? "text-red-700 bg-red-50" : "text-gray-600 bg-gray-50"}`}>{s.direction}</span>
            {s.year && <span className="text-xs text-gray-400">{s.year}</span>}
          </div>
          <p className="text-xs text-gray-700">{s.description}</p>
        </div>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DocumentReviewPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const fileId = params.file_id as string;
  const BACKEND = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const [activeStep, setActiveStep] = useState<StepKey>("parsing");
  const [targetPage, setTargetPage] = useState<number | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState<{ text: string; id: number } | undefined>(undefined);
  const [searchStatus, setSearchStatus] = useState<"idle" | "searching" | "found" | "not-found">("idle");
  const searchIdRef = useRef(0);
  const [markdownMode, setMarkdownMode] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const blobUrlRef = useRef<string | null>(null);

  const { data, isLoading, error } = useQuery<ReviewData>({
    queryKey: ["doc-review", fileId],
    queryFn: () => getFileReview(fileId),
  });

  const invalidate = useCallback(
    () => qc.invalidateQueries({ queryKey: ["doc-review", fileId] }),
    [qc, fileId],
  );

  const classifyMut = useMutation({
    mutationFn: (p: { doc_type?: string; company_name?: string; report_year?: number }) => updateClassification(fileId, p),
    onSuccess: invalidate,
  });

  const reclassifyMut = useMutation({
    mutationFn: () => reclassifyFile(fileId),
    onSuccess: invalidate,
  });

  const approveMut = useMutation({
    mutationFn: (notes?: string) => approveDocument(fileId, notes),
    onSuccess: invalidate,
  });

  const deleteChunkMut = useMutation({
    mutationFn: (chunkId: string) => deleteChunk(chunkId),
    onSuccess: invalidate,
  });

  const editChunkMut = useMutation({
    mutationFn: ({ chunkId, content }: { chunkId: string; content: string }) => updateChunk(chunkId, content),
    onSuccess: invalidate,
  });

  // Load PDF as authenticated blob
  useEffect(() => {
    if (!data?.has_pdf) { setPdfLoading(false); return; }
    const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
    fetch(`${BACKEND}/api/v1/documents/files/${fileId}/serve`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.blob() : Promise.reject(r.status))
      .then(blob => {
        const url = URL.createObjectURL(blob);
        blobUrlRef.current = url;
        setPdfBlobUrl(url);
      })
      .catch(() => setPdfBlobUrl(null))
      .finally(() => setPdfLoading(false));
    return () => { if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current); };
  }, [fileId, data?.has_pdf, BACKEND]);

  const findChunkInPdf = useCallback((chunk: ReviewChunk) => {
    searchIdRef.current += 1;
    setSearchQuery({ text: chunk.content.slice(0, 200), id: searchIdRef.current });
    setSearchStatus("searching");
    // Auto-switch to chunking tab if we're on a different tab
    setActiveStep("chunking");
  }, []);

  if (isLoading) return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="flex flex-col items-center gap-3 text-gray-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm">Lade Dokument…</p>
      </div>
    </div>
  );

  if (error || !data) return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="text-center text-red-500">
        <AlertCircle size={32} className="mx-auto mb-2" />
        <p>Dokument nicht gefunden</p>
      </div>
    </div>
  );

  const qualityScore = computeQualityScore(data);

  const stepDone = (key: StepKey) => {
    if (!["completed", "done", "ok"].includes(data.status)) return false;
    if (key === "parsing") return Boolean(data.parsed_text);
    if (key === "classifying") return Boolean(data.doc_type);
    if (key === "analyzing") return Boolean(data.summary || data.extracted_kpis);
    if (key === "chunking") return data.chunks.length > 0;
    if (key === "embedding") return data.chunks.length > 0;
    if (key === "indexing") return (data.chunks_count ?? 0) > 0;
    if (key === "metrics") return data.metrics.length > 0 || data.signals.length > 0;
    return false;
  };

  const renderStepContent = () => {
    switch (activeStep) {
      // ── Parsing ──────────────────────────────────────────────────────────────
      case "parsing": {
        const chars = data.parsed_text?.length ?? 0;
        const words = data.parsed_text ? wordCount(data.parsed_text) : 0;
        return (
          <div className="space-y-3">
            {data.parsed_text ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span>{chars.toLocaleString()} Zeichen</span>
                    <span>·</span>
                    <span>{words.toLocaleString()} Wörter</span>
                    {data.language && <><span>·</span><span className="uppercase font-medium text-gray-600">{data.language}</span></>}
                  </div>
                  <button
                    onClick={() => setMarkdownMode(m => !m)}
                    className="text-xs border border-gray-200 rounded-lg px-3 py-1 hover:bg-gray-50 text-gray-600"
                  >
                    {markdownMode ? "Raw anzeigen" : "Markdown rendern"}
                  </button>
                </div>
                <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 max-h-[calc(100vh-340px)] overflow-y-auto">
                  {markdownMode ? (
                    <div className="text-xs text-gray-700 leading-relaxed space-y-2">
                      {data.parsed_text.split("\n").map((line, i) => {
                        if (line.startsWith("## ")) return <h2 key={i} className="text-sm font-bold text-gray-900 mt-3">{line.slice(3)}</h2>;
                        if (line.startsWith("# ")) return <h1 key={i} className="text-base font-bold text-gray-900 mt-4">{line.slice(2)}</h1>;
                        if (line.startsWith("### ")) return <h3 key={i} className="text-xs font-semibold text-gray-800 mt-2">{line.slice(4)}</h3>;
                        if (line.startsWith("- ") || line.startsWith("* ")) return <li key={i} className="ml-4 list-disc">{line.slice(2)}</li>;
                        if (line.trim() === "") return <div key={i} className="h-2" />;
                        return <p key={i}>{line}</p>;
                      })}
                    </div>
                  ) : (
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed font-sans">{data.parsed_text}</pre>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <FileText size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Kein Parsing-Ergebnis</p>
                <p className="text-xs mt-1">Dokument neu verarbeiten um Text zu extrahieren</p>
              </div>
            )}
          </div>
        );
      }

      // ── Klassifizierung ───────────────────────────────────────────────────────
      case "classifying":
        return (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              <EditableField label="Dokumenttyp" value={data.doc_type} onSave={v => classifyMut.mutate({ doc_type: v })} />
              <EditableField label="Unternehmen" value={data.company_name ?? ""} onSave={v => classifyMut.mutate({ company_name: v })} />
              <EditableField label="Berichtsjahr" value={String(data.report_year ?? "")} onSave={v => classifyMut.mutate({ report_year: parseInt(v) || undefined })} />
              <EditableField label="Sprache" value={data.language ?? ""} readOnly />
              <EditableField label="Titel" value={data.title ?? ""} readOnly />
            </div>
            <button
              onClick={() => reclassifyMut.mutate()}
              disabled={reclassifyMut.isPending}
              className="flex items-center gap-2 text-sm border border-blue-200 text-blue-600 rounded-lg px-4 py-2 hover:bg-blue-50 disabled:opacity-50"
            >
              <RefreshCw size={14} className={reclassifyMut.isPending ? "animate-spin" : ""} />
              {reclassifyMut.isPending ? "Wird klassifiziert…" : "Neu klassifizieren (LLM)"}
            </button>
            {reclassifyMut.data && (
              <div className={`text-xs rounded-lg p-3 ${reclassifyMut.data.changed ? "bg-blue-50 text-blue-700" : "bg-gray-50 text-gray-500"}`}>
                {reclassifyMut.data.changed
                  ? `Geändert: ${reclassifyMut.data.old_doc_type} → ${reclassifyMut.data.new_doc_type}`
                  : "Keine Änderung — Klassifizierung bestätigt"}
              </div>
            )}
          </div>
        );

      // ── Analyse ───────────────────────────────────────────────────────────────
      case "analyzing":
        return (
          <div className="space-y-4 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
            {data.summary && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Zusammenfassung</h4>
                <p className="text-sm text-gray-700 leading-relaxed bg-white rounded-xl border border-gray-200 p-4">{data.summary}</p>
              </div>
            )}
            {data.extracted_kpis && Object.keys(data.extracted_kpis).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Extrahierte KPIs ({Object.keys(data.extracted_kpis).length})
                </h4>
                <KpiTable kpis={data.extracted_kpis as Record<string, unknown>} />
              </div>
            )}
            {data.extracted_risks && (data.extracted_risks as unknown[]).length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Risiken ({(data.extracted_risks as unknown[]).length})
                </h4>
                <div className="space-y-2">
                  {(data.extracted_risks as { title: string; description: string; severity: string }[]).map((r, i) => (
                    <div key={i} className="bg-white border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs rounded px-1.5 py-0.5 ${r.severity === "kritisch" || r.severity === "hoch" ? "text-red-700 bg-red-50" : "text-yellow-700 bg-yellow-50"}`}>{r.severity}</span>
                        <span className="text-sm font-medium text-gray-800">{r.title}</span>
                      </div>
                      <p className="text-xs text-gray-600">{r.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {!data.summary && (!data.extracted_kpis || Object.keys(data.extracted_kpis).length === 0) && (
              <div className="text-center py-12 text-gray-400">
                <Activity size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Keine Analyse-Ergebnisse</p>
              </div>
            )}
          </div>
        );

      // ── Chunking ──────────────────────────────────────────────────────────────
      case "chunking": {
        const oversized = data.chunks.filter(c => wordCount(c.content) > 900).length;
        return (
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-xs text-gray-500">
              <span>{data.chunks.length} Chunks</span>
              {oversized > 0 && (
                <span className="flex items-center gap-1 text-orange-600 bg-orange-50 rounded px-2 py-0.5">
                  <AlertTriangle size={10} /> {oversized} zu groß (&gt;900 Wörter)
                </span>
              )}
            </div>
            {data.chunks.length > 0 ? (
              <div className="space-y-2 max-h-[calc(100vh-360px)] overflow-y-auto pr-1">
                {data.chunks.map((chunk, i) => (
                  <ChunkCard
                    key={chunk.id}
                    chunk={chunk}
                    index={i}
                    color={CHUNK_COLORS[i % CHUNK_COLORS.length]}
                    onDelete={() => deleteChunkMut.mutate(chunk.id)}
                    onEdit={content => editChunkMut.mutate({ chunkId: chunk.id, content })}
                    onFindInPdf={() => findChunkInPdf(chunk)}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-400">
                <Database size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Keine Chunks vorhanden</p>
              </div>
            )}
          </div>
        );
      }

      // ── Embedding ─────────────────────────────────────────────────────────────
      case "embedding":
        return (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              {[
                ["Modell", "intfloat/multilingual-e5-large"],
                ["Dimensionen", "1024"],
                ["Chunks gesamt", String(data.chunks.length)],
                ["Ähnlichkeitsmaß", "Cosine"],
                ["Min. Similarity", "0.25"],
                ["Laufort", "Lokal (CPU/GPU)"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm">
                  <span className="text-gray-500">{k}</span>
                  <span className="font-medium text-gray-800">{v}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 text-center">
              Embeddings werden automatisch beim Verarbeiten erstellt.<br />
              Manuell bearbeitete Chunks (Embedding = null) werden beim nächsten Retrieval-Lauf neu eingebettet.
            </p>
          </div>
        );

      // ── Indexierung ───────────────────────────────────────────────────────────
      case "indexing":
        return (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              {[
                ["Tabelle", "rag_documents"],
                ["Vektor-Index", "pgvector (HNSW)"],
                ["Volltext-Index", "GIN / tsvector"],
                ["Indexierte Chunks", String(data.chunks_count ?? data.chunks.length)],
                ["Dokument-ID", fileId.slice(0, 8) + "…"],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm">
                  <span className="text-gray-500">{k}</span>
                  <span className={`font-medium text-gray-800 ${k === "Tabelle" ? "font-mono" : ""}`}>{v}</span>
                </div>
              ))}
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Retrieval testen</h4>
              <RetrievalPanel fileId={fileId} />
            </div>
          </div>
        );

      // ── Metriken ─────────────────────────────────────────────────────────────
      case "metrics":
        return (
          <div className="space-y-4 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>ESG-Metriken: <strong className="text-gray-800">{data.metrics.filter(m => m.metric_type.includes("co2") || m.metric_type.includes("esg") || m.metric_type.includes("scope")).length}</strong></span>
              <span>Finanzkennzahlen: <strong className="text-gray-800">{data.metrics.filter(m => ["revenue","ebitda","net_income","employees","capex"].some(k => m.metric_type.includes(k))).length}</strong></span>
              <span>Signale: <strong className="text-gray-800">{data.signals.length}</strong></span>
            </div>
            {data.metrics.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Kennzahlen ({data.metrics.length})</h4>
                <MetricsTable metrics={data.metrics} />
              </div>
            )}
            {data.signals.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Signale ({data.signals.length})</h4>
                <SignalsTable signals={data.signals} />
              </div>
            )}
            {data.metrics.length === 0 && data.signals.length === 0 && (
              <div className="text-center py-12 text-gray-400">
                <BarChart3 size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Keine Metriken oder Signale extrahiert</p>
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3 shrink-0">
        <button onClick={() => router.push("/documents")} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-gray-900 truncate">{data.title ?? data.doc_type}</h1>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusColor(data.status)}`}>{data.status}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${reviewBadge(data.review_status)}`}>{data.review_status}</span>
            <QualityBadge score={qualityScore} />
            {data.company_name && <span className="text-xs text-gray-400">{data.company_name}</span>}
            {data.report_year && <span className="text-xs text-gray-400">· {data.report_year}</span>}
            {data.pages && <span className="text-xs text-gray-400">· {data.pages} Seiten</span>}
          </div>
        </div>
        <button
          onClick={() => approveMut.mutate(undefined)}
          disabled={data.review_status === "approved" || approveMut.isPending}
          className={`flex items-center gap-1.5 text-sm rounded-lg px-4 py-2 font-medium transition-colors ${data.review_status === "approved" ? "bg-green-100 text-green-700 cursor-default" : "bg-green-600 text-white hover:bg-green-700"}`}
        >
          <CheckCircle2 size={15} />
          {data.review_status === "approved" ? "Freigegeben" : "Freigeben"}
        </button>
      </header>

      {/* Split pane */}
      <PanelGroup orientation="horizontal" className="flex-1 overflow-hidden">
        {/* Left: PDF.js viewer */}
        <Panel defaultSize="45" minSize="20%">
          <div className="h-full flex flex-col">
            {/* Search status banner */}
            {searchStatus !== "idle" && (
              <div className={`flex items-center gap-2 px-3 py-1.5 text-xs shrink-0 ${
                searchStatus === "searching" ? "bg-blue-900 text-blue-200"
                : searchStatus === "found" ? "bg-green-900 text-green-200"
                : "bg-orange-900 text-orange-200"
              }`}>
                {searchStatus === "searching" && (
                  <><div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" /> Suche im PDF…</>
                )}
                {searchStatus === "found" && <><span>✓</span> Chunk gefunden</>}
                {searchStatus === "not-found" && <><span>✗</span> Text nicht im PDF gefunden — möglicherweise unterschiedliche Formatierung</>}
                <button onClick={() => setSearchStatus("idle")} className="ml-auto opacity-60 hover:opacity-100">✕</button>
              </div>
            )}
            <div className="flex-1 overflow-hidden">
              <DynamicPdfViewer
                blobUrl={pdfBlobUrl}
                loading={pdfLoading}
                targetPage={targetPage}
                searchQuery={searchQuery}
                onPageChange={(page, total) => { void page; void total; }}
                onSearchResult={(page) => setSearchStatus(page !== null ? "found" : "not-found")}
              />
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1.5 bg-gray-200 hover:bg-blue-400 transition-colors cursor-col-resize" />

        {/* Right: Pipeline */}
        <Panel defaultSize="55" minSize="25%">
          <div className="h-full flex flex-col bg-gray-50">
            {/* Step tabs */}
            <div className="flex items-center gap-1 px-3 py-2 bg-white border-b border-gray-200 overflow-x-auto shrink-0">
              {PIPELINE_STEPS.map((step) => {
                const Icon = step.icon;
                const done = stepDone(step.key);
                const active = activeStep === step.key;
                return (
                  <button
                    key={step.key}
                    onClick={() => setActiveStep(step.key)}
                    className={`flex items-center gap-1.5 text-xs rounded-lg px-3 py-1.5 whitespace-nowrap transition-colors ${active ? "bg-blue-600 text-white shadow-sm" : "text-gray-500 hover:bg-gray-100"}`}
                  >
                    {done ? <CheckCircle2 size={12} className={active ? "text-blue-200" : "text-green-500"} /> : <Icon size={12} />}
                    {step.label}
                  </button>
                );
              })}
            </div>

            {/* Step description */}
            <div className="px-4 py-1.5 bg-white border-b border-gray-100 shrink-0">
              <p className="text-xs text-gray-400">{PIPELINE_STEPS.find(s => s.key === activeStep)?.desc}</p>
            </div>

            {/* Step content */}
            <div className="flex-1 overflow-y-auto p-4">{renderStepContent()}</div>

            {/* Audit log */}
            {data.audit_log.length > 0 && (
              <div className="shrink-0 border-t border-gray-200 bg-white px-4 py-2">
                <details>
                  <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 flex items-center gap-1">
                    <Clock size={11} /> {data.audit_log.length} Änderungen protokolliert
                  </summary>
                  <div className="mt-2 space-y-1 max-h-28 overflow-y-auto">
                    {data.audit_log.map(e => (
                      <div key={e.id} className="flex items-start gap-2 text-xs text-gray-500">
                        <span className="font-mono bg-gray-100 rounded px-1 shrink-0">{e.action}</span>
                        {e.field && <span className="text-gray-400">{e.field}</span>}
                        <span className="text-gray-300 ml-auto shrink-0">{new Date(e.created_at).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" })}</span>
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            )}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  );
}
