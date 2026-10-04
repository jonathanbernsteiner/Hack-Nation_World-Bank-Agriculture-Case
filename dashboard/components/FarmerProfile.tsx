"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FarmerDetail } from "@/lib/farmerDetail";
import { formatDate, formatIndex, formatMonth, formatNumber } from "@/lib/format";

const FarmerMap = dynamic(() => import("./FarmerMap"), { ssr: false });

const SECTION_HEADING = "text-base font-semibold text-gray-900 mb-4";
const CHART_HEIGHT = 220;
// Same chart look as the Prices page: blue for the farmer, slate for context, money in green.
const BLUE = "#3B82F6";
const SLATE = "#CBD5E1";
const MONEY = "#059669";
const AXIS_TICK = { fontSize: 12, fill: "#94A3B8" };
const AXIS = { axisLine: false, tickLine: false, tick: AXIS_TICK } as const;
const TOOLTIP_STYLE = { background: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, fontSize: 13 };
const LEGEND_STYLE = { fontSize: 12 };
const STATUS_BADGE: Record<string, string> = {
  processed: "bg-green-100 text-green-800",
  needs_review: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
};
const MONTHS_SHOWN = 24;
const COFFEE_YEAR_START_MONTH = 10; // the coffee year runs October to September, as in the hotline

export interface FarmerExtras {
  lat: number | null;
  lon: number | null;
  harvests: { date: string; kg: number }[];
  isUnavailable?: boolean;
  calls: FarmerCall[];
  hasMore: boolean;
}

export interface FarmerCall {
  id: number;
  receivedAt: string;
  status: string;
  durationSecs: number | null;
  lines: { role: "farmer" | "agent"; sw: string; en: string }[];
  fallback: { sw: string; en: string } | null; // transcript text without per-line structure
}

function coffeeYear(date: string): string {
  const [y, m] = date.split("-").map(Number);
  const start = m >= COFFEE_YEAR_START_MONTH ? y : y - 1;
  return `${start}/${String((start + 1) % 100).padStart(2, "0")}`;
}

