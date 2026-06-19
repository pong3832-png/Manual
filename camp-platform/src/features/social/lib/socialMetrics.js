function getMetricValue(metrics, metricKey) {
  const row = Array.isArray(metrics)
    ? metrics.find((metric) => metric?.metric_key === metricKey || metric?.metric_type === metricKey)
    : null;
  if (!row) return null;

  const value = row.metric_value ?? row.value;
  return value ?? null;
}

function parseManualMetricValue(value) {
  if (value === null || value === undefined) return null;
  const text = String(value).replaceAll(",", "").trim();
  if (!text) return null;
  const number = Number(text);
  return Number.isFinite(number) ? number : null;
}

function mergeYoutubeMetricsWithManualFallback(apiMetrics = [], manualFallback = {}) {
  const subscriberCount = getMetricValue(apiMetrics, "subscriber_count");
  const videoCount = getMetricValue(apiMetrics, "video_count");
  const viewCount = getMetricValue(apiMetrics, "view_count");
  const manualSubscriberCount = manualFallback && typeof manualFallback === "object"
    ? manualFallback.youtube_subscriber_count
    : manualFallback;
  const manualValue = parseManualMetricValue(manualSubscriberCount);

  if (subscriberCount !== null && subscriberCount !== undefined) {
    return {
      subscriberCount,
      subscriberCountSource: "api",
      videoCount: videoCount ?? null,
      viewCount: viewCount ?? null,
    };
  }

  if (manualValue !== null) {
    return {
      subscriberCount: manualValue,
      subscriberCountSource: "manual",
      videoCount: videoCount ?? null,
      viewCount: viewCount ?? null,
    };
  }

  return {
    subscriberCount: null,
    subscriberCountSource: null,
    videoCount: videoCount ?? null,
    viewCount: viewCount ?? null,
  };
}

export {
  getMetricValue,
  mergeYoutubeMetricsWithManualFallback,
};
