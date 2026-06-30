"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus } from "lucide-react";
import { listAssuranceReports, generateAssuranceReport } from "@/lib/api/ai-governance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

function statusColor(s: string) {
  const m: Record<string, string> = {
    COMPLIANT:           "bg-emerald-100 text-emerald-800",
    PARTIALLY_COMPLIANT: "bg-amber-100 text-amber-800",
    NON_COMPLIANT:       "bg-red-100 text-red-800",
    NOT_ASSESSED:        "bg-slate-100 text-slate-600",
  };
  return m[s] ?? "bg-slate-100 text-slate-600";
}

export default function AssuranceReportsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "",
    period_start: "",
    period_end: "",
  });

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["ai-assurance-reports", ORG_ID],
    queryFn: () => listAssuranceReports(ORG_ID),
    retry: false,
  });

  const generate = useMutation({
    mutationFn: () =>
      generateAssuranceReport(ORG_ID, {
        title: form.title,
        period_start: new Date(form.period_start).toISOString(),
        period_end: new Date(form.period_end).toISOString(),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-assurance-reports", ORG_ID] });
      setShowForm(false);
      setForm({ title: "", period_start: "", period_end: "" });
    },
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.reportsTitle")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("aiGov.reportsSubtitle")}
          </p>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="mr-1 h-4 w-4" /> {t("reports.generate")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("reports.newReport")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("common.title")}</label>
                <input
                  className="w-full rounded border border-input px-3 py-2 text-sm"
                  placeholder="Q2 2026 AI Assurance"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Period Start</label>
                <input
                  type="date"
                  className="w-full rounded border border-input px-3 py-2 text-sm"
                  value={form.period_start}
                  onChange={(e) => setForm((f) => ({ ...f, period_start: e.target.value }))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Period End</label>
                <input
                  type="date"
                  className="w-full rounded border border-input px-3 py-2 text-sm"
                  value={form.period_end}
                  onChange={(e) => setForm((f) => ({ ...f, period_end: e.target.value }))}
                />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                onClick={() => generate.mutate()}
                disabled={!form.title || !form.period_start || !form.period_end || generate.isPending}
              >
                {generate.isPending ? "Generating…" : t("reports.generate")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>
                {t("common.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {reports.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <FileText className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("reports.noReports")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <Card key={r.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold">{r.title}</p>
                      <Badge className={statusColor(r.overall_status)}>
                        {r.overall_status.replace("_", " ")}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {new Date(r.report_period_start).toLocaleDateString()} –{" "}
                      {new Date(r.report_period_end).toLocaleDateString()}
                    </p>
                    <div className="flex gap-4 text-xs text-muted-foreground pt-1">
                      <span>{r.model_count} models</span>
                      <span>{r.use_case_count} use cases</span>
                      <span>{r.control_count} controls</span>
                      <span>{r.incident_count} incidents</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
