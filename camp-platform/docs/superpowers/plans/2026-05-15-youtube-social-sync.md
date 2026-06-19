# YouTube Social Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-ready YouTube public metric sync to the profile page without exposing API keys or locking the app into provider-specific profile columns.

**Architecture:** Add normalized social connection and metric tables, a server-only YouTube sync endpoint, small shared parsing helpers, a focused social activity hook, and profile UI that prefers API metrics while preserving manual fallback values. YouTube is the only provider implemented in this phase; Instagram and Naver Blog stay out of scope except for copy that explains their status.

**Tech Stack:** React 19, Vite 8, Vercel Serverless Functions, Supabase Postgres/RLS, `@supabase/supabase-js`, YouTube Data API v3, Node fixture QA scripts.

---

## File Structure

- Create `database/supabase/migrations/20260515_social_connections.sql`
  - Owns the `social_connections` and `social_metrics` schema, indexes, triggers, constraints, grants, and RLS policies.
- Create `src/features/social/lib/youtube.js`
  - Pure browser-safe parsing and formatting helpers for YouTube channel URLs, handles, channel IDs, and metric display.
- Create `src/features/social/lib/socialMetrics.js`
  - Chooses API metrics over manual fallback metrics and maps metric keys to profile UI values.
- Create `src/features/social/hooks/useSocialConnections.js`
  - Reads the current user's social connections and latest metrics from Supabase.
- Create `api/_lib/youtube.js`
  - Server-only YouTube Data API helper. No Supabase writes here.
- Create `api/social/youtube-sync.js`
  - Vercel function that authenticates the Supabase user, calls YouTube, upserts connection/metrics, and returns UI-ready values.
- Create `scripts/qa/youtube-social-fixture.cjs`
  - Offline QA for URL parsing, API response shaping, metric selection, and endpoint request validation helpers.
- Modify `src/pages/ProfilePage.jsx`
  - Replaces manual-only YouTube block with sync-aware UI.
- Modify `src/features/user/hooks/useUserActivity.js`
  - Loads social connections and exposes a reload function or composes the new hook in `ProfilePage`.
- Modify `src/features/user/lib/profile.js`
  - Keep manual fallback fields, but do not add new provider logic here.
- Modify `src/shared/api/supabase.js`
  - Add any missing query builder no-op methods needed by local fallback.
- Modify `.env.example`
  - Add server-only `YOUTUBE_API_KEY`.
- Modify `package.json`
  - Add `qa:youtube:social`.
- Modify `docs/work-log.md`
  - Record implementation and verification results after the implementation is complete.

## Task 1: YouTube URL Parser And Metric Selection

**Files:**
- Create: `src/features/social/lib/youtube.js`
- Create: `src/features/social/lib/socialMetrics.js`
- Create: `scripts/qa/youtube-social-fixture.cjs`
- Modify: `package.json`

- [ ] **Step 1: Write the fixture QA script first**

Create `scripts/qa/youtube-social-fixture.cjs` with:

```js
const assert = require("node:assert/strict");

(async () => {
  const {
    normalizeYoutubeInput,
    parseYoutubeChannelInput,
    formatSocialMetric,
  } = await import("../../src/features/social/lib/youtube.js");
  const {
    getMetricValue,
    mergeYoutubeMetricsWithManualFallback,
  } = await import("../../src/features/social/lib/socialMetrics.js");

  assert.deepEqual(parseYoutubeChannelInput("@camp-test"), {
    type: "handle",
    value: "camp-test",
    normalizedUrl: "https://www.youtube.com/@camp-test",
  });

  assert.deepEqual(parseYoutubeChannelInput("https://www.youtube.com/@camp-test"), {
    type: "handle",
    value: "camp-test",
    normalizedUrl: "https://www.youtube.com/@camp-test",
  });

  assert.deepEqual(parseYoutubeChannelInput("https://youtube.com/channel/UCabc123xyz987"), {
    type: "channel_id",
    value: "UCabc123xyz987",
    normalizedUrl: "https://www.youtube.com/channel/UCabc123xyz987",
  });

  assert.equal(normalizeYoutubeInput(" youtube.com/@camp-test "), "https://youtube.com/@camp-test");
  assert.equal(parseYoutubeChannelInput("not a youtube url"), null);
  assert.equal(formatSocialMetric(1234567), "1,234,567");
  assert.equal(formatSocialMetric(null), "-");

  const metrics = [
    { metric_key: "subscriber_count", metric_value: 1200, source: "api" },
    { metric_key: "video_count", metric_value: 42, source: "api" },
  ];

  assert.equal(getMetricValue(metrics, "subscriber_count"), 1200);
  assert.deepEqual(mergeYoutubeMetricsWithManualFallback(metrics, "999"), {
    subscriberCount: 1200,
    subscriberCountSource: "api",
    videoCount: 42,
    viewCount: null,
  });

  assert.deepEqual(mergeYoutubeMetricsWithManualFallback([], "999"), {
    subscriberCount: 999,
    subscriberCountSource: "manual",
    videoCount: null,
    viewCount: null,
  });

  console.log(JSON.stringify({ ok: true }, null, 2));
})();
```

