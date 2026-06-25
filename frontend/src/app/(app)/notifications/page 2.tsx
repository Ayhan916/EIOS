"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bell,
  BellOff,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Filter,
  Inbox,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import {
  listNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "@/lib/api/notifications";
import type { NotificationResponse } from "@/types/api";

function entityHref(type: string | null | undefined, id: string | null | undefined): string | null {
  if (!type || !id) return null;
  const t = type.toLowerCase();
  if (t === "supplier" || t === "supplier_user") return `/suppliers/${id}`;
  if (t === "assessment") return `/assessments/${id}`;
  if (t === "finding") return `/findings`;
  if (t === "recommendation") return `/recommendations`;
  if (t === "risk") return `/executive`;
  if (t === "kpi") return `/sustainability/kpis`;
  return null;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  workflow_completed:       { label: "Workflow",   color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" },
  action_overdue:           { label: "Overdue",    color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" },
  assessment_approved:      { label: "Approved",   color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200" },
  recommendation_assigned:  { label: "Assigned",   color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200" },
  finding_escalated:        { label: "Escalation", color: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" },
  risk_critical:            { label: "Risk",       color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" },
};

type FilterType = "all" | "unread" | keyof typeof TYPE_LABELS;

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

const PAGE_SIZE = 20;

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>("all");
  const [page, setPage] = useState(0);

  async function load() {
    setLoading(true);
    try {
      const data = await listNotifications();
      setItems(data.items);
    } catch {
      // non-critical
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleRead(id: string) {
    await markNotificationRead(id);
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
  }

  async function handleReadAll() {
    await markAllNotificationsRead();
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }

  const filtered = items.filter((n) => {
    if (filter === "unread") return !n.is_read;
    if (filter === "all") return true;
    return n.notification_type === filter;
  });

  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const unreadCount = items.filter((n) => !n.is_read).length;
  const uniqueTypes = [...new Set(items.map((n) => n.notification_type))];

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Notifications</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {unreadCount > 0 ? `${unreadCount} unread` : "All caught up"}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleReadAll}
            className="gap-1.5"
            aria-label="Mark all notifications as read"
          >
            <CheckCheck className="h-4 w-4" aria-hidden="true" />
            Mark all read
          </Button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter notifications">
        {(["all", "unread", ...uniqueTypes] as FilterType[]).map((f) => (
          <button
            key={f}
            onClick={() => { setFilter(f); setPage(0); }}
            aria-pressed={filter === f}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors border",
              filter === f
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:border-primary/50 hover:text-foreground"
            )}
          >
            {f === "all" ? `All (${items.length})` : f === "unread" ? `Unread (${unreadCount})` : (TYPE_LABELS[f]?.label ?? f)}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : pageItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
              <Inbox className="h-10 w-10 opacity-30" aria-hidden="true" />
              <p className="text-sm">No notifications{filter !== "all" ? " for this filter" : ""}</p>
            </div>
          ) : (
            <ul role="list" className="divide-y divide-border">
              {pageItems.map((n) => {
                const meta = TYPE_LABELS[n.notification_type];
                return (
                  <li
                    key={n.id}
                    className={cn(
                      "group flex items-start gap-4 px-6 py-4 transition-colors hover:bg-muted/40",
                      !n.is_read && "bg-primary/3"
                    )}
                  >
                    {/* Unread indicator */}
                    <div className="mt-1.5 flex-shrink-0">
                      {!n.is_read ? (
                        <div className="h-2 w-2 rounded-full bg-primary" aria-label="Unread" />
                      ) : (
                        <div className="h-2 w-2" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span
                          className={cn(
                            "rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                            meta?.color ?? "bg-muted text-muted-foreground"
                          )}
                        >
                          {meta?.label ?? n.notification_type}
                        </span>
                        <time
                          dateTime={n.created_at}
                          className="text-xs text-muted-foreground"
                        >
                          {timeAgo(n.created_at)}
                        </time>
                      </div>
                      <p className="text-sm font-medium text-foreground">{n.title}</p>
                      {n.body && (
                        <p className="mt-0.5 text-sm text-muted-foreground line-clamp-2">
                          {n.body}
                        </p>
                      )}
                      {n.entity_type && n.entity_id && (() => {
                        const href = entityHref(n.entity_type, n.entity_id);
                        const label = `${n.entity_type} · ${n.entity_id.slice(0, 8)}…`;
                        return href ? (
                          <Link
                            href={href}
                            className="mt-1 inline-block text-xs text-blue-600 hover:underline"
                          >
                            {label}
                          </Link>
                        ) : (
                          <p className="mt-1 text-xs text-muted-foreground">{label}</p>
                        );
                      })()}
                    </div>

                    {!n.is_read && (
                      <button
                        onClick={() => handleRead(n.id)}
                        aria-label={`Mark "${n.title}" as read`}
                        className="flex-shrink-0 rounded p-1.5 text-muted-foreground opacity-0 group-hover:opacity-100 hover:bg-muted hover:text-foreground transition-opacity"
                      >
                        <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page + 1} of {totalPages} · {filtered.length} notifications
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
