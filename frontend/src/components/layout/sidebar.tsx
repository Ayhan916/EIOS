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
  ChevronRight,
  ClipboardCheck,
  FileCode,
  FileText,
  KeyRound,
  LayoutDashboard,
  Layers,
  Leaf,
  LogOut,
  Network,
  PlayCircle,
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
  MessageCircle,
  Package,
  Link2,
  Moon,
  Sun,
  Wind,
  BookOpen,
  Fingerprint,
  ScrollText,
  Megaphone,
  ListOrdered,
  Activity,
  Scale,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth/context";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/components/theme-provider";
import { listNotifications } from "@/lib/api/notifications";
import { useLanguage, type TranslationKey } from "@/lib/i18n/context";
import { useReadiness } from "@/hooks/use-readiness";

// ─── Nav section definitions ──────────────────────────────────────────────────

interface NavItem {
  labelKey: TranslationKey;
  href: string;
  icon: React.ElementType;
  badge?: string;
  roleGuard?: string[];
}

interface NavSection {
  id: string;
  labelKey: TranslationKey;
  icon: React.ElementType;
  items: NavItem[];
  roleGuard?: string[];
  color?: string;
}

const NAV_SECTIONS: NavSection[] = [
  // ── 1. Lieferketten-Management ───────────────────────────────────────────────
  {
    id: "supply-chain",
    labelKey: "nav.supplyChain",
    icon: Link2,
    color: "text-blue-400",
    items: [
      { labelKey: "nav.suppliers",            href: "/suppliers",              icon: Briefcase },
      { labelKey: "nav.supplierSegmentation",  href: "/suppliers/segmentation",  icon: ShieldAlert },
      { labelKey: "nav.geoHeatmap",            href: "/suppliers/geo-heatmap",   icon: Globe },
      { labelKey: "nav.certificates",          href: "/suppliers/certificates",  icon: CheckSquare },
      { labelKey: "nav.supplierNetwork",  href: "/network",           icon: Network },
      { labelKey: "nav.activityChain",    href: "/activity-chain",    icon: Link2 },
      { labelKey: "nav.supplierPortal",   href: "/suppliers/portal", icon: Users },
      { labelKey: "nav.dueDiligence",     href: "/due-diligence",    icon: Shield },
      { labelKey: "nav.dpp",              href: "/dpp",               icon: ClipboardCheck },
    ],
  },
  // ── 2. Risiko & Bewertung ────────────────────────────────────────────────────
  {
    id: "risk",
    labelKey: "nav.risk",
    icon: AlertTriangle,
    color: "text-amber-400",
    items: [
      { labelKey: "nav.assessments",         href: "/assessments",           icon: FileText },
      { labelKey: "nav.assessmentSchedules", href: "/assessments/schedules", icon: CalendarDays },
      { labelKey: "nav.evidence",            href: "/evidence",              icon: Upload },
      { labelKey: "nav.findings",               href: "/findings",               icon: AlertTriangle },
      { labelKey: "nav.correctiveActionPlans", href: "/corrective-action-plans", icon: ClipboardList },
      { labelKey: "nav.risks",               href: "/risks",                 icon: ShieldAlert },
      { labelKey: "nav.recommendations",     href: "/recommendations",       icon: CheckSquare },
    ],
  },
  // ── 3. Überwachung & Intelligence ────────────────────────────────────────────
  {
    id: "monitoring",
    labelKey: "nav.monitoring",
    icon: Radio,
    color: "text-cyan-400",
    items: [
      { labelKey: "nav.intelligence", href: "/intelligence", icon: Cpu },
      { labelKey: "nav.sectorRisk",   href: "/sector-risk",  icon: Layers },
    ],
  },
  // ── 4. Compliance & Regulatorik ──────────────────────────────────────────────
  {
    id: "compliance",
    labelKey: "nav.complianceSection",
    icon: Shield,
    color: "text-rose-400",
    items: [
      { labelKey: "nav.complianceCenter", href: "/compliance/center",       icon: Shield },
      { labelKey: "nav.regulatoryHub",    href: "/regulatory",               icon: ClipboardList },
      { labelKey: "nav.taxonomy",         href: "/financial-esg/taxonomy",   icon: BookOpen },
      { labelKey: "nav.scCompliance",     href: "/compliance/supply-chain",  icon: ShieldCheck },
      { labelKey: "nav.grievances",       href: "/compliance/grievances",    icon: Megaphone },
      { labelKey: "nav.stakeholders",     href: "/stakeholders",             icon: Users },
      { labelKey: "nav.ddGovernance",     href: "/governance",               icon: ScrollText },
      { labelKey: "nav.remedyCases",             href: "/remedy-cases",             icon: Scale },
      { labelKey: "nav.effectiveness",          href: "/effectiveness",             icon: Activity },
      { labelKey: "nav.scoping",                href: "/scoping",                   icon: Target },
      { labelKey: "nav.contractualAssurance",   href: "/contractual-assurance",     icon: FileText },
      { labelKey: "nav.smeSupport",             href: "/sme-support",               icon: Building2 },
      { labelKey: "nav.readiness",              href: "/readiness",                 icon: ShieldCheck },
      { labelKey: "nav.impactAssessment",       href: "/impact-assessment",          icon: Zap },
      { labelKey: "nav.boardSignoff",            href: "/board-signoff",              icon: ClipboardCheck },
      { labelKey: "nav.supplierAssessments",     href: "/supplier-assessments",       icon: ClipboardList },
      { labelKey: "nav.esapExport",              href: "/esap-export",                icon: ScrollText },
      { labelKey: "nav.thresholdMonitor",        href: "/threshold-monitor",          icon: BarChart3 },
      { labelKey: "nav.regulatoryRadar",         href: "/regulatory-radar",           icon: Radio },
      { labelKey: "nav.prioritization",         href: "/compliance/prioritization", icon: ListOrdered },
    ],
  },
  // ── 5. Nachhaltigkeit ────────────────────────────────────────────────────────
  {
    id: "sustainability",
    labelKey: "nav.sustainability",
    icon: Leaf,
    color: "text-emerald-400",
    items: [
      { labelKey: "nav.sustainabilityObjectives",  href: "/sustainability/objectives",           icon: Target },
      { labelKey: "nav.sustainabilityKpis",        href: "/sustainability/kpis",                 icon: BarChart3 },
      { labelKey: "nav.scienceBasedTargets",       href: "/sustainability/science-based-targets", icon: FlaskConical },
      { labelKey: "nav.ghgCalculator",             href: "/sustainability/ghg",                  icon: Wind },
      { labelKey: "nav.scope3Carbon",              href: "/scope3",                              icon: Leaf },
      { labelKey: "nav.sustainabilityInitiatives", href: "/sustainability/initiatives",          icon: TrendingDown },
    ],
  },
  // ── 6. Finanzen & Strategie ──────────────────────────────────────────────────
  {
    id: "finance-strategy",
    labelKey: "nav.financeStrategy",
    icon: LineChart,
    color: "text-violet-400",
    items: [
      { labelKey: "nav.carbonEconomics", href: "/financial-esg/carbon-economics", icon: Zap },
      { labelKey: "nav.digitalTwin",     href: "/strategy/digital-twin",           icon: Cpu },
      { labelKey: "nav.scenarios",       href: "/strategy/scenarios",              icon: GitBranch },
      { labelKey: "nav.forecasts",       href: "/strategy/forecasts",              icon: BarChart3 },
      { labelKey: "nav.commercial",      href: "/commercial",                      icon: TrendingUp },
    ],
  },
  // ── 7. ESG Operating System ──────────────────────────────────────────────────
  {
    id: "esg-os",
    labelKey: "nav.esgOs",
    icon: Layers,
    color: "text-purple-400",
    items: [
      { labelKey: "nav.processOverview", href: "/process",                     icon: Network },
      { labelKey: "nav.osDashboard",     href: "/operating-system/dashboard",  icon: LayoutDashboard },
      { labelKey: "nav.programs",        href: "/operating-system/programs",   icon: Layers },
      { labelKey: "nav.calendar",        href: "/operating-system/calendar",   icon: CalendarDays },
      { labelKey: "nav.controls",        href: "/operating-system/controls",   icon: Shield },
      { labelKey: "nav.okrs",            href: "/operating-system/okrs",       icon: Target },
    ],
  },
  // ── 8. Reporting & Disclosure ────────────────────────────────────────────────
  {
    id: "reporting",
    labelKey: "nav.reporting",
    icon: FileText,
    color: "text-teal-400",
    items: [
      { labelKey: "nav.reports",    href: "/reports",    icon: FileText },
      { labelKey: "nav.disclosure", href: "/disclosure", icon: ScrollText },
    ],
  },
  // ── 9. AI & Plattform ────────────────────────────────────────────────────────
  {
    id: "ai-governance",
    labelKey: "nav.aiGovernance",
    icon: Bot,
    color: "text-sky-400",
    items: [
      { labelKey: "nav.copilot",         href: "/copilot",                  icon: MessageCircle },
      { labelKey: "nav.knowledgeBase",   href: "/knowledge",                icon: BookOpen },
      { labelKey: "nav.aiModels",        href: "/ai-governance/models",     icon: Layers },
      { labelKey: "nav.aiMonitoring",    href: "/ai-governance/monitoring", icon: Radio },
      { labelKey: "nav.workflowMonitor", href: "/workflows",                icon: PlayCircle },
      { labelKey: "nav.evaluation",      href: "/evaluation",               icon: Activity },
      { labelKey: "nav.benchmarks",      href: "/benchmarks",               icon: BarChart3, roleGuard: ["admin"] },
      { labelKey: "nav.missionControl",  href: "/mission-control",          icon: Zap, roleGuard: ["admin"] },
      { labelKey: "nav.selfImprovement", href: "/self-improvement",         icon: TrendingUp, roleGuard: ["admin"] },
    ],
  },
  // ── 10. Executive ────────────────────────────────────────────────────────────
  {
    id: "executive",
    labelKey: "nav.executive",
    icon: BarChart3,
    color: "text-blue-300",
    roleGuard: ["executive", "admin"],
    items: [
      { labelKey: "nav.executiveSummary",  href: "/executive",               icon: BarChart3 },
      { labelKey: "nav.boardSummary",      href: "/executive/board-summary", icon: ScrollText },
      { labelKey: "nav.executiveDecisions", href: "/executive/decisions",    icon: CheckSquare },
    ],
  },
  // ── 11. Administration ───────────────────────────────────────────────────────
  {
    id: "enterprise",
    labelKey: "nav.enterprise",
    icon: Building2,
    color: "text-slate-300",
    roleGuard: ["admin", "enterprise_admin", "bu_admin", "regional_admin"],
    items: [
      { labelKey: "nav.businessUnits",           href: "/enterprise/business-units", icon: Building2 },
      { labelKey: "nav.regions",                 href: "/enterprise/regions",        icon: Globe },
      { labelKey: "nav.enterpriseIdentity",      href: "/enterprise/identity",       icon: KeyRound },
      { labelKey: "nav.enterpriseSso",           href: "/enterprise/sso",            icon: Fingerprint },
      { labelKey: "nav.enterprisePolicies",      href: "/enterprise/policies",       icon: ClipboardList },
      { labelKey: "nav.enterpriseNotifications", href: "/enterprise/notifications",  icon: Bell },
      { labelKey: "nav.enterpriseAudit",         href: "/enterprise/audit",          icon: CheckSquare },
      { labelKey: "nav.auditLog",                href: "/auditor",                   icon: ShieldCheck },
      { labelKey: "nav.integrations",            href: "/integrations",              icon: Puzzle },
      { labelKey: "nav.developer",               href: "/developer",                 icon: FileCode, roleGuard: ["admin"] },
    ],
  },
];