- [ ] **Step 2: Add the npm script**

Modify `package.json` scripts:

```json
"qa:youtube:social": "node scripts/qa/youtube-social-fixture.cjs"
```

Keep the existing scripts unchanged.

- [ ] **Step 3: Run the fixture and confirm it fails**

Run:

```powershell
npm.cmd run qa:youtube:social
```

Expected: FAIL because `src/features/social/lib/youtube.js` does not exist.

- [ ] **Step 4: Implement the YouTube parser**

Create `src/features/social/lib/youtube.js`:

```js
export function normalizeYoutubeInput(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) return "";
  if (trimmed.startsWith("@")) return `https://www.youtube.com/${trimmed}`;
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

export function parseYoutubeChannelInput(value) {
  const normalized = normalizeYoutubeInput(value);
  if (!normalized) return null;

  try {
    const url = new URL(normalized);
    const host = url.hostname.replace(/^www\./i, "").toLowerCase();
    if (!["youtube.com", "m.youtube.com"].includes(host)) return null;

    const parts = url.pathname.split("/").map((part) => part.trim()).filter(Boolean);
    const first = parts[0] || "";
    const second = parts[1] || "";

    if (first.startsWith("@") && first.length > 1) {
      const handle = first.slice(1);
      return {
        type: "handle",
        value: handle,
        normalizedUrl: `https://www.youtube.com/@${handle}`,
      };
    }

    if (first === "channel" && second) {
      return {
        type: "channel_id",
        value: second,
        normalizedUrl: `https://www.youtube.com/channel/${second}`,
      };
    }

    return null;
  } catch {
    return null;
  }
}

export function formatSocialMetric(value) {
  if (value === null || value === undefined || value === "") return "-";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toLocaleString("ko-KR") : "-";
}
```

- [ ] **Step 5: Implement metric selection**

Create `src/features/social/lib/socialMetrics.js`:

```js
function parseManualMetric(value) {
  const cleaned = String(value || "").replaceAll(",", "").trim();
  if (!cleaned || !/^\d+$/.test(cleaned)) return null;
  const parsed = Number(cleaned);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function getMetricValue(metrics = [], metricKey) {
  const metric = metrics.find((item) => item.metric_key === metricKey && item.metric_value !== null);
  return metric ? Number(metric.metric_value) : null;
}

export function mergeYoutubeMetricsWithManualFallback(metrics = [], manualSubscriberCount = "") {
  const apiSubscriberCount = getMetricValue(metrics, "subscriber_count");
  const manualValue = parseManualMetric(manualSubscriberCount);

  return {
    subscriberCount: apiSubscriberCount ?? manualValue,
    subscriberCountSource: apiSubscriberCount === null ? (manualValue === null ? null : "manual") : "api",
    videoCount: getMetricValue(metrics, "video_count"),
    viewCount: getMetricValue(metrics, "view_count"),
  };
}
```

- [ ] **Step 6: Run parser QA**

Run:

```powershell
npm.cmd run qa:youtube:social
```

Expected: PASS with `{ "ok": true }`.

- [ ] **Step 7: Commit Task 1**

Run:

```powershell
git add package.json src/features/social/lib/youtube.js src/features/social/lib/socialMetrics.js scripts/qa/youtube-social-fixture.cjs
git commit -m "Add YouTube social parsing helpers"
```

## Task 2: Supabase Social Schema

**Files:**
- Create: `database/supabase/migrations/20260515_social_connections.sql`

- [ ] **Step 1: Create the migration**

Create `database/supabase/migrations/20260515_social_connections.sql`:

```sql
-- Social channel connections and metric history.
-- Apply before deploying YouTube automatic sync.

create table if not exists public.social_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text not null,
  account_url text not null,
  provider_account_id text,
  username text,
  display_name text,
  sync_status text not null default 'pending',
  last_synced_at timestamptz,
  last_error text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint social_connections_provider_check
    check (provider in ('youtube', 'instagram', 'naver_blog')),
  constraint social_connections_sync_status_check
    check (sync_status in ('pending', 'synced', 'failed', 'manual'))
);

