"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  FlaskConical,
  AlertTriangle,
  Plus,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { listMaterials, MATERIAL_TYPES, type Material, type MaterialType, type MaterialStatus } from "@/lib/api/material";
import { useLanguage } from "@/lib/i18n/context";

const TYPE_LABELS_KEYS: Record<string, string> = {
  RAW_MATERIAL: "materials.rawMaterialLabel",
  CHEMICAL: "materials.chemicalLabel",
  METAL: "materials.metalLabel",
  PLASTIC: "materials.plasticLabel",
  TEXTILE: "materials.textileLabel",
  ELECTRONIC_COMPONENT: "materials.electronicLabel",
  PACKAGING: "materials.packaging",
  INTERMEDIATE: "materials.intermediateLabel",
  COMPOSITE: "materials.composite",
  OTHER: "materials.other",
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  UNDER_REVIEW: "bg-yellow-100 text-yellow-800",
  RESTRICTED: "bg-red-100 text-red-800",
  PHASING_OUT: "bg-orange-100 text-orange-800",
  ARCHIVED: "bg-gray-100 text-gray-600",
};

const PAGE_SIZE = 50;

export default function MaterialsPage() {
  const { t } = useLanguage();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<MaterialType | "">("");
  const [crmOnly, setCrmOnly] = useState(false);
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["materials", search, typeFilter, crmOnly, offset],
    queryFn: () =>
      listMaterials({
        search: search || undefined,
        material_type: typeFilter || undefined,
        crm_only: crmOnly || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
  });

  const items = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t("materials.title")}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {t("materials.subtitle")}
          </p>
        </div>
        <Button asChild>
          <Link href="/materials/new">
            <Plus className="h-4 w-4 mr-2" />
            {t("materials.newMaterial")}
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t("materials.searchName")}
            className="pl-9"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          />
        </div>
        <select
          className="border rounded-md px-3 py-2 text-sm bg-background"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value as MaterialType | ""); setOffset(0); }}
        >
          <option value="">{t("materials.allTypes")}</option>
          {MATERIAL_TYPES.map((mt) => (
            <option key={mt} value={mt}>{TYPE_LABELS_KEYS[mt] ? t(TYPE_LABELS_KEYS[mt] as Parameters<typeof t>[0]) : mt}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm border rounded-md px-3 py-2 cursor-pointer">
          <input
            type="checkbox"
            checked={crmOnly}
            onChange={(e) => { setCrmOnly(e.target.checked); setOffset(0); }}
            className="rounded"
          />
          {t("materials.isCrm")}
        </label>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title={t("materials.noMaterialsFound")}
          description={t("materials.noMaterialsDesc")}
        />
      ) : (
        <>
          <div className="grid gap-3">
            {items.map((m: Material) => (
              <Link key={m.id} href={`/materials/${m.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-start gap-4">
                    <div className="mt-1 p-2 rounded-lg bg-blue-50">
                      <FlaskConical className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold truncate">{m.name}</span>
                        {m.is_critical_raw_material && (
                          <span className="flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                            <AlertTriangle className="h-3 w-3" />
                            CRM
                          </span>
                        )}
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[m.material_status] ?? "bg-gray-100"}`}>
                          {m.material_status.replace("_", " ")}
                        </span>
                      </div>
                      <div className="flex gap-4 mt-1 text-xs text-muted-foreground flex-wrap">
                        <span>{TYPE_LABELS_KEYS[m.material_type] ? t(TYPE_LABELS_KEYS[m.material_type] as Parameters<typeof t>[0]) : m.material_type}</span>
                        {m.cas_number && <span>CAS {m.cas_number}</span>}
                        {m.hs_code && <span>HS {m.hs_code}</span>}
                        {m.country_of_origin && <span>{m.country_of_origin}</span>}
                        {m.internal_code && <span className="font-mono">{m.internal_code}</span>}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground whitespace-nowrap">
                      {m.unit_of_measure}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-muted-foreground">
                {t("common.page")} {currentPage} {t("common.of")} {totalPages} ({total} {t("common.total")})
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t("common.previous")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  {t("common.next")}
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
