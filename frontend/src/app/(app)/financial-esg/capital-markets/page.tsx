"use client";

import { useQuery } from "@tanstack/react-query";
import {
  listCapitalMarketsAssessments,
  listDisclosurePackages,
} from "@/lib/api/financial-esg";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

const READINESS_STYLE: Record<string, { bar: string; label: string }> = {
  READY: { bar: "bg-green-500", label: "text-green-700 bg-green-100" },
  PARTIAL: { bar: "bg-amber-400", label: "text-amber-700 bg-amber-100" },
  NOT_READY: { bar: "bg-red-500", label: "text-red-700 bg-red-100" },
};

function ReadinessRow({ label, value }: { label: string; value: string }) {
  const style = READINESS_STYLE[value] ?? { bar: "bg-slate-300", label: "bg-muted text-muted-foreground" };
  const pct = value === "READY" ? 100 : value === "PARTIAL" ? 50 : 10;
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${style.label}`}>{value}</span>
      </div>
      <div className="mt-1 h-2 rounded-full bg-muted">
        <div className={`h-2 rounded-full ${style.bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CapitalMarketsPage() {
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: assessments, isLoading: l1 } = useQuery({
    queryKey: ["fin-esg", "readiness", orgId],
    queryFn: () => listCapitalMarketsAssessments(orgId),
  });
  const { data: packages, isLoading: l2 } = useQuery({
    queryKey: ["fin-esg", "disclosure-packages", orgId],
    queryFn: () => listDisclosurePackages(orgId),
  });

  if (l1 || l2) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const latest = [...(assessments ?? [])].sort(
    (a, b) => new Date(b.assessed_at).getTime() - new Date(a.assessed_at).getTime()
  )[0];

  const finalizedPkgs = (packages ?? []).filter((p) => p.is_final).length;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Capital Markets Readiness</h1>
        <p className="text-muted-foreground">
          Readiness assessments and investor disclosure packages
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Overall Readiness</p>
            <p
              className={`mt-1 text-3xl font-bold ${
                latest?.overall_readiness === "READY"
                  ? "text-green-600"
                  : latest?.overall_readiness === "PARTIAL"
                  ? "text-amber-600"
                  : "text-red-600"
              }`}
            >
              {latest?.overall_readiness ?? "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Assessments</p>
            <p className="mt-1 text-3xl font-bold">{(assessments ?? []).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Finalized Disclosures</p>
            <p className="mt-1 text-3xl font-bold">{finalizedPkgs}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              of {(packages ?? []).length} total
            </p>
          </CardContent>
        </Card>
      </div>

      {latest && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Latest Assessment —{" "}
              {new Date(latest.assessed_at).toLocaleDateString()}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <ReadinessRow label="Disclosure Readiness" value={latest.disclosure_readiness} />
              <ReadinessRow label="Assurance Readiness" value={latest.assurance_readiness} />
              <ReadinessRow label="Taxonomy Readiness" value={latest.taxonomy_readiness} />
              <ReadinessRow label="KPI Readiness" value={latest.kpi_readiness} />
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Investor Disclosure Packages</CardTitle>
        </CardHeader>
        <CardContent>
          {(packages ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">No disclosure packages</p>
          ) : (
            <div className="space-y-2">
              {(packages ?? []).map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between rounded border px-3 py-3"
                >
                  <div>
                    <p className="text-sm font-medium">{p.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(p.period_start).toLocaleDateString()} –{" "}
                      {new Date(p.period_end).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      p.is_final
                        ? "bg-green-100 text-green-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {p.is_final ? "FINALIZED" : "DRAFT"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
