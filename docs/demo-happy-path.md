# Demo happy path (spec section 11)

Setting: Uganda, Kiswahili. Demo farmer: **Nakato (SYNTHETIC)**, keypad PIN **9001**, Kyabakuza village, Kasaali parish, Kyanamukaaka sub-county, Masaka district, Central region, robusta, main form kiboko. PINs 9000-9099 are reserved for synthetic and demo farmers. All data on the line is synthetic.

## Seeded numbers (read from production, 2026-10-03 about 22:00 PDT)

Read-only: `hotline.profile.build_profile` for PIN 9001 against the production database. No tool endpoint was called, so no `calls` row was created. The numbers drift (see "Before you record").

| What | Value |
|---|---|
| Village kiboko median (Kyabakuza) | **5,950 UGX/kg**, spoken as "elfu tano na mia tisa na hamsini" |
| Band p25 to p75 | 5,400 to 6,700 UGX/kg |
| Basis | 28 sales by 5 farmers, window 2025-10-04 to 2026-10-04, level village, includes synthetic |
| Other form (faq) | **11,950 UGX/kg** at parish level from 17 sales, "elfu kumi na moja na mia tisa na hamsini" |
| Coffee year 2025/26 | harvest 1,510 kg, sold 1,335 kg, average 6,050 UGX/kg |
| Coffee year 2024/25 | harvest 1,280 kg, sold 1,150 kg, average 7,000 UGX/kg |
| Last sales | 2026-07-18: 400 kg kiboko at 5,300 (middleman); 2026-06-27: 300 kg at 5,850 (cooperative); 2026-06-06: 250 kg at 6,050 (cooperative) |
| Nearby problem reports | black coffee twig borer, 3 farms in the parish, last 30 days (it ages out of the 30-day window, see edge cases) |
| Past problems on her record | none |

Money is spoken from `median_words_sw`, never from digits.

## Phone line

Number: **+1 628 272 9173** (Twilio, answered by the ElevenLabs agent). It is an international call to a +1 number. The agent asks for the PIN on the keypad, followed by `#`, and accepts the spoken PIN ("tisa sifuri sifuri moja") as fallback. **Keypad delivery over the real phone line is unverified until the first live call.** If the keypad does nothing after about 5 seconds, say the PIN; the script covers both.

## Script

Kiswahili lines are drafts: **no Kiswahili or Ugandan speaker has checked them.** Short sentences, one question per turn, numbers as words. Agent lines are what the agent should say; the real wording differs slightly each call, so the check is the content (the number, the read-back, "dalili zinafanana sana na ...").

Pause about one second after every agent turn. Barge-in on the phone line breaks turn-taking.

| # | Speaker | Kiswahili | English gloss |
|---|---|---|---|
| 0 | Agent | Habari, hii ni Simu ya Kahawa. Mimi ni kompyuta, si mtu. Simu hii inarekodiwa ili kutunza kumbukumbu ya shamba lako. Je, unakubali? Kama unakubali, bonyeza au taja nambari zako nne za siri, au sema "nimesahau", au sema "mimi ni mgeni". | Hello, this is the Coffee Line. I am a computer, not a person. This call is recorded to keep your farm record. Do you agree? If you agree, press or say your four-digit PIN, or say "I forgot", or say "I am new". |
| 1 | Nakato | Ndiyo, nakubali. | Yes, I agree. |
| 2 | Agent | Tafadhali bonyeza nambari yako ya siri, kisha alama ya reli. | Please press your PIN, then the hash key. |
| 3 | Nakato | (keypad) 9 0 0 1 # . If nothing happens: "tisa sifuri sifuri moja". | PIN 9001 |
| 4 | Agent | Karibu, Nakato wa Kyabakuza. Bei ya kati ya kiboko hapa Kyabakuza kwa miezi kumi na miwili iliyopita ni shilingi **elfu tano na mia tisa na hamsini** kwa kilo, kutoka ripoti 28. | Welcome, Nakato of Kyabakuza. The middle price of kiboko here in Kyabakuza over the last twelve months is 5,950 shillings per kilo, from 28 reports. |
| 5 | Nakato | Jana niliuza kilo mia tatu za kiboko. | Yesterday I sold three hundred kilos of kiboko. |
| 6 | Agent | Ulipata shilingi ngapi kwa kilo? | How many shillings per kilo? |
| 7 | Nakato | Elfu sita kwa kilo, jumla milioni moja na laki nane. | Six thousand a kilo, total one million eight hundred thousand. |
| 8 | Agent | Ulimuuzia nani, na ulilipwa vipi? | Who did you sell to, and how were you paid? |
| 9 | Nakato | Dalali. Nililipwa kwa simu, pesa za mtandao. | A middleman. Paid by mobile money. |
| 10 | Agent | Nimeandika: kilo mia tatu, kiboko, shilingi milioni moja na laki nane, dalali, pesa za mtandao, jana. Ni sahihi? | I noted: 300 kg kiboko, 1,800,000 shillings, middleman, mobile money, yesterday. Is it correct? |
| 11 | Nakato | Ndiyo, ni sahihi. | Yes, it is correct. |
| 12 | Agent | Kahawa yako ina tatizo lolote mwaka huu? | Does your coffee have any problem this year? |
| 13 | Nakato | Ndiyo. Majani yana unga wa rangi ya chungwa chini, unaoshika kwenye kidole, na majani yanaanguka. | Yes. The leaves have orange powder underneath that rubs onto my finger, and leaves are falling. |
| 14 | Agent | Je, unga huo unatoka kwenye madoa ya kahawia yenye pete ya njano? | Does the powder come from brown spots with a yellow ring? (tell-apart question against brown eye spot) |
| 15 | Nakato | Hapana, ni unga wa chungwa tu chini ya jani. | No, just orange powder under the leaf. |
| 16 | Agent | Dalili zinafanana sana na kutu ya majani. Pogoa, palilia, weka mbolea, na kagua kila wiki wakati wa mvua. Majani mengi yanaanguka, kwa hiyo ongea na afisa ugani wiki hii. | The signs closely match leaf rust. Prune, weed, manure, and check weekly in the rains. Many leaves are falling, so talk to the extension officer this week. |
| 17 | Nakato | Hali ya hewa itakuwaje? | How will the weather be? |
| 18 | Agent | (Open-Meteo forecast for Masaka: rain days, total rain, heavy rain days.) | (forecast, source named as Open-Meteo) |
| 19 | Agent | Asante, Nakato. Rekodi yako itatunzwa. Kwaheri. | Thank you, Nakato. Your record will be kept. Goodbye. |

