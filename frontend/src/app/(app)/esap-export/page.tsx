"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n/context";
import {
  ESAPSubmission,
  ValidationChecklist,
  createSubmission,
  exportReport,
  listSubmissions,
  markReady,
  recordSubmission,
  validateReport,
} from "@/lib/api/esap-export";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  ready: "bg-blue-100 text-blue-800",
  submitted: "bg-green-100 text-green-800",
  archived: "bg-gray-100 text-gray-500",
};

export default function ESAPExportPage() {
  const { t } = useLanguage();
  const [tab, setTab] = useState<"taxonomy" | "export" | "validate" | "submissions">("validate");
  const [reportYear, setReportYear] = useState(2024);
  const [exportFmt, setExportFmt] = useState<"json" | "xml">("json");
  const [exportData, setExportData] = useState("");
  const [exportLoading, setExportLoading] = useState(false);

  const [validation, setValidation] = useState<ValidationChecklist | null>(null);
  const [validating, setValidating] = useState(false);

  const [submissions, setSubmissions] = useState<ESAPSubmission[]>([]);
  const [creating, setCreating] = useState(false);
  const [createNotes, setCreateNotes] = useState("");

  // Record dialog
  const [recordId, setRecordId] = useState<string | null>(null);
  const [recordBy, setRecordBy] = useState("");
  const [recordRef, setRecordRef] = useState("");

  const loadSubmissions = async () => {
    const s = await listSubmissions();
    setSubmissions(s);
  };

  useEffect(() => { loadSubmissions(); }, []);

  const handleValidate = async () => {
    setValidating(true);
    try {
      const r = await validateReport(reportYear);
      setValidation(r);
    } finally {
      setValidating(false);
    }
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const data = await exportReport(reportYear, exportFmt);
      setExportData(data);
    } finally {
      setExportLoading(false);
    }
  };

  const handleCreateSubmission = async () => {
    setCreating(true);
    try {
      await createSubmission(reportYear, exportFmt, createNotes);
      setCreateNotes("");
      loadSubmissions();
    } finally {
      setCreating(false);
    }
  };

  const handleMarkReady = async (id: string) => {
    await markReady(id);
    loadSubmissions();
  };

  const handleRecord = async () => {
    if (!recordId || !recordBy || !recordRef) return;
    await recordSubmission(recordId, recordBy, recordRef);
    setRecordId(null); setRecordBy(""); setRecordRef("");
    loadSubmissions();
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("esapExport.title")}</h1>
        <p className="mt-1 text-sm text-gray-500">{t("esapExport.subtitle")}</p>
      </div>

      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
        <strong>Note:</strong> {t("esapExport.note")}
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {(["validate", "export", "submissions", "taxonomy"] as const).map((tb) => (
          <button key={tb} onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-medium capitalize ${tab === tb ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"}`}>
            {tb === "validate" ? t("esapExport.tabValidate") : tb === "submissions" ? t("esapExport.tabSubmissions") : tb === "export" ? t("esapExport.tabExport") : t("esapExport.tabTaxonomy")}
          </button>
        ))}
      </div>

      {/* Validate Tab */}
      {tab === "validate" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium">Report Year</label>
            <input type="number" value={reportYear} onChange={(e) => setReportYear(+e.target.value)} min={2024} max={2040} className="w-28 rounded border px-2 py-1.5 text-sm" />
            <button onClick={handleValidate} disabled={validating} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-40">
              {validating ? t("esapExport.checking") : t("esapExport.runValidation")}
            </button>
          </div>
          {validation && (
            <div className="space-y-3">
              <div className={`rounded-lg p-3 ${validation.is_valid ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
                <p className={`font-medium ${validation.is_valid ? "text-green-800" : "text-red-800"}`}>
                  {validation.is_valid ? "✓ All Art. 16 required fields are present" : `✗ ${validation.missing_count} required field${validation.missing_count > 1 ? "s" : ""} missing`}
                </p>
                <p className="mt-1 text-xs text-gray-500">{validation.esap_note}</p>
              </div>
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>{["Field", "XBRL Concept", "Article", "Mandatory", "Status"].map(h => <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>)}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {validation.checklist.map((c) => (
                      <tr key={c.field} className="bg-white">
                        <td className="px-3 py-2 font-mono text-xs">{c.field}</td>
                        <td className="px-3 py-2 text-xs text-gray-600">{c.xbrl_concept}</td>
                        <td className="px-3 py-2 text-xs">{c.csddd_article}</td>
                        <td className="px-3 py-2">{c.mandatory ? <span className="text-red-600 text-xs">Required</span> : <span className="text-gray-400 text-xs">Optional</span>}</td>
                        <td className="px-3 py-2">
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c.status === "ok" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>{c.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Export Tab */}
      {tab === "export" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm font-medium">Report Year</label>
            <input type="number" value={reportYear} onChange={(e) => setReportYear(+e.target.value)} min={2024} max={2040} className="w-28 rounded border px-2 py-1.5 text-sm" />
            <select value={exportFmt} onChange={(e) => setExportFmt(e.target.value as "json" | "xml")} className="rounded border px-2 py-1.5 text-sm">
              <option value="json">JSON</option>
              <option value="xml">XML</option>
            </select>
            <button onClick={handleExport} disabled={exportLoading} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-40">
              {exportLoading ? t("esapExport.generating") : t("esapExport.generateExport")}
            </button>
          </div>
          {exportData && (
            <div>
              <div className="flex justify-end mb-1">
                <button onClick={() => navigator.clipboard.writeText(exportData)} className="rounded bg-gray-100 px-2 py-0.5 text-xs hover:bg-gray-200">{t("esapExport.copy")}</button>
              </div>
              <pre className="max-h-96 overflow-auto rounded-lg bg-gray-900 p-4 text-xs text-gray-100">{exportData}</pre>
              <button
                onClick={() => { const a = document.createElement("a"); a.href = `data:text/${exportFmt === "json" ? "json" : "xml"};charset=utf-8,${encodeURIComponent(exportData)}`; a.download = `csddd-esap-${reportYear}.${exportFmt}`; a.click(); }}
                className="mt-2 rounded bg-gray-100 px-3 py-1.5 text-sm hover:bg-gray-200"
              >
                Download .{exportFmt}
              </button>
            </div>
          )}
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium mb-2">Log a Submission Record</h3>
            <div className="flex gap-2 flex-wrap">
              <input value={createNotes} onChange={(e) => setCreateNotes(e.target.value)} placeholder="Notes (optional)" className="flex-1 rounded border px-2 py-1.5 text-sm" />
              <button onClick={handleCreateSubmission} disabled={creating} className="rounded bg-gray-800 px-3 py-1.5 text-sm text-white hover:bg-gray-900 disabled:opacity-40">
                {creating ? t("esapExport.creating") : t("esapExport.createRecord")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submissions Tab */}
      {tab === "submissions" && (
        <div className="space-y-3">
          {submissions.length === 0 ? <p className="text-sm text-gray-500">{t("esapExport.noSubmissions")}</p> : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>{["Year", "Format", "Status", "Submitted By", "Reference", "Actions"].map(h => <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {submissions.map(s => (
                    <tr key={s.id}>
                      <td className="px-3 py-2">{s.report_year}</td>
                      <td className="px-3 py-2 uppercase text-xs">{s.export_format}</td>
                      <td className="px-3 py-2"><span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLORS[s.status] ?? "bg-gray-100"}`}>{s.status}</span></td>
                      <td className="px-3 py-2 text-xs text-gray-500">{s.submitted_by ?? "—"}</td>
                      <td className="px-3 py-2 font-mono text-xs">{s.confirmation_reference ?? "—"}</td>
                      <td className="px-3 py-2 flex gap-1">
                        {s.status === "draft" && <button onClick={() => handleMarkReady(s.id)} className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-800 hover:bg-blue-200">{t("esapExport.markReady")}</button>}
                        {s.status === "ready" && <button onClick={() => setRecordId(s.id)} className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800 hover:bg-green-200">{t("esapExport.logSubmission")}</button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Taxonomy Tab */}
      {tab === "taxonomy" && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500 mb-3">ESAP/XBRL taxonomy mapping for CSDDD Art. 16 fields (schema version CSDDD-ESAP-2024-01). Subject to change until ESAP goes live ca. 2031.</p>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>{["EIOS Field", "XBRL Concept", "Article", "Type", "Mandatory"].map(h => <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  { field: "dd_policy_description", xbrl: "csddd:DueDiligencePolicyDescription", art: "Art. 16 lit. a", type: "text", mandatory: true },
                  { field: "risks_summary", xbrl: "csddd:AdverseImpactIdentified", art: "Art. 16 lit. b", type: "structured_list", mandatory: true },
                  { field: "actions_summary", xbrl: "csddd:PreventionMeasuresTaken", art: "Art. 16 lit. c", type: "structured_list", mandatory: true },
                  { field: "board_approvals", xbrl: "csddd:ManagementBodyOversight", art: "Art. 22 + Art. 16 lit. d", type: "structured_list", mandatory: true },
                  { field: "effectiveness_summary", xbrl: "csddd:EffectivenessAssessment", art: "Art. 16 lit. e", type: "text", mandatory: true },
                  { field: "stakeholder_consultation", xbrl: "csddd:StakeholderConsultationDescription", art: "Art. 13 + Art. 16 lit. f", type: "text", mandatory: false },
                ].map(r => (
                  <tr key={r.field} className="bg-white">
                    <td className="px-3 py-2 font-mono text-xs">{r.field}</td>
                    <td className="px-3 py-2 text-xs text-gray-600">{r.xbrl}</td>
                    <td className="px-3 py-2 text-xs">{r.art}</td>
                    <td className="px-3 py-2 text-xs text-gray-500">{r.type}</td>
                    <td className="px-3 py-2">{r.mandatory ? <span className="text-red-600 text-xs font-medium">Required</span> : <span className="text-gray-400 text-xs">Optional</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Record Submission Dialog */}
      {recordId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-3">
            <h2 className="font-semibold text-gray-900">Record ESAP Submission</h2>
            <p className="text-xs text-gray-500">Since direct ESAP API upload is not yet available, record the submission manually after uploading on ESAP portal.</p>
            <div><label className="block text-sm font-medium">Submitted By *</label><input value={recordBy} onChange={(e) => setRecordBy(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
            <div><label className="block text-sm font-medium">ESAP Confirmation Reference *</label><input value={recordRef} onChange={(e) => setRecordRef(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setRecordId(null)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleRecord} disabled={!recordBy || !recordRef} className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-40">Record</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
