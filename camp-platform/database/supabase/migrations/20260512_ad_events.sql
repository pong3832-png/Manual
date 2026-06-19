-- Store anonymized ad slot events for placement performance analysis.
-- Apply manually in Supabase SQL Editor after review.

create table if not exists public.ad_events (
  id text primary key,
  ad_id text not null,
  slot_id text not null,
  provider text not null,
  event_type text not null check (event_type in ('impression', 'click')),
  page_path text,
  target_url text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_ad_events_created_at on public.ad_events(created_at desc);
create index if not exists idx_ad_events_slot_id on public.ad_events(slot_id);
create index if not exists idx_ad_events_provider on public.ad_events(provider);
create index if not exists idx_ad_events_event_type on public.ad_events(event_type);

alter table public.ad_events enable row level security;

drop policy if exists "ad events public insert" on public.ad_events;
create policy "ad events public insert"
on public.ad_events
for insert
to anon, authenticated
with check (true);
