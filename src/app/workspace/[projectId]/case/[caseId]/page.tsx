import CaseView from "@/components/case/CaseView";
import { cases } from "@/lib/mock-data";

export function generateStaticParams() {
  return cases.map((c) => ({ projectId: c.projectId, caseId: c.id }));
}

export default async function CasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <CaseView caseId={caseId} />;
}
