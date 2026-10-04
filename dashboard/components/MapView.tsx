"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import type { AreaPath, AreaSummary, MapLayer, Warning } from "@/lib/types";
import { MIN_FARMERS, MIN_SALES, PRICE_LOW_INDEX, PROBLEM_MIN_FARMERS, PROBLEM_WINDOW_DAYS } from "@/lib/types";
import { formatIndex, formatNumber, labelLevel } from "@/lib/format";

interface MapViewProps {
  areas: AreaSummary[];
  selected: AreaSummary;
  layer: MapLayer;
  warnings: Warning[];
  onSelect: (path: AreaPath) => void;
}

const UGANDA_CENTER: [number, number] = [1.37, 32.29];
// Standard OpenStreetMap tiles (no key; greyed in globals.css to match DESIGN.md). CARTO basemaps now need a key.
const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

const COLOR_OK = "#10B981";
const COLOR_WARN = "#F59E0B";
const COLOR_BAD = "#DC2626";
const COLOR_NONE = "#94A3B8";
const PRICE_OK_INDEX = 0.97;
const PRICE_RADIUS = 14;
const WARNING_DOT_RADIUS = 5;

interface MarkerStyle {
  radius: number;
  color: string;
  fillColor: string;
  fillOpacity: number;
  weight: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function priceColor(index: number | null): string {
  if (index === null) return COLOR_NONE;
  if (index >= PRICE_OK_INDEX) return COLOR_OK;
  if (index >= PRICE_LOW_INDEX) return COLOR_WARN;
  return COLOR_BAD;
}

function containsWarning(area: AreaSummary, warnings: Warning[]): boolean {
  return warnings.some((w) => area.path.every((name, i) => w.path[i] === name));
}

function styleFor(area: AreaSummary, layer: MapLayer, hasWarning: boolean): MarkerStyle {
  if (layer === "farmers") {
    return {
      radius: clamp(8 + 4 * Math.sqrt(area.farmers), 8, 34),
      color: "#2563EB",
      fillColor: "#3B82F6",
      fillOpacity: 0.35,
      weight: 1.5,
    };
  }
  if (layer === "prices") {
    const color = priceColor(area.priceIndex);
    return { radius: PRICE_RADIUS, color, fillColor: color, fillOpacity: 0.55, weight: 1.5 };
  }
  if (hasWarning) {
    return { radius: 14, color: COLOR_BAD, fillColor: COLOR_BAD, fillOpacity: 0.25, weight: 3 };
  }
  return { radius: 6, color: "#CBD5E1", fillColor: "#CBD5E1", fillOpacity: 0.6, weight: 1 };
}

function labelFor(area: AreaSummary, layer: MapLayer): string | null {
  if (layer === "farmers") return formatNumber(area.farmers);
  if (layer === "prices" && area.priceIndex !== null) return formatIndex(area.priceIndex);
  return null;
}

function labelIcon(text: string): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `<div style="width:60px;margin-left:-30px;margin-top:-8px;text-align:center;font:600 11px/16px 'DM Sans',sans-serif;color:#0F172A;pointer-events:none">${text}</div>`,
    iconSize: [0, 0],
  });
}

