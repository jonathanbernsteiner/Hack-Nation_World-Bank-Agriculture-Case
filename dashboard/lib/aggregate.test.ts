import { describe, expect, it } from "vitest";
import {
  computeWarnings,
  inWindow,
  isLowIndex,
  kpis,
  median,
  referenceAsOf,
  referenceFor,
  saleIndex,
  summarize,
} from "./aggregate";
import type { DashboardData, Farmer, ProblemReport, ReferencePrice, Sale, Village } from "./types";

const reference: ReferencePrice[] = [
  { month: "2026-07", kiboko: 5000, faq: 10000, parchment: 15000, source: "t" },
  { month: "2026-09", kiboko: 5000, faq: 10000, parchment: 15000, source: "t" },
];

const village = (id: number, district: string, parish = "P1"): Village => ({
  id, region: "Central", district, subCounty: "S1", parish, village: `V${id}`,
  lat: 0.5, lon: 32, coffeeType: "robusta", isVerified: true, isSynthetic: false,
});

const sale = (farmerId: number, villageId: number, ugxPerKg: number, date = "2026-09-10"): Sale => ({
  farmerId, villageId, date, form: "faq", ugxPerKg, kg: 100, buyerType: "middleman",
});

const report = (farmerId: number, date: string, villageId = 1): ProblemReport => ({
  farmerId, villageId, date, problem: "coffee_leaf_rust",
});

const farmer = (id: number, registeredOn: string): Farmer => ({
  id, firstName: `F${id}`, villageId: 1, registeredAt: `${registeredOn}T08:00:00Z`, registeredOn,
  callCount: 1, lastCallAt: `${registeredOn}T08:00:00Z`, lastCallOn: registeredOn, isSynthetic: false,
});

function makeData(overrides: Partial<DashboardData>): DashboardData {
  return {
    today: "2026-09-30", villages: [village(1, "Kayunga")], farmers: [], sales: [], problems: [],
    reference, callsLast30d: 0, callsTotal: 0, hasSynthetic: false, ...overrides,
  };
}

describe("median", () => {
  it("handles empty, odd and even lists", () => {
    expect(median([])).toBeNull();
    expect(median([3, 1, 2])).toBe(2);
    expect(median([1, 2, 3, 4])).toBe(2.5);
  });
});

describe("referenceFor", () => {
  const ref: ReferencePrice[] = [
    { month: "2026-03", kiboko: 1, faq: 100, parchment: 1, source: "ucda" },
    { month: "2026-06", kiboko: 2, faq: 200, parchment: 2, source: "ucda" },
    { month: "2026-07", kiboko: 2, faq: 200, parchment: 2, source: "interpolated" },
  ];
  it("uses the month itself, else carries the nearest earlier month forward at most 2 months", () => {
    expect(referenceFor(ref, "faq", "2026-06")).toBe(200);
    expect(referenceFor(ref, "faq", "2026-05")).toBe(100); // 2 months after March
    expect(referenceFor(ref, "faq", "2026-09")).toBe(200); // 2 months after the July row
  });
  it("returns null beyond 2 months and before the first month", () => {
    expect(referenceFor(ref, "faq", "2026-10")).toBeNull();
    expect(referenceFor(ref, "faq", "2025-01")).toBeNull();
    expect(referenceFor([], "faq", "2026-06")).toBeNull();
  });
  it("referenceAsOf is the last published (not interpolated) month", () => {
    expect(referenceAsOf(ref)).toBe("2026-06");
    expect(referenceAsOf([])).toBeNull();
  });
});

describe("shared index and window", () => {
  it("saleIndex is price over the month-matched reference", () => {
    expect(saleIndex(sale(1, 1, 8000), reference)).toBeCloseTo(0.8);
    expect(saleIndex(sale(1, 1, 8000, "2027-01-02"), reference)).toBeNull();
  });
  it("inWindow is inclusive of today and excludes future dates", () => {
    expect(inWindow("2026-09-30", "2026-09-30", 90)).toBe(true);
    expect(inWindow("2026-07-03", "2026-09-30", 90)).toBe(true); // day 90
    expect(inWindow("2026-07-02", "2026-09-30", 90)).toBe(false); // day 91
    expect(inWindow("2026-10-01", "2026-09-30", 90)).toBe(false);
  });
  it("isLowIndex uses the rounded percent, same as the red pill", () => {
    expect(isLowIndex(0.85)).toBe(true);
    expect(isLowIndex(0.8549)).toBe(true); // −15%
    expect(isLowIndex(0.8551)).toBe(false); // −14%
    expect(isLowIndex(null)).toBe(false);
  });
});

