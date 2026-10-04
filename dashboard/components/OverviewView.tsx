"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Info } from "lucide-react";
import { useMemo } from "react";
import { childrenOf, computeWarnings, kpis as computeKpis } from "@/lib/aggregate";
import { formatIndex, formatNumber } from "@/lib/format";
import type { DashboardData } from "@/lib/types";
import KpiRow from "./KpiRow";

const MAX_WARNINGS = 5;
const GREEN_MIN = 0.97;
const AMBER_MIN = 0.85;

function indexPill(index: number | null): string {
  if (index === null) return "bg-gray-100 text-gray-500 border-gray-200";
  if (index >= GREEN_MIN) return "bg-[#ECFDF5] text-[#10B981] border-[#A7F3D0]";
  if (index >= AMBER_MIN) return "bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]";
  return "bg-[#FEF2F2] text-[#EF4444] border-[#FECACA]";
}

function CardHeader({ title, href, linkLabel }: { title: string; href: string; linkLabel: string }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-line">
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

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <p className="text-sm text-gray-500">
        Every call to the Kiswahili hotline registers a farmer, logs sales and problems. This page shows where they are,
        what they are paid and what looks unusual.
      </p>
      <KpiRow kpis={kpis} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white border border-line rounded-xl overflow-hidden self-start w-full">
          <CardHeader title="Active warnings" href="/warnings" linkLabel="View all" />
          {shown.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No unusual patterns right now.</p>
          ) : (
            <ul className="divide-y divide-line">
              {shown.map((w) => (
                <li key={w.id} className="flex gap-3 px-4 py-3">
                  {w.severity === "high" ? (
                    <AlertTriangle size={18} color="#EF4444" className="shrink-0 mt-0.5" />
                  ) : (
                    <Info size={18} color="#F59E0B" className="shrink-0 mt-0.5" />
                  )}
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-ink">{w.title}</div>
                    <div className="text-xs text-faint mt-0.5">{w.detail}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="bg-white border border-line rounded-xl overflow-hidden self-start w-full">
          <CardHeader title="Where farmers are" href="/map" linkLabel="Open map" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-faint bg-surface">
                  <th className="px-4 py-2">District</th>
                  <th className="px-2 py-2">Region</th>
                  <th className="px-2 py-2 text-right">Farmers</th>
                  <th className="px-2 py-2 text-right">Villages</th>
                  <th className="px-4 py-2 text-right">Price vs national</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {districts.map((d) => (
                  <tr key={d.name}>
                    <td className="px-4 py-2 font-medium text-ink">{d.name}</td>
                    <td className="px-2 py-2 text-gray-500">{d.region ?? "—"}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(d.farmers)}</td>
                    <td className="px-2 py-2 text-right">{formatNumber(d.villages)}</td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold border ${indexPill(d.priceIndex)}`}
                      >
                        {formatIndex(d.priceIndex)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
