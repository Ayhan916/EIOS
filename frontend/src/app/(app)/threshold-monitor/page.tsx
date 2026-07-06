"use client";

import { useEffect, useState } from "react";
import {
  CompanyProfile,
  ProfileUpsert,
  ThresholdInfo,
  ThresholdStatus,
  getThresholdInfo,
  getThresholdStatus,
  listProfiles,
  upsertProfile,
} from "@/lib/api/threshold-monitor";

const LEVEL_COLORS: Record<string, string> = {
  not_applicable: "bg-gray-100 text-gray-600",
  borderline: "bg-yellow-100 text-yellow-800",
  tier_2: "bg-orange-100 text-orange-800",
  tier_1: "bg-red-100 text-red-800",
};

const LEVEL_LABELS: Record<string, string> = {
  not_applicable: "Not yet subject to CSDDD",
  borderline: "Borderline — monitor closely",
  tier_2: "CSDDD Tier 2 (from 2028)",
  tier_1: "CSDDD Tier 1 (from 2027)",
};

function CheckIcon({ met }: { met: boolean }) {
  return <span className={`text-sm ${met ? "text-green-600" : "text-gray-400"}`}>{met ? "✓" : "✗"}</span>;
}

export default function ThresholdMonitorPage() {
  const [tab, setTab] = useState<"status" | "profiles" | "info">("status");
  const [status, setStatus] = useState<ThresholdStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [profiles, setProfiles] = useState<CompanyProfile[]>([]);
  const [info, setInfo] = useState<ThresholdInfo | null>(null);
  const [loading, setLoading] = useState(false);

  // Form
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProfileUpsert>({ fiscal_year: 2024, employee_count_worldwide: 0, net_revenue_eur_millions: 0, headquarters_country: "DE", sector: "", non_eu_company: false, notes: "" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [p, i] = await Promise.all([listProfiles(), getThresholdInfo()]);
      setProfiles(p);
      setInfo(i);
      if (p.length > 0) {
        try {
          const s = await getThresholdStatus();
          setStatus(s);
          setStatusError("");
        } catch (e: any) {
          setStatusError(e?.response?.data?.detail ?? "No profile yet");
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await upsertProfile(form);
      setShowForm(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">CSDDD Threshold Monitor</h1>
        <p className="mt-1 text-sm text-gray-500">Art. 2 — Scope: Tier 1 (≥5,000 MA + ≥€1.5B, from 2027) · Tier 2 (≥1,000 MA + ≥€450M, from 2028)</p>
      </div>

      <div className="flex gap-2 border-b border-gray-200">
        {(["status", "profiles", "info"] as const).map((tb) => (
          <button key={tb} onClick={() => setTab(tb)}
            className={`px-4 py-2 text-sm font-medium capitalize ${tab === tb ? "border-b-2 border-blue-600 text-blue-600" : "text-gray-500 hover:text-gray-700"}`}>
            {tb === "status" ? "Current Status" : tb === "profiles" ? "Company Profiles" : "Reference Info"}
          </button>
        ))}
      </div>

      {/* Status Tab */}
      {tab === "status" && (
        <div className="space-y-4">
          {loading && <p className="text-sm text-gray-500">Loading…</p>}
          {statusError && !loading && (
            <div className="rounded-lg border border-dashed border-gray-300 p-6 text-center">
              <p className="text-sm text-gray-500 mb-3">No company profile found. Add your first profile to see your CSDDD threshold status.</p>
              <button onClick={() => setTab("profiles")} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700">Add Profile →</button>
            </div>
          )}
          {status && (
            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <div className="flex items-center gap-3 mb-4">
                  <span className={`rounded-full px-3 py-1 text-sm font-bold ${LEVEL_COLORS[status.level] ?? "bg-gray-100"}`}>
                    {LEVEL_LABELS[status.level] ?? status.level}
                  </span>
                  <span className="text-sm text-gray-500">FY {status.fiscal_year}</span>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div><p className="text-xs text-gray-500">Employees Worldwide</p><p className="text-xl font-bold">{status.employee_count.toLocaleString()}</p></div>
                  <div><p className="text-xs text-gray-500">Net Revenue (€M)</p><p className="text-xl font-bold">{status.net_revenue_eur_millions.toLocaleString()}</p></div>
                </div>
                <div className="grid grid-cols-2 gap-4 border-t pt-4">
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-2">Tier 1 (deadline {status.tier1.deadline})</p>
                    <p className="text-xs text-gray-500"><CheckIcon met={status.tier1.employee_met} /> ≥5,000 employees</p>
                    <p className="text-xs text-gray-500"><CheckIcon met={status.tier1.revenue_met} /> ≥€1,500M revenue</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-2">Tier 2 (deadline {status.tier2.deadline})</p>
                    <p className="text-xs text-gray-500"><CheckIcon met={status.tier2.employee_met} /> ≥1,000 employees</p>
                    <p className="text-xs text-gray-500"><CheckIcon met={status.tier2.revenue_met} /> ≥€450M revenue</p>
                  </div>
                </div>
              </div>
              <div className={`rounded-lg p-4 ${status.is_borderline ? "bg-yellow-50 border border-yellow-200" : status.level !== "not_applicable" ? "bg-orange-50 border border-orange-200" : "bg-blue-50 border border-blue-100"}`}>
                <p className="text-sm">{status.recommendation}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Profiles Tab */}
      {tab === "profiles" && (
        <div className="space-y-4">
          <button onClick={() => setShowForm(true)} className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">+ Add / Update Profile</button>
          {profiles.length === 0 ? <p className="text-sm text-gray-500">No profiles yet.</p> : (
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>{["FY", "Employees", "Revenue (€M)", "HQ", "Sector", "Non-EU", "Updated"].map(h => <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {profiles.map(p => (
                    <tr key={p.id} className="bg-white">
                      <td className="px-3 py-2 font-bold">{p.fiscal_year}</td>
                      <td className="px-3 py-2">{p.employee_count_worldwide.toLocaleString()}</td>
                      <td className="px-3 py-2">{p.net_revenue_eur_millions.toLocaleString()}</td>
                      <td className="px-3 py-2 uppercase">{p.headquarters_country}</td>
                      <td className="px-3 py-2 text-gray-500">{p.sector || "—"}</td>
                      <td className="px-3 py-2">{p.non_eu_company ? "Yes" : "No"}</td>
                      <td className="px-3 py-2 text-xs text-gray-400">{new Date(p.updated_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Info Tab */}
      {tab === "info" && info && (
        <div className="space-y-4">
          <p className="text-xs text-gray-500">{info.source}</p>
          {[{ label: "Tier 1", tier: info.tier_1, bg: "bg-red-50 border-red-200" }, { label: "Tier 2", tier: info.tier_2, bg: "bg-orange-50 border-orange-200" }].map(({ label, tier, bg }) => (
            <div key={label} className={`rounded-lg border p-4 ${bg}`}>
              <h3 className="font-bold mb-2">{label}</h3>
              <div className="grid grid-cols-3 gap-2 text-sm mb-3">
                <div><p className="text-xs text-gray-500">Employees</p><p className="font-medium">≥{tier.employees.toLocaleString()}</p></div>
                <div><p className="text-xs text-gray-500">Revenue</p><p className="font-medium">≥€{tier.revenue_eur_millions.toLocaleString()}M</p></div>
                <div><p className="text-xs text-gray-500">Deadline</p><p className="font-medium">{tier.deadline}</p></div>
              </div>
              <div><p className="text-xs font-medium text-gray-600 mb-1">Key Obligations</p>
                <ul className="space-y-0.5">{tier.obligations.map(o => <li key={o} className="text-xs text-gray-600">• {o}</li>)}</ul>
              </div>
            </div>
          ))}
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3">
            <p className="text-xs text-yellow-800">Borderline zone: within {info.borderline_pct}% below a threshold → EIOS warns to start preparing.</p>
          </div>
        </div>
      )}

      {/* Add Profile Dialog */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-3">
            <h2 className="font-semibold">Add / Update Company Profile</h2>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="block text-xs font-medium">Fiscal Year</label><input type="number" value={form.fiscal_year} onChange={(e) => setForm({ ...form, fiscal_year: +e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
              <div><label className="block text-xs font-medium">Employees (worldwide)</label><input type="number" value={form.employee_count_worldwide} onChange={(e) => setForm({ ...form, employee_count_worldwide: +e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
              <div><label className="block text-xs font-medium">Revenue (€M)</label><input type="number" step="0.1" value={form.net_revenue_eur_millions} onChange={(e) => setForm({ ...form, net_revenue_eur_millions: +e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
              <div><label className="block text-xs font-medium">HQ Country (ISO-2)</label><input value={form.headquarters_country ?? "DE"} onChange={(e) => setForm({ ...form, headquarters_country: e.target.value.toUpperCase().slice(0, 2) })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
            </div>
            <div><label className="block text-xs font-medium">Sector</label><input value={form.sector ?? ""} onChange={(e) => setForm({ ...form, sector: e.target.value })} className="mt-1 w-full rounded border px-2 py-1.5 text-sm" /></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.non_eu_company ?? false} onChange={(e) => setForm({ ...form, non_eu_company: e.target.checked })} /> Non-EU company</label>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowForm(false)} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleSave} disabled={saving} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-40">{saving ? "Saving…" : "Save"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
