"use client";

import { AlertTriangle, ArrowRight, Database, Upload, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useStepReadiness } from "@/hooks/use-readiness";
import type { MissingItem } from "@/lib/api/pipeline";

const TYPE_ICON = {
  upload:  Upload,
  data:    Database,
  action:  ArrowRight,
} as const;

const STATUS_STYLE = {
  warning: {
    wrap:  "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
    icon:  "text-amber-600",
    title: "text-amber-900 dark:text-amber-200",
    item:  "text-amber-800 dark:text-amber-300",
  },
  error: {
    wrap:  "bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800",
    icon:  "text-red-600",
    title: "text-red-900 dark:text-red-200",
    item:  "text-red-800 dark:text-red-300",
  },
};

function ItemRow({ item, cls }: { item: MissingItem; cls: string }) {
  const Icon = TYPE_ICON[item.type] ?? ArrowRight;
  const prefix =
    item.type === "upload" ? "Bitte hochladen:" :
    item.type === "data"   ? "Fehlende Daten:" : "";
  const countStr = item.count > 0 ? ` (${item.count})` : "";

  return (
    <li className={`flex items-center gap-2 text-sm ${cls}`}>
      <Icon className="h-3.5 w-3.5 shrink-0 opacity-70" />
      <Link
        href={item.href}
        className="underline underline-offset-2 hover:opacity-80 transition-opacity"
      >
        {prefix ? `${prefix} ` : ""}{item.label}{countStr}
      </Link>
    </li>
  );
}

interface Props {
  stepKey: string;
  className?: string;
}

export function ReadinessBanner({ stepKey, className = "" }: Props) {
  const step = useStepReadiness(stepKey);
  const [dismissed, setDismissed] = useState(false);

  if (!step || step.status === "ok" || step.missing.length === 0 || dismissed) {
    return null;
  }

  const s = STATUS_STYLE[step.status] ?? STATUS_STYLE.warning;
  const title =
    step.status === "error"
      ? "Aktion erforderlich"
      : "Informationen unvollständig";

  return (
    <div className={`mb-6 rounded-lg border px-4 py-3 ${s.wrap} ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className={`h-4 w-4 mt-0.5 shrink-0 ${s.icon}`} />
          <div className="space-y-1.5">
            <p className={`text-sm font-semibold ${s.title}`}>
              {title}
              <span className="font-normal opacity-75 ml-1">
                — damit dieser Schritt vollständig ist, fehlen folgende Angaben:
              </span>
            </p>
            <ul className="space-y-1">
              {step.missing.map((item, i) => (
                <ItemRow key={i} item={item} cls={s.item} />
              ))}
            </ul>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Banner schließen"
          className="shrink-0 opacity-50 hover:opacity-100 transition-opacity"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
