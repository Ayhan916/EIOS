"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Plus, UsersIcon } from "lucide-react";
import { operatingSystemApi, type AccountabilityAssignment } from "@/lib/api/operating-system";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

const STATUS_COLOURS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  REVOKED: "bg-red-100 text-red-800",
  TRANSFERRED: "bg-blue-100 text-blue-800",
};

const ROLES = ["OWNER", "REVIEWER", "APPROVER", "CONTRIBUTOR", "OBSERVER", "DELEGATE"];
const ENTITY_TYPES = ["PROGRAM", "CONTROL", "RISK", "FINDING", "ASSESSMENT", "OBJECTIVE", "KPI", "OTHER"];

export default function AccountabilityPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [entityType, setEntityType] = useState("PROGRAM");
  const [entityId, setEntityId] = useState("");
  const [role, setRole] = useState("OWNER");
  const [assignedTo, setAssignedTo] = useState("");
  const [entityTypeFilter, setEntityTypeFilter] = useState("");

  const { data: assignments = [], isLoading } = useQuery({
    queryKey: ["accountability-assignments", entityTypeFilter],
    queryFn: () => operatingSystemApi.listAssignments({
      limit: 200,
      entity_type: entityTypeFilter || undefined,
    }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => operatingSystemApi.assignAccountability({
      entity_type: entityType,
      entity_id: entityId,
      role,
      assigned_to_user_id: assignedTo,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accountability-assignments"] });
      setShowForm(false);
      setEntityId(""); setRole("OWNER"); setAssignedTo(""); setEntityType("PROGRAM");
    },
  });

  if (isLoading) return <div className="flex justify-center h-64 items-center"><Spinner /></div>;

  const active = assignments.filter((a) => a.assignment_status === "ACTIVE").length;
  const byEntityType = assignments.reduce<Record<string, number>>((acc, a) => {
    acc[a.entity_type] = (acc[a.entity_type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <UsersIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.accountabilityTitle")}</h1>
        </div>
        <div className="flex gap-2 items-center">
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
          >
            <option value="">All Entity Types</option>
            {Object.keys(byEntityType).map((et) => (
              <option key={et} value={et}>{et}</option>
            ))}
          </select>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-1.5" /> Assign
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("common.total")}</p>
            <p className="text-3xl font-bold mt-1">{assignments.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">{t("common.active")}</p>
            <p className="text-3xl font-bold mt-1 text-green-600">{active}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-5">
            <p className="text-xs text-muted-foreground">Entity Types</p>
            <p className="text-3xl font-bold mt-1">{Object.keys(byEntityType).length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Entity type breakdown */}
      {Object.keys(byEntityType).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(byEntityType).map(([type, count]) => (
            <button
              key={type}
              onClick={() => setEntityTypeFilter(entityTypeFilter === type ? "" : type)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${entityTypeFilter === type ? "bg-slate-800 text-white border-slate-800" : "bg-slate-100 text-slate-700 border-slate-200 hover:border-slate-400"}`}
            >
              {type} · {count}
            </button>
          ))}
        </div>
      )}

      {showForm && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="text-sm font-semibold">New Accountability Assignment</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Entity Type</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={entityType} onChange={(e) => setEntityType(e.target.value)}>
                  {ENTITY_TYPES.map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <Label className="text-xs">Entity ID *</Label>
                <Input className="mt-1" value={entityId} onChange={(e) => setEntityId(e.target.value)}
                  placeholder="UUID of the entity" />
              </div>
              <div>
                <Label className="text-xs">Role</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={role} onChange={(e) => setRole(e.target.value)}>
                  {ROLES.map((v) => <option key={v}>{v}</option>)}
                </select>
              </div>
              <div>
                <Label className="text-xs">Assigned To (User ID) *</Label>
                <Input className="mt-1" value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)}
                  placeholder="User ID" />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!entityId || !assignedTo || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Assignment created.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {assignments.map((a) => <AssignmentRow key={a.id} assignment={a} />)}
        {assignments.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">{t("common.noData")}</div>
        )}
      </div>
    </div>
  );
}

function AssignmentRow({ assignment }: { assignment: AccountabilityAssignment }) {
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-medium">{assignment.role} — {assignment.entity_type}</p>
          <p className="text-xs text-muted-foreground font-mono">
            Entity: {assignment.entity_id.slice(0, 16)}…
          </p>
          <p className="text-xs text-muted-foreground">
            Assigned {formatDate(assignment.assigned_at)}
          </p>
        </div>
        <Badge className={STATUS_COLOURS[assignment.assignment_status] ?? "bg-gray-100 text-gray-800"}>
          {assignment.assignment_status}
        </Badge>
      </CardContent>
    </Card>
  );
}
