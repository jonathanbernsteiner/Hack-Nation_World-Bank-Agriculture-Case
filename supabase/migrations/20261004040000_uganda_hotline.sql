-- Uganda coffee hotline schema (#42, spec section 4). Purely additive: the live synthetic
-- rows (40 farmers / 416 calls / 511 entries) survive. Apply only with `supabase db push`.
-- Row-level security stays on with no policies and no grants for anon or authenticated.
-- Must sort after 20261003234752_ledger_tables.sql (never edit that file: it is live).

create table public.villages (
    id           bigint generated always as identity primary key,
    region       text not null check (region in ('Central', 'Eastern', 'Northern', 'Western')),
    district     text not null,
    sub_county   text not null,
    parish       text not null,
    village      text not null,
    lat          double precision,
    lon          double precision,
    coffee_type  text check (coffee_type in ('robusta', 'arabica')),
    is_verified  boolean not null default true,  -- false = created from a caller's words
    is_synthetic boolean not null default false,
    unique (district, sub_county, parish, village)
);
alter table public.villages enable row level security;

alter table public.farmers
    add column village_id bigint references public.villages (id),
    add column created_at timestamptz not null default now();

-- Existing rows read as processed (default) and synthetic (update below).
alter table public.calls
    alter column farmer_id drop not null,
    add column conversation_id text unique,
    add column source text check (source in ('elevenlabs', 'twilio', 'synthetic', 'eval')),
    add column identified_by text check (identified_by in ('pin', 'location', 'registration')),
    add column status text not null default 'processed'
        check (status in ('in_call', 'received', 'processing', 'processed', 'failed', 'needs_review')),
    add column consent text check (consent in ('yes', 'no', 'unclear')),
    add column pin_attempts smallint not null default 0,
    add column attempts smallint not null default 0,
    add column last_error text,
    add column processing_started_at timestamptz,
    add column processed_at timestamptz,
    add column duration_secs integer,
    add column transcript_lines jsonb,  -- [{i, role: agent|farmer, sw, en, t}]
    add column tool_results jsonb,      -- scrubbed tool calls and results (no PINs)
    add column extraction jsonb;        -- raw model output for audit

update public.calls set source = 'synthetic' where source is null;

create index calls_pending_idx on public.calls (status) where status <> 'processed';

alter table public.entries
    alter column farmer_id drop not null,
    drop constraint entries_currency_check,
    add constraint entries_currency_check check (currency in ('KES', 'UGX', 'USD', 'other')),
    add column coffee_form text
        check (coffee_form in ('red_cherry', 'kiboko', 'faq', 'parchment', 'drugar', 'other')),
    add column coffee_type text check (coffee_type in ('robusta', 'arabica')),
    add column amount_kg double precision check (amount_kg > 0);

-- security_invoker makes the view obey the caller's row-level security instead of the owner's.
create view public.coffee_sale_prices with (security_invoker = true) as
select e.id as entry_id, e.farmer_id, f.is_synthetic, e.coffee_form, e.coffee_type,
       coalesce(e.date_sold, (c.received_at at time zone 'Africa/Kampala')::date) as sale_date,
       e.amount_kg, e.price_total, e.price_total / e.amount_kg as ugx_per_kg,
       v.id as village_id, v.region, v.district, v.sub_county, v.parish, v.village
from public.entries e
join public.calls c on c.id = e.call_id
join public.farmers f on f.id = e.farmer_id
join public.villages v on v.id = f.village_id
where e.kind = 'sale' and e.crop = 'coffee' and e.currency = 'UGX' and e.amount_kg > 0
  and e.price_total > 0 and e.coffee_form <> 'other'
  and e.quote_verified is not false and coalesce(e.confidence, 1) >= 0.6;

revoke all on public.coffee_sale_prices from anon, authenticated;
