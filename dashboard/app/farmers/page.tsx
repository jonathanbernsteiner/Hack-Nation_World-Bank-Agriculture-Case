import { Suspense } from "react";
import FarmersRegistry from "@/components/FarmersRegistry";
import { loadDashboardData } from "@/lib/queries";

export const revalidate = 120;

// Load errors reach app/error.tsx (see app/page.tsx).
export default async function FarmersPage() {
  const data = await loadDashboardData();
  return (
    <Suspense fallback={null}>
      <FarmersRegistry data={data} />
    </Suspense>
  );
}
