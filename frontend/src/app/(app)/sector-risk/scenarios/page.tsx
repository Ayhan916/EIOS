"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, CheckCircle2, Loader2, Newspaper, Radio, X, Zap } from "lucide-react";
import { sectorRiskApi, type ScenarioSuggestion } from "@/lib/api/sector-risk";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { useAuth } from "@/lib/auth/context";

// ── Constants ─────────────────────────────────────────────────────────────────

const SCENARIO_LABELS: Record<string, string> = {
  geopolitical_conflict: "Geopolitischer Konflikt",
  sanctions_escalation: "Sanktionsverschärfung",
  natural_disaster: "Naturkatastrophe",
  regulatory_change: "Regulierungsänderung",
  labour_unrest: "Arbeitskampf / Streik",
  supply_shortage: "Versorgungsengpass",
};

const SCENARIO_ICONS: Record<string, string> = {
  geopolitical_conflict: "⚔️",
  sanctions_escalation: "🚫",
  natural_disaster: "🌊",
  regulatory_change: "📋",
  labour_unrest: "✊",
  supply_shortage: "📦",
};

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  active: "bg-green-50 text-green-700 border-green-200",
  dismissed: "bg-muted text-muted-foreground border-border",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function ScenarioSuggestionsPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const [statusFilter, setStatusFilter] = useState<string>("pending");
  const qc = useQueryClient();

  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["scenario-suggestions", statusFilter],
    queryFn: () => sectorRiskApi.listScenarioSuggestions(statusFilter || undefined),
  });

  const detectMutation = useMutation({
    mutationFn: () =>
      sectorRiskApi.detectScenarios((user as any)?.organization_id ?? ""),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenario-suggestions"] }),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => sectorRiskApi.activateScenario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenario-suggestions"] }),
  });

  const dismissMutation = useMutation({
    mutationFn: (id: string) => sectorRiskApi.dismissScenario(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenario-suggestions"] }),
  });

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <Link href="/sector-risk" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" />
        Sector Risk Register
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Radio className="h-5 w-5 text-orange-500" />
            {t("sectorRisk.suggestionsTitle")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{t("sectorRisk.suggestionsSubtitle")}</p>
        </div>
        <Button
          onClick={() => detectMutation.mutate()}
          disabled={detectMutation.isPending}
          size="sm"
        >
          {detectMutation.isPending ? (
            <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" />Scannt News…</>
          ) : (
            <><Newspaper className="h-4 w-4 mr-1.5" />{t("sectorRisk.scanNews")}</>
          )}
        </Button>
      </div>

      {detectMutation.isSuccess && detectMutation.data && (
        <div className="text-sm bg-blue-50 border border-blue-200 text-blue-700 rounded-md px-3 py-2">
          {detectMutation.data.length > 0
            ? `${detectMutation.data.length} neue Szenario-Vorschläge erstellt.`
            : "Keine neuen Szenarien erkannt (unter Schwellenwert oder bereits aktiv)."}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center justify-between">
        <p className="font-semibold text-sm">Vorschläge</p>
        <div className="flex gap-1">
          {["pending", "active", "dismissed"].map((s) => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(s)}
              className="text-xs"
            >
              {s === "pending" ? t("sectorRisk.pending") : s === "active" ? t("sectorRisk.active") : t("sectorRisk.dismissed")}
            </Button>
          ))}
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-8"><Spinner /></div>}

      {!isLoading && (!suggestions || suggestions.length === 0) && (
        <EmptyState
          icon={Radio}
          title="Keine Vorschläge"
          description={
            statusFilter === "pending"
              ? t("sectorRisk.noSuggestions")
              : `Keine ${statusFilter === "active" ? "aktiven" : "verworfenen"} Vorschläge.`
          }
        />
      )}

      <div className="space-y-3">
        {suggestions?.map((s) => (
          <ScenarioCard
            key={s.id}
            suggestion={s}
            onActivate={() => activateMutation.mutate(s.id)}
            onDismiss={() => dismissMutation.mutate(s.id)}
            actionPending={activateMutation.isPending || dismissMutation.isPending}
          />
        ))}
      </div>
    </div>
  );
}

function ScenarioCard({
  suggestion,
  onActivate,
  onDismiss,
  actionPending,
}: {
  suggestion: ScenarioSuggestion;
  onActivate: () => void;
  onDismiss: () => void;
  actionPending: boolean;
}) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);
  const label = SCENARIO_LABELS[suggestion.scenario_type] ?? suggestion.scenario_type;
  const icon = SCENARIO_ICONS[suggestion.scenario_type] ?? "⚠️";

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="space-y-2 min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xl">{icon}</span>
              <span className="font-semibold text-foreground">{label}</span>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_STYLES[suggestion.status] ?? ""}`}>
                {suggestion.status === "pending" ? t("sectorRisk.pending") : suggestion.status === "active" ? t("sectorRisk.active") : t("sectorRisk.dismissed")}
              </span>
            </div>

            <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              <span>
                <span className="font-medium text-foreground">{suggestion.trigger_article_count}</span> Artikel in 7 Tagen
              </span>
              {suggestion.affected_nace_codes.length > 0 && (
                <span>
                  {t("sectorRisk.affectedSectors")}{" "}
                  {suggestion.affected_nace_codes.map((c) => (
                    <Link key={c} href={`/sector-risk/${c}`} className="font-mono text-blue-600 hover:underline mr-1">{c}</Link>
                  ))}
                </span>
              )}
              {suggestion.expires_at && (
                <span>Läuft ab: {new Date(suggestion.expires_at).toLocaleDateString("de-DE")}</span>
              )}
            </div>

            {/* Keywords */}
            {suggestion.trigger_keywords_matched.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {suggestion.trigger_keywords_matched.slice(0, 6).map((kw) => (
                  <span key={kw} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                    {kw}
                  </span>
                ))}
              </div>
            )}

            {/* Sample headlines toggle */}
            {suggestion.sample_headlines.length > 0 && (
              <div>
                <button
                  onClick={() => setExpanded((v) => !v)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  {expanded ? "Headlines ausblenden" : `${suggestion.sample_headlines.length} Beispiel-Schlagzeilen anzeigen`}
                </button>
                {expanded && (
                  <ul className="mt-1.5 space-y-1">
                    {suggestion.sample_headlines.map((h, i) => (
                      <li key={i} className="text-xs text-muted-foreground pl-3 border-l-2 border-border">
                        {h}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {suggestion.status === "pending" && (
            <div className="flex gap-2 shrink-0">
              <Button size="sm" onClick={onActivate} disabled={actionPending}>
                <Zap className="h-4 w-4 mr-1.5" />
                {t("sectorRisk.activate")}
              </Button>
              <Button size="sm" variant="outline" onClick={onDismiss} disabled={actionPending}>
                <X className="h-4 w-4 mr-1.5" />
                {t("sectorRisk.dismiss")}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
