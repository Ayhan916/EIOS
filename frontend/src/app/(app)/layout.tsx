"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { CommandPalette } from "@/components/layout/command-palette";
import { FeatureSpotlight } from "@/components/layout/feature-spotlight";
import { HelpButton } from "@/components/layout/help-sidebar";
import { KnowledgeSearchDrawer } from "@/components/layout/knowledge-search";
import { NotificationBell } from "@/components/layout/notification-bell";
import { QuickCreateFAB } from "@/components/layout/quick-create-fab";
import { NavigationProgress } from "@/components/layout/navigation-progress";
import { Sidebar } from "@/components/layout/sidebar";
import { Spinner } from "@/components/ui/spinner";
import { DemoModeBanner } from "@/components/demo/DemoModeBanner";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const { t } = useLanguage();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <NavigationProgress />
      {/* #104 Feature spotlight for first-time users */}
      <FeatureSpotlight />
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <CommandPalette />
        <header className="flex h-12 items-center justify-between border-b border-border bg-background px-6">
          <div className="flex items-center gap-2">
            {/* #112 Cmd+K — #107 tooltip via title */}
            <button
              onClick={() => {
                const evt = new KeyboardEvent("keydown", { key: "k", metaKey: true, bubbles: true });
                window.dispatchEvent(evt);
              }}
              title="Global search (⌘K)"
              className="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted transition-colors"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
              <span>{t("header.search")}</span>
              <kbd className="ml-2 rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">{t("header.searchShortcut")}</kbd>
            </button>
            {/* #83 Knowledge base search */}
            <KnowledgeSearchDrawer />
            {/* #106 Context-sensitive help */}
            <HelpButton />
          </div>
          <NotificationBell />
        </header>
        <DemoModeBanner />
        <main className="flex-1 overflow-y-auto">
          <div className="p-8">{children}</div>
        </main>
      </div>
      <QuickCreateFAB />
    </div>
  );
}
