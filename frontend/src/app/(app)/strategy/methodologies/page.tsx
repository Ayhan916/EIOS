"use client";

import { useQuery } from "@tanstack/react-query";
import { listMethodologies } from "@/lib/api/strategy";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  APPROVED: "bg-green-100 text-green-700",
  DEPRECATED: "bg-red-100 text-red-600",
};

export default function StrategyMethodologiesPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  const { data: methodologies, isLoading } = useQuery({
    queryKey: ["strategy", "methodologies", orgId],
    queryFn: () => listMethodologies(orgId),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const approved = (methodologies ?? []).filter((m) => m.approval_status === "APPROVED").length;
  const draft = (methodologies ?? []).filter((m) => m.approval_status === "DRAFT").length;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Strategy Methodology Registry</h1>
        <p className="text-muted-foreground">
          Versioned, auditable methodology records for deterministic forecasts and pathways
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("common.total")}</p>
            <p className="mt-1 text-3xl font-bold">{(methodologies ?? []).length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Approved</p>
            <p className="mt-1 text-3xl font-bold text-green-600">{approved}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Draft</p>
            <p className="mt-1 text-3xl font-bold text-slate-500">{draft}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Registered Methodologies</CardTitle>
        </CardHeader>
        <CardContent>
          {(methodologies ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("strategy.noMethodologies")}
            </p>
          ) : (
            <div className="space-y-3">
              {(methodologies ?? []).map((m) => (
                <div key={m.id} className="rounded border px-4 py-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium">{m.methodology_name}</p>
                      <p className="text-xs text-muted-foreground">
                        v{m.methodology_version}
                        {m.applicable_to &&
                          Array.isArray((m.applicable_to as { types?: string[] }).types) &&
                          (m.applicable_to as { types: string[] }).types.length > 0 &&
                          ` · Applies to: ${(m.applicable_to as { types: string[] }).types.join(", ")}`}
                      </p>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        STATUS_COLORS[m.approval_status] ?? "bg-muted text-muted-foreground"
                      }`}
                    >
                      {m.approval_status}
                    </span>
                  </div>
                  {m.formula_description && (
                    <p className="mt-2 text-sm text-muted-foreground">{m.formula_description}</p>
                  )}
                  {m.approval_status === "APPROVED" && m.approved_by && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      Approved by {m.approved_by}
                      {m.approved_at && ` on ${new Date(m.approved_at).toLocaleDateString()}`}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