// ─── Readiness: which pipeline steps belong to each sidebar section ───────────

const SECTION_STEPS: Record<string, string[]> = {
  "supply-chain": ["onboard"],
  "risk":         ["plan", "assess", "findings", "risks", "recommendations"],
  "esg-os":       ["remediation", "verification"],
  "reporting":    ["reporting"],
};

// ─── Collapsible section component ───────────────────────────────────────────

function SectionBlock({
  section,
  isOpen,
  onToggle,
  isActive,
  onNav,
  t,
  warningLevel,
  userRole,
}: {
  section: NavSection;
  isOpen: boolean;
  onToggle: () => void;
  isActive: (href: string) => boolean;
  onNav: (href: string) => void;
  t: (key: TranslationKey) => string;
  warningLevel: "error" | "warning" | null;
  userRole?: string;
}) {
  const SectionIcon = section.icon;
  const hasActiveChild = section.items.some((i) => isActive(i.href));

  return (
    <div>
      <button
        onClick={onToggle}
        className={cn(
          "mt-1 flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-widest transition-colors",
          hasActiveChild
            ? "text-slate-200"
            : "text-slate-500 hover:text-slate-300"
        )}
      >
        <SectionIcon className={cn("h-3.5 w-3.5 flex-shrink-0", section.color)} />
        <span className="flex-1 text-left">{t(section.labelKey)}</span>
        {warningLevel && (
          <span className={cn(
            "h-2 w-2 rounded-full shrink-0",
            warningLevel === "error" ? "bg-red-500" : "bg-amber-400"
          )} title={warningLevel === "error" ? "Aktion erforderlich" : "Daten unvollständig"} />
        )}
        {isOpen ? (
          <ChevronDown className="h-3 w-3 text-slate-600" />
        ) : (
          <ChevronRight className="h-3 w-3 text-slate-600" />
        )}
      </button>

      {isOpen && (
        <div className="mt-0.5 space-y-0.5 pl-2">
          {section.items.filter((item) => !item.roleGuard || item.roleGuard.includes(userRole ?? "")).map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => onNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{t(item.labelKey)}</span>
                {item.badge && (
                  <span className="text-[9px] font-bold bg-blue-500 text-white rounded px-1 py-0.5">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { resolvedTheme, setTheme } = useTheme();
  const { t } = useLanguage();
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  function getActiveSectionId(): string | null {
    for (const section of NAV_SECTIONS) {
      if (section.items.some((i) => pathname === i.href || pathname.startsWith(`${i.href}/`))) {
        return section.id;
      }
    }
    return null;
  }

  const [openSections, setOpenSections] = useState<Set<string>>(() => {
    const active = getActiveSectionId();
    return new Set(active ? [active] : ["risk"]);
  });

  useEffect(() => {
    setPendingHref(null);
    const active = getActiveSectionId();
    if (active) {
      setOpenSections((prev) => new Set([...prev, active]));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  function toggleSection(id: string) {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

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
  const unreadCount =
    notifData?.items.filter((n: { is_read: boolean }) => !n.is_read).length ?? 0;

  const { data: readinessData } = useReadiness();
  function getSectionWarning(sectionId: string): "error" | "warning" | null {
    const steps = SECTION_STEPS[sectionId];
    if (!steps || !readinessData) return null;
    const relevant = readinessData.steps.filter((s) => steps.includes(s.key));
    if (relevant.some((s) => s.status === "error")) return "error";
    if (relevant.some((s) => s.status === "warning")) return "warning";
    return null;
  }

  const visibleSections = NAV_SECTIONS.filter((s) => {
    if (!s.roleGuard) return true;
    return s.roleGuard.includes(user?.role ?? "");
  });

  const settingsItems: { labelKey: TranslationKey; href: string; icon: React.ElementType }[] = [
    { labelKey: "settings.notifications", href: "/settings/notifications", icon: Bell },
    { labelKey: "settings.language", href: "/settings/language", icon: Globe },
    ...(user?.role === "admin"
      ? ([
          { labelKey: "settings.users", href: "/settings/users", icon: Users },
          { labelKey: "settings.organization", href: "/settings/organization", icon: Building2 },
          { labelKey: "settings.branding", href: "/settings/branding", icon: Palette },
          { labelKey: "settings.integrations", href: "/settings/integrations", icon: Plug2 },
          { labelKey: "settings.roles", href: "/settings/roles", icon: Shield },
          { labelKey: "settings.api", href: "/settings/api", icon: KeyRound },
        ] as const)
      : []),
  ];

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
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {/* Home — always visible */}
        <div className="mb-1 space-y-0.5">
          {([
            { labelKey: "nav.dashboard" as TranslationKey, href: "/dashboard", icon: LayoutDashboard, showBadge: false },
            { labelKey: "nav.inbox" as TranslationKey, href: "/notifications", icon: Bell, showBadge: true },
          ]).map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
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
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span className="flex-1">{t(item.labelKey)}</span>
                {item.showBadge && unreadCount > 0 && (
                  <span className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        {/* Divider */}
        <div className="my-2 border-t border-slate-800" />

        {/* Collapsible sections */}
        <div className="space-y-0.5">
          {visibleSections.map((section) => (
            <SectionBlock
              key={section.id}
              section={section}
              isOpen={openSections.has(section.id)}
              onToggle={() => toggleSection(section.id)}
              isActive={isActive}
              onNav={handleNav}
              t={t}
              warningLevel={getSectionWarning(section.id)}
              userRole={user?.role}
            />
          ))}
        </div>

        {/* Settings */}
        <div className="mt-3 border-t border-slate-800 pt-3 space-y-0.5">
          <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            {t("settings.title")}
          </p>
          {settingsItems.map((item) => {
            const active = isActive(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => handleNav(item.href)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                )}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {t(item.labelKey)}
              </Link>
            );
          })}
        </div>
      </nav>

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
            {resolvedTheme === "dark" ? t("settings.themeDark") : t("settings.themeLight")}
          </span>
          <button
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            aria-label={t("settings.theme")}
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
          {t("auth.signOut")}
        </Button>
      </div>
    </aside>
  );
}
