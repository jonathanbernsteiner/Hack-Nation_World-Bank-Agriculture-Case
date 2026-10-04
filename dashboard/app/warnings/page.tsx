import WarningsView from "@/components/WarningsView";
import { loadDashboardData } from "@/lib/queries";

export const revalidate = 120;

// Load errors reach app/error.tsx (see app/page.tsx).
export default async function WarningsPage() {
  const data = await loadDashboardData();
  return <WarningsView data={data} />;
}
