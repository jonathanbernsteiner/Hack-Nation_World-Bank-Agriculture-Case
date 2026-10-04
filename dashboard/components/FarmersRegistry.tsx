"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, Search, Users, X } from "lucide-react";
import FarmerPeek from "@/components/FarmerPeek";
import { registryRows } from "@/lib/registry";
import type { RegistryRow } from "@/lib/registry";
import { formatDate, formatIndex, formatNumber, labelBuyer, labelProblem } from "@/lib/format";
import { indexPillClass, SyntheticTag } from "@/components/FarmersTable";
import type { BuyerType, DashboardData } from "@/lib/types";

const PAGE_SIZE = 50;
const NEW_DAYS = 30;
const INPUT = "text-sm border rounded-lg px-3 py-2 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors";
const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60";
const TOGGLE = "px-3 py-2 text-sm rounded-lg border inline-flex items-center gap-1.5";
const TOGGLE_OFF = `${TOGGLE} bg-white text-gray-600 border-gray-200 hover:bg-gray-50`;
const TOGGLE_ON = `${TOGGLE} bg-red-50 text-red-700 border-red-200`;
const CHIP = "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";
const PRICE_TOLERANCE = 0.03;
const REGIONS = ["Central", "Eastern", "Northern", "Western"];
const BUYER_OPTIONS: BuyerType[] = ["middleman", "cooperative", "other"];
const PRICE_OPTIONS = [
  { value: "below", label: "Below village by >3%" },
  { value: "same", label: "About the same" },
  { value: "above", label: "Above village by >3%" },
  { value: "none", label: "No recent sale" },
];
type SortKey = "registered" | "calls" | "lastSale" | "vsVillage";
type SortDir = "asc" | "desc";
const SORT_VALUE: Record<SortKey, (r: RegistryRow) => string | number | null> = {
  registered: (r) => r.registeredAt,
  calls: (r) => r.callCount,
  lastSale: (r) => r.lastSale?.date ?? null,
  vsVillage: (r) => r.priceVsVillage,
};

function addDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

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

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="text-xl font-bold text-gray-900">{formatNumber(value)}</span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className={CHIP}>
      {label}
      <button type="button" aria-label={`Remove ${label}`} onClick={onRemove} className="hover:text-blue-900">
        <X size={12} />
      </button>
    </span>
  );
}

