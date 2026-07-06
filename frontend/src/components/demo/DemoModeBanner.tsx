"use client";

import { Clapperboard, X } from "lucide-react";
import { exitDemoMode, isDemoMode } from "@/lib/demo";
import { useLanguage } from "@/lib/i18n/context";

export function DemoModeBanner() {
  const { t } = useLanguage();

  if (!isDemoMode()) return null;

  return (
    <div className="flex items-center justify-between bg-amber-500 px-4 py-2 text-sm font-medium text-white">
      <div className="flex items-center gap-2">
        <Clapperboard className="h-4 w-4 flex-shrink-0" />
        <span>{t("demo.bannerText" as Parameters<typeof t>[0])}</span>
      </div>
      <button
        onClick={exitDemoMode}
        className="flex items-center gap-1.5 rounded-md border border-white/30 bg-white/10 px-3 py-1 text-xs font-semibold hover:bg-white/20 transition-colors"
      >
        <X className="h-3 w-3" />
        {t("demo.exitButton" as Parameters<typeof t>[0])}
      </button>
    </div>
  );
}
