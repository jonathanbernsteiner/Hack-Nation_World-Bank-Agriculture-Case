# Hack-Nation: World Bank Agriculture Case

Our team's project for the Hack Nation hackathon (3 October 2026), working on the World Bank agriculture case.

## Shared services

Keys live in `.env`, which is never committed. Copy `.env.example` to `.env` and ask Jonathan for the values.

Status as of 3 Oct, 22:36 UTC:

| Service | What it's for | Status | Owner |
|---|---|---|---|
| Twilio | the phone number Noor calls in the demo | **Ready and tested** (22:36 UTC): trial account and number **+1 628 272 9173** (voice + SMS). A call from a verified phone gets through. Until the webhook (#14) is live, calls play Twilio's demo message | Jonathan |
| Supabase | a hosted copy of the data, later | **On hold (backlog, #19).** Project `hack-nation-farm-record` exists (`supabase/config.toml`) but isn't used | Jonathan |
| Vercel | hosting the dashboard, later | **On hold.** Set up and linked to this repo with keys (#28); the dashboard runs locally for now | Jonathan |

### Where the data lives

All data is saved **locally on the laptop** (the co-op box) in the SQLite ledger (#7), and the co-op dashboard (#3) runs on the same laptop and only reads it. Nothing goes to the cloud, so it works with Wi-Fi off. Decision: [comment on #1](https://github.com/jonathanbernsteiner/Hack-Nation_World-Bank-Agriculture-Case/issues/1#issuecomment-5974150277).

### Twilio

- Env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
- Demo call route (epic #2): basic phone → Twilio number → ngrok → Ethan's laptop. Jonathan points the number's voice webhook at the ngrok URL, so send him the URL once it's running.
- Free-trial limits:
  - Only verified phones can call the number. To add yours, send Jonathan your number; Twilio texts you a 6-digit code to pass back. Jonathan's phone is verified.
  - Every call first plays a trial notice and waits for the caller to press any key. Only then does our webhook run. Upgrade before recording the demo video.
  - The number can't call out to our phones on the trial, and the API's call log stayed empty in our test, so test by calling in.
  - One phone number, and the trial runs 30 days.
  - Upgrading the account removes these limits.
