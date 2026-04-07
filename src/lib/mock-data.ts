export interface Project {
  id: string;
  name: string;
  description: string;
}

export interface Case {
  id: string;
  projectId: string;
  title: string;
  question: string;
}

export const projects: Project[] = [
  {
    id: "proj-1",
    name: "Research Project Alpha",
    description: "Aurora multi-agent research runs",
  },
];

export const cases: Case[] = [
  {
    id: "case-1",
    projectId: "proj-1",
    title: "Sample Research Case",
    question: "What are the latest findings on this topic?",
  },
];
