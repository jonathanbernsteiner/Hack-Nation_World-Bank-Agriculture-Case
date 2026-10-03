# Hack-Nation: World Bank Agriculture Case

Our team's project for the Hack Nation hackathon (3 October 2026), working on the World Bank agriculture case.

## Shared services

Keys live in `.env`, which is never committed. Copy `.env.example` to `.env` and ask Jonathan for the values.

Status as of 3 Oct, 23:45 UTC. **We moved from the laptop to the cloud** ([decision on #1](https://github.com/jonathanbernsteiner/Hack-Nation_World-Bank-Agriculture-Case/issues/1#issuecomment-5974664966)).

| Service | What it's for | Status | Owner |
|---|---|---|---|
| Supabase | all data: the ledger (`farmers`, `calls`, `entries`) and the call audio | **In use.** Project `hack-nation-farm-record` (East US, `supabase/config.toml`). Tables come from the migration in #19 | Jonathan |
| Vercel | hosting the app: co-op dashboard and the API that saves calls | **In use.** Project linked to this repo, Supabase keys already set (#28) | Jonathan |
| ElevenLabs | voice models: speech-to-text (Scribe), text-to-speech, the call agent | **Account ready** (Creator tier via Hack-Nation). Key being added | Jonathan |
| Twilio | the phone number Noor calls in the demo | **Ready and tested**: trial number **+1 628 272 9173** (voice + SMS). Probably connected through ElevenLabs next | Jonathan |
| Anthropic | Claude, the second model for LLM steps ElevenLabs doesn't cover (extraction, disease matching) | Key being added | Jonathan |

### How a call flows (plan)

```
Basic phone → Twilio number → ElevenLabs agent (Swahili call: PIN, recap, gap questions)
  → post-call webhook → Vercel API (POST /api/calls)
      → Claude: Swahili transcript → English + fixed-field entries (quote check)
      → Supabase: one calls row + its entries rows, audio in private storage
  → Co-op dashboard on Vercel reads Supabase
```

Which model runs which step is a proposal until the owners agree (see the decision link). **Fallback** if the ElevenLabs agent can't hold a Swahili call: our own Twilio webhook (`twilio_line/`) runs on Vercel and sends the recording to ElevenLabs Scribe. The local models in `server/pipeline/` (faster-whisper, NLLB) stay as an offline fallback and as the accuracy baseline.

### Where the data lives

Everything is in the Supabase project: the ledger tables, plus call recordings in a private storage bucket. Only server code (Vercel functions) uses the service-role key; the browser never gets it. Saving a call now needs internet, so the "Wi-Fi off" demo is gone; the offline co-op box is a next step in the pitch.

Callers' voices and transcripts pass through ElevenLabs, Anthropic and Supabase. The demo uses synthetic farmers only, labelled SYNTHETIC.

### Keys

| Variable | Service | Where it's used |
|---|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SUPABASE_*` | Supabase | browser-safe (row-level security applies) |
| `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `SUPABASE_DB_PASSWORD` | Supabase | server only |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`, `ELEVENLABS_WEBHOOK_SECRET` | ElevenLabs | server only |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Anthropic | server only |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | Twilio | server only (also pasted into ElevenLabs to import the number) |

Every server-only key also goes into the Vercel project settings (Production + Preview), so the deployed API can use it.

### Twilio

- Env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
- Demo call route (epic #2), planned: basic phone → Twilio number → ElevenLabs agent. ElevenLabs sets the number's webhooks itself when the number is imported. Fallback: our webhook in `twilio_line/` on Vercel. The old route through ngrok to a laptop is only for local testing now.
- Free-trial limits:
  - Only verified phones can call the number. To add yours, send Jonathan your number; Twilio texts you a 6-digit code to pass back. Jonathan's phone is verified.
  - Every call first plays a trial notice and waits for the caller to press any key. Only then does our webhook run. Upgrade before recording the demo video.
  - The number can't call out to our phones on the trial, and the API's call log stayed empty in our test, so test by calling in.
  - One phone number, and the trial runs 30 days.
  - Upgrading the account removes these limits.
