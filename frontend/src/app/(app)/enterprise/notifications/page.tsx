"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { listEnterprises, listNotificationPolicies, type NotificationPolicy } from "@/lib/api/enterprise";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

export default function EnterpriseNotificationsPage() {
  const { data: enterprises } = useQuery({
    queryKey: ["enterprises"],
    queryFn: listEnterprises,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const activeId = selectedId ?? enterprises?.[0]?.id ?? null;

  const { data: policies, isLoading } = useQuery({
    queryKey: ["notification-policies", activeId],
    queryFn: () => listNotificationPolicies(activeId!),
    enabled: !!activeId,
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Notification Routing</h1>
          <p className="text-sm text-muted-foreground">
            Escalation, regional, and executive notification policies
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

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : !policies || policies.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            No notification policies configured yet.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {policies.map((policy: NotificationPolicy) => (
            <Card key={policy.id}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bell className="h-4 w-4 text-slate-500" />
                    <CardTitle className="text-base">{policy.name}</CardTitle>
                  </div>
                  <Badge
                    variant="outline"
                    className={policy.is_active ? "border-emerald-300 text-emerald-700" : "border-slate-300 text-slate-500"}
                  >
                    {policy.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Escalation routes */}
                {Array.isArray(policy.escalation_routes) && policy.escalation_routes.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Escalation Routes
                    </p>
                    <div className="space-y-1">
                      {(policy.escalation_routes as Record<string, unknown>[]).map((r, i) => (
                        <div key={i} className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                          <span className="rounded bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800">
                            {String(r.severity ?? "any")}
                          </span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-medium">{String(r.route_to_role ?? "—")}</span>
                          {r.delay_hours !== undefined && (
                            <span className="text-xs text-muted-foreground">
                              after {String(r.delay_hours)}h
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Regional routes */}
                {policy.regional_routes && Object.keys(policy.regional_routes).length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Regional Routes
                    </p>
                    <div className="space-y-1">
                      {Object.entries(policy.regional_routes).map(([region, route]) => (
                        <div key={region} className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                          <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                            {region}
                          </span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-mono text-xs">{String(route)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Executive routes */}
                {Array.isArray(policy.executive_routes) && policy.executive_routes.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Executive Routes
                    </p>
                    <div className="space-y-1">
                      {(policy.executive_routes as Record<string, unknown>[]).map((r, i) => (
                        <div key={i} className="flex items-center gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                          <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                            {String(r.trigger ?? "event")}
                          </span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-medium">{String(r.route_to_role ?? "—")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {!policy.escalation_routes.length &&
                 !Object.keys(policy.regional_routes).length &&
                 !policy.executive_routes.length && (
                  <p className="text-sm text-muted-foreground">No routing rules configured.</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
