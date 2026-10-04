import { describe, expect, it } from "vitest";
import { formatK } from "./format";

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
