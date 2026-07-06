"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ClipboardList,
  FileSearch,
  Loader2,
  MailCheck,
  Plus,
  ShieldCheck,
  Users,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Supplier { id: string; name: string; }

interface EvidenceRequest {
  id: string;
  supplier_id: string;
  title: string;
  description: string;
  due_date: string | null;
  evidence_status: string;
  created_at: string;
}

interface RemediationPlan {
  id: string;
  supplier_id: string;
  finding_id: string;
  title: string;
  description: string;
  remediation_status: string;
  completion_percentage: number;
  due_date: string | null;
  verified_by: string | null;
  created_at: string;
}

interface QuestionnaireAssignment {
  id: string;
  supplier_id: string;
  template_id: string;
  organization_id: string;
  assignment_status: string;
  questionnaire_pct: number;
  assigned_at: string;
}

// ── Colour maps ───────────────────────────────────────────────────────────────

const EV_COLOURS: Record<string, string> = {
  requested: "bg-amber-100 text-amber-800",
  submitted: "bg-blue-100 text-blue-800",
  approved:  "bg-green-100 text-green-800",
  rejected:  "bg-red-100 text-red-800",
};

const REM_COLOURS: Record<string, string> = {
  open:        "bg-amber-100 text-amber-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed:   "bg-green-100 text-green-800",
  verified:    "bg-emerald-100 text-emerald-800",
  overdue:     "bg-red-100 text-red-800",
};

const Q_COLOURS: Record<string, string> = {
  assigned:  "bg-amber-100 text-amber-800",
  in_progress: "bg-blue-100 text-blue-800",
  submitted: "bg-purple-100 text-purple-800",
  reviewed:  "bg-green-100 text-green-800",
  approved:  "bg-emerald-100 text-emerald-800",
};

// ── Supplier selector ─────────────────────────────────────────────────────────

function SupplierSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useLanguage();
  const { data: suppliers = [] } = useQuery<Supplier[]>({
    queryKey: ["suppliers-list-minimal"],
    queryFn: () => apiClient.get("/suppliers/?limit=500").then((r) => r.data.items ?? r.data),
    staleTime: 5 * 60_000,
  });
  return (
    <div>
      <Label className="text-xs">{t("portal.supplierLabel")}</Label>
      <select
        className="mt-1 h-9 w-full max-w-sm rounded-md border border-input bg-background px-3 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">— {t("portal.supplierLabel")} —</option>
        {suppliers.map((s) => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>
    </div>
  );
}

// ── Invitations Tab ───────────────────────────────────────────────────────────

function InvitationsTab() {
  const { t } = useLanguage();
  const [supplierId, setSupplierId] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("supplier_user");
  const [token, setToken] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const invite = useMutation({
    mutationFn: () =>
      apiClient.post("/supplier-portal/internal/invitations", { supplier_id: supplierId, email, role }).then((r) => r.data),
    onSuccess: (data) => {
      setToken(data.invite_token ?? null);
      setEmail(""); setSupplierId(""); setRole("supplier_user");
      setShowForm(false);
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">{t("portal.inviteTitle")}</p>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1" /> {t("portal.invite")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <SupplierSelect value={supplierId} onChange={setSupplierId} />
            <div>
              <Label className="text-xs">{t("portal.emailLabel")}</Label>
              <Input className="mt-1" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="supplier@company.com" />
            </div>
            <div>
              <Label className="text-xs">{t("portal.roleLabel")}</Label>
              <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="supplier_user">Supplier User</option>
                <option value="supplier_admin">Supplier Admin</option>
                <option value="supplier_readonly">Read-Only</option>
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!supplierId || !email || invite.isPending} onClick={() => invite.mutate()}>
                {invite.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                <MailCheck className="h-4 w-4 mr-1" /> {t("portal.invite")}
              </Button>
            </div>
            {invite.isError && (
              <p className="text-xs text-red-600">Failed to send invitation.</p>
            )}
          </CardContent>
        </Card>
      )}

      {token && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4 pb-4">
            <p className="text-sm font-medium text-green-800 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" /> {t("portal.inviteSuccess")}
            </p>
            <p className="text-xs font-mono mt-2 break-all text-green-700 bg-green-100 p-2 rounded">{token}</p>
            <p className="text-[10px] text-green-600 mt-1">Share this token with the supplier to activate their account.</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          <MailCheck className="mx-auto mb-2 h-8 w-8 opacity-30" />
          Use the form above to invite supplier contacts to the Supplier Portal.
          They will receive an activation link via email.
        </CardContent>
      </Card>
    </div>
  );
}

// ── Evidence Requests Tab ─────────────────────────────────────────────────────

function EvidenceTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [supplierId, setSupplierId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [evTitle, setEvTitle] = useState("");
  const [evDesc, setEvDesc] = useState("");
  const [evDue, setEvDue] = useState("");

  const { data: requests = [], isLoading } = useQuery<EvidenceRequest[]>({
    queryKey: ["portal-evidence", supplierId],
    queryFn: () => apiClient.get(`/supplier-portal/internal/suppliers/${supplierId}/evidence/requests`).then((r) => r.data),
    enabled: !!supplierId,
  });

  const create = useMutation({
    mutationFn: () => apiClient.post(`/supplier-portal/internal/suppliers/${supplierId}/evidence/requests`, {
      title: evTitle,
      description: evDesc || "",
      due_date: evDue ? new Date(evDue).toISOString() : null,
    }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portal-evidence", supplierId] });
      setShowForm(false); setEvTitle(""); setEvDesc(""); setEvDue("");
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <SupplierSelect value={supplierId} onChange={(v) => { setSupplierId(v); setShowForm(false); }} />
        {supplierId && (
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-1" /> {t("portal.newRequest")}
          </Button>
        )}
      </div>

      {showForm && supplierId && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="text-sm font-semibold">{t("portal.newRequest")}</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("portal.requestTitle")} *</Label>
                <Input className="mt-1" value={evTitle} onChange={(e) => setEvTitle(e.target.value)}
                  placeholder="e.g. ISO 14001 Certificate 2025" />
              </div>
              <div>
                <Label className="text-xs">{t("portal.dueDate")}</Label>
                <Input className="mt-1" type="date" value={evDue} onChange={(e) => setEvDue(e.target.value)} />
              </div>
            </div>
            <div>
              <Label className="text-xs">{t("portal.requestDesc")}</Label>
              <Input className="mt-1" value={evDesc} onChange={(e) => setEvDesc(e.target.value)}
                placeholder="What evidence is required?" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!evTitle || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("portal.createRequest")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> {t("portal.requestCreated")}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {!supplierId && (
        <div className="text-center py-12 text-muted-foreground text-sm">{t("portal.noSupplierSelected")}</div>
      )}

      {supplierId && isLoading && <div className="flex justify-center py-8"><Spinner /></div>}

      {supplierId && !isLoading && (
        <div className="space-y-3">
          {requests.map((req) => (
            <Card key={req.id}>
              <CardContent className="py-4 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <p className="font-medium">{req.title}</p>
                  {req.description && <p className="text-sm text-muted-foreground">{req.description}</p>}
                  <p className="text-xs text-muted-foreground">
                    Created {formatDate(req.created_at)}
                    {req.due_date && ` · Due ${formatDate(req.due_date)}`}
                  </p>
                </div>
                <Badge className={EV_COLOURS[req.evidence_status] ?? "bg-slate-100 text-slate-600"}>
                  {req.evidence_status}
                </Badge>
              </CardContent>
            </Card>
          ))}
          {requests.length === 0 && (
            <div className="text-center py-8 text-muted-foreground text-sm">{t("portal.noRequests")}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Remediation Plans Tab ─────────────────────────────────────────────────────

function RemediationTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [supplierId, setSupplierId] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [planTitle, setPlanTitle] = useState("");
  const [findingId, setFindingId] = useState("");
  const [planDesc, setPlanDesc] = useState("");
  const [planDue, setPlanDue] = useState("");

  const { data: plans = [], isLoading } = useQuery<RemediationPlan[]>({
    queryKey: ["portal-remediation", supplierId],
    queryFn: () => apiClient.get(`/supplier-portal/internal/suppliers/${supplierId}/remediation`).then((r) => r.data),
    enabled: !!supplierId,
  });

  const create = useMutation({
    mutationFn: () => apiClient.post(`/supplier-portal/internal/suppliers/${supplierId}/remediation`, {
      title: planTitle,
      finding_id: findingId,
      description: planDesc || "",
      due_date: planDue ? new Date(planDue).toISOString() : null,
    }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portal-remediation", supplierId] });
      setShowForm(false); setPlanTitle(""); setFindingId(""); setPlanDesc(""); setPlanDue("");
    },
  });

  const verify = useMutation({
    mutationFn: (planId: string) =>
      apiClient.post(`/supplier-portal/internal/remediation/${planId}/verify`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portal-remediation", supplierId] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <SupplierSelect value={supplierId} onChange={(v) => { setSupplierId(v); setShowForm(false); }} />
        {supplierId && (
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-1" /> {t("portal.newPlan")}
          </Button>
        )}
      </div>

      {showForm && supplierId && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="text-sm font-semibold">{t("portal.newPlan")}</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t("portal.planTitle")} *</Label>
                <Input className="mt-1" value={planTitle} onChange={(e) => setPlanTitle(e.target.value)}
                  placeholder="e.g. Remediate child labour risk" />
              </div>
              <div>
                <Label className="text-xs">{t("portal.findingId")} *</Label>
                <Input className="mt-1" value={findingId} onChange={(e) => setFindingId(e.target.value)}
                  placeholder="Finding UUID" />
              </div>
              <div>
                <Label className="text-xs">{t("portal.requestDesc")}</Label>
                <Input className="mt-1" value={planDesc} onChange={(e) => setPlanDesc(e.target.value)}
                  placeholder="Steps and scope…" />
              </div>
              <div>
                <Label className="text-xs">{t("portal.dueDate")}</Label>
                <Input className="mt-1" type="date" value={planDue} onChange={(e) => setPlanDue(e.target.value)} />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!planTitle || !findingId || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("portal.createPlan")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> {t("portal.planCreated")}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {!supplierId && (
        <div className="text-center py-12 text-muted-foreground text-sm">{t("portal.noSupplierSelected")}</div>
      )}

      {supplierId && isLoading && <div className="flex justify-center py-8"><Spinner /></div>}

      {supplierId && !isLoading && (
        <div className="space-y-3">
          {plans.map((plan) => (
            <Card key={plan.id}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1 flex-1 min-w-0">
                    <p className="font-medium">{plan.title}</p>
                    {plan.description && <p className="text-sm text-muted-foreground line-clamp-2">{plan.description}</p>}
                    <p className="text-xs text-muted-foreground">
                      Created {formatDate(plan.created_at)}
                      {plan.due_date && ` · Due ${formatDate(plan.due_date)}`}
                    </p>
                    {/* Progress bar */}
                    <div className="flex items-center gap-2 mt-1.5">
                      <div className="flex-1 bg-muted rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-primary transition-all"
                          style={{ width: `${plan.completion_percentage}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-8 text-right">{plan.completion_percentage}%</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <Badge className={REM_COLOURS[plan.remediation_status] ?? "bg-slate-100 text-slate-600"}>
                      {plan.remediation_status}
                    </Badge>
                    {plan.remediation_status === "completed" && !plan.verified_by && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs"
                        disabled={verify.isPending}
                        onClick={() => verify.mutate(plan.id)}
                      >
                        <ShieldCheck className="h-3 w-3 mr-1" /> {t("portal.verify")}
                      </Button>
                    )}
                    {plan.verified_by && (
                      <span className="text-xs text-emerald-700 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> {t("portal.verified")}
                      </span>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          {plans.length === 0 && (
            <div className="text-center py-8 text-muted-foreground text-sm">{t("portal.noPlans")}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Questionnaires Tab ────────────────────────────────────────────────────────

function QuestionnairesTab() {
  const { t } = useLanguage();
  const { data: assignments = [], isLoading } = useQuery<QuestionnaireAssignment[]>({
    queryKey: ["portal-questionnaires"],
    queryFn: () => apiClient.get("/supplier-portal/internal/questionnaires/assignments").then((r) => r.data),
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center">
        <p className="text-sm text-muted-foreground">{assignments.length} assignment{assignments.length !== 1 ? "s" : ""}</p>
      </div>
      {assignments.map((a) => (
        <Card key={a.id}>
          <CardContent className="py-4 flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="font-medium font-mono text-sm">Template: {a.template_id.slice(0, 8)}…</p>
              <p className="text-xs text-muted-foreground">Supplier: {a.supplier_id.slice(0, 8)}…</p>
              <p className="text-xs text-muted-foreground">Assigned {formatDate(a.assigned_at)}</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Badge className={Q_COLOURS[a.assignment_status] ?? "bg-slate-100 text-slate-600"}>
                {a.assignment_status}
              </Badge>
              <div className="flex items-center gap-1.5 w-28">
                <div className="flex-1 bg-muted rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-blue-500"
                    style={{ width: `${a.questionnaire_pct ?? 0}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground w-8 text-right">{a.questionnaire_pct ?? 0}%</span>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
      {assignments.length === 0 && (
        <div className="text-center py-12 text-muted-foreground text-sm">
          <ClipboardList className="mx-auto mb-2 h-8 w-8 opacity-30" />
          {t("portal.noAssignments")}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "invitations" | "evidence" | "remediation" | "questionnaires";

const tab_defs: { key: Tab; labelKey: keyof typeof import("@/lib/i18n/en").default; icon: React.ElementType }[] = [
  { key: "invitations",     labelKey: "portal.inviteTab",        icon: MailCheck },
  { key: "evidence",        labelKey: "portal.evidenceTab",      icon: FileSearch },
  { key: "remediation",     labelKey: "portal.remediationTab",   icon: ShieldCheck },
  { key: "questionnaires",  labelKey: "portal.questionnairesTab",icon: ClipboardList },
];

export default function SupplierPortalPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("invitations");

  return (
    <div className="p-6 space-y-6">
      <Link href="/suppliers" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
        ← {t("nav.suppliers")}
      </Link>
      <div className="flex items-center gap-3">
        <Users className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("portal.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("portal.subtitle")}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tab_defs.map(({ key, labelKey, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {t(labelKey)}
          </button>
        ))}
      </div>

      <div>
        {activeTab === "invitations"    && <InvitationsTab />}
        {activeTab === "evidence"       && <EvidenceTab />}
        {activeTab === "remediation"    && <RemediationTab />}
        {activeTab === "questionnaires" && <QuestionnairesTab />}
      </div>
    </div>
  );
}
