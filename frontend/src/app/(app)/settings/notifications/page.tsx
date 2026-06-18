"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  getNotificationPreferences,
  updateNotificationPreferences,
} from "@/lib/api/notifications";
import type { NotificationPreferences } from "@/types/api";

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
        <h1 className="text-2xl font-bold tracking-tight">Notification Preferences</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose which events send you an email notification.
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
              aria-checked={prefs[key]}
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

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Save preferences
        </Button>
        {saved && (
          <span className="text-sm text-green-600 dark:text-green-400">Saved!</span>
        )}
      </div>
    </div>
  );
}
