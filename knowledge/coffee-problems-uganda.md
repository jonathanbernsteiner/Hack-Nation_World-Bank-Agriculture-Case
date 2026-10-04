# Coffee problems in Uganda: knowledge for the hotline agent

## 0 Read me first

- This file is the only source of problems and measures for the agent. Name a problem only from the ids below; give only the measures written under it.
- NOTE: the Kiswahili in this file still needs a check by a Ugandan Kiswahili speaker. Names and phrases partly come from Tanzanian sources (TaCRI).
- No product names, amounts or treatments appear here on purpose: for those the caller is told "afisa ugani atakushauri" (the extension officer will advise).
- No hotline number exists for the extension officer; just say to contact the afisa ugani (extension officer).
- Each id is the exact id in `data/coffee-diseases.json`. If nothing fits, the answer is `not_sure`: say you are not sure, and that the afisa ugani will follow up.

## 1 Triage

Ask where on the coffee the problem is, then use the tell-apart question of the candidates.

| Plant part | What the caller sees | Candidates (ask to tell apart) |
|---|---|---|
| Whole tree | sudden wilting, yellow limp leaves | `coffee_wilt_disease`, `drought_stress`, `waterlogging`, `black_coffee_twig_borer` |
| Whole tree | pale trees, weak growth, little yield | `low_soil_fertility`, `weed_competition`, `old_unpruned_trees` |
| Twigs and branches | twig dries, black, small hole under it | `black_coffee_twig_borer`, `coffee_wilt_disease` |
| Leaves | orange powder under leaf, leaves falling | `coffee_leaf_rust` |
| Leaves | round spots with grey centre, no powder | `brown_eye_spot` |
| Leaves | yellowing all over after rain | `waterlogging`, `low_soil_fertility` |
| Green berries | black sunken spots, berries falling | `coffee_berry_disease` |
| Berries | red-ringed spots or red blisters | `brown_eye_spot` |
| Berries | tiny hole at the tip | `coffee_berry_borer` |
| Picked or dried coffee | mixed ripeness, dried on the ground, mouldy | `poor_harvest_practice` |

Urgent (always send to the afisa ugani): `coffee_wilt_disease`, `coffee_berry_disease`.

Pairs to separate with one question: wilt vs twig borer (whole tree with blue-black wood under the bark, vs a twig with a pinhole); wilt vs drought (one tree vs many trees in a dry spell); rust vs brown eye spot (powder that rubs off vs a spot with a grey centre); red blister vs berry borer (red ring on the sunny side vs a hole at the tip); berry disease vs red blister (green berries, black and sunken, Arabica).

## 2 Top 5

### Coffee wilt disease (CWD), tracheomycosis, Fusarium wilt (SW: mnyauko fusari (kahawa)) (`coffee_wilt_disease`)