create table if not exists public.social_metrics (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null references public.social_connections(id) on delete cascade,
  metric_key text not null,
  metric_value bigint,
  source text not null default 'api',
  collected_at timestamptz not null default now(),
  constraint social_metrics_key_check
    check (metric_key in (
      'subscriber_count',
      'video_count',
      'view_count',
      'follower_count',
      'neighbor_count',
      'daily_visitor_count',
      'total_visitor_count'
    )),
  constraint social_metrics_source_check
    check (source in ('api', 'manual', 'verified_manual')),
  constraint social_metrics_nonnegative_check
    check (metric_value is null or metric_value >= 0)
);

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'social_connections_user_provider_account_key'
      and conrelid = 'public.social_connections'::regclass
  ) then
    alter table public.social_connections
      add constraint social_connections_user_provider_account_key
      unique (user_id, provider, provider_account_id);
  end if;

  if not exists (
    select 1
    from pg_constraint
    where conname = 'social_connections_user_provider_url_key'
      and conrelid = 'public.social_connections'::regclass
  ) then
    alter table public.social_connections
      add constraint social_connections_user_provider_url_key
      unique (user_id, provider, account_url);
  end if;
end $$;

create index if not exists social_connections_user_provider_idx
  on public.social_connections (user_id, provider);

create index if not exists social_metrics_connection_collected_idx
  on public.social_metrics (connection_id, collected_at desc);

drop trigger if exists trg_social_connections_updated_at on public.social_connections;
create trigger trg_social_connections_updated_at
before update on public.social_connections
for each row
execute function public.set_updated_at();

alter table public.social_connections enable row level security;
alter table public.social_metrics enable row level security;

drop policy if exists "social connections own read" on public.social_connections;
create policy "social connections own read"
on public.social_connections
for select
to authenticated
using (auth.uid() = user_id);

drop policy if exists "social connections own insert" on public.social_connections;
create policy "social connections own insert"
on public.social_connections
for insert
to authenticated
with check (auth.uid() = user_id);

drop policy if exists "social connections own update" on public.social_connections;
create policy "social connections own update"
on public.social_connections
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "social connections own delete" on public.social_connections;
create policy "social connections own delete"
on public.social_connections
for delete
to authenticated
using (auth.uid() = user_id);

drop policy if exists "social metrics own read" on public.social_metrics;
create policy "social metrics own read"
on public.social_metrics
for select
to authenticated
using (
  exists (
    select 1
    from public.social_connections connection
    where connection.id = social_metrics.connection_id
      and connection.user_id = auth.uid()
  )
);

grant select, insert, update, delete on public.social_connections to authenticated;
grant select on public.social_metrics to authenticated;

notify pgrst, 'reload schema';
```

- [ ] **Step 2: Run SQL text checks**

Run:

```powershell
git diff --check -- database\supabase\migrations\20260515_social_connections.sql
```

Expected: PASS. CRLF warnings are acceptable.

- [ ] **Step 3: Commit Task 2**

Run:

```powershell
git add database/supabase/migrations/20260515_social_connections.sql
git commit -m "Add social connection schema"
```

Do not apply the migration to production yet. Production DB application requires explicit user approval.

## Task 3: Server-Side YouTube API Helper

**Files:**
- Create: `api/_lib/youtube.js`
- Modify: `scripts/qa/youtube-social-fixture.cjs`

- [ ] **Step 1: Extend fixture QA with mocked YouTube responses**

Append to `scripts/qa/youtube-social-fixture.cjs` before the final `console.log`:

```js
  const {
    resolveYoutubeChannel,
    shapeYoutubeChannel,
  } = await import("../../api/_lib/youtube.js");

  const mockChannel = {
    id: "UCabc123xyz987",
    snippet: {
      title: "Camp Test",
      customUrl: "@camp-test",
      thumbnails: {
        default: { url: "https://example.com/avatar.jpg" },
      },
    },
    statistics: {
      subscriberCount: "1200",
      videoCount: "42",
      viewCount: "99000",
      hiddenSubscriberCount: false,
    },
  };

  assert.deepEqual(shapeYoutubeChannel(mockChannel, "https://www.youtube.com/@camp-test"), {
    providerAccountId: "UCabc123xyz987",
    accountUrl: "https://www.youtube.com/@camp-test",
    username: "camp-test",
    displayName: "Camp Test",
    thumbnailUrl: "https://example.com/avatar.jpg",
    metrics: {
      subscriber_count: 1200,
      video_count: 42,
      view_count: 99000,
    },
  });

  const calls = [];
  const mockFetch = async (url) => {
    calls.push(String(url));
    return {
      ok: true,
      status: 200,
      async json() {
        return { items: [mockChannel] };
      },
    };
  };

  const resolved = await resolveYoutubeChannel({
    youtubeUrl: "https://www.youtube.com/channel/UCabc123xyz987",
    apiKey: "test-key",
    fetchImpl: mockFetch,
  });

  assert.equal(resolved.providerAccountId, "UCabc123xyz987");
  assert.equal(resolved.metrics.subscriber_count, 1200);
  assert.ok(calls[0].includes("part=snippet%2Cstatistics"));
