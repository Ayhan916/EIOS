"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bell,
  BarChart3,
  Bot,
  Building2,
  CalendarDays,
  CheckSquare,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  FileCode,
  FileText,
  KeyRound,
  LayoutDashboard,
  Layers,
  Leaf,
  LogOut,
  Network,
  Radio,
  Shield,
  ShieldCheck,
  Target,
  TrendingDown,
  Upload,
  Users,
  Briefcase,
  Globe,
  ClipboardList,
  Zap,
  FlaskConical,
  DollarSign,
  TrendingUp,
  GitBranch,
  Cpu,
  LineChart,
  Palette,
  Plug2,
  Puzzle,
  ShieldAlert,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/context";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";
import { Moon, Sun } from "lucide-react";
import { listNotifications } from "@/lib/api/notifications";

// #111 "New" badge — hrefs of recently shipped features
const NEW_HREFS = new Set([
  "/ai-governance/models",
  "/ai-governance/monitoring",
  "/strategy/forecasts",
  "/sustainability/science-based-targets",
  "/operating-system/okrs",
  "/integrations",
]);

// #102 Reports mega-section
const reportsNavItems = [
  { label: "Reports Center", href: "/reports", icon: FileText },
  { label: "Board Reports", href: "/executive/reports", icon: FileText },
  { label: "Sustainability", href: "/sustainability/reports", icon: Leaf },
  { label: "Financial ESG", href: "/financial-esg/reports", icon: DollarSign },
  { label: "AI Governance", href: "/ai-governance/reports", icon: Bot },
  { label: "Strategy", href: "/strategy/reports", icon: LineChart },
];

// #109 Platform setup tasks stored in localStorage
const SETUP_TASK_KEY = "eios_setup_tasks";
const SETUP_TASKS = [
  "added_supplier",
  "ran_assessment",
  "reviewed_finding",
  "configured_integration",
  "set_objective",
  "uploaded_evidence",
  "set_notifications",
  "viewed_reports",
];

function useSetupPercent() {
  const [pct, setPct] = useState(0);
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(SETUP_TASK_KEY);
      const done: string[] = raw ? JSON.parse(raw) : [];
      const uniqueDone = SETUP_TASKS.filter((t) => done.includes(t)).length;
      setPct(Math.round((uniqueDone / SETUP_TASKS.length) * 100));
    } catch { setPct(0); }
  }, []);
  return pct;
}

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Inbox",
    href: "/notifications",
    icon: Bell,
  },
  {
    label: "Suppliers",
    href: "/suppliers",
    icon: Briefcase,
  },
  {
    label: "Materials",
    href: "/materials",
    icon: FlaskConical,
  },
  {
    label: "Assessments",
    href: "/assessments",
    icon: FileText,
  },
  {
    label: "Findings",
    href: "/findings",
    icon: AlertTriangle,
  },
  {
    label: "Risks",
    href: "/risks",
    icon: ShieldAlert,
  },
  {
    label: "Recommendations",
    href: "/recommendations",
    icon: CheckSquare,
  },
  {
    label: "Evidence",
    href: "/evidence",
    icon: Upload,
  },
  {
    label: "Surveillance",
    href: "/surveillance",
    icon: Radio,
  },
  {
    label: "Network",
    href: "/network",
    icon: Network,
  },
];

const esgOsNavItems = [
  { label: "Calendar", href: "/operating-system/calendar", icon: CalendarDays },
  { label: "Programs", href: "/operating-system/programs", icon: Layers },
  { label: "Controls", href: "/operating-system/controls", icon: Shield },
  { label: "Control Tests", href: "/operating-system/tests", icon: ClipboardCheck },
  { label: "Compliance Ops", href: "/operating-system/compliance-operations", icon: CheckSquare },
  { label: "Accountability", href: "/operating-system/accountability", icon: Users },
];

const enterpriseNavItems = [
  { label: "Overview", href: "/enterprise", icon: ShieldCheck },
  { label: "Business Units", href: "/enterprise/business-units", icon: Building2 },
  { label: "Regions", href: "/enterprise/regions", icon: Globe },
  { label: "Policies", href: "/enterprise/policies", icon: ClipboardList },
  { label: "Identity", href: "/enterprise/identity", icon: KeyRound },
  { label: "Audit", href: "/enterprise/audit", icon: CheckSquare },
  { label: "Notifications", href: "/enterprise/notifications", icon: Bell },
];

