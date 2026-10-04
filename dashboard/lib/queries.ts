import fs from "node:fs";
import path from "node:path";
import { getSql } from "./db";
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

function num(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toIso(value: unknown): string {
  return value instanceof Date ? value.toISOString() : String(value);
}

function kampalaToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Africa/Kampala" }).format(new Date());
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

export async function loadDashboardData(): Promise<DashboardData> {
  const sql = getSql();

  const [villageRows, farmerRows, saleRows, problemRows, callRows] = await Promise.all([
    sql`select id, region, district, sub_county, parish, village, lat, lon, coffee_type, is_verified, is_synthetic
        from villages`,
    // Registration = the farmer's first call; created_at is the load time for seeded rows.
    sql`select f.id, f.name, f.village_id, least(f.created_at, min(c.received_at)) as created_at, f.is_synthetic,
               count(c.id)::int as call_count, max(c.received_at) as last_call_at
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
    sql`select count(*)::int as total,
               count(*) filter (where received_at >= now() - interval '30 days')::int as last30
        from calls`,
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
    firstName: String(r.name ?? "").trim().split(/\s+/)[0] ?? "",
    villageId: Number(r.village_id),
    registeredAt: toIso(r.created_at),
    callCount: Number(r.call_count),
    lastCallAt: r.last_call_at ? toIso(r.last_call_at) : null,
    isSynthetic: Boolean(r.is_synthetic),
  }));

  const sales: Sale[] = saleRows
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

  const problems: ProblemReport[] = problemRows.map((r) => ({
    farmerId: Number(r.farmer_id),
    villageId: Number(r.village_id),
    date: String(r.d),
    problem: String(r.problem),
  }));

  return {
    today: kampalaToday(),
    villages,
    farmers,
    sales,
    problems,
    reference: readReference(),
    callsLast30d: Number(callRows[0]?.last30 ?? 0),
    callsTotal: Number(callRows[0]?.total ?? 0),
    hasSynthetic: villages.some((v) => v.isSynthetic) || farmers.some((f) => f.isSynthetic),
  };
}
