"use client";

import { useQuery } from "@tanstack/react-query";
import { ClipboardCheckIcon } from "lucide-react";
import { operatingSystemApi, ControlTest } from "@/lib/api/operating-system";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { formatDateTime } from "@/lib/utils";
import { useLanguage } from "@/lib/i18n/context";

const RESULT_COLORS: Record<string, string> = {
  PASS: "bg-green-100 text-green-800",
  FAIL: "bg-red-100 text-red-800",
  PARTIAL: "bg-yellow-100 text-yellow-800",
  NOT_APPLICABLE: "bg-gray-100 text-gray-800",
};

export default function ControlTestsPage() {
  const { t } = useLanguage();
  const { data: tests, isLoading, error } = useQuery({
    queryKey: ["control-tests"],
    queryFn: () => operatingSystemApi.listTests({ limit: 200 }).then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return <div className="p-6 text-red-600">Failed to load control tests.</div>;
  }

  const passed = tests?.filter((t) => t.test_result === "PASS").length ?? 0;
  const failed = tests?.filter((t) => t.test_result === "FAIL").length ?? 0;
  const partial = tests?.filter((t) => t.test_result === "PARTIAL").length ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardCheckIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.testsTitle")}</h1>
        </div>
        <span className="text-sm text-muted-foreground">{tests?.length ?? 0} {t("nav.tests").toLowerCase()}</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">{t("common.total")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{tests?.length ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">{t("esgOs.passed")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-green-600">{passed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">{t("esgOs.failed")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-red-600">{failed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Partial</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-yellow-600">{partial}</p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {tests?.map((test) => (
          <TestRow key={test.id} test={test} />
        ))}
        {tests?.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">{t("esgOs.noTests")}</div>
        )}
      </div>
    </div>
  );
}

function TestRow({ test }: { test: ControlTest }) {
  const { t } = useLanguage();
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-sm font-mono text-muted-foreground">{t("esgOs.controlId")}: {test.control_id.slice(0, 8)}…</p>
          {test.findings && (
            <p className="text-sm">{test.findings}</p>
          )}
          <p className="text-xs text-muted-foreground">
            {t("esgOs.testDate")}: {formatDateTime(test.tested_at)}
          </p>
        </div>
        <Badge className={RESULT_COLORS[test.test_result] ?? "bg-gray-100 text-gray-800"}>
          {test.test_result}
        </Badge>
      </CardContent>
    </Card>
  );
}
