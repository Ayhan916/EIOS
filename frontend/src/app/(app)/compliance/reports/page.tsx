"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  FileBarChart2,
  FileCode2,
  FileText,
  Scale,
  ShieldCheck,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReportSummary {
  id: string;
  organization_id: string;
  report_type: string;
  framework_code: string;
  framework_version: string;
  generated_at: string;
  generated_by: string;
  report_hash: string;
}

// ── PDF download helper ───────────────────────────────────────────────────────

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

async function downloadPdf(path: string, filename: string) {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("eios_access_token")
      : null;

  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `Download failed (${res.status})`);
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
}

// ── Report definitions ────────────────────────────────────────────────────────

const REPORTS = [
  {
    id: "csrd_gap",
    path: "/compliance/reports/csrd-gap",
    filename: "csrd-gap-report.pdf",
    titleKey: "complianceReports.csrdTitle" as const,
    descKey: "complianceReports.csrdDesc" as const,
    framework: "CSRD",
    icon: FileBarChart2,
    color: "border-emerald-200 bg-emerald-50",
    iconBg: "bg-emerald-600",
    badgeColor: "bg-emerald-100 text-emerald-800",
    bullets: [
      "Article-level gap analysis",
      "Mandatory vs. voluntary obligations",
      "Coverage ratio per disclosure area",
      "Priority remediation list",
    ],
  },
  {
    id: "esrs_readiness",
    path: "/compliance/reports/esrs-readiness",
    filename: "esrs-readiness-report.pdf",
    titleKey: "complianceReports.esrsTitle" as const,
    descKey: "complianceReports.esrsDesc" as const,
    framework: "ESRS",
    icon: ShieldCheck,
    color: "border-blue-200 bg-blue-50",
    iconBg: "bg-blue-600",
    badgeColor: "bg-blue-100 text-blue-800",
    bullets: [
      "E1–E5 Environmental standards",
      "S1–S4 Social standards",
      "G1 Governance standard",
      "Cross-cutting standards (ESRS 1 & 2)",
    ],
  },
  {
    id: "csddd_due_diligence",
    path: "/compliance/reports/csddd-due-diligence",
    filename: "csddd-due-diligence-report.pdf",
    titleKey: "complianceReports.csdddTitle" as const,
    descKey: "complianceReports.csdddDesc" as const,
    framework: "CSDdD",
    icon: FileText,
    color: "border-violet-200 bg-violet-50",
    iconBg: "bg-violet-600",
    badgeColor: "bg-violet-100 text-violet-800",
    bullets: [
      "21 rights under Annex I",
      "Supply chain due diligence steps",
      "Remediation & preventive measures",
      "Human rights risk coverage",
    ],
  },
] as const;

// ── Report type label map ─────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  csrd_gap: "CSRD Gap",
  esrs_readiness: "ESRS Readiness",
  csddd_due_diligence: "CSDdD Due Diligence",
  lksg_statement: "LkSG §10 Statement",
  lksgg_annual: "LkSG Annual Report",
};

// ── LkSG §10 Statement Generator ─────────────────────────────────────────────

const THIS_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => THIS_YEAR - i);

interface DdReportSummary {
  id: string;
  organization_id: string;
  report_type: string;
  framework: string;
  framework_version: string;
  generated_at: string;
  generated_by: string;
  report_hash: string;
  status: string;
}

