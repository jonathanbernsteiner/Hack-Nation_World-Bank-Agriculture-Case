// Pure aggregation functions (no I/O). Every time window is relative to data.today.

import { formatDate, formatIndex, labelProblem } from "./format";
import {
  LEVELS,
  MIN_FARMERS,
  MIN_MONTHLY_SALES,
  MIN_SALES,
  PRICE_LOW_INDEX,
  PRICE_WARNING_MIN_FARMERS,
  PRICE_WARNING_MIN_SALES,
  PRICE_WINDOW_DAYS,
  PRICE_YEAR_DAYS,
  PROBLEM_BASELINE_WEEKS,
  PROBLEM_MIN_FARMERS,
  PROBLEM_WINDOW_DAYS,
  REFERENCE_MAX_CARRY_MONTHS,
} from "./types";
import type {
  AreaPath,
  AreaSummary,
  BuyerPrice,
  BuyerType,
  CoffeeForm,
  DashboardData,
  Farmer,
  FarmerRow,
  FormPrice,
  Kpis,
  Level,
  MonthlyPoint,
  ProblemReport,
  ReferencePrice,
  Sale,
  Village,
  Warning,
} from "./types";

const FORMS: CoffeeForm[] = ["kiboko", "faq", "parchment"];
const BUYERS: BuyerType[] = ["middleman", "cooperative", "other"];
const UGANDA_CENTRE = { lat: 1.37, lon: 32.29 };
const CHART_MONTHS = 12;
const NEW_FARMER_DAYS = 90;
const PROBLEM_LOOKBACK_DAYS = 90;
const KPI_WINDOW_DAYS = 30;
const INTERPOLATED_SOURCE = "interpolated";
/** Rounded percent at or below which an index is "low" (−15%); the same cut as the red pill. */
const LOW_INDEX_PCT = Math.round((PRICE_LOW_INDEX - 1) * 100);

// ---------- small helpers ----------

export function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

export function addDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function addMonths(month: string, months: number): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1 + months, 1)).toISOString().slice(0, 7);
}

function monthOf(date: string): string {
  return date.slice(0, 7);
}

/** Months elapsed from `from` to `to` (both YYYY-MM); negative when `to` is earlier. */
function monthsBetween(from: string, to: string): number {
  const [y1, m1] = from.split("-").map(Number);
  const [y2, m2] = to.split("-").map(Number);
  return (y2 - y1) * 12 + (m2 - m1);
}

/** The `count` calendar months ending with the month of `today`, oldest first. */
export function lastMonths(today: string, count: number): string[] {
  const current = monthOf(today);
  return Array.from({ length: count }, (_, i) => addMonths(current, i - (count - 1)));
}

/** True when `date` (YYYY-MM-DD) is one of the `days` days ending on `today` (inclusive); future dates are excluded. */
export function inWindow(date: string, today: string, days: number): boolean {
  return date <= today && date > addDays(today, -days);
}

function distinctCount(values: number[]): number {
  return new Set(values).size;
}