```

- [ ] **Step 2: Run fixture and confirm it fails**

Run:

```powershell
npm.cmd run qa:youtube:social
```

Expected: FAIL because `api/_lib/youtube.js` does not exist.

- [ ] **Step 3: Implement the server helper**

Create `api/_lib/youtube.js`:

```js
import { parseYoutubeChannelInput } from "../../src/features/social/lib/youtube.js";

const YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3";

function toSafeInteger(value) {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : null;
}

function getUsernameFromChannel(channel) {
  const customUrl = String(channel?.snippet?.customUrl || "").trim();
  return customUrl.startsWith("@") ? customUrl.slice(1) : customUrl || null;
}

export function shapeYoutubeChannel(channel, fallbackUrl) {
  const username = getUsernameFromChannel(channel);
  const hiddenSubscriberCount = Boolean(channel?.statistics?.hiddenSubscriberCount);

  return {
    providerAccountId: channel.id,
    accountUrl: username ? `https://www.youtube.com/@${username}` : fallbackUrl,
    username,
    displayName: channel?.snippet?.title || username || "YouTube channel",
    thumbnailUrl: channel?.snippet?.thumbnails?.default?.url || null,
    metrics: {
      subscriber_count: hiddenSubscriberCount ? null : toSafeInteger(channel?.statistics?.subscriberCount),
      video_count: toSafeInteger(channel?.statistics?.videoCount),
      view_count: toSafeInteger(channel?.statistics?.viewCount),
    },
  };
}

