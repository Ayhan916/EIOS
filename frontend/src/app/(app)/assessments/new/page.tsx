"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, Loader2 } from "lucide-react";
import { startWorkflow, getJob, getWorkflowTypes } from "@/lib/api/workflows";
import { extractErrorMessage } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const schema = z.object({
  workflow_type: z.string().min(1, "Select a workflow type"),
  query: z
    .string()
    .min(10, "Query must be at least 10 characters")
    .max(10000),
});
type FormData = z.infer<typeof schema>;

type JobState = "idle" | "submitted" | "polling" | "done" | "failed";

export default function NewAssessmentPage() {
  const router = useRouter();
  const [jobState, setJobState] = useState<JobState>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [workflowTypes, setWorkflowTypes] = useState<
    { workflow_type: string; description: string }[]
  >([]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { workflow_type: "", query: "" },
  });

  const selectedType = watch("workflow_type");

  useEffect(() => {
    getWorkflowTypes()
      .then(setWorkflowTypes)
      .catch(() => {});
  }, []);

  // Poll for job completion
  useEffect(() => {
    if (jobState !== "polling" || !jobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await getJob(jobId);
        if (job.job_status === "completed") {
          clearInterval(interval);
          setAssessmentId(job.workflow_run_id ?? null);
          setJobState("done");
        } else if (job.job_status === "failed") {
          clearInterval(interval);
          setError(job.error ?? "Workflow failed");
          setJobState("failed");
        }
      } catch {
        // silently retry
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [jobState, jobId]);

  async function onSubmit(data: FormData) {
    setError("");
    setJobState("submitted");
    try {
      const res = await startWorkflow(data);
      setJobId(res.job_id);
      setJobState("polling");
    } catch (err) {
      setError(extractErrorMessage(err));
      setJobState("failed");
    }
  }

  if (jobState === "done") {
    return (
      <div className="mx-auto max-w-lg space-y-6">
        <Card>
          <CardContent className="pt-8 pb-8 text-center space-y-4">
            <div className="flex justify-center">
              <CheckCircle2 className="h-16 w-16 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Assessment complete</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The ESG analysis has finished. View your findings, risks, and
                recommendations below.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
              {assessmentId && (
                <Button
                  onClick={() =>
                    router.push(`/assessments/${assessmentId}`)
                  }
                >
                  View Assessment
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => {
                  setJobState("idle");
                  setJobId(null);
                  setAssessmentId(null);
                }}
              >
                Run Another
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (jobState === "polling" || jobState === "submitted") {
    return (
      <div className="mx-auto max-w-lg">
        <Card>
          <CardContent className="pt-8 pb-8 text-center space-y-4">
            <Spinner size="lg" className="mx-auto" />
            <div>
              <h2 className="text-xl font-semibold">
                {jobState === "submitted"
                  ? "Submitting workflow…"
                  : "Analysis in progress…"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The AI agents are processing your query. This typically takes
                1–3 minutes. You can navigate away and return to Assessments to
                check progress.
              </p>
            </div>
            <Button variant="outline" onClick={() => router.push("/assessments")}>
              Go to Assessments
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Assessment</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Launch an AI-powered ESG due diligence workflow
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Workflow Configuration</CardTitle>
            <CardDescription>
              Choose the analysis type and describe what you want to assess
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-2">
              <Label>Workflow type</Label>
              <Select
                value={selectedType}
                onValueChange={(v) =>
                  setValue("workflow_type", v, { shouldValidate: true })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select workflow type…" />
                </SelectTrigger>
                <SelectContent>
                  {workflowTypes.length ? (
                    workflowTypes.map((wt) => (
                      <SelectItem key={wt.workflow_type} value={wt.workflow_type}>
                        {wt.workflow_type}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="esg_due_diligence">
                      esg_due_diligence
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
              {errors.workflow_type && (
                <p className="text-xs text-destructive">
                  {errors.workflow_type.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="query">Assessment query</Label>
              <Textarea
                id="query"
                placeholder="Describe the company, sector, or specific ESG concerns to analyse. For example: 'Assess ESG risks for a NACE C13 textile manufacturer with operations in Bangladesh, focusing on supply chain due diligence under CSDDD and LkSG.'"
                rows={6}
                {...register("query")}
              />
              {errors.query && (
                <p className="text-xs text-destructive">
                  {errors.query.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Be specific: include sector (NACE code), geography, applicable
                frameworks (CSRD, CSDDD, LkSG), and areas of concern.
              </p>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Launching…
              </>
            ) : (
              "Launch Assessment"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