function FarmerTableRow({ row, isSelected, onSelect }: { row: RegistryRow; isSelected: boolean; onSelect: (id: number) => void }) {
  return (
    <tr
      onClick={() => onSelect(row.id)}
      className={`border-b border-gray-100 cursor-pointer transition-colors ${isSelected ? "bg-blue-50/50" : "hover:bg-gray-50"}`}
    >
      <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
        <span className="inline-flex items-center gap-2">
          {row.firstName}
          {row.isSynthetic && <SyntheticTag />}
        </span>
      </td>
      <td className="px-4 py-3 text-gray-600 max-w-[180px] truncate">{row.village}</td>
      <td className="px-4 py-3 text-gray-600 hidden sm:table-cell">{row.parish}</td>
      <td className="px-4 py-3 text-gray-600 hidden lg:table-cell">{row.subCounty}</td>
      <td className="px-4 py-3 text-gray-600">{row.district}</td>
      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatDate(row.registeredAt)}</td>
      <td className="px-4 py-3 text-right font-mono text-gray-700">{row.callCount}</td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        {row.lastSale ? (
          <>
            <div className="font-mono text-gray-700">{formatNumber(row.lastSale.ugxPerKg)}</div>
            <div className="text-xs text-faint">{row.lastSale.buyerType ? labelBuyer(row.lastSale.buyerType) : "—"}</div>
          </>
        ) : (
          <Dash />
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <span className={indexPillClass(row.priceVsVillage)}>{formatIndex(row.priceVsVillage)}</span>
      </td>
      <td className="px-4 py-3 text-red-600 font-medium">
        {row.problems90d.length > 0 ? row.problems90d.map(labelProblem).join(", ") : <Dash />}
      </td>
    </tr>
  );
}

export default function FarmersRegistry({ data }: { data: DashboardData }) {
  const rows = useMemo(() => registryRows(data), [data]);
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") ?? "";
  const farmerParam = Number(searchParams.get("farmer"));
  const selectedId = Number.isInteger(farmerParam) && farmerParam > 0 ? farmerParam : null;
  const [query, setQuery] = useState(initialQuery);
  const [lastUrlQuery, setLastUrlQuery] = useState(initialQuery);
  const [region, setRegion] = useState("");
  const [district, setDistrict] = useState("");
  const [buyer, setBuyer] = useState("");
  const [priceBucket, setPriceBucket] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "registered", dir: "desc" });
  const [subCounty, setSubCounty] = useState("");
  const [problemsOnly, setProblemsOnly] = useState(false);
  const [shown, setShown] = useState(PAGE_SIZE);

  // The top-bar search navigates to /farmers?q=...; follow it when the URL parameter changes.
  if (initialQuery !== lastUrlQuery) {
    setLastUrlQuery(initialQuery);
    setQuery(initialQuery);
    setShown(PAGE_SIZE);
  }

  const setFarmerParam = useCallback(
    (id: number | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (id === null) params.delete("farmer");
      else params.set("farmer", String(id));
      const qs = params.toString();
      const url = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
      if (id !== null && selectedId !== null) window.history.replaceState(null, "", url);
      else window.history.pushState(null, "", url);
    },
    [searchParams, selectedId],
  );
  const closePeek = useCallback(() => setFarmerParam(null), [setFarmerParam]);

  const districts = useMemo(
    () => [...new Set(rows.filter((r) => !region || r.region === region).map((r) => r.district))].sort(),
    [rows, region],
  );
  const subCounties = useMemo(
    () => [...new Set(rows.filter((r) => (!region || r.region === region) && (!district || r.district === district)).map((r) => r.subCounty))].sort(),
    [rows, region, district],
  );
  const stats = useMemo(() => {
    const cutoff = addDays(data.today, -NEW_DAYS);
    return {
      villages: new Set(rows.map((r) => `${r.district}/${r.subCounty}/${r.parish}/${r.village}`)).size,
      recent: rows.filter((r) => r.registeredAt.slice(0, 10) > cutoff).length,
    };
  }, [rows, data.today]);

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
    [rows, needle, region, district, subCounty, buyer, priceBucket, problemsOnly, sort],
  );
  const onSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }));
  const visible = filtered.slice(0, shown);
  const hasFilters = Boolean(needle || region || district || subCounty || buyer || priceBucket || problemsOnly);

  const resetPaging = () => setShown(PAGE_SIZE);
  const clearAll = () => {
    setQuery("");
    setRegion("");
    setDistrict("");
    setSubCounty("");
    setBuyer("");
    setPriceBucket("");
    setProblemsOnly(false);
    resetPaging();
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Farmers</h1>
          <p className="text-sm text-muted mt-1 max-w-xl">
            Every first call registers a farmer with their village. First names only; PINs and phone numbers are never shown, and individual records can&apos;t be exported.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-x-8 gap-y-2 mb-6">
        <Stat value={rows.length} label="registered farmers" />
        <Stat value={stats.villages} label="villages" />
        <Stat value={stats.recent} label={`new in the last ${NEW_DAYS} days`} />
      </div>

      <div className="bg-white border border-line rounded-[14px] p-4 mb-6 space-y-3">
        <div className="flex flex-col sm:flex-row sm:flex-wrap gap-3">
          <div className="relative sm:w-64">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              placeholder="Search name, village or area"
              aria-label="Search name, village or area"
              onChange={(e) => { setQuery(e.target.value); resetPaging(); }}
              className={`${INPUT} w-full pl-9`}
            />
          </div>
          <select
            value={region}
            aria-label="Region"
            onChange={(e) => {
              const next = e.target.value;
              setRegion(next);
              if (district && next && !rows.some((r) => r.region === next && r.district === district)) { setDistrict(""); setSubCounty(""); }
              resetPaging();
            }}
            className={`${INPUT} min-w-[130px]`}
          >
            <option value="">All regions</option>
            {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select
            value={district}
            aria-label="District"
            onChange={(e) => { setDistrict(e.target.value); setSubCounty(""); resetPaging(); }}
            className={`${INPUT} min-w-[150px]`}
          >
            <option value="">All districts</option>
            {districts.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select
            value={subCounty}
            aria-label="Sub-county"
            onChange={(e) => { setSubCounty(e.target.value); resetPaging(); }}
            className={`${INPUT} min-w-[150px]`}
          >
            <option value="">All sub-counties</option>
            {subCounties.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={buyer} aria-label="Last sale buyer" onChange={(e) => { setBuyer(e.target.value); resetPaging(); }} className={`${INPUT} min-w-[150px]`}>
            <option value="">Any buyer</option>
            {BUYER_OPTIONS.map((b) => <option key={b} value={b}>Last sale to {labelBuyer(b).toLowerCase()}</option>)}
          </select>
          <select value={priceBucket} aria-label="Price vs village" onChange={(e) => { setPriceBucket(e.target.value); resetPaging(); }} className={`${INPUT} min-w-[170px]`}>
            <option value="">Price vs village: any</option>
            {PRICE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <button
            type="button"
            aria-pressed={problemsOnly}
            className={problemsOnly ? TOGGLE_ON : TOGGLE_OFF}
            onClick={() => { setProblemsOnly(!problemsOnly); resetPaging(); }}
          >
            Reported a problem (90 days)
          </button>
        </div>
        {hasFilters && (
          <div className="flex items-start justify-between gap-3 pt-1 border-t border-gray-100">
            <div className="flex flex-wrap gap-1.5 pt-2">
              {needle && <Chip label={`Search: ${query.trim()}`} onRemove={() => { setQuery(""); resetPaging(); }} />}
              {region && <Chip label={`Region: ${region}`} onRemove={() => { setRegion(""); resetPaging(); }} />}
              {district && <Chip label={`District: ${district}`} onRemove={() => { setDistrict(""); setSubCounty(""); resetPaging(); }} />}
              {subCounty && <Chip label={`Sub-county: ${subCounty}`} onRemove={() => { setSubCounty(""); resetPaging(); }} />}
              {buyer && <Chip label={`Last sale: ${labelBuyer(buyer as BuyerType)}`} onRemove={() => { setBuyer(""); resetPaging(); }} />}
              {priceBucket && <Chip label={`Price: ${PRICE_OPTIONS.find((o) => o.value === priceBucket)?.label ?? priceBucket}`} onRemove={() => { setPriceBucket(""); resetPaging(); }} />}
              {problemsOnly && <Chip label="Reported a problem" onRemove={() => { setProblemsOnly(false); resetPaging(); }} />}
            </div>
            <button type="button" onClick={clearAll} className="text-xs font-medium text-gray-500 hover:text-gray-700 whitespace-nowrap shrink-0 pt-2">
              Clear all
            </button>
          </div>
        )}
      </div>

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
                    <th className={`${TH} text-left`}>First name</th>
                    <th className={`${TH} text-left`}>Village</th>
                    <th className={`${TH} text-left hidden sm:table-cell`}>Parish</th>
                    <th className={`${TH} text-left hidden lg:table-cell`}>Sub-county</th>
                    <th className={`${TH} text-left`}>District</th>
                    <SortTh label="Registered" k="registered" sort={sort} onSort={onSort} className={`${TH} text-left`} />
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
            <p className="text-sm text-muted">Showing {visible.length} of {filtered.length}</p>
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
