import type { BuyerType, CoffeeForm, FarmerRow } from "@/lib/types";
import { formatDate, formatIndex, formatUgx, labelBuyer, labelProblem } from "@/lib/format";

const GREEN_MIN_INDEX = 0.97;
const AMBER_MIN_INDEX = 0.85;

const PILL_BASE = "inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border whitespace-nowrap";
const PILL_GREEN = "bg-[#ECFDF5] text-[#10B981] border-[#A7F3D0]";
const PILL_AMBER = "bg-[#FFFBEB] text-[#F59E0B] border-[#FDE68A]";
const PILL_RED = "bg-red-50 text-red-700 border-red-200";
const PILL_NEUTRAL = "bg-[#F1F5F9] text-[#94A3B8] border-[#E2E8F0]";

const SHORT_FORM: Record<CoffeeForm, string> = { kiboko: "kiboko", faq: "FAQ", parchment: "parchment" };

/** Classes for a bordered pill coloured by price index (1.0 = reference). */
export function indexPillClass(index: number | null): string {
  if (index === null) return `${PILL_BASE} ${PILL_NEUTRAL}`;
  if (index >= GREEN_MIN_INDEX) return `${PILL_BASE} ${PILL_GREEN}`;
  if (index >= AMBER_MIN_INDEX) return `${PILL_BASE} ${PILL_AMBER}`;
  return `${PILL_BASE} ${PILL_RED}`;
}

export function SyntheticTag() {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold border bg-purple-50 text-purple-700 border-purple-200">
      Synthetic
    </span>
  );
}

function Dash() {
  return <span className="text-gray-300">—</span>;
}

function buyerCell(buyer: BuyerType | null) {
  return buyer ? labelBuyer(buyer) : <Dash />;
}

interface FarmersTableProps {
  farmers: FarmerRow[];
}

export default function FarmersTable({ farmers }: FarmersTableProps) {
  return (
    <div>
      <h2 className="text-base font-semibold text-ink">Farmers</h2>
      <p className="text-xs text-faint mt-1 mb-3">First names only. PINs and phone numbers are never shown.</p>
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
                    <tr key={f.id} className="border-b border-gray-100 last:border-b-0">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        <span className="inline-flex items-center gap-1.5">
                          {f.firstName}
                          {f.isSynthetic && <SyntheticTag />}
                        </span>
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
