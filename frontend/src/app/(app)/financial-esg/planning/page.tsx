"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Plus, ChevronDown, ChevronRight, Calendar, DollarSign, Target } from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface TransitionPlan {
  id: string;
  name: string;
  description?: string;
  financing_needs: number;
  currency: string;
  plan_status: string;
  start_date?: string;
  target_date?: string;
  created_at: string;
}

interface Milestone {
  id: string;
  plan_id: string;
  title: string;
  description?: string;
  due_date?: string;
  milestone_status: string;
  created_at: string;
}

interface ClimateFinance {
  id: string;
  analysis_name: string;
  analysis_year: number;
  transition_investment: number;
  emissions_reduction: number;
  cost_per_ton_reduced?: number;
  roi_percent?: number;
  carbon_price_proxy: number;
  currency: string;
  notes?: string;
  created_at: string;
}

// ── API helpers ───────────────────────────────────────────────────────────────

async function listTransitionPlans(orgId: string): Promise<TransitionPlan[]> {
  const res = await apiClient.get(`/financial-esg/${orgId}/transition-plans`);
  return res.data;
}

async function createTransitionPlan(orgId: string, data: object): Promise<TransitionPlan> {
  const res = await apiClient.post(`/financial-esg/${orgId}/transition-plans`, data);
  return res.data;
}

async function addMilestone(orgId: string, planId: string, data: object): Promise<Milestone> {
  const res = await apiClient.post(`/financial-esg/${orgId}/transition-plans/${planId}/milestones`, data);
  return res.data;
}

async function listClimateFinance(orgId: string): Promise<ClimateFinance[]> {
  const res = await apiClient.get(`/financial-esg/${orgId}/climate-finance`);
  return res.data;
}

async function createClimateFinance(orgId: string, data: object): Promise<ClimateFinance> {
  const res = await apiClient.post(`/financial-esg/${orgId}/climate-finance`, data);
  return res.data;
}

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  active: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  archived: "bg-slate-100 text-slate-400",
  pending: "bg-amber-100 text-amber-700",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_COLORS[status] ?? "bg-slate-100 text-slate-600"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

// ── Milestone row ─────────────────────────────────────────────────────────────

