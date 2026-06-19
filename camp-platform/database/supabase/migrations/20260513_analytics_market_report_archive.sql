-- Stored market-report archive for external or paid information products.
-- This layer stores only thresholded aggregates. It never stores user_id,
-- anonymous_id, session_id, page_path, raw campaign journeys, or raw events.
-- Apply manually in Supabase SQL Editor after review.

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
