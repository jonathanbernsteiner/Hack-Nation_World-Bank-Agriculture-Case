# Brainstorm transcript

Team brainstorm for the Hack Nation × World Bank agriculture case.

- **Source:** Notion AI meeting notes on the team's Hack Nation page: https://app.notion.com/p/dryftteam/Hack-Nation-3ee2073003ce80468657e08de8ba7ae3 (current meeting: "Meeting @Today")
- **Last synced:** 2026-10-03 20:14 UTC (Notion page last edited 20:14 UTC)
- **To update:** ask Claude to "sync the transcript". It pulls the latest from Notion, replaces the raw transcript below and updates the summary sections.

The transcript is automatic speech-to-text, so expect errors. For example, "Cloud Code" / "Cloud MD" mean Claude Code / CLAUDE.md, "a disease on their blood" probably means on their plant or leaf, "World Health" probably means World Bank, "metamans" / "mill man" mean middlemen, "kiamas" means chamas and "eight CCOs" probably means SACCOs. "Neuer" / "Newark" mean Noor, "11 lives" / "11.1" mean ElevenLabs, "Olive Trillo" / "Julio" probably mean Twilio, "chirps" means CHIRPS and "Harvard's estimates" means harvest estimates.

---

## Key points so far

Summary of the raw transcript. Not verbatim.

### The idea (recap from the meeting)
Create a **record for each farmer** of what they do and see on their farm, captured by voice. Noor comes back from the field and calls a number, where an AI talks with her in her language (the first plan was a voicemail). Over time this builds a record for her and a dataset across all farmers.

### Why voice, and why AI
- **Voice:** local language; it may be late at night with no electricity to look at a screen; older farmers may not be able to type. Talking is the easiest.
- **Why AI and not a spreadsheet or Google:** turning speech in a local language into structured records. The team sees this as the easy justification.

### What the record is for
**For Noor (individual record)**
- **Loans:** a lender won't trust a farmer they've never met without records of the field and yields. Farmers without a credit history get bad loans or none. The team rated this "super, super important".
- **Certification:** organic, Fair Trade and Rainforest Alliance need written records of inputs and practices, and certified coffee sells at a premium.
- **Farm memory:** what seeds she planted, what worked, how she treated the soil five years ago.
- **Succession:** her daughter will probably take over the farm, and today there's no diary, "it's just vibes".
- **Custom advice:** after a problem ("my crops are bad, what happened?") and before planting (weather, fertiliser patterns).

**For everyone together (collective record)**
- **Smarter expert visits:** the expert who comes twice a year can prioritise. For example, if three farmers in region 1 report the same issue, go to region 1 first. Concern raised: farmers are remote, so a visit may still come late. Region-level priorities help with that.
- **Registry:** farmers become known, so they can reach government services and loans. Ukraine example (from the brief): a registry reached 150,000 farmers.
- **Group loans:** lend to all farmers of a region at once, which gives them bargaining power.
- **Collective knowledge:** what works and what doesn't across farms. "Is it just me?": if everyone's yield dropped, it may be climate; if only mine did, it may be my practices (planting day, too much shade).

### What the team is most sold on
**Loans, (government) services, certification and better-targeted expert support** are the main problems we help solve. Two teammates agreed loans and certification are especially important in emerging markets.

### Pitch story: the cooperative sees the whole year
A teammate's write-up, read out in the meeting:
- Today the cooperative sees Noor **once a year**, when she brings in her coffee. The rest of the year it has no idea what's happening on her farm.
- With our system, Noor calls a number and the cooperative sees what's happening **across every farm, all year**.
- It can **spot problems early**: if five farmers report the same disease in the same place, it can contain it before it spreads. This "early prevention" was the teammate's own addition.
- It knows **how much coffee is coming**, from past records and this season's reports.
- It can help Noor **get a loan** and **get certified** (inspectors need records), and keep the **government's farmer list** up to date.

### Main effect vs side effects
- The team marked the board's long-term uses (**loans, certification, historical and family knowledge, land sale**) as **side effects**: benefits that come from simply having the table. A teammate added that these are probably what the World Bank cares about most.
- **Expert strategic help** is also a side effect and not the top priority: there are too few experts, and they don't have all the information either.
- **AI advice can ease the expert bottleneck:** custom local advice on the phone covers the routine questions, so the expert only handles high-priority cases.

### Day-one value: advice
- Generic advice is a "trap": farmers can Google it, and most other teams will build it.
- But it's the **carrot** that makes a farmer call on day one, before the record is worth anything.
- **Earlier decision:** don't spend more time on it now. Build it near the end, once the data pipeline works.
- **Update later in the meeting:** the demo must show that the call gives advice, as the short-term benefit. Advice now comes at the end of every call, based on weather, rainfall and soil data (see "What the demo shows").

### Debated but not pursued
- **Selling the data** to large firms (e.g. commodity futures): valuable, but the World Bank is unlikely to welcome it.
- **Cutting out the middleman / pricing power:** the list alone doesn't give pricing power; the cooperative does. Kept as a side thought.
- **Yield drop and climate change:** needs more research (TBD). The team still wants to give input that helps farmers grow more, e.g. different planting methods.

### Risk raised: data security
If buyers could see the dataset, they could undercut farmers with bad yields. **Middlemen and buyers must not get access.** The cooperative can, possibly anonymised, for the collective good. Expect judges to ask about this.

### Tech: the hardest part
Ingesting voice in a local language and turning it into structured data (a "data frame"). The brief lists language resources for this, such as Meta's speech models (1,000+ languages) and NLLB-200 translation (200 languages).

### Channel: an interactive AI phone call
Farmers like Noor don't have their own smartphone, so the only options are **calls or SMS**. Sending audio over 3G costs data money, but a normal voice call doesn't.
- First plan: Noor calls a number and **leaves a voicemail** that AI processes. This stays the basic fallback.
- **Agreed later:** she **talks to an AI on a normal phone call** that asks follow-up questions and answers hers. A teammate built an interactive AI phone line at a previous hackathon.

### The call, step by step (agreed)
1. **First call only:** onboarding, where she sets up her identity and a **PIN**.
2. **Every call:** she enters her PIN, so the system knows who she is.
3. "**Tell us what happened today.**" A free-flowing recap from memory, as long or short as she likes.
4. The AI **asks only about gaps** in what she said. The team wants to avoid a tedious form ("What did you do in the morning? In the evening?").
5. **Advice for tomorrow:** weather, fertiliser and what's happening nearby.
6. "**Any other questions?**" For example, "how is the crop looking on the east side of the village?"

- Advice stays **in the same call**, not in a separate call or text the next morning. Regional updates that need many reports can come weekly, mentioned in that night's call ("based on what we heard yesterday…").
- Whether farmers can **query** the collective record is left open.

### Farmers without their own phone
Some households share one phone across five houses, or have none. Idea: on a borrowed phone, **call the number and enter a personal PIN or say your name**, so anyone can add to their own record without owning a phone. The team liked this. It means records must be stored centrally, not on the phone.

### Where the AI runs: local box vs cloud
Earlier options: a box on site in each village, storing on the device and transferring later, or a hosted server. One teammate said individual devices will break, so the data should sit somewhere decentralised. Another noted the PIN idea needs a central store. For the demo, the team wants something visible, like a laptop acting as the server, so judges see "there's a product".

Long debate in the latest part of the meeting:
- **For the cloud:** a normal phone call needs no internet. A farmer can call a number in the capital, and that line can connect to any AI, even one hosted abroad. A local model only really pays off for things like photo checks on a phone with no signal. Local models are also less capable and slower: the reply comes after a pause ("one, two, three"), not instantly.
- **For local:** the brief says the **core feature must work offline**. Local inference costs nothing but power, which matters for low-income farmers. The cooperative office has no internet, so its dashboard has to be local anyway. And "anyone can build it in the cloud", so local makes the demo stand out.
- **Costs both ways:** cloud calls cost per minute (a teammate quoted about 6 cents a minute). A local box has set-up costs. Starlink is too expensive (about $150 a month). The World Bank will only roll out something low-cost.
- **Bigger picture:** the people who look across many villages (e.g. experts) sit further away, maybe ten villages over. A box in one village only serves that village's farmers.
- Asked whether the choice changes what we build, the team said no, so it shouldn't hold up the build.

**Plan for the demo (from the builder):** Twilio routes the call to a laptop, which transcribes it, extracts the data into a local database and shows a dashboard. In the real world, the laptop would be a **box with a SIM card and a GSM adapter** that takes the calls and does everything locally ("buy a SIM card at the supermarket, plug it in, and it runs").

### Who sees the data: the cooperative office
The cooperative has a board of farmers and one person in its office, with no internet. They see the local dashboard, with warnings like "disease reported over here", so they can send people to spray before it spreads. The map of problems also goes to the expert.

### Languages: ElevenLabs won't cover it
ElevenLabs doesn't support the languages we need (around 200 in sub-Saharan Africa alone), and it's closed source, so we can't train it on a dataset. We need an open-source speech model instead. *Claude's note:* the brief's Meta speech models (MMS) are open and cover 1,000+ languages; see "Tech: the hardest part".

### For loans, the record needs sales and payments too
- Lenders care most about **what you sold, for how much, and what you were paid**. Farm activities alone aren't a credit history.
- So the record should have **more layers**: farm activities plus sales and payments.
- The hard part: many farmers are paid **in cash** and have no bank account. Some use e-wallets (GCash in the Philippines was given as an example).
- *Claude's note:* the brief says Noor already uses **mobile money** (in Kenya that's M-Pesa). With her consent, her payment history is a digital record that already exists.

### Can the record be trusted?
- Concern: a farmer could simply say or write false numbers.
- **Verification idea:** buyers often hand over paper receipts. Noor keeps them, and the expert photographs them on the twice-yearly visit to check them against what she said in her voice notes.
- Counterpoint: buyers' own record-keeping in a village isn't reliable either. Sales can be tense cash deals, sometimes not safe.
- **Strongest answer:** with a big record across the whole region, **outliers are easy to spot**. If one farm's numbers don't fit its neighbours', they stand out.
- That regional view also matters for lenders: they need to judge how likely a farm's crop is to turn a profit and pay the loan back.
- Some lenders are also the buyer: they lend inputs and buy the harvest, which cuts out middlemen.
- **Later in the meeting:** it's nobody's job to track down a farmer who lies. Outlier flags are mainly there to **check that the AI extracted the right thing**. Loan officers will spot outliers themselves once they use the data.
- Per the brief, sale prices aren't negotiated by the cooperative: a middleman shows up and sets the price.

### Another use: selling land
A record of how fertile the land has been over the years helps a farmer **negotiate a better price when selling her land**. Without one, a buyer can't tell good soil from sand.

### Geotagging
Mentioned briefly: with a geotagged location for each farm, this data is easy to get. *Claude's reading:* a farm location lets us attach rainfall, temperature and soil data by coordinates (NASA POWER, CHIRPS and iSDAsoil, all listed in the brief) without the farmer reporting it.

### Concern: too many use cases
A teammate worried that a voice diary alone won't solve the problem, and that the idea now has too many use cases.

### Credit data when there's no payslip
- Lenders in emerging markets normally want payslips. Farmers who aren't employed don't have them, so some lenders use other records, such as **phone bill payments**. Buying airtime daily in small packages instead of monthly suggests tight cash flow.
- The team can't capture that data. For loans, the most credible sources remain **how much a farmer sells and how well the region is doing**.
- Concern raised: none of this can be verified without paper records.

