// Shared contract between the data layer (lib/queries.ts, lib/aggregate.ts) and the UI
// (components/*). Change it only together with every user.

export type CoffeeForm = "kiboko" | "faq" | "parchment";
export type BuyerType = "middleman" | "cooperative" | "other";
export type CoffeeType = "robusta" | "arabica";

/** Drill-down levels. An area is addressed by its path of names below the country:
 *  []                                  → Uganda (country)
 *  [district]                          → district
 *  [district, subCounty]               → sub-county
 *  [district, subCounty, parish]       → parish
 *  [district, subCounty, parish, village] → village (farmers listed here)
 *  Village names are unique within a parish (DB constraint), so a path is unique. */
export type Level = "country" | "district" | "sub_county" | "parish" | "village";
export type AreaPath = string[];
export const LEVELS: Level[] = ["country", "district", "sub_county", "parish", "village"];

export type MapLayer = "farmers" | "prices" | "warnings";

// ---- Raw rows loaded once on the server (lib/queries.ts) and passed to the client ----

export interface Village {
  id: number;
  region: string; // UBOS region: Central | Eastern | Northern | Western
  district: string;
  subCounty: string;
  parish: string;
  village: string;
  lat: number | null;
  lon: number | null;
  coffeeType: CoffeeType | null;
  isVerified: boolean; // false = village named by a caller, position falls back to the district centre
  isSynthetic: boolean;
}

export interface Farmer {
  id: number;
  firstName: string; // first name only; PINs and phone numbers never leave the database
  villageId: number;
  registeredAt: string; // ISO timestamp
  callCount: number;
  lastCallAt: string | null; // ISO timestamp
  isSynthetic: boolean;
}

export interface Sale {
  farmerId: number;
  villageId: number;
  date: string; // YYYY-MM-DD (Kampala)
  form: CoffeeForm;
  ugxPerKg: number;
  kg: number;
  buyerType: BuyerType | null;
}

export interface ProblemReport {
  farmerId: number;
  villageId: number;
  date: string; // YYYY-MM-DD (Kampala)
  problem: string; // likely_disease id (e.g. "black_coffee_twig_borer") or the symptom when no disease was named
}

/** National monthly farm-gate reference (UCDA / MAAIF Coffee Department), UGX/kg. */
export interface ReferencePrice {
  month: string; // YYYY-MM
  kiboko: number;
  faq: number;
  parchment: number;
  source: string;
}

export interface DashboardData {
  today: string; // YYYY-MM-DD in Africa/Kampala; every time window is relative to this
  villages: Village[];
  farmers: Farmer[];
  sales: Sale[];
  problems: ProblemReport[];
  reference: ReferencePrice[];
  callsLast30d: number;
  callsTotal: number;
  hasSynthetic: boolean;
}

// ---- Aggregates computed by lib/aggregate.ts (pure functions, run in the browser) ----

export interface FormPrice {
  form: CoffeeForm;
  median: number | null; // UGX/kg, last 12 months; null when < MIN_SALES sales or < MIN_FARMERS farmers
  national: number | null; // latest national reference for this form
  sales: number;
}

export interface BuyerPrice {
  buyer: BuyerType;
  priceIndex: number | null; // median of (sale price / national reference same month+form); 1.0 = national
  sales: number;
}

export interface MonthlyPoint {
  month: string; // YYYY-MM
  median: number | null; // area median for `form` that month (no minimum; chart only)
  national: number | null;
}

export interface Warning {
  id: string; // stable key
  kind: "problem" | "price";
  severity: "high" | "medium";
  path: AreaPath; // the parish (problem) or district (price) it is about
  level: Level;
  areaName: string;
  title: string; // e.g. "Black coffee twig borer: 3 farms in Kasaali parish"
  detail: string; // e.g. "Reported 12–26 Sep 2026 · none in the 12 weeks before"
  lat: number;
  lon: number;
}

export interface AreaSummary {
  path: AreaPath;
  level: Level;
  name: string; // "Uganda", district name, ..., village name
  region: string | null; // region of the area (null at country level)
  lat: number; // mean of its villages' coordinates
  lon: number;
  villages: number;
  farmers: number;
  newFarmers90d: number;
  calls: number; // total calls by its farmers
  priceIndex: number | null; // last 12 months, all forms; null below the minimums
  priceByForm: FormPrice[]; // always all three forms, in order kiboko, faq, parchment
  priceByBuyer: BuyerPrice[]; // middleman, cooperative, other
  mainForm: CoffeeForm | null; // form with the most sales in the area
  monthly: MonthlyPoint[]; // last 12 months for mainForm
  problems90d: { problem: string; farmers: number }[]; // distinct farmers per problem, last 90 days, most first
  warnings: Warning[]; // active warnings inside this area
  isSynthetic: boolean; // true when every farmer in the area is synthetic
}

export interface FarmerRow {
  id: number;
  firstName: string;
  village: string;
  registeredAt: string;
  callCount: number;
  lastCallAt: string | null;
  lastSale: { date: string; form: CoffeeForm; ugxPerKg: number; buyerType: BuyerType | null } | null;
  villageMedian: number | null; // village median for lastSale.form (null below the minimums)
  problems: string[]; // problems reported in the last 90 days
  isSynthetic: boolean;
}

export interface Kpis {
  farmers: number;
  districts: number;
  villages: number;
  newFarmers30d: number;
  callsLast30d: number;
  priceIndex: number | null; // national median price index, last 90 days
  activeWarnings: number;
}

/** Weather route contract: GET /api/weather?lat=..&lon=.. */
export interface WeatherDay {
  date: string; // YYYY-MM-DD
  tMaxC: number | null;
  tMinC: number | null;
  rainMm: number | null;
  rainChancePct: number | null;
}
export interface WeatherResponse {
  days: WeatherDay[]; // next 3 days; empty when Open-Meteo is unreachable
  source: string; // "Open-Meteo (CC BY 4.0)"
}

// Named thresholds (shown in the UI legend so the rules stay explainable)
export const MIN_SALES = 3; // a median needs at least 3 sales ...
export const MIN_FARMERS = 3; // ... from at least 3 different farmers
export const PROBLEM_WINDOW_DAYS = 30; // problem warning: same problem, same parish, within 30 days
export const PROBLEM_MIN_FARMERS = 3; // ... reported by at least 3 different farmers
export const PROBLEM_BASELINE_WEEKS = 12; // "unusual": at most 1 such report in the 12 weeks before
export const PRICE_WINDOW_DAYS = 90; // price warning: district median over the last 90 days ...
export const PRICE_LOW_INDEX = 0.85; // ... at least 15% below the national reference
