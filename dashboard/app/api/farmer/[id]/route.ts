import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

const CALLS_PAGE = 10;

type TranscriptLine = { role?: string; en?: string | null; sw?: string | null };

// One page of the farmer's calls, newest first. Safe columns only; one extra row tells whether more follow.
async function callsPage(sql: ReturnType<typeof getSql>, id: number, offset: number) {
  const rows = await sql`
    select id, received_at, status, duration_secs, transcript_lines, transcript_en, transcript_sw
      from calls where farmer_id = ${id}
     order by received_at desc, id desc limit ${CALLS_PAGE + 1} offset ${offset}`;
  return {
    hasMore: rows.length > CALLS_PAGE,
    calls: rows.slice(0, CALLS_PAGE).map((c) => {
      const lines = ((c.transcript_lines ?? []) as TranscriptLine[]).map((l) => ({
        role: l.role === "farmer" ? "farmer" : "agent",
        sw: l.sw || "",
        en: l.en || "",
        text: l.en || l.sw || "", // read by peeks still open from before the bilingual transcript; drop later
      }));
      const hasText = Boolean(c.transcript_sw || c.transcript_en);
      return {
        id: Number(c.id),
        receivedAt: c.received_at,
        status: c.status,
        durationSecs: c.duration_secs,
        lines,
        fallback: lines.length === 0 && hasText ? { sw: String(c.transcript_sw ?? ""), en: String(c.transcript_en ?? "") } : null,
      };
    }),
  };
}

// Extra detail for the farmer peek: farm position, harvests and the calls with their transcripts.
// `?callsOffset=N` returns only that page of calls. Never selects pin_hash, PINs, phone numbers or the name.
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) return Response.json({ error: "bad_id" }, { status: 400 });

  const sql = getSql();
  const offsetParam = new URL(request.url).searchParams.get("callsOffset");
  if (offsetParam !== null) {
    const offset = Number(offsetParam);
    if (!Number.isInteger(offset) || offset < 0) return Response.json({ error: "bad_offset" }, { status: 400 });
    return Response.json(await callsPage(sql, id, offset));
  }
  const [farmer] = await sql`
    select coalesce(f.lat, v.lat) as lat, coalesce(f.lon, v.lon) as lon
      from farmers f left join villages v on v.id = f.village_id
     where f.id = ${id}`;
  if (!farmer) return Response.json({ error: "not_found" }, { status: 404 });

  // Same harvest rule as the hotline's history (yield in kg), with amount_kg as a fallback.
  const harvests = await sql`
    select to_char(coalesce(e.date_sold, (c.received_at at time zone 'Africa/Kampala')::date), 'YYYY-MM-DD') as date,
           coalesce(case when e.unit = 'kg' then e.yield_amount end, e.amount_kg)::float8 as kg
      from entries e join calls c on c.id = e.call_id
     where e.farmer_id = ${id} and e.kind = 'harvest'
       and coalesce(case when e.unit = 'kg' then e.yield_amount end, e.amount_kg) > 0`;

  const page = await callsPage(sql, id, 0);

  return Response.json({
    lat: farmer.lat,
    lon: farmer.lon,
    harvests,
    ...page,
  });
}
