import { createClient } from "@supabase/supabase-js";
import { resolveYoutubeChannel } from "../_lib/youtube.js";

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function createHttpError(message, status) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function readBearerToken(req) {
  const header = req.headers?.authorization || req.headers?.Authorization || "";
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  return match ? match[1].trim() : "";
}

async function readJsonBody(req) {
  if (Buffer.isBuffer(req.body)) {
    const bufferBody = req.body.toString("utf8").trim();
    if (!bufferBody) return {};
    try {
      return JSON.parse(bufferBody);
    } catch {
      throw createHttpError("Invalid JSON body", 400);
    }
  }

  if (typeof req.body === "string") {
    const textBody = req.body.trim();
    if (!textBody) return {};
    try {
      return JSON.parse(textBody);
    } catch {
      throw createHttpError("Invalid JSON body", 400);
    }
  }

  if (req.body && typeof req.body === "object") return req.body;

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.from(chunk));
  }

  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) return {};

  try {
    return JSON.parse(raw);
  } catch {
    throw createHttpError("Invalid JSON body", 400);
  }
}

function createServiceClient() {
  const url = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceRoleKey) {
    throw createHttpError("Supabase service credentials are not configured", 500);
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

async function getUserFromToken(supabase, accessToken) {
  const { data, error } = await supabase.auth.getUser(accessToken);
  if (error || !data?.user) return null;
  return data.user;
}

function buildConnectionRow({ userId, youtube, now }) {
  return {
    user_id: userId,
    provider: "youtube",
    provider_account_id: youtube.providerAccountId,
    url: youtube.accountUrl,
    display_name: youtube.displayName,
    handle: youtube.username,
    status: "connected",
    sync_status: "synced",
    last_synced_at: now,
    last_sync_error: null,
  };
}

function buildMetricRows({ connectionId, userId, youtube, now }) {
  return Object.entries(youtube.metrics)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([metricType, metricValue]) => ({
      connection_id: connectionId,
      user_id: userId,
      provider: "youtube",
      metric_type: metricType,
      metric_value: metricValue,
      source: "api",
      captured_at: now,
    }));
}

function buildProfileUpdate(youtube) {
  const update = {
    youtube_url: youtube.accountUrl,
  };

  if (youtube.metrics.subscriber_count !== null && youtube.metrics.subscriber_count !== undefined) {
    update.youtube_subscriber_count = youtube.metrics.subscriber_count;
  }

  return update;
}

async function upsertConnectionAndMetrics({ supabase, userId, youtube }) {
  if (!youtube.providerAccountId) {
    throw createHttpError("YouTube channel response is missing a channel ID", 502);
  }

  const now = new Date().toISOString();

  const { data: connection, error: connectionError } = await supabase
    .from("social_connections")
    .upsert(buildConnectionRow({ userId, youtube, now }), {
      onConflict: "user_id,provider,provider_account_id",
    })
    .select("*")
    .single();

  if (connectionError) throw connectionError;

  const metricRows = buildMetricRows({
    connectionId: connection.id,
    userId,
    youtube,
    now,
  });

  if (metricRows.length > 0) {
    const { error: metricsError } = await supabase.from("social_metrics").insert(metricRows);
    if (metricsError) throw metricsError;
  }

  const { error: profileError } = await supabase
    .from("profiles")
    .update(buildProfileUpdate(youtube))
    .eq("id", userId);

  if (profileError) throw profileError;

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
        accountUrl: connection.url,
        providerAccountId: connection.provider_account_id,
        username: connection.handle,
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

export {
  buildConnectionRow,
  buildMetricRows,
  buildProfileUpdate,
  readBearerToken,
  readJsonBody,
};