- **What:** disease; urgency: urgent. Signs: Leaves yellow, fold and curl inward, feel limp, then dry brown and drop until the tree is bare; often starts on one side of the tree; Branches turn blackish and die back; berries on the sick tree turn red early and stay on the branches; Blue-black staining of the wood just under the bark, strongest near the base of the stem (the tell-tale sign); A dead tree stays firmly rooted, and suckers that grow after cutting also wilt.
- **Where / which coffee:** Robusta (Uganda); any tree.
- **Farmer says (EN | SW):** "the tree is wilting suddenly" | "mti unanyauka ghafla"; "leaves turn yellow and go limp" | "majani yanageuka manjano na kulegea".
- **Ask to tell apart:** If you scrape away a little bark near the bottom of the stem, is the wood underneath stained blue-black? | SW: "Kama ukikwangua gome chini ya shina, kuni ya ndani ina rangi ya buluu-nyeusi?"
- **Look-alikes:** `drought_stress`, `armillaria_root_rot`, `fusarium_bark_disease`, `white_stem_borer`, `black_coffee_twig_borer`.
- **Do now and prevent (the only measures you may give):** If the extension officer confirms coffee wilt, the tree cannot be saved: uproot and burn it where it stands, never drag it past healthy trees, and do not keep its wood for firewood, its berries, or its husks for mulch. Avoid cutting the stem base when weeding, keep livestock away from the trees, and clean cutting tools in a fire before moving from one tree to the next. Call the extension officer the same day you see any tree wilting, so it can be confirmed before you uproot it.
- **Call the officer (afisa ugani) when:** Any tree that suddenly yellows, wilts and drops its leaves, especially if berries ripen early on it; call before uprooting so the officer can check for blue-black staining.
- **Sources:** [CABI](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf); [CABI](https://assets.publishing.service.gov.uk/media/57a08b41ed915d3cfd000c12/Coffee_CH01.pdf); [Uganda Coffee Development Authority](https://new.ugandacoffee.go.ug/file-download/download/public/42)

### Black coffee twig borer (BCTB), ambrosia beetle (SW: kidudu cha vitawi (twig borer)) (`black_coffee_twig_borer`)

- **What:** pest; urgency: soon. Signs: A tiny pin-sized entry hole on the underside of a twig or thin branch; The twig wilts and dries beyond the hole, so the leaves and berries on it die; It attacks the crop-bearing primary branches, and thin soft stems, of robusta coffee; Damage is worse in the dry season, under shade trees, and in crowded or unpruned coffee.
- **Where / which coffee:** Robusta, all robusta areas.
- **Farmer says (EN | SW):** "twigs dry and turn black" | "vitawi vinakauka na kuwa vyeusi"; "there is a small hole under the branch" | "kuna kitundu kidogo chini ya tawi".
- **Ask to tell apart:** Is there a pin-sized hole on the underside of the drying twig? | SW: "Kuna kitundu kidogo kama sindano chini ya tawi linalokauka?"
- **Look-alikes:** `coffee_wilt_disease`, `overbearing_dieback`.
- **Do now and prevent (the only measures you may give):** Cut the infested twig off below the hole, chop it up and burn it as soon as you see it, so the beetles inside cannot fly on to other branches. Look over your coffee regularly for more dry twigs with a hole underneath. Prune and de-sucker so the bush is open to light and air, thin heavy shade, and do not plant musizi or musambya as shade trees. Feed the soil with manure or compost, because weak, hungry trees are attacked more. The beetles fly between farms, so ask your neighbours to do the same. If many branches are drying, or you cannot find a hole, call the extension officer.
- **Call the officer (afisa ugani) when:** Many branches are drying, the twigs are drying but you cannot find a hole (it may be coffee wilt disease), or the whole tree is wilting.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/42); [Coffee Department, Ministry of Agricultu](https://www.ugandacoffee.go.ug/node/580); [National Coffee Research Institute](https://researchspace.naro.go.ug/items/033ab680-f857-464c-b3f7-d03884dd9d77/full)

### Coffee leaf rust (SW: kutu ya majani) (`coffee_leaf_rust`)

- **What:** disease; urgency: soon. Signs: Yellow to orange powdery spots on the UNDERSIDE of the leaf, with pale yellow patches on the upper side above them; Spots start small (2-3 mm) and grow; older spots go brown and dead in the middle with powder only at the edge; Heavy leaf drop; badly hit trees can lose almost all leaves and branch tips can die back; Worst on trees carrying a heavy crop.
- **Where / which coffee:** Arabica and Robusta.
- **Farmer says (EN | SW):** "orange powder under the leaf" | "unga wa rangi ya machungwa chini ya jani"; "leaves are falling" | "majani yanapukutika".
- **Ask to tell apart:** When you turn the leaf over, is there orange or yellow powder on the underside of the spots? | SW: "Ukigeuza jani, kuna unga wa machungwa au njano upande wa chini?"
- **Look-alikes:** `brown_eye_spot`, `phoma_leaf_blight`, `coffee_leaf_miner`.
- **Do now and prevent (the only measures you may give):** Prune and space your trees, and keep weeds down, so air moves through the bush and leaves dry quickly. Feed the trees with manure, because weak, hungry trees get rust more easily, and check the undersides of leaves often during and after the rains. Call the extension officer if about 1 in 20 leaves has orange powder around three months after flowering, or if the trees are dropping many leaves.
- **Call the officer (afisa ugani) when:** About 1 in 20 leaves (or more) have orange powder spots, especially around three months after flowering; or trees are losing many leaves; or rust appears on a variety sold as resistant.
- **Sources:** [CABI](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf); [KALRO Coffee Research Institute](https://mdpi-res.com/d_attachment/agronomy/agronomy-11-02590/article_deploy/agronomy-11-02590.pdf); [Uganda Coffee Development Authority](https://new.ugandacoffee.go.ug/file-download/download/public/43)

### Brown eye spot / Cercospora leaf spot (berry blotch; 'red blister disease' on berries in Uganda) (SW: madoa ya jicho la kahawia; malengelenge mekundu kwenye matunda) (`brown_eye_spot`)

- **What:** disease; urgency: routine. Signs: Round brown or reddish-brown leaf spots with a grey or whitish centre, often with a yellow halo, seen best on the upper side of the leaf; No orange powder under the spots; On berries: small red spots, or brown patches with a bright red ring, usually on the sunny side, that can join into dry blisters; Worst on nursery seedlings and young plants, and on stressed, poorly fed or unshaded trees.
- **Where / which coffee:** Arabica and Robusta; worst on seedlings and stressed trees.
- **Farmer says (EN | SW):** "red blisters on the berries" | "malengelenge mekundu kwenye matunda"; "round spots on the leaves" | "madoa ya duara kwenye majani".
- **Ask to tell apart:** Do the spots have a pale grey or whitish centre, like an eye? | SW: "Madoa yana kitovu cha rangi ya kijivu kama jicho?"
- **Look-alikes:** `coffee_leaf_rust`, `phoma_leaf_blight`, `coffee_berry_disease`, `nitrogen_deficiency`, `bacterial_blight`.
- **Do now and prevent (the only measures you may give):** Give seedlings and young plants some shade (about half shade), feed the trees with manure or fertiliser, and water nursery plants regularly without waterlogging, spacing the seedling bags so air can move. Collect and destroy fallen diseased leaves and coffee debris. Call the extension officer if nursery seedlings are losing many leaves or many berries have red-ringed spots.
- **Call the officer (afisa ugani) when:** Seedlings in the nursery are losing many leaves; or many green berries show red-ringed spots; or spots keep spreading after shade and feeding are improved.
- **Sources:** [CABI](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf); [Uganda Coffee Development Authority](https://new.ugandacoffee.go.ug/file-download/download/public/43); [FAO Regional Office for Asia and the Pac](https://www.fao.org/4/ae939e/ae939e0b.htm)

### Coffee berry disease (CBD) (SW: chulebuni) (`coffee_berry_disease`)

- **What:** disease; urgency: urgent. Signs: Small dark, water-soaked spots on young GREEN berries that quickly turn dark brown or black and sink in, covering the whole berry within about a week; In wet weather, pale pink spore masses on the spots; Green berries fall early, or stay on the branch black, dry and shrivelled (mummified); Pale, corky brown 'scab' spots on young or mature green berries, which can become active again when the berry ripens.
- **Where / which coffee:** Arabica, highlands (not Robusta).
- **Farmer says (EN | SW):** "green berries turn black and sink in" | "matunda mabichi yanakuwa meusi na kubonyea".
- **Ask to tell apart:** Is there a bright red ring around the dark spot on the green berry? | SW: "Kuna duara jekundu kuzunguka doa jeusi kwenye tunda bichi?"
- **Look-alikes:** `brown_eye_spot`, `overbearing_dieback`.
- **Do now and prevent (the only measures you may give):** At the end of the season, pick off and remove every berry left on the tree, including dry 'mbuni' berries, so they cannot infect the new crop. Prune to open up the bush so it dries quickly after rain (but do not prune compact varieties such as Catimor-type trees), and keep the shade canopy from getting too dense. Call the extension officer as soon as you see black, sunken spots on green berries during the rains.
- **Call the officer (afisa ugani) when:** Any dark, sunken spots on green berries, or many green berries dropping, especially during the rains.
- **Sources:** [CABI](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf); [KALRO Coffee Research Institute](https://agriculturejournal.org/download/10709); [Uganda Coffee Development Authority](https://new.ugandacoffee.go.ug/file-download/download/public/43)

## 3 Short list

#### Low soil fertility (hungry soil, no manure or fertiliser for years) (`low_soil_fertility`)

- **What:** disorder; urgency: routine. Signs: All trees in the field look evenly pale or yellow, not just one tree or one spot; Small leaves, weak growth and low yield that gets worse over the years; No manure, compost or fertiliser has been given for years, and the harvest takes nutrients out of the soil every season.
- **Where / which coffee:** Any coffee.
- **Farmer says (EN | SW):** "trees are pale, I have not used manure in years" | "miti imepauka, sijaweka mbolea miaka mingi".
- **Ask to tell apart:** Have you put manure, compost or fertiliser on these trees in the last two or three years? | SW: "Umeweka mbolea ya samadi au mboji kwenye miti hii miaka miwili au mitatu iliyopita?"
- **Look-alikes:** `nitrogen_deficiency`, `magnesium_deficiency`, `potassium_deficiency`, `weed_competition`.
- **Do now and prevent (the only measures you may give):** Feed the soil: put well-rotted manure or compost around the trees every year, and spread mulch of dry grass, maize stalks or bean haulms under them, keeping the mulch about 30 cm away from the stem. Ask the extension officer how to take a soil test, so you know what your soil is missing before you buy anything. If the trees stay pale after feeding, call the extension officer.
- **Call the officer (afisa ugani) when:** Trees stay pale or small after a season of manure or compost, a few trees are very different from their neighbours (then it is probably not the soil), or you want a soil test.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/42); [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43)

#### Drought / water stress (`drought_stress`)

- **What:** disorder; urgency: soon. Signs: Leaves lose stiffness, droop or fold; when severe they no longer recover overnight; Older leaves go pale, then brown and dry; leaves and berries drop; Bearing trees and young trees on shallow soils suffer most, during a dry spell; Wood under the bark looks normal (blue-black wood under the bark points to coffee wilt disease).
- **Where / which coffee:** Any coffee, dry spell.
- **Farmer says (EN | SW):** "trees wilt at midday, no rain has fallen" | "miti inanyauka mchana, mvua haijanyesha".
- **Ask to tell apart:** Are many trees on the farm drooping at the same time during the dry spell, rather than one tree or one side of a tree? | SW: "Miti mingi inanyauka kwa wakati mmoja wakati wa ukame, si mti mmoja tu?"
- **Look-alikes:** `coffee_wilt_disease`, `coffee_mealybug`, `coffee_lace_bug`.
- **Do now and prevent (the only measures you may give):** Mulch the soil under the trees (keeping mulch off the stem), keep weeds down, and keep or plant shade trees. Water young trees if you can. If one tree wilts while its neighbours are fine, or wilting stays after rain, call the extension officer.
- **Call the officer (afisa ugani) when:** One tree or one side of a tree wilts while neighbours are fine, wilting does not recover after rain or watering, or the wood under the bark is blue-black.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43); [University of Hawaii CTAHR](https://www.ctahr.hawaii.edu/oc/freepubs/pdf/coffee08.pdf); [CAB International](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf)

#### Waterlogging / poor drainage (`waterlogging`)

- **What:** disorder; urgency: soon. Signs: Follows heavy or long rain; worst in low spots and on heavy clay or poorly drained rows; Leaves turn yellow and drop early; growth slows; Fine feeding roots die; soil stays soggy or water stands for days; Can bring young-leaf yellowing from iron/manganese shortage on poorly drained soil.
- **Where / which coffee:** Any coffee, after heavy rain.
- **Farmer says (EN | SW):** "water pools in the field" | "maji yanatuama shambani".
- **Ask to tell apart:** Has water stood around these trees, or the soil stayed soggy, for several days after the rain? | SW: "Maji yametuama karibu na miti kwa siku kadhaa baada ya mvua?"
- **Look-alikes:** `coffee_wilt_disease`, `armillaria_root_rot`.
- **Do now and prevent (the only measures you may give):** Open or clear drainage channels so water runs away from the trees, and avoid walking or digging on the soaked soil. Put mulch back only once the soil has drained, keeping it off the stem. If trees keep yellowing or wilting after the soil dries, call the extension officer.
- **Call the officer (afisa ugani) when:** Trees keep wilting or yellowing after the soil has drained, or there is white fungal growth or cracking at the stem base (root rot), or blue-black wood under the bark (coffee wilt).
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43); [University of Hawaii CTAHR](https://www.ctahr.hawaii.edu/oc/freepubs/pdf/coffee08.pdf); [Ciencia e Agrotecnologia](https://scielo.br/j/cagro/a/Y6nPvg8pDpg98THS8PGbWJP/?lang=en)

#### Old, unpruned or overgrown trees (`old_unpruned_trees`)

- **What:** disorder; urgency: routine. Signs: Old, tall trees with many stems or suckers and a crowded canopy; Many unproductive or dead branches, small berries and few of them; Low bearing heads, tall stems that are hard to pick, and a field that has not been pruned or stumped for years.
- **Where / which coffee:** Any coffee.
- **Farmer says (EN | SW):** "the trees are old, I have not pruned" | "miti ni mizee, sijapogoa".
- **Ask to tell apart:** Have these trees gone more than a few years without pruning, de-suckering or cutting back the old stems? | SW: "Miti hii imekaa miaka mingi bila kupogolewa au kuondolewa machipukizi ya ziada?"
- **Look-alikes:** `overbearing_dieback`, `low_soil_fertility`.
- **Do now and prevent (the only measures you may give):** After the main harvest, prune: take out dead, broken and unproductive branches and the extra suckers, and keep only 3 or at most 4 good stems per tree. Clean your cutting tool between trees, and burn the cut branches where they were cut instead of dragging them through the farm. Old trees that give few, small berries may need stumping, which means cutting back the old stems so young shoots take over. Plan this with the extension officer rather than doing it alone, and ask the officer when to start.
- **Call the officer (afisa ugani) when:** You want to stump or replant, the trees have dead branches with holes or blue-black wood (then see coffee wilt disease and the twig borer), or yields stay low after pruning.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/42); [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43)

#### Weeds and grass competing with the coffee (`weed_competition`)

- **What:** disorder; urgency: routine. Signs: Grass or weeds covering the ground between and under the coffee, sometimes taller than young trees; Young trees are small, pale or slow, and older trees give low yield or poor beans; Worse where weeding stopped at the end of the rains.
- **Where / which coffee:** Any coffee, young trees most.
- **Farmer says (EN | SW):** "lots of weeds" | "magugu mengi".
- **Ask to tell apart:** Is the ground under and around the stunted trees covered by grass or weeds? | SW: "Ardhi chini ya miti midogo imefunikwa na nyasi au magugu?"
- **Look-alikes:** `low_soil_fertility`, `drought_stress`.
- **Do now and prevent (the only measures you may give):** Weed by hand or slash the weeds before they flower and seed, and keep young coffee especially clean. Do clean weeding at the end of the rains, because weeds then take the little water that is left, and keep it clean until the next rains. Do not weed with a hoe in the rainy season, because it washes the soil away, and take care not to cut the coffee roots. Spread mulch of dry grass, maize stalks or bean haulms to keep weeds down, about 30 cm away from the stem. If the trees stay small or pale after weeding, call the extension officer.
- **Call the officer (afisa ugani) when:** Trees stay stunted or pale after the field has been cleared and mulched, or weeds are too heavy for the family to clear.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/42); [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43)

#### Poor harvest and drying practice (quality and price loss) (`poor_harvest_practice`)

- **What:** disorder; urgency: routine. Signs: Green, unripe or over-ripe cherries mixed with red ones, often from stripping the branch; Coffee dried on bare ground, left in layers that are too thick, or wetted again by rain or dew; Mouldy, musty or smoky smell; low price at the buyer. This is mainly a quality and price loss, not a plant disease.
- **Where / which coffee:** Any coffee (quality and price loss, not a plant disease).
- **Farmer says (EN | SW):** "we pick unripe berries and dry them on the ground" | "tunachuma mabichi, tunaanika chini".
- **Ask to tell apart:** Did you pick green and red cherries together, or dry the coffee on bare ground or leave it uncovered when it rained? | SW: "Mlichuma matunda mabichi na mekundu pamoja, au kuanika kahawa chini ardhini bila kuifunika mvua ikinyesha?"
- **Look-alikes:** none.
- **Do now and prevent (the only measures you may give):** Pick only red ripe cherries by hand and come back to the green ones about 6 to 8 days later; do not strip the branch. Spread a clean tarpaulin or sack under the tree while picking, and do not pick up cherries from the ground. Dry the coffee on a tarpaulin, a mat or a raised rack instead of bare ground, spread it thin, turn it, and cover it at night and before rain so it does not get wet again. Store it dry in clean sisal bags, raised off the floor and away from the wall. If you smell mould or are not sure it is dry, ask the extension officer or your cooperative before you sell.
- **Call the officer (afisa ugani) when:** The coffee smells mouldy or musty, it was wetted again many times, or you are unsure whether it is dry enough to sell.
- **Sources:** [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/42); [Uganda Coffee Development Authority](https://www.ugandacoffee.go.ug/file-download/download/public/43)

#### Coffee berry borer (SW: ruhuka) (`coffee_berry_borer`)

- **What:** pest; urgency: soon. Signs: Usually one small round hole, about 1 mm, at or near the tip (navel) of large green or ripe berries; Inside: beans with blue-green staining and small white legless grubs with brown heads; Tiny black beetle, about 2 mm long; Green berries fall early; some attacked young berries rot.
- **Where / which coffee:** Arabica and Robusta.
- **Farmer says (EN | SW):** "small hole at the tip of the berry" | "kitundu kidogo ncha ya tunda".
- **Ask to tell apart:** Is there a tiny round hole, about the size of a pinhead, at the tip of the berry? | SW: "Kuna kitundu kidogo cha duara, kama kichwa cha sindano, kwenye ncha ya tunda?"
- **Look-alikes:** `antestia_bug`, `coffee_berry_disease`.
- **Do now and prevent (the only measures you may give):** Pick ripe berries often, about every two weeks in the peak season and monthly at other times, and spread a sack or sheet under the tree so no berries are lost. Collect every fallen and dried berry from the ground, strip old berries off the trees after harvest (especially before the rains), and burn them, bury them deep or boil them. Call the extension officer if many berries on several trees have the small hole at the tip.
- **Call the officer (afisa ugani) when:** Many berries on several trees show the small tip hole, or large numbers of green berries are dropping.
- **Sources:** [CABI](https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf); [Uganda Coffee Development Authority](https://new.ugandacoffee.go.ug/file-download/download/public/43); [Infonet-Biovision](https://kolibri.teacherinabox.org.au/modules/en-infonet/export/default$ct$140$crops.html)

## 4 Good practice basics

For general questions only, when no problem is named. These come from the entries above.

- Prune and de-sucker after the main harvest so air and light reach the bush; keep 3 or at most 4 good stems per tree.
- Keep weeds down, with clean weeding at the end of the rains; mulch with dry grass, maize stalks or bean haulms, 30 cm away from the stem.
- Feed the soil every year with well-rotted manure or compost.
- Keep drainage channels open so water does not stand around the trees.
- Pick only red ripe cherries, dry them thin on a tarpaulin or raised rack, cover them at night and before rain, and store them dry off the floor.
- Check the trees often, especially in and after the rains; clean cutting tools between trees.
- For anything about treatments, products, amounts or soil tests, say the afisa ugani will advise.

## 5 Words

| English | Kiswahili |
|---|---|
| coffee | kahawa |
| tree | mti (miti) |
| leaf | jani (majani) |
| twig / branch | kitawi (vitawi) / tawi (matawi) |
| berry / cherry | tunda (matunda) |
| wilting | kunyauka |
| spots | madoa |
| powder | unga |
| hole | kitundu |
| weeds | magugu |
| manure | samadi |
| compost | mboji |
| mulch | matandazo |
| pruning | kupogoa |
| drought / dry spell | ukame |
| rain | mvua |
| extension officer | afisa ugani |
| problem | tatizo |
| price | bei |

## 6 Sources

- CABI: Pests and diseases of coffee in eastern Africa: a technical and advisory manual (Rutherford & Phiri, eds.) - Coffee Wilt Disease (2006). https://assets.publishing.service.gov.uk/media/57a08c1b40f0b64974000fcc/U3071CoffeeManual.pdf
- CABI: Coffee Wilt Disease in Africa - Final Technical Report, Chapter 1 (Phiri & Baker) (2009). https://assets.publishing.service.gov.uk/media/57a08b41ed915d3cfd000c12/Coffee_CH01.pdf
- Uganda Coffee Development Authority (UCDA): Robusta Coffee Handbook - 1.4 Robusta varieties; 7.1 Coffee Wilt Disease (2019). https://new.ugandacoffee.go.ug/file-download/download/public/42
- CABI PlantwisePlus Blog: Do you like your coffee wilted? (2011). https://blog.plantwise.org/2011/07/27/do-you-like-your-coffee-wilted/
- Tanzania Coffee Research Institute (TaCRI): Taarifa ya Mwaka 2003 (Annual Report 2003, Kiswahili) (2003). https://tacri.org/fileadmin/03_uploads/03_documents/TaCRI.Reports/ANNUAL_RPT_2003_KIS_FINAL.pdf
- Tanzania Coffee Research Institute (TaCRI): Coffee Improvement Research Programme (None). https://tacri.org/research-programmes/coffee-improvement-research-programme/
- Uganda Coffee Development Authority (UCDA): Robusta Coffee Handbook (6.1 Black Coffee Twig Borer; 3.1.4 shade trees) (2019). https://www.ugandacoffee.go.ug/file-download/download/public/42
- Coffee Department, Ministry of Agriculture (formerly UCDA): Manage the Black Coffee Twig Borer with these easy steps (None). https://www.ugandacoffee.go.ug/node/580
- National Coffee Research Institute (NaCORI), NARO; Journal of Agricultural Science: Incidence, Damage and Management of the Major Pests and Diseases of Robusta Coffee in Uganda (Kyalo et al., abstract) (2024). https://researchspace.naro.go.ug/items/033ab680-f857-464c-b3f7-d03884dd9d77/full
- KALRO Coffee Research Institute (Agronomy, MDPI): Coffee Leaf Rust (Hemileia vastatrix) in Kenya - A Review (Gichuru, Alwora, Gimase, Kathurima) (2021). https://mdpi-res.com/d_attachment/agronomy/agronomy-11-02590/article_deploy/agronomy-11-02590.pdf
- Uganda Coffee Development Authority (UCDA): Arabica Coffee Handbook - Chapter 7: Diseases of Arabica Coffee and their Management (2019). https://new.ugandacoffee.go.ug/file-download/download/public/43
- CABI PlantwisePlus Blog: Coffee leaf rust: Spotting and managing Hemileia vastatrix (2022). https://blog.plantwise.org/2022/03/17/coffee-leaf-rust-spotting-and-managing-hemileia-vastatrix/
- FAO Regional Office for Asia and the Pacific: Arabica coffee manual for Lao PDR - Pests and diseases (Coffee leaf rust) (2005). https://www.fao.org/4/ae939e/ae939e0b.htm
- World Coffee Research: Varieties catalog: Ruiru 11 (None). https://varieties.worldcoffeeresearch.org/varieties/ruiru-11
- World Coffee Research: Varieties catalog: Batian (None). https://varieties.worldcoffeeresearch.org/varieties/batian
- BRACOL dataset (Krohling, Esgario, Ventura; Mendeley Data): BRACOL - A Brazilian Arabica Coffee Leaf images dataset to identification and quantification of coffee diseases and pests (2019). https://data.mendeley.com/datasets/yy2k5y8mxg/1
- Cenicafe (Colombia): Enfermedades del cafeto en Colombia - Mancha de hierro (Cercospora coffeicola) (2003). https://biblioteca.cenicafe.org/jspui/bitstream/10778/993/20/18.%20Mancha%20de%20hierro.pdf
- arXiv (Esgario, Krohling, Ventura): Deep Learning for Classification and Severity Estimation of Coffee Leaf Biotic Stress (2019). https://arxiv.org/abs/1907.11561
- KALRO Coffee Research Institute (Current Agriculture Research Journal): Efficacy of Two New Fungicides Against Colletotrichum kahawae Infecting Coffee in Kenya (Malaka, Alwora, Bonuke) (2021). https://agriculturejournal.org/download/10709
- Uganda Coffee Development Authority (UCDA): Arabica Coffee Handbook (5.0 Introduction; 5.1 Soil analysis; 5.4.2 Farmyard manure) (2019). https://www.ugandacoffee.go.ug/file-download/download/public/43
- University of Hawaii CTAHR: Growing Coffee in Hawaii, revised edition (soil; weed control/mulch) (2008). https://www.ctahr.hawaii.edu/oc/freepubs/pdf/coffee08.pdf
- Experimental Agriculture (Cambridge, peer-reviewed): Effect of soil drying on rate of stress development, leaf gas exchange and proline accumulation in robusta coffee clones (Tesfaye et al.) (2014). https://www.cambridge.org/core/product/C1008695632CC79FF19E0D2ADE856BA4/core-reader
- Ciencia e Agrotecnologia (peer-reviewed): Gas exchange and carbohydrate partitioning in coffee seedlings under waterlogging (Silveira et al.) (2015). https://scielo.br/j/cagro/a/Y6nPvg8pDpg98THS8PGbWJP/?lang=en
- Synergistic Hawaii Agriculture Council / USDA-ARS: Post-Storm Recovery Guide for Coffee, v1.0 (2026). https://konacoffeefarmers.org/wp-content/uploads/2026/03/post_storm_coffee_recovery_guide.pdf
- Infonet-Biovision (Biovision Foundation), archived copy: Coffee: pests and diseases (plant health page) (2012). https://kolibri.teacherinabox.org.au/modules/en-infonet/export/default$ct$140$crops.html
- PLOS ONE (icipe authors): Some Like It Hot: The Influence and Implications of Climate Change on Coffee Berry Borer and Coffee Production in East Africa (Jaramillo et al.) (2011). https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0024528
- Journal of Pest Science (record in Uganda National Research Repository): Contrasting effects of shade level and altitude on two important coffee pests (Jonsson et al.) (2015). https://nru.uncst.go.ug/handle/123456789/3480
- Tanzania Coffee Research Institute (TaCRI): Good Agricultural Practices Research Programme (None). https://tacri.org/research-programmes/good-agricultural-practices-research-programme/index.html
- Tanzania Coffee Research Institute (TaCRI): Taarifa ya Mwaka 2006/2007 (Annual Report, Kiswahili edition), matched line by line with the English edition (2007). https://www.tacri.org/fileadmin/03_uploads/03_documents/TaCRI.Reports/tacri-Taarifa_ya_Mwaka_2007.pdf
