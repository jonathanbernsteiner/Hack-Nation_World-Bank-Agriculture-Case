// Pure price analytics for the Prices page. Windows are relative to data.today.

import {
  chartMedian,
  districtPriceIndexes,
  inWindow,
  isLowIndex,
  lastMonths,
  medianIndex,
  medianPrice,
  referenceFor,
  yearSales,
} from "./aggregate";
import { PRICE_WINDOW_DAYS } from "./types";
import type { BuyerType, CoffeeForm, DashboardData, Sale } from "./types";

export const FORMS: CoffeeForm[] = ["kiboko", "faq", "parchment"];
const BUYERS: BuyerType[] = ["middleman", "cooperative", "other"];
const CHART_MONTHS = 12;
const P10 = 0.1;
const P50 = 0.5;
const P90 = 0.9;

export type PriceByForm = Record<CoffeeForm, number | null>;

export interface BuyerRow {
  buyer: BuyerType;
  index: number | null;
  byForm: PriceByForm;
  sales: number;
}
export interface BuyerComparison {
  rows: BuyerRow[];
  gapPct: number | null; // (middleman index ÷ cooperative index − 1) × 100; negative = middlemen paid less
  sales: number; // sales with a known buyer type in the window
}
export interface DistrictRow {
  district: string;
  region: string;
  sales: number;
  index90d: number | null; // vs national, 90 days: the price-warning metric (per-farmer median, then across farmers)
  byForm: PriceByForm;
  middlemanShare: number | null; // % of sales (12 months)
  low: boolean; // isLowIndex(index90d): the district has a price warning
}
export interface MonthlyBuyerPoint {
  month: string;
  national: number | null;
  middleman: number | null;
  cooperative: number | null;
  all: number | null;
}
export interface Spread {
  p10: number;
  median: number;
  p90: number;
  sales: number;
}

function pricesByForm(sales: Sale[]): PriceByForm {
  const result = {} as PriceByForm;
  for (const form of FORMS) result[form] = medianPrice(sales.filter((s) => s.form === form));
  return result;
}

export function buyerComparison(data: DashboardData): BuyerComparison {
  const sales = yearSales(data.sales, data.today);
  const rows = BUYERS.map((buyer) => {
    const own = sales.filter((s) => s.buyerType === buyer);
    return { buyer, index: medianIndex(own, data.reference), byForm: pricesByForm(own), sales: own.length };
  });
  const coop = rows.find((r) => r.buyer === "cooperative")?.index ?? null;
  const mid = rows.find((r) => r.buyer === "middleman")?.index ?? null;
  return {
    rows,
    gapPct: coop !== null && mid !== null && coop > 0 ? Math.round((mid / coop - 1) * 100) : null,
    sales: sales.filter((s) => s.buyerType !== null).length,
  };
}

export function districtPrices(data: DashboardData): DistrictRow[] {
  const sales = yearSales(data.sales, data.today);
  const recent = districtPriceIndexes(data);
  const districts = [...new Set(data.villages.map((v) => v.district))];
  const rows = districts.map((district): DistrictRow => {
    const villages = data.villages.filter((v) => v.district === district);
    const ids = new Set(villages.map((v) => v.id));
    const own = sales.filter((s) => ids.has(s.villageId));
    const recentIndex = recent.get(district)?.index ?? null;
    return {
      district,
      region: villages[0].region,
      sales: own.length,
      index90d: recentIndex,
      byForm: pricesByForm(own),
      middlemanShare:
        own.length === 0 ? null : Math.round((own.filter((s) => s.buyerType === "middleman").length / own.length) * 100),
      low: isLowIndex(recentIndex),
    };
  });
  return rows
    .filter((r) => r.sales > 0)
    .sort((a, b) => (a.index90d ?? Infinity) - (b.index90d ?? Infinity) || a.district.localeCompare(b.district));
}

export function monthlyByBuyer(data: DashboardData, form: CoffeeForm): MonthlyBuyerPoint[] {
  const sales = yearSales(data.sales, data.today).filter((s) => s.form === form);
  return lastMonths(data.today, CHART_MONTHS).map((month) => {
    const inMonth = sales.filter((s) => s.date.slice(0, 7) === month);
    return {
      month,
      national: referenceFor(data.reference, form, month),
      middleman: chartMedian(inMonth.filter((s) => s.buyerType === "middleman")),
      cooperative: chartMedian(inMonth.filter((s) => s.buyerType === "cooperative")),
      all: chartMedian(inMonth),
    };
  });
}

function percentile(sorted: number[], p: number): number {
  const pos = (sorted.length - 1) * p;
  const lo = Math.floor(pos);
  const hi = Math.ceil(pos);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
}

export function spread(data: DashboardData, form: CoffeeForm): Spread | null {
  const prices = data.sales
    .filter((s) => s.form === form && inWindow(s.date, data.today, PRICE_WINDOW_DAYS))
    .map((s) => s.ugxPerKg)
    .sort((a, b) => a - b);
  if (prices.length === 0) return null;
  return {
    p10: Math.round(percentile(prices, P10)),
    median: Math.round(percentile(prices, P50)),
    p90: Math.round(percentile(prices, P90)),
    sales: prices.length,
  };
}
