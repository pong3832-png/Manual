import { useMemo, useState } from "react";
import { supabase } from "../shared/api/supabase";
import { SUPPORTED_PLATFORMS } from "../shared/config/platforms";
import {
  areProfileDraftsEqual,
  buildProfileDraftFromProfile,
  buildProfilePayload,
  formatProfileMetric,
  getProfileDraftValidation,
} from "../features/user/lib/profile";
import useSocialConnections from "../features/social/hooks/useSocialConnections";
import { mergeYoutubeMetricsWithManualFallback } from "../features/social/lib/socialMetrics";
import { formatSocialMetric, parseYoutubeChannelInput } from "../features/social/lib/youtube";

const SELECTED_STATUSES = new Set(["선정", "리뷰 작성중", "완료"]);
const ACTIONABLE_STATUSES = new Set(["지원 페이지 열림", "지원완료", "심사중", "선정", "리뷰 작성중"]);
const EMPTY_METRICS = [];

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function getInitial(profile, user) {
  const source = profile?.name || user?.email || "M";
  return source.trim().slice(0, 1).toUpperCase();
}

function getStatusLabel(status) {
  if (status === "지원 페이지 열림") return "확인 필요";
  if (status === "심사중") return "결과 대기";
  return status || "상태 없음";
}

function ProfileDashboard({
  user,
  profile,
  applications,
  favorites,
  onLogout,
  onExplore,
  onStatus,
  onMap,
  onProfileSaved,
  showToast,
}) {
  const [profileDraft, setProfileDraft] = useState(() => buildProfileDraftFromProfile(profile));
  const [isSaving, setIsSaving] = useState(false);
  const [isSyncingYoutube, setIsSyncingYoutube] = useState(false);
  const {
    connections: socialConnections,
    isLoading: isLoadingSocialConnections,
    loadSocialConnections,
    metricsByConnection,
  } = useSocialConnections(user);
  const savedProfileDraft = useMemo(() => buildProfileDraftFromProfile(profile), [profile]);

  const accountSummary = useMemo(() => {
    const confirmedApplications = applications.filter((application) => application.status !== "지원 페이지 열림");
    const selectedCount = applications.filter((application) => SELECTED_STATUSES.has(application.status)).length;
    const reviewingCount = applications.filter((application) => application.status === "리뷰 작성중").length;
    const activeCount = applications.filter((application) => ACTIONABLE_STATUSES.has(application.status)).length;
    const needConfirmCount = applications.filter((application) => application.status === "지원 페이지 열림").length;
    const completedCount = applications.filter((application) => application.status === "완료").length;
    const selectionRate = confirmedApplications.length > 0
      ? Math.round((selectedCount / confirmedApplications.length) * 100)
      : 0;

    return {
      activeCount,
      completedCount,
      confirmedCount: confirmedApplications.length,
      needConfirmCount,
      reviewingCount,
      selectedCount,
      selectionRate,
    };
  }, [applications]);

  const readinessItems = useMemo(() => ([
    { label: "프로필 이름", done: Boolean(profile?.name || profileDraft.name.trim()) },
    { label: "네이버 블로그", done: Boolean(profile?.blog_url || profileDraft.naverBlogUrl.trim()) },
    { label: "SNS 채널", done: Boolean(profile?.instagram_url || profile?.youtube_url || profileDraft.instagramUrl.trim() || profileDraft.youtubeUrl.trim()) },
    { label: "신청 멘트", done: Boolean(profile?.application_message_template || profileDraft.applicationMessageTemplate.trim()) },
    { label: "관심 캠페인", done: favorites.length > 0 },
    { label: "지원 기록", done: applications.length > 0 },
  ]), [
    applications.length,
    favorites.length,
    profile?.application_message_template,
    profile?.blog_url,
    profile?.instagram_url,
    profile?.name,
    profile?.youtube_url,
    profileDraft.applicationMessageTemplate,
    profileDraft.instagramUrl,
    profileDraft.name,
    profileDraft.naverBlogUrl,
    profileDraft.youtubeUrl,
  ]);

  const readinessScore = Math.round((readinessItems.filter((item) => item.done).length / readinessItems.length) * 100);
  const recentApplications = applications.slice(0, 3);
  const hasProfileChanges = !areProfileDraftsEqual(profileDraft, savedProfileDraft);
  const applicationMessageLength = profileDraft.applicationMessageTemplate.trim().length;
  const youtubeConnection = useMemo(
    () => socialConnections.find((connection) => connection.provider === "youtube") || null,
    [socialConnections],
  );
  const youtubeMetrics = youtubeConnection
    ? metricsByConnection.get(youtubeConnection.id) || EMPTY_METRICS
    : EMPTY_METRICS;
  const youtubeSummary = useMemo(
    () => mergeYoutubeMetricsWithManualFallback(youtubeMetrics, {
      youtube_subscriber_count: profile?.youtube_subscriber_count ?? profileDraft.youtubeSubscriberCount,
    }),
    [profile?.youtube_subscriber_count, profileDraft.youtubeSubscriberCount, youtubeMetrics],
  );
  const youtubeSyncStatusLabel = youtubeConnection?.sync_status === "synced"
    ? "연동됨"
    : "연동 전";
  const youtubeMetricSourceLabel = youtubeSummary.subscriberCountSource === "api"
    ? "YouTube API"
    : youtubeSummary.subscriberCountSource === "manual"
      ? "수동 백업"
      : "미확인";
  const youtubeLastSyncedLabel = youtubeConnection?.last_synced_at
    ? new Date(youtubeConnection.last_synced_at).toLocaleString("ko-KR")
    : "동기화 대기";

  const setDraftField = (field, value) => {
    setProfileDraft((prev) => ({ ...prev, [field]: value }));
  };

  const nextActions = [
    !profile?.blog_url
      ? {
          title: "네이버 블로그 연동",
          detail: "지원용 대표 채널 주소를 먼저 저장합니다.",
          action: "연동",
          onClick: () => document.querySelector(".profile-channel-input")?.focus(),
        }
      : null,
    !profile?.application_message_template
      ? {
          title: "신청 멘트 저장",
          detail: "지원 페이지 이동 시 바로 붙여넣을 문구입니다.",
          action: "작성",
          onClick: () => document.querySelector(".profile-message-textarea")?.focus(),
        }
      : null,
    accountSummary.needConfirmCount > 0
      ? {
          title: "지원 여부 확인",
          detail: `${accountSummary.needConfirmCount}건은 아직 실제 지원완료로 확정되지 않았습니다.`,
          action: "현황",
          onClick: onStatus,
        }
      : null,
    accountSummary.reviewingCount > 0
      ? {
          title: "리뷰 작성 진행",
          detail: `${accountSummary.reviewingCount}건의 리뷰 작업이 진행 중입니다.`,
          action: "현황",
          onClick: onStatus,
        }
      : null,
    favorites.length === 0
      ? {
          title: "관심 캠페인 저장",
          detail: "비교할 캠페인을 먼저 모아두면 지원 결정이 빨라집니다.",
          action: "탐색",
          onClick: onExplore,
        }
      : null,
    applications.length === 0
      ? {
          title: "첫 지원 기록 만들기",
          detail: "탐색에서 캠페인을 열면 마이와 현황에 활동이 쌓입니다.",
          action: "탐색",
          onClick: onExplore,
        }
      : null,
  ].filter(Boolean).slice(0, 3);

  const handleSaveProfile = async () => {
    if (!user || isSaving) return;

    const profilePayload = buildProfilePayload(profileDraft);
    const validation = getProfileDraftValidation(profileDraft);

    if (!profilePayload.name) {
      showToast?.("표시 이름을 입력해 주세요.");
      return;
    }

    if (validation.invalidUrlLabels.length > 0) {
      showToast?.(`${validation.invalidUrlLabels[0]} 주소 형식을 확인해 주세요.`);
      return;
    }

    if (validation.invalidMetricLabels.length > 0) {
      showToast?.(`${validation.invalidMetricLabels[0]}는 0 이상의 숫자로 입력해 주세요.`);
      return;
    }

    setIsSaving(true);
    const { data: updatedProfile, error: updateError } = await supabase
      .from("profiles")
      .update(profilePayload)
      .eq("id", user.id)
      .select("id")
      .maybeSingle();

    const { error: insertError } = !updateError && !updatedProfile
      ? await supabase.from("profiles").insert({
        id: user.id,
        ...profilePayload,
      })
      : { error: null };

    setIsSaving(false);

    const error = updateError || insertError;
    if (error) {
      showToast?.("프로필 저장에 실패했습니다.");
      return;
    }

    await onProfileSaved?.();
    showToast?.("프로필을 저장했습니다.");
  };

  const handleSyncYoutube = async () => {
    if (!user || isSyncingYoutube) return;

    const youtubeUrl = profileDraft.youtubeUrl.trim();
    if (!youtubeUrl) {
      showToast?.("유튜브 채널 주소를 입력해 주세요.");
      return;
    }

    if (!parseYoutubeChannelInput(youtubeUrl)) {
      showToast?.("유튜브 채널 주소 또는 @핸들을 확인해 주세요.");
      return;
    }

    setIsSyncingYoutube(true);

    try {
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      const accessToken = sessionData?.session?.access_token;
      if (sessionError || !accessToken) {
        throw new Error("로그인 세션을 다시 확인해 주세요.");
      }

      const response = await fetch("/api/social/youtube-sync", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ youtubeUrl }),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "유튜브 연동에 실패했습니다.");
      }

      if (payload.connection?.accountUrl) {
        setDraftField("youtubeUrl", payload.connection.accountUrl);
      }

      if (payload.metrics?.subscriberCount !== null && payload.metrics?.subscriberCount !== undefined) {
        setDraftField("youtubeSubscriberCount", formatProfileMetric(payload.metrics.subscriberCount));
      }

      await loadSocialConnections(user.id);
      await onProfileSaved?.();
      showToast?.("유튜브 채널 지표를 연동했습니다.");
    } catch (error) {
      showToast?.(error.message || "유튜브 연동에 실패했습니다.", "error");
    } finally {
      setIsSyncingYoutube(false);
    }
  };

  const handleCopyApplicationMessage = async () => {
    const message = profileDraft.applicationMessageTemplate.trim();

    if (!message) {
      showToast?.("복사할 신청 멘트를 입력해 주세요.");
      return;
    }

    if (!navigator.clipboard?.writeText) {
      showToast?.("현재 브라우저에서 클립보드 복사를 사용할 수 없습니다.", "error");
      return;
    }

    try {
      await navigator.clipboard.writeText(message);
      showToast?.("신청 멘트를 복사했습니다.");
    } catch {
      showToast?.("신청 멘트 복사에 실패했습니다.", "error");
    }
  };

  return (
    <div className="page">
      <section className="profile-hero">
        <div>
          <div className="command-eyebrow">MY</div>
          <div className="page-title command-title">마이</div>
          <div className="page-sub command-sub">계정 상태와 내 활동을 한 화면에서 확인합니다.</div>
        </div>
        <div className="profile-hero-actions">
          <button type="button" className="profile-ghost-btn" onClick={onMap}>지도</button>
          <button type="button" className="profile-ghost-btn" onClick={onStatus}>현황</button>
          <button type="button" className="profile-danger-btn" onClick={onLogout}>로그아웃</button>
        </div>
      </section>

      <section className="profile-account-panel">
        <div className="profile-identity">
          <div className="profile-avatar">{getInitial(profile, user)}</div>
          <div>
            <div className="profile-name">{profile?.name || "사용자"} 님</div>
            <div className="profile-email">{user.email}</div>
            <div className="profile-level">프로필 완성 {readinessScore}%</div>
          </div>
        </div>
        <div className="profile-readiness">
          {readinessItems.map((item) => (
            <span key={item.label} className={`profile-readiness-chip ${item.done ? "done" : ""}`}>
              {item.done ? "완료" : "필요"} · {item.label}
            </span>
          ))}
        </div>
      </section>

      <div className="profile-stats-grid">
        {[
          [applications.length, "전체 기록", "#111111"],
          [accountSummary.activeCount, "진행 중", "#2563EB"],
          [accountSummary.selectedCount, "선정", "#059669"],
          [`${accountSummary.selectionRate}%`, "선정률", "#C1440E"],
        ].map(([value, label, color]) => (
          <div key={label} className="stat-box">
            <div className="stat-num" style={{ fontSize: 20, color }}>{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      <section className="profile-section">
        <div className="profile-section-head">
          <div>
            <div className="profile-section-title">계정 정보</div>
            <div className="profile-section-sub">표시 이름과 저장 상태</div>
          </div>
          <button
            type="button"
            className="profile-primary-btn"
            onClick={handleSaveProfile}
            disabled={!hasProfileChanges || isSaving}
          >
            {isSaving ? "저장 중" : "저장"}
          </button>
        </div>
        <div className="profile-form-grid">
          <label className="profile-field">
            <span>표시 이름</span>
            <input
              className="profile-input"
              value={profileDraft.name}
              onChange={(event) => setDraftField("name", event.target.value)}
              placeholder="표시 이름"
            />
          </label>
        </div>
      </section>

      <section className="profile-section">
        <div className="profile-section-head">
          <div>
            <div className="profile-section-title">채널 연동</div>
            <div className="profile-section-sub">네이버 블로그, 인스타그램, 유튜브</div>
          </div>
          <button
            type="button"
            className="profile-primary-btn"
            onClick={handleSaveProfile}
            disabled={!hasProfileChanges || isSaving}
          >
            {isSaving ? "저장 중" : "저장"}
          </button>
        </div>

        <div className="profile-channel-list">
          <div className="profile-channel-block">
            <div className="profile-channel-head">
              <span className="profile-channel-mark naver">N</span>
              <div>
                <div className="profile-channel-name">네이버 블로그</div>
                <div className="profile-channel-sub">이웃수 · 하루 방문자 · 총 방문자</div>
              </div>
            </div>
            <label className="profile-field">
              <span>블로그 주소</span>
              <input
                className="profile-input profile-channel-input"
                value={profileDraft.naverBlogUrl}
                onChange={(event) => setDraftField("naverBlogUrl", event.target.value)}
                placeholder="https://blog.naver.com/..."
              />
            </label>
            <div className="profile-metric-grid">
              {[
                ["naverBlogNeighborCount", "이웃수"],
                ["naverBlogDailyVisitorCount", "하루 방문자"],
                ["naverBlogTotalVisitorCount", "총 방문자"],
              ].map(([field, label]) => (
                <label key={field} className="profile-field">
                  <span>{label}</span>
                  <input
                    className="profile-input"
                    inputMode="numeric"
                    value={profileDraft[field]}
                    onChange={(event) => setDraftField(field, event.target.value)}
                    onBlur={() => setDraftField(field, formatProfileMetric(profileDraft[field]))}
                    placeholder="0"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="profile-channel-block">
            <div className="profile-channel-head">
              <span className="profile-channel-mark instagram">I</span>
              <div>
                <div className="profile-channel-name">인스타그램</div>
                <div className="profile-channel-sub">프로필 주소와 팔로워 수</div>
              </div>
            </div>
            <div className="profile-form-grid">
              <label className="profile-field">
                <span>인스타그램 주소</span>
                <input
                  className="profile-input"
                  value={profileDraft.instagramUrl}
                  onChange={(event) => setDraftField("instagramUrl", event.target.value)}
                  placeholder="https://instagram.com/..."
                />
              </label>
              <label className="profile-field">
                <span>팔로워 수</span>
                <input
                  className="profile-input"
                  inputMode="numeric"
                  value={profileDraft.instagramFollowerCount}
                  onChange={(event) => setDraftField("instagramFollowerCount", event.target.value)}
                  onBlur={() => setDraftField("instagramFollowerCount", formatProfileMetric(profileDraft.instagramFollowerCount))}
                  placeholder="0"
                />
              </label>
            </div>
          </div>

          <div className="profile-channel-block">
            <div className="profile-channel-head">
              <span className="profile-channel-mark youtube">Y</span>
              <div>
                <div className="profile-channel-name">유튜브</div>
                <div className="profile-channel-sub">채널 주소를 확인해 공개 지표를 가져옵니다</div>
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
              <label className="profile-field">
                <span>구독자 수 {youtubeConnection ? "" : "(수동 백업)"}</span>
                <input
                  className="profile-input"
                  inputMode="numeric"
                  value={profileDraft.youtubeSubscriberCount}
                  onChange={(event) => setDraftField("youtubeSubscriberCount", event.target.value)}
                  onBlur={() => setDraftField("youtubeSubscriberCount", formatProfileMetric(profileDraft.youtubeSubscriberCount))}
                  placeholder="0"
                  readOnly={Boolean(youtubeConnection)}
                />
              </label>
            </div>
            <div className="profile-sync-row">
              <button
                type="button"
                className="profile-secondary-btn profile-sync-btn"
                onClick={handleSyncYoutube}
                disabled={isSyncingYoutube || isSaving || isLoadingSocialConnections}
              >
                {isSyncingYoutube ? "동기화 중" : youtubeConnection ? "다시 동기화" : "연동 확인"}
              </button>
              <span className={`profile-sync-status ${youtubeConnection?.sync_status === "synced" ? "synced" : ""}`}>
                {youtubeSyncStatusLabel}
              </span>
              <span className="profile-sync-meta">{youtubeLastSyncedLabel}</span>
            </div>
            <div className="profile-sync-metrics">
              <span>구독자 <strong>{formatSocialMetric(youtubeSummary.subscriberCount)}</strong></span>
              <span>영상 <strong>{formatSocialMetric(youtubeSummary.videoCount)}</strong></span>
              <span>조회수 <strong>{formatSocialMetric(youtubeSummary.viewCount)}</strong></span>
              <span>출처 <strong>{youtubeMetricSourceLabel}</strong></span>
            </div>
          </div>
        </div>
      </section>

      <section className="profile-section">
        <div className="profile-section-head">
          <div>
            <div className="profile-section-title">신청 멘트</div>
            <div className="profile-section-sub">지원 페이지에서 붙여넣을 문구</div>
          </div>
          <div className="profile-message-actions">
            <button type="button" className="profile-secondary-btn" onClick={handleCopyApplicationMessage}>
              복사
            </button>
            <button
              type="button"
              className="profile-primary-btn"
              onClick={handleSaveProfile}
              disabled={!hasProfileChanges || isSaving}
            >
              {isSaving ? "저장 중" : "저장"}
            </button>
          </div>
        </div>
        <label className="profile-field">
          <span>기본 신청 멘트</span>
          <textarea
            className="profile-input profile-textarea profile-message-textarea"
            value={profileDraft.applicationMessageTemplate}
            onChange={(event) => setDraftField("applicationMessageTemplate", event.target.value)}
            placeholder="안녕하세요. 캠페인 취지에 맞춰 성실하게 체험하고 정성껏 리뷰하겠습니다."
          />
        </label>
        <div className="profile-message-meta">{applicationMessageLength.toLocaleString("ko-KR")}자</div>
      </section>

      <section className="profile-section">
        <div className="profile-section-head">
          <div>
            <div className="profile-section-title">채널 지표</div>
            <div className="profile-section-sub">저장된 공개 지표 요약</div>
          </div>
        </div>
        <div className="profile-channel-summary">
          {[
            ["네이버 이웃", profileDraft.naverBlogNeighborCount],
            ["블로그 하루 방문자", profileDraft.naverBlogDailyVisitorCount],
            ["블로그 총 방문자", profileDraft.naverBlogTotalVisitorCount],
            ["인스타 팔로워", profileDraft.instagramFollowerCount],
            ["유튜브 구독자", formatSocialMetric(youtubeSummary.subscriberCount)],
          ].map(([label, value]) => (
            <div key={label} className="profile-channel-summary-item">
              <span>{label}</span>
              <strong>{value || "-"}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="profile-grid">
        <section className="profile-section">
          <div className="profile-section-head">
            <div>
              <div className="profile-section-title">다음 할 일</div>
              <div className="profile-section-sub">확인 우선순위</div>
            </div>
            <button type="button" className="profile-secondary-btn" onClick={onExplore}>캠페인 찾기</button>
          </div>
          <div className="profile-action-list">
            {nextActions.length > 0 ? nextActions.map((item) => (
              <button key={item.title} type="button" className="profile-action-item" onClick={item.onClick}>
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.detail}</small>
                </span>
                <em>{item.action}</em>
              </button>
            )) : (
              <div className="profile-muted-box">현재 바로 처리할 항목이 없습니다.</div>
            )}
          </div>
        </section>

        <section className="profile-section">
          <div className="profile-section-head">
            <div>
              <div className="profile-section-title">최근 활동</div>
              <div className="profile-section-sub">지원 기록 {applications.length}건</div>
            </div>
            <button type="button" className="profile-secondary-btn" onClick={onStatus}>전체 보기</button>
          </div>
          <div className="profile-activity-list">
            {recentApplications.length > 0 ? recentApplications.map((application) => (
              <div key={application.id} className="profile-activity-item">
                <div>
                  <strong>{application.campaign_title || "캠페인"}</strong>
                  <small>{application.platform || "플랫폼"} · {formatDate(application.applied_at)}</small>
                </div>
                <span>{getStatusLabel(application.status)}</span>
              </div>
            )) : (
              <div className="profile-muted-box">아직 지원 기록이 없습니다.</div>
            )}
          </div>
        </section>
      </div>

      <section className="profile-section">
        <div className="profile-section-head">
          <div>
            <div className="profile-section-title">서비스 범위</div>
            <div className="profile-section-sub">연결 가능한 체험단 플랫폼</div>
          </div>
          <span className="profile-service-count">{SUPPORTED_PLATFORMS.length}개</span>
        </div>
        <div className="profile-service-row">
          <span>즐겨찾기 {favorites.length}개</span>
          <span>확정 지원 {accountSummary.confirmedCount}건</span>
          <span>완료 {accountSummary.completedCount}건</span>
        </div>
      </section>
    </div>
  );
}

function ProfilePage(props) {
  const { user, profile, onAuthOpen } = props;

  if (!user) {
    return (
      <div className="page">
        <div className="page-title">마이</div>
        <div className="login-prompt">
          <div className="login-prompt-icon">M</div>
          <div className="login-prompt-title">로그인이 필요합니다</div>
          <div className="login-prompt-sub">즐겨찾기, 지원 현황, 계정 설정을 같은 계정으로 이어서 볼 수 있습니다.</div>
          <button type="button" className="login-prompt-btn" onClick={onAuthOpen}>로그인 / 회원가입</button>
        </div>
      </div>
    );
  }

  const profileKey = [
    profile?.updated_at || "",
    profile?.name || "",
    profile?.blog_url || "",
    profile?.instagram_url || "",
    profile?.youtube_url || "",
    profile?.application_message_template || "",
  ].join(":");
  return <ProfileDashboard key={profileKey} {...props} />;
}

export default ProfilePage;
