-- Aggregate-only analytics summary for the operations dashboard.
-- Apply manually in Supabase SQL Editor after review.

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
