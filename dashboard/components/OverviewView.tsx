"use client";

import { ArrowRight } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { computeWarnings, kpis as computeKpis } from "@/lib/aggregate";
import type { DashboardData } from "@/lib/types";
import DistrictsToWatch from "./DistrictsToWatch";
import DistrictTable from "./DistrictTable";
import KpiRow from "./KpiRow";
import RegistrationsChart from "./RegistrationsChart";
import SidePanel from "./SidePanel";
import WarningRow from "./WarningRow";

const MAX_WARNINGS = 3;

export default function OverviewView({ data }: { data: DashboardData }) {
  const warnings = useMemo(() => computeWarnings(data), [data]);
  const kpis = useMemo(() => computeKpis(data, warnings), [data, warnings]);
  const [panel, setPanel] = useState<"warnings" | "districts" | null>(null);
  const closePanel = useCallback(() => setPanel(null), []);
  const shown = warnings.slice(0, MAX_WARNINGS);

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
      <KpiRow kpis={kpis} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <div className="flex items-center justify-between mb-4 gap-3">
            <h2 className="text-base font-semibold text-ink">Active warnings</h2>
            <button type="button" onClick={() => setPanel("warnings")} className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-accent hover:underline">
              View all <ArrowRight size={14} />
            </button>
          </div>
          <div className="bg-white border border-line rounded-xl overflow-hidden">
            {shown.length === 0 ? (
              <p className="p-6 text-sm text-faint text-center">No unusual patterns right now.</p>
            ) : (
              <ul>
                {shown.map((w) => (
                  <WarningRow key={w.id} warning={w} />
                ))}
              </ul>
            )}
          </div>
        </section>
        <DistrictsToWatch data={data} warnings={warnings} onViewAll={() => setPanel("districts")} />
      </div>
      <RegistrationsChart data={data} />
      <SidePanel title="Active warnings" open={panel === "warnings"} onClose={closePanel} link={{ href: "/warnings", label: "Open Warnings page" }}>
        <div className="bg-white border border-line rounded-xl overflow-hidden">
          {warnings.length === 0 ? (
            <p className="p-6 text-sm text-faint text-center">No unusual patterns right now.</p>
          ) : (
            <ul>
              {warnings.map((w) => (
                <WarningRow key={w.id} warning={w} showMapLink />
              ))}
            </ul>
          )}
        </div>
      </SidePanel>
      <SidePanel title="All districts" open={panel === "districts"} onClose={closePanel} link={{ href: "/prices", label: "Open Prices page" }}>
        <DistrictTable data={data} warnings={warnings} />
      </SidePanel>
    </div>
  );
}
