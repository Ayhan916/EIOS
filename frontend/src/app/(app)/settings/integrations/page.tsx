"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Eye, EyeOff, Save, Plug } from "lucide-react";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

interface OrgSettings {
  integrations_configured: string[];
}

interface FieldConfig {
  key: string;
  label: string;
  placeholder: string;
  type?: "password";
  hint?: string;
}

const INTEGRATIONS: Array<{
  id: string;
  label: string;
  description: string;
  color: string;
  fields: FieldConfig[];
}> = [
  {
    id: "teams",
    label: "Microsoft Teams",
    description: "Send risk alerts and assessment notifications to a Teams channel.",
    color: "bg-blue-600",
    fields: [
      { key: "teams_webhook_url", label: "Webhook URL", placeholder: "https://outlook.office.com/webhook/...", hint: "Create an Incoming Webhook connector in Teams and paste the URL here." },
    ],
  },
  {
    id: "slack",
    label: "Slack",
    description: "Post critical findings and escalations to a Slack channel.",
    color: "bg-emerald-600",
    fields: [
      { key: "slack_webhook_url", label: "Webhook URL", placeholder: "https://hooks.slack.com/services/...", hint: "Create an Incoming Webhook app in your Slack workspace." },
    ],
  },
  {
    id: "jira",
    label: "JIRA",
    description: "Auto-create JIRA tickets when critical findings are raised.",
    color: "bg-blue-500",
    fields: [
      { key: "jira_base_url", label: "JIRA Base URL", placeholder: "https://your-org.atlassian.net" },
      { key: "jira_email", label: "JIRA Email", placeholder: "automation@your-org.com" },
      { key: "jira_api_token", label: "API Token", placeholder: "••••••••••••••••", type: "password", hint: "Generate from https://id.atlassian.com/manage/api-tokens" },
    ],
  },
  {
    id: "servicenow",
    label: "ServiceNow",
    description: "Create ServiceNow incidents from high-severity risks.",
    color: "bg-green-700",
    fields: [
      { key: "servicenow_instance_url", label: "Instance URL", placeholder: "https://your-instance.service-now.com" },
      { key: "servicenow_username", label: "Username", placeholder: "automation_user" },
    ],
  },
];

export default function IntegrationSettingsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: settings, isLoading } = useQuery<OrgSettings>({
    queryKey: ["org-settings"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/commercial/organizations/me/settings");
      return res.data;
    },
  });

  const [values, setValues] = useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});

  const setValue = (key: string, val: string) =>
    setValues((prev) => ({ ...prev, [key]: val }));

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, string | null> = {};
      for (const [k, v] of Object.entries(values)) {
        body[k] = v.trim() || null;
      }
      await apiClient.put("/api/v1/commercial/organizations/me/settings", body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-settings"] }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  const configured = settings?.integrations_configured ?? [];

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Plug className="h-6 w-6" />
          {t("sec.integrationsTitle")}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("sec.integrationsSubtitle")}
        </p>
      </div>

      {INTEGRATIONS.map((integration) => {
        const isConfigured = configured.includes(integration.id);
        return (
          <Card key={integration.id}>
            <CardHeader className="flex flex-row items-start gap-4 space-y-0">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${integration.color} flex-shrink-0`}>
                <Plug className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CardTitle className="text-base">{integration.label}</CardTitle>
                  {isConfigured && (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" /> {t("erp.connected")}
                    </span>
                  )}
                </div>
                <CardDescription>{integration.description}</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              {integration.fields.map((field) => {
                const isPass = field.type === "password";
                const show = showPassword[field.key];
                return (
                  <div key={field.key}>
                    <label className="block text-sm font-medium mb-1.5">{field.label}</label>
                    <div className="relative">
                      <input
                        type={isPass && !show ? "password" : "text"}
                        value={values[field.key] ?? ""}
                        onChange={(e) => setValue(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring pr-10"
                      />
                      {isPass && (
                        <button
                          type="button"
                          onClick={() => setShowPassword((p) => ({ ...p, [field.key]: !p[field.key] }))}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      )}
                    </div>
                    {field.hint && (
                      <p className="text-xs text-muted-foreground mt-1">{field.hint}</p>
                    )}
                  </div>
                );
              })}
            </CardContent>
          </Card>
        );
      })}

      <div className="flex items-center gap-3 pb-8">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="gap-2"
        >
          {saveMutation.isPending ? <Spinner size="sm" /> : <Save className="h-4 w-4" />}
          {t("common.save")}
        </Button>
        {saveMutation.isSuccess && (
          <span className="flex items-center gap-1.5 text-sm text-emerald-600 font-medium">
            <CheckCircle2 className="h-4 w-4" /> Saved
          </span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-600">Failed to save. Admin role required.</span>
        )}
      </div>
    </div>
  );
}
