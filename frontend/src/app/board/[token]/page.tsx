"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  Globe,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { getBoardPortalData } from "@/lib/api/executive";

// ── Types ─────────────────────────────────────────────────────────────────────

type PortalData = Awaited<ReturnType<typeof getBoardPortalData>>;

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number | null | undefined, dec = 1) {
  if (n == null) return "—";
  return n.toFixed(dec);
}

function MetricCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {label}
          </p>
          <p className={`mt-1 text-3xl font-bold tabular-nums ${accent ?? "text-slate-900"}`}>
            {value}
          </p>
          {sub && <p className="mt-0.5 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className="rounded-full bg-slate-100 p-2.5">
          <Icon className="h-5 w-5 text-slate-500" />
        </div>
      </div>
    </div>
  );
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-6 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          {title}
        </h2>
      </div>
      <div className="px-6 py-5">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between py-2 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-slate-900">{value}</span>
    </div>
  );
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded bg-slate-200 ${className ?? "h-4 w-full"}`} />
  );
}

// ── #128 Expiry countdown with extend option ──────────────────────────────────

function ExpiryBadge({ expiresAt, token }: { expiresAt: string; token: string }) {
  const [remaining, setRemaining] = useState("");
  const [extended, setExtended] = useState(false);
  const [extending, setExtending] = useState(false);

  useEffect(() => {
    function update() {
      const diff = new Date(expiresAt).getTime() - Date.now();
      if (diff <= 0) { setRemaining("Expired"); return; }
      const h = Math.floor(diff / 3_600_000);
      const m = Math.floor((diff % 3_600_000) / 60_000);
      setRemaining(h > 0 ? `${h}h ${m}m remaining` : `${m}m remaining`);
    }
    update();
    const id = setInterval(update, 60_000);
    return () => clearInterval(id);
  }, [expiresAt]);

  async function handleExtend() {
    setExtending(true);
    try {
      await fetch(`/executive/board-portal/${token}/extend`, { method: "POST" });
      setExtended(true);
    } catch { /* silent */ }
    finally { setExtending(false); }
  }

  const isExpired = remaining === "Expired";
  const isWarning = !isExpired && remaining.includes("m") && !remaining.includes("h");

  return (
    <div className="flex items-center gap-2">
      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
        isExpired ? "bg-red-100 text-red-700" : isWarning ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"
      }`}>
        <Clock className="h-3 w-3" />
        {remaining}
      </span>
      {(isWarning || isExpired) && !extended && (
        <button
          onClick={handleExtend}
          disabled={extending}
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          {extending ? "Extending…" : "Extend 4h"}
        </button>
      )}
      {extended && (
        <span className="text-xs text-emerald-600 font-medium">Extended ✓</span>
      )}
    </div>
  );
}

// ── Portfolio section ─────────────────────────────────────────────────────────

function PortfolioSection({ data }: { data: PortalData }) {
  const ps = (data.sections.portfolio ?? {}) as Record<string, unknown>;
  const ss = (data.supplier_snapshot ?? {}) as Record<string, unknown>;

  const totalSuppliers = Number(ps.total_suppliers ?? ss.total_suppliers ?? 0);
  const scoredSuppliers = Number(ps.scored_suppliers ?? ss.scored_suppliers ?? 0);
  const avgEsg = Number(ps.avg_esg_score ?? ss.avg_esg_score ?? 0) || null;
  const critical = Number(ps.critical_risk_suppliers ?? ss.critical_risk_suppliers ?? 0);
  const overdueActions = Number(ps.overdue_actions ?? 0);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Total Suppliers"
          value={totalSuppliers}
          icon={Globe}
          sub={`${scoredSuppliers} scored`}
        />
        <MetricCard
          label="Avg ESG Score"
          value={avgEsg != null ? fmt(avgEsg, 0) : "—"}
          icon={TrendingUp}
          accent={avgEsg != null && avgEsg >= 70 ? "text-emerald-600" : "text-red-600"}
        />
        <MetricCard
          label="Critical Risk"
          value={critical}
          icon={ShieldAlert}
          accent={critical > 0 ? "text-red-600" : undefined}
        />
        <MetricCard
          label="Overdue Actions"
          value={overdueActions}
          icon={Clock}
          accent={overdueActions > 0 ? "text-orange-600" : undefined}
        />
      </div>
    </div>
  );
}

// ── ESG Section ──────────────────────────────────────────────────────────────

