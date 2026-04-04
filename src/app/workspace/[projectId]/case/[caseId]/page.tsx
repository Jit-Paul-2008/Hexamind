import CaseView from "@/components/case/CaseView";

export default async function CasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  return <CaseView caseId={caseId} />;
}
