# Labeling guide (gold labels for eval calls)

This guide is the gold definition. Test authors, the Opus label reviewer and the prompt author all work from it. Test authors never see the prompts. Source of truth for fields: spec section 7 (`Entry`, `CallExtraction`) and section 9 (metric). If this guide and the spec disagree, the spec wins and this file gets fixed.

All calls are **synthetic**. Farmers are invented, every file has `is_synthetic: true`, and every PIN (invented ones from 9000-9099, and the new PIN a registration call hands out) appears only as `[PIN]`, including in `params_as_json` and `result_value`. No real names, phone numbers or caller ids, and tool results never carry another farmer's name.

## 1. File format

One JSON file per call, `evals/<set>/<id>.json`:

```json
{
  "id": "d01", "is_synthetic": true, "call_date": "2026-10-02", "timezone": "Africa/Kampala",
  "conversation": { "...ElevenLabs post-call webhook `data` object..." },
  "gold": { "consent": "yes", "entries": [ { "kind": "sale", "...": "..." } ] },
  "free_text_alts": { "buyer_name": ["Mzee Kato"] },
  "quote_possible": true,
  "tags": ["clean_sale", "per_kg_only"],
  "review": { "verdict": "approved", "rounds": 1 }
}
```

`conversation` has `conversation_id`, `transcript[]` and `metadata.start_time_unix_secs` (the call start; its Kampala date must equal `call_date`). Each transcript turn has `role` (`agent` or `user`), `message`, `tool_calls[]`, `tool_results[]`, `time_in_call_secs`. Tool turns follow the ElevenLabs GET shape (docs/spikes/platform.md):

- `tool_calls[] {request_id, tool_name, params_as_json (a JSON string), tool_has_been_called, type}`
- `tool_results[] {request_id, tool_name, result_value (a JSON string), is_error, tool_has_been_called}`

Minimal agent turn that exercises the echoed-median check:

```json
{"role": "agent", "message": "Bei ya kati ya kiboko Kyabakuza ni shilingi elfu tano na mia tano kwa kilo.",
 "tool_calls": [{"request_id": "r1", "tool_name": "identify_farmer", "params_as_json": "{\"pin\": \"[PIN]\"}", "tool_has_been_called": true, "type": "webhook"}],
 "tool_results": [{"request_id": "r1", "tool_name": "identify_farmer", "is_error": false, "tool_has_been_called": true,
                   "result_value": "{\"status\":\"found\",\"village_price\":{\"form\":\"kiboko\",\"median_ugx_per_kg\":5500}}"}]}
```

`gold.entries` use the same keys as `RunResult.entries` (the DB `entries` columns). A gold entry lists every scored field of its kind (section 3), null included, plus optional context keys (`amount`, `unit`, `kg_per_unit`). Unscored fields (`coffee_type`, `price_per_unit`, `disease_confidence`, `evidence_quote`, `evidence_turn`, `description`, `confidence`) are left out of gold on purpose. `amount_kg` and `price_total` are the **code-computed** values: `amount_kg` = amount if unit is kg, or amount x `kg_per_unit`, else null; `price_total` = stated total, or per-unit price x amount.

The agent side follows spec section 1: consent, then PIN or location or registration, then the price from the tool result, then the last-sale question with read-back, then problems (at most 3 tell-apart questions), then weather or other questions, then goodbye. Farmer turns are short, with hesitations, self-corrections and English or Luganda code-switching ("mobile money", "boda", "FAQ", "kiboko", "mitwalo").

## 2. What is an entry

Values come **only from Farmer lines**, or from the farmer's "yes" to a read-back of the farmer's own figures. Agent text alone never creates a value.

| Situation | Entry? |
|---|---|
| Farmer states a completed sale | one `sale` per transaction |
| Agent states the village median and the farmer says "sawa, hiyo hiyo" (echo) | **no** sale |
| "Nitauza wiki ijayo" (intended or future sale) | **no** sale |
| "Sijauza bado" (not sold yet) | **no** sale |
| Farmer reports a harvest quantity | `harvest` |
| Farmer says they already did an activity ("nilipalilia juzi") | `activity` |
| Farmer says they will do it ("kesho nitanyunyizia") | **no** entry |
| Each distinct problem the farmer reports | one `observation` |
| Weather questions, spray-name requests, small talk | none |
| `consent` is `no` | `entries: []`, whatever else the farmer said |

Example (echo): Agent "median is 5,500, do you sell near that?" Farmer "Ndiyo, hiyo hiyo." Gold has no sale.

`consent`: `yes` if the caller agrees, `no` if the caller refuses, `unclear` if there is no clear answer. For `unclear` the entries are labelled normally (the spec drops entries only for `no`).

Self-correction: the farmer's final figure wins ("milioni mbili... hapana, milioni tatu" is 3,000,000). Eval calls are coffee only; other crops are out of scope.

## 3. Scored fields and comparison (spec section 9; the tolerance detail and normalisation are as implemented in `score.py`)

- **sale:** crop, coffee_form, amount_kg, price_total, currency, date_sold, buyer_type, buyer_name, paid_how
- **harvest:** crop, yield_amount, unit
- **activity:** activity, input, quantity, plot
- **observation:** crop, plot, symptom, disease_detected, likely_disease
- plus call-level `consent`

Comparison: null equal to null counts as correct; numbers within +-1% (absolute 0.5 for values under 50); dates and enums exactly; free text after normalisation (lowercase, strip, collapse whitespace, drop punctuation) or matching an entry of `free_text_alts[field]`. Missing and extra entries count all their fields as wrong. Entries are aligned per call, same kind first, then the permutation with the best field agreement.

