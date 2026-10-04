"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, TrendingDown } from "lucide-react";
import { useMemo } from "react";
import { childrenOf, computeWarnings, kpis as computeKpis, median, referenceFor } from "@/lib/aggregate";
import { formatIndex, formatNumber } from "@/lib/format";
import type { BuyerType, DashboardData } from "@/lib/types";
import { indexPillClass } from "./FarmersTable";
import KpiRow from "./KpiRow";

const MAX_WARNINGS = 5;
const PILL_SHAPE = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";

const PRICE_MONTHS = 12;

function monthsAgoCutoff(today: string, months: number): string {
  const [y, m, d] = today.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 - months, d)).toISOString().slice(0, 10);
}

function buyerIndex(data: DashboardData, buyer: BuyerType): number | null {
  const cutoff = monthsAgoCutoff(data.today, PRICE_MONTHS);
  const ratios = data.sales
    .filter((s) => s.buyerType === buyer && s.date > cutoff)
    .flatMap((s) => {
      const ref = referenceFor(data.reference, s.form, s.date.slice(0, 7));
      return ref ? [s.ugxPerKg / ref] : [];
    });
  return median(ratios);
}

function middlemanClause(data: DashboardData): string | null {
  const middleman = buyerIndex(data, "middleman");
  const coop = buyerIndex(data, "cooperative");
  if (middleman === null || coop === null || coop === 0) return null;
  const pct = Math.round((1 - middleman / coop) * 100);
  if (pct === 0) return "middlemen paid the same as cooperatives";
  return pct > 0 ? `middlemen paid ${pct}% less than cooperatives` : `middlemen paid ${-pct}% more than cooperatives`;
}

function SectionHeading({ title, href, linkLabel }: { title: string; href: string; linkLabel: string }) {
  return (
    <div className="flex items-center justify-between mb-4 gap-3">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
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
  const farmerSplit = useMemo(() => {
    const synthetic = data.farmers.filter((f) => f.isSynthetic).length;
    return { live: data.farmers.length - synthetic, synthetic };
  }, [data.farmers]);
  const headline = useMemo(() => {
    const parts = [
      `${formatNumber(kpis.farmers)} farmers registered in ${kpis.districts} districts`,
      `${warnings.length} ${warnings.length === 1 ? "pattern needs" : "patterns need"} an officer's check`,
    ];
    const clause = middlemanClause(data);
    if (clause) parts.push(clause);
    return `${parts.join(" · ")}.`;
  }, [data, kpis, warnings]);

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
                <span
                  className={`${PILL_SHAPE} shrink-0 ${
                    w.severity === "high"
                      ? "bg-red-50 text-red-700 border-red-200"
                      : "bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]"
                  }`}
                >
                  {w.severity === "high" ? "High" : "Medium"}
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
        <p className="text-sm text-muted mt-1">{headline}</p>
      </div>
      <KpiRow kpis={kpis} farmerSplit={farmerSplit} />
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
