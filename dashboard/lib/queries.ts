import { cache } from "react";
import fs from "node:fs";
import path from "node:path";
import { referenceFor } from "./aggregate";
import { getSql } from "./db";
import { OUTLIER_MAX_RATIO, OUTLIER_MIN_RATIO } from "./types";
import type {
  BuyerType,
  CoffeeForm,
  CoffeeType,
  DashboardData,
  Farmer,
  ProblemReport,
  ReferencePrice,
  Sale,
  Village,
} from "./types";

const COFFEE_FORMS: CoffeeForm[] = ["kiboko", "faq", "parchment"];
const KAMPALA_TZ = "Africa/Kampala";
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const CALL_WINDOW_DAYS = 30;

function num(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toIso(value: unknown): string {
  return value instanceof Date ? value.toISOString() : String(value);
}

/** Calendar date (YYYY-MM-DD) of `now` in Kampala. */
export function kampalaDate(now: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: KAMPALA_TZ }).format(now);
}

/** Parses DASHBOARD_AS_OF. Unset or blank → null; anything but a real YYYY-MM-DD date throws. */
export function parseAsOf(value: string | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  if (trimmed === "") return null;
  const match = ISO_DATE.exec(trimmed);
  const [y, m, d] = match ? match.slice(1).map(Number) : [];
  const isRealDate = match !== null && new Date(Date.UTC(y, m - 1, d)).toISOString().slice(0, 10) === trimmed;
  if (!isRealDate) {
    throw new Error(`DASHBOARD_AS_OF must be a date as YYYY-MM-DD (e.g. 2026-10-04), got "${trimmed}".`);
  }
  return trimmed;
}

/** The dashboard's "today": DASHBOARD_AS_OF when set (pins the demo date), else today in Kampala. */
export function dashboardToday(asOf: string | undefined = process.env.DASHBOARD_AS_OF, now: Date = new Date()): string {
  return parseAsOf(asOf) ?? kampalaDate(now);
}

/** Drops sales priced below OUTLIER_MIN_RATIO or above OUTLIER_MAX_RATIO times the national reference for
 *  their month and form (typos such as 58,500 for 5,850). Sales without a reference are kept. Pure. */
export function dropOutlierSales(sales: Sale[], reference: ReferencePrice[]): Sale[] {
  return sales.filter((sale) => {
    const ref = referenceFor(reference, sale.form, sale.date.slice(0, 7));
    if (ref === null || ref <= 0) return true;
    const ratio = sale.ugxPerKg / ref;
    return ratio >= OUTLIER_MIN_RATIO && ratio <= OUTLIER_MAX_RATIO;
  });
}

function toBuyer(value: unknown): BuyerType | null {
  if (value === null || value === undefined) return null;
  if (value === "middleman" || value === "cooperative") return value;
  return "other";
}

/** Reads the national reference CSV; lines starting with '#' are comments. */
export function readReference(): ReferencePrice[] {
  const file = path.join(process.cwd(), "data", "price_reference.csv");
  const lines = fs
    .readFileSync(file, "utf8")
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "" && !line.startsWith("#"));
  return lines
    .slice(1) // header: month,kiboko,faq,parchment,drugar,source
    .map((line) => {
      const [month, kiboko, faq, parchment, , ...source] = line.split(",");
      return {
        month,
        kiboko: Number(kiboko),
        faq: Number(faq),
        parchment: Number(parchment),
        source: source.join(",").trim(),
      };
    })
    .filter((r) => /^\d{4}-\d{2}$/.test(r.month) && [r.kiboko, r.faq, r.parchment].every(Number.isFinite));
}