Free-text fields are `crop`, `plot`, `buyer_name`, `input`. List plausible English renderings in `free_text_alts` (for example `"plot": ["upper garden", "upper plot"]`). A value the farmer never stated is null.

## 4. Field rules

**All kinds.** `crop` is `"coffee"` for every coffee entry. `plot` is the translated plot name only if stated, else null. Non-applicable fields are null (a sale has no `symptom`).

**Sale.**
- `coffee_form`: kiboko (also "kahawa kavu", "mbuni"), faq ("kahawa iliyokobolewa"), parchment, red_cherry, drugar, other. Not stated: null.
- Money, per unit vs total vs `kg_per_unit`. "Shillings" is UGX (`currency: "UGX"`); on this Uganda line a price with no currency word is also UGX, and `currency` is null only when no price is stated. Number words become digits (laki 100,000; milioni; nusu "and a half"; mitwalo = 10,000 each). A stated total gives `price_total`. A stated per-kg price gives `price_total` = price x `amount_kg`. If both are stated, `price_total` is the stated total. Bags: `amount` bags and `kg_per_unit` only if the farmer said the kilos per bag ("kila gunia kilo sitini"): 4 bags of 60 kg is `amount_kg` 240. Bags without kg: `amount_kg` null, and `price_total` only if a total was stated. No arithmetic is done on anything except these two code rules. Gold `price_total` is always the true total: a per-kg price is multiplied by `amount_kg`, even when the unit is bags (the unscored `price_per_unit` is per `unit`).
- `buyer_type`: middleman (mfanyabiashara, buyer), cooperative (chama cha ushirika), other. `buyer_name` only if a name is said ("Kato"). Not stated: null.
- `paid_how`: cash, mobile_money, other. Not stated: null.
- Prices the agent states are never the farmer's price (the echoed-median trap).

**Dates** (`date_sold`, relative to the Kampala `call_date`):

| Farmer says | `date_sold` |
|---|---|
| today / yesterday (jana) | the exact date |
| a weekday (Jumanne) | the most recent such weekday before the call date (7 days back if it is that weekday today) |
| last week (wiki iliyopita) | call date - 7 days |
| two weeks ago | call date - 14 days |
| last month (mwezi uliopita) | the 15th of the previous month |
| a named month (Agosti) | the 15th of its latest past occurrence |
| at harvest, long ago, anything vaguer | null |

**Harvest.** `yield_amount` and `unit` (kg, bag, tin, bunch, other). A harvest is a quantity picked, separate from sales. A statement with a quantity is a `harvest` only; `activity` `harvesting` is for picking with no quantity stated.

**Activity.** `activity` in planting, weeding, fertilising, spraying, pruning, harvesting, other; `input` (product name, free text) and `quantity` only if stated; done only, never planned.

**Observation** (one per distinct problem).
- `symptom` is what the farmer describes, one of 9 values: yellowing_leaves, leaf_spots, powder_or_rust, fruit_spots, rot, wilting, pests, stunted_growth, other. Insect evidence (holes, sawdust, bugs) is `pests`. Drying or drooping without insect evidence is `wilting`. Orange powder is `powder_or_rust`.
- `likely_disease` is **what the agent named** (a hedge such as "huenda" still counts as naming; gold does not apply the pipeline's confidence-below-0.6 downgrade) (a dataset id such as `coffee_leaf_rust`, `coffee_berry_disease`, `coffee_wilt_disease`, `black_coffee_twig_borer`), else `not_sure`. A farm-practice cause named by the agent uses its id (for example `low_soil_fertility`).
- `disease_detected`: true when the farmer reports a problem caused by a disease or pest, including when the agent says `not_sure`; false when the agent names a non-disease cause (nutrition, water, practice). It is null only on non-observation kinds.

## 5. Quote rule (not in gold, scored separately)

The pipeline must output `evidence_quote`: **1-12 words, an exact substring of one Farmer line, never the whole line**, never from an Agent line (case, whitespace, punctuation and digit separators are ignored when checking). It is checked against the English Farmer lines. `quote_possible` is a call-level flag: true when **every** gold entry can be backed by a quotable Farmer line, false otherwise, in which case the call is left out of quote validity (for example a declined-consent call, or an entry whose values come only from a one-word "ndiyo" to a read-back). A consented call with no gold entries is true and counts nothing; a declined-consent call is false.

## 6. Review

An Opus reviewer marks every gold field ok, wrong (with the fix) or ambiguous, with at most 2 fix rounds. `review.verdict` is `approved` only when no field is wrong; ambiguous fields are rewritten in the transcript until unambiguous or the phrasing is avoided. Examples in this guide are not reused in dev or test calls.

## 7. Process and open spec points

- Test sets are written outside the repo until scored, by a fresh author each round who never sees the prompts or past errors. Each set of 10 shows at least 15 coverage tags (coverage.md).
- Points where this guide is stricter than spec section 7, to settle there so prompt, code and gold agree: the weekday rule, the "no currency word is UGX" rule, tolerance 0.5 for values under 50 and the free-text field list (`score.py` implements them); `price_total` for bag sales with a per-kg price (gold is the true total; the verify step's `price_per_unit x amount` is per `unit`); and the verify step's confidence-below-0.6 downgrade to `not_sure`, which gold ignores, so the extraction prompt must give confident diagnoses a `disease_confidence` of 0.6 or more.
- A named month equal to the call month: its 15th may lie in the future, so label null in that case; dates older than 400 days are null (verify step 5).
