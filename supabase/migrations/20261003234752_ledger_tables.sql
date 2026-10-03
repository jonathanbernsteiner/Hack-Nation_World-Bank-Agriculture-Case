-- Ledger tables (#19): farmers, the calls they make, and the entries found in each call.
-- Same columns and fixed lists as #7 (server/farm_ledger/db.py + enums.py);
-- server/tests/test_supabase_schema.py checks that the CHECK lists match the Python enums.
--
-- Differences from the SQLite ledger, because Postgres has the types:
--   received_at is timestamptz and date_sold is date (SQLite stores ISO text);
--   is_synthetic, disease_detected and quote_verified are boolean (SQLite: 0/1).
--
-- pin_hash = sha256("<LEDGER_PIN_SALT>:<pin>") as hex, the same as farm_ledger, so a
-- PIN looks up the same farmer in both stores. A 4-digit PIN is guessable from its
-- hash, so pin_hash must never reach the browser.
--
-- Row-level security is on with no policies: only the server (service role or a
-- direct Postgres connection) can read or write. The anon key sees nothing.

create table public.farmers (
    id           bigint generated always as identity primary key,
    name         text not null,
    pin_hash     text not null unique,
    region       text,
    lat          double precision,
    lon          double precision,
    is_synthetic boolean not null default false
);

create table public.calls (
    id            bigint generated always as identity primary key,
    farmer_id     bigint not null references public.farmers (id),
    received_at   timestamptz not null default now(),
    language      text,
    audio_path    text,
    transcript_sw text,
    transcript_en text,
    is_synthetic  boolean not null default false
);

-- One row per event in a call. Every event field is nullable: blank is better than a guess.
create table public.entries (
    id                 bigint generated always as identity primary key,
    call_id            bigint not null references public.calls (id),
    farmer_id          bigint not null references public.farmers (id),
    kind               text check (kind in ('sale', 'activity', 'harvest', 'observation')),
    plot               text,
    crop               text,  -- free text, English, lowercase and singular ("banana")
    amount             double precision,
    unit               text check (unit in ('kg', 'bag', 'tin', 'bunch', 'other')),
    price_total        numeric(14, 2),  -- the total she was paid, not per unit
    currency           text check (currency in ('KES', 'USD', 'other')),
    date_sold          date,
    buyer_type         text check (buyer_type in ('middleman', 'cooperative', 'other')),
    buyer_name         text,
    paid_how           text check (paid_how in ('cash', 'mobile_money', 'other')),
    activity           text check (activity in (
                           'planting', 'weeding', 'fertilising', 'spraying', 'pruning',
                           'harvesting', 'other')),
    input              text,
    quantity           double precision,
    yield_amount       double precision,
    disease_detected   boolean,
    symptom            text check (symptom in (
                           'yellowing_leaves', 'leaf_spots', 'powder_or_rust', 'fruit_spots',
                           'rot', 'wilting', 'pests', 'stunted_growth', 'other')),
    evidence_quote     text,  -- the exact transcript words
    description        text,
    quote_verified     boolean,
    likely_disease     text,  -- empty until the disease matcher (#29) fills it
    disease_confidence real check (disease_confidence between 0 and 1),
    confidence         real check (confidence between 0 and 1)
);

create index calls_farmer_id_idx on public.calls (farmer_id);
create index calls_received_at_idx on public.calls (received_at);
create index entries_farmer_id_idx on public.entries (farmer_id);
create index entries_call_id_idx on public.entries (call_id);

alter table public.farmers enable row level security;
alter table public.calls enable row level security;
alter table public.entries enable row level security;
