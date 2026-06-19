-- camp-platform MVP schema
-- 목적:
-- 1) 현재 프론트가 쓰는 profiles / favorites / applications를 바로 수용한다.
-- 2) 이후 campaigns / snapshots / subscriptions로 확장할 수 있게 기반을 만든다.

create extension if not exists pgcrypto;

-- updated_at 자동 갱신용
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;


-- ─────────────────────────────────────────────────────────────
-- platforms
-- ─────────────────────────────────────────────────────────────
create table if not exists public.platforms (
  id text primary key,
  name text not null,
  base_url text not null,
  description text,
  color text,
  emoji text,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- campaigns
-- ─────────────────────────────────────────────────────────────
create table if not exists public.campaigns (
  id uuid primary key default gen_random_uuid(),
  platform_id text not null references public.platforms(id) on delete restrict,
  external_id text not null,
  source_url text not null,
  title text not null,
  campaign_type text,
  category text,
  region text,
  location_raw text,
  address_raw text,
  station_name text,
  place_name text,
  reward_text text,
  apply_count integer not null default 0,
  selected_count integer not null default 0,
  lat double precision,
  lng double precision,
  competition_score numeric(10, 2),
  d_day integer not null default 99,
  source_started_at timestamptz,
  source_posted_at timestamptz,
  coordinate_source text,
  first_seen_at timestamptz not null default now(),
  status text not null default 'open',
  crawled_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (platform_id, external_id)
);

create index if not exists idx_campaigns_platform_id on public.campaigns(platform_id);
create index if not exists idx_campaigns_category on public.campaigns(category);
create index if not exists idx_campaigns_status on public.campaigns(status);
create index if not exists idx_campaigns_d_day on public.campaigns(d_day);
create index if not exists idx_campaigns_source_started_at on public.campaigns(source_started_at desc);
create index if not exists idx_campaigns_source_posted_at on public.campaigns(source_posted_at desc);
create index if not exists idx_campaigns_first_seen_at on public.campaigns(first_seen_at desc);
create index if not exists idx_campaigns_crawled_at on public.campaigns(crawled_at desc);

drop trigger if exists trg_campaigns_updated_at on public.campaigns;
create trigger trg_campaigns_updated_at
before update on public.campaigns
for each row
execute function public.set_updated_at();

create or replace function public.close_expired_campaigns()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  affected integer;
begin
  update public.campaigns
  set status = 'closed'
  where d_day < 0
    and status = 'open';

  get diagnostics affected = row_count;
  return affected;
end;
$$;

revoke all on function public.close_expired_campaigns() from public, anon, authenticated;
grant execute on function public.close_expired_campaigns() to service_role;

-- ─────────────────────────────────────────────────────────────
-- campaign_snapshots
-- ─────────────────────────────────────────────────────────────
create table if not exists public.campaign_snapshots (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  title text,
  apply_count integer,
  selected_count integer,
  d_day integer,
  status text,
  captured_at timestamptz not null default now()
);

create index if not exists idx_campaign_snapshots_campaign_id on public.campaign_snapshots(campaign_id);
create index if not exists idx_campaign_snapshots_captured_at on public.campaign_snapshots(captured_at desc);

-- ─────────────────────────────────────────────────────────────
-- profiles
-- 현재 프론트 호환:
-- id, name, blog_url, SNS 채널, 신청 멘트, level, points 필요
-- ─────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  name text,
  blog_url text,
  instagram_url text,
  youtube_url text,
  application_message_template text,
  naver_blog_neighbor_count integer check (naver_blog_neighbor_count is null or naver_blog_neighbor_count >= 0),
  naver_blog_daily_visitor_count integer check (naver_blog_daily_visitor_count is null or naver_blog_daily_visitor_count >= 0),
  naver_blog_total_visitor_count bigint check (naver_blog_total_visitor_count is null or naver_blog_total_visitor_count >= 0),
  instagram_follower_count integer check (instagram_follower_count is null or instagram_follower_count >= 0),
  youtube_subscriber_count integer check (youtube_subscriber_count is null or youtube_subscriber_count >= 0),
  level text not null default '브론즈',
  points integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_profiles_updated_at on public.profiles;
create trigger trg_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

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

-- 신규 auth.users 생성 시 profiles 자동 생성
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, name, blog_url)
  values (
    new.id,
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'name', '')), ''),
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'blog_url', '')), '')
  )
  on conflict (id) do update
  set
    name = coalesce(excluded.name, public.profiles.name),
    blog_url = coalesce(excluded.blog_url, public.profiles.blog_url),
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

