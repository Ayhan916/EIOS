"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, FileText, Loader2, Plus, ShieldAlert, X } from "lucide-react";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type CreateType = "finding" | "risk" | "assessment" | null;

function CreateFindingForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("Medium");

  const mut = useMutation({
    mutationFn: async () => {
      const r = await apiClient.post("/api/v1/findings/", { title, severity, status: "Open" });
      return r.data as { id: string };
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["org-findings"] });
      onClose();
      router.push(`/findings/${data.id}`);
    },
  });

  return (
    <div className="space-y-3">
      <input
        autoFocus
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-orange-400"
        placeholder="Finding title…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && title.trim() && mut.mutate()}
      />
      <select
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm"
        value={severity}
        onChange={(e) => setSeverity(e.target.value)}
      >
        <option value="Critical">Critical</option>
        <option value="High">High</option>
        <option value="Medium">Medium</option>
        <option value="Low">Low</option>
      </select>
      <Button size="sm" className="w-full bg-orange-600 hover:bg-orange-700 text-white" disabled={!title.trim() || mut.isPending} onClick={() => mut.mutate()}>
        {mut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
        Create Finding
      </Button>
      {mut.isError && <p className="text-xs text-red-600">Failed — please try again.</p>}
    </div>
  );
}

function CreateRiskForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [level, setLevel] = useState("Medium");

  const mut = useMutation({
    mutationFn: async () => {
      const r = await apiClient.post("/api/v1/risks/", { title, risk_level: level, status: "Draft" });
      return r.data as { id: string };
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["org-risks"] });
      onClose();
      router.push(`/risks/${data.id}`);
    },
  });

  return (
    <div className="space-y-3">
      <input
        autoFocus
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-red-400"
        placeholder="Risk title…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && title.trim() && mut.mutate()}
      />
      <select
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm"
        value={level}
        onChange={(e) => setLevel(e.target.value)}
      >
        <option value="Critical">Critical</option>
        <option value="High">High</option>
        <option value="Medium">Medium</option>
        <option value="Low">Low</option>
      </select>
      <Button size="sm" className="w-full bg-red-600 hover:bg-red-700 text-white" disabled={!title.trim() || mut.isPending} onClick={() => mut.mutate()}>
        {mut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
        Create Risk
      </Button>
      {mut.isError && <p className="text-xs text-red-600">Failed — please try again.</p>}
    </div>
  );
}

function CreateAssessmentForm({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [type, setType] = useState("ESG_AUDIT");

  const mut = useMutation({
    mutationFn: async () => {
      const r = await apiClient.post("/api/v1/assessments/", { title, assessment_type: type, scope: "Full" });
      return r.data as { id: string };
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["assessments"] });
      onClose();
      router.push(`/assessments/${data.id}`);
    },
  });

  return (
    <div className="space-y-3">
      <input
        autoFocus
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-400"
        placeholder="Assessment title…"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && title.trim() && mut.mutate()}
      />
      <select
        className="w-full rounded border border-input bg-background px-3 py-1.5 text-sm"
        value={type}
        onChange={(e) => setType(e.target.value)}
      >
        <option value="ESG_AUDIT">ESG Audit</option>
        <option value="SUPPLIER_DUE_DILIGENCE">Supplier Due Diligence</option>
        <option value="COMPLIANCE_REVIEW">Compliance Review</option>
        <option value="RISK_ASSESSMENT">Risk Assessment</option>
      </select>
      <Button size="sm" className="w-full bg-blue-600 hover:bg-blue-700 text-white" disabled={!title.trim() || mut.isPending} onClick={() => mut.mutate()}>
        {mut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
        Create Assessment
      </Button>
      {mut.isError && <p className="text-xs text-red-600">Failed — please try again.</p>}
    </div>
  );
}

export function QuickCreateFAB() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<CreateType>(null);

  function choose(t: CreateType) {
    setType(t);
  }

  function close() {
    setOpen(false);
    setType(null);
  }

  const TYPES: { key: CreateType; label: string; icon: React.ComponentType<{ className?: string }>; color: string }[] = [
    { key: "finding", label: "Finding", icon: AlertTriangle, color: "text-orange-600 hover:bg-orange-50" },
    { key: "risk", label: "Risk", icon: ShieldAlert, color: "text-red-600 hover:bg-red-50" },
    { key: "assessment", label: "Assessment", icon: FileText, color: "text-blue-600 hover:bg-blue-50" },
  ];

  const titleMap: Record<string, string> = { finding: "New Finding", risk: "New Risk", assessment: "New Assessment" };

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => { setOpen((v) => !v); if (open) setType(null); }}
        className={cn(
          "fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all",
          open
            ? "bg-slate-700 text-white rotate-45 hover:bg-slate-800"
            : "bg-blue-600 text-white hover:bg-blue-700"
        )}
        title="Quick Create"
      >
        <Plus className="h-6 w-6" />
      </button>

      {/* Popover */}
      {open && (
        <div className="fixed bottom-22 right-6 z-40 w-72 rounded-xl border border-border bg-background shadow-2xl">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <p className="text-sm font-semibold">{type ? titleMap[type] : "Quick Create"}</p>
            <button onClick={close} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="p-4">
            {!type ? (
              <div className="space-y-1">
                {TYPES.map(({ key, label, icon: Icon, color }) => (
                  <button
                    key={key}
                    onClick={() => choose(key)}
                    className={cn("flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors", color)}
                  >
                    <Icon className="h-4 w-4" />
                    {label}
                  </button>
                ))}
              </div>
            ) : (
              <>
                <button
                  onClick={() => setType(null)}
                  className="mb-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  ← Back
                </button>
                {type === "finding" && <CreateFindingForm onClose={close} />}
                {type === "risk" && <CreateRiskForm onClose={close} />}
                {type === "assessment" && <CreateAssessmentForm onClose={close} />}
              </>
            )}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-30" onClick={close} />
      )}
    </>
  );
}
