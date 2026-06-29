"use client";

import { useQuery } from "@tanstack/react-query";
import apiClient from "@/lib/api/client";
import { Shield } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

const ORG_ID = "default";

interface AIControl {
  id: string;
  name: string;
  control_type: string;
  description: string | null;
  model_id: string | null;
  is_active: boolean;
  created_at: string;
}

function typeColor(t: string) {
  const m: Record<string, string> = {
    PREVENTIVE:  "bg-blue-100 text-blue-800",
    DETECTIVE:   "bg-purple-100 text-purple-800",
    CORRECTIVE:  "bg-amber-100 text-amber-800",
  };
  return m[t] ?? "bg-slate-100 text-slate-600";
}

export default function AIControlsPage() {
  const { data: controls = [], isLoading } = useQuery<AIControl[]>({
    queryKey: ["ai-controls", ORG_ID],
    queryFn: async () => {
      const { data } = await apiClient.get(`/ai-governance/${ORG_ID}/controls`);
      return data;
    },
    retry: false,
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">AI Controls</h1>
        <p className="text-sm text-muted-foreground">
          Governance controls applied to AI models
        </p>
      </div>

      {controls.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Shield className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">No controls defined yet.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {controls.map((c) => (
            <Card key={c.id}>
              <CardContent className="pt-4 pb-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold leading-tight">{c.name}</p>
                  <Badge className={typeColor(c.control_type)}>{c.control_type}</Badge>
                </div>
                {c.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">
                    {c.description}
                  </p>
                )}
                {!c.is_active && (
                  <Badge className="bg-slate-100 text-slate-500">Inactive</Badge>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
