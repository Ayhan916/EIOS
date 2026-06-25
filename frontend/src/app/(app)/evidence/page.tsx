"use client";

import React, { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Eye, EyeOff, FileText, FileUp, Link2, Loader2, Upload, X } from "lucide-react";
import {
  createEvidence,
  listEvidence,
  uploadDocument,
} from "@/lib/api/evidence";
import { operatingSystemApi } from "@/lib/api/operating-system";
import apiClient from "@/lib/api/client";
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

function LinkToControlPanel({ evidenceId, onClose }: { evidenceId: string; onClose: () => void }) {
  const [controlId, setControlId] = useState("");
  const [linked, setLinked] = useState(false);

  const { data: controls = [] } = useQuery({
    queryKey: ["esg-controls-for-link"],
    queryFn: () => operatingSystemApi.listControls({ limit: 100 }).then((r) => r.data),
    staleTime: 300_000,
  });

  const { mutate, isPending } = useMutation({
    mutationFn: async () => {
      await apiClient.post(`/evidences/${evidenceId}/link-control`, { control_id: controlId });
    },
    onSuccess: () => setLinked(true),
  });

  if (linked) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
        <CheckCircle2 className="h-3 w-3" /> Linked to control
      </div>
    );
  }

  return (
    <div className="mt-2 flex items-center gap-2 flex-wrap">
      <select
        className="h-7 rounded border border-input bg-background px-2 text-xs flex-1 min-w-32"
        value={controlId}
        onChange={(e) => setControlId(e.target.value)}
      >
        <option value="">Select control…</option>
        {controls.map((c) => (
          <option key={c.id} value={c.id}>{c.control_name}</option>
        ))}
      </select>
      <button
        onClick={() => mutate()}
        disabled={!controlId || isPending}
        className="inline-flex items-center gap-1 rounded bg-violet-600 px-2 py-1 text-[10px] font-medium text-white hover:bg-violet-700 disabled:opacity-50"
      >
        {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Link2 className="h-3 w-3" />}
        Link
      </button>
      <button onClick={onClose} className="text-[10px] text-muted-foreground hover:underline">Cancel</button>
    </div>
  );
}

// ── #144 Evidence viewer ──────────────────────────────────────────────────────

function isImage(filename: string) {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(filename ?? "");
}
function isPdf(filename: string) {
  return /\.pdf$/i.test(filename ?? "");
}

function EvidencePreview({ ev }: { ev: any }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Fetch the document with auth and create a blob URL
  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("eios_access_token") : null;
    fetch(`/api/v1/evidences/${ev.id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error("not found");
        return r.blob();
      })
      .then((blob) => {
        setObjectUrl(URL.createObjectURL(blob));
        setLoading(false);
      })
      .catch(() => { setError(true); setLoading(false); });
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ev.id]);

  if (loading) return <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>;
  if (error || !objectUrl) return <p className="py-4 text-center text-xs text-muted-foreground">Preview unavailable — document not yet uploaded or access denied.</p>;

  if (isPdf(ev.file_name)) {
    return <iframe src={objectUrl} className="w-full rounded border" style={{ height: 480 }} title={ev.title} />;
  }
  if (isImage(ev.file_name)) {
    return <img src={objectUrl} alt={ev.title} className="max-h-96 w-auto rounded border mx-auto" />;
  }
  return (
    <div className="flex flex-col items-center gap-2 py-6 text-center">
      <FileText className="h-8 w-8 text-muted-foreground/40" />
      <p className="text-xs text-muted-foreground">No in-browser preview for this file type.</p>
      <a href={objectUrl} download={ev.file_name} className="text-xs text-blue-600 hover:underline">Download instead</a>
    </div>
  );
}

function EvidenceRow({
  ev,
  ingestionBadge,
}: {
  ev: any;
  ingestionBadge: (status: string, chunks: number) => React.ReactNode;
}) {
  const [showLink, setShowLink] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const hasFile = !!ev.file_name;

  return (
    <div className="rounded-lg border border-border p-3 hover:bg-muted/40 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{ev.title}</p>
          <div className="mt-0.5 flex items-center gap-2">
            {ev.file_name && (
              <span className="text-xs text-muted-foreground">{ev.file_name}</span>
            )}
            {ev.file_size_bytes && (
              <span className="text-xs text-muted-foreground">({formatFileSize(ev.file_size_bytes)})</span>
            )}
          </div>
          <p className="mt-0.5 text-xs text-muted-foreground">{formatDateTime(ev.created_at)}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {ingestionBadge(ev.ingestion_status, ev.chunk_count)}
          {hasFile && (
            <button
              onClick={() => setShowPreview((v) => !v)}
              className="text-[10px] text-blue-600 hover:underline flex items-center gap-0.5"
              title="Preview document"
            >
              {showPreview ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </button>
          )}
          <button
            onClick={() => setShowLink((v) => !v)}
            className="text-[10px] text-violet-600 hover:underline flex items-center gap-0.5"
            title="Link to control"
          >
            <Link2 className="h-3 w-3" />
          </button>
        </div>
      </div>
      {showPreview && hasFile && (
        <div className="mt-3 border-t pt-3">
          <EvidencePreview ev={ev} />
        </div>
      )}
      {showLink && (
        <LinkToControlPanel evidenceId={ev.id} onClose={() => setShowLink(false)} />
      )}
    </div>
  );
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
                  <EvidenceRow key={ev.id} ev={ev} ingestionBadge={ingestionBadge} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