function LksgStatementCard() {
  const qc = useQueryClient();
  const [year, setYear] = useState(THIS_YEAR);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<DdReportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<"pdf" | "xml" | null>(null);

  async function generate() {
    setGenerating(true);
    setError(null);
    setResult(null);
    try {
      const res = await apiClient.post("/due-diligence/reports/generate", {
        report_type: "lksg_statement",
        reporting_year: year,
      });
      setResult(res.data);
      qc.invalidateQueries({ queryKey: ["dd-reports-history"] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Generation failed. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  async function downloadFile(type: "pdf" | "xml") {
    if (!result) return;
    setDownloading(type);
    try {
      const suffix = type === "pdf" ? "download" : "download-xml";
      const ext = type;
      const path = `/due-diligence/reports/${result.id}/${suffix}`;
      const filename = `lksg-statement-${year}-${result.id.slice(0, 8)}.${ext}`;
      await downloadPdf(path, filename);
    } catch {
      setError(`${type.toUpperCase()} download failed.`);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <Card className="border-2 border-amber-200 bg-amber-50 transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-600 flex-shrink-0">
            <Scale className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-base">LkSG §10 Statement</CardTitle>
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                LkSG
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600 leading-snug">
              Annual due diligence declaration required by LkSG §10 for public disclosure.
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <ul className="space-y-1">
          {[
            "(a) Due diligence measures in place",
            "(b) Risk analysis results",
            "(c) Prioritisation decisions & justification",
            "(d) Preventive & remediation measures",
            "(e) Effectiveness review",
            "(f) Grievance mechanism report (LkSG §8)",
          ].map((b) => (
            <li key={b} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              {b}
            </li>
          ))}
        </ul>

        {/* Year selector */}
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Reporting Year</label>
          <select
            className="w-full rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm"
            value={year}
            onChange={(e) => { setYear(Number(e.target.value)); setResult(null); }}
          >
            {YEAR_OPTIONS.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {!result ? (
          <Button onClick={generate} disabled={generating} className="w-full gap-2">
            {generating ? (
              <><Spinner size="sm" />Generating statement…</>
            ) : (
              <><Download className="h-4 w-4" />Generate LkSG §10 Statement</>
            )}
          </Button>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
              <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
              Statement generated for {year}. Hash: {result.report_hash.slice(0, 10)}…
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                className="gap-1.5 text-xs"
                disabled={downloading !== null}
                onClick={() => downloadFile("pdf")}
              >
                {downloading === "pdf" ? <Spinner size="sm" /> : <Download className="h-3.5 w-3.5" />}
                Download PDF
              </Button>
              <Button
                variant="outline"
                className="gap-1.5 text-xs"
                disabled={downloading !== null}
                onClick={() => downloadFile("xml")}
              >
                {downloading === "xml" ? <Spinner size="sm" /> : <FileCode2 className="h-3.5 w-3.5" />}
                Download XML
              </Button>
            </div>
            <button
              onClick={() => setResult(null)}
              className="w-full text-center text-xs text-slate-500 hover:text-slate-700"
            >
              Generate new version
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── DD Reports History ────────────────────────────────────────────────────────

function DdReportsHistory() {
  const [downloading, setDownloading] = useState<string | null>(null);

  const { data: reports = [], isLoading } = useQuery<DdReportSummary[]>({
    queryKey: ["dd-reports-history"],
    queryFn: async () => {
      const res = await apiClient.get("/due-diligence/reports", {
        params: { framework: "LkSG", limit: 20 },
      });
      return res.data;
    },
  });

  async function dl(r: DdReportSummary, type: "pdf" | "xml") {
    setDownloading(r.id + type);
    try {
      const suffix = type === "pdf" ? "download" : "download-xml";
      const year = new Date(r.generated_at).getFullYear();
      await downloadPdf(
        `/due-diligence/reports/${r.id}/${suffix}`,
        `lksg-statement-${year}-${r.id.slice(0, 8)}.${type}`,
      );
    } catch {
      // silent
    } finally {
      setDownloading(null);
    }
  }

  if (isLoading) return <div className="py-4 text-center text-sm text-slate-400">Loading…</div>;
  if (reports.length === 0) return (
    <div className="rounded-lg border border-dashed p-8 text-center text-sm text-slate-400">
      No LkSG statements generated yet.
    </div>
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Framework</th>
            <th className="px-4 py-3">Generated</th>
            <th className="px-4 py-3">Hash</th>
            <th className="px-4 py-3 text-right">Downloads</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <Scale className="h-4 w-4 text-amber-500 flex-shrink-0" />
                  <span className="font-medium">{TYPE_LABELS[r.report_type] ?? r.report_type}</span>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                  {r.framework} {r.framework_version}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  {new Date(r.generated_at).toLocaleString()}
                </div>
              </td>
              <td className="px-4 py-3">
                <span className="font-mono text-[11px] text-slate-400">{r.report_hash.slice(0, 10)}…</span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-end gap-1.5">
                  <button
                    onClick={() => dl(r, "pdf")}
                    disabled={downloading !== null}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                  >
                    {downloading === r.id + "pdf" ? <Spinner size="sm" /> : <Download className="h-3 w-3" />}
                    PDF
                  </button>
                  {r.report_type === "lksg_statement" && (
                    <button
                      onClick={() => dl(r, "xml")}
                      disabled={downloading !== null}
                      className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50"
                    >
                      {downloading === r.id + "xml" ? <Spinner size="sm" /> : <FileCode2 className="h-3 w-3" />}
                      XML
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Generate card ─────────────────────────────────────────────────────────────

function ReportCard({ report }: { report: (typeof REPORTS)[number] }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const Icon = report.icon;

  async function generate() {
    setBusy(true);
    setDone(false);
    setError(null);
    try {
      await downloadPdf(report.path, report.filename);
      setDone(true);
      qc.invalidateQueries({ queryKey: ["compliance-reports-history"] });
      setTimeout(() => setDone(false), 3000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("complianceReports.errorFailed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className={`border-2 ${report.color} transition-shadow hover:shadow-md`}>
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${report.iconBg} flex-shrink-0`}>
            <Icon className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <CardTitle className="text-base">{t(report.titleKey)}</CardTitle>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${report.badgeColor}`}>
                {report.framework}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-600 leading-snug">{t(report.descKey)}</p>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <ul className="space-y-1">
          {report.bullets.map((b) => (
            <li key={b} className="flex items-center gap-2 text-xs text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400 flex-shrink-0" />
              {b}
            </li>
          ))}
        </ul>

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        <Button
          onClick={generate}
          disabled={busy}
          className="w-full gap-2"
          variant={done ? "outline" : "default"}
        >
          {busy ? (
            <><Spinner size="sm" />{t("complianceReports.generating")}</>
          ) : done ? (
            <><CheckCircle2 className="h-4 w-4 text-emerald-600" />{t("complianceReports.download")}</>
          ) : (
            <><Download className="h-4 w-4" />{t("complianceReports.generate")}</>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

// ── History table ─────────────────────────────────────────────────────────────

function HistoryTable({ reports }: { reports: ReportSummary[] }) {
  const { t } = useLanguage();
  const [downloading, setDownloading] = useState<string | null>(null);

  async function downloadHistorical(report: ReportSummary) {
    setDownloading(report.id);
    try {
      const label = TYPE_LABELS[report.report_type] ?? report.report_type;
      const date = new Date(report.generated_at).toISOString().split("T")[0];
      await downloadPdf(
        `/compliance/reports/${report.id}/download`,
        `${label.toLowerCase().replace(/\s+/g, "-")}-${date}.pdf`,
      );
    } catch {
      // silent — the individual download failure is acceptable
    } finally {
      setDownloading(null);
    }
  }

  if (reports.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center text-sm text-slate-400">
        {t("complianceReports.historyEmpty")}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3">{t("complianceReports.type")}</th>
            <th className="px-4 py-3">{t("complianceReports.framework")}</th>
            <th className="px-4 py-3">{t("complianceReports.generatedAt")}</th>
            <th className="px-4 py-3">{t("complianceReports.hash")}</th>
            <th className="px-4 py-3 text-right">{t("common.actions")}</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((r) => (
            <tr key={r.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <FileBarChart2 className="h-4 w-4 text-slate-400 flex-shrink-0" />
                  <span className="font-medium text-slate-800">
                    {TYPE_LABELS[r.report_type] ?? r.report_type}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                  {r.framework_code}
                </span>
              </td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Clock className="h-3.5 w-3.5 text-slate-400" />
                  {new Date(r.generated_at).toLocaleString()}
                </div>
              </td>
              <td className="px-4 py-3">
                <span className="font-mono text-[11px] text-slate-400" title={r.report_hash}>
                  {r.report_hash.slice(0, 10)}…
                </span>
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => downloadHistorical(r)}
                  disabled={downloading === r.id}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 transition-colors"
                >
                  {downloading === r.id ? (
                    <><Spinner size="sm" />{t("complianceReports.downloading")}</>
                  ) : (
                    <><Download className="h-3.5 w-3.5" />{t("complianceReports.download")}</>
                  )}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ComplianceReportsPage() {
  const { t } = useLanguage();

  const { data: history = [], isLoading } = useQuery<ReportSummary[]>({
    queryKey: ["compliance-reports-history"],
    queryFn: async () => {
      const res = await apiClient.get("/compliance/reports", { params: { limit: 50 } });
      return res.data;
    },
  });

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t("complianceReports.title")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("complianceReports.subtitle")}</p>
      </div>

      {/* Report generation cards */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {REPORTS.map((r) => (
          <ReportCard key={r.id} report={r} />
        ))}
      </div>

      {/* LkSG §10 Statement Generator */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-slate-800">LkSG §10 Annual Statement</h2>
          <p className="text-sm text-slate-500">
            Structured due diligence declaration for public disclosure — LkSG §10 Abs. 2 sections (a)–(f) + XML export for BAFA.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          <LksgStatementCard />
        </div>
      </div>

      {/* LkSG Statement History */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-slate-800">LkSG Statement History</h2>
        <DdReportsHistory />
      </div>

      {/* Other compliance report history */}
      <div className="space-y-4">
        <h2 className="text-base font-semibold text-slate-800">{t("complianceReports.history")}</h2>
        {isLoading ? (
          <div className="flex justify-center py-10">
            <Spinner size="lg" />
          </div>
        ) : (
          <HistoryTable reports={history} />
        )}
      </div>
    </div>
  );
}
