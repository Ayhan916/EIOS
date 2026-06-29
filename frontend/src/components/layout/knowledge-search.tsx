"use client";

import { useState } from "react";
import { BookOpen, Loader2, Search, X } from "lucide-react";
import apiClient from "@/lib/api/client";

interface KBResult {
  chunk_id: string;
  evidence_id: string;
  evidence_title: string;
  evidence_source: string;
  text: string;
  similarity: number;
}

export function KnowledgeSearchDrawer() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<KBResult[]>([]);
  const [searched, setSearched] = useState(false);

  async function search() {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(false);
    try {
      const r = await apiClient.post("/api/v1/knowledge/search", {
        query: query.trim(),
        limit: 8,
        min_similarity: 0.1,
      });
      setResults(r.data?.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-md border border-border bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
        title="Search knowledge base"
      >
        <BookOpen className="h-3.5 w-3.5" />
        Ask KB
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/40" onClick={() => setOpen(false)}>
          <div
            className="w-full max-w-xl rounded-xl bg-background border border-border shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 border-b border-border px-4 py-3">
              <BookOpen className="h-4 w-4 text-violet-500 flex-shrink-0" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                placeholder="Search the knowledge base…"
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : (
                <button onClick={search} className="text-violet-600 hover:text-violet-800">
                  <Search className="h-4 w-4" />
                </button>
              )}
              <button onClick={() => setOpen(false)} className="ml-1 text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {searched && results.length === 0 && (
                <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No results found. Try different keywords.
                </p>
              )}
              {results.map((r) => (
                <div key={r.chunk_id} className="border-b border-border last:border-0 px-4 py-3 hover:bg-muted/30 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-foreground">{r.evidence_title}</p>
                    <span className="flex-shrink-0 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
                      {Math.round(r.similarity * 100)}%
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-3">{r.text}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">{r.evidence_source}</p>
                </div>
              ))}
              {!searched && (
                <div className="px-4 py-8 text-center text-xs text-muted-foreground">
                  Type a question and press Enter or click Search
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export function AskKBButton({ contextQuery }: { contextQuery?: string }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(contextQuery ?? "");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<KBResult[]>([]);
  const [searched, setSearched] = useState(false);

  async function search(q?: string) {
    const searchQ = q ?? query;
    if (!searchQ.trim()) return;
    setLoading(true);
    try {
      const r = await apiClient.post("/api/v1/knowledge/search", {
        query: searchQ.trim(),
        limit: 5,
        min_similarity: 0.1,
      });
      setResults(r.data?.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
      setSearched(true);
    }
  }

  return (
    <div className="space-y-2">
      <button
        onClick={() => { setOpen((v) => !v); if (!open && contextQuery) search(contextQuery); }}
        className="inline-flex items-center gap-1.5 rounded-md bg-violet-50 px-3 py-1.5 text-xs font-medium text-violet-700 hover:bg-violet-100 transition-colors"
      >
        <BookOpen className="h-3.5 w-3.5" />
        Ask Knowledge Base
      </button>

      {open && (
        <div className="rounded-lg border border-violet-200 bg-violet-50/40 p-3 space-y-2">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Ask the knowledge base…"
              className="flex-1 rounded border border-input bg-background px-2 py-1.5 text-xs"
            />
            <button
              onClick={() => search()}
              disabled={loading || !query.trim()}
              className="rounded bg-violet-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50 hover:bg-violet-700"
            >
              {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : "Search"}
            </button>
          </div>
          {searched && results.length === 0 && (
            <p className="text-xs text-muted-foreground">No results.</p>
          )}
          {results.map((r) => (
            <div key={r.chunk_id} className="rounded border border-violet-200 bg-white/60 p-2">
              <p className="text-xs font-medium">{r.evidence_title}</p>
              <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">{r.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
