import CompareView from "@/components/compare/CompareView";

export default async function ComparePage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <CompareView projectId={projectId} />;
}
