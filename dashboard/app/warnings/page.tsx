import LoadError from "@/components/LoadError";
import WarningsView from "@/components/WarningsView";
import { loadDashboardData } from "@/lib/queries";
import type { DashboardData } from "@/lib/types";

export const revalidate = 120;

export default async function WarningsPage() {
  let data: DashboardData;
  try {
    data = await loadDashboardData();
  } catch {
    return <LoadError />;
  }
  return <WarningsView data={data} />;
}
