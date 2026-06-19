# YouTube Social Sync Design

Date: 2026-05-15
Scope: first production-ready social channel sync for `camp-platform` profile page.

## Goal

Build the first automatic social channel integration in a way that can later support Instagram and Naver Blog without reshaping the profile page again.

The first provider is YouTube because public channel statistics are available through the official YouTube Data API. Instagram and Naver Blog remain out of implementation scope for this phase.

## Current State

`src/pages/ProfilePage.jsx` currently saves channel URLs and public metrics directly into `profiles`.

Existing profile columns:

- `blog_url`
- `instagram_url`
- `youtube_url`
- `application_message_template`
- `naver_blog_neighbor_count`
- `naver_blog_daily_visitor_count`
- `naver_blog_total_visitor_count`
- `instagram_follower_count`
- `youtube_subscriber_count`

This works for manual input, but it does not separate connected accounts, sync status, API source, failures, or historical metrics.

## Provider Feasibility

YouTube:

- Supported in phase 1.
- Use YouTube Data API `channels` resource.
- Store `subscriberCount`, `videoCount`, and `viewCount`.
- Subscriber count can be hidden by channel settings, so the UI must handle missing subscriber count.
- Official reference: https://developers.google.com/youtube/v3/docs/channels

Instagram:

- Deferred.
- Requires Instagram professional accounts and Meta app/login/token flow.
- Official API can return `followers_count`, but implementation requires more platform setup and possible App Review.
- Official reference: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started

Naver Blog:

- Deferred as semi-manual.
- Official Naver blog API is search-result oriented and does not provide a stable public neighbor/visitor metric API.
- Existing manual fields stay available.
- Official references:
  - https://developers.naver.com/docs/serviceapi/search/blog/blog.md
  - https://developers.naver.com/docs/login/profile/profile.md

## Data Model

Add a provider-level connection table instead of continuing to widen `profiles`.

`public.social_connections`

- `id uuid primary key`
- `user_id uuid not null references auth.users(id) on delete cascade`
- `provider text not null`
- `account_url text not null`
- `provider_account_id text`
- `username text`
- `display_name text`
- `sync_status text not null default 'pending'`
- `last_synced_at timestamptz`
- `last_error text`
- `metadata jsonb not null default '{}'::jsonb`
- `created_at timestamptz not null default now()`
- `updated_at timestamptz not null default now()`

Constraints:

- `provider in ('youtube', 'instagram', 'naver_blog')`
- `sync_status in ('pending', 'synced', 'failed', 'manual')`
- unique `(user_id, provider, provider_account_id)` where `provider_account_id is not null`
- unique `(user_id, provider, account_url)`

`public.social_metrics`

- `id uuid primary key`
- `connection_id uuid not null references public.social_connections(id) on delete cascade`
- `metric_key text not null`
- `metric_value bigint`
- `source text not null default 'api'`
- `collected_at timestamptz not null default now()`

Constraints:

- `metric_key in ('subscriber_count', 'video_count', 'view_count', 'follower_count', 'neighbor_count', 'daily_visitor_count', 'total_visitor_count')`
- `source in ('api', 'manual', 'verified_manual')`
- `metric_value is null or metric_value >= 0`

Indexes:

- `social_connections_user_provider_idx` on `(user_id, provider)`
- `social_metrics_connection_collected_idx` on `(connection_id, collected_at desc)`

RLS:

- Users can select/insert/update/delete only their own `social_connections`.
- Users can select metrics for their own connections.
- Users cannot write `source = 'api'` metrics directly from the browser.
- Server-side sync writes API metrics through a service role context.

## Server API

Add a Vercel serverless function:

`api/social/youtube-sync.js`

Request:

```json
{
  "youtubeUrl": "https://youtube.com/@handle"
}
```

Authentication:

- Read Supabase JWT from the request.
- Use Supabase server client to resolve the current user.
- Reject unauthenticated requests with `401`.

Provider lookup:

- Accept these inputs:
  - `https://youtube.com/channel/<channelId>`
  - `https://youtube.com/@handle`
  - `https://www.youtube.com/@handle`
  - raw `@handle`
