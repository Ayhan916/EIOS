"use client";

import { useEffect, useState } from "react";
import { PortalAssessment, PortalQuestion, portalGetAssessment, portalSaveProgress, portalSubmit } from "@/lib/api/supplier-assessment";

const SECTION_LABELS: Record<string, string> = {
  company_structure: "A — Company Structure (Art. 7)",
  hr_policies: "B — Human Rights Policies (Art. 10 + Annex I)",
  environment: "C — Environmental Measures (Art. 10 + Annex II)",
  grievance: "D — Grievance Mechanism (Art. 14)",
  sub_suppliers: "E — Sub-supplier Cascade (Art. 10 Abs. 2 lit. b)",
};

function groupBySection(questions: PortalQuestion[]): Record<string, PortalQuestion[]> {
  return questions.reduce((acc, q) => {
    (acc[q.section] = acc[q.section] || []).push(q);
    return acc;
  }, {} as Record<string, PortalQuestion[]>);
}

function QuestionField({
  q,
  answer,
  onChange,
}: {
  q: PortalQuestion;
  answer: string;
  onChange: (val: string) => void;
}) {
  if (q.question_type === "yes_no") {
    return (
      <div className="flex gap-4">
        {["yes", "no"].map((opt) => (
          <label key={opt} className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name={q.id}
              value={opt}
              checked={answer === opt}
              onChange={() => onChange(opt)}
              className="accent-blue-600"
            />
            <span className="text-sm capitalize">{opt}</span>
          </label>
        ))}
      </div>
    );
  }
  if (q.question_type === "scale_1_5") {
    return (
      <div className="flex gap-3">
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="flex flex-col items-center gap-0.5 cursor-pointer">
            <input
              type="radio"
              name={q.id}
              value={String(n)}
              checked={answer === String(n)}
              onChange={() => onChange(String(n))}
              className="accent-blue-600"
            />
            <span className="text-xs text-gray-600">{n}</span>
          </label>
        ))}
        <span className="ml-2 text-xs text-gray-400 self-end">(1=none, 5=advanced)</span>
      </div>
    );
  }
  if (q.question_type === "multiple_choice" && q.options.length > 0) {
    return (
      <div className="flex flex-col gap-1">
        {q.options.map((opt) => (
          <label key={opt} className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name={q.id}
              value={opt}
              checked={answer === opt}
              onChange={() => onChange(opt)}
              className="accent-blue-600"
            />
            <span className="text-sm">{opt}</span>
          </label>
        ))}
      </div>
    );
  }
  return (
    <textarea
      value={answer}
      onChange={(e) => onChange(e.target.value)}
      rows={3}
      className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
      placeholder="Your answer…"
    />
  );
}

