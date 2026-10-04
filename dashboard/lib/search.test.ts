import { describe, expect, it } from "vitest";
import { areaHref, escapeLike, farmerHref, matchPages, normalizeQuery } from "./search";

describe("escapeLike", () => {
  it("escapes wildcards and backslashes", () => {
    expect(escapeLike("50%_a\\b")).toBe("50\\%\\_a\\\\b");
  });
  it("leaves plain text alone", () => {
    expect(escapeLike("Masaka")).toBe("Masaka");
  });
});

describe("matchPages", () => {
  it("matches case-insensitively by substring", () => {
    expect(matchPages("PRI").map((p) => p.href)).toEqual(["/prices"]);
  });
  it("returns nothing for no match or blank", () => {
    expect(matchPages("zzz")).toEqual([]);
    expect(matchPages("  ")).toEqual([]);
  });
});

describe("normalizeQuery", () => {
  it("trims and enforces 2-60 chars", () => {
    expect(normalizeQuery(" ab ")).toBe("ab");
    expect(normalizeQuery("a")).toBeNull();
    expect(normalizeQuery("x".repeat(61))).toBeNull();
    expect(normalizeQuery(null)).toBeNull();
  });
});

describe("hrefs", () => {
  it("builds area and farmer links", () => {
    expect(areaHref({ level: "subcounty", path: ["Masaka", "Kyesiiga"] })).toBe(
      "/areas?level=sub_county&area=Masaka%7CKyesiiga",
    );
    expect(farmerHref({ id: 7 })).toBe("/farmers?farmer=7");
  });
});