async function fetchYoutubeJson(url, fetchImpl) {
  const response = await fetchImpl(url);
  const payload = await response.json();

  if (!response.ok) {
    const message = payload?.error?.message || `YouTube API request failed with ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload;
}

async function fetchChannelById({ channelId, apiKey, fetchImpl }) {
  const url = new URL(`${YOUTUBE_API_BASE}/channels`);
  url.searchParams.set("part", "snippet,statistics");
  url.searchParams.set("id", channelId);
  url.searchParams.set("key", apiKey);

  const payload = await fetchYoutubeJson(url, fetchImpl);
  return payload.items?.[0] || null;
}

async function fetchChannelByHandle({ handle, apiKey, fetchImpl }) {
  const url = new URL(`${YOUTUBE_API_BASE}/channels`);
  url.searchParams.set("part", "snippet,statistics");
  url.searchParams.set("forHandle", handle);
  url.searchParams.set("key", apiKey);

  const payload = await fetchYoutubeJson(url, fetchImpl);
  return payload.items?.[0] || null;
}

export async function resolveYoutubeChannel({ youtubeUrl, apiKey, fetchImpl = fetch }) {
  if (!apiKey) {
    const error = new Error("YOUTUBE_API_KEY is not configured");
    error.status = 500;
    throw error;
  }

  const parsed = parseYoutubeChannelInput(youtubeUrl);
  if (!parsed) {
    const error = new Error("Invalid YouTube channel URL or handle");
    error.status = 400;
    throw error;
  }

  const channel = parsed.type === "channel_id"
    ? await fetchChannelById({ channelId: parsed.value, apiKey, fetchImpl })
    : await fetchChannelByHandle({ handle: parsed.value, apiKey, fetchImpl });

  if (!channel) {
    const error = new Error("YouTube channel not found");
    error.status = 404;
    throw error;
  }

  return shapeYoutubeChannel(channel, parsed.normalizedUrl);
}
```

- [ ] **Step 4: Run helper QA**

Run:

```powershell
npm.cmd run qa:youtube:social
node --check api/_lib/youtube.js
```

Expected: both PASS.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add api/_lib/youtube.js scripts/qa/youtube-social-fixture.cjs
git commit -m "Add server YouTube API resolver"
```

## Task 4: YouTube Sync Endpoint

**Files:**
- Create: `api/social/youtube-sync.js`
- Modify: `scripts/qa/youtube-social-fixture.cjs`

- [ ] **Step 1: Add endpoint request validation fixture**

Append to `scripts/qa/youtube-social-fixture.cjs` before final output:

```js
  const {
    readBearerToken,
    readJsonBody,
  } = await import("../../api/social/youtube-sync.js");

  assert.equal(readBearerToken({ headers: { authorization: "Bearer abc" } }), "abc");
  assert.equal(readBearerToken({ headers: { Authorization: "Bearer abc" } }), "abc");
  assert.equal(readBearerToken({ headers: {} }), "");
  assert.deepEqual(await readJsonBody({ body: { youtubeUrl: "@camp-test" } }), { youtubeUrl: "@camp-test" });
```

- [ ] **Step 2: Run endpoint fixture and confirm it fails**

Run:

```powershell
npm.cmd run qa:youtube:social
```

Expected: FAIL because `api/social/youtube-sync.js` does not exist.

- [ ] **Step 3: Implement the endpoint**

Create `api/social/youtube-sync.js`:

```js
import { createClient } from "@supabase/supabase-js";
import { resolveYoutubeChannel } from "../_lib/youtube.js";

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

export function readBearerToken(req) {
  const header = req.headers?.authorization || req.headers?.Authorization || "";
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  return match ? match[1].trim() : "";
}

export async function readJsonBody(req) {
  if (req.body && typeof req.body === "object") return req.body;

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return raw ? JSON.parse(raw) : {};
}

function createServiceClient() {
  const url = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceRoleKey) {
    throw new Error("Supabase service credentials are not configured");
  }
  return createClient(url, serviceRoleKey, {
    auth: { persistSession: false },
  });
}

async function getUserFromToken(supabase, accessToken) {
  const { data, error } = await supabase.auth.getUser(accessToken);
  if (error || !data?.user) return null;
  return data.user;
}

async function upsertConnectionAndMetrics({ supabase, userId, youtube }) {
  const now = new Date().toISOString();

  const { data: connection, error: connectionError } = await supabase
    .from("social_connections")
    .upsert({
      user_id: userId,
      provider: "youtube",
      account_url: youtube.accountUrl,
      provider_account_id: youtube.providerAccountId,
      username: youtube.username,
      display_name: youtube.displayName,
      sync_status: "synced",
      last_synced_at: now,
      last_error: null,
      metadata: {
        thumbnail_url: youtube.thumbnailUrl,
      },
    }, {
      onConflict: "user_id,provider,provider_account_id",
    })
    .select("*")
    .single();

  if (connectionError) throw connectionError;

  const metricRows = Object.entries(youtube.metrics)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([metricKey, metricValue]) => ({
      connection_id: connection.id,
      metric_key: metricKey,
      metric_value: metricValue,
      source: "api",
      collected_at: now,
    }));

  if (metricRows.length > 0) {
    const { error: metricsError } = await supabase.from("social_metrics").insert(metricRows);
    if (metricsError) throw metricsError;
  }

  return connection;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "Method not allowed" });
    return;
  }

  try {
    const accessToken = readBearerToken(req);
    if (!accessToken) {
      sendJson(res, 401, { ok: false, error: "Login is required" });
      return;
    }

    const supabase = createServiceClient();
    const user = await getUserFromToken(supabase, accessToken);
    if (!user) {
      sendJson(res, 401, { ok: false, error: "Login is required" });
      return;
    }

    const body = await readJsonBody(req);
    const youtubeUrl = String(body.youtubeUrl || "").trim();

    const youtube = await resolveYoutubeChannel({
      youtubeUrl,
      apiKey: process.env.YOUTUBE_API_KEY,
    });

    const connection = await upsertConnectionAndMetrics({
      supabase,
      userId: user.id,
      youtube,
    });

    sendJson(res, 200, {
      ok: true,
      connection: {
        id: connection.id,
        provider: connection.provider,
        accountUrl: connection.account_url,
        providerAccountId: connection.provider_account_id,
        username: connection.username,
        displayName: connection.display_name,
        lastSyncedAt: connection.last_synced_at,
      },
      metrics: {
        subscriberCount: youtube.metrics.subscriber_count,
        videoCount: youtube.metrics.video_count,
        viewCount: youtube.metrics.view_count,
      },
    });
  } catch (error) {
    const status = error.status || 500;
    const publicStatus = status >= 400 && status < 500 ? status : 502;
    sendJson(res, publicStatus, {
      ok: false,
      error: error.message || "YouTube sync failed",
    });
  }
}
```

- [ ] **Step 4: Guard endpoint auto-execution for fixture import**

No extra guard is needed because Vercel endpoint exports a default handler and does not execute on import.

- [ ] **Step 5: Run endpoint checks**

Run:

```powershell
npm.cmd run qa:youtube:social
node --check api/social/youtube-sync.js
```

Expected: both PASS.

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add api/social/youtube-sync.js scripts/qa/youtube-social-fixture.cjs
git commit -m "Add YouTube social sync endpoint"
```

## Task 5: Social Connections Hook

**Files:**
- Create: `src/features/social/hooks/useSocialConnections.js`
- Modify: `src/shared/api/supabase.js`

- [ ] **Step 1: Add fallback query methods if needed**

