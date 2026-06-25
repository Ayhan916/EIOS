"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Globe,
  Briefcase,
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  GitBranch,
  Network,
  ShieldAlert,
  BarChart3,
  Edit2,
  Archive,
  Printer,
  ExternalLink,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Share2,
  Target,
  Users,
} from "lucide-react";
import {
  getSupplier,
  getSupplierRiskProfile,
  listSupplierAssessments,
  updateSupplier,
  archiveSupplier,
} from "@/lib/api/suppliers";
import { getSectorProfileByNace } from "@/lib/api/sector_intelligence";
import {
  getSupplierIntelligence,
  recalculateSupplierScore,
  getSupplierScoreHistory,
  getSupplierBenchmark,
  getSupplierHeatmap,
} from "@/lib/api/supplier-scores";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierTier, SupplierStatus, SupplierUpdate } from "@/types/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function tierBadge(tier: string) {
  const colors: Record<string, string> = {
    "Tier 1": "bg-blue-100 text-blue-800",
    "Tier 2": "bg-purple-100 text-purple-800",
    "Tier 3": "bg-slate-100 text-slate-700",
    Other: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${colors[tier] ?? "bg-gray-100"}`}>
      {tier}
    </span>
  );
}

function statusBadge(s: string) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${s === "Active" ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>
      {s}
    </span>
  );
}

function severityColor(sev: string) {
  const m: Record<string, string> = {
    Critical: "text-red-600",
    High: "text-orange-500",
    Medium: "text-amber-500",
    Low: "text-green-600",
  };
  return m[sev] ?? "text-muted-foreground";
}

function riskBandColor(band: string) {
  const m: Record<string, string> = {
    Critical: "text-red-600 bg-red-50",
    High: "text-orange-600 bg-orange-50",
    Moderate: "text-amber-600 bg-amber-50",
    Low: "text-emerald-600 bg-emerald-50",
  };
  return m[band] ?? "text-muted-foreground bg-muted";
}

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative flex h-24 w-24 items-center justify-center">
        <svg viewBox="0 0 88 88" className="h-24 w-24 -rotate-90">
          <circle cx="44" cy="44" r={r} fill="none" strokeWidth="8" className="stroke-muted" />
          <circle
            cx="44" cy="44" r={r} fill="none" strokeWidth="8"
            strokeDasharray={`${filled} ${circ}`}
            className={`transition-all ${color}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute text-xl font-bold tabular-nums">{score.toFixed(0)}</span>
      </div>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function TrendBadge({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "Improving") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700">
        <TrendingUp className="h-3 w-3" /> Improving {delta > 0 ? `+${delta}` : ""}
      </span>
    );
  }
  if (trend === "Deteriorating") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
        <TrendingDown className="h-3 w-3" /> Deteriorating {delta}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
      <Minus className="h-3 w-3" /> Stable
    </span>
  );
}

// ── Network Tab ───────────────────────────────────────────────────────────────

