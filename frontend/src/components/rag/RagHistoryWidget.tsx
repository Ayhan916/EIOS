"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen, TrendingDown, TrendingUp, Minus,
  ChevronDown, ChevronUp, Search, Loader2,
} from "lucide-react";
import { ragHistory, type HistoricalEntry } from "@/lib/api/rag";
import { Input } from "@/components/ui/input";

const OUTCOME_CONFIG = {
  effective:   { label: "Wirksam",        color: "bg-emerald-100 text-emerald-800", icon: TrendingUp },
  partial:     { label: "Teilw. wirksam", color: "bg-amber-100 text-amber-800",    icon: TrendingUp },
  ineffective: { label: "Nicht wirksam",  color: "bg-red-100 text-red-800",        icon: TrendingDown },
  unknown:     { label: "Unbekannt",      color: "bg-slate-100 text-slate-600",    icon: Minus },
};

const EVENT_TYPE_LABEL: Record<string, string> = {
  finding:                  "Befund",
  intelligence_event:       "Intelligence",
  intelligence_recommendation: "Intelligence",
  corrective_action_plan:   "CAP",
};

const SEVERITY_COLOR: Record<string, string> = {
  Critical: "bg-red-100 text-red-800",
  High:     "bg-orange-100 text-orange-800",
  Medium:   "bg-amber-100 text-amber-800",
  Low:      "bg-emerald-100 text-emerald-800",
};

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-xs text-muted-foreground">—</span>;
  const color = delta > 0 ? "text-emerald-700" : delta < 0 ? "text-red-700" : "text-slate-500";
  const sign = delta > 0 ? "+" : "";
  return (
    <span className={`text-xs font-semibold tabular-nums ${color}`}>
      {sign}{delta.toFixed(1)} ESG
    </span>
  );
}

