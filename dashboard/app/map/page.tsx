import { Suspense } from "react";
import LoadError from "@/components/LoadError";
import MapExplorer from "@/components/MapExplorer";
import { loadDashboardData } from "@/lib/queries";
import type { DashboardData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Page() {
  let data: DashboardData | null = null;
  try {
    data = await loadDashboardData();
  } catch {
    data = null;
  }
  if (!data) return <LoadError />;
  return (
    <Suspense fallback={null}>
      <MapExplorer data={data} />
    </Suspense>
  );
}
