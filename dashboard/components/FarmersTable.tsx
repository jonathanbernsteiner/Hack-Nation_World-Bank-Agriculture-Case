import type { BuyerType, CoffeeForm, FarmerRow } from "@/lib/types";
import { formatDate, formatIndex, formatUgx, labelBuyer, labelProblem } from "@/lib/format";

const AMBER_MIN_PCT = -14;

const PILL_BASE = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border whitespace-nowrap";
const PILL_GREEN = "bg-[#ECFDF5] text-[#10B981] border-[#A7F3D0]";
const PILL_AMBER = "bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]";
const PILL_RED = "bg-red-50 text-red-700 border-red-200";
const PILL_NEUTRAL = "bg-[#F1F5F9] text-[#94A3B8] border-[#E2E8F0]";

export type PriceBand = "ok" | "warn" | "bad" | "none";

/** Band by the rounded percent shown: 0% or more ok, -1..-14% warn, -15% or lower bad. */
export function priceBand(index: number | null): PriceBand {
  if (index === null) return "none";
  const pct = Math.round((index - 1) * 100);
  if (pct >= 0) return "ok";
  return pct >= AMBER_MIN_PCT ? "warn" : "bad";
}

const PILL_BY_BAND: Record<PriceBand, string> = { ok: PILL_GREEN, warn: PILL_AMBER, bad: PILL_RED, none: PILL_NEUTRAL };

const SHORT_FORM: Record<CoffeeForm, string> = { kiboko: "Kiboko", faq: "FAQ", parchment: "Parchment" };

export function shortForm(form: CoffeeForm): string {
  return SHORT_FORM[form];
}

/** Classes for a bordered pill coloured by price index (1.0 = reference). */
export function indexPillClass(index: number | null): string {
  return `${PILL_BASE} ${PILL_BY_BAND[priceBand(index)]}`;
}

function Dash() {
  return <span className="text-gray-300">—</span>;
}

function buyerCell(buyer: BuyerType | null) {
  return buyer ? labelBuyer(buyer) : <Dash />;
}

interface FarmersTableProps {
  farmers: FarmerRow[];
  onOpenFarmer?: (id: number) => void;
}

export default function FarmersTable({ farmers, onOpenFarmer }: FarmersTableProps) {
  return (
    <div>
      <h2 className="text-base font-semibold text-ink mb-4">Farmers</h2>
      {farmers.length === 0 ? (
        <p className="text-sm text-faint text-center py-6">No farmers registered in this village yet.</p>
      ) : (
        <div className="border border-line rounded-[14px] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line bg-gray-50">
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">First name</th>
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Last sale</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">vs village</th>
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Buyer</th>
                  <th className="text-left font-medium text-muted px-4 py-3 whitespace-nowrap">Problems</th>
                  <th className="text-right font-medium text-muted px-4 py-3 whitespace-nowrap">Calls</th>
                </tr>
              </thead>
              <tbody>
                {farmers.map((f) => {
                  const sale = f.lastSale;
                  const index = sale && f.villageMedian ? sale.ugxPerKg / f.villageMedian : null;
                  return (
                    <tr
                      key={f.id}
                      className={`border-b border-gray-100 last:border-b-0${onOpenFarmer ? " cursor-pointer hover:bg-gray-50 focus:outline-none focus-visible:bg-gray-50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500" : ""}`}
                      {...(onOpenFarmer && {
                        tabIndex: 0,
                        onClick: () => onOpenFarmer(f.id),
                        onKeyDown: (e: React.KeyboardEvent) => {
                          if (e.key === "Enter") onOpenFarmer(f.id);
                        },
                      })}
                    >
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {f.firstName}
                      </td>
                      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                        {sale ? (
                          <>
                            <div>
                              {formatUgx(sale.ugxPerKg)}/kg · {SHORT_FORM[sale.form]}
                            </div>
                            <div className="text-xs text-faint">{formatDate(sale.date)}</div>
                          </>
                        ) : (
                          <Dash />
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {index === null ? <Dash /> : <span className={indexPillClass(index)}>{formatIndex(index)}</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{buyerCell(sale?.buyerType ?? null)}</td>
                      <td className="px-4 py-3">
                        {f.problems.length === 0 ? (
                          <Dash />
                        ) : (
                          <span className="text-red-600 font-medium">{f.problems.map(labelProblem).join(", ")}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-700">{f.callCount}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
