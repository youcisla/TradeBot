import { redirect } from "next/navigation";

// Brain page is deprecated — agent theater is now at /dashboard/agents
export default function BrainRoutePage() {
  redirect("/dashboard/agents");
}
