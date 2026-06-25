"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, FileText, Plus, Search } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { listAssessments } from "@/lib/api/assessments";
import apiClient from "@/lib/api/client";
import { formatDateTime, severityColor } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

const STATUS_OPTIONS = ["", "pending", "reviewed", "active", "archived"];

export default function AssessmentsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["assessments", { page, page_size: 10, search, status }],
    queryFn: () =>
      listAssessments({
        page,
        page_size: 10,
        search: search || undefined,
        status: status || undefined,
      }),
  });

  const { data: scheduledSupplierIds } = useQuery<Set<string>>({
    queryKey: ["assessment-schedules-supplier-ids"],
    queryFn: async () => {
      try {
        const r = await apiClient.get("/api/v1/assessments/schedules?active_only=true&limit=200");
        const ids = new Set<string>((r.data ?? []).map((s: { supplier_id: string }) => s.supplier_id).filter(Boolean));
        return ids;
      } catch { return new Set(); }
    },
    staleTime: 300_000,
    retry: false,
  });

  function applySearch() {
    setSearch(searchInput);
    setPage(1);
  }

  function qualityBadge(score: number | null) {
    if (score == null) return null;
    const pct = Math.round(score * 100);
    const cls =
      score >= 0.7
        ? "bg-emerald-50 text-emerald-700"
        : score >= 0.4
        ? "bg-amber-50 text-amber-700"
        : "bg-red-50 text-red-700";
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
        {pct}%
      </span>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Assessments</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            All ESG due diligence evaluations
          </p>
        </div>
        <Button asChild>
          <Link href="/assessments/new">
            <Plus className="h-4 w-4" />
            New Assessment
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-3">
            <div className="flex flex-1 items-center gap-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search assessments…"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && applySearch()}
                  className="pl-9"
                />
              </div>
              <Button variant="outline" size="sm" onClick={applySearch}>
                Search
              </Button>
            </div>
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">All statuses</option>
              {STATUS_OPTIONS.filter(Boolean).map((s) => (
                <option key={s} value={s} className="capitalize">
                  {s}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Status summary */}
      {data && data.total > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Pending", cls: "text-amber-600 bg-amber-50", status: "pending" },
            { label: "Reviewed", cls: "text-blue-600 bg-blue-50", status: "reviewed" },
            { label: "Active", cls: "text-emerald-600 bg-emerald-50", status: "active" },
            { label: "Archived", cls: "text-slate-500 bg-slate-50", status: "archived" },
          ].map(({ label, cls, status: s }) => {
            const count = data.items.filter((a) => a.status === s).length;
            const total_pct = data.total > 0 ? Math.round((count / data.total) * 100) : 0;
            return (
              <Card key={s} className="cursor-pointer" onClick={() => { setStatus(s); setPage(1); }}>
                <CardContent className="pt-3 pb-3">
                  <p className={`text-lg font-bold ${cls.split(" ")[0]}`}>{count}</p>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <div className="mt-1.5 h-1 rounded-full bg-muted overflow-hidden">
                    <div className={`h-full rounded-full ${cls.split(" ")[1]}`} style={{ width: `${total_pct}%` }} />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader className="pb-0">
          <CardTitle className="text-base">
            {data ? `${data.total} assessment${data.total !== 1 ? "s" : ""}` : "Assessments"}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spinner size="lg" />
            </div>
          ) : !data?.items.length ? (
            <EmptyState
              icon={FileText}
              title="No assessments yet"
              description="Here's what you can do next: select a supplier and run an ESG assessment to evaluate their environmental, social, and governance practices."
              actions={[
                { label: "Run First Assessment", href: "/assessments/new", variant: "primary" },
                { label: "Add a Supplier First", href: "/suppliers", variant: "outline" },
              ]}
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Title
                      </th>
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Type
                      </th>
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Status
                      </th>
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Schedule
                      </th>
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Quality
                      </th>
                      <th className="pb-3 text-left font-medium text-muted-foreground">
                        Created
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.items.map((a) => (
                      <tr
                        key={a.id}
                        className="hover:bg-muted/40 transition-colors"
                      >
                        <td className="py-3 pr-4">
                          <Link
                            href={`/assessments/${a.id}`}
                            className="font-medium text-foreground hover:text-primary hover:underline"
                          >
                            {a.title}
                          </Link>
                          {a.methodology && (
                            <p className="mt-0.5 truncate text-xs text-muted-foreground max-w-xs">
                              {a.methodology}
                            </p>
                          )}
                        </td>
                        <td className="py-3 pr-4 text-muted-foreground capitalize">
                          {a.assessment_type || "—"}
                        </td>
                        <td className="py-3 pr-4">
                          <span className="capitalize rounded-full bg-secondary px-2 py-0.5 text-xs font-medium">
                            {a.status}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          {a.supplier_id && scheduledSupplierIds?.has(a.supplier_id) ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                              <CalendarClock className="h-3 w-3" /> Scheduled
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          {qualityBadge(a.quality_score)}
                        </td>
                        <td className="py-3 text-muted-foreground whitespace-nowrap">
                          {formatDateTime(a.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.total_pages > 1 && (
                <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {data.total_pages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!data.has_prev}
                      onClick={() => setPage((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={!data.has_next}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
