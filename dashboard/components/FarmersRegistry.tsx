"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, Search, Users, X } from "lucide-react";
import FarmerPeek from "@/components/FarmerPeek";
import FilterMenu from "@/components/FilterMenu";
import type { FilterField } from "@/components/FilterMenu";
import SortMenu from "@/components/SortMenu";
import { registryRows } from "@/lib/registry";
import type { RegistryRow } from "@/lib/registry";
import { formatDate, formatIndex, formatNumber, labelBuyer, labelProblem } from "@/lib/format";
import { indexPillClass, shortForm } from "@/components/FarmersTable";
import type { BuyerType, DashboardData } from "@/lib/types";

const PAGE_SIZE = 50;
const CONTROL = "h-10 w-full min-w-0 truncate text-sm border rounded-lg px-3 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors";
const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60";
const CHIP = "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";
const WIDE = "hidden 2xl:table-cell";
const MAX_PROBLEM_WIDTH = "max-w-[180px]";
const PRICE_TOLERANCE = 0.03;
const REGIONS = ["Central", "Eastern", "Northern", "Western"];
const BUYER_OPTIONS: BuyerType[] = ["middleman", "cooperative", "other"];
const PRICE_OPTIONS = [
  { value: "below", label: "Below" },
  { value: "same", label: "Same" },
  { value: "above", label: "Above" },
  { value: "none", label: "No sale" },
];
type FilterKey = "q" | "region" | "district" | "sub" | "buyer" | "price" | "problems" | "sort" | "dir";
type SortKey = "name" | "registered" | "calls" | "lastSale" | "vsVillage";
const SORT_KEYS: SortKey[] = ["name", "registered", "calls", "lastSale", "vsVillage"];
const SORT_FIELDS: { key: SortKey; label: string }[] = [
  { key: "registered", label: "Registered" },
  { key: "calls", label: "Calls" },
  { key: "vsVillage", label: "Last sale vs village" },
  { key: "name", label: "First name" },
];
const DEFAULT_SORT = { key: "registered" as SortKey, dir: "desc" as SortDir };
type SortDir = "asc" | "desc";
const SORT_VALUE: Record<SortKey, (r: RegistryRow) => string | number | null> = {
  name: (r) => r.firstName.toLowerCase(),
  registered: (r) => r.registeredAt,
  calls: (r) => r.callCount,
  lastSale: (r) => r.lastSale?.ugxPerKg ?? null,
  vsVillage: (r) => r.priceVsVillage,
};

function matchesQuery(row: RegistryRow, needle: string): boolean {
  return [row.firstName, row.village, row.parish, row.subCounty, row.district].some((v) =>
    v.toLowerCase().includes(needle),
  );
}

function matchesPrice(row: RegistryRow, bucket: string): boolean {
  const v = row.priceVsVillage;
  if (!bucket) return true;
  if (bucket === "none") return v === null;
  if (v === null) return false;
  if (bucket === "below") return v < 1 - PRICE_TOLERANCE;
  if (bucket === "above") return v > 1 + PRICE_TOLERANCE;
  return Math.abs(v - 1) <= PRICE_TOLERANCE;
}

function sortRows(rows: RegistryRow[], key: SortKey, dir: SortDir): RegistryRow[] {
  const get = SORT_VALUE[key];
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = get(a);
    const y = get(b);
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sign;
  });
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

function FarmerTableRow({ row, isSelected, onSelect }: { row: RegistryRow; isSelected: boolean; onSelect: (id: number) => void }) {
  const [first, ...rest] = row.problems90d.map(labelProblem);
  return (
    <tr
      onClick={() => onSelect(row.id)}
      className={`border-b border-gray-100 cursor-pointer transition-colors ${isSelected ? "bg-blue-50/50" : "hover:bg-gray-50"}`}
    >
      <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">{row.firstName}</td>
      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{row.village}</td>
      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{row.district}</td>
      <td className={`px-4 py-3 text-gray-600 whitespace-nowrap ${WIDE}`}>{row.parish}</td>
      <td className={`px-4 py-3 text-gray-600 whitespace-nowrap ${WIDE}`}>{row.subCounty}</td>
      <td className="px-4 py-3 text-gray-600 whitespace-nowrap hidden lg:table-cell">{formatDate(row.registeredAt)}</td>
      <td className="px-4 py-3 text-right font-mono text-gray-700 whitespace-nowrap">{row.callCount}</td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        {row.lastSale ? (
          <>
            <div className="font-mono text-gray-700">{formatNumber(row.lastSale.ugxPerKg)}</div>
            <div className="text-xs text-faint">
              {shortForm(row.lastSale.form)} · {row.lastSale.buyerType ? labelBuyer(row.lastSale.buyerType) : "—"}
            </div>
          </>
        ) : (
          <Dash />
        )}
      </td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        <span className={indexPillClass(row.priceVsVillage)}>{formatIndex(row.priceVsVillage)}</span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap" title={row.problems90d.map(labelProblem).join(", ")}>
        {first === undefined ? (
          <Dash />
        ) : (
          <span className="inline-flex items-center gap-1.5">
            <span className={`${MAX_PROBLEM_WIDTH} truncate text-red-600 font-medium`}>{first}</span>
            {rest.length > 0 && <span className="text-xs text-muted">+{rest.length}</span>}
          </span>
        )}
      </td>
    </tr>
  );
}

