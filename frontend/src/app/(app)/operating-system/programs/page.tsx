"use client";

import { useQuery } from "@tanstack/react-query";
import { LayersIcon } from "lucide-react";
import { operatingSystemApi, ESGProgram } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/context";

const STATUS_COLORS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  DRAFT: "bg-gray-100 text-gray-800",
  COMPLETED: "bg-blue-100 text-blue-800",
  ON_HOLD: "bg-yellow-100 text-yellow-800",
  CANCELLED: "bg-red-100 text-red-800",
};

export default function ESGProgramsPage() {
  const { t } = useLanguage();
  const { data: programs, isLoading, error } = useQuery({
    queryKey: ["esg-programs"],
    queryFn: () => operatingSystemApi.listPrograms({ limit: 100 }).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load programs.</div>;
  }

  const byStatus = (programs ?? []).reduce<Record<string, number>>((acc, p) => {
    acc[p.program_status] = (acc[p.program_status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <LayersIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.programsTitle")}</h1>
        </div>
        <span className="text-sm text-muted-foreground">{programs?.length ?? 0} programs</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(byStatus).map(([status, count]) => (
          <Card key={status}>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium text-muted-foreground uppercase">{status}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{count}</p>
            </CardContent>
          </Card>
        ))}
        {Object.keys(byStatus).length === 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-medium text-muted-foreground">{t("common.total")}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">0</p>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="space-y-3">
        {programs?.map((prog) => (
          <ProgramRow key={prog.id} program={prog} />
        ))}
        {programs?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">{t("esgOs.noPrograms")}</div>
        )}
      </div>
    </div>
  );
}

function ProgramRow({ program }: { program: ESGProgram }) {
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-medium">{program.title}</p>
          {program.description && (
            <p className="text-sm text-muted-foreground">{program.description}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {program.program_type ?? "General"} &middot; Created {formatDate(program.created_at)}
          </p>
          {program.linked_objectives.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {program.linked_objectives.length} linked objective{program.linked_objectives.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
        <Badge className={STATUS_COLORS[program.program_status] ?? "bg-gray-100 text-gray-800"}>
          {program.program_status}
        </Badge>
      </CardContent>
    </Card>
  );
}
