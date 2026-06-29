"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Plus, Shield, Trash2, Users, X } from "lucide-react";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

interface CustomRole {
  id: string;
  role_name: string;
  description: string;
  permissions: Array<{ resource: string; actions: string[] }>;
  base_template: string | null;
  is_system: boolean;
}

interface RolesResponse {
  items: CustomRole[];
  templates: string[];
}

const TEMPLATE_INFO: Record<string, { label: string; description: string; color: string }> = {
  viewer:           { label: "Viewer",           description: "Read-only access to all modules",                                 color: "bg-slate-500" },
  analyst:          { label: "Analyst",           description: "Read + update on assessments, findings, risks, and evidence",    color: "bg-blue-600" },
  auditor:          { label: "Auditor",           description: "Read-only with audit trail access",                              color: "bg-violet-600" },
  supplier_manager: { label: "Supplier Manager",  description: "Manage suppliers and due diligence",                            color: "bg-emerald-600" },
};

const RESOURCES = [
  { key: "assessment", label: "Assessments" },
  { key: "finding",    label: "Findings" },
  { key: "risk",       label: "Risks" },
  { key: "evidence",   label: "Evidence" },
  { key: "supplier",   label: "Suppliers" },
  { key: "recommendation", label: "Recommendations" },
  { key: "audit_log", label: "Audit Log" },
  { key: "report",    label: "Reports" },
  { key: "*",         label: "All (wildcard)" },
];

const ACTIONS = ["read", "create", "update", "delete", "export", "approve"];

