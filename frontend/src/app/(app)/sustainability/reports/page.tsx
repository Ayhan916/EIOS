"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Lock, FileText, Send } from "lucide-react";
import apiClient from "@/lib/api/client";
import {
  listReports,
  finalizeReport,
  type SustainabilityReport,
} from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

function ragColor(s: string) {
  switch (s) {
    case "GREEN": return "bg-emerald-100 text-emerald-800";
    case "AMBER": return "bg-amber-100 text-amber-800";
    case "RED":   return "bg-red-100 text-red-800";
    default:      return "bg-slate-100 text-slate-600";
  }
}

function ReportCard({ report }: { report: SustainabilityReport }) {
  const qc = useQueryClient();
  const finalize = useMutation({
    mutationFn: () => finalizeReport(ORG_ID, report.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports", ORG_ID] }),
  });

  const kpiSummary = report.kpi_summary as Record<string, unknown>;
  const emissionsSummary = report.emissions_summary as Record<string, unknown>;
  const objStatus = report.objective_status as Record<string, unknown>;

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold">{report.title}</p>
          <p className="text-xs text-muted-foreground">
            {new Date(report.period_start).toLocaleDateString()} –{" "}
            {new Date(report.period_end).toLocaleDateString()} · {report.report_type}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${ragColor(report.overall_status)}`}>
            {report.overall_status}
          </span>
          {report.is_final && (
            <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
              <Lock className="h-3 w-3" /> Finalized
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        {kpiSummary.total_active_kpis != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">Active KPIs</p>
            <p className="font-bold">{String(kpiSummary.total_active_kpis)}</p>
          </div>
        )}
        {emissionsSummary.total_emissions != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">Total Emissions</p>
            <p className="font-bold">{Number(emissionsSummary.total_emissions).toLocaleString()} tCO₂e</p>
          </div>
        )}
        {(objStatus.completion_rate_pct as number) != null && (
          <div className="rounded bg-muted p-2">
            <p className="text-muted-foreground">Obj. Completion</p>
            <p className="font-bold">{Number(objStatus.completion_rate_pct).toFixed(1)}%</p>
          </div>
        )}
      </div>

      {!report.is_final && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => finalize.mutate()}
          disabled={finalize.isPending}
        >
          <Lock className="mr-1 h-3 w-3" />
          {finalize.isPending ? "Finalizing…" : "Finalize (Immutable)"}
        </Button>
      )}
      {report.is_final && report.finalized_at && (
        <p className="text-xs text-muted-foreground">
          Finalized {new Date(report.finalized_at).toLocaleDateString()} · Read-only
        </p>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [sendingNow, setSendingNow] = useState(false);
  const [sentNow, setSentNow] = useState(false);

  const { data: reports, isLoading } = useQuery({
    queryKey: ["reports", ORG_ID],
    queryFn: () => listReports(ORG_ID),
  });

  const finalized = reports?.filter((r) => r.is_final).length ?? 0;
  const draft = (reports?.length ?? 0) - finalized;

  async function sendQuarterlyNow() {
    setSendingNow(true);
    try {
      const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
      await apiClient.post("/api/v1/automations/trigger", {
        rule_id: "quarterly_sustainability",
        entity_type: "org",
        entity_id: ORG_ID,
        payload: {
          recipients: stored?.quarterly_sustainability?.config?.recipients ?? "",
          include_charts: stored?.quarterly_sustainability?.config?.include_charts ?? true,
          triggered_manually: true,
        },
      });
      setSentNow(true);
      setTimeout(() => setSentNow(false), 3000);
    } catch { /* silent */ }
    finally { setSendingNow(false); }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Sustainability Reports</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Immutable performance snapshots once finalized. Supports CSRD, ISSB, and full ESG reporting.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
          onClick={sendQuarterlyNow}
          disabled={sendingNow}
        >
          <Send className="h-3.5 w-3.5" />
          {sentNow ? "Sent!" : sendingNow ? "Sending…" : "Send quarterly report now"}
        </Button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Reports</p>
            <p className="text-2xl font-bold">{reports?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Draft</p>
            <p className="text-2xl font-bold text-amber-600">{draft}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Finalized</p>
            <p className="text-2xl font-bold text-emerald-600">{finalized}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Reports{reports ? ` (${reports.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {reports?.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No reports yet. Generate a sustainability report via the API.
            </p>
          )}
          <div className="space-y-3">
            {reports?.map((r) => <ReportCard key={r.id} report={r} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