async function loadDashboardDataUncached(): Promise<DashboardData> {
  const sql = getSql();
  const today = dashboardToday();
  const reference = readReference();

  const [villageRows, farmerRows, saleRows, problemRows, callRows] = await Promise.all([
    sql`select id, region, district, sub_county, parish, village, lat, lon, coffee_type, is_verified, is_synthetic
        from villages`,
    // Registration = the farmer's first call; created_at is the load time for seeded rows.
    // *_on columns are Kampala calendar dates for day windows; the timestamps stay for display.
    sql`select f.id, f.name, f.village_id, least(f.created_at, min(c.received_at)) as created_at, f.is_synthetic,
               to_char((least(f.created_at, min(c.received_at)) at time zone 'Africa/Kampala')::date, 'YYYY-MM-DD')
                 as registered_on,
               count(c.id)::int as call_count, max(c.received_at) as last_call_at,
               to_char((max(c.received_at) at time zone 'Africa/Kampala')::date, 'YYYY-MM-DD') as last_call_on
        from farmers f left join calls c on c.farmer_id = f.id
        where f.village_id is not null
        group by f.id`,
    sql`select s.farmer_id, s.village_id, to_char(s.sale_date, 'YYYY-MM-DD') as sale_date,
               s.coffee_form, s.ugx_per_kg, s.amount_kg, e.buyer_type
        from coffee_sale_prices s join entries e on e.id = s.entry_id
        where s.coffee_form in ('kiboko', 'faq', 'parchment') and s.village_id is not null`,
    sql`select e.farmer_id, f.village_id,
               to_char((c.received_at at time zone 'Africa/Kampala')::date, 'YYYY-MM-DD') as d,
               coalesce(e.likely_disease, e.symptom) as problem
        from entries e
        join calls c on c.id = e.call_id
        join farmers f on f.id = e.farmer_id
        where e.kind = 'observation' and f.village_id is not null
          and coalesce(e.likely_disease, e.symptom) is not null
          and coalesce(e.confidence, 1) >= 0.6 and e.quote_verified is not false`,
    // Calls per Kampala calendar day: last30 = the 30 days ending `today` (inclusive), prev30 = the 30 before.
    sql`select count(*)::int as total,
               count(*) filter (where d between ${today}::date - ${CALL_WINDOW_DAYS - 1}::int and ${today}::date)::int
                 as last30,
               count(*) filter (where d between ${today}::date - ${2 * CALL_WINDOW_DAYS - 1}::int
                                          and ${today}::date - ${CALL_WINDOW_DAYS}::int)::int as prev30
        from (select (received_at at time zone 'Africa/Kampala')::date as d from calls) c`,
  ]);

  const villages: Village[] = villageRows.map((r) => ({
    id: Number(r.id),
    region: String(r.region ?? ""),
    district: String(r.district),
    subCounty: String(r.sub_county),
    parish: String(r.parish),
    village: String(r.village),
    lat: num(r.lat),
    lon: num(r.lon),
    coffeeType: (r.coffee_type as CoffeeType | null) ?? null,
    isVerified: Boolean(r.is_verified),
    isSynthetic: Boolean(r.is_synthetic),
  }));

  const farmers: Farmer[] = farmerRows.map((r) => ({
    id: Number(r.id),
    name: String(r.name ?? "").trim(),
    firstName: String(r.name ?? "").trim().split(/\s+/)[0] ?? "",
    villageId: Number(r.village_id),
    registeredAt: toIso(r.created_at),
    registeredOn: String(r.registered_on),
    callCount: Number(r.call_count),
    lastCallAt: r.last_call_at ? toIso(r.last_call_at) : null,
    lastCallOn: r.last_call_on ? String(r.last_call_on) : null,
    isSynthetic: Boolean(r.is_synthetic),
  }));

  const parsedSales: Sale[] = saleRows
    .filter((r) => num(r.ugx_per_kg) !== null && COFFEE_FORMS.includes(r.coffee_form as CoffeeForm))
    .map((r) => ({
      farmerId: Number(r.farmer_id),
      villageId: Number(r.village_id),
      date: String(r.sale_date),
      form: r.coffee_form as CoffeeForm,
      ugxPerKg: Number(r.ugx_per_kg),
      kg: num(r.amount_kg) ?? 0,
      buyerType: toBuyer(r.buyer_type),
    }));
  const sales = dropOutlierSales(parsedSales, reference);

  const problems: ProblemReport[] = problemRows.map((r) => ({
    farmerId: Number(r.farmer_id),
    villageId: Number(r.village_id),
    date: String(r.d),
    problem: String(r.problem),
  }));

  return {
    today,
    villages,
    farmers,
    sales,
    problems,
    reference,
    callsLast30d: Number(callRows[0]?.last30 ?? 0),
    callsPrev30d: Number(callRows[0]?.prev30 ?? 0),
    callsTotal: Number(callRows[0]?.total ?? 0),
    hasSynthetic: villages.some((v) => v.isSynthetic) || farmers.some((f) => f.isSynthetic),
  };
}

/** One load per request: every server component calling this shares the result. */
export const loadDashboardData = cache(loadDashboardDataUncached);
