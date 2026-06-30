"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle, FileSearch, Loader2, ShieldAlert } from "lucide-react";
import { listIncidents, resolveIncident, type AIIncident } from "@/lib/api/ai-governance";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

function IncidentCreateButtons({ inc }: { inc: AIIncident }) {
  const [findingCreated, setFindingCreated] = useState(false);
  const [riskCreated, setRiskCreated] = useState(false);

  const createFinding = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/api/v1/findings/", {
        title: `[AI Incident] ${inc.incident_type.replace(/_/g, " ")}`,
        severity: inc.severity,
        status: "Open",
      });
      return res.data;
    },
    onSuccess: () => setFindingCreated(true),
  });

  const createRisk = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/api/v1/risks/", {
        title: `[AI Incident] ${inc.incident_type.replace(/_/g, " ")}`,
        risk_level: inc.severity.charAt(0) + inc.severity.slice(1).toLowerCase(),
        status: "Draft",
        category: "AI Governance",
      });
      return res.data;
    },
    onSuccess: () => setRiskCreated(true),
  });

  return (
    <div className="flex items-center gap-1.5 flex-wrap mt-1">
      {findingCreated ? (
        <span className="flex items-center gap-0.5 text-[10px] text-emerald-600 font-medium">
          <CheckCircle className="h-3 w-3" /> Finding created
        </span>
      ) : (
        <button
          onClick={() => createFinding.mutate()}
          disabled={createFinding.isPending || inc.is_resolved}
          className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-40"
        >
          {createFinding.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileSearch className="h-3 w-3" />}
          Create Finding
        </button>
      )}
      {riskCreated ? (
        <span className="flex items-center gap-0.5 text-[10px] text-emerald-600 font-medium">
          <CheckCircle className="h-3 w-3" /> Risk created
        </span>
      ) : (
        <button
          onClick={() => createRisk.mutate()}
          disabled={createRisk.isPending || inc.is_resolved}
          className="inline-flex items-center gap-1 rounded bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700 hover:bg-orange-100 disabled:opacity-40"
        >
          {createRisk.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <ShieldAlert className="h-3 w-3" />}
          Create Risk
        </button>
      )}
    </div>
  );
}

function severityColor(s: string) {
  const m: Record<string, string> = {
    LOW:      "bg-emerald-100 text-emerald-800",
    MEDIUM:   "bg-amber-100 text-amber-800",
    HIGH:     "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800",
  };
  return m[s] ?? "bg-slate-100 text-slate-600";
}

export default function AIIncidentsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [unresolvedOnly, setUnresolvedOnly] = useState(false);

  const { data: incidents = [], isLoading } = useQuery({
    queryKey: ["ai-incidents", ORG_ID, unresolvedOnly],
    queryFn: () => listIncidents(ORG_ID, unresolvedOnly),
    retry: false,
  });

  const resolve = useMutation({
    mutationFn: (incidentId: string) => resolveIncident(ORG_ID, incidentId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["ai-incidents", ORG_ID] }),
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.incidentsTitle")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("aiGov.incidentsSubtitle")}
          </p>
        </div>
        <Button
          size="sm"
          variant={unresolvedOnly ? "default" : "outline"}
          onClick={() => setUnresolvedOnly((v) => !v)}
        >
          {unresolvedOnly ? "All Incidents" : "Open Only"}
        </Button>
      </div>

      {incidents.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <AlertTriangle className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("aiGov.noIncidents")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((inc) => (
            <Card key={inc.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={severityColor(inc.severity)}>
                        {inc.severity}
                      </Badge>
                      <Badge className="bg-slate-100 text-slate-600">
                        {inc.incident_type.replace("_", " ")}
                      </Badge>
                      {inc.is_resolved && (
                        <Badge className="bg-emerald-100 text-emerald-800">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Resolved
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-foreground leading-snug mt-1">
                      {inc.description}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(inc.created_at).toLocaleString()}
                      {inc.reported_by ? ` · Reported by ${inc.reported_by}` : ""}
                    </p>
                    <IncidentCreateButtons inc={inc} />
                  </div>
                  {!inc.is_resolved && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => resolve.mutate(inc.id)}
                      disabled={resolve.isPending}
                    >
                      Resolve
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
