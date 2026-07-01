"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2, FlaskConical, Loader2, X, AlertTriangle, ChevronDown } from "lucide-react";
import { sectorRiskApi, type CalibrationSuggestion } from "@/lib/api/sector-risk";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";

// ── Constants ─────────────────────────────────────────────────────────────────

const CSDDD_RIGHTS = [
  { value: "child_labour", label: "Child Labour (ILO C138, C182)" },
  { value: "forced_labour", label: "Forced Labour (ILO C029, C105)" },
  { value: "freedom_of_association", label: "Freedom of Association (ILO C087)" },
  { value: "collective_bargaining", label: "Collective Bargaining (ILO C098)" },
  { value: "discrimination", label: "Non-Discrimination (ILO C100, C111)" },
  { value: "minimum_wage", label: "Minimum Wage (ILO C131)" },
  { value: "working_hours", label: "Working Hours (ILO C001)" },
  { value: "occupational_safety", label: "Occupational Safety (ILO C155)" },
  { value: "land_rights", label: "Land Rights (UNDRIP, VGGT)" },
  { value: "water_rights", label: "Right to Water (UN A/RES/64/292)" },
  { value: "environmental_destruction", label: "Environmental Destruction" },
  { value: "harmful_chemicals", label: "Harmful Chemicals (Stockholm/Rotterdam)" },
  { value: "biodiversity", label: "Biodiversity (CBD)" },
  { value: "mercury", label: "Mercury (Minamata Convention)" },
  { value: "hazardous_waste", label: "Hazardous Waste (Basel Convention)" },
  { value: "privacy", label: "Right to Privacy (ICCPR Art. 17)" },
  { value: "freedom_of_expression", label: "Freedom of Expression (ICCPR Art. 19)" },
  { value: "human_dignity", label: "Human Dignity (UDHR Art. 1)" },
  { value: "modern_slavery", label: "Modern Slavery (Palermo Protocol)" },
  { value: "migrant_worker_rights", label: "Migrant Worker Rights (ICRMW)" },
  { value: "community_rights", label: "Community Rights (ILO C169, UNDRIP)" },
];

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  approved: "bg-green-50 text-green-700 border-green-200",
  rejected: "bg-red-50 text-red-700 border-red-200",
};

