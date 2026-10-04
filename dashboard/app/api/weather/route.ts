import { NextResponse } from "next/server";
import type { WeatherDay, WeatherResponse } from "@/lib/types";

const SOURCE = "Open-Meteo (CC BY 4.0)";
const TIMEOUT_MS = 5000;
const REVALIDATE_SECONDS = 3600;
const LAT_RANGE = { min: -2, max: 5 };
const LON_RANGE = { min: 29, max: 36 };

function parseCoord(value: string | null, min: number, max: number): number | null {
  if (value === null || value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

function emptyResponse(): NextResponse<WeatherResponse> {
  return NextResponse.json({ days: [], source: SOURCE });
}

function numberAt(list: unknown, i: number): number | null {
  if (!Array.isArray(list)) return null;
  const n = Number(list[i]);
  return list[i] === null || list[i] === undefined || !Number.isFinite(n) ? null : n;
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const lat = parseCoord(searchParams.get("lat"), LAT_RANGE.min, LAT_RANGE.max);
  const lon = parseCoord(searchParams.get("lon"), LON_RANGE.min, LON_RANGE.max);
  if (lat === null || lon === null) {
    return NextResponse.json({ error: "lat and lon must be numbers inside Uganda" }, { status: 400 });
  }

  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max" +
    "&timezone=Africa%2FKampala&forecast_days=3";

  try {
    const res = await fetch(url, {
      signal: AbortSignal.timeout(TIMEOUT_MS),
      next: { revalidate: REVALIDATE_SECONDS },
    });
    if (!res.ok) return emptyResponse();
    const json = (await res.json()) as { daily?: Record<string, unknown> };
    const daily = json.daily;
    if (!daily || !Array.isArray(daily.time)) return emptyResponse();
    const days: WeatherDay[] = daily.time.map((date, i) => ({
      date: String(date),
      tMaxC: numberAt(daily.temperature_2m_max, i),
      tMinC: numberAt(daily.temperature_2m_min, i),
      rainMm: numberAt(daily.precipitation_sum, i),
      rainChancePct: numberAt(daily.precipitation_probability_max, i),
    }));
    return NextResponse.json({ days, source: SOURCE } satisfies WeatherResponse);
  } catch {
    return emptyResponse();
  }
}
