"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { listEnterprises, getEnterpriseAudit, globalSearch } from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

function fmt(ts: string) {
  return new Date(ts).toLocaleString();
}

function actionBadge(action: string) {
  if (action.includes("enterprise")) return "bg-blue-100 text-blue-800";
  if (action.includes("scim"))       return "bg-purple-100 text-purple-800";
  if (action.includes("policy"))     return "bg-amber-100 text-amber-800";
  if (action.includes("risk"))       return "bg-red-100 text-red-800";
  if (action.includes("role"))       return "bg-teal-100 text-teal-800";
  return "bg-slate-100 text-slate-700";
}

export default function EnterpriseAuditPage() {
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchActive, setSearchActive] = useState(false);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: events, isLoading: loadingAudit } = useQuery({
    queryKey: ["enterprise-audit", activeId],
    queryFn: () => getEnterpriseAudit(activeId!, { limit: 100 }),
    enabled: !!activeId && !searchActive,
  });

  const { data: searchResults, isLoading: loadingSearch } = useQuery({
    queryKey: ["enterprise-search", activeId, searchQuery],
    queryFn: () => globalSearch(activeId!, searchQuery),
    enabled: !!activeId && searchActive && searchQuery.length >= 2,
  });

  const isLoading = loadingAudit || loadingSearch;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Enterprise Audit</h1>
          <p className="text-sm text-muted-foreground">
            Cross-organizational audit trail and global search
          </p>
        </div>
        {enterprises && enterprises.length > 1 && (
          <select
            className="rounded-lg border px-3 py-2 text-sm"
            value={activeId ?? ""}
            onChange={(e) => setSelectedId(e.target.value)}
          >
            {enterprises.map((e) => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
        )}
      </div>

      {/* Search bar */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Global Search</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                className="w-full rounded-lg border py-2 pl-9 pr-3 text-sm"
                placeholder="Search suppliers, risks, findings…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button
              onClick={() => setSearchActive(!!searchQuery)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-sm text-white"
            >
              Search
            </button>
            {searchActive && (
              <button
                onClick={() => { setSearchActive(false); setSearchQuery(""); }}
                className="rounded-lg border px-4 py-2 text-sm"
              >
                Clear
              </button>
            )}
          </div>

          {searchActive && (
            <div className="mt-4">
              {loadingSearch ? (
                <div className="flex justify-center py-4"><Spinner /></div>
              ) : !searchResults || searchResults.length === 0 ? (
                <p className="text-sm text-muted-foreground">No results found.</p>
              ) : (
                <div className="space-y-2">
                  {searchResults.map((r, i) => (
                    <div key={i} className="flex items-center justify-between rounded-lg border px-3 py-2">
                      <div>
                        <p className="text-sm font-medium">{r.title}</p>
                        {r.subtitle && (
                          <p className="text-xs text-muted-foreground">{r.subtitle}</p>
                        )}
                      </div>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {r.entity_type}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Audit events */}
      {!searchActive && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Audit Events</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : !events || events.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No enterprise audit events yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-muted-foreground">
                      <th className="pb-2 text-left">Action</th>
                      <th className="pb-2 text-left">Entity</th>
                      <th className="pb-2 text-left">Outcome</th>
                      <th className="pb-2 text-left">When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(events as Record<string, unknown>[]).map((e, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2">
                          <span className={`rounded px-2 py-0.5 text-xs font-medium ${actionBadge(String(e.action ?? ""))}`}>
                            {String(e.action ?? "—")}
                          </span>
                        </td>
                        <td className="py-2 text-xs text-muted-foreground">
                          {String(e.entity_type ?? "")} {String(e.entity_id ?? "").slice(0, 8)}
                        </td>
                        <td className="py-2 text-xs">
                          <span className={String(e.outcome) === "success" ? "text-emerald-600" : "text-red-600"}>
                            {String(e.outcome ?? "—")}
                          </span>
                        </td>
                        <td className="py-2 text-xs text-muted-foreground">
                          {e.created_at ? fmt(String(e.created_at)) : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
