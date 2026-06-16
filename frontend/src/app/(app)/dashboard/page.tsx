"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  FileText,
  Plus,
  RefreshCw,
} from "lucide-react";
import { listAssessments } from "@/lib/api/assessments";
import { listJobs } from "@/lib/api/workflows";
import { formatDateTime, jobStatusColor, severityColor } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/context";

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  sub?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1 text-3xl font-bold text-foreground">{value}</p>
            {sub && (
              <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
            )}
          </div>
          <div className="rounded-full bg-primary/10 p-2.5">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();

  const { data: assessments, isLoading: loadingAssessments } = useQuery({
    queryKey: ["assessments", { page: 1, page_size: 5 }],
    queryFn: () => listAssessments({ page: 1, page_size: 5 }),
  });

  const { data: jobs, isLoading: loadingJobs } = useQuery({
    queryKey: ["jobs", { page: 1, page_size: 5 }],
    queryFn: () => listJobs({ page: 1, page_size: 5 }),
  });

  const completedJobs =
    jobs?.items.filter((j) => j.job_status === "completed").length ?? 0;
  const runningJobs =
    jobs?.items.filter((j) => j.job_status === "running" || j.job_status === "pending")
      .length ?? 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Welcome back, {user?.display_name?.split(" ")[0]}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            ESG Due Diligence & Risk Intelligence Overview
          </p>
        </div>
        <Button asChild>
          <Link href="/assessments/new">
            <Plus className="h-4 w-4" />
            New Assessment
          </Link>
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Assessments"
          value={assessments?.total ?? "—"}
          icon={FileText}
          sub="across your organisation"
        />
        <StatCard
          label="Active Jobs"
          value={runningJobs}
          icon={RefreshCw}
          sub="workflows in progress"
        />
        <StatCard
          label="Completed Jobs"
          value={completedJobs}
          icon={CheckCircle2}
          sub="this session"
        />
        <StatCard
          label="Pending Review"
          value={
            assessments?.items.filter((a) => a.status === "pending").length ?? 0
          }
          icon={AlertTriangle}
          sub="require attention"
        />
      </div>

      {/* Two-column content */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Assessments */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle className="text-base">Recent Assessments</CardTitle>
              <CardDescription>Latest ESG evaluations</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/assessments" className="gap-1 text-xs">
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {loadingAssessments ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : !assessments?.items.length ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No assessments yet.{" "}
                <Link href="/assessments/new" className="text-primary underline">
                  Run your first assessment
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {assessments.items.map((a) => (
                  <Link
                    key={a.id}
                    href={`/assessments/${a.id}`}
                    className="flex items-start justify-between rounded-md p-3 transition-colors hover:bg-muted/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {a.title}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatDateTime(a.created_at)}
                      </p>
                    </div>
                    <div
                      className={`ml-3 flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                        a.quality_score != null
                          ? a.quality_score >= 0.7
                            ? "bg-emerald-50 text-emerald-700"
                            : a.quality_score >= 0.4
                            ? "bg-amber-50 text-amber-700"
                            : "bg-red-50 text-red-700"
                          : "bg-slate-50 text-slate-600"
                      }`}
                    >
                      {a.quality_score != null
                        ? `${Math.round(a.quality_score * 100)}%`
                        : a.status}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
            <div>
              <CardTitle className="text-base">Workflow Jobs</CardTitle>
              <CardDescription>Analysis pipeline status</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {loadingJobs ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : !jobs?.items.length ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No jobs yet. Start by running a new assessment.
              </div>
            ) : (
              <div className="space-y-3">
                {jobs.items.map((job) => {
                  const colors = jobStatusColor(job.job_status);
                  return (
                    <div
                      key={job.id}
                      className="flex items-start justify-between rounded-md p-3 hover:bg-muted/60"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-foreground">
                          {job.workflow_type}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {job.query.slice(0, 60)}
                          {job.query.length > 60 ? "…" : ""}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {formatDateTime(job.created_at)}
                        </p>
                      </div>
                      <span
                        className={`ml-3 flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium capitalize ${colors.bg} ${colors.text}`}
                      >
                        {job.job_status}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
