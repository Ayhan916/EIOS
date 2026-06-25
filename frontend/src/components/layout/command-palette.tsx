"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";
import * as Dialog from "@radix-ui/react-dialog";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  Briefcase,
  CheckSquare,
  ClipboardList,
  DollarSign,
  FileText,
  LayoutDashboard,
  Leaf,
  LineChart,
  Network,
  Radio,
  Palette,
  Plug2,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Upload,
  Users,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ── Command registry ──────────────────────────────────────────────────────────

const COMMANDS = [
  // Core
  { id: "dashboard",        label: "Dashboard",             href: "/dashboard",                  icon: LayoutDashboard, category: "Core" },
  { id: "suppliers",        label: "Suppliers",             href: "/suppliers",                  icon: Briefcase,       category: "Core" },
  { id: "assessments",      label: "Assessments",           href: "/assessments",                icon: FileText,        category: "Core" },
  { id: "findings",         label: "Findings",              href: "/findings",                   icon: AlertTriangle,   category: "Core" },
  { id: "risks",            label: "Risks",                 href: "/risks",                      icon: ShieldAlert,     category: "Core" },
  { id: "recommendations",  label: "Recommendations",       href: "/recommendations",            icon: CheckSquare,     category: "Core" },
  { id: "evidence",         label: "Evidence Library",      href: "/evidence",                   icon: Upload,          category: "Core" },
  { id: "notifications",    label: "Notification Inbox",    href: "/notifications",              icon: FileText,        category: "Core" },
  // ESG
  { id: "sustainability",   label: "Sustainability",        href: "/sustainability",             icon: Leaf,            category: "ESG" },
  { id: "carbon",           label: "Carbon Inventory",      href: "/sustainability/carbon",      icon: Zap,             category: "ESG" },
  { id: "sbts",             label: "Science-Based Targets", href: "/sustainability/science-based-targets", icon: Leaf, category: "ESG" },
  { id: "ghg",              label: "GHG Accounting",        href: "/sustainability",             icon: Leaf,            category: "ESG" },
  { id: "surveillance",     label: "Surveillance",          href: "/surveillance",               icon: Radio,           category: "ESG" },
  { id: "network",          label: "Supplier Network",      href: "/network",                    icon: Network,         category: "ESG" },
  // Financial ESG
  { id: "financial-esg",    label: "Financial ESG",         href: "/financial-esg",              icon: DollarSign,      category: "Finance" },
  { id: "sfdr",             label: "SFDR / Taxonomy",       href: "/financial-esg/taxonomy",     icon: DollarSign,      category: "Finance" },
  { id: "strategy",         label: "Strategy & Digital Twin", href: "/strategy",                 icon: LineChart,       category: "Finance" },
  // Governance
  { id: "enterprise",       label: "Enterprise",            href: "/enterprise",                 icon: Shield,          category: "Governance" },
  { id: "ai-governance",    label: "AI Governance",         href: "/ai-governance",              icon: Bot,             category: "Governance" },
  { id: "esg-os",           label: "ESG Operating System",  href: "/operating-system/calendar",  icon: ClipboardList,   category: "Governance" },
  { id: "users",            label: "Users & Roles",         href: "/settings/users",             icon: Users,           category: "Governance" },
  // Reports
  { id: "executive",        label: "Executive Dashboard",   href: "/executive",                  icon: BarChart3,       category: "Reports" },
  { id: "board-reports",    label: "Board Reports",         href: "/executive/reports",          icon: FileText,        category: "Reports" },
  { id: "reports-center",   label: "Reports Center",        href: "/reports",                    icon: FileText,        category: "Reports" },
  // Security
  { id: "auditor",          label: "Auditor Workspace",     href: "/auditor",                    icon: ShieldCheck,     category: "Security" },
  { id: "settings",         label: "Settings",              href: "/settings/notifications",     icon: ShieldCheck,     category: "Security" },
  { id: "branding",         label: "Branding & White-Label",href: "/settings/branding",          icon: Palette,         category: "Security" },
  { id: "settings-integrations", label: "Integration Settings", href: "/settings/integrations", icon: Plug2,           category: "Security" },
  { id: "custom-roles",     label: "Custom Roles",          href: "/settings/roles",             icon: Shield,          category: "Security" },
];

// ── Entity search types ───────────────────────────────────────────────────────

interface EntityResult {
  id: string;
  label: string;
  sub: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

function useEntitySearch(query: string) {
  const q = query.trim();
  const enabled = q.length >= 2;

  const { data: suppliers } = useQuery({
    queryKey: ["cmd-suppliers", q],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/executive/suppliers?limit=5");
      return (r.data as Array<{ id: string; name: string; risk_level: string | null }>)
        .filter((s) => s.name.toLowerCase().includes(q.toLowerCase()));
    },
    enabled,
    staleTime: 30_000,
  });

