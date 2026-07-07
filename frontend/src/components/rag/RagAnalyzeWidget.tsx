"use client";

import { useState } from "react";
import { Bot, ChevronDown, ChevronUp, Loader2, Search, Sparkles } from "lucide-react";
import { ragAnalyze, type RagAnalyzeResponse, type RagSource } from "@/lib/api/rag";
import { Button } from "@/components/ui/button";

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
  HIGH:     "bg-orange-100 text-orange-700 border-orange-200",
  MEDIUM:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  LOW:      "bg-blue-100 text-blue-700 border-blue-200",
};

const EXAMPLE_QUERIES = [
  "Welche Risiken gibt es aktuell?",
  "Gibt es Hinweise auf Menschenrechtsverletzungen?",
  "Wie ist die finanzielle Lage?",
  "Welche Lieferkettenstörungen wurden gemeldet?",
];

function SourceCard({ source }: { source: RagSource }) {
  const typeLabel = source.doc_type === "news_article" ? "Nachricht" : "Intelligence-Event";
  const severityClass = source.severity ? SEVERITY_COLORS[source.severity] ?? "" : "";

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs space-y-1">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-medium text-muted-foreground">{typeLabel}</span>
        {source.severity && (
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${severityClass}`}>
            {source.severity}
          </span>
        )}
        {source.published_at && (
          <span className="text-muted-foreground">{source.published_at}</span>
        )}
        {source.source_name && (
          <span className="text-muted-foreground">· {source.source_name}</span>
        )}
        <span className="ml-auto text-muted-foreground">
          {(source.similarity * 100).toFixed(0)}% Relevanz
        </span>
      </div>
      <p className="text-muted-foreground leading-relaxed">{source.content_preview}</p>
    </div>
  );
}

interface Props {
  supplierId: string;
  supplierName: string;
}

export function RagAnalyzeWidget({ supplierId, supplierName }: Props) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RagAnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSources, setShowSources] = useState(false);

  async function handleAnalyze(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setShowSources(false);
    try {
      const res = await ragAnalyze({
        query: trimmed,
        supplier_id: supplierId,
        supplier_name: supplierName,
        top_k: 6,
      });
      setResult(res);
    } catch {
      setError("Analyse fehlgeschlagen. Bitte stelle sicher dass der RAG Knowledge Base befüllt ist.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-border bg-background p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100">
          <Sparkles className="h-4 w-4 text-violet-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">KI-Risikoanalyse</h3>
          <p className="text-xs text-muted-foreground">
            Stelle Fragen zu {supplierName} — beantwortet aus dem Intelligence Knowledge Base
          </p>
        </div>
      </div>

      {/* Example queries */}
      <div className="flex flex-wrap gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            onClick={() => { setQuery(q); handleAnalyze(q); }}
            className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:border-violet-400 hover:text-violet-600 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyze(query)}
            placeholder="Frage stellen…"
            className="w-full rounded-lg border border-input bg-background pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
        <Button
          onClick={() => handleAnalyze(query)}
          disabled={loading || !query.trim()}
          className="bg-violet-600 hover:bg-violet-700 text-white gap-2"
          size="sm"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
          {loading ? "Analysiere…" : "Analysieren"}
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-3">
          {/* Answer */}
          <div className="rounded-lg border border-violet-200 bg-violet-50/50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Bot className="h-4 w-4 text-violet-600" />
              <span className="text-xs font-semibold text-violet-700">
                Antwort · {result.model}
              </span>
            </div>
            <div className="prose prose-sm max-w-none text-sm text-foreground whitespace-pre-wrap leading-relaxed">
              {result.answer}
            </div>
          </div>

          {/* Sources toggle */}
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
                    <SourceCard key={s.rank} source={s} />
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