function FitBounds({ areas, selected }: { areas: AreaSummary[]; selected: AreaSummary }) {
  const map = useMap();
  const latest = useRef({ areas, selected });
  const pathKey = selected.path.join("/");

  useEffect(() => {
    latest.current = { areas, selected };
  });

  useEffect(() => {
    const { areas: current, selected: sel } = latest.current;
    if (current.length === 0) {
      map.flyTo([sel.lat, sel.lon], 12);
      return;
    }
    const bounds = L.latLngBounds(current.map((a) => [a.lat, a.lon] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
  }, [map, pathKey]);

  return null;
}

function AreaTooltip({ area }: { area: AreaSummary }) {
  return (
    <Tooltip sticky>
      <div className="text-xs">
        <div className="font-semibold text-ink">
          {area.name} <span className="font-normal text-faint">{labelLevel(area.level)}</span>
        </div>
        <div>Farmers: {formatNumber(area.farmers)}</div>
        <div>Price: {formatIndex(area.priceIndex)} vs national</div>
        <div>Warnings: {area.warnings.length}</div>
      </div>
    </Tooltip>
  );
}

function Legend({ layer }: { layer: MapLayer }) {
  const swatches: { color: string; text: string }[] = [
    { color: COLOR_OK, text: "at or above national (≥ −3%)" },
    { color: COLOR_WARN, text: "3–15% below" },
    { color: COLOR_BAD, text: "more than 15% below" },
    { color: COLOR_NONE, text: `not enough sales (needs ${MIN_SALES} sales from ${MIN_FARMERS} farmers)` },
  ];
  return (
    <div className="absolute bottom-4 left-4 z-[1000] max-w-xs rounded-lg border border-line bg-white p-3 text-xs text-gray-600">
      {layer === "farmers" && <p>Circle size = registered farmers</p>}
      {layer === "prices" && (
        <ul className="space-y-1">
          {swatches.map((s) => (
            <li key={s.color} className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: s.color }} />
              {s.text}
            </li>
          ))}
        </ul>
      )}
      {layer === "warnings" && (
        <p>
          Red = at least {PROBLEM_MIN_FARMERS} farms in one parish report the same problem within {PROBLEM_WINDOW_DAYS}{" "}
          days, or prices ≥{Math.round((1 - PRICE_LOW_INDEX) * 100)}% below national
        </p>
      )}
    </div>
  );
}

export default function MapView({ areas, selected, layer, warnings, onSelect }: MapViewProps) {
  const isVillage = selected.level === "village";
  const isEmpty = areas.length === 0 && !isVillage;
  const shown = areas.length === 0 && isVillage ? [] : areas;

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={UGANDA_CENTER}
        zoom={7}
        maxZoom={13}
        scrollWheelZoom
        zoomControl={false}
        className="h-full w-full"
      >
        <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} className="map-tiles-muted" />
        <ZoomTopRight />
        <FitBounds areas={areas} selected={selected} />

        {shown.map((area) => {
          const style = styleFor(area, layer, containsWarning(area, warnings));
          const label = labelFor(area, layer);
          const key = area.path.join("/");
          return (
            <span key={key}>
              <CircleMarker
                center={[area.lat, area.lon]}
                pathOptions={style}
                radius={style.radius}
                eventHandlers={{ click: () => onSelect(area.path) }}
              >
                <AreaTooltip area={area} />
              </CircleMarker>
              {label && (
                <Marker
                  position={[area.lat, area.lon]}
                  icon={labelIcon(label)}
                  interactive={false}
                  keyboard={false}
                />
              )}
            </span>
          );
        })}

        {isVillage && (
          <CircleMarker
            center={[selected.lat, selected.lon]}
            radius={16}
            pathOptions={{ color: "#2563EB", fillColor: "#3B82F6", fillOpacity: 0.45, weight: 3 }}
          >
            <AreaTooltip area={selected} />
          </CircleMarker>
        )}

        {layer === "warnings" &&
          warnings.map((w) => (
            <CircleMarker
              key={w.id}
              center={[w.lat, w.lon]}
              radius={WARNING_DOT_RADIUS}
              pathOptions={{ color: "#FFFFFF", fillColor: COLOR_BAD, fillOpacity: 1, weight: 1.5 }}
            >
              <Tooltip>
                <div className="text-xs">
                  <div className="font-semibold text-ink">{w.title}</div>
                  <div>{w.detail}</div>
                </div>
              </Tooltip>
            </CircleMarker>
          ))}
      </MapContainer>

      <Legend layer={layer} />

      {isEmpty && (
        <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
          <div className="rounded-lg border border-line bg-white px-4 py-3 text-sm text-gray-600">
            No registered farmers here yet
          </div>
        </div>
      )}
    </div>
  );
}

function ZoomTopRight() {
  const map = useMap();
  useEffect(() => {
    const control = L.control.zoom({ position: "topright" });
    control.addTo(map);
    return () => {
      control.remove();
    };
  }, [map]);
  return null;
}
