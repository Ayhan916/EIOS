"use client";

import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Bot,
  ChevronRight,
  Loader2,
  Send,
  Sparkles,
  User,
} from "lucide-react";
import { founderChatApi, FOUNDER_QUICK_ACTIONS } from "@/lib/api/founder-chat";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  model_used?: string;
  generation_ms?: number | null;
  context_available?: boolean;
}

// ── Markdown-lite renderer (bold + headers only) ───────────────────────────────

function renderAnswer(text: string) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    if (line.startsWith("**") && line.endsWith("**")) {
      return (
        <p key={i} className="font-bold text-gray-900 dark:text-white mt-3 first:mt-0">
          {line.slice(2, -2)}
        </p>
      );
    }
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={i} className={line === "" ? "mt-2" : undefined}>
        {parts.map((part, j) =>
          part.startsWith("**") && part.endsWith("**") ? (
            <strong key={j}>{part.slice(2, -2)}</strong>
          ) : (
            part
          )
        )}
      </p>
    );
  });
}

// ── Main component ─────────────────────────────────────────────────────────────

export function FounderChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: founderChatApi.ask,
    onSuccess: (data) => {
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          model_used: data.model_used,
          generation_ms: data.generation_ms,
          context_available: data.context_available,
        },
      ]);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    },
  });

  const submit = (question: string) => {
    if (!question.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    mutation.mutate({ question, conversation_id: conversationId, window_days: 30 });
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex flex-col" style={{ minHeight: 420 }}>
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-100 dark:border-gray-800 px-4 py-3">
        <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-1.5">
          <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900 dark:text-white">Founder Intelligence</p>
          <p className="text-xs text-gray-400">Grounded in internal EIOS metrics only</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ maxHeight: 400 }}>
        {messages.length === 0 && (
          <div className="py-6 text-center">
            <Bot className="mx-auto h-8 w-8 text-gray-300 mb-3" />
            <p className="text-sm text-gray-400 mb-4">
              Ask about platform health, evaluation metrics, agent status, or costs.
            </p>
            <div className="flex flex-col gap-2 items-center">
              {FOUNDER_QUICK_ACTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => submit(q)}
                  className="flex items-center gap-1.5 rounded-lg border border-gray-200 dark:border-gray-700 px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors max-w-xs text-left"
                >
                  <ChevronRight className="h-3 w-3 shrink-0 text-gray-400" />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && (
              <div className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 p-1.5 h-7 w-7 shrink-0 flex items-center justify-center mt-0.5">
                <Bot className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
              </div>
            )}

            <div
              className={`rounded-xl px-4 py-3 text-sm max-w-[82%] ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-200"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="space-y-0.5 leading-relaxed">{renderAnswer(msg.content)}</div>
              ) : (
                msg.content
              )}
              {msg.role === "assistant" && msg.generation_ms !== undefined && (
                <p className="text-xs text-gray-400 mt-2">
                  {msg.model_used} · {msg.generation_ms}ms
                  {msg.context_available === false && (
                    <span className="ml-2 text-amber-500">⚠ No evaluation data</span>
                  )}
                </p>
              )}
            </div>

            {msg.role === "user" && (
              <div className="rounded-full bg-gray-200 dark:bg-gray-700 p-1.5 h-7 w-7 shrink-0 flex items-center justify-center mt-0.5">
                <User className="h-3.5 w-3.5 text-gray-600 dark:text-gray-300" />
              </div>
            )}
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex gap-3">
            <div className="rounded-full bg-indigo-100 dark:bg-indigo-900/30 p-1.5 h-7 w-7 shrink-0 flex items-center justify-center">
              <Bot className="h-3.5 w-3.5 text-indigo-600" />
            </div>
            <div className="rounded-xl bg-gray-50 dark:bg-gray-800 px-4 py-3 flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
              <span className="text-xs text-gray-400">Analysing platform data…</span>
            </div>
          </div>
        )}

        {mutation.isError && (
          <p className="text-xs text-red-500 text-center">
            Error contacting Founder Chat. Check console.
          </p>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-100 dark:border-gray-800 p-3 flex gap-2">
        <textarea
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about platform health, benchmarks, costs…"
          disabled={mutation.isPending}
          className="flex-1 resize-none rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 disabled:opacity-50"
        />
        <button
          onClick={() => submit(input)}
          disabled={mutation.isPending || !input.trim()}
          className="shrink-0 rounded-lg bg-indigo-600 px-3 py-2 text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
