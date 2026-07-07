"use client";

import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Network, AlertTriangle, ChevronRight, ChevronLeft,
  TrendingUp, Users, X, Download,
} from "lucide-react";
import {
  getVisualizationData, getChainStats,
  type ChainNode,
} from "@/lib/api/activity-chain";
import { useLanguage } from "@/lib/i18n/context";

const DIRECTION_LABELS: Record<string, string> = {
  upstream: "Upstream",
  downstream: "Downstream",
  both: "Upstream + Downstream",
};

const DOWNSTREAM_TYPE_LABELS: Record<string, string> = {
  distributor: "Distributor",
  logistics: "Logistik",
  licensee: "Lizenznehmer",
  disposal: "Entsorgung",
  retailer: "Händler",
  other: "Sonstige",
};

// ── SVG Chain Visualization ───────────────────────────────────────────────────

function ChainViz({
  nodes,
  onSelect,
  riskFilter,
}: {
  nodes: ChainNode[];
  onSelect: (n: ChainNode) => void;
  riskFilter: boolean;
}) {
  const upstream = nodes
    .filter((n) => n.chain_direction === "upstream" && n.id !== "company")
    .filter((n) => !riskFilter || (n.risk_band && ["Critical", "High"].includes(n.risk_band)));
  const downstream = nodes
    .filter((n) => n.chain_direction === "downstream" || n.chain_direction === "both")
    .filter((n) => n.id !== "company")
    .filter((n) => !riskFilter || (n.risk_band && ["Critical", "High"].includes(n.risk_band)));

  const maxRows = Math.max(upstream.length, downstream.length, 1);
  const ROW_H = 52;
  const COL_W = 220;
  const SVG_H = Math.max(200, maxRows * ROW_H + 80);
  const SVG_W = COL_W * 3 + 60;

  const cx = SVG_W / 2; // center x (company)
  const cy = SVG_H / 2; // center y

  function nodeY(idx: number, total: number) {
    const startY = cy - ((total - 1) * ROW_H) / 2;
    return startY + idx * ROW_H;
  }

  return (
    <div className="overflow-x-auto">
      <svg width={SVG_W} height={SVG_H} className="block mx-auto">
        {/* Upstream edges */}
        {upstream.map((n, i) => {
          const ny = nodeY(i, upstream.length);
          return (
            <line
              key={`eu-${n.id}`}
              x1={COL_W + 10}
              y1={ny}
              x2={cx - 36}
              y2={cy}
              stroke="#cbd5e1"
              strokeWidth={1.5}
            />
          );
        })}
        {/* Downstream edges */}
        {downstream.map((n, i) => {
          const ny = nodeY(i, downstream.length);
          return (
            <line
              key={`ed-${n.id}`}
              x1={cx + 36}
              y1={cy}
              x2={SVG_W - COL_W - 10}
              y2={ny}
              stroke="#cbd5e1"
              strokeWidth={1.5}
            />
          );
        })}

        {/* Upstream nodes */}
        {upstream.map((n, i) => {
          const ny = nodeY(i, upstream.length);
          return (
            <g key={n.id} onClick={() => onSelect(n)} className="cursor-pointer">
              <rect x={10} y={ny - 18} width={COL_W - 20} height={36} rx={6}
                fill={n.color + "22"} stroke={n.color} strokeWidth={1.5} />
              <text x={COL_W / 2} y={ny - 4} textAnchor="middle" fontSize={11} fontWeight={500} fill="#1e293b">
                {n.label.length > 20 ? n.label.slice(0, 20) + "…" : n.label}
              </text>
              <text x={COL_W / 2} y={ny + 10} textAnchor="middle" fontSize={9} fill="#64748b">
                {n.country} · {n.risk_score !== null ? n.risk_score.toFixed(1) : "—"}
              </text>
            </g>
          );
        })}

        {/* Company center node */}
        <g>
          <circle cx={cx} cy={cy} r={34} fill="#3b82f6" opacity={0.15} />
          <circle cx={cx} cy={cy} r={28} fill="#3b82f6" />
          <text x={cx} y={cy - 5} textAnchor="middle" fontSize={9} fill="white" fontWeight={700}>Mein</text>
          <text x={cx} y={cy + 8} textAnchor="middle" fontSize={9} fill="white" fontWeight={700}>Unternehmen</text>
        </g>

        {/* Downstream nodes */}
        {downstream.map((n, i) => {
          const nx = SVG_W - COL_W + 10;
          const ny = nodeY(i, downstream.length);
          return (
            <g key={n.id} onClick={() => onSelect(n)} className="cursor-pointer">
              <rect x={nx} y={ny - 18} width={COL_W - 20} height={36} rx={6}
                fill={n.color + "22"} stroke={n.color} strokeWidth={1.5} />
              <text x={nx + (COL_W - 20) / 2} y={ny - 4} textAnchor="middle" fontSize={11} fontWeight={500} fill="#1e293b">
                {n.label.length > 20 ? n.label.slice(0, 20) + "…" : n.label}
              </text>
              <text x={nx + (COL_W - 20) / 2} y={ny + 10} textAnchor="middle" fontSize={9} fill="#64748b">
                {n.downstream_type ? DOWNSTREAM_TYPE_LABELS[n.downstream_type] || n.downstream_type : "Downstream"}
                {n.risk_score !== null ? ` · ${n.risk_score.toFixed(1)}` : ""}
              </text>
            </g>
          );
        })}

        {/* Column labels */}
        <text x={COL_W / 2} y={20} textAnchor="middle" fontSize={11} fill="#64748b" fontWeight={600}>Upstream</text>
        <text x={SVG_W / 2} y={20} textAnchor="middle" fontSize={11} fill="#3b82f6" fontWeight={600}>Unternehmen</text>
        <text x={SVG_W - COL_W / 2} y={20} textAnchor="middle" fontSize={11} fill="#64748b" fontWeight={600}>Downstream</text>
      </svg>
    </div>
  );
}

