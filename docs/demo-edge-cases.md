# Demo edge cases (what to keep out of the video)

Ranked by demo risk: how likely the item is to break the recorded happy path in `docs/demo-happy-path.md`, not by product severity. Sources: the "Demo risks:" lines in the closing comments of #11, #17, #19, #20, #21, #39 to #68 and #76, the review notes on their PRs, the starting list in #70, and the main agent's list. Duplicates are merged. Items already fixed are marked "fixed". No test-set text, names or numbers from the held-out eval rounds appear here; round 1 (#67) passed with no failing categories to report.

## Ranked register

| # | Edge case | What triggers it | What you would see | How to avoid it in the video | Sources |
|---|---|---|---|---|---|
| 1 | Keypad PIN unverified on the real phone line | Pressing 9001 then # on the imported Twilio number. Out-of-band DTMF is documented but was never observed live | Agent hears nothing and asks again, or waits; the first 30 seconds stall | Rehearse once on the real line before recording. If no response after about 5 seconds, say "tisa sifuri sifuri moja" (the script allows it). Keep the widget (spoken PIN) as backup | main agent (a), #39, #47, #56 |
| 2 | Kiswahili prompts, lines and transcripts not checked by a speaker | Any Kiswahili line in the script, the first message, the sample price sentence, the rust phrasing, the synthetic transcripts | A native speaker may find lines stiff or wrong; East African judges notice | Do not claim fluency. Say in the pitch that no Ugandan speaker has reviewed the Kiswahili. Get one check of the script lines if anyone can | main agent (g), #20, #46, #47 |
| 3 | Re-running synthetic `--reset` during a rehearsal | Running the loader with `--reset` after a rehearsal or demo call | The rehearsal call and its entries vanish from `/demo`; n drops | Never run `--reset` between rehearsal and recording. If you must, redo the rehearsal call afterwards | main agent (d), #44 |
| 4 | Rehearsal calls drift the medians | Every synthetic call adds one sale (n 28 goes to 29, the median can move from 5,950) | Spoken median differs from the script and from earlier cuts | Read n and the median off `/demo` right before recording and narrate those, not the numbers in this doc | #69, #20 (median depends on seed and V1 tuning) |
| 5 | Cold start on the first call | First tool call after idle on Vercel (Python, psycopg, anthropic imports) | A 2 to 4 second silence after the PIN | Warm `/api/health` twice and rehearse once a minute before recording | #40 |
| 6 | Processing latency after hang-up | Webhook to `processed` needs translate plus extract: about 1 to 2 minutes for a 3-minute call (a 120-line call took 40.8 s in translation alone) | `/demo` shows the call as `received` or without entries | Cut to `/demo` about 90 seconds after hang-up and wait. The pg_cron sweeper (active in production, every minute) re-processes stuck calls | #66, #58, #68, #21 |
| 7 | `/demo` 10 s refresh | Expanding a call or scrolling while the page refreshes | The expanded call collapses mid-take | Show entries in one pass on the collapsed row; re-take on a collapse | #21 |
| 8 | Fragile caller phrasings (extraction) | Bags plus a per-kilo price without kilos per bag; naming the buyer only by name; "recently", "at harvest" or the current month as the date; agreeing with the agent's median instead of stating your own price | Sale with no total, empty buyer type, null date, or a sale copied from the agent's median | Use the exact caller lines: kilos, price per kilo, "dalali", "jana". Say your own price ("elfu sita") | #65 |
| 9 | PIN redaction gaps | A PIN split over two turns, spoken before any tool call, or spoken with fewer than 3 digit words in a turn. Keypad digits appear as `<REDACTED>`. The earlier unredacted-transcript risk on #11 is fixed in #57 | A spoken PIN visible in the transcript panel on `/demo` | Use the keypad if it works. If spoken, say all four digits in one breath. Check the transcript panel before publishing the video | #11, #57, #39 |
| 10 | Merge out of dependency order broke production | The merge poller merged PRs out of dependency order (tools before the prices/history/places they import) and production returned errors for about 10 minutes. Fixed, poller disabled | Tool errors; the agent says information is unavailable | Do not merge anything on recording day without checking `/api/health` and one rehearsal call afterwards | main agent (b), #51, #52, #53 |
| 11 | Agent sync points at the wrong URL | `PUBLIC_BASE_URL` in the local `.env` still points at ngrok; `sync_agent` refuses a non-production URL | `--apply` fails, or tools point at a dead ngrok host | Run `PUBLIC_BASE_URL=https://hack-nation-world-bank-agriculture.vercel.app uv run python scripts/sync_agent.py --dry-run` first | main agent (e), #54 |
| 12 | International call | Caller dials a +1 number from a phone without credit or international calling | Call fails or drops | Check credit and international calling on the recording phone; place one test call. Backup is the browser widget | #69, #56 |
| 13 | Barge-in on the phone line | Speaking while the agent is mid-sentence; the first keypad press interrupts the agent by design | Agent cuts off or answers the wrong turn | Pause about one second after each agent turn | #69, #39 |
| 14 | Luganda or Lugisu rather than Kiswahili | Many rural Ugandan farmers speak Luganda or Lugisu more than Kiswahili; a judge points it out | "Would Nakato really speak Kiswahili?" | Say it in the pitch: Kiswahili is the demo language, Luganda is next. Do not claim farmer testing | main agent (h) |
| 15 | Timezone: "jana" and the date | Recording in the US evening, when Kampala (UTC+3) is already the next day | Extracted date is one day later than your "yesterday" | Narrate the date shown on `/demo`, or record before about 16:00 PDT | #69, #42 |
| 16 | Widget mic and placement | Browser blocks the microphone, or the widget is expected on `/demo` | No audio; or the call ends on refresh | The widget is only on `/` (public page), not `/demo`. Allow the mic beforehand. Spoken PIN only (no keypad on the widget) | #21, #39 |
| 17 | Open-Meteo is a live dependency | Open-Meteo slow, down or returning null fields | Agent says it cannot get the forecast | Ask the weather question last; re-take if it fails. The refusal path is correct behaviour | #50 |
| 18 | Disease advice gating | Uprooting or burning advice is officer-gated; twig borer advice lacks a sourced cut distance; practice rows rest on two UCDA handbooks only | Agent says "if the officer confirms" or gives no cut distance | Demo rust only. Do not ask about twig borer treatment or uprooting | #17, #45, #46 |
| 19 | Rust phrasing | A caller describing rust differently from the knowledge file | A different tell-apart question, or "not sure, the officer will follow up" | Use the exact lines at steps 13 and 15 | #46, #55 |
| 20 | Nearby twig-borer report disappears | The planted cluster needs at least 2 other farms in the sub-county with a report in the last 30 days | Agent has nothing nearby to mention | Do not script a line about neighbours' problems; check `nearby_reports` first if you want it | #49, #20 |
| 21 | History rows not in kg and UGX | Harvests in bags or non-UGX sales are not totalled | Missing totals | Her seeded rows are kg and UGX. Do not ask her to log a sale in bags | #49 |
| 22 | Location login (scene 2) | Wrong ASR for the district gives `none`; unknown villages need `create_unverified_village`; the village cache refreshes every 60 s per instance | "I could not find you", or follow-up questions | Use Masaka, Kyabakuza, Nakato; say the district first and slowly. The REVIEW flag is correct | #48, #52 |
| 23 | Null or national price | `red_cherry` has no national fallback and gives a null median in a thin village; p25 and p75 are null below 5 sales; a national figure is the Feb 2026 UCDA reference, not a local median | Agent says no price, or says "national reference" | Use kiboko (28 sales). Do not ask for red cherry | #43 |
| 24 | Extraction schema above documented limit | 25 nullable fields, above Anthropic's documented 16, accepted today | Works today; could be rejected after an API change | No model or schema change on recording day; one rehearsal after any deploy | main agent (f), #59 |
| 25 | Loader needs certifi on this Mac | The loader's urllib fails certificate verification here | `CERTIFICATE_VERIFY_FAILED` on load or reset | Set `SSL_CERT_FILE=$(python3 -c "import certifi;print(certifi.where())")`. Do not reload on recording day | main agent (c), #44 |
| 26 | Flaky LLM-judged agent tests | Using Agent Tests as a pre-recording gate | A test fails once and passes on retry; the happy test only checks `identify_farmer` | Do not read one red test as a regression; rehearse the full call yourself | #55 |
| 27 | Translation edge cases | A translation refusal (untested live); calls much over 3 minutes | Missing English column | Keep the call under 3 minutes; translation runs in the background | #58, #66 |
| 28 | Sweeper limits | Max 5 calls per sweep within 300 s; a missing Vault secret gives a silent 401 | Calls stay `received` | Cron is active in production. One call at a time | #66, #68 |
| 29 | First real webhook delivery | The #11 fixture was derived from a text conversation, not a real delivery | Call not stored | Production already holds 313 processed calls; still rehearse once | #11, #39 |
| 30 | Agent id in public PR history | An earlier agent id is public | Strangers could talk to the agent | Not a video risk; the tools check the secret. Mention if asked | #39, #47 |
| 31 | Missing synthetic-call cleanup | The curl check suggested in #69 would create a `p1-check` call row | A stray `in_call` row | Not created: the numbers were read with a read-only query. Nothing to clean | #69 |

