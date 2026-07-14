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
  Eye,
  EyeOff,
  BookOpen,
  XCircle,
} from "lucide-react";

import DynamicPdfViewer from "@/components/document-review/DynamicPdfViewer";
import {
  getFileReview,
  updateClassification,
  updateKpis,
  approveDocument,
  unapproveDocument,
  runCopilotSandbox,
  type SandboxResult,
  deleteChunk,
  updateChunk,
  splitChunk,
  mergeChunks,
  testRetrieval,
  reclassifyFile,
  reanalyzeFile,
  excludeChunk,
  toggleCopilotVisibility,
  updateMetric,
  deleteMetric,
  addMetric,
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
  { key: "sandbox",    icon: BookOpen,   label: "Copilot-Test",   desc: "Testfragen direkt ans Dokument stellen" },
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

function ChunkCard({ chunk, index, color, onDelete, onEdit, onFindInPdf, onSplit, onMergeWith, onExclude, isLast }: {
  chunk: ReviewChunk; index: number; color: string; isLast: boolean;
  onDelete: () => void; onEdit: (c: string) => void; onFindInPdf: () => void;
  onSplit: (splitAt: number) => void; onMergeWith: () => void; onExclude: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [splitting, setSplitting] = useState(false);
  const [draft, setDraft] = useState(chunk.content);
  const [splitPos, setSplitPos] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const words = wordCount(chunk.content);
  const tokens = estimateTokens(words);
  const oversized = words > 900;

  const handleSplitClick = () => {
    setSplitPos(Math.floor(chunk.content.length / 2));
    setSplitting(true);
    setExpanded(true);
    setEditing(false);
  };

  const isExcluded = Boolean(chunk.excluded_from_index);

  return (
    <div className={`border rounded-lg bg-white shadow-sm transition-opacity ${isExcluded ? "opacity-50 border-dashed border-gray-300" : oversized ? "border-orange-300" : "border-gray-200"}`}>
      <div className="flex items-start gap-2 p-3 cursor-pointer hover:bg-gray-50" onClick={() => setExpanded(e => !e)}>
        <div className="w-2.5 h-2.5 rounded-full mt-1 shrink-0" style={{ background: color }} />
        {expanded ? <ChevronDown size={14} className="mt-0.5 shrink-0 text-gray-400" /> : <ChevronRight size={14} className="mt-0.5 shrink-0 text-gray-400" />}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-mono text-gray-400">#{index + 1}</span>
            <span className="text-xs bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">{chunk.chunk_level}</span>
            {chunk.doc_class && <span className="text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5">{chunk.doc_class}</span>}
            {chunk.page_number != null && (
              <span className="text-xs bg-purple-50 text-purple-600 rounded px-1.5 py-0.5 font-medium">S.{chunk.page_number}</span>
            )}
            <span className="text-xs text-gray-400">{words} Wörter · ~{tokens} Token</span>
            {oversized && <span className="text-xs text-orange-600 bg-orange-50 rounded px-1.5 py-0.5 flex items-center gap-0.5"><AlertTriangle size={10} /> zu groß</span>}
            {isExcluded && <span className="text-xs text-gray-400 bg-gray-100 rounded px-1.5 py-0.5 flex items-center gap-0.5"><EyeOff size={9} /> ausgeschlossen</span>}
          </div>
          <p className="text-xs text-gray-600 truncate">{chunk.content.slice(0, 100)}…</p>
        </div>
        <div className="flex gap-1 shrink-0" onClick={e => e.stopPropagation()}>
          <button onClick={onFindInPdf} title="Im PDF finden" className="p-1 rounded hover:bg-purple-50 text-gray-400 hover:text-purple-500"><Search size={12} /></button>
          <button onClick={() => { setDraft(chunk.content); setEditing(true); setSplitting(false); setExpanded(true); }} title="Bearbeiten" className="p-1 rounded hover:bg-blue-50 text-gray-400 hover:text-blue-500"><Edit3 size={12} /></button>
          <button onClick={handleSplitClick} title="Teilen" className="p-1 rounded hover:bg-yellow-50 text-gray-400 hover:text-yellow-600">
            <svg width={12} height={12} viewBox="0 0 16 16" fill="currentColor"><path d="M8 1v14M3 5l5-4 5 4M3 11l5 4 5-4" stroke="currentColor" strokeWidth={1.5} fill="none"/></svg>
          </button>
          {!isLast && (
            <button onClick={onMergeWith} title="Mit nächstem zusammenführen" className="p-1 rounded hover:bg-green-50 text-gray-400 hover:text-green-600">
              <svg width={12} height={12} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.5}><path d="M8 3v10M3 8h10"/></svg>
            </button>
          )}
          <button
            onClick={onExclude}
            title={isExcluded ? "Aus Index wieder einschließen" : "Aus Copilot-Index ausschließen"}
            className={`p-1 rounded ${isExcluded ? "text-gray-500 hover:text-gray-700 hover:bg-gray-100" : "text-gray-400 hover:text-orange-500 hover:bg-orange-50"}`}
          >
            {isExcluded ? <Eye size={12} /> : <EyeOff size={12} />}
          </button>
          <button onClick={onDelete} title="Löschen" className="p-1 rounded hover:bg-red-50 text-gray-400 hover:text-red-500"><Trash2 size={12} /></button>
        </div>
      </div>

      {expanded && !editing && !splitting && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <p className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed">{chunk.content}</p>
        </div>
      )}

      {editing && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <textarea autoFocus ref={textareaRef} className="w-full text-xs text-gray-700 border border-blue-300 rounded p-2 resize-y outline-none focus:ring-2 focus:ring-blue-200 mt-1" rows={8} value={draft} onChange={e => setDraft(e.target.value)} />
          <div className="flex gap-2 mt-2">
            <button onClick={() => { onEdit(draft); setEditing(false); }} className="flex items-center gap-1 text-xs bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700"><Save size={11} /> Speichern</button>
            <button onClick={() => setEditing(false)} className="text-xs text-gray-500 hover:text-gray-700">Abbrechen</button>
          </div>
        </div>
      )}

      {splitting && (
        <div className="px-4 pb-3 border-t border-gray-100 pt-2">
          <p className="text-xs text-gray-500 mb-2">Trennposition: Zeichen {splitPos} von {chunk.content.length}</p>
          <div className="relative">
            <div className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed bg-gray-50 rounded p-2 border border-gray-200 max-h-48 overflow-y-auto font-mono">
              <span className="bg-blue-100">{chunk.content.slice(0, splitPos)}</span>
              <span className="inline-block w-0.5 h-3.5 bg-blue-500 align-middle mx-0.5 animate-pulse" />
              <span>{chunk.content.slice(splitPos)}</span>
            </div>
          </div>
          <input type="range" min={1} max={chunk.content.length - 1} value={splitPos}
            onChange={e => setSplitPos(parseInt(e.target.value))}
            className="w-full mt-2" />
          <div className="flex gap-2 mt-2 text-xs text-gray-500">
            <span>Teil A: {chunk.content.slice(0, splitPos).split(/\s+/).filter(Boolean).length} Wörter</span>
            <span>·</span>
            <span>Teil B: {chunk.content.slice(splitPos).split(/\s+/).filter(Boolean).length} Wörter</span>
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={() => { onSplit(splitPos); setSplitting(false); }} className="flex items-center gap-1 text-xs bg-yellow-500 text-white rounded px-3 py-1 hover:bg-yellow-600"><Save size={11} /> Teilen</button>
            <button onClick={() => setSplitting(false)} className="text-xs text-gray-500 hover:text-gray-700">Abbrechen</button>
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

// ── KPI schema helpers ────────────────────────────────────────────────────────

type RichKpiEntry = { value: string | number | null; unit?: string | null; year?: number | null; scope?: string | null; confidence?: string | null; source_page?: number | null };

function isRich(v: unknown): v is RichKpiEntry {
  return typeof v === "object" && v !== null && "value" in v;
}

function kpiDisplayValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (isRich(v)) return v.value != null ? String(v.value) : "–";
  return String(v);
}

function kpiStringForSearch(key: string, v: unknown): string {
  if (isRich(v)) return `${v.value ?? ""} ${v.unit ?? ""} ${key}`;
  return `${String(v ?? "")} ${key}`;
}

// ── Editable KPI Table ────────────────────────────────────────────────────────

function EditableKpiTable({ kpis, onSave, saving, onFindInPdf }: {
  kpis: Record<string, unknown>;
  onSave: (kpis: Record<string, unknown>) => void;
  saving: boolean;
  onFindInPdf?: (key: string, value: string, sourcePage?: number | null) => void;
}) {
  const [draft, setDraft] = useState<Record<string, unknown>>(() => ({ ...kpis }));
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [addKey, setAddKey] = useState("");
  const [addVal, setAddVal] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const save = () => onSave(draft);

  const del = (key: string) => {
    const next = { ...draft };
    delete next[key];
    setDraft(next);
  };

  const startEdit = (key: string) => {
    setEditingKey(key);
    setEditDraft(kpiDisplayValue(draft[key]));
  };

  const commitEdit = (key: string) => {
    const existing = draft[key];
    if (isRich(existing)) {
      setDraft(d => ({ ...d, [key]: { ...existing, value: editDraft } }));
    } else {
      setDraft(d => ({ ...d, [key]: editDraft }));
    }
    setEditingKey(null);
  };

  const addEntry = () => {
    if (!addKey.trim()) return;
    setDraft(d => ({ ...d, [addKey.trim()]: addVal.trim() }));
    setAddKey(""); setAddVal(""); setShowAdd(false);
  };

  const hasRich = Object.values(draft).some(isRich);

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="w-full text-xs">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-3 py-2 text-gray-500 font-medium">KPI</th>
              <th className="text-right px-3 py-2 text-gray-500 font-medium">Wert</th>
              {hasRich && <th className="text-right px-3 py-2 text-gray-500 font-medium">Einheit</th>}
              {hasRich && <th className="text-right px-3 py-2 text-gray-500 font-medium">Jahr</th>}
              {hasRich && <th className="text-center px-3 py-2 text-gray-500 font-medium">Konfidenz</th>}
              {hasRich && <th className="text-center px-3 py-2 text-gray-500 font-medium">Seite</th>}
              <th className="w-8" />
            </tr>
          </thead>
          <tbody>
            {Object.entries(draft).map(([k, v], i) => {
              const rich = isRich(v) ? v : null;
              const displayVal = kpiDisplayValue(v);
              return (
                <tr key={k} className={`group ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                  <td className="px-3 py-2 text-gray-600">
                    <div className="flex items-center gap-1.5">
                      {onFindInPdf && (
                        <button
                          onClick={() => onFindInPdf(k, kpiStringForSearch(k, v), rich?.source_page)}
                          title="Im PDF finden"
                          className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-purple-50 text-gray-400 hover:text-purple-500 shrink-0 transition-opacity"
                        >
                          <Search size={10} />
                        </button>
                      )}
                      <span>{k}</span>
                      {rich?.scope && <span className="text-gray-400 text-[10px] bg-gray-100 rounded px-1">{rich.scope}</span>}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {editingKey === k ? (
                      <input
                        autoFocus
                        className="text-right bg-blue-50 border border-blue-300 rounded px-2 py-0.5 outline-none focus:ring-1 focus:ring-blue-400 w-full"
                        value={editDraft}
                        onChange={e => setEditDraft(e.target.value)}
                        onBlur={() => commitEdit(k)}
                        onKeyDown={e => { if (e.key === "Enter") commitEdit(k); if (e.key === "Escape") setEditingKey(null); }}
                      />
                    ) : (
                      <span
                        className="font-mono font-medium text-gray-800 cursor-pointer hover:bg-blue-50 rounded px-1"
                        onClick={() => startEdit(k)}
                        title="Klicken zum Bearbeiten"
                      >{displayVal}</span>
                    )}
                  </td>
                  {hasRich && <td className="px-3 py-2 text-right text-gray-500">{rich?.unit ?? "–"}</td>}
                  {hasRich && <td className="px-3 py-2 text-right text-gray-600">{rich?.year ?? "–"}</td>}
                  {hasRich && (
                    <td className="px-3 py-2 text-center">
                      {rich?.confidence ? (
                        <span className={`rounded px-1.5 py-0.5 ${rich.confidence === "exact" ? "bg-green-50 text-green-700" : rich.confidence === "estimated" ? "bg-yellow-50 text-yellow-700" : "bg-gray-100 text-gray-500"}`}>
                          {rich.confidence}
                        </span>
                      ) : "–"}
                    </td>
                  )}
                  {hasRich && (
                    <td className="px-3 py-2 text-center">
                      {rich?.source_page ? (
                        <span className="text-purple-600 bg-purple-50 rounded px-1.5 py-0.5 font-medium">S.{rich.source_page}</span>
                      ) : "–"}
                    </td>
                  )}
                  <td className="px-1">
                    <button onClick={() => del(k)} className="p-0.5 rounded text-gray-300 hover:text-red-400"><X size={10} /></button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {showAdd && (
        <div className="flex gap-2">
          <input className="flex-1 text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="KPI-Name" value={addKey} onChange={e => setAddKey(e.target.value)} />
          <input className="w-32 text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="Wert" value={addVal} onChange={e => setAddVal(e.target.value)} onKeyDown={e => e.key === "Enter" && addEntry()} />
          <button onClick={addEntry} className="text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700">+</button>
          <button onClick={() => setShowAdd(false)} className="text-xs text-gray-400 hover:text-gray-600"><X size={12} /></button>
        </div>
      )}
      <div className="flex gap-2">
        <button onClick={() => setShowAdd(s => !s)} className="text-xs text-blue-500 hover:text-blue-700">+ KPI hinzufügen</button>
        <button onClick={save} disabled={saving} className="ml-auto flex items-center gap-1 text-xs bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700 disabled:opacity-50">
          <Save size={11} />{saving ? "Speichern…" : "Alle KPIs speichern"}
        </button>
      </div>
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

// ── AddMetricForm ─────────────────────────────────────────────────────────────

function AddMetricForm({ onAdd, saving }: { onAdd: (p: { metric_type: string; value: number; unit: string; year: number; period?: string; confidence?: string }) => void; saving: boolean }) {
  const [show, setShow] = useState(false);
  const [f, setF] = useState({ metric_type: "", value: "", unit: "", year: new Date().getFullYear().toString(), period: "FY", confidence: "exact" });

  const submit = () => {
    if (!f.metric_type || !f.value || !f.unit || !f.year) return;
    onAdd({ metric_type: f.metric_type, value: parseFloat(f.value), unit: f.unit, year: parseInt(f.year), period: f.period, confidence: f.confidence });
    setF({ metric_type: "", value: "", unit: "", year: new Date().getFullYear().toString(), period: "FY", confidence: "exact" });
    setShow(false);
  };

  if (!show) return (
    <button onClick={() => setShow(true)} className="text-xs text-blue-500 hover:text-blue-700 flex items-center gap-1">
      + Metrik hinzufügen
    </button>
  );

  return (
    <div className="bg-white border border-blue-200 rounded-xl p-3 space-y-2">
      <p className="text-xs font-semibold text-gray-600">Neue Metrik</p>
      <div className="grid grid-cols-2 gap-2">
        <input className="col-span-2 text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="metric_type (z.B. co2_scope1)" value={f.metric_type} onChange={e => setF(d => ({ ...d, metric_type: e.target.value }))} />
        <input className="text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="Wert (z.B. 12500.0)" value={f.value} onChange={e => setF(d => ({ ...d, value: e.target.value }))} />
        <input className="text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="Einheit (z.B. tCO2e)" value={f.unit} onChange={e => setF(d => ({ ...d, unit: e.target.value }))} />
        <input className="text-xs border border-gray-200 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-300" placeholder="Jahr" value={f.year} onChange={e => setF(d => ({ ...d, year: e.target.value }))} />
        <select className="text-xs border border-gray-200 rounded px-2 py-1" value={f.confidence} onChange={e => setF(d => ({ ...d, confidence: e.target.value }))}>
          <option value="exact">exact</option>
          <option value="estimated">estimated</option>
          <option value="calculated">calculated</option>
        </select>
      </div>
      <div className="flex gap-2">
        <button onClick={submit} disabled={saving || !f.metric_type || !f.value} className="text-xs bg-blue-600 text-white rounded px-3 py-1 hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1">
          <Save size={11} />{saving ? "Speichern…" : "Speichern"}
        </button>
        <button onClick={() => setShow(false)} className="text-xs text-gray-400 hover:text-gray-600">Abbrechen</button>
      </div>
    </div>
  );
}

// ── MetricsTable (editable) ───────────────────────────────────────────────────

function MetricsTable({ metrics, onUpdate, onDelete }: {
  metrics: ReviewMetric[];
  onUpdate: (id: string, payload: { value?: number; unit?: string; year?: number; confidence?: string }) => void;
  onDelete: (id: string) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<{ value: string; unit: string; year: string; confidence: string }>({ value: "", unit: "", year: "", confidence: "" });

  const startEdit = (m: ReviewMetric) => {
    setEditingId(m.id);
    setEditDraft({ value: String(m.value), unit: m.unit, year: String(m.year), confidence: m.confidence });
  };

  const commitEdit = (id: string) => {
    onUpdate(id, {
      value: parseFloat(editDraft.value) || undefined,
      unit: editDraft.unit || undefined,
      year: parseInt(editDraft.year) || undefined,
      confidence: editDraft.confidence || undefined,
    });
    setEditingId(null);
  };

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
            <th className="w-12" />
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, i) => {
            const editing = editingId === m.id;
            return (
              <tr key={m.id} className={`group ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                <td className="px-3 py-2 text-gray-600">{m.metric_type}</td>
                <td className="px-3 py-2 text-right">
                  {editing ? (
                    <input autoFocus className="text-right bg-blue-50 border border-blue-300 rounded px-1 py-0.5 w-24 outline-none" value={editDraft.value} onChange={e => setEditDraft(d => ({ ...d, value: e.target.value }))} />
                  ) : (
                    <span className="font-mono font-semibold text-gray-800 cursor-pointer hover:bg-blue-50 rounded px-1" onClick={() => startEdit(m)}>{m.value.toLocaleString("de-DE")}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {editing ? (
                    <input className="text-right bg-blue-50 border border-blue-300 rounded px-1 py-0.5 w-16 outline-none" value={editDraft.unit} onChange={e => setEditDraft(d => ({ ...d, unit: e.target.value }))} />
                  ) : (
                    <span className="text-gray-500">{m.unit}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  {editing ? (
                    <input className="text-right bg-blue-50 border border-blue-300 rounded px-1 py-0.5 w-16 outline-none" value={editDraft.year} onChange={e => setEditDraft(d => ({ ...d, year: e.target.value }))} />
                  ) : (
                    <span className="text-gray-600">{m.year}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-gray-500">{m.period}</td>
                <td className="px-3 py-2 text-center">
                  {editing ? (
                    <select className="text-xs bg-blue-50 border border-blue-300 rounded px-1 py-0.5" value={editDraft.confidence} onChange={e => setEditDraft(d => ({ ...d, confidence: e.target.value }))}>
                      <option value="exact">exact</option>
                      <option value="estimated">estimated</option>
                      <option value="calculated">calculated</option>
                    </select>
                  ) : (
                    <span className={`rounded px-1.5 py-0.5 ${m.confidence === "exact" ? "bg-green-50 text-green-700" : m.confidence === "estimated" ? "bg-yellow-50 text-yellow-700" : "bg-gray-100 text-gray-500"}`}>
                      {m.confidence}
                    </span>
                  )}
                </td>
                <td className="px-1">
                  <div className="flex gap-0.5 opacity-0 group-hover:opacity-100">
                    {editing ? (
                      <>
                        <button onClick={() => commitEdit(m.id)} className="p-0.5 rounded text-green-500 hover:text-green-700"><Save size={11} /></button>
                        <button onClick={() => setEditingId(null)} className="p-0.5 rounded text-gray-400 hover:text-gray-600"><X size={11} /></button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => startEdit(m)} className="p-0.5 rounded text-gray-400 hover:text-blue-500"><Edit3 size={11} /></button>
                        <button onClick={() => onDelete(m.id)} className="p-0.5 rounded text-gray-300 hover:text-red-400"><Trash2 size={11} /></button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
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
  const chunksRef = useRef<ReviewChunk[]>([]);
  const [searchQuery, setSearchQuery] = useState<{ text: string; id: number } | undefined>(undefined);
  const [highlightTerms, setHighlightTerms] = useState<string[]>([]);
  const [searchStatus, setSearchStatus] = useState<"idle" | "searching" | "found" | "not-found">("idle");
  const [searchFoundPage, setSearchFoundPage] = useState<number | null>(null);
  const searchIdRef = useRef(0);
  const [markdownMode, setMarkdownMode] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const blobUrlRef = useRef<string | null>(null);
  const [sandboxQuery, setSandboxQuery] = useState("");
  const [sandboxResult, setSandboxResult] = useState<SandboxResult | null>(null);
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<ReviewData>({
    queryKey: ["doc-review", fileId],
    queryFn: () => getFileReview(fileId),
  });

  // Keep ref always in sync — avoids stale closure in findKpiInPdf
  useEffect(() => { chunksRef.current = data?.chunks ?? []; }, [data?.chunks]);

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

  const reanalyzeMut = useMutation({
    mutationFn: () => reanalyzeFile(fileId),
    onSuccess: invalidate,
  });

  const excludeChunkMut = useMutation({
    mutationFn: (chunkId: string) => excludeChunk(chunkId),
    onSuccess: invalidate,
  });

  const copilotVisibilityMut = useMutation({
    mutationFn: () => toggleCopilotVisibility(fileId),
    onSuccess: invalidate,
  });

  const approveMut = useMutation({
    mutationFn: (notes?: string) => approveDocument(fileId, notes),
    onSuccess: invalidate,
  });

  const unapproveMut = useMutation({
    mutationFn: () => unapproveDocument(fileId),
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

  const splitChunkMut = useMutation({
    mutationFn: ({ chunkId, splitAt }: { chunkId: string; splitAt: number }) => splitChunk(chunkId, splitAt),
    onSuccess: invalidate,
  });

  const mergeChunkMut = useMutation({
    mutationFn: ({ chunkId, otherChunkId }: { chunkId: string; otherChunkId: string }) =>
      mergeChunks(chunkId, otherChunkId),
    onSuccess: invalidate,
  });

  const updateKpisMut = useMutation({
    mutationFn: (kpis: Record<string, unknown>) => updateKpis(fileId, kpis),
    onSuccess: invalidate,
  });

  const updateMetricMut = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { value?: number; unit?: string; year?: number; confidence?: string } }) => updateMetric(id, payload),
    onSuccess: invalidate,
  });

  const deleteMetricMut = useMutation({
    mutationFn: (id: string) => deleteMetric(id),
    onSuccess: invalidate,
  });

  const addMetricMut = useMutation({
    mutationFn: (payload: { metric_type: string; value: number; unit: string; year: number; period?: string; confidence?: string }) => addMetric(fileId, payload),
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
    setActiveStep("chunking");
  }, []);

  const findTextInPdf = useCallback((text: string) => {
    searchIdRef.current += 1;
    setSearchQuery({ text: text.slice(0, 200), id: searchIdRef.current });
    setSearchStatus("searching");
  }, []);

  // KPI → direct source_page navigation if available, else chunk search
  const findKpiInPdf = useCallback((key: string, value: string, sourcePage?: number | null) => {
    // Fastest path: KPI has a stored source_page from the LLM
    if (sourcePage) {
      setTargetPage(undefined);
      setTimeout(() => setTargetPage(sourcePage), 0);
      setSearchStatus("found");
      setSearchFoundPage(sourcePage);
      const kws = `${value} ${key}`.toLowerCase().replace(/[^a-z0-9äöüß\s]/g, " ").split(/\s+/).filter(w => w.length >= 2).slice(0, 6);
      setHighlightTerms(kws);
      return;
    }

    const chunks = chunksRef.current;

    const numPart = value.replace(/[^\d.,\s]/g, " ").trim();
    const allWords = `${numPart} ${key}`
      .toLowerCase()
      .replace(/[^a-z0-9äöüß\s]/g, " ")
      .split(/\s+/)
      .filter(w => w.length >= 2);
    const numWords = allWords.filter(w => /\d/.test(w));

    let bestChunk: ReviewChunk | null = null;
    let bestScore = 0;
    let bestMatchPos = 0;

    if (chunks.length > 0 && allWords.length > 0) {
      for (const chunk of chunks) {
        const ct = chunk.content.toLowerCase().replace(/[^a-z0-9äöüß\s]/g, " ");
        const hits = allWords.filter(w => ct.includes(w)).length;
        const score = hits / allWords.length;
        if (score > bestScore) {
          bestScore = score;
          bestChunk = chunk;
          const pivot = numWords.find(w => ct.includes(w));
          bestMatchPos = pivot ? ct.indexOf(pivot) : Math.floor(chunk.content.length / 2);
        }
      }
    }

    // If the chunk has a stored page number, navigate directly — no fuzzy PDF text search
    if (bestChunk?.page_number) {
      // Reset first so same page number re-triggers the useEffect in PdfViewer
      setTargetPage(undefined);
      setTimeout(() => setTargetPage(bestChunk!.page_number!), 0);
      setSearchStatus("found");
      setSearchFoundPage(bestChunk.page_number);
      // Set highlight terms directly — do NOT set searchQuery to avoid triggering fuzzy navigation
      const kws = `${numPart} ${key}`
        .toLowerCase()
        .replace(/[^a-z0-9äöüß\s]/g, " ")
        .split(/\s+/)
        .filter(w => w.length >= 2)
        .slice(0, 6);
      setHighlightTerms(kws);
      return;
    }

    // Fallback: fuzzy PDF text search (page_number not stored)
    setHighlightTerms([]);
    let searchText = `${numPart} ${key}`;
    if (bestChunk) {
      const start = Math.max(0, bestMatchPos - 80);
      const end = Math.min(bestChunk.content.length, start + 300);
      searchText = bestChunk.content.slice(start, end);
    }
    searchIdRef.current += 1;
    setSearchQuery({ text: searchText, id: searchIdRef.current });
    setSearchStatus("searching");
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
        const totalPages = data.pages ?? 0;
        // Page coverage: which pages have at least one chunk with page_number
        const coveredPages = new Set(data.chunks.map(c => c.page_number).filter((p): p is number => p != null));
        const coveragePct = totalPages > 0 ? Math.round((coveredPages.size / totalPages) * 100) : null;
        const chunksWithPage = data.chunks.filter(c => c.page_number != null).length;
        const chunkCoveragePct = data.chunks.length > 0 ? Math.round((chunksWithPage / data.chunks.length) * 100) : null;
        return (
          <div className="space-y-3">
            {/* Quality indicators */}
            {totalPages > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: "Seitenabdeckung", value: coveragePct != null ? `${coveragePct}%` : "–", sub: `${coveredPages.size} / ${totalPages} Seiten`, ok: coveragePct != null && coveragePct >= 80 },
                  { label: "Chunk-Tracking", value: chunkCoveragePct != null ? `${chunkCoveragePct}%` : "–", sub: `${chunksWithPage} / ${data.chunks.length} Chunks`, ok: chunkCoveragePct != null && chunkCoveragePct >= 70 },
                  { label: "Wörter/Seite", value: totalPages > 0 && words > 0 ? Math.round(words / totalPages).toLocaleString() : "–", sub: "Ø Dichte", ok: totalPages > 0 && words / totalPages >= 100 },
                ].map(({ label, value, sub, ok }) => (
                  <div key={label} className={`rounded-lg border p-3 ${ok ? "border-green-200 bg-green-50" : "border-orange-200 bg-orange-50"}`}>
                    <div className={`text-lg font-bold ${ok ? "text-green-700" : "text-orange-700"}`}>{value}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{label}</div>
                    <div className="text-[10px] text-gray-400">{sub}</div>
                  </div>
                ))}
              </div>
            )}
            {coveragePct != null && coveragePct < 80 && (
              <div className="flex items-start gap-2 text-xs text-orange-700 bg-orange-50 rounded-lg px-3 py-2 border border-orange-200">
                <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                <span>Nur {coveragePct}% der Seiten haben Chunks mit Seitenreferenz — Navigation via KPI-Seitenangaben kann unvollständig sein. Dokument neu indexieren.</span>
              </div>
            )}
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
      case "classifying": {
        const storedConf = data.classification_confidence;
        const storedAlts = data.classification_alternatives ?? [];
        const reclassResult = reclassifyMut.data as { changed?: boolean; old_doc_type?: string; new_doc_type?: string; confidence?: number; alternatives?: { doc_type: string; confidence: number }[] } | undefined;
        const showConf = reclassResult?.confidence ?? storedConf;
        const showAlts = reclassResult?.alternatives ?? storedAlts;
        return (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
              <EditableField label="Dokumenttyp" value={data.doc_type} onSave={v => classifyMut.mutate({ doc_type: v })} />
              <EditableField label="Unternehmen" value={data.company_name ?? ""} onSave={v => classifyMut.mutate({ company_name: v })} />
              <EditableField label="Berichtsjahr" value={String(data.report_year ?? "")} onSave={v => classifyMut.mutate({ report_year: parseInt(v) || undefined })} />
              <EditableField label="Sprache" value={data.language ?? ""} readOnly />
              <EditableField label="Titel" value={data.title ?? ""} readOnly />
            </div>
            {/* Confidence + alternatives */}
            {(showConf != null || showAlts.length > 0) && (
              <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
                {showConf != null && (
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-500">Klassifizierungs-Konfidenz</span>
                      <span className={`text-xs font-semibold ${showConf >= 0.8 ? "text-green-700" : showConf >= 0.5 ? "text-yellow-700" : "text-red-700"}`}>{Math.round(showConf * 100)} %</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all ${showConf >= 0.8 ? "bg-green-500" : showConf >= 0.5 ? "bg-yellow-500" : "bg-red-500"}`}
                        style={{ width: `${Math.round(showConf * 100)}%` }}
                      />
                    </div>
                  </div>
                )}
                {showAlts.length > 0 && (
                  <div>
                    <p className="text-xs text-gray-400 mb-2">Alternativen</p>
                    <div className="space-y-1.5">
                      {showAlts.map((alt: { doc_type: string; confidence: number }) => (
                        <div key={alt.doc_type} className="flex items-center gap-2">
                          <span className="text-xs text-gray-600 w-40 shrink-0">{alt.doc_type}</span>
                          <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                            <div className="h-1.5 rounded-full bg-gray-400" style={{ width: `${Math.round(alt.confidence * 100)}%` }} />
                          </div>
                          <span className="text-xs text-gray-400 w-8 text-right">{Math.round(alt.confidence * 100)}%</span>
                          <button
                            onClick={() => classifyMut.mutate({ doc_type: alt.doc_type })}
                            className="text-xs text-blue-500 hover:text-blue-700 shrink-0"
                            title="Diese Klassifizierung übernehmen"
                          >übernehmen</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            <button
              onClick={() => reclassifyMut.mutate()}
              disabled={reclassifyMut.isPending}
              className="flex items-center gap-2 text-sm border border-blue-200 text-blue-600 rounded-lg px-4 py-2 hover:bg-blue-50 disabled:opacity-50"
            >
              <RefreshCw size={14} className={reclassifyMut.isPending ? "animate-spin" : ""} />
              {reclassifyMut.isPending ? "Wird klassifiziert…" : "Neu klassifizieren (LLM)"}
            </button>
            {reclassResult && (
              <div className={`text-xs rounded-lg p-3 ${reclassResult.changed ? "bg-blue-50 text-blue-700" : "bg-gray-50 text-gray-500"}`}>
                {reclassResult.changed
                  ? `Geändert: ${reclassResult.old_doc_type} → ${reclassResult.new_doc_type}`
                  : "Keine Änderung — Klassifizierung bestätigt"}
              </div>
            )}
          </div>
        );
      }

      // ── Analyse ───────────────────────────────────────────────────────────────
      case "analyzing":
        return (
          <div className="space-y-4 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
            {/* Analyse wiederholen — always accessible */}
            <div className="flex justify-end">
              <button
                onClick={() => reanalyzeMut.mutate()}
                disabled={reanalyzeMut.isPending}
                className="flex items-center gap-1.5 text-xs border border-blue-200 text-blue-600 rounded-lg px-3 py-1.5 hover:bg-blue-50 disabled:opacity-50"
              >
                <RefreshCw size={12} className={reanalyzeMut.isPending ? "animate-spin" : ""} />
                {reanalyzeMut.isPending ? "Analyse läuft…" : "Analyse wiederholen"}
              </button>
            </div>
            {data.summary && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Zusammenfassung</h4>
                <p className="text-sm text-gray-700 leading-relaxed bg-white rounded-xl border border-gray-200 p-4">{data.summary}</p>
              </div>
            )}
            {data.extracted_kpis && Object.keys(data.extracted_kpis).length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Extrahierte KPIs ({Object.keys(data.extracted_kpis).length})
                  </h4>
                  {updateKpisMut.isSuccess && (
                    <span className="text-xs text-green-600 flex items-center gap-1"><CheckCircle2 size={11} /> Gespeichert</span>
                  )}
                </div>
                {/* PDF navigation feedback — shown in right panel so user knows to look left */}
                {searchStatus === "searching" && (
                  <div className="flex items-center gap-2 text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-2 mb-2">
                    <div className="w-3 h-3 border border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
                    Suche KPI im PDF…
                  </div>
                )}
                {searchStatus === "found" && searchFoundPage !== null && (
                  <div className="flex items-center gap-2 text-xs text-green-700 bg-green-50 rounded-lg px-3 py-2 mb-2">
                    <CheckCircle2 size={12} className="shrink-0" />
                    PDF springt zu <strong>Seite {searchFoundPage}</strong> — schaue links
                    <button onClick={() => setSearchStatus("idle")} className="ml-auto text-green-400 hover:text-green-600"><X size={10} /></button>
                  </div>
                )}
                {searchStatus === "not-found" && (
                  <div className="flex items-center gap-2 text-xs text-orange-700 bg-orange-50 rounded-lg px-3 py-2 mb-2">
                    <AlertTriangle size={12} className="shrink-0" />
                    KPI-Stelle nicht gefunden — PDF-Text weicht vom extrahierten Text ab
                    <button onClick={() => setSearchStatus("idle")} className="ml-auto text-orange-400 hover:text-orange-600"><X size={10} /></button>
                  </div>
                )}
                <EditableKpiTable
                  kpis={data.extracted_kpis as Record<string, unknown>}
                  onSave={kpis => updateKpisMut.mutate(kpis)}
                  saving={updateKpisMut.isPending}
                  onFindInPdf={findKpiInPdf}
                />
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
                <Activity size={32} className="mx-auto mb-3 opacity-40" />
                <p className="text-sm mb-1">Keine Analyse-Ergebnisse</p>
                <p className="text-xs text-gray-400 mb-4">Die KPI-Extraktion ist fehlgeschlagen oder wurde übersprungen.</p>
                <button
                  onClick={() => reanalyzeMut.mutate()}
                  disabled={reanalyzeMut.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
                >
                  {reanalyzeMut.isPending ? (
                    <><div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" /> Analyse läuft…</>
                  ) : (
                    <><Activity size={14} /> Analyse wiederholen</>
                  )}
                </button>
                {reanalyzeMut.isError && (
                  <p className="text-xs text-red-500 mt-2">Fehler beim Starten der Analyse</p>
                )}
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
                    isLast={i === data.chunks.length - 1}
                    onDelete={() => deleteChunkMut.mutate(chunk.id)}
                    onEdit={content => editChunkMut.mutate({ chunkId: chunk.id, content })}
                    onFindInPdf={() => findChunkInPdf(chunk)}
                    onSplit={splitAt => splitChunkMut.mutate({ chunkId: chunk.id, splitAt })}
                    onMergeWith={() => {
                      const next = data.chunks[i + 1];
                      if (next) mergeChunkMut.mutate({ chunkId: chunk.id, otherChunkId: next.id });
                    }}
                    onExclude={() => excludeChunkMut.mutate(chunk.id)}
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
      case "metrics": {
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
                <MetricsTable
                  metrics={data.metrics}
                  onUpdate={(id, payload) => updateMetricMut.mutate({ id, payload })}
                  onDelete={(id) => deleteMetricMut.mutate(id)}
                />
              </div>
            )}
            {/* Add metric form */}
            <AddMetricForm onAdd={(payload) => addMetricMut.mutate(payload)} saving={addMetricMut.isPending} />
            {data.signals.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Signale ({data.signals.length})</h4>
                <SignalsTable signals={data.signals} />
              </div>
            )}
            {data.metrics.length === 0 && data.signals.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <BarChart3 size={32} className="mx-auto mb-2 opacity-40" />
                <p className="text-sm">Keine Metriken oder Signale extrahiert</p>
              </div>
            )}
          </div>
        );
      }
      case "sandbox": {
        const simColor = (s: number) => s >= 0.7 ? "bg-green-500" : s >= 0.45 ? "bg-yellow-500" : "bg-red-400";
        const simLabel = (s: number) => s >= 0.7 ? "✅" : s >= 0.45 ? "⚠️" : "❌";
        return (
          <div className="space-y-4">
            <p className="text-xs text-gray-400">Stelle eine Testfrage direkt an dieses Dokument — ohne Freigabe, alle Chunks sichtbar.</p>
            <div className="flex gap-2">
              <input
                className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-blue-200"
                placeholder="z.B. Was sind die CO₂-Ziele von BMW?"
                value={sandboxQuery}
                onChange={e => setSandboxQuery(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && sandboxQuery.trim() && !sandboxLoading) {
                    setSandboxLoading(true);
                    setSandboxResult(null);
                    runCopilotSandbox(fileId, sandboxQuery.trim())
                      .then(r => setSandboxResult(r))
                      .finally(() => setSandboxLoading(false));
                  }
                }}
              />
              <button
                disabled={!sandboxQuery.trim() || sandboxLoading}
                onClick={() => {
                  setSandboxLoading(true);
                  setSandboxResult(null);
                  runCopilotSandbox(fileId, sandboxQuery.trim())
                    .then(r => setSandboxResult(r))
                    .finally(() => setSandboxLoading(false));
                }}
                className="flex items-center gap-1.5 text-sm bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {sandboxLoading ? <><div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" /> Läuft…</> : <><Search size={13} /> Fragen</>}
              </button>
            </div>

            {sandboxResult && (
              <div className="space-y-3">
                {/* Answer */}
                {sandboxResult.answer && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                    <p className="text-xs font-semibold text-blue-600 mb-2 flex items-center gap-1"><BookOpen size={12} /> Copilot-Antwort</p>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{sandboxResult.answer}</p>
                  </div>
                )}

                {/* Source chunks */}
                <div>
                  <div className="mb-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Quell-Chunks ({sandboxResult.chunks.length})</p>
                    <p className="text-xs text-gray-400 mt-0.5">% = Relevanz zur Frage · 🟢 ≥70% sehr relevant · 🟡 45–69% teilweise · 🔴 &lt;45% kaum relevant</p>
                  </div>
                  <div className="space-y-2">
                    {sandboxResult.chunks.map((c, i) => (
                      <div
                        key={c.chunk_id}
                        title={c.page_number ? `Zur Seite ${c.page_number} springen` : "Inhalt anzeigen"}
                        className={`rounded-xl border p-3 cursor-pointer hover:border-blue-300 transition-colors ${c.excluded_from_index ? "border-orange-200 bg-orange-50" : "border-gray-200 bg-white"}`}
                        onClick={() => {
                          if (c.page_number) {
                            setTargetPage(undefined);
                            setTimeout(() => setTargetPage(c.page_number!), 0);
                          } else {
                            setExpandedChunk(expandedChunk === c.chunk_id ? null : c.chunk_id);
                          }
                        }}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-mono text-gray-400">#{i + 1}</span>
                          <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full ${simColor(c.similarity)}`} style={{ width: `${Math.round(c.similarity * 100)}%` }} />
                          </div>
                          <span className="text-xs font-semibold text-gray-600">{Math.round(c.similarity * 100)}%</span>
                          <span className="text-xs">{simLabel(c.similarity)}</span>
                          {c.page_number && <span className="text-xs bg-purple-50 text-purple-600 border border-purple-200 rounded px-1.5 py-0.5">S.{c.page_number}</span>}
                          {c.excluded_from_index && <span className="text-xs bg-orange-100 text-orange-600 rounded px-1.5 py-0.5">ausgeschlossen</span>}
                        </div>
                        <p className={`text-xs text-gray-600 ${expandedChunk === c.chunk_id ? "whitespace-pre-wrap" : "line-clamp-3"}`}>{c.content}</p>
                        {!c.page_number && expandedChunk !== c.chunk_id && (
                          <p className="text-xs text-gray-400 mt-1 italic">↓ Klicken zum Aufklappen (keine Seitennummer)</p>
                        )}
                      </div>
                    ))}
                    {sandboxResult.chunks.length === 0 && (
                      <div className="text-center py-6 text-gray-400">
                        <Search size={24} className="mx-auto mb-2 opacity-40" />
                        <p className="text-sm">Keine passenden Chunks gefunden — Similarity zu niedrig</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      }
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
          onClick={() => copilotVisibilityMut.mutate()}
          disabled={copilotVisibilityMut.isPending}
          title={data.copilot_hidden ? "Dokument für Copilot sichtbar machen" : "Dokument aus Copilot ausblenden"}
          className={`flex items-center gap-1.5 text-sm rounded-lg px-3 py-2 border font-medium transition-colors ${data.copilot_hidden ? "border-orange-300 bg-orange-50 text-orange-700 hover:bg-orange-100" : "border-gray-200 text-gray-500 hover:bg-gray-50"}`}
        >
          {data.copilot_hidden ? <EyeOff size={15} /> : <Eye size={15} />}
          {data.copilot_hidden ? "Copilot: aus" : "Copilot: an"}
        </button>
        {data.review_status === "approved" ? (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-sm rounded-lg px-4 py-2 font-medium bg-green-100 text-green-700">
              <CheckCircle2 size={15} />
              Freigegeben
            </span>
            <button
              onClick={() => unapproveMut.mutate()}
              disabled={unapproveMut.isPending}
              className="flex items-center gap-1.5 text-xs rounded-lg px-3 py-2 border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
              title="Freigabe widerrufen"
            >
              <XCircle size={13} />
              Widerrufen
            </button>
          </div>
        ) : (
          <button
            onClick={() => approveMut.mutate(undefined)}
            disabled={approveMut.isPending}
            className="flex items-center gap-1.5 text-sm rounded-lg px-4 py-2 font-medium bg-green-600 text-white hover:bg-green-700 transition-colors"
          >
            <CheckCircle2 size={15} />
            Freigeben
          </button>
        )}
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
                {searchStatus === "found" && <><span>✓</span> Seite {searchFoundPage} ← PDF springt hierhin</>}
                {searchStatus === "not-found" && <><span>✗</span> Nicht gefunden — Docling-Text weicht von PDF-Rohtext ab</>}
                <button onClick={() => setSearchStatus("idle")} className="ml-auto opacity-60 hover:opacity-100">✕</button>
              </div>
            )}
            <div className="flex-1 overflow-hidden">
              <DynamicPdfViewer
                blobUrl={pdfBlobUrl}
                loading={pdfLoading}
                targetPage={targetPage}
                searchQuery={searchQuery}
                highlightTerms={highlightTerms}
                onPageChange={(page, total) => { void page; void total; }}
                onSearchResult={(page) => {
                  setSearchStatus(page !== null ? "found" : "not-found");
                  setSearchFoundPage(page);
                }}
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
