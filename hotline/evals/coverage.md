# Coverage tags

Each set of 10 calls must show at least **15 distinct tags**, including at least **3 no-sale traps** (marked below). A call carries 3-6 tags. Tags come from spec section 9 plus the extras the dev set needed.

## No-sale traps (the pass condition needs zero phantom sales)

| Tag | Definition |
|---|---|
| `no_sale_trap` | The call contains a price or sale-like text that is not a completed sale by the farmer (umbrella tag, set on every trap call). |
| `echo_median` | The agent states the village median and the farmer only agrees ("hiyo hiyo"); no figure of their own. |
| `intended_sale` | The farmer says they will sell later ("nitauza wiki ijayo"). |
| `not_sold` | The farmer says they have not sold ("sijauza bado"). |

## Sales

| Tag | Definition |
|---|---|
| `clean_sale` | One sale, all fields stated plainly. |
| `per_kg_only` | Only a price per kg is stated; the total is computed. |
| `total_only` | Only a total is stated. |
| `both_price_forms` | A per-kg price and a total are both stated and agree. |
| `bags_with_kg` | Bags with kilos per bag stated. |
| `bags_no_kg` | Bags with no kilos stated, so `amount_kg` is null. |
| `laki_milioni` | Amounts in laki or milioni words. |
| `nusu` | A number with "na nusu" (and a half). |
| `mitwalo` | Amounts in mitwalo (10,000 each). |
| `two_sales` | Two separate sales in one call. |
| `buyer_name`, `buyer_type` | A buyer name or a buyer type is stated. |
| `mobile_money` | Paid by mobile money. |
| `self_correction` | The farmer corrects a figure mid-sentence; the final value counts. |

## Dates

| Tag | Definition |
|---|---|
| `yesterday`, `last_week`, `last_month` | The relative date form named, per the guide's date table. |
| `named_month` | A month name ("Agosti"). |
| `weekday_date` | A weekday name ("Jumanne"). |
| `vague_date` | "Wakati wa mavuno" or similar; `date_sold` is null. |

## Problems

| Tag | Definition |
|---|---|
| `problem_leaf_rust`, `problem_cbd`, `problem_wilt`, `problem_twig_borer` | The agent names `coffee_leaf_rust`, `coffee_berry_disease`, `coffee_wilt_disease`, `black_coffee_twig_borer`. |
| `non_disease_cause` | The agent names a farm-practice cause (for example low soil fertility); `disease_detected` is false. |
| `vague_symptom_not_sure` | The farmer cannot describe the symptom; `likely_disease` is `not_sure`. |

## Other entry kinds and call shapes

| Tag | Definition |
|---|---|
| `harvest` | A harvest quantity is reported. |
| `activity_done_vs_planned` | One activity done (entry) and one planned (no entry). |
| `activity_planned_only` | Only a planned activity is mentioned (no entry). |
| `code_switching` | English or Luganda words mixed into the Kiswahili. |
| `asr_noise` | Dropped words, `[unclear]`, a misheard word. |
| `weather`, `weather_only` | A weather question; or a call whose only content is weather. |
| `spray_name_request` | The farmer asks for a spray product name; no entry. |
| `declined_consent` | The caller refuses recording; `entries` is empty. |
| `forgot_pin` | PIN forgotten, location login. |
| `registration` | New caller registered by the agent. |

## Dev set: tag to call ids

41 distinct tags across 10 calls; no-sale traps: `no_sale_trap` (d03, d08), `echo_median` (d03), `intended_sale` (d03), `not_sold` (d03, d08).

| Tag | Calls |
|---|---|
| `activity_done_vs_planned` | d05 |
| `activity_planned_only` | d08 |
| `asr_noise` | d06 |
| `bags_no_kg` | d04 |
| `bags_with_kg` | d04 |
| `both_price_forms` | d05 |
| `buyer_name` | d02, d10 |
| `buyer_type` | d01 |
| `clean_sale` | d01, d06 |
| `code_switching` | d05, d10 |
| `declined_consent` | d07 |
| `echo_median` | d03 |
| `forgot_pin` | d08 |
| `harvest` | d05, d09 |
| `intended_sale` | d03 |
| `laki_milioni` | d02 |
| `last_month` | d04 |
| `last_week` | d02 |
| `mitwalo` | d10 |
| `mobile_money` | d02 |
| `named_month` | d05 |
| `no_sale_trap` | d03, d08 |
| `non_disease_cause` | d09 |
| `not_sold` | d03, d08 |
| `nusu` | d05, d09 |
| `per_kg_only` | d01, d04, d06, d09 |
| `problem_cbd` | d03 |
| `problem_leaf_rust` | d01 |
| `problem_twig_borer` | d09 |
| `problem_wilt` | d10 |
| `registration` | d09 |
| `self_correction` | d02 |
| `spray_name_request` | d05 |
| `total_only` | d02, d04, d10 |
| `two_sales` | d04 |
| `vague_date` | d09 |
| `vague_symptom_not_sure` | d06 |
| `weather` | d04 |
| `weather_only` | d08 |
| `weekday_date` | d10 |
| `yesterday` | d01, d04, d06 |
