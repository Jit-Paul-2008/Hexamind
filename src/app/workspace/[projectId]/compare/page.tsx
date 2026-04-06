import CompareView from "@/components/compare/CompareView";
import { projects } from "@/lib/mock-data";

export function generateStaticParams() {
  return projects.map((p) => ({ projectId: p.id }));
}

export default async function ComparePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <CompareView projectId={projectId} />;
}
