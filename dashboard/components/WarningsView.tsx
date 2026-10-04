"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, TrendingDown } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { computeWarnings } from "@/lib/aggregate";
import { formatDate, labelProblem } from "@/lib/format";
import { OTHER_KEY, problemsByDistrict, weeklyCounts } from "@/lib/problems";
import {
  PRICE_LOW_INDEX,
  PRICE_WINDOW_DAYS,
  MIN_FARMERS,
  MIN_SALES,
  PROBLEM_BASELINE_WEEKS,
  PROBLEM_MIN_FARMERS,
  PROBLEM_WINDOW_DAYS,
  type DashboardData,
  type Warning,
} from "@/lib/types";

const PALETTE = ["#DC2626", "#F59E0B", "#3B82F6", "#8B5CF6"];
const OTHER_COLOR = "#94A3B8";
const WEEKS = 26;
const TABLE_DAYS = 90;
const TABLE_ROWS = 50;
const AXIS_TICK = { fontSize: 12, fill: "#94A3B8" };

const WARNING_PILL = "bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]";

function shortDate(iso: string): string {
  return formatDate(iso).slice(0, -5);
}

const YEAR_SUFFIX = /\s\d{4}$/;

function splitWarning(w: Warning): { title: string; meta: string } {
  const range = (w.detail.split(" · ")[0] ?? "").replace(/^Reported /, "").replace(YEAR_SUFFIX, "");
  if (w.kind !== "problem") return { title: w.title, meta: range ? `${w.areaName} district · ${range}` : w.areaName };
  const [head, tail = ""] = w.title.split(": ");
  const name = head.replace(/^Suspected /, "");
  const match = tail.match(/^(\d+ farms?) in (.+)$/);
  const meta = match ? [match[1], match[2], range] : [tail, range];
  return { title: name.charAt(0).toUpperCase() + name.slice(1), meta: meta.filter(Boolean).join(" · ") };
}

function WarningRow({ warning }: { warning: Warning }) {
  const isProblem = warning.kind === "problem";
  const Icon = isProblem ? AlertTriangle : TrendingDown;
  const { title, meta } = splitWarning(warning);
  return (
    <li className="flex items-center gap-4 px-4 sm:px-6 py-4 border-b border-gray-100 last:border-b-0 hover:bg-slate-50 transition-colors">
      <Icon size={20} className={`shrink-0 ${isProblem ? "text-red-600" : "text-amber-500"}`} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-gray-900">{title}</div>
        <div className="text-sm text-muted">{meta}</div>
      </div>
      <span className={`hidden sm:inline-flex shrink-0 items-center whitespace-nowrap px-2 py-0.5 rounded-full text-[11px] font-semibold border ${WARNING_PILL}`}>
        Officer check
      </span>
      <Link
        href={`/map?path=${encodeURIComponent(warning.path.join("|"))}`}
        className="shrink-0 text-xs font-medium text-accent hover:underline whitespace-nowrap"
      >
        View on map
      </Link>
    </li>
  );
}

export default function WarningsView({ data }: { data: DashboardData }) {
  const warnings = useMemo(() => computeWarnings(data), [data]);
  const weekly = useMemo(() => weeklyCounts(data, WEEKS), [data]);
  const rows = useMemo(() => problemsByDistrict(data, TABLE_DAYS), [data]);

  const chartData = weekly.weeks.map((w) => ({ week: shortDate(w.weekStart), weekStart: w.weekStart, ...w.counts }));
  const colorOf = (key: string, index: number) => (key === OTHER_KEY ? OTHER_COLOR : PALETTE[index % PALETTE.length]);
  const nameOf = (key: string) => (key === OTHER_KEY ? "Other" : labelProblem(key));

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <h1 className="text-2xl font-bold text-gray-900">Warnings</h1>

      <section>
        <h2 className="text-base font-semibold text-ink mb-4">Active warnings ({warnings.length})</h2>
        <div className="bg-white border border-line rounded-xl max-h-[480px] overflow-y-auto">
          {warnings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <CheckCircle2 size={48} className="mb-4" />
              <div className="text-lg font-medium text-gray-500">No unusual patterns right now.</div>
            </div>
          ) : (
            <ul>
              {warnings.map((w) => (
                <WarningRow key={w.id} warning={w} />
              ))}
            </ul>
          )}
        </div>
        <details className="mt-3 text-sm text-gray-600">
          <summary className="cursor-pointer text-xs font-medium text-muted hover:text-gray-700">How warnings work</summary>
          <ul className="list-disc pl-5 mt-2 space-y-1">
            <li>
              Problem: {PROBLEM_MIN_FARMERS}+ farms in one parish within {PROBLEM_WINDOW_DAYS} days, above the prior {PROBLEM_BASELINE_WEEKS} weeks.
            </li>
            <li>
              Price: district median {Math.round((1 - PRICE_LOW_INDEX) * 100)}%+ below national over {PRICE_WINDOW_DAYS} days ({MIN_SALES}+ sales, {MIN_FARMERS}+ farmers).
            </li>
          </ul>
        </details>
      </section>

      <div className="bg-white border border-line rounded-xl p-6">
        <h2 className="text-base font-semibold text-ink mb-4">Problem reports per week ({WEEKS} weeks)</h2>
        {weekly.keys.length === 0 ? (
          <div className="h-[280px] flex items-center justify-center text-sm text-gray-400">
            Problem reports will appear here once farmers report them.
          </div>
        ) : (
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 15, right: 20, left: 20, bottom: 0 }}>
                <CartesianGrid stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="week" axisLine={false} tickLine={false} tick={AXIS_TICK} interval={3} />
                <YAxis axisLine={false} tickLine={false} tick={AXIS_TICK} width={45} allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: "#F8FAFC" }}
                  labelFormatter={(_, payload) => `Week of ${formatDate(payload?.[0]?.payload?.weekStart ?? null)}`}
                  contentStyle={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 8, fontSize: 13 }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                {weekly.keys.map((key, i) => (
                  <Bar key={key} dataKey={key} name={nameOf(key)} stackId="problems" fill={colorOf(key, i)} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <section>
        <h2 className="text-base font-semibold text-ink mb-4">Problems by district, last {TABLE_DAYS} days</h2>
        <div className="bg-white border border-line rounded-[14px] overflow-hidden">
          {rows.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-400">No problems reported in the last {TABLE_DAYS} days.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line bg-gray-50">
                    <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">District</th>
                    <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap hidden sm:table-cell">Region</th>
                    <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Problem</th>
                    <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Farms</th>
                    <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap hidden sm:table-cell">Reports</th>
                    <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Last report</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, TABLE_ROWS).map((r) => (
                    <tr key={`${r.district}|${r.problem}`} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{r.district}</td>
                      <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">{r.region}</td>
                      <td className="px-4 py-3 text-gray-600">{labelProblem(r.problem)}</td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">{r.farmers}</td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700 hidden sm:table-cell">{r.reports}</td>
                      <td className="px-4 py-3 text-right text-gray-600 whitespace-nowrap">{formatDate(r.lastDate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
