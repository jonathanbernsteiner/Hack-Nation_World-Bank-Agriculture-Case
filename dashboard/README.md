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

## How it works

- Server components load all rows once (`lib/queries.ts`, server-side SQL with `DATABASE_URL`); `lib/aggregate.ts`, `lib/prices.ts`, `lib/problems.ts` and `lib/registry.ts` are pure functions with tests.
- No login: the dashboard is public. PINs and phone numbers are never selected.
- National reference: `data/price_reference.csv` (UCDA / MAAIF Coffee Department monthly farm-gate averages).
- Weather: Open-Meteo (`app/api/weather`). Map tiles: OpenStreetMap.
- Look and components follow `../DESIGN.md`.

## Data

Most records are synthetic and labelled. `server/synthetic/map_expansion.py` adds ~180 synthetic farmers in 16 districts (additive; `--remove` deletes only those rows), including a planted low-price district (Kayunga) and a planted coffee wilt cluster (Ibanda) so both warning rules can be seen working.
