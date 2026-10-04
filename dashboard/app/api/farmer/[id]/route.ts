import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

const CALLS_SHOWN = 5;

type TranscriptLine = { role?: string; en?: string | null; sw?: string | null };

// Extra detail for the farmer peek: farm position, harvests and recent call transcripts.
// Never selects pin_hash, PINs, phone numbers or the full name.
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) return Response.json({ error: "bad_id" }, { status: 400 });

  const sql = getSql();
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

  const calls = await sql`
    select id, received_at, status, duration_secs, transcript_lines
      from calls where farmer_id = ${id} and transcript_lines is not null
     order by received_at desc limit ${CALLS_SHOWN}`;

  return Response.json({
    lat: farmer.lat,
    lon: farmer.lon,
    harvests,
    calls: calls.map((c) => ({
      id: Number(c.id),
      receivedAt: c.received_at,
      status: c.status,
      durationSecs: c.duration_secs,
      lines: ((c.transcript_lines ?? []) as TranscriptLine[]).map((l) => ({
        role: l.role === "farmer" ? "farmer" : "agent",
        text: l.en || l.sw || "",
      })),
    })),
  });
}
