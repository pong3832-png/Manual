-- Bring older Supabase campaigns tables in line with the current crawler/frontend schema.

alter table public.campaigns
  add column if not exists location_raw text,
  add column if not exists address_raw text,
  add column if not exists station_name text,
  add column if not exists place_name text,
  add column if not exists lat double precision,
  add column if not exists lng double precision,
  add column if not exists source_started_at timestamptz,
  add column if not exists source_posted_at timestamptz,
  add column if not exists coordinate_source text,
  add column if not exists first_seen_at timestamptz not null default now();

create index if not exists idx_campaigns_source_started_at
  on public.campaigns(source_started_at desc);

create index if not exists idx_campaigns_source_posted_at
  on public.campaigns(source_posted_at desc);

create index if not exists idx_campaigns_first_seen_at
  on public.campaigns(first_seen_at desc);
