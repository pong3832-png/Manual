const assert = require("node:assert/strict");

(async () => {
  const {
    formatSocialMetric,
    normalizeYoutubeInput,
    parseYoutubeChannelInput,
  } = await import("../../src/features/social/lib/youtube.js");
  const {
    getMetricValue,
    mergeYoutubeMetricsWithManualFallback,
  } = await import("../../src/features/social/lib/socialMetrics.js");

  const handleChannel = {
    type: "handle",
    value: "camp-test",
    normalizedUrl: "https://www.youtube.com/@camp-test",
  };

  assert.deepEqual(parseYoutubeChannelInput("@camp-test"), handleChannel);
  assert.deepEqual(parseYoutubeChannelInput("https://www.youtube.com/@camp-test"), handleChannel);
  assert.deepEqual(parseYoutubeChannelInput("https://m.youtube.com/@camp-test"), handleChannel);
  assert.deepEqual(parseYoutubeChannelInput("https://www.youtube.com/@camp-test?si=abc"), handleChannel);
  assert.deepEqual(parseYoutubeChannelInput("https://youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"), {
    type: "channel_id",
    value: "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    normalizedUrl: "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw",
  });
  assert.equal(normalizeYoutubeInput(" youtube.com/@camp-test "), "https://youtube.com/@camp-test");
  assert.equal(parseYoutubeChannelInput("not a youtube url"), null);
  assert.equal(parseYoutubeChannelInput("https://youtube.com/channel/videos"), null);
  assert.equal(parseYoutubeChannelInput("https://youtube.com/channel/UCabc123xyz987"), null);
  assert.equal(formatSocialMetric(1234567), "1,234,567");
  assert.equal(formatSocialMetric(null), "-");

  const metricRows = [
    { metric_key: "view_count", metric_value: 99 },
    { metric_key: "subscriber_count", metric_value: 1234 },
    { metric_type: "video_count", metric_value: 42 },
  ];

  assert.equal(getMetricValue(metricRows, "subscriber_count"), 1234);
  assert.equal(getMetricValue(metricRows, "video_count"), 42);
  assert.equal(getMetricValue(metricRows, "missing_count"), null);

  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback(
      [{ metric_key: "subscriber_count", metric_value: 1234 }],
      { youtube_subscriber_count: 77 },
    ),
    { subscriberCount: 1234, subscriberCountSource: "api", videoCount: null, viewCount: null },
  );
  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback([], { youtube_subscriber_count: 77 }),
    { subscriberCount: 77, subscriberCountSource: "manual", videoCount: null, viewCount: null },
  );
  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback([], "1,234"),
    { subscriberCount: 1234, subscriberCountSource: "manual", videoCount: null, viewCount: null },
  );
  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback([], "   "),
    { subscriberCount: null, subscriberCountSource: null, videoCount: null, viewCount: null },
  );
  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback([], null),
    { subscriberCount: null, subscriberCountSource: null, videoCount: null, viewCount: null },
  );
  assert.deepEqual(
    mergeYoutubeMetricsWithManualFallback(
      [
        { metric_key: "subscriber_count", metric_value: 0 },
        { metric_type: "video_count", metric_value: 42 },
        { metric_type: "view_count", metric_value: 99000 },
      ],
      { youtube_subscriber_count: 77 },
    ),
    { subscriberCount: 0, subscriberCountSource: "api", videoCount: 42, viewCount: 99000 },
  );

  const {
    resolveYoutubeChannel,
    shapeYoutubeChannel,
  } = await import("../../api/_lib/youtube.js");

  const mockChannel = {
    id: "UC_x5XG1OV2P6uZZ5FSM9Ttw",
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
    providerAccountId: "UC_x5XG1OV2P6uZZ5FSM9Ttw",
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

  assert.equal(
    shapeYoutubeChannel(
      {
        ...mockChannel,
        statistics: { ...mockChannel.statistics, hiddenSubscriberCount: true },
      },
      "https://www.youtube.com/@camp-test",
    ).metrics.subscriber_count,
    null,
  );

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
    youtubeUrl: "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw",
    apiKey: "test-key",
    fetchImpl: mockFetch,
  });

  assert.equal(resolved.providerAccountId, "UC_x5XG1OV2P6uZZ5FSM9Ttw");
  assert.equal(resolved.metrics.subscriber_count, 1200);
  assert.ok(calls[0].includes("part=snippet%2Cstatistics"));
  assert.ok(calls[0].includes("id=UC_x5XG1OV2P6uZZ5FSM9Ttw"));

  const {
    buildConnectionRow,
    buildMetricRows,
    buildProfileUpdate,
    readBearerToken,
    readJsonBody,
  } = await import("../../api/social/youtube-sync.js");

  assert.equal(readBearerToken({ headers: { authorization: "Bearer abc" } }), "abc");
  assert.equal(readBearerToken({ headers: { Authorization: "Bearer abc" } }), "abc");
  assert.equal(readBearerToken({ headers: {} }), "");
  assert.deepEqual(await readJsonBody({ body: { youtubeUrl: "@camp-test" } }), { youtubeUrl: "@camp-test" });
  assert.deepEqual(await readJsonBody({ body: "{\"youtubeUrl\":\"@camp-test\"}" }), { youtubeUrl: "@camp-test" });
  assert.deepEqual(
    await readJsonBody({ body: Buffer.from("{\"youtubeUrl\":\"@camp-test\"}") }),
    { youtubeUrl: "@camp-test" },
  );

  assert.deepEqual(
    buildConnectionRow({
      userId: "user-1",
      youtube: resolved,
      now: "2026-05-15T00:00:00.000Z",
    }),
    {
      user_id: "user-1",
      provider: "youtube",
      provider_account_id: "UC_x5XG1OV2P6uZZ5FSM9Ttw",
      url: "https://www.youtube.com/@camp-test",
      display_name: "Camp Test",
      handle: "camp-test",
      status: "connected",
      sync_status: "synced",
      last_synced_at: "2026-05-15T00:00:00.000Z",
      last_sync_error: null,
    },
  );

  assert.deepEqual(
    buildMetricRows({
      connectionId: "connection-1",
      userId: "user-1",
      youtube: resolved,
      now: "2026-05-15T00:00:00.000Z",
    }),
    [
      {
        connection_id: "connection-1",
        user_id: "user-1",
        provider: "youtube",
        metric_type: "subscriber_count",
        metric_value: 1200,
        source: "api",
        captured_at: "2026-05-15T00:00:00.000Z",
      },
      {
        connection_id: "connection-1",
        user_id: "user-1",
        provider: "youtube",
        metric_type: "video_count",
        metric_value: 42,
        source: "api",
        captured_at: "2026-05-15T00:00:00.000Z",
      },
      {
        connection_id: "connection-1",
        user_id: "user-1",
        provider: "youtube",
        metric_type: "view_count",
        metric_value: 99000,
        source: "api",
        captured_at: "2026-05-15T00:00:00.000Z",
      },
    ],
  );

  assert.deepEqual(buildProfileUpdate(resolved), {
    youtube_url: "https://www.youtube.com/@camp-test",
    youtube_subscriber_count: 1200,
  });

  assert.deepEqual(
    buildProfileUpdate({
      ...resolved,
      metrics: { ...resolved.metrics, subscriber_count: null },
    }),
    { youtube_url: "https://www.youtube.com/@camp-test" },
  );
})();
