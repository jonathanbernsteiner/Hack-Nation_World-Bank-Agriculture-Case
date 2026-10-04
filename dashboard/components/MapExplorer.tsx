"use client";

import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { childrenOf, computeWarnings, farmersIn, inArea, summarize } from "@/lib/aggregate";
import type { AreaPath, DashboardData, MapLayer } from "@/lib/types";
import AreaPanel from "./AreaPanel";
import MapToolbar from "./MapToolbar";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => <div className="w-full h-full animate-pulse bg-gray-100" />,
});

const VILLAGE_DEPTH = 4;

/** Parse "A|B|C" into an area path; [] unless every segment exists in the data. */
function pathFromParam(param: string | null, data: DashboardData): AreaPath {
  if (!param) return [];
  const segments = param.split("|").slice(0, VILLAGE_DEPTH);
  const isValid = data.villages.some((v) => inArea(v, segments));
  return isValid ? segments : [];
}

export default function MapExplorer({ data }: { data: DashboardData }) {
  const searchParams = useSearchParams();
  const [path, setPath] = useState<AreaPath>(() => pathFromParam(searchParams.get("path"), data));
  const [layer, setLayer] = useState<MapLayer>("farmers");

  const warnings = useMemo(() => computeWarnings(data), [data]);
  const area = useMemo(() => summarize(data, path, warnings), [data, path, warnings]);
  const children = useMemo(() => childrenOf(data, path, warnings), [data, path, warnings]);
  const farmers = useMemo(
    () => (path.length === VILLAGE_DEPTH ? farmersIn(data, path) : null),
    [data, path],
  );

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6">
        <div className="bg-white border border-line rounded-xl overflow-hidden flex flex-col">
          <MapToolbar path={path} layer={layer} onLayer={setLayer} onSelect={setPath} />
          <div className="h-[60vh] min-h-[420px] xl:h-[calc(100vh-140px)] xl:min-h-[520px]">
            <MapView areas={children} selected={area} layer={layer} warnings={area.warnings} onSelect={setPath} />
          </div>
        </div>
        <div className="xl:max-h-[calc(100vh-112px)] xl:overflow-y-auto">
          <AreaPanel area={area} childAreas={children} farmers={farmers} onSelect={setPath} />
        </div>
      </div>
      <p className="text-xs text-faint">
        Prices: farmer-reported sales vs national monthly farm-gate reference (UCDA / MAAIF Coffee Department). Map tiles
        © OpenStreetMap contributors. Synthetic records are labelled.
      </p>
    </div>
  );
}