describe("minimum-sales gating", () => {
  it("returns null medians below 3 sales or 3 farmers", () => {
    const two = makeData({ sales: [sale(1, 1, 9000), sale(2, 1, 9000)] });
    expect(summarize(two, []).priceByForm[1].median).toBeNull();
    const oneFarmer = makeData({ sales: [sale(1, 1, 9000), sale(1, 1, 9000), sale(1, 1, 9000)] });
    expect(summarize(oneFarmer, []).priceByForm[1].median).toBeNull();
    const ok = makeData({ sales: [sale(1, 1, 9000), sale(2, 1, 9500), sale(3, 1, 10000)] });
    expect(summarize(ok, []).priceByForm[1].median).toBe(9500);
  });
});

describe("area summary", () => {
  it("FormPrice.index is the median of per-sale indexes for the form", () => {
    const ref: ReferencePrice[] = [
      { month: "2026-08", kiboko: 5000, faq: 8000, parchment: 15000, source: "t" },
      { month: "2026-09", kiboko: 5000, faq: 12000, parchment: 15000, source: "t" },
    ];
    // indexes 1.0, 1.0, 0.75: median 1.0, while the ratio of medians is 9000 / 12000 = 0.75
    const data = makeData({
      reference: ref,
      sales: [sale(1, 1, 8000, "2026-08-10"), sale(2, 1, 12000, "2026-09-10"), sale(3, 1, 9000, "2026-09-11")],
    });
    const faq = summarize(data, []).priceByForm[1];
    expect(faq.index).toBeCloseTo(1);
    expect(summarize(makeData({ sales: [sale(1, 1, 9000)] }), []).priceByForm[1].index).toBeNull();
  });
  it("uses a rolling 365-day window and leaves out future dates", () => {
    const base = [sale(1, 1, 9000), sale(2, 1, 9000), sale(3, 1, 9000)];
    const data = makeData({
      reference: [{ month: "2025-09", kiboko: 5000, faq: 10000, parchment: 15000, source: "t" }, ...reference],
      sales: [...base, sale(4, 1, 9000, "2025-10-01"), sale(5, 1, 9000, "2025-09-30"), sale(6, 1, 1000, "2026-10-01")],
    });
    // 2025-10-01 is day 365 (in); 2025-09-30 is day 366 (out); 2026-10-01 is in the future (out)
    expect(summarize(data, []).priceByForm[1].sales).toBe(4);
    expect(summarize(data, []).priceIndex).toBeCloseTo(0.9);
  });
  it("monthly chart points need at least 2 sales", () => {
    const data = makeData({ sales: [sale(1, 1, 9000, "2026-08-10"), sale(2, 1, 9000), sale(3, 1, 9400)] });
    const monthly = summarize(data, []).monthly;
    expect(monthly.find((m) => m.month === "2026-08")?.median).toBeNull();
    expect(monthly.find((m) => m.month === "2026-09")?.median).toBe(9200);
  });
});

describe("kpis", () => {
  it("counts new farmers by Kampala registration date and leaves out future sales", () => {
    const data = makeData({
      farmers: [
        farmer(1, "2026-09-01"), farmer(2, "2026-08-31"), farmer(3, "2026-08-02"), farmer(4, "2026-08-01"),
        farmer(5, "2026-10-01"),
      ],
      sales: [
        ...[1, 2, 3].map((f) => sale(f, 1, 9000)),
        ...[4, 5, 6].map((f) => sale(f, 1, 2000, "2026-10-01")), // would pull the median to 0.55
      ],
    });
    const k = kpis(data, []);
    expect(k.newFarmers30d).toBe(1); // 2026-09-01 .. 2026-09-30; 2026-10-01 is in the future
    expect(k.newFarmersPrev30d).toBe(2); // 2026-08-02 .. 2026-08-31
    expect(k.priceIndex).toBeCloseTo(0.9);
  });
});

