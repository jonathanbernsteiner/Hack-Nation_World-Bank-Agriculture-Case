import CallView from "@/components/CallView";

export const dynamic = "force-dynamic";

export default function CallPage() {
  // Agent ids are public: the hotline's /demo page embeds one in the ElevenLabs widget too.
  // ELEVENLABS_AGENT_ID is the Swahili hotline (also on the phone line); _EN is the English demo copy.
  return <CallView agentIds={{ en: process.env.ELEVENLABS_AGENT_ID_EN ?? "", sw: process.env.ELEVENLABS_AGENT_ID ?? "" }} />;
}