### How smallholders borrow today
- **"5-6" lending (a teammate's experience in the Philippines):** borrow $5 on Monday, pay back $6 at the end of the week, about 20% interest per week. Lenders are individuals from the village, and they collect by intimidation.
- **Kenya:** **chamas** (villagers pool money and lend to each other), **cooperative advances** before the harvest, and **SACCOs** (savings and credit cooperatives).
- Next step from the meeting: check how other startups do it (see the research section below).

### Kenya may already have a farmer registry
In the meeting: in Kenya, farmers registered through local officers receive an **e-voucher on their phone** to collect subsidised fertiliser, so a registry exists there. *Claude's note:* this is likely the **KIAMIS** system behind the national fertiliser subsidy. So "we create the registry" only holds where none exists, as in the brief's fictional Ondera. Where one exists, our record plugs into it instead. To verify (see "To check").

### Who pays for it?
- Question raised: for the bigger picture, how does this become a sustainable business, and who finances it?
- Answer in the meeting: the **World Bank** would fund it, as a public tool rather than a profit-first product.
- Someone outside the team ("Dr. Ali") liked the idea.
- Later: with cloud calls, someone pays for compute and call minutes (the team assumed the World Bank); local inference costs only power. Either way it must be cheap, or the World Bank won't roll it out.

### What the demo shows (agreed outputs)
1. **The phone call, live:** one of us calls and talks to the model on camera. The team called this "the crux of our demo".
2. **The data table** the call fills: activities, yield, sale price.
3. **A map of irregularities** for the cooperative and the expert: regional warnings (e.g. diseases), outlier flags, a review queue for records the AI probably got wrong, harvest estimates and farmer profiles.
4. **A record for a lender:** the call history becomes a one-page financial record (e.g. a PDF). Lenders have internet, so it can be uploaded or emailed, with the farmer's PIN as consent. Another option: call the number and have the record read out. Informal lenders without internet were cut ("more like scammers").
5. **Advice from free data:** weather from the **NASA POWER** API, **soil** data and **CHIRPS** rainfall (historical and current). A teammate said these work over a 2G connection. Lower priority than 1–4.

### A visitor's questions
The team pitched the idea to a visitor and explained the brief's key constraint: **use AI in a way a Google search or spreadsheet can't**. Questions raised:
- **Are these problems the same in Latin America, Africa and elsewhere?** The team aims to make it region-agnostic, which makes it scalable for the World Bank.
- **Can the market size be quantified?** A back-of-the-envelope estimate is possible; not done yet.
- **Which farmers?** Small farmers. Bigger farms with many workers (raised by Colin) are better equipped already.

### Timeline and roles
- Intermediate pitches are at **5 pm** (local time). At 12:25 the team agreed to plan a timeline from 12:45 and a development pipeline, to decide what to build first.
- One teammate takes **slide design for the pitch and video editing**, and supports elsewhere. Another offered to help with a tutorial.
- For the demo: "move fast". In the video, steer the caller into one specific flow rather than handling every possible input.

---

## Whiteboard

![Team whiteboard, 3 Oct](brainstorm-whiteboard.jpg)

Transcribed by Claude; ⭐ marks items starred on the board.

**Left: the record as a table.** One block of rows per farmer, with more farmers below ("⋮"). Each row holds:
- activities
- yield
- sale price

**Middle: what the individual record is for**
- ⭐ (land) sale
- ⭐ loans
- ⭐ certification
- [custom advice]
  - post- (after a problem)
  - pre- (before planting), using **rainfall** and **fertilizer** data
- historical knowledge
  - familial (handed down in the family)

**Right: what the collective record is for**
- ⭐ Expert = strategic help
- Bigger / crowd-sourced loans
- Collective knowledge

**Far right, future:** collective bargaining power.

**What this settles:** a record row is *activities, yield, sale price*. The starred priorities are **land sale, loans, certification and the expert's strategic help**. Custom advice is shown in brackets as a side feature, which matches the meeting's "build it last".

**Since this photo:** the team marked main effects vs side effects on the board and added the demo outputs (data table, map of irregularities, lender record). Upload a new photo to sync those.

---

## Research: how others lend to smallholder farmers

Compiled by Claude from web sources on 2026-10-03.

| Model | Example | What they base the loan on | How it's repaid |
|---|---|---|---|
| Farmer self-tracking + score | **FarmDrive** (Kenya, founded 2014) | Farmers log revenues and expenses by SMS/USSD on basic phones, combined with satellite, soil, weather and phone data | Via mobile phone |
| Field data + satellite + ML | **Apollo Agriculture** (Kenya, Zambia) | Field officers collect farm data in an app, a verification team checks it, then ML adds satellite yield estimates and credit bureau data | Inputs on credit, automated decisions |
| Buyer payment history | **Safaricom DigiFarm** (Kenya) | Repayment history plus **payment history from the factory/buyer**; limit up to 100% of average earnings | Deducted from produce sales before the farmer is paid, or via M-Pesa |
| Cooperative delivery records | **Coffee Cherry Advance Revolving Fund** (Kenya, government) | Cooperative membership + coffee cherry delivered (advance of 40% of the expected price, or KSh 20/kg cherry) | Deducted when the coffee is sold |
| Group liability | **One Acre Fund** | Farmers in groups are jointly liable; inputs only | Flexible instalments before season end; ~99% repaid |
| Lend + buy the harvest | **Babban Gona, ThriveAgric** (Nigeria) | Inputs, training and credit as one package | Repaid from the harvest they buy (offtake) |
| Lend to the cooperative | **Root Capital** | The cooperative's future sales contracts with buyers act as collateral | The cooperative repays from export sales |

**What this means for our idea**
- **FarmDrive is our closest precedent:** farmers recording their own farm finances on basic phones to build a credit history. Our twist: **voice in the farmer's local language**, for farmers who can't or won't type.
- **Nobody trusts self-reported data alone.** Every lender anchors it to something verifiable: buyer or cooperative payment records, field officer checks, satellite data or group liability. We should show at least one anchor, e.g. regional outlier checks or the expert's receipt photos.
- **Repayment is usually taken from the harvest sale.** That's why lenders want sales records, which matches the "sale price" column on our whiteboard.
- **Gap in Noor's case:** the brief says she sells her parchment "to whichever middleman drives up the valley", so the cooperative has no record of her sales. Her voice record fills exactly that gap.
- **We don't need to build a lender.** We build the record, and with Noor's consent it feeds existing lenders and funds like these. For the demo, a one-page "season summary for a lender" (activities, yield, sales, how it compares with the region) would be a concrete output.

Sources: [GSMA on Apollo Agriculture](https://www.gsma.com/solutions-and-impact/connectivity-for-good/mobile-for-development/blog/ai-driven-smallholder-farmer-lending-in-africa-insights-from-apollo-agriculture/) · [FarmDrive (Capital FM)](https://www.capitalfm.co.ke/business/2017/02/safaricom-spark-fund-backs-agricultural-analytics-startup/) · [FarmDrive (UN Africa Renewal)](https://africarenewal.un.org/en/magazine/linking-smallholder-farmers-banks) · [DigiFarm FAQ (Safaricom)](https://www.safaricom.co.ke/media-center-landing/frequently-asked-questions/access-bank-farmer-cash-credit-strategy) · [Coffee Cherry Fund (Business Daily)](https://www.businessdailyafrica.com/bd/markets/commodities/coffee-cherry-fund-advances-to-farmers-hit-sh6-7-bn-4867766) · [Coffee cherry fund (Citizen Digital)](https://www.citizen.digital/business/coffee-cherry-fund-loans-match-farmers-earnings-312264) · [One Acre Fund (How We Made It in Africa)](https://www.howwemadeitinafrica.com/what-one-acre-fund-can-teach-us-about-supporting-african-small-scale-farmers/) · [Babban Gona (Food for Transformation)](https://www.foodfortransformation.org/results-details/babban-gonas-holistic-financing-approach.html) · [ThriveAgric (BusinessDay)](https://businessday.ng/agriculture/article/we-would-support-500000-farmers-with-56-4m-debt-funding-thriveagric/) · [Root Capital (Convergence)](https://www.blendedfinance.earth/blended-finance-funds/2020/11/16/root-capital)

---

## Use cases and problems tackled

Ordered by the team's current priority. Combines the meeting, the whiteboard, the chat with Claude and the official brief (Annex B). ⭐ = starred on the whiteboard.

| # | Use case | For whom | Pays off | Brief link |
|---|---|---|---|---|
| 1 | ⭐ **Record for loans:** field, yield, sales and payment history a lender can trust, checked against the region; group loans for a whole region | Noor, cooperative | Next season | Not named in the ag brief; best framed through the registry precondition (see "To check") |
| 2 | ⭐ **Record for certification premium:** voice notes become the input and practice records certifiers need | Noor, cooperative | Next harvest | No fair price at harvest; "connecting evidence to a pricing, market… next step" |
| 3 | **Registry:** every caller becomes a known farmer who can reach services | Cooperative, government | Ongoing | "The absence of a working farmer registry" is the binding constraint |
| 4 | ⭐ **Targeted expert support:** reports show which farmers or regions need a visit first; later called a side effect, not top priority (too few experts) | Extension officer | Now | Extension "staff shortages, manual data collection, delayed alerts" |
| 5 | **Collective knowledge:** what works across farms; "is it just me or the climate?" | Noor, cooperative | Weeks to years | "Yields have dropped… she cannot say why" |
| 6 | **Farm memory and succession:** a diary of what worked, handed to the next generation | Noor, her daughter | Years | Not in the brief; good human story for the video |
| 7 | **Day-one advice (the carrot):** after-problem and pre-planting advice at the end of every call; now part of the demo | Noor | Now | Timely, localized advice |
| 8 | ⭐ **Land sale:** proof of how fertile the land has been, for a better sale price | Noor | Years | Not in the brief |

---

## Use cases by timeframe

Claude's proposal on 2026-10-03, answering "what are the use cases, first individual, then collective, immediate / mid / long term". Not yet discussed by the team.

**Immediate** = next day to a few weeks · **Mid** = this season to the next harvest · **Long** = two years or more

### Individual: Noor

**Immediate**
- **Read-back:** after each call, a short voice reply confirms what was recorded ("You sprayed two rows on the upper plot. Correct?"). This doubles as the human check.
- **"Is it just me?":** the next day she hears whether neighbours reported the same problem, and that the extension officer knows. A web search can't tell her this, so it's a day-one reason to call that isn't generic advice.
- **Memory on demand:** "When did I last apply fertiliser?" is answered from her own record.

**Mid**
- **Season summary:** activities, harvest, and what she sold, to whom and for how much, on one page (or read out) for the cooperative or a lender.
- **Price memory:** what she was paid last time and this time, so she negotiates with the middleman with numbers.
- **Cooperative advance or input credit** based on her record and deliveries.

**Long**
- **Credit history:** two or three seasons of consistent records mean bigger, cheaper loans.
- **Certification:** organic needs about three years of records before the first certified harvest.
- **Yield diagnosis:** her yield trend compared with her neighbours' separates her practices (shade, old trees, pruning) from climate.
- **Succession and land:** a diary for her daughter; proof of land quality when she sells or leases.

### Collective: cooperative, extension officer, region

**Immediate**
- **Early warning:** several reports of the same symptom in one area in one week trigger an alert to the extension officer, plus a visit list ranked by urgency.
- **Broadcast back:** a voice message to every member in that area ("rust reported nearby, check your trees"). One farmer's report helps everyone.

**Mid**
- **Harvest forecast:** expected volume per area, so the cooperative can plan buyers, transport and pre-harvest finance.
- **Price transparency:** anonymised prices that middlemen paid this week, so members know a fair price.
- **Group certification:** Fairtrade, Rainforest Alliance and organic certify smallholders as groups, so the cooperative needs records for every member farm (an "internal control system"). Our record feeds that. Certification is therefore both an individual and a collective use.
- **Registry and group loans:** a list of active farmers with records, for services, subsidies and group lending.

**Long**
- **What works here:** which practices go with better yields across farms, giving local advice that beats generic search.
- **Climate or practice:** regional yield trends combined with rainfall and soil data by location.
- **Insurance:** area-yield index insurance needs years of yield data per area.
- **Bargaining power** (the whiteboard's "future"), and **local-language voice data**, used only with consent, to improve speech AI for that language. This ties into the "localizing AI" question.

### How to make the record more useful
1. **Give something back on every call** (read-back plus one useful line). Otherwise farmers stop logging and the long-term uses never arrive.
2. **Record numbers, not just stories:** date, plot, quantity, price, buyer type and payment method. Loans, certification and forecasts all need numbers.
3. **Tie each record to a place** (plot or geotag), so weather and soil data attach automatically.
4. **Anchor it to something verifiable:** cooperative delivery records, mobile money with consent, receipt photos at expert visits, and regional outlier checks.
5. **Show one record in several views:** voice for Noor, a list or map for the cooperative, a one-page summary for a lender and a practice log for certifiers. Noor decides who sees what.

**For the pitch:** the immediate collective uses (alerts, "is it just me?") keep Noor calling. The long-term individual uses (loans, certification, land) make the record valuable. One needs the other.

---

## Still open

**Decided: the channel is an interactive AI phone call**
The brief says Noor's own phone is used for "calls, messages, and mobile money" (a basic phone), and her daughter's smartphone is only around on weekends. Voice calls work on any phone and use no mobile data. The meeting first settled on a voicemail, then agreed on a live call with an AI that asks about gaps and gives advice. Voicemail stays the fallback.

**Decided: callers identify with a PIN**, set once at onboarding, so shared phones work.

**Decided: the demo outputs** (see "What the demo shows"): live call, data table, map of irregularities, lender record, then advice from weather and soil data.

**Decide now (blocks the build)**
- **Setting: which country?** The brief uses the fictional Ondera highlands and Ondera Coffee Cooperative. Countries are named freely in the notes as examples; the team still has to pick the setting for the pitch. This also decides the demo language and the speech model.
0. **Where the AI runs.** The meeting leaned local: in the demo, Twilio sends the call to a laptop; in the real world, a box with a SIM card at the cooperative. This matches Claude's earlier suggestion of **one small server per cooperative**. Still open: how data from many boxes reaches the people who look across villages, e.g. experts. *Claude's idea:* each box sends short anonymised summaries over SMS or a little 2G data.
1. **The brief's "one better agricultural decision".** Loans and certification are outcomes, not farm decisions. Frame the tool as "documenting a field observation" and "connecting evidence to a pricing, market or extension-service next step", which is the brief's own wording.
2. **What one record contains:** the whiteboard sets the core as **activities, yield, sale price** per row, one block of rows per farmer. Still to detail: date, plot, inputs used, observations, and how she was paid (cash, mobile money). This is the "data frame" and drives the whole build.
2b. **How records become trustworthy:** regional outlier checks, the expert photographing paper receipts on visits, and mobile money history with consent. Pick which to show in the demo; outlier checks are the easiest to build.
3. **Who sees what:** Noor owns her record; the cooperative sees it, possibly anonymised; lenders or certifiers only with her consent; buyers and middlemen never.
4. **Leaf photo checker:** effectively dropped. The meeting said farmers won't scan leaves; they'll report symptoms on the call. A photo model on a phone stays a "maybe" for later.

**Decide during the build**
5. **Daily incentive:** *answered:* advice on every call (weather, rainfall, soil) plus the chance to ask questions.
6. **Speech-to-text for the local language, then extraction into fixed fields** from a fixed list, so nothing is invented. ElevenLabs doesn't cover the languages, so use an open-source model.
7. **Human check of each record:** e.g. read the extracted record back to Noor to confirm, as a guardrail. The meeting added a review queue for records the AI probably got wrong.
8. **Model size and speed** for the "small model" rule: a local model replies after a pause, so pick one small enough for a laptop but quick enough for a live call.
9. **A less-supported language:** what happens there? The brief says to expect this question.

**To check (facts we're relying on)**
10. **The Ukraine example:** the brief says a working farmer registry "unlocked advisory services, insurance, and grants for 150,000 farmers". It doesn't say loans, so quote it as written.
11. Which records each certification really requires, and whether voice-based logs would be accepted.
12. Whether lenders would accept these records. See "Research: how others lend to smallholder farmers" above.
13. Problem evidence with source, year and country: FAOSTAT coffee yields, extension officers per farmer (once we pick a country), certification premiums, smallholder access to credit.
14. Test data without real farmer recordings: synthetic voice notes, clearly labelled as synthetic.
15. **Which countries already have a working farmer registry** (e.g. Kenya's KIAMIS fertiliser e-vouchers, mentioned in the meeting)? This matters once the team picks a country: there, use case #3 becomes "feed the existing registry" instead of "create one".
16. **Who pays after the first funding?** The meeting said the World Bank would fund it. The brief scores scalability, so judges may ask who runs and pays for it afterwards. *Claude's options to discuss:* the cooperative (small fee from the price premium or advances), the government extension or registry budget, or lenders and certifiers paying per verified record with the farmer's consent.
17. **NASA POWER, CHIRPS and soil data "over 2G":** *Claude's note:* these are internet APIs, and 2G data is a slow mobile internet link, so the box needs a SIM with a small data plan. The downloads are small, so it's realistic, but it isn't "offline". Keep the offline core as call → transcript → record, and present weather as an add-on.
18. **A GSM box that answers calls:** *Claude's note:* a common set-up is Asterisk with a voice-capable USB GSM modem (chan_dongle / chan_quectel). Check it works before promising it in the pitch.
19. **Cost per call:** cloud call providers charge per minute (about 6 cents was quoted); compare with a one-off local box.
20. **Market size:** a back-of-the-envelope number for the pitch, since the visitor asked.

---

## Raw transcript

I already invited you to a chat, get rapport. Do you also have GitHub or Cloud Code? Wait. That meant right here.

Can you type in your email or username? Thank you. Can you also type in your username? Yes. So normally it's like the URL, like that, and that's that. Yeah, I think that's just my first name.

Sorry to interrupt you, but what is the outcome from But then, like, it has all this information, but what is it trying to do? Yeah, that's a great question.

I'm also about progress with Dargill. Thank you.

Coffee yield decline, right? The question is why did it happen, how do I fix it? There's no, right now if I'm in the position of a farmer, I've done my best, right? Maybe I've talked to people in my village, figured out, what are you planting, what does the weather look like? Maybe I Google searched on my daughter's phone, figure out, is today a good day, is it raining tomorrow? Then when the coffee yield shows up and it's not great, Do other people have this problem? Is it my fault? Did I do something differently? Was there anything I could have done to prevent it? How do I prevent it next time?

And I think the thing with something like this is having this massive record could be helpful for just being able to pinpoint some of those issues and then prevent them in the future. So if you think about things like really simple, like trees that are providing too much shade to your plants because they're not getting enough sunlight, so your yield is bad. You're not going to know that by a picture of the leaf.

You're going to know that by somebody who's really, enforcing this model, it's like, hey, we planted this tree, or we cut down this tree, or now we have a lot of clouds today, that's something like that, we're able to have this record, so it's more of just this record keeping for them, but we can think a lot about what the specific outcome is that they currently can't have right now from a Google search perspective.

That's the number one issue that we need to find out what it is, so yeah.

Exactly.

But it's like more than like a long-term solution or they can also like let's say um the plants have some diseases they can also say it on the phone and maybe the day after they get like a response on what they should actually do.

We have an open source thing here.

Maybe being... Have you done both?

Okay So we want to then focus on short-term, unlike more on the long-term.

I think.

Isn't alter more important though? 'Cause like, I mean, it's--Yeah. Yeah.

But probably it's always a mix, like also for the long term you still want to get feedback on the weather and a lot of those things. I think it's always a mix. I get like long term, we can say yeah we start short term, but long term the record will be more and more valuable. And we kind of incentivize that the people do it also daily. So if they do it daily, they also get something back, something more in dot angle.

So with time we build up the huge, huge record and then after like one or two years it will be like super, super powerful. We still need to give them results now. Obviously if they have a disease on their blood, I think that's the most urgent one. We need to give them feedback on the disease. We can't say, "Okay, you need to build up the record." You're right.

You're right. You're both, right? The short term is the long term. I don't think is the one thingI think the one thing we choose is what's happening in the short term and what's happening in the long term, that's one thing, but you do need both. So I think we put them together. The question we now have to answer is, So in the prompt, it said-identify a solution for documenting field observation. So this is a mechanism that we've now talked about. What is the output of the field observation? Is that what we just need to solve next? And then we can start really thinking about implementation.

So maybe we do like 10 minutes of just like brainstorming and then we're back.

So if you interpret what you said, you just take the outcome of what I said, right?

It was a little bit like... To answer your exam question, like, okay, we have this idea, voicemail, whatever, to create this record, what does that do? How does that help us?

Interesting. Anything that has to be labeled as fair trade, organic, or rainforest alliance, all require written input records. So if, and obviously you can charge a premium for something like that, so we're thinking about pricing and our ability to make more money based on our crops. Having this recorded, record of how she planted everything and the practices that she used in order to make the crops go to the shade.

One example of an output of why you would want to keep it like this. Just maybe.

So from what I understand, like super dumb terms, as much as maximums are profit. Yeah.

Another potential output for something like this is if everOne is speaking, you know,A one minute voicemail into your phone.

Mm-hmm. Mm-hmm.

One person who comes at max twice a year. Yeah. If you don't want to land, yeah.

Okay, let's... Put all together How do we want to map it out? So first we know what the tool that we now build. And now like the use cases for each of the programs, right? Okay. Yeah, you can start. I mean, you already mentioned something. I directly throw it in our Cloud MD. So type it in there. So that's it. You want me to talk about what I'm thinking? Yeah, sure, go for it. I'll be off, also on Notion, cool.

Okay, so I think the idea is to recap is like how can we create records for individual farmers to be able to track what their processes have been on a daily basis. As we think about this, Side effect, you also have more registered farmers because it was also one problem.

More farmers were on record because one problem was that reach outdoor farmers and that would be like a side effect.

100%. Can you repeat? 40 minutes.

Like not only would this be valuable just for you as an individual farmer, but now as we think about the World Bank which sponsors registries, if all three of us fill it out and we're all the farmers in some country, now they have all of the farmers in one data center.

Those are my points here.

The reason we would wanna potentially consider voice for something like this is because it's like local language, you got farmers, I don't know what like, and functionality is available late at night. Electricity might not be available if you're trying to see something on your phone. These are the older people that might not be able to, I don't know, type. So I feel like talking is probably the easiest.

Or literally, trying to find your type of--Everyone, that's a classical to everyone. um Why this would be AI and not something that's like a spreadsheet, Google search, whatever, is because of the voice translation. So that feels like an easy justification for us. And then as we think about where this is valuable, a couple things. So one, what I was mentioning, certification. So if you want to certify it, organic, fair trade, whatever, you need to have records of what you did and how you planted your crops.

So that's one option. Other ones, if you want to go alone, you need to be able to have records of what your field was like,How it went every year is that I trust you as a farmer and said, "You're just coming to me "and I've never met you before "and you're asking me for a million dollars, right?" I think that's also super important.

In our concept, we pitch how we do we bring it actually. Keep it.

Totally. Also for the community effect in that, okay? And the other piece here is what we got, what we were talking about with the-Expert. That comes twice a year. They're able to be more strategic about who they go to when, because he needs more help quickly. So that's why they're like so. I think there's lots of positives with something like this.

To that point, I have the exact same thing. Getting these people on the list, 'cause these people aren't known. And if they want help from World Health or whatever, they need to be honest. I just had some facts here. Like 150,000 farmers in Ukraine that didn't have, they weren't on our list for anything once they got eventualized and finally got loans, all those sort of things. And they're able to get these government services, et cetera, which is something I think, yeah, we should focus on that then.

Trying to get people help, you know what I mean? 'Cause I mean, we're literally doing it for World Health. And if we can make their job easier by helping people, Yeah, but Hmm.

One thing that comes to my mind, I mean that the yields have dropped, that probably also has some long-term issues, but also some short-term things, what you need to fix. And I think the farmers might be especially interested in the short-term fixes, because they want to have the answer now. Like, what's going on with my plants? Like, is there any disease? And of course, then it makes sense, with all the data from the whole region, then maybe we can compare, like maybe a lot of farmers have the same issues.

A lot of those things. Hmm. What are the main problems that we tackle in our challenge? I get all these side effects, but do we also tackle the challenge that the yields have dropped and how do we tackle it?

So the yields dropping might not be a problem in reality, right? Like if my yields drop from 100 to 90 in one year, but everyone else's also dropped, then maybe that's just climate change. Right, like there's nothing that we can do about that just for me. There are questions about what you can do with that low yield if it's my fault, right? Maybe I planted on a bad day, the weather was bad, I'm shading my crops too much, something like that.

So there's like,TBD.

okay we still need to do more research on that oneWhat you just said. Specifically about what though?

The climate change.

Yeah, the climate change. Yeah. Specifically, they never talked to the people about this. You know what I mean? It's more valuable to have a phone system to talk to other people about this. That's what the whole point was here, in the file at least.

But still we kind of need to fix the issue that they can grow more. For example, I know in Africa there's some concept that you planted in a different way, a lot of those things. So I think still we need to give input on that angle.

Yeah. The tricky part of giving input, though, is you can find out... search, right? For some times. Oh, okay, like what's happened to my crop? My leaves are turning yellow. Like maybe you don't need AI for that. And so we're trying to figure out where the AI is, but I agree with you. It's like you need that, and then you also need the carrot, right? Why would a farmer come to you on day one if they can just go to Google?

Hopefully you're providing something meaningful to them. So maybe that's our customer acquisition strategy is to be able to provide the free advice or customized advice. But then as we submit this and we're talking to the world, well, we can just Google search. Well, that's not the whole point. Yes. A benefit, right? That we're helping them with? But they can Google it too. And the piece that's risky here, just something to keep in mind, 'cause we're hoping, if we become a finalist, we'll ask this, it's just like, what about data security rate?

If all of us have really bad yields, or I only have a really bad yield, and the buyers have access to now this big data set, they can undercut me in a way that they couldn't before because they didn't have the visibility. That makes sense.

That means we need to cut out the metamans.

Not cut-off more lines, but make sure they just don't have access to the data. Like the co-op can have access, but maybe that is still anonymized, so you don't actually know who it is, but they use it for the collective good. We can talk about that down the line, which is something that's going on. Thank you. Do you like this idea? Yes. Where do you guys see problems? Or any sort of questions that we should dig into.

I'm just curious about how this will work. The final outcome, I still am not quite understanding. Is it just to get them on this list like you're saying?

Yeah, yeah, maybe it's a good word. There's a lot of benefit, but it's hard to see because it's It's a very rudimentary product, right? We're just making a list. Okay, so this is one row. And then ultimately we're creating this like Really long data set, right? There's a ton of benefits here. So at the micro level, what are our benefits? What are we talking about? You now have a record for things like loans.

Mm-hmm. I see the loan record is super, super valuable.

You also now have a record for certifications. So certified organic examples that you can increase your sales. Now, if we think about it not just from an individual record standpoint, but from a broader collection, what do you have?

I don't think I'm gonna say monster. I'm not gonna lie to you.

Yeah, okay. So you have collective knowledge, right, about what's happening. So there's like live, well, okay, here. Let's do that more obvious one first. Is that person, what was it called?

A... Which one are you? Oh, the person. Oh, yeah. I forgot what it's called. I'm gonna call it the expert.

I'm just gonna call him the expert.

The expert, yeah.

The expert can now be like strategic. Yeah. in their support. Right, that's the first thing. So the people who actually need help first.

Then with the farmer's list.

Yeah, the whole list. So now if we think about loans, we can do like a bigger loan.

This extra person only comes twice a year, you know what I mean?

Exactly, but they have no idea who to go to when.

Wouldn't it be too late anyway if they came like two years later or whatever?

They come twice a year.

Okay, twice a year. But wouldn't it still be too late? Normally, yeah.

Because imagine you're just like, close your eyes and you're like, I'm going to pick somebody to go to today. Versus if I have something that can anonymize the data or maybe it doesn't need to be super anonymized for the expert, but it tells them like, you should go to this person tomorrow. Okay.

The question is still though if they don't come because they're so remote to farmers, that could also be an issue. Because I think they just can't like hand back to which farmer they go.

I agree. They could however do, if this is a co-op, like this is region one. And then three people or two people, three have said they've seen like an issue. Then it's like okay, prioritize this region.

Something.

Okay, so strategic support from the expert. There is this idea of like crowdsourced loans. So if we now have a collective herd of all the farmers in this region, then you can make a loan to all the farmers at once, so there's the sparking power that comes from the worker keeping?

Yeah, also individual. Yes. What else comes from? A huge record.

of farmers. That's just valuable in and of itself, no? What did you say? It's just valuable in itself.

Well, why? It's just a list.

No, like for example, if I could, no, that's a dumb idea.

No, no, say it.

I'm just saying these data sets could be like immensely valuable for like huge firms. Like do you like future stuff on this stuff? Like I remember like when I was learning all the quant stuff, like they just do like futures for like wheat in Brazil or whatever.

You know what I mean? Yeah, yeah, no, that's fair. This is true, there's a lot of value in data like that. I don't think the world would think we would be super receptive to selling it to like a big brand.

But I agree with you.

There's like other monetary upside. Yeah. Okay, there's more here. I'm just forgetting now.

I mean one huge is probably that you can improve from the collected farmer that they can grow more because you have all the data. And obviously then you can see balance. What is working, what is not working, what are actually problems. Collecting knowledge.

I'm thinking more on the tech side. Sorry. I'm just thinking more on the tech side. I'm thinking about feasibility. Okay.

Yeah, let's get there.

Yeah, I know, I'm a little bit ahead of my player.

No, no, no, you're fine. Let's just make sure we're bought into this.

Yeah, yeah, I think that's important that we know what to build. Yeah. Sir, I'll look.

There's no place to lie. Um...

Hmm. Okay, so individual record, you're able to better apply for loans, better apply for certification. You can get individual, like custom advice, but I feel like this is kind of a trap. Because you can find advice on the internet. So this is like a sub-blog.

I agree on that. But I think it should still be brought, to be honest.

No, because every other team is going to do that. That's like what everyone's going to go for. Oh my gosh.

So this is like not our main, but it does exist.

Yeah, it does exist, or we could build it. Because obviously the farmers, like if you go 100 years back, people don't search something in the internet. You also need to have this in mind.

Well, no, like you're saying, but I mean, we can kind of just plug that feature in if we just build this whole infrastructure. Yeah, yeah.

And okay, there's two ways you can give advice. Also, post advice. Okay, my crops suck. what happened and it can tell you, but also pre-planting advice. You're about to plant this tomorrow because you told me that, but here's the weather patterns, the fertilizer patterns, blah, blah, blah. So there's two ways that could work. And then they would both be custom to your specific situation. Okay. What else is useful about creating a record?

I think like On the individual front, for future years, if you were just remembering how many seeds did you plant? Did it work? Did it not work? What happened to the soil? How did you till your soil to ensure that you've renewed the minerals? If you don't remember what you did five years ago that really worked, how are you going to ever do that in the future? So I think there's just historical knowledge.

Or even... Like one of the big benefits here, this farmer is going to die. The daughter is probably going to take over her farm. There's no diary, there's no record, it's just vibes, right? And so there's a little bit of like familial Yeah.

What else? Why would an individual record be helpful?

Obviously hyper specific advice or whatever, but aren't these people competitors?

It's a little tricky. No.

No, like, that could commune.

We don't have enough food on the planet right now to feed everyone.

Yeah, you're right.

So they're never going to, like, not make a sale. And together they're stronger because I can go like...

Sure, in practice everyone's stronger together, but I mean... Me and him are still gonna fight over the two dollars, you know what I mean? So I don't know, what-You don't have $2 to fight over though. Maybe. Like you have coffee plants, you have coffee plants.

So I don't know, what-You don't have $2 to fight over, though.

Maybe.

Like, you have coffee plants, you have coffee plants. If you work together, you can get a good price. If you don't work together, one of you is going to get a worse price than the other.

Because we underbought ourselves. You sell it for $2, I sell it for $1. And you sell it for $50, for 50 cent.

I guess they're making it public record then, like you said, okay, yes, that makes sense.

Maybe just, I think farmers, where the price of money is made, farmers mostly don't make their money, it's mostly the middlemen, because they buy it super, super cheap and then sell it super, super expensive. Some stuff, I don't say that we should do it now, but they cut out the middleman's, so it's more transparent. People saw my future on Weed.

Yeah, I think the way to do that is like-to cut out the middleman is probably somewhere around--With that, with them.

Oh, no, sorry. With the list, do we have the list? Farmers? Could have been knowledge bigger.

Like pricing power. I guess they don't, I don't think the list actually gives them pricing power. I think that's the go off.

No, but if you have all the records of all farmers, then you can definitely somehow cut out the middleman's because at the moment--You sell like wholesale. In the moment, the middlemen might have the record on the farmhouse. Just a side thought.

I don't know. Like future... Yeah, I agree with you. And I have collective gardening.

Because let's say the farmer's mill man knows this region and another region. So technically they could buy it cheaper here and more expensive wherever. Sure, sure.

Okay, so I think in this case, what I'm most sold on is loans, services, certifications and this on the ground support is more dedicated. I feel like those are like the mainProblems that we can help them solve.

Yeah, I think loans and certification, I agree. That's super, super, super important in the emerging markets. People always need loans that don't have a credit history, so they mostly get like super shitty, shitty loans or they don't get loans at all.

We're going to figure out the media value of stuff.

The immediate value of something like this Like the day one value?

Yeah.

Okay, you told me you were going to do... Yeah, this is your day one value.

Okay, yeah. We shouldn't spend a bunch more time there, I don't think.

At that day one value? Yeah, because everyone else can do that.

Totally agree.

But I think that's something we can build up quite fast.

I think we can do that near the end. That's the easiest part, once we have all the data in place.

Yeah, let's do it. I think the hardest part, well I actually don't know how to engineer a Bible, How do we actually build the piece that ingests from a different language and just collects it and puts it in a data frame? Maybe that's really it.

I feel like that's something at the heart. Maybe just the language is something. Because that's the only way to get to work is just building data layers. Like, how do you quote unquote stop for businesses?

Yeah. It's not that difficult.

Okay. Yeah. The language is part, like you said, they had some stuff here. What does it matter?

But they had a bunch, like 200 languages. Right, right. Yeah, a lot of stuff in Africa that's there. Yeah.

Okay. I want you guys to poke holes in this because it's really,If you're sitting in this woman's house, you are the woman you draw on the phone. You're out on the farm all day, come back. Just talk to the phone. Just talk to, like call a number? Yeah, call a number. And it goes to this voicemail?

But the connection's so bad anyways, I mean, you just capture that, like it's like an audio note or whatever. And then you text it? Yeah. Okay.

I don't know if it's possible with the phone.

Yeah, 'cause it's 3G or whatever. So 3G, does that transfer audio? But I want you to check real quick. Don't, yeah, yeah, yeah.

Also, what is, are there any notes about what kind of phone she has?

If you could just put a little packet, something. Sorry. Uh-uh.

I know this is kind of far in advance, but just start thinking about it. Is this gonna be like an on-premise little thing in our house or something, or is this gonna be on the middle of all the farms or something?

No, because it's hosted.

Or we're doing it on device and then when the person comes it just transfers on their stuff. That's also a solution as well. Yeah, can you dumb it down for me? OK, so for example, there are certain things like-Different machines that create quantities of something, I don't know, like they make different, like amount of flour. And we can't have that because there's no connection, Wi-Fi connection on-premise, so it can't get to the server.

So when a maintenance worker goes in, he logs in on his phone through the service, all the information is transferred onto his phone, and once he gets back to the place, it uploads onto the place. You know what I'm talking about? Or is there going to be like a server in the middle of Palo Alto here where we text it and it just stays on that local server, and then she comes back with a laptop and then it goes to her laptop or whatever?

What do you think is best? Um...

People are going to break their individual things. So I think it's decentralized somewhere.

Agreed. I also want us to think about people who don't have phones at all. We're building for this farmer who has a phone in our house, but maybe they share a phone across five houses. So on a borrowed phone, can you call a number, put in your individualized PIN code or whatever, or your name or something, so that I don't even need a phone, but I can still contribute to this public record? Yep.

That's a good idea.

I think in that case, it would need to be centralized, right? Oh, man.

I wish there were a fire or something here. I was supposed to do it on a laptop then. It was to show a server or something. The judges were like, oh, there's a product there. Is 3G concurious?

I'm more concerned if she already has a smartphone is this actually in the case? Yeah, yeah cause because we don't know if those folks actually have smartphones to send voice notes, they don't so The only option is like calls or SMS you 3G costs money to send voice mail.

Like if I'm like sending audio. Like a audio.

But a voice mail is something like that is fine?

Yeah, that's fine. Cool. Okay.

Guys, I'm pumped. That's actually a really cool project. Mm-hmm. What university are you at?

I go separate.

Geez, yeah, that makes sense.

Yeah. Yeah.

You're very good on your feet, Jace.

Oh, thank you. I appreciate that.

I'm losing it like 20% here. I'm losing the focus here sometimes. Um.

You said business? Yeah.

Cool.

I'm going to push it here one more time. Any holes. Like, this is the perfect time to, like-We got it all on tape, right?

Is it recording stuff?

Yeah, it's still recording. Let's put it here on the-yeah. It's constantly updating the MD file. Yeah. So it's connected.

Let's pull it right now and just talk to it and make sure.

Do you want to see? Yeah. Email it to us.

What do you want to do?

So just take the MD file and email it to me or something.

Can you upload it? I think it should be in GitHub. Wait, let me push it. Yeah, push it. And then you can just chat over a cloud code or whatever. Yeah, yeah. --You know what's also interesting?

Okay. If you want to sell that land, right? You need to be able to know how fertile the land has been for the last few years. And if you don't have a record, you don't know. It could be sand. It could be really fertile dirt or whatever. But this could actually help you negotiate a better sale price on your own land.

Yeah, that's true. I mean, obviously an obvious concern is just how true it is.

Touching the record, can you pinch it? Yeah. Yeah. If it is live recorded every day and it's held like that, you have to--I would work for a year to get like 100 kids to--Maybe, maybe, true.

You know what I mean?

Maybe that's what you're like, for you to know. Also for the notes, how it, More important than the Rutgers are. Well, because... Yeah, I get it for the loans, but for the loans, I think it's more important that I have, like, the end words for what I sell. So they can see the transactions of what I do.

Hello.

True, true, it can be both. I mean the record doesn't just have to be what you did on the farm.

It can also be like this is how much I sold it for, this is how much I paid you.

Yeah, maybe we need to enrich the record across more layers. 'Cause that's like the most important thing for loans. Otherwise, with just a record, of course, Because it contributes to the credit history. For example, they need to see that like a bank transfer has been done. Exactly. Something like that because they don't want invoices or maybe they even get paid in cash that could also happen. I'm so tired.

So, somehow we need to capture those things. So either they have like an e-wallet, what we need to capture, or an e-wallet. Like an invoice record or something? Yeah, like most, those folks that don't have like a bank account. For example, in the Philippines, they all use like GCash, that's like an e-wallet. Or in India or wherever, Or often they get also paid in cash.

Yeah, I think they're cash transactions.

So that's like a hard part. So what I mean is that middle guys, someone needs to give them an invoice.

Okay, maybe this is kind of dumb idea once again as well. The expert when they convert two times a year, they can keep their records because, I don't know, they give them cash, but they probably give them an invoice or something. And then we can just verify those records because they can be pulled from their individual file. This, this, this, this, this one. They just scan it in, scan it in. They can get verified. You know what I'm saying?

Yeah. Okay, so you are a farmer and you have, you get to make a cash, but they give you paper invoices. Okay, you keep those records and then when I come two years later, I take photos of those records. Twice a year. Sorry, twice a year.

And I go back and I take photos of it and then it verifies that exact amount by whatever you said inside the vault or whatever you want to call it there.

And those can be verified.

I mean, if I say I got a million dollars in the vault and I write a million dollars on a piece of paper.

No, but then it's not.

Because there's a company buying it, you know what I'm saying? Yeah. So it's always you can double-check with the company as well, because they're not just going to trust one person.

I wouldn't have so much faith in the company. record keeping for something like this. Okay. Just because we're being like super of a village, right?

Like really, like, Oh yeah.

Yeah. The corporation stuff. Yes. Yeah. Yeah. Yeah. There's all the shoes. Like you're coming in with cash.

You have a gun. Like this is not a, like maybe not the safest place. Yeah. And it's maybe not the most like calm negotiation either, right? And it's just like, this is the cash, like give me your stuff, and we're really fine. And so I really think about these. I don't think they're that tense, but they can be that tense of a negotiation. And so as we think of the sales praise, they're not going to have a good progress.

I think the voice And the yield over time is probably going to beYou're right about lying and the ability, but then maybe you use the fact that you have a huge record, right?

To be like, okay, it's pretty easy to see the outlier.

That's true. That's also important for the loans. For example, loans could be that you give them drops or whatever. Then you always need to have the likelihood that those drops actually come profit. And therefore the record is super valuable.

Well, you can just see the whole region and just see if the number makes sense.

Yeah, right. that the one farm is also paying it back. So you can give the farm a lot. So I think that's like a huge thing. And I think some of those loans for farmers, some have like the whole infrastructure also from them buying those crops, they give them the loan and then also buy the crops or like the yields or whatever. So a lot of, often that means everything is involved as well. Translates as a small heads up.

And often like the middle man's are maybe then a bit more cut out. But yeah.

What?

Yes. That's pretty good. Do you have it?

Yeah, you got it now. Thank you. What's wrong?

Is this table on? Oh yeah it is.

It's quite practical. Like it's connected in Notion, it's updating itself. It's quite cool. Bring forward the flag.

-Like if you have a geotagged location, You're able to get this pretty easily.

I'm just going to wait for the same corn pines, I've picked up some stuff from the little water we got. Okay. The nursing board. Can you talk about it, I'll do it right now.

Still a big... I just keep seeing here the voice in my diary is not going to get rid of it alone. Yeah.

Mm.

So too many use cases as well.

Just saying, Alfred. Hm. In the merchant market, information is very useful. Obviously, the traditional is like payslip and all of those things, but a lot of people are not employed or whatever, they don't have those information. Then you take other records, for example, that they pay their phone bills. And if they pay their phone bills, then you can also track, oh, are they taking like, do they pay their phone bills on a daily basis?

That means they don't have money to pay it on a monthly basis. A lot of those factors you also keep in mind and track.

They're buying like packages.

Yeah, right, right. Even something like that, like...

Like you're in a Walmart. They're buying a little package. Yeah, it's like remote. Yeah. Yeah, super remote.

Okay, that is also something we can't really try. But still though, then for loans, The most credible source is on how much they sell and how good the region is doing. to get loans. I think that's the main information.

So what is your saying that counters that?

Which, sorry, I was reading.

Like, why is it saying that? It'd be hard to.

Just because nothing can be verified.

What do you mean though?

like actual paper and records.

Can you ask it like in remote areas of Africa, how do they currently get loans? Like what rents do they have?

They don't get loans. I can only say from the Philippines people who even live in Manila, that's the capital city, they often do 5-6 landings. What it means, on Monday I give you 5 USD, on end of the week you pay me back 6 USD. So they pay around 20% interest per week. And the loans are mainly done by like individual people from the village or from the community. So basically you call me, I will bring you the money and after one week I'm going to collect you and I have like a baseball bat with me and take care that I'm going to collect it.

Okay, so villagers called kiamas in Kenya, like pool money and they lend it to each other. Co-op advances before harvest. That's eight CCOs.

Let's check how other startups are doing it.

Can you now run some subsidized fertilizer through a farm? Registry called. Yeah, it was. Farmers are described through local officers on receiving an e-voucher on their phone to collect subsidized fertilizer. She's right there, yeah. Do the Rook Street already exist in Kenya apparently?

For the broader picture in the end we also need to think about how this can be like a profitable business. I like. Who is financing this? Like, we obviously like overlaunch people earning money. So we like...

you I think this fits into the lovely. Yeah.

In terms of this being aTool.

No, because it's the World Bank and they'll fund it. So it's like probable for-Oh, cool.

Yes, I don't know why not.

This is more like a--Can I get you guys a drink?

Okay, thank you.

I will also get myself something. I need to stop by in a minute too.

Huh? I need to stop by in a minute. What happened to him?

Thank you. I think that Dr. Ali, she likes the idea. Huh? I actually liked the idea. That was huge.

This is like an idea I like. I don't think this is like stop. like a freaking wall of text.

Okay, so right now the co-op sees Neuer only once a year.

She brings in her coffee the rest of the year. They have no clue what's happening. Our system changes that. Every year, Neuer calls a number. We, Newark calls the number, whatever, and the co-op can now see what's happening across every farm all year long, and that helps in five weeks. They spot problems early, all right? Like if five farmers report the same disease in the same location, they can contain that, whatever.

They know how much coffee's coming, 'cause they can predict that on how much they've done in the past, and how much they think is now coming in 'cause of the ledger. And then they can help Newark get a loan. They can get certified, yeah, inspectors need records, yeah. And then keep the government's pharma list up to date. There you go. That's just kind of what I was thinking through. The part that I added there is kind of the, I don't know, the early prevention of spread of whatever disease the coffee has.

This is for the experts out sorry that's for the experts hard so from what I understand here there's like a board of the collective farmers A specific farmer, whether the representative is at the co-op, goes out and does that. This is separate from the expert, is what I was thinking. Mm-hmm.

I'm not sure what you guys think about that.

I like the idea but only think like all information with the expert is technically communicating with them maybe AI can actually replace the experts because probably they're not so many experts So what I mean, we feed all the information for good experts for strategic help. But maybe there's a bottleneck that we don't have enough experts within the region. What I mean with it, The expert, yes, we can support him that he can provide even more strategic help, but I think our job is also to provide them better strategic help over the phone calls or whatever, something like that.

Just to have it in our mind.

really says in the brief that the public expertise sectionAnd so this then enables these guys to have some local advice, customized advice to them where they don't need the expert for. So then the expert can only focus on really high priority items. So absolutely what you're saying. Okay, what's the sun direction?

Yeah, and how we make it useful.

Okay, the core is we collect all the records over phone calls. The phone call is probably an interactive phone call because they're calling AI. No. That just speak on the phone? Well, actually we can decide.

The way I was originally thinking about it is they just give like a recount. Of the day, if it's possible with a 3D network to have an interactive AI model asking other questions.

But wait, let me ask. With our connectivity, can you have normal phone calls? Yes. So I can call you? Yes. So technically I can also call an AI? So yes, we can have an AI in the car. Yeah.

Do we need AI in the car? Probably.

Yeah.

It's useful, for example, you can also ask questions or whatever, like not all farmers probably will answer everything. If you speak to a phone where nothing is coming back, I don't know. It's a bit too broad, but if we have the customer advice, then the AI would also say, oh yeah, by the way, they've got a forecast for the next day or whatever. Something like that. Before we do anything else, can we--Yeah.

In each farm?

So is it on a cloud or whatever?

Why do we need to host it locally? Because there's no internet. But probably the expert on that, where we feed the information, they have internet. But they're not coming. They only come every twice a year. Yeah, right. But they call, they'd be called over a normal phone line. And if they, we can also connect the normal phone line with AI.

You know, I see what you're saying. I think there's a disconnect in how you're thinking about this. Because the reason why that it can't just call to say, oh, actually, hold on. Because where was the information going to go?

I'm just thinking right now.

I mean, technically a real person in Kenya or wherever, in Namibia or whatever, can call a normal phone line. And can call a normal phone line. If they can call within Namibia, we can always connect them with AI. And if we can connect them with AI, we can even have the data center here in Palo Alto and SF or wherever.

I get it. I think a different option would be if we say we have it locally only within the village.

So that maybe they even don't call, maybe they are connected with whatever, walkie-talkies or whatever. No, I just say so. That would be like a different case. If you say we have a model that we host somewhere in the village, and in the village we have a model running, that can process all the data. But if we assume we have an official phone line, then we can just run it on the normal model. And in our demo, we can also show it to them.

Like we can connect. we can do that, like the call-out.

You can process it on the cloud, you're right. I don't know why, I just totally didn't think about that. And that means also for the advice that AI can talk with them. Yeah, you're right.

We need to figure out what information are we now capturing.

We just pull structured objects is what they're saying.

We just pull structured objects. That's about it. We just have AI infer what it's talking about and pull that out into a different table. That's it, I think. We just define what we want to pull out.

I think we need to define our use case a bit more. Because I think from a building aspect, I think that's all doable. It's more like it gets a bit harder if you make use of all this data. That's a bit harder. Yeah, you're totally right.

Yes.

You were saying that you'd have to use case.

By use case, do you mean like-Yeah, I'm still don't fully get it like for the farmers like I don't know like that you convinced me that I call like a freaking Like every day I pick up my phone and call Ekanamba.

He's asking what objects you pull out, like what are we looking for?

Yeah, like what things do we actually build? I mean, we have once the advice and what other things do we need to collect?

Yeah, do you mind writing it? Yeah. Actually, it's a great point. Let's work backwards. So right now it's 1225. We want toWe're doing our intermediate pitches of five, right? Yes. So do you want to create a little bit of a timeline starting at 12:45, so 20 minutes? Yeah, for sure. And then we just do a development pipeline, and then to your point, you can figure out what's highest priority to build, and what we build after and after.

Does that work? Yeah, that's cool. Okay, let's do that. So let's start 12:45.

11 lives doesn't have language, I forgot all that.

What's the part number?

It doesn't help language.

Remember all like 200 languages, like the Sub-Saharan, LAF,Oh gosh, you need to figure out something here. That's a hard one. You have the Duda set, you can't train the 11 lines on the Duda?

Actually, I'm going to look. But no, because it's closed source.

Google is the open source for smart-up.

Yeah, we don't have to use 11.1 specifically. Probably just have to open source one.

I don't know what I'm saying though, but how's it gonna, hmm.

I got it. I got it.

So your question was, what does it look like?

What does the product look like? Yeah, and what do we capture? What use case do we now have? Yeah. Like I get it, we have the loan from the certificates. Yeah.

OK, actually we have it on the picture. And how do we actually now get it out? The experts, the 3D shear bias, I think not the highest priority because probably that's always a constraint. And also this expert also don't have all the information. Yeah, that one's like a side effect. Side effect, OK. The longs is also a side effect. That's it.

Okay, wait, wait, wait. Let's mark side effect and main effect differently.

Okay.

The effect is like the outcome of just having the list, right? So loans.

Certification.

All of these.

Okay.

And the historical knowledge familial is also a side effect.

The knowledge. Yeah, and the historical knowledge. And historical knowledge. Okay. And the sale. And the what? Sale of the looms, yeah.

This is it.

So these are all things that are benefits of having this table.

I think they're like huge benefits. They're probably the main benefits of what the World Bank is actually interested in.

As we think about what the actual interviews will look like for the demo, we need to show that it can do advice. Okay.

Short term benefit or like...

like a physical benefit.

I think we have to go back to local because they want it local. I just re-read this. They want local. The whole thing. So it means we're all in.

But-If it goes to the cloud, that's kind of-If you make a phone call-Yeah, I'm still saying about running on a normal laptop or something like that, the local models that are processing the data.

I still think we should keep that global, unfortunately, because, I mean, for the demo. What are the limitations of that, then?

Does that mean we can't have a call with an AI? Oh, you can. Yeah, you can. OK. Then what are the limitations of this?

I'm just pulling weather data. You know what I mean? That's the good-We can't do that. Because there's no internet out there. But we can have one local model that's connected with stock.

Well, I mean, in an ideal world, yes, but...

Starlink works like everywhere in the world.

I just want to make sure I'm understanding the story.

They don't know who has money for that, bro. OK. No one has money for Starlink out there. It's expensive as hell. Even for like me, it's like 150 a month. Sorry.

I just want to make sure, because this then can have ripple effects.

If the mechanism is you call, let's do the basic version, you call and you go to voicemail and you leave a voicemail and you do that every day for a year.

Can you have AI process all those voicemails and maintain that as a record?

I believe you can.

I do have a little.

Now version two is you call, but instead of leaving a voicemail, you speak with a chatbot.

Can you do that live? Yeah, locally, yes. You can do it.

Oh look at that, holy... Oh fuck, that's... I want to see now.

Oh, God.

Let's go.

-Hi, everybody.

Oh gosh.

For me the local model more technically would make sense if you say you have a model running on your phone. Hello?

Working on the same thing or all different stuff? No, all the same World Bank agriculture case. Ah, okay. Yes.

His speech and overview is almost impassioned as I was looking at how different people present on the challenges this morning.

you So what's the solution or what's the idea?

Oh, we are still a bit aviating, but our core model is like, um...

That... Oh, you can explain. You mapped this out.

Okay, so we're building for the archetype of a farmer who goes out to the farm and does not have access to her phone.

Until he makes me.

--Thank you.

So, The questions we're trying to answer are-There's a whole bunch of problems that this farmer is facing, including a customized advice about what's happening on the farm, how to improve their yield, things like that. Then also thinking about pricing. So in these villages, you usually have somebody else who comes and buys. They set a price. There's no inversion rate. Oh, there's like always a middleman. Yeah.

And then there's a lot of side effects and all those things as well. And so what we're thinking about under the constraint, and they're very clear about this in the group, is you need to use AI in a way that a Google search or spreadsheet cannot be useful to you. And so the solution that we're thinking of is we We know that there's no central record keeping device for all these programmers and unlock a lot of things. And so the way we're measuring that is by creating a system where you can use your regular phone or your smartphone and you call into a platform and, well, we're traveling exactly where this looks like, but it's either easy for every minute, let's say, like a one minute voicemail about what you did, problems you saw, the bugger, anything that could be useful and you can create this record over time.

As you spread this to multiple people, and of course you have this really huge longitudinal data set that can be valuable, but even for the individual person, we're looking at benefits on a very short-term basis. Like in the morning, maybe you wake up and AI has ingested what you said in your local language.

Use that and inform by local weather patterns, fertilizer, show some of that, give you an X for the next day. Over time, though, for that individual person, you are also creating your launch record for yourself, which enables things like loan eligibility, easier to stay in love with your land, that it's fertile. You're thinking about things like the certification of your crops as organic or fair trade.

You need brand records and things like that, so enabling that quite easily. The reason we chose voice versus typing or anything is because we are farmers, so we have their hands, and they have access to electricity, so they can see us.

So we're like a family of three. We speak three times as fast as we type anyway. Oh yeah, we spoke real-Most efficient.

And then we're also thinking about things like--Familial compounds on these lands and to make sure that the institutional knowledge that a lot of these farmers have are able to be qualified somewhere. And then other side effects of course are having a huge database across all farmers.

And then like this, this means like you're able to have one collective knowledge on if yield issues are systemic or if they're localized to you as a farmer, maybe your region. You're also then able to potentially access data that are across your entire farm. They also mentioned in the brief that there was somebody who's a government-sponsored expert who comes in and supports farmers, but they come in at night.

It sounds like it's a support.

Yeah. So it, Eliminates the neutral out of demand, but it also allows for a very strategic one.

All right, so we're going to do these agricultural challenges, how they as pervasive across like South America and Latin America, or like Africa and like just Or is it very specific to a particular climate, continent, and all of that? We know that the World Bank right now is investing a lot in Africa, but I imagine that similar issues are going to be present and value of this will persist across a bunch of different continents.

And we're trying to make it agnostic to particular regions.

That's a little scalable for the World Bank especially. We're also thinking about issues Farmers who don't have access to food, who don't own food, in general, so can we make a solution right now? One minute every night. Sure.

So really trying to make this look like a ball.

That's super cool. The dam for this whole thing. Is it quantifiable at this stage or is it too early to like--Really good numbers on,I'm sure we could back on the envelope now.

Yeah, an estimate on there. Oh. Is this also a requirement that we make a business case out of it? No, I'm just curious.

I haven't read the case in detail. I know all the requirements and these natural questions that are coming in.

Yeah, obviously.

They didn't give us a term directly. They have mentioned though just about how... How difficult it is right now to even identify Sure. These are the lessons that we would do pretty well.

Farmers do everything. Here's the... labor that they take from the farm and then the brokers and people who go upstream with their yields and stuff.

is what you're doing If you want to see the robot dogs, they're just here for a few minutes.

And it would be good time to see them.

Yeah, they're going to do a little show. The farmer, The archetype that you're talking about is inclusive of-All of the--jobs that exist like farm or I would imagine like if you're the owner of the farm, you might not do everything that theRight. What you're building, and all of the jobs.

The archetype we're solving for right now is small farmers. That's pretty much it. Thank you.

Thank you.

Okay, let's go ahead.

Also all inputs we collected on it, for example the bigger farms and all of those thingsFor The input that you got from Colin?

Yeah, for example, yeah also like Colin, whatever, no it doesn't matter, like input he just gave. For example, there might be bigger farms, but have more workers, as I focused, right? Yeah. And a lot of other things.

The bigger forms, I'm just less concerned about because I feel like they're better equipped for some of these things. From a building perspective, I'm going to rely on you because I feel like you know the most about timing and things like that. Hi. My strengths for this process will probably be on the, like, any sort of slide design we need to do for the pitch, and then any video editing, and then I'm happy to support on anything.

Yeah, I can also contribute to a tutorial.

Yeah, yeah, yeah.

Yeah. Yeah, just tap us in. OK, as I think about what this looks like, should we do that? It's just like this.

Sure, I gotta ask though, are we doing local or what are we doing here with the models and stuff? Are we doing a server or are we doing full cloud? Like what have we decided on that?

So what are the differences of each in terms, not in terms of like what the actual--Pull up your table. Not quality, but like, What are the different features or the limitations that we'll have if we choose one versus the other? Good question.

Obviously, local is gonna be a little bit. less intelligent, because it's not front-end or mall sort of thing. It might be slow querying data because it's limited by whatever the server's capacity is. That's obviously going to be bad. Harvard's going to be bad out of us. You know what I mean? So it depends on that. The real limitation just depends on how good the model can transcribe where 2G on the voice, you know what I mean? That's going to be really poor voice quality. So I don't know.

I need to look for a model that's good interpreting that as well. Good.

Just asking a Gucci quality is like a normal phone call or isn't it a normal phone call? Sorry? A Gucci phone call is it like just a normal phone call? It is. So what's now the difference if we host them or the model locally in the village or just host it in the car? I mean we do like a normal phone call. In my, in If I get it right, the local model was more like, let's say you have, I don't know, like... Photo stuff, yes. Photo stuff and you run the model on the farm. You get what I mean?

Yeah. So let's say all the workers, we have a farm with 100 workers or whatever, and they make a photo on the smartphone. There's no internet connectivity at all, so they send it to the local provider or whatever and get the feedback. Yeah, you're right. But like, just in calling, I don't get the use case. Let's look at it, ladies. Look at his eyes. I don't get the use case in having a local hosted model in the village.

without internet, you know what I mean? I think we should lean into that as well. I agree. Because anyone can build something in the cloud, anyone can get information and store it on the web, but it's very difficult to do it on, well it's not difficult, but it's more technical, like there's some technical difficulty, which is part of the demo, is a bigger part of,Having it local.

Okay, I get it. Only for the things that we do, technically we don't need it, just to keep it in mind. Yes, yes. Like for the things, We would need it if we would have an app where we send pictures to the local model.

I think it would be useful for this as well, for the advice custom, where we could do it for people just a little bit of building in the background. It's going to be a side feature. If it doesn't work out on time, we don't do it. But I have a building in another branch where we do the advice custom, where people with text can also text questions as well. You know what I mean? And that gets processed right there instead of on site with images or whatever.

But basically what you want to say, we host a local date, communication between the local model and the stuff, whatever. And this from the local model sometimes still needs to be sent to the expert. So we collect all the data. Because that's still hosted separately.

So you're saying the only limitations of doing it locally are that it might just be slower and less up-to-date?

Yeah, let's dive in.

And slower and less up-to-date in terms of it'll update-It'll take like five minutes. Just because it's slower or it will take multiple more days?

Just five minutes. So it's quite low.

Yeah, but I would more think about the use case.

And also inference speed on phone calls is going to be like instead of being snappy, it responds like a real human. It's going to be like one, two, three, and then start talking. You know what I mean?

That's really important for me. So let's talk in two cases. I agree on local. I'm good on local.

No, wait, wait, wait. I agree on local if we have a use case for local. If we do normal phone calls, I don't see the use case on having it locally.

So it's not about the use case, but more about the... Practicality of the implementation of the solution, right?

It's way harder to have a local model. You need to put like GBU in the town. But visual appeal though. Yeah, I get it. From a visual appearance, it's cool. Yeah. But like-Which one is more realistic if we were to be in Africa right now? If implemented tomorrow, obviously having no local thing.

Oh, if we're not very local, because I mean, the Wi-Fi's shit over there. Yeah. Yeah, so I'll just do local.

But if you go phone call it.

Yeah, you're right on that point for 100%. like how, like I just,What you're saying, you know.

If you, look, you call the phone, and in our solution you would call the local provider. Yeah. And then the local model is coming back to you. If you call from a random down in Kenya to Nairobi, the capital city, then you can directly call the cloud model. Can you do that? Of course. I mean, if you can do it, what are you saying?

So basically, the ultimate goal of what we're trying to figure out is can you have an interactive web conference?

Yes. I literally did the last hackathon with the 11-9 thing. I built the exact same thing last hackathon with Google. So an interactive phone. Yes.

And we all agree that this is just a better--Cool. For this, like an interactive call would be better than voice calls.

Maybe, yeah.

Then if we're sitting at Apple right now and we're thinking about implementing this.

If we gave them a phone number, a local phone number so they don't have to pay international calling fees, is it realistic for them to be able to call a live Basically, is it possible to have an interactive phone call?

in Africa right now. It should be, right?

Yeah, you can, you can.

Well, I'm just kinda confused. Like, are you talking about the LLM or something? No, like, of course you--If I was in--Yeah, I know what you're saying.

Kenya, can I make a phone call to a local? Phone number that can basically let me talk to Claude.

Yeah, obviously, yes.

And the latency, it wouldn't take very long.

No, obviously.

Obviously, first.

If you host it locally or if you host it on a cloud.

-But the guideline, it literally says, from my understanding, the core feature needs to work offline, the middle core feature, core feature. Yeah, see, it's perfect. Look at this, it needs to run on one.

Right, so I don't have Wi-Fi, right? Yeah.

I have a phone number and I have 3G.

Can I call... Can I still call something that's a cooked up plot? Yeah, obviously, yes.

So then this isn't a-OK, well, there's also cost, too. Obviously, I keep thinking that I'm in this person's shoes. It actually is expensive to call a global front-like, a frontier model or whatever.

But you can't call it China's model. And then host a challenge modeler live in some random cloud.

Right, that's the problem, he's right.

No, the thing is, okay, just to imagine, if you make a phone call to your mom, you do it over, not without an internet. And that can also be a rural village in Kenya, you can call to the capital city. And in the capital city, their phone can always be connected to some sort of AI. So that always works. In my point of view, having a local mode would make sense if you have some things that we send I don't know that we even can't do a phone call or we can send pictures or whatever. Or maybe the farmers have a smartphone with them and make pictures of the crops just saying.

And the phone is directly saying what they should do because you can even run a model on your phone as possible. That's like use case in my opinion where you actually need a local model.

Yeah, I mean where you can think about it having still local if you I can promise you though if we do like offer models, we're not gonna win because that's just like obvious You know what I mean? It's just too obvious if you do what like if we just have it like call like freaking AWS or something Yeah, I agree on that but I agree.

I think we need to dig deeper maybe in a case of what we have We need to find like one unique thing, you know, I just can't figure it out I think it would be cool if we can host it locally And it... And in the local box you can just plug in a SIM card when you buy in the supermarket. And then it starts running, something like that. Okay.

So, given the time, does the local versus offshore decision impact how we build this? No. Then we should not be having this conversation right now.

No, it's more like the new scale what we build. Like, if we would build something more locally, then we would obviously build a different new scale.

How? Why would it be different?

No, it wouldn't be the case. But at the moment, we don't need a local model, just to point this out.

Okay.

If we did a local model, would it change the end output? Like, versus an off-road model.

Maybe we could have some solution that you send pictures to the local model, or some of those things.

But you can't do-This makes sense now.

Um, this is so dumb, dude. Damn. Okay, so it's saying, you know, we have the phone in the cloud and that's what, you know, calls and talks to it or whatever. And the laptop acts as a call box, like we were saying. And then we have it read the transcript and take everything out of it, whatever. And then it puts, that's the thing, because they have no internet, so they can't see the data visually. So that's why another case we have, the local thing here, so that we can see it on a laptop.

We can see it on like a little web server or whatever. So that the people in the call, The office person, for example, prevent these things from happening earlier on. Like if there's a spread of some random disease over here on the west side of the property, and then containing it before it goes to the east side, and then their whole thing is ruined. You know what I'm saying? It's another case for having it locally, because they can't just call an API and be like, oh, what's our data on AWS right now? You know what I mean?

So I think we need to have the call, and then the full transcript just goes to the local version right away. And then after that, it gets processed locally as well, and then on we go back. something.

Just to throw something in for the collective data. You've got a lot of small villages and probably not in every village does like an expert sitting was processing the data Probably sit like a bit more like in a city or somewhere just to keep this in back of your mind What do you mean? Like if we process the data in a local village, then probably we don't process the data for the bigger picture. We only process it for the individual farmers.

Because for the bigger picture, those folks that probably don't sit in the village, they probably sit like 10 villages far away. Right.

And it costs you nothing. That's another thing as well because people are obviously lower income. So local inference is zero. It's zero.

Yeah, I think that's a big one. Okay. I think that for--Okay, then no, the cost is a huge thing in the merchant market.

Yeah, yeah, so we need to do local, in my opinion, 'cause all it is is power, you know what I mean?

That's all it is, but when you're--Is it a local fund number? Or local hosting? Are those different?

Those are different. Those are different things. We always have local phone numbers, obviously.

Yeah, so if I have a local phone number, it can be hosted offshore still. So it still costs them nothing?

Yeah. It should cost them nothing. I mean-So then what would the cost be for them?

Oh, like the credits. Like if you pull in something in cloud, it needs to process all your data.

Like the World Bank is paying for those credits. I don't know.

It doesn't matter. So if it's just these people, then it'd be free for the people. All they have to pay for is the energy.

That's all I want. Yeah, yeah. It's free for the people, so you don't need to worry about costs. For now we don't need to worry about book owners and offshore crime.

Still the World Bank will only implement something if we also have low cost because otherwise it's not possible. Just to keep it back of our mind. This is a pretty low cost. I would like just in my imagination that something will be hosted locally and then the whole farm, all the farms are run on it. I don't know.

That's the case I'm trying to tell you.

Yeah, yeah, but we need to think a bit broader.

you I think if you're worried about doing what other people are doing, let's think back to the brief, right? It's about the yield has declined and they don't know why. And then they don't know how to set a price. So some people will probably go the price route, do some crowdsourcing, some data collection on what people received for prices previously, and how they can set a price. The other way is probably the very first instinct that we have, which is like, let's just take pictures and identify diseases.

And that's why the yield is going like that. We'll fall. A lot of people will fall into that trap.

Yes.

And then those who fall into that trap, maybe they're bringing some infected leaves home, waiting for the weekend, taking a picture. That could work. That's another way of doing things. I don't think we should try to predict what other teams are going to do and then try to one up our prediction. We should build something that is really durable, that can work. And then once we've built that, we then think about how to make that better.

I also feel about constraints, or other people don't might think about it. If you call a phone number, Over at, for example, Retail or Olive Trillo or whatever, I don't know if they provide us, The Bermuda cost around six cent or even more. That's to keep in your mind, huh, Matt?

Yeah, you're right. There's a lot of costs.

So if we have a system that runs fully locally in a village, Maybe we could cut out all the costs. I don't know if that works. Just random input, but yeah. But hosting a local model in a village is also freaking expensive. That the set up costs are expensive to buy this.

But sorry, Push back.

I should forget now. I don't remember what we were talking about.

To not worry about what other people are doing.

Oh, um... You're saying to have it durable. I think the whole thing is to move fast, break things, whatever. I don't think it needs to be perfect because as well, half the thing is, unfortunately, it's kind of lured. You have to kind of force the user into one specific spot. You can have a wide variety of outputs. Sure, it's durable if we have a million different outputs, but you've got to force them into one input just for the demo.

Obviously, if we keep building on it, I just think we have to ship whatever we can and not worry too much on how durable it is for now. We can just force them into one specific output.

Is that what I'm saying? on the video, I think that's a huge thing.

Yeah, for sure.

OK, but still do the use case.

Should we start with what we think the final interface should look like? And then we can start building that once we align on it? Because I think we've been swirling for a little bit.

Couple things.

Um... So, okay, we're aligned on, it's up on the ball, yeah?

Are we fully aligned on the features that we build?

I think we'll get to that.

We have to get to that, because we don't actually know which features to prioritize, so that's exactly what we're doing here.

So you call on the phone. It's interactive. Gated.

Okay, in what way do we want it to work?

Just quiz them and then ask for additional input.

So is everyone like, what's your name? Tell me your name. What's this?

Do this. What's this? Do this. What's this? Well, when they call it, they go just enter a pin on their thing so we already know who they are. So they set up their identity one time. They set a pin. Yeah, that's easy. OK. And then after that we just ask general questions. You're gonna be more useful on this than I am because I don't know what loaners or whatever you want to call it need. So you go to decide that, what the structure input is and then I just ask some questions and any additional feedback or something.

And then are we doing something, are we just doing give or treat or are we doing like asking questions to the thing as well? You know what I mean?

So we agreed it was an interactive phone call, right? Yes. They are asking questions. So they are asking questions as well?

They are asking questions. Yeah, they can ask questions, obviously. If you have questions, we'll ask.

Something like that, for example, like how is X or Y doing? Or like how is the crop looking for, you know, the east side of our village? You know what I mean? Things like that. Yeah, sure.

So everything at the end. which is like this record keeping. Right? It's not like critical to the core.

Is it queryable? Is it queryable? Is it queryable?

Let's leave it as a question. So we ask questions, they ask questions.

Okay, and then that's the end of the phone call?

Yes, yeah it is, all of a sudden.

Do you have anything else to add?

I think that's it with the phone card. It more depends what information you want to figure out how they look useful. I think that's like, yeah, the core basic.

Then what happens? So maybe a couple options here. One is like, This phone call processes all the information. If they ask questions, they don't need to talk to the phone call for maybe another day, right? Or they can wake up to a text message, they can wake up to advice, they can wake up to a summary of the phone call.

They can get called. And it can be a readout.

That's true. Yeah, that's true. That's a good idea actually.

What do you think? Do you like that?

Yeah, I think that college is cool.

So maybe like this is the night, for example, and then this could be the morning.

But it would make sense that we call them twice. I mean, then you can do everything in the night. What other information do you have in the morning that you don't have in the night?

Yeah, super carefully.

I mean everything I can deny, my point of view would be like that. First we try to put our data and if we have collected everything every day then we go to the customer advice so that's the benefit they get out of the call. That means that you can say hey tomorrow the weather is like whatever something like that.

Yeah okay so basically the option is this. This is like the advice. Yeah.

Yeah. First, all questions about needing to collect for the records after what's said last. Yeah.

Okay, and then it's basically just a question of if this is on the same phone call or later.

Yes, is there a reason to have it later?

The only reason I can think of is if you're trying to crowdsource, you want to wait until everyone or a lot of people have called in to then be able to give advice that's more local about the region and what's happening.

Does it matter on a daily basis?

Maybe not. So maybe this is like once a week. We call them an implement update.

But then you can still include it once a week in the daily night?

Yeah, or you can include it the following day.

Oh, by the way, based on yesterday and what we heard, like this is blah, blah, blah, blah. Yeah. It's okay. I'm fine with this being the same phone call.

Let's keep it as a little possible. Okay.

We're, I have a question on the will we ask questions.

You guys have all done this. I have done this. I hate this. Of like, what's your name? What's your birthday, blah, blah, blah.

What's this, blah, blah, blah. This is a calendar fest, first call. Sorry.

Onboarding, you're onboarding. No, but even on a day to day, What activities did you do? What did you do in the morning? What did you do in the evening? We need to be thinking about the questions in this.

And maybe I'll posit one-simplifying way, which is Give us a description of what happened today.

They can give as much detail as they want. It's free flowing. It's all from recall.

And then we ask questions based on the gaps.

Yeah. Of course. It's just an easier phone call. Yeah, I agree. Okay. That make sense?

You can just make it like a dynamic thing.

What kind of questions do you think they would ask us?

I think the question they would ask-It depends more on what you use, because they will mainly ask something about that.

So do you think we switch these? Oh.

No problem, that's a go-to font. I mean, they're not strong, so. then those folks ask whatever they think about.

Right, right.

But if they're probably going to ask about advice and weather and all of these, then maybe-Hello, what's your name? What's your, or like, what's your pen? Yeah, do your pen. What happened today? You give them your recap? Okay, well what about this? What about this? What about this? Yeah. Okay, based on everything you've said, looking forward to tomorrow, this is what we see in weather, this is what we see in fertilizer, this is what we're seeing in the kitchen.

Do you have any other questions? I may ask.

Yeah, okay, we can do it. Your tail came up. I think that's not that important to be honest, but I think You go there, Bugs.

So you can start with this. OK.

So what I'm thinking is when-we're going to say in the demo, obviously, we don't have a box right now. But in an ideal world, right now, we're going to have this Twilio. And it's going to route the call into-Transcript into my computer will in a real world would have Julio with the same card with a GSM adapter to it which can receive phone calls or thing and it can process the transcription locally we say that And then it literally does everything locally and after that we can just show a dashboard of all the data that we talked about being populated in a local database and some dashboard Okay, I think the local model is trusted it sounds cool the local model is also bought it because it sounds cool and how it predicts all this sort of stuff and how they're supposed to get that information.

Who does get the data? Yeah, who does get the data? Like the co-op board, is what I'm saying. 'Cause they have a board of farmers and they have one person who's dedicated to being in that office or whatever. But what do we do?

They're not connected to the internet. Yeah.

The experts. No, no, no, not the expert. There's a co-op person. Oh, yeah? There's a good person.

Also not have great That's what I'm saying.

So it's another case for it being local. So they can see all this sort of thing, see all this sort of predictions with local models, and the model can infer whatever it needs to, whatever we're trying to accomplish over the structured data that we do have on each individual person with their specific location as well.

Okay, yeah, sure, understood.

Then we see like, I don't know, warnings on X is happening over here, like, you know, we're going to be, we have to move people over here and have them spray the crops or whatever they need to do. What are you doing outside? Oh, it's a robot still? Probably.

You don't give a damn about those who you love. You're from here, though.

Okay, but let's, sorry to jump in, we have all the things, are we fully aligned on the data or on the goals that we want to achieve? I think we achieve on those external moments. I think we all agree on that one, that kind of makes sense. We still obviously need to do a deep dive for each group on how to make it useful, for example, collective knowledge, et cetera, et cetera.

Okay, phone calls happen. I think the outputs that we wanna show, one is just this, right? In our demo, we just need to show that this phone call can create a role like this. Yeah. Yeah?

Are you aligned with that?

Yeah, I understand.

So we need to show the data table.

The other part of the demo-You know how people are talking about, oh, I have a disease in this area, and scanning with a photo? People aren't going to do that. So they're going to report it to the phone. They're going to talk about that. And then we're like, OK, we need to look into this. And the co-op board is going to alert the farmers in the area.

So one output is going to be like... Yes, sorry. One output is going to be a map of-Like irregularities, yeah? Yes. So that's things like diseases. In cross.

That would have been reported.

Regional warnings, outlier flags, review queues, like where the AI was probably wrong about, Harvard's estimates, and farmer profiles. That's one thing you need to think about.

So, OK. Regional warnings. Oh, let's highlight that. Sure, okay, so that's the math. Outline of lights.

So the data table will have these like harvest, Pieces of data, right?

It'll have this. Your activities, your healing yourself, grace. In the map of the irregularities, this is going to the experts, let's say.

Hold on, aren't the sale prices negotiated by the co-op on behalf of the farmers? No.

I mean, in theory, yes. But based on the brief, it says some guy just shows up and sets a price. Oh, OK.

Maybe it would change if they have other records because they don't have the data source of all the files.

Okay, so data table not for regularities, then you would set something about... Outliers.

So I think that It's nobody's formal job if somebody is massively lying. to then go track them down. That's true. This is ultimately meant to be a tool for them to get advice. to help with I think. As this data table is created, These loan officers will know when things are outliers because they're also going to have access to this data. They're going to have more people asking for loans. So I think it's less about correcting, going to have somebody down to make sure they actually are not lying.

It's more so just validating that we thought that the AI put the right thing. Right.

And so I think that one, maybe we can add it as-So we're here, we ask questions for gaps.

This can be like a very deprioritized feature, but like we heard yesterday, Do you know what NASA power is?

It keeps telling me about NASA power.

So data table, not the irregularities. I think there is something here around When you're applying for a loan or a certification, we should show that the phone call and the data table can then translate into something that you can give a loan officer, right? That's like a pretty easy output. Does that make sense? No. It's like your financial records.

Okay.

I think this is the most powerful. There's like, One of us can be the caller and we speak to the model right in the video.

Yeah, I mean that's easy we can use like So, OK, I think this is like the crux of our demo.

Right, is this. And then we need to be able to show the back end of how this data then gets processed into a data table on that with irregularities. that it can also be pulled by the individual farmer to get financial records. How do we do this? If they are...

Calling in by the phone, they don't have access to Anything, right? They don't have access to a printer, they don't have access to a laptop, I need to go apply for a loan tomorrow.

But you have the database, it just goes from the database.

and the database can send it to-I can email my record with my pin to somebody else maybe.

I think that could be really cool.

Or maybe-Yeah, yeah. But probably they're lenders. They have like access to the internet. We just need to upload it somewhere once. Yeah. So they can just pull the data out of it? Yeah. You can just sell them the data, you can see the original overview, like the mapping, oh, this region is growing that fast, here are some main bonds, whatever.

If you can do that, then we can just show this, how the phone call will translate into a PDF, basically, that over Wi-Fi you can send to a lender.

Maybe another option.

OK, yeah, yeah. Let's note it down because we need to include it in the board.

Yeah, yeah, that's very good. Is that you could call the number and ask. to read it out for you.

Yeah, let's do no data issues. Yes. What am I missing?

I mean with calling the numbers I partly agree because landers are most like institutions that are fully connected to the internet and the world. So that would be more like an informal lander but those are most like scammers. They're more scary. So I think we can cut this out.

Okay, this is actually great. Look at this, we can actually pull local weather data over the NASA Power API, which literally goes over two G-connections.

Without internet?

Yes, it's literally 2G power, so we're already calling with that.

That's fucking awesome.

And then we also have soil, it's another API as well, that doesn't change, so obviously we have local soil data as well, and then there's chirps, which is like rainfall stuff, it's historical and present, same kind of data connection as well, so we can kind of infer that and tell them with historical data as well, look out for when, which, whatever, we can infer whatever we want with that data as well, so it's helpful.

Fabulous. OK, so now it's a chirps. And that's what our soil trips get. OK, do we agree that this is what we're working towards?
