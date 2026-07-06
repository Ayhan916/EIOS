"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  ShieldAlert,
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

interface RiskDraft {
  id: string;
  organization_id: string;
  supplier_id: string | null;
  signal_id: string | null;
  draft_title: string;
  draft_description: string;
  draft_severity: string;
  draft_category: string | null;
  draft_likelihood: string | null;
  llm_model: string;
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  promoted_risk_id: string | null;
  created_at: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const SEV_COL: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800",
  HIGH:     "bg-orange-100 text-orange-800",
  MEDIUM:   "bg-amber-100 text-amber-700",
  LOW:      "bg-green-100 text-green-800",
};

const STATUS_COL: Record<string, string> = {
  pending:  "bg-blue-100 text-blue-700",
  accepted: "bg-emerald-100 text-emerald-800",
  rejected: "bg-slate-100 text-slate-600",
};

type TabKey = "pending" | "accepted" | "rejected";

const tab_defs: { key: TabKey; labelKey: string }[] = [
  { key: "pending",  labelKey: "drafts.pendingTab" },
  { key: "accepted", labelKey: "drafts.statusAccepted" },
  { key: "rejected", labelKey: "drafts.statusRejected" },
];

// ── Draft Card ────────────────────────────────────────────────────────────────

function DraftCard({ draft, onMutated }: { draft: RiskDraft; onMutated: () => void }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const [showAccept, setShowAccept] = useState(false);
  const [overrideTitle, setOverrideTitle] = useState("");
  const [overrideSeverity, setOverrideSeverity] = useState("");
  const [notes, setNotes] = useState("");

  const accept = useMutation({
    mutationFn: () =>
      apiClient.post(`/risks/drafts/${draft.id}/accept`, {
        notes: notes || undefined,
        override_severity: overrideSeverity || undefined,
        override_title: overrideTitle || undefined,
      }).then((r) => r.data),
    onSuccess: () => { onMutated(); setShowAccept(false); },
  });

  const reject = useMutation({
    mutationFn: () =>
      apiClient.post(`/risks/drafts/${draft.id}/reject`).then((r) => r.data),
    onSuccess: onMutated,
  });

  const isPending = draft.review_status === "pending";

  return (
    <Card className={`transition-colors ${draft.review_status === "accepted" ? "border-emerald-200" : draft.review_status === "rejected" ? "opacity-60" : "border-blue-200"}`}>
      <CardContent className="py-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1 flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <Bot className="h-4 w-4 text-muted-foreground shrink-0" />
              <p className="font-semibold">{draft.draft_title}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge className={SEV_COL[draft.draft_severity] ?? "bg-slate-100 text-slate-600"}>
                {draft.draft_severity}
              </Badge>
              <Badge className={STATUS_COL[draft.review_status] ?? "bg-slate-100 text-slate-600"}>
                {draft.review_status}
              </Badge>
              {draft.draft_category && (
                <Badge className="bg-slate-100 text-slate-600">{draft.draft_category}</Badge>
              )}
              {draft.draft_likelihood && (
                <Badge className="bg-purple-100 text-purple-700">{draft.draft_likelihood}</Badge>
              )}
            </div>
          </div>
          <div className="shrink-0 text-right space-y-1">
            <p className="text-xs text-muted-foreground">{formatDate(draft.created_at)}</p>
            <p className="text-[10px] text-muted-foreground font-mono">{draft.llm_model}</p>
          </div>
        </div>

        {/* Description toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? "Hide details" : "Show details"}
        </button>

        {expanded && (
          <div className="space-y-2 border-t pt-2">
            <p className="text-sm text-muted-foreground">{draft.draft_description}</p>
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              {draft.supplier_id && (
                <span>{t("drafts.supplier")}: <Link href={`/suppliers/${draft.supplier_id}`} className="font-mono text-blue-600 hover:underline">{draft.supplier_id.slice(0, 12)}…</Link></span>
              )}
              {draft.signal_id && <span>{t("drafts.signal")}: <span className="font-mono">{draft.signal_id.slice(0, 12)}…</span></span>}
            </div>
            {draft.reviewed_by && (
              <p className="text-xs text-muted-foreground">
                {t("drafts.reviewedBy")}: {draft.reviewed_by} · {draft.reviewed_at ? formatDate(draft.reviewed_at) : "—"}
              </p>
            )}
            {draft.promoted_risk_id && (
              <p className="text-xs text-emerald-600">
                {t("drafts.promotedRisk")}: <Link href={`/risks/${draft.promoted_risk_id}`} className="font-mono hover:underline">{draft.promoted_risk_id.slice(0, 12)}…</Link>
              </p>
            )}
          </div>
        )}

        {/* Action buttons — only for pending drafts */}
        {isPending && (
          <div className="flex flex-wrap gap-2 pt-1 border-t">
            <Button
              size="sm"
              className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700"
              onClick={() => { setShowAccept((v) => !v); }}
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> {t("drafts.accept")}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs text-red-700 border-red-300 hover:bg-red-50"
              disabled={reject.isPending}
              onClick={() => reject.mutate()}
            >
              {reject.isPending
                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                : <><X className="h-3.5 w-3.5 mr-1" />{t("drafts.reject")}</>}
            </Button>
          </div>
        )}

        {/* Accept expansion form */}
        {isPending && showAccept && (
          <div className="border rounded-md p-3 space-y-3 bg-muted/30">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Review & Promote to Risk
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">{t("drafts.overrideTitle")}</label>
                <input
                  className="mt-1 h-8 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder={draft.draft_title}
                  value={overrideTitle}
                  onChange={(e) => setOverrideTitle(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">{t("drafts.overrideSeverity")}</label>
                <select
                  className="mt-1 h-8 w-full rounded border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  value={overrideSeverity}
                  onChange={(e) => setOverrideSeverity(e.target.value)}
                >
                  <option value="">Keep: {draft.draft_severity}</option>
                  {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs text-muted-foreground">{t("drafts.notes")}</label>
              <textarea
                rows={2}
                className="mt-1 w-full rounded border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700"
                disabled={accept.isPending}
                onClick={() => accept.mutate()}
              >
                {accept.isPending
                  ? <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />{t("drafts.accepting")}</>
                  : <><CheckCircle2 className="h-3.5 w-3.5 mr-1" />Confirm & Promote</>}
              </Button>
              <Button size="sm" variant="ghost" className="h-8 text-xs" onClick={() => setShowAccept(false)}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RiskDraftsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>("pending");

  const { data: drafts = [], isLoading } = useQuery<RiskDraft[]>({
    queryKey: ["risk-drafts", activeTab],
    queryFn: () =>
      apiClient.get("/risks/drafts", {
        params: { review_status: activeTab, limit: 100 },
      }).then((r) => r.data),
  });

  const { data: pendingDrafts = [] } = useQuery<RiskDraft[]>({
    queryKey: ["risk-drafts", "pending"],
    queryFn: () =>
      apiClient.get("/risks/drafts", {
        params: { review_status: "pending", limit: 100 },
      }).then((r) => r.data),
  });

  function invalidate() {
    qc.invalidateQueries({ queryKey: ["risk-drafts"] });
  }

  const pendingCount = pendingDrafts.length;

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link
        href="/risks"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> {t("nav.risks")}
      </Link>

      {/* Header */}
      <div className="flex items-start gap-3">
        <Bot className="h-7 w-7 text-primary mt-0.5" />
        <div>
          <h1 className="text-2xl font-semibold">{t("drafts.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("drafts.subtitle")}</p>
        </div>
      </div>

      {/* Security notice */}
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
        <ShieldAlert className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
        <p className="text-sm text-amber-800">
          AI agents propose risks — only humans can promote them. Accepting creates a <strong>Draft</strong> risk that still requires standard risk approval.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tab_defs.map(({ key, labelKey }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t(labelKey as Parameters<typeof t>[0])}
            {key === "pending" && pendingCount > 0 && (
              <span className="rounded-full bg-blue-600 text-white text-[10px] font-bold px-1.5 py-0.5 leading-none">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner /></div>
      ) : drafts.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Bot className="mx-auto mb-3 h-10 w-10 opacity-25" />
          <p className="text-sm">{t("drafts.noDrafts")}</p>
          {activeTab === "pending" && (
            <p className="text-xs mt-1 text-muted-foreground">
              Risk drafts are generated automatically from surveillance signals.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} onMutated={invalidate} />
          ))}
        </div>
      )}
    </div>
  );
}
