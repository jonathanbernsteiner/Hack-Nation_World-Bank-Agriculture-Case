"use client";

import { AlertTriangle, TrendingDown } from "lucide-react";
import type { AreaPath, AreaSummary, BuyerPrice, FarmerRow, FormPrice, Level, Warning } from "@/lib/types";
import { formatIndex, formatNumber, formatUgx, labelBuyer, labelForm, labelLevel, labelProblem } from "@/lib/format";
import FarmersTable, { SyntheticTag, indexPillClass } from "./FarmersTable";
import PriceChart from "./PriceChart";
import WeatherCard from "./WeatherCard";

const CARD = "bg-white border border-line rounded-xl p-5";
const HEADING = "text-base font-semibold text-ink";
const TABLE_WRAP = "border border-line rounded-[14px] overflow-hidden";
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
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xl font-bold text-ink">{formatNumber(value)}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

function HeaderCard({ area }: { area: AreaSummary }) {
  const subtitle = area.region ? `${labelLevel(area.level)} · ${area.region}` : labelLevel(area.level);
  return (
    <div className={CARD}>
      <div className="flex items-center gap-2 flex-wrap">
        <h2 className="text-xl font-bold text-ink">{area.name}</h2>
        {area.isSynthetic && <SyntheticTag />}
      </div>
      <div className="text-sm text-muted">{subtitle}</div>
      <div className="grid grid-cols-2 gap-4 mt-4">
        <Stat label="Farmers" value={area.farmers} />
        <Stat label="Villages" value={area.villages} />
        <Stat label="Calls" value={area.calls} />
        <Stat label="New in 90 days" value={area.newFarmers90d} />
      </div>
    </div>
  );
}

function WarningRow({ warning, onSelect }: { warning: Warning; onSelect: (path: AreaPath) => void }) {
  const isProblem = warning.kind === "problem";
  const Icon = isProblem && warning.severity === "high" ? AlertTriangle : TrendingDown;
  const color = isProblem && warning.severity === "high" ? "text-red-600" : "text-amber-500";
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(warning.path)}
        className="w-full flex items-start gap-3 py-3 text-left border-b border-divider last:border-b-0 hover:bg-gray-50 transition-colors"
      >
        <Icon size={16} className={`${color} mt-0.5 shrink-0`} />
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">{warning.title}</span>
          <span className="block text-[13px] text-muted">{warning.detail}</span>
        </span>
      </button>
    </li>
  );
}

