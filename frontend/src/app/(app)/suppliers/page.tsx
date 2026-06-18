"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Search,
  Briefcase,
  Globe,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { listSuppliers, createSupplier } from "@/lib/api/suppliers";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import type { SupplierCreate, SupplierTier } from "@/types/api";

const TIER_OPTIONS: { value: SupplierTier | ""; label: string }[] = [
  { value: "", label: "All Tiers" },
  { value: "Tier 1", label: "Tier 1" },
  { value: "Tier 2", label: "Tier 2" },
  { value: "Tier 3", label: "Tier 3" },
  { value: "Other", label: "Other" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "Active", label: "Active" },
  { value: "Inactive", label: "Inactive" },
];

function tierBadge(tier: string) {
  const colors: Record<string, string> = {
    "Tier 1": "bg-blue-100 text-blue-800",
    "Tier 2": "bg-purple-100 text-purple-800",
    "Tier 3": "bg-slate-100 text-slate-700",
    Other: "bg-gray-100 text-gray-700",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[tier] ?? "bg-gray-100 text-gray-700"}`}
    >
      {tier}
    </span>
  );
}

function statusBadge(s: string) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        s === "Active"
          ? "bg-emerald-100 text-emerald-800"
          : "bg-slate-100 text-slate-600"
      }`}
    >
      {s}
    </span>
  );
}

export default function SuppliersPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState<SupplierCreate>({
    name: "",
    legal_name: "",
    country: "",
    industry: "",
    nace_code: "",
    website: "",
    supplier_tier: "Tier 1",
    notes: "",
  });

  const PAGE_SIZE = 15;

  const { data, isLoading } = useQuery({
    queryKey: ["suppliers", { page, page_size: PAGE_SIZE, search, tierFilter, statusFilter }],
    queryFn: () =>
      listSuppliers({
        page,
        page_size: PAGE_SIZE,
        search: search || undefined,
        supplier_tier: tierFilter || undefined,
        status: statusFilter || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suppliers"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setShowCreate(false);
      setCreateError(null);
      setForm({
        name: "",
        legal_name: "",
        country: "",
        industry: "",
        nace_code: "",
        website: "",
        supplier_tier: "Tier 1",
        notes: "",
      });
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error ? err.message : "Failed to create supplier";
      setCreateError(msg);
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  }

  const suppliers = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data ? Math.ceil(total / PAGE_SIZE) : 1;

  // Summary cards (computed from current page when no API aggregate)
  const activeCount = data?.items.filter((s) => s.supplier_status === "Active").length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Suppliers</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            ESG due diligence subjects — manage supplier risk profiles
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          Add Supplier
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search suppliers..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-9 w-64"
            />
          </div>
          <Button type="submit" variant="secondary">
            Search
          </Button>
        </form>
        <select
          value={tierFilter}
          onChange={(e) => { setTierFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          {TIER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        {(search || tierFilter || statusFilter) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setSearch(""); setSearchInput(""); setTierFilter(""); setStatusFilter(""); setPage(1); }}
            className="gap-1 text-muted-foreground"
          >
            <X className="h-3 w-3" /> Clear
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {total} supplier{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Spinner size="lg" /></div>
      ) : suppliers.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Briefcase className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-muted-foreground">
              {search || tierFilter || statusFilter
                ? "No suppliers match your filters."
                : "No suppliers yet. Add your first supplier to begin ESG due diligence."}
            </p>
            {!search && !tierFilter && !statusFilter && (
              <Button onClick={() => setShowCreate(true)} className="mt-2 gap-2">
                <Plus className="h-4 w-4" /> Add Supplier
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Country</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Industry</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Tier</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">Status</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">NACE</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {suppliers.map((s) => (
                    <tr key={s.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-3">
                        <Link
                          href={`/suppliers/${s.id}`}
                          className="font-medium text-foreground hover:text-blue-600 hover:underline"
                        >
                          {s.name}
                        </Link>
                        {s.legal_name && s.legal_name !== s.name && (
                          <p className="text-xs text-muted-foreground">{s.legal_name}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {s.country ? (
                          <span className="flex items-center gap-1 text-muted-foreground">
                            <Globe className="h-3 w-3" /> {s.country}
                          </span>
                        ) : (
                          <span className="text-muted-foreground/50">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {s.industry || <span className="text-muted-foreground/50">—</span>}
                      </td>
                      <td className="px-4 py-3">{tierBadge(s.supplier_tier)}</td>
                      <td className="px-4 py-3">{statusBadge(s.supplier_status)}</td>
                      <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                        {s.nace_code || <span className="text-muted-foreground/50">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl bg-background p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Add Supplier</h2>
              <button
                onClick={() => { setShowCreate(false); setCreateError(null); }}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium">Name *</label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Supplier legal entity name"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Legal Name</label>
                <Input
                  value={form.legal_name ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, legal_name: e.target.value }))}
                  placeholder="Full legal name (if different)"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Country</label>
                  <Input
                    value={form.country ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, country: e.target.value }))}
                    placeholder="DE, US, FR…"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">NACE Code</label>
                  <Input
                    value={form.nace_code ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, nace_code: e.target.value }))}
                    placeholder="C24.10"
                  />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Industry</label>
                <Input
                  value={form.industry ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                  placeholder="Steel Manufacturing, Agriculture…"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium">Supplier Tier</label>
                  <select
                    value={form.supplier_tier}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, supplier_tier: e.target.value as SupplierTier }))
                    }
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="Tier 1">Tier 1</option>
                    <option value="Tier 2">Tier 2</option>
                    <option value="Tier 3">Tier 3</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Website</label>
                  <Input
                    value={form.website ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))}
                    placeholder="https://…"
                  />
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium">Notes</label>
                <textarea
                  value={form.notes ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  rows={3}
                  placeholder="Internal notes…"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {createError && (
              <p className="mt-3 text-sm text-red-600">{createError}</p>
            )}

            <div className="mt-5 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => { setShowCreate(false); setCreateError(null); }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (!form.name.trim()) {
                    setCreateError("Name is required");
                    return;
                  }
                  createMutation.mutate({
                    ...form,
                    legal_name: form.legal_name || undefined,
                    nace_code: form.nace_code || undefined,
                    website: form.website || undefined,
                    notes: form.notes || undefined,
                  });
                }}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <Spinner size="sm" className="mr-2" />
                ) : null}
                Create Supplier
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
