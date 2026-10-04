"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, TrendingDown } from "lucide-react";
import { useMemo } from "react";
import { childrenOf, computeWarnings, kpis as computeKpis } from "@/lib/aggregate";
import { formatIndex, formatNumber } from "@/lib/format";
import type { DashboardData } from "@/lib/types";
import { indexPillClass } from "./FarmersTable";
import KpiRow from "./KpiRow";

const MAX_WARNINGS = 5;
const PILL_SHAPE = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";

function SectionHeading({ title, href, linkLabel }: { title: string; href: string; linkLabel: string }) {
  return (
    <div className="flex items-center justify-between mb-4 gap-3">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <Link href={href} className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-accent hover:underline">
        {linkLabel} <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export default function OverviewView({ data }: { data: DashboardData }) {
  const warnings = useMemo(() => computeWarnings(data), [data]);
  const kpis = useMemo(() => computeKpis(data), [data]);
  const districts = useMemo(
    () => [...childrenOf(data, [], warnings)].sort((a, b) => b.farmers - a.farmers),
    [data, warnings],
  );
  const shown = warnings.slice(0, MAX_WARNINGS);
  const hasWarnings = shown.length > 0;

  const warningsBlock = (
    <section>
      <SectionHeading title="Active warnings" href="/warnings" linkLabel="View all" />
      <div className="bg-white border border-line rounded-xl overflow-hidden">
        {!hasWarnings ? (
          <p className="p-6 text-sm text-faint text-center">No unusual patterns right now.</p>
        ) : (
          <ul className="divide-y divide-line">
            {shown.map((w) => (
              <li key={w.id} className="flex gap-3 px-4 py-3 items-start">
                {w.kind === "problem" ? (
                  <AlertTriangle size={18} className="shrink-0 mt-0.5 text-red-600" />
                ) : (
                  <TrendingDown size={18} className="shrink-0 mt-0.5 text-amber-500" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-ink">{w.title}</div>
                  <div className="text-xs text-faint mt-0.5">{w.detail}</div>
                </div>
                <span className={`${PILL_SHAPE} shrink-0 whitespace-nowrap bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]`}>
                  Officer check
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
      <KpiRow kpis={kpis} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {warningsBlock}
        <section>
          <SectionHeading title="Where farmers are" href="/map" linkLabel="Open map" />
          <div className="bg-white border border-line rounded-[14px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line bg-gray-50">
                    <th className={`text-left ${TH}`}>District</th>
                    <th className={`text-left ${TH}`}>Region</th>
                    <th className={`text-right ${TH}`}>Farmers</th>
                    <th className={`text-right ${TH}`}>Villages</th>
                    <th className={`text-right ${TH}`}>Price vs national</th>
                  </tr>
                </thead>
                <tbody>
                  {districts.map((d) => (
                    <tr key={d.name} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{d.name}</td>
                      <td className="px-4 py-3 text-gray-600">{d.region ?? "—"}</td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">{formatNumber(d.farmers)}</td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">{formatNumber(d.villages)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={indexPillClass(d.priceIndex)}>{formatIndex(d.priceIndex)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
