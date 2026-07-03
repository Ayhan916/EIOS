"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { Download, X } from "lucide-react";
import { getEvidenceChain } from "@/lib/api/evidence-chain";
import type { ChainNode, FindingFilterOption } from "@/lib/api/evidence-chain";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";

// ── Node colours per type ─────────────────────────────────────────────────────
const NODE_COLOR: Record<string, string> = {
  evidence:       "#94a3b8",  // slate  – input layer
  finding:        "#f97316",  // orange – observed issues
  risk:           "#ef4444",  // red    – risk items
  recommendation: "#22c55e",  // green  – remediation
  cap:            "#a855f7",  // violet – corrective action plan
};

const NODE_LABEL: Record<string, string> = {
  evidence:       "Evidence",
  finding:        "Finding",
  risk:           "Risk",
  recommendation: "Recommendation",
  cap:            "CAP",
};

// ── Selected node panel ───────────────────────────────────────────────────────
function NodePanel({ node, onClose }: { node: ChainNode; onClose: () => void }) {
  const color = NODE_COLOR[node.node_type] ?? "#64748b";
  const typeLabel = NODE_LABEL[node.node_type] ?? node.node_type;

  return (
    <div className="absolute top-3 right-3 w-64 rounded-xl border border-border bg-white shadow-xl p-3 space-y-2 z-10">
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full px-2 py-0.5 text-[10px] font-bold text-white" style={{ background: color }}>
          {typeLabel}
        </span>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <p className="text-sm font-semibold leading-snug">{node.label}</p>
      <p className="text-[10px] text-muted-foreground capitalize">{node.detail.replace(/_/g, " ")}</p>
      {node.href && (
        <Link
          href={node.href}
          className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          Öffnen →
        </Link>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function EvidenceChainTab({ assessmentId }: { assessmentId: string }) {
  const [findingFilter, setFindingFilter] = useState<string>("");
  const [selected, setSelected] = useState<ChainNode | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["evidence-chain", assessmentId, findingFilter],
    queryFn: () => getEvidenceChain(assessmentId, findingFilter || undefined),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  useEffect(() => {
    if (!containerRef.current || !data) return;

    // Destroy previous instance
    if (cyRef.current) {
      cyRef.current.destroy();
      cyRef.current = null;
    }

    if (data.nodes.length === 0) return;

    const elements: ElementDefinition[] = [
      ...data.nodes.map((n) => ({
        data: { id: n.id, label: n.label, nodeType: n.node_type, detail: n.detail, href: n.href },
        classes: n.node_type,
      })),
      ...data.edges.map((e, i) => ({
        data: { id: `e-${i}`, source: e.source, target: e.target, label: e.label },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      layout: {
        name: "breadthfirst",
        directed: true,
        spacingFactor: 1.4,
        avoidOverlap: true,
        animate: false,
      } as cytoscape.LayoutOptions,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "bottom" as const,
            "text-halign": "center" as const,
            "font-size": "9px",
            "text-wrap": "ellipsis" as const,
            "text-max-width": "90px",
            color: "#1e293b",
            width: 40,
            height: 40,
            "border-width": 2,
            "border-color": "#fff",
            "background-color": "#94a3b8",
            "overlay-padding": "4px",
          },
        },
        ...Object.entries(NODE_COLOR).map(([type, color]) => ({
          selector: `.${type}`,
          style: { "background-color": color },
        })),
        {
          selector: "node:selected",
          style: {
            "border-color": "#1d4ed8",
            "border-width": 4,
          },
        },
        {
          selector: "edge",
          style: {
            "line-color": "#cbd5e1",
            width: 1.5,
            "target-arrow-shape": "triangle" as const,
            "target-arrow-color": "#cbd5e1",
            "curve-style": "bezier" as const,
            label: "data(label)",
            "font-size": "8px",
            color: "#94a3b8",
            "text-rotation": "autorotate" as const,
          },
        },
      ],
    });

    cy.on("tap", "node", (evt) => {
      const nd = evt.target.data();
      setSelected({
        id: nd.id,
        node_type: nd.nodeType,
        label: nd.label,
        detail: nd.detail,
        href: nd.href,
      });
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelected(null);
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [data]);

  function handleExportPng() {
    if (!cyRef.current) return;
    const png = (cyRef.current as Core).png({ full: true, scale: 2 });
    const a = document.createElement("a");
    a.href = png;
    a.download = `evidence-chain-${assessmentId}.png`;
    a.click();
  }

  const filterOptions: FindingFilterOption[] = data?.finding_filter_options ?? [];

  return (
    <div className="space-y-3">
      {/* Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          value={findingFilter}
          onChange={(e) => { setFindingFilter(e.target.value); setSelected(null); }}
        >
          <option value="">Alle Findings</option>
          {filterOptions.map((f) => (
            <option key={f.id} value={f.id}>
              [{f.severity}] {f.title.slice(0, 60)}
            </option>
          ))}
        </select>

        <Button variant="outline" size="sm" className="gap-1.5 h-8" onClick={handleExportPng}>
          <Download className="h-3.5 w-3.5" /> PNG Export
        </Button>

        {/* Legend */}
        <div className="flex items-center gap-2 flex-wrap ml-auto">
          {Object.entries(NODE_COLOR).map(([type, color]) => (
            <span key={type} className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
              {NODE_LABEL[type]}
            </span>
          ))}
        </div>
      </div>

      {/* Graph container */}
      <div className="relative rounded-xl border border-border bg-slate-50/60 overflow-hidden" style={{ height: 480 }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/60">
            <Spinner />
          </div>
        )}
        {isError && (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
            Graph konnte nicht geladen werden.
          </div>
        )}
        {data && data.nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-sm text-muted-foreground">
            <p className="font-semibold">Keine Verknüpfungen vorhanden</p>
            <p className="text-xs">Füge Findings, Risks und Empfehlungen hinzu um die Evidence Chain zu sehen.</p>
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" />
        {selected && <NodePanel node={selected} onClose={() => setSelected(null)} />}
      </div>

      <p className="text-[10px] text-muted-foreground">
        Klick auf einen Knoten für Details · Breadthfirst-Layout (Evidence → Finding → Risk → Recommendation → CAP)
      </p>
    </div>
  );
}
