"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useLanguage } from "@/lib/i18n/context";
import {
  Package,
  AlertTriangle,
  Network,
  ShieldCheck,
  Leaf,
  Info,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import {
  getProduct,
  listBOM,
  getProductCompliance,
  getProductSustainability,
  deleteBOMItem,
  type Product,
  type ProductBOMItem,
  type ProductComplianceSummary,
  type ProductSustainabilitySummary,
} from "@/lib/api/product";

const TABS = ["Overview", "BOM", "Compliance", "Sustainability"] as const;
type Tab = typeof TABS[number];

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  ACTIVE: "bg-green-100 text-green-800",
  DISCONTINUED: "bg-orange-100 text-orange-800",
  ARCHIVED: "bg-gray-100 text-gray-400",
};

const COMPLIANCE_STATUS_COLORS: Record<string, string> = {
  COMPLIANT: "bg-green-100 text-green-800",
  NON_COMPLIANT: "bg-red-100 text-red-800",
  PARTIALLY_COMPLIANT: "bg-yellow-100 text-yellow-800",
  UNDER_ASSESSMENT: "bg-blue-100 text-blue-800",
  EXEMPT: "bg-purple-100 text-purple-800",
  UNKNOWN: "bg-gray-100 text-gray-600",
};

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ product }: { product: Product }) {
  const { t } = useLanguage();
  const fields: [string, string | number | boolean | null][] = [
    [t("common.type"), product.product_type.replace(/_/g, " ")],
    [t("common.status"), product.product_status],
    [t("products.sku"), product.sku],
    ["GTIN / Barcode", product.gtin],
    ["Internal Code", product.internal_code],
    [t("common.category"), product.category],
    ["Brand", product.brand],
    ["Unit of Measure", product.unit_of_measure],
    [t("products.weight"), product.weight_kg],
    [t("products.manufacturer"), product.country_of_manufacture],
    [t("products.targetMarket"), product.target_market],
    ["Regulated Product", product.is_regulated_product ? `${t("common.yes")} (DPP scope)` : t("common.no")],
  ];

  return (
    <div className="space-y-6">
      {product.description && (
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">{product.description}</p>
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader><CardTitle className="text-base">Properties</CardTitle></CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
            {fields.map(([label, value]) =>
              value != null && value !== "" ? (
                <div key={label}>
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="text-sm font-medium mt-0.5">{String(value)}</dd>
                </div>
              ) : null
            )}
          </dl>
        </CardContent>
      </Card>
      {product.notes && (
        <Card>
          <CardHeader><CardTitle className="text-base">{t("common.notes")}</CardTitle></CardHeader>
          <CardContent><p className="text-sm">{product.notes}</p></CardContent>
        </Card>
      )}
    </div>
  );
}

// ── BOM Tab ───────────────────────────────────────────────────────────────────

function BOMTab({ productId }: { productId: string }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["product-bom", productId],
    queryFn: () => listBOM(productId),
  });
  const items: ProductBOMItem[] = data?.data ?? [];

  const del = useMutation({
    mutationFn: (itemId: string) => deleteBOMItem(productId, itemId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["product-bom", productId] }),
  });

  const totalPct = items.reduce((s, i) => s + (i.weight_pct ?? 0), 0);

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Bill of Materials ({items.length} materials)</h3>
        {totalPct > 0 && (
          <span className="text-sm text-muted-foreground">{totalPct.toFixed(1)}% by weight covered</span>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">No BOM entries yet. Add materials to build the bill of materials.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.id} className={item.is_substance_of_concern ? "border-orange-300" : ""}>
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-start gap-3">
                  {item.is_substance_of_concern && (
                    <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <p className="text-sm font-medium font-mono">{item.material_id}</p>
                    <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                      {item.weight_pct != null && <span>{item.weight_pct}% by weight</span>}
                      {item.quantity != null && <span>{item.quantity} {item.unit ?? ""}</span>}
                      {item.is_substance_of_concern && <span className="text-orange-600 font-medium">Substance of concern</span>}
                      {item.notes && <span>{item.notes}</span>}
                    </div>
                  </div>
                </div>
                {item.weight_pct != null && (
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${Math.min(item.weight_pct, 100)}%` }}
                      />
                    </div>
                    <Button
                      variant="ghost" size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => del.mutate(item.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Compliance Tab ────────────────────────────────────────────────────────────

function ComplianceTab({ productId }: { productId: string }) {
  const { t } = useLanguage();
  const { data, isLoading } = useQuery({
    queryKey: ["product-compliance", productId],
    queryFn: () => getProductCompliance(productId),
  });
  const items: ProductComplianceSummary[] = data?.data ?? [];

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  const nonCompliant = items.filter((i) => i.worst_status === "NON_COMPLIANT").length;
  const compliant = items.filter((i) => i.worst_status === "COMPLIANT").length;

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Aggregated from compliance flags of all BOM materials.
      </p>
      {items.length > 0 && (
        <div className="flex gap-4">
          <div className="flex-1 rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-green-600">{compliant}</div>
            <div className="text-xs text-muted-foreground">{t("scCompliance.compliant")}</div>
          </div>
          <div className="flex-1 rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold text-red-600">{nonCompliant}</div>
            <div className="text-xs text-muted-foreground">{t("scCompliance.nonCompliantStatus")}</div>
          </div>
          <div className="flex-1 rounded-lg border p-3 text-center">
            <div className="text-2xl font-bold">{items.length}</div>
            <div className="text-xs text-muted-foreground">Regulations tracked</div>
          </div>
        </div>
      )}
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm py-8 text-center">
          No compliance data yet. Add materials with compliance flags to the BOM.
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((c) => (
            <Card key={c.regulation} className={c.worst_status === "NON_COMPLIANT" ? "border-red-300" : ""}>
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{c.regulation.replace(/_/g, " ")}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${COMPLIANCE_STATUS_COLORS[c.worst_status] ?? "bg-gray-100"}`}>
                      {c.worst_status.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {c.material_count} material{c.material_count !== 1 ? "s" : ""}
                    {c.non_compliant_material_ids.length > 0 && ` · ${c.non_compliant_material_ids.length} non-compliant`}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Sustainability Tab ────────────────────────────────────────────────────────

function SustainabilityTab({ productId }: { productId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["product-sustainability", productId],
    queryFn: () => getProductSustainability(productId),
  });
  const s: ProductSustainabilitySummary | undefined = data?.data;

  if (isLoading) return <div className="flex justify-center py-12"><Spinner /></div>;

  if (!s || !s.has_data) {
    return (
      <p className="text-muted-foreground text-sm py-8 text-center">
        No LCA data yet. Add materials with sustainability metrics to the BOM.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Product Carbon Footprint (PCF) computed from BOM × material LCA data.
        {s.weight_coverage_pct < 100 && (
          <span className="ml-1 text-orange-600">
            Coverage: {s.weight_coverage_pct}% by weight.
          </span>
        )}
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">
              {s.product_carbon_footprint_kg_co2e_per_kg != null
                ? s.product_carbon_footprint_kg_co2e_per_kg
                : "—"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">kg CO₂e/kg (PCF)</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">
              {s.product_water_footprint_l_per_kg != null
                ? s.product_water_footprint_l_per_kg
                : "—"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">L/kg water</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-bold">{s.bom_materials_with_lca}/{s.bom_materials_total}</div>
            <div className="text-xs text-muted-foreground mt-1">Materials with LCA data</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className={`text-2xl font-bold ${s.materials_with_concern > 0 ? "text-orange-600" : "text-green-600"}`}>
              {s.materials_with_concern}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Substances of concern</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span>Weight coverage</span>
            <span className="font-medium">{s.weight_coverage_pct}%</span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 rounded-full transition-all"
              style={{ width: `${Math.min(s.weight_coverage_pct, 100)}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            PCF is weighted by material composition. 100% coverage = all materials have LCA data.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  const { data, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => getProduct(id),
    enabled: !!id,
  });

  const product: Product | undefined = data?.data;

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-96"><Spinner /></div>;
  }
  if (!product) {
    return <div className="p-6 text-center text-muted-foreground">{t("products.noProductsFound")}</div>;
  }

  const TAB_LABELS: Record<Tab, string> = {
    Overview: t("products.tabOverview"),
    BOM: t("products.tabBom"),
    Compliance: t("products.tabCompliance"),
    Sustainability: t("materials.tabSustainability"),
  };

  const TAB_ICONS: Record<Tab, React.ReactNode> = {
    Overview: <Info className="h-4 w-4" />,
    BOM: <Network className="h-4 w-4" />,
    Compliance: <ShieldCheck className="h-4 w-4" />,
    Sustainability: <Leaf className="h-4 w-4" />,
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-purple-50">
          <Package className="h-7 w-7 text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold truncate">{product.name}</h1>
            {product.is_regulated_product && (
              <span className="flex items-center gap-1 text-xs font-medium bg-red-100 text-red-700 px-2 py-1 rounded-full">
                <AlertTriangle className="h-3 w-3" />
                Regulated
              </span>
            )}
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_COLORS[product.product_status] ?? "bg-gray-100"}`}>
              {product.product_status}
            </span>
          </div>
          <div className="flex gap-4 mt-1 text-sm text-muted-foreground flex-wrap">
            <span>{product.product_type.replace(/_/g, " ")}</span>
            {product.sku && <span>{t("products.sku")}: {product.sku}</span>}
            {product.gtin && <span>{t("products.gtin")}: {product.gtin}</span>}
            {product.brand && <span>{product.brand}</span>}
            {product.target_market && <span>{product.target_market}</span>}
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

      <div>
        {activeTab === "Overview" && <OverviewTab product={product} />}
        {activeTab === "BOM" && <BOMTab productId={product.id} />}
        {activeTab === "Compliance" && <ComplianceTab productId={product.id} />}
        {activeTab === "Sustainability" && <SustainabilityTab productId={product.id} />}
      </div>
    </div>
  );
}
