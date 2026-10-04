"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMonth, formatNumber } from "@/lib/format";
import type { DashboardData } from "@/lib/types";

const MONTHS_SHOWN = 12;
const TICK = { fontSize: 12, fill: "#94A3B8" };

interface MonthBar {
  month: string; // YYYY-MM
  label: string;
  farmers: number;
}

const kampalaMonth = new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kampala", year: "numeric", month: "2-digit" });

function monthOf(iso: string): string | null {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const parts = kampalaMonth.formatToParts(new Date(t));
  const y = parts.find((p) => p.type === "year")?.value;
  const m = parts.find((p) => p.type === "month")?.value;
  return y && m ? `${y}-${m}` : null;
}

function lastMonths(today: string, count: number): string[] {
  const [y, m] = today.split("-").map(Number);
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(Date.UTC(y, m - 1 - (count - 1 - i), 1));
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
  });
}

export function registrationsByMonth(data: DashboardData): MonthBar[] {
  const counts = new Map<string, number>();
  for (const f of data.farmers) {
    const month = monthOf(f.registeredAt);
    if (month) counts.set(month, (counts.get(month) ?? 0) + 1);
  }
  return lastMonths(data.today, MONTHS_SHOWN).map((month) => ({
    month,
    label: formatMonth(month).split(" ")[0],
    farmers: counts.get(month) ?? 0,
  }));
}

interface TipProps {
  active?: boolean;
  payload?: { payload: MonthBar }[];
}

function Tip({ active, payload }: TipProps) {
  const bar = payload?.[0]?.payload;
  if (!active || !bar) return null;
  return (
    <div className="bg-white border border-line rounded-lg px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-ink">{formatMonth(bar.month)}</div>
      <div className="text-muted">{formatNumber(bar.farmers)} new farmers</div>
    </div>
  );
}

export default function RegistrationsChart({ data }: { data: DashboardData }) {
  const bars = useMemo(() => registrationsByMonth(data), [data]);
  const total = bars.reduce((sum, b) => sum + b.farmers, 0);

  return (
    <section>
      <div className="flex items-center justify-between mb-4 gap-3">
        <h2 className="text-base font-semibold text-ink">New farmers per month</h2>
        <span className="text-sm text-muted whitespace-nowrap">+{formatNumber(total)} in 12 months</span>
      </div>
      <div className="bg-white border border-line rounded-xl p-4" style={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} margin={{ top: 15, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#F1F5F9" vertical={false} />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={TICK} interval="preserveStartEnd" minTickGap={6} />
            <YAxis axisLine={false} tickLine={false} tick={TICK} width={45} allowDecimals={false} />
            <Tooltip content={<Tip />} cursor={{ fill: "#F8FAFC" }} />
            <Bar dataKey="farmers" fill="#3B82F6" radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
