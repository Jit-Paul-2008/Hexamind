// TODO(backend): replace static array with GET /api/agents when backend is ready
// Agent type mirrors the backend schema — keep in sync with server/models/agent.go

export type AgentShape = "tetrahedron" | "icosahedron" | "dodecahedron" | "box";

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

// Processing order: Advocate → Skeptic → Synthesiser → Oracle
export const AGENTS: Agent[] = [
  {
    id: "advocate",
    codename: "Advocate",
    role: "Constructive Reasoning",
    purpose:
      "Builds the strongest possible case for each hypothesis, surfacing supporting evidence and expanding the solution space.",
    accentColor: "#818cf8",
    glowColor: "rgba(99, 102, 241, 0.28)",
    shape: "tetrahedron",
    processingOrder: 1,
  },
  {
    id: "skeptic",
    codename: "Skeptic",
    role: "Adversarial Stress-Testing",
    purpose:
      "Systematically challenges every assumption and exposes logical blind spots before they compound into costly errors.",
    accentColor: "#f87171",
    glowColor: "rgba(239, 68, 68, 0.28)",
    shape: "icosahedron",
    processingOrder: 2,
  },
  {
    id: "synthesiser",
    codename: "Synthesiser",
    role: "Perspective Integration",
    purpose:
      "Fuses competing viewpoints into a coherent, nuanced answer — resolving contradictions without losing critical signal.",
    accentColor: "#34d399",
    glowColor: "rgba(16, 185, 129, 0.28)",
    shape: "dodecahedron",
    processingOrder: 3,
  },
  {
    id: "oracle",
    codename: "Oracle",
    role: "Predictive Inference",
    purpose:
      "Projects synthesised findings into probable futures, quantifying second-order effects and strategic implications.",
    accentColor: "#fbbf24",
    glowColor: "rgba(245, 158, 11, 0.28)",
    shape: "box",
    processingOrder: 4,
  },
];