describe("problem warnings", () => {
  it("fires for 3 farmers in 30 days with no baseline", () => {
    const data = makeData({ problems: [report(1, "2026-09-12"), report(2, "2026-09-20"), report(3, "2026-09-26")] });
    const warnings = computeWarnings(data);
    expect(warnings).toHaveLength(1);
    expect(warnings[0].title).toBe("Coffee leaf rust");
    expect(warnings[0].detail).toBe("3 farms · P1 parish · 12–26 Sep · none before");
    expect(warnings[0]).toMatchObject({ farms: 3, place: "P1 parish", dateRange: "12–26 Sep" });
  });
  it("does not fire for 2 farmers", () => {
    expect(computeWarnings(makeData({ problems: [report(1, "2026-09-12"), report(2, "2026-09-20")] }))).toHaveLength(0);
  });
  it("fires when growing: baseline 2 farms, window 3 farms", () => {
    const data = makeData({
      problems: [report(1, "2026-09-12"), report(2, "2026-09-20"), report(3, "2026-09-26"), report(4, "2026-08-01"), report(5, "2026-07-20")],
    });
    const warnings = computeWarnings(data);
    expect(warnings).toHaveLength(1);
    expect(warnings[0].detail).toContain("· 2 before");
  });
  it("does not fire when window farms do not exceed baseline farms (3 vs 3)", () => {
    const data = makeData({
      problems: [
        report(1, "2026-09-12"), report(2, "2026-09-20"), report(3, "2026-09-26"),
        report(4, "2026-08-01"), report(5, "2026-07-20"), report(6, "2026-07-10"),
      ],
    });
    expect(computeWarnings(data)).toHaveLength(0);
  });
});

describe("national reference", () => {
  it("is the month-matched median over the same sales", () => {
    const ref: ReferencePrice[] = [
      { month: "2026-08", kiboko: 5000, faq: 9000, parchment: 15000, source: "t" },
      { month: "2026-09", kiboko: 5000, faq: 11000, parchment: 15000, source: "t" },
    ];
    const data = makeData({
      reference: ref,
      sales: [sale(1, 1, 9000, "2026-08-10"), sale(2, 1, 9000, "2026-08-11"), sale(3, 1, 11000, "2026-09-10")],
    });
    expect(summarize(data, []).priceByForm[1].national).toBe(9000);
  });
});

describe("price warnings", () => {
  const twoEach = (price: number) => [1, 2, 3, 4, 5].flatMap((f) => [sale(f, 1, price), sale(f, 1, price, "2026-09-11")]);

  it("fires at −15% with 10 sales from 5 farmers and not above", () => {
    const w = computeWarnings(makeData({ sales: twoEach(8500) }));
    expect(w).toHaveLength(1);
    expect(w[0].title).toBe("Low prices in Kayunga");
    expect(w[0].detail).toBe("−15% vs national · 10 sales · 5 farms · 90 days");
    expect(w[0].farms).toBe(5);
    expect(computeWarnings(makeData({ sales: twoEach(8600) }))).toHaveLength(0);
  });

  it("needs 10 sales from 5 farmers", () => {
    const nine = twoEach(5000).slice(0, 9);
    expect(computeWarnings(makeData({ sales: nine }))).toHaveLength(0);
    const fourFarmers = [1, 2, 3, 4].flatMap((f) => [1, 2, 3].map((d) => sale(f, 1, 5000, `2026-09-1${d}`)));
    expect(computeWarnings(makeData({ sales: fourFarmers }))).toHaveLength(0);
  });

  it("one farmer with 3 half-price sales cannot trigger it", () => {
    const halfPrice = [1, 2, 3].map((d) => sale(1, 1, 5000, `2026-09-1${d}`));
    // below the minimums (5 sales, 3 farmers): the old per-sale median (0.5) fired here
    expect(computeWarnings(makeData({ sales: [...halfPrice, sale(2, 1, 10000), sale(3, 1, 10000)] }))).toHaveLength(0);
    // above the minimums, the one farmer's 7 sales are the per-sale majority but count once
    const many = [1, 2, 3, 4, 5, 6, 7].map((d) => sale(1, 1, 5000, `2026-09-1${d}`));
    const others = [2, 3, 4, 5].map((f) => sale(f, 1, 10000));
    expect(computeWarnings(makeData({ sales: [...many, ...others] }))).toHaveLength(0);
  });

  it("leaves out sales dated after today", () => {
    const future = twoEach(5000).map((s) => ({ ...s, date: "2026-10-01" }));
    expect(computeWarnings(makeData({ sales: future }))).toHaveLength(0);
  });
});
