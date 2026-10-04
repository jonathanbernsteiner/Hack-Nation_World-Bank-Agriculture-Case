// Pure per-farmer detail for the Farmer peek panel (no I/O). Windows are relative to data.today.

import { indexVsVillage, median, medianIndex, medianPrice, referenceFor, saleIndex, yearSales } from "./aggregate";
import type { BuyerType, CoffeeForm, DashboardData } from "./types";

export interface FarmerSale {
  date: string;
  form: CoffeeForm;
  kg: number;
  ugxPerKg: number;
  buyerType: BuyerType | null;
  national: number | null; // national reference for the sale's month and form
  indexVsNational: number | null;
  villageMedian: number | null; // village median UGX/kg for the form, 365 days (null below the minimums)
  indexVsVillage: number | null; // sale index / village median index for the form (month-aware)
  totalUgx: number;
}

export interface FarmerDetail {
  profile: {
    id: number;
    firstName: string;
    village: string;
    parish: string;
    subCounty: string;
    district: string;
    region: string;
    registeredAt: string;
    callCount: number;
    lastCallAt: string | null;
    isSynthetic: boolean;
  };
  sales: FarmerSale[]; // newest first
  villageMedianByForm: Partial<Record<CoffeeForm, number | null>>;
  medianVsVillage: number | null;
  lastSaleVsVillage: number | null; // last sale's index / village median index for its form (same metric as the Farmers list)
  mainBuyer: BuyerType | null;
  problems: { date: string; problem: string }[]; // newest first
}

function mostCommonBuyer(sales: FarmerSale[]): BuyerType | null {
  const counts = new Map<BuyerType, number>();
  for (const s of sales) if (s.buyerType) counts.set(s.buyerType, (counts.get(s.buyerType) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
}

export function farmerDetail(data: DashboardData, farmerId: number): FarmerDetail | null {
  const farmer = data.farmers.find((f) => f.id === farmerId);
  const village = farmer && data.villages.find((v) => v.id === farmer.villageId);
  if (!farmer || !village) return null;

  const villageSales = yearSales(
    data.sales.filter((s) => s.villageId === village.id),
    data.today,
  );
  const medianByForm = new Map<CoffeeForm, number | null>();
  const indexByForm = new Map<CoffeeForm, number | null>();
  const villageStatsFor = (form: CoffeeForm): { median: number | null; index: number | null } => {
    if (!medianByForm.has(form)) {
      const formSales = villageSales.filter((s) => s.form === form);
      medianByForm.set(form, medianPrice(formSales));
      indexByForm.set(form, medianIndex(formSales, data.reference));
    }
    return { median: medianByForm.get(form) ?? null, index: indexByForm.get(form) ?? null };
  };

  const sales: FarmerSale[] = data.sales
    .filter((s) => s.farmerId === farmerId)
    .sort((a, b) => b.date.localeCompare(a.date))
    .map((s) => {
      const national = referenceFor(data.reference, s.form, s.date.slice(0, 7));
      const villageStats = villageStatsFor(s.form);
      return {
        date: s.date,
        form: s.form,
        kg: s.kg,
        ugxPerKg: s.ugxPerKg,
        buyerType: s.buyerType,
        national,
        indexVsNational: saleIndex(s, data.reference),
        villageMedian: villageStats.median,
        indexVsVillage: indexVsVillage(s, villageStats.index, data.reference),
        totalUgx: s.ugxPerKg * s.kg,
      };
    });

  const villageIndexes = sales.flatMap((s) => (s.indexVsVillage === null ? [] : [s.indexVsVillage]));
  return {
    profile: {
      id: farmer.id,
      firstName: farmer.firstName,
      village: village.village,
      parish: village.parish,
      subCounty: village.subCounty,
      district: village.district,
      region: village.region,
      registeredAt: farmer.registeredAt,
      callCount: farmer.callCount,
      lastCallAt: farmer.lastCallAt,
      isSynthetic: farmer.isSynthetic,
    },
    sales,
    villageMedianByForm: Object.fromEntries(medianByForm) as Partial<Record<CoffeeForm, number | null>>,
    medianVsVillage: median(villageIndexes),
    lastSaleVsVillage: sales[0]?.indexVsVillage ?? null,
    mainBuyer: mostCommonBuyer(sales),
    problems: data.problems
      .filter((p) => p.farmerId === farmerId)
      .map((p) => ({ date: p.date, problem: p.problem }))
      .sort((a, b) => b.date.localeCompare(a.date)),
  };
}
