// ─────────────────────────────────────────────────────────────────────────────
// Edge definitions — connections between pipeline nodes
// ─────────────────────────────────────────────────────────────────────────────

import type { Edge } from "@xyflow/react";

export const INITIAL_EDGES: Edge[] = [
  // Input fans out to both Advocate and Skeptic
  {
    id: "input-advocate",
    source: "input",
    target: "advocate",
    type: "animatedEdge",
    data: { color: "#818cf8" },
  },
  {
    id: "input-skeptic",
    source: "input",
    target: "skeptic",
    type: "animatedEdge",
    data: { color: "#f87171" },
  },
  // Both converge into Synthesiser
  {
    id: "advocate-synthesiser",
    source: "advocate",
    target: "synthesiser",
    type: "animatedEdge",
    data: { color: "#34d399" },
  },
  {
    id: "skeptic-synthesiser",
    source: "skeptic",
    target: "synthesiser",
    type: "animatedEdge",
    data: { color: "#34d399" },
  },
  // Synthesiser → Oracle
  {
    id: "synthesiser-oracle",
    source: "synthesiser",
    target: "oracle",
    type: "animatedEdge",
    data: { color: "#fbbf24" },
  },
  // Oracle → Output
  {
    id: "oracle-output",
    source: "oracle",
    target: "output",
    type: "animatedEdge",
    data: { color: "#e2e8f0" },
  },
];
