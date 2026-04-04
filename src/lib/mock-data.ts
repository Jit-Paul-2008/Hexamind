export type AriaMode = "chat" | "deep_research" | "decision_brief" | "compare_models" | "scenario_test";

export type Project = {
  id: string;
  name: string;
  description: string;
};

export type CaseItem = {
  id: string;
  projectId: string;
  title: string;
  question: string;
};

export type SourceItem = {
  id: string;
  title: string;
  url: string;
  domain: string;
  relevance: number;
};

export type QualityItem = {
  trustScore: number;
  overallScore: number;
  contradictionCount: number;
  sourceCount: number;
};

export type RunItem = {
  id: string;
  caseId: string;
  backendSessionId?: string;
  mode: AriaMode;
  createdAt: string;
  answer: string;
  sources: SourceItem[];
  quality: QualityItem;
  contradictions: string[];
};

export const projects: Project[] = [
  {
    id: "proj-healthcare",
    name: "Healthcare AI Strategy",
    description: "Assess rollout risk, evidence quality, and adoption pathways.",
  },
  {
    id: "proj-education",
    name: "Education Outcomes",
    description: "Analyze education outcomes and policy tradeoffs.",
  },
];

export const cases: CaseItem[] = [
  {
    id: "case-hc-1",
    projectId: "proj-healthcare",
    title: "Hospital Triage Copilot",
    question: "Should a regional hospital network deploy an AI triage assistant in 2026?",
  },
  {
    id: "case-hc-2",
    projectId: "proj-healthcare",
    title: "Clinical Documentation",
    question: "What controls are needed before scaling clinical documentation automation?",
  },
  {
    id: "case-ed-1",
    projectId: "proj-education",
    title: "Outcome Forecast Pilot",
    question: "How should we evaluate policy interventions for student outcomes over 3 years?",
  },
];

export const runs: RunItem[] = [
  {
    id: "run-001",
    caseId: "case-hc-1",
    mode: "deep_research",
    createdAt: "2026-04-04T09:15:00Z",
    answer:
      "Recommendation: proceed with a staged pilot under strict oversight, explicit fallback protocols, and transparent clinician review checkpoints.",
    sources: [
      {
        id: "S1",
        title: "Clinical AI Safety Framework",
        url: "https://example.org/clinical-ai-safety",
        domain: "example.org",
        relevance: 0.91,
      },
      {
        id: "S2",
        title: "Hospital Workflow Risk Analysis",
        url: "https://example.com/workflow-risk",
        domain: "example.com",
        relevance: 0.84,
      },
    ],
    quality: {
      trustScore: 71,
      overallScore: 78,
      contradictionCount: 1,
      sourceCount: 2,
    },
    contradictions: [
      "Study A reports improved intake speed; Study B reports nurse workload increase in under-resourced settings.",
    ],
  },
  {
    id: "run-002",
    caseId: "case-hc-1",
    mode: "decision_brief",
    createdAt: "2026-04-04T10:10:00Z",
    answer:
      "Decision brief: deploy only in low-acuity scenarios first; define a stop condition tied to error rates and clinician override frequency.",
    sources: [
      {
        id: "S1",
        title: "Clinical AI Safety Framework",
        url: "https://example.org/clinical-ai-safety",
        domain: "example.org",
        relevance: 0.88,
      },
    ],
    quality: {
      trustScore: 66,
      overallScore: 74,
      contradictionCount: 0,
      sourceCount: 1,
    },
    contradictions: [],
  },
  {
    id: "run-003",
    caseId: "case-ed-1",
    mode: "scenario_test",
    createdAt: "2026-04-04T08:05:00Z",
    answer:
      "Scenario test indicates strongest expected gains where advising intensity is paired with baseline support and attendance interventions.",
    sources: [
      {
        id: "S1",
        title: "Student Retention Meta Analysis",
        url: "https://example.edu/retention-meta",
        domain: "example.edu",
        relevance: 0.9,
      },
      {
        id: "S2",
        title: "Policy Impact Review",
        url: "https://example.gov/policy-impact",
        domain: "example.gov",
        relevance: 0.82,
      },
    ],
    quality: {
      trustScore: 69,
      overallScore: 76,
      contradictionCount: 2,
      sourceCount: 2,
    },
    contradictions: [
      "Short-term attendance effects are positive while long-term graduation effects are mixed.",
      "High-touch advising helps first-year students more than final-year students.",
    ],
  },
];

export const modeLabels: Record<AriaMode, string> = {
  chat: "Chat",
  deep_research: "Deep Research",
  decision_brief: "Decision Brief",
  compare_models: "Compare Models",
  scenario_test: "Scenario Test",
};
