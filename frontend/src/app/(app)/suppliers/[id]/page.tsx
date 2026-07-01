"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/i18n/context";
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
  Shield,
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
import {
  collectIntelligence,
  getSupplierTwin,
  getSupplierTwinTimeline,
  processSupplierSignals,
  type CollectIntelligenceResponse,
  type SupplierDigitalTwin,
  type IntelligenceTimelineEvent,
} from "@/lib/api/supplier-twin";
import {
  listLocations,
  createLocation,
  deleteLocation,
  listContacts,
  createContact,
  listCertifications,
  createCertification,
  getOwnership,
  upsertOwnership,
  listESGMetrics,
  recordESGMetric,
  listESGRatings,
  createESGRating,
  deleteESGRating,
  type SupplierLocation,
  type SupplierContact,
  type SupplierCertification,
  type SupplierOwnership,
  type SupplierESGMetric,
  type ExternalESGRating,
} from "@/lib/api/supplier-extensions";
import apiClient from "@/lib/api/client";
import { sectorRiskApi, type SectorBaseline, type SimulationResult as SectorSimResult } from "@/lib/api/sector-risk";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierTier, SupplierStatus, SupplierUpdate } from "@/types/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function toAbsoluteUrl(url: string): string {
  if (!url) return url;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `https://${url}`;
}

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

// ── Twin Event Card ───────────────────────────────────────────────────────────

