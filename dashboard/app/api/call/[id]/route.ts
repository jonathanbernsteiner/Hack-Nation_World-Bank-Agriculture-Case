import { getSql } from "@/lib/db";

export const dynamic = "force-dynamic";

// The record the hotline is building for one conversation: who called (set during the call
// by the identify tools) and the entries (set after the call by the extraction pipeline).
// Never selects pin_hash or phone numbers.
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[\w-]{1,128}$/.test(id)) return Response.json({ error: "bad_id" }, { status: 400 });

  const sql = getSql();
  const [call] = await sql`
    select c.id, c.status, c.identified_by, c.consent, c.duration_secs, c.last_error,
           f.name as farmer_name, v.village, v.district
      from calls c
      left join farmers f on f.id = c.farmer_id
      left join villages v on v.id = f.village_id
     where c.conversation_id = ${id}`;
  if (!call) return Response.json({ status: "none" });

  const entries = await sql`
    select kind, crop, coffee_form, coffee_type, amount, unit, amount_kg, price_total, currency,
           date_sold, buyer_type, buyer_name, paid_how, activity, input, symptom, likely_disease,
           evidence_quote, quote_verified, confidence, description
      from entries where call_id = ${call.id} order by id`;

  return Response.json({
    status: call.status,
    identifiedBy: call.identified_by,
    consent: call.consent,
    durationSecs: call.duration_secs,
    error: call.last_error,
    farmer: call.farmer_name ? { name: call.farmer_name, village: call.village, district: call.district } : null,
    entries,
  });
}
