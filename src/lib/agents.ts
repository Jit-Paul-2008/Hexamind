// Agent metadata mirrors backend defaults from ai-service/agents.py.
// Keeping a local copy ensures the graph layout can render immediately.

export type AgentShape = "tetrahedron" | "icosahedron" | "dodecahedron" | "box" | "sphere";

export interface Agent {
  id: string;           // matches backend agent UUID
  codename: string;
  role: string;
  purpose: string;
  accentColor: string;
  glowColor: string;    // rgba string for radial glow
  shape: AgentShape;    // unique polygon assigned to agent
  processingOrder: number; // 1-indexed pipeline position
}

// Processing order: Researcher → Critic (Two-Brain framework)
export const AGENTS: Agent[] = [
  {
    id: "researcher",
    codename: "Researcher",
    role: "Evidence Gathering and Structured Analysis",
    purpose: "Synthesizes sources into a comprehensive, well-structured research report.",
    accentColor: "#10b981",
    glowColor: "rgba(16, 185, 129, 0.28)",
    shape: "tetrahedron",
    processingOrder: 1,
  },
  {
    id: "critic",
    codename: "Critic",
    role: "Bias Detection and Quality Assurance",
    purpose: "Reviews the research report for bias, gaps, and unsupported claims.",
    accentColor: "#f59e0b",
    glowColor: "rgba(245, 158, 11, 0.28)",
    shape: "icosahedron",
    processingOrder: 2,
  },
  // Legacy agents for V2 framework
  {
    id: "advocate",
    codename: "Advocate",
    role: "Opportunity Thesis and Value Realization",
    purpose: "Builds the strongest evidence-based upside case and execution path.",
    accentColor: "#818cf8",
    glowColor: "rgba(99, 102, 241, 0.28)",
    shape: "dodecahedron",
    processingOrder: 3,
  },
  {
    id: "skeptic",
    codename: "Skeptic",
    role: "Risk Decomposition and Failure Analysis",
    purpose: "Challenges assumptions, identifies failure modes, and quantifies downside exposure.",
    accentColor: "#f87171",
    glowColor: "rgba(239, 68, 68, 0.28)",
    shape: "icosahedron",
    processingOrder: 4,
  },
  {
    id: "synthesiser",
    codename: "Synthesiser",
    role: "Tradeoff Integration and Decision Framing",
    purpose: "Integrates competing perspectives into a decision-ready recommendation.",
    accentColor: "#34d399",
    glowColor: "rgba(16, 185, 129, 0.28)",
    shape: "dodecahedron",
    processingOrder: 5,
  },
  {
    id: "oracle",
    codename: "Oracle",
    role: "Scenario Forecasting and Operating Outlook",
    purpose: "Forecasts near-term outcomes with scenario ranges, triggers, and confidence levels.",
    accentColor: "#fbbf24",
    glowColor: "rgba(245, 158, 11, 0.28)",
    shape: "box",
    processingOrder: 6,
  },
  {
    id: "verifier",
    codename: "Verifier",
    role: "Evidence Audit and Claim Verification",
    purpose: "Audits source claims, triangulates evidence, and flags unsupported statements.",
    accentColor: "#60a5fa",
    glowColor: "rgba(59, 130, 246, 0.28)",
    shape: "sphere",
    processingOrder: 7,
  },
];
