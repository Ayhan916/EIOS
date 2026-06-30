"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useLanguage } from "@/lib/i18n/context";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  FlaskConical,
  AlertTriangle,
  Leaf,
  Network,
  ShieldCheck,
  BarChart3,
  Info,
  Trash2,
  Plus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getMaterial,
  listComposition,
  listSourcing,
  listCompliance,
  listSustainability,
  deleteComposition,
  deleteSourcing,
  deleteComplianceFlag,
  type Material,
  type MaterialCompliance,
  type MaterialSourcing,
  type MaterialSustainability,
  type MaterialComposition,
} from "@/lib/api/material";

const TABS = [
  "Overview",
  "Composition",
  "Sourcing",
  "Compliance",
  "Sustainability",
] as const;
type Tab = typeof TABS[number];

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
  RESTRICTED: "bg-red-100 text-red-800",
  PHASING_OUT: "bg-orange-100 text-orange-800",
  ARCHIVED: "bg-gray-100 text-gray-600",
};

const COMPLIANCE_STATUS_COLORS: Record<string, string> = {
  COMPLIANT: "bg-green-100 text-green-800",
  NON_COMPLIANT: "bg-red-100 text-red-800",
  PARTIALLY_COMPLIANT: "bg-yellow-100 text-yellow-800",
  UNDER_ASSESSMENT: "bg-blue-100 text-blue-800",
  EXEMPT: "bg-purple-100 text-purple-800",
  UNKNOWN: "bg-gray-100 text-gray-600",
};

