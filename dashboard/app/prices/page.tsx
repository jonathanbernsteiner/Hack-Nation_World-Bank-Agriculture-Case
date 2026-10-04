import PricesView from "@/components/PricesView";
import { loadDashboardData } from "@/lib/queries";

export const revalidate = 120;

// Load errors reach app/error.tsx (see app/page.tsx).
export default async function PricesPage() {
  const data = await loadDashboardData();
  return <PricesView data={data} />;
}
