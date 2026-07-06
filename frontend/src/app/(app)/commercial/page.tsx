"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import apiClient from "@/lib/api/client";
import { formatDate, formatDateTime } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Download,
  Share2,
  Copy,
  Check,
  FileText,
  BarChart3,
} from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BenchmarkResult {
  supplier_id: string;
  supplier_name: string;
  scores: {
    overall: number | null;
    environmental: number | null;
    social: number | null;
    governance: number | null;
  };
  peer_group: { count: number; industry: string | null };
  percentile_ranks: {
    overall: number | null;
    environmental: number | null;
    social: number | null;
    governance: number | null;
  };
  performance_tier: string;
  strengths: string[];
  improvement_areas: string[];
}

interface ExecSupplier {
  id: string;
  name: string;
  industry?: string;
}

interface BoardReport {
  id: string;
  title: string;
  report_version: string;
  period_start: string;
  period_end: string;
  generated_at: string;
  executive_summary: string;
}

interface ShareLinkResult {
  token: string;
  expires_at: string;
  board_url: string;
}

// ── Shared helpers ─────────────────────────────────────────────────────────────

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1`;

const TIER_STYLES: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  "Top Quartile":     { bg: "bg-green-50 border-green-200",  text: "text-green-700",  icon: <TrendingUp className="h-4 w-4" /> },
  "Above Average":    { bg: "bg-blue-50 border-blue-200",    text: "text-blue-700",   icon: <TrendingUp className="h-4 w-4" /> },
  "Below Average":    { bg: "bg-amber-50 border-amber-200",  text: "text-amber-700",  icon: <TrendingDown className="h-4 w-4" /> },
  "Bottom Quartile":  { bg: "bg-red-50 border-red-200",      text: "text-red-700",    icon: <TrendingDown className="h-4 w-4" /> },
  "Insufficient Data":{ bg: "bg-slate-50 border-slate-200",  text: "text-slate-500",  icon: <Minus className="h-4 w-4" /> },
};

function TierBadge({ tier }: { tier: string }) {
  const s = TIER_STYLES[tier] ?? TIER_STYLES["Insufficient Data"];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${s.bg} ${s.text}`}>
      {s.icon} {tier}
    </span>
  );
}

function PercentileRing({ value, label, color }: { value: number | null; label: string; color: string }) {
  const v = value ?? 0;
  const r = 34;
  const circ = 2 * Math.PI * r;
  const dash = circ * (v / 100);
  const ringColor =
    v >= 75 ? "stroke-green-500" : v >= 50 ? "stroke-blue-500" : v >= 25 ? "stroke-amber-400" : "stroke-red-500";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative inline-flex items-center justify-center">
        <svg width={80} height={80} className="rotate-[-90deg]">
          <circle cx={40} cy={40} r={r} fill="none" stroke="#f1f5f9" strokeWidth={7} />
          <circle
            cx={40} cy={40} r={r}
            fill="none"
            className={value != null ? ringColor : "stroke-slate-200"}
            strokeWidth={7}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute text-center">
          <span className="text-base font-bold text-slate-900">{value != null ? `${v.toFixed(0)}` : "—"}</span>
          <span className="block text-[9px] text-slate-400">pct</span>
        </div>
      </div>
      <span className="text-xs font-medium text-slate-600">{label}</span>
    </div>
  );
}

// ── Benchmarking Tab ──────────────────────────────────────────────────────────

function BenchmarkTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [selectedId, setSelectedId] = useState("");
  const [search, setSearch] = useState("");

  const { data: suppliers = [] } = useQuery<ExecSupplier[]>({
    queryKey: ["exec-suppliers-names"],
    queryFn: async () => (await apiClient.get("/executive/suppliers")).data,
    staleTime: 5 * 60_000,
    enabled: !!orgId,
  });

  const { data: benchmark, isLoading, error } = useQuery<BenchmarkResult>({
    queryKey: ["commercial", "benchmark", selectedId],
    queryFn: async () => (await apiClient.get(`/suppliers/${selectedId}/benchmark`)).data,
    enabled: !!selectedId,
    staleTime: 120_000,
    retry: false,
  });

  const filtered = suppliers.filter(
    (s) => !search || s.name.toLowerCase().includes(search.toLowerCase()) || s.id.toLowerCase().includes(search.toLowerCase())
  );

  const selectedName = suppliers.find((s) => s.id === selectedId)?.name;

  return (
    <div className="space-y-6">
      {/* Supplier picker */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <Label className="text-xs text-slate-500 mb-2 block">{t("comm.selectSupplier")}</Label>
          <Input
            placeholder={t("comm.searchSupplier")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
          {search && filtered.length > 0 && (
            <div className="mt-2 max-h-48 w-full max-w-sm overflow-y-auto rounded-md border border-slate-200 bg-white shadow-sm">
              {filtered.slice(0, 10).map((s) => (
                <button
                  key={s.id}
                  className={`flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-slate-50 ${selectedId === s.id ? "bg-blue-50 text-blue-700" : "text-slate-700"}`}
                  onClick={() => { setSelectedId(s.id); setSearch(""); }}
                >
                  <span className="font-medium">{s.name}</span>
                  {s.industry && <span className="text-xs text-slate-400 ml-2">{s.industry}</span>}
                </button>
              ))}
            </div>
          )}
          {selectedId && !search && (
            <p className="mt-2 text-xs text-slate-500">
              {t("comm.viewing")}: <strong className="text-slate-700">{selectedName}</strong>
            </p>
          )}
        </CardContent>
      </Card>

      {!selectedId ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <BarChart3 className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="text-slate-500">{t("comm.selectPrompt")}</p>
          </CardContent>
        </Card>
      ) : isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : error ? (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-6 text-center text-sm text-red-700">{t("comm.benchmarkError")}</CardContent>
        </Card>
      ) : benchmark ? (
        <div className="space-y-5">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{benchmark.supplier_name}</h2>
              <p className="text-sm text-slate-500">
                {benchmark.peer_group.count} {t("comm.peers")}
                {benchmark.peer_group.industry ? ` · ${benchmark.peer_group.industry}` : ""}
              </p>
            </div>
            <TierBadge tier={benchmark.performance_tier} />
          </div>

          {/* Percentile rings */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">{t("comm.percentileRanks")}</CardTitle>
              <p className="text-xs text-slate-400">{t("comm.percentileDesc")}</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6 sm:grid-cols-4 justify-items-center">
                <PercentileRing value={benchmark.percentile_ranks.overall}       label={t("comm.overall")}       color="blue" />
                <PercentileRing value={benchmark.percentile_ranks.environmental}  label={t("comm.environmental")} color="green" />
                <PercentileRing value={benchmark.percentile_ranks.social}         label={t("comm.social")}        color="purple" />
                <PercentileRing value={benchmark.percentile_ranks.governance}     label={t("comm.governance")}    color="amber" />
              </div>
            </CardContent>
          </Card>

          {/* Raw scores */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold">{t("comm.rawScores")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {(["overall", "environmental", "social", "governance"] as const).map((dim) => {
                  const val = benchmark.scores[dim];
                  const pct = val != null ? val : null;
                  return (
                    <div key={dim} className="rounded-md bg-slate-50 p-3 text-center">
                      <p className="text-xs text-slate-400 mb-1 capitalize">{t(`comm.${dim}`)}</p>
                      <p className="text-xl font-bold text-slate-900">
                        {pct != null ? pct.toFixed(1) : "—"}
                      </p>
                      {pct != null && (
                        <div className="mt-1.5 h-1 w-full rounded-full bg-slate-200">
                          <div
                            className={`h-1 rounded-full ${pct >= 70 ? "bg-green-500" : pct >= 50 ? "bg-blue-400" : pct >= 30 ? "bg-amber-400" : "bg-red-500"}`}
                            style={{ width: `${Math.min(100, pct)}%` }}
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Strengths & improvement areas */}
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="border-green-100">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-green-700 flex items-center gap-1.5">
                  <TrendingUp className="h-4 w-4" /> {t("comm.strengths")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {benchmark.strengths.length === 0 ? (
                  <p className="text-xs text-slate-400">{t("comm.none")}</p>
                ) : (
                  <ul className="space-y-1.5">
                    {benchmark.strengths.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-green-500 shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card className="border-amber-100">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold text-amber-700 flex items-center gap-1.5">
                  <TrendingDown className="h-4 w-4" /> {t("comm.improvements")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {benchmark.improvement_areas.length === 0 ? (
                  <p className="text-xs text-slate-400">{t("comm.none")}</p>
                ) : (
                  <ul className="space-y-1.5">
                    {benchmark.improvement_areas.map((s, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                        <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ── Board Portal Tab ──────────────────────────────────────────────────────────

const ALLOWED_SECTIONS_OPTIONS = ["portfolio", "esg", "governance", "risk", "sustainability", "financial"] as const;

function BoardPortalTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [shareLinks, setShareLinks] = useState<Record<string, ShareLinkResult | null>>({});
  const [shareForm, setShareForm] = useState<Record<string, { hours: string; email: string; sections: string[] }>>({});
  const [pptxLoading, setPptxLoading] = useState<Record<string, boolean>>({});
  const [copied, setCopied] = useState<string | null>(null);
  const [shareError, setShareError] = useState<Record<string, string>>({});

  const { data: reports, isLoading } = useQuery<BoardReport[]>({
    queryKey: ["comm", "board-reports", orgId],
    queryFn: async () => (await apiClient.get("/executive/reports?limit=20")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const createLink = useMutation({
    mutationFn: async ({ reportId, hours, email, sections }: { reportId: string; hours: number; email: string; sections: string[] }) => {
      const body: Record<string, unknown> = { expires_in_hours: hours };
      if (email) body.shared_with_email = email;
      if (sections.length > 0) body.allowed_sections = sections;
      const res = await apiClient.post(`/executive/reports/${reportId}/share-link`, body);
      return { reportId, data: res.data as ShareLinkResult };
    },
    onSuccess: ({ reportId, data }) => {
      setShareLinks((prev) => ({ ...prev, [reportId]: data }));
      setShareError((prev) => ({ ...prev, [reportId]: "" }));
    },
    onError: (e: Error, { reportId }) => {
      setShareError((prev) => ({ ...prev, [reportId]: e.message }));
    },
  });

  async function handlePptxDownload(report: BoardReport) {
    setPptxLoading((prev) => ({ ...prev, [report.id]: true }));
    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
      const res = await fetch(`${API_BASE}/executive/reports/${report.id}/export?format=pptx`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report.title.replace(/\s+/g, "_").toLowerCase()}.pptx`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch {
      // silent
    } finally {
      setPptxLoading((prev) => ({ ...prev, [report.id]: false }));
    }
  }

  async function copyLink(reportId: string) {
    const link = shareLinks[reportId];
    if (!link) return;
    const url = `${window.location.origin}${link.board_url}`;
    await navigator.clipboard.writeText(url).catch(() => {});
    setCopied(reportId);
    setTimeout(() => setCopied(null), 2500);
  }

  function getForm(reportId: string) {
    return shareForm[reportId] ?? { hours: "168", email: "", sections: [] };
  }

  function setForm(reportId: string, partial: Partial<{ hours: string; email: string; sections: string[] }>) {
    setShareForm((prev) => ({ ...prev, [reportId]: { ...getForm(reportId), ...partial } }));
  }

  function toggleSection(reportId: string, section: string) {
    const current = getForm(reportId).sections;
    const next = current.includes(section) ? current.filter((s) => s !== section) : [...current, section];
    setForm(reportId, { sections: next });
  }

  return (
    <div className="space-y-4">
      {isLoading ? (
        <div className="flex h-40 items-center justify-center"><Spinner /></div>
      ) : !reports || reports.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <FileText className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="text-slate-500">{t("comm.noReports")}</p>
          </CardContent>
        </Card>
      ) : (
        reports.map((report) => {
          const form = getForm(report.id);
          const link = shareLinks[report.id];

          return (
            <Card key={report.id}>
              <CardContent className="pt-5 space-y-4">
                {/* Report header */}
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900">{report.title}</h3>
                    <p className="text-xs text-slate-400">
                      v{report.report_version} · {formatDate(report.period_start)} – {formatDate(report.period_end)}
                    </p>
                    {report.executive_summary && (
                      <p className="text-xs text-slate-500 mt-1 line-clamp-2">{report.executive_summary}</p>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1.5 h-8 text-xs shrink-0"
                    onClick={() => handlePptxDownload(report)}
                    disabled={pptxLoading[report.id]}
                  >
                    {pptxLoading[report.id] ? <Spinner className="h-3 w-3" /> : <Download className="h-3.5 w-3.5" />}
                    PPTX
                  </Button>
                </div>

                {/* Share link form */}
                <div className="rounded-md border border-slate-100 bg-slate-50 p-4 space-y-3">
                  <p className="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
                    <Share2 className="h-3.5 w-3.5" /> {t("comm.createShareLink")}
                  </p>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <Label className="text-xs">{t("comm.expiresHours")}</Label>
                      <select
                        className="mt-1 h-8 w-full rounded-md border border-slate-200 bg-white px-2 text-sm"
                        value={form.hours}
                        onChange={(e) => setForm(report.id, { hours: e.target.value })}
                      >
                        {[24, 48, 72, 168, 336, 720].map((h) => (
                          <option key={h} value={String(h)}>{h}h ({h >= 168 ? `${Math.round(h / 24)}d` : `${h}h`})</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label className="text-xs">{t("comm.shareWithEmail")}</Label>
                      <Input
                        type="email"
                        className="mt-1 h-8 text-sm"
                        value={form.email}
                        onChange={(e) => setForm(report.id, { email: e.target.value })}
                        placeholder="board@company.com"
                      />
                    </div>
                  </div>

                  <div>
                    <Label className="text-xs mb-1.5 block">{t("comm.allowedSections")} ({t("comm.allIfNone")})</Label>
                    <div className="flex flex-wrap gap-1.5">
                      {ALLOWED_SECTIONS_OPTIONS.map((sec) => (
                        <button
                          key={sec}
                          onClick={() => toggleSection(report.id, sec)}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors capitalize ${
                            form.sections.includes(sec)
                              ? "bg-blue-600 text-white border-blue-600"
                              : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
                          }`}
                        >
                          {sec}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      className="gap-1.5 h-8 text-xs"
                      disabled={createLink.isPending}
                      onClick={() =>
                        createLink.mutate({
                          reportId: report.id,
                          hours: parseInt(form.hours, 10),
                          email: form.email,
                          sections: form.sections,
                        })
                      }
                    >
                      {createLink.isPending ? <Spinner className="h-3 w-3" /> : <Share2 className="h-3.5 w-3.5" />}
                      {t("comm.generate")}
                    </Button>
                    {shareError[report.id] && (
                      <p className="text-xs text-red-600">{shareError[report.id]}</p>
                    )}
                  </div>

                  {/* Share link result */}
                  {link && (
                    <div className="rounded-md border border-green-200 bg-green-50 p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <code className="flex-1 truncate rounded bg-white px-2 py-1 text-xs font-mono text-slate-700 border border-slate-200">
                          {typeof window !== "undefined" ? window.location.origin : ""}{link.board_url}
                        </code>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs gap-1 shrink-0"
                          onClick={() => copyLink(report.id)}
                        >
                          {copied === report.id ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
                          {copied === report.id ? t("comm.copied") : t("comm.copy")}
                        </Button>
                      </div>
                      <p className="text-xs text-slate-500">
                        {t("comm.expiresAt")}: {formatDateTime(link.expires_at)}
                      </p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CommercialPage() {
  const { t } = useLanguage();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("comm.pageTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("comm.pageSubtitle")}</p>
      </div>

      <Tabs defaultValue="benchmark">
        <TabsList>
          <TabsTrigger value="benchmark">{t("comm.tabBenchmark")}</TabsTrigger>
          <TabsTrigger value="board">{t("comm.tabBoard")}</TabsTrigger>
        </TabsList>
        <TabsContent value="benchmark" className="mt-6"><BenchmarkTab /></TabsContent>
        <TabsContent value="board" className="mt-6"><BoardPortalTab /></TabsContent>
      </Tabs>
    </div>
  );
}
