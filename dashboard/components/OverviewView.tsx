"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useMemo } from "react";
import { computeWarnings, kpis as computeKpis } from "@/lib/aggregate";
import type { DashboardData } from "@/lib/types";
import DistrictTable from "./DistrictTable";
import KpiRow from "./KpiRow";
import WarningRow from "./WarningRow";

const MAX_WARNINGS = 5;

export default function OverviewView({ data }: { data: DashboardData }) {
  const warnings = useMemo(() => computeWarnings(data), [data]);
  const kpis = useMemo(() => computeKpis(data), [data]);
  const shown = warnings.slice(0, MAX_WARNINGS);

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
      <KpiRow kpis={kpis} />
      <section>
        <div className="flex items-center justify-between mb-4 gap-3">
          <h2 className="text-base font-semibold text-ink">Active warnings</h2>
          <Link href="/warnings" className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-accent hover:underline">
            View all <ArrowRight size={14} />
          </Link>
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
      <DistrictTable data={data} warnings={warnings} />
    </div>
  );
}
