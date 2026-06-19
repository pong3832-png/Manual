function normalizeYoutubeInput(input) {
  const text = String(input || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

function isYoutubeHost(hostname) {
  return ["youtube.com", "www.youtube.com", "m.youtube.com"].includes(hostname.toLowerCase());
}

function isValidYoutubeChannelId(value) {
  return /^UC[A-Za-z0-9_-]{22}$/.test(String(value || ""));
}

function parseYoutubeChannelInput(input) {
  const normalizedInput = normalizeYoutubeInput(input);
  const rawText = String(input || "").trim();

  if (/^@[A-Za-z0-9._-]+$/.test(rawText)) {
    const handle = rawText.slice(1);
    return {
      type: "handle",
      value: handle,
      normalizedUrl: `https://www.youtube.com/@${handle}`,
    };
  }

  let url;
  try {
    url = new URL(normalizedInput);
  } catch {
    return null;
  }

  if (!isYoutubeHost(url.hostname)) return null;

  const parts = url.pathname.split("/").filter(Boolean);
  const firstPart = parts[0] || "";
  if (/^@[A-Za-z0-9._-]+$/.test(firstPart)) {
    const handle = firstPart.slice(1);
    return {
      type: "handle",
      value: handle,
      normalizedUrl: `https://www.youtube.com/@${handle}`,
    };
  }

  if (firstPart === "channel" && isValidYoutubeChannelId(parts[1])) {
    const channelId = parts[1];
    return {
      type: "channel_id",
      value: channelId,
      normalizedUrl: `https://www.youtube.com/channel/${channelId}`,
    };
  }

  return null;
}

function formatSocialMetric(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("en-US") : "-";
}

export {
  formatSocialMetric,
  normalizeYoutubeInput,
  parseYoutubeChannelInput,
};
