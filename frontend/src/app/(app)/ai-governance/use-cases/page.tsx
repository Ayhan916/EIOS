"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Layers, Loader2, Plus } from "lucide-react";
import { listModels, listUseCases, createUseCase, type AIUseCase } from "@/lib/api/ai-governance";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

const RISK_COLOUR: Record<string, string> = {
  LOW: "bg-emerald-100 text-emerald-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
};

const APPROVAL_COLOUR: Record<string, string> = {
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-red-100 text-red-800",
  PENDING: "bg-amber-100 text-amber-800",
};

function ModelUseCases({ modelId, modelName }: { modelId: string; modelName: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [riskLevel, setRiskLevel] = useState("MEDIUM");
  const [bizOwner, setBizOwner] = useState("");
  const [desc, setDesc] = useState("");

  const { data: useCases = [] } = useQuery<AIUseCase[]>({
    queryKey: ["ai-use-cases", ORG_ID, modelId],
    queryFn: () => listUseCases(ORG_ID, modelId),
    retry: false,
  });

  const add = useMutation({
    mutationFn: () => createUseCase(ORG_ID, modelId, {
      title,
      description: desc || undefined,
      risk_level: riskLevel,
      business_owner: bizOwner || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-use-cases", ORG_ID, modelId] });
      setShowForm(false);
      setTitle(""); setRiskLevel("MEDIUM"); setBizOwner(""); setDesc("");
    },
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">{modelName}</h2>
        <Button size="sm" variant="outline" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-3.5 w-3.5 mr-1" /> {t("aiGov.addUseCase")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 pb-4 space-y-3">
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Title *</Label>
                <Input className="mt-1" value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Risk scoring for suppliers" />
              </div>
              <div>
                <Label className="text-xs">Risk Level</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Business Owner</Label>
                <Input className="mt-1" value={bizOwner} onChange={(e) => setBizOwner(e.target.value)}
                  placeholder="Name or team" />
              </div>
              <div>
                <Label className="text-xs">Description</Label>
                <Input className="mt-1" value={desc} onChange={(e) => setDesc(e.target.value)}
                  placeholder="Briefly describe the use case…" />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!title || add.isPending} onClick={() => add.mutate()}>
                {add.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {add.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Use case registered.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {useCases.length === 0 ? (
        <p className="text-sm text-muted-foreground pl-1">{t("aiGov.noUseCases")}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {useCases.map((uc) => (
            <Card key={uc.id}>
              <CardContent className="pt-4 pb-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium leading-tight">{uc.title}</p>
                  <Badge className={APPROVAL_COLOUR[uc.approval_status] ?? "bg-slate-100 text-slate-600"}>
                    {uc.approval_status}
                  </Badge>
                </div>
                <Badge className={RISK_COLOUR[uc.risk_level] ?? "bg-slate-100 text-slate-600"}>
                  {uc.risk_level} Risk
                </Badge>
                {uc.business_owner && (
                  <p className="text-xs text-muted-foreground">Owner: {uc.business_owner}</p>
                )}
                {uc.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">{uc.description}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AIUseCasesPage() {
  const { t } = useLanguage();
  const { data: models = [], isLoading } = useQuery({
    queryKey: ["ai-models", ORG_ID],
    queryFn: () => listModels(ORG_ID),
    retry: false,
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.useCasesTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("aiGov.useCasesSubtitle")}</p>
      </div>

      {models.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Layers className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">Register an AI model first to add use cases.</p>
        </div>
      ) : (
        models.map((model) => (
          <ModelUseCases key={model.id} modelId={model.id} modelName={model.name} />
        ))
      )}
    </div>
  );
}
