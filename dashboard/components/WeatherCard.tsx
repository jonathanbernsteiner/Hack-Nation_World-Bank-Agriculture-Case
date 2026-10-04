"use client";

import { useEffect, useState } from "react";
import { CloudRain, CloudSun, Sun } from "lucide-react";
import type { WeatherDay, WeatherResponse } from "@/lib/types";
import { formatDate } from "@/lib/format";

const RAIN_CHANCE_ICON_PCT = 50;
const RAIN_MM_ICON = 5;
const SKELETON_CELLS = [0, 1, 2];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

type Result = { key: string; days: WeatherDay[] | null }; // days null = failed

function weekday(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

function degrees(value: number | null): string {
  return value === null ? "–" : `${Math.round(value)}°`;
}

function DayIcon({ day }: { day: WeatherDay }) {
  const isWet = (day.rainChancePct ?? 0) >= RAIN_CHANCE_ICON_PCT || (day.rainMm ?? 0) >= RAIN_MM_ICON;
  if (isWet) return <CloudRain size={24} className="text-accent" />;
  const isSunny = (day.rainChancePct ?? 0) < 20;
  return isSunny ? <Sun size={24} className="text-amber-500" /> : <CloudSun size={24} className="text-amber-500" />;
}

interface WeatherCardProps {
  lat: number;
  lon: number;
}

export default function WeatherCard({ lat, lon }: WeatherCardProps) {
  const [result, setResult] = useState<Result | null>(null);
  const latKey = lat.toFixed(2);
  const lonKey = lon.toFixed(2);
  const key = `${latKey},${lonKey}`;

  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/weather?lat=${latKey}&lon=${lonKey}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`weather ${res.status}`);
        return res.json() as Promise<WeatherResponse>;
      })
      .then((data) => {
        setResult({ key, days: data.days.length > 0 ? data.days : null });
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setResult({ key, days: null });
      });
    return () => controller.abort();
  }, [latKey, lonKey, key]);

  const current = result !== null && result.key === key ? result : null;

  return (
    <div>
      <h2 className="text-base font-semibold text-ink mb-4">Weather, next 3 days</h2>
      {current === null && (
        <div className="grid grid-cols-3 gap-2">
          {SKELETON_CELLS.map((i) => (
            <div key={i} className="h-28 rounded-lg bg-gray-200 animate-pulse" />
          ))}
        </div>
      )}
      {current !== null && current.days === null && <p className="text-sm text-faint text-center py-6">Forecast unavailable right now.</p>}
      {current?.days &&  (
        <div className="grid grid-cols-3 gap-2">
          {current.days.map((day) => (
            <div key={day.date} className="border border-line rounded-lg p-3 flex flex-col items-center text-center gap-1">
              <div className="text-sm font-semibold text-ink">{weekday(day.date)}</div>
              <div className="text-xs text-faint">{formatDate(day.date)}</div>
              <DayIcon day={day} />
              <div className="text-sm font-medium text-gray-900">
                {degrees(day.tMaxC)} / {degrees(day.tMinC)}
              </div>
              <div className="text-xs text-muted">
                Rain {day.rainMm === null ? "–" : Math.round(day.rainMm)} mm ·{" "}
                {day.rainChancePct === null ? "–" : Math.round(day.rainChancePct)}%
              </div>
            </div>
          ))}
        </div>
      )}
      <p className="text-xs text-faint mt-3">Open-Meteo</p>
    </div>
  );
}
