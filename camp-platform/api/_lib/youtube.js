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

function getThumbnailUrl(channel) {
  return (
    channel?.snippet?.thumbnails?.default?.url ||
    channel?.snippet?.thumbnails?.medium?.url ||
    channel?.snippet?.thumbnails?.high?.url ||
    null
  );
}

function createYoutubeError(message, status) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function shapeYoutubeChannel(channel, fallbackUrl) {
  const username = getUsernameFromChannel(channel);
  const hiddenSubscriberCount = Boolean(channel?.statistics?.hiddenSubscriberCount);

  return {
    providerAccountId: channel?.id || null,
    accountUrl: username ? `https://www.youtube.com/@${username}` : fallbackUrl,
    username,
    displayName: channel?.snippet?.title || username || "YouTube channel",
    thumbnailUrl: getThumbnailUrl(channel),
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
    throw createYoutubeError(message, response.status);
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

async function resolveYoutubeChannel({ youtubeUrl, apiKey, fetchImpl = fetch }) {
  if (!apiKey) {
    throw createYoutubeError("YOUTUBE_API_KEY is not configured", 500);
  }

  const parsed = parseYoutubeChannelInput(youtubeUrl);
  if (!parsed) {
    throw createYoutubeError("Invalid YouTube channel URL or handle", 400);
  }

  const channel = parsed.type === "channel_id"
    ? await fetchChannelById({ channelId: parsed.value, apiKey, fetchImpl })
    : await fetchChannelByHandle({ handle: parsed.value, apiKey, fetchImpl });

  if (!channel) {
    throw createYoutubeError("YouTube channel not found", 404);
  }

  return shapeYoutubeChannel(channel, parsed.normalizedUrl);
}

export {
  resolveYoutubeChannel,
  shapeYoutubeChannel,
};