function WarningsCard({ warnings, onSelect }: { warnings: Warning[]; onSelect: (path: AreaPath) => void }) {
  return (
    <div className={CARD}>
      <div className="flex items-center gap-2 mb-1">
        <h2 className={HEADING}>Warnings</h2>
        <span className="inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5 bg-red-100 text-red-800">
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
  const index = price.median !== null && price.national ? price.median / price.national : null;
  if (index === null) return <span className={indexPillClass(null)}>not enough sales</span>;
  return <span className={indexPillClass(index)}>{formatIndex(index)}</span>;
}

function BuyerRow({ buyer }: { buyer: BuyerPrice }) {
  const widthPct = Math.min(100, Math.round((buyer.priceIndex ?? 0) * 100));
  return (
    <li className="py-2">
      <div className="flex items-baseline justify-between text-sm gap-2">
        <span className="font-medium text-gray-900">{labelBuyer(buyer.buyer)}</span>
        <span className="text-gray-600">
          <span className="font-mono">{formatIndex(buyer.priceIndex)}</span> · {buyer.sales} sales
        </span>
      </div>
      <div className="h-2 rounded-full bg-gray-100 mt-1.5">
        <div className="h-2 rounded-full bg-blue-500" style={{ width: `${widthPct}%` }} />
      </div>
    </li>
  );
}

function takeaway(buyers: BuyerPrice[]): string | null {
  const middleman = buyers.find((b) => b.buyer === "middleman")?.priceIndex ?? null;
  const coop = buyers.find((b) => b.buyer === "cooperative")?.priceIndex ?? null;
  if (middleman === null || coop === null || coop === 0) return null;
  const pct = Math.round(Math.abs(middleman / coop - 1) * 100);
  if (pct === 0) return "Middlemen and cooperatives paid the same here.";
  return middleman < coop
    ? `Middlemen paid ${pct}% less than cooperatives here.`
    : `Middlemen paid ${pct}% more than cooperatives here.`;
}

function PricesCard({ area }: { area: AreaSummary }) {
  const forms = area.priceByForm.filter((p) => p.sales > 0);
  const buyers = area.priceByBuyer.filter((b) => b.sales > 0);
  const sentence = takeaway(area.priceByBuyer);
  return (
    <div className={CARD}>
      <h2 className={`${HEADING} mb-3`}>Prices, last 12 months</h2>
      {forms.length === 0 ? (
        <p className="text-sm text-faint text-center py-4">No sales reported in the last 12 months.</p>
      ) : (
        <div className={TABLE_WRAP}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-gray-50">
                <th className={`text-left ${TH}`}>Form</th>
                <th className={`text-right ${TH}`}>Here</th>
                <th className={`text-right ${TH}`}>National</th>
                <th className={`text-right ${TH}`}>Difference</th>
              </tr>
            </thead>
            <tbody>
              {forms.map((p) => (
                <tr key={p.form} className="border-b border-gray-100 last:border-b-0">
                  <td className="px-3 py-2 font-medium text-gray-900">{labelForm(p.form)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatUgx(p.median)}</td>
                  <td className="px-3 py-2 text-right font-mono text-gray-700 whitespace-nowrap">{formatUgx(p.national)}</td>
                  <td className="px-3 py-2 text-right">{formPill(p)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {buyers.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-semibold text-ink">Who pays more</h3>
          <ul>
            {buyers.map((b) => (
              <BuyerRow key={b.buyer} buyer={b} />
            ))}
          </ul>
          {sentence && <p className="text-sm text-gray-700 mt-1">{sentence}</p>}
        </div>
      )}
      <p className="text-xs text-faint mt-3">
        Median needs 3 sales from 3 farmers. National = UCDA / MAAIF monthly farm-gate average.
      </p>
    </div>
  );
}

function ProblemsCard({ problems }: { problems: AreaSummary["problems90d"] }) {
  return (
    <div className={CARD}>
      <h2 className={`${HEADING} mb-2`}>Problems reported, last 90 days</h2>
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
              <span className="text-gray-600 font-mono">{p.farmers} {p.farmers === 1 ? "farm" : "farms"}</span>
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
      <h2 className={`${HEADING} mb-3`}>
        {CHILD_HEADINGS[childAreas[0].level]} in {area.name}
      </h2>
      <div className={TABLE_WRAP}>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-line bg-gray-50">
              <th className={`text-left ${TH}`}>Name</th>
              <th className={`text-right ${TH}`}>Farmers</th>
              <th className={`text-right ${TH}`}>Price vs national</th>
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
                <td className="px-3 py-2 font-medium text-gray-900">{c.name}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatNumber(c.farmers)}</td>
                <td className="px-3 py-2 text-right font-mono text-gray-700">{formatIndex(c.priceIndex)}</td>
                <td
                  className={`px-3 py-2 text-right font-mono ${
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
  );
}

export default function AreaPanel({ area, childAreas, farmers, onSelect }: AreaPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      <HeaderCard area={area} />
      {area.warnings.length > 0 && <WarningsCard warnings={area.warnings} onSelect={onSelect} />}
      <PricesCard area={area} />
      <div className={CARD}>
        <PriceChart area={area} />
      </div>
      <ProblemsCard problems={area.problems90d} />
      <div className={CARD}>
        <WeatherCard lat={area.lat} lon={area.lon} />
      </div>
      {childAreas.length > 0 && <ChildrenCard area={area} childAreas={childAreas} onSelect={onSelect} />}
      {farmers !== null && (
        <div className={CARD}>
          <FarmersTable farmers={farmers} />
        </div>
      )}
    </div>
  );
}
