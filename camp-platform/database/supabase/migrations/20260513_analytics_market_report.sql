-- Market-report aggregate for external or paid information products.
-- This function intentionally excludes user_id, anonymous_id, session_id,
-- page_path, raw campaign journeys, and raw analytics event rows.
-- Apply manually in Supabase SQL Editor after review.

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