-- ─────────────────────────────────────────────────────────────
-- favorites
-- 현재 프론트 호환:
-- campaign_id, campaign_title, campaign_url, platform, platform_id, category, d_day 저장
-- 장기적으로는 campaign_id 참조 중심으로 정리 가능
-- ─────────────────────────────────────────────────────────────
create table if not exists public.favorites (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  campaign_id text not null,
  campaign_title text not null,
  campaign_url text not null,
  platform text,
  platform_id text,
  category text,
  d_day integer,
  created_at timestamptz not null default now(),
  unique (user_id, campaign_id)
);

create index if not exists idx_favorites_user_id on public.favorites(user_id);
create index if not exists idx_favorites_platform_id on public.favorites(platform_id);

-- ─────────────────────────────────────────────────────────────
-- applications
-- 현재 프론트 호환:
-- campaign_title, platform, platform_id, applied_at, status 사용
-- ─────────────────────────────────────────────────────────────
create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  campaign_id text not null,
  campaign_title text not null,
  campaign_url text,
  platform text,
  platform_id text,
  category text,
  d_day integer,
  status text not null default '심사중',
  applied_at timestamptz not null default now(),
  selected_at timestamptz,
  completed_at timestamptz,
  memo text,
  review_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, campaign_id)
);

create index if not exists idx_applications_user_id on public.applications(user_id);
create index if not exists idx_applications_status on public.applications(status);
create index if not exists idx_applications_platform_id on public.applications(platform_id);
create index if not exists idx_applications_applied_at on public.applications(applied_at desc);

drop trigger if exists trg_applications_updated_at on public.applications;
create trigger trg_applications_updated_at
before update on public.applications
for each row
execute function public.set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- alerts
-- ─────────────────────────────────────────────────────────────
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  keyword text,
  category text,
  platform_id text references public.platforms(id) on delete set null,
  max_competition_score numeric(10, 2),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists idx_alerts_user_id on public.alerts(user_id);

-- ─────────────────────────────────────────────────────────────
-- ad_events
-- ─────────────────────────────────────────────────────────────
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

-- analytics_events
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

-- ─────────────────────────────────────────────────────────────
-- plans
-- ─────────────────────────────────────────────────────────────
create table if not exists public.plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  price_monthly integer not null default 0,
  features jsonb not null default '{}'::jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- ─────────────────────────────────────────────────────────────
-- subscriptions
-- ─────────────────────────────────────────────────────────────
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_id uuid not null references public.plans(id) on delete restrict,
  status text not null default 'inactive',
  started_at timestamptz,
  ends_at timestamptz,
  billing_provider text,
  billing_reference text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_subscriptions_user_id on public.subscriptions(user_id);

drop trigger if exists trg_subscriptions_updated_at on public.subscriptions;
create trigger trg_subscriptions_updated_at
before update on public.subscriptions
for each row
execute function public.set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- RLS
-- campaigns / platforms는 읽기 공개
-- favorites / applications / profiles / alerts / subscriptions는 본인만 접근
-- ─────────────────────────────────────────────────────────────
alter table public.platforms enable row level security;
alter table public.campaigns enable row level security;
alter table public.campaign_snapshots enable row level security;
alter table public.profiles enable row level security;
alter table public.social_connections enable row level security;
alter table public.social_metrics enable row level security;
alter table public.favorites enable row level security;
alter table public.applications enable row level security;
alter table public.alerts enable row level security;
alter table public.ad_events enable row level security;
alter table public.analytics_events enable row level security;
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;

-- 공개 읽기
drop policy if exists "platforms public read" on public.platforms;
create policy "platforms public read"
on public.platforms
for select
to anon, authenticated
using (true);

drop policy if exists "campaigns public read" on public.campaigns;
create policy "campaigns public read"
on public.campaigns
for select
to anon, authenticated
using (true);

drop policy if exists "campaign snapshots public read" on public.campaign_snapshots;
create policy "campaign snapshots public read"
on public.campaign_snapshots
for select
to anon, authenticated
using (true);

