"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  const router = useRouter();
  const [path, setPath] = useState<AreaPath>(() => pathFromParam(searchParams.get("path"), data));
  const context = useMemo(() => {
    const farmersByVillage = new Map<number, number>();
    for (const f of data.farmers) farmersByVillage.set(f.villageId, (farmersByVillage.get(f.villageId) ?? 0) + 1);
    const villages = data.villages
      .filter((v) => v.lat !== null && v.lon !== null)
      .map((v) => ({
        path: [v.district, v.subCounty, v.parish, v.village],
        name: `${v.village}, ${v.district}`,
        lat: v.lat as number,
        lon: v.lon as number,
        farmers: farmersByVillage.get(v.id) ?? 0,
      }));
    const byDistrict = new Map<string, { lat: number; lon: number; n: number; farmers: number }>();
    for (const v of villages) {
      const d = byDistrict.get(v.path[0]) ?? { lat: 0, lon: 0, n: 0, farmers: 0 };
      byDistrict.set(v.path[0], { lat: d.lat + v.lat, lon: d.lon + v.lon, n: d.n + 1, farmers: d.farmers + v.farmers });
    }
    const districts = [...byDistrict].map(([name, d]) => ({
      path: [name],
      name,
      lat: d.lat / d.n,
      lon: d.lon / d.n,
      farmers: d.farmers,
    }));
    return { villages, districts };
  }, [data]);
  const [hasUnknownPath, setHasUnknownPath] = useState(() => {
    const param = searchParams.get("path");
    return Boolean(param) && pathFromParam(param, data).length === 0;
  });
  const panelRef = useRef<HTMLDivElement>(null);

  const select = useCallback(
    (next: AreaPath) => {
      setPath(next);
      setHasUnknownPath(false);
      const query = next.length > 0 ? `?path=${encodeURIComponent(next.join("|"))}` : "";
      router.replace(`/map${query}`, { scroll: false });
    },
    [router],
  );

  useEffect(() => {
    panelRef.current?.scrollTo({ top: 0 });
  }, [path]);
  const [layer, setLayer] = useState<MapLayer>("farmers");

  const warnings = useMemo(() => computeWarnings(data), [data]);
  const area = useMemo(() => summarize(data, path, warnings), [data, path, warnings]);
  const children = useMemo(() => childrenOf(data, path, warnings), [data, path, warnings]);
  const farmers = useMemo(
    () => (path.length === VILLAGE_DEPTH ? farmersIn(data, path) : null),
    [data, path],
  );

  return (
    <div className="p-4 sm:p-6 flex flex-col gap-4">
      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-6 xl:h-[calc(100vh-104px)]">
        <div className="bg-white border border-line rounded-xl overflow-hidden flex flex-col xl:h-full xl:min-h-0">
          <MapToolbar path={path} layer={layer} onLayer={setLayer} onSelect={select} />
          <div className="h-[60vh] min-h-[420px] xl:h-auto xl:min-h-0 xl:flex-1">
            <MapView areas={children} selected={area} layer={layer} warnings={area.warnings} onSelect={select} context={context} />
          </div>
        </div>
        <div ref={panelRef} className="xl:h-full xl:min-h-0 xl:overflow-y-auto">
          <AreaPanel
            area={area}
            childAreas={children}
            farmers={farmers}
            onSelect={select}
            notice={hasUnknownPath ? "Area not found — showing Uganda" : null}
          />
        </div>
      </div>
      <p className="text-xs text-faint">
        Sources: UCDA / MAAIF, © OpenStreetMap contributors
      </p>
    </div>
  );
}
