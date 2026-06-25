"use client";

import { useEffect, useState } from "react";
import { X, Bot, BarChart3, FileText, Shield, Globe, Zap, Building2, Search } from "lucide-react";
import Link from "next/link";

const STORAGE_KEY = "eios_feature_spotlight_seen";

const FEATURES = [
  { icon: Shield, color: "bg-blue-100 text-blue-700", title: "ESG Risk Management", desc: "Assess suppliers, track findings, and manage your risk register end-to-end.", href: "/assessments" },
  { icon: BarChart3, color: "bg-emerald-100 text-emerald-700", title: "Sustainability Dashboard", desc: "Monitor carbon inventory, KPIs, SBTs, and decarbonization initiatives.", href: "/sustainability" },
  { icon: FileText, color: "bg-violet-100 text-violet-700", title: "Regulatory Reporting", desc: "Generate TCFD, SFDR, GRI, CSRD, and CDP reports with one click.", href: "/reports" },
  { icon: Bot, color: "bg-orange-100 text-orange-700", title: "AI Governance", desc: "Register AI models, monitor drift, track incidents and use cases.", href: "/ai-governance/models" },
  { icon: Globe, color: "bg-teal-100 text-teal-700", title: "Financial ESG", desc: "EU Taxonomy alignment, green revenue tracking, and SFDR PAI.", href: "/financial-esg" },
  { icon: Zap, color: "bg-amber-100 text-amber-700", title: "Strategy & Forecasting", desc: "Digital twin, scenario modelling, and board simulation tools.", href: "/strategy" },
  { icon: Building2, color: "bg-slate-100 text-slate-700", title: "Enterprise Hierarchy", desc: "Manage business units, regions, and legal entities with rollup reporting.", href: "/enterprise" },
  { icon: Search, color: "bg-pink-100 text-pink-700", title: "Knowledge Base", desc: "Search evidence and compliance documentation across all frameworks.", href: "/evidence" },
];

export function FeatureSpotlight() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const seen = localStorage.getItem(STORAGE_KEY);
      if (!seen) setVisible(true);
    }
  }, []);

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-background border border-border shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="relative bg-gradient-to-br from-blue-600 to-violet-600 px-8 py-6 text-white">
          <button onClick={dismiss} className="absolute right-4 top-4 text-white/70 hover:text-white">
            <X className="h-5 w-5" />
          </button>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-blue-200 mb-1">Welcome to</p>
          <h2 className="text-2xl font-bold">EIOS Platform</h2>
          <p className="mt-1 text-sm text-blue-100">Your integrated ESG intelligence and governance platform. Here's what you can do:</p>
        </div>

        {/* Feature grid */}
        <div className="p-6 grid grid-cols-2 gap-3 max-h-96 overflow-y-auto">
          {FEATURES.map((f) => (
            <Link
              key={f.href}
              href={f.href}
              onClick={dismiss}
              className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-muted/50 transition-colors group"
            >
              <div className={`flex-shrink-0 rounded-lg p-2 ${f.color}`}>
                <f.icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold group-hover:text-primary">{f.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{f.desc}</p>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-6 py-3 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">Press <kbd className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd> anytime to search</p>
          <button
            onClick={dismiss}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Get Started →
          </button>
        </div>
      </div>
    </div>
  );
}
