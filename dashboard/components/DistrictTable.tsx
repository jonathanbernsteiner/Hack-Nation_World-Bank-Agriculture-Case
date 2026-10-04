"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronUp } from "lucide-react";
import { childrenOf, computeWarnings, median, referenceFor } from "@/lib/aggregate";
import { formatIndex, formatNumber } from "@/lib/format";
import { MIN_FARMERS, MIN_SALES } from "@/lib/types";
import type { DashboardData, Sale, Warning } from "@/lib/types";
import { indexPillClass } from "./FarmersTable";

const WINDOW_DAYS = 90;
const NEW_DAYS = 30;
const MS_PER_DAY = 86_400_000;

type SortKey = "name" | "region" | "farmers" | "new30d" | "index" | "middleman" | "warnings";
type SortDir = "asc" | "desc";

interface Row {
  name: string;
  region: string;
  farmers: number;
  new30d: number;
  index: number | null;
  middleman: number | null;
  warnings: number;
}

function isoDaysBefore(today: string, days: number): string {
  return new Date(Date.parse(`${today}T00:00:00Z`) - days * MS_PER_DAY).toISOString().slice(0, 10);
}

/** Median price index vs the month-matched national reference; null below the minimums. */
export function priceIndexOfSales(sales: Sale[], data: DashboardData): number | null {
  if (sales.length < MIN_SALES || new Set(sales.map((s) => s.farmerId)).size < MIN_FARMERS) return null;
  const ratios: number[] = [];
  for (const s of sales) {
    const ref = referenceFor(data.reference, s.form, s.date.slice(0, 7));
    if (ref !== null && ref > 0) ratios.push(s.ugxPerKg / ref);
  }
  return median(ratios);
}

export function middlemanSharePct(sales: Sale[]): number | null {
  if (sales.length === 0) return null;
  return Math.round((sales.filter((s) => s.buyerType === "middleman").length / sales.length) * 100);
}

function buildRows(data: DashboardData, warnings: Warning[]): Row[] {
  const districtOf = new Map(data.villages.map((v) => [v.id, v.district]));
  const salesFrom = isoDaysBefore(data.today, WINDOW_DAYS - 1);
  const newFrom = isoDaysBefore(data.today, NEW_DAYS);
  const salesBy = new Map<string, Sale[]>();
  for (const s of data.sales) {
    const d = districtOf.get(s.villageId);
    if (!d || s.date < salesFrom || s.date > data.today) continue;
    salesBy.set(d, [...(salesBy.get(d) ?? []), s]);
  }
  const newBy = new Map<string, number>();
  for (const f of data.farmers) {
    const d = districtOf.get(f.villageId);
    if (d && f.registeredAt.slice(0, 10) > newFrom) newBy.set(d, (newBy.get(d) ?? 0) + 1);
  }
  const warningsBy = new Map<string, number>();
  for (const w of warnings) warningsBy.set(w.path[0], (warningsBy.get(w.path[0]) ?? 0) + 1);

  return childrenOf(data, [], warnings).map((d) => {
    const sales = salesBy.get(d.name) ?? [];
    return {
      name: d.name,
      region: d.region ?? "—",
      farmers: d.farmers,
      new30d: newBy.get(d.name) ?? 0,
      index: priceIndexOfSales(sales, data),
      middleman: middlemanSharePct(sales),
      warnings: warningsBy.get(d.name) ?? 0,
    };
  });
}

function compareBy(key: SortKey, dir: SortDir) {
  const sign = dir === "asc" ? 1 : -1;
  return (a: Row, b: Row): number => {
    const av = a[key];
    const bv = b[key];
    if (av === null && bv !== null) return 1;
    if (bv === null && av !== null) return -1;
    if (av !== null && bv !== null && av !== bv) {
      const c = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number);
      return c * sign;
    }
    return b.farmers - a.farmers || a.name.localeCompare(b.name);
  };
}

const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";

const COLUMNS: { key: SortKey; label: string; align: "left" | "right"; className?: string }[] = [
  { key: "name", label: "District", align: "left" },
  { key: "region", label: "Region", align: "left", className: "hidden lg:table-cell" },
  { key: "farmers", label: "Farmers", align: "right" },
  { key: "new30d", label: "New, 30 days", align: "right" },
  { key: "index", label: "vs national, 90 days", align: "right" },
  { key: "middleman", label: "Middlemen, 90 days", align: "right" },
  { key: "warnings", label: "Warnings", align: "right" },
];

export default function DistrictTable({ data, warnings }: { data: DashboardData; warnings?: Warning[] }) {
  const router = useRouter();
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "warnings", dir: "desc" });
  const all = useMemo(() => warnings ?? computeWarnings(data), [warnings, data]);
  const rows = useMemo(() => buildRows(data, all), [data, all]);
  const sorted = useMemo(() => [...rows].sort(compareBy(sort.key, sort.dir)), [rows, sort]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" || key === "region" ? "asc" : "desc" }));
  const open = (name: string) => router.push(`/map?path=${encodeURIComponent(name)}`);

  return (
    <section>
      <h2 className="text-base font-semibold text-ink mb-4">Districts</h2>
      <div className="bg-white border border-line rounded-[14px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-gray-50">
                {COLUMNS.map((c) => {
                  const active = sort.key === c.key;
                  const Chevron = sort.dir === "asc" ? ChevronUp : ChevronDown;
                  return (
                    <th
                      key={c.key}
                      className={`${TH} ${c.align === "left" ? "text-left" : "text-right"} ${c.className ?? ""}`}
                      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
                    >
                      <button type="button" onClick={() => toggle(c.key)} className="inline-flex items-center gap-1 font-medium hover:text-gray-700">
                        {c.label}
                        {active && <Chevron size={12} />}
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 && (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-faint">No districts yet.</td>
                </tr>
              )}
              {sorted.map((r) => (
                <tr
                  key={r.name}
                  onClick={() => open(r.name)}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">{r.name}</td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap hidden lg:table-cell">{r.region}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{formatNumber(r.farmers)}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{formatNumber(r.new30d)}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    {r.index === null ? <span className="text-gray-300">—</span> : <span className={indexPillClass(r.index)}>{formatIndex(r.index)}</span>}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">
                    {r.middleman === null ? <span className="text-gray-300">—</span> : `${r.middleman}%`}
                  </td>
                  <td className={`px-4 py-3 text-right font-mono ${r.warnings > 0 ? "text-red-600 font-medium" : "text-gray-700"}`}>
                    {r.warnings}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
