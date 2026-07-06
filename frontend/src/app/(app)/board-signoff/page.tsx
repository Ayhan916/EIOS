"use client";

import { useEffect, useState } from "react";
import {
  BoardDashboard,
  BoardDecision,
  BoardSignoffRequest,
  CreateSignoffRequest,
  approveRequest,
  createBoardRequest,
  getBoardDashboard,
  getDecisions,
  listBoardRequests,
  rejectRequest,
  withdrawRequest,
} from "@/lib/api/board-signoff";
const SIGNOFF_TYPES = [
  { value: "dd_policy", label: "DD Policy" },
  { value: "dd_strategy", label: "DD Strategy" },
  { value: "annual_report", label: "Annual Report" },
  { value: "scoping_study", label: "Scoping Study" },
  { value: "cap_plan", label: "CAP Plan" },
  { value: "remedy_settlement", label: "Remedy Settlement" },
  { value: "other", label: "Other" },
];

const ROLES = [
  { value: "ceo", label: "CEO" },
  { value: "cfo", label: "CFO" },
  { value: "cso", label: "CSO" },
  { value: "board_member", label: "Board Member" },
  { value: "supervisory_board", label: "Supervisory Board" },
  { value: "compliance_officer", label: "Compliance Officer" },
  { value: "other", label: "Other" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-700",
};

function KPICard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export default function BoardSignoffPage() {
  const [tab, setTab] = useState<"dashboard" | "requests" | "create">("dashboard");
  const [dashboard, setDashboard] = useState<BoardDashboard | null>(null);
  const [requests, setRequests] = useState<BoardSignoffRequest[]>([]);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterType, setFilterType] = useState("");
  const [loading, setLoading] = useState(false);

  // Decision panel
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<BoardDecision[]>([]);
  const [showDecisions, setShowDecisions] = useState(false);

  // Approve/Reject dialogs
  const [showApprove, setShowApprove] = useState<string | null>(null);
  const [showReject, setShowReject] = useState<string | null>(null);
  const [approveBy, setApproveBy] = useState("");
  const [approveRole, setApproveRole] = useState("board_member");
  const [approveComment, setApproveComment] = useState("");
  const [rejectBy, setRejectBy] = useState("");
  const [rejectRole, setRejectRole] = useState("board_member");
  const [rejectReason, setRejectReason] = useState("");

  // Create form
  const [form, setForm] = useState<CreateSignoffRequest>({
    title: "",
    signoff_type: "other",
    description: "",
    document_ref: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const [dash, reqs] = await Promise.all([
        getBoardDashboard(),
        listBoardRequests({ status: filterStatus || undefined, signoff_type: filterType || undefined }),
      ]);
      setDashboard(dash);
      setRequests(reqs);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus, filterType]);

  const handleCreate = async () => {
    if (!form.title) return;
    await createBoardRequest(form);
    setForm({ title: "", signoff_type: "other", description: "", document_ref: "" });
    setTab("requests");
    load();
  };

  const handleApprove = async () => {
    if (!showApprove || !approveBy) return;
    await approveRequest(showApprove, { approved_by: approveBy, approved_by_role: approveRole, comment: approveComment || undefined });
    setShowApprove(null);
    setApproveBy(""); setApproveComment("");
    load();
  };

  const handleReject = async () => {
    if (!showReject || !rejectBy || !rejectReason) return;
    await rejectRequest(showReject, { rejected_by: rejectBy, rejected_by_role: rejectRole, reason: rejectReason });
    setShowReject(null);
    setRejectBy(""); setRejectReason("");
    load();
  };

  const handleWithdraw = async (id: string) => {
    if (!confirm("Withdraw this request?")) return;
    await withdrawRequest(id);
    load();
  };

  const openDecisions = async (id: string) => {
    setSelectedId(id);
    const d = await getDecisions(id);
    setDecisions(d);
    setShowDecisions(true);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Board Sign-off Trail (Art. 22)</h1>
        <p className="mt-1 text-sm text-gray-500">CSDDD Art. 22 — Board-Level Due Diligence Oversight</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(["dashboard", "requests", "create"] as const).map((tb) => (
          <button
            key={tb}
            onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-medium capitalize ${
              tab === tb ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tb === "dashboard" ? "Dashboard" : tb === "requests" ? "Requests" : "New Request"}
          </button>
        ))}
      </div>

      {/* Dashboard Tab */}
      {tab === "dashboard" && dashboard && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <KPICard label="Total" value={dashboard.total} />
            <KPICard label="Pending" value={dashboard.pending} />
            <KPICard label="Approved" value={dashboard.approved} />
            <KPICard label="Rejected" value={dashboard.rejected} />
            <KPICard label="Overdue" value={dashboard.overdue} sub="past due date" />
            <KPICard label="Approval Rate" value={`${dashboard.approval_rate_pct}%`} />
          </div>

          {dashboard.overdue > 0 && (
            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
              <p className="font-medium text-orange-800">
                ⚠ {dashboard.overdue} request{dashboard.overdue > 1 ? "s" : ""} past their due date. Board action required per CSDDD Art. 22.
              </p>
            </div>
          )}

          <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
            <strong>Art. 22 Note:</strong> Board members must personally approve or reject sign-off requests. AI agents are strictly prohibited from performing approvals or rejections.
          </div>
        </div>
      )}

      {/* Requests Tab */}
      {tab === "requests" && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="">All Statuses</option>
              {["pending", "approved", "rejected", "withdrawn"].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="">All Types</option>
              {SIGNOFF_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          {loading ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : requests.length === 0 ? (
            <p className="text-sm text-gray-500">No sign-off requests found.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {["Title", "Type", "Status", "Requested By", "Due Date", "Actions"].map((h) => (
                      <th key={h} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {requests.map((r) => (
                    <tr key={r.id} className="bg-white hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium">{r.title}</td>
                      <td className="px-4 py-2 text-gray-600">{r.signoff_type}</td>
                      <td className="px-4 py-2"><StatusBadge status={r.status} /></td>
                      <td className="px-4 py-2 text-gray-600">{r.requested_by}</td>
                      <td className="px-4 py-2 text-gray-600">
                        {r.due_date ? new Date(r.due_date).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1">
                          <button
                            onClick={() => openDecisions(r.id)}
                            className="rounded bg-gray-100 px-2 py-0.5 text-xs hover:bg-gray-200"
                          >
                            History
                          </button>
                          {r.status === "pending" && (
                            <>
                              <button
                                onClick={() => setShowApprove(r.id)}
                                className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800 hover:bg-green-200"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => setShowReject(r.id)}
                                className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-800 hover:bg-red-200"
                              >
                                Reject
                              </button>
                              <button
                                onClick={() => handleWithdraw(r.id)}
                                className="rounded bg-gray-100 px-2 py-0.5 text-xs hover:bg-gray-200"
                              >
                                Withdraw
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create Tab */}
      {tab === "create" && (
        <div className="max-w-xl space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Title *</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. Annual DD Report Board Approval 2025"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Type</label>
            <select
              value={form.signoff_type}
              onChange={(e) => setForm({ ...form, signoff_type: e.target.value })}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
            >
              {SIGNOFF_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={4}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Document Reference (URL or ID)</label>
            <input
              value={form.document_ref ?? ""}
              onChange={(e) => setForm({ ...form, document_ref: e.target.value })}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              placeholder="e.g. confluence/page/12345"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!form.title}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Create Request
          </button>
        </div>
      )}

      {/* Decisions Drawer */}
      {showDecisions && (
        <div className="fixed inset-0 z-50 flex items-end justify-end bg-black/30">
          <div className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Decision Audit Trail</h2>
              <button onClick={() => setShowDecisions(false)} className="text-gray-400 hover:text-gray-700">✕</button>
            </div>
            {decisions.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">No decisions recorded yet.</p>
            ) : (
              <ul className="mt-4 space-y-3">
                {decisions.map((d) => (
                  <li key={d.id} className="rounded-lg border p-3">
                    <div className="flex items-center justify-between">
                      <StatusBadge status={d.decision} />
                      <span className="text-xs text-gray-400">{new Date(d.decided_at).toLocaleString()}</span>
                    </div>
                    <p className="mt-1 text-sm font-medium">{d.decided_by} <span className="font-normal text-gray-500">({d.decided_by_role})</span></p>
                    {d.comment && <p className="mt-1 text-xs text-gray-600">{d.comment}</p>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Approve Dialog */}
      {showApprove && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-green-800">Approve — Board Sign-off</h2>
            <p className="mb-4 rounded bg-yellow-50 p-3 text-xs text-yellow-800">
              This action records formal board approval per CSDDD Art. 22 Abs. 1. Only an authorized human board member or admin may perform this action.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium">Your Name *</label>
                <input value={approveBy} onChange={(e) => setApproveBy(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium">Role</label>
                <select value={approveRole} onChange={(e) => setApproveRole(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm">
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium">Comment (optional)</label>
                <textarea value={approveComment} onChange={(e) => setApproveComment(e.target.value)} rows={3} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowApprove(null)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleApprove} disabled={!approveBy} className="rounded bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-40">Confirm Approval</button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showReject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-red-800">Reject — Board Sign-off</h2>
            <p className="mb-4 rounded bg-yellow-50 p-3 text-xs text-yellow-800">
              Only an authorized human board member or admin may reject sign-off requests (Art. 22).
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium">Your Name *</label>
                <input value={rejectBy} onChange={(e) => setRejectBy(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium">Role</label>
                <select value={rejectRole} onChange={(e) => setRejectRole(e.target.value)} className="mt-1 w-full rounded border px-2 py-1.5 text-sm">
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium">Reason *</label>
                <textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} rows={3} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowReject(null)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleReject} disabled={!rejectBy || !rejectReason} className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-40">Confirm Rejection</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
