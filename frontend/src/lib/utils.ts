import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function severityColor(
  level: string
): { bg: string; text: string; dot: string } {
  switch (level?.toLowerCase()) {
    case "critical":
      return { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500" };
    case "high":
      return {
        bg: "bg-orange-50",
        text: "text-orange-700",
        dot: "bg-orange-500",
      };
    case "medium":
      return {
        bg: "bg-amber-50",
        text: "text-amber-700",
        dot: "bg-amber-500",
      };
    case "low":
      return {
        bg: "bg-emerald-50",
        text: "text-emerald-700",
        dot: "bg-emerald-500",
      };
    default:
      return { bg: "bg-slate-50", text: "text-slate-700", dot: "bg-slate-400" };
  }
}

export function verdictColor(status: string): string {
  switch (status?.toLowerCase()) {
    case "compliant":
      return "text-emerald-600";
    case "partially_compliant":
      return "text-amber-600";
    case "non_compliant":
      return "text-red-600";
    default:
      return "text-slate-500";
  }
}

export function jobStatusColor(status: string): {
  bg: string;
  text: string;
} {
  switch (status?.toLowerCase()) {
    case "completed":
      return { bg: "bg-emerald-50", text: "text-emerald-700" };
    case "running":
    case "pending":
      return { bg: "bg-blue-50", text: "text-blue-700" };
    case "failed":
      return { bg: "bg-red-50", text: "text-red-700" };
    default:
      return { bg: "bg-slate-50", text: "text-slate-600" };
  }
}

export function extractErrorMessage(error: unknown): string {
  if (!error) return "An unexpected error occurred";
  if (typeof error === "string") return error;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const err = error as any;
  if (err.response?.data?.detail) {
    const detail = err.response.data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg: string }) => d.msg).join(", ");
    }
  }
  if (err.message) return err.message;
  return "An unexpected error occurred";
}
