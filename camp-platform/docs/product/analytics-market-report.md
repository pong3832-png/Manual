# Analytics Market Report Policy

## Purpose

CheheomMoa can use accumulated behavior events to create aggregate market reports for campaign operators, agencies, and internal planning. The sellable product is not a user-level dataset. It is an anonymized, thresholded, time-windowed report about market demand and campaign interest.

## Allowed Report Units

- Category interest by period
- Region interest by period
- Platform interest by period
- Category and region combined interest
- Tab and feature usage distribution
- Category-level open-to-apply funnel rate
- Event type mix such as campaign open, apply click, search/filter usage

## Not Allowed

- Raw `analytics_events` export
- `user_id`, `anonymous_id`, `session_id`
- Individual user journey or clickstream
- Raw `page_path` values
- Search query text
- Passwords, cookies, tokens, account values, external platform login data
- Reports with sample counts below the configured minimum threshold

## Minimum Privacy Threshold

The first market-report RPC is:

```sql
public.get_analytics_market_report(
  lookback_days integer default 30,
  min_events integer default 20,
  min_browsers integer default 5
)
```

The SQL clamps thresholds so reports require at least:

- `min_events >= 10`
- `min_browsers >= 5`

Segments below the threshold are suppressed. This prevents small samples from exposing individual behavior patterns.

## Data Product Shape

Recommended first products:

- Monthly category demand report
- Regional campaign interest report
- Platform comparison report
- Category funnel report
- Campaign planning insight report for advertisers

Each report should include:

- Report period
- Segment name
- Metric name
- Metric value
- Event count
- Unique browser count
- Unique logged-in user count
- Clear note that values are aggregate behavioral indicators, not guaranteed sales or application outcomes

## Operating Rules

- Use `get_analytics_market_report` or a future export built from it.
- Store external-delivery candidates in `analytics_market_reports` and `analytics_market_report_items`.
- Keep raw event tables internal.
- Do not create per-user or per-session exports.
- Do not sell data until the privacy policy and user consent scope are reviewed for the intended product.
- Review minimum sample thresholds before each external delivery.
- Only users listed in `analytics_report_admins` can create or read stored report archives through the operations dashboard RPCs.

## Stored Report Archive

The archive migration is:

```sql
database/supabase/migrations/20260513_analytics_market_report_archive.sql
```

It adds:

- `analytics_report_admins`: allowlist for report operators
- `analytics_market_reports`: one row per generated report and its criteria
- `analytics_market_report_items`: thresholded aggregate rows only

The operations dashboard uses RPCs instead of direct table reads:

- `create_analytics_market_report(...)`
- `list_analytics_market_reports(...)`
- `get_analytics_market_report_items(...)`

Before using the dashboard generate/download flow, register the operator's Supabase Auth user ID:

```sql
insert into public.analytics_report_admins (user_id, notes)
values ('00000000-0000-0000-0000-000000000000', 'owner')
on conflict (user_id) do nothing;
```

## Current Implementation

- Event capture table: `database/supabase/migrations/20260513_analytics_events.sql`
- Operations dashboard summary: `database/supabase/migrations/20260513_analytics_dashboard_summary.sql`
- Market report RPC: `database/supabase/migrations/20260513_analytics_market_report.sql`
- Stored report archive: `database/supabase/migrations/20260513_analytics_market_report_archive.sql`
