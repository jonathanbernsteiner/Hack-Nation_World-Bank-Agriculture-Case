import { describe, expect, it } from "vitest";
import { formatK, maskedPhone } from "./format";

describe("formatK", () => {
  it("drops the decimal on whole thousands", () => {
    expect(formatK(8000)).toBe("8k");
    expect(formatK(0)).toBe("0k");
  });
  it("keeps one decimal otherwise", () => {
    expect(formatK(8500)).toBe("8.5k");
    expect(formatK(2500)).toBe("2.5k");
  });
});

describe("maskedPhone", () => {
  it("is deterministic and masked", () => {
    expect(maskedPhone(42)).toBe(maskedPhone(42));
    expect(maskedPhone(42)).toMatch(/^\+256 7•• ••• \d{3}$/);
  });
  it("differs between ids", () => {
    const tails = new Set(Array.from({ length: 50 }, (_, i) => maskedPhone(i + 1)));
    expect(tails.size).toBeGreaterThan(40);
  });
});
