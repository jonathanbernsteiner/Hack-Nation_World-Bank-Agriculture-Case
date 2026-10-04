"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Scale, TrendingDown, MapPinned } from "lucide-react";
import type { ReactNode } from "react";
import type { CoffeeForm, DashboardData, Sale } from "@/lib/types";
import { MIN_FARMERS, MIN_SALES } from "@/lib/types";
import { formatIndex, formatMonth, formatNumber, formatUgx } from "@/lib/format";
import { buyerComparison, districtPrices, FORMS, monthlyByBuyer, spread } from "@/lib/prices";
import Link from "next/link";
import DistrictTable, { middlemanSharePct, priceIndexOfSales } from "./DistrictTable";
import { indexPillClass } from "./FarmersTable";

const CHART_HEIGHT = 280;
const TICK = { fontSize: 12, fill: "#94A3B8" };
const TAB_LABEL: Record<CoffeeForm, string> = { kiboko: "Kiboko", faq: "FAQ", parchment: "Parchment" };
const SERIES = [
  { key: "national", name: "National reference", color: "#94A3B8", dashed: true },
  { key: "middleman", name: "Middlemen", color: "#F59E0B", dashed: false },
  { key: "cooperative", name: "Cooperatives", color: "#10B981", dashed: false },
  { key: "all", name: "All buyers", color: "#3B82F6", dashed: false },
] as const;

function Tile({ icon, value, label, sub }: { icon: ReactNode; value: string; label: string; sub: string }) {
  return (
    <div className="bg-white border border-line rounded-xl p-6">
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center mb-4"
        style={{ background: "rgba(59,130,246,0.1)" }}
      >
        {icon}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "#0F172A" }}>{value}</div>
      <div style={{ fontSize: 14, fontWeight: 500, color: "#64748B", marginTop: 4 }}>{label}</div>
      <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 2 }}>{sub}</div>
    </div>
  );
}

const VILLAGE_DAYS = 90;
const VILLAGE_ROWS = 10;
const MS_PER_DAY = 86_400_000;

function VillagesLowest({ data }: { data: DashboardData }) {
  const rows = useMemo(() => {
    const from = new Date(Date.parse(`${data.today}T00:00:00Z`) - (VILLAGE_DAYS - 1) * MS_PER_DAY).toISOString().slice(0, 10);
    const byVillage = new Map<number, Sale[]>();
    for (const s of data.sales) {
      if (s.date < from || s.date > data.today) continue;
      byVillage.set(s.villageId, [...(byVillage.get(s.villageId) ?? []), s]);
    }
    return data.villages
      .map((v) => {
        const sales = byVillage.get(v.id) ?? [];
        return { village: v, sales: sales.length, index: priceIndexOfSales(sales, data), middleman: middlemanSharePct(sales) };
      })
      .filter((r): r is typeof r & { index: number } => r.index !== null)
      .sort((a, b) => a.index - b.index || b.sales - a.sales)
      .slice(0, VILLAGE_ROWS);
  }, [data]);

  return (
    <section>
      <h2
        className="text-base font-semibold text-ink mb-4"
        title={`Median needs ${MIN_SALES} sales from ${MIN_FARMERS} farmers.`}
      >
        Villages paid least ({VILLAGE_DAYS} days)
      </h2>
      <div className="bg-white border border-line rounded-[14px] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-gray-50">
                <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Village</th>
                <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">District</th>
                <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">vs national, 90 days</th>
                <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Middlemen, 90 days</th>
                <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Sales, 90 days</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-faint">Villages appear once enough sales are reported.</td>
                </tr>
              )}
              {rows.map(({ village: v, sales, index, middleman }) => {
                const href = `/map?path=${encodeURIComponent([v.district, v.subCounty, v.parish, v.village].join("|"))}`;
                return (
                  <tr key={v.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                      <Link href={href} className="hover:underline">{v.village}</Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{v.district}</td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <span className={indexPillClass(index)}>{formatIndex(index)}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{middleman === null ? "—" : `${middleman}%`}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{sales}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default function PricesView({ data }: { data: DashboardData }) {
  const [form, setForm] = useState<CoffeeForm>("faq");
  const buyers = useMemo(() => buyerComparison(data), [data]);
  const districts = useMemo(() => districtPrices(data), [data]);
  const monthly = useMemo(() => monthlyByBuyer(data, form), [data, form]);
  const range = useMemo(() => spread(data, form), [data, form]);
  const lowCount = districts.filter((d) => d.low).length;
  const hasChart = monthly.some((p) => p.middleman !== null || p.cooperative !== null || p.all !== null);
  const gapLabel = buyers.gapPct === null ? "—" : formatIndex(1 + buyers.gapPct / 100);

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">Prices</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Tile
          icon={<Scale size={20} color="#3B82F6" />}
          value={gapLabel}
          label="Middlemen vs cooperatives"
          sub="median, 12 months"
        />
        <Tile
          icon={<TrendingDown size={20} color="#3B82F6" />}
          value={range ? `${formatNumber(range.p10)}–${formatNumber(range.p90)}` : "—"}
          label={`Typical ${TAB_LABEL[form]} price`}
          sub="UGX/kg, p10–p90, 90 days"
        />
        <Tile
          icon={<MapPinned size={20} color="#3B82F6" />}
          value={String(lowCount)}
          label="Districts 15%+ below national"
          sub="90 days"
        />
      </div>

      <div className="bg-white border border-line rounded-xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <h2 className="text-base font-semibold text-ink">Price per kg by buyer</h2>
          <div className="flex gap-1 shrink-0">
            {FORMS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setForm(f)}
                className={`px-3 py-1.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  f === form ? "border-accent text-accent" : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {TAB_LABEL[f]}
              </button>
            ))}
          </div>
        </div>
        {!hasChart ? (
          <p className="text-sm text-faint text-center py-10">Price history appears once farmers report sales.</p>
        ) : (
          <div style={{ height: CHART_HEIGHT }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthly} margin={{ top: 15, right: 20, left: 20, bottom: 0 }}>
                <CartesianGrid stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="month" tickFormatter={formatMonth} axisLine={false} tickLine={false} tick={TICK} />
                <YAxis
                  width={45}
                  domain={["auto", "auto"]}
                  axisLine={false}
                  tickLine={false}
                  tick={TICK}
                  tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
                />
                <Tooltip
                  labelFormatter={(label) => formatMonth(String(label))}
                  formatter={(value, name) => [`${formatUgx(typeof value === "number" ? value : null)}/kg`, String(name)]}
                  contentStyle={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, fontSize: 13 }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12, whiteSpace: "nowrap" }} />
                {SERIES.map((s) => (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    name={s.name}
                    stroke={s.color}
                    strokeWidth={2}
                    strokeDasharray={s.dashed ? "5 4" : undefined}
                    dot={s.dashed ? false : { r: 3 }}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <DistrictTable data={data} />

      <VillagesLowest data={data} />
    </div>
  );
}