const SOURCING_RISK_COLORS: Record<string, string> = {
  LOW: "bg-green-100 text-green-800",
  MEDIUM: "bg-yellow-100 text-yellow-800",
  HIGH: "bg-orange-100 text-orange-800",
  CRITICAL: "bg-red-100 text-red-800",
};

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ material }: { material: Material }) {
  const { t } = useLanguage();
  const fields: [string, string | number | boolean | null][] = [
    [t("common.type"), material.material_type.replace(/_/g, " ")],
    [t("common.status"), material.material_status.replace(/_/g, " ")],
    ["Internal Code", material.internal_code],
    [t("materials.casNumber"), material.cas_number],
    ["EC Number", material.ec_number],
    ["IUPAC Name", material.iupac_name],
    ["Molecular Formula", material.molecular_formula],
    [t("materials.hsCode"), material.hs_code],
    ["UN Number", material.un_number],
    ["GHS Hazard Class", material.ghs_hazard_class],
    [t("materials.unitOfMeasure"), material.unit_of_measure],
    ["Weight per Unit (kg)", material.weight_per_unit_kg],
    [t("common.country"), material.country_of_origin],
    [t("materials.isCrm"), material.is_critical_raw_material ? t("common.yes") : t("common.no")],
    ["Recycled Content %", material.recycled_content_pct != null ? `${material.recycled_content_pct}%` : null],
  ];

  return (
    <div className="space-y-6">
      {material.description && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">{material.description}</p>
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader><CardTitle className="text-base">{t("common.details")}</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
            {fields.map(([label, value]) => (
              value != null && value !== "" ? (
                <div key={label}>
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="text-sm font-medium mt-0.5">{String(value)}</dd>
                </div>
              ) : null
            ))}
          </dl>
        </CardContent>
      </Card>
      {material.notes && (
        <Card>
          <CardHeader><CardTitle className="text-base">{t("common.notes")}</CardTitle></CardHeader>
          <CardContent><p className="text-sm">{material.notes}</p></CardContent>
        </Card>
      )}
    </div>
  );
}

// ── Composition Tab ───────────────────────────────────────────────────────────

function CompositionTab({ materialId }: { materialId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["material-composition", materialId],
    queryFn: () => listComposition(materialId),
  });
  const items: MaterialComposition[] = data?.data ?? [];

  const del = useMutation({
    mutationFn: (compositionId: string) => deleteComposition(materialId, compositionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["material-composition", materialId] }),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">{t("materials.composition")} ({items.length})</h3>
      </div>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">{t("common.noData")}</p>
      ) : (
        <div className="space-y-2">
          {items.map((c) => (
            <Card key={c.id}>
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium font-mono">{c.child_material_id}</p>
                  <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                    {c.weight_pct != null && <span>{c.weight_pct}%</span>}
                    {c.quantity != null && <span>{c.quantity} {c.unit ?? ""}</span>}
                    {c.notes && <span>{c.notes}</span>}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:text-destructive"
                  onClick={() => del.mutate(c.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sourcing Tab ──────────────────────────────────────────────────────────────

function SourcingTab({ materialId }: { materialId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["material-sourcing", materialId],
    queryFn: () => listSourcing(materialId),
  });
  const items: MaterialSourcing[] = data?.data ?? [];

  const del = useMutation({
    mutationFn: (sourcingId: string) => deleteSourcing(materialId, sourcingId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["material-sourcing", materialId] }),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">{t("materials.sourcing")} ({items.length})</h3>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">{t("common.noData")}</p>
      ) : (
        <div className="space-y-2">
          {items.map((s) => (
            <Card key={s.id}>
              <CardContent className="p-4 flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {s.is_primary && (
                    <span className="mt-0.5 text-xs font-medium bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">Primary</span>
                  )}
                  <div>
                    <p className="text-sm font-medium font-mono">{s.supplier_id}</p>
                    <div className="flex gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                      {s.country_of_origin && <span>{s.country_of_origin}</span>}
                      {s.annual_volume != null && <span>{s.annual_volume} {s.unit ?? ""}/yr</span>}
                      {s.price_per_unit_eur != null && <span>€{s.price_per_unit_eur}/{s.unit ?? "unit"}</span>}
                      {s.lead_time_days != null && <span>{s.lead_time_days}d lead time</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${SOURCING_RISK_COLORS[s.sourcing_risk] ?? "bg-gray-100"}`}>
                    {s.sourcing_risk} risk
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:text-destructive"
                    onClick={() => del.mutate(s.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Compliance Tab ────────────────────────────────────────────────────────────

function ComplianceTab({ materialId }: { materialId: string }) {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["material-compliance", materialId],
    queryFn: () => listCompliance(materialId),
  });
  const items: MaterialCompliance[] = data?.data ?? [];

  const del = useMutation({
    mutationFn: (flagId: string) => deleteComplianceFlag(materialId, flagId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["material-compliance", materialId] }),
  });

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const compliant = items.filter((c) => c.compliance_status === "COMPLIANT").length;
  const nonCompliant = items.filter((c) => c.compliance_status === "NON_COMPLIANT").length;
  const expired = items.filter((c) => c.is_expired).length;

  return (
    <div className="space-y-4">
      <div className="flex gap-4">
        <div className="flex-1 rounded-lg border p-3 text-center">
          <div className="text-2xl font-bold text-green-600">{compliant}</div>
          <div className="text-xs text-muted-foreground">{t("scCompliance.compliant")}</div>
        </div>
        <div className="flex-1 rounded-lg border p-3 text-center">
          <div className="text-2xl font-bold text-red-600">{nonCompliant}</div>
          <div className="text-xs text-muted-foreground">{t("scCompliance.nonCompliantStatus")}</div>
        </div>
        {expired > 0 && (
          <div className="flex-1 rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-orange-600">{expired}</div>
            <div className="text-xs text-muted-foreground">Expired</div>
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">{t("common.noData")}</p>
      ) : (
        <div className="space-y-2">
          {items.map((c) => (
            <Card key={c.id} className={c.is_expired ? "border-orange-300" : ""}>
              <CardContent className="p-4 flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">
                      {c.custom_regulation_name ?? c.regulation.replace(/_/g, " ")}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${COMPLIANCE_STATUS_COLORS[c.compliance_status] ?? "bg-gray-100"}`}>
                      {c.compliance_status.replace(/_/g, " ")}
                    </span>
                    {c.is_expired && (
                      <span className="text-xs font-medium bg-orange-100 text-orange-800 px-2 py-0.5 rounded-full">
                        Expired
                      </span>
                    )}
                  </div>
                  <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                    {c.assessor && <span>Assessor: {c.assessor}</span>}
                    {c.assessed_at && <span>Assessed: {new Date(c.assessed_at).toLocaleDateString()}</span>}
                    {c.valid_until && <span>Valid until: {new Date(c.valid_until).toLocaleDateString()}</span>}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive hover:text-destructive"
                  onClick={() => del.mutate(c.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sustainability Tab ────────────────────────────────────────────────────────

function SustainabilityTab({ materialId }: { materialId: string }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["material-sustainability", materialId],
    queryFn: () => listSustainability(materialId),
  });
  const items: MaterialSustainability[] = data?.data ?? [];

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">{t("materials.tabSustainability")} ({items.length})</h3>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">{t("common.noData")}</p>
      ) : (
        <div className="space-y-4">
          {items.map((s) => (
            <Card key={s.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">{s.reporting_year}</CardTitle>
                  <div className="flex items-center gap-2">
                    {s.is_third_party_verified && (
                      <span className="flex items-center gap-1 text-xs font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                        <ShieldCheck className="h-3 w-3" />
                        Verified {s.verification_standard ? `(${s.verification_standard})` : ""}
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">{s.carbon_scope.replace(/_/g, " ")}</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {s.carbon_footprint_kg_co2e_per_kg != null && (
                    <div>
                      <div className="text-xs text-muted-foreground">{t("materials.carbonFootprint")}</div>
                      <div className="text-lg font-bold">{s.carbon_footprint_kg_co2e_per_kg}</div>
                      <div className="text-xs text-muted-foreground">kg CO₂e/kg</div>
                    </div>
                  )}
                  {s.water_footprint_l_per_kg != null && (
                    <div>
                      <div className="text-xs text-muted-foreground">Water footprint</div>
                      <div className="text-lg font-bold">{s.water_footprint_l_per_kg}</div>
                      <div className="text-xs text-muted-foreground">L/kg</div>
                    </div>
                  )}
                  {s.energy_mj_per_kg != null && (
                    <div>
                      <div className="text-xs text-muted-foreground">Energy</div>
                      <div className="text-lg font-bold">{s.energy_mj_per_kg}</div>
                      <div className="text-xs text-muted-foreground">MJ/kg{s.energy_renewable_pct != null ? ` (${s.energy_renewable_pct}% renew.)` : ""}</div>
                    </div>
                  )}
                  {s.recycled_content_pct != null && (
                    <div>
                      <div className="text-xs text-muted-foreground">{t("materials.recyclability")}</div>
                      <div className="text-lg font-bold">{s.recycled_content_pct}%</div>
                      {s.recyclability_pct != null && <div className="text-xs text-muted-foreground">{s.recyclability_pct}% recyclable</div>}
                    </div>
                  )}
                </div>
                {s.data_source && (
                  <p className="text-xs text-muted-foreground mt-3">Source: {s.data_source}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MaterialDetailPage() {
  const { t } = useLanguage();
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const { data, isLoading } = useQuery({
    queryKey: ["material", id],
    queryFn: () => getMaterial(id),
    enabled: !!id,
  });

  const material: Material | undefined = data?.data;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-96">
        <Spinner />
      </div>
    );
  }

  if (!material) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        {t("error.notFound")}
      </div>
    );
  }

  const TAB_ICONS: Record<Tab, React.ReactNode> = {
    Overview: <Info className="h-4 w-4" />,
    Composition: <Network className="h-4 w-4" />,
    Sourcing: <FlaskConical className="h-4 w-4" />,
    Compliance: <ShieldCheck className="h-4 w-4" />,
    Sustainability: <Leaf className="h-4 w-4" />,
  };

  const TAB_LABELS: Record<Tab, string> = {
    Overview: t("materials.tabOverview"),
    Composition: t("materials.composition"),
    Sourcing: t("materials.tabSourcing"),
    Compliance: t("materials.tabCompliance"),
    Sustainability: t("materials.tabSustainability"),
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-blue-50">
          <FlaskConical className="h-7 w-7 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold truncate">{material.name}</h1>
            {material.is_critical_raw_material && (
              <span className="flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-800 px-2 py-1 rounded-full">
                <AlertTriangle className="h-3 w-3" />
                {t("materials.isCrm")}
              </span>
            )}
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[material.material_status] ?? "bg-gray-100"}`}>
              {material.material_status.replace(/_/g, " ")}
            </span>
          </div>
          <div className="flex gap-4 mt-1 text-sm text-muted-foreground flex-wrap">
            <span>{material.material_type.replace(/_/g, " ")}</span>
            {material.cas_number && <span>CAS {material.cas_number}</span>}
            {material.hs_code && <span>HS {material.hs_code}</span>}
            {material.internal_code && <span className="font-mono">{material.internal_code}</span>}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-1 -mb-px">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {TAB_ICONS[tab]}
              {TAB_LABELS[tab]}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === "Overview" && <OverviewTab material={material} />}
        {activeTab === "Composition" && <CompositionTab materialId={material.id} />}
        {activeTab === "Sourcing" && <SourcingTab materialId={material.id} />}
        {activeTab === "Compliance" && <ComplianceTab materialId={material.id} />}
        {activeTab === "Sustainability" && <SustainabilityTab materialId={material.id} />}
      </div>
    </div>
  );
}
