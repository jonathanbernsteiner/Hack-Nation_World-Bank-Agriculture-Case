export type AreaLevel = "district" | "subcounty" | "parish" | "village";

export interface AreaResult {
  level: AreaLevel;
  name: string;
  path: string[];
  parent: string;
}

export interface FarmerResult {
  id: number;
  firstName: string;
  village: string;
  district: string;
}

export interface PageResult {
  label: string;
  href: string;
}

export interface SearchResponse {
  pages: PageResult[];
  areas: AreaResult[];
  farmers: FarmerResult[];
}

export const MIN_QUERY = 2;
export const MAX_QUERY = 60;

export const SEARCH_PAGES: readonly PageResult[] = [
  { label: "Overview", href: "/" },
  { label: "Map", href: "/map" },
  { label: "Areas", href: "/areas" },
  { label: "Farmers", href: "/farmers" },
  { label: "Prices", href: "/prices" },
  { label: "Warnings", href: "/warnings" },
  { label: "Settings", href: "/settings" },
  { label: "Uganda (map)", href: "/map" },
];

export function emptySearch(): SearchResponse {
  return { pages: [], areas: [], farmers: [] };
}

/** Escape LIKE wildcards so user text matches literally (backslash is the escape char). */
export function escapeLike(q: string): string {
  return q.replace(/[\\%_]/g, (c) => `\\${c}`);
}

/** Trim and length-check a query; returns null when it is not searchable. */
export function normalizeQuery(raw: string | null | undefined): string | null {
  const q = (raw ?? "").trim();
  return q.length >= MIN_QUERY && q.length <= MAX_QUERY ? q : null;
}

export function matchPages(q: string): PageResult[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return [];
  return SEARCH_PAGES.filter((p) => p.label.toLowerCase().includes(needle));
}

export function areaHref(area: Pick<AreaResult, "level" | "path">): string {
  // The Areas page names this level "sub_county".
  const level = area.level === "subcounty" ? "sub_county" : area.level;
  return `/areas?level=${level}&area=${encodeURIComponent(area.path.join("|"))}`;
}

export function farmerHref(f: Pick<FarmerResult, "id">): string {
  return `/farmers?farmer=${f.id}`;
}
