"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Download, Trash2, AlertCircle, Share2, Check, Loader2 } from "lucide-react";
import {
  generateBoardReport,
  listBoardReports,
  deleteBoardReport,
  boardReportPdfUrl,
  createShareLink,
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

  // #126 Customizable slide selection
  const SLIDES = [
    { key: "executive_summary",  label: "Executive Summary" },
    { key: "esg_health",         label: "ESG Health Score" },
    { key: "risk_heatmap",       label: "Risk Heatmap" },
    { key: "supplier_portfolio", label: "Supplier Portfolio" },
    { key: "compliance_status",  label: "Compliance Status" },
    { key: "sustainability",     label: "Sustainability KPIs" },
    { key: "financial_esg",      label: "Financial ESG" },
    { key: "pending_decisions",  label: "Pending Decisions" },
  ];
  const [selectedSlides, setSelectedSlides] = useState<Set<string>>(
    new Set(SLIDES.map((s) => s.key))
  );
  function toggleSlide(key: string) {
    setSelectedSlides((prev) => {
      const next = new Set(prev);
      if (next.has(key)) { if (next.size > 1) next.delete(key); }
      else next.add(key);
      return next;
    });
  }

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

          {/* #126 Slide selection */}
          <div>
            <p className="text-sm font-medium mb-2">Slides to include</p>
            <div className="grid grid-cols-2 gap-1.5">
              {SLIDES.map((s) => {
                const checked = selectedSlides.has(s.key);
                return (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => toggleSlide(s.key)}
                    className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-xs font-medium transition-colors ${
                      checked
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-border text-muted-foreground hover:bg-muted/50"
                    }`}
                  >
                    <span className={`flex h-3.5 w-3.5 flex-shrink-0 items-center justify-center rounded border ${checked ? "border-primary bg-primary" : "border-slate-300"}`}>
                      {checked && <span className="block h-1.5 w-1.5 rounded-sm bg-white" />}
                    </span>
                    {s.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-[10px] text-muted-foreground">{selectedSlides.size} of {SLIDES.length} slides selected</p>
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

// ── Share link button ─────────────────────────────────────────────────────────

function ShareLinkButton({ reportId }: { reportId: string }) {
  const [sharing, setSharing] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleShare() {
    setSharing(true);
    try {
      const res = await createShareLink(reportId, { expires_in_hours: 168 });
      const url = `${window.location.origin}${res.board_url}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // clipboard fallback: not critical
    } finally {
      setSharing(false);
    }
  }

  return (
    <button
      onClick={handleShare}
      disabled={sharing}
      className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
      title="Share with board (copies portal link)"
    >
      {sharing ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <Share2 className="h-3.5 w-3.5" />
      )}
      {copied ? "Copied!" : "Share"}
    </button>
  );
}

// ── PPTX download button ──────────────────────────────────────────────────────

function PptxButton({ reportId, title }: { reportId: string; title: string }) {
  const [busy, setBusy] = useState(false);

  async function handleDownload() {
    setBusy(true);
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
      const res = await fetch(`/api/v1/commercial/executive/reports/${reportId}/pptx`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_").toLowerCase()}.pptx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent — PPTX endpoint may require commercial tier
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={handleDownload}
      disabled={busy}
      className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
      title="Download as PowerPoint"
    >
      {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
      PPTX
    </button>
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
            <div className="ml-4 flex shrink-0 gap-2 flex-wrap">
              <PptxButton reportId={r.id} title={r.title} />
              <a
                href={boardReportPdfUrl(r.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
              >
                <Download className="h-3.5 w-3.5" /> PDF
              </a>
              <ShareLinkButton reportId={r.id} />
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
