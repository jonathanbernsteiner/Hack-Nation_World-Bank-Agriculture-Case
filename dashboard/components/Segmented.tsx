"use client";

import type { LucideIcon } from "lucide-react";

export interface SegmentedOption<T extends string> {
  value: T;
  label: string;
  icon?: LucideIcon;
}

interface SegmentedProps<T extends string> {
  options: SegmentedOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
}

/** One toggle style for every "pick one view" control (map layers, coffee forms). */
export default function Segmented<T extends string>({ options, value, onChange, ariaLabel }: SegmentedProps<T>) {
  return (
    <div role="tablist" aria-label={ariaLabel} className="inline-flex shrink-0 p-0.5 rounded-lg border border-line bg-gray-50">
      {options.map(({ value: optionValue, label, icon: Icon }) => {
        const isOn = optionValue === value;
        return (
          <button
            key={optionValue}
            type="button"
            role="tab"
            aria-selected={isOn}
            onClick={() => onChange(optionValue)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md whitespace-nowrap transition-colors ${
              isOn ? "bg-white text-ink ring-1 ring-line shadow-sm" : "text-gray-500 hover:text-gray-900"
            }`}
          >
            {Icon && <Icon size={14} />}
            {label}
          </button>
        );
      })}
    </div>
  );
}
