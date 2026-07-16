"use client";

import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, Legend,
  ResponsiveContainer, CartesianGrid,
} from "recharts";
import {
  ArrowLeft, RefreshCw, Loader2, TrendingUp, TrendingDown,
  Minus, AlertTriangle, BarChart3, Leaf, Zap, Activity,
} from "lucide-react";
import {
  listMetrics, listSignals, listTrends, extractAllIntelligence, verifyMetrics, detectContradictions,
  METRIC_LABELS, UNIT_LABELS, FINANCIAL_METRICS, ESG_METRICS,
  DIMENSION_LABELS, SEVERITY_ORDER, formatValue,
  type CompanyMetric, type CompanySignal, type TrendAlert,
} from "@/lib/api/intelligence";

// ── Colour palette ────────────────────────────────────────────────────────────

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#f97316", "#84cc16",
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function DirectionIcon({ direction }: { direction: string }) {
  if (direction === "positive") return <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />;
  if (direction === "negative") return <TrendingDown className="w-3.5 h-3.5 text-red-500" />;
  return <Minus className="w-3.5 h-3.5 text-slate-400" />;
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "critical" ? "bg-red-100 text-red-700 border-red-200" :
    severity === "high"     ? "bg-orange-100 text-orange-700 border-orange-200" :
    severity === "medium"   ? "bg-amber-100 text-amber-700 border-amber-200" :
                              "bg-slate-100 text-slate-600 border-slate-200";
  const label =
    severity === "critical" ? "Kritisch" :
    severity === "high"     ? "Hoch" :
    severity === "medium"   ? "Mittel" : "Niedrig";
  return (
    <span className={`inline-flex text-xs px-1.5 py-0.5 rounded-full border font-medium ${cls}`}>
      {label}
    </span>
  );
}

// ── Time-series chart builder ─────────────────────────────────────────────────

function buildChartData(metrics: CompanyMetric[], selectedTypes: string[]) {
  const byYear: Record<number, Record<string, number>> = {};
  for (const m of metrics) {
    if (!selectedTypes.includes(m.metric_type)) continue;
    if (!byYear[m.year]) byYear[m.year] = {};
    byYear[m.year][m.metric_type] = m.value;
  }
  return Object.entries(byYear)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([year, vals]) => ({ year: Number(year), ...vals }));
}

// ── Metric Selector ───────────────────────────────────────────────────────────