Rules the caller lines follow, so extraction does not trip (from #65): say the **kilos and the price per kilo** (no bags); say the buyer type ("dalali", a middleman, as in her history) rather than a name; say your own price, never "yes" to the agent's median; "jana" is fine, do not say "recently" or the current month.

The agent must not name a spray or dose, give another farmer's price, or call rust certain. If the agent mentions the twig borer cluster nearby, that is fine ("if the officer confirms" applies to uprooting or burning).

## What the screen shows (`/demo`, Basic auth, refreshes every 10 s, within 3 minutes of hanging up)

Processing takes roughly 1 to 2 minutes after hang-up (translate plus extract); the pg_cron sweeper (every minute) is the safety net. Cut to `/demo` after hang-up and do not touch the page; the refresh collapses anything you expand.

- A new call row, Kampala time, status `processed`, identified by `pin`, SYNTHETIC badge (rehearsal and demo calls inherit synthetic).
- Kiswahili | English transcript side by side; the PIN appears as `[PIN]` or `<REDACTED>`.
- **Sale:** kiboko, 300 kg, 1,800,000 UGX, middleman, mobile money, quote ticked.
- **Observation:** leaf rust (`not_sure` is also acceptable if the tell-apart answer was unclear), quote ticked.
- Kyabakuza kiboko median and n: **5,950 and 28 before the call**; n goes up by 1 after the call (29), median can shift slightly because the new sale is 6,000.
- No REVIEW flag expected. A flag appears if confidence is under 0.6, a quote is not found, or identification was by location.

## Scene 2 (location, no PIN)

Caller says "nimesahau", then gives first name, district and village (Nakato, Masaka, Kyabakuza). The call shows `identified by location` and the REVIEW flag, and the agent gives only the price and her coffee-year totals. Check once that the village resolves before recording.

## Backup: browser widget

If the phone line fails, open the public call page `/` (https://hack-nation-world-bank-agriculture.vercel.app/) and use the ElevenLabs widget there; keep `/demo` open in a second tab. The widget is not on `/demo` because its 10 s refresh would end the call. The widget has no keypad: use the **spoken PIN** ("tisa sifuri sifuri moja") and the agent's read-back. Allow microphone access in the browser first.

## Before you record

- Each rehearsal is synthetic and adds one report to the village median (n and possibly the median move). Note n on `/demo` just before recording and use that, not 28.
- Do not re-run the synthetic loader `--reset` after a rehearsal call: it deletes that call.
- "jana" resolves to the call date minus 1 in Kampala time (UTC+3). A US-evening recording can already be the next day in Kampala; the extracted date will not match your local yesterday. Say the date shown on `/demo`, not yours, in the video narration.
- The 12-month window moves with the Kampala date; the median may change by the time you record.
- The nearby twig-borer report is only returned while at least 2 other farms in her sub-county have a report in the last 30 days.

## Pre-flight checklist

- [ ] Warm `/api/health` (curl it twice; the first call after idle is a cold start). `/api/health?deep=1` with the admin secret: db ok, salt fingerprint matches.
- [ ] Open `/demo` with the Basic auth login: it loads, the Kyabakuza kiboko median and n are visible. Note them here: median ____ n ____.
- [ ] Agent is synced: `PUBLIC_BASE_URL=https://hack-nation-world-bank-agriculture.vercel.app uv run python scripts/sync_agent.py --dry-run` shows no diff (the local `.env` points at ngrok).
- [ ] The phone has credit and international calling enabled for a +1 number; dial +1 628 272 9173 once to confirm it rings and the agent answers.
- [ ] Quiet room; speak after the agent finishes.
- [ ] Widget backup loads on `/` and the microphone prompt works.
- [ ] A Kiswahili speaker has checked the lines, or the pitch says the lines are unchecked.
- [ ] Numbers in the script match `/demo` at the moment of recording.