const sustainabilityNavItems = [
  { label: "Dashboard", href: "/sustainability", icon: Leaf },
  { label: "Objectives", href: "/sustainability/objectives", icon: Target },
  { label: "Targets", href: "/sustainability/targets", icon: Target },
  { label: "SBTs", href: "/sustainability/science-based-targets", icon: FlaskConical },
  { label: "KPIs", href: "/sustainability/kpis", icon: BarChart3 },
  { label: "Carbon Inventory", href: "/sustainability/carbon", icon: Zap },
  { label: "Decarbonization", href: "/sustainability/initiatives", icon: TrendingDown },
  { label: "Net Zero", href: "/sustainability/roadmaps", icon: Globe },
  { label: "Enterprise View", href: "/sustainability/rollups", icon: Building2 },
  { label: "Reports", href: "/sustainability/reports", icon: FileText },
];

const aiGovernanceNavItems = [
  { label: "Models", href: "/ai-governance/models", icon: Layers },
  { label: "Monitoring", href: "/ai-governance/monitoring", icon: Radio },
  { label: "Use Cases", href: "/ai-governance/use-cases", icon: ClipboardList },
  { label: "Controls", href: "/ai-governance/controls", icon: Shield },
  { label: "Prompts", href: "/ai-governance/prompts", icon: FileCode },
  { label: "Incidents", href: "/ai-governance/incidents", icon: AlertTriangle },
  { label: "Reports", href: "/ai-governance/reports", icon: FileText },
];

const executiveNavItems = [
  {
    label: "Executive Dashboard",
    href: "/executive",
    icon: BarChart3,
  },
  {
    label: "Board Reports",
    href: "/executive/reports",
    icon: FileText,
  },
  {
    label: "Reports Center",
    href: "/reports",
    icon: FileText,
  },
];

const securityNavItems = [
  { label: "Auditor Workspace", href: "/auditor", icon: ShieldCheck },
  { label: "Compliance Center", href: "/compliance/center", icon: Shield },
];

const financialESGNavItems = [
  { label: "Dashboard", href: "/financial-esg", icon: DollarSign },
  { label: "Carbon Economics", href: "/financial-esg/carbon-economics", icon: Zap },
  { label: "Value Creation", href: "/financial-esg/value-creation", icon: TrendingUp },
  { label: "Sustainable Finance", href: "/financial-esg/sustainable-finance", icon: BarChart3 },
  { label: "Taxonomy", href: "/financial-esg/taxonomy", icon: Leaf },
  { label: "Green Revenue", href: "/financial-esg/green-revenue", icon: Globe },
  { label: "Capital Markets", href: "/financial-esg/capital-markets", icon: Building2 },
  { label: "Reports", href: "/financial-esg/reports", icon: FileText },
];

