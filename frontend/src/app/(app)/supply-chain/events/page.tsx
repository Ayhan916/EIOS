"use client";

import { useEffect, useState } from "react";
import {
  listEvents,
  listOutbox,
  retryOutboxEntry,
  type EventLog,
  type EventOutbox,
} from "@/lib/api/supply_chain_events";
import { useLanguage } from "@/lib/i18n/context";

type View = "events" | "outbox";

const STATUS_COLORS: Record<string, string> = {
  OK: "bg-green-100 text-green-700",
  ERROR: "bg-red-100 text-red-700",
  PENDING: "bg-yellow-100 text-yellow-700",
  PUBLISHED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

function truncate(s: string, n = 40): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

export default function SupplyChainEventsPage() {
  const { t } = useLanguage();
  const [view, setView] = useState<View>("events");
  const [events, setEvents] = useState<EventLog[]>([]);
  const [outbox, setOutbox] = useState<EventOutbox[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [totalOutbox, setTotalOutbox] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [aggregateTypeFilter, setAggregateTypeFilter] = useState("");
  const [outboxStatusFilter, setOutboxStatusFilter] = useState("");
  const [retrying, setRetrying] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    if (view === "events") {
      listEvents({
        event_type: eventTypeFilter || undefined,
        aggregate_type: aggregateTypeFilter || undefined,
      })
        .then((res) => {
          setEvents(res.items);
          setTotalEvents(res.total);
        })
        .catch((e) => setError(e.message ?? "Failed to load events"))
        .finally(() => setLoading(false));
    } else {
      listOutbox({ outbox_status: outboxStatusFilter || undefined })
        .then((res) => {
          setOutbox(res.items);
          setTotalOutbox(res.total);
        })
        .catch((e) => setError(e.message ?? "Failed to load outbox"))
        .finally(() => setLoading(false));
    }
  }, [view, eventTypeFilter, aggregateTypeFilter, outboxStatusFilter]);

  async function handleRetry(id: string) {
    setRetrying(id);
    try {
      const updated = await retryOutboxEntry(id);
      setOutbox((prev) =>
        prev.map((e) => (e.id === id ? updated : e))
      );
    } catch (e: unknown) {
      if (e instanceof Error) setError(e.message);
    } finally {
      setRetrying(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">
          {t("eventBus.title")}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {t("eventBus.subtitle")}
        </p>
      </div>

      {/* View Toggle */}
      <div className="flex gap-4 border-b border-gray-200">
        {(["events", "outbox"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`pb-2 capitalize text-sm font-medium transition-colors ${
              view === v
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {v === "events" ? "Event Log" : "Outbox Queue"}
          </button>
        ))}
      </div>

      {/* Event Log Filters */}
      {view === "events" && (
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Filter by event type…"
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-60"
          />
          <input
            type="text"
            placeholder="Filter by aggregate type…"
            value={aggregateTypeFilter}
            onChange={(e) => setAggregateTypeFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-60"
          />
        </div>
      )}

      {/* Outbox Filters */}
      {view === "outbox" && (
        <div className="flex gap-3">
          <select
            value={outboxStatusFilter}
            onChange={(e) => setOutboxStatusFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">{t("eventBus.allSeverities")}</option>
            <option value="PENDING">Pending</option>
            <option value="PUBLISHED">Published</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <p className="text-sm text-gray-500">{t("common.loading")}</p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : view === "events" ? (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("eventBus.eventType")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.type")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("eventBus.source")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.status")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Offset</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("eventBus.timestamp")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-gray-400">
                      {t("eventBus.noEvents")}
                    </td>
                  </tr>
                ) : (
                  events.map((e) => (
                    <tr key={e.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">
                        {e.event_type}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        <span className="font-medium">{e.aggregate_type}</span>
                        <span className="ml-1 font-mono text-xs text-gray-400">
                          {e.aggregate_id.slice(0, 8)}…
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">
                        {truncate(e.topic, 30)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            STATUS_COLORS[e.handler_status] ?? "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {e.handler_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">
                        {e.kafka_partition}/{e.kafka_offset}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(e.consumed_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
              {t("common.total")}: {totalEvents}
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("eventBus.eventType")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.type")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("eventBus.source")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.status")}</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">Attempts</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-500">{t("common.createdAt")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {outbox.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-gray-400">
                      {t("eventBus.noEventsDesc")}
                    </td>
                  </tr>
                ) : (
                  outbox.map((e) => (
                    <tr key={e.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-700">
                        {e.event_type}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        <span className="font-medium">{e.aggregate_type}</span>
                        <span className="ml-1 font-mono text-xs text-gray-400">
                          {e.aggregate_id.slice(0, 8)}…
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">
                        {truncate(e.topic, 28)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                            STATUS_COLORS[e.outbox_status] ?? "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {e.outbox_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-gray-700">
                        {e.attempts}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {e.outbox_status === "FAILED" && (
                          <button
                            onClick={() => handleRetry(e.id)}
                            disabled={retrying === e.id}
                            className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                          >
                            {retrying === e.id ? "Retrying…" : "Retry"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
            <div className="border-t border-gray-200 bg-gray-50 px-4 py-2 text-xs text-gray-500">
              {t("common.total")}: {totalOutbox}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