function PermissionToggle({
  permissions,
  onChange,
}: {
  permissions: Array<{ resource: string; actions: string[] }>;
  onChange: (perms: Array<{ resource: string; actions: string[] }>) => void;
}) {
  const getActions = (resource: string) =>
    permissions.find((p) => p.resource === resource)?.actions ?? [];

  const toggle = (resource: string, action: string) => {
    const existing = permissions.find((p) => p.resource === resource);
    if (existing) {
      const newActions = existing.actions.includes(action)
        ? existing.actions.filter((a) => a !== action)
        : [...existing.actions, action];
      if (newActions.length === 0) {
        onChange(permissions.filter((p) => p.resource !== resource));
      } else {
        onChange(permissions.map((p) => (p.resource === resource ? { ...p, actions: newActions } : p)));
      }
    } else {
      onChange([...permissions, { resource, actions: [action] }]);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b">
            <th className="text-left py-1.5 pr-3 font-medium text-muted-foreground w-36">Resource</th>
            {ACTIONS.map((a) => (
              <th key={a} className="text-center py-1.5 px-1 font-medium text-muted-foreground capitalize">{a}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {RESOURCES.map((r) => {
            const acts = getActions(r.key);
            return (
              <tr key={r.key} className="border-b border-muted/40">
                <td className="py-1.5 pr-3 font-medium text-sm">{r.label}</td>
                {ACTIONS.map((a) => (
                  <td key={a} className="text-center py-1.5 px-1">
                    <input
                      type="checkbox"
                      checked={acts.includes(a)}
                      onChange={() => toggle(r.key, a)}
                      className="cursor-pointer accent-primary"
                    />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function CustomRolesPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleDesc, setRoleDesc] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<Array<{ resource: string; actions: string[] }>>([]);

  const { data, isLoading } = useQuery<RolesResponse>({
    queryKey: ["custom-roles"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/commercial/roles/custom");
      return res.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      await apiClient.post("/api/v1/commercial/roles/custom", {
        role_name: roleName.trim(),
        description: roleDesc.trim(),
        permissions,
        base_template: selectedTemplate ?? undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["custom-roles"] });
      setShowCreate(false);
      setRoleName("");
      setRoleDesc("");
      setPermissions([]);
      setSelectedTemplate(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/api/v1/commercial/roles/custom/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["custom-roles"] }),
  });

  const applyTemplate = (templateKey: string) => {
    setSelectedTemplate(templateKey);
    const info = TEMPLATE_INFO[templateKey];
    if (info) setRoleDesc(info.description);
    const templatePerms: Record<string, Array<{ resource: string; actions: string[] }>> = {
      viewer:           [{ resource: "*", actions: ["read"] }],
      analyst:          [
        { resource: "assessment", actions: ["read", "update"] },
        { resource: "finding",    actions: ["read", "update", "create"] },
        { resource: "risk",       actions: ["read", "update", "create"] },
        { resource: "evidence",   actions: ["read", "create"] },
      ],
      auditor:          [{ resource: "*", actions: ["read"] }, { resource: "audit_log", actions: ["read", "export"] }],
      supplier_manager: [
        { resource: "supplier",      actions: ["read", "create", "update"] },
        { resource: "finding",       actions: ["read"] },
      ],
    };
    setPermissions(templatePerms[templateKey] ?? []);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Custom Roles
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Define role templates with fine-grained resource permissions.
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="h-4 w-4" /> Create Role
        </Button>
      </div>

      {/* Role Templates */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">Built-in Templates</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(TEMPLATE_INFO).map(([key, info]) => (
            <div key={key} className="rounded-lg border p-4 space-y-1.5">
              <div className={`w-7 h-7 rounded-lg ${info.color} flex items-center justify-center`}>
                <Users className="h-4 w-4 text-white" />
              </div>
              <p className="text-sm font-semibold">{info.label}</p>
              <p className="text-xs text-muted-foreground leading-snug">{info.description}</p>
              <button
                onClick={() => { setShowCreate(true); applyTemplate(key); setRoleName(info.label + " (Custom)"); }}
                className="mt-1 text-xs text-primary hover:underline"
              >
                Use template →
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-base">Create Custom Role</CardTitle>
              <CardDescription>Define name, description, and per-resource permissions.</CardDescription>
            </div>
            <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1.5">Role Name</label>
                <input
                  type="text"
                  value={roleName}
                  onChange={(e) => setRoleName(e.target.value)}
                  placeholder="e.g. ESG Analyst"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Description</label>
                <input
                  type="text"
                  value={roleDesc}
                  onChange={(e) => setRoleDesc(e.target.value)}
                  placeholder="Brief description of this role"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Permissions</label>
              <PermissionToggle permissions={permissions} onChange={setPermissions} />
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending || !roleName.trim()}
                className="gap-2"
              >
                {createMutation.isPending ? <Spinner size="sm" /> : <Plus className="h-4 w-4" />}
                Create Role
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              {createMutation.isSuccess && (
                <span className="flex items-center gap-1.5 text-sm text-emerald-600 font-medium">
                  <CheckCircle2 className="h-4 w-4" /> Created
                </span>
              )}
              {createMutation.isError && (
                <span className="text-sm text-red-600">Failed to create. Check role name uniqueness.</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Existing roles */}
      <div>
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          Custom Roles ({data?.items.length ?? 0})
        </h2>
        {!data?.items.length ? (
          <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            No custom roles yet. Use a template above or create from scratch.
          </div>
        ) : (
          <div className="space-y-3">
            {data.items.map((role) => (
              <Card key={role.id}>
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-sm">{role.role_name}</p>
                        {role.base_template && (
                          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground">
                            based on: {role.base_template}
                          </span>
                        )}
                        {role.is_system && (
                          <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-semibold">System</span>
                        )}
                      </div>
                      {role.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">{role.description}</p>
                      )}
                      {role.permissions.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {role.permissions.map((p, i) => (
                            <span key={i} className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">
                              {p.resource}: {p.actions.join(", ")}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {!role.is_system && (
                      <button
                        onClick={() => deleteMutation.mutate(role.id)}
                        disabled={deleteMutation.isPending}
                        className="text-muted-foreground hover:text-red-500 transition-colors flex-shrink-0"
                        title="Delete role"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
