import { getSql } from "@/lib/db";
import {
  emptySearch,
  escapeLike,
  matchPages,
  normalizeQuery,
  type AreaLevel,
  type AreaResult,
  type FarmerResult,
  type SearchResponse,
} from "@/lib/search";

export const dynamic = "force-dynamic";

const MAX_AREAS = 8;
const MAX_FARMERS = 6;
const HEADERS = { "Cache-Control": "no-store" };

const json = (body: unknown, status = 200) => Response.json(body, { status, headers: HEADERS });

interface AreaRow {
  level: AreaLevel;
  name: string;
  district: string;
  sub_county: string | null;
  parish: string | null;
  region: string | null;
}

function toArea(r: AreaRow): AreaResult {
  const path = [r.district, r.sub_county, r.parish, r.level === "village" ? r.name : null]
    .slice(0, { district: 1, subcounty: 2, parish: 3, village: 4 }[r.level])
    .map(String);
  const parent = r.level === "district" ? (r.region ?? "") : path.slice(0, -1).join(" · ");
  return { level: r.level, name: r.name, path, parent };
}

export async function GET(req: Request): Promise<Response> {
  const q = normalizeQuery(new URL(req.url).searchParams.get("q"));
  if (!q) return json(emptySearch());

  const prefix = `${escapeLike(q)}%`;
  const contains = `%${escapeLike(q)}%`;
  try {
    const sql = getSql();
    const [areaRows, farmerRows] = await Promise.all([
      sql<AreaRow[]>`
        select level, name, district, sub_county, parish, region from (
          select distinct 'district' as level, 1 as ord, district as name, district, null::text as sub_county, null::text as parish, region from villages
          union
          select distinct 'subcounty', 2, sub_county, district, sub_county, null, null from villages
          union
          select distinct 'parish', 3, parish, district, sub_county, parish, null from villages
          union
          select distinct 'village', 4, village, district, sub_county, parish, null from villages
        ) a
        where name ilike ${contains}
        order by (name ilike ${prefix}) desc, ord, name
        limit ${MAX_AREAS}`,
      sql<{ id: number; first_name: string; village: string; district: string }[]>`
        select f.id, split_part(f.name, ' ', 1) as first_name, v.village, v.district
        from farmers f join villages v on v.id = f.village_id
        where split_part(f.name, ' ', 1) ilike ${prefix} or v.village ilike ${prefix}
        order by f.name
        limit ${MAX_FARMERS}`,
    ]);

    const areas = [...areaRows.map(toArea)].sort(
      (a, b) => LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level] || a.name.localeCompare(b.name),
    );
    const farmers: FarmerResult[] = farmerRows.map((r) => ({
      id: Number(r.id),
      firstName: String(r.first_name),
      village: String(r.village),
      district: String(r.district),
    }));
    const body: SearchResponse = { pages: matchPages(q), areas, farmers };
    return json(body);
  } catch (err) {
    console.error("search failed", err);
    return json({ error: "search failed" }, 500);
  }
}

const LEVEL_ORDER: Record<AreaLevel, number> = { district: 0, subcounty: 1, parish: 2, village: 3 };
