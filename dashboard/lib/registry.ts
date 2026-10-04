// Pure builder for the farmer registry page (no I/O). Windows are relative to data.today.

import { inWindow, indexVsVillage, medianIndex, yearSales } from "./aggregate";
import type { BuyerType, CoffeeForm, DashboardData, Sale } from "./types";

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
  priceVsVillage: number | null; // last sale's index / village median index for that form (365 days, minimums): month-aware
  problems90d: string[];
  isSynthetic: boolean;
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
  const salesByFarmer = groupBy(data.sales, (s) => s.farmerId);
  const recentSalesByVillage = groupBy(yearSales(data.sales, data.today), (s) => s.villageId);
  const problemsByFarmer = groupBy(
    data.problems.filter((p) => inWindow(p.date, data.today, PROBLEM_DAYS)),
    (p) => p.farmerId,
  );
  const villageIndexCache = new Map<string, number | null>();
  const villageIndex = (villageId: number, form: CoffeeForm): number | null => {
    const key = `${villageId}:${form}`;
    if (!villageIndexCache.has(key)) {
      const formSales = (recentSalesByVillage.get(villageId) ?? []).filter((s) => s.form === form);
      villageIndexCache.set(key, medianIndex(formSales, data.reference));
    }
    return villageIndexCache.get(key) ?? null;
  };

  const rows: RegistryRow[] = [];
  for (const farmer of data.farmers) {
    const village = villageById.get(farmer.villageId);
    if (!village) continue;
    const last = (salesByFarmer.get(farmer.id) ?? []).reduce<Sale | undefined>(
      (best, s) => (best === undefined || s.date > best.date ? s : best),
      undefined,
    );
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
      priceVsVillage: last ? indexVsVillage(last, villageIndex(village.id, last.form), data.reference) : null,
      problems90d: [...new Set((problemsByFarmer.get(farmer.id) ?? []).map((p) => p.problem))],
      isSynthetic: farmer.isSynthetic,
    });
  }
  return rows.sort((a, b) => b.registeredAt.localeCompare(a.registeredAt));
}
