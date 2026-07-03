"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Search, Shield } from "lucide-react";
import {
  submitGrievance,
  checkGrievanceStatus,
  type GrievanceSubmitResponse,
  type GrievanceStatusCheckResponse,
} from "@/lib/api/grievance";

const CATEGORIES = [
  { value: "labour_rights", label: "Labour Rights Violation" },
  { value: "child_labour", label: "Child Labour" },
  { value: "forced_labour", label: "Forced or Compulsory Labour" },
  { value: "health_and_safety", label: "Health & Safety Violation" },
  { value: "environmental", label: "Environmental Damage" },
  { value: "discrimination", label: "Discrimination or Harassment" },
  { value: "corruption", label: "Corruption or Bribery" },
  { value: "human_rights", label: "Other Human Rights Violation" },
  { value: "other", label: "Other" },
];

const STATUS_LABELS: Record<string, string> = {
  received: "Received — your report is in our system",
  under_review: "Under Review — a compliance officer is reviewing your report",
  investigating: "Under Investigation — a formal investigation has been opened",
  resolved: "Resolved — this matter has been concluded",
  rejected: "Closed — this report was reviewed and closed without further action",
};

export default function GrievancePage() {
  const searchParams = useSearchParams();
  const orgId = searchParams.get("org_id") ?? "";

  const [mode, setMode] = useState<"submit" | "check" | "done">("submit");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [submitResult, setSubmitResult] = useState<GrievanceSubmitResponse | null>(null);
  const [statusResult, setStatusResult] = useState<GrievanceStatusCheckResponse | null>(null);
  const [checkCode, setCheckCode] = useState("");
  const [checking, setChecking] = useState(false);

  // Form state
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "other",
    submitted_by_email: "",
    submitted_by_name: "",
    wantContact: false,
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!orgId) {
      setError("Missing organisation ID in URL. Please use the link provided by your contact.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await submitGrievance({
        organization_id: orgId,
        title: form.title,
        description: form.description,
        category: form.category,
        submitted_by_email: form.wantContact ? form.submitted_by_email || undefined : undefined,
        submitted_by_name: form.wantContact ? form.submitted_by_name || undefined : undefined,
      });
      setSubmitResult(result);
      setMode("done");
    } catch {
      setError("Submission failed. Please try again or contact your compliance office directly.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCheck(e: React.FormEvent) {
    e.preventDefault();
    if (!checkCode.trim()) return;
    setChecking(true);
    setError("");
    setStatusResult(null);
    try {
      const result = await checkGrievanceStatus(checkCode.trim().toUpperCase());
      setStatusResult(result);
    } catch {
      setError("Reference code not found. Please check the code and try again.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="w-full max-w-xl">
      {/* Header */}
      <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-3">
          <Shield className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="text-sm text-amber-800">
            <p className="font-semibold">Confidential Grievance Channel</p>
            <p className="mt-1">
              This channel is available to workers, trade union representatives, local
              communities, and any affected person. All submissions are treated confidentially.
              Your identity will not be disclosed to the subject of the report without your
              explicit consent.
            </p>
            <p className="mt-1 text-xs">
              Operated in accordance with LkSG §8 and CSDDD Art. 14.
            </p>
          </div>
        </div>
      </div>

      {/* Mode switcher */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => { setMode("submit"); setError(""); setStatusResult(null); }}
          className={`flex-1 rounded-lg border py-2 text-sm font-medium transition-colors ${
            mode === "submit" || mode === "done"
              ? "border-blue-600 bg-blue-600 text-white"
              : "border-border bg-background text-muted-foreground hover:bg-muted"
          }`}
        >
          Submit a Report
        </button>
        <button
          onClick={() => { setMode("check"); setError(""); }}
          className={`flex-1 rounded-lg border py-2 text-sm font-medium transition-colors ${
            mode === "check"
              ? "border-blue-600 bg-blue-600 text-white"
              : "border-border bg-background text-muted-foreground hover:bg-muted"
          }`}
        >
          Check Status
        </button>
      </div>

      {/* ── Done state ── */}
      {mode === "done" && submitResult && (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-6 text-center">
          <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-600" />
          <h2 className="text-lg font-bold text-emerald-900">Report Received</h2>
          <p className="mt-2 text-sm text-emerald-800">{submitResult.message}</p>
          <div className="mt-4 rounded-lg border border-emerald-300 bg-white px-6 py-3 text-center">
            <p className="text-xs font-medium text-muted-foreground">Your Reference Code</p>
            <p className="mt-1 text-2xl font-mono font-bold tracking-wider text-slate-900">
              {submitResult.reference_code}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Save this code — you can use it to check the status of your report.
            </p>
          </div>
          <button
            onClick={() => { setMode("submit"); setSubmitResult(null); setForm({ title: "", description: "", category: "other", submitted_by_email: "", submitted_by_name: "", wantContact: false }); }}
            className="mt-4 text-sm text-blue-600 hover:underline"
          >
            Submit another report
          </button>
        </div>
      )}

      {/* ── Submit form ── */}
      {mode === "submit" && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Category *</label>
            <select
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Subject / Title *</label>
            <input
              type="text"
              required
              minLength={5}
              maxLength={500}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              placeholder="Brief description of the issue"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Description *</label>
            <textarea
              required
              minLength={20}
              maxLength={10000}
              rows={6}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              placeholder="Please describe the issue in detail: what happened, where, when, who was involved, and any other relevant information."
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
            <p className="mt-0.5 text-xs text-muted-foreground">
              {form.description.length} / 10 000 characters
            </p>
          </div>

          {/* Optional contact */}
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.wantContact}
                onChange={(e) => setForm((f) => ({ ...f, wantContact: e.target.checked }))}
                className="h-4 w-4"
              />
              <span className="font-medium">I am willing to be contacted (optional)</span>
            </label>
            <p className="mt-1 text-xs text-muted-foreground">
              Your contact details will be stored confidentially and only used to keep you
              informed — they will never be disclosed to the subject of this report.
            </p>
            {form.wantContact && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium">Name (optional)</label>
                  <input
                    type="text"
                    maxLength={255}
                    className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
                    placeholder="Your name"
                    value={form.submitted_by_name}
                    onChange={(e) => setForm((f) => ({ ...f, submitted_by_name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium">Email (optional)</label>
                  <input
                    type="email"
                    maxLength={320}
                    className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm"
                    placeholder="your@email.com"
                    value={form.submitted_by_email}
                    onChange={(e) => setForm((f) => ({ ...f, submitted_by_email: e.target.value }))}
                  />
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Submitting…" : "Submit Report Confidentially"}
          </button>

          <p className="text-center text-xs text-muted-foreground">
            Submissions are encrypted and stored securely. You can submit anonymously.
          </p>
        </form>
      )}

      {/* ── Status check ── */}
      {mode === "check" && (
        <div className="space-y-4">
          <form onSubmit={handleCheck} className="flex gap-2">
            <input
              type="text"
              placeholder="GR-XXXXXXXXXX"
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
              value={checkCode}
              onChange={(e) => setCheckCode(e.target.value)}
            />
            <button
              type="submit"
              disabled={checking || !checkCode.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Search className="h-4 w-4" />
              {checking ? "Checking…" : "Check"}
            </button>
          </form>

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {statusResult && (
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm text-muted-foreground">
                  {statusResult.reference_code}
                </span>
                <span className="rounded-full bg-blue-100 px-3 py-0.5 text-xs font-semibold text-blue-800">
                  {statusResult.status.replace("_", " ").toUpperCase()}
                </span>
              </div>
              <p className="mt-3 text-sm">
                {STATUS_LABELS[statusResult.status] ?? statusResult.status}
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div>
                  <span className="font-medium">Category: </span>
                  {statusResult.category.replace(/_/g, " ")}
                </div>
                <div>
                  <span className="font-medium">Submitted: </span>
                  {new Date(statusResult.submitted_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
