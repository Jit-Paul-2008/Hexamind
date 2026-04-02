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
    position: { x: 520, y: 20 },
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
      role: "Opportunity Thesis and Upside Proof",
      accentColor: "#818cf8",
    },
  },
  {
    id: "advocate-processing",
    type: "processingNode",
    position: { x: 380, y: 180 },
    data: {
      agentId: "advocate",
      label: "Advocate",
      accentColor: "#818cf8",
    },
  },
  // ── Skeptic — right branch
  {
    id: "skeptic",
    type: "agentNode",
    position: { x: 920, y: 180 },
    data: {
      agentId: "skeptic",
      label: "Skeptic",
      role: "Risk Decomposition and Failure Modes",
      accentColor: "#f87171",
    },
  },
  {
    id: "skeptic-processing",
    type: "processingNode",
    position: { x: 1220, y: 180 },
    data: {
      agentId: "skeptic",
      label: "Skeptic",
      accentColor: "#f87171",
    },
  },
  // ── Synthesiser — merges branches
  {
    id: "synthesiser",
    type: "agentNode",
    position: { x: 500, y: 430 },
    data: {
      agentId: "synthesiser",
      label: "Synthesiser",
      role: "Decision Integration and Tradeoff Resolution",
      accentColor: "#34d399",
    },
  },
  {
    id: "synthesiser-processing",
    type: "processingNode",
    position: { x: 800, y: 430 },
    data: {
      agentId: "synthesiser",
      label: "Synthesiser",
      accentColor: "#34d399",
    },
  },
  // ── Oracle — final inference
  {
    id: "oracle",
    type: "agentNode",
    position: { x: 500, y: 680 },
    data: {
      agentId: "oracle",
      label: "Oracle",
      role: "Scenario Forecasting and Execution Outlook",
      accentColor: "#fbbf24",
    },
  },
  {
    id: "oracle-processing",
    type: "processingNode",
    position: { x: 800, y: 680 },
    data: {
      agentId: "oracle",
      label: "Oracle",
      accentColor: "#fbbf24",
    },
  },
  // ── Output node — bottom
  {
    id: "output",
    type: "outputNode",
    position: { x: 500, y: 930 },
    data: { label: "Output" },
  },
];
