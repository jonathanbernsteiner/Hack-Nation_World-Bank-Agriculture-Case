import { Suspense } from "react";
import FarmersRegistry from "@/components/FarmersRegistry";
import LoadError from "@/components/LoadError";
import { loadDashboardData } from "@/lib/queries";
import type { DashboardData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function FarmersPage() {
  let data: DashboardData | null = null;
  try {
    data = await loadDashboardData();
  } catch {
    data = null;
  }
  if (!data) return <LoadError />;
  return (
    <Suspense fallback={null}>
      <FarmersRegistry data={data} />
    </Suspense>
  );
}
