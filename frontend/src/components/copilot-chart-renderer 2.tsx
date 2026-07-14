"use client";

import { useEffect, useRef, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ChartSpec {
  type: "bar" | "line" | "pie";
  title?: string;
  unit?: string;
  data: { label: string; [key: string]: string | number }[];
  keys?: string[];       // which numeric keys to plot (bar/line)
  colors?: string[];
}

// ── Colors ────────────────────────────────────────────────────────────────────

const PALETTE = [
  "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5",
];

// ── Recharts wrapper ──────────────────────────────────────────────────────────

function DataChart({ spec }: { spec: ChartSpec }) {
  const keys = spec.keys ?? Object.keys(spec.data[0] ?? {}).filter(k => k !== "label");
  const colors = spec.colors ?? PALETTE;

  const tooltip = ({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number }[]; label?: string }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="rounded-lg border bg-white shadow-md px-3 py-2 text-xs">
        <p className="font-semibold mb-1">{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: colors[i % colors.length] }}>
            {p.name}: <strong>{p.value}{spec.unit ? ` ${spec.unit}` : ""}</strong>
          </p>
        ))}
      </div>
    );
  };

  return (
    <div className="rounded-xl border bg-white p-4 my-3">
      {spec.title && <p className="text-sm font-semibold text-slate-700 mb-3">{spec.title}</p>}
      <ResponsiveContainer width="100%" height={260}>
        {spec.type === "pie" ? (
          <PieChart>
            <Pie data={spec.data} dataKey={keys[0]} nameKey="label" cx="50%" cy="50%" outerRadius={90} label={({ label, value }) => `${label}: ${value}${spec.unit ?? ""}`}>
              {spec.data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
            </Pie>
            <Tooltip content={tooltip as never} />
            <Legend />
          </PieChart>
        ) : spec.type === "line" ? (
          <LineChart data={spec.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit={spec.unit} />
            <Tooltip content={tooltip as never} />
            <Legend />
            {keys.map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} stroke={colors[i % colors.length]} strokeWidth={2} dot={{ r: 4 }} />
            ))}
          </LineChart>
        ) : (
          <BarChart data={spec.data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit={spec.unit} />
            <Tooltip content={tooltip as never} />
            <Legend />
            {keys.map((k, i) => (
              <Bar key={k} dataKey={k} fill={colors[i % colors.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

// ── Mermaid wrapper ───────────────────────────────────────────────────────────

function sanitizeMermaid(raw: string): string {
  const s = raw.trim();

  // Already well-formed: has more than 2 non-empty lines
  const nonEmpty = s.split("\n").filter(l => l.trim());
  if (nonEmpty.length > 2) return s;

  // Extract graph directive ("graph TD", "flowchart LR", "sequenceDiagram", etc.)
  const directiveMatch = s.match(/^((?:graph|flowchart)\s+\w+|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|gantt|pie(?:\s+title)?)\s*/i);
  if (!directiveMatch) return s;

  const directive = directiveMatch[1];
  let rest = s.slice(directiveMatch[0].length);

  // Insert newline before each new statement:
  // A new statement starts with a word-char after a closing bracket,
  // BUT only when the next token is NOT an arrow (-->, ---, ==>, -.->)
  // Split after closing ] or ) when NOT followed by an arrow (-->, ---, ==>)
  rest = rest.replace(/([)\]])\s+(?!-[->{=])(?=[A-Za-z_])/g, "$1\n    ");

  // Also split on subgraph keyword and end
  rest = rest.replace(/\s+(subgraph\s|end\b)/g, "\n    $1");

  return `${directive}\n    ${rest}`;
}

function MermaidChart({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const render = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
        const id = `mermaid-${Math.random().toString(36).slice(2)}`;
        const { svg } = await mermaid.render(id, sanitizeMermaid(code));
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    };
    render();
    return () => { cancelled = true; };
  }, [code]);

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-3 my-3 text-xs text-red-700">
        Diagramm konnte nicht gerendert werden: {error}
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-white p-4 my-3 overflow-x-auto">
      <div ref={ref} className="flex justify-center" />
    </div>
  );
}

// ── Main parser: splits message text into text + chart blocks ─────────────────

interface Block {
  type: "text" | "chart" | "mermaid";
  content: string;
}

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const regex = /```(chart|mermaid)\n([\s\S]*?)```/g;
  let last = 0;
  let match;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      blocks.push({ type: "text", content: text.slice(last, match.index) });
    }
    blocks.push({ type: match[1] as "chart" | "mermaid", content: match[2].trim() });
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    blocks.push({ type: "text", content: text.slice(last) });
  }
  return blocks;
}

// ── Public component ──────────────────────────────────────────────────────────

export function CopilotMessageRenderer({ content }: { content: string }) {
  const blocks = parseBlocks(content);

  return (
    <>
      {blocks.map((block, i) => {
        if (block.type === "chart") {
          try {
            const spec: ChartSpec = JSON.parse(block.content);
            return <DataChart key={i} spec={spec} />;
          } catch {
            return <pre key={i} className="text-xs text-red-500">{block.content}</pre>;
          }
        }
        if (block.type === "mermaid") {
          return <MermaidChart key={i} code={block.content} />;
        }
        return (
          <span key={i} className="whitespace-pre-wrap">{block.content}</span>
        );
      })}
    </>
  );
}
