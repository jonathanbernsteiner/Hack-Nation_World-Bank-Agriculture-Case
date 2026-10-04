"use client";

import { AlertTriangle, TrendingUp, Users } from "lucide-react";
import type { ComponentType } from "react";
import type { AreaPath, Level, MapLayer } from "@/lib/types";
import { LEVELS } from "@/lib/types";
import { labelLevel } from "@/lib/format";

interface MapToolbarProps {
  path: AreaPath;
  layer: MapLayer;
  onLayer: (layer: MapLayer) => void;
  onSelect: (path: AreaPath) => void;
}

const CHIPS: { layer: MapLayer; label: string; Icon: ComponentType<{ size?: number }> }[] = [
  { layer: "farmers", label: "Farmers", Icon: Users },
  { layer: "prices", label: "Prices", Icon: TrendingUp },
  { layer: "warnings", label: "Warnings", Icon: AlertTriangle },
];

const CHIP_BASE = "shrink-0 whitespace-nowrap px-3 py-2 text-sm rounded-lg border inline-flex items-center gap-1.5 transition-colors";
const CHIP_OFF = "bg-white text-gray-600 border-gray-200 hover:bg-gray-50";
const CHIP_ON = "bg-gray-800 text-white border-gray-800";
const CHIP_ON_ALERT = "bg-red-50 text-red-700 border-red-200";

export default function MapToolbar({ path, layer, onLayer, onSelect }: MapToolbarProps) {
  const names = ["Uganda", ...path];
  const level: Level = LEVELS[Math.min(path.length, LEVELS.length - 1)];

  return (
    <div className="flex flex-nowrap items-center justify-between gap-3 px-4 py-3 border-b border-line">
      <nav aria-label="Area" className="flex flex-1 min-w-0 items-center gap-1.5 text-sm truncate">
        {names.map((name, i) => {
          const isLast = i === names.length - 1;
          return (
            <span key={`${i}-${name}`} className="inline-flex min-w-0 items-center gap-1.5">
              {isLast ? (
                <span className="font-semibold text-ink truncate">{name}</span>
              ) : (
                <button
                  type="button"
                  className="text-gray-500 hover:text-gray-900 truncate"
                  onClick={() => onSelect(path.slice(0, i))}
                >
                  {name}
                </button>
              )}
              {!isLast && <span className="text-faint">›</span>}
            </span>
          );
        })}
        <span className="ml-1 text-xs text-faint whitespace-nowrap shrink-0">{labelLevel(level)}</span>
      </nav>

      <div className="flex shrink-0 flex-nowrap items-center gap-2">
        {CHIPS.map(({ layer: chipLayer, label, Icon }) => {
          const isOn = chipLayer === layer;
          const onClass = chipLayer === "warnings" ? CHIP_ON_ALERT : CHIP_ON;
          return (
            <button
              key={chipLayer}
              type="button"
              aria-pressed={isOn}
              className={`${CHIP_BASE} ${isOn ? onClass : CHIP_OFF}`}
              onClick={() => onLayer(chipLayer)}
            >
              <Icon size={14} />
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
