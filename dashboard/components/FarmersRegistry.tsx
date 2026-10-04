"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, Search, Users, X } from "lucide-react";
import { registryRows } from "@/lib/registry";
import type { RegistryRow } from "@/lib/registry";
import { formatDate, formatIndex, formatNumber, labelBuyer, labelProblem } from "@/lib/format";
import { indexPillClass, SyntheticTag } from "@/components/FarmersTable";
import type { DashboardData } from "@/lib/types";

const PAGE_SIZE = 50;
const NEW_DAYS = 30;
const INPUT = "text-sm border rounded-lg px-3 py-2 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors";
const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-60";
const TOGGLE = "px-3 py-2 text-sm rounded-lg border inline-flex items-center gap-1.5";
const TOGGLE_OFF = `${TOGGLE} bg-white text-gray-600 border-gray-200 hover:bg-gray-50`;
const TOGGLE_ON = `${TOGGLE} bg-red-50 text-red-700 border-red-200`;
const CHIP = "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-50 text-blue-700 border border-blue-200";
const TH = "font-medium text-muted px-4 py-3 whitespace-nowrap";
const CSV_HEADERS = ["First name", "Village", "Parish", "Sub-county", "District", "Registered", "Calls", "Last sale (UGX/kg)", "Buyer", "vs village", "Problems (90 days)"];

function addDays(date: string, days: number): string {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function matchesQuery(row: RegistryRow, needle: string): boolean {
  return [row.firstName, row.village, row.parish, row.subCounty, row.district].some((v) =>
    v.toLowerCase().includes(needle),
  );
}

function csvCell(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function toCsv(rows: RegistryRow[]): string {
  const lines = rows.map((r) =>
    [
      r.firstName, r.village, r.parish, r.subCounty, r.district, r.registeredAt.slice(0, 10), r.callCount,
      r.lastSale?.ugxPerKg ?? "", r.lastSale?.buyerType ? labelBuyer(r.lastSale.buyerType) : "",
      r.priceVsVillage === null ? "" : formatIndex(r.priceVsVillage), r.problems90d.map(labelProblem).join("; "),
    ].map(csvCell).join(","),
  );
  return [CSV_HEADERS.map(csvCell).join(","), ...lines].join("\n");
}

function downloadCsv(rows: RegistryRow[]) {
  const url = URL.createObjectURL(new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "farmers.csv";
  link.click();
  URL.revokeObjectURL(url);
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

function FarmerTableRow({ row }: { row: RegistryRow }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
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
  const initialQuery = useSearchParams().get("q") ?? "";
  const [query, setQuery] = useState(initialQuery);
  const [lastUrlQuery, setLastUrlQuery] = useState(initialQuery);
  const [district, setDistrict] = useState("");
  const [subCounty, setSubCounty] = useState("");
  const [problemsOnly, setProblemsOnly] = useState(false);
  const [shown, setShown] = useState(PAGE_SIZE);

  // The top-bar search navigates to /farmers?q=...; follow it when the URL parameter changes.
  if (initialQuery !== lastUrlQuery) {
    setLastUrlQuery(initialQuery);
    setQuery(initialQuery);
    setShown(PAGE_SIZE);
  }

  const districts = useMemo(() => [...new Set(rows.map((r) => r.district))].sort(), [rows]);
  const subCounties = useMemo(
    () => [...new Set(rows.filter((r) => !district || r.district === district).map((r) => r.subCounty))].sort(),
    [rows, district],
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
      rows.filter(
        (r) =>
          (!needle || matchesQuery(r, needle)) &&
          (!district || r.district === district) &&
          (!subCounty || r.subCounty === subCounty) &&
          (!problemsOnly || r.problems90d.length > 0),
      ),
    [rows, needle, district, subCounty, problemsOnly],
  );
  const visible = filtered.slice(0, shown);
  const hasFilters = Boolean(needle || district || subCounty || problemsOnly);

  const resetPaging = () => setShown(PAGE_SIZE);
  const clearAll = () => {
    setQuery("");
    setDistrict("");
    setSubCounty("");
    setProblemsOnly(false);
    resetPaging();
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <div className="flex items-start justify-between mb-4 gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Farmers</h1>
          <p className="text-sm text-muted mt-1 max-w-xl">
            Every first call registers a farmer with their village. First names only; PINs and phone numbers are never shown.
          </p>
        </div>
        <button type="button" className={BTN_SECONDARY} disabled={filtered.length === 0} onClick={() => downloadCsv(filtered)}>
          <Download size={14} /> Download CSV
        </button>
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
              {district && <Chip label={`District: ${district}`} onRemove={() => { setDistrict(""); setSubCounty(""); resetPaging(); }} />}
              {subCounty && <Chip label={`Sub-county: ${subCounty}`} onRemove={() => { setSubCounty(""); resetPaging(); }} />}
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
                    <th className={`${TH} text-left`}>Registered</th>
                    <th className={`${TH} text-right`}>Calls</th>
                    <th className={`${TH} text-right`}>Last sale (UGX/kg)</th>
                    <th className={`${TH} text-right`}>vs village</th>
                    <th className={`${TH} text-left`}>Problems</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((row) => <FarmerTableRow key={row.id} row={row} />)}
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
    </div>
  );
}
