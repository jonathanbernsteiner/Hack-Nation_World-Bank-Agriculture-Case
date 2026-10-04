import { describe, expect, it } from "vitest";
import { registryRows } from "./registry";
import type { DashboardData, Farmer, ReferencePrice, Sale, Village } from "./types";

const village: Village = {
  id: 1, region: "Central", district: "Masaka", subCounty: "Kyanamukaaka", parish: "Kasaali", village: "Kasaali A",
  lat: 0, lon: 31, coffeeType: "robusta", isVerified: true, isSynthetic: false,
};
const farmer = (id: number, registeredAt: string): Farmer => ({
  id, firstName: `F${id}`, villageId: 1, registeredAt, registeredOn: registeredAt.slice(0, 10), callCount: 1,
  lastCallAt: registeredAt, lastCallOn: registeredAt.slice(0, 10), isSynthetic: false,
});
const sale = (farmerId: number, ugxPerKg: number, date = "2026-09-10"): Sale => ({
  farmerId, villageId: 1, date, form: "faq", ugxPerKg, kg: 10, buyerType: "middleman",
});
const reference: ReferencePrice[] = [
  { month: "2026-06", kiboko: 3000, faq: 10000, parchment: 9000, source: "t" },
  { month: "2026-09", kiboko: 3000, faq: 5000, parchment: 9000, source: "t" },
];
const base: DashboardData = {
  today: "2026-10-03", villages: [village], farmers: [], sales: [], problems: [], reference,
  callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
};

describe("registryRows", () => {
  it("sorts by registeredAt descending", () => {
    const rows = registryRows({ ...base, farmers: [farmer(1, "2026-09-01T08:00:00Z"), farmer(2, "2026-09-20T08:00:00Z")] });
    expect(rows.map((r) => r.id)).toEqual([2, 1]);
  });

  it("computes price vs village when minimums are met", () => {
    const farmers = [1, 2, 3].map((id) => farmer(id, "2026-09-01T08:00:00Z"));
    const sales = [sale(1, 4000), sale(2, 5000), sale(3, 6000)];
    const rows = registryRows({ ...base, farmers, sales });
    expect(rows.find((r) => r.id === 3)?.priceVsVillage).toBeCloseTo(1.2);
  });

  it("is month-aware: the last sale's index vs the village median index", () => {
    // June reference 10000, September 5000. Everyone was paid exactly the national price.
    const farmers = [1, 2, 3, 4].map((id) => farmer(id, "2026-05-01T08:00:00Z"));
    const sales = [sale(1, 10000, "2026-06-10"), sale(2, 10000, "2026-06-11"), sale(3, 10000, "2026-06-12"), sale(4, 5000)];
    const row = registryRows({ ...base, farmers, sales }).find((r) => r.id === 4);
    // a plain UGX comparison would say 5000 / 10000 = −50%
    expect(row?.priceVsVillage).toBeCloseTo(1);
  });

  it("returns null price index below the minimums", () => {
    const rows = registryRows({ ...base, farmers: [farmer(1, "2026-09-01T08:00:00Z")], sales: [sale(1, 4000)] });
    expect(rows[0].priceVsVillage).toBeNull();
    expect(rows[0].lastSale?.ugxPerKg).toBe(4000);
  });
});
