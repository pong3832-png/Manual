-- Store privacy-minimized product analytics events.
-- Apply manually in Supabase SQL Editor after review.

create table if not exists public.analytics_events (
  id text primary key,
  event_type text not null check (
    event_type in (
      'tab_view',
      'home_discovery_click',
      'category_filter',
      'region_filter',
      'search_filter',
      'preset_filter',
      'sort_filter',
      'filter_reset',
      'campaign_impression',
      'campaign_open',
      'favorite_add',
      'favorite_remove',
      'apply_click',
      'application_status_update',
      'application_memo_update',
      'application_review_url_update',
      'map_filter',
      'map_pin_open',
      'map_cluster_interaction',
      'traffic_source',
      'market_report_create',
      'market_report_download',
      'legal_open',
      'analytics_opt_out',
      'analytics_opt_in'
    )
  ),
  user_id uuid references auth.users(id) on delete set null,
  anonymous_id text,
  session_id text,
  page_path text,
  category text,
  region text,
  city text,
  platform_id text,
  campaign_id text,
  slot_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint analytics_events_user_or_anonymous check (
    user_id is not null or nullif(anonymous_id, '') is not null
  )
);

create index if not exists idx_analytics_events_created_at on public.analytics_events(created_at desc);
create index if not exists idx_analytics_events_event_type on public.analytics_events(event_type);
create index if not exists idx_analytics_events_user_id on public.analytics_events(user_id);
create index if not exists idx_analytics_events_anonymous_id on public.analytics_events(anonymous_id);
create index if not exists idx_analytics_events_campaign_id on public.analytics_events(campaign_id);
create index if not exists idx_analytics_events_category on public.analytics_events(category);
create index if not exists idx_analytics_events_region on public.analytics_events(region);
create index if not exists idx_analytics_events_platform_id on public.analytics_events(platform_id);

alter table public.analytics_events enable row level security;

drop policy if exists "analytics events privacy-minimized insert" on public.analytics_events;
create policy "analytics events privacy-minimized insert"
on public.analytics_events
for insert
to anon, authenticated
with check (
  user_id is null or auth.uid() = user_id
);

create or replace function public.get_analytics_event_summary(lookback_days integer default 30)
returns table (
  event_type text,
  category text,
  region text,
  platform_id text,
  event_count bigint,
  unique_users bigint,
  unique_browsers bigint,
  last_event_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  select
    analytics_events.event_type,
    analytics_events.category,
    analytics_events.region,
    analytics_events.platform_id,
    count(*)::bigint as event_count,
    count(distinct analytics_events.user_id)::bigint as unique_users,
    count(distinct analytics_events.anonymous_id)::bigint as unique_browsers,
    max(analytics_events.created_at) as last_event_at
  from public.analytics_events
  where analytics_events.created_at >= now() - make_interval(days => greatest(1, least(coalesce(lookback_days, 30), 365)))
  group by analytics_events.event_type, analytics_events.category, analytics_events.region, analytics_events.platform_id
  order by event_count desc, analytics_events.event_type, analytics_events.category, analytics_events.region, analytics_events.platform_id;
$$;

revoke execute on function public.get_analytics_event_summary(integer) from public, anon, authenticated;
grant execute on function public.get_analytics_event_summary(integer) to service_role;
