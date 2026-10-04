import { describe, expect, it } from "vitest";
import { problemFarms, problemsByDistrict, problemTotals, weeklyCounts } from "./problems";
import type { DashboardData } from "./types";

const village = (id: number, district: string) => ({
  id, region: "Central", district, subCounty: "S", parish: "P", village: `V${id}`,
  lat: 0, lon: 0, coffeeType: null, isVerified: true, isSynthetic: false,
});

const data: DashboardData = {
  today: "2026-10-03", // Saturday; week starts Mon 2026-09-28
  villages: [village(1, "Masaka"), village(2, "Mbale")],
  farmers: [], sales: [], reference: [], callsLast30d: 0, callsTotal: 0, hasSynthetic: false,
  problems: [
    { farmerId: 1, villageId: 1, date: "2026-09-30", problem: "coffee_leaf_rust" },
    { farmerId: 1, villageId: 1, date: "2026-10-01", problem: "coffee_leaf_rust" },
    { farmerId: 2, villageId: 1, date: "2026-09-20", problem: "coffee_leaf_rust" },
    { farmerId: 3, villageId: 2, date: "2026-09-01", problem: "wilting" },
    { farmerId: 4, villageId: 2, date: "2026-01-01", problem: "wilting" },
  ],
};

describe("problems", () => {
  it("groups by district with distinct farmers, most farmers first", () => {
    const rows = problemsByDistrict(data, 90);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ district: "Masaka", farmers: 2, reports: 3, lastDate: "2026-10-01" });
  });

  it("problemFarms counts distinct farms with any problem, not per problem", () => {
    const withSecondProblem: DashboardData = {
      ...data,
      problems: [
        ...data.problems,
        { farmerId: 1, villageId: 1, date: "2026-09-25", problem: "wilting" },
        { farmerId: 5, villageId: 1, date: "2026-10-04", problem: "wilting" }, // after today
      ],
    };
    const perProblem = problemTotals(withSecondProblem, 90).reduce((sum, t) => sum + t.farmers, 0);
    expect(perProblem).toBe(4); // farmer 1 counted twice
    expect(problemFarms(withSecondProblem, [], 90)).toBe(3); // farmers 1, 2, 3
    expect(problemFarms(withSecondProblem, ["Masaka"], 90)).toBe(2);
    expect(problemFarms(withSecondProblem, ["Masaka"], 7)).toBe(1);
  });

  it("counts reports per week start", () => {
    const { weeks, keys } = weeklyCounts(data, 26);
    expect(weeks).toHaveLength(26);
    expect(keys).toContain("coffee_leaf_rust");
    expect(weeks[25].weekStart).toBe("2026-09-28");
    expect(weeks[25].counts.coffee_leaf_rust).toBe(2);
  });
});