function compact(value: number): string {
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${Math.round(value / 1e3)}k`;
  return formatNumber(value);
}

/** Harvest kg, sold kg and income per coffee year, oldest first. */
function yearly(detail: FarmerDetail, extras: FarmerExtras | null) {
  const years = new Map<string, { year: string; harvest: number; sold: number; income: number }>();
  const row = (year: string) => years.get(year) ?? years.set(year, { year, harvest: 0, sold: 0, income: 0 }).get(year)!;
  for (const s of detail.sales) {
    const r = row(coffeeYear(s.date));
    r.sold += s.kg;
    r.income += s.totalUgx;
  }
  for (const h of extras?.harvests ?? []) row(coffeeYear(h.date)).harvest += h.kg;
  return [...years.values()].sort((a, b) => a.year.localeCompare(b.year)).map((r) => ({
    ...r,
    harvest: Math.round(r.harvest),
    sold: Math.round(r.sold),
    income: Math.round(r.income),
  }));
}

/** Kg sold and income for each of the last 24 calendar months up to today. */
function monthly(detail: FarmerDetail, today: string) {
  const [y, m] = today.split("-").map(Number);
  const keys = Array.from({ length: MONTHS_SHOWN }, (_, i) => new Date(Date.UTC(y, m - MONTHS_SHOWN + i, 1)).toISOString().slice(0, 7));
  const byMonth = new Map(keys.map((k) => [k, { month: formatMonth(k), sold: 0, income: 0 }]));
  for (const s of detail.sales) {
    const r = byMonth.get(s.date.slice(0, 7));
    if (r) {
      r.sold += s.kg;
      r.income += s.totalUgx;
    }
  }
  return [...byMonth.values()].map((r) => ({ ...r, sold: Math.round(r.sold), income: Math.round(r.income) }));
}

function tooltipValue(value: unknown, name: unknown): string {
  return String(name).includes("UGX") ? `UGX ${formatNumber(Number(value))}` : `${formatNumber(Number(value))} kg`;
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className="text-lg font-semibold text-ink mt-0.5 whitespace-nowrap">{value}</div>
      <div className="text-xs text-faint">{sub}</div>
    </div>
  );
}

const UNAVAILABLE_EXTRAS: FarmerExtras = { lat: null, lon: null, harvests: [], calls: [], hasMore: false, isUnavailable: true };

export function useFarmerExtras(farmerId: number): FarmerExtras | null {
  const [extras, setExtras] = useState<{ id: number; data: FarmerExtras } | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/farmer/${farmerId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("farmer extras failed"))))
      .then((data) => !cancelled && setExtras({ id: farmerId, data }))
      .catch(() => !cancelled && setExtras({ id: farmerId, data: UNAVAILABLE_EXTRAS }));
    return () => {
      cancelled = true;
    };
  }, [farmerId]);
  return extras?.id === farmerId ? extras.data : null;
}

export function ProfileKpis({ detail, extras }: { detail: FarmerDetail; extras: FarmerExtras | null }) {
  const soldKg = detail.sales.reduce((sum, s) => sum + s.kg, 0);
  const income = detail.sales.reduce((sum, s) => sum + s.totalUgx, 0);
  const harvestYears = yearly(detail, extras).filter((y) => y.harvest > 0);
  const avgHarvest = harvestYears.length ? harvestYears.reduce((sum, y) => sum + y.harvest, 0) / harvestYears.length : null;
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-y-4 border-y border-line py-4">
      <Stat
        label="Average harvest"
        value={avgHarvest === null ? "—" : `${formatNumber(avgHarvest)} kg`}
        sub={harvestYears.length ? `${harvestYears.length} coffee year${harvestYears.length > 1 ? "s" : ""}` : "none reported"}
      />
      <Stat label="Coffee sold" value={`${formatNumber(soldKg)} kg`} sub={`${detail.sales.length} sales`} />
      <Stat label="Earned from coffee" value={`UGX ${compact(income)}`} sub={`UGX ${formatNumber(income)}`} />
      <Stat label="Price vs village" value={formatIndex(detail.medianVsVillage)} sub="median sale" />
    </div>
  );
}

export function LocationAndYield({ detail, extras }: { detail: FarmerDetail; extras: FarmerExtras | null }) {
  const years = useMemo(() => yearly(detail, extras), [detail, extras]);
  const p = detail.profile;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section>
        <h3 className={SECTION_HEADING}>Farm location</h3>
        <div style={{ height: CHART_HEIGHT }} className="rounded-xl border border-line bg-surface overflow-hidden">
          {extras?.lat != null && extras.lon != null ? (
            <FarmerMap lat={extras.lat} lon={extras.lon} label={`${p.firstName}, ${p.village}`} />
          ) : (
            <p className="h-full flex items-center justify-center text-sm text-faint">{extras ? "No location on file." : "Loading map…"}</p>
          )}
        </div>
      </section>
      <section>
        <h3 className={SECTION_HEADING}>Harvest, sales and earnings by coffee year</h3>
        {years.length === 0 ? (
          <p className="text-sm text-muted">No harvests or sales yet.</p>
        ) : (
          <div style={{ height: CHART_HEIGHT }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={years} margin={{ top: 15, right: 0, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="year" {...AXIS} />
                <YAxis yAxisId="kg" width={44} {...AXIS} tickFormatter={compact} />
                <YAxis yAxisId="ugx" orientation="right" width={44} {...AXIS} tickFormatter={compact} />
                <Tooltip formatter={tooltipValue} contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#F8FAFC" }} />
                <Legend iconType="circle" wrapperStyle={LEGEND_STYLE} />
                <Bar yAxisId="kg" dataKey="harvest" name="Harvest (kg)" fill={SLATE} radius={[4, 4, 0, 0]} maxBarSize={32} isAnimationActive={false} />
                <Bar yAxisId="kg" dataKey="sold" name="Sold (kg)" fill={BLUE} radius={[4, 4, 0, 0]} maxBarSize={32} isAnimationActive={false} />
                <Line yAxisId="ugx" type="monotone" dataKey="income" name="Earned (UGX)" stroke={MONEY} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  );
}

export function MonthlySales({ detail, today }: { detail: FarmerDetail; today: string }) {
  const months = useMemo(() => monthly(detail, today), [detail, today]);
  if (detail.sales.length === 0) return null;
  return (
    <section>
      <h3 className={SECTION_HEADING}>Sales by month</h3>
      <div style={{ height: CHART_HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={months} margin={{ top: 15, right: 0, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#F1F5F9" vertical={false} />
            <XAxis dataKey="month" {...AXIS} interval="preserveStartEnd" minTickGap={16} />
            <YAxis yAxisId="kg" width={44} {...AXIS} tickFormatter={compact} />
            <YAxis yAxisId="ugx" orientation="right" width={44} {...AXIS} tickFormatter={compact} />
            <Tooltip formatter={tooltipValue} contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#F8FAFC" }} />
            <Legend iconType="circle" wrapperStyle={LEGEND_STYLE} />
            <Bar yAxisId="kg" dataKey="sold" name="Sold (kg)" fill={BLUE} radius={[3, 3, 0, 0]} maxBarSize={16} isAnimationActive={false} />
            <Bar yAxisId="ugx" dataKey="income" name="Earned (UGX)" fill={SLATE} radius={[3, 3, 0, 0]} maxBarSize={16} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function Language({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-muted mb-1 md:hidden">{title}</div>
      {children}
    </div>
  );
}

function Transcript({ call }: { call: FarmerCall }) {
  if (call.lines.length === 0 && !call.fallback) return <p className="px-4 pb-3 text-sm text-muted">No transcript</p>;
  return (
    <div className="px-4 pb-3 text-sm">
      <div className="hidden md:grid grid-cols-[3.5rem_1fr_1fr] gap-4 py-1.5 border-t border-gray-100 text-xs font-medium text-muted">
        <span />
        <span>Kiswahili</span>
        <span>English</span>
      </div>
      {call.lines.map((line, i) => (
        <div key={i} className="grid md:grid-cols-[3.5rem_1fr_1fr] gap-x-4 gap-y-1 py-1.5 border-t border-gray-100">
          <div className="text-muted">{line.role === "farmer" ? "Farmer" : "Agent"}</div>
          <Language title="Kiswahili"><span className={line.role === "farmer" ? "text-ink" : "text-gray-600"}>{line.sw || "—"}</span></Language>
          <Language title="English"><span className={line.role === "farmer" ? "text-ink" : "text-gray-600"}>{line.en || "—"}</span></Language>
        </div>
      ))}
      {call.fallback && (
        <div className="grid md:grid-cols-[3.5rem_1fr_1fr] gap-x-4 gap-y-1 py-1.5 border-t border-gray-100">
          <span />
          <Language title="Kiswahili"><p className="whitespace-pre-wrap text-gray-600">{call.fallback.sw || "—"}</p></Language>
          <Language title="English"><p className="whitespace-pre-wrap text-gray-600">{call.fallback.en || "—"}</p></Language>
        </div>
      )}
    </div>
  );
}

/** Every call of the farmer, newest first, 10 at a time; each expands to its Kiswahili and English transcript. */
export function CallsSection({ farmerId, extras }: { farmerId: number; extras: FarmerExtras | null }) {
  const [more, setMore] = useState<{ id: number; calls: FarmerCall[]; hasMore: boolean; isFailed: boolean } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const extra = more?.id === farmerId ? more : null;
  const calls = [...(extras?.calls ?? []), ...(extra?.calls ?? [])];
  const hasMore = extra ? extra.hasMore : (extras?.hasMore ?? false);

  async function showMore() {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/farmer/${farmerId}?callsOffset=${calls.length}`);
      if (!res.ok) throw new Error("calls page failed");
      const page: { calls: FarmerCall[]; hasMore: boolean } = await res.json();
      setMore({ id: farmerId, calls: [...(extra?.calls ?? []), ...page.calls], hasMore: page.hasMore, isFailed: false });
    } catch {
      setMore({ id: farmerId, calls: extra?.calls ?? [], hasMore: true, isFailed: true });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section>
      <h3 className={SECTION_HEADING}>Calls</h3>
      {!extras ? (
        <p className="text-sm text-faint">Loading calls…</p>
      ) : calls.length === 0 ? (
        <p className="text-sm text-muted">{extras.isUnavailable ? "Call history unavailable." : "No calls yet."}</p>
      ) : (
        <div className="border border-line rounded-xl overflow-hidden divide-y divide-gray-100">
          {calls.map((call) => (
            <details key={call.id} className="group">
              <summary className="cursor-pointer list-none px-4 py-3 text-sm flex items-center gap-3 hover:bg-gray-50 transition-colors">
                <ChevronRight size={16} className="text-faint transition-transform group-open:rotate-90" />
                <span className="font-medium text-ink">{formatDate(call.receivedAt)}</span>
                {call.durationSecs != null && <span className="text-muted">{Math.max(1, Math.round(call.durationSecs / 60))} min</span>}
                <span className={`ml-auto text-xs font-medium rounded-full px-2 py-0.5 ${STATUS_BADGE[call.status] ?? "bg-gray-100 text-gray-800"}`}>
                  {call.status.replaceAll("_", " ")}
                </span>
              </summary>
              <Transcript call={call} />
            </details>
          ))}
        </div>
      )}
      {hasMore && (
        <div className="mt-3">
          <button
            type="button"
            disabled={isLoading}
            onClick={showMore}
            className="text-sm font-medium text-accent hover:underline disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
          >
            {isLoading ? "Loading…" : "Show more"}
          </button>
          {extra?.isFailed && <span className="ml-3 text-sm text-red-600">Could not load more calls.</span>}
        </div>
      )}
    </section>
  );
}
