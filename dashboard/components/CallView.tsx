"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ConversationProvider, useConversation } from "@elevenlabs/react";
import { Loader2, Mic, MicOff, Phone, PhoneOff, Wrench } from "lucide-react";

type Line = { id: number; role: "farmer" | "agent"; text: string };
type ToolEvent = { id: string; name: string; state: "running" | "done" | "error" };
type Entry = Record<string, string | number | boolean | null>;
type CallRecord = {
  status: string;
  identifiedBy?: string | null;
  consent?: string | null;
  error?: string | null;
  farmer?: { name: string; village: string | null; district: string | null } | null;
  entries?: Entry[];
};

const TOOL_LABELS: Record<string, string> = {
  identify_farmer: "Checking the caller's PIN",
  find_farmer_by_location: "Finding the caller by name and village",
  register_farmer: "Registering a new farmer",
  get_weather_forecast: "Getting the weather forecast",
};

const IDENTIFIED_BY: Record<string, string> = { pin: "PIN", location: "Name and village", registration: "New registration" };

const DONE = new Set(["processed", "failed", "needs_review"]);
const POLL_MS = 2500;
const POLL_LIMIT_MS = 4 * 60_000;

// Entry fields shown in the record, in reading order.
const ENTRY_FIELDS: [string, string][] = [
  ["kind", "Kind"],
  ["coffee_form", "Coffee form"],
  ["coffee_type", "Coffee type"],
  ["crop", "Crop"],
  ["amount", "Amount"],
  ["unit", "Unit"],
  ["amount_kg", "Kilograms"],
  ["price_total", "Paid in total"],
  ["currency", "Currency"],
  ["buyer_type", "Buyer"],
  ["buyer_name", "Buyer name"],
  ["paid_how", "Paid how"],
  ["date_sold", "Date sold"],
  ["activity", "Activity"],
  ["input", "Input"],
  ["symptom", "Symptom"],
  ["likely_disease", "Likely disease"],
  ["description", "Notes"],
];

function show(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString("en-US");
  return String(value).replaceAll("_", " ");
}

type Language = "en" | "sw";
const LANGUAGES: { key: Language; label: string }[] = [
  { key: "en", label: "English" },
  { key: "sw", label: "Kiswahili" },
];

export default function CallView({ agentIds }: { agentIds: Record<Language, string> }) {
  return (
    <ConversationProvider>
      <Call agentIds={agentIds} />
    </ConversationProvider>
  );
}