function EsgSection({ data }: { data: PortalData }) {
  const esg = (data.sections.esg ?? {}) as Record<string, unknown>;

  if (!Object.keys(esg).length) {
    return (
      <p className="text-sm text-slate-400">
        ESG summary not included in this report share.
      </p>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {Object.entries(esg).map(([k, v]) => (
        <Row key={k} label={k.replace(/_/g, " ")} value={String(v ?? "—")} />
      ))}
    </div>
  );
}

// ── Governance Section ───────────────────────────────────────────────────────

function GovernanceSection({ data }: { data: PortalData }) {
  const gov = (data.sections.governance ?? {}) as Record<string, unknown>;

  if (!Object.keys(gov).length) {
    return (
      <p className="text-sm text-slate-400">
        Governance data not included in this report share.
      </p>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {Object.entries(gov).map(([k, v]) => (
        <Row key={k} label={k.replace(/_/g, " ")} value={String(v ?? "—")} />
      ))}
    </div>
  );
}

// ── Sustainability section ───────────────────────────────────────────────────

function SustainabilitySection({ data }: { data: PortalData }) {
  const sus = (data.sections.sustainability ?? {}) as Record<string, unknown>;

  if (!Object.keys(sus).length) {
    return (
      <p className="text-sm text-slate-400">
        Sustainability data not included in this report share.
      </p>
    );
  }

  const emissions = sus.total_emissions_tco2e as number | null;
  const kpis = sus.total_kpis as number | null;
  const objectives = sus.active_objectives as number | null;

  return (
    <div className="space-y-4">
      {emissions != null && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCard
            label="Total Emissions"
            value={`${(emissions / 1000).toFixed(1)}k tCO₂e`}
            icon={Globe}
          />
          <MetricCard
            label="Active KPIs"
            value={kpis ?? "—"}
            icon={TrendingUp}
          />
          <MetricCard
            label="Active Objectives"
            value={objectives ?? "—"}
            icon={CheckCircle2}
          />
        </div>
      )}
      <div className="divide-y divide-slate-100">
        {Object.entries(sus)
          .filter(([k]) => !["total_emissions_tco2e", "total_kpis", "active_objectives"].includes(k))
          .map(([k, v]) => (
            <Row key={k} label={k.replace(/_/g, " ")} value={String(v ?? "—")} />
          ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BoardPortalPage() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PortalData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    getBoardPortalData(token)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-5xl space-y-6">
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-4 w-48" />
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-48 rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-8">
        <div className="rounded-xl border border-red-200 bg-white p-10 text-center shadow-sm">
          <AlertTriangle className="mx-auto mb-4 h-10 w-10 text-red-400" />
          <h1 className="text-lg font-semibold text-slate-800">
            {error?.includes("expired") || error?.includes("revoked")
              ? "This link is no longer valid"
              : "Unable to load report"}
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            {error ?? "The board portal link may have expired or been revoked."}
          </p>
        </div>
      </div>
    );
  }

  const showPortfolio = !data.allowed_sections.length || data.allowed_sections.includes("portfolio");
  const showEsg = !data.allowed_sections.length || data.allowed_sections.includes("esg");
  const showGovernance = !data.allowed_sections.length || data.allowed_sections.includes("governance");
  const showSustainability = !data.allowed_sections.length || data.allowed_sections.includes("sustainability");

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white px-8 py-5">
        <div className="mx-auto flex max-w-5xl items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-slate-900 px-3 py-1.5">
                <span className="text-sm font-bold tracking-wide text-white">EIOS</span>
              </div>
              <span className="text-xs text-slate-400">Board Portal</span>
            </div>
            <h1 className="mt-3 text-xl font-bold text-slate-900">{data.title}</h1>
            <p className="mt-1 text-sm text-slate-500">
              Period: {data.period_start} → {data.period_end}
              {data.generated_at && (
                <> · Generated {new Date(data.generated_at).toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric" })}</>
              )}
            </p>
          </div>
          <ExpiryBadge expiresAt={data.expires_at} token={token} />
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-5xl space-y-6 px-8 py-8">
        {/* Executive Summary */}
        {data.executive_summary && (
          <SectionCard title="Executive Summary">
            <p className="text-sm leading-relaxed text-slate-700">
              {data.executive_summary}
            </p>
          </SectionCard>
        )}

        {/* Portfolio */}
        {showPortfolio && (
          <SectionCard title="Supplier Portfolio">
            <PortfolioSection data={data} />
          </SectionCard>
        )}

        {/* ESG */}
        {showEsg && (data.sections.esg != null) && (
          <SectionCard title="ESG Performance">
            <EsgSection data={data} />
          </SectionCard>
        )}

        {/* Governance */}
        {showGovernance && (data.sections.governance != null) && (
          <SectionCard title="Governance">
            <GovernanceSection data={data} />
          </SectionCard>
        )}

        {/* Sustainability */}
        {showSustainability && (data.sections.sustainability != null) && (
          <SectionCard title="Sustainability">
            <SustainabilitySection data={data} />
          </SectionCard>
        )}

        {/* Footer */}
        <div className="py-4 text-center text-xs text-slate-400">
          This report is confidential and intended solely for the named recipient.
          Powered by EIOS Enterprise Intelligence Operating System.
        </div>
      </main>
    </div>
  );
}
