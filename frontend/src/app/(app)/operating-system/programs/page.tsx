"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, LayersIcon, Loader2, Plus } from "lucide-react";
import { operatingSystemApi, type ESGProgram } from "@/lib/api/operating-system";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

const STATUS_COLOURS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  DRAFT: "bg-gray-100 text-gray-800",
  COMPLETED: "bg-blue-100 text-blue-800",
  ON_HOLD: "bg-yellow-100 text-yellow-800",
  CANCELLED: "bg-red-100 text-red-800",
};

const PROGRAM_TYPES = ["ESG_INITIATIVE", "COMPLIANCE_PROGRAM", "RISK_MITIGATION", "SUSTAINABILITY", "GOVERNANCE", "OTHER"];

export default function ESGProgramsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [programType, setProgramType] = useState("ESG_INITIATIVE");
  const [statusFilter, setStatusFilter] = useState("");

  const { data: programs = [], isLoading } = useQuery({
    queryKey: ["esg-programs", statusFilter],
    queryFn: () => operatingSystemApi.listPrograms({ limit: 100, program_status: statusFilter || undefined }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => operatingSystemApi.createProgram({ title, description: description || undefined, program_type: programType }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["esg-programs"] });
      setShowForm(false);
      setTitle(""); setDescription(""); setProgramType("ESG_INITIATIVE");
    },
  });

  if (isLoading) return <div className="flex justify-center h-64 items-center"><Spinner /></div>;

  const byStatus = programs.reduce<Record<string, number>>((acc, p) => {
    acc[p.program_status] = (acc[p.program_status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <LayersIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.programsTitle")}</h1>
        </div>
        <div className="flex gap-2 items-center">
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">{t("esgOs.allStatuses")}</option>
            {["ACTIVE", "DRAFT", "COMPLETED", "ON_HOLD", "CANCELLED"].map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-1.5" /> {t("esgOs.newProgram")}
          </Button>
        </div>
      </div>

      {/* Summary pills */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(byStatus).map(([status, count]) => (
          <button
            key={status}
            onClick={() => setStatusFilter(statusFilter === status ? "" : status)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${statusFilter === status ? "bg-slate-800 text-white border-slate-800" : STATUS_COLOURS[status] ?? "bg-slate-100 text-slate-700 border-slate-200"}`}
          >
            {status} · {count}
          </button>
        ))}
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="text-sm font-semibold">{t("esgOs.newProgramTitle")}</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("common.title")} *</Label>
                <Input className="mt-1" value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Carbon Reduction Initiative 2026" />
              </div>
              <div>
                <Label className="text-xs">{t("esgOs.programType")}</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={programType} onChange={(e) => setProgramType(e.target.value)}>
                  {PROGRAM_TYPES.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">{t("common.description")}</Label>
              <Input className="mt-1" value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder={t("esgOs.programDescPlaceholder")} />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!title || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> {t("esgOs.programCreated")}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* List */}
      <div className="space-y-3">
        {programs.map((prog) => <ProgramRow key={prog.id} program={prog} />)}
        {programs.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">{t("esgOs.noPrograms")}</div>
        )}
      </div>
    </div>
  );
}

function ProgramRow({ program }: { program: ESGProgram }) {
  const { t } = useLanguage();
  const objCount = program.linked_objectives.length;
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-medium">{program.title}</p>
          {program.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">{program.description}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {program.program_type?.replace(/_/g, " ") ?? t("esgOs.programGeneral")} · {t("esgOs.programCreatedOn").replace("{date}", formatDate(program.created_at))}
          </p>
          {objCount > 0 && (
            <p className="text-xs text-muted-foreground">
              {objCount === 1
                ? t("esgOs.linkedObjectives").replace("{n}", String(objCount))
                : t("esgOs.linkedObjectivesPlural").replace("{n}", String(objCount))}
            </p>
          )}
        </div>
        <Badge className={STATUS_COLOURS[program.program_status] ?? "bg-gray-100 text-gray-800"}>
          {program.program_status}
        </Badge>
      </CardContent>
    </Card>
  );
}
