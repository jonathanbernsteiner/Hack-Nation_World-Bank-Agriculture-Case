"use client";

import { AlertTriangle, TrendingDown } from "lucide-react";
import type { AreaPath, AreaSummary, BuyerPrice, CoffeeForm, FarmerRow, FormPrice, Level, Warning } from "@/lib/types";
import { formatIndex, formatNumber, labelBuyer, labelLevel, labelProblem } from "@/lib/format";
import FarmersTable, { indexPillClass } from "./FarmersTable";
import PriceChart from "./PriceChart";
import WeatherCard from "./WeatherCard";

const CARD = "bg-white border border-line rounded-xl p-6";
const HEADING = "text-base font-semibold text-ink";
const TABLE_WRAP = "-mx-6 border-y border-line overflow-hidden";
const TABLE_SCROLL = "overflow-x-auto";
const FORM_SHORT: Record<CoffeeForm, string> = { kiboko: "Kiboko", faq: "FAQ", parchment: "Parchment" };
const TH = "font-medium text-muted px-3 py-2 whitespace-nowrap";

const CHILD_HEADINGS: Record<Level, string> = {
  country: "Countries",
  district: "Districts",
  sub_county: "Sub-counties",
  parish: "Parishes",
  village: "Villages",
};

interface AreaPanelProps {
  area: AreaSummary;
  childAreas: AreaSummary[];
  farmers: FarmerRow[] | null;
  onSelect: (path: AreaPath) => void;
  notice?: string | null;
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-2xl font-bold text-ink">{formatNumber(value)}</div>
      <div className="text-sm font-medium text-muted">{label}</div>
    </div>
  );
}

function subtitleFor(area: AreaSummary): string {
  if (area.level === "village" && area.path.length === 4) return `${area.path[2]} parish, ${area.path[0]}`;
  return area.region ? `${labelLevel(area.level)} · ${area.region}` : labelLevel(area.level);
}

function HeaderCard({ area }: { area: AreaSummary }) {
  return (
    <div className={CARD}>
      <h2 className="text-lg font-semibold text-ink">{area.name}</h2>
      <div className="text-sm text-muted">{subtitleFor(area)}</div>
      <div className="grid grid-cols-2 gap-4 mt-4">
        <Stat label="Farmers" value={area.farmers} />
        {area.level !== "village" && <Stat label="Villages" value={area.villages} />}
        <Stat label="Calls, all time" value={area.calls} />
        <Stat label="New, 90 days" value={area.newFarmers90d} />
      </div>
    </div>
  );
}

function WarningRow({ warning, onSelect }: { warning: Warning; onSelect: (path: AreaPath) => void }) {
  const isProblem = warning.kind === "problem";
  const Icon = isProblem ? AlertTriangle : TrendingDown;
  const color = isProblem ? "text-red-600" : "text-amber-500";
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(warning.path)}
        className="w-full flex items-start gap-3 py-3 text-left border-b border-divider last:border-b-0 hover:bg-gray-50 transition-colors"
      >
        <Icon size={16} className={`${color} mt-0.5 shrink-0`} />
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span className="text-sm font-semibold text-ink">{warning.title}</span>
            <span className="inline-flex shrink-0 items-center whitespace-nowrap px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]">
              Officer check
            </span>
          </span>
          <span className="block text-[13px] text-muted">{warning.detail}</span>
        </span>
      </button>
    </li>
  );
}

function WarningsCard({ warnings, onSelect }: { warnings: Warning[]; onSelect: (path: AreaPath) => void }) {
  return (
    <div className={CARD}>
      <div className="flex items-center gap-2 mb-4">
        <h2 className={HEADING}>Warnings</h2>
        <span className="inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5 border bg-gray-100 text-gray-700 border-gray-200">
          {warnings.length}
        </span>
      </div>
      <ul>
        {warnings.map((w) => (
          <WarningRow key={w.id} warning={w} onSelect={onSelect} />
        ))}
      </ul>
    </div>
  );
}

function formPill(price: FormPrice) {
  // Median of per-sale indexes (month-matched), the same metric as every other page.
  const index = price.index;
  if (index === null) return <span className={indexPillClass(null)}>Not enough sales</span>;
  return <span className={indexPillClass(index)}>{formatIndex(index)}</span>;
}

function BuyerRow({ buyer }: { buyer: BuyerPrice }) {
  return (
    <li className="grid grid-cols-[1fr_auto_auto] gap-3 items-center py-2 text-sm">
      <span className="font-medium text-gray-900">{labelBuyer(buyer.buyer)}</span>
      <span className={indexPillClass(buyer.priceIndex)}>{formatIndex(buyer.priceIndex)}</span>
      <span className="text-gray-600 whitespace-nowrap text-right">
        {formatNumber(buyer.sales)} {buyer.sales === 1 ? "sale" : "sales"}
      </span>
    </li>
  );
}

