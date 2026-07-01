"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Globe,
  Link2,
  MessageSquare,
  Shield,
  Ticket,
  Zap,
} from "lucide-react";
import apiClient from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Integration {
  id: string;
  name: string;
  description: string;
  category: "Compliance" | "Communication" | "Ticketing" | "ESG" | "Security" | "Storage";
  icon: React.ElementType;
  docsUrl?: string;
  testEndpoint?: string;
  testMethod?: "GET" | "POST";
  testPayload?: Record<string, unknown>;
}

const INTEGRATIONS: Integration[] = [
  {
    id: "sbti",
    name: "SBTi Validation",
    description: "Validate emission reduction targets against Science Based Targets Initiative 1.5°C criteria.",
    category: "ESG",
    icon: CheckCircle2,
    testEndpoint: "/integrations/sbti/validate",
    testMethod: "POST",
  },
  {
    id: "cdp",
    name: "CDP Climate",
    description: "Generate CDP Climate Change questionnaire response packages for annual disclosure.",
    category: "ESG",
    icon: Globe,
    testEndpoint: "/integrations/cdp/report",
    testMethod: "POST",
    testPayload: { reporting_year: 2024 },
  },
  {
    id: "ofac",
    name: "OFAC Sanctions Screening",
    description: "Screen suppliers against the OFAC Specially Designated Nationals (SDN) list in real-time.",
    category: "Compliance",
    icon: Shield,
  },
  {
    id: "slack",
    name: "Slack",
    description: "Send ESG alerts, assessment completions, and risk notifications to Slack channels.",
    category: "Communication",
    icon: MessageSquare,
    testEndpoint: "/integrations/slack/notify",
    testMethod: "POST",
    testPayload: { message: "EIOS integration test" },
  },
  {
    id: "teams",
    name: "Microsoft Teams",
    description: "Deliver real-time ESG notifications and board alerts to Teams channels via webhook.",
    category: "Communication",
    icon: MessageSquare,
    testEndpoint: "/integrations/teams/notify",
    testMethod: "POST",
    testPayload: { message: "EIOS integration test", title: "EIOS" },
  },
  {
    id: "jira",
    name: "Jira",
    description: "Sync ESG findings and remediation recommendations as Jira issues for engineering teams.",
    category: "Ticketing",
    icon: Ticket,
    testEndpoint: "/integrations/jira/issues",
    testMethod: "GET",
  },
  {
    id: "servicenow",
    name: "ServiceNow",
    description: "Create and track ESG incidents, risks, and action items in ServiceNow ITSM workflows.",
    category: "Ticketing",
    icon: Ticket,
    testEndpoint: "/integrations/servicenow/incidents",
    testMethod: "GET",
  },
  {
    id: "sharepoint",
    name: "SharePoint",
    description: "Store and retrieve ESG evidence documents from SharePoint via OAuth2.",
    category: "Storage",
    icon: Link2,
    testEndpoint: "/integrations/sharepoint/files",
    testMethod: "GET",
  },
  {
    id: "webhooks",
    name: "Webhooks",
    description: "Send real-time event payloads to any URL when ESG events occur in your platform.",
    category: "Communication",
    icon: Zap,
  },
];

const CATEGORY_COLORS: Record<string, string> = {
  ESG: "bg-emerald-100 text-emerald-800",
  Compliance: "bg-red-100 text-red-800",
  Communication: "bg-blue-100 text-blue-800",
  Ticketing: "bg-purple-100 text-purple-800",
  Storage: "bg-slate-100 text-slate-700",
  Security: "bg-orange-100 text-orange-800",
};

function IntegrationCard({ integration }: { integration: Integration }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "error" | null>(null);
  const Icon = integration.icon;

  async function runTest() {
    if (!integration.testEndpoint) return;
    setTesting(true);
    setTestResult(null);
    try {
      if (integration.testMethod === "POST") {
        await apiClient.post(integration.testEndpoint, integration.testPayload ?? {});
      } else {
        await apiClient.get(integration.testEndpoint);
      }
      setTestResult("ok");
    } catch {
      setTestResult("error");
    } finally {
      setTesting(false);
      setTimeout(() => setTestResult(null), 4000);
    }
  }

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2">
              <Icon className="h-5 w-5 text-slate-600" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold">{integration.name}</CardTitle>
              <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold mt-0.5 ${CATEGORY_COLORS[integration.category]}`}>
                {integration.category}
              </span>
            </div>
          </div>
          {testResult === "ok" && <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />}
          {testResult === "error" && <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 gap-3">
        <p className="text-xs text-muted-foreground flex-1">{integration.description}</p>
        <div className="flex items-center gap-2">
          {integration.testEndpoint ? (
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={testing}
              onClick={runTest}
            >
              {testing ? "Testing…" : "Test Connection"}
            </Button>
          ) : (
            <Button size="sm" variant="outline" className="h-7 text-xs" disabled>
              Configure in Settings
            </Button>
          )}
          {integration.docsUrl && (
            <a
              href={integration.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            >
              Docs <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
        {testResult === "error" && (
          <p className="text-xs text-amber-600">Connection failed — check credentials in Settings.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function IntegrationsPage() {
  const { t } = useLanguage();
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const categories = ["all", ...Array.from(new Set(INTEGRATIONS.map((i) => i.category)))];
  const filtered = categoryFilter === "all"
    ? INTEGRATIONS
    : INTEGRATIONS.filter((i) => i.category === categoryFilter);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("sec.integrationsTitle")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {INTEGRATIONS.length} integrations available — connect EIOS to your existing toolchain
          </p>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
              categoryFilter === cat
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40"
            }`}
          >
            {cat === "all" ? `${t("common.all")} (${INTEGRATIONS.length})` : cat}
          </button>
        ))}
      </div>

      {/* Integration cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((integration) => (
          <IntegrationCard key={integration.id} integration={integration} />
        ))}
      </div>
    </div>
  );
}
