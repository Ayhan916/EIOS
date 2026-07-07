"use client";

import { useEffect, useState } from "react";
import {
  AssessmentTemplate,
  GapReport,
  SupplierAssessment,
  createAssessment,
  getGapReport,
  listAssessments,
  listTemplates,
  seedDefaultTemplate,
} from "@/lib/api/supplier-assessment";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  sent: "bg-blue-100 text-blue-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  submitted: "bg-green-100 text-green-800",
  expired: "bg-gray-100 text-gray-600",
  archived: "bg-gray-100 text-gray-500",
  draft: "bg-gray-100 text-gray-600",
};

const TL_COLORS: Record<string, string> = {
  green: "text-green-700 bg-green-100",
  yellow: "text-yellow-700 bg-yellow-100",
  red: "text-red-700 bg-red-100",
};

const TL_ICONS: Record<string, string> = { green: "●", yellow: "●", red: "●" };

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function TrafficLight({ tl }: { tl: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TL_COLORS[tl] ?? ""}`}>
      {TL_ICONS[tl]} {tl}
    </span>
  );
}

export default function SupplierAssessmentsPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<"assessments" | "templates" | "gap">("assessments");
  const [templates, setTemplates] = useState<AssessmentTemplate[]>([]);
  const [assessments, setAssessments] = useState<SupplierAssessment[]>([]);
  const [filterStatus, setFilterStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);

  // Create assessment dialog
  const [showCreate, setShowCreate] = useState(false);
  const [createTemplateId, setCreateTemplateId] = useState("");
  const [createSupplierId, setCreateSupplierId] = useState("");
  const [createdLink, setCreatedLink] = useState<string | null>(null);

  // Gap report
  const [gapAssessmentId, setGapAssessmentId] = useState("");
  const [gapReport, setGapReport] = useState<GapReport | null>(null);
  const [gapLoading, setGapLoading] = useState(false);
  const [gapError, setGapError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [tmpl, asmt] = await Promise.all([
        listTemplates(),
        listAssessments(filterStatus || undefined),
      ]);
      setTemplates(tmpl);
      setAssessments(asmt);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seedDefaultTemplate();
      await load();
    } finally {
      setSeeding(false);
    }
  };

  const handleCreate = async () => {
    if (!createTemplateId || !createSupplierId) return;
    const result = await createAssessment(createTemplateId, createSupplierId);
    setCreatedLink(result.portal_link ?? null);
    setCreateTemplateId("");
    setCreateSupplierId("");
    load();
  };

  const handleGapReport = async () => {
    if (!gapAssessmentId) return;
    setGapLoading(true);
    setGapError("");
    setGapReport(null);
    try {
      const r = await getGapReport(gapAssessmentId);
      setGapReport(r);
    } catch (e: any) {
      setGapError(e?.response?.data?.detail ?? "Error loading gap report");
    } finally {
      setGapLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("supplierAssessments.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("supplierAssessments.subtitle")}</p>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {(["assessments", "templates", "gap"] as const).map((tb) => (
          <button
            key={tb}
            onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-medium capitalize ${
              tab === tb ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tb === "gap" ? t("supplierAssessments.tabGap") : tb === "assessments" ? t("supplierAssessments.tabAssessments") : t("supplierAssessments.tabTemplates")}
          </button>
        ))}
      </div>

      {/* Assessments Tab */}
      {tab === "assessments" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="">All Statuses</option>
              {["sent", "in_progress", "submitted", "expired", "archived"].map((s) => (
                <option key={s} value={s}>{s.replace("_", " ")}</option>
              ))}
            </select>
            <button
              onClick={() => setShowCreate(true)}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              + Send Assessment
            </button>
          </div>

          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : assessments.length === 0 ? (
            <p className="text-sm text-gray-500">No assessments found. Send your first one above.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["Supplier ID", "Status", "Reference", "Expires", "Submitted", "Actions"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {assessments.map((a) => (
                    <tr key={a.id} className="bg-white hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{a.supplier_id.slice(0, 8)}…</td>
                      <td className="px-4 py-2"><StatusBadge status={a.status} /></td>
                      <td className="px-4 py-2 font-mono text-xs">{a.reference_code}</td>
                      <td className="px-4 py-2 text-gray-500 text-xs">{new Date(a.token_expires_at).toLocaleDateString()}</td>
                      <td className="px-4 py-2 text-gray-500 text-xs">
                        {a.submitted_at ? new Date(a.submitted_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {a.status === "submitted" && (
                          <button
                            onClick={() => { setGapAssessmentId(a.id); setTab("gap"); }}
                            className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-800 hover:bg-purple-200"
                          >
                            Gap Report
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Templates Tab */}
      {tab === "templates" && (
        <div className="space-y-4">
          {templates.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
              <p className="text-sm text-gray-500 mb-3">No templates yet. Seed the standard CSDDD 25-question template to get started.</p>
              <button
                onClick={handleSeed}
                disabled={seeding}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-40"
              >
                {seeding ? "Creating…" : "Create CSDDD Standard Template (25 questions)"}
              </button>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {templates.map((t) => (
                <div key={t.id} className="rounded-lg border border-gray-200 bg-white p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{t.title}</p>
                      <p className="mt-1 text-xs text-gray-500">{t.description.slice(0, 100)}{t.description.length > 100 ? "…" : ""}</p>
                    </div>
                    {t.is_default && (
                      <span className="rounded bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700">Default</span>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
                    <span>{t.question_count} questions</span>
                    <span>Created {new Date(t.created_at).toLocaleDateString()}</span>
                  </div>
                  <button
                    onClick={() => { setCreateTemplateId(t.id); setShowCreate(true); setTab("assessments"); }}
                    className="mt-3 rounded bg-gray-100 px-3 py-1.5 text-xs hover:bg-gray-200"
                  >
                    Send to Supplier →
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Gap Analysis Tab */}
      {tab === "gap" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              value={gapAssessmentId}
              onChange={(e) => setGapAssessmentId(e.target.value)}
              placeholder="Assessment ID"
              className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm"
            />
            <button
              onClick={handleGapReport}
              disabled={!gapAssessmentId || gapLoading}
              className="rounded bg-purple-600 px-4 py-1.5 text-sm text-white hover:bg-purple-700 disabled:opacity-40"
            >
              {gapLoading ? "Loading…" : "Load Gap Report"}
            </button>
          </div>

          {gapError && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{gapError}</p>}

          {gapReport && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">Gap Report</h3>
                <TrafficLight tl={gapReport.overall_traffic_light} />
                <span className="text-sm text-gray-500">{gapReport.total_gaps} gaps · {gapReport.critical_gaps} critical</span>
              </div>

              {/* Section scores */}
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {gapReport.section_scores.map((s) => (
                  <div key={s.section} className="rounded-lg border border-gray-200 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium capitalize">{s.section.replace("_", " ")}</p>
                      <TrafficLight tl={s.traffic_light} />
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {s.answered}/{s.total_questions} answered · {s.gaps} gaps
                    </p>
                  </div>
                ))}
              </div>

              {/* Gaps list */}
              {gapReport.gaps.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900">Identified Gaps</h4>
                  {gapReport.gaps.map((g, i) => (
                    <div key={i} className="rounded-lg border border-gray-200 bg-white p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium">{g.question_text}</p>
                        <span className={`shrink-0 rounded px-1.5 py-0.5 text-xs font-medium ${
                          g.severity === "critical" ? "bg-red-100 text-red-800" :
                          g.severity === "high" ? "bg-orange-100 text-orange-800" :
                          g.severity === "medium" ? "bg-yellow-100 text-yellow-800" :
                          "bg-gray-100 text-gray-600"
                        }`}>{g.severity}</span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        <span className="font-medium">{g.csddd_article}</span> · Answered: "{g.answer_given}" · Expected: "{g.expected_answer}"
                      </p>
                      <p className="mt-1.5 rounded bg-blue-50 px-2 py-1 text-xs text-blue-800">
                        → {g.recommendation}
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {gapReport.gaps.length === 0 && (
                <div className="rounded-lg bg-green-50 p-4 text-center text-sm text-green-800">
                  ✓ No gaps identified — supplier meets all assessed CSDDD requirements.
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Create Assessment Dialog */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold">Send Assessment to Supplier</h2>

            {createdLink ? (
              <div className="space-y-3">
                <p className="text-sm text-green-800 bg-green-50 rounded p-3">Assessment created. Share this portal link with your supplier:</p>
                <div className="rounded border bg-gray-50 p-2 font-mono text-xs break-all">{window.location.origin}{createdLink}</div>
                <p className="text-xs text-gray-500">Link valid for 30 days. The supplier does not need an EIOS account.</p>
                <button onClick={() => { setCreatedLink(null); setShowCreate(false); }} className="w-full rounded bg-blue-600 py-2 text-sm text-white hover:bg-blue-700">Done</button>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium">Template</label>
                  <select
                    value={createTemplateId}
                    onChange={(e) => setCreateTemplateId(e.target.value)}
                    className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
                  >
                    <option value="">Select template…</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>{t.title}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium">Supplier ID *</label>
                  <input
                    value={createSupplierId}
                    onChange={(e) => setCreateSupplierId(e.target.value)}
                    placeholder="UUID of supplier"
                    className="mt-1 w-full rounded border px-2 py-1.5 text-sm"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button onClick={() => setShowCreate(false)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
                  <button
                    onClick={handleCreate}
                    disabled={!createTemplateId || !createSupplierId}
                    className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-40"
                  >
                    Create & Get Link
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
