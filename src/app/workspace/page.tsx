import { redirect } from "next/navigation";
import { projects } from "@/lib/mock-data";

export default function WorkspaceIndexPage() {
  const firstProject = projects[0]?.id;
  if (!firstProject) {
    return <div className="p-6 text-white">No projects available.</div>;
  }
  redirect(`/workspace/${firstProject}`);
}
