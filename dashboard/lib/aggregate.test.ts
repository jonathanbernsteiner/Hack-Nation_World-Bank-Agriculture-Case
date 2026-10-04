import { describe, expect, it } from "vitest";
import { computeWarnings, median, referenceFor, summarize } from "./aggregate";
import type { DashboardData, ProblemReport, ReferencePrice, Sale, Village } from "./types";

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
  it("falls back to the nearest earlier month, then the earliest", () => {
    const ref: ReferencePrice[] = [
      { month: "2026-03", kiboko: 1, faq: 100, parchment: 1, source: "" },
      { month: "2026-06", kiboko: 2, faq: 200, parchment: 2, source: "" },
    ];
    expect(referenceFor(ref, "faq", "2026-06")).toBe(200);
    expect(referenceFor(ref, "faq", "2026-05")).toBe(100);
    expect(referenceFor(ref, "faq", "2026-12")).toBe(200);
    expect(referenceFor(ref, "faq", "2025-01")).toBe(100);
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

describe("problem warnings", () => {
  it("fires for 3 farmers in 30 days", () => {
    const data = makeData({ problems: [report(1, "2026-09-12"), report(2, "2026-09-20"), report(3, "2026-09-26")] });
    const warnings = computeWarnings(data);
    expect(warnings).toHaveLength(1);
    expect(warnings[0].title).toBe("Coffee leaf rust: 3 farms in P1 parish");
    expect(warnings[0].detail).toContain("none in the 12 weeks before");
  });
  it("does not fire for 2 farmers", () => {
    expect(computeWarnings(makeData({ problems: [report(1, "2026-09-12"), report(2, "2026-09-20")] }))).toHaveLength(0);
  });
  it("is suppressed when the baseline had 2 reports", () => {
    const data = makeData({
      problems: [report(1, "2026-09-12"), report(2, "2026-09-20"), report(3, "2026-09-26"), report(4, "2026-08-01"), report(5, "2026-07-20")],
    });
    expect(computeWarnings(data)).toHaveLength(0);
  });
});

describe("price warnings", () => {
  it("fires at index <= 0.85 and not above", () => {
    const low = makeData({ sales: [sale(1, 1, 8500), sale(2, 1, 8500), sale(3, 1, 8500)] });
    const w = computeWarnings(low);
    expect(w).toHaveLength(1);
    expect(w[0].title).toBe("Prices 15% below national in Kayunga");
    const fine = makeData({ sales: [sale(1, 1, 8600), sale(2, 1, 8600), sale(3, 1, 8600)] });
    expect(computeWarnings(fine)).toHaveLength(0);
  });
});
