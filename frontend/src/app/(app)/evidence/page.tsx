"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileUp, Loader2, Upload, X } from "lucide-react";
import {
  createEvidence,
  listEvidence,
  uploadDocument,
} from "@/lib/api/evidence";
import {
  extractErrorMessage,
  formatDateTime,
  formatFileSize,
} from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Progress } from "@/components/ui/progress";

type UploadStage =
  | "idle"
  | "creating"
  | "uploading"
  | "done"
  | "error";

interface UploadState {
  stage: UploadStage;
  progress: number;
  error: string;
  result: { chunks_created: number; parser_used: string } | null;
}

export default function EvidencePage() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [uploadState, setUploadState] = useState<UploadState>({
    stage: "idle",
    progress: 0,
    error: "",
    result: null,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["evidence", { page: 1 }],
    queryFn: () => listEvidence({ page: 1, page_size: 20 }),
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setSelectedFile(file);
    if (file && !title) {
      setTitle(file.name.replace(/\.[^.]+$/, ""));
    }
  }

  async function handleUpload() {
    if (!selectedFile || !title.trim()) return;
    setUploadState({ stage: "creating", progress: 0, error: "", result: null });

    let evidenceId: string;
    try {
      const ev = await createEvidence({
        title: title.trim(),
        source: selectedFile.name,
        description: description.trim() || title.trim(),
        evidence_type: "document",
        language: "en",
      });
      evidenceId = ev.id;
    } catch (err) {
      setUploadState((s) => ({
        ...s,
        stage: "error",
        error: extractErrorMessage(err),
      }));
      return;
    }

    setUploadState((s) => ({ ...s, stage: "uploading" }));
    try {
      const result = await uploadDocument(evidenceId, selectedFile, (pct) => {
        setUploadState((s) => ({ ...s, progress: pct }));
      });
      setUploadState({
        stage: "done",
        progress: 100,
        error: "",
        result: {
          chunks_created: result.chunks_created,
          parser_used: result.parser_used,
        },
      });
      queryClient.invalidateQueries({ queryKey: ["evidence"] });
      // Reset form
      setSelectedFile(null);
      setTitle("");
      setDescription("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setUploadState((s) => ({
        ...s,
        stage: "error",
        error: extractErrorMessage(err),
      }));
    }
  }

  function ingestionBadge(status: string, chunks: number) {
    switch (status) {
      case "ingested":
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700 font-medium">
            <CheckCircle2 className="h-3 w-3" />
            {chunks} chunks
          </span>
        );
      case "ocr_required":
        return (
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700 font-medium">
            OCR required
          </span>
        );
      case "failed":
        return (
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs text-red-700 font-medium">
            Failed
          </span>
        );
      default:
        return (
          <span className="rounded-full bg-slate-50 px-2 py-0.5 text-xs text-slate-600 font-medium">
            {status}
          </span>
        );
    }
  }

  const canUpload =
    !!selectedFile && !!title.trim() && uploadState.stage === "idle";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Evidence Library</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload and manage source documents for ESG analysis
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Upload panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upload Document</CardTitle>
            <CardDescription>
              PDF, DOCX, or XLSX — up to 50 MB. Documents are parsed and
              embedded for semantic search.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File drop zone */}
            <div
              onClick={() => fileRef.current?.click()}
              className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-8 text-center transition-colors hover:border-primary hover:bg-muted/50"
            >
              <FileUp className="mb-2 h-8 w-8 text-muted-foreground" />
              {selectedFile ? (
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {selectedFile.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-medium">Click to select file</p>
                  <p className="text-xs text-muted-foreground">
                    PDF, DOCX, XLSX
                  </p>
                </div>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.xlsx"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            {selectedFile && (
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  if (fileRef.current) fileRef.current.value = "";
                }}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive"
              >
                <X className="h-3 w-3" /> Remove file
              </button>
            )}

            <div className="space-y-2">
              <Label htmlFor="ev-title">Document title</Label>
              <Input
                id="ev-title"
                placeholder="Annual Sustainability Report 2024"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ev-desc">Description (optional)</Label>
              <Textarea
                id="ev-desc"
                placeholder="Brief description of the document content…"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            {/* Upload progress */}
            {uploadState.stage === "uploading" && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Uploading…</span>
                  <span>{uploadState.progress}%</span>
                </div>
                <Progress value={uploadState.progress} className="h-2" />
              </div>
            )}

            {uploadState.stage === "creating" && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Spinner size="sm" /> Creating evidence record…
              </div>
            )}

            {uploadState.stage === "done" && uploadState.result && (
              <div className="flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                Ingested {uploadState.result.chunks_created} chunks via{" "}
                {uploadState.result.parser_used}.{" "}
                <button
                  type="button"
                  className="ml-auto text-xs underline"
                  onClick={() =>
                    setUploadState({
                      stage: "idle",
                      progress: 0,
                      error: "",
                      result: null,
                    })
                  }
                >
                  Upload another
                </button>
              </div>
            )}

            {uploadState.stage === "error" && (
              <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 border border-red-200">
                {uploadState.error}
              </div>
            )}

            <Button
              className="w-full"
              onClick={handleUpload}
              disabled={
                !canUpload ||
                uploadState.stage === "creating" ||
                uploadState.stage === "uploading"
              }
            >
              {uploadState.stage === "creating" ||
              uploadState.stage === "uploading" ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing…
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Upload & Ingest
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Evidence list */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {data ? `${data.total} document${data.total !== 1 ? "s" : ""}` : "Documents"}
            </CardTitle>
            <CardDescription>
              Source files available for assessment
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : !data?.items.length ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No documents uploaded yet.
              </p>
            ) : (
              <div className="space-y-2">
                {data.items.map((ev) => (
                  <div
                    key={ev.id}
                    className="flex items-start justify-between rounded-lg border border-border p-3 hover:bg-muted/40 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {ev.title}
                      </p>
                      <div className="mt-0.5 flex items-center gap-2">
                        {ev.file_name && (
                          <span className="text-xs text-muted-foreground">
                            {ev.file_name}
                          </span>
                        )}
                        {ev.file_size_bytes && (
                          <span className="text-xs text-muted-foreground">
                            ({formatFileSize(ev.file_size_bytes)})
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatDateTime(ev.created_at)}
                      </p>
                    </div>
                    <div className="ml-3 flex-shrink-0">
                      {ingestionBadge(ev.ingestion_status, ev.chunk_count)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