const CONFIDENCE_STYLES: Record<string, string> = {
  High: "text-green-600",
  Medium: "text-amber-600",
  Low: "text-red-600",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function CalibrationPage() {
  const [naceCode, setNaceCode] = useState("29");
  const [right, setRight] = useState("child_labour");
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const qc = useQueryClient();

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["calibration-suggestions", statusFilter],
    queryFn: () => sectorRiskApi.listCalibrationSuggestions(statusFilter || undefined),
  });

  const calibrateMutation = useMutation({
    mutationFn: () => sectorRiskApi.startCalibration(naceCode, right),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calibration-suggestions"] }),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => sectorRiskApi.approveCalibration(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calibration-suggestions"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      sectorRiskApi.rejectCalibration(id, reason),
    onSuccess: () => {
      setRejectId(null);
      setRejectReason("");
      qc.invalidateQueries({ queryKey: ["calibration-suggestions"] });
    },
  });

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <Link href="/sector-risk" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Sector Risk Register
      </Link>

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-blue-500" />
          RAG Kalibrierung
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Groq LLM + pgvector generiert Wahrscheinlichkeitsvorschläge aus ILO/OECD-Dokumenten. Jeder Vorschlag erfordert Founder-Genehmigung (M43).
        </p>
      </div>

      {/* Start calibration form */}
      <Card>
        <CardContent className="pt-5 pb-5 space-y-4">
          <p className="text-sm font-semibold">Neuen Kalibrierungsvorschlag erstellen</p>
          <div className="flex gap-3 flex-wrap items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">NACE-Code</label>
              <input
                type="text"
                value={naceCode}
                onChange={(e) => setNaceCode(e.target.value)}
                placeholder="z.B. 29, 13, 01"
                className="w-28 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">CSDDD-Recht</label>
              <div className="relative">
                <select
                  value={right}
                  onChange={(e) => setRight(e.target.value)}
                  className="appearance-none pl-3 pr-8 py-2 text-sm rounded-md border border-border bg-background focus:outline-none focus:ring-2 focus:ring-ring max-w-xs"
                >
                  {CSDDD_RIGHTS.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            <Button
              onClick={() => calibrateMutation.mutate()}
              disabled={calibrateMutation.isPending || !naceCode || !right}
              size="sm"
            >
              {calibrateMutation.isPending ? (
                <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" />Kalibriert…</>
              ) : (
                <><FlaskConical className="h-4 w-4 mr-1.5" />RAG starten</>
              )}
            </Button>
          </div>
          {calibrateMutation.isSuccess && (
            <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2">
              Vorschlag erstellt — jetzt unter &quot;Ausstehend&quot; sichtbar.
            </div>
          )}
          {calibrateMutation.isError && (
            <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2">
              Fehler beim Starten der Kalibrierung. Bitte NACE-Code prüfen.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Suggestion list */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-sm">Kalibrierungsvorschläge</p>
          <div className="flex gap-1">
            {["pending", "approved", "rejected"].map((s) => (
              <Button
                key={s}
                variant={statusFilter === s ? "default" : "outline"}
                size="sm"
                onClick={() => setStatusFilter(s)}
                className="text-xs capitalize"
              >
                {s === "pending" ? "Ausstehend" : s === "approved" ? "Genehmigt" : "Abgelehnt"}
              </Button>
            ))}
          </div>
        </div>

        {isLoading && <div className="flex justify-center py-8"><Spinner /></div>}

        {!isLoading && (!suggestions || suggestions.length === 0) && (
          <EmptyState icon={FlaskConical} title="Keine Vorschläge" description={`Keine ${statusFilter === "pending" ? "ausstehenden" : statusFilter === "approved" ? "genehmigten" : "abgelehnten"} Vorschläge.`} />
        )}

        {suggestions?.map((s) => (
          <CalibrationCard
            key={s.id}
            suggestion={s}
            onApprove={() => approveMutation.mutate(s.id)}
            onReject={() => setRejectId(s.id)}
            approvePending={approveMutation.isPending}
          />
        ))}
      </div>

      {/* Reject modal */}
      {rejectId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <CardContent className="pt-5 pb-5 space-y-4">
              <div className="flex items-center justify-between">
                <p className="font-semibold">Vorschlag ablehnen</p>
                <button onClick={() => setRejectId(null)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Begründung für die Ablehnung (min. 5 Zeichen)…"
                rows={3}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
              <div className="flex gap-2 justify-end">
                <Button variant="outline" size="sm" onClick={() => setRejectId(null)}>Abbrechen</Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={rejectReason.length < 5 || rejectMutation.isPending}
                  onClick={() => rejectMutation.mutate({ id: rejectId, reason: rejectReason })}
                >
                  {rejectMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Ablehnen"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function CalibrationCard({
  suggestion,
  onApprove,
  onReject,
  approvePending,
}: {
  suggestion: CalibrationSuggestion;
  onApprove: () => void;
  onReject: () => void;
  approvePending: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-bold text-sm">{suggestion.nace_code}</span>
              <span className="text-muted-foreground text-sm">·</span>
              <span className="text-sm font-medium">{suggestion.csddd_right.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[suggestion.status] ?? ""}`}>
                {suggestion.status}
              </span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span>
                Wahrscheinlichkeit:{" "}
                <span className="font-bold text-foreground">{suggestion.suggested_probability}/10</span>
              </span>
              <span>
                Konfidenz:{" "}
                <span className={`font-medium ${CONFIDENCE_STYLES[suggestion.confidence] ?? ""}`}>{suggestion.confidence}</span>
              </span>
            </div>
            {suggestion.reasoning && (
              <p className="text-xs text-muted-foreground max-w-xl">{suggestion.reasoning}</p>
            )}
            {suggestion.sources.length > 0 && (
              <p className="text-xs text-muted-foreground">Quellen: {suggestion.sources.join(" · ")}</p>
            )}
          </div>

          {suggestion.status === "pending" && (
            <div className="flex gap-2 shrink-0">
              <Button size="sm" onClick={onApprove} disabled={approvePending}>
                <CheckCircle2 className="h-4 w-4 mr-1.5" />
                Genehmigen
              </Button>
              <Button size="sm" variant="outline" onClick={onReject}>
                <X className="h-4 w-4 mr-1.5" />
                Ablehnen
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
