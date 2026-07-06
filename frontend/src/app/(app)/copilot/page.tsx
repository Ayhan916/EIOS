"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Bot,
  ChevronRight,
  Loader2,
  MessageCircle,
  Plus,
  Send,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

// ── Types ────────────────────────────────────────────────────────────────────

interface Citation {
  citation_type: string;
  object_id: string;
  relevance: string;
}

interface Conversation {
  id: string;
  title: string;
  context_type: string;
  message_count: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent: string;
  citations: Citation[];
  model_used: string;
  generated_at: string;
}

interface AskResponse {
  conversation_id: string;
  answer: string;
  intent: string;
  citations: Citation[];
  model_used: string;
  confidence_level: string;
}

interface ExecutiveBrief {
  answer: string;
  key_risks: Record<string, unknown>[];
  compliance_concerns: Record<string, unknown>[];
  reporting_blockers: Record<string, unknown>[];
  recommended_actions: Record<string, unknown>[];
  open_recommendations_total: number;
  citations: Citation[];
  model_used: string;
  generated_at: string;
}

interface ActionAdvisor {
  answer: string;
  highest_impact_actions: Record<string, unknown>[];
  fastest_remediations: Record<string, unknown>[];
  risk_reduction_priorities: Record<string, unknown>[];
  finding_hotspots: Record<string, unknown>[];
  open_action_count: number;
  citations: Citation[];
  model_used: string;
  generated_at: string;
}

// ── Tab types ─────────────────────────────────────────────────────────────────

type Tab = "chat" | "brief" | "advisor";

// ── Helpers ───────────────────────────────────────────────────────────────────

function ItemList({ items, labelKey = "title" }: { items: Record<string, unknown>[]; labelKey?: string }) {
  const { t } = useLanguage();
  if (!items || items.length === 0) return <p className="text-xs text-muted-foreground italic">{t("copilot.noItems")}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-sm">
          <ChevronRight className="h-3.5 w-3.5 shrink-0 mt-0.5 text-muted-foreground" />
          <span>{String(item[labelKey] ?? item["description"] ?? item["title"] ?? JSON.stringify(item))}</span>
        </li>
      ))}
    </ul>
  );
}

function CitationBadges({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {citations.slice(0, 6).map((c) => (
        <Badge key={c.object_id} className="text-[10px] bg-slate-100 text-slate-600 font-mono">
          {c.citation_type}: {c.object_id.slice(0, 8)}
        </Badge>
      ))}
      {citations.length > 6 && (
        <Badge className="text-[10px] bg-slate-100 text-slate-500">+{citations.length - 6}</Badge>
      )}
    </div>
  );
}

// ── Chat Tab ──────────────────────────────────────────────────────────────────

