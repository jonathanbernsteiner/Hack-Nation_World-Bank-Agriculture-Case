import { describe, expect, it } from "vitest";
import { farmerDetail } from "./farmerDetail";
import type { DashboardData, Farmer, Sale, Village } from "./types";

const village: Village = {
  id: 1, region: "Central", district: "Masaka", subCounty: "Kyanamukaaka", parish: "Kasaali", village: "Kasaali A",
  lat: 0, lon: 31, coffeeType: "robusta", isVerified: true, isSynthetic: false,
};
const farmer = (id: number): Farmer => ({
  id, firstName: `F${id}`, villageId: 1, registeredAt: "2026-09-01T08:00:00Z", registeredOn: "2026-09-01", callCount: 2,
  lastCallAt: "2026-09-20T08:00:00Z", lastCallOn: "2026-09-20", isSynthetic: false,
});
const sale = (farmerId: number, ugxPerKg: number, date = "2026-09-10"): Sale => ({
  farmerId, villageId: 1, date, form: "faq", ugxPerKg, kg: 10, buyerType: "middleman",
});
const base: DashboardData = {
  today: "2026-10-03", villages: [village], farmers: [farmer(1), farmer(2), farmer(3), farmer(4)], sales: [], problems: [],
  reference: [
    { month: "2026-06", kiboko: 3000, faq: 10000, parchment: 9000, source: "test" },
    { month: "2026-09", kiboko: 3000, faq: 5000, parchment: 9000, source: "test" },
  ],
  callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
};

describe("farmerDetail", () => {
  it("returns null for an unknown farmer", () => {
    expect(farmerDetail(base, 99)).toBeNull();
  });

  it("sorts sales newest first and computes indexes and problems", () => {
    const data: DashboardData = {
      ...base,
      sales: [sale(1, 4000, "2026-09-01"), sale(1, 4500, "2026-09-10"), sale(2, 5000), sale(3, 6000)],
      problems: [
        { farmerId: 1, villageId: 1, date: "2026-08-01", problem: "wilting" },
        { farmerId: 1, villageId: 1, date: "2026-09-05", problem: "coffee_leaf_rust" },
      ],
    };
    const d = farmerDetail(data, 1);
    expect(d?.sales.map((s) => s.date)).toEqual(["2026-09-10", "2026-09-01"]);
    expect(d?.sales[0].indexVsNational).toBeCloseTo(0.9);
    expect(d?.villageMedianByForm.faq).toBe(4750);
    expect(d?.sales[0].indexVsVillage).toBeCloseTo(4500 / 4750);
    expect(d?.problems.map((p) => p.problem)).toEqual(["coffee_leaf_rust", "wilting"]);
    expect(d?.lastSaleVsVillage).toBeCloseTo(4500 / 4750);
    expect(d?.mainBuyer).toBe("middleman");
  });

  it("compares the last sale with the village month-aware", () => {
    const data: DashboardData = {
      ...base,
      sales: [sale(1, 10000, "2026-06-10"), sale(2, 10000, "2026-06-11"), sale(3, 10000, "2026-06-12"), sale(4, 5000)],
    };
    expect(farmerDetail(data, 4)?.lastSaleVsVillage).toBeCloseTo(1); // not 5000 / 10000
    expect(farmerDetail(data, 4)?.sales[0].villageMedian).toBe(10000); // UGX median stays for display
  });
});
