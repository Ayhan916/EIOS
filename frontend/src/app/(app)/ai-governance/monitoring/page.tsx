"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";
import { listModels, listDriftAlerts } from "@/lib/api/ai-governance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

function severityColor(s: string) {
  const m: Record<string, string> = {
    LOW:      "bg-emerald-100 text-emerald-800",
    MEDIUM:   "bg-amber-100 text-amber-800",
    HIGH:     "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800",
  };
  return m[s] ?? "bg-slate-100 text-slate-600";
}

function ModelDriftSection({ modelId, modelName }: { modelId: string; modelName: string }) {
  const { data: alerts = [], isLoading } = useQuery({
    queryKey: ["drift-alerts", ORG_ID, modelId],
    queryFn: () => listDriftAlerts(ORG_ID, modelId, false),
    staleTime: 60_000,
  });

  if (isLoading) return <div className="py-2"><Spinner /></div>;
  if (alerts.length === 0) return null;

  const openCount = alerts.filter((a) => !a.is_resolved).length;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-700">{modelName}</p>
        {openCount > 0 && (
          <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-semibold text-orange-700">
            {openCount} open
          </span>
        )}
      </div>
      <div className="space-y-0">
        {alerts.map((alert) => (
          <div key={alert.id} className="flex items-start gap-3 py-2.5 border-b last:border-0">
            <Badge className={`${severityColor(alert.severity)} flex-shrink-0`}>{alert.severity}</Badge>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium">{alert.alert_type.replace(/_/g, " ")}</p>
              <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{alert.description}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                Detected {new Date(alert.detected_at).toLocaleString()}
                {alert.resolved_at && ` · Resolved ${new Date(alert.resolved_at).toLocaleString()}`}
              </p>
            </div>
            {alert.is_resolved ? (
              <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-medium flex-shrink-0 mt-0.5">
                <CheckCircle2 className="h-3 w-3" /> Resolved
              </span>
            ) : (
              <span className="h-2 w-2 rounded-full bg-orange-500 mt-1.5 flex-shrink-0" title="Open" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AIMonitoringPage() {
  const { t } = useLanguage();
  const { data: models = [], isLoading } = useQuery({
    queryKey: ["ai-models", ORG_ID],
    queryFn: () => listModels(ORG_ID),
    staleTime: 300_000,
  });

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Activity className="h-6 w-6 text-primary" />
          {t("aiGov.monitoringTitle")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("aiGov.monitoringSubtitle")}
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : models.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Activity className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("aiGov.noModels")}</p>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-orange-500" />
              Drift Alerts by Model
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y">
              {models.map((m) => (
                <div key={m.id} className="py-4 first:pt-0 last:pb-0">
                  <ModelDriftSection modelId={m.id} modelName={m.name} />
                </div>
              ))}
            </div>
            {models.length > 0 && (
              <p className="mt-4 text-xs text-muted-foreground text-center">
                Showing alerts for {models.length} model{models.length !== 1 ? "s" : ""}. Models with no alerts are hidden.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
