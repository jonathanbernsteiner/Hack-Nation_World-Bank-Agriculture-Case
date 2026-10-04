"use client";

import { useMemo } from "react";
import { ChevronRight } from "lucide-react";
import AreaPanel from "@/components/AreaPanel";
import SidePanel from "@/components/SidePanel";
import { childrenOf, computeWarnings, farmersIn, summarize } from "@/lib/aggregate";
import type { AreaPath, DashboardData, Warning } from "@/lib/types";

const VILLAGE_DEPTH = 4;

interface AreaPeekProps {
  data: DashboardData;
  path: AreaPath;
  warnings?: Warning[];
  onSelect: (path: AreaPath) => void;
  onClose: () => void;
}

function Breadcrumb({ path, onSelect }: { path: AreaPath; onSelect: (path: AreaPath) => void }) {
  if (path.length < 2) return null;
  return (
    <nav aria-label="Area path" className="flex flex-wrap items-center gap-1 mb-4 text-sm">
      {path.slice(0, -1).map((name, i) => (
        <span key={path.slice(0, i + 1).join("|")} className="inline-flex items-center gap-1">
          <button type="button" onClick={() => onSelect(path.slice(0, i + 1))} className="text-accent hover:underline">
            {name}
          </button>
          <ChevronRight size={12} className="text-faint" />
        </span>
      ))}
      <span className="text-muted">{path[path.length - 1]}</span>
    </nav>
  );
}

export default function AreaPeek({ data, path, warnings, onSelect, onClose }: AreaPeekProps) {
  const allWarnings = useMemo(() => warnings ?? computeWarnings(data), [warnings, data]);
  const area = useMemo(() => summarize(data, path, allWarnings), [data, path, allWarnings]);
  const childAreas = useMemo(() => childrenOf(data, path, allWarnings), [data, path, allWarnings]);
  const farmers = useMemo(() => (path.length === VILLAGE_DEPTH ? farmersIn(data, path) : null), [data, path]);
  return (
    <SidePanel title={area.name} open onClose={onClose} link={{ href: `/map?path=${encodeURIComponent(path.join("|"))}`, label: "Open on map" }}>
      <Breadcrumb path={path} onSelect={onSelect} />
      <AreaPanel area={area} childAreas={childAreas} farmers={farmers} onSelect={onSelect} />
    </SidePanel>
  );
}
