"use client";

import { ArrowRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";
import { formatIndex } from "@/lib/format";
import type { DashboardData, Sale, Warning } from "@/lib/types";
import { middlemanSharePct, priceIndexOfSales } from "./DistrictTable";
import { indexPillClass } from "./FarmersTable";

const WINDOW_DAYS = 90;
const MAX_ROWS = 5;
const MS_PER_DAY = 86_400_000;
const TH = "font-medium text-muted px-4 py-2.5 whitespace-nowrap";

interface Row {
  name: string;
  index: number | null;
  middleman: number | null;
  warnings: number;
}

function isoDaysBefore(today: string, days: number): string {
  return new Date(Date.parse(`${today}T00:00:00Z`) - days * MS_PER_DAY).toISOString().slice(0, 10);
}

/** Warnings desc, then price index asc (no index last), then name. */
function compareRows(a: Row, b: Row): number {
  if (a.warnings !== b.warnings) return b.warnings - a.warnings;
  if (a.index !== b.index) {
    if (a.index === null) return 1;
    if (b.index === null) return -1;
    return a.index - b.index;
  }
  return a.name.localeCompare(b.name);
}

export function topDistricts(data: DashboardData, warnings: Warning[]): Row[] {
  const districtOf = new Map(data.villages.map((v) => [v.id, v.district]));
  const from = isoDaysBefore(data.today, WINDOW_DAYS - 1);
  const salesBy = new Map<string, Sale[]>();
  for (const s of data.sales) {
    const d = districtOf.get(s.villageId);
    if (!d || s.date < from || s.date > data.today) continue;
    salesBy.set(d, [...(salesBy.get(d) ?? []), s]);
  }
  const warningsBy = new Map<string, number>();
  for (const w of warnings) {
    if (w.path.length > 0) warningsBy.set(w.path[0], (warningsBy.get(w.path[0]) ?? 0) + 1);
  }
  return [...new Set(districtOf.values())]
    .map((name) => {
      const sales = salesBy.get(name) ?? [];
      return {
        name,
        index: priceIndexOfSales(sales, data),
        middleman: middlemanSharePct(sales),
        warnings: warningsBy.get(name) ?? 0,
      };
    })
    .sort(compareRows)
    .slice(0, MAX_ROWS);
}

export default function DistrictsToWatch({ data, warnings, onViewAll }: { data: DashboardData; warnings: Warning[]; onViewAll: () => void }) {
  const router = useRouter();
  const rows = useMemo(() => topDistricts(data, warnings), [data, warnings]);

  return (
    <section>
      <div className="flex items-center justify-between mb-4 gap-3">
        <h2 className="text-base font-semibold text-ink">Districts to watch</h2>
        <button type="button" onClick={onViewAll} className="inline-flex items-center gap-1 whitespace-nowrap text-sm font-medium text-accent hover:underline">
          All districts <ArrowRight size={14} />
        </button>
      </div>
      <div className="bg-white border border-line rounded-[14px] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line bg-gray-50">
              <th className={`${TH} text-left`}>District</th>
              <th className={`${TH} text-right`}>vs national (90d)</th>
              <th className={`${TH} text-right`}>Middlemen (90d)</th>
              <th className={`${TH} text-right`}>Warnings</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-faint">No districts yet.</td>
              </tr>
            )}
            {rows.map((r) => (
              <tr
                key={r.name}
                onClick={() => router.push(`/map?path=${encodeURIComponent(r.name)}`)}
                className="border-b border-gray-100 last:border-b-0 hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <td className="px-4 py-2.5 font-medium text-gray-900 whitespace-nowrap">{r.name}</td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  {r.index === null ? <span className="text-gray-300">—</span> : <span className={indexPillClass(r.index)}>{formatIndex(r.index)}</span>}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                  {r.middleman === null ? <span className="text-gray-300">—</span> : `${r.middleman}%`}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono ${r.warnings > 0 ? "text-red-600 font-medium" : "text-gray-700"}`}>
                  {r.warnings}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
