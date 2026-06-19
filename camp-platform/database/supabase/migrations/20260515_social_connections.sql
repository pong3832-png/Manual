-- Store verified social account connections and metric snapshots.
-- Apply manually in Supabase SQL Editor before enabling provider sync UI.

create extension if not exists pgcrypto;

create table if not exists public.social_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  provider text not null check (provider in ('youtube', 'instagram', 'naver_blog')),
  provider_account_id text,
  url text not null,
  display_name text,
  handle text,
  status text not null default 'connected' check (status in ('connected', 'manual', 'error', 'disconnected')),
  sync_status text not null default 'pending' check (sync_status in ('pending', 'synced', 'failed', 'manual')),
  last_synced_at timestamptz,
  last_sync_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint social_connections_user_provider_account_key unique (user_id, provider, provider_account_id),
  constraint social_connections_user_provider_url_key unique (user_id, provider, url)
);

create index if not exists idx_social_connections_user_id
  on public.social_connections(user_id);

create index if not exists idx_social_connections_provider
  on public.social_connections(provider);

drop trigger if exists trg_social_connections_updated_at on public.social_connections;
create trigger trg_social_connections_updated_at
before update on public.social_connections
for each row
execute function public.set_updated_at();

create table if not exists public.social_metrics (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null references public.social_connections(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  provider text not null check (provider in ('youtube', 'instagram', 'naver_blog')),
  metric_type text not null check (
    metric_type in (
      'subscriber_count',
      'follower_count',
      'neighbor_count',
      'daily_visitor_count',
      'total_visitor_count',
      'view_count',
      'video_count'
    )
  ),
  metric_value bigint not null check (metric_value >= 0),
  source text not null default 'api' check (source in ('api', 'manual', 'crawler', 'import')),
  captured_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_social_metrics_connection_captured_at
  on public.social_metrics(connection_id, captured_at desc);

create index if not exists idx_social_metrics_user_provider_captured_at
  on public.social_metrics(user_id, provider, captured_at desc);

create index if not exists idx_social_metrics_metric_type
  on public.social_metrics(metric_type);

alter table public.social_connections enable row level security;
alter table public.social_metrics enable row level security;

drop policy if exists "social connections own read" on public.social_connections;
create policy "social connections own read"
on public.social_connections
for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "social connections own insert" on public.social_connections;
create policy "social connections own insert"
on public.social_connections
for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists "social connections own update" on public.social_connections;
create policy "social connections own update"
on public.social_connections
for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "social connections own delete" on public.social_connections;
create policy "social connections own delete"
on public.social_connections
for delete
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists "social metrics own read" on public.social_metrics;
create policy "social metrics own read"
on public.social_metrics
for select
to authenticated
using ((select auth.uid()) = user_id);

grant select, insert, update, delete on public.social_connections to authenticated;
grant select on public.social_metrics to authenticated;
grant select, insert, update, delete on public.social_connections to service_role;
grant select, insert, update, delete on public.social_metrics to service_role;

notify pgrst, 'reload schema';