export default function FarmersRegistry({ data }: { data: DashboardData }) {
  const rows = useMemo(() => registryRows(data), [data]);
  const searchParams = useSearchParams();
  const farmerParam = Number(searchParams.get("farmer"));
  const selectedId = Number.isInteger(farmerParam) && farmerParam > 0 ? farmerParam : null;
  const param = (key: FilterKey) => searchParams.get(key) ?? "";
  const query = param("q");
  const oneOf = (key: FilterKey, allowed: string[]) => (allowed.includes(param(key)) ? param(key) : "");
  const region = oneOf("region", REGIONS);
  const district = rows.some((r) => r.district === param("district") && (!region || r.region === region)) ? param("district") : "";
  const subCounty = district && rows.some((r) => r.district === district && r.subCounty === param("sub")) ? param("sub") : "";
  const buyer = oneOf("buyer", BUYER_OPTIONS);
  const priceBucket = oneOf("price", PRICE_OPTIONS.map((o) => o.value));
  const problemsOnly = param("problems") === "1";
  const sortParam = param("sort") as SortKey;
  const sort = {
    key: SORT_KEYS.includes(sortParam) ? sortParam : DEFAULT_SORT.key,
    dir: (param("dir") === "asc" || param("dir") === "desc" ? param("dir") : DEFAULT_SORT.dir) as SortDir,
  };
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [shown, setShown] = useState(PAGE_SIZE);

  // Filters live in the URL so other pages can link to e.g. /farmers?district=Masaka.
  const setFilters = useCallback(
    (patch: Partial<Record<FilterKey, string>>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value) params.set(key, value);
        else params.delete(key);
      }
      const qs = params.toString();
      window.history.replaceState(null, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
      setShown(PAGE_SIZE);
    },
    [searchParams, setShown],
  );

  const setFarmerParam = useCallback(
    (id: number | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (id === null) params.delete("farmer");
      else params.set("farmer", String(id));
      const qs = params.toString();
      const url = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
      // Open pushes; switching rows and closing replace, so Back never re-opens the peek.
      if (id !== null && selectedId === null) window.history.pushState(null, "", url);
      else window.history.replaceState(null, "", url);
    },
    [searchParams, selectedId],
  );
  const closePeek = useCallback(() => setFarmerParam(null), [setFarmerParam]);

  const districts = useMemo(
    () => [...new Set(rows.filter((r) => !region || r.region === region).map((r) => r.district))].sort(),
    [rows, region],
  );
  const subCounties = useMemo(
    () => [...new Set(rows.filter((r) => r.district === district).map((r) => r.subCounty))].sort(),
    [rows, district],
  );
  const villageCount = useMemo(
    () => new Set(rows.map((r) => `${r.district}/${r.subCounty}/${r.parish}/${r.village}`)).size,
    [rows],
  );

  const needle = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      sortRows(
        rows.filter(
          (r) =>
            (!needle || matchesQuery(r, needle)) &&
            (!region || r.region === region) &&
            (!district || r.district === district) &&
            (!subCounty || r.subCounty === subCounty) &&
            (!buyer || r.lastSale?.buyerType === buyer) &&
            matchesPrice(r, priceBucket) &&
            (!problemsOnly || r.problems90d.length > 0),
        ),
        sort.key,
        sort.dir,
      ),
    [rows, needle, region, district, subCounty, buyer, priceBucket, problemsOnly, sort.key, sort.dir],
  );
  const applySort = (key: string, dir: SortDir) => setFilters({ sort: key, dir });
  const onSort = (key: SortKey) =>
    applySort(key, sort.key === key ? (sort.dir === "asc" ? "desc" : "asc") : key === "name" ? "asc" : "desc");
  const visible = filtered.slice(0, shown);
  
  const clearAll = () => setFilters({ region: "", district: "", sub: "", buyer: "", price: "", problems: "" });
  const filterValues: Record<string, string> = { region, district, sub: subCounty, buyer, price: priceBucket, problems: problemsOnly ? "1" : "" };
  const toOptions = (list: string[]) => list.map((v) => ({ value: v, label: v }));
  const fields: FilterField[] = [
    { key: "region", label: "Region", options: toOptions(REGIONS) },
    { key: "district", label: "District", options: toOptions(districts) },
    { key: "sub", label: "Sub-county", options: toOptions(subCounties), disabledHint: district ? undefined : "Choose a district" },
    { key: "buyer", label: "Buyer", options: BUYER_OPTIONS.map((b) => ({ value: b, label: labelBuyer(b) })) },
    { key: "price", label: "Price vs village", options: PRICE_OPTIONS },
    { key: "problems", label: "Has problems", options: [], kind: "toggle" },
  ];
  const onFilterChange = (key: string, value: string) => {
    if (key === "region") {
      const isDistrictKept = !district || !value || rows.some((r) => r.region === value && r.district === district);
      setFilters(isDistrictKept ? { region: value } : { region: value, district: "", sub: "" });
    } else if (key === "district") setFilters({ district: value, sub: "" });
    else setFilters({ [key]: value });
  };
  const chips = fields
    .filter((f) => filterValues[f.key])
    .map((f) => {
      const v = filterValues[f.key];
      const label = f.kind === "toggle" ? f.label : `${f.label}: ${f.options.find((o) => o.value === v)?.label ?? v}`;
      return { key: f.key, label };
    });
  const openFilter = () => setIsFilterOpen(true);

  return (
    <div className="p-4 sm:p-6">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[240px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={query}
            placeholder="Search name or village"
            aria-label="Search name, village or area"
            onChange={(e) => setFilters({ q: e.target.value })}
            className={`${CONTROL} pl-9`}
          />
        </div>
        <FilterMenu fields={fields} values={filterValues} onChange={onFilterChange} onClearAll={clearAll} open={isFilterOpen} onOpenChange={setIsFilterOpen} />
        <SortMenu fields={SORT_FIELDS} sortKey={sort.key} dir={sort.dir} onChange={applySort} />
        <p className="ml-auto text-sm text-muted whitespace-nowrap">
          {formatNumber(rows.length)} farmers · {formatNumber(villageCount)} villages
        </p>
      </div>

      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {chips.map((c) => (
            <Chip
              key={c.key}
              label={c.label}
              onOpen={openFilter}
              onRemove={() => setFilters(c.key === "district" ? { district: "", sub: "" } : { [c.key]: "" })}
            />
          ))}
        </div>
      )}

      <div className="mb-6" />

      {filtered.length === 0 ? (
        <div className="bg-white border border-line rounded-[14px] flex flex-col items-center justify-center py-16 text-gray-400">
          <Users size={48} className="mb-4" />
          <p className="text-lg font-medium text-gray-500">No farmers found</p>
          <p className="text-sm text-gray-400 mt-1">{rows.length === 0 ? "Farmers appear here after their first call." : "Try adjusting your filters"}</p>
        </div>
      ) : (
        <>
          <div className="bg-white border border-line rounded-[14px] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line bg-gray-50">
                    <SortTh label="First name" k="name" sort={sort} onSort={onSort} className={`${TH} text-left`} />
                    <th className={`${TH} text-left`}>Village</th>
                    <th className={`${TH} text-left`}>District</th>
                    <th className={`${TH} text-left ${WIDE}`}>Parish</th>
                    <th className={`${TH} text-left ${WIDE}`}>Sub-county</th>
                    <SortTh label="Registered" k="registered" sort={sort} onSort={onSort} className={`${TH} text-left hidden lg:table-cell`} />
                    <SortTh label="Calls" k="calls" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <SortTh label="Last sale (UGX/kg)" k="lastSale" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <SortTh label="vs village" k="vsVillage" sort={sort} onSort={onSort} className={`${TH} text-right`} />
                    <th className={`${TH} text-left`}>Problems</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((row) => <FarmerTableRow key={row.id} row={row} isSelected={row.id === selectedId} onSelect={setFarmerParam} />)}
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
        </>
      )}
      {selectedId !== null && <FarmerPeek data={data} farmerId={selectedId} onClose={closePeek} />}
    </div>
  );
}
