const assert = require("node:assert/strict");

(async () => {
  const {
    areProfileDraftsEqual,
    buildProfileDraftFromProfile,
    buildProfilePayload,
    formatProfileMetric,
    getProfileDraftValidation,
  } = await import("../../src/features/user/lib/profile.js");

  const draft = buildProfileDraftFromProfile({
    name: "  캠프러  ",
    blog_url: "blog.naver.com/camp",
    instagram_url: "https://instagram.com/camp.profile",
    youtube_url: "youtube.com/@camp",
    application_message_template: " 안녕하세요.\n정성껏 리뷰하겠습니다. ",
    naver_blog_neighbor_count: 1200,
    naver_blog_daily_visitor_count: 345,
    naver_blog_total_visitor_count: 456789,
    instagram_follower_count: 3200,
    youtube_subscriber_count: 42,
  });

  assert.equal(draft.name, "  캠프러  ");
  assert.equal(draft.naverBlogUrl, "blog.naver.com/camp");
  assert.equal(draft.naverBlogNeighborCount, "1,200");
  assert.equal(draft.naverBlogTotalVisitorCount, "456,789");

  const payload = buildProfilePayload({
    ...draft,
    name: " 캠프러 ",
    naverBlogUrl: "blog.naver.com/camp",
    instagramUrl: "",
    youtubeUrl: "youtube.com/@camp",
    applicationMessageTemplate: " 안녕하세요.\n정성껏 리뷰하겠습니다. ",
    naverBlogNeighborCount: "1,234",
    naverBlogDailyVisitorCount: "",
    instagramFollowerCount: "3,200",
  });

  assert.deepEqual(payload, {
    name: "캠프러",
    blog_url: "https://blog.naver.com/camp",
    instagram_url: null,
    youtube_url: "https://youtube.com/@camp",
    application_message_template: "안녕하세요.\n정성껏 리뷰하겠습니다.",
    naver_blog_neighbor_count: 1234,
    naver_blog_daily_visitor_count: null,
    naver_blog_total_visitor_count: 456789,
    instagram_follower_count: 3200,
    youtube_subscriber_count: 42,
  });

  assert.equal(formatProfileMetric(1000000), "1,000,000");
  assert.deepEqual(getProfileDraftValidation({ ...draft, instagramUrl: "instagram.com/camp" }), {
    invalidMetricLabels: [],
    invalidUrlLabels: [],
  });
  assert.deepEqual(getProfileDraftValidation({ ...draft, youtubeSubscriberCount: "-1" }), {
    invalidMetricLabels: ["유튜브 구독자"],
    invalidUrlLabels: [],
  });

  const emptyDraft = buildProfileDraftFromProfile({});
  assert.equal(areProfileDraftsEqual({ ...emptyDraft, instagramFollowerCount: "abc" }, emptyDraft), false);
})();