- For `/channel/<id>`, call `channels.list?part=snippet,statistics&id=<id>`.
- For `@handle`, use the YouTube API handle lookup if available. If not reliable, fall back to a `search.list` channel lookup and then `channels.list` by resolved channel ID.
- Do not scrape YouTube pages.

Secrets:

- `YOUTUBE_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Rules:

- These secrets must not use `VITE_`.
- Do not expose API keys to the browser.
- Store only public channel stats and provider identifiers.
- Store raw API response only as minimal metadata, not full payload dumps.

Response:

```json
{
  "ok": true,
  "connection": {
    "provider": "youtube",
    "accountUrl": "...",
    "providerAccountId": "...",
    "username": "...",
    "displayName": "...",
    "lastSyncedAt": "..."
  },
  "metrics": {
    "subscriberCount": 12000,
    "videoCount": 44,
    "viewCount": 991234
  }
}
```

Failure behavior:

- Invalid URL: `400`
- Not authenticated: `401`
- Channel not found: `404`
- YouTube quota/API failure: `502`
- Supabase write failure: `500`

On failure, the API should update `social_connections.sync_status = 'failed'` only when a connection row exists. It should not erase existing profile/manual values.

## Frontend UI

Profile page should separate manual values from connected values.

YouTube block phase 1:

- Input: YouTube channel URL or handle.
- Button: `연동 확인`
- Secondary action after success: `다시 동기화`
- Status text:
  - `연동 전`
  - `동기화 중`
  - `연동됨 · 마지막 갱신 ...`
  - `동기화 실패`
- Metrics:
  - 구독자
  - 영상 수
  - 총 조회수

Fallback:

- Keep existing `youtube_subscriber_count` manual profile field during transition.
- If API metrics exist, show API metrics first and label them `자동 연동`.
- If no API metrics exist, show manual subscriber count and label it `수동 입력`.

No Instagram OAuth or Naver automation UI is implemented in phase 1. Their blocks may show:

- Instagram: `Business/Creator 계정 연동 준비 중`
- Naver Blog: `공식 자동 지표 연동 제한으로 수동 인증 지표 사용`

## Application Structure

Keep the profile page from becoming a provider-specific catch-all.

Recommended files:

- `src/features/social/lib/youtube.js`
  - parse and validate YouTube URL/handle
  - normalize display values
- `src/features/social/lib/socialMetrics.js`
  - convert metric keys to UI labels
  - choose API value over manual fallback
- `src/features/social/hooks/useSocialConnections.js`
  - fetch current user's connections and latest metrics
  - expose reload function
- `api/social/youtube-sync.js`
  - server-only YouTube sync handler
- `database/supabase/migrations/YYYYMMDD_social_connections.sql`
  - tables, constraints, RLS, indexes
- `scripts/qa/youtube-social-fixture.cjs`
  - local parser/payload tests without external API calls

## Verification

Local, no network:

- `node --check api/social/youtube-sync.js`
- `node --check scripts/qa/youtube-social-fixture.cjs`
- `npm.cmd run lint`
- `npm.cmd run build`

Supabase:

- Apply migration only after user approval.
- Confirm tables, constraints, indexes, RLS policies.
- Rollback transaction test for one user-owned connection and metrics.

Network/API:

- Run only after user approval and with `YOUTUBE_API_KEY` configured.
- Test one known public YouTube channel.
- Confirm metrics insert and profile UI display.

Production:

- Add server-only `YOUTUBE_API_KEY` to Vercel.
- Deploy after local build and migration are complete.
- Verify profile YouTube sync from production URL.

## Rollout Plan

Phase 1:

- Create schema and RLS.
- Add YouTube parser and server sync endpoint.
- Add profile UI for YouTube auto sync.
- Preserve manual profile fields as fallback.

Phase 2:

- Add scheduled or button-triggered resync rules.
- Add stale metric labels when `last_synced_at` is older than a threshold.

Phase 3:

- Add Instagram Business/Creator integration after Meta app setup is confirmed.

Phase 4:

- Improve Naver Blog with URL validation and optional manual verification workflow, not scraping.

## Out Of Scope

- Instagram OAuth implementation.
- Naver Blog neighbor/visitor scraping.
- Browser automation for social accounts.
- Background scheduled sync.
- Data resale or ranking logic based on social metrics.