export default function SupplierAssessmentPortal({ params }: { params: Promise<{ token: string }> }) {
  const [token, setToken] = useState<string>("");

  useEffect(() => {
    Promise.resolve(params).then((p) => setToken(p.token));
  }, [params]);
  const [data, setData] = useState<PortalAssessment | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [refCode, setRefCode] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  useEffect(() => {
    if (!token) return;
    portalGetAssessment(token)
      .then((d) => {
        setData(d);
        const init: Record<string, string> = {};
        d.questions.forEach((q) => { if (q.saved_answer) init[q.id] = q.saved_answer; });
        setAnswers(init);
      })
      .catch((e) => setError(e?.response?.data?.detail ?? "Could not load assessment. The link may have expired."))
      .finally(() => setLoading(false));
  }, [token]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg("");
    try {
      await portalSaveProgress(token, answers);
      setSaveMsg("Progress saved.");
    } catch {
      setSaveMsg("Could not save — check your connection.");
    } finally {
      setSaving(false);
      setTimeout(() => setSaveMsg(""), 3000);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await portalSubmit(token, answers, email);
      setRefCode(res.reference_code);
      setSubmitted(true);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = Object.keys(answers).length;
  const requiredCount = data?.questions.filter((q) => q.is_required).length ?? 0;
  const requiredAnswered = data?.questions.filter((q) => q.is_required && answers[q.id]).length ?? 0;
  const canSubmit = requiredAnswered === requiredCount && requiredCount > 0 && email.includes("@");

  if (loading) return <div className="flex min-h-screen items-center justify-center"><p className="text-gray-500">Loading questionnaire…</p></div>;
  if (error) return <div className="flex min-h-screen items-center justify-center p-8"><div className="max-w-md rounded-lg border border-red-200 bg-red-50 p-6 text-center"><p className="text-red-800 font-medium">Unable to Load</p><p className="mt-2 text-sm text-red-600">{error}</p></div></div>;
  if (submitted) return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-8">
      <div className="max-w-md rounded-xl bg-white p-8 shadow-lg text-center">
        <div className="mb-4 text-4xl">✓</div>
        <h1 className="text-xl font-bold text-gray-900">Submitted Successfully</h1>
        <p className="mt-2 text-sm text-gray-600">Your self-assessment has been received. Please save your reference code for your records.</p>
        <div className="mt-4 rounded-lg bg-gray-100 px-4 py-3">
          <p className="text-xs text-gray-500">Reference Code</p>
          <p className="text-xl font-mono font-bold text-gray-900">{refCode}</p>
        </div>
        <p className="mt-4 text-xs text-gray-400">Thank you for participating in this CSDDD compliance self-assessment.</p>
      </div>
    </div>
  );

  const sections = groupBySection(data!.questions);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-2xl px-4">
        {/* Header */}
        <div className="mb-6 rounded-xl bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{data!.template_title}</h1>
              <p className="mt-1 text-sm text-gray-500">CSDDD Art. 10 Abs. 2 lit. a — Supplier Self-Assessment</p>
            </div>
            <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
              Ref: {data!.reference_code}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
            <span>Expires: {new Date(data!.expires_at).toLocaleDateString()}</span>
            <span>{answeredCount} / {data!.questions.length} answered</span>
            <span>{requiredAnswered} / {requiredCount} required answered</span>
          </div>
          <div className="mt-2 h-1.5 w-full rounded bg-gray-200">
            <div
              className="h-1.5 rounded bg-blue-600 transition-all"
              style={{ width: `${requiredCount ? (requiredAnswered / requiredCount) * 100 : 0}%` }}
            />
          </div>
        </div>

        {/* Questions by section */}
        {Object.entries(sections).map(([section, questions]) => (
          <div key={section} className="mb-4 rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wide text-gray-700">
              {SECTION_LABELS[section] ?? section}
            </h2>
            <div className="space-y-5">
              {questions.map((q, i) => (
                <div key={q.id}>
                  <label className="block text-sm font-medium text-gray-800">
                    {i + 1}. {q.question_text}
                    {q.is_required && <span className="ml-1 text-red-500">*</span>}
                    <span className="ml-2 text-xs font-normal text-gray-400">{q.csddd_article}</span>
                  </label>
                  <div className="mt-2">
                    <QuestionField
                      q={q}
                      answer={answers[q.id] ?? ""}
                      onChange={(v) => setAnswers((prev) => ({ ...prev, [q.id]: v }))}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Submit section */}
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-sm font-bold text-gray-700">Submit Assessment</h2>
          <div className="mb-3">
            <label className="block text-sm font-medium text-gray-700">Your email address *</label>
            <p className="mb-1 text-xs text-gray-400">Used for confirmation only — never shared publicly.</p>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              placeholder="your@email.com"
            />
          </div>
          <div className="mb-4 rounded bg-yellow-50 p-3 text-xs text-yellow-800">
            By submitting, you confirm that all answers are accurate and complete to the best of your knowledge.
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-40"
            >
              {saving ? "Saving…" : "Save Progress"}
            </button>
            {saveMsg && <span className="self-center text-xs text-green-600">{saveMsg}</span>}
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || submitting}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              {submitting ? "Submitting…" : "Submit Assessment"}
            </button>
          </div>
          {!canSubmit && requiredAnswered < requiredCount && (
            <p className="mt-2 text-xs text-gray-400">
              {requiredCount - requiredAnswered} required question{requiredCount - requiredAnswered > 1 ? "s" : ""} remaining.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