function ChatTab() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [localMessages, setLocalMessages] = useState<{ role: "user" | "assistant"; content: string; confidence?: string }[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: conversations = [], isLoading: convsLoading } = useQuery<Conversation[]>({
    queryKey: ["copilot-conversations"],
    queryFn: () => apiClient.get("/copilot/conversations").then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: messages = [] } = useQuery<ChatMessage[]>({
    queryKey: ["copilot-messages", activeConvId],
    queryFn: () => apiClient.get(`/copilot/conversations/${activeConvId}/messages`).then((r) => r.data),
    enabled: !!activeConvId,
  });

  const { data: suggested } = useQuery<{ questions: string[] }>({
    queryKey: ["copilot-suggested"],
    queryFn: () => apiClient.get("/copilot/suggested-questions").then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const createConv = useMutation({
    mutationFn: () => apiClient.post<Conversation>("/copilot/conversations", { title: "New Conversation", context_type: "general" }).then((r) => r.data),
    onSuccess: (conv) => {
      qc.invalidateQueries({ queryKey: ["copilot-conversations"] });
      setActiveConvId(conv.id);
      setLocalMessages([]);
    },
  });

  const ask = useMutation({
    mutationFn: (question: string) =>
      apiClient.post<AskResponse>("/copilot/ask", {
        question,
        conversation_id: activeConvId,
        context_type: "general",
      }).then((r) => r.data),
    onMutate: (question) => {
      setLocalMessages((m) => [...m, { role: "user", content: question }]);
      setInput("");
    },
    onSuccess: (data) => {
      if (!activeConvId) setActiveConvId(data.conversation_id);
      setLocalMessages((m) => [...m, {
        role: "assistant",
        content: data.answer,
        confidence: data.confidence_level,
      }]);
      qc.invalidateQueries({ queryKey: ["copilot-conversations"] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || ask.isPending) return;
    ask.mutate(q);
  };

  const displayMessages = activeConvId && localMessages.length === 0 ? messages : localMessages;

  return (
    <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] gap-4 h-[calc(100vh-200px)] min-h-[500px]">
      {/* Conversation list */}
      <div className="flex flex-col gap-2 overflow-y-auto">
        <Button size="sm" className="w-full" onClick={() => { setActiveConvId(null); setLocalMessages([]); createConv.mutate(); }}>
          <Plus className="h-4 w-4 mr-1" /> {t("copilot.newChat")}
        </Button>
        {convsLoading && <Spinner className="mx-auto mt-4" />}
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => { setActiveConvId(conv.id); setLocalMessages([]); }}
            className={`text-left rounded-lg border px-3 py-2 text-sm transition-colors ${activeConvId === conv.id ? "bg-primary/10 border-primary/30" : "hover:bg-muted/50"}`}
          >
            <p className="font-medium line-clamp-1">{conv.title}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{t("copilot.messages").replace("{n}", String(conv.message_count))}</p>
          </button>
        ))}
        {conversations.length === 0 && !convsLoading && (
          <p className="text-xs text-muted-foreground px-2">{t("copilot.noConversations")}</p>
        )}
      </div>

      {/* Chat pane */}
      <div className="flex flex-col border rounded-xl bg-background overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {displayMessages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-4 py-8">
              <Bot className="h-12 w-12 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">{t("copilot.subtitle")}</p>
              {suggested?.questions && (
                <div className="w-full max-w-md space-y-2">
                  <p className="text-xs font-medium text-muted-foreground text-center">{t("copilot.suggestedQuestions")}</p>
                  {suggested.questions.slice(0, 5).map((q) => (
                    <button
                      key={q}
                      onClick={() => { setInput(q); ask.mutate(q); }}
                      className="w-full text-left text-xs px-3 py-2 rounded-lg border bg-muted/30 hover:bg-muted/60 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {displayMessages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-foreground"
              }`}>
                {msg.role === "assistant" && (
                  <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-muted-foreground">
                    <Bot className="h-3 w-3" /> EIOS Copilot
                    {"confidence" in msg && msg.confidence && (
                      <Badge className="text-[10px] bg-slate-100 text-slate-600 ml-1">{msg.confidence}</Badge>
                    )}
                  </div>
                )}
                {msg.content}
              </div>
            </div>
          ))}

          {ask.isPending && (
            <div className="flex justify-start">
              <div className="bg-muted/60 rounded-xl px-4 py-3 flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> {t("copilot.thinking")}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t p-3 flex gap-2">
          <input
            className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={t("copilot.placeholder")}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
          />
          <Button size="sm" disabled={!input.trim() || ask.isPending} onClick={handleSend}>
            {ask.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Executive Brief Tab ───────────────────────────────────────────────────────

function ExecutiveBriefTab() {
  const { t } = useLanguage();
  const [brief, setBrief] = useState<ExecutiveBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await apiClient.get<ExecutiveBrief>("/copilot/executive-brief");
      setBrief(r.data);
    } catch (e: unknown) {
      const err = e as { response?: { status?: number } };
      if (err?.response?.status === 403) {
        setError(t("copilot.errorExecutivePerms"));
      } else {
        setError(t("copilot.errorBriefFailed"));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">{t("copilot.briefNote")}</p>
        </div>
        <Button size="sm" disabled={loading} onClick={generate}>
          {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-1.5" />{t("copilot.generating")}</> : <><Sparkles className="h-4 w-4 mr-1.5" />{t("copilot.generateBrief")}</>}
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {brief && (
        <div className="space-y-4">
          {/* AI Narrative */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{t("copilot.narrativeSummary")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{brief.answer}</p>
              <CitationBadges citations={brief.citations} />
              <p className="text-[10px] text-muted-foreground mt-2">{t("copilot.modelUsed")}: {brief.model_used}</p>
            </CardContent>
          </Card>

          {/* 4 section grid */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-red-700">{t("copilot.keyRisks")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={brief.key_risks} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-orange-700">{t("copilot.compliance")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={brief.compliance_concerns} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-amber-700">{t("copilot.reportingBlockers")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={brief.reporting_blockers} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-green-700">{t("copilot.recommendedActions")}</CardTitle>
              </CardHeader>
              <CardContent>
                <ItemList items={brief.recommended_actions} />
                <p className="text-xs text-muted-foreground mt-3">
                  {t("copilot.openActions")}: <span className="font-semibold">{brief.open_recommendations_total}</span>
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Action Advisor Tab ────────────────────────────────────────────────────────

function ActionAdvisorTab() {
  const { t } = useLanguage();
  const [advisor, setAdvisor] = useState<ActionAdvisor | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await apiClient.get<ActionAdvisor>("/copilot/action-advisor");
      setAdvisor(r.data);
    } catch {
      setError(t("copilot.errorAdvisorFailed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-muted-foreground">{t("copilot.advisorNote")}</p>
        <Button size="sm" disabled={loading} onClick={generate}>
          {loading ? <><Loader2 className="h-4 w-4 animate-spin mr-1.5" />{t("copilot.generating")}</> : <><TrendingUp className="h-4 w-4 mr-1.5" />{t("copilot.generateAdvisor")}</>}
        </Button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {advisor && (
        <div className="space-y-4">
          {/* KPI chips */}
          <div className="flex flex-wrap gap-3">
            <div className="rounded-lg border bg-muted/30 px-4 py-3 text-center min-w-[120px]">
              <p className="text-xs text-muted-foreground">{t("copilot.openActions")}</p>
              <p className="text-2xl font-bold text-red-600">{advisor.open_action_count}</p>
            </div>
            <div className="rounded-lg border bg-muted/30 px-4 py-3 text-center min-w-[120px]">
              <p className="text-xs text-muted-foreground">{t("copilot.highestImpact")}</p>
              <p className="text-2xl font-bold">{advisor.highest_impact_actions.length}</p>
            </div>
            <div className="rounded-lg border bg-muted/30 px-4 py-3 text-center min-w-[120px]">
              <p className="text-xs text-muted-foreground">{t("copilot.findingHotspots")}</p>
              <p className="text-2xl font-bold text-orange-600">{advisor.finding_hotspots.length}</p>
            </div>
          </div>

          {/* AI narrative */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" /> {t("copilot.narrativeSummary")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{advisor.answer}</p>
              <CitationBadges citations={advisor.citations} />
              <p className="text-[10px] text-muted-foreground mt-2">{t("copilot.modelUsed")}: {advisor.model_used}</p>
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-red-700">{t("copilot.highestImpact")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={advisor.highest_impact_actions} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-green-700">{t("copilot.fastestRemediation")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={advisor.fastest_remediations} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-orange-700">{t("copilot.riskReduction")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={advisor.risk_reduction_priorities} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-amber-700">{t("copilot.findingHotspots")}</CardTitle>
              </CardHeader>
              <CardContent><ItemList items={advisor.finding_hotspots} /></CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const tab_defs = [
  { key: "chat" as Tab, label: "copilot.chatTab" as const, icon: MessageCircle },
  { key: "brief" as Tab, label: "copilot.briefTab" as const, icon: Sparkles },
  { key: "advisor" as Tab, label: "copilot.advisorTab" as const, icon: TrendingUp },
];

export default function CopilotPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("chat");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Bot className="h-7 w-7 text-primary" />
        <div>
          <h1 className="text-2xl font-semibold">{t("copilot.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("copilot.subtitle")}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b pb-0">
        {tab_defs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              activeTab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-4 w-4" />
            {t(label)}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "chat" && <ChatTab />}
        {activeTab === "brief" && <ExecutiveBriefTab />}
        {activeTab === "advisor" && <ActionAdvisorTab />}
      </div>
    </div>
  );
}
