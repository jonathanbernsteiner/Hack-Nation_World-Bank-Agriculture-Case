"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, MapPin, Search, X } from "lucide-react";
import AreaPeek from "@/components/AreaPeek";
import FilterMenu from "@/components/FilterMenu";
import type { FilterField } from "@/components/FilterMenu";
import Segmented from "@/components/Segmented";
import SortMenu from "@/components/SortMenu";
import { priceBand } from "@/components/FarmersTable";
import { computeWarnings } from "@/lib/aggregate";
import { AREA_LEVELS, areasAtLevel, coffeeTypesByArea, isKnownPath, middlemenShare, pathKey } from "@/lib/areas";
import type { AreaLevel } from "@/lib/areas";
import { formatIndex, formatNumber } from "@/lib/format";
import type { AreaPath, AreaSummary, DashboardData } from "@/lib/types";

const PAGE_SIZE = 50;
const CONTROL = "h-10 w-full min-w-0 truncate text-sm border rounded-lg px-3 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors";
const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors";
const CHIP = "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";
const REGIONS = ["Central", "Eastern", "Northern", "Western"];
const TYPE_OPTIONS = [{ value: "robusta", label: "Robusta" }, { value: "arabica", label: "Arabica" }];
const PRICE_OPTIONS = [
  { value: "bad", label: "15%+ below national" },
  { value: "warn", label: "1–14% below" },
  { value: "ok", label: "At or above" },
  { value: "none", label: "Not enough sales" },
];
const LEVEL_OPTIONS: { value: AreaLevel; label: string }[] = [
  { value: "district", label: "Districts" },
  { value: "sub_county", label: "Sub-counties" },
  { value: "parish", label: "Parishes" },
  { value: "village", label: "Villages" },
];
const LEVEL_NOUN: Record<AreaLevel, [string, string]> = {
  district: ["district", "districts"],
  sub_county: ["sub-county", "sub-counties"],
  parish: ["parish", "parishes"],
  village: ["village", "villages"],
};

type SortKey = "farmers" | "new" | "calls" | "price" | "warnings" | "name";
type SortDir = "asc" | "desc";
type ParamKey = "level" | "q" | "region" | "type" | "warn" | "price" | "sort" | "dir" | "area";
const SORT_FIELDS: { key: SortKey; label: string }[] = [
  { key: "farmers", label: "Farmers" },
  { key: "new", label: "New 90d" },
  { key: "calls", label: "Calls" },
  { key: "price", label: "vs national" },
  { key: "warnings", label: "Warnings" },
  { key: "name", label: "Name" },
];
const SORT_KEYS = SORT_FIELDS.map((f) => f.key);
const SORT_VALUE: Record<SortKey, (a: AreaSummary) => string | number | null> = {
  farmers: (a) => a.farmers,
  new: (a) => a.newFarmers90d,
  calls: (a) => a.calls,
  price: (a) => a.priceIndex,
  warnings: (a) => a.warnings.length,
  name: (a) => a.name.toLowerCase(),
};

function sortAreas(rows: AreaSummary[], key: SortKey, dir: SortDir): AreaSummary[] {
  const get = SORT_VALUE[key];
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = get(a);
    const y = get(b);
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sign || a.name.localeCompare(b.name);
  });
}

function parentLabel(area: AreaSummary): string {
  return [...area.path.slice(0, -1).reverse(), area.region].filter(Boolean).join(" · ");
}

function matchesQuery(area: AreaSummary, needle: string): boolean {
  return [...area.path, area.region ?? ""].some((v) => v.toLowerCase().includes(needle));
}

function Dash() {
  return <span className="text-gray-300">—</span>;
}

function Chip({ label, onOpen, onRemove }: { label: string; onOpen: () => void; onRemove: () => void }) {
  return (
    <span className={CHIP}>
      <button type="button" onClick={onOpen} className="hover:text-blue-900">{label}</button>
      <button type="button" aria-label={`Remove ${label}`} onClick={onRemove} className="hover:text-blue-900">
        <X size={12} />
      </button>
    </span>
  );
}

