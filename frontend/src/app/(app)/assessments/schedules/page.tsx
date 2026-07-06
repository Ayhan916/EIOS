"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  CalendarClock,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AssessmentSchedule {
  id: string;
  organization_id: string;
  supplier_id: string;
  frequency_days: number;
  last_triggered_at: string | null;
  next_due_at: string;
  template_assessment_id: string | null;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

interface ExecSupplier {
  id: string;
  name: string;
}

interface ScheduleFormState {
  supplier_id: string;
  frequency_days: string;
  template_assessment_id: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  const now = Date.now();
  const due = new Date(dateStr).getTime();
  return Math.ceil((due - now) / 86_400_000);
}

function daysSince(dateStr: string): number {
  const now = Date.now();
  const ts = new Date(dateStr).getTime();
  return Math.floor((now - ts) / 86_400_000);
}

function statusBadge(schedule: AssessmentSchedule): { label: string; cls: string } {
  if (!schedule.is_active) return { label: "inactive", cls: "bg-slate-100 text-slate-600" };
  if (daysUntil(schedule.next_due_at) < 0) return { label: "overdue", cls: "bg-red-100 text-red-700" };
  return { label: "active", cls: "bg-emerald-100 text-emerald-800" };
}

const DEFAULT_FORM: ScheduleFormState = {
  supplier_id: "",
  frequency_days: "90",
  template_assessment_id: "",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AssessmentSchedulesPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ScheduleFormState>(DEFAULT_FORM);
  const [formError, setFormError] = useState("");
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const { data: schedules = [], isLoading } = useQuery<AssessmentSchedule[]>({
    queryKey: ["assessment-schedules"],
    queryFn: () => apiClient.get("/assessments/schedules?limit=200").then((r) => r.data),
  });

  const { data: suppliers = [] } = useQuery<ExecSupplier[]>({
    queryKey: ["exec-suppliers-names"],
    queryFn: () => apiClient.get("/executive/suppliers").then((r) => r.data),
    staleTime: 60_000,
  });

  const supplierMap = new Map(suppliers.map((s) => [s.id, s.name]));

  const create = useMutation({
    mutationFn: () => {
      const days = parseInt(form.frequency_days, 10);
      if (!form.supplier_id || isNaN(days) || days < 7 || days > 3650) {
        throw new Error("validation");
      }
      return apiClient.post("/assessments/schedules", {
        supplier_id: form.supplier_id,
        frequency_days: days,
        template_assessment_id: form.template_assessment_id || undefined,
      }).then((r) => r.data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assessment-schedules"] });
      qc.invalidateQueries({ queryKey: ["assessment-schedules-supplier-ids"] });
      setShowForm(false);
      setForm(DEFAULT_FORM);
      setFormError("");
    },
    onError: (err: Error) => {
      setFormError(err.message === "validation" ? t("schedules.validationError") : t("schedules.createError"));
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/assessments/schedules/${id}`).then(() => id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assessment-schedules"] });
      qc.invalidateQueries({ queryKey: ["assessment-schedules-supplier-ids"] });
      setPendingDelete(null);
    },
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    create.mutate();
  }

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link href="/assessments" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-3.5 w-3.5" />{t("nav.assessments")}
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <CalendarClock className="h-7 w-7 text-primary mt-0.5 shrink-0" />
          <div>
            <h1 className="text-2xl font-semibold">{t("schedules.title")}</h1>
            <p className="text-sm text-muted-foreground">{t("schedules.subtitle")}</p>
          </div>
        </div>
        <Button size="sm" onClick={() => { setShowForm((v) => !v); setFormError(""); }}>
          {showForm ? <X className="h-4 w-4 mr-1.5" /> : <Plus className="h-4 w-4 mr-1.5" />}
          {t("schedules.newSchedule")}
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card className="border-primary/30 bg-muted/20">
          <CardContent className="py-5">
            <h2 className="text-sm font-semibold mb-4">{t("schedules.createTitle")}</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Supplier */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5">
                    {t("schedules.supplier")} <span className="text-red-500">*</span>
                  </label>
                  <select
                    className="h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    value={form.supplier_id}
                    onChange={(e) => setForm((f) => ({ ...f, supplier_id: e.target.value }))}
                    required
                  >
                    <option value="">{t("schedules.selectSupplier")}</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                {/* Frequency */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5">
                    {t("schedules.frequency")} <span className="text-muted-foreground/60">({t("schedules.frequencyHint")})</span>
                  </label>
                  <input
                    type="number"
                    min={7}
                    max={3650}
                    required
                    className="h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    value={form.frequency_days}
                    onChange={(e) => setForm((f) => ({ ...f, frequency_days: e.target.value }))}
                  />
                </div>

                {/* Template */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5">
                    {t("schedules.template")}
                  </label>
                  <input
                    type="text"
                    placeholder={t("schedules.templatePlaceholder")}
                    className="h-9 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono"
                    value={form.template_assessment_id}
                    onChange={(e) => setForm((f) => ({ ...f, template_assessment_id: e.target.value }))}
                  />
                </div>
              </div>

              {formError && (
                <p className="text-sm text-red-600">{formError}</p>
              )}

              <div className="flex gap-2">
                <Button type="submit" size="sm" disabled={create.isPending}>
                  {create.isPending
                    ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />{t("schedules.creating")}</>
                    : <><Plus className="h-3.5 w-3.5 mr-1.5" />{t("schedules.newSchedule")}</>}
                </Button>
                <Button type="button" size="sm" variant="ghost" onClick={() => { setShowForm(false); setForm(DEFAULT_FORM); setFormError(""); }}>
                  {t("common.cancel")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Delete confirmation */}
      {pendingDelete && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-4 flex items-center justify-between gap-4">
            <p className="text-sm text-red-800">{t("schedules.deleteConfirm")}</p>
            <div className="flex gap-2 shrink-0">
              <Button
                size="sm"
                variant="destructive"
                className="h-8 text-xs"
                disabled={remove.isPending}
                onClick={() => remove.mutate(pendingDelete)}
              >
                {remove.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : t("common.delete")}
              </Button>
              <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setPendingDelete(null)}>
                {t("common.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">
          <CalendarDays className="mx-auto mb-3 h-10 w-10 opacity-25" />
          <p className="text-sm font-medium">{t("schedules.noSchedules")}</p>
          <p className="text-xs mt-1 max-w-sm mx-auto">{t("schedules.noSchedulesDesc")}</p>
        </div>
      ) : (
        <div className="rounded-md border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="border-b">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("schedules.supplier")}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("schedules.frequency")}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("schedules.nextDue")}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("schedules.lastTriggered")}</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">{t("schedules.status")}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y">
              {schedules.map((s) => {
                const { label, cls } = statusBadge(s);
                const daysToGo = daysUntil(s.next_due_at);
                const sinceLast = s.last_triggered_at ? daysSince(s.last_triggered_at) : null;

                return (
                  <tr key={s.id} className="hover:bg-muted/30 transition-colors">
                    {/* Supplier */}
                    <td className="px-4 py-3">
                      <Link href={`/suppliers/${s.supplier_id}`} className="font-medium hover:underline">
                        {supplierMap.get(s.supplier_id) ?? s.supplier_id.slice(0, 12) + "…"}
                      </Link>
                      <p className="text-[11px] font-mono text-muted-foreground">{s.supplier_id.slice(0, 8)}…</p>
                    </td>

                    {/* Frequency */}
                    <td className="px-4 py-3 text-muted-foreground">
                      {t("schedules.every").replace("{n}", String(s.frequency_days))}
                    </td>

                    {/* Next due */}
                    <td className="px-4 py-3">
                      <p>{formatDate(s.next_due_at)}</p>
                      <p className={`text-[11px] font-medium ${daysToGo < 0 ? "text-red-600" : daysToGo < 14 ? "text-amber-600" : "text-muted-foreground"}`}>
                        {daysToGo < 0
                          ? t("schedules.daysOverdue").replace("{n}", String(Math.abs(daysToGo)))
                          : daysToGo === 0
                          ? t("schedules.dueToday")
                          : t("schedules.dueIn").replace("{n}", String(daysToGo))}
                      </p>
                    </td>

                    {/* Last triggered */}
                    <td className="px-4 py-3 text-muted-foreground text-sm">
                      {sinceLast === null
                        ? <span className="text-muted-foreground/60 italic">{t("schedules.never")}</span>
                        : <><p>{formatDate(s.last_triggered_at!)}</p><p className="text-[11px]">{t("schedules.daysAgo").replace("{n}", String(sinceLast))}</p></>}
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <Badge className={cls}>{t(`schedules.${label}` as "schedules.active")}</Badge>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-muted-foreground hover:text-red-600"
                        onClick={() => setPendingDelete(s.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Summary */}
      {schedules.length > 0 && (
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <span>{t("schedules.totalCount").replace("{n}", String(schedules.length))}</span>
          <span>{schedules.filter((s) => s.is_active).length} {t("schedules.active").toLowerCase()}</span>
          <span className={schedules.filter((s) => daysUntil(s.next_due_at) < 0 && s.is_active).length > 0 ? "text-red-600 font-medium" : ""}>
            {schedules.filter((s) => daysUntil(s.next_due_at) < 0 && s.is_active).length} {t("schedules.overdue").toLowerCase()}
          </span>
        </div>
      )}
    </div>
  );
}
