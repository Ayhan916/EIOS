"use client";

import { useQuery } from "@tanstack/react-query";
import { Layers } from "lucide-react";
import { listModels, listUseCases } from "@/lib/api/ai-governance";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

function riskColor(r: string) {
  const m: Record<string, string> = {
    LOW:      "bg-emerald-100 text-emerald-800",
    MEDIUM:   "bg-amber-100 text-amber-800",
    HIGH:     "bg-orange-100 text-orange-800",
    CRITICAL: "bg-red-100 text-red-800",
  };
  return m[r] ?? "bg-slate-100 text-slate-600";
}

function approvalColor(s: string) {
  return s === "APPROVED"
    ? "bg-emerald-100 text-emerald-800"
    : s === "REJECTED"
    ? "bg-red-100 text-red-800"
    : "bg-amber-100 text-amber-800";
}

export default function AIUseCasesPage() {
  const { data: models = [], isLoading } = useQuery({
    queryKey: ["ai-models", ORG_ID],
    queryFn: () => listModels(ORG_ID),
    retry: false,
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  if (models.length === 0) {
    return (
      <div className="py-16 text-center text-muted-foreground p-6">
        <Layers className="mx-auto mb-3 h-10 w-10 opacity-30" />
        <p className="text-sm">Register an AI model first to add use cases.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Use Cases</h1>
        <p className="text-sm text-muted-foreground">
          Approved and pending AI use cases per model
        </p>
      </div>
      {models.map((model) => (
        <ModelUseCases key={model.id} modelId={model.id} modelName={model.name} orgId={ORG_ID} />
      ))}
    </div>
  );
}

function ModelUseCases({
  modelId,
  modelName,
  orgId,
}: {
  modelId: string;
  modelName: string;
  orgId: string;
}) {
  const { data: useCases = [] } = useQuery({
    queryKey: ["ai-use-cases", orgId, modelId],
    queryFn: () => listUseCases(orgId, modelId),
    retry: false,
  });

  return (
    <div className="space-y-3">
      <h2 className="text-base font-semibold text-foreground">{modelName}</h2>
      {useCases.length === 0 ? (
        <p className="text-sm text-muted-foreground pl-1">No use cases registered.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {useCases.map((uc) => (
            <Card key={uc.id}>
              <CardContent className="pt-4 pb-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium leading-tight">{uc.title}</p>
                  <Badge className={approvalColor(uc.approval_status)} style={{ whiteSpace: "nowrap" }}>
                    {uc.approval_status}
                  </Badge>
                </div>
                <Badge className={riskColor(uc.risk_level)}>{uc.risk_level} Risk</Badge>
                {uc.business_owner && (
                  <p className="text-xs text-muted-foreground">Owner: {uc.business_owner}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
