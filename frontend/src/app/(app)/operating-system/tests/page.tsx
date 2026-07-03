"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardCheckIcon, Loader2, Plus } from "lucide-react";
import { operatingSystemApi, type ControlTest } from "@/lib/api/operating-system";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDateTime } from "@/lib/utils";

const RESULT_COLOURS: Record<string, string> = {
  PASS: "bg-green-100 text-green-800",
  FAIL: "bg-red-100 text-red-800",
  PARTIAL: "bg-yellow-100 text-yellow-800",
  NOT_APPLICABLE: "bg-gray-100 text-gray-800",
};

export default function ControlTestsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [controlId, setControlId] = useState("");
  const [testResult, setTestResult] = useState("PASS");
  const [findings, setFindings] = useState("");
  const [resultFilter, setResultFilter] = useState("");

  const { data: tests = [], isLoading } = useQuery({
    queryKey: ["control-tests-all", resultFilter],
    queryFn: () => operatingSystemApi.listTests({ limit: 200, test_result: resultFilter || undefined }).then((r) => r.data),
  });

  const { data: controls = [] } = useQuery({
    queryKey: ["esg-controls"],
    queryFn: () => operatingSystemApi.listControls({ limit: 200 }).then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const create = useMutation({
    mutationFn: () => operatingSystemApi.createTest({
      control_id: controlId,
      test_result: testResult,
      findings: findings || undefined,
      tested_at: new Date().toISOString(),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-tests-all"] });
      qc.invalidateQueries({ queryKey: ["control-tests", controlId] });
      qc.invalidateQueries({ queryKey: ["esg-controls"] });
      setShowForm(false);
      setControlId(""); setTestResult("PASS"); setFindings("");
    },
  });

  if (isLoading) return <div className="flex justify-center h-64 items-center"><Spinner /></div>;

  const passed = tests.filter((t) => t.test_result === "PASS").length;
  const failed = tests.filter((t) => t.test_result === "FAIL").length;
  const partial = tests.filter((t) => t.test_result === "PARTIAL").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <ClipboardCheckIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.testsTitle")}</h1>
        </div>
        <div className="flex gap-2 items-center">
          <select
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={resultFilter}
            onChange={(e) => setResultFilter(e.target.value)}
          >
            <option value="">All Results</option>
            {["PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE"].map((v) => (
              <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
            ))}
          </select>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-1.5" /> Record Test
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: t("common.total"), value: tests.length, colour: "" },
          { label: t("esgOs.passed"), value: passed, colour: "text-green-600" },
          { label: t("esgOs.failed"), value: failed, colour: failed > 0 ? "text-red-600" : "" },
          { label: "Partial", value: partial, colour: partial > 0 ? "text-amber-600" : "" },
        ].map(({ label, value, colour }) => (
          <Card key={label}>
            <CardContent className="pt-5 pb-5">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className={`text-3xl font-bold mt-1 ${colour}`}>{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="text-sm font-semibold">Record Control Test</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Control *</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={controlId} onChange={(e) => setControlId(e.target.value)}>
                  <option value="">— select control —</option>
                  {controls.map((c) => <option key={c.id} value={c.id}>{c.control_name}</option>)}
                </select>
              </div>
              <div>
                <Label className="text-xs">Result</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={testResult} onChange={(e) => setTestResult(e.target.value)}>
                  {["PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE"].map((v) => (
                    <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
                  ))}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Findings / Observations</Label>
              <Input className="mt-1" value={findings} onChange={(e) => setFindings(e.target.value)}
                placeholder="Document any findings or observations…" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!controlId || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Test recorded.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {tests.map((test) => <TestRow key={test.id} test={test} controls={controls} />)}
        {tests.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">{t("esgOs.noTests")}</div>
        )}
      </div>
    </div>
  );
}

function TestRow({ test, controls }: { test: ControlTest; controls: any[] }) {
  const controlName = controls.find((c) => c.id === test.control_id)?.control_name ?? test.control_id.slice(0, 8) + "…";
  return (
    <Card>
      <CardContent className="py-4 flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-medium">{controlName}</p>
          {test.findings && <p className="text-sm text-muted-foreground">{test.findings}</p>}
          <p className="text-xs text-muted-foreground">Tested {formatDateTime(test.tested_at)}</p>
        </div>
        <Badge className={RESULT_COLOURS[test.test_result] ?? "bg-gray-100 text-gray-800"}>
          {test.test_result.replace(/_/g, " ")}
        </Badge>
      </CardContent>
    </Card>
  );
}
