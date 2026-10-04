"use client";

import { useRef } from "react";
import { SlidersHorizontal } from "lucide-react";
import Select from "@/components/Select";
import { useDismiss } from "@/components/useDismiss";

export interface FilterField {
  key: string;
  label: string;
  options: { value: string; label: string }[];
  disabledHint?: string;
  kind?: "select" | "toggle";
}

interface FilterMenuProps {
  fields: FilterField[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onClearAll: () => void;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const BTN_SECONDARY = "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors";

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (next: boolean) => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-5 w-9 rounded-full transition-colors ${checked ? "bg-blue-600" : "bg-gray-300"}`}
    >
      <span className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-4" : ""}`} />
    </button>
  );
}

function FieldRow({ field, value, onChange }: { field: FilterField; value: string; onChange: (value: string) => void }) {
  const isDisabled = Boolean(field.disabledHint);
  return (
    <div className="flex items-center gap-2 px-1 py-1">
      <span className="w-24 shrink-0 text-sm text-muted">{field.label}</span>
      {field.kind === "toggle" ? (
        <Toggle label={field.label} checked={value === "1"} onChange={(next) => onChange(next ? "1" : "")} />
      ) : (
        <Select
          value={value}
          options={field.options}
          placeholder={field.disabledHint ?? "Any"}
          ariaLabel={field.label}
          disabled={isDisabled}
          onChange={onChange}
          className="flex-1"
        />
      )}
    </div>
  );
}

export default function FilterMenu({ fields, values, onChange, onClearAll, open, onOpenChange }: FilterMenuProps) {
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(ref, open, () => onOpenChange(false));
  const count = fields.filter((f) => values[f.key]).length;

  return (
    <div ref={ref} className="relative">
      <button type="button" aria-expanded={open} aria-haspopup="dialog" onClick={() => onOpenChange(!open)} className={BTN_SECONDARY}>
        <SlidersHorizontal size={14} />
        Filter
        {count > 0 && (
          <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-blue-600 text-white text-[11px] font-semibold">
            {count}
          </span>
        )}
      </button>
      {open && (
        <div role="dialog" aria-label="Filters" className="absolute left-0 z-30 mt-1 w-80 bg-white border border-line rounded-lg shadow-lg p-2">
          {fields.map((f) => (
            <FieldRow key={f.key} field={f} value={values[f.key] ?? ""} onChange={(v) => onChange(f.key, v)} />
          ))}
          <div className="flex items-center pt-2 mt-1 border-t border-gray-100 px-1">
            <button type="button" onClick={onClearAll} disabled={count === 0} className="text-xs font-medium text-gray-500 hover:text-gray-700 disabled:opacity-40">
              Clear all
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
