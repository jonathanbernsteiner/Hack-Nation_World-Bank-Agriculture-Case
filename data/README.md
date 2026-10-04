# Coffee disease reference

A cited reference of what can go wrong on an arabica coffee farm, so the hotline agent can go from what a farmer says on the call ("the leaves have dots on them") to a **likely** problem and safe advice. If the description doesn't clearly fit one row, the answer is **"not sure, flagged for the extension officer"**.

Built for issue #17. The hotline agent's knowledge file (#46) is built from these rows.

## Files

| File | What it is | Size |
|---|---|---|
| `coffee-diseases.json` | 30 rows: 10 diseases, 11 pests, 8 non-disease look-alikes, 1 `not_sure` fallback | ~130 KB, 58 cited sources |
| `disease-eval.csv` | 32 farmer-style phrases with the expected answer, **all SYNTHETIC** (written by us) | ~5 KB |

## How it is meant to be used

1. The hotline agent's knowledge file (#46) is built from these rows. The agent may only recommend measures listed for the problem it names (grounded generation).
2. When the agent is unsure, or the farmer's description fits several rows, the answer is `not_sure`, and it asks the row's `tell_apart_question` to narrow it down.
3. Post-call extraction (Opus 5.5, #10) stores the agent's stated diagnosis in `entries.likely_disease`: an `id` from this file or `not_sure`.
4. `officer_note_en` is for the extension officer and the co-op only, never read to the farmer. Unsure or `urgent` results go to the extension officer.

## Row fields

| Field | Meaning |
|---|---|
| `id` | Stable snake_case id; the value the model picks and `entries.likely_disease` stores |
| `kind` | `disease`, `pest`, `disorder` (non-disease look-alike) or `fallback` |
| `common_name`, `scientific_name` | Names as the sources give them |
| `swahili_name` | Only where a source gives one (see gaps below), else `null` |
| `plant_parts` | `leaves`, `berries`, `stem`, `roots`, `whole_tree` |
| `symptom_categories` | Subset of the fixed list agreed on #1: `yellowing_leaves, leaf_spots, powder_or_rust, fruit_spots, rot, wilting, pests, stunted_growth, other` |
| `farmer_words` | How a farmer with no training might say it out loud |
| `key_signs` | Plain signs that tell it apart |
| `look_alikes` | Ids of rows it is confused with |
| `tell_apart_question` | One yes/no question a farmer can answer by looking |
| `conditions` | Season, weather, altitude or farm conditions that favour it |
| `urgency` | `routine`, `soon` or `urgent` (urgent always goes to the officer) |
| `farmer_advice_en` | Safe steps she can take herself, ending with when to call the officer. **No chemical names, products or doses.** |
| `officer_note_en` | Control guidance as the sources state it, for the officer and co-op |
| `escalate_when` | When the farmer must call the extension officer |
| `regions` | Where the sources report it |
| `in_bracol` | `true` if it is a class in the BRACOL leaf image dataset |
| `sources` | `publisher`, `title`, `url`, `year` for every source used for the row |

## What's covered

- **Diseases:** coffee leaf rust, coffee berry disease, coffee wilt disease, bacterial blight (Elgon die-back), brown eye spot (Cercospora), Phoma leaf blight, Fusarium bark disease, Armillaria root rot, American leaf spot (Latin America only), sooty mould.
- **Pests:** leaf miner, Antestia bug, coffee berry borer, white stem borer, thrips, mealybug, root mealybug, green scale, nematodes, lace bug, leaf skeletoniser.
- **Non-disease look-alikes:** nitrogen, magnesium and potassium deficiency, waterlogging, drought stress, sun scorch, overbearing dieback (with the biennial on/off-year pattern), hail damage. The brief hints at these ("40 mm overnight", "why the third row is struggling"). Without them the model would call every yellow leaf a disease.

## Sources and licences

Every row cites at least one source, and 26 of the 29 problem rows cite three or more. Rows cite these publishers:

| Publisher | Rows citing it | Licence |
|---|---|---|
| Uganda Coffee Development Authority (UCDA): Arabica and Robusta Coffee Handbooks, 2019 | 22 | Public PDF; no licence stated |
| CABI: *Pests and Diseases of Coffee in Eastern Africa: A Technical and Advisory Manual* (Rutherford & Phiri, eds., 2006) | 12 | Public PDF on gov.uk (DFID-funded); no licence stated |
| Infonet-Biovision coffee page (archived 2012 copy; cites Kenya's Coffee Research Foundation) | 11 | Not checked |
| Tanzania Coffee Research Institute (TaCRI): annual reports and programme pages | 10 | Public; no licence stated |
| University of Hawaii CTAHR: *Growing Coffee in Hawaii* (2008) and nutrient guides | 8 | Public; no licence stated |
| KALRO Coffee Research Institute scientists' papers (MDPI *Agronomy* 2021 and 2023, other journals) | 4 | MDPI papers are CC BY 4.0 |
| FAO: *Arabica coffee manual for Lao PDR* (2005) | 4 | FAO terms |
| World Coffee Research varieties catalogue | 3 | Website |
| Cenicafé (Colombia): *Enfermedades del cafeto en Colombia* (2003) | 3 | Public; no licence stated |
| BRACOL dataset and paper | 3 | CC BY 4.0 |
| Other peer-reviewed or research sources (PLOS ONE, Frontiers, Cambridge journals, SciELO, CGSpace, Procafé, ASIC posters) | 18 | Mostly open access; a few rows rest on abstracts only |

We cite these sources and restate the facts in our own words. No text, tables or images are copied from them.

## What it does NOT cover (read before using it)

- **Not checked by an agronomist.** Nobody from KALRO or an extension service has reviewed it.
  - Two planned sources were unreachable while we researched: KALRO's own repository and the CABI PlantwisePlus factsheets.
  - Kenya is covered through peer-reviewed papers by KALRO-CRI scientists instead.
  - Most extension sources are Ugandan and Tanzanian, and some details come from Hawaii, Brazil and Colombia.
- **Symptoms overlap.** For example, 12 rows include `leaf_spots`. A short description like "the leaves have dots" fits several rows, so the right answer is `not_sure` plus a `tell_apart_question`, not a guess.
- **Sources disagree on some points.** Where they do, the row's officer note says so. The main disagreements:
  - whether shade lowers leaf rust (CABI says yes; KALRO studies in Kenya found more rust under shade);
  - how high leaf rust and coffee berry disease reach;
  - how long to wait before replanting after coffee wilt (6 months to 2 years).
  - Ruiru 11 and Batian resist berry disease and rust, but in KALRO seedling trials they were badly affected by Fusarium bark disease.
- **Thin rows:**
  - American leaf spot (Latin America only, 2 sources);
  - Phoma (no East African extension source; local occurrence unconfirmed);
  - lesion nematodes;
  - lace bug and leaf skeletoniser (2 sources each);
  - sun scorch (one undated extension-linked website plus general sources);
  - waterlogging (one Brazilian seedling study plus general guidance).
- **Not in the dataset:**
  - minor pests: capsid bug, berry moth, yellow-headed borer, red coffee mite, star scale, tailed caterpillar;
  - other problems: boron deficiency, ripe-berry anthracnose, Fusarium root rot;
  - **any crop other than coffee** (maize, beans, bananas), which the hotline therefore doesn't diagnose.
- **No doses or product names in the farmer advice**, by design. The officer notes give control types as the sources state them. Before acting on them, check the products against the current national registered list (in Kenya, the PCPB list).
- **Coffee wilt is strain-specific.** The strain that attacks arabica is reported from Ethiopia. The strain in Uganda, DRC and Tanzania attacks robusta only.
- **Swahili names:**
  - Only 8 rows have one, all taken from TaCRI's Kiswahili annual reports, so they reflect **Tanzanian** usage:
    - leaf rust: *kutu ya majani*
    - coffee berry disease: *chulebuni*
    - coffee wilt: *mnyauko fusari*
    - Antestia: *kimatira*
    - berry borer: *ruhuka*
    - leaf miner: *kidomozi*
    - white stem borer: *bungua mweupe*
    - green scale: *vidugamba*
  - None has been checked by a speaker.
  - *kidomozi* is the weakest: it was matched by its position in a list, not found in a glossary.
  - The advice text is English only; the Swahili wording is a separate step.
- **The eval phrases are synthetic.** We wrote them in English, as they would read after translation. They are not real farmer speech. `not_sure_ok` marks phrases where falling back to "not sure" counts as safe.
- **BRACOL is not field data for our setting.**
  - About the dataset: Krohling, Esgario & Ventura, Mendeley Data (2019), DOI 10.17632/yy2k5y8mxg.1, CC BY 4.0. It has 1,747 photos of detached arabica leaves, lower side only, on a white background, from Espírito Santo, Brazil.
  - Its five classes (healthy, leaf miner, rust, brown leaf spot, cercospora leaf spot) cover only 3 of our rows.
  - The paper names no pathogens, so its "brown leaf spot" class is not linked to Phoma here.
  - It has no berries, stems or East African photos.
  - A Kenyan field dataset exists (Jepkoech et al. 2021, *Data in Brief*, Kirinyaga County, about 58,000 images, classes healthy, rust, miner, Phoma, Cercospora). Its class counts and data licence have not been checked yet.
