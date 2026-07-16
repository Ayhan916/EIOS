"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getFileReview, listFiles, DocumentFile, ReviewData, ReviewMetric } from "@/lib/api/documents";
import { ArrowUpRight, ArrowDownRight, Minus, ArrowLeft, GitCompareArrows } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

// ── Helpers ──────────────────────────────────────────────────────────────────

function delta(a: number, b: number): number {
  if (a === 0) return 0;
  return ((b - a) / Math.abs(a)) * 100;
}

function fmtDelta(pct: number): string {
  const abs = Math.abs(pct);
  return (pct > 0 ? "+" : "") + (abs >= 10 ? abs.toFixed(0) : abs.toFixed(1)) + "%";
}

function DeltaBadge({ pct, lowerIsBetter = false }: { pct: number; lowerIsBetter?: boolean }) {
  if (Math.abs(pct) < 0.5) return <span className="text-gray-400 text-xs flex items-center gap-0.5"><Minus size={11} /> 0%</span>;
  const improved = lowerIsBetter ? pct < 0 : pct > 0;
  const color = improved ? "text-green-600" : "text-red-500";
  const Icon = pct > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`text-xs font-semibold flex items-center gap-0.5 ${color}`}>
      <Icon size={12} />
      {fmtDelta(pct)}
    </span>
  );
}

function numericKpiValue(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (typeof v === "object" && v !== null && "value" in v) return numericKpiValue((v as Record<string, unknown>).value);
  if (typeof v === "string") { const n = parseFloat(v.replace(",", ".")); return isNaN(n) ? null : n; }
  return null;
}

// ── Document Selector ─────────────────────────────────────────────────────────

function DocSelector({ value, onChange, exclude }: { value: string; onChange: (id: string) => void; exclude?: string }) {
  const { data: files } = useQuery({ queryKey: ["files-list-compare"], queryFn: () => listFiles() });
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[240px] max-w-[340px]"
    >
      <option value="">— Dokument wählen —</option>
      {(files ?? [])
        .filter((f: DocumentFile) => f.id !== exclude && ["done", "ok", "completed"].includes(f.status))
        .map((f: DocumentFile) => (
          <option key={f.id} value={f.id}>
            {f.title ?? f.doc_type}{f.company_name ? ` · ${f.company_name}` : ""}{f.report_year ? ` · ${f.report_year}` : ""}
          </option>
        ))}
    </select>
  );
}

// ── Overview comparison ───────────────────────────────────────────────────────

function MetaRow({ label, a, b }: { label: string; a: React.ReactNode; b: React.ReactNode }) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-2 pr-4 text-xs text-gray-500 font-medium whitespace-nowrap">{label}</td>
      <td className="py-2 px-4 text-xs text-gray-800 text-center">{a ?? <span className="text-gray-300">—</span>}</td>
      <td className="py-2 px-4 text-xs text-gray-800 text-center">{b ?? <span className="text-gray-300">—</span>}</td>
    </tr>
  );
}

function qualityScore(d: ReviewData): number {
  const parseScore = d.pages ? Math.round(Math.min((d.chunks_count ?? 0) / d.pages, 1) * 25) : 0;
  const classScore = Math.round((d.classification_confidence ?? 0) * 25);
  const chunkScore = (() => {
    const cs = d.chunks ?? [];
    if (cs.length === 0) return 0;
    const avg = cs.reduce((s, c) => s + c.content.length, 0) / cs.length;
    const ratio = Math.min(avg / 800, 1);
    return Math.round(ratio * 25);
  })();
  const kpiCount = (d.metrics?.length ?? 0) + Object.keys(d.extracted_kpis ?? {}).length;
  const kpiScore = Math.round(Math.min(kpiCount / 10, 1) * 25);
  return parseScore + classScore + chunkScore + kpiScore;
}

