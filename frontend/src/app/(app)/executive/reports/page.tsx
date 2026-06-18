"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Download, Trash2, AlertCircle } from "lucide-react";
import {
  generateBoardReport,
  listBoardReports,
  deleteBoardReport,
  boardReportPdfUrl,
} from "@/lib/api/executive";
import type { BoardReportRequest } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

// ── Generate form ─────────────────────────────────────────────────────────────

function GenerateForm({ onSuccess }: { onSuccess: () => void }) {
  const [title, setTitle] = useState("Board Report");
  const [periodStart, setPeriodStart] = useState(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 1);
    d.setDate(1);
    return d.toISOString().split("T")[0];
  });
  const [periodEnd, setPeriodEnd] = useState(() => {
    const d = new Date();
    d.setDate(0);
    return d.toISOString().split("T")[0];
  });
  const [kpiDays, setKpiDays] = useState<30 | 90 | 365>(90);
  const [error, setError] = useState<string | null>(null);

  const { mutate, isPending } = useMutation({
    mutationFn: (body: BoardReportRequest) => generateBoardReport(body),
    onSuccess: () => {
      setError(null);
      onSuccess();
    },
    onError: (e: Error) => setError(e.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutate({ title, period_start: periodStart, period_end: periodEnd, kpi_period_days: kpiDays });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Generate New Board Report</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title">Report Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Q1 2026 Board Report"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="period-start">Period Start</Label>
              <Input
                id="period-start"
                type="date"
                value={periodStart}
                onChange={(e) => setPeriodStart(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="period-end">Period End</Label>
              <Input
                id="period-end"
                type="date"
                value={periodEnd}
                onChange={(e) => setPeriodEnd(e.target.value)}
                required
              />
            </div>
          </div>
          <div>
            <Label>KPI Trend Window</Label>
            <div className="mt-1 flex gap-2">
              {([30, 90, 365] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setKpiDays(d)}
                  className={`rounded px-3 py-1.5 text-sm font-medium transition-colors ${
                    kpiDays === d
                      ? "bg-slate-800 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {d === 365 ? "1 Year" : `${d} Days`}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <Button type="submit" disabled={isPending} className="w-full">
            {isPending ? (
              <span className="flex items-center gap-2">
                <Spinner className="h-4 w-4" /> Generating…
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Plus className="h-4 w-4" /> Generate Report
              </span>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Report list ───────────────────────────────────────────────────────────────

function ReportList() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const { data: reports, isLoading } = useQuery({
    queryKey: ["executive-reports"],
    queryFn: () => listBoardReports(50),
  });

  const { mutate: doDelete, isPending: deleting } = useMutation({
    mutationFn: deleteBoardReport,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["executive-reports"] }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-10">
        <Spinner />
      </div>
    );
  }

  if (!reports || reports.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          No board reports generated yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {reports.map((r) => (
        <Card key={r.id}>
          <CardContent className="flex items-start justify-between pt-4">
            <div className="flex gap-3">
              <FileText className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" />
              <div>
                <p className="font-medium">{r.title}</p>
                <p className="text-xs text-muted-foreground">
                  {r.period_start} → {r.period_end} · v{r.report_version} ·
                  Generated{" "}
                  {new Date(r.generated_at).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </p>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                  {r.executive_summary}
                </p>
              </div>
            </div>
            <div className="ml-4 flex shrink-0 gap-2">
              <a
                href={boardReportPdfUrl(r.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
              >
                <Download className="h-3.5 w-3.5" /> PDF
              </a>
              {isAdmin && (
                <button
                  onClick={() => doDelete(r.id)}
                  disabled={deleting}
                  className="inline-flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BoardReportsPage() {
  const qc = useQueryClient();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold">Board Reports</h1>
        <p className="text-sm text-muted-foreground">
          Generate immutable, auditable board-level ESG reports. Each report
          captures a full portfolio snapshot at generation time.
        </p>
      </div>

      <GenerateForm
        onSuccess={() =>
          qc.invalidateQueries({ queryKey: ["executive-reports"] })
        }
      />
      <ReportList />
    </div>
  );
}
