"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Plus, Shield } from "lucide-react";
import { listControls, createControl } from "@/lib/api/ai-governance";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

const TYPE_COLOURS: Record<string, string> = {
  PREVENTIVE: "bg-blue-100 text-blue-800",
  DETECTIVE: "bg-purple-100 text-purple-800",
  CORRECTIVE: "bg-amber-100 text-amber-800",
};

export default function AIControlsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [ctrlType, setCtrlType] = useState("PREVENTIVE");
  const [description, setDescription] = useState("");

  const { data: controls = [], isLoading } = useQuery({
    queryKey: ["ai-controls", ORG_ID],
    queryFn: () => listControls(ORG_ID),
    retry: false,
  });

  const create = useMutation({
    mutationFn: () => createControl(ORG_ID, { name, control_type: ctrlType, description: description || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ai-controls", ORG_ID] });
      setShowForm(false);
      setName(""); setCtrlType("PREVENTIVE"); setDescription("");
    },
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.controlsTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("aiGov.controlsSubtitle")}</p>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1.5" /> {t("aiGov.addControl")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Name *</Label>
                <Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Output filtering" />
              </div>
              <div>
                <Label className="text-xs">Type</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={ctrlType} onChange={(e) => setCtrlType(e.target.value)}>
                  {["PREVENTIVE", "DETECTIVE", "CORRECTIVE"].map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Input className="mt-1" value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the control…" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!name || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Control saved.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {controls.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Shield className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("aiGov.noControls")}</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {controls.map((c) => (
            <Card key={c.id}>
              <CardContent className="pt-4 pb-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold leading-tight">{c.name}</p>
                  <Badge className={TYPE_COLOURS[c.control_type] ?? "bg-slate-100 text-slate-600"}>
                    {c.control_type}
                  </Badge>
                </div>
                {c.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">{c.description}</p>
                )}
                {!c.is_active && (
                  <Badge className="bg-slate-100 text-slate-500">{t("common.inactive")}</Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
