"use client";

import { useQuery } from "@tanstack/react-query";
import { UsersIcon } from "lucide-react";
import { operatingSystemApi, AccountabilityAssignment } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  REVOKED: "bg-red-100 text-red-800",
  TRANSFERRED: "bg-blue-100 text-blue-800",
};

export default function AccountabilityPage() {
  const { data: assignments, isLoading, error } = useQuery({
    queryKey: ["accountability-assignments"],
    queryFn: () =>
      operatingSystemApi.listAssignments({ limit: 200 }).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load accountability assignments.</div>;
  }

  const active = assignments?.filter((a) => a.assignment_status === "ACTIVE").length ?? 0;
  const byEntityType = (assignments ?? []).reduce<Record<string, number>>((acc, a) => {
    acc[a.entity_type] = (acc[a.entity_type] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UsersIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">Accountability Framework</h1>
        </div>
        <span className="text-sm text-muted-foreground">{assignments?.length ?? 0} assignments</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{assignments?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Active</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{active}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Entity Types</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{Object.keys(byEntityType).length}</p>
          </CardContent>
        </Card>
      </div>

      {Object.keys(byEntityType).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">By Entity Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(byEntityType).map(([type, count]) => (
                <div key={type} className="flex items-center gap-1 text-sm">
                  <span className="font-medium">{type}</span>
                  <Badge variant="outline">{count}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {assignments?.map((a) => (
          <AssignmentRow key={a.id} assignment={a} />
        ))}
        {assignments?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">No assignments yet.</div>
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
          <p className="font-medium">
            {assignment.role} &mdash; {assignment.entity_type}
          </p>
          <p className="text-xs text-muted-foreground font-mono">
            Entity: {assignment.entity_id.slice(0, 8)}…
          </p>
          <p className="text-xs text-muted-foreground">
            Assigned {formatDate(assignment.assigned_at)}
          </p>
        </div>
        <Badge className={STATUS_COLORS[assignment.assignment_status] ?? "bg-gray-100 text-gray-800"}>
          {assignment.assignment_status}
        </Badge>
      </CardContent>
    </Card>
  );
}