function PricesCard({ area }: { area: AreaSummary }) {
  const forms = area.priceByForm.filter((p) => p.sales > 0);
  const buyers = area.priceByBuyer.filter((b) => b.sales > 0);
  return (
    <div className={CARD}>
      <h2 className={`${HEADING} mb-4`} title="Median needs 3 sales from 3 farmers">
        Prices, 12 months (UGX/kg)
      </h2>
      {forms.length === 0 ? (
        <p className="text-sm text-faint text-center py-4">No sales reported in the last 12 months.</p>
      ) : (
        <div className={TABLE_WRAP}>
          <div className={TABLE_SCROLL}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-gray-50">
                <th className={`text-left ${TH}`}>Form</th>
                <th className={`text-right ${TH}`}>Here</th>
                <th className={`text-right ${TH}`}>National</th>
                <th className={`text-right ${TH}`}>vs nat.</th>
              </tr>
            </thead>
            <tbody>
              {forms.map((p) => (
                <tr key={p.form} className="border-b border-gray-100 last:border-b-0">
                  <td className="px-3 py-2 font-medium text-gray-900 whitespace-nowrap">{FORM_SHORT[p.form]}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{p.median === null ? "—" : formatNumber(p.median)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{p.national === null ? "—" : formatNumber(p.national)}</td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">{formPill(p)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
      )}
      {buyers.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-ink mb-1">By buyer</h3>
          <ul>
            {buyers.map((b) => (
              <BuyerRow key={b.buyer} buyer={b} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ProblemsCard({ problems }: { problems: AreaSummary["problems90d"] }) {
  return (
    <div className={CARD}>
      <h2 className={`${HEADING} mb-4`}>Problems, 90 days</h2>
      {problems.length === 0 ? (
        <p className="text-sm text-faint">No problems reported in the last 90 days</p>
      ) : (
        <ul>
          {problems.map((p) => (
            <li
              key={p.problem}
              className="flex items-center justify-between py-2 text-sm border-b border-divider last:border-b-0"
            >
              <span className="text-gray-900">{labelProblem(p.problem)}</span>
              <span className="text-gray-600">{p.farmers} {p.farmers === 1 ? "farm" : "farms"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ChildrenCard({
  area,
  childAreas,
  onSelect,
}: {
  area: AreaSummary;
  childAreas: AreaSummary[];
  onSelect: (path: AreaPath) => void;
}) {
  return (
    <div className={CARD}>
      <h2 className={`${HEADING} mb-4`}>
        {CHILD_HEADINGS[childAreas[0].level]} in {area.name}
      </h2>
      <div className={TABLE_WRAP}>
        <div className={TABLE_SCROLL}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line bg-gray-50">
              <th className={`text-left ${TH}`}>Name</th>
              <th className={`text-right ${TH}`}>Farmers</th>
              <th className={`text-right ${TH}`}>vs national, 12 months</th>
              <th className={`text-right ${TH}`}>Warnings</th>
            </tr>
          </thead>
          <tbody>
            {childAreas.map((c) => (
              <tr
                key={c.path.join("/")}
                onClick={() => onSelect(c.path)}
                className="border-b border-gray-100 last:border-b-0 hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <td className="px-3 py-2 font-medium text-gray-900 whitespace-nowrap">{c.name}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(c.farmers)}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <span className={indexPillClass(c.priceIndex)}>{formatIndex(c.priceIndex)}</span>
                </td>
                <td
                  className={`px-3 py-2 text-right font-mono whitespace-nowrap ${
                    c.warnings.length > 0 ? "text-red-600 font-medium" : "text-gray-300"
                  }`}
                >
                  {c.warnings.length > 0 ? c.warnings.length : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>
    </div>
  );
}

export default function AreaPanel({ area, childAreas, farmers, onSelect, notice = null }: AreaPanelProps) {
  const sortedChildren = [...childAreas].sort((a, b) => b.farmers - a.farmers);
  return (
    <div className="flex flex-col gap-4">
      {notice && (
        <p role="status" className="rounded-lg border border-line bg-gray-50 px-3 py-2 text-sm text-gray-700">
          {notice}
        </p>
      )}
      <HeaderCard area={area} />
      {area.warnings.length > 0 && <WarningsCard warnings={area.warnings} onSelect={onSelect} />}
      {sortedChildren.length > 0 && <ChildrenCard area={area} childAreas={sortedChildren} onSelect={onSelect} />}
      <div className={CARD}>
        <PriceChart area={area} />
      </div>
      <PricesCard area={area} />
      <ProblemsCard problems={area.problems90d} />
      <div className={CARD}>
        <WeatherCard lat={area.lat} lon={area.lon} />
      </div>
      {farmers !== null && (
        <div className={CARD}>
          <FarmersTable farmers={farmers} />
        </div>
      )}
    </div>
  );
}