function QScore({ score }: { score: number }) {
  const color = score >= 75 ? "text-green-600 bg-green-50 border-green-200"
    : score >= 50 ? "text-yellow-600 bg-yellow-50 border-yellow-200"
    : "text-red-600 bg-red-50 border-red-200";
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-bold ${color}`}>{score}</span>;
}

function OverviewTable({ a, b }: { a: ReviewData; b: ReviewData }) {
  const qA = qualityScore(a);
  const qB = qualityScore(b);
  return (
    <table className="w-full text-left">
      <thead>
        <tr className="border-b border-gray-200">
          <th className="py-2 pr-4 text-xs text-gray-400 font-medium">Feld</th>
          <th className="py-2 px-4 text-xs text-gray-400 font-medium text-center">Dok A</th>
          <th className="py-2 px-4 text-xs text-gray-400 font-medium text-center">Dok B</th>
        </tr>
      </thead>
      <tbody>
        <MetaRow label="Dokumenttyp" a={a.doc_type} b={b.doc_type} />
        <MetaRow label="Jahr" a={a.report_year} b={b.report_year} />
        <MetaRow label="Sprache" a={a.language?.toUpperCase()} b={b.language?.toUpperCase()} />
        <MetaRow label="Seiten" a={a.pages} b={b.pages} />
        <MetaRow label="Chunks" a={a.chunks_count} b={b.chunks_count} />
        <MetaRow label="Metriken" a={a.metrics.length} b={b.metrics.length} />
        <MetaRow label="Freigabe" a={<StatusBadge s={a.review_status} />} b={<StatusBadge s={b.review_status} />} />
        <MetaRow label="Qualität" a={<QScore score={qA} />} b={<div className="flex items-center justify-center gap-2"><QScore score={qB} />{qA > 0 && <DeltaBadge pct={delta(qA, qB)} />}</div>} />
      </tbody>
    </table>
  );
}

function StatusBadge({ s }: { s: string }) {
  const color = s === "approved" ? "bg-green-50 text-green-700 border-green-200"
    : s === "draft" ? "bg-gray-50 text-gray-500 border-gray-200"
    : "bg-yellow-50 text-yellow-700 border-yellow-200";
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${color}`}>{s}</span>;
}

// ── KPI Comparison ────────────────────────────────────────────────────────────

