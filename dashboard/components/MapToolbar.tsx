"use client";

import { AlertTriangle, TrendingUp, Users } from "lucide-react";
import type { AreaPath, Level, MapLayer } from "@/lib/types";
import { LEVELS } from "@/lib/types";
import { labelLevel } from "@/lib/format";
import Segmented from "./Segmented";
import type { SegmentedOption } from "./Segmented";

interface MapToolbarProps {
  path: AreaPath;
  layer: MapLayer;
  onLayer: (layer: MapLayer) => void;
  onSelect: (path: AreaPath) => void;
}

const LAYER_OPTIONS: SegmentedOption<MapLayer>[] = [
  { value: "farmers", label: "Farmers", icon: Users },
  { value: "prices", label: "Prices", icon: TrendingUp },
  { value: "warnings", label: "Warnings", icon: AlertTriangle },
];

export default function MapToolbar({ path, layer, onLayer, onSelect }: MapToolbarProps) {
  const names = ["Uganda", ...path];
  const level: Level = LEVELS[Math.min(path.length, LEVELS.length - 1)];

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3 border-b border-line">
      <nav aria-label="Area" className="flex basis-full sm:basis-0 flex-1 min-w-0 items-center gap-1.5 text-sm truncate">
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

      <Segmented options={LAYER_OPTIONS} value={layer} onChange={onLayer} ariaLabel="Map layer" />
    </div>
  );
}