## Say this in the pitch

Product limits judges may ask about; keep them out of the happy path and state them plainly:

- **Luganda vs Kiswahili.** The demo is in Kiswahili. Many rural Ugandan coffee farmers speak Luganda or Lugisu first. We did not test those.
- **Synthetic data.** All farmers, sales and prices are synthetic, built from UCDA price anchors. Nakato is not a real person. The Sep 2026 anchor is interpolated; village and parish names are indicative or invented.
- **4-digit PIN guessability.** 10,000 combinations, three tries per call, then locked. Location login exists for forgotten PINs and goes to review. It is not strong authentication.
- **Kiswahili speaker check.** Not done. The Kiswahili in the agent, the script and the transcripts is model-written.
- **Eval score.** Extraction reached 1.000 on the dev set (tuned on it, so optimistic) and 100% in held-out round 1 (#67): one round, no failing categories. The translation was not stress-tested and the 25-field schema is above Anthropic's documented 16.
- **Advice is gated.** Textbook steps only, no products or doses, urgent cases to the extension officer.

## Cross-check: happy-path steps and what could hit them

| Script step | Register entries |
|---|---|
| 0 to 1 Greeting and consent | 2, 5, 12, 13 |
| 2 to 3 PIN (keypad, then spoken) | 1, 5, 9, 10, 11, 13 |
| 4 Price in words | 4, 5, 10, 23, 24 |
| 5 to 11 Sale and read-back | 8, 13, 15, 24 |
| 12 to 16 Problem and rust advice | 2, 18, 19 |
| 17 to 18 Weather | 17 |
| 19 Goodbye | 13 |
| After hang-up on `/demo` | 3, 4, 6, 7, 15, 27, 28, 29 |
| Scene 2 (location) | 2, 22 |
| Backup widget | 1, 12, 16 |
| Setup before recording | 10, 11, 25, 26 |
