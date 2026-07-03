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
import { Search, BookOpen, CheckCircle, AlertTriangle, RefreshCw } from "lucide-react";

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
        </TabsList>
        <TabsContent value="search" className="mt-6"><SearchTab /></TabsContent>
        <TabsContent value="ingest" className="mt-6"><IngestTab /></TabsContent>
      </Tabs>
    </div>
  );
}
