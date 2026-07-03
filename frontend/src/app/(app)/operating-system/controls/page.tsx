"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ClipboardList, FileSearch, Loader2, Plus, ShieldCheckIcon } from "lucide-react";
import { operatingSystemApi, type ESGControl } from "@/lib/api/operating-system";
import { useLanguage } from "@/lib/i18n/context";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/utils";
import apiClient from "@/lib/api/client";

const EFFECTIVENESS_COLOURS: Record<string, string> = {
  EFFECTIVE: "bg-green-100 text-green-800",
  PARTIALLY_EFFECTIVE: "bg-yellow-100 text-yellow-800",
  INEFFECTIVE: "bg-red-100 text-red-800",
  NOT_TESTED: "bg-gray-100 text-gray-800",
};

const STATUS_COLOURS: Record<string, string> = {
  ACTIVE: "bg-green-100 text-green-800",
  INACTIVE: "bg-gray-100 text-gray-800",
  FAILING: "bg-red-100 text-red-800",
  UNDER_REVIEW: "bg-blue-100 text-blue-800",
};

const CONTROL_TYPES = ["PREVENTIVE", "DETECTIVE", "CORRECTIVE", "COMPENSATING", "DIRECTIVE"];
const TEST_RESULTS = ["PASS", "FAIL", "PARTIAL", "NOT_APPLICABLE"];

function ControlRow({ control }: { control: ESGControl }) {
  const qc = useQueryClient();
  const [showTest, setShowTest] = useState(false);
  const [testResult, setTestResult] = useState("PASS");
  const [findings, setFindings] = useState("");

  const { data: tests = [] } = useQuery({
    queryKey: ["control-tests", control.id],
    queryFn: () => operatingSystemApi.listTests({ control_id: control.id, limit: 100 }).then((r) => r.data),
    staleTime: 300_000,
  });

  const { data: linkedFindings = [] } = useQuery({
    queryKey: ["control-findings", control.id],
    queryFn: async () => {
      try { return (await apiClient.get(`/controls/${control.id}/findings`)).data as any[]; }
      catch { return []; }
    },
    staleTime: 300_000,
    retry: false,
  });

  const runTest = useMutation({
    mutationFn: () => operatingSystemApi.createTest({
      control_id: control.id,
      test_result: testResult,
      findings: findings || undefined,
      tested_at: new Date().toISOString(),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["control-tests", control.id] });
      qc.invalidateQueries({ queryKey: ["esg-controls"] });
      setShowTest(false);
      setFindings("");
    },
  });

  return (
    <Card>
      <CardContent className="py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 flex-1 min-w-0">
            <p className="font-medium">{control.control_name}</p>
            {control.description && (
              <p className="text-sm text-muted-foreground line-clamp-2">{control.description}</p>
            )}
            <p className="text-xs text-muted-foreground">
              {control.control_type} · Created {formatDate(control.created_at)}
            </p>
            <div className="flex items-center gap-2 flex-wrap mt-1">
              <span className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                <ClipboardList className="h-3 w-3" />
                {tests.length} test{tests.length !== 1 ? "s" : ""}
              </span>
              {linkedFindings.length > 0 && (
                <span className="inline-flex items-center gap-1 rounded bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700">
                  <FileSearch className="h-3 w-3" />
                  {linkedFindings.length} finding{linkedFindings.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <Badge className={STATUS_COLOURS[control.control_status] ?? "bg-gray-100 text-gray-800"}>
              {control.control_status}
            </Badge>
            <Badge className={EFFECTIVENESS_COLOURS[control.effectiveness_status] ?? "bg-gray-100 text-gray-800"}>
              {control.effectiveness_status.replace(/_/g, " ")}
            </Badge>
            <button
              onClick={() => setShowTest(!showTest)}
              className="text-xs text-primary hover:underline"
            >
              + Run Test
            </button>
          </div>
        </div>

        {showTest && (
          <div className="mt-3 rounded-lg border border-border bg-muted/30 p-3 space-y-2">
            <p className="text-xs font-semibold">Run Control Test</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-xs">Result</Label>
                <select className="mt-1 h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
                  value={testResult} onChange={(e) => setTestResult(e.target.value)}>
                  {TEST_RESULTS.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
                </select>
              </div>
              <div>
                <Label className="text-xs">Findings (optional)</Label>
                <Input className="mt-1 h-8 text-xs" value={findings}
                  onChange={(e) => setFindings(e.target.value)} placeholder="Observations…" />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setShowTest(false)}>Cancel</Button>
              <Button size="sm" className="h-7 text-xs" disabled={runTest.isPending} onClick={() => runTest.mutate()}>
                {runTest.isPending && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                Submit
              </Button>
            </div>
            {runTest.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Test recorded.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ESGControlsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [controlName, setControlName] = useState("");
  const [controlType, setControlType] = useState("PREVENTIVE");
  const [description, setDescription] = useState("");

  const { data: controls = [], isLoading } = useQuery({
    queryKey: ["esg-controls"],
    queryFn: () => operatingSystemApi.listControls({ limit: 200 }).then((r) => r.data),
  });

  const create = useMutation({
    mutationFn: () => operatingSystemApi.createControl({
      control_name: controlName,
      control_type: controlType,
      description: description || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["esg-controls"] });
      setShowForm(false);
      setControlName(""); setControlType("PREVENTIVE"); setDescription("");
    },
  });

  if (isLoading) return <div className="flex justify-center h-64 items-center"><Spinner /></div>;

  const failing = controls.filter((c) => c.control_status === "FAILING").length;
  const effective = controls.filter((c) => c.effectiveness_status === "EFFECTIVE").length;
  const notTested = controls.filter((c) => c.effectiveness_status === "NOT_TESTED").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheckIcon className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-2xl font-semibold">{t("esgOs.controlsTitle")}</h1>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1.5" /> New Control
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: t("common.total"), value: controls.length, colour: "" },
          { label: "Effective", value: effective, colour: "text-green-600" },
          { label: "Failing", value: failing, colour: failing > 0 ? "text-red-600" : "" },
          { label: "Not Tested", value: notTested, colour: notTested > 0 ? "text-amber-600" : "" },
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
            <p className="text-sm font-semibold">New ESG Control</p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Control Name *</Label>
                <Input className="mt-1" value={controlName} onChange={(e) => setControlName(e.target.value)}
                  placeholder="e.g. Supplier Audit Control" />
              </div>
              <div>
                <Label className="text-xs">Control Type</Label>
                <select className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={controlType} onChange={(e) => setControlType(e.target.value)}>
                  {CONTROL_TYPES.map((v) => <option key={v} value={v}>{v.replace(/_/g, " ")}</option>)}
                </select>
              </div>
            </div>
            <div>
              <Label className="text-xs">Description</Label>
              <Input className="mt-1" value={description} onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the control objective…" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>{t("common.cancel")}</Button>
              <Button size="sm" disabled={!controlName || create.isPending} onClick={() => create.mutate()}>
                {create.isPending && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                {t("common.save")}
              </Button>
            </div>
            {create.isSuccess && (
              <p className="text-xs text-green-700 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Control created.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {controls.map((ctrl) => <ControlRow key={ctrl.id} control={ctrl} />)}
        {controls.length === 0 && (
          <div className="text-center py-12 text-muted-foreground text-sm">{t("esgOs.noControls")}</div>
        )}
      </div>
    </div>
  );
}
