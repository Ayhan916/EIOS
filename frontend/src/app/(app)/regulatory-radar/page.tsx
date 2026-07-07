"use client";

import { useEffect, useState } from "react";
import {
  ChangeCreate,
  ChangeUpdate,
  RadarDashboard,
  RegulatoryChange,
  RegulatorySource,
  createChange,
  getRadarDashboard,
  listChanges,
  listSources,
  seedSources,
  updateChange,
} from "@/lib/api/regulatory-radar";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  analysed: "bg-yellow-100 text-yellow-800",
  implemented: "bg-green-100 text-green-800",
  not_relevant: "bg-gray-100 text-gray-500",
};

const ACTION_COLORS: Record<string, string> = {
  yes: "bg-red-100 text-red-800",
  no: "bg-gray-100 text-gray-600",
  pending: "bg-yellow-100 text-yellow-700",
};

function KPI({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${highlight && value > 0 ? "border-orange-200 bg-orange-50" : "border-gray-200 bg-white"}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${highlight && value > 0 ? "text-orange-700" : "text-gray-900"}`}>{value}</p>
    </div>
  );
}

export default function RegulatoryRadarPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<"inbox" | "sources" | "create">("inbox");
  const [dashboard, setDashboard] = useState<RadarDashboard | null>(null);
  const [changes, setChanges] = useState<RegulatoryChange[]>([]);
  const [sources, setSources] = useState<RegulatorySource[]>([]);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterAction, setFilterAction] = useState("");
  const [seeding, setSeeding] = useState(false);
  const [loading, setLoading] = useState(false);

  // Create form
  const [form, setForm] = useState<ChangeCreate>({ title: "", source_name: "Manual Entry", summary: "", affected_articles: [], action_required: "pending" });
  const [articlesInput, setArticlesInput] = useState("");
  const [creating, setCreating] = useState(false);

  // Analyse dialog
  const [analyseId, setAnalyseId] = useState<string | null>(null);
  const [update, setUpdate] = useState<ChangeUpdate>({});

  const load = async () => {
    setLoading(true);
    try {
      const [dash, ch, src] = await Promise.all([
        getRadarDashboard(),
        listChanges({ status: filterStatus || undefined, action_required: filterAction || undefined }),
        listSources(),
      ]);
      setDashboard(dash);
      setChanges(ch);
      setSources(src);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus, filterAction]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seedSources();
      load();
    } finally {
      setSeeding(false);
    }
  };

  const handleCreate = async () => {
    if (!form.title) return;
    setCreating(true);
    try {
      const articles = articlesInput.split(",").map(a => a.trim()).filter(Boolean);
      await createChange({ ...form, affected_articles: articles });
      setForm({ title: "", source_name: "Manual Entry", summary: "", affected_articles: [], action_required: "pending" });
      setArticlesInput("");
      setTab("inbox");
      load();
    } finally {
      setCreating(false);
    }
  };

  const handleUpdate = async () => {
    if (!analyseId) return;
    await updateChange(analyseId, update);
    setAnalyseId(null); setUpdate({});
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("regRadar.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("regRadar.subtitle")}</p>
      </div>

      {dashboard && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <KPI label={t("regRadar.kpiTotal")} value={dashboard.total} />
          <KPI label={t("regRadar.kpiNew")} value={dashboard.new} highlight />
          <KPI label={t("regRadar.actionRequired")} value={dashboard.action_required} highlight />
          <KPI label={t("regRadar.kpiImplemented")} value={dashboard.implemented} />
          <KPI label={t("regRadar.kpiNotRelevant")} value={dashboard.not_relevant} />
        </div>
      )}

      <div className="flex gap-2 border-b border-gray-200">
        {(["inbox", "sources", "create"] as const).map((tb) => (
          <button key={tb} onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-medium capitalize ${tab === tb ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"}`}>
            {tb === "inbox" ? t("regRadar.tabInbox") : tb === "sources" ? t("regRadar.tabSources") : t("regRadar.tabAddChange")}
          </button>
        ))}
      </div>

      {/* Inbox Tab */}
      {tab === "inbox" && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} className="rounded border px-2 py-1.5 text-sm">
              <option value="">{t("regRadar.allStatuses")}</option>
              {["new", "analysed", "implemented", "not_relevant"].map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
            </select>
            <select value={filterAction} onChange={(e) => setFilterAction(e.target.value)} className="rounded border px-2 py-1.5 text-sm">
              <option value="">{t("regRadar.allActions")}</option>
              {["yes", "no", "pending"].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          {loading ? <p className="text-sm text-gray-500">Loading…</p> : changes.length === 0 ? (
            <p className="text-sm text-gray-500">No regulatory changes. Add one manually or enable RSS monitoring.</p>
          ) : (
            <div className="space-y-2">
              {changes.map((c) => (
                <div key={c.id} className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex flex-wrap gap-2 mb-1">
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[c.status] ?? ""}`}>{c.status}</span>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ACTION_COLORS[c.action_required] ?? ""}`}>action: {c.action_required}</span>
                        {c.affected_articles.map(a => <span key={a} className="rounded bg-blue-50 px-1.5 py-0.5 text-xs text-blue-700">{a}</span>)}
                      </div>
                      <p className="font-medium text-gray-900">{c.title}</p>
                      <p className="mt-0.5 text-xs text-gray-500">{c.source_name}{c.effective_date ? ` · ${new Date(c.effective_date).toLocaleDateString()}` : ""}</p>
                      {c.summary && <p className="mt-1 text-xs text-gray-600 line-clamp-2">{c.summary}</p>}
                    </div>
                    <button onClick={() => { setAnalyseId(c.id); setUpdate({ status: c.status, action_required: c.action_required, action_description: c.action_description }); }} className="shrink-0 rounded bg-gray-100 px-2 py-0.5 text-xs hover:bg-gray-200">Analyse</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sources Tab */}
      {tab === "sources" && (
        <div className="space-y-3">
          {sources.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
              <p className="text-sm text-gray-500 mb-3">No regulatory sources. Seed the global library with 10 pre-configured sources (EUR-Lex, BAFA, EFRAG, ILO, OECD, etc.)</p>
              <button onClick={handleSeed} disabled={seeding} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-40">
                {seeding ? "Seeding…" : "Seed 10 Standard Sources"}
              </button>
            </div>
          ) : (
            <>
              <button onClick={handleSeed} disabled={seeding} className="rounded bg-gray-100 px-3 py-1.5 text-sm hover:bg-gray-200 disabled:opacity-40">
                {seeding ? "Seeding…" : "Re-seed Standard Sources"}
              </button>
              <div className="grid gap-3 sm:grid-cols-2">
                {sources.map((s) => (
                  <div key={s.id} className="rounded-lg border border-gray-200 bg-white p-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">{s.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{s.description.slice(0, 80)}{s.description.length > 80 ? "…" : ""}</p>
                      </div>
                      <span className="text-xs text-gray-400">★{s.relevance_score}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-400">
                      {s.country_code && <span>🌍 {s.country_code}</span>}
                      {s.rss_feed_url && <span>📡 RSS</span>}
                      {!s.organization_id && <span className="text-blue-500">Global</span>}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Create Tab */}
      {tab === "create" && (
        <div className="max-w-xl space-y-3">
          <div><label className="block text-sm font-medium">Title *</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" placeholder="e.g. CSDDD Delegated Act on High-Risk Sectors" /></div>
          <div><label className="block text-sm font-medium">Source Name</label><input value={form.source_name ?? ""} onChange={(e) => setForm({ ...form, source_name: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
          <div><label className="block text-sm font-medium">URL</label><input value={form.url ?? ""} onChange={(e) => setForm({ ...form, url: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" placeholder="https://eur-lex.europa.eu/…" /></div>
          <div><label className="block text-sm font-medium">Affected CSDDD Articles (comma-separated)</label><input value={articlesInput} onChange={(e) => setArticlesInput(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" placeholder="Art. 7, Art. 10, Art. 16" /></div>
          <div><label className="block text-sm font-medium">Summary</label><textarea value={form.summary ?? ""} onChange={(e) => setForm({ ...form, summary: e.target.value })} rows={4} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
          <div><label className="block text-sm font-medium">Action Required</label>
            <select value={form.action_required ?? "pending"} onChange={(e) => setForm({ ...form, action_required: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm">
              <option value="pending">Pending analysis</option>
              <option value="yes">Yes — action needed</option>
              <option value="no">No — not applicable</option>
            </select>
          </div>
          <button onClick={handleCreate} disabled={!form.title || creating} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-40">
            {creating ? "Creating…" : "Add to Inbox"}
          </button>
        </div>
      )}

      {/* Analyse Dialog */}
      {analyseId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-3">
            <h2 className="font-semibold">Impact Analysis</h2>
            <div><label className="block text-xs font-medium">Status</label>
              <select value={update.status ?? "new"} onChange={(e) => setUpdate({ ...update, status: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm">
                {["new", "analysed", "implemented", "not_relevant"].map(s => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
              </select>
            </div>
            <div><label className="block text-xs font-medium">Action Required</label>
              <select value={update.action_required ?? "pending"} onChange={(e) => setUpdate({ ...update, action_required: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm">
                <option value="pending">Pending</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </div>
            <div><label className="block text-xs font-medium">Action Description</label>
              <textarea value={update.action_description ?? ""} onChange={(e) => setUpdate({ ...update, action_description: e.target.value })} rows={3} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div><label className="block text-xs font-medium">Estimated Effort (days)</label>
              <input type="number" value={update.estimated_effort_days ?? 0} onChange={(e) => setUpdate({ ...update, estimated_effort_days: +e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setAnalyseId(null)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleUpdate} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">Save Analysis</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
