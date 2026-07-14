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
  Minus, AlertTriangle, BarChart3, Leaf, Zap,
} from "lucide-react";
import {
  listMetrics, listSignals, extractAllIntelligence,
  METRIC_LABELS, UNIT_LABELS, FINANCIAL_METRICS, ESG_METRICS,
  DIMENSION_LABELS, SEVERITY_ORDER, formatValue,
  type CompanyMetric, type CompanySignal,
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

type Tab = "financial" | "esg" | "signals";

export default function DocumentMetricsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("financial");
  const [selectedFinancial, setSelectedFinancial] = useState<string[]>(["revenue", "ebitda", "net_income"]);
  const [selectedEsg, setSelectedEsg] = useState<string[]>(["co2_scope1", "co2_scope2", "co2_scope3"]);
  const [signalDimension, setSignalDimension] = useState<string>("all");

  const { data: metrics = [], isLoading: loadingMetrics } = useQuery({
    queryKey: ["company-metrics"],
    queryFn: () => listMetrics(),
  });

  const { data: signals = [], isLoading: loadingSignals } = useQuery({
    queryKey: ["company-signals"],
    queryFn: () => listSignals(),
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

  const filteredSignals = useMemo(() => {
    const base = signalDimension === "all" ? signals : signals.filter(s => s.dimension === signalDimension);
    return [...base].sort((a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
    );
  }, [signals, signalDimension]);

  const signalDimensions = useMemo(() => [...new Set(signals.map(s => s.dimension))], [signals]);

  // ── KPIs ──────────────────────────────────────────────────────────────────

  const kpis = [
    { label: "Metriken", value: metrics.length, icon: BarChart3, color: "text-blue-600 bg-blue-50" },
    { label: "Signale", value: signals.length, icon: Zap, color: "text-amber-600 bg-amber-50" },
    { label: "Unternehmen", value: companies.length, icon: TrendingUp, color: "text-emerald-600 bg-emerald-50" },
    { label: "Jahre", value: years.length ? `${years[0]}–${years[years.length - 1]}` : "—", icon: Leaf, color: "text-violet-600 bg-violet-50" },
  ];

  const isEmpty = metrics.length === 0 && signals.length === 0;
  const isLoading = loadingMetrics || loadingSignals;

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
        <button
          onClick={() => {
            if (confirm("Alle indexierten Dokumente neu analysieren und Metriken/Signale extrahieren? Das kann einige Minuten dauern."))
              extractMut.mutate();
          }}
          disabled={extractMut.isPending}
          className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg border border-violet-300 dark:border-violet-600 text-violet-700 dark:text-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 font-medium disabled:opacity-50"
        >
          {extractMut.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {extractMut.isPending ? "Extrahiere…" : "Neu extrahieren"}
        </button>
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

          {/* Signals Tab */}
          {tab === "signals" && (
            <div className="space-y-4">
              {signals.length === 0 ? (
                <EmptyTab label="Signale" />
              ) : (
                <>
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
