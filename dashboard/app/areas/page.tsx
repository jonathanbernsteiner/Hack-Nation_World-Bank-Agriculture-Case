import { Suspense } from "react";
import AreasView from "@/components/AreasView";
import { loadDashboardData } from "@/lib/queries";

export const revalidate = 120;

export default async function AreasPage() {
  const data = await loadDashboardData();
  return (
    <Suspense fallback={null}>
      <AreasView data={data} />
    </Suspense>
  );
}
