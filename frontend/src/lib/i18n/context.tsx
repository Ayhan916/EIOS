"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import de from "./de";
import en from "./en";
import type { TranslationKey } from "./de";

export type Language = "de" | "en";

const STORAGE_KEY = "eios_language";
const DEFAULT_LANG: Language = "de";

type Translations = typeof de;

const DICTIONARIES = { de, en } as unknown as Record<Language, Translations>;

interface LanguageContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANG);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Language | null;
    if (stored === "de" || stored === "en") {
      setLanguageState(stored);
    }
  }, []);

  function setLanguage(lang: Language) {
    setLanguageState(lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }

  function t(key: TranslationKey): string {
    const dict = DICTIONARIES[language] as Record<string, string>;
    return dict[key] ?? (DICTIONARIES.en as Record<string, string>)[key] ?? key;
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}

// Convenience re-export so callers only need one import
export { type TranslationKey };