Modify `src/shared/api/supabase.js` `createEmptyQueryBuilder()` to include `in()` and `maybeSingle()` if future social queries need them:

```js
    in() {
      return builder;
    },
    maybeSingle() {
      return Promise.resolve({ data: null, error: null });
    },
```

- [ ] **Step 2: Create the hook**

Create `src/features/social/hooks/useSocialConnections.js`:

```js
import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "../../../shared/api/supabase";

function getLatestMetrics(metrics = []) {
  const byConnection = new Map();

  metrics.forEach((metric) => {
    const key = metric.connection_id;
    const current = byConnection.get(key) || [];
    current.push(metric);
    byConnection.set(key, current);
  });

  return byConnection;
}

export default function useSocialConnections(user) {
  const userId = user?.id || null;
  const [state, setState] = useState({
    userId: null,
    connections: [],
    metrics: [],
    isLoading: false,
  });

  const loadSocialConnections = useCallback(async (targetUserId = userId) => {
    if (!targetUserId) {
      setState({ userId: null, connections: [], metrics: [], isLoading: false });
      return { connections: [], metrics: [] };
    }

    setState((prev) => ({ ...prev, isLoading: true }));

    const { data: connections } = await supabase
      .from("social_connections")
      .select("*")
      .eq("user_id", targetUserId)
      .order("created_at", { ascending: false });

    const connectionIds = (connections || []).map((connection) => connection.id);
    const { data: metrics } = connectionIds.length > 0
      ? await supabase
        .from("social_metrics")
        .select("*")
        .in("connection_id", connectionIds)
        .order("collected_at", { ascending: false })
      : { data: [] };

    const nextState = {
      userId: targetUserId,
      connections: connections || [],
      metrics: metrics || [],
      isLoading: false,
    };

    setState(nextState);
    return nextState;
  }, [userId]);

  useEffect(() => {
    void loadSocialConnections(userId);
  }, [userId, loadSocialConnections]);

  const metricsByConnection = useMemo(() => getLatestMetrics(
    state.userId === userId ? state.metrics : [],
  ), [state.metrics, state.userId, userId]);

  return {
    connections: state.userId === userId ? state.connections : [],
    metrics: state.userId === userId ? state.metrics : [],
    metricsByConnection,
    isLoading: state.isLoading,
    loadSocialConnections,
  };
}
```

- [ ] **Step 3: Run lint for the new hook**

Run:

```powershell
.\node_modules\.bin\eslint.cmd .\src\features\social\hooks\useSocialConnections.js .\src\shared\api\supabase.js
```

Expected: PASS.

- [ ] **Step 4: Commit Task 5**

Run:

```powershell
git add src/features/social/hooks/useSocialConnections.js src/shared/api/supabase.js
git commit -m "Add social connection loading hook"
```

## Task 6: Profile Page YouTube Sync UI

**Files:**
- Modify: `src/pages/ProfilePage.jsx`
- Modify: `src/app/App.css` or `src/app/compact-ui.css`
- Modify: `src/features/user/lib/profile.js` only if the manual fallback labels need helper exports.

- [ ] **Step 1: Import social helpers and hook**

In `src/pages/ProfilePage.jsx`, add:

```js
import useSocialConnections from "../features/social/hooks/useSocialConnections";
import { formatSocialMetric } from "../features/social/lib/youtube";
import { mergeYoutubeMetricsWithManualFallback } from "../features/social/lib/socialMetrics";
```

- [ ] **Step 2: Add hook state in `ProfileDashboard`**

Inside `ProfileDashboard`, after local state declarations:

```js
  const {
    connections: socialConnections,
    metricsByConnection,
    loadSocialConnections,
  } = useSocialConnections(user);
  const [isSyncingYoutube, setIsSyncingYoutube] = useState(false);
```

- [ ] **Step 3: Derive YouTube connection and metrics**

Add near existing memo values:

```js
  const youtubeConnection = socialConnections.find((connection) => connection.provider === "youtube") || null;
  const youtubeMetrics = youtubeConnection
    ? metricsByConnection.get(youtubeConnection.id) || []
    : [];
  const mergedYoutubeMetrics = mergeYoutubeMetricsWithManualFallback(
    youtubeMetrics,
    profileDraft.youtubeSubscriberCount,
  );
```

- [ ] **Step 4: Add sync handler**

Add this function in `ProfileDashboard`:

```js
  const handleSyncYoutube = async () => {
    if (!user || isSyncingYoutube) return;

    const youtubeUrl = profileDraft.youtubeUrl.trim();
    if (!youtubeUrl) {
      showToast?.("유튜브 채널 주소를 입력해 주세요.");
      return;
    }

    setIsSyncingYoutube(true);
    try {
      const { data: sessionData } = await supabase.auth.getSession();
      const accessToken = sessionData?.session?.access_token;
      if (!accessToken) {
        showToast?.("로그인 세션을 다시 확인해 주세요.", "error");
        return;
      }

      const response = await fetch("/api/social/youtube-sync", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ youtubeUrl }),
      });
      const payload = await response.json();

      if (!response.ok || !payload.ok) {
        showToast?.(payload.error || "유튜브 연동에 실패했습니다.", "error");
        return;
      }

      await loadSocialConnections(user.id);
      if (!hasProfileChanges) {
        await onProfileSaved?.();
      }
      showToast?.("유튜브 지표를 동기화했습니다.");
    } catch {
      showToast?.("유튜브 연동 중 오류가 발생했습니다.", "error");
    } finally {
      setIsSyncingYoutube(false);
    }
  };
```

- [ ] **Step 5: Replace the YouTube channel block**

Replace only the existing YouTube block in `ProfilePage.jsx` with:

```jsx
          <div className="profile-channel-block">
            <div className="profile-channel-head">
              <span className="profile-channel-mark youtube">Y</span>
              <div>
                <div className="profile-channel-name">유튜브</div>
                <div className="profile-channel-sub">
                  {youtubeConnection
                    ? `자동 연동 · ${youtubeConnection.last_synced_at ? new Date(youtubeConnection.last_synced_at).toLocaleString("ko-KR") : "동기화 대기"}`
                    : "채널 주소로 공개 지표를 연동합니다"}
                </div>
              </div>
            </div>
            <div className="profile-form-grid">
              <label className="profile-field">
                <span>유튜브 주소</span>
                <input
                  className="profile-input"
                  value={profileDraft.youtubeUrl}
                  onChange={(event) => setDraftField("youtubeUrl", event.target.value)}
                  placeholder="https://youtube.com/@..."
                />
              </label>
              <div className="profile-sync-actions">
                <button
                  type="button"
                  className="profile-secondary-btn"
                  onClick={handleSyncYoutube}
                  disabled={isSyncingYoutube}
                >
                  {isSyncingYoutube ? "동기화 중" : youtubeConnection ? "다시 동기화" : "연동 확인"}
                </button>
                <span className={`profile-sync-status ${youtubeConnection?.sync_status === "synced" ? "synced" : ""}`}>
                  {youtubeConnection?.sync_status === "synced" ? "연동됨" : "연동 전"}
                </span>
              </div>
            </div>
            <div className="profile-channel-summary compact">
              <div className="profile-channel-summary-item">
                <span>구독자</span>
                <strong>{formatSocialMetric(mergedYoutubeMetrics.subscriberCount)}</strong>
                <small>{mergedYoutubeMetrics.subscriberCountSource === "api" ? "자동 연동" : "수동 입력"}</small>
              </div>
              <div className="profile-channel-summary-item">
                <span>영상 수</span>
                <strong>{formatSocialMetric(mergedYoutubeMetrics.videoCount)}</strong>
                <small>자동 연동</small>
              </div>
              <div className="profile-channel-summary-item">
                <span>총 조회수</span>
                <strong>{formatSocialMetric(mergedYoutubeMetrics.viewCount)}</strong>
                <small>자동 연동</small>
              </div>
            </div>
          </div>
```

- [ ] **Step 6: Add compact CSS**

Add to `src/app/App.css` or the file that currently owns `.profile-channel-*`:

```css
.profile-sync-actions {
  align-items: center;
  display: flex;
  gap: 8px;
  min-height: 40px;
}

.profile-sync-status {
  color: #6B7280;
  font-size: 12px;
  font-weight: 700;
}

.profile-sync-status.synced {
  color: #059669;
}

.profile-channel-summary.compact {
  margin-top: 10px;
}

.profile-channel-summary-item small {
  color: #6B7280;
  display: block;
  font-size: 11px;
  font-weight: 600;
  margin-top: 2px;
}
```

- [ ] **Step 7: Run focused lint**

Run:

```powershell
.\node_modules\.bin\eslint.cmd .\src\pages\ProfilePage.jsx .\src\features\social\hooks\useSocialConnections.js .\src\features\social\lib\youtube.js .\src\features\social\lib\socialMetrics.js
```

Expected: PASS.

- [ ] **Step 8: Commit Task 6**

Run:

```powershell
git add src/pages/ProfilePage.jsx src/app/App.css src/features/social
git commit -m "Add YouTube sync profile UI"
```

## Task 7: Environment And Documentation

**Files:**
- Modify: `.env.example`
- Modify: `AGENTS.md`
- Modify: `docs/work-log.md`

