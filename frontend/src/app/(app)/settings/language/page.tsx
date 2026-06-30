"use client";

import { useState } from "react";
import { Check, Globe } from "lucide-react";
import { useLanguage, type Language } from "@/lib/i18n/context";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const LANGUAGE_OPTIONS: { value: Language; labelKey: string; nativeLabel: string; flag: string }[] = [
  { value: "de", labelKey: "settings.languageGerman", nativeLabel: "Deutsch", flag: "🇩🇪" },
  { value: "en", labelKey: "settings.languageEnglish", nativeLabel: "English", flag: "🇬🇧" },
];

export default function LanguageSettingsPage() {
  const { language, setLanguage, t } = useLanguage();
  const [saved, setSaved] = useState(false);
  const [selected, setSelected] = useState<Language>(language);

  function handleSave() {
    setLanguage(selected);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("settings.languageTitle")}</h1>
        <p className="text-sm text-muted-foreground mt-1">{t("settings.languageDescription")}</p>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4" />
            {t("settings.languageTitle")}
          </CardTitle>
          <CardDescription>{t("settings.languageDescription")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {LANGUAGE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setSelected(opt.value)}
              className={`flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors hover:bg-muted/50 ${
                selected === opt.value
                  ? "border-primary bg-primary/5"
                  : "border-border"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{opt.flag}</span>
                <div>
                  <p className="font-medium">{opt.nativeLabel}</p>
                  <p className="text-xs text-muted-foreground">{t(opt.labelKey as Parameters<typeof t>[0])}</p>
                </div>
              </div>
              {selected === opt.value && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </button>
          ))}

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={handleSave} disabled={selected === language}>
              {t("settings.saveChanges")}
            </Button>
            {saved && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-600">
                <Check className="h-3.5 w-3.5" />
                {t("settings.languageSaved")}
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
