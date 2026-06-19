-- Allow privacy-minimized map behavior analytics events.
-- Apply manually in Supabase SQL Editor after review.

alter table public.analytics_events
drop constraint if exists analytics_events_event_type_check;

alter table public.analytics_events
add constraint analytics_events_event_type_check
check (
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
    'legal_open',
    'analytics_opt_out',
    'analytics_opt_in'
  )
);
