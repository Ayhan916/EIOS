"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Search, BookOpen, CheckCircle, AlertTriangle, RefreshCw, GitBranch, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { FEATURES, WORKFLOWS, type FeatureEntry, type WorkflowId } from "@/lib/data/feature-knowledge-graph";

// ── Types ─────────────────────────────────────────────────────────────────────

interface SearchResultItem {
  chunk_id: string;
  evidence_id: string;
  evidence_title: string;
  evidence_source: string;
  text: string;
  similarity: number;
  chunk_index: number;
}

interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  model: string;
}

interface IngestResponse {
  evidence_id: string;
  chunks_created: number;
  model: string;
}

interface EvidenceItem {
  id: string;
  title: string;
  source: string;
  evidence_type: string;
  confidence: string;
  description: string;
}

// ── Similarity badge ──────────────────────────────────────────────────────────

function SimBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "bg-green-100 text-green-700"
    : pct >= 60 ? "bg-blue-100 text-blue-700"
    : pct >= 40 ? "bg-amber-100 text-amber-700"
    : "bg-slate-100 text-slate-500";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium tabular-nums ${color}`}>
      {pct}%
    </span>
  );
}

// ── Search Tab ─────────────────────────────────────────────────────────────────

function SearchTab() {
  const { t } = useLanguage();
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(10);
  const [minSim, setMinSim] = useState(0.0);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const search = useMutation({
    mutationFn: async (): Promise<SearchResponse> => {
      const res = await apiClient.post("/knowledge/search", {
        query: query.trim(),
        limit,
        min_similarity: minSim,
      });
      return res.data;
    },
    onSuccess: (data) => {
      setResults(data);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    search.mutate();
  }

  return (
    <div className="space-y-6">
      {/* Search form */}
      <Card>
        <CardContent className="pt-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label className="text-sm">{t("kb.query")}</Label>
              <div className="mt-1.5 flex gap-2">
                <Input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("kb.queryPlaceholder")}
                  className="flex-1"
                />
                <Button type="submit" disabled={search.isPending || !query.trim()} className="gap-1.5 shrink-0">
                  {search.isPending ? <Spinner className="h-4 w-4" /> : <Search className="h-4 w-4" />}
                  {t("kb.search")}
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap gap-6">
              <div className="flex items-center gap-2">
                <Label className="text-xs text-slate-500 whitespace-nowrap">{t("kb.maxResults")}</Label>
                <select
                  className="h-8 rounded-md border border-slate-200 bg-white px-2 text-sm"
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                >
                  {[5, 10, 20, 50].map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <Label className="text-xs text-slate-500 whitespace-nowrap">{t("kb.minSimilarity")}</Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={minSim}
                  onChange={(e) => setMinSim(parseFloat(e.target.value))}
                  className="w-28 accent-blue-600"
                />
                <span className="text-xs font-medium text-slate-600 w-8">{(minSim * 100).toFixed(0)}%</span>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="py-3 text-sm text-red-700">{error}</CardContent>
        </Card>
      )}

      {/* Results */}
      {results && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">
              <strong className="text-slate-800">{results.results.length}</strong> {t("kb.resultsFor")} &ldquo;{results.query}&rdquo;
            </p>
            <span className="text-xs text-slate-400 font-mono">{t("kb.model")}: {results.model}</span>
          </div>

          {results.results.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Search className="mx-auto mb-3 h-10 w-10 text-slate-300" />
                <p className="font-medium text-slate-600">{t("kb.noResults")}</p>
                <p className="mt-1 text-sm text-slate-400">{t("kb.noResultsDesc")}</p>
              </CardContent>
            </Card>
          ) : (
            results.results.map((r) => (
              <Card key={r.chunk_id}>
                <CardContent className="pt-4">
                  <div className="flex items-start gap-3">
                    {/* Similarity ring */}
                    <div className="shrink-0 mt-0.5">
                      <SimBadge score={r.similarity} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <p className="font-semibold text-slate-800 text-sm">{r.evidence_title}</p>
                        {r.evidence_source && (
                          <span className="text-xs text-slate-400 truncate max-w-[200px]">{r.evidence_source}</span>
                        )}
                        <span className="ml-auto text-xs text-slate-400">{t("kb.chunk")} #{r.chunk_index}</span>
                      </div>
                      <p className="text-sm text-slate-700 leading-relaxed">{r.text}</p>
                      <div className="mt-2 flex gap-3 text-xs text-slate-400">
                        <span>{t("kb.evidenceId")}: <span className="font-mono">{r.evidence_id.slice(0, 12)}…</span></span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      {!results && !search.isPending && (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center">
            <BookOpen className="mx-auto mb-3 h-10 w-10 text-slate-300" />
            <p className="font-medium text-slate-600">{t("kb.searchPrompt")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("kb.searchPromptDesc")}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Ingest Tab ────────────────────────────────────────────────────────────────

function IngestTab() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const orgId = user?.organization_id ?? "";
  const [manualId, setManualId] = useState("");
  const [force, setForce] = useState(false);
  const [results, setResults] = useState<Record<string, { ok: boolean; chunks?: number; model?: string; error?: string }>>({});

  // List evidence items to pick from
  const { data: evidencePage, isLoading: evidenceLoading } = useQuery<{ items: EvidenceItem[]; total: number }>({
    queryKey: ["evidence-list", orgId],
    queryFn: async () => (await apiClient.get("/evidences/?size=50&page=1")).data,
    staleTime: 60_000,
    enabled: !!orgId,
  });

  const evidence = evidencePage?.items ?? [];

  const ingest = useMutation({
    mutationFn: async (evidenceId: string): Promise<IngestResponse> => {
      const res = await apiClient.post("/knowledge/ingest", { evidence_id: evidenceId, force });
      return res.data;
    },
    onSuccess: (data) => {
      setResults((prev) => ({
        ...prev,
        [data.evidence_id]: { ok: true, chunks: data.chunks_created, model: data.model },
      }));
    },
    onError: (e: Error, evidenceId) => {
      setResults((prev) => ({
        ...prev,
        [evidenceId]: { ok: false, error: e.message },
      }));
    },
  });

  function handleManualIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!manualId.trim()) return;
    ingest.mutate(manualId.trim());
  }

  return (
    <div className="space-y-6">
      {/* Manual ingest by ID */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold">{t("kb.manualIngest")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleManualIngest} className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs">{t("kb.evidenceId")}</Label>
              <Input
                className="mt-1 font-mono text-sm"
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                placeholder="uuid…"
              />
            </div>
            <div className="flex items-center gap-2 pb-1">
              <input
                type="checkbox"
                id="force"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 accent-blue-600"
              />
              <label htmlFor="force" className="text-sm text-slate-600">{t("kb.forceReingest")}</label>
            </div>
            <Button type="submit" disabled={!manualId.trim() || ingest.isPending} className="gap-1.5">
              {ingest.isPending ? <Spinner className="h-4 w-4" /> : <RefreshCw className="h-4 w-4" />}
              {t("kb.ingest")}
            </Button>
          </form>
          {results[manualId] && (
            <div className={`mt-3 rounded-md px-3 py-2 text-sm ${results[manualId].ok ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
              {results[manualId].ok
                ? `✓ ${results[manualId].chunks} ${t("kb.chunksCreated")} · ${results[manualId].model}`
                : results[manualId].error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Evidence list */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 mb-3">
          {t("kb.availableEvidence")}
          <span className="ml-2 text-xs font-normal text-slate-400">({evidencePage?.total ?? 0})</span>
        </h3>

        {evidenceLoading ? (
          <div className="flex h-32 items-center justify-center"><Spinner /></div>
        ) : evidence.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="py-12 text-center">
              <BookOpen className="mx-auto mb-3 h-10 w-10 text-slate-300" />
              <p className="text-slate-500">{t("kb.noEvidence")}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {evidence.map((ev) => {
              const res = results[ev.id];
              const isPending = ingest.isPending && ingest.variables === ev.id;
              return (
                <Card key={ev.id}>
                  <CardContent className="pt-3 pb-3">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-slate-800 text-sm">{ev.title}</p>
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500 capitalize">
                            {ev.evidence_type?.replace(/_/g, " ")}
                          </span>
                          <span className={`rounded-full px-1.5 py-0.5 text-xs font-medium capitalize ${
                            ev.confidence === "HIGH" ? "bg-green-100 text-green-700"
                            : ev.confidence === "MEDIUM" ? "bg-amber-100 text-amber-700"
                            : "bg-slate-100 text-slate-500"
                          }`}>
                            {ev.confidence}
                          </span>
                        </div>
                        {ev.source && (
                          <p className="text-xs text-slate-400 mt-0.5 truncate">{ev.source}</p>
                        )}
                        {ev.description && (
                          <p className="text-xs text-slate-500 mt-1 line-clamp-1">{ev.description}</p>
                        )}
                      </div>

                      <div className="shrink-0 flex items-center gap-2">
                        {res?.ok && (
                          <span className="flex items-center gap-1 text-xs text-green-600">
                            <CheckCircle className="h-3.5 w-3.5" />
                            {res.chunks} {t("kb.chunks")}
                          </span>
                        )}
                        {res?.error && (
                          <span className="flex items-center gap-1 text-xs text-red-600">
                            <AlertTriangle className="h-3.5 w-3.5" />
                            {t("kb.failed")}
                          </span>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 text-xs gap-1"
                          disabled={isPending}
                          onClick={() => ingest.mutate(ev.id)}
                        >
                          {isPending ? <Spinner className="h-3 w-3" /> : <RefreshCw className="h-3 w-3" />}
                          {res?.ok ? t("kb.reingest") : t("kb.ingest")}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Feature Graph Tab ─────────────────────────────────────────────────────────

const GAP_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border border-red-200",
  high:     "bg-orange-100 text-orange-700 border border-orange-200",
  medium:   "bg-amber-100 text-amber-800 border border-amber-200",
};

function FeatureCard({ feature }: { feature: FeatureEntry }) {
  const [expanded, setExpanded] = useState(false);
  const openGaps = feature.gaps.filter((g) => !g.closed);
  const hasDetail = !!feature.frontendDetail;

  return (
    <Card className={`transition-all ${openGaps.length === 0 ? "border-emerald-200" : openGaps.some(g => g.severity === "critical" || g.severity === "high") ? "border-orange-200" : "border-amber-100"}`}>
      <CardContent className="pt-4 pb-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2 min-w-0">
            <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-mono font-semibold text-slate-600">
              {feature.id}
            </span>
            <div className="min-w-0">
              <p className="font-semibold text-sm text-slate-900 leading-tight">{feature.name}</p>
              {feature.csdddArticle && (
                <span className="text-[10px] text-slate-400">{feature.csdddArticle}</span>
              )}
            </div>
          </div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="shrink-0 rounded p-0.5 hover:bg-muted transition-colors"
          >
            {expanded
              ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
              : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
          </button>
        </div>

        {/* Workflow badges */}
        <div className="mt-2 flex flex-wrap gap-1">
          {feature.workflows.map((wf) => (
            <span key={wf} className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${WORKFLOWS[wf].color}`}>
              {wf}
            </span>
          ))}
        </div>

        {/* Frontend status row */}
        <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
          <span className={feature.frontendList ? "text-emerald-600" : "text-red-500"}>
            {feature.frontendList ? "✓ Liste" : "✗ Liste"}
          </span>
          <span className={hasDetail ? "text-emerald-600" : "text-red-500"}>
            {hasDetail ? "✓ Detail" : "✗ Detail"}
          </span>
          <span className={feature.tests.length > 0 ? "text-emerald-600" : "text-red-500"}>
            {feature.tests.length > 0 ? `✓ Tests (${feature.tests.length})` : "✗ Tests"}
          </span>
        </div>

        {/* Gap count pill */}
        {openGaps.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {openGaps.map((g, i) => (
              <span key={i} className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${GAP_COLORS[g.severity]}`}>
                {g.text}
              </span>
            ))}
          </div>
        )}
        {openGaps.length === 0 && (
          <p className="mt-2 text-[10px] text-emerald-600 font-medium">✓ Keine offenen Gaps</p>
        )}

        {/* Expanded detail */}
        {expanded && (
          <div className="mt-4 pt-3 border-t border-border space-y-3 text-xs text-muted-foreground">
            <div>
              <p className="font-semibold text-slate-700 mb-0.5">Backend</p>
              <p className="font-mono text-[10px] break-all">{feature.backendService}</p>
            </div>
            <div>
              <p className="font-semibold text-slate-700 mb-0.5">API Router</p>
              <p className="font-mono text-[10px] break-all">{feature.apiRouter}</p>
            </div>
            <div>
              <p className="font-semibold text-slate-700 mb-0.5">DB Model</p>
              <p className="font-mono text-[10px] break-all">{feature.dbModel}</p>
            </div>
            {feature.upstream.length > 0 && (
              <div>
                <p className="font-semibold text-slate-700 mb-1">Upstream (FK-Abhängigkeiten)</p>
                <div className="flex flex-wrap gap-1">
                  {feature.upstream.map((u) => (
                    <span key={u} className="rounded bg-blue-50 text-blue-700 px-1.5 py-0.5 text-[10px]">{u}</span>
                  ))}
                </div>
              </div>
            )}
            {feature.downstream.length > 0 && (
              <div>
                <p className="font-semibold text-slate-700 mb-1">Downstream</p>
                <div className="flex flex-wrap gap-1">
                  {feature.downstream.map((d) => (
                    <span key={d} className="rounded bg-violet-50 text-violet-700 px-1.5 py-0.5 text-[10px]">{d}</span>
                  ))}
                </div>
              </div>
            )}
            {feature.tests.length > 0 && (
              <div>
                <p className="font-semibold text-slate-700 mb-1">Test-Dateien</p>
                {feature.tests.map((t) => (
                  <p key={t} className="font-mono text-[10px] text-slate-500">{t}</p>
                ))}
              </div>
            )}
            {feature.frontendList && (
              <div className="flex items-center gap-3 pt-1">
                <a
                  href={feature.frontendList.includes("[id]") ? "#" : feature.frontendList}
                  className="flex items-center gap-1 text-blue-600 hover:underline text-[10px]"
                >
                  <ExternalLink className="h-3 w-3" /> Liste öffnen
                </a>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FeatureGraphTab() {
  const [search, setSearch] = useState("");
  const [wfFilter, setWfFilter] = useState<WorkflowId | "ALL">("ALL");
  const [gapFilter, setGapFilter] = useState<"ALL" | "HAS_GAPS" | "CLEAN">("ALL");

  const filtered = FEATURES.filter((f) => {
    const matchSearch =
      !search ||
      f.name.toLowerCase().includes(search.toLowerCase()) ||
      f.id.toLowerCase().includes(search.toLowerCase());
    const matchWf = wfFilter === "ALL" || f.workflows.includes(wfFilter);
    const openGaps = f.gaps.filter((g) => !g.closed);
    const matchGap =
      gapFilter === "ALL" ||
      (gapFilter === "HAS_GAPS" && openGaps.length > 0) ||
      (gapFilter === "CLEAN" && openGaps.length === 0);
    return matchSearch && matchWf && matchGap;
  });

  const totalGaps = FEATURES.reduce((n, f) => n + f.gaps.filter((g) => !g.closed).length, 0);
  const highGaps  = FEATURES.reduce((n, f) => n + f.gaps.filter((g) => !g.closed && (g.severity === "critical" || g.severity === "high")).length, 0);
  const cleanFeatures = FEATURES.filter((f) => f.gaps.filter((g) => !g.closed).length === 0).length;

  return (
    <div className="space-y-5">
      {/* KPI bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Features total", value: FEATURES.length, color: "text-slate-700" },
          { label: "Workflows", value: 5, color: "text-blue-700" },
          { label: "Offene Gaps",  value: totalGaps, color: totalGaps > 0 ? "text-orange-600" : "text-emerald-600" },
          { label: "Kritische Gaps", value: highGaps, color: highGaps > 0 ? "text-red-600" : "text-emerald-600" },
        ].map((kpi) => (
          <div key={kpi.label} className="rounded-xl border bg-white dark:bg-gray-900 px-4 py-3">
            <p className="text-xs text-muted-foreground">{kpi.label}</p>
            <p className={`text-2xl font-bold tabular-nums ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Search + Filter */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            className="w-full rounded-md border border-border bg-background pl-8 pr-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            placeholder="Feature suchen (Name oder ID)…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex gap-1 flex-wrap">
          {(["ALL", "WF-01", "WF-02", "WF-03", "WF-04", "WF-05"] as const).map((wf) => (
            <button
              key={wf}
              onClick={() => setWfFilter(wf)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                wfFilter === wf
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              {wf === "ALL" ? "Alle Workflows" : wf}
            </button>
          ))}
        </div>

        <div className="flex gap-1">
          {(["ALL", "HAS_GAPS", "CLEAN"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setGapFilter(f)}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${
                gapFilter === f
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              {f === "ALL" ? "Alle" : f === "HAS_GAPS" ? "Hat Gaps" : "✓ Ohne Gaps"}
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      <p className="text-xs text-muted-foreground">
        {filtered.length} von {FEATURES.length} Features
      </p>

      {/* Feature grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((f) => (
          <FeatureCard key={f.id} feature={f} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="py-12 text-center">
          <GitBranch className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">Keine Features gefunden.</p>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  const { t } = useLanguage();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("kb.pageTitle")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("kb.pageSubtitle")}</p>
      </div>

      <Tabs defaultValue="search">
        <TabsList>
          <TabsTrigger value="search">{t("kb.tabSearch")}</TabsTrigger>
          <TabsTrigger value="ingest">{t("kb.tabIngest")}</TabsTrigger>
          <TabsTrigger value="graph" className="gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            Feature Graph
          </TabsTrigger>
        </TabsList>
        <TabsContent value="search" className="mt-6"><SearchTab /></TabsContent>
        <TabsContent value="ingest" className="mt-6"><IngestTab /></TabsContent>
        <TabsContent value="graph" className="mt-6"><FeatureGraphTab /></TabsContent>
      </Tabs>
    </div>
  );
}