drop policy if exists "plans public read" on public.plans;
create policy "plans public read"
on public.plans
for select
to anon, authenticated
using (true);

-- profiles
drop policy if exists "profiles own read" on public.profiles;
create policy "profiles own read"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

drop policy if exists "profiles own insert" on public.profiles;
create policy "profiles own insert"
on public.profiles
for insert
to authenticated
with check (auth.uid() = id);

drop policy if exists "profiles own update" on public.profiles;
create policy "profiles own update"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

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

-- favorites
drop policy if exists "favorites own read" on public.favorites;
create policy "favorites own read"
on public.favorites
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "favorites own insert" on public.favorites;
create policy "favorites own insert"
on public.favorites
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "favorites own delete" on public.favorites;
create policy "favorites own delete"
on public.favorites
for delete
to authenticated
using (auth.uid() = user_id);

-- applications
drop policy if exists "applications own read" on public.applications;
create policy "applications own read"
on public.applications
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "applications own insert" on public.applications;
create policy "applications own insert"
on public.applications
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "applications own update" on public.applications;
create policy "applications own update"
on public.applications
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "applications own delete" on public.applications;
create policy "applications own delete"
on public.applications
for delete
to authenticated
using (auth.uid() = user_id);

-- alerts
drop policy if exists "alerts own read" on public.alerts;
create policy "alerts own read"
on public.alerts
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "alerts own insert" on public.alerts;
create policy "alerts own insert"
on public.alerts
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "alerts own update" on public.alerts;
create policy "alerts own update"
on public.alerts
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "alerts own delete" on public.alerts;
create policy "alerts own delete"
on public.alerts
for delete
to authenticated
using (auth.uid() = user_id);

-- ad_events
drop policy if exists "ad events public insert" on public.ad_events;
create policy "ad events public insert"
on public.ad_events
for insert
to anon, authenticated
with check (true);