function SortTh({ label, k, sort, onSort, className }: { label: string; k: SortKey; sort: { key: SortKey; dir: SortDir }; onSort: (k: SortKey) => void; className: string }) {
  const Icon = sort.dir === "asc" ? ChevronUp : ChevronDown;
  return (
    <th className={className} aria-sort={sort.key === k ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}>
      <button type="button" onClick={() => onSort(k)} className="inline-flex items-center gap-1 font-medium hover:text-gray-700">
        {label}
        {sort.key === k && <Icon size={12} />}
      </button>
    </th>
  );
}

function AreaRow({ area, isSelected, onSelect }: { area: AreaSummary; isSelected: boolean; onSelect: (path: AreaPath) => void }) {
  const share = middlemenShare(area);
  const isLow = priceBand(area.priceIndex) === "bad";
  return (
    <tr
      onClick={() => onSelect(area.path)}
      className={`border-b border-gray-100 cursor-pointer transition-colors ${isSelected ? "bg-blue-50/50" : "hover:bg-gray-50"}`}
    >
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="font-medium text-gray-900">{area.name}</div>
        <div className="text-xs text-muted">{parentLabel(area)}</div>
      </td>
      <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(area.farmers)}</td>
      <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(area.newFarmers90d)}</td>
      <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">{formatNumber(area.calls)}</td>
      <td className={`px-4 py-3 text-right font-mono whitespace-nowrap ${isLow ? "text-red-600" : "text-gray-700"}`}>
        {area.priceIndex === null ? <Dash /> : formatIndex(area.priceIndex)}
      </td>
      <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">{share === null ? <Dash /> : `${Math.round(share * 100)}%`}</td>
      <td className="px-4 py-3 text-right font-mono whitespace-nowrap">
        {area.warnings.length === 0 ? <Dash /> : <span className="text-red-600 font-medium">{area.warnings.length}</span>}
      </td>
    </tr>
  );
}

