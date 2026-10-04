import { describe, expect, it } from "vitest";
import { buyerComparison, districtPrices } from "./prices";
import type { BuyerType, DashboardData, Sale, Village } from "./types";

const reference = [{ month: "2026-09", kiboko: 5000, faq: 10000, parchment: 15000, source: "t" }];

const village: Village = {
  id: 1, region: "Central", district: "Kayunga", subCounty: "S", parish: "P", village: "V",
  lat: 0, lon: 32, coffeeType: "robusta", isVerified: true, isSynthetic: false,
};

const sale = (farmerId: number, ugxPerKg: number, buyerType: BuyerType): Sale => ({
  farmerId, villageId: 1, date: "2026-09-10", form: "faq", ugxPerKg, kg: 100, buyerType,
});

const makeData = (sales: Sale[]): DashboardData => ({
  today: "2026-09-30", villages: [village], farmers: [], sales, problems: [],
  reference, callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
});

describe("prices", () => {
  it("gates medians on 3 sales from 3 farmers", () => {
    const two = makeData([sale(1, 8000, "middleman"), sale(2, 8000, "middleman")]);
    expect(districtPrices(two)[0].index).toBeNull();
    const enough = makeData([1, 2, 3].map((f) => sale(f, 8000, "middleman")));
    expect(districtPrices(enough)[0].index).toBeCloseTo(0.8);
  });

  it("gap sign follows cooperative minus middleman", () => {
    const sales = [1, 2, 3].map((f) => sale(f, 8000, "middleman")).concat([4, 5, 6].map((f) => sale(f, 9400, "cooperative")));
    expect(buyerComparison(makeData(sales)).gapPct).toBe(14);
    const reversed = [1, 2, 3].map((f) => sale(f, 9400, "middleman")).concat([4, 5, 6].map((f) => sale(f, 8000, "cooperative")));
    expect(buyerComparison(makeData(reversed)).gapPct).toBe(-14);
  });

  it("flags districts at or below the low index", () => {
    const low = makeData([1, 2, 3].map((f) => sale(f, 8500, "middleman")));
    expect(districtPrices(low)[0].low).toBe(true);
    const fine = makeData([1, 2, 3].map((f) => sale(f, 9500, "middleman")));
    expect(districtPrices(fine)[0].low).toBe(false);
  });
});