const strategyNavItems = [
  { label: "Overview", href: "/strategy", icon: LineChart },
  { label: "Digital Twin", href: "/strategy/digital-twin", icon: Cpu },
  { label: "Scenarios", href: "/strategy/scenarios", icon: GitBranch },
  { label: "Pathways", href: "/strategy/pathways", icon: TrendingDown },
  { label: "Forecasts", href: "/strategy/forecasts", icon: BarChart3 },
  { label: "Stress Tests", href: "/strategy/stress-tests", icon: Zap },
  { label: "Board Simulation", href: "/strategy/board-simulation", icon: Users },
  { label: "Templates", href: "/strategy/templates", icon: Puzzle },
  { label: "Reports", href: "/strategy/reports", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const setupPct = useSetupPercent();
  const [reportsOpen, setReportsOpen] = useState(false);
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  // Clear pending state when navigation completes
  useEffect(() => {
    setPendingHref(null);
  }, [pathname]);

  function isActive(href: string) {
    if (pendingHref) return pendingHref === href;
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  function handleNav(href: string) {
    if (href !== pathname) setPendingHref(href);
  }

  const { data: notifData } = useQuery({
    queryKey: ["notifications-unread-count"],
    queryFn: listNotifications,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const unreadCount = notifData?.items.filter((n: { is_read: boolean }) => !n.is_read).length ?? 0;

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-slate-950 text-slate-100">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-white">EIOS</p>
          <p className="text-[10px] text-slate-400 uppercase tracking-wider">
            ESG Intelligence
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
          Platform
        </p>
        {navItems.map((item) => {
          const active = isActive(item.href);
          const isInbox = item.href === "/notifications";
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => handleNav(item.href)}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
              )}
            >
              <item.icon className="h-4 w-4 flex-shrink-0" />
              <span className="flex-1">{item.label}</span>
              {isInbox && unreadCount > 0 && (
                <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>
          );
        })}

        {/* #102 Reports mega-section */}
        <>
          <button
            onClick={() => setReportsOpen((o) => !o)}
            className="mt-4 flex w-full items-center rounded-md px-3 pb-2 pt-1 text-[10px] font-semibold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
          >
            <span className="flex-1 text-left">Reports</span>
            {reportsOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {reportsOpen && reportsNavItems.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            ESG Operating System
          </p>
          {esgOsNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            AI Governance
          </p>
          {aiGovernanceNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{item.label}</span>
                {NEW_HREFS.has(item.href) && (
                  <span className="text-[9px] font-bold bg-blue-500 text-white rounded px-1 py-0.5">New</span>
                )}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Sustainability
          </p>
          {sustainabilityNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-emerald-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{item.label}</span>
                {NEW_HREFS.has(item.href) && (
                  <span className="text-[9px] font-bold bg-blue-500 text-white rounded px-1 py-0.5">New</span>
                )}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Financial ESG
          </p>
          {financialESGNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-700 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Strategy
          </p>
          {strategyNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-violet-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{item.label}</span>
                {NEW_HREFS.has(item.href) && (
                  <span className="text-[9px] font-bold bg-blue-500 text-white rounded px-1 py-0.5">New</span>
                )}
              </Link>
            );
          })}
        </>

        {(user?.role === "admin" || user?.role === "enterprise_admin" || user?.role === "bu_admin" || user?.role === "regional_admin") && (
          <>
            <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
              Enterprise
            </p>
            {enterpriseNavItems.map((item) => {
              const active =
                isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => handleNav(item.href)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  )}
                >
                  <item.icon className="h-4 w-4 flex-shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}

        {(user?.role === "executive" || user?.role === "admin") && (
          <>
            <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
              Executive
            </p>
            {executiveNavItems.map((item) => {
              const active =
                isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => handleNav(item.href)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  )}
                >
                  <item.icon className="h-4 w-4 flex-shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </>
        )}

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Security & Audit
          </p>
          {securityNavItems.map((item) => {
            const active =
              isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-slate-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Integrations
          </p>
          {[{ label: "Marketplace", href: "/integrations", icon: Puzzle }].map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <item.icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{item.label}</span>
                {NEW_HREFS.has(item.href) && (
                  <span className="text-[9px] font-bold bg-blue-500 text-white rounded px-1 py-0.5">New</span>
                )}
              </Link>
            );
          })}
        </>

        <>
          <p className="mt-4 px-3 pb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
            Settings
          </p>
          {[
            {
              label: "Notifications",
              href: "/settings/notifications",
              icon: Bell,
              adminOnly: false,
            },
            ...(user?.role === "admin"
              ? [
                  { label: "Users", href: "/settings/users", icon: Users, adminOnly: true },
                  { label: "Organization", href: "/settings/organization", icon: Building2, adminOnly: true },
                  { label: "Branding", href: "/settings/branding", icon: Palette, adminOnly: true },
                  { label: "Integrations", href: "/settings/integrations", icon: Plug2, adminOnly: true },
                  { label: "Roles", href: "/settings/roles", icon: Shield, adminOnly: true },
                  { label: "API & Webhooks", href: "/settings/api", icon: KeyRound, adminOnly: true },
                  { label: "Automations", href: "/settings/automations", icon: Zap, adminOnly: true },
                ]
              : []),
          ].map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => handleNav(item.href)}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-blue-600 text-white"
                      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                  )}
                >
                  <item.icon className="h-4 w-4 flex-shrink-0" />
                  {item.label}
                </Link>
              );
            })}
        </>
      </nav>

      {/* #109 Platform setup progress bar */}
      {setupPct < 100 && (
        <div className="border-t border-slate-800 px-4 pt-3 pb-1">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-slate-400">Platform setup</span>
            <span className="text-[10px] font-semibold text-slate-300">{setupPct}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-500"
              style={{ width: `${setupPct}%` }}
            />
          </div>
        </div>
      )}

      {/* User section */}
      <div className="border-t border-slate-800 p-4">
        <div className="mb-3 flex items-center gap-3 rounded-md px-2 py-1">
          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-700 text-xs font-semibold text-white">
            {user?.display_name?.charAt(0).toUpperCase() ?? "U"}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-slate-100">
              {user?.display_name}
            </p>
            <p className="truncate text-xs text-slate-400 capitalize">
              {user?.role}
            </p>
          </div>
        </div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {resolvedTheme === "dark" ? "Dark mode" : "Light mode"}
          </span>
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            aria-label={`Switch to ${resolvedTheme === "dark" ? "light" : "dark"} mode`}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          >
            {resolvedTheme === "dark" ? (
              <Sun className="h-4 w-4" />
            ) : (
              <Moon className="h-4 w-4" />
            )}
          </button>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="w-full justify-start gap-2 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          Sign out
        </Button>
      </div>
    </aside>
  );
}
