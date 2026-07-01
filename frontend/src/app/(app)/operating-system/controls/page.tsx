"use client";

import { useQuery } from "@tanstack/react-query";
import { ClipboardList, FileSearch, ShieldCheckIcon } from "lucide-react";
import { operatingSystemApi, ESGControl } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import apiClient from "@/lib/api/client";
import { useLanguage } from "@/lib/i18n/context";

const EFFECTIVENESS_COLORS: Record<string, string> = {
  EFFECTIVE: "bg-green-100 text-green-800",
  PARTIALLY_EFFECTIVE: "bg-yellow-100 text-yellow-800",
  INEFFECTIVE: "bg-red-100 text-red-800",
  NOT_TESTED: "bg-gray-100 text-gray-800",
};

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  INACTIVE: "bg-gray-100 text-gray-800",
  FAILING: "bg-red-100 text-red-800",
  UNDER_REVIEW: "bg-blue-100 text-blue-800",
};

export default function ESGControlsPage() {
  const { t } = useLanguage();
  const { data: controls, isLoading, error } = useQuery({
    queryKey: ["esg-controls"],
    queryFn: () => operatingSystemApi.listControls({ limit: 200 }).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load controls.</div>;
  }

  const failing = controls?.filter((c) => c.control_status === "FAILING").length ?? 0;
  const effective = controls?.filter((c) => c.effectiveness_status === "EFFECTIVE").length ?? 0;
  const notTested = controls?.filter((c) => c.effectiveness_status === "NOT_TESTED").length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.controlsTitle")}</h1>
        </div>
        <span className="text-sm text-muted-foreground">{controls?.length ?? 0} controls</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">{t("common.total")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{controls?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Effective</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{effective}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Failing</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{failing}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Not Tested</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-gray-500">{notTested}</p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {controls?.map((ctrl) => (
          <ControlRow key={ctrl.id} control={ctrl} />
        ))}
        {controls?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">{t("esgOs.noControls")}</div>
        )}
      </div>
    </div>
  );
}

function ControlLinkedCounts({ controlId }: { controlId: string }) {
  const { data: tests = [] } = useQuery({
    queryKey: ["control-tests", controlId],
    queryFn: () => operatingSystemApi.listTests({ control_id: controlId, limit: 100 }).then((r) => r.data),
    staleTime: 300_000,
  });

  const { data: findings } = useQuery({
    queryKey: ["control-findings", controlId],
    queryFn: async () => {
      try {
        const res = await apiClient.get(`/controls/${controlId}/findings`);
        return res.data as any[];
      } catch {
        return [] as any[];
      }
    },
    staleTime: 300_000,
    retry: false,
  });

  return (
    <div className="flex items-center gap-2 flex-wrap mt-1">
      <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
        <ClipboardList className="h-3 w-3" />
        {tests.length} test{tests.length !== 1 ? "s" : ""}
      </span>
      {findings !== undefined && findings.length > 0 && (
        <span className="inline-flex items-center gap-1 rounded bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700">
          <FileSearch className="h-3 w-3" />
          {findings.length} finding{findings.length !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}

function ControlRow({ control }: { control: ESGControl }) {
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-medium">{control.control_name}</p>
          {control.description && (
            <p className="text-sm text-muted-foreground">{control.description}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {control.control_type} &middot; Created {formatDate(control.created_at)}
          </p>
          <ControlLinkedCounts controlId={control.id} />
        </div>
        <div className="flex flex-col items-end gap-2 shrink-0">
          <Badge className={STATUS_COLORS[control.control_status] ?? "bg-gray-100 text-gray-800"}>
            {control.control_status}
          </Badge>
          <Badge className={EFFECTIVENESS_COLORS[control.effectiveness_status] ?? "bg-gray-100 text-gray-800"}>
            {control.effectiveness_status.replace("_", " ")}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}