// ── Node Detail Popover ───────────────────────────────────────────────────────

function NodeDetail({ node, onClose }: { node: ChainNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end bg-black/20" onClick={onClose}>
      <div className="m-4 w-72 bg-white rounded-xl shadow-xl p-5" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-800">{node.label}</h3>
          <button onClick={onClose}><X className="w-4 h-4 text-slate-400" /></button>
        </div>
        <div className="space-y-2 text-sm">
          <Row label="Kettenposition" value={DIRECTION_LABELS[node.chain_direction] || node.chain_direction} />
          {node.downstream_type && (
            <Row label="Typ" value={DOWNSTREAM_TYPE_LABELS[node.downstream_type] || node.downstream_type} />
          )}
          {node.country && <Row label="Land" value={node.country} />}
          {node.industry && <Row label="Branche" value={node.industry} />}
          <Row label="Tier" value={node.tier === 0 ? "—" : `Tier ${node.tier}`} />
          {node.risk_score !== null && (
            <Row label="Risikoscore" value={
              <span style={{ color: node.color }} className="font-semibold">
                {node.risk_score.toFixed(1)} ({node.risk_band})
              </span>
            } />
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-800">{value}</span>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function ActivityChainPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<"viz" | "stats">("viz");
  const [riskFilter, setRiskFilter] = useState(false);
  const [selected, setSelected] = useState<ChainNode | null>(null);

  const { data: vizData, isLoading: vizLoading } = useQuery({
    queryKey: ["activity-chain-viz"],
    queryFn: getVisualizationData,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["activity-chain-stats"],
    queryFn: getChainStats,
    enabled: activeTab === "stats",
  });

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Network className="w-7 h-7 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-slate-800">{t("actChain.title")}</h1>
            <p className="text-sm text-slate-500">{t("actChain.subtitle")}</p>
          </div>
        </div>
      </div>

      {/* KPIs */}
      {vizData && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard label={t("actChain.totalPartners")} value={vizData.summary.total} />
          <KpiCard label={t("actChain.upstream")} value={vizData.summary.upstream} color="text-blue-600" icon={<ChevronLeft className="w-5 h-5" />} />
          <KpiCard label={t("actChain.downstream")} value={vizData.summary.downstream} color="text-emerald-600" icon={<ChevronRight className="w-5 h-5" />} />
          <KpiCard label={t("actChain.highRisk")} value={vizData.summary.high_risk} color="text-red-600" icon={<AlertTriangle className="w-5 h-5" />} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b">
        {[
          { id: "viz", label: t("actChain.tabViz") },
          { id: "stats", label: t("actChain.tabStats") },
        ].map((t) => (
          <button key={t.id} onClick={() => setActiveTab(t.id as typeof activeTab)}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${activeTab === t.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Visualization Tab */}
      {activeTab === "viz" && (
        <div className="bg-white border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b bg-slate-50">
            <p className="text-sm font-medium text-slate-700">{t("actChain.fullChain")}</p>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                <input type="checkbox" className="rounded" checked={riskFilter} onChange={(e) => setRiskFilter(e.target.checked)} />
                Nur Hochrisiko
              </label>
              {/* Risk legend */}
              {[
                { label: "Kritisch", color: "#ef4444" },
                { label: "Hoch", color: "#f97316" },
                { label: "Mittel", color: "#eab308" },
                { label: "Gering", color: "#22c55e" },
              ].map((l) => (
                <span key={l.label} className="flex items-center gap-1 text-xs text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: l.color }} />
                  {l.label}
                </span>
              ))}
            </div>
          </div>

          <div className="p-4">
            {vizLoading ? (
              <p className="text-sm text-slate-500 py-12 text-center">Wird geladen...</p>
            ) : !vizData || vizData.nodes.length <= 1 ? (
              <div className="py-12 text-center text-slate-400">
                <Network className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Keine Partner vorhanden</p>
                <p className="text-xs mt-1">Lieferanten mit Kettenposition "Downstream" erfassen, um die Kette vollständig abzubilden</p>
              </div>
            ) : (
              <ChainViz nodes={vizData.nodes} onSelect={setSelected} riskFilter={riskFilter} />
            )}
          </div>
        </div>
      )}

      {/* Stats Tab */}
      {activeTab === "stats" && (
        <div className="space-y-4">
          {statsLoading || !stats ? (
            <p className="text-sm text-slate-500">Wird geladen...</p>
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard label="Partner gesamt" value={stats.total} />
                <StatCard label="Upstream" value={stats.upstream_count} />
                <StatCard label="Downstream" value={stats.downstream_count} />
                <StatCard label="Beide Richtungen" value={stats.both_count} />
                <StatCard label="Downstream-Abdeckung" value={`${stats.downstream_coverage_pct}%`} />
              </div>

              {Object.keys(stats.downstream_type_breakdown).length > 0 && (
                <div className="bg-white border rounded-xl p-5">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Downstream nach Typ</h3>
                  <div className="space-y-2">
                    {Object.entries(stats.downstream_type_breakdown).map(([type, count]) => (
                      <div key={type} className="flex items-center gap-3">
                        <span className="w-32 text-sm text-slate-600">{DOWNSTREAM_TYPE_LABELS[type] || type}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${Math.min(100, (count / stats.downstream_count) * 100)}%` }}
                          />
                        </div>
                        <span className="w-6 text-sm font-medium text-slate-700 text-right">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {stats.downstream_count === 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                  <p className="text-sm text-amber-800">
                    <strong>Hinweis:</strong> Keine Downstream-Partner erfasst. CSDDD Art. 2 Abs. 1 lit. g schreibt vor, auch Vertrieb, Transport, Lagerung und Entsorgung durch Geschäftspartner in die DD einzubeziehen.
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {selected && <NodeDetail node={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function KpiCard({ label, value, color = "text-slate-800", icon }: { label: string; value: number; color?: string; icon?: React.ReactNode }) {
  return (
    <div className="bg-white border rounded-xl p-4 flex items-center gap-3">
      {icon && <span className={color}>{icon}</span>}
      <div>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white border rounded-xl p-4">
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  );
}
