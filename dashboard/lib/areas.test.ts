import { describe, expect, it } from "vitest";
import { areasAtLevel, coffeeTypesByArea, isKnownPath, middlemenShare } from "./areas";
import { summarize } from "./aggregate";
import type { DashboardData, Village } from "./types";

const village = (id: number, district: string, subCounty: string, parish: string, name: string, coffeeType: Village["coffeeType"] = "robusta"): Village => ({
  id, region: "Central", district, subCounty, parish, village: name,
  lat: 0.5, lon: 32, coffeeType, isVerified: true, isSynthetic: false,
});

const data: DashboardData = {
  today: "2026-09-30",
  villages: [
    village(1, "Masaka", "S1", "P1", "V1"),
    village(2, "Masaka", "S1", "P1", "V2", "arabica"),
    village(3, "Masaka", "S1", "P2", "V3"),
    village(4, "Masaka", "S2", "P3", "V4"),
    village(5, "Kayunga", "S3", "P4", "V5"),
  ],
  farmers: [], sales: [], problems: [], reference: [], callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
};

describe("areasAtLevel", () => {
  it("counts distinct areas per level", () => {
    expect(areasAtLevel(data, "district", []).map((a) => a.name).sort()).toEqual(["Kayunga", "Masaka"]);
    expect(areasAtLevel(data, "sub_county", [])).toHaveLength(3);
    expect(areasAtLevel(data, "parish", [])).toHaveLength(4);
    expect(areasAtLevel(data, "village", [])).toHaveLength(5);
  });

  it("summarizes each path", () => {
    const masaka = areasAtLevel(data, "district", []).find((a) => a.name === "Masaka");
    expect(masaka?.villages).toBe(4);
    expect(masaka?.level).toBe("district");
  });
});

describe("helpers", () => {
  it("collects coffee types per area", () => {
    expect([...(coffeeTypesByArea(data, "parish").get("Masaka|S1|P1") ?? [])].sort()).toEqual(["arabica", "robusta"]);
  });
  it("validates paths", () => {
    expect(isKnownPath(data, ["Masaka", "S1"])).toBe(true);
    expect(isKnownPath(data, ["Masaka", "S3"])).toBe(false);
    expect(isKnownPath(data, [])).toBe(false);
  });
  it("has no middleman share without sales", () => {
    expect(middlemenShare(summarize(data, ["Masaka"], []))).toBeNull();
  });
});
