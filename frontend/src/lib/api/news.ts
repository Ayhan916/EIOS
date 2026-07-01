import apiClient from "./client";

export interface NewsSupplier {
  id: string;
  name: string;
  match_reason: "direct" | "country" | "partner";
}

export interface NewsArticle {
  id: string;
  title: string;
  translated_title: string | null;
  summary: string | null;
  translated_summary: string | null;
  url: string;
  source_name: string | null;
  image_url: string | null;
  published_at: string | null;
  fetched_at: string;
  language: string;
  match_type: "supplier" | "country" | "partner";
  suppliers: NewsSupplier[];
}

export interface NewsFeedResponse {
  articles: NewsArticle[];
  total: number;
  limit: number;
  offset: number;
  last_refresh: string | null;
}

export async function getNewsFeed(params?: {
  match_type?: string;
  supplier_id?: string;
  limit?: number;
  offset?: number;
}): Promise<NewsFeedResponse> {
  const res = await apiClient.get("/news/feed", { params });
  return res.data;
}

export async function triggerNewsRefresh(uiLanguage = "de"): Promise<void> {
  await apiClient.post("/news/refresh", null, {
    params: { ui_language: uiLanguage },
  });
}
