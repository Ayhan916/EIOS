"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarIcon, CheckCircle2, ClipboardList } from "lucide-react";
import Link from "next/link";
import { operatingSystemApi, CalendarEvent } from "@/lib/api/operating-system";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatDateTime } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  SCHEDULED: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-red-100 text-red-800",
  PENDING:   "bg-yellow-100 text-yellow-800",
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  COMPLIANCE_DEADLINE: "bg-red-100 text-red-700 border-red-200",
  AUDIT_DEADLINE:      "bg-orange-100 text-orange-700 border-orange-200",
  REPORTING_DEADLINE:  "bg-amber-100 text-amber-700 border-amber-200",
  ASSESSMENT:          "bg-blue-100 text-blue-700 border-blue-200",
  REVIEW:              "bg-violet-100 text-violet-700 border-violet-200",
  TRAINING:            "bg-emerald-100 text-emerald-700 border-emerald-200",
  MEETING:             "bg-slate-100 text-slate-700 border-slate-200",
  // short-form aliases used by the backend
  DEADLINE:            "bg-red-100 text-red-700 border-red-200",
  AUDIT:               "bg-orange-100 text-orange-700 border-orange-200",
};

type ViewMode = "month" | "week" | "day";

function getViewRange(mode: ViewMode): { start: Date; end: Date } {
  const now = new Date();
  const start = new Date(now);
  const end = new Date(now);
  if (mode === "day") {
    start.setHours(0, 0, 0, 0);
    end.setHours(23, 59, 59, 999);
  } else if (mode === "week") {
    const day = now.getDay();
    start.setDate(now.getDate() - day);
    start.setHours(0, 0, 0, 0);
    end.setDate(start.getDate() + 6);
    end.setHours(23, 59, 59, 999);
  } else {
    start.setDate(1);
    start.setHours(0, 0, 0, 0);
    end.setMonth(now.getMonth() + 1, 0);
    end.setHours(23, 59, 59, 999);
  }
  return { start, end };
}

const DEADLINE_TYPES = new Set(["COMPLIANCE_DEADLINE", "AUDIT_DEADLINE", "REPORTING_DEADLINE", "DEADLINE"]);

// ── Create Assessment Inline ──────────────────────────────────────────────────

function CreateAssessmentForm({
  event,
  onClose,
}: {
  event: CalendarEvent;
  onClose: () => void;
}) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(`Assessment: ${event.title}`);
  const [description, setDescription] = useState(
    event.notes ?? `Assessment triggered by calendar event: ${event.title}`
  );
  const [done, setDone] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post("/assessments/", {
        title,
        description,
        assessment_type: event.event_type,
        scope: "Full",
      });
      return res.data as { id: string };
    },
    onSuccess: (data) => {
      setCreatedId(data.id);
      setDone(true);
      queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
      setTimeout(onClose, 2000);
    },
  });

  if (done && createdId) {
    return (
      <div className="space-y-1 py-1">
        <div className="flex items-center gap-2 text-xs text-emerald-600">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Assessment created.{" "}
          <Link href={`/assessments/${createdId}`} className="underline font-medium">
            Open →
          </Link>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-blue-600">
          <ClipboardList className="h-3.5 w-3.5" />
          A notification has been sent.{" "}
          <Link href="/notifications" className="underline font-medium">
            Check inbox →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-blue-200 bg-blue-50/60 p-3">
      <p className="text-xs font-semibold text-blue-700">Create Assessment from Deadline</p>
      <div>
        <label className="block text-xs text-muted-foreground mb-1">{t("common.title")}</label>
        <input
          className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <div>
        <label className="block text-xs text-muted-foreground mb-1">{t("common.description")}</label>
        <textarea
          className="w-full rounded border border-input bg-background px-2 py-1 text-xs resize-none"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          className="h-7 text-xs px-3"
          disabled={!title.trim() || !description.trim() || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? t("common.loading") : t("assessments.newAssessment")}
        </Button>
        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={onClose}>
          {t("common.cancel")}
        </Button>
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-600">Failed to create assessment.</p>
      )}
    </div>
  );
}

