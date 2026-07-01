"use client";

import { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ExternalLink,
  Globe,
  Newspaper,
  RefreshCw,
  Building2,
  MapPin,
  Users,
} from "lucide-react";
import { getNewsFeed, triggerNewsRefresh, type NewsArticle } from "@/lib/api/news";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

const MATCH_TYPE_TABS = [
  { key: undefined, labelKey: "news.all" },
  { key: "supplier", labelKey: "news.supplier" },
  { key: "country", labelKey: "news.country" },
] as const;

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

function MatchBadge({ type }: { type: string }) {
  if (type === "supplier") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-semibold">
        <Building2 className="h-2.5 w-2.5" /> Lieferant
      </span>
    );
  }
  if (type === "country") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-[10px] font-semibold">
        <MapPin className="h-2.5 w-2.5" /> Land
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-[10px] font-semibold">
      <Users className="h-2.5 w-2.5" /> Partner
    </span>
  );
}

function LangBadge({ lang }: { lang: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-muted text-muted-foreground px-1.5 py-0.5 text-[10px] font-medium uppercase">
      <Globe className="h-2.5 w-2.5" />
      {lang}
    </span>
  );
}

function ArticleCard({ article, uiLanguage }: { article: NewsArticle; uiLanguage: string }) {
  const title =
    uiLanguage !== article.language && article.translated_title
      ? article.translated_title
      : article.title;
  const summary =
    uiLanguage !== article.language && article.translated_summary
      ? article.translated_summary
      : article.summary;

  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex gap-3 rounded-lg border border-border bg-card p-3 transition-colors hover:bg-muted/40"
    >
      {article.image_url && (
        <img
          src={article.image_url}
          alt=""
          className="h-16 w-24 flex-shrink-0 rounded object-cover"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-foreground leading-snug line-clamp-2 group-hover:text-primary transition-colors">
            {title}
          </p>
          <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground/50 mt-0.5" />
        </div>

        {summary && (
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{summary}</p>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <MatchBadge type={article.match_type} />
          {uiLanguage !== article.language && <LangBadge lang={article.language} />}

          {article.suppliers.slice(0, 3).map((s) => (
            <span
              key={s.id}
              className="rounded-full bg-slate-100 text-slate-600 px-2 py-0.5 text-[10px] font-medium truncate max-w-[120px]"
              title={s.name}
            >
              {s.name}
            </span>
          ))}
          {article.suppliers.length > 3 && (
            <span className="text-[10px] text-muted-foreground">
              +{article.suppliers.length - 3}
            </span>
          )}

          <span className="ml-auto text-[10px] text-muted-foreground flex-shrink-0">
            {article.source_name && <>{article.source_name} · </>}
            {timeAgo(article.published_at || article.fetched_at)}
          </span>
        </div>
      </div>
    </a>
  );
}

export function NewsFeedWidget() {
  const { t, language } = useLanguage();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<string | undefined>(undefined);
  const [refreshing, setRefreshing] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["news-feed", activeTab],
    queryFn: () => getNewsFeed({ match_type: activeTab, limit: 20 }),
    refetchInterval: 5 * 60 * 1000, // auto-refresh every 5 minutes
    staleTime: 2 * 60 * 1000,
  });

  const handleManualRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await triggerNewsRefresh(language);
      // Wait briefly then invalidate so the feed reloads with new articles
      await new Promise((r) => setTimeout(r, 2000));
      queryClient.invalidateQueries({ queryKey: ["news-feed"] });
    } finally {
      setRefreshing(false);
    }
  }, [language, queryClient]);

  const lastRefresh = data?.last_refresh
    ? new Date(data.last_refresh).toLocaleTimeString(language === "de" ? "de-DE" : "en-GB", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <Newspaper className="h-4 w-4 text-blue-500" />
              {t("news.title")}
            </CardTitle>
            <CardDescription>
              {t("news.description")}
              {lastRefresh && (
                <span className="ml-2 text-[10px]">· {t("news.lastUpdate")} {lastRefresh}</span>
              )}
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs flex-shrink-0"
            onClick={handleManualRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? t("news.refreshing") : t("news.refresh")}
          </Button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mt-2">
          {MATCH_TYPE_TABS.map(({ key, labelKey }) => (
            <button
              key={String(key)}
              onClick={() => setActiveTab(key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                activeTab === key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {t(labelKey)}
              {key === undefined && data?.total != null && (
                <span className="ml-1.5 rounded-full bg-primary/20 px-1.5 text-[10px]">
                  {data.total}
                </span>
              )}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading && (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
            ))}
          </div>
        )}

        {error && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {t("news.loadError")}
          </p>
        )}

        {!isLoading && !error && (!data?.articles.length) && (
          <div className="py-10 text-center">
            <Newspaper className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">{t("news.empty")}</p>
            <p className="text-xs text-muted-foreground mt-1">{t("news.emptyHint")}</p>
          </div>
        )}

        {!isLoading && data && data.articles.length > 0 && (
          <div className="space-y-2">
            {data.articles.map((article) => (
              <ArticleCard key={article.id} article={article} uiLanguage={language} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
