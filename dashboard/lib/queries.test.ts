import { describe, expect, it } from "vitest";
import { dashboardToday, dropOutlierSales, kampalaDate, parseAsOf } from "./queries";
import type { ReferencePrice, Sale } from "./types";

describe("DASHBOARD_AS_OF", () => {
  it("is unset when missing or blank", () => {
    expect(parseAsOf(undefined)).toBeNull();
    expect(parseAsOf("")).toBeNull();
    expect(parseAsOf("   ")).toBeNull();
  });

  it("accepts a real YYYY-MM-DD date (surrounding spaces ignored)", () => {
    expect(parseAsOf("2026-10-04")).toBe("2026-10-04");
    expect(parseAsOf(" 2024-02-29 ")).toBe("2024-02-29");
  });

  it("rejects other formats and impossible dates", () => {
    for (const bad of ["2026-10-4", "04/10/2026", "2026-10-04T00:00:00Z", "2026-13-01", "2026-02-30", "2025-02-29", "today"]) {
      expect(() => parseAsOf(bad), bad).toThrow(/DASHBOARD_AS_OF/);
    }
  });

  it("pins today when set, else uses the Kampala date (UTC+3)", () => {
    const lateUtc = new Date("2026-10-03T22:30:00Z"); // already 4 Oct in Kampala
    expect(kampalaDate(lateUtc)).toBe("2026-10-04");
    expect(dashboardToday(undefined, lateUtc)).toBe("2026-10-04");
    expect(dashboardToday("2026-09-15", lateUtc)).toBe("2026-09-15");
    expect(() => dashboardToday("2026-9-15", lateUtc)).toThrow(/YYYY-MM-DD/);
  });
});

describe("dropOutlierSales", () => {
  const reference: ReferencePrice[] = [{ month: "2026-09", kiboko: 6000, faq: 12000, parchment: 15000, source: "t" }];
  const sale = (ugxPerKg: number, date = "2026-09-10"): Sale => ({
    farmerId: 1, villageId: 1, date, form: "kiboko", ugxPerKg, kg: 10, buyerType: "middleman",
  });

  it("keeps sales from 0.3x to 3x the month+form reference and drops the rest", () => {
    const sales = [sale(1799), sale(1800), sale(6000), sale(18000), sale(18001), sale(58500)];
    expect(dropOutlierSales(sales, reference).map((s) => s.ugxPerKg)).toEqual([1800, 6000, 18000]);
  });

  it("keeps sales without a reference and does not mutate the input", () => {
    const sales = [sale(58500, "2027-03-01"), sale(58500)];
    const copy = structuredClone(sales);
    expect(dropOutlierSales(sales, reference)).toEqual([sales[0]]);
    expect(sales).toEqual(copy);
  });
});
