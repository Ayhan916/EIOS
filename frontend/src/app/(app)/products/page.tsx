"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Search,
  Package,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  listProducts,
  PRODUCT_TYPES,
  type Product,
  type ProductType,
} from "@/lib/api/product";

const TYPE_LABELS: Record<string, string> = {
  FINISHED_GOOD: "Finished Good",
  SEMI_FINISHED: "Semi-Finished",
  COMPONENT: "Component",
  SPARE_PART: "Spare Part",
  SERVICE: "Service",
  OTHER: "Other",
};

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  ACTIVE: "bg-green-100 text-green-800",
  DISCONTINUED: "bg-orange-100 text-orange-800",
  ARCHIVED: "bg-gray-100 text-gray-400",
};

const PAGE_SIZE = 50;

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<ProductType | "">("");
  const [regulatedOnly, setRegulatedOnly] = useState(false);
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["products", search, typeFilter, regulatedOnly, offset],
    queryFn: () =>
      listProducts({
        search: search || undefined,
        product_type: typeFilter || undefined,
        regulated_only: regulatedOnly || undefined,
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Product Twin</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {total} product{total !== 1 ? "s" : ""} — BOM, compliance &amp; carbon footprint
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-56">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search name, SKU, GTIN…"
            className="pl-9"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          />
        </div>
        <select
          className="border rounded-md px-3 py-2 text-sm bg-background"
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value as ProductType | ""); setOffset(0); }}
        >
          <option value="">All Types</option>
          {PRODUCT_TYPES.map((t) => (
            <option key={t} value={t}>{TYPE_LABELS[t] ?? t}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm border rounded-md px-3 py-2 cursor-pointer">
          <input
            type="checkbox"
            checked={regulatedOnly}
            onChange={(e) => { setRegulatedOnly(e.target.checked); setOffset(0); }}
            className="rounded"
          />
          Regulated products only
        </label>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner /></div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Package}
          title="No products found"
          description="Add your first product to start managing BOM, compliance and carbon footprint."
        />
      ) : (
        <>
          <div className="grid gap-3">
            {items.map((p: Product) => (
              <Link key={p.id} href={`/products/${p.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                  <CardContent className="p-4 flex items-start gap-4">
                    <div className="mt-1 p-2 rounded-lg bg-purple-50">
                      <Package className="h-5 w-5 text-purple-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold truncate">{p.name}</span>
                        {p.is_regulated_product && (
                          <span className="flex items-center gap-1 text-xs font-medium bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                            <AlertTriangle className="h-3 w-3" />
                            Regulated
                          </span>
                        )}
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_COLORS[p.product_status] ?? "bg-gray-100"}`}>
                          {p.product_status}
                        </span>
                      </div>
                      <div className="flex gap-4 mt-1 text-xs text-muted-foreground flex-wrap">
                        <span>{TYPE_LABELS[p.product_type] ?? p.product_type}</span>
                        {p.sku && <span>SKU: {p.sku}</span>}
                        {p.gtin && <span>GTIN: {p.gtin}</span>}
                        {p.category && <span>{p.category}</span>}
                        {p.brand && <span>{p.brand}</span>}
                        {p.country_of_manufacture && <span>{p.country_of_manufacture}</span>}
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground whitespace-nowrap">
                      {p.target_market ?? "—"}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-muted-foreground">
                Page {currentPage} of {totalPages} ({total} total)
              </span>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                  <ChevronLeft className="h-4 w-4" /> Previous
                </Button>
                <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}>
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
