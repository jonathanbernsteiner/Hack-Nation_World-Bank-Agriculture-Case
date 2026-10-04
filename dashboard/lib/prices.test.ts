import { describe, expect, it } from "vitest";
import { childrenOf, computeWarnings, districtPriceIndexes, farmersIn, kpis, summarize } from "./aggregate";
import { farmerDetail } from "./farmerDetail";
import { buyerComparison, districtPrices, monthlyByBuyer } from "./prices";
import { registryRows } from "./registry";
import type { BuyerType, DashboardData, Farmer, Sale, Village } from "./types";

const reference = [
  { month: "2026-08", kiboko: 5000, faq: 8000, parchment: 15000, source: "t" },
  { month: "2026-09", kiboko: 5000, faq: 10000, parchment: 15000, source: "t" },
];

const village: Village = {
  id: 1, region: "Central", district: "Kayunga", subCounty: "S", parish: "P", village: "V",
  lat: 0, lon: 32, coffeeType: "robusta", isVerified: true, isSynthetic: false,
};

const sale = (farmerId: number, ugxPerKg: number, buyerType: BuyerType, date = "2026-09-10"): Sale => ({
  farmerId, villageId: 1, date, form: "faq", ugxPerKg, kg: 100, buyerType,
});

const makeData = (sales: Sale[], farmers: Farmer[] = []): DashboardData => ({
  today: "2026-09-30", villages: [village], farmers, sales, problems: [],
  reference, callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
});

/** 2 sales each from farmers 1..n, all at `price` in September. */
const twoEach = (n: number, price: number, buyer: BuyerType = "middleman") =>
  Array.from({ length: n }, (_, i) => i + 1).flatMap((f) => [sale(f, price, buyer), sale(f, price, buyer, "2026-09-11")]);

describe("prices", () => {
  it("gates the 90-day district index on 10 sales from 5 farmers", () => {
    expect(districtPrices(makeData(twoEach(4, 8000)))[0].index90d).toBeNull();
    expect(districtPrices(makeData(twoEach(5, 8000)))[0].index90d).toBeCloseTo(0.8);
  });

  it("gap is middleman index over cooperative index minus 1", () => {
    const sales = [1, 2, 3].map((f) => sale(f, 8000, "middleman")).concat([4, 5, 6].map((f) => sale(f, 9400, "cooperative")));
    expect(buyerComparison(makeData(sales)).gapPct).toBe(-15);
    const reversed = [1, 2, 3].map((f) => sale(f, 9600, "middleman")).concat([4, 5, 6].map((f) => sale(f, 8000, "cooperative")));
    expect(buyerComparison(makeData(reversed)).gapPct).toBe(20);
  });

  it("flags districts at or below the low index (rounded −15%)", () => {
    expect(districtPrices(makeData(twoEach(5, 8500)))[0].low).toBe(true);
    expect(districtPrices(makeData(twoEach(5, 8549)))[0].low).toBe(true); // −15% after rounding
    expect(districtPrices(makeData(twoEach(5, 8551)))[0].low).toBe(false); // −14%
  });

  it("monthly chart points need at least 2 sales", () => {
    const sales = [sale(1, 9000, "middleman"), sale(2, 9400, "middleman"), sale(3, 9000, "cooperative")];
    const sep = monthlyByBuyer(makeData(sales), "faq").find((p) => p.month === "2026-09");
    expect(sep).toMatchObject({ middleman: 9200, cooperative: null, all: 9000 });
  });
});

describe("all pages agree on one fixture", () => {
  // One sale per farmer, all inside 90 days, so the 90-day, 12-month and per-farmer metrics see the same sales.
  // August reference 8000, September 10000: indexes 0.8 (Aug) and 0.75..0.9 (Sep).
  const farmers: Farmer[] = Array.from({ length: 12 }, (_, i) => ({
    id: i + 1, name: `F${i + 1}`, firstName: `F${i + 1}`, villageId: 1, registeredAt: "2026-07-01T08:00:00Z", registeredOn: "2026-07-01",
    callCount: 1, lastCallAt: "2026-09-01T08:00:00Z", lastCallOn: "2026-09-01", isSynthetic: false,
  }));
  const sales: Sale[] = [
    ...[1, 2, 3, 4].map((f) => sale(f, 6400, "middleman", "2026-08-20")),
    ...[5, 6, 7, 8].map((f, i) => sale(f, 7500 + i * 500, "middleman")),
    ...[9, 10, 11, 12].map((f) => sale(f, 9000, "cooperative")),
    sale(1, 100, "middleman", "2026-10-02"), // after today: every page must ignore it
  ];
  const data = makeData(sales, farmers);
  const warnings = computeWarnings(data);

  it("district index: warning, Prices table, map summary and district table agree", () => {
    const fromAggregate = districtPriceIndexes(data).get("Kayunga")?.index ?? null;
    const row = districtPrices(data)[0];
    const district = summarize(data, ["Kayunga"], warnings);
    expect(fromAggregate).not.toBeNull();
    expect(row.index90d).toBe(fromAggregate);
    expect(district.priceIndex).toBe(fromAggregate);
    expect(childrenOf(data, [], warnings)[0].priceIndex).toBe(fromAggregate);
    expect(district.priceByForm.find((f) => f.form === "faq")?.index).toBe(fromAggregate);
    expect(row.low).toBe(warnings.some((w) => w.id === "price:Kayunga"));
    expect(kpis(data, warnings).priceIndex).toBe(fromAggregate);
  });

  it("buyer index: map panel and Prices page agree", () => {
    const panel = summarize(data, [], warnings).priceByBuyer;
    const page = buyerComparison(data).rows;
    for (const buyer of ["middleman", "cooperative", "other"] as const) {
      expect(page.find((r) => r.buyer === buyer)?.index).toBe(panel.find((b) => b.buyer === buyer)?.priceIndex);
    }
  });

  it("vs village: Farmers list, farmer peek and map farmer rows agree", () => {
    const registry = registryRows(data);
    const mapRows = farmersIn(data, ["Kayunga", "S", "P", "V"]);
    for (const id of [2, 5, 9]) {
      const listed = registry.find((r) => r.id === id)?.priceVsVillage;
      expect(listed).not.toBeNull();
      expect(farmerDetail(data, id)?.lastSaleVsVillage).toBe(listed);
      expect(mapRows.find((r) => r.id === id)?.lastSaleVsVillage).toBe(listed);
    }
  });
});
