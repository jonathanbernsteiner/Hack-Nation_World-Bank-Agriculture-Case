# Coffee hotline dashboard

Read-only dashboard for World Bank staff, extension officers and cooperatives, built on the records the Kiswahili coffee hotline (`../hotline`) stores in Supabase.

| Page | Shows |
|---|---|
| Overview | Headline numbers, warnings that need an officer's check, districts |
| Map | Drill-down Uganda → district → sub-county → parish → village, with prices, problems and a 3-day forecast per area |
| Farmers | Registry of callers (first names only), filters, a side peek per farmer |
| Prices | Farmer-reported prices vs the national farm-gate reference; middlemen vs cooperatives; districts below national |
| Warnings | Suspected problem clusters and low-price districts, with the rules in plain words |
| Data & limits | Sources, what the data does not cover, rules, privacy |

## Run

```bash
npm install
cp .env.example .env.local   # DATABASE_URL
npm run dev                  # http://localhost:3000
npm test                     # vitest: medians, warning rules, price index
```

### Pinning the date (`DASHBOARD_AS_OF`)

Every window (30/90 days, 12 months, warnings) counts back from the dashboard's "today". By default that is today's date in Kampala. To pin it for a demo, so warnings don't expire as the days pass, set:

```bash
DASHBOARD_AS_OF=2026-10-04   # YYYY-MM-DD; .env.local or the Vercel project env
```

The value must be a real `YYYY-MM-DD` date. Anything else fails the data load with a clear message in the server log, and the page shows the error state. Remove the variable to go back to the live date.

## How it works

- Server components load all rows once (`lib/queries.ts`, server-side SQL with `DATABASE_URL`); `lib/aggregate.ts`, `lib/prices.ts`, `lib/problems.ts` and `lib/registry.ts` are pure functions with tests.
- No login: the dashboard is public. PINs and phone numbers are never selected.
- National reference: `data/price_reference.csv` (UCDA / MAAIF Coffee Department monthly farm-gate averages). A month is carried forward at most 2 months. After that, sales have no reference and no index. Rows marked `interpolated` are carried-forward estimates.
- One price index everywhere: sale price ÷ national reference for the same month and form (`saleIndex` in `lib/aggregate.ts`). "Last 12 months" is the rolling 365 days ending today. Dates after today are left out.
- Sales below 0.3× or above 3× the reference for their month and form are dropped on load (`dropOutlierSales` in `lib/queries.ts`).
- Price warning: over the last 90 days, each farmer's median index, then the median across farmers. It needs 10+ sales from 5+ farmers and fires at −15% or lower (rounded, the same cut as the red pill).
- Day windows use Kampala calendar dates. Calls in the last 30 days include today.
- If loading fails, the page throws to `app/error.tsx` (Retry). With ISR the last good page keeps being served when a revalidation fails.
- Weather: Open-Meteo (`app/api/weather`). Map tiles: OpenStreetMap.
- Look and components follow `../DESIGN.md`.

## Data

Most records are synthetic (`is_synthetic` in the database). `server/synthetic/map_expansion.py` adds ~180 synthetic farmers in 16 districts (additive; `--remove` deletes only those rows), including a planted low-price district (Kayunga) and a planted coffee wilt cluster (Ibanda) so both warning rules can be seen working.
