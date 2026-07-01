"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Image, Palette, Save } from "lucide-react";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

interface OrgSettings {
  organization_id: string;
  company_name_override: string | null;
  logo_url: string | null;
  primary_color: string | null;
  favicon_url: string | null;
  integrations_configured: string[];
}

const PRESET_COLORS = [
  "#2563eb", // blue-600
  "#16a34a", // green-600
  "#9333ea", // purple-600
  "#dc2626", // red-600
  "#ea580c", // orange-600
  "#0891b2", // cyan-600
  "#0f172a", // slate-900
  "#374151", // gray-700
];

export default function BrandingPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: settings, isLoading } = useQuery<OrgSettings>({
    queryKey: ["org-settings"],
    queryFn: async () => {
      const res = await apiClient.get("/commercial/organizations/me/settings");
      return res.data;
    },
  });

  const [companyName, setCompanyName] = useState<string>("");
  const [logoUrl, setLogoUrl] = useState<string>("");
  const [primaryColor, setPrimaryColor] = useState<string>("#2563eb");
  const [faviconUrl, setFaviconUrl] = useState<string>("");
  const [initialized, setInitialized] = useState(false);

  if (settings && !initialized) {
    setCompanyName(settings.company_name_override ?? "");
    setLogoUrl(settings.logo_url ?? "");
    setPrimaryColor(settings.primary_color ?? "#2563eb");
    setFaviconUrl(settings.favicon_url ?? "");
    setInitialized(true);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, string | null> = {};
      if (companyName.trim()) body.company_name_override = companyName.trim();
      else body.company_name_override = null;
      if (logoUrl.trim()) body.logo_url = logoUrl.trim();
      else body.logo_url = null;
      if (faviconUrl.trim()) body.favicon_url = faviconUrl.trim();
      else body.favicon_url = null;
      const colorVal = /^#[0-9A-Fa-f]{6}$/.test(primaryColor) ? primaryColor : null;
      if (colorVal) body.primary_color = colorVal;
      await apiClient.put("/commercial/organizations/me/settings", body);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["org-settings"] }),
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  const previewColor = /^#[0-9A-Fa-f]{6}$/.test(primaryColor) ? primaryColor : "#2563eb";

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{t("sec.brandingTitle")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("sec.brandingSubtitle")}
        </p>
      </div>

      {/* Live Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Palette className="h-4 w-4" />
            {t("sec.brandingTitle")}
          </CardTitle>
          <CardDescription>{t("sec.brandingSubtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 rounded-lg p-4 w-fit" style={{ backgroundColor: "#0f172a" }}>
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{ backgroundColor: previewColor }}
            >
              {logoUrl ? (
                <img src={logoUrl} alt="logo" className="h-6 w-6 object-contain rounded" onError={() => {}} />
              ) : (
                <span className="text-white text-xs font-bold">
                  {(companyName || "EIOS").charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <div>
              <p className="text-sm font-bold tracking-tight text-white">{companyName || "EIOS"}</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">ESG Intelligence</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Settings form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("sec.orgTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <label className="block text-sm font-medium mb-1.5">{t("sec.companyName")}</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Leave blank to use default (EIOS)"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground mt-1">Replaces "EIOS" in the sidebar and browser title.</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">{t("sec.primaryColor")}</label>
            <div className="flex items-center gap-3">
              <input
                type="color"
                value={previewColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                className="h-9 w-9 rounded cursor-pointer border border-input p-0.5"
              />
              <input
                type="text"
                value={primaryColor}
                onChange={(e) => setPrimaryColor(e.target.value)}
                placeholder="#2563eb"
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm font-mono shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <p className="text-xs text-muted-foreground mt-1.5">
              Preset colors:
              <span className="ml-2 inline-flex gap-1.5 flex-wrap">
                {PRESET_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setPrimaryColor(c)}
                    className="h-5 w-5 rounded-full border-2 transition-transform hover:scale-110"
                    style={{ backgroundColor: c, borderColor: primaryColor === c ? "white" : c }}
                    title={c}
                  />
                ))}
              </span>
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Image className="h-4 w-4" />
            Logo & Favicon
          </CardTitle>
          <CardDescription>{t("sec.logoUrl")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-1.5">{t("sec.logoUrl")}</label>
            <div className="flex items-center gap-3">
              <input
                type="url"
                value={logoUrl}
                onChange={(e) => setLogoUrl(e.target.value)}
                placeholder="https://your-cdn.com/logo.png"
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              {logoUrl && (
                <img
                  src={logoUrl}
                  alt="logo preview"
                  className="h-9 w-9 rounded border object-contain"
                  onError={(e) => (e.currentTarget.style.display = "none")}
                />
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Square PNG or SVG, min 32×32px. Shown in the sidebar header.</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5">{t("sec.logoUrl")} (Favicon)</label>
            <input
              type="url"
              value={faviconUrl}
              onChange={(e) => setFaviconUrl(e.target.value)}
              placeholder="https://your-cdn.com/favicon.ico"
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground mt-1">16×16 or 32×32 .ico or .png shown in browser tab.</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center gap-3">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="gap-2"
        >
          {saveMutation.isPending ? <Spinner size="sm" /> : <Save className="h-4 w-4" />}
          {t("settings.saveChanges")}
        </Button>
        {saveMutation.isSuccess && (
          <span className="flex items-center gap-1.5 text-sm text-emerald-600 font-medium">
            <CheckCircle2 className="h-4 w-4" /> {t("settings.orgSaved")}
          </span>
        )}
        {saveMutation.isError && (
          <span className="text-sm text-red-600">{t("settings.adminOnly")}</span>
        )}
      </div>
    </div>
  );
}
