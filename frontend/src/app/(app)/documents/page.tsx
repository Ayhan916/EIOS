"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useLanguage, type TranslationKey } from "@/lib/i18n/context";
import {
  BookOpen,
  Building2,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  Eye,
  EyeOff,
  FileText,
  Globe,
  Loader2,
  Microscope,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  XCircle,
  AlertTriangle,
  BarChart3,
} from "lucide-react";
import {
  listSources,
  createSource,
  updateSource,
  deleteSource,
  triggerIngest,
  uploadDocument,
  classifyDocument,
  listFiles,
  getFile,
  deleteFile,
  ingestAll,
  deleteQueuedFiles,
  reclassifyAllFiles,
  processPending,
  cancelProcessing,
  processSingleFile,
  toggleCopilotVisibility,
  type DocumentSource,
  type DocumentFile,
  type DocumentSourceCreate,
} from "@/lib/api/documents";
import { getDocQuality, METRIC_LABELS, type DocQuality } from "@/lib/api/intelligence";
import { listSuppliers } from "@/lib/api/suppliers";
import type { SupplierResponse } from "@/types/api";

// ── Doc type helpers ──────────────────────────────────────────────────────────

const DOC_TYPES = [
  // Berichte
  { value: "annual_report",          label: "Geschäftsbericht (Annual Report)" },
  { value: "sustainability_report",  label: "Nachhaltigkeitsbericht / Sustainable Value Report" },
  { value: "esg_overview",           label: "ESG Übersicht / ESG Overview" },
  { value: "governance_report",      label: "Corporate Governance Bericht" },
  // Investor Relations
  { value: "investor_presentation",  label: "Investoren-Präsentation" },
  { value: "press_release",          label: "Pressemitteilung" },
  { value: "qa_document",            label: "Q&A (Media / Investor / Analyst)" },
  { value: "executive_statement",    label: "Vorstandsaussage / Rede / Speech" },
  { value: "key_metrics",            label: "Kennzahlen / Key Metrics" },
  // Regulatorisch / Compliance
  { value: "csrd_report",            label: "CSRD Bericht" },
  { value: "csddd_disclosure",       label: "CSDDD Disclosure" },
  { value: "cdp_questionnaire",      label: "CDP Fragebogen (Klima / Wasser)" },
  { value: "audit_report",           label: "Audit-Bericht" },
  { value: "sector_risk",            label: "Sektorrisiko-Report" },
] as const;

type DocTypeValue = typeof DOC_TYPES[number]["value"];

function docTypeLabelDirect(value: string): string {
  return DOC_TYPES.find((d) => d.value === value)?.label ?? value.replace(/_/g, " ");
}

const SCHEDULES = [
  { value: "manual", labelKey: "docLib.scheduleManual" },
  { value: "daily", labelKey: "docLib.scheduleDaily" },
  { value: "weekly", labelKey: "docLib.scheduleWeekly" },
  { value: "monthly", labelKey: "docLib.scheduleMonthly" },
] as const;

function docTypeLabel(docType: string): string {
  return docTypeLabelDirect(docType);
}

function scheduleLabel(schedule: string, t: (k: TranslationKey) => string): string {
  const found = SCHEDULES.find((s) => s.value === schedule);
  return found ? t(found.labelKey) : schedule;
}

