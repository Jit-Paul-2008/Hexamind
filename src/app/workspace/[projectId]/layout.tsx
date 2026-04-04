import WorkspaceLayout from "@/components/workspace/WorkspaceLayout";

export default async function ProjectWorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <WorkspaceLayout projectId={projectId}>{children}</WorkspaceLayout>;
}
