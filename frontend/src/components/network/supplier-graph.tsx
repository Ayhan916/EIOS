"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { cn } from "@/lib/utils";
import { ArrowRight, X, AlertTriangle, CheckCircle } from "lucide-react";

const TIER_COLORS: Record<number, string> = {
  1: "#3b82f6",
  2: "#8b5cf6",
  3: "#f59e0b",
  4: "#6b7280",
};

const RISK_BORDER: Record<string, string> = {
  HIGH: "#ef4444",
  MEDIUM: "#f59e0b",
  LOW: "#10b981",
};

export interface GraphSupplier {
  id: string;
  name: string;
  tier: number;
  overall_risk_level?: string | null;
  country?: string | null;
  score?: number | null;
  industry?: string | null;
}

export interface GraphRelationship {
  source: string;
  target: string;
  relationship_type?: string;
}

interface Props {
  suppliers: GraphSupplier[];
  relationships: GraphRelationship[];
  ownOrgName?: string;
  className?: string;
}

function RiskIcon({ level }: { level?: string | null }) {
  if (level === "HIGH") return <AlertTriangle className="h-4 w-4 text-red-500" />;
  if (level === "MEDIUM") return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  return <CheckCircle className="h-4 w-4 text-emerald-500" />;
}

export function SupplierGraph({ suppliers, relationships, ownOrgName = "Your Org", className }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<GraphSupplier | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const elements: ElementDefinition[] = [
      // Central org node
      {
        data: { id: "__org__", label: ownOrgName, tier: 0 },
        classes: "org-node",
      },
      // Supplier nodes
      ...suppliers.map((s) => ({
        data: {
          id: s.id,
          label: s.name,
          tier: s.tier,
          riskLevel: s.overall_risk_level ?? "LOW",
          country: s.country ?? "",
          score: s.score,
        },
        classes: `tier-${s.tier}`,
      })),
      // Edges
      ...relationships.map((r) => ({
        data: {
          id: `${r.source}-${r.target}`,
          source: r.source,
          target: r.target,
          type: r.relationship_type ?? "direct",
        },
      })),
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      layout: {
        name: "cose",
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: () => 100,
      } as cytoscape.LayoutOptions,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "text-valign": "bottom",
            "text-halign": "center",
            "font-size": "10px",
            "text-wrap": "ellipsis",
            "text-max-width": "80px",
            color: "#1e293b",
            "background-color": "#3b82f6",
            width: 36,
            height: 36,
            "border-width": 2,
            "border-color": "#fff",
          },
        },
        {
          selector: ".org-node",
          style: {
            "background-color": "#1e40af",
            width: 48,
            height: 48,
            "border-color": "#93c5fd",
            "border-width": 3,
            "font-weight": "bold",
          },
        },
        ...([1, 2, 3, 4] as const).map((tier) => ({
          selector: `.tier-${tier}`,
          style: { "background-color": TIER_COLORS[tier] },
        })),
        {
          selector: "edge",
          style: {
            "line-color": "#cbd5e1",
            width: 1.5,
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#94a3b8",
            "curve-style": "bezier",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#f59e0b",
            "border-width": 4,
          },
        },
      ],
    });

    cy.on("tap", "node", (evt) => {
      const nodeId = evt.target.id();
      const sup = suppliers.find((s) => s.id === nodeId) ?? null;
      setSelected(sup);
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelected(null);
    });

    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [suppliers, relationships, ownOrgName]);

  return (
    <div className={cn("relative flex h-[520px] rounded-lg border bg-background overflow-hidden", className)}>
      {/* Graph canvas */}
      <div
        ref={containerRef}
        className="flex-1"
        role="img"
        aria-label="Supplier network graph"
      />

      {/* Legend */}
      <div className="absolute left-3 top-3 rounded-md border bg-card/90 p-3 backdrop-blur-sm text-xs space-y-1.5">
        <p className="font-semibold text-foreground mb-2">Tier</p>
        {Object.entries(TIER_COLORS).map(([tier, color]) => (
          <div key={tier} className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-muted-foreground">Tier {tier}</span>
          </div>
        ))}
      </div>

      {/* Sidebar: selected supplier */}
      {selected && (
        <aside
          className="w-64 border-l bg-card p-4 flex flex-col gap-3 overflow-y-auto"
          aria-label="Selected supplier risk summary"
        >
          <div className="flex items-start justify-between">
            <h3 className="font-semibold text-sm text-foreground">{selected.name}</h3>
            <button
              onClick={() => setSelected(null)}
              aria-label="Close supplier panel"
              className="rounded p-0.5 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Tier</span>
              <span
                className="rounded px-1.5 py-0.5 font-medium text-white"
                style={{ backgroundColor: TIER_COLORS[selected.tier] ?? "#64748b" }}
              >
                Tier {selected.tier}
              </span>
            </div>

            {selected.country && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Country</span>
                <span className="text-foreground">{selected.country}</span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Risk Level</span>
              <div className="flex items-center gap-1">
                <RiskIcon level={selected.overall_risk_level} />
                <span
                  className="font-medium"
                  style={{ color: RISK_BORDER[selected.overall_risk_level ?? "LOW"] ?? "#10b981" }}
                >
                  {selected.overall_risk_level ?? "LOW"}
                </span>
              </div>
            </div>

            {selected.score != null && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">ESG Score</span>
                <span className="font-semibold text-foreground">{selected.score}</span>
              </div>
            )}
          </div>

          <Link
            href={`/suppliers/${selected.id}`}
            className="mt-auto flex items-center justify-center gap-1.5 rounded-md border border-border bg-muted/50 px-3 py-2 text-xs font-medium text-foreground hover:bg-muted transition-colors"
          >
            View supplier <ArrowRight className="h-3 w-3" />
          </Link>
        </aside>
      )}
    </div>
  );
}