function useNow(intervalMs = 10_000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function ElapsedTime({ since }: { since: string }) {
  const now = useNow(10_000);
  const mins = Math.floor((now - new Date(since).getTime()) / 60_000);
  if (mins < 1) return <span className="ml-1 opacity-60">gerade eben</span>;
  return <span className="ml-1 opacity-60">{mins} Min</span>;
}

function StatusBadge({ status, updatedAt }: { status: string; updatedAt?: string }) {
  const { t } = useLanguage();
  const map: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
    done:       { label: t("docLib.statusDone"),       cls: "text-green-700 bg-green-50 border-green-200",   icon: CheckCircle },
    ok:         { label: t("docLib.statusDone"),       cls: "text-green-700 bg-green-50 border-green-200",   icon: CheckCircle },
    pending:    { label: t("docLib.statusPending"),    cls: "text-yellow-700 bg-yellow-50 border-yellow-200", icon: Clock },
    parsing:    { label: "Wird geparst",  cls: "text-violet-700 bg-violet-50 border-violet-200", icon: Loader2 },
    analyzing:  { label: "Wird analysiert", cls: "text-blue-700 bg-blue-50 border-blue-200",   icon: Loader2 },
    indexing:   { label: "Wird indexiert",  cls: "text-sky-700 bg-sky-50 border-sky-200",      icon: Loader2 },
    processing: { label: t("docLib.statusProcessing"), cls: "text-blue-700 bg-blue-50 border-blue-200", icon: Loader2 },
    failed:     { label: t("docLib.statusFailed"),     cls: "text-red-700 bg-red-50 border-red-200",         icon: XCircle },
    error:      { label: t("docLib.statusFailed"),     cls: "text-red-700 bg-red-50 border-red-200",         icon: XCircle },
  };
  const { label, cls, icon: Icon } = map[status] ?? map.pending;
  const isActive = ["parsing", "analyzing", "indexing", "processing"].includes(status);
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border font-medium ${cls}`}>
      <Icon className={`w-3 h-3 ${isActive ? "animate-spin" : ""}`} />
      {label}
      {isActive && updatedAt && <ElapsedTime since={updatedAt} />}
    </span>
  );
}

// ── Data Quality Badge ────────────────────────────────────────────────────────

function DocQualityBadge({ quality, expanded = false }: { quality: DocQuality | undefined; expanded?: boolean }) {
  if (!quality) return <span className="text-xs text-slate-300">—</span>;

  const score = quality.quality_score;
  const cls =
    score >= 70 ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
    score >= 40 ? "bg-amber-50 text-amber-700 border-amber-200" :
                  "bg-red-50 text-red-600 border-red-200";

  const yearRange = quality.years.length > 0
    ? `${quality.years[0]}–${quality.years[quality.years.length - 1]}`
    : null;

  const missingLabels = quality.missing_core
    .map((t) => METRIC_LABELS[t] ?? t.replace(/_/g, " "));

  const foundLabels = quality.metric_types
    .map((t) => METRIC_LABELS[t] ?? t.replace(/_/g, " "));

  const tooltipText = [
    `${quality.metric_count} Metriken extrahiert`,
    quality.total_core > 0 ? `Kern: ${quality.found_core}/${quality.total_core}` : null,
    missingLabels.length > 0 ? `Fehlt: ${missingLabels.join(", ")}` : "Alle Kern-Metriken vorhanden",
    yearRange ? `Zeitraum: ${yearRange}` : null,
    `Vorhanden: ${foundLabels.join(", ")}`,
  ].filter(Boolean).join(" · ");

  if (expanded) {
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border font-medium ${cls}`}>
            <BarChart3 className="w-3 h-3 shrink-0" />
            {quality.metric_count} Metriken · {score.toFixed(0)}%
            {quality.total_core > 0 && (
              <span className="opacity-70 font-normal"> ({quality.found_core}/{quality.total_core} Kern)</span>
            )}
          </span>
          {yearRange && (
            <span className="text-xs text-slate-400">{yearRange}</span>
          )}
        </div>
        {missingLabels.length > 0 && (
          <p className="text-xs text-amber-600 flex items-start gap-1">
            <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
            <span>Fehlt: {missingLabels.join(", ")}</span>
          </p>
        )}
      </div>
    );
  }

  return (
    <span
      title={tooltipText}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border font-medium cursor-default ${cls}`}
    >
      <BarChart3 className="w-3 h-3 shrink-0" />
      {quality.metric_count} Metriken · {score.toFixed(0)}%
      {quality.total_core > 0 && (
        <span className="opacity-60 font-normal"> ({quality.found_core}/{quality.total_core})</span>
      )}
    </span>
  );
}

// ── Supplier Documents Modal ──────────────────────────────────────────────────

interface SupplierDocsModalProps {
  supplier: SupplierResponse;
  files: DocumentFile[];
  onClose: () => void;
  onDelete: (fileId: string) => void;
  onView: (file: DocumentFile) => void;
  onProcess: (fileId: string) => void;
  processingId: string | null;
  onUpload: (sup: SupplierResponse, docType?: string, year?: number, title?: string, file?: File, signal?: AbortSignal) => Promise<void>;
  uploadProgress: Record<string, number>;
  sources: DocumentSource[];
  docQualityMap: Record<string, DocQuality>;
}

function SupplierDocsModal({
  supplier, files, onClose, onDelete, onView, onProcess, processingId, onUpload, uploadProgress, sources, docQualityMap,
}: SupplierDocsModalProps) {
  const supFiles = files
    .filter((f) => f.supplier_id === supplier.id)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const uploadingSource = sources.find((s) => s.supplier_id === supplier.id && s.id in uploadProgress);
  const isUploading = !!uploadingSource;
  const currentProgress = uploadingSource ? uploadProgress[uploadingSource.id] : 0;

  const qc = useQueryClient();
  const copilotToggleMut = useMutation({
    mutationFn: (fileId: string) => toggleCopilotVisibility(fileId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["doc-files"] }),
  });
  const [classifying, setClassifying] = useState(false);
  const [batch, setBatch] = useState<{ total: number; done: number; currentName: string } | null>(null);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  function guessDocType(filename: string): { docType: string; year?: number } {
    const f = filename.toLowerCase();
    const yearMatch = f.match(/20(\d{2})/);
    const year = yearMatch ? parseInt("20" + yearMatch[1]) : undefined;
    if (f.includes("nachhaltig") || f.includes("sustain") || f.includes("svb") || f.includes("svr")) return { docType: "sustainability_report", year };
    if (f.includes("csrd")) return { docType: "csrd_report", year };
    if (f.includes("csddd")) return { docType: "csddd_disclosure", year };
    if (f.includes("esg")) return { docType: "esg_overview", year };
    if (f.includes("annual") || f.includes("geschaeft") || f.includes("gesch") || f.includes("gb") || f.includes("ar")) return { docType: "annual_report", year };
    if (f.includes("press") || f.includes("pm_")) return { docType: "press_release", year };
    if (f.includes("investor") || f.includes("praes") || f.includes("pres")) return { docType: "investor_presentation", year };
    if (f.includes("cdp")) return { docType: "cdp_questionnaire", year };
    if (f.includes("audit")) return { docType: "audit_report", year };
    return { docType: "annual_report", year };
  }

  async function handleFilesSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = Array.from(e.target.files ?? []);
    e.target.value = "";
    if (!selectedFiles.length) return;
    setUploadErrors([]);
    setClassifying(true);
    const abort = new AbortController();
    abortRef.current = abort;
    setBatch({ total: selectedFiles.length, done: 0, currentName: selectedFiles[0].name });
    const errors: string[] = [];
    try {
      for (let i = 0; i < selectedFiles.length; i++) {
        if (abort.signal.aborted) break;
        const file = selectedFiles[i];
        setBatch({ total: selectedFiles.length, done: i, currentName: file.name });
        try {
          const { docType, year } = guessDocType(file.name);
          await onUpload(supplier, docType, year, undefined, file, abort.signal);
        } catch (err) {
          if (abort.signal.aborted) break;
          const msg = err instanceof Error ? err.message : String(err);
          errors.push(`${file.name}: ${msg}`);
          console.error("[upload] failed for", file.name, err);
        }
        setBatch({ total: selectedFiles.length, done: i + 1, currentName: file.name });
      }
    } finally {
      abortRef.current = null;
      setClassifying(false);
      if (errors.length) setUploadErrors(errors);
      setTimeout(() => setBatch(null), 2000);
    }
  }

  function handlePickFile() {
    fileInputRef.current?.click();
  }

  function handleStopUpload() {
    abortRef.current?.abort();
  }

  const isBusy = isUploading || classifying || !!batch;
  const batchPct = batch ? Math.round((batch.done / batch.total) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      {/* Hidden file input — React-controlled for reliable Safari support */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
      />
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-7xl mx-4 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-sky-100 dark:bg-sky-950/40 flex items-center justify-center">
              <Building2 className="w-4 h-4 text-sky-600" />
            </div>
            <div>
              <h2 className="text-base font-semibold">{supplier.name}</h2>
              <p className="text-xs text-slate-500">{supplier.country} · {supplier.supplier_tier} · {supFiles.length} Dokument{supFiles.length !== 1 ? "e" : ""}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isBusy && (
              <button
                onClick={handleStopUpload}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
              >
                <XCircle className="w-3.5 h-3.5" />Stopp
              </button>
            )}
            <button
              onClick={handlePickFile}
              disabled={isBusy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium disabled:opacity-50 transition-colors"
            >
              {isBusy
                ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Wird verarbeitet…</>
                : <><Upload className="w-3.5 h-3.5" />PDFs hochladen</>}
            </button>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Upload errors */}
        {uploadErrors.length > 0 && (
          <div className="px-6 py-3 bg-red-50 dark:bg-red-950/20 border-b border-red-200 dark:border-red-900 shrink-0">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1">Fehler beim Hochladen:</p>
                {uploadErrors.map((e, i) => (
                  <p key={i} className="text-xs text-red-600 dark:text-red-300 font-mono break-all">{e}</p>
                ))}
              </div>
              <button onClick={() => setUploadErrors([])} className="text-red-400 hover:text-red-600 shrink-0 text-lg leading-none">×</button>
            </div>
          </div>
        )}

        {/* Batch progress strip */}
        {batch && (
          <div className="px-6 py-3 bg-emerald-50 dark:bg-emerald-950/20 border-b border-emerald-200 dark:border-emerald-900 shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium text-emerald-800 dark:text-emerald-300 truncate max-w-[60%]">
                {batch.done < batch.total ? batch.currentName : "Fertig"}
              </span>
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 shrink-0 ml-2">
                {batch.done} / {batch.total} Dateien · {batchPct}%
              </span>
            </div>
            <div className="w-full h-1.5 bg-emerald-200 dark:bg-emerald-900 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                style={{ width: `${batchPct}%` }}
              />
            </div>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          {supFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <FileText className="w-12 h-12 mb-3 opacity-25" />
              <p className="text-sm font-medium">Noch keine Dokumente</p>
              <p className="text-xs mt-1">Lade das erste Dokument für diesen Lieferanten hoch.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800/80 backdrop-blur-sm">
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Dokument</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Typ</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Jahr</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Seiten</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Datenqualität</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {supFiles.map((f) => (
                  <tr key={f.id} className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                    <td className="px-5 py-3">
                      <p className="font-medium truncate max-w-xs">{f.title || f.company_name || "—"}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{new Date(f.created_at).toLocaleDateString("de-DE")}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">{f.doc_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3 text-slate-500">{f.report_year ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500">{f.pages ?? "—"}</td>
                    <td className="px-4 py-3"><DocQualityBadge quality={docQualityMap[f.id]} /></td>
                    <td className="px-4 py-3"><StatusBadge status={f.status} updatedAt={f.updated_at} /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {/* Detail ansehen */}
                        <button
                          onClick={() => { onView(f); onClose(); }}
                          title="Details ansehen"
                          className="p-1.5 rounded-lg hover:bg-sky-50 dark:hover:bg-sky-950/30 text-slate-400 hover:text-sky-600 transition-colors"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                        {/* Human-in-Loop Review */}
                        {["done", "ok", "completed"].includes(f.status) && (
                          <Link
                            href={`/documents/review/${f.id}`}
                            title="Human-in-Loop Review"
                            className="p-1.5 rounded-lg hover:bg-purple-50 text-slate-400 hover:text-purple-600 transition-colors"
                          >
                            <Microscope className="w-4 h-4" />
                          </Link>
                        )}
                        {/* Copilot Visibility */}
                        <button
                          onClick={() => copilotToggleMut.mutate(f.id)}
                          disabled={copilotToggleMut.isPending}
                          title={f.copilot_hidden ? "Copilot: ausgeblendet — klicken zum Einblenden" : "Copilot: sichtbar — klicken zum Ausblenden"}
                          className={`p-1.5 rounded-lg transition-colors ${f.copilot_hidden ? "text-orange-500 bg-orange-50 hover:bg-orange-100" : "text-slate-300 hover:text-slate-500 hover:bg-slate-50"}`}
                        >
                          {f.copilot_hidden ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                        {/* Download wenn echte URL */}
                        {f.file_url && !f.file_url.startsWith("upload://") && (
                          <a
                            href={f.file_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Herunterladen"
                            className="p-1.5 rounded-lg hover:bg-sky-50 dark:hover:bg-sky-950/30 text-slate-400 hover:text-sky-600 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                        {/* Verarbeitung starten (nur bei pending/failed/error) */}
                        {["pending", "failed", "error"].includes(f.status) && (
                          <button
                            onClick={() => onProcess(f.id)}
                            disabled={processingId === f.id}
                            title="Verarbeitung starten"
                            className="p-1.5 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-950/30 text-slate-400 hover:text-blue-600 transition-colors disabled:opacity-40"
                          >
                            {processingId === f.id
                              ? <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
                              : <Play className="w-4 h-4" />}
                          </button>
                        )}
                        {/* Löschen */}
                        <button
                          onClick={() => {
                            if (confirm(`"${f.title || f.doc_type}" löschen?`)) onDelete(f.id);
                          }}
                          title="Löschen"
                          className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-400 hover:text-red-500 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-700 shrink-0 flex justify-between items-center text-xs text-slate-400">
          <span>
            {(() => {
              const done = supFiles.filter(f => f.status === "done").length;
              const total = supFiles.length;
              const active = supFiles.filter(f => ["parsing","analyzing","indexing","processing"].includes(f.status)).length;
              const chunks = supFiles.reduce((s, f) => s + (f.chunks_count ?? 0), 0);
              return (
                <>
                  <span className="font-medium text-slate-600 dark:text-slate-300">{done}/{total}</span> fertig
                  {active > 0 && <span className="ml-2 text-violet-600 dark:text-violet-400">· {active} in Bearbeitung</span>}
                  {chunks > 0 && <span className="ml-2">· {chunks.toLocaleString()} Chunks</span>}
                </>
              );
            })()}
          </span>
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-medium">
            Schließen
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Add/Edit Source form ──────────────────────────────────────────────────────

interface SourceFormProps {
  initial?: DocumentSource;
  onClose: () => void;
  onSave: (data: DocumentSourceCreate) => void;
  saving: boolean;
  suppliers: SupplierResponse[];
}

function SourceForm({ initial, onClose, onSave, saving, suppliers }: SourceFormProps) {
  const { t } = useLanguage();
  const [url, setUrl] = useState(initial?.source_url ?? "");
  const [docType, setDocType] = useState(initial?.doc_type ?? "annual_report");
  const [schedule, setSchedule] = useState(initial?.schedule ?? "manual");
  const [supplierId, setSupplierId] = useState(initial?.supplier_id ?? "");
  const [company, setCompany] = useState(initial?.company_name ?? "");

  function handleSupplierChange(id: string) {
    setSupplierId(id);
    if (id) {
      const sup = suppliers.find((s) => s.id === id);
      if (sup) setCompany(sup.name);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave({
      source_url: url,
      doc_type: docType,
      schedule,
      supplier_id: supplierId || undefined,
      company_name: company || undefined,
    });
  }

  const inputCls = "w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold mb-4">
          {initial ? t("docLib.formEdit") : t("docLib.formAdd")}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Lieferant Dropdown */}
          <div>
            <label className="block text-sm font-medium mb-1">
              {t("docLib.companyName")}
              {suppliers.length > 0 && (
                <span className="ml-2 text-xs text-slate-400">({suppliers.length} Lieferanten)</span>
              )}
            </label>
            <select
              value={supplierId}
              onChange={(e) => handleSupplierChange(e.target.value)}
              className={inputCls}
            >
              <option value="">— Kein Lieferant / Extern —</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.country}) · {s.supplier_tier}
                </option>
              ))}
            </select>
            {/* Freitext-Fallback wenn kein Lieferant gewählt */}
            {!supplierId && (
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="z. B. EU Kommission, OECD …"
                className={`${inputCls} mt-2`}
              />
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">{t("docLib.sourceUrl")} *</label>
            <input
              required
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className={inputCls}
              placeholder="https://example.com/annual-report.pdf"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">{t("docLib.docType")} *</label>
              <select value={docType} onChange={(e) => setDocType(e.target.value)} className={inputCls}>
                {DOC_TYPES.map((d) => (
                  <option key={d.value} value={d.value}>{d.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">{t("docLib.schedule")}</label>
              <select value={schedule} onChange={(e) => setSchedule(e.target.value)} className={inputCls}>
                {SCHEDULES.map((s) => (
                  <option key={s.value} value={s.value}>{t(s.labelKey)}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800">
              {t("common.cancel")}
            </button>
            <button type="submit" disabled={saving}
              className="px-4 py-2 text-sm rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-medium disabled:opacity-50 flex items-center gap-2">
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {t("common.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Document detail panel ─────────────────────────────────────────────────────

function DocumentDetail({ file, onClose }: { file: DocumentFile; onClose: () => void }) {
  const { t } = useLanguage();

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/30">
      <div className="h-full w-full max-w-xl bg-white dark:bg-slate-900 shadow-2xl border-l border-slate-200 dark:border-slate-700 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          <div>
            <h2 className="font-semibold text-sm leading-tight">{file.title ?? file.company_name ?? "—"}</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {file.company_name} · {file.report_year ?? "—"} · {file.language?.toUpperCase() ?? "—"}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          <div className="flex gap-3 flex-wrap">
            <StatusBadge status={file.status} />
            {file.esg_score != null && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border border-emerald-200 bg-emerald-50 text-emerald-700 font-medium">
                ESG {file.esg_score.toFixed(1)}
              </span>
            )}
            {file.pages != null && (
              <span className="text-xs text-slate-500">{file.pages}p · {file.chunks_count ?? 0} chunks</span>
            )}
          </div>

          {file.summary && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailSummary")}</h3>
              <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{file.summary}</p>
            </section>
          )}

          {file.extracted_risks && file.extracted_risks.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailRisks")}</h3>
              <ul className="space-y-2">
                {file.extracted_risks.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{r.title}</span>
                      {r.severity && (
                        <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                          r.severity === "hoch" || r.severity === "kritisch"
                            ? "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400"
                            : r.severity === "mittel"
                            ? "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}>{r.severity}</span>
                      )}
                      {r.description && <p className="text-slate-500 dark:text-slate-400 mt-0.5">{r.description}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {file.extracted_targets && file.extracted_targets.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailTargets")}</h3>
              <ul className="space-y-2">
                {file.extracted_targets.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                    <div>
                      <span className="font-medium text-slate-800 dark:text-slate-200">{r.target}</span>
                      {r.target_year && <span className="ml-2 text-xs text-slate-500">bis {r.target_year}</span>}
                      {r.current_progress && <p className="text-slate-500 dark:text-slate-400 mt-0.5">{r.current_progress}</p>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {file.extracted_kpis && Object.values(file.extracted_kpis).some(v => v !== null) && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailKpis")}</h3>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                <table className="w-full text-xs">
                  <tbody>
                    {Object.entries(file.extracted_kpis)
                      .filter(([, v]) => v !== null)
                      .map(([k, v]) => (
                        <tr key={k} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                          <td className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400 w-1/2">{k.replace(/_/g, " ")}</td>
                          <td className="px-3 py-2 text-slate-800 dark:text-slate-200">{String(v)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {file.error_msg && (
            <section className="rounded-lg bg-red-50 border border-red-200 p-3">
              <p className="text-xs text-red-700 font-mono break-all">{file.error_msg}</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

type Tab = "suppliers" | "sources" | "log" | "documents";

export default function DocumentLibraryPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("suppliers");
  const [showForm, setShowForm] = useState(false);
  const [editingSource, setEditingSource] = useState<DocumentSource | null>(null);
  const [selectedFile, setSelectedFile] = useState<DocumentFile | null>(null);
  const [ingestingId, setIngestingId] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  // per-row doc_type selector for the supplier tab
  // supplier docs modal
  const [docsModalSupplier, setDocsModalSupplier] = useState<SupplierResponse | null>(null);

  const { data: sources = [], isLoading: loadingSources } = useQuery({
    queryKey: ["document-sources"],
    queryFn: listSources,
  });

  const { data: files = [], isLoading: loadingFiles } = useQuery({
    queryKey: ["document-files"],
    queryFn: () => listFiles(),
    refetchInterval: 5_000,
  });

  const { data: docQualityList = [] } = useQuery({
    queryKey: ["doc-quality"],
    queryFn: getDocQuality,
    staleTime: 60_000,
  });
  const docQualityMap: Record<string, DocQuality> = Object.fromEntries(
    docQualityList.map((q) => [q.doc_file_id, q])
  );

  const { data: suppliersPage, isError: suppliersError, error: suppliersErrDetail } = useQuery({
    queryKey: ["suppliers-dropdown"],
    queryFn: () => listSuppliers({ page_size: 100 }),
    retry: false,
  });
  if (suppliersError) console.error("[docLib] suppliers query failed:", suppliersErrDetail);
  const allSuppliers: SupplierResponse[] = suppliersPage?.items ?? [];

  const createMut = useMutation({
    mutationFn: (payload: DocumentSourceCreate) =>
      editingSource
        ? updateSource(editingSource.id, payload)
        : createSource(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-sources"] });
      setShowForm(false);
      setEditingSource(null);
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-sources"] }),
  });

  const deleteFileMut = useMutation({
    mutationFn: deleteFile,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["document-files"] }),
  });

  const ingestAllMut = useMutation({
    mutationFn: ingestAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
      qc.invalidateQueries({ queryKey: ["document-sources"] });
    },
  });

  const deleteQueuedMut = useMutation({
    mutationFn: deleteQueuedFiles,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
      alert(`${data.deleted} hängende Dokumente gelöscht. Bitte jetzt erneut hochladen.`);
    },
  });

  const reclassifyAllMut = useMutation({
    mutationFn: reclassifyAllFiles,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
      const changedList = data.details
        .filter((r) => "changed" in r && r.changed)
        .map((r) => "old_doc_type" in r ? `${r.old_doc_type} → ${r.new_doc_type}` : "")
        .join("\n");
      alert(`Neu klassifiziert: ${data.total} Dokumente\n✅ Geändert: ${data.changed}\n❌ Fehler: ${data.errors}${changedList ? "\n\nÄnderungen:\n" + changedList : ""}`);
    },
  });

  const processPendingMut = useMutation({
    mutationFn: processPending,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
    },
  });

  const [processingFileId, setProcessingFileId] = useState<string | null>(null);
  const processSingleMut = useMutation({
    mutationFn: processSingleFile,
    onMutate: (id) => setProcessingFileId(id),
    onSettled: () => {
      setProcessingFileId(null);
      qc.invalidateQueries({ queryKey: ["document-files"] });
    },
  });

  const cancelProcessingMut = useMutation({
    mutationFn: cancelProcessing,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
    },
  });

  async function handleIngestSource(sourceId: string) {
    setIngestingId(sourceId);
    try {
      await triggerIngest(sourceId);
      qc.invalidateQueries({ queryKey: ["document-files"] });
      qc.invalidateQueries({ queryKey: ["document-sources"] });
    } finally {
      setIngestingId(null);
    }
  }

  function handleUploadClick(sourceId: string) {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,application/pdf";
    input.multiple = true;
    input.style.display = "none";
    document.body.appendChild(input);
    input.onchange = async () => {
      const files = Array.from(input.files ?? []);
      document.body.removeChild(input);
      if (!files.length) return;
      for (const file of files) {
        setUploadProgress((p) => ({ ...p, [sourceId]: 0 }));
        try {
          await uploadDocument(sourceId, file, (pct) => setUploadProgress((p) => ({ ...p, [sourceId]: pct })));
          qc.invalidateQueries({ queryKey: ["document-files"] });
          qc.invalidateQueries({ queryKey: ["document-sources"] });
        } finally {
          setUploadProgress((p) => { const n = { ...p }; delete n[sourceId]; return n; });
        }
      }
    };
    input.click();
  }

  async function handleSupplierUpload(sup: SupplierResponse, docType?: string, year?: number, title?: string, file?: File, signal?: AbortSignal) {
    if (!file) return;
    const dt = docType ?? "annual_report";

    let source = sources.find((s) => s.supplier_id === sup.id && s.doc_type === dt);
    if (!source) {
      try {
        source = await createSource({
          supplier_id: sup.id,
          company_name: sup.name,
          doc_type: dt,
          source_url: `upload://supplier/${sup.id}/${dt}`,
          schedule: "manual",
        });
        await qc.invalidateQueries({ queryKey: ["document-sources"] });
      } catch (err) {
        console.error("[handleSupplierUpload] createSource failed:", err);
        throw err;
      }
    }

    const sid = source.id;
    setUploadProgress((p) => ({ ...p, [sid]: 0 }));
    try {
      await uploadDocument(sid, file, (pct) => setUploadProgress((p) => ({ ...p, [sid]: pct })), year, title, signal);
      await qc.invalidateQueries({ queryKey: ["document-files"] });
      await qc.invalidateQueries({ queryKey: ["document-sources"] });
    } catch (err) {
      console.error("[handleSupplierUpload] uploadDocument failed:", err);
      throw err;
    } finally {
      setUploadProgress((p) => { const n = { ...p }; delete n[sid]; return n; });
    }
  }

  function handleSupplierDelete(sup: SupplierResponse) {
    const supFiles = files.filter((f) => f.supplier_id === sup.id);
    const supSources = sources.filter((s) => s.supplier_id === sup.id);
    if (supFiles.length === 0 && supSources.length === 0) return;
    if (!confirm(`Alle Dokumente von ${sup.name} löschen?`)) return;
    supSources.forEach((s) => deleteMut.mutate(s.id));
  }

  // KPIs derived from loaded data
  const kpis = [
    { id: "sources", label: t("docLib.kpiSources"), value: sources.length },
    { id: "documents", label: t("docLib.kpiDocuments"), value: files.length },
    { id: "indexed", label: t("docLib.kpiIndexed"), value: files.filter((f) => f.status === "done").length },
    { id: "failed", label: t("docLib.kpiFailed"), value: files.filter((f) => f.status === "failed").length },
  ];

  const TABS: [Tab, string][] = [
    ["suppliers", "Lieferanten"],
    ["sources", t("docLib.tabSources")],
    ["log", t("docLib.tabLog")],
    ["documents", t("docLib.tabDocuments")],
  ];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t("docLib.title")}</h1>
          <p className="text-sm text-slate-500 mt-0.5">{t("docLib.subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          {files.some((f) => (f.status === "queued" || f.status === "error") && (f.chunks_count ?? 0) === 0) && (
            <button
              onClick={() => {
                if (confirm("Alle hängenden / fehlerhaften Dokumente (ohne Chunks) löschen damit sie neu hochgeladen werden können?"))
                  deleteQueuedMut.mutate();
              }}
              disabled={deleteQueuedMut.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-amber-300 dark:border-amber-600 text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 font-medium disabled:opacity-50"
            >
              {deleteQueuedMut.isPending
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <AlertTriangle className="w-4 h-4" />}
              Hängende löschen ({files.filter((f) => (f.status === "queued" || f.status === "error") && (f.chunks_count ?? 0) === 0).length})
            </button>
          )}
          {files.some((f) => f.status === "done") && (
            <button
              onClick={() => {
                if (confirm(`Alle ${files.filter(f => f.status === "done").length} indexierten Dokumente neu klassifizieren? Das kann einige Minuten dauern.`))
                  reclassifyAllMut.mutate();
              }}
              disabled={reclassifyAllMut.isPending}
              title="Alle Dokumente vom Groq-Classifier neu analysieren (doc_type, Firma, Jahr)"
              className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-violet-300 dark:border-violet-600 text-violet-700 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 font-medium disabled:opacity-50"
            >
              {reclassifyAllMut.isPending
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <RefreshCw className="w-4 h-4" />}
              {reclassifyAllMut.isPending ? "Klassifiziere…" : "Alle neu klassifizieren"}
            </button>
          )}
          {(() => {
            const pendingCount = files.filter(f => ["pending", "failed", "error"].includes(f.status)).length;
            const activeCount = files.filter(f => ["parsing", "analyzing", "indexing", "processing"].includes(f.status)).length;
            if (pendingCount === 0 && activeCount === 0) return null;
            return activeCount > 0 ? (
              <button
                onClick={() => cancelProcessingMut.mutate()}
                disabled={cancelProcessingMut.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-red-300 text-red-700 hover:bg-red-50 font-medium disabled:opacity-50"
              >
                {cancelProcessingMut.isPending
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Pause className="w-4 h-4" />}
                Verarbeitung stoppen ({activeCount} aktiv)
              </button>
            ) : (
              <button
                onClick={() => processPendingMut.mutate()}
                disabled={processPendingMut.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50 font-medium disabled:opacity-50"
              >
                {processPendingMut.isPending
                  ? <Loader2 className="w-4 h-4 animate-spin" />
                  : <Play className="w-4 h-4" />}
                {processPendingMut.isPending ? "Wird gestartet…" : `Verarbeitung starten (${pendingCount})`}
              </button>
            );
          })()}
          <button
            onClick={() => ingestAllMut.mutate()}
            disabled={ingestAllMut.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 font-medium disabled:opacity-50"
          >
            {ingestAllMut.isPending
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <RefreshCw className="w-4 h-4" />}
            {t("docLib.ingestAll")}
          </button>
          <Link
            href="/documents/metrics"
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-emerald-300 dark:border-emerald-600 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 font-medium"
          >
            <BarChart3 className="w-4 h-4" />
            Metriken & Signale
          </Link>
          <Link
            href="/documents/review-queue"
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 font-medium"
          >
            <Microscope className="w-4 h-4" />
            Review Queue
          </Link>
          <button
            onClick={() => { setEditingSource(null); setShowForm(true); }}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-sky-600 hover:bg-sky-700 text-white font-medium"
          >
            <Plus className="w-4 h-4" />
            {t("docLib.addSource")}
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.id} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">{kpi.label}</p>
            <p className="text-2xl font-bold mt-1">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="flex gap-1">
          {TABS.map(([tabId, label]) => (
            <button
              key={tabId}
              onClick={() => setActiveTab(tabId)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tabId
                  ? "border-sky-600 text-sky-600"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab: Lieferanten */}
      {activeTab === "suppliers" && (
        <div>
          {allSuppliers.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Building2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Keine Lieferanten gefunden</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Lieferant</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Land</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Tier</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Dokumente</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                    <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide text-right">Aktionen</th>
                  </tr>
                </thead>
                <tbody>
                  {allSuppliers.map((sup) => {
                    const supFiles = files.filter((f) => f.supplier_id === sup.id);
                    const latestFile = supFiles.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
                    const isUploading = sources.some((s) => s.supplier_id === sup.id && s.id in uploadProgress);

                    return (
                      <tr key={sup.id} className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                        {/* Lieferant */}
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-sky-100 dark:bg-sky-950/40 flex items-center justify-center shrink-0">
                              <Building2 className="w-3.5 h-3.5 text-sky-600" />
                            </div>
                            <span className="font-medium">{sup.name}</span>
                          </div>
                        </td>
                        {/* Land */}
                        <td className="px-4 py-3 text-slate-500">{sup.country ?? "—"}</td>
                        {/* Tier */}
                        <td className="px-4 py-3">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {sup.supplier_tier ?? "—"}
                          </span>
                        </td>
                        {/* Dokumente */}
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setDocsModalSupplier(sup)}
                            className={`text-xs px-2.5 py-1 rounded-lg font-medium transition-colors ${
                              supFiles.length > 0
                                ? "bg-sky-50 hover:bg-sky-100 dark:bg-sky-950/30 dark:hover:bg-sky-950/60 text-sky-700 dark:text-sky-400"
                                : "text-slate-300 dark:text-slate-600 hover:text-slate-500"
                            }`}
                          >
                            {supFiles.length > 0 ? `${supFiles.length} Dok. →` : "—"}
                          </button>
                        </td>
                        {/* Status */}
                        <td className="px-4 py-3">
                          {latestFile ? (
                            <StatusBadge status={latestFile.status} />
                          ) : (
                            <span className="text-xs text-slate-300 dark:text-slate-600">—</span>
                          )}
                        </td>
                        {/* Aktionen */}
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            {/* Upload — öffnet Modal mit Fortschrittsanzeige */}
                            <button
                              onClick={() => setDocsModalSupplier(sup)}
                              title="PDF hochladen"
                              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:hover:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 font-medium transition-colors"
                            >
                              {isUploading
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Upload className="w-3.5 h-3.5" />}
                              Hochladen
                            </button>
                            {/* Download — nur wenn Datei vorhanden und URL kein upload:// */}
                            {latestFile?.file_url && !latestFile.file_url.startsWith("upload://") && (
                              <a
                                href={latestFile.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                title="Dokument herunterladen"
                                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-sky-50 hover:bg-sky-100 dark:bg-sky-950/30 dark:hover:bg-sky-950/60 text-sky-700 dark:text-sky-400 font-medium transition-colors"
                              >
                                <Download className="w-3.5 h-3.5" />
                                Download
                              </a>
                            )}
                            {/* Löschen — nur wenn Dokumente vorhanden */}
                            {supFiles.length > 0 && (
                              <button
                                onClick={() => handleSupplierDelete(sup)}
                                title="Dokumente löschen"
                                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-red-50 hover:bg-red-100 dark:bg-red-950/30 dark:hover:bg-red-950/60 text-red-600 dark:text-red-400 font-medium transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                                Löschen
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Sources */}
      {activeTab === "sources" && (
        <div>
          {loadingSources ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : sources.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">{t("docLib.noSources")}</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.companyName")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.docType")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.schedule")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.lastFetched")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.lastStatus")}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {sources.map((src) => (
                    <tr key={src.id} className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Globe className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <div>
                            <p className="font-medium">{src.company_name ?? "—"}</p>
                            <a href={src.source_url} target="_blank" rel="noopener noreferrer"
                              className="text-xs text-slate-400 hover:text-sky-500 truncate max-w-[180px] block">
                              {src.source_url}
                            </a>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{docTypeLabel(src.doc_type)}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{scheduleLabel(src.schedule, t)}</td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {src.last_fetched_at ? new Date(src.last_fetched_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-3">
                        {src.last_status ? <StatusBadge status={src.last_status} /> : <span className="text-xs text-slate-400">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleIngestSource(src.id)}
                            disabled={ingestingId === src.id || src.id in uploadProgress}
                            title={t("docLib.ingest")}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-sky-600 disabled:opacity-40"
                          >
                            {ingestingId === src.id
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <Download className="w-3.5 h-3.5" />}
                          </button>
                          <button
                            onClick={() => handleUploadClick(src.id)}
                            disabled={src.id in uploadProgress || ingestingId === src.id}
                            title={src.id in uploadProgress ? `${t("docLib.uploading")} ${uploadProgress[src.id]}%` : t("docLib.upload")}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-emerald-600 disabled:opacity-40"
                          >
                            {src.id in uploadProgress
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <Upload className="w-3.5 h-3.5" />}
                          </button>
                          <button
                            onClick={() => { setEditingSource(src); setShowForm(true); }}
                            title={t("common.edit")}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-sky-600"
                          >
                            <FileText className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(t("docLib.deleteConfirm"))) deleteMut.mutate(src.id);
                            }}
                            title={t("common.delete")}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-red-500"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Log */}
      {activeTab === "log" && (
        <div>
          {loadingFiles ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <Clock className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">{t("docLib.noDocuments")}</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colTitle")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colType")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colYear")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colPages")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colChunks")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colStatus")}</th>
                    <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">{t("docLib.colDate")}</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((f) => (
                    <tr
                      key={f.id}
                      className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 cursor-pointer"
                      onClick={() => setSelectedFile(f)}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium truncate max-w-[200px]">{f.title ?? f.company_name ?? "—"}</p>
                        <p className="text-xs text-slate-400">{f.company_name}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400 text-xs">{docTypeLabel(f.doc_type)}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.report_year ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.pages ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.chunks_count ?? "—"}</td>
                      <td className="px-4 py-3"><StatusBadge status={f.status} updatedAt={f.updated_at} /></td>
                      <td className="px-4 py-3 text-xs text-slate-500">{new Date(f.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Documents */}
      {activeTab === "documents" && (
        <div>
          {loadingFiles ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {files.filter((f) => f.status === "done").length === 0 ? (
                <div className="col-span-full text-center py-12 text-slate-400">
                  <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">{t("docLib.noDocuments")}</p>
                </div>
              ) : (
                files.filter((f) => f.status === "done").map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedFile(f)}
                    className="text-left bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4 hover:border-sky-300 dark:hover:border-sky-700 hover:shadow-sm transition-all"
                  >
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <div className="w-8 h-8 rounded-lg bg-sky-50 dark:bg-sky-950/30 flex items-center justify-center shrink-0">
                        <Building2 className="w-4 h-4 text-sky-500" />
                      </div>
                      <StatusBadge status={f.status} />
                    </div>
                    <p className="font-semibold text-sm leading-tight line-clamp-2">{f.title ?? f.company_name ?? "—"}</p>
                    <p className="text-xs text-slate-500 mt-1">{f.company_name} · {f.report_year ?? "—"}</p>
                    <div className="flex items-center gap-3 mt-3 text-xs text-slate-400">
                      <span>{docTypeLabel(f.doc_type)}</span>
                      {f.pages && <span>{f.pages}p</span>}
                      {f.esg_score != null && (
                        <span className="text-emerald-600 font-medium">ESG {f.esg_score.toFixed(1)}</span>
                      )}
                    </div>
                    {docQualityMap[f.id] && (
                      <div className="mt-2">
                        <DocQualityBadge quality={docQualityMap[f.id]} expanded />
                      </div>
                    )}
                    {f.summary && (
                      <p className="mt-2 text-xs text-slate-500 line-clamp-2 leading-relaxed">{f.summary}</p>
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* Source form modal */}
      {showForm && (
        <SourceForm
          initial={editingSource ?? undefined}
          onClose={() => { setShowForm(false); setEditingSource(null); }}
          onSave={(data) => createMut.mutate(data)}
          saving={createMut.isPending}
          suppliers={allSuppliers}
        />
      )}

      {/* Supplier Documents Modal */}
      {docsModalSupplier && (
        <SupplierDocsModal
          supplier={docsModalSupplier}
          files={files}
          sources={sources}
          onClose={() => setDocsModalSupplier(null)}
          onDelete={(id) => deleteFileMut.mutate(id)}
          onView={(f) => setSelectedFile(f)}
          onProcess={(id) => processSingleMut.mutate(id)}
          processingId={processingFileId}
          onUpload={(sup, docType, year, title, file) => handleSupplierUpload(sup, docType, year, title, file)}
          uploadProgress={uploadProgress}
          docQualityMap={docQualityMap}
        />
      )}

      {/* Document detail panel */}
      {selectedFile && (
        <DocumentDetail file={selectedFile} onClose={() => setSelectedFile(null)} />
      )}
    </div>
  );
}
