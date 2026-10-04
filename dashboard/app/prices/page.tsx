import LoadError from "@/components/LoadError";
import PricesView from "@/components/PricesView";
import { loadDashboardData } from "@/lib/queries";
import type { DashboardData } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function PricesPage() {
  let data: DashboardData | null = null;
  try {
    data = await loadDashboardData();
  } catch {
    data = null;
  }
  if (!data) return <LoadError />;
  return <PricesView data={data} />;
}
