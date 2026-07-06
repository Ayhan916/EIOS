"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Bot, Plus, ShieldAlert } from "lucide-react";
import { listModels, listUseCases, listDriftAlerts, registerModel, updateModelStatus, type AIModel } from "@/lib/api/ai-governance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

const RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

function statusBadge(s: string) {
  const colors: Record<string, string> = {
    ACTIVE:    "bg-emerald-100 text-emerald-800",
    DRAFT:     "bg-slate-100 text-slate-600",
    RETIRED:   "bg-gray-100 text-gray-500",
    SUSPENDED: "bg-red-100 text-red-700",
  };
  return <Badge className={colors[s] ?? "bg-slate-100 text-slate-600"}>{s}</Badge>;
}

function riskBadgeClass(level: string) {
  const colors: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-800",
    HIGH:     "bg-orange-100 text-orange-800",
    MEDIUM:   "bg-amber-100 text-amber-800",
    LOW:      "bg-emerald-100 text-emerald-800",
  };
  return colors[level] ?? "bg-slate-100 text-slate-600";
}

function ModelCard({ m }: { m: AIModel }) {
  const { t } = useLanguage();
  const { data: useCases = [] } = useQuery({
    queryKey: ["ai-use-cases", ORG_ID, m.id],
    queryFn: () => listUseCases(ORG_ID, m.id),
    staleTime: 300_000,
  });

  // #72 Drift alerts per model
  const { data: driftAlerts = [] } = useQuery({
    queryKey: ["drift-alerts-model", ORG_ID, m.id],
    queryFn: () => listDriftAlerts(ORG_ID, m.id, false),
    staleTime: 120_000,
    retry: false,
  });

  const activeDrifts = driftAlerts.filter((a) => !a.is_resolved);
  const topDrift = activeDrifts[0] ?? null;

  const topRisk = useCases.length > 0
    ? RISK_ORDER.find((r) => useCases.some((uc) => uc.risk_level === r)) ?? null
    : null;

  const driftSeverityClass: Record<string, string> = {
    CRITICAL: "bg-red-100 text-red-800 border-red-200",
    HIGH:     "bg-orange-100 text-orange-800 border-orange-200",
    MEDIUM:   "bg-amber-100 text-amber-800 border-amber-200",
    LOW:      "bg-slate-100 text-slate-600 border-slate-200",
  };

  return (
    <Card className={activeDrifts.length > 0 ? "border-amber-300" : undefined}>
      <CardContent className="pt-4 pb-4 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-sm leading-tight">{m.name}</p>
          <div className="flex flex-col items-end gap-1">
            {statusBadge(m.ai_status)}
            {topRisk && (
              <Badge className={riskBadgeClass(topRisk)}>
                <ShieldAlert className="h-3 w-3 mr-1" />
                {t("aiGov.riskLabel").replace("{level}", topRisk)}
              </Badge>
            )}
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {m.provider} · {m.model_type}
          {m.model_version ? ` · ${m.model_version}` : ""}
        </p>
        {m.purpose && (
          <p className="text-xs text-muted-foreground line-clamp-2">{m.purpose}</p>
        )}
        {useCases.length > 0 && (
          <p className="text-[10px] text-muted-foreground">{(useCases.length === 1 ? t("aiGov.useCaseCount") : t("aiGov.useCaseCountPlural")).replace("{n}", String(useCases.length))}</p>
        )}
        {/* #72 Drift alert badge */}
        {topDrift && (
          <div className={`flex items-start gap-1.5 rounded border px-2 py-1.5 text-[11px] ${driftSeverityClass[topDrift.severity] ?? driftSeverityClass.LOW}`}>
            <AlertTriangle className="h-3 w-3 flex-shrink-0 mt-px" />
            <div className="min-w-0">
              <span className="font-semibold">{t("aiGov.driftLabel").replace("{severity}", topDrift.severity)}</span>
              <span className="mx-1">·</span>
              <span className="text-[10px]">{topDrift.alert_type.replace(/_/g, " ")}</span>
              {activeDrifts.length > 1 && (
                <span className="ml-1 text-[10px] opacity-70">{t("aiGov.driftMore").replace("{n}", String(activeDrifts.length - 1))}</span>
              )}
              <p className="mt-0.5 line-clamp-1 opacity-80">{topDrift.description}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function AIModelsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "", provider: "anthropic", model_type: "LLM", model_version: "",
  });

  const { data: models = [], isLoading } = useQuery({
    queryKey: ["ai-models", ORG_ID],
    queryFn: () => listModels(ORG_ID),
    retry: false,
  });

  const register = useMutation({
    mutationFn: () => registerModel(ORG_ID, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-models", ORG_ID] });
      setShowForm(false);
      setForm({ name: "", provider: "anthropic", model_type: "LLM", model_version: "" });
    },
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.modelsTitle")}</h1>
          <p className="text-sm text-muted-foreground">
            {t("aiGov.modelsSubtitle")}
          </p>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="mr-1 h-4 w-4" /> {t("aiGov.addModel")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("aiGov.addModel")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {[
                { key: "name", label: t("aiGov.modelName"), placeholder: "e.g. Risk Scorer v1" },
                { key: "provider", label: t("aiGov.provider"), placeholder: "anthropic / openai / custom" },
                { key: "model_version", label: t("aiGov.version"), placeholder: "claude-sonnet-4-6" },
              ].map(({ key, label, placeholder }) => (
                <div key={key} className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">{label}</label>
                  <input
                    className="w-full rounded border border-input px-3 py-2 text-sm"
                    placeholder={placeholder}
                    value={(form as Record<string, string>)[key]}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, [key]: e.target.value }))
                    }
                  />
                </div>
              ))}
              <div className="space-y-1">
                <label className="text-xs font-medium text-muted-foreground">{t("common.type")}</label>
                <select
                  className="w-full rounded border border-input px-3 py-2 text-sm"
                  value={form.model_type}
                  onChange={(e) => setForm((f) => ({ ...f, model_type: e.target.value }))}
                >
                  {["LLM", "CLASSIFICATION", "RISK_SCORING", "EMBEDDING", "RANKING", "FORECASTING", "OTHER"].map(
                    (opt) => <option key={opt}>{opt}</option>
                  )}
                </select>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Button
                size="sm"
                onClick={() => register.mutate()}
                disabled={!form.name || register.isPending}
              >
                {register.isPending ? t("common.loading") : t("common.save")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>
                {t("common.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {models.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Bot className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("aiGov.noModels")}</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {models.map((m) => (
            <ModelCard key={m.id} m={m} />
          ))}
        </div>
      )}
    </div>
  );
}
