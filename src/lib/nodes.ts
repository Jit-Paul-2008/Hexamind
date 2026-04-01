// ─────────────────────────────────────────────────────────────────────────────
// Node layout definitions for the ReactFlow canvas
// Diamond pipeline layout: Input → Advocate + Skeptic → Synthesiser → Oracle → Output
// ─────────────────────────────────────────────────────────────────────────────

import type { Node } from "@xyflow/react";

export const INITIAL_NODES: Node[] = [
  // ── Input node — top centre
  {
    id: "input",
    type: "inputNode",
    position: { x: 350, y: 0 },
    data: { label: "Input" },
  },
  // ── Advocate — left branch
  {
    id: "advocate",
    type: "agentNode",
    position: { x: 80, y: 180 },
    data: {
      agentId: "advocate",
      label: "Advocate",
      role: "Constructive Reasoning",
      accentColor: "#818cf8",
    },
  },
  // ── Skeptic — right branch
  {
    id: "skeptic",
    type: "agentNode",
    position: { x: 580, y: 180 },
    data: {
      agentId: "skeptic",
      label: "Skeptic",
      role: "Adversarial Stress-Testing",
      accentColor: "#f87171",
    },
  },
  // ── Synthesiser — merges branches
  {
    id: "synthesiser",
    type: "agentNode",
    position: { x: 330, y: 380 },
    data: {
      agentId: "synthesiser",
      label: "Synthesiser",
      role: "Perspective Integration",
      accentColor: "#34d399",
    },
  },
  // ── Oracle — final inference
  {
    id: "oracle",
    type: "agentNode",
    position: { x: 330, y: 560 },
    data: {
      agentId: "oracle",
      label: "Oracle",
      role: "Predictive Inference",
      accentColor: "#fbbf24",
    },
  },
  // ── Output node — bottom
  {
    id: "output",
    type: "outputNode",
    position: { x: 330, y: 740 },
    data: { label: "Output" },
  },
];
