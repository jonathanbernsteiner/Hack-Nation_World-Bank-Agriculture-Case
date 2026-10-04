// Pure price analytics for the Prices page. Windows are relative to data.today.

import { median, referenceFor } from "./aggregate";
import { MIN_FARMERS, MIN_SALES, PRICE_LOW_INDEX, PRICE_WINDOW_DAYS } from "./types";
import type { BuyerType, CoffeeForm, DashboardData, Sale } from "./types";

export const FORMS: CoffeeForm[] = ["kiboko", "faq", "parchment"];
const BUYERS: BuyerType[] = ["middleman", "cooperative", "other"];
const MONTHS_WINDOW = 12;
const P10 = 0.1;
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
  index90d: number | null; // vs national, same 90-day window as `low`
  byForm: PriceByForm;
  middlemanShare: number | null; // % of sales
  low: boolean;
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

function addDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function addMonths(month: string, months: number): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + months, 1)).toISOString().slice(0, 7);
}

function lastMonths(today: string): string[] {
  const current = today.slice(0, 7);
  return Array.from({ length: MONTHS_WINDOW }, (_, i) => addMonths(current, i - (MONTHS_WINDOW - 1)));
}

function windowSales(data: DashboardData, fromDate: string): Sale[] {
  return data.sales.filter((s) => s.date >= fromDate && s.date <= data.today);
}

function yearSales(data: DashboardData): Sale[] {
  return windowSales(data, `${lastMonths(data.today)[0]}-01`);
}

function enough(sales: Sale[]): boolean {
  return sales.length >= MIN_SALES && new Set(sales.map((s) => s.farmerId)).size >= MIN_FARMERS;
}

function indexOf(sales: Sale[], data: DashboardData): number | null {
  if (!enough(sales)) return null;
  const ratios: number[] = [];
  for (const s of sales) {
    const ref = referenceFor(data.reference, s.form, s.date.slice(0, 7));
    if (ref !== null && ref > 0) ratios.push(s.ugxPerKg / ref);
  }
  return median(ratios);
}

function pricesByForm(sales: Sale[]): PriceByForm {
  const result = {} as PriceByForm;
  for (const form of FORMS) {
    const formSales = sales.filter((s) => s.form === form);
    result[form] = enough(formSales) ? median(formSales.map((s) => s.ugxPerKg)) : null;
  }
  return result;
}

export function buyerComparison(data: DashboardData): BuyerComparison {
  const sales = yearSales(data);
  const rows = BUYERS.map((buyer) => {
    const own = sales.filter((s) => s.buyerType === buyer);
    return { buyer, index: indexOf(own, data), byForm: pricesByForm(own), sales: own.length };
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
  const sales = yearSales(data);
  const recentFrom = addDays(data.today, -(PRICE_WINDOW_DAYS - 1));
  const districts = [...new Set(data.villages.map((v) => v.district))];
  const rows = districts.map((district): DistrictRow => {
    const villages = data.villages.filter((v) => v.district === district);
    const ids = new Set(villages.map((v) => v.id));
    const own = sales.filter((s) => ids.has(s.villageId));
    const recentIndex = indexOf(
      own.filter((s) => s.date >= recentFrom),
      data,
    );
    return {
      district,
      region: villages[0].region,
      sales: own.length,
      index90d: recentIndex,
      byForm: pricesByForm(own),
      middlemanShare:
        own.length === 0 ? null : Math.round((own.filter((s) => s.buyerType === "middleman").length / own.length) * 100),
      low: recentIndex !== null && recentIndex <= PRICE_LOW_INDEX,
    };
  });
  return rows
    .filter((r) => r.sales > 0)
    .sort((a, b) => (a.index90d ?? Infinity) - (b.index90d ?? Infinity) || a.district.localeCompare(b.district));
}

export function monthlyByBuyer(data: DashboardData, form: CoffeeForm): MonthlyBuyerPoint[] {
  const sales = yearSales(data).filter((s) => s.form === form);
  return lastMonths(data.today).map((month) => {
    const inMonth = sales.filter((s) => s.date.slice(0, 7) === month);
    const med = (rows: Sale[]) => median(rows.map((s) => s.ugxPerKg));
    return {
      month,
      national: referenceFor(data.reference, form, month),
      middleman: med(inMonth.filter((s) => s.buyerType === "middleman")),
      cooperative: med(inMonth.filter((s) => s.buyerType === "cooperative")),
      all: med(inMonth),
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
  const from = addDays(data.today, -(PRICE_WINDOW_DAYS - 1));
  const prices = windowSales(data, from)
    .filter((s) => s.form === form)
    .map((s) => s.ugxPerKg)
    .sort((a, b) => a - b);
  if (prices.length === 0) return null;
  return {
    p10: Math.round(percentile(prices, P10)),
    median: Math.round(percentile(prices, 0.5)),
    p90: Math.round(percentile(prices, P90)),
    sales: prices.length,
  };
}