function NetworkTab({ supplierId }: { supplierId: string }) {
  const { data: rels, isLoading: relsLoading } = useQuery({
    queryKey: ["supplier-network-rels", supplierId],
    queryFn: async () => {
      const res = await apiClient.get(
        `/api/v1/network/relationships?supplier_id=${supplierId}&limit=50`
      );
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const { data: exposures, isLoading: expLoading } = useQuery({
    queryKey: ["supplier-network-exposures", supplierId],
    queryFn: async () => {
      const res = await apiClient.get(
        `/api/v1/network/exposure-signals?impacted_supplier_id=${supplierId}&exposure_status=ACTIVE&limit=10`
      );
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const { data: criticality, isLoading: critLoading } = useQuery({
    queryKey: ["supplier-criticality", supplierId],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/api/v1/network/criticality/${supplierId}`);
        return res.data;
      } catch {
        return null;
      }
    },
    refetchInterval: 300_000,
  });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {/* Criticality */}
      <Card className="border-slate-800 bg-slate-900 text-slate-100">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <ShieldAlert className="h-4 w-4" />
            Supplier Criticality
          </CardTitle>
        </CardHeader>
        <CardContent>
          {critLoading ? (
            <div className="flex justify-center p-4"><Spinner /></div>
          ) : criticality ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Classification</span>
                <span className={`text-sm font-bold ${
                  criticality.criticality === "CRITICAL" ? "text-red-400" :
                  criticality.criticality === "HIGH" ? "text-orange-400" :
                  criticality.criticality === "MEDIUM" ? "text-yellow-400" : "text-green-400"
                }`}>{criticality.criticality}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Score</span>
                <span className="text-sm text-slate-200">{Math.round(criticality.criticality_score * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Degree Centrality</span>
                <span className="text-sm text-slate-200">{Math.round(criticality.degree_centrality * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Inbound / Outbound</span>
                <span className="text-sm text-slate-200">{criticality.inbound_degree} / {criticality.outbound_degree}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Component Size</span>
                <span className="text-sm text-slate-200">{criticality.connected_component_size}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 py-4 text-center">
              No criticality data yet. Compute centrality from the Network dashboard.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Relationships */}
      <Card className="border-slate-800 bg-slate-900 text-slate-100">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <Share2 className="h-4 w-4" />
            Relationships ({relsLoading ? "…" : (rels?.length ?? 0)})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {relsLoading ? (
            <div className="flex justify-center p-4"><Spinner /></div>
          ) : !rels?.length ? (
            <p className="text-sm text-slate-500 py-4 text-center">No relationships found.</p>
          ) : (
            <div className="divide-y divide-slate-800">
              {rels.map((r: any) => (
                <div key={r.id} className="py-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-slate-300">
                      {r.supplier_id === supplierId
                        ? `→ ${r.related_supplier_id.slice(0, 8)}…`
                        : `← ${r.supplier_id.slice(0, 8)}…`}
                    </span>
                    <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                      {r.relationship_type.replace(/_/g, " ")}
                    </span>
                    <span className="ml-auto text-xs text-slate-500">
                      {Math.round(r.confidence * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Exposure Signals */}
      <Card className="border-slate-800 bg-slate-900 text-slate-100 lg:col-span-2">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
            <GitBranch className="h-4 w-4 text-orange-400" />
            Network Exposure Signals ({expLoading ? "…" : (exposures?.length ?? 0)})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {expLoading ? (
            <div className="flex justify-center p-4"><Spinner /></div>
          ) : !exposures?.length ? (
            <p className="text-sm text-slate-500 py-4 text-center">
              No active exposure signals for this supplier.
            </p>
          ) : (
            <div className="divide-y divide-slate-800">
              {exposures.map((e: any) => (
                <div key={e.id} className="py-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                      e.severity === "CRITICAL" ? "bg-red-600 text-white" :
                      e.severity === "HIGH" ? "bg-orange-500 text-white" :
                      e.severity === "MEDIUM" ? "bg-yellow-500 text-black" : "bg-blue-500 text-white"
                    }`}>{e.severity}</span>
                    <span className="text-sm font-medium text-slate-200">
                      {e.exposure_type.replace(/_/g, " ")}
                    </span>
                    <span className="ml-auto text-xs text-slate-500">
                      {Math.round(e.confidence * 100)}% · {e.path_length} hop(s)
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400 truncate">{e.rationale}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    From: {e.origin_supplier_id.slice(0, 8)}…
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Portal Tab ────────────────────────────────────────────────────────────────

function SupplierPortalTab({ supplierId, supplierName }: { supplierId: string; supplierName: string }) {
  const [newMessage, setNewMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const qc = useQueryClient();

  const { data: conversations = [], isLoading } = useQuery<{
    id: string; subject: string | null; created_at: string;
    message_count: number; last_message_at: string | null;
  }[]>({
    queryKey: ["portal-conversations", supplierId],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/api/v1/supplier-portal/internal/conversations?supplier_id=${supplierId}`);
        return r.data ?? [];
      } catch { return []; }
    },
    retry: false,
  });

  const [activeConvId, setActiveConvId] = useState<string | null>(null);

  const { data: messages = [] } = useQuery<{
    id: string; content: string; sender_type: string; sent_at: string;
  }[]>({
    queryKey: ["portal-messages", activeConvId],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/api/v1/supplier-portal/internal/conversations/${activeConvId}/messages`);
        return r.data ?? [];
      } catch { return []; }
    },
    enabled: !!activeConvId,
    retry: false,
  });

  async function sendMessage() {
    if (!newMessage.trim()) return;
    setSending(true); setSendError(null);
    try {
      if (!activeConvId) {
        const r = await apiClient.post("/api/v1/supplier-portal/internal/conversations", {
          supplier_id: supplierId, subject: `Message to ${supplierName}`,
        });
        const convId = r.data.id;
        await apiClient.post("/api/v1/supplier-portal/internal/messages", {
          conversation_id: convId, content: newMessage,
        });
        qc.invalidateQueries({ queryKey: ["portal-conversations", supplierId] });
        setActiveConvId(convId);
      } else {
        await apiClient.post("/api/v1/supplier-portal/internal/messages", {
          conversation_id: activeConvId, content: newMessage,
        });
        qc.invalidateQueries({ queryKey: ["portal-messages", activeConvId] });
      }
      setNewMessage("");
    } catch { setSendError("Failed to send"); }
    finally { setSending(false); }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Conversations</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading && <div className="flex justify-center py-6"><Spinner /></div>}
          {!isLoading && conversations.length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground">No conversations yet.</p>
          )}
          <div className="divide-y divide-border">
            {conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveConvId(c.id)}
                className={`w-full text-left px-4 py-3 hover:bg-muted/40 transition-colors ${activeConvId === c.id ? "bg-muted/60" : ""}`}
              >
                <p className="text-sm font-medium truncate">{c.subject || "No subject"}</p>
                <p className="text-xs text-muted-foreground">
                  {c.message_count} message{c.message_count !== 1 ? "s" : ""}
                  {c.last_message_at && ` · ${new Date(c.last_message_at).toLocaleDateString()}`}
                </p>
              </button>
            ))}
          </div>
          <div className="p-3 border-t border-border">
            <button
              onClick={() => setActiveConvId(null)}
              className="text-xs text-blue-600 hover:text-blue-800"
            >
              + New conversation
            </button>
          </div>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">
            {activeConvId
              ? conversations.find((c) => c.id === activeConvId)?.subject ?? "Conversation"
              : `New message to ${supplierName}`}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {activeConvId && (
            <div className="max-h-64 overflow-y-auto space-y-2 rounded-lg border border-border bg-muted/20 p-3">
              {messages.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">No messages yet.</p>
              ) : (
                messages.map((m) => (
                  <div key={m.id} className={`flex ${m.sender_type === "internal" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-xs rounded-lg px-3 py-2 text-sm ${m.sender_type === "internal" ? "bg-blue-600 text-white" : "bg-background border border-border"}`}>
                      <p>{m.content}</p>
                      <p className={`text-[10px] mt-0.5 ${m.sender_type === "internal" ? "text-blue-200" : "text-muted-foreground"}`}>
                        {new Date(m.sent_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
          <div className="flex gap-2">
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Write a message…"
              rows={3}
              className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <Button onClick={sendMessage} disabled={sending || !newMessage.trim()} className="self-end">
              {sending ? "…" : "Send"}
            </Button>
          </div>
          {sendError && <p className="text-xs text-red-500">{sendError}</p>}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = ["Overview", "Assessments", "Findings", "Risk Profile", "Intelligence", "Network", "Portal"] as const;
type Tab = typeof TABS[number];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("Overview");
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<SupplierUpdate>({});
  const [editError, setEditError] = useState<string | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);
  const [intelligenceSubTab, setIntelligenceSubTab] = useState<"score" | "history" | "benchmark" | "heatmap">("score");

  // Start Assessment dialog
  const [startAssessment, setStartAssessment] = useState(false);
  const [assessTitle, setAssessTitle] = useState("");
  const [assessType, setAssessType] = useState("ESG");
  const [assessBusy, setAssessBusy] = useState(false);
  const [assessError, setAssessError] = useState<string | null>(null);

  // Schedule Reassessment
  const [showSchedule, setShowSchedule] = useState(false);
  const [scheduleFrequency, setScheduleFrequency] = useState(90);
  const [scheduleNextDue, setScheduleNextDue] = useState("");

  // OFAC scan
  const [ofacBusy, setOfacBusy] = useState(false);
  const [ofacResult, setOfacResult] = useState<{ matches_found: number; matches: { sdn_name: string; sdn_type: string; programs: string[] }[] } | null>(null);
  const [ofacError, setOfacError] = useState<string | null>(null);

  // Due diligence
  const [ddBusy, setDdBusy] = useState(false);
  const [ddError, setDdError] = useState<string | null>(null);

  const { data: supplier, isLoading } = useQuery({
    queryKey: ["supplier", id],
    queryFn: () => getSupplier(id),
    enabled: !!id,
  });

  const { data: profile } = useQuery({
    queryKey: ["supplier-risk-profile", id],
    queryFn: () => getSupplierRiskProfile(id),
    enabled: !!id && tab === "Risk Profile",
  });

  const { data: assessments, isLoading: assessmentsLoading } = useQuery({
    queryKey: ["supplier-assessments", id],
    queryFn: () => listSupplierAssessments(id, { page: 1, page_size: 20 }),
    enabled: !!id && tab === "Assessments",
  });

  const { data: intelligence, isLoading: intelligenceLoading } = useQuery({
    queryKey: ["supplier-intelligence", id],
    queryFn: () => getSupplierIntelligence(id),
    enabled: !!id && tab === "Intelligence",
  });

  const { data: history } = useQuery({
    queryKey: ["supplier-intelligence-history", id],
    queryFn: () => getSupplierScoreHistory(id, 12),
    enabled: !!id && tab === "Intelligence" && intelligenceSubTab === "history",
  });

  const { data: benchmark } = useQuery({
    queryKey: ["supplier-benchmark", id],
    queryFn: () => getSupplierBenchmark(id),
    enabled: !!id && (tab === "Overview" || (tab === "Intelligence" && intelligenceSubTab === "benchmark")),
    staleTime: 300_000,
  });

  const { data: heatmap } = useQuery({
    queryKey: ["supplier-heatmap", id],
    queryFn: () => getSupplierHeatmap(id),
    enabled: !!id && tab === "Intelligence" && intelligenceSubTab === "heatmap",
  });

  const { data: sectorProfile } = useQuery({
    queryKey: ["sector-profile-nace", supplier?.nace_code],
    queryFn: () => getSectorProfileByNace(supplier!.nace_code!),
    enabled: !!supplier?.nace_code && tab === "Intelligence" && intelligenceSubTab === "benchmark",
    staleTime: 600_000,
    retry: false,
  });

  const { data: dueDiligence, refetch: refetchDD } = useQuery<{
    supplier_id: string; overall_risk: string; csddd_score: number;
    human_rights_score: number; environmental_score: number;
    active_findings: number; critical_findings: number;
    open_recommendations: number; last_updated: string | null;
  } | null>({
    queryKey: ["supplier-due-diligence", id],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/api/v1/due-diligence/suppliers/${id}`);
        return r.data;
      } catch { return null; }
    },
    enabled: !!id && tab === "Overview",
    retry: false,
  });

  const { data: certificates } = useQuery<{
    id: string; certificate_type: string; issuer: string | null;
    valid_from: string | null; valid_until: string | null; status: string;
  }[]>({
    queryKey: ["supplier-certificates", id],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/api/v1/suppliers/${id}/certificates`);
        return r.data;
      } catch { return []; }
    },
    enabled: !!id && tab === "Overview",
    staleTime: 300_000,
    retry: false,
  });

  const { data: questionnaireProgress } = useQuery<{
    supplier_id: string; questionnaire_pct: number;
  } | null>({
    queryKey: ["supplier-questionnaire-pct", id],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/api/v1/executive/suppliers?limit=500`);
        const row = (r.data?.items ?? r.data ?? []).find((s: { id: string }) => s.id === id);
        return row ? { supplier_id: id, questionnaire_pct: row.questionnaire_pct ?? 0 } : null;
      } catch { return null; }
    },
    enabled: !!id && tab === "Overview",
    staleTime: 300_000,
    retry: false,
  });

  const { data: supplierFindings, isLoading: findingsLoading } = useQuery<{
    id: string; title: string; description: string; severity: string;
    category: string; status: string; assessment_id: string; created_at: string | null;
  }[]>({
    queryKey: ["supplier-findings", id],
    queryFn: async () => {
      const r = await apiClient.get(`/api/v1/executive/findings?supplier_id=${id}&limit=200`);
      return r.data;
    },
    enabled: !!id && tab === "Findings",
  });

  const updateMutation = useMutation({
    mutationFn: (body: SupplierUpdate) => updateSupplier(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier", id] });
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      setEditing(false);
      setEditError(null);
    },
    onError: (err: unknown) => {
      setEditError(err instanceof Error ? err.message : "Update failed");
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveSupplier(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      router.push("/suppliers");
    },
  });

  const recalcMutation = useMutation({
    mutationFn: () => recalculateSupplierScore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-intelligence", id] });
      queryClient.invalidateQueries({ queryKey: ["supplier-intelligence-history", id] });
      queryClient.invalidateQueries({ queryKey: ["supplier-benchmark", id] });
    },
  });

  const { data: existingSchedule } = useQuery<{ id: string; frequency_days: number; next_due_at: string; is_active: boolean } | null>({
    queryKey: ["supplier-schedule", id],
    queryFn: async () => {
      const r = await apiClient.get(`/api/v1/assessments/schedules?supplier_id=${id}&active_only=false`);
      return r.data?.[0] ?? null;
    },
    enabled: !!id && tab === "Assessments",
  });

  const scheduleMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, unknown> = {
        supplier_id: id,
        frequency_days: scheduleFrequency,
      };
      if (scheduleNextDue) body.next_due_at = new Date(scheduleNextDue).toISOString();
      const r = await apiClient.post("/api/v1/assessments/schedules", body);
      return r.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["supplier-schedule", id] });
      setShowSchedule(false);
    },
  });

  if (isLoading) {
    return <div className="flex justify-center py-20"><Spinner size="lg" /></div>;
  }
  if (!supplier) {
    return (
      <div className="flex flex-col items-center gap-4 py-20 text-center">
        <ShieldAlert className="h-12 w-12 text-muted-foreground/40" />
        <p className="text-muted-foreground">Supplier not found.</p>
        <Link href="/suppliers"><Button variant="outline">Back to Suppliers</Button></Link>
      </div>
    );
  }

  function startEdit() {
    setEditForm({
      name: supplier!.name,
      legal_name: supplier!.legal_name,
      country: supplier!.country,
      industry: supplier!.industry,
      nace_code: supplier!.nace_code,
      website: supplier!.website,
      supplier_tier: supplier!.supplier_tier,
      notes: supplier!.notes,
    });
    setEditing(true);
  }

  async function handleStartAssessment() {
    if (!assessTitle) return;
    setAssessBusy(true);
    setAssessError(null);
    try {
      const r = await apiClient.post("/api/v1/assessments/", {
        title: assessTitle,
        description: `Assessment for ${supplier!.name}`,
        assessment_type: assessType,
        scope: "",
        supplier_id: id,
      });
      queryClient.invalidateQueries({ queryKey: ["supplier-assessments", id] });
      setStartAssessment(false);
      setAssessTitle("");
      router.push(`/assessments/${r.data.id}`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAssessError(msg ?? "Failed to create assessment");
    } finally {
      setAssessBusy(false);
    }
  }

  async function handleOfacScan() {
    setOfacBusy(true);
    setOfacError(null);
    setOfacResult(null);
    try {
      const r = await apiClient.post(`/api/v1/integrations/sanctions/ofac/scan/supplier/${id}`);
      setOfacResult(r.data);
      // #151 Auto-create finding when OFAC matches found
      if (r.data?.matches_found > 0) {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.ofac_match_finding?.enabled !== false) {
            await apiClient.post("/api/v1/automations/trigger", {
              rule_id: "ofac_match_finding",
              entity_type: "supplier",
              entity_id: id,
              payload: {
                matches: r.data.matches,
                severity: stored?.ofac_match_finding?.config?.finding_severity ?? "HIGH",
              },
            });
          }
        } catch { /* silent */ }
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setOfacError(msg ?? "OFAC scan failed");
    } finally {
      setOfacBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Back + Header */}
      <div>
        <Link
          href="/suppliers"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Suppliers
        </Link>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
              <Briefcase className="h-5 w-5 text-blue-700" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{supplier.name}</h1>
              {supplier.legal_name && supplier.legal_name !== supplier.name && (
                <p className="text-sm text-muted-foreground">{supplier.legal_name}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {tierBadge(supplier.supplier_tier)}
            {statusBadge(supplier.supplier_status)}
            <Button variant="outline" size="sm" onClick={() => window.print()} className="gap-1.5 print:hidden">
              <Printer className="h-3.5 w-3.5" /> Export PDF
            </Button>
            <Button variant="outline" size="sm" onClick={startEdit} className="gap-1.5">
              <Edit2 className="h-3.5 w-3.5" /> Edit
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmArchive(true)}
              className="gap-1.5 text-red-600 hover:text-red-700"
            >
              <Archive className="h-3.5 w-3.5" /> Archive
            </Button>
          </div>
        </div>
      </div>

      {/* Meta strip */}
      <div className="flex flex-wrap items-center gap-6 text-sm text-muted-foreground">
        {supplier.country && (
          <span className="flex items-center gap-1.5">
            <Globe className="h-4 w-4" /> {supplier.country}
          </span>
        )}
        {supplier.industry && (
          <span className="flex items-center gap-1.5">
            <BarChart3 className="h-4 w-4" /> {supplier.industry}
          </span>
        )}
        {supplier.nace_code && (
          <span className="font-mono text-xs bg-muted px-2 py-1 rounded">{supplier.nace_code}</span>
        )}
        {supplier.website && (
          <a
            href={supplier.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Website
          </a>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-6">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`pb-3 text-sm font-medium transition-colors ${
                tab === t
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {/* ── Overview Tab ──────────────────────────────────────────────────── */}
      {tab === "Overview" && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle className="text-base">Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Country</p>
                  <p className="font-medium">{supplier.country || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Industry</p>
                  <p className="font-medium">{supplier.industry || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">NACE Code</p>
                  <p className="font-mono font-medium">{supplier.nace_code || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Tier</p>
                  <p className="font-medium">{supplier.supplier_tier}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-medium">{supplier.supplier_status}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Website</p>
                  {supplier.website ? (
                    <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {supplier.website}
                    </a>
                  ) : (
                    <p className="font-medium">—</p>
                  )}
                </div>
              </div>
              {supplier.notes && (
                <div className="border-t border-border pt-4">
                  <p className="mb-1 text-sm text-muted-foreground">Notes</p>
                  <p className="text-sm whitespace-pre-wrap">{supplier.notes}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-4">
            {/* ── Benchmark Summary Card (Item 19) ─────────────────────────── */}
            {benchmark && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <BarChart3 className="h-4 w-4 text-violet-500" />
                      Peer Benchmark
                    </span>
                    <button
                      onClick={() => { setTab("Intelligence"); setIntelligenceSubTab("benchmark"); }}
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Full view →
                    </button>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Risk Score</span>
                    <span className="text-lg font-bold tabular-nums">{benchmark.risk_score?.toFixed(0) ?? "—"}</span>
                  </div>
                  {benchmark.sector_percentile != null && (
                    <div>
                      <div className="flex justify-between text-xs text-muted-foreground mb-1">
                        <span>Sector percentile</span>
                        <span className="font-medium text-foreground">{benchmark.sector_percentile.toFixed(0)}th</span>
                      </div>
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-violet-500 rounded-full"
                          style={{ width: `${benchmark.sector_percentile}%` }}
                        />
                      </div>
                    </div>
                  )}
                  {benchmark.peer_comparison && (
                    <p className="text-xs text-muted-foreground">{benchmark.peer_comparison}</p>
                  )}
                </CardContent>
              </Card>
            )}

            {/* #88 Questionnaire progress bar */}
            {questionnaireProgress != null && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <FileText className="h-4 w-4 text-blue-500" /> Portal Questionnaire
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Completion</span>
                    <span className="font-semibold">{questionnaireProgress.questionnaire_pct}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        questionnaireProgress.questionnaire_pct >= 100 ? "bg-emerald-500" :
                        questionnaireProgress.questionnaire_pct >= 50 ? "bg-amber-500" : "bg-red-400"
                      }`}
                      style={{ width: `${questionnaireProgress.questionnaire_pct}%` }}
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* #85-86 Due Diligence card */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <GitBranch className="h-4 w-4 text-orange-500" />
                    Due Diligence
                  </span>
                  <button
                    onClick={async () => {
                      setDdBusy(true); setDdError(null);
                      try {
                        await apiClient.post("/api/v1/due-diligence/reports/generate", {
                          supplier_id: id, report_types: ["CSDDD", "HUMAN_RIGHTS", "ENVIRONMENTAL"],
                        });
                        refetchDD();
                      } catch { setDdError("Failed to run"); }
                      finally { setDdBusy(false); }
                    }}
                    disabled={ddBusy}
                    className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  >
                    {ddBusy ? "Running…" : "Run"}
                  </button>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                {ddError && <p className="text-xs text-red-500 mb-2">{ddError}</p>}
                {dueDiligence ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Overall Risk</span>
                      <span className={`font-semibold ${dueDiligence.overall_risk === "Critical" || dueDiligence.overall_risk === "High" ? "text-red-600" : dueDiligence.overall_risk === "Medium" ? "text-amber-600" : "text-emerald-600"}`}>
                        {dueDiligence.overall_risk}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">CSDDD Score</span>
                      <span className="font-medium">{dueDiligence.csddd_score?.toFixed(0) ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Human Rights</span>
                      <span className="font-medium">{dueDiligence.human_rights_score?.toFixed(0) ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Active Findings</span>
                      <span className={`font-semibold ${dueDiligence.active_findings > 0 ? "text-red-600" : "text-emerald-600"}`}>
                        {dueDiligence.active_findings}
                      </span>
                    </div>
                    {dueDiligence.last_updated && (
                      <p className="text-muted-foreground">
                        Updated {new Date(dueDiligence.last_updated).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No due diligence report yet. Click Run to generate.</p>
                )}
              </CardContent>
            </Card>

            {/* #90 Certificate expiry widget */}
            {certificates && certificates.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Certificates
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0 space-y-1.5">
                  {certificates.slice(0, 4).map((cert) => {
                    const expiryDate = cert.valid_until ? new Date(cert.valid_until) : null;
                    const daysLeft = expiryDate ? Math.floor((expiryDate.getTime() - Date.now()) / 86_400_000) : null;
                    const expired = daysLeft != null && daysLeft < 0;
                    const expiring = daysLeft != null && daysLeft >= 0 && daysLeft < 90;
                    return (
                      <div key={cert.id} className="flex items-center justify-between text-xs">
                        <span className="truncate max-w-[120px]" title={cert.certificate_type}>{cert.certificate_type}</span>
                        {daysLeft == null ? (
                          <span className="text-muted-foreground">No expiry</span>
                        ) : expired ? (
                          <span className="text-red-600 font-semibold">Expired</span>
                        ) : expiring ? (
                          <span className="text-amber-600 font-semibold">{daysLeft}d left</span>
                        ) : (
                          <span className="text-emerald-600">{daysLeft}d left</span>
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            )}

            {(["Assessments", "Findings", "Risk Profile", "Intelligence"] as Tab[]).map((t) => {
              const icons: Record<string, React.ReactNode> = {
                Assessments: <FileText className="h-8 w-8 text-blue-500" />,
                Findings: <AlertTriangle className="h-8 w-8 text-red-500" />,
                "Risk Profile": <ShieldAlert className="h-8 w-8 text-amber-500" />,
                Intelligence: <Target className="h-8 w-8 text-violet-500" />,
              };
              const subtitles: Record<string, string> = {
                Assessments: "View all assessments",
                Findings: "All findings across assessments",
                "Risk Profile": "Findings, risks, actions",
                Intelligence: "ESG & risk scores, trend",
              };
              return (
                <Card key={t} className="cursor-pointer hover:bg-muted/30 transition-colors" onClick={() => setTab(t)}>
                  <CardContent className="flex items-center gap-4 p-4">
                    {icons[t]}
                    <div>
                      <p className="font-semibold">{t}</p>
                      <p className="text-xs text-muted-foreground">{subtitles[t]}</p>
                    </div>
                    <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Assessments Tab ───────────────────────────────────────────────── */}
      {tab === "Assessments" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold">Assessments ({assessments?.total ?? 0})</h2>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => { setShowSchedule((v) => !v); }}
              >
                <Clock className="h-3.5 w-3.5" />
                {existingSchedule ? "Edit Schedule" : "Schedule Reassessment"}
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => { setStartAssessment((v) => !v); setAssessError(null); }}
              >
                <FileText className="h-3.5 w-3.5" /> Start Assessment
              </Button>
            </div>
          </div>

          {existingSchedule && !showSchedule && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50/60 px-4 py-3 text-sm flex items-center gap-2 dark:border-emerald-800 dark:bg-emerald-950/30">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
              <span className="text-emerald-800 dark:text-emerald-300">
                Reassessment scheduled every <strong>{existingSchedule.frequency_days} days</strong>
                {existingSchedule.next_due_at && (
                  <> — next due <strong>{new Date(existingSchedule.next_due_at).toLocaleDateString()}</strong></>
                )}
              </span>
            </div>
          )}

          {showSchedule && (
            <Card className="mb-4">
              <CardContent className="pt-4 pb-4 space-y-3">
                <p className="text-sm font-medium">Schedule Reassessment for {supplier.name}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Frequency</label>
                    <select
                      className="w-full rounded border px-3 py-1.5 text-sm bg-background"
                      value={scheduleFrequency}
                      onChange={(e) => setScheduleFrequency(Number(e.target.value))}
                    >
                      <option value={30}>Monthly (30 days)</option>
                      <option value={90}>Quarterly (90 days)</option>
                      <option value={180}>Semi-annual (180 days)</option>
                      <option value={365}>Annual (365 days)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Next due date (optional)</label>
                    <input
                      type="date"
                      className="w-full rounded border px-3 py-1.5 text-sm bg-background"
                      value={scheduleNextDue}
                      onChange={(e) => setScheduleNextDue(e.target.value)}
                    />
                  </div>
                </div>
                {scheduleMutation.isError && (
                  <p className="text-xs text-red-600">Failed to save schedule — a schedule may already exist for this supplier.</p>
                )}
                {scheduleMutation.isSuccess && (
                  <p className="text-xs text-emerald-600">Schedule saved.</p>
                )}
                <div className="flex gap-2">
                  <Button size="sm" disabled={scheduleMutation.isPending} onClick={() => scheduleMutation.mutate()}>
                    {scheduleMutation.isPending ? "Saving…" : "Save Schedule"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowSchedule(false)}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {startAssessment && (
            <Card className="mb-4">
              <CardContent className="pt-4 pb-4 space-y-3">
                <p className="text-sm font-medium">New Assessment for {supplier.name}</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <label className="block text-xs text-muted-foreground mb-1">Title</label>
                    <input
                      className="w-full rounded border px-3 py-1.5 text-sm bg-background"
                      placeholder={`${supplier.name} ESG Assessment ${new Date().getFullYear()}`}
                      value={assessTitle}
                      onChange={(e) => setAssessTitle(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Type</label>
                    <select
                      className="w-full rounded border px-3 py-1.5 text-sm bg-background"
                      value={assessType}
                      onChange={(e) => setAssessType(e.target.value)}
                    >
                      {["ESG", "Environmental", "Social", "Governance", "Compliance", "Financial"].map((t) => (
                        <option key={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                </div>
                {assessError && <p className="text-xs text-red-600">{assessError}</p>}
                <div className="flex gap-2">
                  <Button size="sm" disabled={!assessTitle || assessBusy} onClick={handleStartAssessment}>
                    {assessBusy ? "Creating…" : "Create & Open"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setStartAssessment(false)}>Cancel</Button>
                </div>
              </CardContent>
            </Card>
          )}

          {assessmentsLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : !assessments?.items.length ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
                <FileText className="h-10 w-10 text-muted-foreground/40" />
                <p className="text-muted-foreground">No assessments for this supplier yet.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30">
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Title</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Type</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Review Status</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Quality</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {assessments.items.map((a) => (
                      <tr key={a.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <Link href={`/assessments/${a.id}`} className="font-medium hover:text-blue-600 hover:underline">
                            {a.title}
                          </Link>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{a.assessment_type || "—"}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium ${
                            a.review_status === "Approved" ? "text-emerald-600" :
                            a.review_status === "InReview" ? "text-blue-600" :
                            a.review_status === "ChangesRequested" ? "text-amber-600" :
                            "text-muted-foreground"
                          }`}>
                            {a.review_status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {a.quality_score != null ? (
                            <span className="font-medium">{(a.quality_score * 100).toFixed(0)}%</span>
                          ) : <span className="text-muted-foreground/50">—</span>}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">
                          {new Date(a.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Findings Tab ──────────────────────────────────────────────────── */}
      {tab === "Findings" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">
              Findings ({supplierFindings?.length ?? 0})
            </h2>
          </div>
          {findingsLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : !supplierFindings?.length ? (
            <Card>
              <CardContent className="py-12 text-center">
                <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">No findings for this supplier yet.</p>
                <p className="mt-1 text-xs text-muted-foreground">Findings are surfaced when assessments are run.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs text-muted-foreground">
                      <th className="px-4 py-3 text-left">Finding</th>
                      <th className="px-4 py-3 text-left">Severity</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">Category</th>
                      <th className="px-4 py-3 text-left hidden md:table-cell">Date</th>
                      <th className="px-4 py-3 text-right">Assessment</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {supplierFindings.map((f) => {
                      const sevColor: Record<string, string> = {
                        Critical: "bg-red-100 text-red-800 border-red-200",
                        High: "bg-orange-100 text-orange-800 border-orange-200",
                        Medium: "bg-amber-100 text-amber-800 border-amber-200",
                        Low: "bg-slate-100 text-slate-700 border-slate-200",
                      };
                      return (
                        <tr key={f.id} className="hover:bg-muted/20 transition-colors">
                          <td className="px-4 py-3">
                            <p className="font-medium line-clamp-1 max-w-sm">{f.title}</p>
                            {f.description && (
                              <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1 max-w-sm">{f.description}</p>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${sevColor[f.severity] ?? "bg-slate-100 text-slate-700"}`}>
                              {f.severity}
                            </span>
                          </td>
                          <td className="px-4 py-3 hidden sm:table-cell">
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                              {f.category || "—"}
                            </span>
                          </td>
                          <td className="px-4 py-3 hidden md:table-cell text-xs text-muted-foreground">
                            {f.created_at ? new Date(f.created_at).toLocaleDateString() : "—"}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <Link
                              href={`/assessments/${f.assessment_id}`}
                              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                            >
                              <ExternalLink className="h-3 w-3" /> View
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Risk Profile Tab ──────────────────────────────────────────────── */}
      {tab === "Risk Profile" && (
        <div>
          {!profile ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {[
                  { label: "Total Assessments", value: profile.total_assessments, icon: FileText, sub: `${profile.approved_assessments} approved`, color: "text-blue-600" },
                  { label: "Total Findings", value: profile.total_findings, icon: AlertTriangle, sub: `${profile.findings_by_severity["Critical"] ?? 0} critical`, color: profile.findings_by_severity["Critical"] ? "text-red-600" : "text-amber-500" },
                  { label: "Total Risks", value: profile.total_risks, icon: ShieldAlert, sub: `${profile.risks_by_severity["Critical"] ?? 0} critical`, color: profile.risks_by_severity["Critical"] ? "text-red-600" : "text-orange-500" },
                  { label: "Open Actions", value: profile.open_actions, icon: Clock, sub: profile.overdue_actions > 0 ? `${profile.overdue_actions} overdue` : "None overdue", color: profile.overdue_actions > 0 ? "text-red-600" : "text-muted-foreground" },
                ].map(({ label, value, icon: Icon, sub, color }) => (
                  <Card key={label}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-xs text-muted-foreground">{label}</p>
                          <p className={`text-3xl font-bold ${color}`}>{value}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
                        </div>
                        <Icon className={`h-5 w-5 ${color} opacity-60`} />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                {(["Findings", "Risks"] as const).map((kind) => {
                  const data = kind === "Findings" ? profile.findings_by_severity : profile.risks_by_severity;
                  const total = kind === "Findings" ? profile.total_findings : profile.total_risks;
                  return (
                    <Card key={kind}>
                      <CardHeader><CardTitle className="text-base">{kind} by Severity</CardTitle></CardHeader>
                      <CardContent>
                        {["Critical", "High", "Medium", "Low"].map((sev) => {
                          const count = data[sev] ?? 0;
                          const pct = total > 0 ? (count / total) * 100 : 0;
                          return (
                            <div key={sev} className="mb-3">
                              <div className="mb-1 flex items-center justify-between text-sm">
                                <span className={`font-medium ${severityColor(sev)}`}>{sev}</span>
                                <span className="text-muted-foreground">{count}</span>
                              </div>
                              <div className="h-2 w-full rounded-full bg-muted">
                                <div
                                  className={`h-2 rounded-full transition-all ${
                                    sev === "Critical" ? "bg-red-500" : sev === "High" ? "bg-orange-500" : sev === "Medium" ? "bg-amber-400" : "bg-green-500"
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <Card>
                <CardHeader><CardTitle className="text-base">Action Tracking</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <p className="text-3xl font-bold text-foreground">{profile.open_recommendations}</p>
                      <p className="text-xs text-muted-foreground mt-1">Open Recommendations</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-amber-600">{profile.open_actions}</p>
                      <p className="text-xs text-muted-foreground mt-1">Open Actions</p>
                    </div>
                    <div>
                      <p className={`text-3xl font-bold ${profile.overdue_actions > 0 ? "text-red-600" : "text-emerald-600"}`}>
                        {profile.overdue_actions}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">Overdue Actions</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ── Intelligence Tab ──────────────────────────────────────────────── */}
      {tab === "Intelligence" && (
        <div className="space-y-5">
          {/* Sub-tab nav */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1 rounded-lg border border-border bg-muted/30 p-1">
              {(["score", "history", "benchmark", "heatmap"] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setIntelligenceSubTab(st)}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                    intelligenceSubTab === st
                      ? "bg-background shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {st === "benchmark" ? "Benchmark" : st.charAt(0).toUpperCase() + st.slice(1)}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleOfacScan}
                disabled={ofacBusy}
              >
                <ShieldAlert className={`h-3.5 w-3.5 ${ofacBusy ? "animate-pulse" : ""}`} />
                {ofacBusy ? "Scanning…" : "OFAC Scan"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={() => recalcMutation.mutate()}
                disabled={recalcMutation.isPending}
              >
                <RefreshCw className={`h-3.5 w-3.5 ${recalcMutation.isPending ? "animate-spin" : ""}`} />
                Recalculate
              </Button>
            </div>
          </div>

          {ofacResult && (
            <Card className={ofacResult.matches_found > 0 ? "border-red-300 bg-red-50" : "border-emerald-300 bg-emerald-50"}>
              <CardContent className="pt-4 pb-3">
                {ofacResult.matches_found === 0 ? (
                  <p className="text-sm font-medium text-emerald-700 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4" /> No OFAC SDN matches found for {supplier.name}
                  </p>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-red-700 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      {ofacResult.matches_found} potential OFAC match{ofacResult.matches_found > 1 ? "es" : ""}
                    </p>
                    {ofacResult.matches.slice(0, 5).map((m, i) => (
                      <div key={i} className="text-xs text-red-800 border border-red-200 rounded p-2 bg-white/60">
                        <p className="font-medium">{m.sdn_name} <span className="font-normal text-muted-foreground">({m.sdn_type})</span></p>
                        {m.programs.length > 0 && <p className="text-red-600">Programs: {m.programs.join(", ")}</p>}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
          {ofacError && <p className="text-xs text-red-600">{ofacError}</p>}

          {/* Score sub-tab */}
          {intelligenceSubTab === "score" && (
            <div>
              {intelligenceLoading ? (
                <div className="flex justify-center py-12"><Spinner size="lg" /></div>
              ) : !intelligence ? (
                <Card>
                  <CardContent className="py-12 text-center text-muted-foreground">
                    No score calculated yet. Click Recalculate to generate the first score.
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-6">
                  {/* Score overview row */}
                  <div className="grid gap-4 lg:grid-cols-2">
                    {/* ESG scores */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">ESG Score</CardTitle>
                        <p className="text-xs text-muted-foreground">
                          Calculated {new Date(intelligence.calculated_at).toLocaleString()} · v{intelligence.score_version}
                        </p>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-around py-2">
                          <ScoreRing score={intelligence.esg_score} label="Total ESG" color="stroke-blue-500" />
                          <ScoreRing score={intelligence.environmental_score} label="Environmental" color="stroke-emerald-500" />
                          <ScoreRing score={intelligence.social_score} label="Social" color="stroke-violet-500" />
                          <ScoreRing score={intelligence.governance_score} label="Governance" color="stroke-amber-500" />
                        </div>
                        <div className="mt-3 flex items-center justify-center gap-3">
                          <TrendBadge trend={intelligence.trend} delta={intelligence.trend_delta} />
                        </div>
                      </CardContent>
                    </Card>

                    {/* Risk score */}
                    <Card>
                      <CardHeader><CardTitle className="text-base">Risk Score</CardTitle></CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-5xl font-bold tabular-nums">{intelligence.risk_score.toFixed(0)}</p>
                            <p className="text-sm text-muted-foreground mt-1">out of 100</p>
                          </div>
                          <span className={`rounded-lg px-4 py-2 text-lg font-bold ${riskBandColor(intelligence.risk_band)}`}>
                            {intelligence.risk_band}
                          </span>
                        </div>
                        <div className="h-3 w-full rounded-full bg-muted">
                          <div
                            className={`h-3 rounded-full transition-all ${
                              intelligence.risk_band === "Critical" ? "bg-red-500" :
                              intelligence.risk_band === "High" ? "bg-orange-500" :
                              intelligence.risk_band === "Moderate" ? "bg-amber-400" : "bg-emerald-500"
                            }`}
                            style={{ width: `${intelligence.risk_score}%` }}
                          />
                        </div>
                        <div className="grid grid-cols-4 gap-1 text-center text-xs text-muted-foreground">
                          <span>Low<br/>0–25</span>
                          <span>Moderate<br/>26–50</span>
                          <span>High<br/>51–75</span>
                          <span>Critical<br/>76–100</span>
                        </div>
                        {intelligence.sector_percentile != null && (
                          <p className="text-xs text-muted-foreground text-center">
                            Better than {intelligence.sector_percentile.toFixed(0)}% of industry peers
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  </div>

                  {/* Score drivers */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Score Drivers</CardTitle>
                      <p className="text-xs text-muted-foreground">
                        Why this score was assigned — ordered by impact
                      </p>
                    </CardHeader>
                    <CardContent>
                      {intelligence.drivers.length === 0 ? (
                        <div className="flex flex-col items-center gap-2 py-6 text-center">
                          <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                          <p className="text-sm text-muted-foreground">No risk drivers identified. This supplier has a clean profile.</p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {intelligence.drivers.map((d, i) => (
                            <div key={i} className="flex items-start gap-3 rounded-lg border border-border p-3">
                              <span className={`mt-0.5 h-2 w-2 flex-shrink-0 rounded-full ${
                                d.impact === "high" ? "bg-red-500" :
                                d.impact === "medium" ? "bg-amber-500" : "bg-slate-400"
                              }`} />
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="text-sm font-medium">{d.factor}</p>
                                  <span className="text-sm font-bold tabular-nums">{d.count}</span>
                                </div>
                                <p className="text-xs text-muted-foreground">{d.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* Raw inputs (collapsible audit data) */}
                  <details className="rounded-lg border border-border">
                    <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground">
                      Raw Score Inputs (Audit Data)
                    </summary>
                    <div className="grid grid-cols-2 gap-2 px-4 pb-4 pt-2 text-xs sm:grid-cols-3 lg:grid-cols-4">
                      {Object.entries(intelligence.inputs).map(([k, v]) => (
                        <div key={k} className="flex justify-between rounded bg-muted/50 px-2 py-1">
                          <span className="text-muted-foreground">{k.replace(/_/g, " ")}</span>
                          <span className="font-mono font-semibold">{v}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}

          {/* History sub-tab */}
          {intelligenceSubTab === "history" && (
            <Card>
              <CardHeader><CardTitle className="text-base">Score History</CardTitle></CardHeader>
              <CardContent>
                {!history ? (
                  <div className="flex justify-center py-8"><Spinner size="lg" /></div>
                ) : history.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">No score history yet.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="pb-2 text-left font-medium">Date</th>
                        <th className="pb-2 text-right font-medium">ESG Score</th>
                        <th className="pb-2 text-right font-medium">Risk Score</th>
                        <th className="pb-2 text-center font-medium">Risk Band</th>
                        <th className="pb-2 text-center font-medium">Trend</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {history.map((h, i) => (
                        <tr key={i} className="hover:bg-muted/20">
                          <td className="py-2 text-muted-foreground">
                            {new Date(h.calculated_at).toLocaleString()}
                          </td>
                          <td className="py-2 text-right font-semibold">{h.esg_score.toFixed(1)}</td>
                          <td className="py-2 text-right font-semibold">{h.risk_score.toFixed(1)}</td>
                          <td className="py-2 text-center">
                            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${riskBandColor(h.risk_band)}`}>
                              {h.risk_band}
                            </span>
                          </td>
                          <td className="py-2 text-center">
                            <TrendBadge trend={h.trend} delta={0} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </CardContent>
            </Card>
          )}

          {/* Benchmark sub-tab */}
          {intelligenceSubTab === "benchmark" && (
            <div className="space-y-4">
              {!benchmark ? (
                <div className="flex justify-center py-8"><Spinner size="lg" /></div>
              ) : (
                <>
                  <Card>
                    <CardHeader><CardTitle className="text-base">Peer Benchmark — {benchmark.industry || "All Industries"}</CardTitle></CardHeader>
                    <CardContent className="space-y-6">
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div className="text-center">
                          <p className="text-4xl font-bold tabular-nums">{benchmark.risk_score.toFixed(0)}</p>
                          <p className="text-xs text-muted-foreground mt-1">Risk Score</p>
                          <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${riskBandColor(benchmark.risk_band)}`}>
                            {benchmark.risk_band}
                          </span>
                        </div>
                        <div className="text-center">
                          <p className="text-4xl font-bold tabular-nums">
                            {benchmark.sector_percentile != null ? `${benchmark.sector_percentile.toFixed(0)}th` : "—"}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">Percentile</p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm font-semibold mt-2">{benchmark.peer_comparison}</p>
                          <p className="text-xs text-muted-foreground mt-1">{benchmark.peers_evaluated} peers evaluated</p>
                        </div>
                      </div>

                      {benchmark.sector_percentile != null && (
                        <div>
                          <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                            <span>Worst (0th)</span>
                            <span>Best (100th)</span>
                          </div>
                          <div className="relative h-3 w-full rounded-full bg-gradient-to-r from-red-400 via-amber-400 to-emerald-500">
                            <div
                              className="absolute top-1/2 h-5 w-5 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-background bg-foreground shadow-md transition-all"
                              style={{ left: `${benchmark.sector_percentile}%` }}
                            />
                          </div>
                          <p className="mt-2 text-center text-xs text-muted-foreground">
                            This supplier is at the <strong>{benchmark.sector_percentile.toFixed(0)}th percentile</strong> — better than{" "}
                            {benchmark.sector_percentile.toFixed(0)}% of peers in {benchmark.industry || "this industry"}
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                  <p className="text-xs text-muted-foreground text-center">
                    Benchmarking is within your organization's supplier portfolio.
                  </p>

                  {/* #87 Sector intelligence comparison */}
                  {sectorProfile && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">
                          Sector Risk Profile — {sectorProfile.section_name}
                        </CardTitle>
                        <p className="text-xs text-muted-foreground">
                          NACE {supplier?.nace_code} · Industry-level E/S/G risk baseline
                        </p>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-3 gap-3 text-center text-xs">
                          {[
                            { label: "Environmental", value: sectorProfile.environmental_risk },
                            { label: "Social", value: sectorProfile.social_risk },
                            { label: "Governance", value: sectorProfile.governance_risk },
                          ].map(({ label, value }) => (
                            <div key={label} className="rounded-lg border p-2">
                              <p className="text-muted-foreground">{label}</p>
                              <p className={`font-semibold mt-0.5 ${
                                value === "HIGH" ? "text-red-600" :
                                value === "MEDIUM" ? "text-amber-600" : "text-emerald-600"
                              }`}>{value}</p>
                            </div>
                          ))}
                        </div>
                        {sectorProfile.key_risk_themes.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1.5 uppercase tracking-wide">Key Risk Themes</p>
                            <div className="flex flex-wrap gap-1">
                              {sectorProfile.key_risk_themes.slice(0, 6).map((t) => (
                                <span key={t} className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-700">{t}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {sectorProfile.applicable_frameworks.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-muted-foreground mb-1.5 uppercase tracking-wide">Applicable Frameworks</p>
                            <div className="flex flex-wrap gap-1">
                              {sectorProfile.applicable_frameworks.slice(0, 6).map((f) => (
                                <span key={f} className="rounded-full bg-blue-50 text-blue-700 px-2 py-0.5 text-[10px]">{f}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </div>
          )}

          {/* Heatmap sub-tab */}
          {intelligenceSubTab === "heatmap" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">ESG Risk Heatmap</CardTitle>
                <p className="text-xs text-muted-foreground">Finding count by ESG pillar × severity</p>
              </CardHeader>
              <CardContent>
                {!heatmap ? (
                  <div className="flex justify-center py-8"><Spinner size="lg" /></div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="py-2 text-left font-medium text-muted-foreground w-32">Pillar</th>
                          {["Critical", "High", "Medium", "Low"].map((s) => (
                            <th key={s} className={`py-2 text-center font-medium ${severityColor(s)}`}>{s}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {["Environmental", "Social", "Governance"].map((pillar) => (
                          <tr key={pillar} className="hover:bg-muted/20">
                            <td className="py-3 font-medium">{pillar}</td>
                            {["Critical", "High", "Medium", "Low"].map((sev) => {
                              const cell = heatmap.cells.find((c) => c.pillar === pillar && c.severity === sev);
                              const count = cell?.count ?? 0;
                              const maxCount = Math.max(...heatmap.cells.map((c) => c.count), 1);
                              const intensity = count / maxCount;
                              return (
                                <td key={sev} className="py-3 text-center">
                                  <div
                                    className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg font-bold transition-all"
                                    style={{
                                      backgroundColor: count === 0 ? undefined :
                                        sev === "Critical" ? `rgba(239,68,68,${0.15 + intensity * 0.6})` :
                                        sev === "High" ? `rgba(249,115,22,${0.15 + intensity * 0.6})` :
                                        sev === "Medium" ? `rgba(245,158,11,${0.15 + intensity * 0.6})` :
                                        `rgba(34,197,94,${0.15 + intensity * 0.6})`,
                                    }}
                                  >
                                    <span className={count === 0 ? "text-muted-foreground/40" : ""}>{count}</span>
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <p className="mt-3 text-right text-xs text-muted-foreground">
                      Total: {heatmap.total_findings} finding{heatmap.total_findings !== 1 ? "s" : ""}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Network Tab ───────────────────────────────────────────────────── */}
      {tab === "Network" && (
        <div className="space-y-4">
          <NetworkTab supplierId={id} />
        </div>
      )}

      {/* ── Portal Tab (#89 supplier portal conversation thread) ──────── */}
      {tab === "Portal" && (
        <SupplierPortalTab supplierId={id} supplierName={supplier.name} />
      )}

      {/* Edit Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background p-6 shadow-2xl">
            <h2 className="mb-4 text-lg font-semibold">Edit Supplier</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">Name *</label>
                <Input value={editForm.name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Legal Name</label>
                <Input value={editForm.legal_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, legal_name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Country</label>
                  <Input value={editForm.country ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, country: e.target.value }))} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">NACE Code</label>
                  <Input value={editForm.nace_code ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, nace_code: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Industry</label>
                <Input value={editForm.industry ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, industry: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Tier</label>
                  <select
                    value={editForm.supplier_tier ?? "Tier 1"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {["Tier 1", "Tier 2", "Tier 3", "Other"].map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Status</label>
                  <select
                    value={editForm.supplier_status ?? "Active"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_status: e.target.value as SupplierStatus }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="Active">Active</option>
                    <option value="Inactive">Inactive</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Website</label>
                <Input value={editForm.website ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, website: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  value={editForm.notes ?? ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={3}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            {editError && <p className="mt-3 text-sm text-red-600">{editError}</p>}
            <div className="mt-5 flex justify-end gap-3">
              <Button variant="outline" onClick={() => { setEditing(false); setEditError(null); }}>Cancel</Button>
              <Button onClick={() => updateMutation.mutate(editForm)} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Archive Confirm Modal */}
      {confirmArchive && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm rounded-xl bg-background p-6 shadow-2xl">
            <h2 className="mb-2 text-lg font-semibold text-red-600">Archive Supplier</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Are you sure you want to archive <strong>{supplier.name}</strong>? This will set the
              supplier to Inactive. Existing assessments are not affected.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setConfirmArchive(false)}>Cancel</Button>
              <Button variant="destructive" onClick={() => archiveMutation.mutate()} disabled={archiveMutation.isPending}>
                {archiveMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                Archive
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
