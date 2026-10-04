// Pure builder for the farmer registry page (no I/O). Windows are relative to data.today.

import { median } from "./aggregate";
import { MIN_FARMERS, MIN_SALES } from "./types";
import type { BuyerType, CoffeeForm, DashboardData, Sale } from "./types";

const PRICE_MONTHS = 12;
const PROBLEM_DAYS = 90;

export interface RegistryRow {
  id: number;
  firstName: string;
  region: string;
  district: string;
  subCounty: string;
  parish: string;
  village: string;
  registeredAt: string;
  callCount: number;
  lastCallAt: string | null;
  lastSale: { date: string; form: CoffeeForm; ugxPerKg: number; buyerType: BuyerType | null } | null;
  priceVsVillage: number | null; // last sale price / village 12-month median for that form
  problems90d: string[];
  isSynthetic: boolean;
}

function addDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function windowStart(today: string): string {
  const [y, m] = today.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 - (PRICE_MONTHS - 1), 1)).toISOString().slice(0, 10);
}

function villageMedian(sales: Sale[]): number | null {
  if (sales.length < MIN_SALES) return null;
  if (new Set(sales.map((s) => s.farmerId)).size < MIN_FARMERS) return null;
  return median(sales.map((s) => s.ugxPerKg));
}

function groupBy<T>(items: T[], key: (item: T) => number): Map<number, T[]> {
  const groups = new Map<number, T[]>();
  for (const item of items) {
    const k = key(item);
    const group = groups.get(k);
    if (group) group.push(item);
    else groups.set(k, [item]);
  }
  return groups;
}

export function registryRows(data: DashboardData): RegistryRow[] {
  const villageById = new Map(data.villages.map((v) => [v.id, v]));
  const start = windowStart(data.today);
  const problemCutoff = addDays(data.today, -PROBLEM_DAYS);
  const salesByFarmer = groupBy(data.sales, (s) => s.farmerId);
  const recentSalesByVillage = groupBy(
    data.sales.filter((s) => s.date >= start),
    (s) => s.villageId,
  );
  const problemsByFarmer = groupBy(
    data.problems.filter((p) => p.date > problemCutoff),
    (p) => p.farmerId,
  );

  const rows: RegistryRow[] = [];
  for (const farmer of data.farmers) {
    const village = villageById.get(farmer.villageId);
    if (!village) continue;
    const last = (salesByFarmer.get(farmer.id) ?? []).reduce<Sale | undefined>(
      (best, s) => (best === undefined || s.date > best.date ? s : best),
      undefined,
    );
    const med = last
      ? villageMedian((recentSalesByVillage.get(village.id) ?? []).filter((s) => s.form === last.form))
      : null;
    rows.push({
      id: farmer.id,
      firstName: farmer.firstName,
      region: village.region,
      district: village.district,
      subCounty: village.subCounty,
      parish: village.parish,
      village: village.village,
      registeredAt: farmer.registeredAt,
      callCount: farmer.callCount,
      lastCallAt: farmer.lastCallAt,
      lastSale: last ? { date: last.date, form: last.form, ugxPerKg: last.ugxPerKg, buyerType: last.buyerType } : null,
      priceVsVillage: last && med !== null && med > 0 ? last.ugxPerKg / med : null,
      problems90d: [...new Set((problemsByFarmer.get(farmer.id) ?? []).map((p) => p.problem))],
      isSynthetic: farmer.isSynthetic,
    });
  }
  return rows.sort((a, b) => b.registeredAt.localeCompare(a.registeredAt));
}
