// Pure helpers for the Warnings page: problem reports by district, per week, and totals.

import type { DashboardData } from "./types";

const DAY_MS = 86_400_000;
const TOP_PROBLEMS = 4;
export const OTHER_KEY = "other";

export interface DistrictProblemRow {
  district: string;
  region: string;
  problem: string;
  farmers: number; // distinct farmers
  reports: number;
  lastDate: string;
}

export interface WeekCounts {
  weekStart: string; // Monday, YYYY-MM-DD
  counts: Record<string, number>; // problem id (top 4) or "other" -> reports
}

export interface WeeklyResult {
  keys: string[]; // top problems (most reports first), then "other" if used
  weeks: WeekCounts[];
}

export interface ProblemTotal {
  problem: string;
  farmers: number;
  reports: number;
}

function toMs(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

function fromMs(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

function addDays(date: string, days: number): string {
  return fromMs(toMs(date) + days * DAY_MS);
}

/** Monday of the week containing the date. */
function weekStartOf(date: string): string {
  const dow = (new Date(toMs(date)).getUTCDay() + 6) % 7; // Mon = 0
  return addDays(date, -dow);
}

function recentProblems(data: DashboardData, days: number) {
  const since = addDays(data.today, -days);
  return data.problems.filter((p) => p.date > since && p.date <= data.today);
}

export function problemsByDistrict(data: DashboardData, days = 90): DistrictProblemRow[] {
  const villages = new Map(data.villages.map((v) => [v.id, v]));
  const groups = new Map<string, { district: string; region: string; problem: string; farmers: Set<number>; reports: number; lastDate: string }>();
  for (const report of recentProblems(data, days)) {
    const village = villages.get(report.villageId);
    if (!village) continue;
    const key = `${village.district}|${report.problem}`;
    const group = groups.get(key) ?? {
      district: village.district,
      region: village.region,
      problem: report.problem,
      farmers: new Set<number>(),
      reports: 0,
      lastDate: report.date,
    };
    group.farmers.add(report.farmerId);
    groups.set(key, {
      ...group,
      reports: group.reports + 1,
      lastDate: report.date > group.lastDate ? report.date : group.lastDate,
    });
  }
  return [...groups.values()]
    .map(({ farmers, ...rest }) => ({ ...rest, farmers: farmers.size }))
    .sort((a, b) => b.farmers - a.farmers || b.reports - a.reports || a.district.localeCompare(b.district));
}

export function problemTotals(data: DashboardData, days = 90): ProblemTotal[] {
  const groups = new Map<string, { farmers: Set<number>; reports: number }>();
  for (const report of recentProblems(data, days)) {
    const group = groups.get(report.problem) ?? { farmers: new Set<number>(), reports: 0 };
    group.farmers.add(report.farmerId);
    groups.set(report.problem, { farmers: group.farmers, reports: group.reports + 1 });
  }
  return [...groups.entries()]
    .map(([problem, g]) => ({ problem, farmers: g.farmers.size, reports: g.reports }))
    .sort((a, b) => b.farmers - a.farmers || b.reports - a.reports || a.problem.localeCompare(b.problem));
}

export function weeklyCounts(data: DashboardData, weeks = 26): WeeklyResult {
  const lastStart = weekStartOf(data.today);
  const starts = Array.from({ length: weeks }, (_, i) => addDays(lastStart, -7 * (weeks - 1 - i)));
  const first = starts[0];
  const inRange = data.problems.filter((p) => p.date >= first && p.date <= data.today);

  const totals = new Map<string, number>();
  for (const p of inRange) totals.set(p.problem, (totals.get(p.problem) ?? 0) + 1);
  const top = [...totals.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, TOP_PROBLEMS)
    .map(([problem]) => problem);
  const topSet = new Set(top);
  const hasOther = [...totals.keys()].some((p) => !topSet.has(p));
  const keys = hasOther ? [...top, OTHER_KEY] : top;

  const byWeek = new Map(starts.map((s) => [s, Object.fromEntries(keys.map((k) => [k, 0])) as Record<string, number>]));
  for (const p of inRange) {
    const counts = byWeek.get(weekStartOf(p.date));
    if (!counts) continue;
    const key = topSet.has(p.problem) ? p.problem : OTHER_KEY;
    counts[key] += 1;
  }
  return { keys, weeks: starts.map((weekStart) => ({ weekStart, counts: byWeek.get(weekStart)! })) };
}
