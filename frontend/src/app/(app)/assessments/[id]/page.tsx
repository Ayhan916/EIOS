"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  ShieldAlert,
  Lightbulb,
} from "lucide-react";
import { getAssessment } from "@/lib/api/assessments";
import { listFindings } from "@/lib/api/findings";
import { listRisks } from "@/lib/api/risks";
import { listRecommendations } from "@/lib/api/recommendations";
import { getComplianceCoverage } from "@/lib/api/compliance";
import { generateReport, listReports, downloadReportPdf } from "@/lib/api/reports";
import { getAssessmentBenchmark } from "@/lib/api/sector_intelligence";
import {
  formatDateTime,
  severityColor,
  verdictColor,
} from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { Separator } from "@/components/ui/separator";

function SeverityDot({ level }: { level: string }) {
  const c = severityColor(level);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ${c.bg} ${c.text} px-2.5 py-0.5 text-xs font-semibold capitalize`}>
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {level}
    </span>
  );
}

export default function AssessmentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState("");

  const { data: assessment, isLoading: loadingAssessment } = useQuery({
    queryKey: ["assessment", id],
    queryFn: () => getAssessment(id),
  });

  const { data: findings, isLoading: loadingFindings } = useQuery({
    queryKey: ["findings", id],
    queryFn: () => listFindings(id),
    enabled: !!id,
  });

  const { data: risks, isLoading: loadingRisks } = useQuery({
    queryKey: ["risks", id],
    queryFn: () => listRisks(id),
    enabled: !!id,
  });

  const { data: recs, isLoading: loadingRecs } = useQuery({
    queryKey: ["recommendations", id],
    queryFn: () => listRecommendations(id),
    enabled: !!id,
  });

  const { data: compliance, isLoading: loadingCompliance } = useQuery({
    queryKey: ["compliance", id],
    queryFn: () => getComplianceCoverage(id),
    enabled: !!id,
  });

  const {
    data: reports,
    isLoading: loadingReports,
    refetch: refetchReports,
  } = useQuery({
    queryKey: ["reports", id],
    queryFn: () => listReports(id),
    enabled: !!id,
  });

  const { data: benchmark, isLoading: loadingBenchmark } = useQuery({
    queryKey: ["benchmark", id],
    queryFn: () => getAssessmentBenchmark(id),
    enabled: !!id,
  });

  async function handleGenerateReport() {
    setGeneratingReport(true);
    setReportError("");
    try {
      await generateReport(id);
      await refetchReports();
    } catch {
      setReportError("Failed to generate report. Please try again.");
    } finally {
      setGeneratingReport(false);
    }
  }

  async function handleDownloadReport(reportId: string, title: string) {
    try {
      await downloadReportPdf(reportId, title);
    } catch {
      setReportError("Failed to download report.");
    }
  }

  if (loadingAssessment) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="py-24 text-center text-muted-foreground">
        Assessment not found.
      </div>
    );
  }

  const qualityPct = assessment.quality_score != null
    ? Math.round(assessment.quality_score * 100)
    : null;

  return (
    <div className="space-y-6">
      {/* Breadcrumb + header */}
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-4 -ml-1 gap-1">
          <Link href="/assessments">
            <ArrowLeft className="h-4 w-4" />
            Back to assessments
          </Link>
        </Button>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold leading-tight">{assessment.title}</h1>
            <p className="mt-1.5 text-sm text-muted-foreground leading-relaxed max-w-3xl">
              {assessment.description}
            </p>
          </div>
          {qualityPct != null && (
            <div className="flex-shrink-0 text-right">
              <p className="text-xs text-muted-foreground">Quality Score</p>
              <p className={`text-2xl font-bold ${
                qualityPct >= 70 ? "text-emerald-600" : qualityPct >= 40 ? "text-amber-600" : "text-red-600"
              }`}>
                {qualityPct}%
              </p>
            </div>
          )}
        </div>

        {/* Meta strip */}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="capitalize rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
            {assessment.status}
          </span>
          {assessment.assessment_type && (
            <span className="capitalize">{assessment.assessment_type}</span>
          )}
          <span>{formatDateTime(assessment.created_at)}</span>
          {assessment.methodology && (
            <>
              <Separator orientation="vertical" className="h-3" />
              <span className="italic truncate max-w-xs">{assessment.methodology}</span>
            </>
          )}
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="findings">
            Findings {findings ? `(${findings.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="risks">
            Risks {risks ? `(${risks.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="recommendations">
            Actions {recs ? `(${recs.length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
          <TabsTrigger value="benchmark">Benchmark</TabsTrigger>
          <TabsTrigger value="reports">
            Reports {reports ? `(${reports.length})` : ""}
          </TabsTrigger>
        </TabsList>

        {/* ── OVERVIEW ── */}
        <TabsContent value="overview" className="mt-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card className="flex flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  <CardTitle className="text-sm font-medium">Findings</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{findings?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">material ESG findings</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <ShieldAlert className="h-4 w-4 text-red-500" />
                  <CardTitle className="text-sm font-medium">Risks</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{risks?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">identified risk factors</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Lightbulb className="h-4 w-4 text-blue-500" />
                  <CardTitle className="text-sm font-medium">Actions</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{recs?.length ?? "—"}</p>
                <p className="text-xs text-muted-foreground mt-1">remediation recommendations</p>
              </CardContent>
            </Card>
          </div>

          {compliance && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle className="text-base">Compliance Snapshot</CardTitle>
                <CardDescription>
                  Verdict:{" "}
                  <span className={`font-semibold capitalize ${verdictColor(compliance.verdict.status)}`}>
                    {compliance.verdict.status.replace(/_/g, " ")}
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-muted-foreground">Overall coverage</span>
                    <span className="font-medium">
                      {Math.round(compliance.overall_coverage_ratio * 100)}%
                    </span>
                  </div>
                  <Progress
                    value={compliance.overall_coverage_ratio * 100}
                    className="h-2"
                  />
                </div>
                <div>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-muted-foreground">Mandatory coverage</span>
                    <span className="font-medium">
                      {Math.round(compliance.mandatory_coverage_ratio * 100)}%
                    </span>
                  </div>
                  <Progress
                    value={compliance.mandatory_coverage_ratio * 100}
                    className="h-2"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {compliance.verdict.explanation}
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── FINDINGS ── */}
        <TabsContent value="findings" className="mt-6">
          {loadingFindings ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !findings?.length ? (
            <p className="py-12 text-center text-muted-foreground">No findings extracted.</p>
          ) : (
            <div className="space-y-3">
              {findings.map((f) => (
                <Card key={f.id}>
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground">{f.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{f.description}</p>
                        {f.reasoning && (
                          <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
                            {f.reasoning}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                          {f.category && (
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {f.category}
                            </span>
                          )}
                          <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                            Confidence: {f.confidence}
                          </span>
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <SeverityDot level={f.severity} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── RISKS ── */}
        <TabsContent value="risks" className="mt-6">
          {loadingRisks ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !risks?.length ? (
            <p className="py-12 text-center text-muted-foreground">No risks identified.</p>
          ) : (
            <div className="space-y-3">
              {risks.map((r) => (
                <Card key={r.id}>
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-foreground">{r.title}</p>
                        <p className="mt-1 text-sm text-muted-foreground">{r.description}</p>
                        {r.reasoning && (
                          <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
                            {r.reasoning}
                          </p>
                        )}
                        <div className="mt-3 flex flex-wrap gap-2">
                          {r.probability != null && (
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              Probability: {Math.round(r.probability * 100)}%
                            </span>
                          )}
                          {r.impact != null && (
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              Impact: {Math.round(r.impact * 100)}%
                            </span>
                          )}
                          {r.category && (
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {r.category}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex-shrink-0">
                        <SeverityDot level={r.risk_level} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── RECOMMENDATIONS ── */}
        <TabsContent value="recommendations" className="mt-6">
          {loadingRecs ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !recs?.length ? (
            <p className="py-12 text-center text-muted-foreground">No recommendations generated.</p>
          ) : (
            <div className="space-y-3">
              {recs.map((rec) => (
                <Card key={rec.id}>
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-foreground">{rec.title}</p>
                          {rec.action_required && (
                            <Badge variant="destructive" className="text-[10px] h-4 px-1.5">
                              Required
                            </Badge>
                          )}
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">{rec.description}</p>
                        {rec.reasoning && (
                          <p className="mt-2 text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
                            {rec.reasoning}
                          </p>
                        )}
                        {rec.due_date && (
                          <p className="mt-2 text-xs text-muted-foreground">
                            Due: {formatDateTime(rec.due_date)}
                          </p>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        <SeverityDot level={rec.priority} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── COMPLIANCE ── */}
        <TabsContent value="compliance" className="mt-6">
          {loadingCompliance ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !compliance ? (
            <p className="py-12 text-center text-muted-foreground">
              No compliance data available.
            </p>
          ) : (
            <div className="space-y-6">
              {/* Verdict card */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Compliance Verdict</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <p className={`text-xl font-bold capitalize ${verdictColor(compliance.verdict.status)}`}>
                      {compliance.verdict.status.replace(/_/g, " ")}
                    </p>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {compliance.verdict.explanation}
                  </p>
                  <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-center">
                    {[
                      { label: "Mandatory covered", value: `${compliance.verdict.covered_mandatory_count}/${compliance.verdict.total_mandatory_articles}` },
                      { label: "Mandatory gaps", value: compliance.verdict.mandatory_gap_count },
                      { label: "Critical gaps", value: compliance.verdict.critical_gap_count },
                      { label: "High gaps", value: compliance.verdict.high_gap_count },
                    ].map((stat) => (
                      <div key={stat.label} className="rounded-lg bg-muted/50 p-3">
                        <p className="text-xs text-muted-foreground">{stat.label}</p>
                        <p className="mt-1 text-lg font-bold">{stat.value}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Framework coverage */}
              {compliance.framework_coverage.map((fw) => (
                <Card key={fw.framework}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-semibold">{fw.framework}</CardTitle>
                      <span className="text-sm font-medium text-muted-foreground">
                        {fw.covered_count}/{fw.total_articles} articles covered
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Progress value={fw.coverage_ratio * 100} className="h-2 mb-4" />
                    <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                      {fw.articles.map((art) => (
                        <div
                          key={art.code}
                          className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs ${
                            art.covered
                              ? "bg-emerald-50 text-emerald-800"
                              : "bg-red-50 text-red-800"
                          }`}
                        >
                          {art.covered ? (
                            <CheckCircle2 className="h-3 w-3 flex-shrink-0" />
                          ) : (
                            <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                          )}
                          <span className="font-mono font-medium">{art.code}</span>
                          <span className="truncate">{art.title}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {/* Top gaps */}
              {compliance.gaps.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Compliance Gaps</CardTitle>
                    <CardDescription>
                      Regulatory obligations not yet addressed
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {compliance.gaps.map((gap) => (
                      <div
                        key={gap.article_code}
                        className="rounded-lg border border-border p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-sm">
                              <span className="font-mono text-muted-foreground mr-2">
                                {gap.article_code}
                              </span>
                              {gap.title}
                            </p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {gap.explanation}
                            </p>
                            {gap.remediation_hint && (
                              <p className="mt-2 text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
                                💡 {gap.remediation_hint}
                              </p>
                            )}
                          </div>
                          <SeverityDot level={gap.gap_severity} />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>
        {/* ── BENCHMARK ── */}
        <TabsContent value="benchmark" className="mt-6">
          {loadingBenchmark ? (
            <div className="flex justify-center py-12"><Spinner /></div>
          ) : !benchmark ? (
            <p className="py-12 text-center text-muted-foreground">
              Benchmark data unavailable. Ensure the assessment has a sector assigned.
            </p>
          ) : (
            <div className="space-y-5">
              {/* Overall rating */}
              <Card>
                <CardHeader>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">Sector Benchmark</CardTitle>
                      <CardDescription>
                        {benchmark.sector_name} ({benchmark.sector_nace_code})
                      </CardDescription>
                    </div>
                    <span className={`flex-shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                      benchmark.benchmark_rating === "above_sector_baseline"
                        ? "bg-emerald-100 text-emerald-800"
                        : benchmark.benchmark_rating === "meets_sector_baseline"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-red-100 text-red-800"
                    }`}>
                      {benchmark.benchmark_rating.replace(/_/g, " ")}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{benchmark.benchmark_explanation}</p>
                </CardContent>
              </Card>

              {/* Sector inherent risk */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Inherent Sector ESG Risk</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      { label: "Environmental", level: benchmark.environmental_risk },
                      { label: "Social", level: benchmark.social_risk },
                      { label: "Governance", level: benchmark.governance_risk },
                      { label: "Overall", level: benchmark.overall_sector_risk },
                    ].map(({ label, level }) => {
                      const c = severityColor(level);
                      return (
                        <div key={label} className={`rounded-lg p-3 text-center ${c.bg}`}>
                          <p className={`text-xs font-medium ${c.text}`}>{label}</p>
                          <p className={`text-sm font-bold mt-1 ${c.text}`}>{level}</p>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-4 space-y-1">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Applicable Frameworks</p>
                    <div className="flex flex-wrap gap-2">
                      {benchmark.applicable_frameworks.map((fw) => (
                        <span key={fw} className="rounded-full bg-blue-50 text-blue-700 px-2.5 py-0.5 text-xs font-medium">
                          {fw}
                        </span>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Coverage vs baseline */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Compliance Coverage vs Sector Baseline</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Sector Baseline</p>
                      <p className="text-xl font-bold mt-1">
                        {Math.round(benchmark.baseline_mandatory_coverage * 100)}%
                      </p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">This Assessment</p>
                      <p className={`text-xl font-bold mt-1 ${
                        benchmark.mandatory_coverage == null
                          ? "text-muted-foreground"
                          : benchmark.coverage_vs_baseline != null && benchmark.coverage_vs_baseline >= 0
                          ? "text-emerald-600"
                          : "text-red-600"
                      }`}>
                        {benchmark.mandatory_coverage != null
                          ? `${Math.round(benchmark.mandatory_coverage * 100)}%`
                          : "—"}
                      </p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{benchmark.coverage_explanation}</p>
                </CardContent>
              </Card>

              {/* Finding adequacy */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Finding Adequacy</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Critical</p>
                      <p className="text-xl font-bold text-red-600">{benchmark.finding_distribution.critical}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">High</p>
                      <p className="text-xl font-bold text-orange-600">{benchmark.finding_distribution.high}</p>
                    </div>
                    <div className="rounded-lg bg-muted/50 p-3 text-center">
                      <p className="text-xs text-muted-foreground">Medium + Low</p>
                      <p className="text-xl font-bold">{benchmark.finding_distribution.medium + benchmark.finding_distribution.low}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">{benchmark.finding_explanation}</p>
                </CardContent>
              </Card>

              {/* Key sector risk themes */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Key Sector Risk Themes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {benchmark.key_risk_themes.map((theme) => {
                    const identified = benchmark.key_themes_identified.includes(theme);
                    return (
                      <div
                        key={theme}
                        className={`flex items-center gap-2 rounded-md px-3 py-2 text-xs ${
                          identified
                            ? "bg-emerald-50 text-emerald-800"
                            : "bg-red-50 text-red-700"
                        }`}
                      >
                        {identified ? (
                          <CheckCircle2 className="h-3 w-3 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="h-3 w-3 flex-shrink-0" />
                        )}
                        <span>{theme}</span>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>

              {/* Regulatory exposure */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-semibold">Regulatory Exposure</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{benchmark.regulatory_exposure_notes}</p>
                </CardContent>
              </Card>

              {/* Peer comparison */}
              {benchmark.peer_count > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      Organisational Peer Comparison ({benchmark.peer_count} peer{benchmark.peer_count !== 1 ? "s" : ""})
                    </CardTitle>
                    <CardDescription>
                      Other assessments in the same sector within your organisation
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {benchmark.org_avg_quality_score != null && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="rounded-lg bg-muted/50 p-3 text-center">
                          <p className="text-xs text-muted-foreground">Org avg quality score</p>
                          <p className="text-xl font-bold">{Math.round(benchmark.org_avg_quality_score * 100)}%</p>
                        </div>
                        <div className="rounded-lg bg-muted/50 p-3 text-center">
                          <p className="text-xs text-muted-foreground">Org avg findings</p>
                          <p className="text-xl font-bold">{benchmark.org_avg_finding_count}</p>
                        </div>
                      </div>
                    )}
                    <div className="space-y-2">
                      {benchmark.peers.map((peer) => (
                        <div key={peer.assessment_id} className="rounded-lg border border-border px-3 py-2 flex items-center justify-between gap-3 text-sm">
                          <span className="truncate text-foreground">{peer.title}</span>
                          <div className="flex-shrink-0 flex gap-2 text-xs text-muted-foreground">
                            <span>{peer.finding_count} findings</span>
                            {peer.quality_score != null && (
                              <span className="font-medium text-foreground">
                                {Math.round(peer.quality_score * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>

        {/* ── REPORTS ── */}
        <TabsContent value="reports" className="mt-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Executive Reports</h3>
                <p className="text-sm text-muted-foreground">
                  Generate a PDF report capturing all findings, risks, recommendations, and evidence at this point in time.
                </p>
              </div>
              <Button
                onClick={handleGenerateReport}
                disabled={generatingReport}
                className="gap-2 flex-shrink-0"
              >
                {generatingReport ? (
                  <Spinner size="sm" className="text-white" />
                ) : (
                  <FileText className="h-4 w-4" />
                )}
                {generatingReport ? "Generating..." : "Generate Report"}
              </Button>
            </div>

            {reportError && (
              <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
                {reportError}
              </div>
            )}

            {loadingReports ? (
              <div className="flex justify-center py-12"><Spinner /></div>
            ) : !reports?.length ? (
              <div className="rounded-lg border-2 border-dashed border-border py-16 text-center">
                <FileText className="mx-auto h-10 w-10 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground">No reports generated yet.</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Click "Generate Report" to create an executive-ready PDF.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {reports.map((report) => (
                  <Card key={report.id}>
                    <CardContent className="pt-4 pb-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <p className="font-semibold text-sm text-foreground truncate">
                            {report.title}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Generated {formatDateTime(report.created_at)}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-2">
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.finding_count} findings
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.risk_count} risks
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.recommendation_count} recommendations
                            </span>
                            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                              {report.evidence_count} evidence sources
                            </span>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-shrink-0 gap-1.5"
                          onClick={() => handleDownloadReport(report.id, report.title)}
                        >
                          <Download className="h-3.5 w-3.5" />
                          Download PDF
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
