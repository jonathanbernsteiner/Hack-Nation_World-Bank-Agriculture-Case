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
  it("fires at index <= 0.85 and not above", () => {
    const low = makeData({ sales: [sale(1, 1, 8500), sale(2, 1, 8500), sale(3, 1, 8500)] });
    const w = computeWarnings(low);
    expect(w).toHaveLength(1);
    expect(w[0].title).toBe("Low prices in Kayunga");
    expect(w[0].detail).toBe("−15% vs national · 3 sales · 90 days");
    const fine = makeData({ sales: [sale(1, 1, 8600), sale(2, 1, 8600), sale(3, 1, 8600)] });
    expect(computeWarnings(fine)).toHaveLength(0);
  });
});
