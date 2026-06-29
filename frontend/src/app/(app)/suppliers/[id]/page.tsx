"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Globe,
  Briefcase,
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  ShieldAlert,
  BarChart3,
  Edit2,
  Archive,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Target,
  Users,
} from "lucide-react";
import {
  getSupplier,
  getSupplierRiskProfile,
  listSupplierAssessments,
  updateSupplier,
  archiveSupplier,
} from "@/lib/api/suppliers";
import {
  getSupplierIntelligence,
  recalculateSupplierScore,
  getSupplierScoreHistory,
  getSupplierBenchmark,
  getSupplierHeatmap,
} from "@/lib/api/supplier-scores";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierTier, SupplierStatus, SupplierUpdate } from "@/types/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function tierBadge(tier: string) {
  const colors: Record<string, string> = {
    "Tier 1": "bg-blue-100 text-blue-800",
    "Tier 2": "bg-purple-100 text-purple-800",
    "Tier 3": "bg-slate-100 text-slate-700",
    Other: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${colors[tier] ?? "bg-gray-100"}`}>
      {tier}
    </span>
  );
}

function statusBadge(s: string) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${s === "Active" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
      {s}
    </span>
  );
}

function severityColor(sev: string) {
  const m: Record<string, string> = {
    Critical: "text-red-600",
    High: "text-orange-500",
    Medium: "text-amber-500",
    Low: "text-green-600",
  };
  return m[sev] ?? "text-muted-foreground";
}

function riskBandColor(band: string) {
  const m: Record<string, string> = {
    Critical: "text-red-600 bg-red-50",
    High: "text-orange-600 bg-orange-50",
    Moderate: "text-amber-600 bg-amber-50",
    Low: "text-emerald-600 bg-emerald-50",
  };
  return m[band] ?? "text-muted-foreground bg-muted";
}

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <svg viewBox="0 0 88 88" className="h-24 w-24 -rotate-90">
          <circle cx="44" cy="44" r={r} fill="none" strokeWidth="8" className="stroke-muted" />
          <circle
            cx="44" cy="44" r={r} fill="none" strokeWidth="8"
            strokeDasharray={`${filled} ${circ}`}
            className={`transition-all ${color}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute text-xl font-bold tabular-nums">{score.toFixed(0)}</span>
      </div>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function TrendBadge({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "Improving") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
        <TrendingUp className="h-3 w-3" /> Improving {delta > 0 ? `+${delta}` : ""}
      </span>
    );
  }
  if (trend === "Deteriorating") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
        <TrendingDown className="h-3 w-3" /> Deteriorating {delta}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
      <Minus className="h-3 w-3" /> Stable
    </span>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = ["Overview", "Assessments", "Risk Profile", "Intelligence"] as const;
