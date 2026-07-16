"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  FileText,
  RefreshCw,
  Search,
  XCircle,
} from "lucide-react";
import {
  listFiles,
  toggleCopilotVisibility,
  approveDocument,
  unapproveDocument,
  type DocumentFile,
} from "@/lib/api/documents";

// ── Quality Score ──────────────────────────────────────────────────────────────

function computeListQuality(f: DocumentFile): number {
  let score = 0;
  if (f.status === "done") score += 20;
  if (f.company_name) score += 15;
  if (f.report_year) score += 15;
  if (f.doc_type && f.doc_type !== "other") score += 10;
  if (f.summary) score += 10;
  if ((f.chunks_count ?? 0) > 0) score += 15;
  if ((f.chunks_count ?? 0) > 10) score += 5;
  const kpiCount = f.extracted_kpis ? Object.keys(f.extracted_kpis).length : 0;
  if (kpiCount > 0) score += 5;
  if (kpiCount > 3) score += 5;
  return Math.min(100, score);
}

function QBadge({ score }: { score: number }) {
  const cls = score >= 80 ? "bg-green-100 text-green-800 border-green-200"
    : score >= 50 ? "bg-yellow-100 text-yellow-800 border-yellow-200"
    : "bg-red-100 text-red-800 border-red-200";
  return <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${cls}`}>Q {score}</span>;
}

function reviewBadge(s: string) {
  if (s === "approved") return "bg-green-100 text-green-700 border-green-200";
  if (s === "in_review") return "bg-yellow-100 text-yellow-700 border-yellow-200";
  return "bg-gray-100 text-gray-500 border-gray-200";
}

function statusDot(s: string) {
  if (["done", "ok", "completed"].includes(s)) return "bg-green-500";
  if (["parsing", "analyzing", "indexing", "processing"].includes(s)) return "bg-blue-500 animate-pulse";
  if (["failed", "error"].includes(s)) return "bg-red-500";
  return "bg-gray-300";
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReviewQueuePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "needs_review" | "approved" | "copilot_off">("needs_review");
  const [sortAsc, setSortAsc] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkPending, setBulkPending] = useState(false);

  const { data: files, isLoading } = useQuery<DocumentFile[]>({
    queryKey: ["doc-files-all"],
    queryFn: () => listFiles(),
  });

  const copilotMut = useMutation({
    mutationFn: (fileId: string) => toggleCopilotVisibility(fileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doc-files-all"] }),
  });

  const approveMut = useMutation({
    mutationFn: (fileId: string) => approveDocument(fileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doc-files-all"] }),
  });

  const unapproveMut = useMutation({
    mutationFn: (fileId: string) => unapproveDocument(fileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doc-files-all"] }),
  });

  const all = files ?? [];

  const filtered = useMemo(() => all
    .filter(f => {
      if (filter === "needs_review") return f.review_status !== "approved" && f.status === "done";
      if (filter === "approved") return f.review_status === "approved";
      if (filter === "copilot_off") return Boolean(f.copilot_hidden);
      return true;
    })
    .filter(f => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (f.company_name ?? "").toLowerCase().includes(q)
        || (f.title ?? "").toLowerCase().includes(q)
        || f.doc_type.toLowerCase().includes(q);
    })
    .map(f => ({ ...f, _q: computeListQuality(f) }))
    .sort((a, b) => sortAsc ? a._q - b._q : b._q - a._q),
    [all, filter, search, sortAsc]
  );

  const needsReview = all.filter(f => f.review_status !== "approved" && f.status === "done").length;
  const approved = all.filter(f => f.review_status === "approved").length;
  const copilotOff = all.filter(f => Boolean(f.copilot_hidden)).length;
  const avgQ = all.length > 0 ? Math.round(all.reduce((sum, f) => sum + computeListQuality(f), 0) / all.length) : 0;

  const allFilteredIds = filtered.map(f => f.id);
  const allSelected = allFilteredIds.length > 0 && allFilteredIds.every(id => selected.has(id));
  const someSelected = selected.size > 0;

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(allFilteredIds));
    }
  };

  const bulkApprove = async () => {
    setBulkPending(true);
    const ids = [...selected].filter(id => {
      const f = all.find(x => x.id === id);
      return f && f.review_status !== "approved";
    });
    await Promise.all(ids.map(id => approveDocument(id)));
    await qc.invalidateQueries({ queryKey: ["doc-files-all"] });
    setSelected(new Set());
    setBulkPending(false);
  };

  const bulkUnapprove = async () => {
    setBulkPending(true);
    const ids = [...selected].filter(id => {
      const f = all.find(x => x.id === id);
      return f && f.review_status === "approved";
    });
    await Promise.all(ids.map(id => unapproveDocument(id)));
    await qc.invalidateQueries({ queryKey: ["doc-files-all"] });
    setSelected(new Set());
    setBulkPending(false);
  };

  const selectedCanApprove = [...selected].filter(id => all.find(x => x.id === id)?.review_status !== "approved").length;
  const selectedCanUnapprove = [...selected].filter(id => all.find(x => x.id === id)?.review_status === "approved").length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center gap-4">
        <button onClick={() => router.push("/documents")} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
          <ArrowLeft size={18} />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Review Queue</h1>
          <p className="text-xs text-gray-400 mt-0.5">Dokumente prüfen und freigeben — niedrigster Q-Score zuerst</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => qc.invalidateQueries({ queryKey: ["doc-files-all"] })}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
            title="Aktualisieren"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </header>

      {/* Stats */}
      <div className="px-6 py-4 grid grid-cols-4 gap-3">
        {[
          { label: "Gesamt", value: all.length, icon: FileText, color: "text-gray-700", f: "all" as const },
          { label: "Zu prüfen", value: needsReview, icon: AlertTriangle, color: "text-orange-600", f: "needs_review" as const },
          { label: "Freigegeben", value: approved, icon: CheckCircle2, color: "text-green-600", f: "approved" as const },
          { label: "Copilot aus", value: copilotOff, icon: EyeOff, color: "text-gray-500", f: "copilot_off" as const },
        ].map(({ label, value, icon: Icon, color, f }) => (
          <button
            key={label}
            onClick={() => setFilter(f)}
            className={`bg-white rounded-xl border p-4 flex items-center gap-3 text-left transition-colors ${filter === f ? "border-blue-300 ring-1 ring-blue-200" : "border-gray-200 hover:border-gray-300"}`}
          >
            <Icon size={20} className={color} />
            <div>
              <div className="text-2xl font-bold text-gray-900">{value}</div>
              <div className="text-xs text-gray-400">{label}</div>
            </div>
          </button>
        ))}
      </div>

      {/* Avg quality bar */}
      {all.length > 0 && (
        <div className="px-6 pb-2">
          <div className="bg-white rounded-xl border border-gray-200 px-4 py-3 flex items-center gap-4">
            <BarChart3 size={16} className="text-gray-400 shrink-0" />
            <span className="text-xs text-gray-500 shrink-0">Ø Qualitätsscore</span>
            <div className="flex-1 bg-gray-100 rounded-full h-2">
              <div className={`h-2 rounded-full transition-all ${avgQ >= 80 ? "bg-green-500" : avgQ >= 50 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${avgQ}%` }} />
            </div>
            <span className={`text-sm font-bold ${avgQ >= 80 ? "text-green-700" : avgQ >= 50 ? "text-yellow-700" : "text-red-700"}`}>{avgQ}</span>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {someSelected && (
        <div className="px-6 pb-2">
          <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2.5 flex items-center gap-3">
            <span className="text-sm font-medium text-blue-800">{selected.size} ausgewählt</span>
            <div className="flex items-center gap-2 ml-auto">
              {selectedCanApprove > 0 && (
                <button
                  onClick={bulkApprove}
                  disabled={bulkPending}
                  className="flex items-center gap-1.5 text-sm bg-green-600 text-white rounded-lg px-3 py-1.5 hover:bg-green-700 disabled:opacity-50 font-medium"
                >
                  <CheckCircle2 size={14} />
                  {bulkPending ? "Wird freigegeben…" : `${selectedCanApprove} freigeben`}
                </button>
              )}
              {selectedCanUnapprove > 0 && (
                <button
                  onClick={bulkUnapprove}
                  disabled={bulkPending}
                  className="flex items-center gap-1.5 text-sm border border-red-200 text-red-600 rounded-lg px-3 py-1.5 hover:bg-red-50 disabled:opacity-50"
                >
                  <XCircle size={14} />
                  {selectedCanUnapprove} widerrufen
                </button>
              )}
              <button
                onClick={() => setSelected(new Set())}
                className="text-xs text-blue-500 hover:text-blue-700 px-2"
              >
                Auswahl aufheben
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters + search */}
      <div className="px-6 pb-3 flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-1">
          {(["all", "needs_review", "approved", "copilot_off"] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`text-xs rounded px-3 py-1 transition-colors ${filter === f ? "bg-blue-600 text-white" : "text-gray-500 hover:bg-gray-50"}`}
            >
              {f === "all" ? "Alle" : f === "needs_review" ? "Zu prüfen" : f === "approved" ? "Freigegeben" : "Copilot aus"}
            </button>
          ))}
        </div>
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            className="pl-7 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-200 bg-white"
            placeholder="Unternehmen, Titel, Typ…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button
          onClick={() => setSortAsc(a => !a)}
          className="text-xs border border-gray-200 bg-white rounded-lg px-3 py-1.5 hover:bg-gray-50 text-gray-500 flex items-center gap-1"
        >
          Q-Score {sortAsc ? "↑ aufsteigend" : "↓ absteigend"}
        </button>
      </div>

      {/* List */}
      <div className="px-6 pb-8 space-y-1">
        {/* Select-all header */}
        {filtered.length > 0 && (
          <div className="flex items-center gap-3 px-4 py-2 text-xs text-gray-400">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleSelectAll}
              className="w-3.5 h-3.5 rounded accent-blue-600 cursor-pointer"
            />
            <span>{filtered.length} Dokumente</span>
          </div>
        )}

        {isLoading && (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-3" />
            Lädt…
          </div>
        )}
        {!isLoading && filtered.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            <CheckCircle2 size={32} className="mx-auto mb-2 opacity-40 text-green-400" />
            <p className="text-sm font-medium">Alles erledigt</p>
            <p className="text-xs mt-1">Keine Dokumente in dieser Ansicht</p>
          </div>
        )}

        {filtered.map(f => {
          const isSelected = selected.has(f.id);
          const isApproved = f.review_status === "approved";
          const isDuplicate = Boolean(
            f.company_name && f.report_year &&
            all.some(other =>
              other.id !== f.id &&
              other.review_status === "approved" &&
              other.company_name === f.company_name &&
              other.report_year === f.report_year
            )
          );
          return (
            <div
              key={f.id}
              className={`bg-white rounded-xl border px-4 py-3 flex items-center gap-3 transition-colors ${isSelected ? "border-blue-300 bg-blue-50/30" : "border-gray-200 hover:border-gray-300"}`}
            >
              {/* Checkbox */}
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => toggleSelect(f.id)}
                className="w-3.5 h-3.5 rounded accent-blue-600 cursor-pointer shrink-0"
              />

              {/* Status dot */}
              <div className={`w-2 h-2 rounded-full shrink-0 ${statusDot(f.status)}`} />

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-gray-800 truncate">{f.title ?? f.doc_type}</span>
                  {f.company_name && <span className="text-xs text-gray-400 shrink-0">{f.company_name}</span>}
                  {f.report_year && <span className="text-xs text-gray-400 shrink-0">{f.report_year}</span>}
                  {isDuplicate && (
                    <span
                      className="inline-flex items-center gap-1 text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-full px-2 py-0.5 shrink-0"
                      title={`Ein bereits freigegebenes Dokument mit ${f.company_name} ${f.report_year} existiert bereits`}
                    >
                      <Copy size={10} />
                      Duplikat
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-xs text-gray-400 bg-gray-50 rounded px-1.5 py-0.5">{f.doc_type}</span>
                  {f.chunks_count != null && <span className="text-xs text-gray-400">{f.chunks_count} Chunks</span>}
                  {f.pages && <span className="text-xs text-gray-400">{f.pages} S.</span>}
                  <span className={`text-xs px-1.5 py-0.5 rounded-full border ${reviewBadge(f.review_status)}`}>{f.review_status}</span>
                </div>
              </div>

              {/* Quality + confidence */}
              <div className="flex items-center gap-2 shrink-0">
                <QBadge score={f._q} />
                {f.classification_confidence != null && (
                  <span className={`text-xs ${f.classification_confidence >= 0.8 ? "text-green-600" : f.classification_confidence >= 0.5 ? "text-yellow-600" : "text-red-500"}`}>
                    {Math.round(f.classification_confidence * 100)}% Konf.
                  </span>
                )}
              </div>

              {/* Copilot toggle */}
              <button
                onClick={() => copilotMut.mutate(f.id)}
                disabled={copilotMut.isPending}
                title={f.copilot_hidden ? "Für Copilot sichtbar machen" : "Aus Copilot ausblenden"}
                className={`p-2 rounded-lg transition-colors shrink-0 ${f.copilot_hidden ? "bg-orange-50 text-orange-600 hover:bg-orange-100" : "text-gray-300 hover:text-gray-500 hover:bg-gray-50"}`}
              >
                {f.copilot_hidden ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>

              {/* Inline approve / unapprove */}
              {isApproved ? (
                <button
                  onClick={() => unapproveMut.mutate(f.id)}
                  disabled={unapproveMut.isPending}
                  className="flex items-center gap-1.5 text-xs border border-red-200 text-red-600 rounded-lg px-2.5 py-1.5 hover:bg-red-50 shrink-0"
                  title="Freigabe widerrufen"
                >
                  <XCircle size={13} />
                  Widerrufen
                </button>
              ) : f.status === "done" ? (
                <button
                  onClick={() => approveMut.mutate(f.id)}
                  disabled={approveMut.isPending}
                  className="flex items-center gap-1.5 text-xs bg-green-600 text-white rounded-lg px-2.5 py-1.5 hover:bg-green-700 shrink-0 font-medium"
                >
                  <CheckCircle2 size={13} />
                  Freigeben
                </button>
              ) : (
                <span className="w-[82px] shrink-0" />
              )}

              {/* Review link */}
              <Link
                href={`/documents/review/${f.id}`}
                className="flex items-center gap-1 text-xs border border-gray-200 text-gray-500 rounded-lg px-2.5 py-1.5 hover:bg-gray-50 shrink-0"
              >
                Review →
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
