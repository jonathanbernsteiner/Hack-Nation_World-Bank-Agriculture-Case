"use client";

import { useRef, useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { useDismiss } from "@/components/useDismiss";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  placeholder: string;
  ariaLabel: string;
  disabled?: boolean;
  className?: string;
}

export default function Select({ value, options, onChange, placeholder, ariaLabel, disabled = false, className = "" }: SelectProps) {
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  useDismiss(ref, open, () => setOpen(false));
  const items: SelectOption[] = [{ value: "", label: placeholder }, ...options];
  const selected = options.find((o) => o.value === value);

  const openMenu = () => {
    setHighlight(Math.max(0, items.findIndex((o) => o.value === value)));
    setOpen(true);
  };
  const choose = (v: string) => {
    onChange(v);
    setOpen(false);
  };
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) return openMenu();
      const step = e.key === "ArrowDown" ? 1 : -1;
      setHighlight((h) => (h + step + items.length) % items.length);
    } else if (e.key === "Enter" && open) {
      e.preventDefault();
      choose(items[highlight].value);
    } else if (e.key === "Escape" && open) {
      e.stopPropagation();
      setOpen(false);
    }
  };

  return (
    <div ref={ref} className={`relative min-w-[160px] ${className}`}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={onKeyDown}
        className="h-9 w-full flex items-center justify-between gap-2 text-sm border rounded-lg px-3 border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors disabled:opacity-50 disabled:bg-gray-50 disabled:cursor-not-allowed"
      >
        <span className={`truncate ${selected ? "text-gray-900" : "text-gray-500"}`}>{selected?.label ?? placeholder}</span>
        <ChevronDown size={14} className="text-gray-400 shrink-0" />
      </button>
      {open && (
        <div role="listbox" aria-label={ariaLabel} className="absolute z-30 mt-1 w-full min-w-[180px] max-h-72 overflow-auto bg-white border border-line rounded-lg shadow-lg p-1">
          {items.map((o, i) => (
            <div
              key={o.value || "__any"}
              role="option"
              aria-selected={o.value === value}
              onMouseEnter={() => setHighlight(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(o.value)}
              className={`flex items-center justify-between px-2 py-1.5 text-sm rounded-md cursor-pointer ${i === highlight ? "bg-gray-50" : ""}`}
            >
              <span className="truncate">{o.label}</span>
              {o.value === value && <Check size={14} className="text-blue-600 shrink-0" />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
