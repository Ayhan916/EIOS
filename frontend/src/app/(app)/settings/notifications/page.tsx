"use client";

import { useEffect, useState } from "react";
import { Loader2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
} from "@/lib/api/notifications";
import type { NotificationPreferences } from "@/types/api";
import { useLanguage } from "@/lib/i18n/context";

const PREFS: { key: keyof NotificationPreferences; label: string; description: string }[] = [
  {
    key: "email_workflow_completed",
    label: "Workflow completed",
    description: "Receive an email when an AI workflow analysis finishes.",
  },
  {
    key: "email_action_overdue",
    label: "Action overdue",
    description: "Receive an email when a recommendation assigned to you is past its due date.",
  },
  {
    key: "email_assessment_approved",
    label: "Assessment approved",
    description: "Receive an email when an assessment you created is approved.",
  },
  {
    key: "email_recommendation_assigned",
    label: "Recommendation assigned",
    description: "Receive an email when a recommendation is assigned to you.",
  },
];

export default function NotificationSettingsPage() {
  const { t } = useLanguage();
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getNotificationPreferences()
      .then(setPrefs)
      .catch(() => setError("Failed to load preferences."));
  }, []);

  function toggle(key: keyof NotificationPreferences) {
    if (!prefs) return;
    setPrefs({ ...prefs, [key]: !prefs[key] });
    setSaved(false);
  }

  async function handleSave() {
    if (!prefs) return;
    setSaving(true);
    setError(null);
    try {
      await updateNotificationPreferences(prefs);
      setSaved(true);
    } catch {
      setError("Failed to save preferences.");
    } finally {
      setSaving(false);
    }
  }

  if (!prefs) {
    return (
      <div className="flex h-40 items-center justify-center">
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sec.notifSettingsTitle")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("sec.notifSettingsSubtitle")}
        </p>
      </div>

      <div className="rounded-lg border border-border divide-y divide-border">
        {PREFS.map(({ key, label, description }) => (
          <div key={key} className="flex items-start justify-between gap-4 p-4">
            <div>
              <p className="text-sm font-medium">{label}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
            </div>
            <button
              role="switch"
              aria-checked={!!prefs[key]}
              onClick={() => toggle(key)}
              className={`mt-0.5 relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
                prefs[key] ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-700"
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
                  prefs[key] ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        ))}
      </div>

      {/* #134 Weekly ESG digest */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Mail className="h-4 w-4 text-blue-500" />
          <h2 className="text-sm font-semibold">Weekly ESG Digest</h2>
        </div>
        <div className="rounded-lg border border-border divide-y divide-border">
          <div className="flex items-start justify-between gap-4 p-4">
            <div>
              <p className="text-sm font-medium">Weekly summary email</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Receive a weekly ESG portfolio digest: top risks, KPI changes, pending actions, and compliance status.
              </p>
            </div>
            <button
              role="switch"
              aria-checked={prefs.email_weekly_digest ?? false}
              onClick={() => setPrefs({ ...prefs, email_weekly_digest: !(prefs.email_weekly_digest ?? false) })}
              className={`mt-0.5 relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none ${
                prefs.email_weekly_digest ? "bg-blue-600" : "bg-slate-300 dark:bg-slate-700"
              }`}
            >
              <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition-transform ${
                prefs.email_weekly_digest ? "translate-x-4" : "translate-x-0"
              }`} />
            </button>
          </div>
          {prefs.email_weekly_digest && (
            <div className="flex items-center justify-between gap-4 p-4">
              <div>
                <p className="text-sm font-medium">Send on</p>
                <p className="text-xs text-muted-foreground mt-0.5">Which weekday to receive the digest.</p>
              </div>
              <select
                value={prefs.digest_day ?? "Monday"}
                onChange={(e) => setPrefs({ ...prefs, digest_day: e.target.value as typeof prefs.digest_day })}
                className="rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                {["Monday","Tuesday","Wednesday","Thursday","Friday"].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {saving ? t("settings.saving") : t("settings.saveChanges")}
        </Button>
        {saved && (
          <span className="text-sm text-green-600 dark:text-green-400">Saved!</span>
        )}
      </div>
    </div>
  );
}
