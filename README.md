# Hack-Nation: World Bank Agriculture Case

Our team's project for the Hack Nation hackathon (3 October 2026), working on the World Bank agriculture case.

## Shared services

Keys live in `.env`, which is never committed. Copy `.env.example` to `.env` and ask Jonathan for the values.

Status as of 3 Oct, 22:10 UTC:

| Service | What it's for | Status | Owner |
|---|---|---|---|
| Twilio | the phone number Noor calls in the demo | Trial account set up. Phone number still pending: Twilio needs a verified phone first | Jonathan |
| Supabase | shared database, project `hack-nation-farm-record` (East US) | Project created and linked (`supabase/config.toml`) | Jonathan |
| Vercel | hosting, project `hack-nation-world-bank-agriculture-case` | Project linked | Jonathan |

### Twilio

- Env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
- Demo call route (epic #2): basic phone → Twilio number → ngrok → Ethan's laptop. Jonathan points the number's voice webhook at the ngrok URL, so send him the URL once it's running.
- Free-trial limits:
  - Only verified phones can call the number. To add yours, send Jonathan your number; Twilio calls you and you type a 6-digit code.
  - One phone number, and the trial runs 30 days.
  - Upgrading the account removes these limits.