export default function AreasView({ data }: { data: DashboardData }) {
  const searchParams = useSearchParams();
  const warnings = useMemo(() => computeWarnings(data), [data]);
  const param = (key: ParamKey) => searchParams.get(key) ?? "";
  const oneOf = (key: ParamKey, allowed: string[]) => (allowed.includes(param(key)) ? param(key) : "");
  const level = (oneOf("level", AREA_LEVELS) || "district") as AreaLevel;
  const query = param("q");
  const region = oneOf("region", REGIONS);
  const coffeeType = oneOf("type", TYPE_OPTIONS.map((o) => o.value));
  const hasWarnings = param("warn") === "1";
  const priceBucket = oneOf("price", PRICE_OPTIONS.map((o) => o.value));
  const sort = {
    key: (oneOf("sort", SORT_KEYS) || "farmers") as SortKey,
    dir: (oneOf("dir", ["asc", "desc"]) || "desc") as SortDir,
  };
  const areaPath = useMemo<AreaPath | null>(() => {
    const raw = searchParams.get("area");
    const path = raw ? raw.split("|") : [];
    return isKnownPath(data, path) ? path : null;
  }, [searchParams, data]);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [shown, setShown] = useState(PAGE_SIZE);

  const writeParams = useCallback(
    (patch: Partial<Record<ParamKey, string>>, mode: "push" | "replace") => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value) params.set(key, value);
        else params.delete(key);
      }
      const qs = params.toString();
      const url = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
      if (mode === "push") window.history.pushState(null, "", url);
      else window.history.replaceState(null, "", url);
    },
    [searchParams],
  );
  const setFilters = useCallback(
    (patch: Partial<Record<ParamKey, string>>) => {
      writeParams(patch, "replace");
      setShown(PAGE_SIZE);
    },
    [writeParams, setShown],
  );
  const openArea = useCallback(
    (path: AreaPath | null) => writeParams({ area: path ? path.join("|") : "" }, path && !areaPath ? "push" : "replace"),
    [writeParams, areaPath],
  );
  const closeArea = useCallback(() => openArea(null), [openArea]);

  const areas = useMemo(() => areasAtLevel(data, level, warnings), [data, level, warnings]);
  const types = useMemo(() => coffeeTypesByArea(data, level), [data, level]);
  const needle = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      sortAreas(
        areas.filter(
          (a) =>
            (!needle || matchesQuery(a, needle)) &&
            (!region || a.region === region) &&
            (!coffeeType || types.get(pathKey(a.path))?.has(coffeeType as "robusta" | "arabica")) &&
            (!hasWarnings || a.warnings.length > 0) &&
            (!priceBucket || priceBand(a.priceIndex) === priceBucket),
        ),
        sort.key,
        sort.dir,
      ),
    [areas, types, needle, region, coffeeType, hasWarnings, priceBucket, sort.key, sort.dir],
  );
  const visible = filtered.slice(0, shown);

  const applySort = (key: string, dir: SortDir) => setFilters({ sort: key, dir });
  const onSort = (key: SortKey) =>
    applySort(key, sort.key === key ? (sort.dir === "asc" ? "desc" : "asc") : key === "name" ? "asc" : "desc");
  const filterValues: Record<string, string> = { region, type: coffeeType, warn: hasWarnings ? "1" : "", price: priceBucket };
  const fields: FilterField[] = [
    { key: "region", label: "Region", options: REGIONS.map((r) => ({ value: r, label: r })) },
    { key: "type", label: "Coffee type", options: TYPE_OPTIONS },
    { key: "warn", label: "Has warnings", options: [], kind: "toggle" },
    { key: "price", label: "Price", options: PRICE_OPTIONS },
  ];
  const chips = fields
    .filter((f) => filterValues[f.key])
    .map((f) => {
      const v = filterValues[f.key];
      return { key: f.key, label: f.kind === "toggle" ? f.label : `${f.label}: ${f.options.find((o) => o.value === v)?.label ?? v}` };
    });
  const clearAll = () => setFilters({ region: "", type: "", warn: "", price: "" });
  const [singular, plural] = LEVEL_NOUN[level];

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <Segmented options={LEVEL_OPTIONS} value={level} onChange={(v) => setFilters({ level: v === "district" ? "" : v })} ariaLabel="Area level" />
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              placeholder="Search area"
              aria-label="Search areas"
              onChange={(e) => setFilters({ q: e.target.value })}
              className={`${CONTROL} pl-9`}
            />
          </div>
          <FilterMenu fields={fields} values={filterValues} onChange={(k, v) => setFilters({ [k]: v })} onClearAll={clearAll} open={isFilterOpen} onOpenChange={setIsFilterOpen} />
          <SortMenu fields={SORT_FIELDS} sortKey={sort.key} dir={sort.dir} onChange={applySort} />
          <p className="ml-auto text-sm text-muted whitespace-nowrap">
            {formatNumber(filtered.length)} {filtered.length === 1 ? singular : plural}
          </p>
        </div>
        {chips.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {chips.map((c) => (
              <Chip key={c.key} label={c.label} onOpen={() => setIsFilterOpen(true)} onRemove={() => setFilters({ [c.key]: "" })} />
            ))}
          </div>
        )}
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white border border-line rounded-[14px] flex flex-col items-center justify-center py-16 text-gray-400">
          <MapPin size={48} className="mb-4" />
          <p className="text-lg font-medium text-gray-500">No areas found</p>
        </div>
      ) : (
        <div>
          <div className="bg-white border border-line rounded-[14px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line bg-gray-50">
                    <SortTh label="Name" k="name" sort={sort} onSort={onSort} className={`${TH} text-left`} />
                    <SortTh label="Farmers" k="farmers" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <SortTh label="New 90d" k="new" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <SortTh label="Calls" k="calls" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <SortTh label="vs national, 12 months" k="price" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <th className={`${TH} text-right`}>Middlemen, 12 months</th>
                    <SortTh label="Warnings" k="warnings" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((a) => (
                    <AreaRow key={pathKey(a.path)} area={a} isSelected={areaPath !== null && pathKey(areaPath) === pathKey(a.path)} onSelect={openArea} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-muted">Showing {formatNumber(visible.length)} of {formatNumber(filtered.length)}</p>
            {visible.length < filtered.length && (
              <button type="button" className={BTN_SECONDARY} onClick={() => setShown(shown + PAGE_SIZE)}>
                Load more
              </button>
            )}
          </div>
        </div>
      )}
      {areaPath && <AreaPeek data={data} path={areaPath} warnings={warnings} onSelect={openArea} onClose={closeArea} />}
    </div>
  );
}
