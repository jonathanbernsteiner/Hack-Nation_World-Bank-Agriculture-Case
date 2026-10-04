"use client";

import { useEffect } from "react";
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from "react-leaflet";

const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const ZOOM = 12;

function QuietAttribution() {
  const map = useMap();
  useEffect(() => {
    map.attributionControl.setPrefix(false);
  }, [map]);
  return null;
}

export default function FarmerMap({ lat, lon, label }: { lat: number; lon: number; label: string }) {
  return (
    <MapContainer center={[lat, lon]} zoom={ZOOM} scrollWheelZoom={false} className="h-full w-full rounded-lg">
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} className="map-tiles-muted" />
      <QuietAttribution />
      <CircleMarker center={[lat, lon]} radius={9} pathOptions={{ color: "#fff", weight: 3, fillColor: "#3B82F6", fillOpacity: 1 }}>
        <Tooltip permanent direction="top" offset={[0, -10]}>
          {label}
        </Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