function TwinEventCard({ event }: { event: IntelligenceTimelineEvent }) {
  const [expanded, setExpanded] = useState(false);

  const severityColors: Record<string, string> = {
    CRITICAL: "border-red-300 bg-red-50",
    HIGH: "border-orange-300 bg-orange-50",
    MEDIUM: "border-amber-300 bg-amber-50",
    LOW: "border-slate-200 bg-slate-50",
    INFO: "border-blue-200 bg-blue-50",
  };
  const severityBadge: Record<string, string> = {
    CRITICAL: "bg-red-600 text-white",
    HIGH: "bg-orange-500 text-white",
    MEDIUM: "bg-amber-500 text-black",
    LOW: "bg-slate-400 text-white",
    INFO: "bg-blue-500 text-white",
  };
  const categoryIcons: Record<string, React.ReactNode> = {
    ESG: <BarChart3 className="h-3.5 w-3.5" />,
    COMPLIANCE: <CheckCircle2 className="h-3.5 w-3.5" />,
    FINANCIAL: <TrendingDown className="h-3.5 w-3.5" />,
    GEOPOLITICAL: <Globe className="h-3.5 w-3.5" />,
    CYBER: <ShieldAlert className="h-3.5 w-3.5" />,
    HUMAN_RIGHTS: <Users className="h-3.5 w-3.5" />,
    ENVIRONMENTAL: <Globe className="h-3.5 w-3.5" />,
    OPERATIONAL: <Network className="h-3.5 w-3.5" />,
  };

  return (
    <div className={`rounded-xl border p-4 ${severityColors[event.severity] ?? "border-border bg-card"}`}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-bold ${severityBadge[event.severity] ?? "bg-slate-400 text-white"}`}>
            {event.severity}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              {categoryIcons[event.event_category] ?? <AlertTriangle className="h-3.5 w-3.5" />}
              {event.event_category}
            </span>
            <span className="ml-auto text-xs text-muted-foreground">
              {new Date(event.occurred_at).toLocaleDateString()}
            </span>
          </div>
          <p className="mt-1 font-semibold text-sm">{event.title}</p>
          {event.source_name && (
            <div className="mt-1">
              {event.source_url ? (
                <a
                  href={toAbsoluteUrl(event.source_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline"
                >
                  <ExternalLink className="h-3 w-3" />
                  {event.source_name}
                </a>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                  <Globe className="h-3 w-3" />
                  {event.source_name}
                </span>
              )}
            </div>
          )}
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{event.summary}</p>

          {/* Health impact */}
          {event.twin_dimension_affected && event.health_delta !== 0 && (
            <div className="mt-2 flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Impact:</span>
              <span className="font-mono font-semibold text-red-600">
                {event.health_delta.toFixed(0)} pts
              </span>
              <span className="text-muted-foreground">on</span>
              <span className="font-medium">{event.twin_dimension_affected.replace("_health", "").replace("_", " ").toUpperCase()}</span>
            </div>
          )}

          {/* Expand button */}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-xs text-blue-600 hover:text-blue-800"
          >
            {expanded ? "Hide details ↑" : "Why does this matter? ↓"}
          </button>

          {expanded && (
            <div className="mt-3 space-y-3 border-t border-border pt-3">
              {event.why_important && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Why important</p>
                  <p className="text-xs">{event.why_important}</p>
                </div>
              )}
              {event.regulatory_impact && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Regulatory impact</p>
                  <p className="text-xs">{event.regulatory_impact}</p>
                </div>
              )}
              {event.recommended_action && (
                <div>
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Recommended action</p>
                  <p className="text-xs whitespace-pre-line">{event.recommended_action}</p>
                </div>
              )}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span>Confidence: {Math.round(event.confidence * 100)}%</span>
                {event.signal_id && <span>Signal: {event.signal_id.slice(0, 8)}…</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Network Tab ───────────────────────────────────────────────────────────────

function NetworkTab({ supplierId }: { supplierId: string }) {
  const { data: rels, isLoading: relsLoading } = useQuery({
    queryKey: ["supplier-network-rels", supplierId],
    queryFn: async () => {
      const res = await apiClient.get(
        `/network/relationships?supplier_id=${supplierId}&limit=50`
      );
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const { data: exposures, isLoading: expLoading } = useQuery({
    queryKey: ["supplier-network-exposures", supplierId],
    queryFn: async () => {
      const res = await apiClient.get(
        `/network/exposure-signals?impacted_supplier_id=${supplierId}&exposure_status=ACTIVE&limit=10`
      );
      return res.data;
    },
    refetchInterval: 60_000,
  });

  const { data: criticality, isLoading: critLoading } = useQuery({
    queryKey: ["supplier-criticality", supplierId],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/network/criticality/${supplierId}`);
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
        const r = await apiClient.get(`/supplier-portal/internal/conversations?supplier_id=${supplierId}`);
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
        const r = await apiClient.get(`/supplier-portal/internal/conversations/${activeConvId}/messages`);
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
        const r = await apiClient.post("/supplier-portal/internal/conversations", {
          supplier_id: supplierId, subject: `Message to ${supplierName}`,
        });
        const convId = r.data.id;
        await apiClient.post("/supplier-portal/internal/messages", {
          conversation_id: convId, content: newMessage,
        });
        qc.invalidateQueries({ queryKey: ["portal-conversations", supplierId] });
        setActiveConvId(convId);
      } else {
        await apiClient.post("/supplier-portal/internal/messages", {
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

// ── Locations Tab ─────────────────────────────────────────────────────────────

function LocationsTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ location_type: "PLANT", name: "", country: "", city: "", address: "", employee_count: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: locations = [], isLoading } = useQuery<SupplierLocation[]>({
    queryKey: ["supplier-locations", supplierId],
    queryFn: () => listLocations(supplierId),
  });

  async function handleCreate() {
    if (!form.name.trim()) { setError("Name is required"); return; }
    setSaving(true); setError(null);
    try {
      await createLocation(supplierId, {
        location_type: form.location_type,
        name: form.name,
        country: form.country || undefined,
        city: form.city || undefined,
        address: form.address || undefined,
        employee_count: form.employee_count ? parseInt(form.employee_count) : undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-locations", supplierId] });
      setShowForm(false);
      setForm({ location_type: "PLANT", name: "", country: "", city: "", address: "", employee_count: "" });
    } catch { setError("Failed to create location"); }
    finally { setSaving(false); }
  }

  async function handleDelete(locationId: string) {
    try {
      await deleteLocation(supplierId, locationId);
      qc.invalidateQueries({ queryKey: ["supplier-locations", supplierId] });
    } catch { /* ignore */ }
  }

  const locationTypeColors: Record<string, string> = {
    PLANT: "bg-blue-100 text-blue-800",
    WAREHOUSE: "bg-purple-100 text-purple-800",
    OFFICE: "bg-slate-100 text-slate-700",
    R_AND_D: "bg-violet-100 text-violet-800",
    DISTRIBUTION_CENTER: "bg-amber-100 text-amber-800",
    SUPPLIER_HUB: "bg-teal-100 text-teal-800",
    OTHER: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Supplier Locations ({locations.length})</h3>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Location"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Type *</label>
                <select
                  value={form.location_type}
                  onChange={(e) => setForm((f) => ({ ...f, location_type: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {["PLANT", "WAREHOUSE", "OFFICE", "R_AND_D", "DISTRIBUTION_CENTER", "SUPPLIER_HUB", "OTHER"].map((t) => (
                    <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Name *</label>
                <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Main Manufacturing Plant" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Country</label>
                <Input value={form.country} onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))} placeholder="DE" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">City</label>
                <Input value={form.city} onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))} placeholder="Munich" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Address</label>
                <Input value={form.address} onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))} placeholder="Street address" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Employee Count</label>
                <Input type="number" value={form.employee_count} onChange={(e) => setForm((f) => ({ ...f, employee_count: e.target.value }))} placeholder="0" />
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={saving}>{saving ? "Saving…" : "Save Location"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : locations.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <Globe className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No locations recorded yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {locations.map((loc) => (
            <Card key={loc.id}>
              <CardContent className="pt-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${locationTypeColors[loc.location_type] ?? "bg-gray-100 text-gray-700"}`}>
                      {loc.location_type.replace(/_/g, " ")}
                    </span>
                    {loc.is_primary && (
                      <span className="ml-1 inline-flex rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">PRIMARY</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDelete(loc.id)}
                    className="text-muted-foreground hover:text-red-500 transition-colors text-xs"
                  >
                    ✕
                  </button>
                </div>
                <p className="text-sm font-medium">{loc.name}</p>
                {(loc.city || loc.country) && (
                  <p className="text-xs text-muted-foreground">{[loc.city, loc.country].filter(Boolean).join(", ")}</p>
                )}
                {loc.address && <p className="text-xs text-muted-foreground">{loc.address}</p>}
                {loc.employee_count != null && (
                  <p className="text-xs text-muted-foreground">{loc.employee_count.toLocaleString()} employees</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Contacts Tab ──────────────────────────────────────────────────────────────

function ContactsTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "", role: "ACCOUNT_MANAGER", job_title: "", department: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: contacts = [], isLoading } = useQuery<SupplierContact[]>({
    queryKey: ["supplier-contacts", supplierId],
    queryFn: () => listContacts(supplierId),
  });

  async function handleCreate() {
    if (!form.first_name.trim()) { setError("First name is required"); return; }
    setSaving(true); setError(null);
    try {
      await createContact(supplierId, {
        first_name: form.first_name,
        last_name: form.last_name || undefined,
        email: form.email || undefined,
        phone: form.phone || undefined,
        role: form.role,
        job_title: form.job_title || undefined,
        department: form.department || undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-contacts", supplierId] });
      setShowForm(false);
      setForm({ first_name: "", last_name: "", email: "", phone: "", role: "ACCOUNT_MANAGER", job_title: "", department: "" });
    } catch { setError("Failed to create contact"); }
    finally { setSaving(false); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Supplier Contacts ({contacts.length})</h3>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Contact"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">First Name *</label>
                <Input value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} placeholder="John" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Last Name</label>
                <Input value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} placeholder="Doe" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Role *</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {["ACCOUNT_MANAGER", "ESG_CONTACT", "COMPLIANCE_OFFICER", "TECHNICAL_CONTACT", "EXECUTIVE", "FINANCE_CONTACT", "LEGAL_CONTACT", "OTHER"].map((r) => (
                    <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Job Title</label>
                <Input value={form.job_title} onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))} placeholder="Head of ESG" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Email</label>
                <Input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} placeholder="john@supplier.com" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Phone</label>
                <Input value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} placeholder="+49 89 123456" />
              </div>
              <div className="col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Department</label>
                <Input value={form.department} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))} placeholder="Sustainability" />
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={saving}>{saving ? "Saving…" : "Save Contact"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : contacts.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <Users className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No contacts recorded yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {contacts.map((c) => (
            <Card key={c.id}>
              <CardContent className="pt-4 space-y-1">
                {c.is_primary && (
                  <span className="inline-flex rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold text-blue-800">PRIMARY</span>
                )}
                <p className="text-sm font-semibold">{c.full_name}</p>
                <p className="text-xs text-muted-foreground">{c.role.replace(/_/g, " ")}{c.job_title ? ` · ${c.job_title}` : ""}</p>
                {c.department && <p className="text-xs text-muted-foreground">{c.department}</p>}
                {c.email && (
                  <a href={`mailto:${c.email}`} className="text-xs text-blue-600 hover:underline block">{c.email}</a>
                )}
                {c.phone && <p className="text-xs text-muted-foreground">{c.phone}</p>}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Certifications Tab ────────────────────────────────────────────────────────

function CertificationsTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ cert_type: "ISO_14001", issuing_body: "", certificate_number: "", valid_from: "", valid_until: "", scope_description: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: certs = [], isLoading } = useQuery<SupplierCertification[]>({
    queryKey: ["supplier-certifications", supplierId],
    queryFn: () => listCertifications(supplierId),
  });

  async function handleCreate() {
    setSaving(true); setError(null);
    try {
      await createCertification(supplierId, {
        cert_type: form.cert_type,
        issuing_body: form.issuing_body || undefined,
        certificate_number: form.certificate_number || undefined,
        valid_from: form.valid_from || undefined,
        valid_until: form.valid_until || undefined,
        scope_description: form.scope_description || undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-certifications", supplierId] });
      setShowForm(false);
      setForm({ cert_type: "ISO_14001", issuing_body: "", certificate_number: "", valid_from: "", valid_until: "", scope_description: "" });
    } catch { setError("Failed to create certification"); }
    finally { setSaving(false); }
  }

  function expiryBadge(cert: SupplierCertification) {
    if (cert.is_expired) {
      return <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-800">EXPIRED</span>;
    }
    if (cert.days_until_expiry !== null && cert.days_until_expiry <= 90) {
      return <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-800">EXPIRING SOON</span>;
    }
    if (cert.valid_until) {
      return <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">VALID</span>;
    }
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Certifications ({certs.length})</h3>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Certification"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Certification Type *</label>
                <select
                  value={form.cert_type}
                  onChange={(e) => setForm((f) => ({ ...f, cert_type: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {["ISO_14001", "ISO_9001", "ISO_45001", "ISO_50001", "SA8000", "IATF_16949", "REACH_COMPLIANT", "ROHS_COMPLIANT", "CONFLICT_MINERALS_FREE", "ECOVADIS_BRONZE", "ECOVADIS_SILVER", "ECOVADIS_GOLD", "ECOVADIS_PLATINUM", "B_CORP", "FSSC_22000", "OTHER"].map((t) => (
                    <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Issuing Body</label>
                <Input value={form.issuing_body} onChange={(e) => setForm((f) => ({ ...f, issuing_body: e.target.value }))} placeholder="TÜV SÜD" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Certificate Number</label>
                <Input value={form.certificate_number} onChange={(e) => setForm((f) => ({ ...f, certificate_number: e.target.value }))} placeholder="DE-12345-2024" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Scope</label>
                <Input value={form.scope_description} onChange={(e) => setForm((f) => ({ ...f, scope_description: e.target.value }))} placeholder="Manufacturing operations" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Valid From</label>
                <Input type="date" value={form.valid_from} onChange={(e) => setForm((f) => ({ ...f, valid_from: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Valid Until</label>
                <Input type="date" value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))} />
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={saving}>{saving ? "Saving…" : "Save Certification"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : certs.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <CheckCircle2 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No certifications recorded yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {certs.map((cert) => (
            <Card key={cert.id} className={cert.is_expired ? "border-red-200" : ""}>
              <CardContent className="pt-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">{cert.cert_type.replace(/_/g, " ")}</span>
                  {expiryBadge(cert)}
                </div>
                {cert.issuing_body && <p className="text-xs text-muted-foreground">{cert.issuing_body}</p>}
                {cert.certificate_number && <p className="text-xs font-mono text-muted-foreground">{cert.certificate_number}</p>}
                {cert.scope_description && <p className="text-xs text-muted-foreground">{cert.scope_description}</p>}
                <div className="text-xs text-muted-foreground">
                  {cert.valid_from && <span>From: {cert.valid_from}</span>}
                  {cert.valid_from && cert.valid_until && <span> · </span>}
                  {cert.valid_until && <span>Until: {cert.valid_until}</span>}
                  {cert.days_until_expiry !== null && !cert.is_expired && (
                    <span className="ml-1 text-amber-600">({cert.days_until_expiry}d left)</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Ownership Tab ─────────────────────────────────────────────────────────────

function OwnershipTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    ownership_type: "PRIVATE",
    parent_company_name: "",
    parent_company_country: "",
    ultimate_parent_name: "",
    ultimate_parent_country: "",
    is_state_owned: false,
    state_ownership_pct: "",
    publicly_listed: false,
    stock_exchange: "",
    ticker_symbol: "",
    lei_code: "",
    duns_number: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: ownership, isLoading } = useQuery<SupplierOwnership | null>({
    queryKey: ["supplier-ownership", supplierId],
    queryFn: () => getOwnership(supplierId),
  });

  function startEdit() {
    if (ownership) {
      setForm({
        ownership_type: ownership.ownership_type,
        parent_company_name: ownership.parent_company_name ?? "",
        parent_company_country: ownership.parent_company_country ?? "",
        ultimate_parent_name: ownership.ultimate_parent_name ?? "",
        ultimate_parent_country: ownership.ultimate_parent_country ?? "",
        is_state_owned: ownership.is_state_owned,
        state_ownership_pct: ownership.state_ownership_pct?.toString() ?? "",
        publicly_listed: ownership.publicly_listed,
        stock_exchange: ownership.stock_exchange ?? "",
        ticker_symbol: ownership.ticker_symbol ?? "",
        lei_code: ownership.lei_code ?? "",
        duns_number: ownership.duns_number ?? "",
      });
    }
    setEditing(true);
  }

  async function handleSave() {
    setSaving(true); setError(null);
    try {
      await upsertOwnership(supplierId, {
        ownership_type: form.ownership_type,
        parent_company_name: form.parent_company_name || undefined,
        parent_company_country: form.parent_company_country || undefined,
        ultimate_parent_name: form.ultimate_parent_name || undefined,
        ultimate_parent_country: form.ultimate_parent_country || undefined,
        is_state_owned: form.is_state_owned,
        state_ownership_pct: form.state_ownership_pct ? parseFloat(form.state_ownership_pct) : undefined,
        publicly_listed: form.publicly_listed,
        stock_exchange: form.stock_exchange || undefined,
        ticker_symbol: form.ticker_symbol || undefined,
        lei_code: form.lei_code || undefined,
        duns_number: form.duns_number || undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-ownership", supplierId] });
      setEditing(false);
    } catch { setError("Failed to save ownership data"); }
    finally { setSaving(false); }
  }

  if (isLoading) {
    return <div className="flex justify-center py-8"><Spinner /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Ownership Structure</h3>
        <Button size="sm" onClick={editing ? () => setEditing(false) : startEdit}>
          {editing ? "Cancel" : (ownership ? "Edit" : "+ Add Ownership")}
        </Button>
      </div>

      {editing && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ownership Type *</label>
                <select
                  value={form.ownership_type}
                  onChange={(e) => setForm((f) => ({ ...f, ownership_type: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {["PRIVATE", "PUBLIC", "STATE_OWNED", "SUBSIDIARY", "JOINT_VENTURE", "COOPERATIVE", "FAMILY_OWNED", "UNKNOWN"].map((t) => (
                    <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Parent Company</label>
                <Input value={form.parent_company_name} onChange={(e) => setForm((f) => ({ ...f, parent_company_name: e.target.value }))} placeholder="Acme Holdings GmbH" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Parent Country</label>
                <Input value={form.parent_company_country} onChange={(e) => setForm((f) => ({ ...f, parent_company_country: e.target.value }))} placeholder="DE" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ultimate Parent</label>
                <Input value={form.ultimate_parent_name} onChange={(e) => setForm((f) => ({ ...f, ultimate_parent_name: e.target.value }))} placeholder="Global Corp Inc." />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ultimate Parent Country</label>
                <Input value={form.ultimate_parent_country} onChange={(e) => setForm((f) => ({ ...f, ultimate_parent_country: e.target.value }))} placeholder="US" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">LEI Code</label>
                <Input value={form.lei_code} onChange={(e) => setForm((f) => ({ ...f, lei_code: e.target.value }))} placeholder="5493001KJTIIGC8Y1R12" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">D-U-N-S Number</label>
                <Input value={form.duns_number} onChange={(e) => setForm((f) => ({ ...f, duns_number: e.target.value }))} placeholder="12-345-6789" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Stock Exchange</label>
                <Input value={form.stock_exchange} onChange={(e) => setForm((f) => ({ ...f, stock_exchange: e.target.value }))} placeholder="NYSE" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ticker Symbol</label>
                <Input value={form.ticker_symbol} onChange={(e) => setForm((f) => ({ ...f, ticker_symbol: e.target.value }))} placeholder="ACME" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">State Ownership %</label>
                <Input type="number" value={form.state_ownership_pct} onChange={(e) => setForm((f) => ({ ...f, state_ownership_pct: e.target.value }))} placeholder="0" />
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                  <input type="checkbox" checked={form.is_state_owned} onChange={(e) => setForm((f) => ({ ...f, is_state_owned: e.target.checked }))} className="rounded" />
                  State Owned
                </label>
                <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                  <input type="checkbox" checked={form.publicly_listed} onChange={(e) => setForm((f) => ({ ...f, publicly_listed: e.target.checked }))} className="rounded" />
                  Publicly Listed
                </label>
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setEditing(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleSave} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!editing && !ownership && (
        <Card>
          <CardContent className="py-10 text-center">
            <Briefcase className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No ownership data recorded yet.</p>
          </CardContent>
        </Card>
      )}

      {!editing && ownership && (
        <Card>
          <CardContent className="pt-4">
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Ownership Type</dt>
                <dd className="font-medium">{ownership.ownership_type.replace(/_/g, " ")}</dd>
              </div>
              {ownership.parent_company_name && (
                <div>
                  <dt className="text-xs text-muted-foreground">Parent Company</dt>
                  <dd className="font-medium">{ownership.parent_company_name} {ownership.parent_company_country && <span className="text-muted-foreground">({ownership.parent_company_country})</span>}</dd>
                </div>
              )}
              {ownership.ultimate_parent_name && (
                <div>
                  <dt className="text-xs text-muted-foreground">Ultimate Parent</dt>
                  <dd className="font-medium">{ownership.ultimate_parent_name} {ownership.ultimate_parent_country && <span className="text-muted-foreground">({ownership.ultimate_parent_country})</span>}</dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-muted-foreground">State Owned</dt>
                <dd className={`font-medium ${ownership.is_state_owned ? "text-amber-600" : "text-muted-foreground"}`}>
                  {ownership.is_state_owned ? `Yes ${ownership.state_ownership_pct != null ? `(${ownership.state_ownership_pct}%)` : ""}` : "No"}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Publicly Listed</dt>
                <dd className="font-medium">
                  {ownership.publicly_listed
                    ? `Yes${ownership.stock_exchange ? ` · ${ownership.stock_exchange}` : ""}${ownership.ticker_symbol ? ` : ${ownership.ticker_symbol}` : ""}`
                    : "No"}
                </dd>
              </div>
              {ownership.lei_code && (
                <div>
                  <dt className="text-xs text-muted-foreground">LEI</dt>
                  <dd className="font-mono text-xs">{ownership.lei_code}</dd>
                </div>
              )}
              {ownership.duns_number && (
                <div>
                  <dt className="text-xs text-muted-foreground">D-U-N-S</dt>
                  <dd className="font-mono text-xs">{ownership.duns_number}</dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── ESG Metrics Tab ───────────────────────────────────────────────────────────

function ESGMetricsTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [yearFilter, setYearFilter] = useState<string>("");
  const [form, setForm] = useState({
    reporting_year: new Date().getFullYear().toString(),
    metric_type: "GHG_SCOPE1_TONNES_CO2E",
    value: "",
    unit: "tCO2e",
    esrs_reference: "",
    gri_reference: "",
    data_source: "",
    is_third_party_verified: false,
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: metrics = [], isLoading } = useQuery<SupplierESGMetric[]>({
    queryKey: ["supplier-esg-metrics", supplierId, yearFilter],
    queryFn: () => listESGMetrics(supplierId, yearFilter ? parseInt(yearFilter) : undefined),
  });

  async function handleCreate() {
    if (!form.value) { setError("Value is required"); return; }
    setSaving(true); setError(null);
    try {
      await recordESGMetric(supplierId, {
        reporting_year: parseInt(form.reporting_year),
        metric_type: form.metric_type,
        value: parseFloat(form.value),
        unit: form.unit || undefined,
        esrs_reference: form.esrs_reference || undefined,
        gri_reference: form.gri_reference || undefined,
        data_source: form.data_source || undefined,
        is_third_party_verified: form.is_third_party_verified,
        notes: form.notes || undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-esg-metrics", supplierId] });
      setShowForm(false);
      setForm({ reporting_year: new Date().getFullYear().toString(), metric_type: "GHG_SCOPE1_TONNES_CO2E", value: "", unit: "tCO2e", esrs_reference: "", gri_reference: "", data_source: "", is_third_party_verified: false, notes: "" });
    } catch { setError("Failed to record metric"); }
    finally { setSaving(false); }
  }

  const categoryColors: Record<string, string> = {
    GHG: "bg-blue-100 text-blue-800",
    ENERGY: "bg-yellow-100 text-yellow-800",
    WATER: "bg-cyan-100 text-cyan-800",
    WASTE: "bg-orange-100 text-orange-800",
    SOCIAL: "bg-purple-100 text-purple-800",
    GOVERNANCE: "bg-slate-100 text-slate-700",
  };

  function metricCategory(metricType: string): string {
    if (metricType.startsWith("GHG")) return "GHG";
    if (metricType.startsWith("ENERGY")) return "ENERGY";
    if (metricType.startsWith("WATER")) return "WATER";
    if (metricType.startsWith("WASTE")) return "WASTE";
    if (["FEMALE_LEADERSHIP_PCT", "GENDER_PAY_GAP_PCT", "INJURY_RATE_PER_1M_HOURS", "LOST_TIME_INJURY_RATE", "FATALITIES", "CHILD_LABOUR_INCIDENTS", "FORCED_LABOUR_INCIDENTS", "COLLECTIVE_BARGAINING_COVERAGE_PCT", "EMPLOYEE_TRAINING_HOURS"].includes(metricType)) return "SOCIAL";
    return "GOVERNANCE";
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold flex-1">ESG Metrics ({metrics.length})</h3>
        <select
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        >
          <option value="">All Years</option>
          {[2025, 2024, 2023, 2022, 2021].map((y) => (
            <option key={y} value={y.toString()}>{y}</option>
          ))}
        </select>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Record Metric"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Metric Type *</label>
                <select
                  value={form.metric_type}
                  onChange={(e) => setForm((f) => ({ ...f, metric_type: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {["GHG_SCOPE1_TONNES_CO2E", "GHG_SCOPE2_TONNES_CO2E", "GHG_SCOPE3_TONNES_CO2E", "GHG_INTENSITY_TONNE_PER_REVENUE", "ENERGY_TOTAL_MWH", "ENERGY_RENEWABLE_PCT", "WATER_WITHDRAWAL_M3", "WATER_RECYCLED_PCT", "WASTE_TOTAL_TONNES", "WASTE_RECYCLED_PCT", "HAZARDOUS_WASTE_TONNES", "FEMALE_LEADERSHIP_PCT", "GENDER_PAY_GAP_PCT", "INJURY_RATE_PER_1M_HOURS", "LOST_TIME_INJURY_RATE", "FATALITIES", "CHILD_LABOUR_INCIDENTS", "FORCED_LABOUR_INCIDENTS", "COLLECTIVE_BARGAINING_COVERAGE_PCT", "EMPLOYEE_TRAINING_HOURS", "SUPPLY_CHAIN_DUE_DILIGENCE_COVERAGE_PCT", "SUPPLIERS_AUDITED_PCT", "SUPPLIERS_WITH_CODE_OF_CONDUCT_PCT", "CUSTOM"].map((t) => (
                    <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Reporting Year *</label>
                <Input type="number" value={form.reporting_year} onChange={(e) => setForm((f) => ({ ...f, reporting_year: e.target.value }))} placeholder="2024" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Value *</label>
                <Input type="number" value={form.value} onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))} placeholder="0.0" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Unit</label>
                <Input value={form.unit} onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))} placeholder="tCO2e" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">ESRS Reference</label>
                <Input value={form.esrs_reference} onChange={(e) => setForm((f) => ({ ...f, esrs_reference: e.target.value }))} placeholder="E1-5" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">GRI Reference</label>
                <Input value={form.gri_reference} onChange={(e) => setForm((f) => ({ ...f, gri_reference: e.target.value }))} placeholder="GRI 305-1" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Data Source</label>
                <Input value={form.data_source} onChange={(e) => setForm((f) => ({ ...f, data_source: e.target.value }))} placeholder="Annual sustainability report" />
              </div>
              <div className="flex items-center gap-2 pt-4">
                <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                  <input type="checkbox" checked={form.is_third_party_verified} onChange={(e) => setForm((f) => ({ ...f, is_third_party_verified: e.target.checked }))} className="rounded" />
                  Third-party verified
                </label>
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={saving}>{saving ? "Saving…" : "Record Metric"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : metrics.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <BarChart3 className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No ESG metrics recorded yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {metrics.map((m) => {
            const cat = metricCategory(m.metric_type);
            return (
              <Card key={m.id}>
                <CardContent className="pt-4 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${categoryColors[cat] ?? "bg-gray-100 text-gray-700"}`}>{cat}</span>
                    {m.is_third_party_verified && (
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold text-green-800">VERIFIED</span>
                    )}
                  </div>
                  <p className="text-xs font-medium text-muted-foreground">{m.metric_type.replace(/_/g, " ")}</p>
                  <p className="text-lg font-bold">
                    {m.value.toLocaleString()} <span className="text-xs font-normal text-muted-foreground">{m.unit}</span>
                  </p>
                  <p className="text-xs text-muted-foreground">FY {m.reporting_year}</p>
                  {(m.esrs_reference || m.gri_reference) && (
                    <p className="text-[10px] text-muted-foreground">
                      {[m.esrs_reference, m.gri_reference].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  {m.data_source && <p className="text-[10px] text-muted-foreground truncate">{m.data_source}</p>}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── ESG Ratings Tab (KAN-90) ──────────────────────────────────────────────────

const PROVIDER_META: Record<string, { label: string; color: string; maxScore?: number }> = {
  ECOVADIS:       { label: "EcoVadis",        color: "bg-orange-100 text-orange-800",  maxScore: 100 },
  MSCI:           { label: "MSCI ESG",         color: "bg-blue-100 text-blue-800" },
  SUSTAINALYTICS: { label: "Sustainalytics",   color: "bg-teal-100 text-teal-800" },
  CDP:            { label: "CDP",              color: "bg-green-100 text-green-800" },
  ISS_ESG:        { label: "ISS-ESG",          color: "bg-purple-100 text-purple-800" },
  REFINITIV:      { label: "Refinitiv",        color: "bg-sky-100 text-sky-800" },
  SP_GLOBAL:      { label: "S&P Global ESG",   color: "bg-red-100 text-red-800" },
  BLOOMBERG_ESG:  { label: "Bloomberg ESG",    color: "bg-slate-100 text-slate-700" },
  FTSE_RUSSELL:   { label: "FTSE Russell",     color: "bg-indigo-100 text-indigo-800" },
  MOODY_ESG:      { label: "Moody's ESG",      color: "bg-amber-100 text-amber-800" },
  OTHER:          { label: "Other",            color: "bg-gray-100 text-gray-700" },
};

function ESGRatingsTab({ supplierId }: { supplierId: string }) {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    provider: "ECOVADIS",
    rating_date: "",
    score: "",
    max_score: "",
    score_pct: "",
    grade: "",
    percentile: "",
    peer_group: "",
    environmental_score: "",
    social_score: "",
    governance_score: "",
    ethics_score: "",
    sustainable_procurement_score: "",
    valid_until: "",
    report_url: "",
    methodology_version: "",
    notes: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: ratings = [], isLoading } = useQuery<ExternalESGRating[]>({
    queryKey: ["supplier-esg-ratings", supplierId],
    queryFn: () => listESGRatings(supplierId),
  });

  async function handleCreate() {
    if (!form.rating_date) { setError("Rating date is required"); return; }
    setSaving(true); setError(null);
    try {
      await createESGRating(supplierId, {
        provider: form.provider,
        rating_date: form.rating_date,
        score: form.score ? parseFloat(form.score) : undefined,
        max_score: form.max_score ? parseFloat(form.max_score) : undefined,
        score_pct: form.score_pct ? parseFloat(form.score_pct) : undefined,
        grade: form.grade || undefined,
        percentile: form.percentile ? parseFloat(form.percentile) : undefined,
        peer_group: form.peer_group || undefined,
        environmental_score: form.environmental_score ? parseFloat(form.environmental_score) : undefined,
        social_score: form.social_score ? parseFloat(form.social_score) : undefined,
        governance_score: form.governance_score ? parseFloat(form.governance_score) : undefined,
        ethics_score: form.ethics_score ? parseFloat(form.ethics_score) : undefined,
        sustainable_procurement_score: form.sustainable_procurement_score ? parseFloat(form.sustainable_procurement_score) : undefined,
        valid_until: form.valid_until || undefined,
        report_url: form.report_url || undefined,
        methodology_version: form.methodology_version || undefined,
        notes: form.notes || undefined,
      });
      qc.invalidateQueries({ queryKey: ["supplier-esg-ratings", supplierId] });
      setShowForm(false);
      setForm({ provider: "ECOVADIS", rating_date: "", score: "", max_score: "", score_pct: "", grade: "", percentile: "", peer_group: "", environmental_score: "", social_score: "", governance_score: "", ethics_score: "", sustainable_procurement_score: "", valid_until: "", report_url: "", methodology_version: "", notes: "" });
    } catch { setError("Failed to save rating"); }
    finally { setSaving(false); }
  }

  async function handleDelete(ratingId: string) {
    try {
      await deleteESGRating(supplierId, ratingId);
      qc.invalidateQueries({ queryKey: ["supplier-esg-ratings", supplierId] });
    } catch { /* ignore */ }
  }

  function scoreBar(pct: number | null) {
    if (pct === null) return null;
    const color = pct >= 75 ? "bg-green-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
    return (
      <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    );
  }

  const latestByProvider = Object.values(
    ratings.reduce<Record<string, ExternalESGRating>>((acc, r) => {
      if (!acc[r.provider] || r.rating_date > acc[r.provider].rating_date) acc[r.provider] = r;
      return acc;
    }, {})
  );

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">External ESG Ratings ({ratings.length})</h3>
          {latestByProvider.length > 0 && (
            <p className="text-xs text-muted-foreground mt-0.5">{latestByProvider.length} provider{latestByProvider.length !== 1 ? "s" : ""} tracked</p>
          )}
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "+ Add Rating"}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Provider *</label>
                <select
                  value={form.provider}
                  onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {Object.entries(PROVIDER_META).map(([k, v]) => (
                    <option key={k} value={k}>{v.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Rating Date *</label>
                <input type="date" value={form.rating_date} onChange={(e) => setForm((f) => ({ ...f, rating_date: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Score</label>
                <Input type="number" value={form.score} onChange={(e) => setForm((f) => ({ ...f, score: e.target.value }))} placeholder="62" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Max Score</label>
                <Input type="number" value={form.max_score} onChange={(e) => setForm((f) => ({ ...f, max_score: e.target.value }))} placeholder="100" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Score % (0–100)</label>
                <Input type="number" value={form.score_pct} onChange={(e) => setForm((f) => ({ ...f, score_pct: e.target.value }))} placeholder="62" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Grade / Tier</label>
                <Input value={form.grade} onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))} placeholder="GOLD / AA / CDP_A" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Percentile (0–100)</label>
                <Input type="number" value={form.percentile} onChange={(e) => setForm((f) => ({ ...f, percentile: e.target.value }))} placeholder="82" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Peer Group</label>
                <Input value={form.peer_group} onChange={(e) => setForm((f) => ({ ...f, peer_group: e.target.value }))} placeholder="Automotive Components" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">E-Score</label>
                <Input type="number" value={form.environmental_score} onChange={(e) => setForm((f) => ({ ...f, environmental_score: e.target.value }))} placeholder="65" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">S-Score</label>
                <Input type="number" value={form.social_score} onChange={(e) => setForm((f) => ({ ...f, social_score: e.target.value }))} placeholder="60" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">G-Score</label>
                <Input type="number" value={form.governance_score} onChange={(e) => setForm((f) => ({ ...f, governance_score: e.target.value }))} placeholder="58" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Ethics Score (EcoVadis)</label>
                <Input type="number" value={form.ethics_score} onChange={(e) => setForm((f) => ({ ...f, ethics_score: e.target.value }))} placeholder="55" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Valid Until</label>
                <input type="date" value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Report URL</label>
                <Input value={form.report_url} onChange={(e) => setForm((f) => ({ ...f, report_url: e.target.value }))} placeholder="https://ecovadis.com/..." />
              </div>
              <div className="col-span-2">
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Methodology Version</label>
                <Input value={form.methodology_version} onChange={(e) => setForm((f) => ({ ...f, methodology_version: e.target.value }))} placeholder="EcoVadis 2024" />
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setError(null); }}>Cancel</Button>
              <Button size="sm" onClick={handleCreate} disabled={saving}>{saving ? "Saving…" : "Save Rating"}</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><Spinner /></div>
      ) : ratings.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <TrendingUp className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">No external ESG ratings recorded yet.</p>
            <p className="mt-1 text-xs text-muted-foreground">Add scores from EcoVadis, MSCI, Sustainalytics, CDP, or other providers.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Latest per provider summary */}
          {latestByProvider.length > 1 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Latest per Provider</p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {latestByProvider.map((r) => {
                  const meta = PROVIDER_META[r.provider] ?? PROVIDER_META.OTHER;
                  return (
                    <Card key={r.provider} className={r.is_expired ? "border-red-200 opacity-60" : ""}>
                      <CardContent className="pt-3 pb-3 space-y-1">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${meta.color}`}>{meta.label}</span>
                        <div className="flex items-end gap-2">
                          {r.score_pct !== null ? (
                            <span className="text-xl font-bold">{r.score_pct.toFixed(0)}<span className="text-xs font-normal text-muted-foreground">%</span></span>
                          ) : r.grade ? (
                            <span className="text-xl font-bold">{r.grade}</span>
                          ) : (
                            <span className="text-sm text-muted-foreground">—</span>
                          )}
                          {r.percentile !== null && (
                            <span className="text-xs text-muted-foreground mb-0.5">P{r.percentile.toFixed(0)}</span>
                          )}
                        </div>
                        {scoreBar(r.score_pct)}
                        <p className="text-[10px] text-muted-foreground">{r.rating_date}</p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* All ratings */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">All Ratings</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {ratings.map((r) => {
                const meta = PROVIDER_META[r.provider] ?? PROVIDER_META.OTHER;
                return (
                  <Card key={r.id} className={r.is_expired ? "border-red-200" : ""}>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-start justify-between">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${meta.color}`}>{meta.label}</span>
                        <button onClick={() => handleDelete(r.id)} className="text-muted-foreground hover:text-red-500 transition-colors text-xs">✕</button>
                      </div>

                      {/* Main score */}
                      <div className="flex items-center gap-2">
                        {r.score_pct !== null && (
                          <span className="text-lg font-bold">{r.score_pct.toFixed(1)}<span className="text-xs font-normal text-muted-foreground">%</span></span>
                        )}
                        {r.grade && <span className="rounded bg-muted px-1.5 py-0.5 text-xs font-semibold">{r.grade}</span>}
                        {r.is_expired && <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-800">EXPIRED</span>}
                      </div>
                      {scoreBar(r.score_pct)}

                      {/* Sub-scores */}
                      {(r.environmental_score !== null || r.social_score !== null || r.governance_score !== null) && (
                        <div className="grid grid-cols-3 gap-1 pt-1">
                          {[["E", r.environmental_score], ["S", r.social_score], ["G", r.governance_score]].map(([label, val]) => (
                            <div key={label as string} className="text-center">
                              <p className="text-[10px] text-muted-foreground">{label as string}</p>
                              <p className="text-xs font-semibold">{val !== null ? (val as number).toFixed(0) : "—"}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {r.percentile !== null && (
                        <p className="text-xs text-muted-foreground">P{r.percentile.toFixed(0)} {r.peer_group ? `· ${r.peer_group}` : ""}</p>
                      )}
                      <p className="text-[10px] text-muted-foreground">Rated: {r.rating_date}</p>
                      {r.valid_until && (
                        <p className={`text-[10px] ${r.is_expired ? "text-red-500" : r.days_until_expiry !== null && r.days_until_expiry <= 90 ? "text-amber-600" : "text-muted-foreground"}`}>
                          Valid until: {r.valid_until}{r.days_until_expiry !== null && !r.is_expired ? ` (${r.days_until_expiry}d)` : ""}
                        </p>
                      )}
                      {r.report_url && (
                        <a href={toAbsoluteUrl(r.report_url)} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[10px] text-blue-600 hover:underline">
                          <ExternalLink className="h-3 w-3" /> Report
                        </a>
                      )}
                      {r.methodology_version && <p className="text-[10px] text-muted-foreground">{r.methodology_version}</p>}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS = ["Overview", "Assessments", "Findings", "Risk Profile", "Sector Risk", "Intelligence", "Twin", "Network", "Portal", "Locations", "Contacts", "Certifications", "Ownership", "ESG Metrics", "ESG Ratings"] as const;
type Tab = typeof TABS[number];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SupplierDetailPage() {
  const { t } = useLanguage();
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

  // Global intelligence collection
  const [collecting, setCollecting] = useState(false);
  const [collectResult, setCollectResult] = useState<CollectIntelligenceResponse | null>(null);
  const [collectError, setCollectError] = useState<string | null>(null);

  // Due diligence
  const [ddBusy, setDdBusy] = useState(false);
  const [ddError, setDdError] = useState<string | null>(null);
  const [ddSuccess, setDdSuccess] = useState(false);

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

  // ── Sector Risk queries ────────────────────────────────────────────────────
  const [sectorScenario, setSectorScenario] = useState<string>("");
  const { data: sectorBaseline } = useQuery({
    queryKey: ["sector-baseline-supplier", supplier?.nace_code],
    queryFn: () => sectorRiskApi.getSector(supplier!.nace_code!),
    enabled: !!supplier?.nace_code && tab === "Sector Risk",
    staleTime: 300_000,
  });
  const { data: sectorSimulation, isLoading: sectorSimLoading } = useQuery({
    queryKey: ["sector-simulate-supplier", supplier?.nace_code, sectorScenario],
    queryFn: () => sectorRiskApi.simulate(supplier!.nace_code!, sectorScenario),
    enabled: !!supplier?.nace_code && tab === "Sector Risk" && !!sectorScenario,
    staleTime: 300_000,
  });

  // ── Digital Twin queries ───────────────────────────────────────────────────
  const { data: twin, isLoading: twinLoading, refetch: refetchTwin } = useQuery({
    queryKey: ["supplier-twin", id],
    queryFn: () => getSupplierTwin(id),
    enabled: !!id && tab === "Twin",
    staleTime: 60_000,
  });

  const { data: twinTimeline, isLoading: timelineLoading, refetch: refetchTimeline } = useQuery({
    queryKey: ["supplier-twin-timeline", id],
    queryFn: () => getSupplierTwinTimeline(id, { limit: 50 }),
    enabled: !!id && tab === "Twin",
    staleTime: 60_000,
  });

  const [processingSignals, setProcessingSignals] = useState(false);
  const [processResult, setProcessResult] = useState<string | null>(null);

  const { data: dueDiligence, refetch: refetchDD } = useQuery<{
    supplier_id: string; risk_band: string; esg_score: number;
    environmental_score: number; social_score: number; governance_score: number;
    risk_score: number; trend: string;
    critical_findings: number; high_findings: number;
    open_actions: number; overdue_actions: number;
    hr_findings: number; env_findings: number;
    unresolved_gaps: number; lksgg_coverage: string; csddd_coverage: string;
    explainability: { factor: string; value: string | number; detail: string }[];
  } | null>({
    queryKey: ["supplier-due-diligence", id],
    queryFn: async () => {
      try {
        const r = await apiClient.get(`/due-diligence/suppliers/${id}`);
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
        const r = await apiClient.get(`/suppliers/${id}/certificates`);
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
        const r = await apiClient.get(`/executive/suppliers?limit=500`);
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
      const r = await apiClient.get(`/executive/findings?supplier_id=${id}&limit=200`);
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
      const r = await apiClient.get(`/assessments/schedules?supplier_id=${id}&active_only=false`);
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
      const r = await apiClient.post("/assessments/schedules", body);
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
        <p className="text-muted-foreground">{t("error.notFound")}</p>
        <Link href="/suppliers"><Button variant="outline">{t("common.back")}</Button></Link>
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
      const r = await apiClient.post("/assessments/", {
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
      const r = await apiClient.post(`/integrations/sanctions/ofac/scan/supplier/${id}`);
      setOfacResult(r.data);
      // #151 Auto-create finding when OFAC matches found
      if (r.data?.matches_found > 0) {
        try {
          const stored = JSON.parse(localStorage.getItem("eios_automation_rules") ?? "{}");
          if (stored?.ofac_match_finding?.enabled !== false) {
            await apiClient.post("/automations/trigger", {
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
          <ArrowLeft className="h-3.5 w-3.5" /> {t("suppliers.title")}
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
              <Printer className="h-3.5 w-3.5" /> {t("common.export")} PDF
            </Button>
            <Button variant="outline" size="sm" onClick={startEdit} className="gap-1.5">
              <Edit2 className="h-3.5 w-3.5" /> {t("common.edit")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmArchive(true)}
              className="gap-1.5 text-red-600 hover:text-red-700"
            >
              <Archive className="h-3.5 w-3.5" /> {t("common.delete")}
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
            href={toAbsoluteUrl(supplier.website)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" /> {t("common.website")}
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
            <CardHeader><CardTitle className="text-base">{t("common.details")}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">{t("common.country")}</p>
                  <p className="font-medium">{supplier.country || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("common.industry")}</p>
                  <p className="font-medium">{supplier.industry || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">NACE Code</p>
                  <p className="font-mono font-medium">{supplier.nace_code || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("suppliers.tier")}</p>
                  <p className="font-medium">{supplier.supplier_tier}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("common.status")}</p>
                  <p className="font-medium">{supplier.supplier_status}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t("common.website")}</p>
                  {supplier.website ? (
                    <a href={toAbsoluteUrl(supplier.website)} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {supplier.website}
                    </a>
                  ) : (
                    <p className="font-medium">—</p>
                  )}
                </div>
              </div>
              {supplier.notes && (
                <div className="border-t border-border pt-4">
                  <p className="mb-1 text-sm text-muted-foreground">{t("common.notes")}</p>
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
                      setDdBusy(true); setDdError(null); setDdSuccess(false);
                      try {
                        for (const report_type of ["csddd", "human_rights", "environmental"]) {
                          await apiClient.post("/due-diligence/reports/generate", { report_type });
                        }
                        await refetchDD();
                        setDdSuccess(true);
                        setTimeout(() => setDdSuccess(false), 4000);
                      } catch (e: unknown) {
                        const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to run";
                        setDdError(msg);
                      } finally { setDdBusy(false); }
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
                {ddSuccess && <p className="text-xs text-emerald-600 mb-2">3 reports generated successfully.</p>}
                {dueDiligence ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Risk Band</span>
                      <span className={`font-semibold ${dueDiligence.risk_band === "Critical" || dueDiligence.risk_band === "High" ? "text-red-600" : dueDiligence.risk_band === "Moderate" ? "text-amber-600" : "text-emerald-600"}`}>
                        {dueDiligence.risk_band}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">ESG Score</span>
                      <span className="font-medium">{dueDiligence.esg_score?.toFixed(0) ?? "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">CSDDD Coverage</span>
                      <span className={`font-medium ${dueDiligence.csddd_coverage === "Compliant" ? "text-emerald-600" : dueDiligence.csddd_coverage === "Partially Compliant" ? "text-amber-600" : "text-red-600"}`}>
                        {dueDiligence.csddd_coverage}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Critical Findings</span>
                      <span className={`font-semibold ${dueDiligence.critical_findings > 0 ? "text-red-600" : "text-emerald-600"}`}>
                        {dueDiligence.critical_findings}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Open Actions</span>
                      <span className={`font-semibold ${dueDiligence.open_actions > 0 ? "text-amber-600" : "text-emerald-600"}`}>
                        {dueDiligence.open_actions}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">LkSG Coverage</span>
                      <span className={`font-medium ${dueDiligence.lksgg_coverage === "High" ? "text-emerald-600" : dueDiligence.lksgg_coverage === "Partial" ? "text-amber-600" : "text-red-600"}`}>
                        {dueDiligence.lksgg_coverage}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No due diligence data yet. Click Run to generate.</p>
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
            <h2 className="text-base font-semibold">{t("assessments.title")} ({assessments?.total ?? 0})</h2>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                onClick={() => { setShowSchedule((v) => !v); }}
              >
                <Clock className="h-3.5 w-3.5" />
                {existingSchedule ? t("common.edit") : "Schedule Reassessment"}
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                onClick={() => { setStartAssessment((v) => !v); setAssessError(null); }}
              >
                <FileText className="h-3.5 w-3.5" /> {t("assessments.newAssessment")}
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
                    {scheduleMutation.isPending ? t("common.loading") : t("common.save")}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowSchedule(false)}>{t("common.cancel")}</Button>
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
                    {assessBusy ? t("common.loading") : t("common.create")}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setStartAssessment(false)}>{t("common.cancel")}</Button>
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
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.title")}</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.type")}</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.status")}</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("assessments.quality")}</th>
                      <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("common.createdAt")}</th>
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
              {t("findings.title")} ({supplierFindings?.length ?? 0})
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
                      <th className="px-4 py-3 text-left">{t("auditor.finding")}</th>
                      <th className="px-4 py-3 text-left">{t("common.severity")}</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">{t("common.category")}</th>
                      <th className="px-4 py-3 text-left hidden md:table-cell">{t("common.date")}</th>
                      <th className="px-4 py-3 text-right">{t("findings.assessment")}</th>
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
                <CardHeader><CardTitle className="text-base">{t("dashboard.actionStatus")}</CardTitle></CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-6 text-center">
                    <div>
                      <p className="text-3xl font-bold text-foreground">{profile.open_recommendations}</p>
                      <p className="text-xs text-muted-foreground mt-1">{t("recommendations.title")}</p>
                    </div>
                    <div>
                      <p className="text-3xl font-bold text-amber-600">{profile.open_actions}</p>
                      <p className="text-xs text-muted-foreground mt-1">{t("dashboard.openActionsKpi")}</p>
                    </div>
                    <div>
                      <p className={`text-3xl font-bold ${profile.overdue_actions > 0 ? "text-red-600" : "text-emerald-600"}`}>
                        {profile.overdue_actions}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">{t("dashboard.overdue")}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ── Sector Risk Tab ───────────────────────────────────────────────── */}
      {tab === "Sector Risk" && (
        <div className="space-y-5">
          {!supplier?.nace_code ? (
            <div className="rounded-lg border border-dashed border-border p-8 text-center space-y-2">
              <Shield className="h-8 w-8 text-muted-foreground mx-auto" />
              <p className="font-medium">Kein NACE-Code hinterlegt</p>
              <p className="text-sm text-muted-foreground">
                Bitte den NACE-2-digit-Code im Lieferantenprofil (Übersicht → Bearbeiten) eintragen,
                damit das sektorspezifische Risikoregister angezeigt werden kann.
              </p>
              <button onClick={() => setTab("Overview")} className="text-sm text-blue-600 hover:underline">
                Zum Profil →
              </button>
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-lg">{supplier.nace_code}</span>
                    {sectorBaseline && (
                      <>
                        <span className="text-muted-foreground">·</span>
                        <span className="font-medium">{sectorBaseline.sector_name}</span>
                        {sectorBaseline.is_fully_calibrated ? (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">Kalibriert</span>
                        ) : (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">Fallback-Scores</span>
                        )}
                      </>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    CSDDD Sector Risk Register · 21 Schutzrechte (Annex I) · deterministisch
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <select
                      value={sectorScenario}
                      onChange={(e) => setSectorScenario(e.target.value)}
                      className="appearance-none pl-3 pr-8 py-2 text-sm rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">Kein Szenario (Baseline)</option>
                      <option value="geopolitical_conflict">Geopolitischer Konflikt</option>
                      <option value="sanctions_escalation">Sanktionsverschärfung</option>
                      <option value="natural_disaster">Naturkatastrophe</option>
                      <option value="regulatory_change">Regulierungsänderung (CSDDD)</option>
                      <option value="labour_unrest">Arbeitskampf / Streik</option>
                      <option value="supply_shortage">Versorgungsengpass</option>
                    </select>
                    <ChevronRight className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground rotate-90" />
                  </div>
                  {sectorSimLoading && <RefreshCw className="h-4 w-4 animate-spin text-muted-foreground" />}
                  <Link href={`/sector-risk/${supplier.nace_code}`} className="text-xs text-blue-600 hover:underline whitespace-nowrap">
                    Vollansicht →
                  </Link>
                </div>
              </div>

              {/* Simulation summary bar */}
              {sectorScenario && sectorSimulation && (
                <div className="flex gap-3 flex-wrap">
                  <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-md bg-amber-50 border border-amber-200 text-amber-800">
                    <GitBranch className="h-4 w-4" />
                    <span className="font-medium">{sectorSimulation.scenario_name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-md bg-orange-50 border border-orange-200 text-orange-800">
                    <TrendingUp className="h-4 w-4" />
                    <span>{sectorSimulation.summary.rights_increased} Rechte erhöht</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-md bg-red-50 border border-red-200 text-red-800">
                    <AlertTriangle className="h-4 w-4" />
                    <span>{sectorSimulation.summary.rights_above_7_scenario} Rechte ≥ 7</span>
                  </div>
                </div>
              )}

              {/* Rights table */}
              {sectorBaseline && (
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left bg-muted/30">
                          <th className="px-4 py-2.5 font-medium text-muted-foreground">CSDDD-Schutzrecht</th>
                          <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-20">Baseline</th>
                          {sectorScenario && sectorSimulation && (
                            <>
                              <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-24">Szenario</th>
                              <th className="px-4 py-2.5 font-medium text-muted-foreground text-center w-16">Delta</th>
                            </>
                          )}
                          <th className="px-4 py-2.5 font-medium text-muted-foreground w-36">Wahrscheinlichkeit</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(sectorScenario && sectorSimulation ? sectorSimulation.rights : sectorBaseline.rights).map((r) => {
                          const delta = r.scenario?.delta ?? 0;
                          const scenarioScore = r.scenario?.adjusted_probability;
                          const displayScore = sectorScenario && scenarioScore !== undefined ? scenarioScore : r.probability;
                          const pct = (displayScore / 10) * 100;
                          const barColor = displayScore >= 8 ? "bg-red-500" : displayScore >= 6 ? "bg-orange-400" : displayScore >= 4 ? "bg-amber-400" : "bg-green-500";
                          const pillColor = displayScore >= 8 ? "bg-red-100 text-red-800 border-red-200" : displayScore >= 6 ? "bg-orange-100 text-orange-800 border-orange-200" : displayScore >= 4 ? "bg-amber-100 text-amber-800 border-amber-200" : "bg-green-100 text-green-800 border-green-200";
                          return (
                            <tr key={r.right_id} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                              <td className="px-4 py-2">{r.right_name}</td>
                              <td className="px-4 py-2 text-center">
                                <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border ${displayScore >= 8 ? "bg-red-100 text-red-800 border-red-200" : displayScore >= 6 ? "bg-orange-100 text-orange-800 border-orange-200" : displayScore >= 4 ? "bg-amber-100 text-amber-800 border-amber-200" : "bg-green-100 text-green-800 border-green-200"} ${sectorScenario ? "opacity-60" : ""}`}>
                                  {r.probability}
                                </span>
                              </td>
                              {sectorScenario && sectorSimulation && (
                                <>
                                  <td className="px-4 py-2 text-center">
                                    {scenarioScore !== undefined ? (
                                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold border ${pillColor}`}>
                                        {scenarioScore}
                                      </span>
                                    ) : "—"}
                                  </td>
                                  <td className="px-4 py-2 text-center text-xs font-semibold">
                                    {delta > 0 ? <span className="text-red-600">+{delta}</span> : delta < 0 ? <span className="text-green-600">{delta}</span> : <span className="text-muted-foreground">—</span>}
                                  </td>
                                </>
                              )}
                              <td className="px-4 py-2">
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                                  </div>
                                  <span className="text-xs font-medium w-4 text-right">{displayScore}</span>
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {!sectorBaseline && (
                <div className="flex justify-center py-8"><RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" /></div>
              )}
            </>
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
              <Button
                variant="default"
                size="sm"
                className="gap-1.5"
                disabled={collecting}
                onClick={async () => {
                  setCollecting(true);
                  setCollectResult(null);
                  setCollectError(null);
                  try {
                    const r = await collectIntelligence();
                    setCollectResult(r);
                    refetchTwin?.();
                    refetchTimeline?.();
                  } catch {
                    setCollectError("Collection failed — check backend logs");
                  } finally {
                    setCollecting(false);
                  }
                }}
              >
                <Globe className={`h-3.5 w-3.5 ${collecting ? "animate-spin" : ""}`} />
                {collecting ? "Collecting…" : "Collect Intelligence"}
              </Button>
            </div>
          </div>

          {collectError && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700">{collectError}</div>
          )}
          {collectResult && (
            <Card className={collectResult.signals_created > 0 ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-slate-50"}>
              <CardContent className="pt-4 pb-3 space-y-2">
                <p className={`text-sm font-semibold flex items-center gap-2 ${collectResult.signals_created > 0 ? "text-blue-800" : "text-slate-600"}`}>
                  <Globe className="h-4 w-4" />
                  {collectResult.message}
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                  <span className="font-medium">Sources live: {collectResult.sources_ok}/{collectResult.sources_attempted}</span>
                  <span>EU Sanctions · OFAC · UN SC · World Bank · GDELT News</span>
                </div>
                <div className="flex flex-wrap gap-4 text-xs text-muted-foreground border-t pt-1.5">
                  <span>Entities screened: {collectResult.entities_checked.toLocaleString()}</span>
                  <span>New signals: <strong>{collectResult.signals_created}</strong></span>
                  <span>Twins updated: {collectResult.twins_updated}</span>
                  <span>Events: {collectResult.events_created}</span>
                  <span>{collectResult.duration_seconds.toFixed(1)}s</span>
                </div>
                {collectResult.errors.length > 0 && (
                  <p className="text-xs text-amber-700">⚠ {collectResult.errors.join(" | ")}</p>
                )}
              </CardContent>
            </Card>
          )}

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
                        <CardTitle className="text-base">{t("suppliers.esgScore")}</CardTitle>
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
                      <CardHeader><CardTitle className="text-base">{t("suppliers.riskLevel")}</CardTitle></CardHeader>
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
                      <CardTitle className="text-base">{t("suppliers.riskLevel")}</CardTitle>
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
              <CardHeader><CardTitle className="text-base">{t("common.overview")}</CardTitle></CardHeader>
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
                <CardTitle className="text-base">{t("dashboard.riskHeatmap")}</CardTitle>
                <p className="text-xs text-muted-foreground">{t("common.category")} × {t("common.severity")}</p>
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

      {/* ── Twin Tab ──────────────────────────────────────────────────────── */}
      {tab === "Twin" && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">{t("strategy.digitalTwinTitle")}</h2>
              <p className="text-xs text-muted-foreground">
                Continuously updated from external intelligence sources
              </p>
            </div>
            <button
              onClick={async () => {
                setProcessingSignals(true);
                setProcessResult(null);
                try {
                  const r = await processSupplierSignals(id);
                  setProcessResult(r.message);
                  refetchTwin();
                  refetchTimeline();
                } catch { setProcessResult("Failed to process signals"); }
                finally { setProcessingSignals(false); }
              }}
              disabled={processingSignals}
              className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${processingSignals ? "animate-spin" : ""}`} />
              {processingSignals ? "Processing…" : "Sync Intelligence"}
            </button>
          </div>
          {processResult && (
            <p className="text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
              {processResult}
            </p>
          )}

          {twinLoading ? (
            <div className="flex justify-center py-12"><Spinner size="lg" /></div>
          ) : twin ? (
            <>
              {/* Overall Health Banner */}
              <div className={`rounded-xl border p-4 flex items-center justify-between ${
                twin.overall_health < 40 ? "border-red-300 bg-red-50" :
                twin.overall_health < 60 ? "border-orange-300 bg-orange-50" :
                twin.overall_health < 75 ? "border-amber-300 bg-amber-50" :
                "border-emerald-300 bg-emerald-50"
              }`}>
                <div>
                  <p className={`text-3xl font-bold tabular-nums ${
                    twin.overall_health < 40 ? "text-red-700" :
                    twin.overall_health < 60 ? "text-orange-700" :
                    twin.overall_health < 75 ? "text-amber-700" : "text-emerald-700"
                  }`}>{twin.overall_health.toFixed(0)}</p>
                  <p className="text-xs text-muted-foreground">Overall Health Score</p>
                </div>
                <div className="text-right space-y-1">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                    twin.health_trend === "IMPROVING" ? "bg-emerald-100 text-emerald-800" :
                    twin.health_trend === "DETERIORATING" ? "bg-red-100 text-red-800" :
                    "bg-slate-100 text-slate-700"
                  }`}>
                    {twin.health_trend === "IMPROVING" ? <TrendingUp className="h-3 w-3" /> :
                     twin.health_trend === "DETERIORATING" ? <TrendingDown className="h-3 w-3" /> :
                     <Minus className="h-3 w-3" />}
                    {twin.health_trend}
                  </span>
                  <p className="text-xs text-muted-foreground">{twin.event_count} events processed</p>
                  {twin.last_event_at && (
                    <p className="text-xs text-muted-foreground">
                      Last event {new Date(twin.last_event_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
              </div>

              {/* Health Dimensions Grid */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {twin.dimensions.map((dim) => (
                  <div
                    key={dim.name}
                    className={`rounded-xl border p-4 ${
                      dim.status === "CRITICAL" ? "border-red-200 bg-red-50" :
                      dim.status === "AT_RISK" ? "border-orange-200 bg-orange-50" :
                      dim.status === "MODERATE" ? "border-amber-200 bg-amber-50" :
                      "border-emerald-200 bg-emerald-50"
                    }`}
                  >
                    <p className="text-xs font-medium text-muted-foreground mb-2">{dim.label}</p>
                    <p className={`text-2xl font-bold tabular-nums ${
                      dim.status === "CRITICAL" ? "text-red-700" :
                      dim.status === "AT_RISK" ? "text-orange-700" :
                      dim.status === "MODERATE" ? "text-amber-700" : "text-emerald-700"
                    }`}>{dim.score.toFixed(0)}</p>
                    <div className="mt-2 h-1.5 w-full rounded-full bg-white/60 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          dim.status === "CRITICAL" ? "bg-red-500" :
                          dim.status === "AT_RISK" ? "bg-orange-500" :
                          dim.status === "MODERATE" ? "bg-amber-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${dim.score}%` }}
                      />
                    </div>
                    <p className={`mt-1.5 text-[10px] font-semibold ${
                      dim.status === "CRITICAL" ? "text-red-600" :
                      dim.status === "AT_RISK" ? "text-orange-600" :
                      dim.status === "MODERATE" ? "text-amber-600" : "text-emerald-600"
                    }`}>{dim.status.replace("_", " ")}</p>
                  </div>
                ))}
              </div>

              {/* Intelligence Timeline */}
              <div>
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-500" />
                  {t("aiGov.monitoringTitle")}
                  {timelineLoading && <Spinner size="sm" />}
                </h3>
                {!twinTimeline?.events.length ? (
                  <Card>
                    <CardContent className="py-10 text-center">
                      <Target className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
                      <p className="text-sm text-muted-foreground">No intelligence events yet.</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Click "Sync Intelligence" to process external signals into the twin.
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-3">
                    {twinTimeline.events.map((event) => (
                      <TwinEventCard key={event.id} event={event} />
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <Card>
              <CardContent className="py-10 text-center">
                <Target className="mx-auto mb-3 h-10 w-10 text-muted-foreground/40" />
                <p className="text-muted-foreground">Twin not yet initialized.</p>
                <p className="mt-1 text-xs text-muted-foreground">Click "Sync Intelligence" to initialize this supplier's Digital Twin.</p>
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

      {/* ── Locations Tab (KAN-85) ────────────────────────────────────── */}
      {tab === "Locations" && (
        <LocationsTab supplierId={id} />
      )}

      {/* ── Contacts Tab (KAN-86) ─────────────────────────────────────── */}
      {tab === "Contacts" && (
        <ContactsTab supplierId={id} />
      )}

      {/* ── Certifications Tab (KAN-87) ───────────────────────────────── */}
      {tab === "Certifications" && (
        <CertificationsTab supplierId={id} />
      )}

      {/* ── Ownership Tab (KAN-88) ────────────────────────────────────── */}
      {tab === "Ownership" && (
        <OwnershipTab supplierId={id} />
      )}

      {/* ── ESG Metrics Tab (KAN-89) ──────────────────────────────────── */}
      {tab === "ESG Metrics" && (
        <ESGMetricsTab supplierId={id} />
      )}

      {/* ── ESG Ratings Tab (KAN-90) ─────────────────────────────────── */}
      {tab === "ESG Ratings" && (
        <ESGRatingsTab supplierId={id} />
      )}

      {/* Edit Modal */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background p-6 shadow-2xl">
            <h2 className="mb-4 text-lg font-semibold">{t("common.edit")} {t("nav.suppliers").slice(0, -1)}</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.name")} *</label>
                <Input value={editForm.name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("suppliers.legalName")}</label>
                <Input value={editForm.legal_name ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, legal_name: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("common.country")}</label>
                  <Input value={editForm.country ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, country: e.target.value }))} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">NACE Code</label>
                  <Input value={editForm.nace_code ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, nace_code: e.target.value }))} />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.industry")}</label>
                <Input value={editForm.industry ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, industry: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("suppliers.tier")}</label>
                  <select
                    value={editForm.supplier_tier ?? "Tier 1"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    {["Tier 1", "Tier 2", "Tier 3", "Other"].map((tier) => <option key={tier} value={tier}>{tier}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">{t("common.status")}</label>
                  <select
                    value={editForm.supplier_status ?? "Active"}
                    onChange={(e) => setEditForm((f) => ({ ...f, supplier_status: e.target.value as SupplierStatus }))}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="Active">{t("suppliers.active")}</option>
                    <option value="Inactive">{t("suppliers.inactive")}</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.website")}</label>
                <Input value={editForm.website ?? ""} onChange={(e) => setEditForm((f) => ({ ...f, website: e.target.value }))} />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">{t("common.notes")}</label>
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
              <Button variant="outline" onClick={() => { setEditing(false); setEditError(null); }}>{t("common.cancel")}</Button>
              <Button onClick={() => updateMutation.mutate(editForm)} disabled={updateMutation.isPending}>
                {updateMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                {t("common.save")}
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
              <Button variant="outline" onClick={() => setConfirmArchive(false)}>{t("common.cancel")}</Button>
              <Button variant="destructive" onClick={() => archiveMutation.mutate()} disabled={archiveMutation.isPending}>
                {archiveMutation.isPending ? <Spinner size="sm" className="mr-2" /> : null}
                {t("common.confirm")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