// ── Event Row ─────────────────────────────────────────────────────────────────

function EventRow({ event }: { event: CalendarEvent }) {
  const { t } = useLanguage();
  const [showForm, setShowForm] = useState(false);
  const isDeadline = DEADLINE_TYPES.has(event.event_type);
  const typeColorClass = EVENT_TYPE_COLORS[event.event_type] ?? "bg-slate-100 text-slate-700 border-slate-200";

  return (
    <Card className={`border-l-4 ${typeColorClass.includes("red") ? "border-l-red-400" : typeColorClass.includes("orange") ? "border-l-orange-400" : typeColorClass.includes("amber") ? "border-l-amber-400" : typeColorClass.includes("blue") ? "border-l-blue-400" : typeColorClass.includes("violet") ? "border-l-violet-400" : typeColorClass.includes("emerald") ? "border-l-emerald-400" : "border-l-slate-300"}`}>
      <CardContent className="py-4 space-y-1">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <p className="font-medium">{event.title}</p>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold ${typeColorClass}`}>
                {event.event_type.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-muted-foreground">{formatDateTime(event.scheduled_at)}</span>
            </div>
            {event.notes && (
              <p className="text-xs text-muted-foreground">{event.notes}</p>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge className={STATUS_COLORS[event.event_status] ?? "bg-gray-100 text-gray-800"}>
              {event.event_status}
            </Badge>
            {isDeadline && event.event_status === "SCHEDULED" && !showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-100 transition-colors"
              >
                <ClipboardList className="h-3 w-3" /> {t("assessments.newAssessment")}
              </button>
            )}
          </div>
        </div>
        {showForm && (
          <CreateAssessmentForm event={event} onClose={() => setShowForm(false)} />
        )}
      </CardContent>
    </Card>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

const VIEW_LABELS: Record<ViewMode, string> = { month: "Month", week: "Week", day: "Day" };

export default function GovernanceCalendarPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("month");

  const { data: events, isLoading, error } = useQuery({
    queryKey: ["calendar-events"],
    queryFn: () => operatingSystemApi.listCalendarEvents({ limit: 100 }).then((r) => r.data),
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><Spinner /></div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load calendar events.</div>;
  }

  const { start, end } = getViewRange(viewMode);
  const filtered = events?.filter((e) => {
    const d = new Date(e.scheduled_at);
    return d >= start && d <= end;
  }) ?? [];

  const upcoming = filtered.filter((e) => e.event_status === "SCHEDULED");
  const past = filtered.filter((e) => e.event_status !== "SCHEDULED");
  const allUpcoming = events?.filter((e) => e.event_status === "SCHEDULED") ?? [];
  const deadlines = allUpcoming.filter((e) => DEADLINE_TYPES.has(e.event_type));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <CalendarIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">Governance Calendar</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg border overflow-hidden">
            {(["month", "week", "day"] as ViewMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  viewMode === mode
                    ? "bg-slate-800 text-white"
                    : "bg-white text-slate-600 hover:bg-muted/50"
                }`}
              >
                {VIEW_LABELS[mode]}
              </button>
            ))}
          </div>
          <span className="text-sm text-muted-foreground">{filtered.length} events</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Events</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{events?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Upcoming</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-blue-600">{upcoming.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Deadlines</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-3xl font-bold ${deadlines.length > 0 ? "text-amber-600" : "text-emerald-600"}`}>
              {deadlines.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">
              {events?.filter((e) => e.event_status === "COMPLETED").length ?? 0}
            </p>
          </CardContent>
        </Card>
      </div>

      {upcoming.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Upcoming</h2>
          <div className="space-y-3">
            {upcoming.map((evt) => (
              <EventRow key={evt.id} event={evt} />
            ))}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Past Events</h2>
          <div className="space-y-3">
            {past.map((evt) => (
              <EventRow key={evt.id} event={evt} />
            ))}
          </div>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          {events?.length === 0
            ? "No calendar events yet."
            : `No events in this ${viewMode}.`}
        </div>
      )}
    </div>
  );
}