function MetricSelector({
  available, selected, onChange,
}: { available: string[]; selected: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {available.map((mt, i) => {
        const active = selected.includes(mt);
        return (
          <button
            key={mt}
            onClick={() => onChange(active ? selected.filter(x => x !== mt) : [...selected, mt])}
            className={`px-2.5 py-1 text-xs rounded-full border font-medium transition-colors ${
              active
                ? "text-white border-transparent"
                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-400"
            }`}
            style={active ? { backgroundColor: COLORS[i % COLORS.length], borderColor: COLORS[i % COLORS.length] } : {}}
          >
            {METRIC_LABELS[mt] ?? mt}
          </button>
        );
      })}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type Tab = "financial" | "esg" | "signals" | "trends";

export default function DocumentMetricsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("financial");
  const [selectedFinancial, setSelectedFinancial] = useState<string[]>(["revenue", "ebitda", "net_income"]);
  const [selectedEsg, setSelectedEsg] = useState<string[]>(["co2_scope1", "co2_scope2", "co2_scope3"]);
  const [signalDimension, setSignalDimension] = useState<string>("all");
  const [yoySortAsc, setYoySortAsc] = useState(false);

  const { data: metrics = [], isLoading: loadingMetrics } = useQuery({
    queryKey: ["company-metrics"],
    queryFn: () => listMetrics(),
  });

  const { data: signals = [], isLoading: loadingSignals } = useQuery({
    queryKey: ["company-signals"],
    queryFn: () => listSignals(),
  });

  const { data: trends = [], isLoading: loadingTrends } = useQuery({
    queryKey: ["company-trends"],
    queryFn: () => listTrends(),
  });

  const extractMut = useMutation({
    mutationFn: extractAllIntelligence,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["company-metrics"] });
      qc.invalidateQueries({ queryKey: ["company-signals"] });
      alert(`Extraktion abgeschlossen:\n✅ ${data.total_metrics} Metriken\n✅ ${data.total_signals} Signale`);
    },
    onError: (err: Error) => alert(`Fehler: ${err.message}`),
  });

  const verifyMut = useMutation({
    mutationFn: verifyMetrics,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["company-metrics"] });
      qc.invalidateQueries({ queryKey: ["company-trends"] });
      alert(`Verifizierung abgeschlossen:\n✅ ${data.verified} bestätigt\n⚠️ ${data.discrepant} Ausreißer erkannt\n— ${data.not_found} nicht gefunden`);
    },
    onError: (err: Error) => alert(`Fehler: ${err.message}`),
  });

  const contradictionMut = useMutation({
    mutationFn: detectContradictions,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["company-signals"] });
      const n = data.contradictions ?? data.total_contradictions ?? 0;
      alert(`Widerspruchsanalyse abgeschlossen:\n⚠️ ${n} Widersprüche erkannt`);
    },
    onError: (err: Error) => alert(`Fehler: ${err.message}`),
  });

  // ── Derived data ──────────────────────────────────────────────────────────

  const companies = useMemo(() => [...new Set(metrics.map(m => m.company_name))], [metrics]);
  const years = useMemo(() => [...new Set(metrics.map(m => m.year))].sort(), [metrics]);

  const availableFinancial = useMemo(
    () => FINANCIAL_METRICS.filter(mt => metrics.some(m => m.metric_type === mt)),
    [metrics]
  );
  const availableEsg = useMemo(
    () => ESG_METRICS.filter(mt => metrics.some(m => m.metric_type === mt)),
    [metrics]
  );

  const financialChartData = useMemo(
    () => buildChartData(metrics.filter(m => FINANCIAL_METRICS.includes(m.metric_type)), selectedFinancial),
    [metrics, selectedFinancial]
  );

  const esgChartData = useMemo(
    () => buildChartData(metrics.filter(m => ESG_METRICS.includes(m.metric_type)), selectedEsg),
    [metrics, selectedEsg]
  );

  const yoySignals = useMemo(
    () => [...signals.filter(s => s.signal_type === "yoy_comparison")]
      .sort((a, b) => yoySortAsc ? (a.year ?? 0) - (b.year ?? 0) : (b.year ?? 0) - (a.year ?? 0)),
    [signals, yoySortAsc]
  );

  const contradictionSignals = useMemo(
    () => [...signals.filter(s => s.signal_type === "contradiction")]
      .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)),
    [signals]
  );

  const otherSignals = useMemo(
    () => signals.filter(s => s.signal_type !== "yoy_comparison" && s.signal_type !== "contradiction"),
    [signals]
  );

  const filteredSignals = useMemo(() => {
    const base = signalDimension === "all" ? otherSignals : otherSignals.filter(s => s.dimension === signalDimension);
    return [...base].sort((a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
    );
  }, [otherSignals, signalDimension]);

  const signalDimensions = useMemo(() => [...new Set(otherSignals.map(s => s.dimension))], [otherSignals]);

  // ── KPIs ──────────────────────────────────────────────────────────────────

  const kpis = [
    { label: "Metriken", value: metrics.length, icon: BarChart3, color: "text-blue-600 bg-blue-50" },
    { label: "Signale", value: signals.length, icon: Zap, color: "text-amber-600 bg-amber-50" },
    { label: "Unternehmen", value: companies.length, icon: TrendingUp, color: "text-emerald-600 bg-emerald-50" },
    { label: "Jahre", value: years.length ? `${years[0]}–${years[years.length - 1]}` : "—", icon: Leaf, color: "text-violet-600 bg-violet-50" },
  ];

  const negTrends = useMemo(() => trends.filter(t => t.sentiment === "negative"), [trends]);
  const isEmpty = metrics.length === 0 && signals.length === 0;
  const isLoading = loadingMetrics || loadingSignals || loadingTrends;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/documents" className="text-slate-400 hover:text-slate-600 transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Company Intelligence</h1>
            <p className="text-sm text-slate-500 mt-0.5">Strukturierte Kennzahlen und Signale aus Dokumenten</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (confirm("Commitments und Ziele gegen tatsächliche Kennzahlen prüfen? Dauert 1–2 Minuten."))
                contradictionMut.mutate({});
            }}
            disabled={contradictionMut.isPending || extractMut.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-orange-300 dark:border-orange-600 text-orange-700 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 font-medium disabled:opacity-50"
          >
            {contradictionMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
            {contradictionMut.isPending ? "Analysiere…" : "Widersprüche erkennen"}
          </button>
          <button
            onClick={() => {
              if (confirm("Extrahierte Metriken gegen Online-Quellen (Yahoo Finance + Web) prüfen? Dauert 1–3 Minuten."))
                verifyMut.mutate({});
            }}
            disabled={verifyMut.isPending || extractMut.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-emerald-300 dark:border-emerald-600 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 font-medium disabled:opacity-50"
          >
            {verifyMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
            {verifyMut.isPending ? "Verifiziere…" : "Online verifizieren"}
          </button>
          <button
            onClick={() => {
              if (confirm("Alle indexierten Dokumente neu analysieren und Metriken/Signale extrahieren? Das kann einige Minuten dauern."))
                extractMut.mutate();
            }}
            disabled={extractMut.isPending || verifyMut.isPending}
            className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-violet-300 dark:border-violet-600 text-violet-700 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 font-medium disabled:opacity-50"
          >
            {extractMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            {extractMut.isPending ? "Extrahiere…" : "Neu extrahieren"}
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-3">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${kpi.color}`}>
              <kpi.icon className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs text-slate-500">{kpi.label}</p>
              <p className="text-xl font-bold">{isLoading ? "…" : kpi.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {!isLoading && isEmpty && (
        <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-300 dark:border-slate-600 p-12 text-center">
          <BarChart3 className="w-10 h-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 dark:text-slate-400 font-medium">Noch keine Metriken extrahiert</p>
          <p className="text-sm text-slate-500 mt-1 mb-4">Klicke "Neu extrahieren" um Kennzahlen und Signale aus den indexierten Dokumenten zu laden.</p>
          <button
            onClick={() => extractMut.mutate()}
            disabled={extractMut.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-violet-600 hover:bg-violet-700 text-white font-medium disabled:opacity-50"
          >
            {extractMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Extraktion starten
          </button>
        </div>
      )}

      {/* Tabs */}
      {!isEmpty && (
        <>
          <div className="border-b border-slate-200 dark:border-slate-700">
            <nav className="flex gap-1">
              {([
                ["financial", "Finanzkennzahlen", BarChart3],
                ["esg",       "ESG & Nachhaltigkeit", Leaf],
                ["signals",   `Signale (${signals.length})`, Zap],
                ["trends",    `Trend-Alerts (${trends.length})`, Activity],
              ] as [Tab, string, React.ElementType][]).map(([id, label, Icon]) => (
                <button
                  key={id}
                  onClick={() => setTab(id)}
                  className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                    tab === id
                      ? "border-sky-600 text-sky-600"
                      : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              ))}
            </nav>
          </div>

          {/* Financial Tab */}
          {tab === "financial" && (
            <div className="space-y-4">
              {availableFinancial.length === 0 ? (
                <EmptyTab label="Finanzkennzahlen" />
              ) : (
                <>
                  <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Kennzahl auswählen</p>
                    <MetricSelector available={availableFinancial} selected={selectedFinancial} onChange={setSelectedFinancial} />
                  </div>

                  {financialChartData.length > 0 && selectedFinancial.length > 0 && (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                      <h3 className="text-sm font-semibold mb-4">Zeitreihe</h3>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={financialChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} width={60} />
                          <Tooltip
                            formatter={(value: number, name: string) => [
                              value.toLocaleString("de-DE"),
                              METRIC_LABELS[name] ?? name,
                            ]}
                          />
                          <Legend formatter={(v) => METRIC_LABELS[v] ?? v} />
                          {selectedFinancial.map((mt, i) => (
                            <Line
                              key={mt}
                              type="monotone"
                              dataKey={mt}
                              stroke={COLORS[i % COLORS.length]}
                              strokeWidth={2}
                              dot={{ r: 4 }}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <MetricsTable metrics={metrics.filter(m => FINANCIAL_METRICS.includes(m.metric_type))} />
                </>
              )}
            </div>
          )}

          {/* ESG Tab */}
          {tab === "esg" && (
            <div className="space-y-4">
              {availableEsg.length === 0 ? (
                <EmptyTab label="ESG-Metriken" />
              ) : (
                <>
                  <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Metrik auswählen</p>
                    <MetricSelector available={availableEsg} selected={selectedEsg} onChange={setSelectedEsg} />
                  </div>

                  {esgChartData.length > 0 && selectedEsg.length > 0 && (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
                      <h3 className="text-sm font-semibold mb-4">Zeitreihe</h3>
                      <ResponsiveContainer width="100%" height={320}>
                        <LineChart data={esgChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} width={60} />
                          <Tooltip
                            formatter={(value: number, name: string) => [
                              value.toLocaleString("de-DE"),
                              METRIC_LABELS[name] ?? name,
                            ]}
                          />
                          <Legend formatter={(v) => METRIC_LABELS[v] ?? v} />
                          {selectedEsg.map((mt, i) => (
                            <Line
                              key={mt}
                              type="monotone"
                              dataKey={mt}
                              stroke={COLORS[i % COLORS.length]}
                              strokeWidth={2}
                              dot={{ r: 4 }}
                              connectNulls
                            />
                          ))}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}

                  <MetricsTable metrics={metrics.filter(m => ESG_METRICS.includes(m.metric_type))} />
                </>
              )}
            </div>
          )}

          {/* Trends Tab */}
          {tab === "trends" && (
            <div className="space-y-4">
              {trends.length === 0 ? (
                <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 p-10 text-center">
                  <Activity className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">Noch keine Trends erkennbar.<br />Mindestens 2 Datenpunkte pro Metrik nötig.</p>
                </div>
              ) : (
                <>
                  {negTrends.length > 0 && (
                    <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
                      <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                      <p className="text-sm text-red-700 dark:text-red-400">
                        <span className="font-semibold">{negTrends.length} besorgniserregende Trends</span> erkannt —
                        Metriken die sich in die falsche Richtung entwickeln.
                      </p>
                    </div>
                  )}
                  {/* Legende */}
                  <div className="flex items-center gap-4 px-1 text-xs text-slate-500">
                    <span className="font-medium text-slate-400">Farbe:</span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm border border-red-300 bg-red-50 inline-block" />
                      Negativ — Metrik entwickelt sich in die falsche Richtung
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm border border-emerald-300 bg-emerald-50 inline-block" />
                      Positiv — Metrik entwickelt sich gut
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm border border-slate-200 bg-white inline-block" />
                      Neutral — Richtung nicht eindeutig bewertbar
                    </span>
                  </div>

                  <div className="space-y-3">
                    {trends.map((alert, i) => (
                      <TrendAlertCard key={i} alert={alert} />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Signals Tab */}
          {tab === "signals" && (
            <div className="space-y-4">
              {signals.length === 0 ? (
                <EmptyTab label="Signale" />
              ) : (
                <>
                  {/* Jahresvergleich */}
                  {yoySignals.length > 0 && (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-sky-200 dark:border-sky-800 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <BarChart3 className="w-4 h-4 text-sky-500" />
                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          Jahresvergleich
                        </h3>
                        <span className="text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                          automatisch beim Dokument-Upload
                        </span>
                        <button
                          onClick={() => setYoySortAsc(v => !v)}
                          className="ml-auto flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 border border-slate-200 dark:border-slate-700 rounded px-2 py-0.5"
                        >
                          {yoySortAsc ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                          {yoySortAsc ? "Älteste zuerst" : "Neueste zuerst"}
                        </button>
                      </div>
                      <div className="space-y-1">
                        {yoySignals.map(s => {
                          const color =
                            s.direction === "positive" ? "text-emerald-600 dark:text-emerald-400" :
                            s.direction === "negative" ? "text-red-600 dark:text-red-400" :
                            "text-slate-500";
                          const Icon =
                            s.direction === "positive" ? TrendingUp :
                            s.direction === "negative" ? TrendingDown : Minus;
                          return (
                            <div key={s.id} className="flex items-center gap-2 py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0">
                              <Icon className={`w-3.5 h-3.5 shrink-0 ${color}`} />
                              <span className={`text-sm ${color} font-medium min-w-0`}>{s.description}</span>
                              <span className="ml-auto text-xs text-slate-400 shrink-0">{s.year}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Widersprüche */}
                  {contradictionSignals.length > 0 && (
                    <div className="bg-white dark:bg-slate-900 rounded-xl border border-orange-200 dark:border-orange-800 p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="w-4 h-4 text-orange-500" />
                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          Widersprüche erkannt
                        </h3>
                        <span className="text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                          {contradictionSignals.length} Commitment{contradictionSignals.length !== 1 ? "s" : ""} nicht eingehalten
                        </span>
                      </div>
                      <div className="space-y-2">
                        {contradictionSignals.map(s => {
                          const badgeCls =
                            s.severity === "high"   ? "bg-red-100 text-red-700 border-red-200" :
                            s.severity === "medium" ? "bg-orange-100 text-orange-700 border-orange-200" :
                                                      "bg-amber-100 text-amber-700 border-amber-200";
                          const severityLabel =
                            s.severity === "high" ? "Hoch" : s.severity === "medium" ? "Mittel" : "Niedrig";
                          const parts = s.description.split(" | ");
                          return (
                            <div key={s.id} className="border border-orange-100 dark:border-orange-900 rounded-lg p-3 space-y-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className={`inline-flex text-xs px-1.5 py-0.5 rounded-full border font-medium ${badgeCls}`}>
                                  {severityLabel}
                                </span>
                                {s.year && <span className="text-xs text-slate-400">{s.year}</span>}
                                <span className="text-xs text-slate-500">{s.company_name}</span>
                              </div>
                              {parts.map((p, i) => (
                                <p key={i} className={`text-xs leading-relaxed ${i === 2 ? "text-orange-700 dark:text-orange-400 font-medium" : "text-slate-600 dark:text-slate-400"}`}>
                                  {p}
                                </p>
                              ))}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Dimension filter */}
                  <div className="flex flex-wrap gap-2">
                    {["all", ...signalDimensions].map((dim) => (
                      <button
                        key={dim}
                        onClick={() => setSignalDimension(dim)}
                        className={`px-3 py-1 text-xs rounded-full border font-medium transition-colors ${
                          signalDimension === dim
                            ? "bg-sky-600 text-white border-sky-600"
                            : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 hover:border-slate-400"
                        }`}
                      >
                        {dim === "all" ? `Alle (${signals.length})` : `${DIMENSION_LABELS[dim] ?? dim} (${signals.filter(s => s.dimension === dim).length})`}
                      </button>
                    ))}
                  </div>

                  <div className="space-y-2">
                    {filteredSignals.map((signal) => (
                      <div
                        key={signal.id}
                        className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5">
                            <DirectionIcon direction={signal.direction} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="text-xs font-mono text-slate-500 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                                {signal.signal_type}
                              </span>
                              <span className="text-xs text-slate-500">
                                {DIMENSION_LABELS[signal.dimension] ?? signal.dimension}
                              </span>
                              <SeverityBadge severity={signal.severity} />
                              {signal.year && (
                                <span className="text-xs text-slate-400">{signal.year}</span>
                              )}
                            </div>
                            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                              {signal.description}
                            </p>
                            <p className="text-xs text-slate-400 mt-1">{signal.company_name}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TrendAlertCard({ alert }: { alert: TrendAlert }) {
  const isNeg = alert.sentiment === "negative";
  const isPos = alert.sentiment === "positive";

  const border = isNeg
    ? "border-red-200 dark:border-red-800"
    : isPos
    ? "border-emerald-200 dark:border-emerald-800"
    : "border-slate-200 dark:border-slate-700";

  const badge =
    alert.severity === "critical" ? "bg-red-100 text-red-700 border-red-200" :
    alert.severity === "high"     ? "bg-orange-100 text-orange-700 border-orange-200" :
    alert.severity === "medium"   ? "bg-amber-100 text-amber-700 border-amber-200" :
                                    "bg-slate-100 text-slate-600 border-slate-200";

  const severityLabel =
    alert.severity === "critical" ? "Kritisch" :
    alert.severity === "high"     ? "Hoch" :
    alert.severity === "medium"   ? "Mittel" : "Niedrig";

  const Icon = alert.direction === "up" ? TrendingUp : TrendingDown;
  const iconColor = isNeg ? "text-red-500" : isPos ? "text-emerald-500" : "text-slate-400";
  const sign = alert.direction === "up" ? "+" : "-";

  const unit = UNIT_LABELS[alert.unit] ?? alert.unit;

  return (
    <div className={`bg-white dark:bg-slate-900 rounded-xl border ${border} p-4`}>
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${iconColor}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              {METRIC_LABELS[alert.metric_type] ?? alert.metric_type}
            </span>
            <span className="text-xs text-slate-500">{alert.company_name}</span>
            <span className={`inline-flex text-xs px-1.5 py-0.5 rounded-full border font-medium ${badge}`}>
              {severityLabel}
            </span>
            <span className="text-xs text-slate-400 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
              {alert.alert_type === "consecutive" ? "Konsekutiv" : "Sprung"}
            </span>
          </div>

          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">{alert.description}</p>

          {/* Quellenangabe */}
          {alert.reference_source && (
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-xs text-slate-400">Quelle:</span>
              {alert.reference_url ? (
                <a
                  href={alert.reference_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {alert.reference_source}
                </a>
              ) : (
                <span className="text-xs text-slate-500">{alert.reference_source}</span>
              )}
              {alert.verification_note && (
                <span className="text-xs text-slate-400 italic">— {alert.verification_note}</span>
              )}
            </div>
          )}

          {/* Jahr-zu-Jahr Verlauf */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {alert.changes.map((c, idx) => {
              const pos = c.pct_change > 0;
              const color = isNeg
                ? (pos ? "text-red-600" : "text-emerald-600")
                : isPos
                ? (pos ? "text-emerald-600" : "text-red-600")
                : "text-slate-500";
              return (
                <span key={idx} className="flex items-center gap-1 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-700 rounded px-2 py-0.5">
                  <span className="text-slate-400">{c.year_from}→{c.year_to}</span>
                  <span className={`font-medium ${color}`}>
                    {c.pct_change > 0 ? "+" : ""}{c.pct_change.toFixed(1)}%
                  </span>
                  <span className="text-slate-400">
                    ({c.value_to.toLocaleString("de-DE", { maximumFractionDigits: 1 })} {unit})
                  </span>
                </span>
              );
            })}
          </div>
        </div>
        <div className={`text-right shrink-0 ${iconColor}`}>
          <div className="text-lg font-bold">
            {sign}{alert.avg_pct_change.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400">Ø/Jahr</div>
        </div>
      </div>
    </div>
  );
}

function EmptyTab({ label }: { label: string }) {
  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 p-10 text-center">
      <AlertTriangle className="w-8 h-8 text-slate-300 mx-auto mb-2" />
      <p className="text-sm text-slate-500">Keine {label} extrahiert.<br />Starte die Extraktion oben rechts.</p>
    </div>
  );
}

function MetricsTable({ metrics }: { metrics: CompanyMetric[] }) {
  const byType = useMemo(() => {
    const map: Record<string, CompanyMetric[]> = {};
    for (const m of metrics) {
      if (!map[m.metric_type]) map[m.metric_type] = [];
      map[m.metric_type].push(m);
    }
    return map;
  }, [metrics]);

  if (Object.keys(byType).length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
            <th className="text-left px-4 py-2.5 font-medium text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Kennzahl</th>
            {[...new Set(metrics.map(m => m.year))].sort().map(y => (
              <th key={y} className="text-right px-3 py-2.5 font-medium text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">{y}</th>
            ))}
            <th className="text-left px-4 py-2.5 font-medium text-slate-600 dark:text-slate-400 text-xs uppercase tracking-wide">Einheit</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(byType).map(([mt, rows]) => {
            const years = [...new Set(metrics.map(m => m.year))].sort();
            const byYear: Record<number, number> = {};
            for (const r of rows) byYear[r.year] = r.value;
            return (
              <tr key={mt} className="border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                <td className="px-4 py-2.5 font-medium text-slate-700 dark:text-slate-300">
                  {METRIC_LABELS[mt] ?? mt}
                </td>
                {years.map(y => (
                  <td key={y} className="px-3 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-400">
                    {byYear[y] != null ? byYear[y].toLocaleString("de-DE") : "—"}
                  </td>
                ))}
                <td className="px-4 py-2.5 text-xs text-slate-400">
                  {UNIT_LABELS[rows[0]?.unit] ?? rows[0]?.unit ?? ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
