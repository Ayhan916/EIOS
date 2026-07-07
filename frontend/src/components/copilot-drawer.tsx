"use client";

import { useRef, useState } from "react";
import { Bot, ChevronRight, Send, X } from "lucide-react";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface CopilotDrawerProps {
  contextType: "finding" | "risk" | "disclosure" | "compliance" | "recommendation" | "cap" | "general";
  contextId?: string;
  contextSummary?: string;
}

export function CopilotDrawer({ contextType, contextId, contextSummary }: CopilotDrawerProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const SUGGESTED: Record<string, string[]> = {
    finding: [
      "Draft a remediation recommendation for this finding.",
      "What controls address this finding?",
      "Summarize the risk impact.",
    ],
    risk: [
      "What mitigation options exist for this risk?",
      "Draft an escalation message for this risk.",
      "Which frameworks reference this risk?",
    ],
    disclosure: [
      "Draft an ESG disclosure paragraph.",
      "Identify gaps in this disclosure.",
      "Suggest supporting evidence.",
    ],
    compliance: [
      "What controls close this compliance gap?",
      "Draft a remediation plan for this gap.",
    ],
    general: ["Summarize the current risk posture.", "What are the highest-priority actions?"],
  };

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await apiClient.post("/api/v1/copilot/ask", {
        question,
        context_type: contextType,
        context_id: contextId ?? null,
        conversation_id: conversationId,
      });
      const data = res.data as { answer: string; conversation_id: string };
      setConversationId(data.conversation_id);
      setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Failed to get a response. Please try again." }]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors shadow-sm"
        title="Open AI Copilot"
      >
        <Bot className="h-4 w-4" />
        Copilot
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex">
          <button
            className="flex-1 bg-black/30"
            onClick={() => setOpen(false)}
            aria-label="Close"
          />
          <div className="flex w-[420px] max-w-full flex-col bg-background shadow-2xl border-l border-border">
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-violet-600" />
                <span className="font-semibold text-sm">AI Copilot</span>
                <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-medium text-violet-700 uppercase">
                  {contextType}
                </span>
              </div>
              <button onClick={() => setOpen(false)} className="rounded p-1 hover:bg-muted">
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Context hint */}
            {contextSummary && (
              <div className="border-b bg-muted/30 px-4 py-2 text-xs text-muted-foreground line-clamp-2">
                {contextSummary}
              </div>
            )}

            {/* Suggested questions (shown when empty) */}
            {messages.length === 0 && (
              <div className="px-4 pt-4 space-y-2">
                <p className="text-xs font-medium text-muted-foreground">Suggested questions</p>
                {(SUGGESTED[contextType] ?? SUGGESTED.general).map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="flex w-full items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-left hover:bg-muted transition-colors"
                  >
                    <ChevronRight className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`rounded-xl px-3 py-2 text-sm max-w-[92%] whitespace-pre-wrap ${
                    m.role === "user"
                      ? "ml-auto bg-violet-600 text-white"
                      : "bg-muted text-foreground"
                  }`}
                >
                  {m.content}
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Spinner className="h-3 w-3" /> Thinking…
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t px-3 py-3 flex gap-2">
              <input
                className="flex-1 rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500"
                placeholder="Ask anything about this item…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send();
                  }
                }}
                disabled={loading}
              />
              <Button
                size="sm"
                className="px-2 bg-violet-600 hover:bg-violet-700"
                disabled={!input.trim() || loading}
                onClick={() => send()}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
