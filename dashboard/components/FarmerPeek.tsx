"use client";

import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Maximize2, Minimize2, X } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { farmerDetail } from "@/lib/farmerDetail";
import type { FarmerDetail } from "@/lib/farmerDetail";
import { formatDate, formatIndex, formatMonth, formatNumber, labelBuyer, labelProblem } from "@/lib/format";
import { indexPillClass, shortForm } from "@/components/FarmersTable";
import type { CoffeeForm, DashboardData } from "@/lib/types";
import { LocationAndYield, MonthlySales, ProfileKpis, RecentCalls, useFarmerExtras } from "@/components/FarmerProfile";

const SECTION_HEADING = "text-base font-semibold text-gray-900 mb-4";
const TH = "font-medium text-muted px-3 py-2 whitespace-nowrap";
const ICON_BTN = "p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
const CHART_HEIGHT = 220; // matches Sales by month, which sits beside it
const BLUE = "#3B82F6";
const GRAY = "#94A3B8";
const MS_PER_DAY = 86_400_000;

function mainForm(detail: FarmerDetail): CoffeeForm | null {
  const counts = new Map<CoffeeForm, number>();
  for (const s of detail.sales) counts.set(s.form, (counts.get(s.form) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

function toTime(date: string): number {
  return Date.parse(`${date.slice(0, 10)}T00:00:00Z`);
}

function tickLabel(ms: number): string {
  return formatMonth(new Date(ms).toISOString().slice(0, 7));
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted whitespace-nowrap">{label}</div>
      <div className="text-sm font-medium text-gray-900 whitespace-nowrap">{value}</div>
    </div>
  );
}

function SalesChart({ detail }: { detail: FarmerDetail }) {
  const form = mainForm(detail);
  const points = [...detail.sales]
    .filter((s) => s.form === form)
    .reverse()
    .map((s) => ({ t: toTime(s.date), price: s.ugxPerKg, national: s.national }));
  if (points.length < 2) return <p className="text-sm text-muted">Chart needs 2+ sales of one form.</p>;
  return (
    <div>
      <div className="flex gap-4 text-xs text-muted mb-2">
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-4 border-t-2" style={{ borderColor: BLUE }} />Sale price</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-4 border-t-2 border-dashed" style={{ borderColor: GRAY }} />National</span>
      </div>
      <div style={{ height: CHART_HEIGHT }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 5, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#F1F5F9" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(t: number) => tickLabel(t)}
            tick={{ fontSize: 12, fill: GRAY }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis width={44} axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: GRAY }} tickFormatter={(v: number) => formatNumber(v)} domain={["auto", "auto"]} />
          <Tooltip formatter={(v) => `UGX ${formatNumber(Number(v))}/kg`} labelFormatter={(t) => formatDate(new Date(Number(t) + MS_PER_DAY / 2).toISOString())} />
          <Line type="monotone" dataKey="national" name="National" stroke={GRAY} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="price" name="Sale price" stroke={BLUE} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}

// `side` (Sales by month) sits next to the price chart; the sales table runs full width below.
function SalesCard({ detail, side }: { detail: FarmerDetail; side?: ReactNode }) {
  return (
    <section>
      <div className="grid gap-6 lg:grid-cols-2 mb-4">
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-4">
            <h3 className="text-base font-semibold text-gray-900">Sales</h3>
            {detail.sales.length > 0 && (
              <div className="flex gap-4 text-xs text-muted whitespace-nowrap">
                <span>Last sale vs village <span className="font-medium text-gray-900">{formatIndex(detail.lastSaleVsVillage ?? null)}</span></span>
                {detail.mainBuyer && <span>Main buyer <span className="font-medium text-gray-900">{labelBuyer(detail.mainBuyer)}</span></span>}
              </div>
            )}
          </div>
          {detail.sales.length === 0 ? <p className="text-sm text-muted">No sales reported yet.</p> : <SalesChart detail={detail} />}
        </div>
        {side}
      </div>
      {detail.sales.length > 0 && (
        <div className="border border-line rounded-[14px] overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-gray-50">
                <th className={`${TH} text-left`}>Date</th>
                <th className={`${TH} text-left`}>Form</th>
                <th className={`${TH} text-right`}>Kg</th>
                <th className={`${TH} text-right`}>UGX/kg</th>
                <th className={`${TH} text-left`}>Buyer</th>
                <th className={`${TH} text-right`}>vs national</th>
                <th className={`${TH} text-right`}>Total UGX</th>
              </tr>
            </thead>
            <tbody>
              {detail.sales.map((s, i) => (
                <tr key={`${s.date}-${i}`} className="border-b border-gray-100">
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{formatDate(s.date)}</td>
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{shortForm(s.form)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.kg)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.ugxPerKg)}</td>
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{s.buyerType ? labelBuyer(s.buyerType) : "—"}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap"><span className={indexPillClass(s.indexVsNational)}>{formatIndex(s.indexVsNational)}</span></td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.totalUgx)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ProblemsCard({ detail }: { detail: FarmerDetail }) {
  return (
    <section>
      <h3 className={SECTION_HEADING}>Problems reported</h3>
      {detail.problems.length === 0 ? (
        <p className="text-sm text-muted">No problems reported</p>
      ) : (
        <ul className="space-y-1.5">
          {detail.problems.map((p, i) => (
            <li key={`${p.date}-${i}`} className="flex gap-3 text-sm">
              <span className="text-muted w-28 shrink-0">{formatDate(p.date)}</span>
              <span className="text-red-600 font-medium">{labelProblem(p.problem)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function FarmerPeek({ data, farmerId, onClose }: { data: DashboardData; farmerId: number; onClose: () => void }) {
  const [isFull, setIsFull] = useState(false);
  const detail = useMemo(() => farmerDetail(data, farmerId), [data, farmerId]);
  const extras = useFarmerExtras(farmerId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      const el = document.activeElement;
      if (el instanceof HTMLElement && (el.matches("input, textarea, select, [contenteditable]") || el.closest("[role=dialog], [role=listbox]"))) return;
      onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const position = isFull ? "left-0 md:left-14 right-0" : "left-0 right-0 md:left-auto md:w-[min(max(880px,62vw),calc(100vw-56px))]";
  const p = detail?.profile;
  const path = p ? [p.village, p.parish, p.subCounty, p.district, p.region].join(" · ") : "";
  return (
    <aside
      aria-label="Farmer details"
      className={`fixed top-14 bottom-14 md:bottom-0 ${position} bg-white border-l border-line shadow-xl z-40 flex flex-col transition-[width,left] duration-150`}
    >
      <div className="flex items-start justify-between gap-3 px-6 py-5 border-b border-line">
        {p ? (
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-gray-900 truncate">{p.firstName}</h2>
            <p className="text-sm text-muted mt-0.5 truncate" title={path}>{path}</p>
            <div className="flex gap-x-6 mt-3">
              <Stat label="Registered" value={formatDate(p.registeredAt)} />
              <Stat label="Calls" value={String(p.callCount)} />
              <Stat label="Last call" value={formatDate(p.lastCallAt)} />
            </div>
          </div>
        ) : (
          <h2 className="text-lg font-semibold text-gray-900">Farmer not found</h2>
        )}
        <div className="flex gap-1 shrink-0">
          <button type="button" className={ICON_BTN} aria-label={isFull ? "Shrink panel" : "Expand panel"} onClick={() => setIsFull(!isFull)}>
            {isFull ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button type="button" className={ICON_BTN} aria-label="Close" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
      </div>
      {detail && (
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-white">
          <ProfileKpis detail={detail} extras={extras} />
          <LocationAndYield detail={detail} extras={extras} />
          <SalesCard detail={detail} side={<MonthlySales detail={detail} today={data.today} />} />
          <ProblemsCard detail={detail} />
          <RecentCalls extras={extras} />
        </div>
      )}
    </aside>
  );
}
