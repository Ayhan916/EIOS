"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  UserPlus,
  Shield,
  ShieldCheck,
  ShieldOff,
  UserCheck,
  UserX,
} from "lucide-react";
import { listUsers, updateUser, inviteUser } from "@/lib/api/users";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import type { UserResponse, UserInviteRequest } from "@/types/api";

const ROLES = ["viewer", "analyst", "reviewer", "admin"] as const;
type Role = (typeof ROLES)[number];

const ROLE_COLORS: Record<Role, string> = {
  admin: "bg-purple-100 text-purple-800",
  reviewer: "bg-blue-100 text-blue-800",
  analyst: "bg-green-100 text-green-800",
  viewer: "bg-slate-100 text-slate-700",
};

function RoleBadge({ role }: { role: string }) {
  const color =
    ROLE_COLORS[role as Role] ?? "bg-slate-100 text-slate-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${color}`}
    >
      {role}
    </span>
  );
}

function InviteModal({
  onClose,
  onSubmit,
  loading,
  result,
}: {
  onClose: () => void;
  onSubmit: (req: UserInviteRequest) => void;
  loading: boolean;
  result: { temp_password: string } | null;
}) {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("analyst");

  if (result) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <div className="mb-4 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-green-600" />
            <h2 className="text-base font-semibold">{t("sec.inviteUser")}</h2>
          </div>
          <p className="mb-2 text-sm text-slate-600">
            {t("users.tempPasswordDesc")}
          </p>
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 font-mono text-sm">
            {result.temp_password}
          </div>
          <button
            onClick={onClose}
            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
          >
            {t("common.close")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-base font-semibold">{t("sec.inviteUser")}</h2>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              {t("common.email")}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="colleague@company.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              {t("auth.displayName")}
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Jane Smith"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              {t("sec.role")}
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            >
              {ROLES.map((r) => (
                <option key={r} value={r} className="capitalize">
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-5 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t("common.cancel")}
          </button>
          <button
            onClick={() =>
              onSubmit({ email, display_name: displayName, role })
            }
            disabled={loading || !email || !displayName}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? t("users.inviting") : t("users.sendInvite")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function UsersSettingsPage() {
  const { t } = useLanguage();
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [showInvite, setShowInvite] = useState(false);
  const [inviteResult, setInviteResult] = useState<{
    temp_password: string;
  } | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["org-users"],
    queryFn: listUsers,
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateUser(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-users"] }),
  });

  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      updateUser(id, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-users"] }),
  });

  const invite = useMutation({
    mutationFn: inviteUser,
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["org-users"] });
      setInviteResult({ temp_password: res.temp_password });
    },
  });

  if (me?.role !== "admin") {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <ShieldOff className="mb-4 h-10 w-10 text-slate-300" />
        <p className="text-sm text-slate-500">{t("settings.adminOnly")}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {t("sec.usersTitle")}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t("sec.usersSubtitle")}
          </p>
        </div>
        <button
          onClick={() => {
            setInviteResult(null);
            setShowInvite(true);
          }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <UserPlus className="h-4 w-4" />
          {t("sec.inviteUser")}
        </button>
      </div>

      {isLoading ? (
        <div className="py-12 text-center text-sm text-slate-400">
          {t("common.loading")}
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">{t("sec.usersTitle")}</th>
                <th className="px-4 py-3">{t("sec.role")}</th>
                <th className="px-4 py-3">{t("common.status")}</th>
                <th className="px-4 py-3">MFA</th>
                <th className="px-4 py-3">{t("sec.lastLogin")}</th>
                <th className="px-4 py-3 text-right">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u: UserResponse) => (
                <tr
                  key={u.id}
                  className="border-b border-slate-50 last:border-0 hover:bg-slate-50"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                        {u.display_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {u.display_name}
                          {u.id === me?.id && (
                            <span className="ml-2 text-xs text-slate-400">
                              {t("users.you")}
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-slate-400">{u.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {u.id === me?.id ? (
                      <RoleBadge role={u.role} />
                    ) : (
                      <select
                        value={u.role}
                        onChange={(e) =>
                          changeRole.mutate({ id: u.id, role: e.target.value })
                        }
                        className="rounded border border-slate-200 px-2 py-1 text-xs capitalize outline-none focus:ring-1 focus:ring-blue-500"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r} className="capitalize">
                            {r}
                          </option>
                        ))}
                      </select>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs text-green-600">
                        <UserCheck className="h-3.5 w-3.5" />
                        {t("common.active")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs text-red-500">
                        <UserX className="h-3.5 w-3.5" />
                        {t("common.inactive")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {u.mfa_enabled ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                        <ShieldCheck className="h-3 w-3" /> {t("users.mfaEnrolled")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500">
                        <ShieldOff className="h-3 w-3" /> {t("users.mfaNotSet")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {u.last_login_at
                      ? new Date(u.last_login_at).toLocaleDateString()
                      : t("common.never")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.id !== me?.id && (
                      <button
                        onClick={() =>
                          toggleActive.mutate({
                            id: u.id,
                            is_active: !u.is_active,
                          })
                        }
                        className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                          u.is_active
                            ? "text-red-600 hover:bg-red-50"
                            : "text-green-600 hover:bg-green-50"
                        }`}
                      >
                        {u.is_active ? t("users.deactivate") : t("users.activate")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="py-10 text-center text-sm text-slate-400">
              {t("sec.noUsers")}
            </div>
          )}
        </div>
      )}

      {showInvite && (
        <InviteModal
          onClose={() => {
            setShowInvite(false);
            setInviteResult(null);
          }}
          onSubmit={(req) => invite.mutate(req)}
          loading={invite.isPending}
          result={inviteResult}
        />
      )}
    </div>
  );
}
