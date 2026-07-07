"use client";

import { useState } from "react";
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
  FileText,
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import {
  listSources,
  createSource,
  updateSource,
  deleteSource,
  triggerIngest,
  listFiles,
  getFile,
  ingestAll,
  type DocumentSource,
  type DocumentFile,
  type DocumentSourceCreate,
} from "@/lib/api/documents";

// ── Doc type helpers ──────────────────────────────────────────────────────────

const DOC_TYPES = [
  { value: "annual_report", labelKey: "docLib.typeAnnual" },
  { value: "sustainability_report", labelKey: "docLib.typeSustainability" },
  { value: "audit_report", labelKey: "docLib.typeAudit" },
  { value: "csrd_report", labelKey: "docLib.typeCsrd" },
  { value: "csddd_disclosure", labelKey: "docLib.typeCsddd" },
  { value: "sector_risk", labelKey: "docLib.typeSector" },
] as const;

const SCHEDULES = [
  { value: "manual", labelKey: "docLib.scheduleManual" },
  { value: "daily", labelKey: "docLib.scheduleDaily" },
  { value: "weekly", labelKey: "docLib.scheduleWeekly" },
  { value: "monthly", labelKey: "docLib.scheduleMonthly" },
] as const;

function docTypeLabel(
  docType: string,
  t: (k: TranslationKey) => string,
): string {
  const found = DOC_TYPES.find((d) => d.value === docType);
  return found ? t(found.labelKey) : docType;
}

function scheduleLabel(schedule: string, t: (k: TranslationKey) => string): string {
  const found = SCHEDULES.find((s) => s.value === schedule);
  return found ? t(found.labelKey) : schedule;
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useLanguage();
  const map: Record<string, { label: string; cls: string; icon: React.ElementType }> = {
    done: { label: t("docLib.statusDone"), cls: "text-green-700 bg-green-50 border-green-200", icon: CheckCircle },
    pending: { label: t("docLib.statusPending"), cls: "text-yellow-700 bg-yellow-50 border-yellow-200", icon: Clock },
    processing: { label: t("docLib.statusProcessing"), cls: "text-blue-700 bg-blue-50 border-blue-200", icon: Loader2 },
    failed: { label: t("docLib.statusFailed"), cls: "text-red-700 bg-red-50 border-red-200", icon: XCircle },
  };
  const { label, cls, icon: Icon } = map[status] ?? map.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border font-medium ${cls}`}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
}

// ── Add/Edit Source form ──────────────────────────────────────────────────────

interface SourceFormProps {
  initial?: DocumentSource;
  onClose: () => void;
  onSave: (data: DocumentSourceCreate) => void;
  saving: boolean;
}

function SourceForm({ initial, onClose, onSave, saving }: SourceFormProps) {
  const { t } = useLanguage();
  const [url, setUrl] = useState(initial?.source_url ?? "");
  const [docType, setDocType] = useState(initial?.doc_type ?? "annual_report");
  const [schedule, setSchedule] = useState(initial?.schedule ?? "monthly");
  const [company, setCompany] = useState(initial?.company_name ?? "");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSave({ source_url: url, doc_type: docType, schedule, company_name: company || undefined });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-lg p-6">
        <h2 className="text-lg font-semibold mb-4">
          {initial ? t("docLib.formEdit") : t("docLib.formAdd")}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">{t("docLib.sourceUrl")} *</label>
            <input
              required
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              placeholder="https://example.com/annual-report"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("docLib.companyName")}</label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">{t("docLib.docType")} *</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                {DOC_TYPES.map((d) => (
                  <option key={d.value} value={d.value}>{t(d.labelKey)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">{t("docLib.schedule")}</label>
              <select
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
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
              <ul className="space-y-1.5">
                {file.extracted_risks.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                    <span className="text-slate-700 dark:text-slate-300">{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {file.extracted_targets && file.extracted_targets.length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailTargets")}</h3>
              <ul className="space-y-1.5">
                {file.extracted_targets.map((r, i) => (
                  <li key={i} className="flex gap-2 text-sm">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                    <span className="text-slate-700 dark:text-slate-300">{r}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {file.extracted_kpis && Object.keys(file.extracted_kpis).length > 0 && (
            <section>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">{t("docLib.detailKpis")}</h3>
              <div className="rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                <table className="w-full text-xs">
                  <tbody>
                    {Object.entries(file.extracted_kpis).map(([k, v]) => (
                      <tr key={k} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                        <td className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400 w-1/2">{k}</td>
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

type Tab = "sources" | "log" | "documents";

export default function DocumentLibraryPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>("sources");
  const [showForm, setShowForm] = useState(false);
  const [editingSource, setEditingSource] = useState<DocumentSource | null>(null);
  const [selectedFile, setSelectedFile] = useState<DocumentFile | null>(null);
  const [ingestingId, setIngestingId] = useState<string | null>(null);

  const { data: sources = [], isLoading: loadingSources } = useQuery({
    queryKey: ["document-sources"],
    queryFn: listSources,
  });

  const { data: files = [], isLoading: loadingFiles } = useQuery({
    queryKey: ["document-files"],
    queryFn: () => listFiles(),
    refetchInterval: 15_000,
  });

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

  const ingestAllMut = useMutation({
    mutationFn: ingestAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document-files"] });
      qc.invalidateQueries({ queryKey: ["document-sources"] });
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

  // KPIs derived from loaded data
  const kpis = [
    { id: "sources", label: t("docLib.kpiSources"), value: sources.length },
    { id: "documents", label: t("docLib.kpiDocuments"), value: files.length },
    { id: "indexed", label: t("docLib.kpiIndexed"), value: files.filter((f) => f.status === "done").length },
    { id: "failed", label: t("docLib.kpiFailed"), value: files.filter((f) => f.status === "failed").length },
  ];

  const TABS: [Tab, string][] = [
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
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{docTypeLabel(src.doc_type, t)}</td>
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
                            disabled={ingestingId === src.id}
                            title={t("docLib.ingest")}
                            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 hover:text-sky-600 disabled:opacity-40"
                          >
                            {ingestingId === src.id
                              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              : <Download className="w-3.5 h-3.5" />}
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
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400 text-xs">{docTypeLabel(f.doc_type, t)}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.report_year ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.pages ?? "—"}</td>
                      <td className="px-4 py-3 text-slate-600 dark:text-slate-400">{f.chunks_count ?? "—"}</td>
                      <td className="px-4 py-3"><StatusBadge status={f.status} /></td>
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
                      <span>{docTypeLabel(f.doc_type, t)}</span>
                      {f.pages && <span>{f.pages}p</span>}
                      {f.esg_score != null && (
                        <span className="text-emerald-600 font-medium">ESG {f.esg_score.toFixed(1)}</span>
                      )}
                    </div>
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
        />
      )}

      {/* Document detail panel */}
      {selectedFile && (
        <DocumentDetail file={selectedFile} onClose={() => setSelectedFile(null)} />
      )}
    </div>
  );
}
