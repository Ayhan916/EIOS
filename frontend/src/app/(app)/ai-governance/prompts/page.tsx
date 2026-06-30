"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Clock, FileCode } from "lucide-react";
import { listPrompts, approvePrompt } from "@/lib/api/ai-governance";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useLanguage } from "@/lib/i18n/context";

const ORG_ID = "default";

export default function PromptsPage() {
  const { t } = useLanguage();
  const qc = useQueryClient();

  const { data: prompts = [], isLoading } = useQuery({
    queryKey: ["ai-prompts", ORG_ID],
    queryFn: () => listPrompts(ORG_ID),
    retry: false,
  });

  const approve = useMutation({
    mutationFn: (promptId: string) => approvePrompt(ORG_ID, promptId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ai-prompts", ORG_ID] }),
  });

  if (isLoading) return <Spinner className="mt-12 mx-auto" />;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("aiGov.promptsTitle")}</h1>
        <p className="text-sm text-muted-foreground">
          {t("aiGov.promptsSubtitle")}
        </p>
      </div>

      {prompts.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <FileCode className="mx-auto mb-3 h-10 w-10 opacity-30" />
          <p className="text-sm">{t("aiGov.noPromptsDesc")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prompts.map((p) => (
            <Card key={p.id}>
              <CardContent className="pt-4 pb-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold">{p.name}</p>
                      <Badge className="bg-slate-100 text-slate-600">v{p.prompt_version}</Badge>
                      {p.is_approved ? (
                        <Badge className="bg-emerald-100 text-emerald-800">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          Approved
                        </Badge>
                      ) : (
                        <Badge className="bg-amber-100 text-amber-800">
                          <Clock className="mr-1 h-3 w-3" />
                          Pending Approval
                        </Badge>
                      )}
                    </div>
                    {p.approved_by && (
                      <p className="text-xs text-muted-foreground">
                        Approved by {p.approved_by}
                        {p.approved_at ? ` · ${new Date(p.approved_at).toLocaleDateString()}` : ""}
                      </p>
                    )}
                  </div>
                  {!p.is_approved && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => approve.mutate(p.id)}
                      disabled={approve.isPending}
                    >
                      {t("exec.approve")}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
