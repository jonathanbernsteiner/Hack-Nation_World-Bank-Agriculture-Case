# Demo happy path (spec section 11)

Setting: Uganda, Kiswahili. Demo farmer: **Nakato (SYNTHETIC)**, keypad PIN **9001**, village Kyabakuza, parish Kyanamukaaka, Masaka, Robusta kiboko. PINs 9000-9099 are reserved for synthetic and demo farmers.

Numbers marked **[from /demo after the load]** come from the seeded data and must be read off `/demo` (village medians panel) after the synthetic load, never from the generator. Spec expectation: kiboko median about 5,900 UGX/kg from at least 10 reports; Nakato's last sale 400 kg at 5,300. Money is spoken from `median_words_sw`, never from digits.

Kiswahili lines are drafts: **need a Kiswahili speaker check** before recording. Short sentences, one question per turn, numbers as words.

## Script

| # | Speaker | Kiswahili | English gloss |
|---|---|---|---|
| 0 | Agent | Habari. Mimi ni msaidizi wa AI. Simu hii inarekodiwa. Je, unakubali? | Hello. I am an AI assistant. This call is recorded. Do you agree? |
| 1 | Nakato | Ndiyo, nakubali. | Yes, I agree. |
| 2 | Agent | Tafadhali bonyeza namba yako ya siri. | Please press your PIN. |
| 3 | Nakato | (keypad) 9 0 0 1 | (keypad) 9001 |
| 4 | Agent | Karibu Nakato wa Kyabakuza. Bei ya kahawa kiboko kijijini kwako ni **[median in words, from /demo after the load]** kwa kilo. | Welcome Nakato of Kyabakuza. The village kiboko price is **[median]** per kilo. |
| 5 | Nakato | Jana niliuza kilo mia tatu za kiboko. | Yesterday I sold three hundred kilos of kiboko. |
| 6 | Agent | Ulipata shilingi ngapi kwa kilo? | How many shillings per kilo? |
| 7 | Nakato | Elfu sita kwa kilo, jumla milioni moja na laki nane. | Six thousand a kilo, total one million eight hundred thousand. |
| 8 | Agent | Ulimuuzia nani, na ulilipwa vipi? | Who did you sell to, and how were you paid? |
| 9 | Nakato | Dalali. Nililipwa kwa simu, pesa za mtandao. | A middleman. Paid by mobile money. |
| 10 | Agent | Nimeandika: kilo mia tatu, kiboko, shilingi milioni moja na laki nane, dalali, pesa za mtandao, jana. Sawa? | I noted: 300 kg kiboko, 1,800,000 shillings, middleman, mobile money, yesterday. Correct? |
| 11 | Nakato | Ndiyo, sawa. | Yes, correct. |
| 12 | Nakato | Majani yana unga wa rangi ya chungwa chini, unaoshika kwenye kidole, na majani yanaanguka. | The leaves have orange powder underneath that rubs onto my finger, and leaves are falling. |
| 13 | Agent | Je, unga huo unatoka kwenye madoa ya kahawia yenye pete ya njano? | Does the powder come from brown spots with a yellow ring? (tell-apart question vs. brown eye spot) |
| 14 | Nakato | Hapana, ni unga wa chungwa tu chini ya jani. | No, just orange powder under the leaf. |
| 15 | Agent | Dalili zinafanana sana na kutu ya majani. Pogoa, palilia, weka mbolea, na kagua kila wiki wakati wa mvua. Kwa kuwa majani mengi yanaanguka, ongea na afisa wa kilimo wiki hii. | The signs closely match leaf rust. Prune, weed, manure, and check weekly in the rains. Since many leaves are falling, talk to the agriculture officer this week. |
| 16 | Nakato | Hali ya hewa itakuwaje? | How will the weather be? |
| 17 | Agent | (Open-Meteo figures for Kyabakuza) ... Funika kahawa inayokauka. | (forecast) ... Cover drying coffee. |
| 18 | Agent | Asante, Nakato. Kwaheri. | Thank you, Nakato. Goodbye. |

Guardrails respected: no spray names or doses, no other farmers' prices, no certainty claims ("closely match", not "is").

## What the screen shows (`/demo`, refreshes every 10 s, within 3 minutes of hanging up)

- A new call row, Kampala time, status `processed`, identified by `pin`, SYNTHETIC badge (rehearsal calls inherit synthetic).
- Kiswahili | English transcript side by side; the PIN appears as `[PIN]`.
- **Sale:** kiboko, 300 kg, 1,800,000 UGX, quote ✓.
- **Observation:** leaf rust, quote ✓.
- Kyabakuza kiboko median: **[from /demo after the load]**, n **[from /demo after the load]**, level village; n goes up by 1 after the call.
- No REVIEW flag expected. A flag appears if confidence < 0.6, a quote is ✗, or identification was by location.

## Scene 2 (location, no PIN)

Caller without a PIN gives village Kyabakuza, parish Kyanamukaaka. The call shows `identified by location` and the REVIEW flag. Check that the village resolves before recording.

## Backup: browser widget

If the phone line fails (the +1 number is an international call from Uganda), open the public call page `/` and use the widget there; keep `/demo` (Basic auth) open in a second tab to watch the result. The widget is not on `/demo` because its 10 s refresh would end the call. The widget has no keypad: use the **spoken PIN** (nine, zero, zero, one) with the agent's read-back. Allow microphone access in the browser.

## Notes

- "jana" (yesterday) resolves to the call date minus 1 in Kampala time (UTC+3). A US-evening recording can already be the next day in Kampala; the extracted date will differ from your local yesterday.
- Pause after each agent turn: phone-line barge-in breaks turn-taking.
- Each rehearsal is synthetic and adds +1 report to the median. Note the count before recording.

## Pre-recording checklist

- [ ] Warm `/api/health` (and `/api/health?deep=1` with the admin secret: db ok, salt_fp matches).
- [ ] Note the Kyabakuza kiboko median and n on `/demo`: **[from /demo after the load]**.
- [ ] Confirm the agent is synced (`sync_agent --dry-run` shows no diff).
- [ ] Confirm the widget backup loads on `/` and the microphone prompt works.
- [ ] Kiswahili lines checked by a speaker; numbers in the script match `/demo`.
