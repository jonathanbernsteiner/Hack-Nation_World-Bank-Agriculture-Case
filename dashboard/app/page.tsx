import OverviewView from "@/components/OverviewView";
import { loadDashboardData } from "@/lib/queries";

export const revalidate = 120;

// Load errors are not caught here: they reach app/error.tsx, so a failed revalidation never replaces the
// last good cached page with an error page.
export default async function Page() {
  const data = await loadDashboardData();
  return <OverviewView data={data} />;
}
