"use client";

import { useState } from "react";
import {
  AlertTriangle, Bot, ChevronDown, ChevronUp,
  FlaskConical, Loader2, TrendingUp,
} from "lucide-react";
import { ragSimulate, type RagSimulateResponse } from "@/lib/api/rag";
import { Button } from "@/components/ui/button";

const SCENARIOS = [
  {
    type: "geopolitical_conflict",
    label: "Geopolitischer Konflikt",
    description: "Krieg, Konflikte oder Instabilität im Lieferland",
    icon: "🌍",
    color: "border-red-200 bg-red-50 hover:border-red-400",
    activeColor: "border-red-400 bg-red-100 ring-2 ring-red-300",
  },
  {
    type: "sanctions_escalation",
    label: "Sanktionsverschärfung",
    description: "Neue oder erweiterte Wirtschaftssanktionen",
    icon: "🚫",
    color: "border-orange-200 bg-orange-50 hover:border-orange-400",
    activeColor: "border-orange-400 bg-orange-100 ring-2 ring-orange-300",
  },
  {
    type: "natural_disaster",
    label: "Naturkatastrophe",
    description: "Überschwemmung, Erdbeben, Hurrikan in Produktionsregion",
    icon: "🌊",
    color: "border-blue-200 bg-blue-50 hover:border-blue-400",
    activeColor: "border-blue-400 bg-blue-100 ring-2 ring-blue-300",
  },
  {
    type: "regulatory_change",
    label: "Regulatorische Verschärfung",
    description: "CSDDD / LkSG Verschärfung, neue Sorgfaltspflichten",
    icon: "📋",
    color: "border-purple-200 bg-purple-50 hover:border-purple-400",
    activeColor: "border-purple-400 bg-purple-100 ring-2 ring-purple-300",
  },
  {
    type: "labour_unrest",
    label: "Arbeitskampf / Streik",
    description: "Streiks, Gewerkschaftskonflikte in der Lieferkette",
    icon: "✊",
    color: "border-yellow-200 bg-yellow-50 hover:border-yellow-400",
    activeColor: "border-yellow-400 bg-yellow-100 ring-2 ring-yellow-300",
  },
  {
    type: "supply_shortage",
    label: "Rohstoff- / Lieferengpass",
    description: "Halbleiter-, Rohstoff- oder Energieknappheit",
    icon: "⚡",
    color: "border-slate-200 bg-slate-50 hover:border-slate-400",
    activeColor: "border-slate-400 bg-slate-100 ring-2 ring-slate-300",
  },
];

const DELTA_COLOR = (delta: number) =>
  delta >= 3 ? "text-red-700 bg-red-100" :
  delta >= 1 ? "text-orange-700 bg-orange-100" :
               "text-slate-600 bg-slate-100";

interface Props {
  supplierId: string;
  supplierName: string;
}

export function RagSimulateWidget({ supplierId, supplierName }: Props) {
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState<RagSimulateResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [showSources, setShowSources] = useState(false);

  async function handleSimulate() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setShowSources(false);
    try {
      const res = await ragSimulate({
        scenario_type: selected,
        supplier_id: supplierId,
        supplier_name: supplierName,
      });
      setResult(res);
    } catch {
      setError("Simulation fehlgeschlagen. Bitte erneut versuchen.");
    } finally {
      setLoading(false);
    }
  }

  const scenarioMeta = SCENARIOS.find((s) => s.type === selected);

  return (
    <div className="rounded-xl border border-border bg-background p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100">
          <FlaskConical className="h-4 w-4 text-emerald-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">Szenario-Simulation</h3>
          <p className="text-xs text-muted-foreground">
            Simuliere Auswirkungen auf {supplierName} — deterministisch + KI-Narrativ
          </p>
        </div>
      </div>

      {/* Scenario selector */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {SCENARIOS.map((s) => (
          <button
            key={s.type}
            onClick={() => { setSelected(s.type); setResult(null); }}
            className={`rounded-lg border p-3 text-left transition-all ${
              selected === s.type ? s.activeColor : s.color
            }`}
          >
            <div className="text-lg mb-1">{s.icon}</div>
            <div className="text-xs font-semibold leading-tight">{s.label}</div>
            <div className="mt-0.5 text-[10px] text-muted-foreground leading-tight">
              {s.description}
            </div>
          </button>
        ))}
      </div>

      {/* Simulate button */}
      <Button
        onClick={handleSimulate}
        disabled={!selected || loading}
        className="w-full bg-emerald-600 hover:bg-emerald-700 text-white gap-2"
      >
        {loading
          ? <><Loader2 className="h-4 w-4 animate-spin" /> Simuliere…</>
          : <><FlaskConical className="h-4 w-4" /> Simulation starten</>
        }
      </Button>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Scenario badge */}
          <div className="flex items-center gap-2">
            <span className="text-lg">{scenarioMeta?.icon}</span>
            <span className="text-sm font-semibold">{result.scenario_name}</span>
            {result.deterministic_ok && (
              <span className="ml-auto rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                CSDDD-Scores verfügbar
              </span>
            )}
          </div>

          {/* Affected CSDDD rights */}
          {result.top_affected_rights.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                Betroffene CSDDD-Rechte
              </p>
              {result.top_affected_rights.map((r) => (
                <div
                  key={r.right_id}
                  className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-3.5 w-3.5 text-orange-500" />
                    <span className="text-xs font-medium">{r.right_name}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-muted-foreground">{r.baseline} → {r.adjusted}</span>
                    <span className={`rounded-full px-2 py-0.5 font-semibold ${DELTA_COLOR(r.delta)}`}>
                      +{r.delta}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Narrative */}
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Bot className="h-4 w-4 text-emerald-600" />
              <span className="text-xs font-semibold text-emerald-700">
                KI-Risikoanalyse · {result.model}
              </span>
            </div>
            <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
              {result.narrative}
            </div>
          </div>

          {/* Sources */}
          {result.sources.length > 0 && (
            <div>
              <button
                onClick={() => setShowSources((v) => !v)}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {showSources ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                {result.chunks_found} Quellen verwendet
              </button>
              {showSources && (
                <div className="mt-2 space-y-2">
                  {result.sources.map((s) => (
                    <div key={s.rank} className="rounded-lg border border-border bg-muted/30 p-3 text-xs space-y-1">
                      <div className="flex gap-2 text-muted-foreground flex-wrap">
                        <span className="font-medium">
                          {s.doc_type === "news_article" ? "Nachricht" : "Intelligence-Event"}
                        </span>
                        {s.published_at && <span>{s.published_at}</span>}
                        {s.source_name && <span>· {s.source_name}</span>}
                        <span className="ml-auto">{(s.similarity * 100).toFixed(0)}% Relevanz</span>
                      </div>
                      <p className="text-muted-foreground">{s.content_preview}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
