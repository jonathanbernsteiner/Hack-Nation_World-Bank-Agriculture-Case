"use client";

import { useEffect, useMemo, useState } from "react";
import { Maximize2, Minimize2, X } from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { farmerDetail } from "@/lib/farmerDetail";
import type { FarmerDetail } from "@/lib/farmerDetail";
import { formatDate, formatIndex, formatNumber, labelBuyer, labelProblem } from "@/lib/format";
import { indexPillClass } from "@/components/FarmersTable";
import type { DashboardData } from "@/lib/types";

const CARD = "bg-white border border-line rounded-[14px] p-5";
const TH = "font-medium text-muted px-3 py-2 whitespace-nowrap";
const ICON_BTN = "p-2 rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
const CHART_HEIGHT = 160;
const BLUE = "#3B82F6";
const GRAY = "#94A3B8";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-muted whitespace-nowrap">{label}</div>
      <div className="text-sm font-medium text-gray-900 whitespace-nowrap">{value}</div>
    </div>
  );
}

function SalesChart({ detail }: { detail: FarmerDetail }) {
  const points = [...detail.sales].reverse().map((s) => ({ date: s.date, price: s.ugxPerKg, national: s.national }));
  if (points.length < 2) return null;
  return (
    <div style={{ height: CHART_HEIGHT }} className="mb-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 5, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#F1F5F9" vertical={false} />
          <XAxis dataKey="date" tickFormatter={(d: string) => formatDate(d).slice(0, 6)} tick={{ fontSize: 11, fill: GRAY }} />
          <YAxis width={44} tick={{ fontSize: 11, fill: GRAY }} tickFormatter={(v: number) => formatNumber(v)} domain={["auto", "auto"]} />
          <Tooltip formatter={(v) => `UGX ${formatNumber(Number(v))}/kg`} labelFormatter={(d) => formatDate(String(d))} />
          <Line type="monotone" dataKey="national" name="National reference" stroke={GRAY} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="price" name="Farmer" stroke={BLUE} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SalesCard({ detail, isFull }: { detail: FarmerDetail; isFull: boolean }) {
  return (
    <section className={CARD}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 mb-3">
        <h3 className="text-base font-semibold text-gray-900">Sales</h3>
        {detail.sales.length > 0 && (
          <div className="flex gap-4 text-xs text-muted whitespace-nowrap">
            <span>vs village <span className="font-medium text-gray-900">{formatIndex(detail.medianVsVillage)}</span></span>
            {detail.mainBuyer && <span>Main buyer <span className="font-medium text-gray-900">{labelBuyer(detail.mainBuyer)}</span></span>}
          </div>
        )}
      </div>
      {detail.sales.length === 0 ? (
        <p className="text-sm text-muted">No sales reported yet.</p>
      ) : (
        <>
          <SalesChart detail={detail} />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-gray-50">
                  <th className={`${TH} text-left`}>Date</th>
                  <th className={`${TH} text-left`}>Form</th>
                  <th className={`${TH} text-right`}>Kg</th>
                  <th className={`${TH} text-right`}>UGX/kg</th>
                  <th className={`${TH} text-left`}>Buyer</th>
                  <th className={`${TH} text-right`}>vs national</th>
                  {isFull && <th className={`${TH} text-right`}>Total UGX</th>}
                </tr>
              </thead>
              <tbody>
                {detail.sales.map((s, i) => (
                  <tr key={`${s.date}-${i}`} className="border-b border-gray-100">
                    <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{formatDate(s.date)}</td>
                    <td className="px-3 py-2 text-gray-600 capitalize whitespace-nowrap">{s.form}</td>
                    <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.kg)}</td>
                    <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.ugxPerKg)}</td>
                    <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{s.buyerType ? labelBuyer(s.buyerType) : "—"}</td>
                    <td className="px-3 py-2 text-right whitespace-nowrap"><span className={indexPillClass(s.indexVsNational)}>{formatIndex(s.indexVsNational)}</span></td>
                    {isFull && <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(s.totalUgx)}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function ProblemsCard({ detail }: { detail: FarmerDetail }) {
  return (
    <section className={CARD}>
      <h3 className="text-base font-semibold text-gray-900 mb-2">Problems reported</h3>
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

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const position = isFull ? "left-0 md:left-14 w-auto right-0" : "right-0 left-auto";
  const p = detail?.profile;
  const path = p ? [p.village, p.parish, p.subCounty, p.district, p.region].join(" · ") : "";
  return (
    <aside
      aria-label="Farmer details"
      style={isFull ? undefined : { width: "min(560px, 100vw)" }}
      className={`fixed top-14 bottom-0 ${position} bg-white border-l border-line shadow-xl z-40 flex flex-col transition-[width,left] duration-150`}
    >
      <div className="flex items-start justify-between gap-3 p-5 border-b border-line">
        {p ? (
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-bold text-gray-900 truncate">{p.firstName}</h2>
            <p className="text-sm text-muted mt-0.5 truncate" title={path}>{path}</p>
            <div className="flex gap-x-6 mt-3">
              <Stat label="Registered" value={formatDate(p.registeredAt)} />
              <Stat label="Calls" value={String(p.callCount)} />
              <Stat label="Last call" value={formatDate(p.lastCallAt)} />
            </div>
          </div>
        ) : (
          <h2 className="text-xl font-bold text-gray-900">Farmer not found</h2>
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
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-gray-50">
          <SalesCard detail={detail} isFull={isFull} />
          <ProblemsCard detail={detail} />
        </div>
      )}
    </aside>
  );
}
