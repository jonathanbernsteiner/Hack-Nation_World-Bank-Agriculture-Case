import { areaPathOf, summarize } from "./aggregate";
import type { AreaPath, AreaSummary, CoffeeType, DashboardData, Warning } from "./types";

export type AreaLevel = "district" | "sub_county" | "parish" | "village";
export const AREA_LEVELS: AreaLevel[] = ["district", "sub_county", "parish", "village"];
const DEPTH: Record<AreaLevel, number> = { district: 1, sub_county: 2, parish: 3, village: 4 };
const KEY_SEPARATOR = "|";

export const pathKey = (path: AreaPath): string => path.join(KEY_SEPARATOR);

/** Every distinct area at `level`, summarized. Pure: memoize on (data, level, warnings). */
export function areasAtLevel(data: DashboardData, level: AreaLevel, warnings: Warning[]): AreaSummary[] {
  const depth = DEPTH[level];
  const paths = new Map<string, AreaPath>();
  for (const village of data.villages) {
    const path = areaPathOf(village).slice(0, depth);
    paths.set(pathKey(path), path);
  }
  return [...paths.values()].map((path) => summarize(data, path, warnings));
}

/** Coffee types grown in each area at `level`, keyed by pathKey. */
export function coffeeTypesByArea(data: DashboardData, level: AreaLevel): Map<string, Set<CoffeeType>> {
  const depth = DEPTH[level];
  const types = new Map<string, Set<CoffeeType>>();
  for (const village of data.villages) {
    const key = pathKey(areaPathOf(village).slice(0, depth));
    const set = types.get(key) ?? new Set<CoffeeType>();
    if (village.coffeeType) set.add(village.coffeeType);
    types.set(key, set);
  }
  return types;
}

/** Share of sales (with a known buyer) that went to middlemen; null without sales. */
export function middlemenShare(area: AreaSummary): number | null {
  const total = area.priceByBuyer.reduce((sum, b) => sum + b.sales, 0);
  if (total === 0) return null;
  const middlemen = area.priceByBuyer.find((b) => b.buyer === "middleman")?.sales ?? 0;
  return middlemen / total;
}

/** True when `path` addresses an existing area (1 to 4 names). */
export function isKnownPath(data: DashboardData, path: AreaPath): boolean {
  if (path.length < 1 || path.length > 4) return false;
  return data.villages.some((v) => {
    const own = areaPathOf(v);
    return path.every((name, i) => own[i] === name);
  });
}
