// V1 Simplified Agent System for Free Tier Hosting
// Maintains visual consistency while reducing complexity

export type V1AgentShape = "tetrahedron" | "dodecahedron";

export interface V1Agent {
  id: string;
  codename: string;
  role: string;
  purpose: string;
  accentColor: string;
  glowColor: string;
  shape: V1AgentShape;
  processingOrder: number;
  combines: string[]; // Which original agents this combines
}

// V1 Processing order: Analyst → Synthesizer
export const V1_AGENTS: V1Agent[] = [
  {
    id: "analyst",
    codename: "Analyst",
    role: "Balanced Research Analysis",
    purpose: "Provides comprehensive opportunity analysis with built-in risk assessment and evidence evaluation. Combines the upside case from Advocate with critical risk analysis from Skeptic.",
    accentColor: "#818cf8",
    glowColor: "rgba(99, 102, 241, 0.28)",
    shape: "tetrahedron",
    processingOrder: 1,
    combines: ["advocate", "skeptic"]
  },
  {
    id: "synthesizer", 
    codename: "Synthesizer",
    role: "Executive Summary & Forecasting",
    purpose: "Integrates analysis into actionable recommendations with scenario forecasting and confidence assessment. Combines synthesis from Synthesiser, forecasting from Oracle, and verification from Verifier.",
    accentColor: "#34d399",
    glowColor: "rgba(16, 185, 129, 0.28)",
    shape: "dodecahedron",
    processingOrder: 2,
    combines: ["synthesiser", "oracle", "verifier"]
  },
];

// Helper to get V1 agent by ID
export const getV1Agent = (id: string): V1Agent | undefined => {
  return V1_AGENTS.find(agent => agent.id === id);
};

// Helper to get all V1 agent IDs in processing order
export const getV1AgentIds = (): string[] => {
  return V1_AGENTS
    .sort((a, b) => a.processingOrder - b.processingOrder)
    .map(agent => agent.id);
};

// Helper to check if we're in V1 mode
export const isV1Mode = (): boolean => {
  return process.env.NEXT_PUBLIC_V1_MODE === "true";
};

// Helper to get appropriate agents based on mode
export const getAgents = () => {
  return isV1Mode() ? V1_AGENTS : []; // Import original AGENTS if needed
};
