"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock,
  FileCheck,
  Plus,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { capApi, CAP } from "@/lib/api/corrective-action-plans";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  DRAFT:              "bg-gray-100 text-gray-700",
  COMMITTED:          "bg-blue-100 text-blue-700",
  IN_PROGRESS:        "bg-amber-100 text-amber-700",
  EVIDENCE_SUBMITTED: "bg-violet-100 text-violet-700",
  VERIFIED:           "bg-emerald-100 text-emerald-700",
  CLOSED:             "bg-slate-100 text-slate-600",
};

const STATUS_STEPS = [
  "DRAFT",
  "COMMITTED",
  "IN_PROGRESS",
  "EVIDENCE_SUBMITTED",
  "VERIFIED",
  "CLOSED",
];

function StatusTrail({ current }: { current: string }) {
  const idx = STATUS_STEPS.indexOf(current);
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {STATUS_STEPS.map((s, i) => (
        <div key={s} className="flex items-center gap-1">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              i < idx
                ? "bg-gray-100 text-gray-400 line-through"
                : i === idx
                ? STATUS_COLOR[s] + " font-bold"
                : "bg-gray-50 text-gray-300"
            }`}
          >
            {s.replace("_", " ")}
          </span>
          {i < STATUS_STEPS.length - 1 && (
            <ChevronRight className={`h-3 w-3 ${i < idx ? "text-gray-300" : "text-gray-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── Create CAP form ───────────────────────────────────────────────────────────

function CreateCAPForm({
  findingId,
  onCreated,
}: {
  findingId: string;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [responsible, setResponsible] = useState("");
  const [deadline, setDeadline] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      capApi.create({
        finding_id: findingId,
        title,
        description,
        responsible_party: responsible,
        deadline: deadline || null,
      }),
    onSuccess: onCreated,
  });

  return (
    <div className="space-y-3 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 p-4">
      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
        Create Corrective Action Plan
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="md:col-span-2">
          <label className="text-xs text-gray-500 mb-1 block">Title *</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Implement supplier code-of-conduct sign-off process"
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>
        <div className="md:col-span-2">
          <label className="text-xs text-gray-500 mb-1 block">Description *</label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the remediation actions required…"
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400 resize-none"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Responsible party</label>
          <input
            value={responsible}
            onChange={(e) => setResponsible(e.target.value)}
            placeholder="e.g. Supplier Procurement Team"
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">Deadline</label>
          <input
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-400"
          />
        </div>
      </div>
      <div className="flex justify-end">
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !title.trim() || !description.trim()}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" />
          {mutation.isPending ? "Creating…" : "Create CAP"}
        </button>
      </div>
    </div>
  );
}

// ── Evidence submit form ──────────────────────────────────────────────────────

function EvidenceForm({ capId, onDone }: { capId: string; onDone: () => void }) {
  const [note, setNote] = useState("");
  const [url, setUrl] = useState("");
  const mutation = useMutation({
    mutationFn: () => capApi.submitEvidence(capId, { evidence_note: note, evidence_file_url: url || null }),
    onSuccess: onDone,
  });
  return (
    <div className="space-y-2 rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-900/20 p-3 mt-2">
      <p className="text-xs font-semibold text-violet-700 dark:text-violet-300">Submit Evidence</p>
      <textarea
        rows={2}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Describe the evidence uploaded (min. 10 chars)…"
        className="w-full rounded border border-violet-300 dark:border-violet-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-violet-400 resize-none"
      />
      <input
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Evidence file URL (optional)"
        className="w-full rounded border border-violet-300 dark:border-violet-700 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs focus:outline-none"
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || note.length < 10}
        className="rounded bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
      >
        {mutation.isPending ? "Submitting…" : "Submit Evidence"}
      </button>
    </div>
  );
}

// ── Verify / Insufficient forms ───────────────────────────────────────────────

function VerifyForm({ capId, onDone }: { capId: string; onDone: () => void }) {
  const [note, setNote] = useState("");
  const verify = useMutation({ mutationFn: () => capApi.verify(capId, note), onSuccess: onDone });
  const insufficient = useMutation({
    mutationFn: () => capApi.markInsufficient(capId, note),
    onSuccess: onDone,
  });
  return (
    <div className="space-y-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-3 mt-2">
      <p className="text-xs font-semibold text-gray-600 dark:text-gray-300">Analyst Verification</p>
      <textarea
        rows={2}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Verification note (min. 5 chars)…"
        className="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-xs focus:outline-none resize-none"
      />
      <div className="flex gap-2">
        <button
          onClick={() => verify.mutate()}
          disabled={verify.isPending || note.length < 5}
          className="flex items-center gap-1 rounded bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          <ThumbsUp className="h-3 w-3" />
          {verify.isPending ? "…" : "Evidence Sufficient"}
        </button>
        <button
          onClick={() => insufficient.mutate()}
          disabled={insufficient.isPending || note.length < 10}
          className="flex items-center gap-1 rounded border border-red-300 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          <ThumbsDown className="h-3 w-3" />
          {insufficient.isPending ? "…" : "Insufficient — request more"}
        </button>
      </div>
    </div>
  );
}

// ── CAP detail panel ──────────────────────────────────────────────────────────

function CAPDetail({ cap, onRefresh }: { cap: CAP; onRefresh: () => void }) {
  const qc = useQueryClient();
  const refresh = () => { qc.invalidateQueries({ queryKey: ["cap-by-finding"] }); onRefresh(); };

  const commitMut = useMutation({ mutationFn: () => capApi.commit(cap.id), onSuccess: refresh });
  const startMut  = useMutation({ mutationFn: () => capApi.start(cap.id),  onSuccess: refresh });
  const closeMut  = useMutation({ mutationFn: () => capApi.close(cap.id),  onSuccess: refresh });

  return (
    <div className="space-y-4">
      {/* Status trail */}
      <StatusTrail current={cap.cap_status} />

      {/* Overdue banner */}
      {cap.is_overdue && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 px-3 py-2">
          <AlertTriangle className="h-4 w-4 text-red-500 shrink-0" />
          <span className="text-xs font-semibold text-red-700">
            Overdue by {cap.overdue_days} day{cap.overdue_days !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Meta */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-400 font-medium mb-0.5">Responsible Party</p>
          <p className="text-gray-700 dark:text-gray-200">{cap.responsible_party || "—"}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 font-medium mb-0.5">Deadline</p>
          <p className={`font-medium ${cap.is_overdue ? "text-red-600" : "text-gray-700 dark:text-gray-200"}`}>
            {cap.deadline ? new Date(cap.deadline).toLocaleDateString("en-GB") : "—"}
          </p>
        </div>
        <div className="md:col-span-2">
          <p className="text-xs text-gray-400 font-medium mb-0.5">Description</p>
          <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">{cap.description}</p>
        </div>
      </div>

      {/* Evidence section */}
      {cap.evidence_note && (
        <div className="rounded-lg border border-violet-200 dark:border-violet-800 bg-violet-50 dark:bg-violet-900/10 p-3">
          <p className="text-xs font-semibold text-violet-700 dark:text-violet-400 mb-1">Evidence Submitted</p>
          <p className="text-xs text-gray-700 dark:text-gray-300">{cap.evidence_note}</p>
          {cap.evidence_file_url && (
            <a href={cap.evidence_file_url} target="_blank" rel="noopener noreferrer"
               className="text-xs text-indigo-500 hover:underline mt-1 block">
              View file ↗
            </a>
          )}
          {cap.evidence_submitted_at && (
            <p className="text-xs text-gray-400 mt-1">
              Submitted: {new Date(cap.evidence_submitted_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {/* Verification section */}
      {cap.verification_note && (
        <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/10 p-3">
          <p className="text-xs font-semibold text-emerald-700 mb-1">Analyst Verification</p>
          <p className="text-xs text-gray-700 dark:text-gray-300">{cap.verification_note}</p>
          {cap.verified_at && (
            <p className="text-xs text-gray-400 mt-1">
              Verified: {new Date(cap.verified_at).toLocaleString()}
            </p>
          )}
        </div>
      )}

      {cap.insufficient_reason && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 p-3">
          <p className="text-xs font-semibold text-red-700 mb-1">Evidence marked insufficient</p>
          <p className="text-xs text-gray-700 dark:text-gray-300">{cap.insufficient_reason}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2 pt-1">
        {cap.cap_status === "DRAFT" && (
          <button onClick={() => commitMut.mutate()} disabled={commitMut.isPending}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
            {commitMut.isPending ? "…" : "Commit to Plan"}
          </button>
        )}
        {cap.cap_status === "COMMITTED" && (
          <button onClick={() => startMut.mutate()} disabled={startMut.isPending}
            className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600 disabled:opacity-50">
            {startMut.isPending ? "…" : "Mark In Progress"}
          </button>
        )}
        {["VERIFIED", "IN_PROGRESS", "COMMITTED"].includes(cap.cap_status) && (
          <button onClick={() => closeMut.mutate()} disabled={closeMut.isPending}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50">
            {closeMut.isPending ? "…" : "Close CAP"}
          </button>
        )}
      </div>

      {/* Evidence submit form */}
      {["COMMITTED", "IN_PROGRESS"].includes(cap.cap_status) && (
        <EvidenceForm capId={cap.id} onDone={refresh} />
      )}

      {/* Verify form */}
      {cap.cap_status === "EVIDENCE_SUBMITTED" && (
        <VerifyForm capId={cap.id} onDone={refresh} />
      )}
    </div>
  );
}

// ── Public CAPTab component ───────────────────────────────────────────────────

export function CAPTab({ findingId }: { findingId: string }) {
  const qc = useQueryClient();

  const { data: cap, isLoading } = useQuery({
    queryKey: ["cap-by-finding", findingId],
    queryFn: () => capApi.getByFinding(findingId),
  });

  const refresh = () => qc.invalidateQueries({ queryKey: ["cap-by-finding", findingId] });

  if (isLoading) {
    return <div className="py-8 text-center text-sm text-gray-400">Loading…</div>;
  }

  if (!cap) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-gray-400 py-4">
          <FileCheck className="h-5 w-5" />
          <p className="text-sm">No Corrective Action Plan for this finding yet.</p>
        </div>
        <CreateCAPForm findingId={findingId} onCreated={refresh} />
      </div>
    );
  }

  return <CAPDetail cap={cap} onRefresh={refresh} />;
}
