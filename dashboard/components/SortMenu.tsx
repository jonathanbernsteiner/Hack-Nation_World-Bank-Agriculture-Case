"use client";

import { useRef, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { useDismiss } from "@/components/useDismiss";

export type SortDirection = "asc" | "desc";

interface SortMenuProps {
  fields: { key: string; label: string }[];
  sortKey: string;
  dir: SortDirection;
  onChange: (key: string, dir: SortDirection) => void;
}

const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors";
const DIRECTIONS: { value: SortDirection; label: string }[] = [
  { value: "asc", label: "Ascending" },
  { value: "desc", label: "Descending" },
];

export default function SortMenu({ fields, sortKey, dir, onChange }: SortMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(ref, open, () => setOpen(false));
  const active = fields.find((f) => f.key === sortKey);

  return (
    <div ref={ref} className="relative">
      <button type="button" aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(!open)} className={BTN_SECONDARY}>
        <ArrowUpDown size={14} />
        Sort{active ? `: ${active.label} ${dir === "asc" ? "↑" : "↓"}` : ""}
      </button>
      {open && (
        <div role="dialog" aria-label="Sort" className="absolute left-0 z-30 mt-1 w-64 bg-white border border-line rounded-lg shadow-lg p-2">
          <div role="radiogroup" aria-label="Sort by">
            {fields.map((f) => (
              <label key={f.key} className="flex items-center gap-2 px-2 py-1.5 text-sm rounded-md hover:bg-gray-50 cursor-pointer">
                <input type="radio" name="sort-field" checked={f.key === sortKey} onChange={() => onChange(f.key, dir)} className="accent-blue-600" />
                {f.label}
              </label>
            ))}
          </div>
          <div className="flex gap-1 mt-1 pt-2 border-t border-gray-100 p-0.5">
            {DIRECTIONS.map((d) => (
              <button
                key={d.value}
                type="button"
                aria-pressed={dir === d.value}
                onClick={() => onChange(sortKey, d.value)}
                className={`flex-1 px-2 py-1 text-xs font-medium rounded-md border transition-colors ${
                  dir === d.value ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
