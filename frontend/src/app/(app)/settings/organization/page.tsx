"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Building2, CheckCircle, ShieldOff } from "lucide-react";
import { getMyOrganization, updateMyOrganization } from "@/lib/api/organizations";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import type { OrganizationUpdate } from "@/types/api";

export default function OrganizationSettingsPage() {
  const { user: me } = useAuth();
  const { t } = useLanguage();

  const { data: org, isLoading } = useQuery({
    queryKey: ["my-organization"],
    queryFn: getMyOrganization,
  });

  const [form, setForm] = useState<OrganizationUpdate>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (org) {
      setForm({
        name: org.name,
        description: org.description ?? "",
        country: org.country ?? "",
        industry: org.industry ?? "",
      });
    }
  }, [org]);

  const update = useMutation({
    mutationFn: updateMyOrganization,
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
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

  if (isLoading || !org) {
    return (
      <div className="py-12 text-center text-sm text-slate-400">{t("common.loading")}</div>
    );
  }

  const field = (
    label: string,
    key: keyof OrganizationUpdate,
    type: "text" | "textarea" = "text"
  ) => (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-600">
        {label}
      </label>
      {type === "textarea" ? (
        <textarea
          value={(form[key] as string) ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          rows={3}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        />
      ) : (
        <input
          type="text"
          value={(form[key] as string) ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
        />
      )}
    </div>
  );

  return (
    <div className="max-w-2xl">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
          <Building2 className="h-5 w-5 text-slate-600" />
        </div>
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {t("sec.orgTitle")}
          </h1>
          <p className="text-sm text-slate-500">{org.organization_type}</p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <div className="space-y-4">
          {field(t("settings.orgName"), "name")}
          {field(t("settings.orgDescription"), "description", "textarea")}
          {field(t("settings.orgCountry"), "country")}
          {field(t("settings.orgIndustry"), "industry")}
        </div>

        <div className="mt-6 flex items-center justify-between">
          {saved ? (
            <span className="flex items-center gap-1.5 text-sm text-green-600">
              <CheckCircle className="h-4 w-4" />
              {t("settings.orgSaved")}
            </span>
          ) : (
            <span />
          )}
          <button
            onClick={() => update.mutate(form)}
            disabled={update.isPending}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {update.isPending ? t("settings.saving") : t("settings.saveChanges")}
          </button>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-xs text-slate-400">
        <span className="font-medium">{t("common.id")}:</span> {org.id}
        <span className="ml-4 font-medium">{t("common.status")}:</span>{" "}
        <span className="capitalize">{org.status}</span>
      </div>
    </div>
  );
}
