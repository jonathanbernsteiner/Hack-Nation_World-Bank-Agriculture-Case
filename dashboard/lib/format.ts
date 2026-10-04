// Display helpers shared by every component. Pure, no React.

import type { BuyerType, CoffeeForm, Level } from "./types";

const PROBLEM_LABELS: Record<string, string> = {
  coffee_leaf_rust: "Coffee leaf rust",
  coffee_berry_disease: "Coffee berry disease",
  coffee_wilt_disease: "Coffee wilt disease",
  black_coffee_twig_borer: "Black coffee twig borer",
  coffee_berry_borer: "Coffee berry borer",
  white_stem_borer: "White stem borer",
  coffee_leaf_miner: "Coffee leaf miner",
  antestia_bug: "Antestia bug",
  drought_stress: "Drought stress",
  not_sure: "Not sure (referred to a person)",
  yellowing_leaves: "Yellowing leaves",
  leaf_spots: "Leaf spots",
  powder_or_rust: "Powder or rust on leaves",
  fruit_spots: "Spots on berries",
  wilting: "Wilting",
  pests: "Pests",
  stunted_growth: "Stunted growth",
  rot: "Rot",
};

const FORM_LABELS: Record<CoffeeForm, string> = {
  kiboko: "Kiboko (dry cherry)",
  faq: "FAQ (robusta beans)",
  parchment: "Arabica parchment",
};

const BUYER_LABELS: Record<BuyerType, string> = {
  middleman: "Middleman",
  cooperative: "Cooperative",
  other: "Other buyer",
};

const LEVEL_LABELS: Record<Level, string> = {
  country: "Country",
  district: "District",
  sub_county: "Sub-county",
  parish: "Parish",
  village: "Village",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function labelProblem(id: string): string {
  const known = PROBLEM_LABELS[id];
  if (known) return known;
  const words = id.replace(/_/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function labelForm(form: CoffeeForm): string {
  return FORM_LABELS[form];
}

export function labelBuyer(buyer: BuyerType): string {
  return BUYER_LABELS[buyer];
}

export function labelLevel(level: Level): string {
  return LEVEL_LABELS[level];
}

/** 5800 → "5,800" (UGX shown by the caller as a unit). */
export function formatNumber(value: number): string {
  return Math.round(value).toLocaleString("en-US");
}

/** 5800 → "UGX 5,800" */
export function formatUgx(value: number | null): string {
  return value === null ? "—" : `UGX ${formatNumber(value)}`;
}

/** Price index vs national: 0.92 → "−8%", 1.03 → "+3%", 1 → "±0%", null → "—". */
export function formatIndex(index: number | null): string {
  if (index === null) return "—";
  const pct = Math.round((index - 1) * 100);
  if (pct === 0) return "±0%";
  return pct > 0 ? `+${pct}%` : `−${Math.abs(pct)}%`;
}

/** "2026-09-12" → "12 Sep 2026" */
export function formatDate(isoDate: string | null): string {
  if (!isoDate) return "—";
  const [y, m, d] = isoDate.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

/** "2026-09" → "Sep 26" */
export function formatMonth(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${MONTHS[m - 1]} ${String(y).slice(2)}`;
}

export function formatK(v: number): string {
  return v % 1000 === 0 ? `${v / 1000}k` : `${(v / 1000).toFixed(1)}k`;
}
