"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { HelpCircle, X, ChevronRight } from "lucide-react";

interface HelpTopic {
  title: string;
  body: string;
  links?: { label: string; href: string }[];
}

const PAGE_HELP: Record<string, HelpTopic> = {
  "/dashboard": {
    title: "Dashboard",
    body: "Your dashboard shows a live summary of ESG health, open findings, risks, and pending actions. Use the KPI cards to drill into any metric.",
    links: [{ label: "Add your first supplier →", href: "/suppliers" }],
  },
  "/suppliers": {
    title: "Supplier Management",
    body: "Add and manage your supply chain. Run due diligence checks, track certificates, and view sector risk benchmarks per supplier.",
    links: [{ label: "Run a due diligence check", href: "/suppliers" }, { label: "View sector intelligence", href: "/suppliers" }],
  },
  "/assessments": {
    title: "Assessments",
    body: "Assessments evaluate your suppliers against ESG criteria. Schedule recurring assessments and track quality scores over time.",
    links: [{ label: "Start a new assessment →", href: "/assessments/new" }],
  },
  "/findings": {
    title: "Findings",
    body: "Findings represent issues discovered during assessments. Assign owners, link to risks, and track remediation progress.",
    links: [{ label: "Bulk assign findings", href: "/findings" }],
  },
  "/risks": {
    title: "Risk Register",
    body: "Track ESG risks across your portfolio. Escalate critical risks, link mitigating actions, and monitor probability vs. impact.",
  },
  "/reports": {
    title: "Reports Center",
    body: "Generate and export regulatory reports — TCFD, SFDR PAI, GRI, CSRD, and CDP. Download iXBRL packages for regulatory filing.",
    links: [{ label: "Generate a disclosure package →", href: "/reports" }],
  },
  "/sustainability": {
    title: "Sustainability",
    body: "Track your ESG objectives, KPIs, carbon inventory, science-based targets, and net zero roadmaps in one place.",
    links: [{ label: "Download scorecard PDF", href: "/sustainability" }],
  },
  "/ai-governance": {
    title: "AI Governance",
    body: "Register AI models, monitor drift alerts, manage use cases, and track incidents. Your AI governance posture is scored automatically.",
    links: [{ label: "Register a model →", href: "/ai-governance/models" }],
  },
  "/compliance": {
    title: "Compliance",
    body: "Monitor compliance gaps across frameworks. The radar chart shows coverage % per framework at a glance.",
  },
  "/financial-esg": {
    title: "Financial ESG",
    body: "Track EU Taxonomy alignment, green revenue %, and SFDR metrics. Waterfall and donut charts show eligible vs. aligned breakdown.",
  },
  "/operating-system/calendar": {
    title: "Governance Calendar",
    body: "View regulatory deadlines, filing dates, and compliance events in month, week, or day view. Events are color-coded by type.",
  },
  "/settings": {
    title: "Settings",
    body: "Manage users, MFA, branding, integrations, roles, and API keys. Admin-only settings are gated by role.",
    links: [{ label: "Configure integrations →", href: "/settings/integrations" }],
  },
};

function getHelpForPath(pathname: string): HelpTopic {
  for (const [prefix, topic] of Object.entries(PAGE_HELP)) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) return topic;
  }
  return {
    title: "EIOS Help",
    body: "Navigate using the sidebar to access suppliers, assessments, findings, risks, sustainability, and reporting modules.",
    links: [{ label: "Go to Dashboard →", href: "/dashboard" }],
  };
}

// ── Exported trigger button ───────────────────────────────────────────────────

export function HelpButton() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const help = getHelpForPath(pathname);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Context-sensitive help"
        className="flex items-center gap-1.5 rounded-md border border-border bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
      >
        <HelpCircle className="h-3.5 w-3.5" />
        Help
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          {/* Drawer */}
          <div className="fixed right-0 top-0 z-50 flex h-full w-80 flex-col border-l border-border bg-background shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div className="flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-blue-500" />
                <p className="font-semibold text-sm">{help.title}</p>
              </div>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              <p className="text-sm text-muted-foreground leading-relaxed">{help.body}</p>
              {help.links && (
                <div className="space-y-1">
                  {help.links.map((l) => (
                    <a
                      key={l.href}
                      href={l.href}
                      className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
                      onClick={() => setOpen(false)}
                    >
                      <ChevronRight className="h-3.5 w-3.5" />
                      {l.label}
                    </a>
                  ))}
                </div>
              )}
              <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground">Quick tips</p>
                <p>• Press <kbd className="rounded border px-1 py-0.5 font-mono text-[10px]">⌘K</kbd> for global search</p>
                <p>• Use the Knowledge Base button to search evidence</p>
                <p>• The FAB <kbd className="rounded border px-1 py-0.5 font-mono text-[10px]">+</kbd> creates entities from any page</p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