type Tab = typeof TABS[number];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("Overview");
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<SupplierUpdate>({});
  const [editError, setEditError] = useState<string | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [intelligenceSubTab, setIntelligenceSubTab] = useState<"score" | "history" | "benchmark" | "heatmap">("score");

  const { data: supplier, isLoading } = useQuery({
    queryKey: ["supplier", id],
    queryFn: () => getSupplier(id),
    enabled: !!id,
  });

  const { data: profile } = useQuery({
    queryKey: ["supplier-risk-profile", id],
    queryFn: () => getSupplierRiskProfile(id),
    enabled: !!id && tab === "Risk Profile",
  });

  const { data: assessments, isLoading: assessmentsLoading } = useQuery({
    queryKey: ["supplier-assessments", id],
    queryFn: () => listSupplierAssessments(id, { page: 1, page_size: 20 }),
    enabled: !!id && tab === "Assessments",
  });

  const { data: intelligence, isLoading: intelligenceLoading } = useQuery({
    queryKey: ["supplier-intelligence", id],
    queryFn: () => getSupplierIntelligence(id),
    enabled: !!id && tab === "Intelligence",
  });

  const { data: history } = useQuery({
    queryKey: ["supplier-intelligence-history", id],
    queryFn: () => getSupplierScoreHistory(id, 12),
    enabled: !!id && tab === "Intelligence" && intelligenceSubTab === "history",
  });

  const { data: benchmark } = useQuery({
    queryKey: ["supplier-benchmark", id],
    queryFn: () => getSupplierBenchmark(id),
    enabled: !!id && tab === "Intelligence" && intelligenceSubTab === "benchmark",
  });

  const { data: heatmap } = useQuery({
    queryKey: ["supplier-heatmap", id],
    queryFn: () => getSupplierHeatmap(id),
    enabled: !!id && tab === "Intelligence" && intelligenceSubTab === "heatmap",
  });

  const updateMutation = useMutation({
    mutationFn: (body: SupplierUpdate) => updateSupplier(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier", id] });
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setEditing(false);
      setEditError(null);
    },
    onError: (err: unknown) => {
      setEditError(err instanceof Error ? err.message : "Update failed");
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveSupplier(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      router.push("/suppliers");
    },
  });

  const recalcMutation = useMutation({
    mutationFn: () => recalculateSupplierScore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-intelligence", id] });
      queryClient.invalidateQueries({ queryKey: ["supplier-intelligence-history", id] });
      queryClient.invalidateQueries({ queryKey: ["supplier-benchmark", id] });
    },
  });

  if (isLoading) {
    return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  }
  if (!supplier) {
    return (
      <div className="flex flex-col items-center gap-4 py-20 text-center">
        <ShieldAlert className="h-12 w-12 text-muted-foreground/40" />
        <p className="text-muted-foreground">Supplier not found.</p>
        <Link href="/suppliers"><Button variant="outline">Back to Suppliers</Button></Link>
      </div>
    );
  }

  function startEdit() {
    setEditForm({
      name: supplier!.name,
      legal_name: supplier!.legal_name,
      country: supplier!.country,
      industry: supplier!.industry,
      nace_code: supplier!.nace_code,
      website: supplier!.website,
      supplier_tier: supplier!.supplier_tier,
      notes: supplier!.notes,
    });
    setEditing(true);
  }

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href="/suppliers"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Suppliers
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
              <Briefcase className="h-5 w-5 text-blue-700" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{supplier.name}</h1>
              {supplier.legal_name && supplier.legal_name !== supplier.name && (
                <p className="text-sm text-muted-foreground">{supplier.legal_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {tierBadge(supplier.supplier_tier)}
            {statusBadge(supplier.supplier_status)}
            <Button variant="outline" size="sm" onClick={startEdit} className="gap-1.5">
              <Edit2 className="h-3.5 w-3.5" /> Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmArchive(true)}
              className="gap-1.5 text-red-600 hover:text-red-700"
            >
              <Archive className="h-3.5 w-3.5" /> Archive
            </Button>
          </div>
        </div>
      </div>

      {/* Meta strip */}
      <div className="flex flex-wrap items-center gap-6 text-sm text-muted-foreground">
        {supplier.country && (
          <span className="flex items-center gap-1.5">
            <Globe className="h-4 w-4" /> {supplier.country}
          </span>
        )}
        {supplier.industry && (
          <span className="flex items-center gap-1.5">
            <BarChart3 className="h-4 w-4" /> {supplier.industry}
          </span>
        )}
        {supplier.nace_code && (
          <span className="font-mono text-xs bg-muted px-2 py-1 rounded">{supplier.nace_code}</span>
        )}
        {supplier.website && (
          <a
            href={supplier.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Website
          </a>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-6">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`pb-3 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Overview Tab ──────────────────────────────────────────────────── */}
      {tab === "Overview" && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="text-base">Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Country</p>
                  <p className="font-medium">{supplier.country || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Industry</p>
                  <p className="font-medium">{supplier.industry || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">NACE Code</p>
                  <p className="font-mono font-medium">{supplier.nace_code || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Tier</p>
                  <p className="font-medium">{supplier.supplier_tier}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-medium">{supplier.supplier_status}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Website</p>
                  {supplier.website ? (
                    <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {supplier.website}
                    </a>
                  ) : (
                    <p className="font-medium">—</p>
                  )}
                </div>
              </div>
              {supplier.notes && (
                <div className="border-t border-border pt-4">
                  <p className="mb-1 text-sm text-muted-foreground">Notes</p>
                  <p className="text-sm whitespace-pre-wrap">{supplier.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            {(["Assessments", "Risk Profile", "Intelligence"] as Tab[]).map((t) => {
              const icons: Record<string, React.ReactNode> = {
                Assessments: <FileText className="h-8 w-8 text-blue-500" />,
                "Risk Profile": <AlertTriangle className="h-8 w-8 text-amber-500" />,
                Intelligence: <Target className="h-8 w-8 text-violet-500" />,
              };
              const subtitles: Record<string, string> = {
                Assessments: "View all assessments",
                "Risk Profile": "Findings, risks, actions",
                Intelligence: "ESG & risk scores, trend",
              };
              return (
                <Card key={t} className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={() => setTab(t)}>
                  <CardContent className="flex items-center gap-4 p-4">
                    {icons[t]}
                    <div>
                      <p className="font-semibold">{t}</p>
                      <p className="text-xs text-muted-foreground">{subtitles[t]}</p>
                    </div>
                    <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Assessments Tab ───────────────────────────────────────────────── */}
      {tab === "Assessments" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold">Assessments ({assessments?.total ?? 0})</h2>
            <Link href="/assessments">
              <Button variant="outline" size="sm" className="gap-1.5">
                <FileText className="h-3.5 w-3.5" /> New Assessment
              </Button>
            </Link>
          </div>

          {assessmentsLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : !assessments?.items.length ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <FileText className="h-10 w-10 text-muted-foreground/40" />
                <p className="text-muted-foreground">No assessments for this supplier yet.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Title</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Review Status</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Quality</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {assessments.items.map((a) => (
                      <tr key={a.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <Link href={`/assessments/${a.id}`} className="font-medium hover:text-blue-600 hover:underline">
                            {a.title}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{a.assessment_type || "—"}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium ${
                            a.review_status === "Approved" ? "text-emerald-600" :
                            a.review_status === "InReview" ? "text-blue-600" :
                            a.review_status === "ChangesRequested" ? "text-amber-600" :
                            "text-muted-foreground"
                          }`}>
                            {a.review_status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {a.quality_score != null ? (
                            <span className="font-medium">{(a.quality_score * 100).toFixed(0)}%</span>
                          ) : <span className="text-muted-foreground/50">—</span>}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {new Date(a.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Risk Profile Tab ──────────────────────────────────────────────── */}
      {tab === "Risk Profile" && (
        <div>
          {!profile ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: "Total Assessments", value: profile.total_assessments, icon: FileText, sub: `${profile.approved_assessments} approved`, color: "text-blue-600" },
                  { label: "Total Findings", value: profile.total_findings, icon: AlertTriangle, sub: `${profile.findings_by_severity["Critical"] ?? 0} critical`, color: profile.findings_by_severity["Critical"] ? "text-red-600" : "text-amber-500" },
                  { label: "Total Risks", value: profile.total_risks, icon: ShieldAlert, sub: `${profile.risks_by_severity["Critical"] ?? 0} critical`, color: profile.risks_by_severity["Critical"] ? "text-red-600" : "text-orange-500" },
                  { label: "Open Actions", value: profile.open_actions, icon: Clock, sub: profile.overdue_actions > 0 ? `${profile.overdue_actions} overdue` : "None overdue", color: profile.overdue_actions > 0 ? "text-red-600" : "text-muted-foreground" },
                ].map(({ label, value, icon: Icon, sub, color }) => (
                  <Card key={label}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground">{label}</p>
                          <p className={`text-3xl font-bold ${color}`}>{value}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
                        </div>
                        <Icon className={`h-5 w-5 ${color} opacity-60`} />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                {(["Findings", "Risks"] as const).map((kind) => {
                  const data = kind === "Findings" ? profile.findings_by_severity : profile.risks_by_severity;
                  const total = kind === "Findings" ? profile.total_findings : profile.total_risks;
                  return (
                    <Card key={kind}>
                      <CardHeader><CardTitle className="text-base">{kind} by Severity</CardTitle></CardHeader>
                      <CardContent>
                        {["Critical", "High", "Medium", "Low"].map((sev) => {
                          const count = data[sev] ?? 0;
                          const pct = total > 0 ? (count / total) * 100 : 0;
                          return (
                            <div key={sev} className="mb-3">
                              <div className="mb-1 flex items-center justify-between text-sm">
                                <span className={`font-medium ${severityColor(sev)}`}>{sev}</span>
                                <span className="text-muted-foreground">{count}</span>
                              </div>
                              <div className="h-2 w-full rounded-full bg-muted">
                                <div
                                  className={`h-2 rounded-full transition-all ${
                                    sev === "Critical" ? "bg-red-500" : sev === "High" ? "bg-orange-500" : sev === "Medium" ? "bg-amber-400" : "bg-green-500"
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <Card>
                <CardHeader><CardTitle className="text-base">Action Tracking</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <p className="text-3xl font-bold text-foreground">{profile.open_recommendations}</p>
                      <p className="text-xs text-muted-foreground mt-1">Open Recommendations</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-amber-600">{profile.open_actions}</p>
                      <p className="text-xs text-muted-foreground mt-1">Open Actions</p>
                    </div>
                    <div>
                      <p className={`text-3xl font-bold ${profile.overdue_actions > 0 ? "text-red-600" : "text-emerald-600"}`}>
                        {profile.overdue_actions}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">Overdue Actions</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ── Intelligence Tab ──────────────────────────────────────────────── */}
      {tab === "Intelligence" && (
        <div className="space-y-5">
          {/* Sub-tab nav */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1 rounded-lg border border-border bg-muted/30 p-1">
              {(["score", "history", "benchmark", "heatmap"] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setIntelligenceSubTab(st)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                    intelligenceSubTab === st
                      ? "bg-background shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {st === "benchmark" ? "Benchmark" : st.charAt(0).toUpperCase() + st.slice(1)}
                </button>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => recalcMutation.mutate()}
              disabled={recalcMutation.isPending}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${recalcMutation.isPending ? "animate-spin" : ""}`} />
              Recalculate
            </Button>
          </div>

          {/* Score sub-tab */}
          {intelligenceSubTab === "score" && (
            <div>
              {intelligenceLoading ? (
                <div className="flex justify-center py-12"><Spinner size="lg" /></div>
              ) : !intelligence ? (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    No score calculated yet. Click Recalculate to generate the first score.
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-6">
                  {/* Score overview row */}
                  <div className="grid gap-4 lg:grid-cols-2">
                    {/* ESG scores */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">ESG Score</CardTitle>
                        <p className="text-xs text-muted-foreground">
                          Calculated {new Date(intelligence.calculated_at).toLocaleString()} · v{intelligence.score_version}
                        </p>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-around py-2">
                          <ScoreRing score={intelligence.esg_score} label="Total ESG" color="stroke-blue-500" />
                          <ScoreRing score={intelligence.environmental_score} label="Environmental" color="stroke-emerald-500" />
                          <ScoreRing score={intelligence.social_score} label="Social" color="stroke-violet-500" />
                          <ScoreRing score={intelligence.governance_score} label="Governance" color="stroke-amber-500" />
                        </div>
                        <div className="mt-3 flex items-center justify-center gap-3">
                          <TrendBadge trend={intelligence.trend} delta={intelligence.trend_delta} />
                        </div>
                      </CardContent>
                    </Card>

                    {/* Risk score */}
                    <Card>
                      <CardHeader><CardTitle className="text-base">Risk Score</CardTitle></CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-5xl font-bold tabular-nums">{intelligence.risk_score.toFixed(0)}</p>
                            <p className="text-sm text-muted-foreground mt-1">out of 100</p>
                          </div>
                          <span className={`rounded-lg px-4 py-2 text-lg font-bold ${riskBandColor(intelligence.risk_band)}`}>
                            {intelligence.risk_band}
                          </span>
                        </div>
                        <div className="h-3 w-full rounded-full bg-muted">
                          <div
                            className={`h-3 rounded-full transition-all ${
                              intelligence.risk_band === "Critical" ? "bg-red-500" :
                              intelligence.risk_band === "High" ? "bg-orange-500" :
                              intelligence.risk_band === "Moderate" ? "bg-amber-400" : "bg-emerald-500"
                            }`}
                            style={{ width: `${intelligence.risk_score}%` }}
                          />
                        </div>
                        <div className="grid grid-cols-4 gap-1 text-center text-xs text-muted-foreground">
                          <span>Low<br/>0–25</span>
                          <span>Moderate<br/>26–50</span>
                          <span>High<br/>51–75</span>
                          <span>Critical<br/>76–100</span>
                        </div>
                        {intelligence.sector_percentile != null && (
                          <p className="text-xs text-muted-foreground text-center">
                            Better than {intelligence.sector_percentile.toFixed(0)}% of industry peers
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Score drivers */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Score Drivers</CardTitle>
                      <p className="text-xs text-muted-foreground">
                        Why this score was assigned — ordered by impact
                      </p>
                    </CardHeader>
                    <CardContent>
                      {intelligence.drivers.length === 0 ? (
                        <div className="flex flex-col items-center gap-2 py-6 text-center">
                          <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                          <p className="text-sm text-muted-foreground">No risk drivers identified. This supplier has a clean profile.</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {intelligence.drivers.map((d, i) => (
                            <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-3">
                              <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${
                                d.impact === "high" ? "bg-red-500" :
                                d.impact === "medium" ? "bg-amber-500" : "bg-slate-400"
                              }`} />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="text-sm font-medium">{d.factor}</p>
                                  <span className="text-sm font-bold tabular-nums">{d.count}</span>
                                </div>
                                <p className="text-xs text-muted-foreground">{d.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Raw inputs (collapsible audit data) */}
                  <details className="rounded-lg border border-border">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground">
                      Raw Score Inputs (Audit Data)
                    </summary>
                    <div className="grid grid-cols-2 gap-2 px-4 pb-4 pt-2 text-xs sm:grid-cols-3 lg:grid-cols-4">
                      {Object.entries(intelligence.inputs).map(([k, v]) => (
                        <div key={k} className="flex justify-between rounded bg-muted/50 px-2 py-1">
                          <span className="text-muted-foreground">{k.replace(/_/g, " ")}</span>
                          <span className="font-mono font-semibold">{v}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}

          {/* History sub-tab */}
          {intelligenceSubTab === "history" && (
            <Card>
              <CardHeader><CardTitle className="text-base">Score History</CardTitle></CardHeader>
              <CardContent>
                {!history ? (
                  <div className="flex justify-center py-8"><Spinner size="lg" /></div>
                ) : history.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">No score history yet.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="pb-2 text-left font-medium">Date</th>
                        <th className="pb-2 text-right font-medium">ESG Score</th>
                        <th className="pb-2 text-right font-medium">Risk Score</th>
                        <th className="pb-2 text-center font-medium">Risk Band</th>
                        <th className="pb-2 text-center font-medium">Trend</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {history.map((h, i) => (
                        <tr key={i} className="hover:bg-muted/20">
                          <td className="py-2 text-muted-foreground">
                            {new Date(h.calculated_at).toLocaleString()}
                          </td>
                          <td className="py-2 text-right font-semibold">{h.esg_score.toFixed(1)}</td>
                          <td className="py-2 text-right font-semibold">{h.risk_score.toFixed(1)}</td>
                          <td className="py-2 text-center">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskBandColor(h.risk_band)}`}>
                              {h.risk_band}
                            </span>
                          </td>
                          <td className="py-2 text-center">
                            <TrendBadge trend={h.trend} delta={0} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          )}

          {/* Benchmark sub-tab */}
          {intelligenceSubTab === "benchmark" && (
            <div className="space-y-4">
              {!benchmark ? (
                <div className="flex justify-center py-8"><Spinner size="lg" /></div>
              ) : (
                <>
                  <Card>
                    <CardHeader><CardTitle className="text-base">Peer Benchmark — {benchmark.industry || "All Industries"}</CardTitle></CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div className="text-center">
                          <p className="text-4xl font-bold tabular-nums">{benchmark.risk_score.toFixed(0)}</p>
                          <p className="text-xs text-muted-foreground mt-1">Risk Score</p>
                          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${riskBandColor(benchmark.risk_band)}`}>
                            {benchmark.risk_band}
                          </span>
                        </div>
                        <div className="text-center">
                          <p className="text-4xl font-bold tabular-nums">
                            {benchmark.sector_percentile != null ? `${benchmark.sector_percentile.toFixed(0)}th` : "—"}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">Percentile</p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm font-semibold mt-2">{benchmark.peer_comparison}</p>
                          <p className="text-xs text-muted-foreground mt-1">{benchmark.peers_evaluated} peers evaluated</p>
                        </div>
                      </div>

                      {benchmark.sector_percentile != null && (
                        <div>
                          <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                            <span>Worst (0th)</span>
                            <span>Best (100th)</span>
                          </div>
                          <div className="relative h-3 w-full rounded-full bg-gradient-to-r from-red-400 via-amber-400 to-emerald-500">
                            <div
                              className="absolute top-1/2 h-5 w-5 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-background bg-foreground shadow-md transition-all"
                              style={{ left: `${benchmark.sector_percentile}%` }}
                            />
                          </div>
                          <p className="mt-2 text-center text-xs text-muted-foreground">
                            This supplier is at the <strong>{benchmark.sector_percentile.toFixed(0)}th percentile</strong> — better than{" "}
                            {benchmark.sector_percentile.toFixed(0)}% of peers in {benchmark.industry || "this industry"}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                  <p className="text-xs text-muted-foreground text-center">
                    Benchmarking is within your organization's supplier portfolio.
                    Cross-organization benchmarking is planned for M31 (Regulatory Intelligence).
                  </p>
                </>
              )}
            </div>
          )}

          {/* Heatmap sub-tab */}
          {intelligenceSubTab === "heatmap" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">ESG Risk Heatmap</CardTitle>
                <p className="text-xs text-muted-foreground">Finding count by ESG pillar × severity</p>
              </CardHeader>
              <CardContent>
                {!heatmap ? (
                  <div className="flex justify-center py-8"><Spinner size="lg" /></div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="py-2 text-left font-medium text-muted-foreground w-32">Pillar</th>
                          {["Critical", "High", "Medium", "Low"].map((s) => (
                            <th key={s} className={`py-2 text-center font-medium ${severityColor(s)}`}>{s}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {["Environmental", "Social", "Governance"].map((pillar) => (
                          <tr key={pillar} className="hover:bg-muted/20">
                            <td className="py-3 font-medium">{pillar}</td>
                            {["Critical", "High", "Medium", "Low"].map((sev) => {
                              const cell = heatmap.cells.find((c) => c.pillar === pillar && c.severity === sev);
                              const count = cell?.count ?? 0;
                              const maxCount = Math.max(...heatmap.cells.map((c) => c.count), 1);
                              const intensity = count / maxCount;
                              return (
                                <td key={sev} className="py-3 text-center">
                                  <div
                                    className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg font-bold transition-all"
                                    style={{
                                      backgroundColor: count === 0 ? undefined :
                                        sev === "Critical" ? `rgba(239,68,68,${0.15 + intensity * 0.6})` :
                                        sev === "High" ? `rgba(249,115,22,${0.15 + intensity * 0.6})` :
                                        sev === "Medium" ? `rgba(245,158,11,${0.15 + intensity * 0.6})` :
                                        `rgba(34,197,94,${0.15 + intensity * 0.6})`,
                                    }}
                                  >
                                    <span className={count === 0 ? "text-muted-foreground/40" : ""}>{count}</span>
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="mt-3 text-right text-xs text-muted-foreground">
                      Total: {heatmap.total_findings} finding{heatmap.total_findings !== 1 ? "s" : ""}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Edit Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background p-6 shadow-2xl">
            <h2 className="mb-4 text-lg font-semibold">Edit Supplier</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">Name *</label>
                <Input value={editForm.name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Legal Name</label>
                <Input value={editForm.legal_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, legal_name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Country</label>
                  <Input value={editForm.country ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, country: e.target.value }))} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">NACE Code</label>
                  <Input value={editForm.nace_code ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, nace_code: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Industry</label>
                <Input value={editForm.industry ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, industry: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Tier</label>
                  <select
                    value={editForm.supplier_tier ?? "Tier 1"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {["Tier 1", "Tier 2", "Tier 3", "Other"].map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Status</label>
                  <select
                    value={editForm.supplier_status ?? "Active"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_status: e.target.value as SupplierStatus }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Website</label>
                <Input value={editForm.website ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, website: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  value={editForm.notes ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={3}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            {editError && <p className="mt-3 text-sm text-red-600">{editError}</p>}
            <div className="mt-5 flex justify-end gap-3">
              <Button variant="outline" onClick={() => { setEditing(false); setEditError(null); }}>Cancel</Button>
              <Button onClick={() => updateMutation.mutate(editForm)} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirm Modal */}
      {confirmArchive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-xl bg-background p-6 shadow-2xl">
            <h2 className="mb-2 text-lg font-semibold text-red-600">Archive Supplier</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Are you sure you want to archive <strong>{supplier.name}</strong>? This will set the
              supplier to Inactive. Existing assessments are not affected.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setConfirmArchive(false)}>Cancel</Button>
              <Button variant="destructive" onClick={() => archiveMutation.mutate()} disabled={archiveMutation.isPending}>
                {archiveMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                Archive
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