function MilestoneSection({ orgId, plan }: { orgId: string; plan: TransitionPlan }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", due_date: "" });
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (data: object) => addMilestone(orgId, plan.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fin-esg", "plans", orgId] });
      setShowForm(false);
      setForm({ title: "", description: "", due_date: "" });
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) { setError(t("planning.titleRequired")); return; }
    const payload: Record<string, unknown> = { title: form.title };
    if (form.description) payload.description = form.description;
    if (form.due_date) payload.due_date = new Date(form.due_date).toISOString();
    mutation.mutate(payload);
  }

  return (
    <div className="border-t border-slate-100 pt-3 mt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {t("planning.milestones")}
      </button>

      {open && (
        <div className="mt-3 space-y-2">
          {!showForm ? (
            <Button variant="outline" size="sm" onClick={() => setShowForm(true)} className="h-7 text-xs gap-1">
              <Plus className="h-3 w-3" /> {t("planning.addMilestone")}
            </Button>
          ) : (
            <form onSubmit={submit} className="rounded-md border border-slate-200 bg-slate-50 p-3 space-y-2">
              <div>
                <Label className="text-xs">{t("planning.milestoneTitle")} *</Label>
                <Input
                  className="h-8 text-sm mt-1"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder={t("planning.milestoneTitlePlaceholder")}
                />
              </div>
              <div>
                <Label className="text-xs">{t("planning.description")}</Label>
                <Textarea
                  className="text-sm mt-1 min-h-[60px]"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder={t("planning.descriptionPlaceholder")}
                />
              </div>
              <div>
                <Label className="text-xs">{t("planning.dueDate")}</Label>
                <Input
                  type="date"
                  className="h-8 text-sm mt-1"
                  value={form.due_date}
                  onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                />
              </div>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <div className="flex gap-2">
                <Button type="submit" size="sm" className="h-7 text-xs" disabled={mutation.isPending}>
                  {mutation.isPending ? <Spinner className="h-3 w-3" /> : t("planning.save")}
                </Button>
                <Button type="button" variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setShowForm(false)}>
                  {t("planning.cancel")}
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </div>
  );
}

// ── Transition Plans Tab ──────────────────────────────────────────────────────

function TransitionPlansTab({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    description: "",
    financing_needs: "",
    currency: "USD",
    start_date: "",
    target_date: "",
  });

  const { data: plans, isLoading } = useQuery({
    queryKey: ["fin-esg", "plans", orgId],
    queryFn: () => listTransitionPlans(orgId),
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (data: object) => createTransitionPlan(orgId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fin-esg", "plans", orgId] });
      setShowForm(false);
      setForm({ name: "", description: "", financing_needs: "", currency: "USD", start_date: "", target_date: "" });
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) { setError(t("planning.nameRequired")); return; }
    const payload: Record<string, unknown> = {
      name: form.name,
      currency: form.currency || "USD",
      financing_needs: form.financing_needs ? parseFloat(form.financing_needs) : 0,
    };
    if (form.description) payload.description = form.description;
    if (form.start_date) payload.start_date = new Date(form.start_date).toISOString();
    if (form.target_date) payload.target_date = new Date(form.target_date).toISOString();
    mutation.mutate(payload);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{t("planning.transitionPlansTitle")}</h2>
          <p className="text-sm text-slate-500">{t("planning.transitionPlansSubtitle")}</p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)} className="gap-1.5">
            <Plus className="h-4 w-4" /> {t("planning.newPlan")}
          </Button>
        )}
      </div>

      {showForm && (
        <Card className="border-blue-200 bg-blue-50/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("planning.newPlan")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Label>{t("planning.planName")} *</Label>
                  <Input
                    className="mt-1"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder={t("planning.planNamePlaceholder")}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Label>{t("planning.description")}</Label>
                  <Textarea
                    className="mt-1 min-h-[80px]"
                    value={form.description}
                    onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                    placeholder={t("planning.descriptionPlaceholder")}
                  />
                </div>
                <div>
                  <Label>{t("planning.financingNeeds")}</Label>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    className="mt-1"
                    value={form.financing_needs}
                    onChange={(e) => setForm((f) => ({ ...f, financing_needs: e.target.value }))}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label>{t("planning.currency")}</Label>
                  <Input
                    className="mt-1"
                    value={form.currency}
                    onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase().slice(0, 3) }))}
                    placeholder="USD"
                    maxLength={3}
                  />
                </div>
                <div>
                  <Label>{t("planning.startDate")}</Label>
                  <Input
                    type="date"
                    className="mt-1"
                    value={form.start_date}
                    onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>{t("planning.targetDate")}</Label>
                  <Input
                    type="date"
                    className="mt-1"
                    value={form.target_date}
                    onChange={(e) => setForm((f) => ({ ...f, target_date: e.target.value }))}
                  />
                </div>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={mutation.isPending} className="gap-1.5">
                  {mutation.isPending && <Spinner className="h-4 w-4" />}
                  {t("planning.createPlan")}
                </Button>
                <Button type="button" variant="outline" onClick={() => { setShowForm(false); setError(""); }}>
                  {t("planning.cancel")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner />
        </div>
      ) : !plans || plans.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <Target className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("planning.noPlans")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("planning.noPlansDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {plans.map((plan) => (
            <Card key={plan.id}>
              <CardContent className="pt-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-slate-900">{plan.name}</h3>
                      <StatusBadge status={plan.plan_status} />
                    </div>
                    {plan.description && (
                      <p className="mt-1 text-sm text-slate-500 line-clamp-2">{plan.description}</p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <DollarSign className="h-3.5 w-3.5" />
                        {plan.financing_needs.toLocaleString()} {plan.currency}
                      </span>
                      {plan.start_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3.5 w-3.5" />
                          {new Date(plan.start_date).toLocaleDateString()}
                          {plan.target_date && ` → ${new Date(plan.target_date).toLocaleDateString()}`}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <MilestoneSection orgId={orgId} plan={plan} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Climate Finance Tab ───────────────────────────────────────────────────────

function ClimateFinanceTab({ orgId }: { orgId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    analysis_name: "",
    analysis_year: String(new Date().getFullYear()),
    transition_investment: "",
    emissions_reduction: "",
    carbon_price_proxy: "50.0",
    currency: "USD",
    notes: "",
  });

  const { data: analyses, isLoading } = useQuery({
    queryKey: ["fin-esg", "climate-finance", orgId],
    queryFn: () => listClimateFinance(orgId),
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: (data: object) => createClimateFinance(orgId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fin-esg", "climate-finance", orgId] });
      setShowForm(false);
      setForm({
        analysis_name: "",
        analysis_year: String(new Date().getFullYear()),
        transition_investment: "",
        emissions_reduction: "",
        carbon_price_proxy: "50.0",
        currency: "USD",
        notes: "",
      });
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.analysis_name.trim()) { setError(t("planning.nameRequired")); return; }
    if (!form.transition_investment || isNaN(parseFloat(form.transition_investment))) {
      setError(t("planning.investmentRequired")); return;
    }
    if (!form.emissions_reduction || isNaN(parseFloat(form.emissions_reduction))) {
      setError(t("planning.emissionsRequired")); return;
    }
    const payload: Record<string, unknown> = {
      analysis_name: form.analysis_name,
      analysis_year: parseInt(form.analysis_year, 10) || new Date().getFullYear(),
      transition_investment: parseFloat(form.transition_investment),
      emissions_reduction: parseFloat(form.emissions_reduction),
      carbon_price_proxy: parseFloat(form.carbon_price_proxy) || 50,
      currency: form.currency || "USD",
    };
    if (form.notes) payload.notes = form.notes;
    mutation.mutate(payload);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{t("planning.climateFinanceTitle")}</h2>
          <p className="text-sm text-slate-500">{t("planning.climateFinanceSubtitle")}</p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)} className="gap-1.5">
            <Plus className="h-4 w-4" /> {t("planning.newAnalysis")}
          </Button>
        )}
      </div>

      {showForm && (
        <Card className="border-green-200 bg-green-50/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{t("planning.newAnalysis")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <Label>{t("planning.analysisName")} *</Label>
                  <Input
                    className="mt-1"
                    value={form.analysis_name}
                    onChange={(e) => setForm((f) => ({ ...f, analysis_name: e.target.value }))}
                    placeholder={t("planning.analysisNamePlaceholder")}
                  />
                </div>
                <div>
                  <Label>{t("planning.analysisYear")} *</Label>
                  <Input
                    type="number"
                    min="2000"
                    max="2100"
                    className="mt-1"
                    value={form.analysis_year}
                    onChange={(e) => setForm((f) => ({ ...f, analysis_year: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>{t("planning.transitionInvestment")} *</Label>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    className="mt-1"
                    value={form.transition_investment}
                    onChange={(e) => setForm((f) => ({ ...f, transition_investment: e.target.value }))}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label>{t("planning.emissionsReduction")} * (tCO₂e)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    className="mt-1"
                    value={form.emissions_reduction}
                    onChange={(e) => setForm((f) => ({ ...f, emissions_reduction: e.target.value }))}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label>{t("planning.carbonPriceProxy")} ($/t)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    className="mt-1"
                    value={form.carbon_price_proxy}
                    onChange={(e) => setForm((f) => ({ ...f, carbon_price_proxy: e.target.value }))}
                  />
                </div>
                <div>
                  <Label>{t("planning.currency")}</Label>
                  <Input
                    className="mt-1"
                    value={form.currency}
                    onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase().slice(0, 3) }))}
                    placeholder="USD"
                    maxLength={3}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Label>{t("planning.notes")}</Label>
                  <Textarea
                    className="mt-1 min-h-[80px]"
                    value={form.notes}
                    onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                    placeholder={t("planning.notesPlaceholder")}
                  />
                </div>
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={mutation.isPending} className="gap-1.5">
                  {mutation.isPending && <Spinner className="h-4 w-4" />}
                  {t("planning.createAnalysis")}
                </Button>
                <Button type="button" variant="outline" onClick={() => { setShowForm(false); setError(""); }}>
                  {t("planning.cancel")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <Spinner />
        </div>
      ) : !analyses || analyses.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <DollarSign className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("planning.noAnalyses")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("planning.noAnalysesDesc")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {analyses.map((a) => (
            <Card key={a.id}>
              <CardContent className="pt-5 space-y-3">
                <div>
                  <h3 className="font-semibold text-slate-900">{a.analysis_name}</h3>
                  <p className="text-xs text-slate-400">{t("planning.year")} {a.analysis_year}</p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-xs text-slate-500">{t("planning.transitionInvestment")}</p>
                    <p className="font-semibold text-slate-800">
                      {a.transition_investment.toLocaleString()} <span className="text-xs font-normal">{a.currency}</span>
                    </p>
                  </div>
                  <div className="rounded-md bg-slate-50 p-2">
                    <p className="text-xs text-slate-500">{t("planning.emissionsReduction")}</p>
                    <p className="font-semibold text-slate-800">
                      {a.emissions_reduction.toLocaleString()} <span className="text-xs font-normal">tCO₂e</span>
                    </p>
                  </div>
                  {a.cost_per_ton_reduced != null && (
                    <div className="rounded-md bg-blue-50 p-2">
                      <p className="text-xs text-slate-500">{t("planning.costPerTon")}</p>
                      <p className="font-semibold text-blue-700">
                        {a.cost_per_ton_reduced.toFixed(2)} <span className="text-xs font-normal">{a.currency}/t</span>
                      </p>
                    </div>
                  )}
                  {a.roi_percent != null && (
                    <div className={`rounded-md p-2 ${a.roi_percent >= 0 ? "bg-green-50" : "bg-red-50"}`}>
                      <p className="text-xs text-slate-500">{t("planning.roi")}</p>
                      <p className={`font-semibold ${a.roi_percent >= 0 ? "text-green-700" : "text-red-700"}`}>
                        {a.roi_percent.toFixed(1)}%
                      </p>
                    </div>
                  )}
                </div>
                {a.notes && (
                  <p className="text-xs text-slate-500 line-clamp-2">{a.notes}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PlanningPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "default";

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("planning.pageTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("planning.pageSubtitle")}</p>
      </div>

      <Tabs defaultValue="transition-plans">
        <TabsList>
          <TabsTrigger value="transition-plans">{t("planning.tabTransitionPlans")}</TabsTrigger>
          <TabsTrigger value="climate-finance">{t("planning.tabClimateFinance")}</TabsTrigger>
        </TabsList>
        <TabsContent value="transition-plans" className="mt-6">
          <TransitionPlansTab orgId={orgId} />
        </TabsContent>
        <TabsContent value="climate-finance" className="mt-6">
          <ClimateFinanceTab orgId={orgId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