function KpiCompareTable({ a, b }: { a: ReviewData; b: ReviewData }) {
  const kpisA = a.extracted_kpis ?? {};
  const kpisB = b.extracted_kpis ?? {};
  const allKeys = Array.from(new Set([...Object.keys(kpisA), ...Object.keys(kpisB)])).sort();

  if (allKeys.length === 0) {
    return <p className="text-xs text-gray-400 py-4 text-center">Keine KPIs vorhanden</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-3 py-2 text-gray-500 font-medium">KPI</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Dok A</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Dok B</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Änderung</th>
          </tr>
        </thead>
        <tbody>
          {allKeys.map((key, i) => {
            const va = numericKpiValue(kpisA[key]);
            const vb = numericKpiValue(kpisB[key]);
            const pct = va !== null && vb !== null ? delta(va, vb) : null;
            const lowerIsBetter = /co2|emission|energy|waste|water|risk/i.test(key);
            return (
              <tr key={key} className={`border-b border-gray-100 last:border-0 ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                <td className="px-3 py-2 text-gray-600 font-medium">{key}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-800">
                  {va !== null ? va.toLocaleString("de-DE") : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-800">
                  {vb !== null ? vb.toLocaleString("de-DE") : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2 text-right">
                  {pct !== null ? <DeltaBadge pct={pct} lowerIsBetter={lowerIsBetter} /> : <span className="text-gray-300">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Metric Comparison ─────────────────────────────────────────────────────────

function MetricCompareTable({ a, b }: { a: ReviewData; b: ReviewData }) {
  // Match by metric_type + unit; show all (outer join)
  type MatchedMetric = { key: string; unit: string; ma?: ReviewMetric; mb?: ReviewMetric };

  const map = new Map<string, MatchedMetric>();
  for (const m of a.metrics) {
    const k = `${m.metric_type}||${m.unit}`;
    map.set(k, { key: m.metric_type, unit: m.unit, ma: m });
  }
  for (const m of b.metrics) {
    const k = `${m.metric_type}||${m.unit}`;
    const existing = map.get(k);
    if (existing) existing.mb = m;
    else map.set(k, { key: m.metric_type, unit: m.unit, mb: m });
  }
  const rows = Array.from(map.values()).sort((x, y) => x.key.localeCompare(y.key));

  if (rows.length === 0) {
    return <p className="text-xs text-gray-400 py-4 text-center">Keine Metriken vorhanden</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            <th className="text-left px-3 py-2 text-gray-500 font-medium">Metrik</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Einheit</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Dok A</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Dok B</th>
            <th className="text-right px-3 py-2 text-gray-500 font-medium">Δ %</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ key, unit, ma, mb }, i) => {
            const pct = ma && mb ? delta(ma.value, mb.value) : null;
            const lowerIsBetter = /co2|emission|scope|energy|waste|water|accident|injury/i.test(key);
            const onlyInA = !mb;
            const onlyInB = !ma;
            return (
              <tr key={`${key}${unit}`} className={`border-b border-gray-100 last:border-0 ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                <td className="px-3 py-2 text-gray-600 font-medium">
                  <div className="flex items-center gap-1.5">
                    {key}
                    {onlyInA && <span className="text-[10px] bg-blue-50 text-blue-500 border border-blue-200 rounded px-1">nur A</span>}
                    {onlyInB && <span className="text-[10px] bg-purple-50 text-purple-500 border border-purple-200 rounded px-1">nur B</span>}
                  </div>
                </td>
                <td className="px-3 py-2 text-right text-gray-400">{unit}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-800">
                  {ma ? ma.value.toLocaleString("de-DE") : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-800">
                  {mb ? mb.value.toLocaleString("de-DE") : <span className="text-gray-300">—</span>}
                </td>
                <td className="px-3 py-2 text-right">
                  {pct !== null ? <DeltaBadge pct={pct} lowerIsBetter={lowerIsBetter} /> : <span className="text-gray-300">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

function ComparePageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const idA = searchParams.get("a") ?? "";
  const idB = searchParams.get("b") ?? "";

  const { data: docA, isLoading: loadingA } = useQuery({
    queryKey: ["review", idA],
    queryFn: () => getFileReview(idA),
    enabled: !!idA,
  });
  const { data: docB, isLoading: loadingB } = useQuery({
    queryKey: ["review", idB],
    queryFn: () => getFileReview(idB),
    enabled: !!idB,
  });

  const setA = (id: string) => router.push(`/documents/compare?a=${id}&b=${idB}`);
  const setB = (id: string) => router.push(`/documents/compare?a=${idA}&b=${id}`);

  const ready = !!docA && !!docB;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <Link href="/documents" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft size={16} />
            </Link>
            <div className="flex items-center gap-2">
              <GitCompareArrows size={18} className="text-blue-600" />
              <h1 className="text-lg font-semibold text-gray-900">Dokumenten-Vergleich</h1>
            </div>
          </div>

          {/* Selectors */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded px-2 py-0.5">A</span>
              <DocSelector value={idA} onChange={setA} exclude={idB} />
            </div>
            <span className="text-gray-400 text-sm font-medium">vs.</span>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-purple-600 bg-purple-50 border border-purple-200 rounded px-2 py-0.5">B</span>
              <DocSelector value={idB} onChange={setB} exclude={idA} />
            </div>
            {docA && <Link href={`/documents/review/${idA}`} className="text-xs text-gray-400 hover:text-blue-500 ml-2">→ Dok A öffnen</Link>}
            {docB && <Link href={`/documents/review/${idB}`} className="text-xs text-gray-400 hover:text-purple-500 ml-2">→ Dok B öffnen</Link>}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Placeholder when nothing selected */}
        {!idA && !idB && (
          <div className="flex flex-col items-center justify-center py-24 text-gray-400">
            <GitCompareArrows size={48} className="mb-4 opacity-30" />
            <p className="text-sm">Wähle zwei Dokumente aus, um sie zu vergleichen.</p>
          </div>
        )}

        {/* Loading */}
        {((idA && loadingA) || (idB && loadingB)) && (
          <div className="flex items-center justify-center py-16 text-gray-400">
            <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mr-3" />
            Dokumente werden geladen…
          </div>
        )}

        {/* Comparison */}
        {ready && (
          <div className="space-y-8">
            {/* Doc title bar */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-blue-600 bg-blue-100 rounded px-1.5 py-0.5">A</span>
                  <span className="text-sm font-semibold text-gray-800">{docA.company_name ?? "Unbekannt"}</span>
                </div>
                <p className="text-xs text-gray-500">{docA.title ?? docA.doc_type} · {docA.report_year ?? "?"} · {docA.pages ?? "?"} Seiten</p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-bold text-purple-600 bg-purple-100 rounded px-1.5 py-0.5">B</span>
                  <span className="text-sm font-semibold text-gray-800">{docB.company_name ?? "Unbekannt"}</span>
                </div>
                <p className="text-xs text-gray-500">{docB.title ?? docB.doc_type} · {docB.report_year ?? "?"} · {docB.pages ?? "?"} Seiten</p>
              </div>
            </div>

            {/* Overview */}
            <section>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">Überblick</h2>
              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <OverviewTable a={docA} b={docB} />
              </div>
            </section>

            {/* Metrics */}
            <section>
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Metriken
                <span className="ml-2 text-xs font-normal text-gray-400">
                  {docA.metrics.length} in A · {docB.metrics.length} in B
                </span>
              </h2>
              <MetricCompareTable a={docA} b={docB} />
            </section>

            {/* KPIs */}
            {(Object.keys(docA.extracted_kpis ?? {}).length > 0 || Object.keys(docB.extracted_kpis ?? {}).length > 0) && (
              <section>
                <h2 className="text-sm font-semibold text-gray-700 mb-3">
                  Extrahierte KPIs
                  <span className="ml-2 text-xs font-normal text-gray-400">
                    {Object.keys(docA.extracted_kpis ?? {}).length} in A · {Object.keys(docB.extracted_kpis ?? {}).length} in B
                  </span>
                </h2>
                <KpiCompareTable a={docA} b={docB} />
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense>
      <ComparePageInner />
    </Suspense>
  );
}
