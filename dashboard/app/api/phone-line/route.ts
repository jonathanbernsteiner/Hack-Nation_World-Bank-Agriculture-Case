export const dynamic = "force-dynamic";

// Which agent answers the Twilio hotline number: the Swahili hotline or the English demo copy.
// Switching re-assigns the number in ElevenLabs; the key stays on the server.
const API = "https://api.elevenlabs.io/v1/convai/phone-numbers";

type Language = "en" | "sw";
type PhoneNumber = { phone_number_id: string; phone_number: string; assigned_agent?: { agent_id: string } | null };

function agents(): Record<Language, string | undefined> {
  return { en: process.env.ELEVENLABS_AGENT_ID_EN, sw: process.env.ELEVENLABS_AGENT_ID };
}

async function elevenlabs(path: string, init?: RequestInit): Promise<Response> {
  const key = process.env.ELEVENLABS_API_KEY;
  if (!key) throw new Error("ELEVENLABS_API_KEY is not set");
  return fetch(`${API}${path}`, { ...init, headers: { "xi-api-key": key, "Content-Type": "application/json" }, cache: "no-store" });
}

// The hotline has one number; it is the one assigned to either of our agents.
async function hotlineNumber(): Promise<PhoneNumber | null> {
  const res = await elevenlabs("");
  if (!res.ok) return null;
  const ids = Object.values(agents());
  const numbers = (await res.json()) as PhoneNumber[];
  return numbers.find((n) => n.assigned_agent && ids.includes(n.assigned_agent.agent_id)) ?? null;
}

function languageOf(number: PhoneNumber): Language | null {
  const id = number.assigned_agent?.agent_id;
  return id === agents().en ? "en" : id === agents().sw ? "sw" : null;
}

function switchEnabled(): boolean {
  return process.env.PHONE_LINE_SWITCH === "1";
}

export async function GET() {
  try {
    const number = await hotlineNumber();
    if (!number) return Response.json({ error: "no_number" }, { status: 404 });
    return Response.json({ phoneNumber: number.phone_number, language: languageOf(number), switchEnabled: switchEnabled() });
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503 });
  }
}

export async function POST(request: Request) {
  if (!switchEnabled()) return Response.json({ error: "disabled" }, { status: 403 });
  const { language } = (await request.json().catch(() => ({}))) as { language?: string };
  const agentId = language === "en" || language === "sw" ? agents()[language] : undefined;
  if (!agentId) return Response.json({ error: "bad_language" }, { status: 400 });
  try {
    const number = await hotlineNumber();
    if (!number) return Response.json({ error: "no_number" }, { status: 404 });
    const res = await elevenlabs(`/${number.phone_number_id}`, { method: "PATCH", body: JSON.stringify({ agent_id: agentId }) });
    if (!res.ok) return Response.json({ error: "switch_failed" }, { status: 502 });
    return Response.json({ phoneNumber: number.phone_number, language });
  } catch {
    return Response.json({ error: "unavailable" }, { status: 503 });
  }
}
