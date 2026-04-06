import Link from "next/link";
import { cases, projects } from "@/lib/mock-data";

export function generateStaticParams() {
  return projects.map((p) => ({ projectId: p.id }));
}

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const projectCases = cases.filter((item) => item.projectId === projectId);

  return (
    <div className="flex h-full flex-col gap-4">
      <header>
        <p className="text-xs uppercase tracking-[0.14em] text-white/45">Workspace</p>
        <h1 className="text-2xl font-semibold text-white">Project Overview</h1>
      </header>
      <div className="grid gap-3 md:grid-cols-2">
        {projectCases.map((caseItem) => (
          <Link
            key={caseItem.id}
            href={`/workspace/${projectId}/case/${caseItem.id}`}
            className="rounded-md border border-white/10 bg-white/5 p-3 transition hover:bg-white/10"
          >
            <p className="text-sm font-medium text-white">{caseItem.title}</p>
            <p className="mt-1 text-xs text-white/70">{caseItem.question}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