function HistoryCard({ entry, expanded, onToggle }: {
  entry: HistoricalEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const outcome = OUTCOME_CONFIG[entry.outcome_category as keyof typeof OUTCOME_CONFIG]
    ?? OUTCOME_CONFIG.unknown;
  const OutcomeIcon = outcome.icon;

  return (
    <div className="rounded-lg border border-border bg-background overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 text-left hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {entry.event_severity && (
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${SEVERITY_COLOR[entry.event_severity] ?? "bg-slate-100 text-slate-600"}`}>
                  {entry.event_severity}
                </span>
              )}
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
                {EVENT_TYPE_LABEL[entry.event_type] ?? entry.event_type}
              </span>
              {entry.csddd_right && (
                <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] text-blue-700 font-medium">
                  {entry.csddd_right.replace(/_/g, " ")}
                </span>
              )}
              {entry.reference_date && (
                <span className="text-[10px] text-muted-foreground">
                  {entry.reference_date.slice(0, 10)}
                </span>
              )}
            </div>
            <p className="text-xs font-medium line-clamp-2 text-foreground">
              {entry.event_description.slice(0, 180)}
              {entry.event_description.length > 180 ? "…" : ""}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${outcome.color}`}>
              <OutcomeIcon className="h-3 w-3" />
              {outcome.label}
            </span>
            <DeltaBadge delta={entry.health_delta} />
            {expanded ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-border/50 pt-3">
          {/* Ereignis */}
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1">
              Was ist passiert?
            </p>
            <p className="text-xs text-foreground leading-relaxed">{entry.event_description}</p>
          </div>

          {/* Gegenmassnahme */}
          {entry.countermeasure_description && (
            <div>
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1">
                Gegenmassnahme
              </p>
              <p className="text-xs text-foreground leading-relaxed">{entry.countermeasure_description}</p>
            </div>
          )}

          {/* Ergebnis */}
          <div className={`rounded-md px-3 py-2 text-xs ${outcome.color}`}>
            <span className="font-semibold">{outcome.label}: </span>
            {entry.outcome_description}
          </div>

          {entry.similarity !== undefined && (
            <p className="text-[10px] text-muted-foreground">
              Semantische Relevanz: {(entry.similarity * 100).toFixed(0)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  supplierId: string;
  supplierName: string;
}

export function RagHistoryWidget({ supplierId, supplierName }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [searchInput, setSearchInput] = useState("");
  const [activeQuery, setActiveQuery] = useState<string | undefined>(undefined);
  const [rightFilter, setRightFilter] = useState<string | undefined>(undefined);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["rag-history", supplierId, activeQuery, rightFilter],
    queryFn: () => ragHistory({
      supplier_id: supplierId,
      query: activeQuery,
      csddd_right: rightFilter,
      limit: 20,
    }),
    staleTime: 60_000,
  });

  function toggleCard(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setActiveQuery(searchInput.trim() || undefined);
  }

  const entries = data?.entries ?? [];
  const total = data?.total ?? 0;

  const effectiveCount = entries.filter((e) => e.outcome_category === "effective").length;
  const partialCount   = entries.filter((e) => e.outcome_category === "partial").length;
  const ineffCount     = entries.filter((e) => e.outcome_category === "ineffective").length;

  return (
    <div className="rounded-xl border border-border bg-background p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100">
          <BookOpen className="h-4 w-4 text-indigo-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">Lernhistorie</h3>
          <p className="text-xs text-muted-foreground">
            Was wurde in der Vergangenheit unternommen? Hat es gewirkt?
          </p>
        </div>
        {total > 0 && (
          <span className="ml-auto rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
            {total} Einträge
          </span>
        )}
      </div>

      {/* Outcome-Zusammenfassung */}
      {entries.length > 0 && (
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-lg bg-emerald-50 border border-emerald-200 py-2">
            <p className="text-lg font-bold text-emerald-700">{effectiveCount}</p>
            <p className="text-[10px] text-emerald-600">Wirksam</p>
          </div>
          <div className="rounded-lg bg-amber-50 border border-amber-200 py-2">
            <p className="text-lg font-bold text-amber-700">{partialCount}</p>
            <p className="text-[10px] text-amber-600">Teilw. wirksam</p>
          </div>
          <div className="rounded-lg bg-red-50 border border-red-200 py-2">
            <p className="text-lg font-bold text-red-700">{ineffCount}</p>
            <p className="text-[10px] text-red-600">Nicht wirksam</p>
          </div>
        </div>
      )}

      {/* Suche + Filter */}
      <div className="space-y-2">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Semantische Suche in der Lernhistorie…"
              className="pl-8 text-xs h-8"
            />
          </div>
          <button
            type="submit"
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700"
          >
            {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Suchen"}
          </button>
          {activeQuery && (
            <button
              type="button"
              onClick={() => { setActiveQuery(undefined); setSearchInput(""); }}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          )}
        </form>

        {/* CSDDD Right Filter */}
        <select
          value={rightFilter ?? ""}
          onChange={(e) => setRightFilter(e.target.value || undefined)}
          className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs"
        >
          <option value="">Alle CSDDD-Rechte</option>
          {["child_labour","forced_labour","freedom_of_association","collective_bargaining",
            "discrimination","minimum_wage","working_hours","occupational_safety",
            "land_rights","water_rights","environmental_destruction","harmful_chemicals",
            "biodiversity","mercury","hazardous_waste","modern_slavery",
            "migrant_worker_rights","community_rights","human_dignity",
            "privacy","freedom_of_expression"].map((r) => (
            <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {/* Entries */}
      {isLoading ? (
        <div className="flex justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : entries.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-6 text-center">
          <BookOpen className="mx-auto h-8 w-8 text-muted-foreground/30 mb-2" />
          <p className="text-sm font-medium text-muted-foreground">Keine Lernhistorie vorhanden</p>
          <p className="text-xs text-muted-foreground mt-1">
            Führe zuerst den historischen Ingestion-Lauf durch (⬇ Ingest History).
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => (
            <HistoryCard
              key={entry.id}
              entry={entry}
              expanded={expanded.has(entry.id)}
              onToggle={() => toggleCard(entry.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