function mean(values: number[]): number {
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function centreOf(villages: Village[]): { lat: number; lon: number } {
  const points = villages.filter((v) => v.lat !== null && v.lon !== null);
  if (points.length === 0) return UGANDA_CENTRE;
  return { lat: mean(points.map((v) => v.lat as number)), lon: mean(points.map((v) => v.lon as number)) };
}

// ---------- reference prices ----------

const sortedReferenceCache = new WeakMap<ReferencePrice[], ReferencePrice[]>();

function sortedReference(reference: ReferencePrice[]): ReferencePrice[] {
  const cached = sortedReferenceCache.get(reference);
  if (cached) return cached;
  const sorted = [...reference].sort((a, b) => a.month.localeCompare(b.month));
  sortedReferenceCache.set(reference, sorted);
  return sorted;
}

/** Reference for `month`, else the nearest earlier month if it is at most REFERENCE_MAX_CARRY_MONTHS older; else null. */
export function referenceFor(reference: ReferencePrice[], form: CoffeeForm, month: string): number | null {
  let row: ReferencePrice | undefined;
  for (const r of sortedReference(reference)) {
    if (r.month > month) break;
    row = r;
  }
  if (!row || monthsBetween(row.month, month) > REFERENCE_MAX_CARRY_MONTHS) return null;
  return row[form];
}

/** Last month with a published (not "interpolated") reference, YYYY-MM; null when there is none. */
export function referenceAsOf(reference: ReferencePrice[]): string | null {
  const published = sortedReference(reference).filter(
    (r) => !r.source.toLowerCase().includes(INTERPOLATED_SOURCE),
  );
  return published.length === 0 ? null : published[published.length - 1].month;
}

/** Sale price / national reference for the sale's month and form (1.0 = national); null without a reference. */
export function saleIndex(sale: Pick<Sale, "date" | "form" | "ugxPerKg">, reference: ReferencePrice[]): number | null {
  const ref = referenceFor(reference, sale.form, monthOf(sale.date));
  return ref !== null && ref > 0 ? sale.ugxPerKg / ref : null;
}

/** True when the index rounds to −15% or lower (the red pill and the price-warning cut). */
export function isLowIndex(index: number | null): boolean {
  return index !== null && Math.round((index - 1) * 100) <= LOW_INDEX_PCT;
}

/** Median of the month-matched reference over these sales, comparable with their median price. */
function nationalFor(sales: Sale[], reference: ReferencePrice[], form: CoffeeForm): number | null {
  const refs: number[] = [];
  for (const sale of sales) {
    const ref = referenceFor(reference, form, monthOf(sale.date));
    if (ref !== null) refs.push(ref);
  }
  return median(refs);
}

// ---------- area paths ----------

export function areaPathOf(village: Village): AreaPath {
  return [village.district, village.subCounty, village.parish, village.village];
}

export function inArea(village: Village, path: AreaPath): boolean {
  const own = areaPathOf(village);
  return path.every((name, i) => own[i] === name);
}

export function levelOf(path: AreaPath): Level {
  return LEVELS[path.length];
}

// ---------- price statistics ----------

interface IndexedSale {
  farmerId: number;
  index: number;
}

function meetsMinimums(rows: { farmerId: number }[], minSales = MIN_SALES, minFarmers = MIN_FARMERS): boolean {
  return rows.length >= minSales && distinctCount(rows.map((r) => r.farmerId)) >= minFarmers;
}

function indexedSales(sales: Sale[], reference: ReferencePrice[]): IndexedSale[] {
  return sales.flatMap((sale) => {
    const index = saleIndex(sale, reference);
    return index === null ? [] : [{ farmerId: sale.farmerId, index }];
  });
}

/** Median UGX/kg; null below MIN_SALES sales or MIN_FARMERS farmers. */
export function medianPrice(sales: Sale[]): number | null {
  return meetsMinimums(sales) ? median(sales.map((s) => s.ugxPerKg)) : null;
}

/** Median of per-sale indexes vs national; null below MIN_SALES indexed sales or MIN_FARMERS farmers. */
export function medianIndex(sales: Sale[], reference: ReferencePrice[]): number | null {
  const rows = indexedSales(sales, reference);
  return meetsMinimums(rows) ? median(rows.map((r) => r.index)) : null;
}

/** Monthly chart point: median UGX/kg, null below MIN_MONTHLY_SALES sales. */
export function chartMedian(sales: Sale[]): number | null {
  return sales.length >= MIN_MONTHLY_SALES ? median(sales.map((s) => s.ugxPerKg)) : null;
}

/** Sales of the last 12 months (rolling PRICE_YEAR_DAYS days ending today, no future dates). */
export function yearSales(sales: Sale[], today: string): Sale[] {
  return sales.filter((s) => inWindow(s.date, today, PRICE_YEAR_DAYS));
}

/** Sale index relative to the village: saleIndex / village median index for the same form (month-aware). */
export function indexVsVillage(
  sale: Pick<Sale, "date" | "form" | "ugxPerKg">,
  villageIndex: number | null,
  reference: ReferencePrice[],
): number | null {
  const own = saleIndex(sale, reference);
  return own !== null && villageIndex !== null && villageIndex > 0 ? own / villageIndex : null;
}

export interface DistrictPriceIndex {
  index: number | null; // median across farmers of each farmer's median index; null below the warning minimums
  sales: number; // indexed sales in the window
  farms: number; // distinct farmers selling in the window
}

/** Price-warning metric over the last PRICE_WINDOW_DAYS days: each farmer's median index first, then the
 *  median across farmers, so one farmer's many sales cannot move it. Needs PRICE_WARNING_MIN_SALES sales
 *  from PRICE_WARNING_MIN_FARMERS farmers. */
export function farmerMedianIndex(sales: Sale[], reference: ReferencePrice[]): DistrictPriceIndex {
  const rows = indexedSales(sales, reference);
  const byFarmer = new Map<number, number[]>();
  for (const r of rows) byFarmer.set(r.farmerId, [...(byFarmer.get(r.farmerId) ?? []), r.index]);
  const enough = meetsMinimums(rows, PRICE_WARNING_MIN_SALES, PRICE_WARNING_MIN_FARMERS);
  const perFarmer = [...byFarmer.values()].map((indexes) => median(indexes) as number);
  return { index: enough ? median(perFarmer) : null, sales: rows.length, farms: byFarmer.size };
}

/** The district 90-day index used by the price warning, the Prices page and the district table. */
export function districtPriceIndexes(data: DashboardData): Map<string, DistrictPriceIndex> {
  const districtOf = new Map(data.villages.map((v) => [v.id, v.district]));
  const salesBy = new Map<string, Sale[]>();
  for (const district of new Set(districtOf.values())) salesBy.set(district, []);
  for (const sale of data.sales) {
    const district = districtOf.get(sale.villageId);
    if (district !== undefined && inWindow(sale.date, data.today, PRICE_WINDOW_DAYS)) salesBy.get(district)?.push(sale);
  }
  return new Map([...salesBy].map(([district, sales]) => [district, farmerMedianIndex(sales, data.reference)]));
}

// ---------- summaries ----------

function problemsByFarmers(problems: ProblemReport[]): { problem: string; farmers: number }[] {
  const byProblem = new Map<string, Set<number>>();
  for (const p of problems) {
    byProblem.set(p.problem, (byProblem.get(p.problem) ?? new Set()).add(p.farmerId));
  }
  return [...byProblem.entries()]
    .map(([problem, set]) => ({ problem, farmers: set.size }))
    .sort((a, b) => b.farmers - a.farmers || a.problem.localeCompare(b.problem));
}

function mainFormOf(sales: Sale[]): CoffeeForm | null {
  if (sales.length === 0) return null;
  const counts = FORMS.map((form) => ({ form, n: sales.filter((s) => s.form === form).length }));
  return counts.reduce((best, c) => (c.n > best.n ? c : best)).form;
}

function monthlySeries(sales: Sale[], form: CoffeeForm, data: DashboardData): MonthlyPoint[] {
  return lastMonths(data.today, CHART_MONTHS).map((month) => ({
    month,
    median: chartMedian(sales.filter((s) => s.form === form && monthOf(s.date) === month)),
    national: referenceFor(data.reference, form, month),
  }));
}

function startsWithPath(warning: Warning, path: AreaPath): boolean {
  return path.every((name, i) => warning.path[i] === name);
}

export function summarize(data: DashboardData, path: AreaPath, allWarnings?: Warning[]): AreaSummary {
  const villages = data.villages.filter((v) => inArea(v, path));
  const villageIds = new Set(villages.map((v) => v.id));
  const farmers = data.farmers.filter((f) => villageIds.has(f.villageId));
  const sales = yearSales(
    data.sales.filter((s) => villageIds.has(s.villageId)),
    data.today,
  );
  const problemsRecent = data.problems.filter(
    (p) => villageIds.has(p.villageId) && inWindow(p.date, data.today, PROBLEM_LOOKBACK_DAYS),
  );
  const warnings = (allWarnings ?? computeWarnings(data)).filter((w) => startsWithPath(w, path));

  const priceByForm: FormPrice[] = FORMS.map((form) => {
    const formSales = sales.filter((s) => s.form === form);
    return {
      form,
      median: medianPrice(formSales),
      national: nationalFor(formSales, data.reference, form),
      index: medianIndex(formSales, data.reference),
      sales: formSales.length,
    };
  });
  const priceByBuyer: BuyerPrice[] = BUYERS.map((buyer) => {
    const buyerSales = sales.filter((s) => s.buyerType === buyer);
    return { buyer, priceIndex: medianIndex(buyerSales, data.reference), sales: buyerSales.length };
  });
  const mainForm = mainFormOf(sales);

  return {
    path,
    level: levelOf(path),
    name: path.length === 0 ? "Uganda" : path[path.length - 1],
    region: path.length === 0 ? null : (villages[0]?.region ?? null),
    ...centreOf(villages),
    villages: villages.length,
    farmers: farmers.length,
    newFarmers90d: farmers.filter((f) => inWindow(f.registeredOn, data.today, NEW_FARMER_DAYS)).length,
    calls: farmers.reduce((sum, f) => sum + f.callCount, 0),
    priceIndex: medianIndex(sales, data.reference),
    priceByForm,
    priceByBuyer,
    mainForm,
    monthly: mainForm ? monthlySeries(sales, mainForm, data) : [],
    problems90d: problemsByFarmers(problemsRecent),
    warnings,
    // contains synthetic records
    isSynthetic: farmers.length > 0 ? farmers.some((f) => f.isSynthetic) : villages.some((v) => v.isSynthetic),
  };
}

export function childrenOf(data: DashboardData, path: AreaPath, allWarnings?: Warning[]): AreaSummary[] {
  if (path.length >= 4) return [];
  const warnings = allWarnings ?? computeWarnings(data);
  const names = new Set<string>();
  for (const village of data.villages) {
    if (inArea(village, path)) names.add(areaPathOf(village)[path.length]);
  }
  return [...names]
    .map((name) => summarize(data, [...path, name], warnings))
    .sort((a, b) => b.farmers - a.farmers || a.name.localeCompare(b.name));
}

// ---------- warnings ----------

function formatShortDate(isoDate: string): string {
  return formatDate(isoDate).replace(/ \d{4}$/, "");
}

/** "12–26 Sep", "28 Aug – 3 Sep", "12 Sep" (no year). */
function formatRange(first: string, last: string): string {
  if (first === last) return formatShortDate(first);
  const [, m1] = first.split("-");
  const [, m2] = last.split("-");
  if (first.slice(0, 4) === last.slice(0, 4) && m1 === m2) {
    return `${Number(first.split("-")[2])}–${formatShortDate(last)}`;
  }
  return `${formatShortDate(first)} – ${formatShortDate(last)}`;
}

function problemWarnings(data: DashboardData): Warning[] {
  const windowStart = addDays(data.today, -(PROBLEM_WINDOW_DAYS - 1));
  const baselineStart = addDays(windowStart, -PROBLEM_BASELINE_WEEKS * 7);
  const villageById = new Map(data.villages.map((v) => [v.id, v]));

  const groups = new Map<string, { parish: AreaPath; problem: string; recent: ProblemReport[]; baseline: Set<number> }>();
  for (const report of data.problems) {
    const village = villageById.get(report.villageId);
    if (!village || report.date < baselineStart || report.date > data.today) continue;
    const parish = areaPathOf(village).slice(0, 3);
    const key = `${parish.join("/")}:${report.problem}`;
    const group = groups.get(key) ?? { parish, problem: report.problem, recent: [], baseline: new Set<number>() };
    if (report.date >= windowStart) group.recent.push(report);
    else group.baseline.add(report.farmerId);
    groups.set(key, group);
  }

  const warnings: Warning[] = [];
  for (const [key, group] of groups) {
    const farmerIds = new Set(group.recent.map((r) => r.farmerId));
    if (farmerIds.size < PROBLEM_MIN_FARMERS || farmerIds.size <= group.baseline.size) continue;
    const dates = group.recent.map((r) => r.date).sort();
    const reporting = [...new Set(group.recent.map((r) => r.villageId))]
      .map((id) => villageById.get(id))
      .filter((v): v is Village => v !== undefined);
    const parishName = group.parish[2];
    const dateRange = formatRange(dates[0], dates[dates.length - 1]);
    warnings.push({
      id: `problem:${key}`,
      kind: "problem",
      severity: "high",
      path: group.parish,
      level: "parish",
      areaName: parishName,
      title: labelProblem(group.problem),
      detail: [
        `${farmerIds.size} ${farmerIds.size === 1 ? "farm" : "farms"}`,
        `${parishName} parish`,
        dateRange,
        group.baseline.size === 0 ? "none before" : `${group.baseline.size} before`,
      ].join(" · "),
      farms: farmerIds.size,
      place: `${parishName} parish`,
      dateRange,
      ...centreOf(reporting),
    });
  }
  return warnings;
}

function priceWarnings(data: DashboardData): Warning[] {
  const warnings: Warning[] = [];
  for (const [district, { index, sales, farms }] of districtPriceIndexes(data)) {
    if (index === null || !isLowIndex(index)) continue;
    warnings.push({
      id: `price:${district}`,
      kind: "price",
      severity: "medium",
      path: [district],
      level: "district",
      areaName: district,
      title: `Low prices in ${district}`,
      detail: `${formatIndex(index)} vs national · ${sales} sales · ${farms} farms · ${PRICE_WINDOW_DAYS} days`,
      farms,
      place: district,
      ...centreOf(data.villages.filter((v) => v.district === district)),
    });
  }
  return warnings;
}

export function computeWarnings(data: DashboardData): Warning[] {
  const severityRank = { high: 0, medium: 1 };
  return [...problemWarnings(data), ...priceWarnings(data)].sort(
    (a, b) => severityRank[a.severity] - severityRank[b.severity] || a.id.localeCompare(b.id),
  );
}

// ---------- KPIs and farmer rows ----------

export function kpis(data: DashboardData, warnings?: Warning[]): Kpis {
  const villageIds = new Set(data.farmers.map((f) => f.villageId));
  const farmedVillages = data.villages.filter((v) => villageIds.has(v.id));
  const recentSales = data.sales.filter((s) => inWindow(s.date, data.today, PRICE_WINDOW_DAYS));
  const prevEnd = addDays(data.today, -KPI_WINDOW_DAYS);
  return {
    farmers: data.farmers.length,
    districts: new Set(farmedVillages.map((v) => v.district)).size,
    villages: farmedVillages.length,
    newFarmers30d: data.farmers.filter((f) => inWindow(f.registeredOn, data.today, KPI_WINDOW_DAYS)).length,
    newFarmersPrev30d: data.farmers.filter((f) => inWindow(f.registeredOn, prevEnd, KPI_WINDOW_DAYS)).length,
    callsLast30d: data.callsLast30d,
    callsPrev30d: data.callsPrev30d ?? 0,
    priceIndex: medianIndex(recentSales, data.reference),
    activeWarnings: (warnings ?? computeWarnings(data)).length,
  };
}

function toFarmerRow(farmer: Farmer, village: Village, data: DashboardData, villageSales: Sale[]): FarmerRow {
  const own = data.sales.filter((s) => s.farmerId === farmer.id).sort((a, b) => b.date.localeCompare(a.date));
  const last = own[0];
  const formSales = last ? villageSales.filter((s) => s.form === last.form) : [];
  return {
    id: farmer.id,
    firstName: farmer.firstName,
    village: village.village,
    registeredAt: farmer.registeredAt,
    callCount: farmer.callCount,
    lastCallAt: farmer.lastCallAt,
    lastSale: last ? { date: last.date, form: last.form, ugxPerKg: last.ugxPerKg, buyerType: last.buyerType } : null,
    villageMedian: last ? medianPrice(formSales) : null,
    lastSaleVsVillage: last ? indexVsVillage(last, medianIndex(formSales, data.reference), data.reference) : null,
    problems: [
      ...new Set(
        data.problems
          .filter((p) => p.farmerId === farmer.id && inWindow(p.date, data.today, PROBLEM_LOOKBACK_DAYS))
          .map((p) => p.problem),
      ),
    ],
    isSynthetic: farmer.isSynthetic,
  };
}

export function farmersIn(data: DashboardData, path: AreaPath): FarmerRow[] {
  const village = data.villages.find((v) => inArea(v, path));
  if (!village) return [];
  const villageSales = yearSales(
    data.sales.filter((s) => s.villageId === village.id),
    data.today,
  );
  return data.farmers
    .filter((f) => f.villageId === village.id)
    .map((f) => toFarmerRow(f, village, data, villageSales))
    .sort((a, b) => (b.lastCallAt ?? "").localeCompare(a.lastCallAt ?? ""));
}
