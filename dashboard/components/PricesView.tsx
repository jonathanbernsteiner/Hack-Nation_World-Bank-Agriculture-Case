"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Scale, TrendingDown, MapPinned } from "lucide-react";
import type { ReactNode } from "react";
import type { CoffeeForm, DashboardData } from "@/lib/types";
import { MIN_FARMERS, MIN_SALES } from "@/lib/types";
import { formatIndex, formatMonth, formatNumber, formatUgx } from "@/lib/format";
import { buyerComparison, districtPrices, FORMS, monthlyByBuyer, spread } from "@/lib/prices";
import type { PriceByForm } from "@/lib/prices";
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

function buildHeadline(gapPct: number | null, lowCount: number): string {
  const districtPart =
    lowCount === 0
      ? "no district is 15% or more below the national price."
      : `${lowCount} ${lowCount === 1 ? "district is" : "districts are"} 15% or more below the national price.`;
  if (gapPct === null) return `Not enough sales yet to compare buyers; ${districtPart}`;
  const gapPart =
    gapPct === 0
      ? "Middlemen paid the same as cooperatives"
      : `Middlemen paid ${Math.abs(gapPct)}% ${gapPct < 0 ? "less" : "more"} than cooperatives`;
  return `${gapPart} over the last 12 months; ${districtPart}`;
}

function Dash() {
  return <span className="text-gray-300">—</span>;
}

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

function FormCell({ values, form, className = "" }: { values: PriceByForm; form: CoffeeForm; className?: string }) {
  const v = values[form];
  return (
    <td className={`px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap ${className}`}>
      {v === null ? <Dash /> : formatNumber(v)}
    </td>
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
  const headline = buildHeadline(buyers.gapPct, lowCount);

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Prices</h1>
        <p className="text-sm text-gray-500 mt-1">
          {headline}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Tile
          icon={<Scale size={20} color="#3B82F6" />}
          value={gapLabel}
          label="Middlemen vs cooperatives"
          sub={`median of ${formatNumber(buyers.sales)} sales, last 12 months`}
        />
        <Tile
          icon={<TrendingDown size={20} color="#3B82F6" />}
          value={range ? `${formatNumber(range.p10)}–${formatNumber(range.p90)}` : "—"}
          label={`Price range (90 days) · ${TAB_LABEL[form]}`}
          sub={range ? `UGX/kg, ${TAB_LABEL[form]}, middle ${formatNumber(range.median)}` : `UGX/kg, ${TAB_LABEL[form]}`}
        />
        <Tile
          icon={<MapPinned size={20} color="#3B82F6" />}
          value={String(lowCount)}
          label="Districts below national"
          sub="15% or more under, last 90 days"
        />
      </div>

      <div className="bg-white border border-line rounded-xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <h2 className="text-base font-semibold text-ink">Price per kg by buyer: {TAB_LABEL[form]}</h2>
          <div className="flex gap-1">
            {FORMS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setForm(f)}
                className={`px-3 py-1.5 text-sm font-medium border-b-2 transition-colors ${
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
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
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
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div>
        <h2 className="text-base font-semibold text-ink mb-4">By district</h2>
        <div className="bg-white border border-line rounded-[14px] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-gray-50">
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">District</th>
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap hidden sm:table-cell">Region</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Sales</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">vs national (90 days)</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Kiboko (UGX/kg)</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap hidden md:table-cell">FAQ (UGX/kg)</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap hidden md:table-cell">Parchment (UGX/kg)</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Sold to middlemen</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {districts.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-10 text-center text-faint">
                      Districts appear once farmers report sales.
                    </td>
                  </tr>
                )}
                {districts.map((d) => (
                  <tr key={d.district} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-gray-900">{d.district}</td>
                    <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">{d.region}</td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">{d.sales}</td>
                    <td className="px-4 py-3 text-right">
                      {d.index90d === null ? <Dash /> : <span className={indexPillClass(d.index90d)}>{formatIndex(d.index90d)}</span>}
                    </td>
                    <FormCell values={d.byForm} form="kiboko" />
                    <FormCell values={d.byForm} form="faq" className="hidden md:table-cell" />
                    <FormCell values={d.byForm} form="parchment" className="hidden md:table-cell" />
                    <td className="px-4 py-3 text-right font-mono text-gray-700">
                      {d.middlemanShare === null ? <Dash /> : `${d.middlemanShare}%`}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {d.low && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-red-50 text-red-700 border-red-200">
                          Low
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="text-xs text-faint mt-3">
          Median needs {MIN_SALES} sales from {MIN_FARMERS} farmers. National reference: UCDA / MAAIF Coffee Department
          monthly farm-gate averages. Synthetic records are labelled.
        </p>
      </div>
    </div>
  );
}