- [ ] **Step 1: Add server-only env var**

Add to `.env.example`:

```text
YOUTUBE_API_KEY=
```

Do not add a `VITE_` prefix.

- [ ] **Step 2: Update `AGENTS.md`**

Add under Environment Variables or social/profile rules:

```markdown
### Social Sync

| 변수 | 용도 | 필수 여부 |
| --- | --- | --- |
| `YOUTUBE_API_KEY` | Server-only YouTube Data API key for profile channel metric sync | YouTube sync endpoint requires it |

Rules:

- Never expose `YOUTUBE_API_KEY` with a `VITE_` prefix.
- YouTube sync uses official API only and does not scrape YouTube pages.
- Instagram and Naver Blog automatic metric sync are separate future work.
```

- [ ] **Step 3: Update work log after implementation**

Append a short entry to `docs/work-log.md` once code and verification are complete:

```markdown
- YouTube social sync phase 1 implemented with server-only API key, `social_connections`/`social_metrics` schema, profile UI sync action, and manual fallback.
- Verification: `npm.cmd run qa:youtube:social`, focused ESLint, and `npm.cmd run build` passed.
- Production DB migration and Vercel env/deploy remain approval-gated.
```

- [ ] **Step 4: Run doc diff check**

Run:

```powershell
git diff --check -- .env.example AGENTS.md docs/work-log.md
```

Expected: PASS.

- [ ] **Step 5: Commit Task 7**

Run:

```powershell
git add .env.example AGENTS.md docs/work-log.md
git commit -m "Document YouTube social sync setup"
```

## Task 8: Local Verification

**Files:**
- No new files unless fixes are needed.

- [ ] **Step 1: Run fixture QA**

Run:

```powershell
npm.cmd run qa:youtube:social
```

Expected: PASS.

- [ ] **Step 2: Run syntax checks**

Run:

```powershell
node --check api/_lib/youtube.js
node --check api/social/youtube-sync.js
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```powershell
npm.cmd run lint
```

Expected: PASS.

- [ ] **Step 4: Run build**

Run:

```powershell
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 5: Check git status**

Run:

```powershell
git status --short
```

Expected: only intentional files changed. Existing unrelated dirty files such as `public/campaigns.json`, `public/crawl-status.json`, `public/data-quality.json`, or `AI identity prompt.md` must not be staged unless the user explicitly includes them.

## Task 9: Approval-Gated Production Steps

**Files:**
- No code changes.

- [ ] **Step 1: Ask user to apply Supabase migration**

Provide this exact instruction:

```text
Apply `database/supabase/migrations/20260515_social_connections.sql` in Supabase SQL Editor.
```

Do not apply production DB migration without explicit user approval.

- [ ] **Step 2: Verify migration after user applies it**

Use Supabase read-only SQL:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('social_connections', 'social_metrics')
order by table_name;

select indexname
from pg_indexes
where schemaname = 'public'
  and tablename in ('social_connections', 'social_metrics')
order by tablename, indexname;
```

Expected:

- `social_connections`
- `social_metrics`
- unique/index entries for user/provider/account and metrics collection

- [ ] **Step 3: Ask user to configure Vercel env**

Provide:

```text
Add `YOUTUBE_API_KEY` as a server-only Vercel environment variable for Production.
Do not add `VITE_YOUTUBE_API_KEY`.
```

- [ ] **Step 4: Run one live API sync only after approval**

Only after DB migration and Vercel/local env are ready, test with one known public YouTube channel from the browser or a local authenticated session.

Expected:

- Profile UI shows `연동됨`.
- Metrics show `자동 연동`.
- `social_connections.sync_status = 'synced'`.
- `social_metrics` has rows for `subscriber_count`, `video_count`, and `view_count` when the API returns them.

- [ ] **Step 5: Deploy only after approval**

Run production deploy only after user approval:

```powershell
vercel.cmd --prod --yes
```

Expected:

- Vercel build succeeds.
- Production alias updates.
- No unrelated dirty public JSON changes are unintentionally included.

## Self-Review

Spec coverage:

- Data model is covered by Task 2.
- Server-only YouTube API and key secrecy are covered by Tasks 3, 4, 7, and 9.
- Profile UI and manual fallback are covered by Tasks 5 and 6.
- Verification and approval gates are covered by Tasks 8 and 9.
- Instagram and Naver Blog remain deferred and are not implemented in this plan.

Placeholder scan:

- The plan contains no `TBD` or undefined implementation placeholders.
- All code-bearing tasks include concrete code.

Type consistency:

- `providerAccountId`, `accountUrl`, `username`, `displayName`, and metric keys are consistent between helper, endpoint, and UI plan.
- Database column names use snake_case. Browser response names use camelCase.