  const { data: findings } = useQuery({
    queryKey: ["cmd-findings", q],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/executive/findings?limit=5");
      return (r.data as Array<{ id: string; title: string; severity: string }>)
        .filter((f) => f.title.toLowerCase().includes(q.toLowerCase()));
    },
    enabled,
    staleTime: 30_000,
  });

  const { data: risks } = useQuery({
    queryKey: ["cmd-risks", q],
    queryFn: async () => {
      const r = await apiClient.get("/api/v1/executive/risks?limit=5");
      return (r.data as Array<{ id: string; title: string; risk_level: string }>)
        .filter((r2) => r2.title.toLowerCase().includes(q.toLowerCase()));
    },
    enabled,
    staleTime: 30_000,
  });

  if (!enabled) return [];

  const results: EntityResult[] = [];
  for (const s of suppliers ?? []) {
    results.push({ id: `s-${s.id}`, label: s.name, sub: `Supplier · ${s.risk_level ?? "Unknown"}`, href: `/suppliers/${s.id}`, icon: Briefcase });
  }
  for (const f of findings ?? []) {
    results.push({ id: `f-${f.id}`, label: f.title, sub: `Finding · ${f.severity}`, href: `/findings/${f.id}`, icon: AlertTriangle });
  }
  for (const r of risks ?? []) {
    results.push({ id: `r-${r.id}`, label: r.title, sub: `Risk · ${r.risk_level}`, href: `/risks/${r.id}`, icon: ShieldAlert });
  }
  return results.slice(0, 8);
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const entityResults = useEntitySearch(query);

  // Open on Cmd+K / Ctrl+K
  useEffect(() => {
    function onKeydown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKeydown);
    return () => window.removeEventListener("keydown", onKeydown);
  }, []);

  // Reset state when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const filtered = query.trim()
    ? COMMANDS.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.category.toLowerCase().includes(query.toLowerCase())
      )
    : COMMANDS;

  const totalResults = filtered.length + entityResults.length;

  function navigate(href: string) {
    setOpen(false);
    router.push(href);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected((s) => Math.min(s + 1, totalResults - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected((s) => Math.max(s - 1, 0));
    } else if (e.key === "Enter") {
      if (selected < filtered.length && filtered[selected]) navigate(filtered[selected].href);
      else if (selected >= filtered.length && entityResults[selected - filtered.length]) navigate(entityResults[selected - filtered.length].href);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  // Group by category
  const byCategory: Record<string, typeof COMMANDS> = {};
  for (const cmd of filtered) {
    byCategory[cmd.category] = byCategory[cmd.category] ?? [];
    byCategory[cmd.category].push(cmd);
  }

  const flatFiltered = filtered;

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed left-1/2 top-[15%] z-50 w-full max-w-xl -translate-x-1/2 rounded-xl border border-border bg-background shadow-2xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
          onKeyDown={onKeyDown}
        >
          {/* Search input */}
          <div className="flex items-center gap-3 border-b border-border px-4 py-3">
            <Search className="h-4 w-4 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(0);
              }}
              placeholder="Search pages and features..."
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden sm:inline-flex items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono">
              esc
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-[400px] overflow-y-auto py-2">
            {totalResults === 0 ? (
              <p className="px-4 py-8 text-center text-sm text-muted-foreground">
                No results for &quot;{query}&quot;
              </p>
            ) : query.trim() ? (
              // Flat list when searching — pages + entity results
              <>
                {filtered.length > 0 && (
                  <>
                    <p className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">Pages</p>
                    {filtered.map((cmd, idx) => {
                      const Icon = cmd.icon;
                      return (
                        <button
                          key={cmd.id}
                          onClick={() => navigate(cmd.href)}
                          onMouseEnter={() => setSelected(idx)}
                          className={cn(
                            "flex w-full items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                            selected === idx ? "bg-accent text-accent-foreground" : "text-foreground hover:bg-muted/50"
                          )}
                        >
                          <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="flex-1 text-left">{cmd.label}</span>
                          <span className="text-[10px] text-muted-foreground">{cmd.category}</span>
                        </button>
                      );
                    })}
                  </>
                )}
                {entityResults.length > 0 && (
                  <>
                    <p className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60 mt-1">Records</p>
                    {entityResults.map((ent, i) => {
                      const idx = filtered.length + i;
                      const Icon = ent.icon;
                      return (
                        <button
                          key={ent.id}
                          onClick={() => navigate(ent.href)}
                          onMouseEnter={() => setSelected(idx)}
                          className={cn(
                            "flex w-full items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                            selected === idx ? "bg-accent text-accent-foreground" : "text-foreground hover:bg-muted/50"
                          )}
                        >
                          <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="flex-1 text-left">{ent.label}</span>
                          <span className="text-[10px] text-muted-foreground">{ent.sub}</span>
                        </button>
                      );
                    })}
                  </>
                )}
              </>
            ) : (
              // Grouped view when not searching
              Object.entries(byCategory).map(([cat, items]) => (
                <div key={cat}>
                  <p className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
                    {cat}
                  </p>
                  {items.map((cmd) => {
                    const idx = flatFiltered.indexOf(cmd);
                    const Icon = cmd.icon;
                    return (
                      <button
                        key={cmd.id}
                        onClick={() => navigate(cmd.href)}
                        onMouseEnter={() => setSelected(idx)}
                        className={cn(
                          "flex w-full items-center gap-3 px-4 py-2 text-sm transition-colors",
                          selected === idx ? "bg-accent text-accent-foreground" : "text-foreground hover:bg-muted/50"
                        )}
                      >
                        <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                        <span>{cmd.label}</span>
                      </button>
                    );
                  })}
                </div>
              ))
            )}
          </div>

          {/* Footer hint */}
          <div className="flex items-center gap-3 border-t border-border px-4 py-2">
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">↑↓</kbd>
              navigate
            </div>
            <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">↵</kbd>
              open
            </div>
            <div className="ml-auto text-[10px] text-muted-foreground">
              <kbd className="rounded border border-border bg-muted px-1 py-0.5 font-mono">⌘K</kbd>
              {" "}to toggle
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
