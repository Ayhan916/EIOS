"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import {
  listObjectives,
  createObjective,
  updateObjectiveStatus,
  type ESGObjective,
} from "@/lib/api/sustainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

const CATEGORIES = ["ENVIRONMENTAL", "SOCIAL", "GOVERNANCE"] as const;
const STATUSES = ["DRAFT", "ACTIVE", "COMPLETED", "CANCELLED"] as const;

function statusColor(s: string) {
  switch (s) {
    case "ACTIVE":    return "bg-blue-100 text-blue-800";
    case "COMPLETED": return "bg-emerald-100 text-emerald-800";
    case "CANCELLED": return "bg-red-100 text-red-800";
    default:          return "bg-slate-100 text-slate-600";
  }
}

function categoryColor(c: string) {
  switch (c) {
    case "ENVIRONMENTAL": return "bg-green-100 text-green-800";
    case "SOCIAL":        return "bg-purple-100 text-purple-800";
    case "GOVERNANCE":    return "bg-blue-100 text-blue-800";
    default:              return "bg-slate-100 text-slate-600";
  }
}

function ObjectiveRow({ obj }: { obj: ESGObjective }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const advance = useMutation({
    mutationFn: (status: string) => updateObjectiveStatus(ORG_ID, obj.id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["objectives", ORG_ID] }),
  });

  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{obj.title}</span>
          <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${categoryColor(obj.category)}`}>
            {obj.category}
          </span>
          <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${statusColor(obj.objective_status)}`}>
            {obj.objective_status}
          </span>
        </div>
        {obj.description && <p className="text-xs text-muted-foreground">{obj.description}</p>}
      </div>
      {obj.objective_status === "DRAFT" && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => advance.mutate("ACTIVE")}
          disabled={advance.isPending}
        >
          Activate
        </Button>
      )}
      {obj.objective_status === "ACTIVE" && (
        <Button
          size="sm"
          variant="outline"
          onClick={() => advance.mutate("COMPLETED")}
          disabled={advance.isPending}
        >
          Complete
        </Button>
      )}

    </div>
  );
}

export default function ObjectivesPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<string>("ENVIRONMENTAL");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const { data: objectives, isLoading } = useQuery({
    queryKey: ["objectives", ORG_ID],
    queryFn: () => listObjectives(ORG_ID),
  });

  const create = useMutation({
    mutationFn: () => createObjective(ORG_ID, { title, category, description }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["objectives", ORG_ID] });
      setTitle("");
      setDescription("");
      setCreating(false);
    },
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("sustain.objectivesTitle")}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t("sustain.objectivesSubtitle")}
          </p>
        </div>
        <Button onClick={() => setCreating(true)} size="sm">
          <Plus className="mr-2 h-4 w-4" /> {t("sustain.addObjective")}
        </Button>
      </div>

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("sustain.addObjective")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="block text-xs font-medium mb-1">{t("common.title")}</label>
              <input
                className="w-full rounded border px-3 py-1.5 text-sm"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Reduce Scope 1 emissions by 30%"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">{t("common.category")}</label>
              <select
                className="w-full rounded border px-3 py-1.5 text-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">{t("common.description")}</label>
              <textarea
                className="w-full rounded border px-3 py-1.5 text-sm"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => create.mutate()}
                disabled={!title || create.isPending}
              >
                {create.isPending ? t("common.loading") : t("common.create")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setCreating(false)}>
                {t("common.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {t("sustain.objectivesTitle")}{objectives ? ` (${objectives.length})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <Spinner />}
          {objectives?.length === 0 && (
            <p className="text-sm text-muted-foreground">{t("sustain.noObjectives")}</p>
          )}
          <div className="space-y-2">
            {objectives?.map((obj) => <ObjectiveRow key={obj.id} obj={obj} />)}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