function Call({ agentIds }: { agentIds: Record<Language, string> }) {
  // One switch for both: the agent in the browser and the agent on the phone line.
  const [language, setLanguage] = useState<Language>("en");
  const [phoneNumber, setPhoneNumber] = useState<string | null>(null);
  const [switching, setSwitching] = useState(false);
  const [switchEnabled, setSwitchEnabled] = useState(false);
  const agentId = agentIds[language];

  useEffect(() => {
    fetch("/api/phone-line")
      .then((r) => (r.ok ? r.json() : null))
      .then((line) => {
        if (!line) return;
        setPhoneNumber(line.phoneNumber);
        setSwitchEnabled(line.switchEnabled === true);
        if (line.language === "en" || line.language === "sw") setLanguage(line.language);
      })
      .catch(() => {});
  }, []);

  async function chooseLanguage(next: Language) {
    if (next === language) return;
    const previous = language;
    setLanguage(next);
    setSwitching(true);
    setError(null);
    try {
      const res = await fetch("/api/phone-line", { method: "POST", body: JSON.stringify({ language: next }) });
      if (!res.ok) throw new Error();
    } catch {
      setLanguage(previous);
      setError("Could not switch the phone line, so the language was not changed.");
    } finally {
      setSwitching(false);
    }
  }
  const [lines, setLines] = useState<Line[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [record, setRecord] = useState<CallRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ended, setEnded] = useState(false);
  const [pollExpired, setPollExpired] = useState(false);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const idRef = useRef<string | null>(null);

  const poll = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/call/${encodeURIComponent(id)}`, { cache: "no-store" });
      if (res.ok) setRecord(await res.json());
    } catch {
      // A missed poll is retried on the next tick.
    }
  }, []);

  const conversation = useConversation({
    onConnect: ({ conversationId: id }) => {
      idRef.current = id;
      setConversationId(id);
    },
    onDisconnect: () => setEnded(true),
    onError: (message) => setError(message),
    onMessage: ({ message, event_id, role }) =>
      setLines((prev) => [...prev, { id: event_id ?? prev.length, role: role === "user" ? "farmer" : "agent", text: message }]),
    onAgentToolRequest: ({ tool_call_id, tool_name }) =>
      setTools((prev) => [...prev.filter((t) => t.id !== tool_call_id), { id: tool_call_id, name: tool_name, state: "running" }]),
    onAgentToolResponse: ({ tool_call_id, tool_name, is_error }) => {
      setTools((prev) => [
        ...prev.filter((t) => t.id !== tool_call_id),
        { id: tool_call_id, name: tool_name, state: is_error ? "error" : "done" },
      ]);
      // Refresh right away, so the caller fills in as soon as they are identified.
      if (idRef.current) void poll(idRef.current);
    },
  });

  const live = conversation.status === "connected" || conversation.status === "connecting";

  // Poll the hotline's record: the caller appears mid-call, the entries a minute or so after hang-up.
  useEffect(() => {
    if (!conversationId) return;
    if (record && DONE.has(record.status)) return;
    if (pollExpired) return;
    const timer = setInterval(() => poll(conversationId), POLL_MS);
    return () => clearInterval(timer);
  }, [conversationId, record, pollExpired, poll]);

  // Stop polling a few minutes after hang-up if the record never finishes.
  useEffect(() => {
    if (!ended) return;
    const timer = setTimeout(() => setPollExpired(true), POLL_LIMIT_MS);
    return () => clearTimeout(timer);
  }, [ended]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: "smooth" });
  }, [lines]);

  async function start() {
    setError(null);
    setLines([]);
    setTools([]);
    setRecord(null);
    setConversationId(null);
    setEnded(false);
    setPollExpired(false);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access is needed to call the hotline.");
      return;
    }
    conversation.startSession({ agentId, connectionType: "webrtc" });
  }


  return (
    <div className="p-4 sm:p-6 flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Live call</h1>
          <p className="text-sm text-muted mt-1">Talk to the hotline agent in your browser and watch the farmer&apos;s record fill in.</p>
          {phoneNumber && (
            <p className="text-sm text-muted mt-1">
              Or phone <span className="font-mono text-ink">{phoneNumber.replace(/^\+1(\d{3})(\d{3})(\d{4})$/, "+1 $1 $2 $3")}</span>; it answers in the
              same language.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div role="radiogroup" aria-label="Agent language" className="inline-flex rounded-lg border border-line bg-white p-0.5">
            {LANGUAGES.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={language === key}
                disabled={live || switching || !switchEnabled || !agentIds[key]}
                title={switchEnabled ? undefined : "Language is fixed"}
                onClick={() => chooseLanguage(key)}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors disabled:cursor-not-allowed ${
                  language === key ? "bg-navy text-white" : "text-gray-600 hover:text-gray-900 disabled:opacity-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          {switching && <Loader2 size={16} className="animate-spin text-accent" />}
          {live && (
            <button
              type="button"
              onClick={() => conversation.setMuted(!conversation.isMuted)}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg bg-white border border-line text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {conversation.isMuted ? <MicOff size={16} /> : <Mic size={16} />}
              {conversation.isMuted ? "Unmute" : "Mute"}
            </button>
          )}
          {live ? (
            <button
              type="button"
              onClick={() => conversation.endSession()}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
            >
              <PhoneOff size={16} /> Hang up
            </button>
          ) : (
            <button
              type="button"
              onClick={start}
              disabled={!agentId}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-accent text-white hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              <Phone size={16} /> {conversationId ? "Call again" : "Start call"}
            </button>
          )}
        </div>
      </div>

      {!agentId && (
        <p className="rounded-lg border border-line bg-white px-4 py-3 text-sm text-gray-600">Live calls are not available right now.</p>
      )}
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <section className="rounded-xl border border-line bg-white flex flex-col min-h-[28rem]">
          <header className="flex items-center justify-between px-4 py-3 border-b border-line">
            <h2 className="text-base font-semibold text-ink">Transcript</h2>
            {live && (
              <span className="inline-flex items-center gap-2 text-xs font-medium text-red-600">
                <span className="h-2 w-2 rounded-full bg-red-600 animate-pulse" />
                {conversation.status === "connecting" ? "Connecting" : conversation.isSpeaking ? "Agent speaking" : "Listening"}
              </span>
            )}
          </header>
          <div ref={transcriptRef} className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 max-h-[60vh]">
            {lines.length === 0 && (
              <p className="m-auto text-sm text-faint">{live ? "Say hello…" : "Press Start call, allow the microphone, and speak as a farmer."}</p>
            )}
            {lines.map((line) => (
              <div key={line.id} className={`flex flex-col max-w-[85%] ${line.role === "farmer" ? "self-end items-end" : "self-start"}`}>
                <span className="text-xs text-faint mb-1">{line.role === "farmer" ? "Farmer" : "Agent"}</span>
                <p
                  className={`rounded-2xl px-4 py-2 text-sm ${
                    line.role === "farmer" ? "bg-accent text-white rounded-br-sm" : "bg-surface border border-line text-ink rounded-bl-sm"
                  }`}
                >
                  {line.text}
                </p>
              </div>
            ))}
          </div>
          {tools.length > 0 && (
            <footer className="border-t border-line px-4 py-3 flex flex-wrap gap-2">
              {tools.map((t) => (
                <span key={t.id} className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700">
                  {t.state === "running" ? <Loader2 size={12} className="animate-spin" /> : <Wrench size={12} />}
                  {TOOL_LABELS[t.name] ?? t.name}
                  {t.state === "error" && <span className="text-red-600">failed</span>}
                </span>
              ))}
            </footer>
          )}
        </section>

        <Record record={record} hasCall={conversationId !== null} live={live} />
      </div>
    </div>
  );
}

function Field({ label, value, pending = false }: { label: string; value: unknown; pending?: boolean }) {
  const empty = value === null || value === undefined || value === "";
  return (
    <div className="flex justify-between gap-4 py-1.5 text-sm border-b border-divider last:border-0">
      <span className="text-muted">{label}</span>
      {empty && pending ? (
        <span className="h-4 w-20 rounded bg-gray-100 animate-pulse" aria-label="waiting" />
      ) : empty ? (
        <span className="text-faint">—</span>
      ) : (
        <span className="text-ink font-medium text-right">{show(value)}</span>
      )}
    </div>
  );
}

function Record({ record, hasCall, live }: { record: CallRecord | null; hasCall: boolean; live: boolean }) {
  const entries = record?.entries ?? [];
  const status = record?.status ?? "none";
  const pending = hasCall && !DONE.has(status);
  return (
    <section className="rounded-xl border border-line bg-white">
      <header className="px-4 py-3 border-b border-line">
        <h2 className="text-base font-semibold text-ink">Farmer record</h2>
        <p className="text-xs text-muted mt-0.5">
          The caller fills in when the agent identifies them; the entries after the call, once the AI has read the transcript.
        </p>
      </header>
      <div className="p-4 flex flex-col gap-5">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-faint mb-1">Caller</h3>
          <Field label="Name" value={record?.farmer?.name} pending={pending} />
          <Field label="Village" value={record?.farmer?.village} pending={pending} />
          <Field label="District" value={record?.farmer?.district} pending={pending} />
          <Field label="Identified by" value={record?.identifiedBy ? IDENTIFIED_BY[record.identifiedBy] ?? record.identifiedBy : null} pending={pending} />
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-faint mb-1">
            Entries{entries.length > 0 && ` (${entries.length})`}
          </h3>
          {!hasCall && <p className="text-sm text-faint py-2">No call yet.</p>}
          {hasCall && entries.length === 0 && (
            <p className="text-sm text-faint py-2">
              {live
                ? "Sales, harvests and problems are written after hang-up."
                : status === "processed"
                  ? record?.consent === "no"
                    ? "The caller did not consent, so nothing was saved."
                    : "Nothing to record from this call."
                  : status === "failed" || status === "needs_review"
                    ? "The AI could not finish this record; it is queued for review."
                    : "Waiting for the AI to read the transcript…"}
            </p>
          )}
          <div className="flex flex-col gap-3">
            {entries.map((entry, i) => (
              <div key={i} className="rounded-lg border border-line p-3">
                {ENTRY_FIELDS.filter(([key]) => entry[key] !== null && entry[key] !== undefined).map(([key, label]) => (
                  <Field key={key} label={label} value={entry[key]} />
                ))}
                {entry.evidence_quote && (
                  <blockquote className="mt-2 border-l-2 border-ai pl-3 text-sm italic text-gray-600">
                    &ldquo;{String(entry.evidence_quote)}&rdquo;
                    {entry.quote_verified === true && <span className="not-italic text-xs text-emerald-600 ml-2">verified quote</span>}
                  </blockquote>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
