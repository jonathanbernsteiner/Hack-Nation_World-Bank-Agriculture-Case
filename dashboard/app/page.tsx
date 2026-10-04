import LoadError from "@/components/LoadError";
import OverviewView from "@/components/OverviewView";
import { loadDashboardData } from "@/lib/queries";
import type { DashboardData } from "@/lib/types";

export const revalidate = 120;

export default async function Page() {
  let data: DashboardData | null = null;
  try {
    data = await loadDashboardData();
  } catch {
    data = null;
  }
  if (!data) return <LoadError />;
  return <OverviewView data={data} />;
}