create or replace function public.get_ad_event_summary(lookback_days integer default 30)
returns table (
  slot_id text,
  provider text,
  event_type text,
  event_count bigint,
  last_event_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  select
    ad_events.slot_id,
    ad_events.provider,
    ad_events.event_type,
    count(*)::bigint as event_count,
    max(ad_events.created_at) as last_event_at
  from public.ad_events
  where ad_events.created_at >= now() - make_interval(days => greatest(1, least(coalesce(lookback_days, 30), 365)))
  group by ad_events.slot_id, ad_events.provider, ad_events.event_type
  order by event_count desc, ad_events.slot_id, ad_events.provider, ad_events.event_type;
$$;

grant execute on function public.get_ad_event_summary(integer) to anon, authenticated;

-- analytics_events
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

create or replace function public.get_analytics_dashboard_summary(lookback_days integer default 30)
returns table (
  summary_type text,
  summary_key text,
  event_type text,
  event_count bigint,
  unique_users bigint,
  unique_browsers bigint,
  last_event_at timestamptz
)
language sql
security definer
set search_path = public
as $$
  with bounded_events as (
    select *
    from public.analytics_events
    where created_at >= now() - make_interval(days => greatest(1, least(coalesce(lookback_days, 30), 365)))
  )
  select
    'total'::text as summary_type,
    'all'::text as summary_key,
    'all'::text as event_type,
    count(*)::bigint as event_count,
    count(distinct user_id)::bigint as unique_users,
    count(distinct anonymous_id)::bigint as unique_browsers,
    max(created_at) as last_event_at
  from bounded_events

  union all

  select
    'event_type'::text,
    event_type,
    event_type,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  group by event_type

  union all

  select
    'category'::text,
    category,
    'all'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where nullif(category, '') is not null
  group by category

  union all

  select
    'region'::text,
    region,
    'all'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where nullif(region, '') is not null
  group by region

  union all

  select
    'platform'::text,
    platform_id,
    'all'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where nullif(platform_id, '') is not null
  group by platform_id

  union all

  select
    'tab'::text,
    coalesce(nullif(metadata->>'tab', ''), 'unknown'),
    'tab_view'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where event_type = 'tab_view'
  group by coalesce(nullif(metadata->>'tab', ''), 'unknown')

  union all

  select
    'identity'::text,
    case when user_id is null then 'anonymous' else 'logged_in' end,
    'all'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  group by case when user_id is null then 'anonymous' else 'logged_in' end

  union all

  select
    'apply_campaign'::text,
    campaign_id,
    'apply_click'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where event_type = 'apply_click'
    and nullif(campaign_id, '') is not null
  group by campaign_id

  union all

  select
    'open_campaign'::text,
    campaign_id,
    'campaign_open'::text,
    count(*)::bigint,
    count(distinct user_id)::bigint,
    count(distinct anonymous_id)::bigint,
    max(created_at)
  from bounded_events
  where event_type = 'campaign_open'
    and nullif(campaign_id, '') is not null
  group by campaign_id

  order by summary_type, event_count desc, summary_key;
$$;

revoke execute on function public.get_analytics_dashboard_summary(integer) from public, anon;
grant execute on function public.get_analytics_dashboard_summary(integer) to authenticated;

create or replace function public.get_analytics_market_report(
  lookback_days integer default 30,
  min_events integer default 20,
  min_browsers integer default 5
)
returns table (
  report_type text,
  dimension_key text,
  metric_name text,
  metric_value numeric,
  event_count bigint,
  unique_browsers bigint,
  unique_users bigint,
  period_start timestamptz,
  period_end timestamptz
)
language sql
security definer
set search_path = public
as $$
  with settings as (
    select
      greatest(1, least(coalesce(lookback_days, 30), 365))::integer as bounded_days,
      greatest(10, coalesce(min_events, 20))::integer as threshold_events,
      greatest(5, coalesce(min_browsers, 5))::integer as threshold_browsers
  ),
  bounded_events as (
    select analytics_events.*
    from public.analytics_events, settings
    where analytics_events.created_at >= now() - make_interval(days => settings.bounded_days)
  ),
  period as (
    select
      min(created_at) as period_start,
      max(created_at) as period_end
    from bounded_events
  ),
  event_mix as (
    select
      'event_type_mix'::text as report_type,
      event_type as dimension_key,
      'event_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    group by event_type
  ),
  category_interest as (
    select
      'category_interest'::text as report_type,
      category as dimension_key,
      'event_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    where nullif(category, '') is not null
    group by category
  ),
  region_interest as (
    select
      'region_interest'::text as report_type,
      region as dimension_key,
      'event_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    where nullif(region, '') is not null
    group by region
  ),
  platform_interest as (
    select
      'platform_interest'::text as report_type,
      platform_id as dimension_key,
      'event_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    where nullif(platform_id, '') is not null
    group by platform_id
  ),
  tab_attention as (
    select
      'tab_attention'::text as report_type,
      coalesce(nullif(metadata->>'tab', ''), 'unknown') as dimension_key,
      'tab_view_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    where event_type = 'tab_view'
    group by coalesce(nullif(metadata->>'tab', ''), 'unknown')
  ),
  category_apply_funnel as (
    select
      'category_apply_funnel'::text as report_type,
      category as dimension_key,
      'open_to_apply_rate'::text as metric_name,
      (
        count(*) filter (where event_type = 'apply_click')::numeric
        / nullif(count(*) filter (where event_type = 'campaign_open'), 0)
      ) as metric_value,
      count(*) filter (where event_type in ('campaign_open', 'apply_click'))::bigint as event_count,
      count(distinct anonymous_id) filter (where event_type in ('campaign_open', 'apply_click'))::bigint as unique_browsers,
      count(distinct user_id) filter (where event_type in ('campaign_open', 'apply_click'))::bigint as unique_users
    from bounded_events
    where nullif(category, '') is not null
    group by category
  ),
  category_region_interest as (
    select
      'category_region_interest'::text as report_type,
      concat_ws(' / ', category, region) as dimension_key,
      'event_count'::text as metric_name,
      count(*)::numeric as metric_value,
      count(*)::bigint as event_count,
      count(distinct anonymous_id)::bigint as unique_browsers,
      count(distinct user_id)::bigint as unique_users
    from bounded_events
    where nullif(category, '') is not null
      and nullif(region, '') is not null
    group by category, region
  ),
  combined as (
    select * from event_mix
    union all select * from category_interest
    union all select * from region_interest
    union all select * from platform_interest
    union all select * from tab_attention
    union all select * from category_apply_funnel
    union all select * from category_region_interest
  )
  select
    combined.report_type,
    combined.dimension_key,
    combined.metric_name,
    round(coalesce(combined.metric_value, 0), 4) as metric_value,
    combined.event_count,
    combined.unique_browsers,
    combined.unique_users,
    period.period_start,
    period.period_end
  from combined
  cross join settings
  cross join period
  where combined.event_count >= settings.threshold_events
    and combined.unique_browsers >= settings.threshold_browsers
  order by combined.report_type, combined.event_count desc, combined.dimension_key;
$$;

revoke execute on function public.get_analytics_market_report(integer, integer, integer) from public, anon, authenticated;
grant execute on function public.get_analytics_market_report(integer, integer, integer) to service_role;

-- Stored analytics market reports
create table if not exists public.analytics_report_admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists public.analytics_market_reports (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  status text not null default 'ready' check (status in ('ready', 'empty')),
  lookback_days integer not null,
  min_events integer not null,
  min_browsers integer not null,
  row_count integer not null default 0,
  total_event_count bigint not null default 0,
  total_unique_browsers bigint not null default 0,
  period_start timestamptz,
  period_end timestamptz,
  generated_by uuid references auth.users(id) on delete set null,
  generated_at timestamptz not null default now(),
  export_policy_version text not null default 'analytics-market-report-v1',
  notes text,
  parameters jsonb not null default '{}'::jsonb
);

create table if not exists public.analytics_market_report_items (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references public.analytics_market_reports(id) on delete cascade,
  report_type text not null,
  dimension_key text not null,
  metric_name text not null,
  metric_value numeric not null default 0,
  event_count bigint not null default 0,
  unique_browsers bigint not null default 0,
  unique_users bigint not null default 0,
  period_start timestamptz,
  period_end timestamptz,
  rank_position integer not null,
  created_at timestamptz not null default now(),
  unique (report_id, report_type, dimension_key, metric_name)
);

create index if not exists idx_analytics_market_reports_generated_at
on public.analytics_market_reports(generated_at desc);

create index if not exists idx_analytics_market_report_items_report_id
on public.analytics_market_report_items(report_id, rank_position);

alter table public.analytics_report_admins enable row level security;
alter table public.analytics_market_reports enable row level security;
alter table public.analytics_market_report_items enable row level security;

revoke all on table public.analytics_report_admins from public, anon, authenticated;
revoke all on table public.analytics_market_reports from public, anon, authenticated;
revoke all on table public.analytics_market_report_items from public, anon, authenticated;

create or replace function public.is_analytics_report_admin()
returns boolean
language sql
security definer
set search_path = public
as $$
  select coalesce(auth.role(), '') = 'service_role'
    or exists (
      select 1
      from public.analytics_report_admins
      where user_id = auth.uid()
    );
$$;

create or replace function public.create_analytics_market_report(
  lookback_days integer default 30,
  min_events integer default 20,
  min_browsers integer default 5,
  report_title text default null,
  report_notes text default null
)
returns table (
  report_id uuid,
  report_status text,
  report_row_count integer,
  total_event_count bigint,
  total_unique_browsers bigint,
  period_start timestamptz,
  period_end timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
  bounded_days integer := greatest(1, least(coalesce(lookback_days, 30), 365));
  threshold_events integer := greatest(10, coalesce(min_events, 20));
  threshold_browsers integer := greatest(5, coalesce(min_browsers, 5));
  next_report_id uuid := gen_random_uuid();
  inserted_count integer := 0;
  event_total bigint := 0;
  browser_total bigint := 0;
  report_period_start timestamptz;
  report_period_end timestamptz;
  next_status text := 'empty';
begin
  if not public.is_analytics_report_admin() then
    raise exception 'analytics market report admin access required'
      using errcode = '42501';
  end if;

  select
    count(*)::bigint,
    count(distinct anonymous_id)::bigint,
    min(created_at),
    max(created_at)
  into event_total, browser_total, report_period_start, report_period_end
  from public.analytics_events
  where created_at >= now() - make_interval(days => bounded_days);

  insert into public.analytics_market_reports (
    id,
    title,
    lookback_days,
    min_events,
    min_browsers,
    total_event_count,
    total_unique_browsers,
    period_start,
    period_end,
    generated_by,
    notes,
    parameters
  )
  values (
    next_report_id,
    coalesce(nullif(trim(report_title), ''), format('Market report %s', to_char(now(), 'YYYY-MM-DD HH24:MI'))),
    bounded_days,
    threshold_events,
    threshold_browsers,
    event_total,
    browser_total,
    report_period_start,
    report_period_end,
    auth.uid(),
    nullif(trim(report_notes), ''),
    jsonb_build_object(
      'lookback_days', bounded_days,
      'min_events', threshold_events,
      'min_browsers', threshold_browsers,
      'source', 'get_analytics_market_report'
    )
  );

  insert into public.analytics_market_report_items (
    report_id,
    report_type,
    dimension_key,
    metric_name,
    metric_value,
    event_count,
    unique_browsers,
    unique_users,
    period_start,
    period_end,
    rank_position
  )
  select
    next_report_id,
    generated.report_type,
    generated.dimension_key,
    generated.metric_name,
    generated.metric_value,
    generated.event_count,
    generated.unique_browsers,
    generated.unique_users,
    generated.period_start,
    generated.period_end,
    (row_number() over (
      order by generated.report_type, generated.event_count desc, generated.dimension_key
    ))::integer
  from public.get_analytics_market_report(bounded_days, threshold_events, threshold_browsers) as generated;

  get diagnostics inserted_count = row_count;
  next_status := case when inserted_count > 0 then 'ready' else 'empty' end;

  update public.analytics_market_reports
  set
    status = next_status,
    row_count = inserted_count
  where id = next_report_id;

  return query
  select
    next_report_id,
    next_status,
    inserted_count,
    event_total,
    browser_total,
    report_period_start,
    report_period_end;
end;
$$;

create or replace function public.list_analytics_market_reports(report_limit integer default 12)
returns table (
  id uuid,
  title text,
  status text,
  lookback_days integer,
  min_events integer,
  min_browsers integer,
  row_count integer,
  total_event_count bigint,
  total_unique_browsers bigint,
  period_start timestamptz,
  period_end timestamptz,
  generated_at timestamptz,
  generated_by uuid,
  export_policy_version text,
  notes text
)
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_analytics_report_admin() then
    raise exception 'analytics market report admin access required'
      using errcode = '42501';
  end if;

  return query
  select
    reports.id,
    reports.title,
    reports.status,
    reports.lookback_days,
    reports.min_events,
    reports.min_browsers,
    reports.row_count,
    reports.total_event_count,
    reports.total_unique_browsers,
    reports.period_start,
    reports.period_end,
    reports.generated_at,
    reports.generated_by,
    reports.export_policy_version,
    reports.notes
  from public.analytics_market_reports as reports
  order by reports.generated_at desc
  limit greatest(1, least(coalesce(report_limit, 12), 50));
end;
$$;

create or replace function public.get_analytics_market_report_items(target_report_id uuid)
returns table (
  report_id uuid,
  report_type text,
  dimension_key text,
  metric_name text,
  metric_value numeric,
  event_count bigint,
  unique_browsers bigint,
  unique_users bigint,
  period_start timestamptz,
  period_end timestamptz,
  rank_position integer
)
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_analytics_report_admin() then
    raise exception 'analytics market report admin access required'
      using errcode = '42501';
  end if;

  return query
  select
    items.report_id,
    items.report_type,
    items.dimension_key,
    items.metric_name,
    items.metric_value,
    items.event_count,
    items.unique_browsers,
    items.unique_users,
    items.period_start,
    items.period_end,
    items.rank_position
  from public.analytics_market_report_items as items
  where items.report_id = target_report_id
  order by items.rank_position, items.report_type, items.dimension_key;
end;
$$;

revoke execute on function public.is_analytics_report_admin() from public, anon;
grant execute on function public.is_analytics_report_admin() to authenticated, service_role;

revoke execute on function public.create_analytics_market_report(integer, integer, integer, text, text) from public, anon;
grant execute on function public.create_analytics_market_report(integer, integer, integer, text, text) to authenticated, service_role;

revoke execute on function public.list_analytics_market_reports(integer) from public, anon;
grant execute on function public.list_analytics_market_reports(integer) to authenticated, service_role;

revoke execute on function public.get_analytics_market_report_items(uuid) from public, anon;
grant execute on function public.get_analytics_market_report_items(uuid) to authenticated, service_role;

-- subscriptions
drop policy if exists "subscriptions own read" on public.subscriptions;
create policy "subscriptions own read"
on public.subscriptions
for select
to authenticated
using (auth.uid() = user_id);
