-- Aggregate ad event performance without exposing raw event rows to visitors.
-- Apply manually in Supabase SQL Editor after review.

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
