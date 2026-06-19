import { useMemo, useState } from "react";
import { trackAnalyticsEvent } from "../features/analytics/lib/analytics";
import { supabase } from "../shared/api/supabase";
import { BG_MAP, EMOJI_MAP, PLATFORMS, SUPPORTED_PLATFORMS } from "../shared/config/platforms";

const STATUS_OPTIONS = ["지원 페이지 열림", "지원완료", "선정", "리뷰 작성중", "완료", "미선정"];
const SELECTED_STATUSES = ["선정", "리뷰 작성중", "완료"];
const ACTIVE_STATUSES = ["지원 페이지 열림", "지원완료", "심사중", "선정", "리뷰 작성중"];

const STATUS_STYLES = {
  "지원 페이지 열림": { bg: "#F3F4F6", c: "#52525B" },
  지원완료: { bg: "#FEF3C7", c: "#B45309" },
  심사중: { bg: "#FEF3C7", c: "#B45309" },
  선정: { bg: "#D1FAE5", c: "#047857" },
  "리뷰 작성중": { bg: "#DBEAFE", c: "#1D4ED8" },
  완료: { bg: "#F3F4F6", c: "#52525B" },
  미선정: { bg: "#FEE2E2", c: "#B91C1C" },
};

const STATUS_STEPS = {
  "지원 페이지 열림": [2, 0, 0, 0],
  지원완료: [1, 2, 0, 0],
  심사중: [1, 2, 0, 0],
  선정: [1, 1, 2, 0],
  "리뷰 작성중": [1, 1, 1, 2],
  완료: [1, 1, 1, 1],
  미선정: [1, 1, 3, 0],
};

const STATUS_ACTION_COPY = {
  "지원 페이지 열림": "실제로 지원을 마쳤다면 지원완료로 바꾸세요.",
  지원완료: "발표 결과를 확인하고 선정 여부를 기록하세요.",
  심사중: "발표 결과를 확인하고 선정 여부를 기록하세요.",
  선정: "방문/체험 일정과 리뷰 작성 계획을 메모하세요.",
  "리뷰 작성중": "리뷰 URL을 저장하고 완료 처리하세요.",
  완료: "완료된 지원 기록입니다.",
  미선정: "미선정된 기록입니다. 다음 후보를 찾으세요.",
};

function normalizeStatus(status) {
  return STATUS_STYLES[status] ? status : "지원완료";
}

function normalizeUrl(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return text;
  return `https://${text}`;
}

function formatDate(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "-";
  return date.toLocaleDateString("ko-KR");
}

function getFreshCampaign(application, campaigns) {
  return campaigns.find((campaign) => campaign.id === application.campaign_id) || null;
}

function getNumericDDay(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function getEffectiveDDay(application, campaign) {
  return getNumericDDay(campaign?.dDay ?? application.d_day);
}

function getDDayLabel(dDay) {
  if (dDay === null) return "마감일 미정";
  if (dDay < 0) return "마감";
  if (dDay === 0) return "오늘 마감";
  if (dDay === 1) return "내일 마감";
  return `D-${dDay}`;
}

function getNextAction(application, dDay) {
  const status = normalizeStatus(application.status);
  if (status === "지원 페이지 열림") return "지원 여부 확인";
  if (status === "선정") return application.memo ? "리뷰 준비" : "일정/조건 메모";
  if (status === "리뷰 작성중") return application.review_url ? "완료 처리" : "리뷰 URL 저장";
  if (["지원완료", "심사중"].includes(status) && dDay !== null && dDay <= 1) return "마감 전 결과 확인";
  if (["지원완료", "심사중"].includes(status)) return "발표 결과 확인";
  return STATUS_ACTION_COPY[status] || "상태 확인";
}

function buildApplicationAnalyticsPayload(application, campaign, metadata = {}) {
  return {
    campaignId: application.campaign_id,
    platformId: application.platform_id || campaign?.platformId,
    category: application.category || campaign?.category,
    region: campaign?.province || campaign?.region,
    city: campaign?.city,
    metadata: {
      status: normalizeStatus(application.status),
      dDay: getEffectiveDDay(application, campaign),
      hasMemo: Boolean(String(application.memo || "").trim()),
      hasReviewUrl: Boolean(String(application.review_url || "").trim()),
      ...metadata,
    },
  };
}

function buildFocusItems(applications, campaigns) {
  return applications
    .map((application) => {
      const campaign = getFreshCampaign(application, campaigns);
      const dDay = getEffectiveDDay(application, campaign);
      const status = normalizeStatus(application.status);
      const priority = status === "지원 페이지 열림"
        ? 1
        : status === "리뷰 작성중"
          ? 2
          : status === "선정"
            ? 3
            : dDay !== null && dDay <= 1 && ACTIVE_STATUSES.includes(status)
              ? 4
              : 9;
      return { application, campaign, dDay, status, priority };
    })
    .filter((item) => item.priority < 9)
    .sort((left, right) =>
      left.priority - right.priority
      || (left.dDay ?? 999) - (right.dDay ?? 999)
      || String(left.application.campaign_title).localeCompare(String(right.application.campaign_title)),
    )
    .slice(0, 5);
}

function ApplicationCard({
  application,
  campaigns,
  onSelect,
  onStatusChange,
  onSaveMeta,
  saving,
}) {
  const campaign = getFreshCampaign(application, campaigns);
  const status = normalizeStatus(application.status);
  const dDay = getEffectiveDDay(application, campaign);
  const [memo, setMemo] = useState(application.memo || "");
  const [reviewUrl, setReviewUrl] = useState(application.review_url || "");
  const style = STATUS_STYLES[status] || STATUS_STYLES.지원완료;

  return (
    <article className="application-card">
      <div className="application-top">
        <div className="application-title-block">
          <div className="status-title">{application.campaign_title}</div>
          <div className="status-meta">
            {application.platform || "플랫폼"} · {application.category || "카테고리"} · {formatDate(application.applied_at)}
          </div>
        </div>
        <span className="status-pill" style={{ background: style.bg, color: style.c }}>
          {status}
        </span>
      </div>

      <div className="application-signal-row">
        <div>
          <span>마감</span>
          <strong>{getDDayLabel(dDay)}</strong>
        </div>
        <div>
          <span>다음 액션</span>
          <strong>{getNextAction(application, dDay)}</strong>
        </div>
      </div>

      <div className="step-track" aria-label={`${application.campaign_title} 진행 단계`}>
        {(STATUS_STEPS[status] || STATUS_STEPS.지원완료).map((step, index) => (
          <div
            key={`${application.id}-${index}`}
            className={`step-dot step-${step}`}
            style={{ width: `${100 / 4}%` }}
          />
        ))}
      </div>

      <div className="status-actions" aria-label="지원 상태 변경">
        {STATUS_OPTIONS.map((nextStatus) => (
          <button
            key={nextStatus}
            type="button"
            className={`mini-chip ${status === nextStatus ? "active" : ""}`}
            onClick={() => onStatusChange(application, nextStatus)}
          >
            {nextStatus}
          </button>
        ))}
      </div>

      <div className="application-notes">
        <label>
          <span>메모</span>
          <textarea
            value={memo}
            onChange={(event) => setMemo(event.target.value)}
            rows={3}
            placeholder="방문 일정, 제공 조건, 발표일 등을 적어두세요."
          />
        </label>
        <label>
          <span>리뷰 URL</span>
          <input
            value={reviewUrl}
            onChange={(event) => setReviewUrl(event.target.value)}
            placeholder="블로그/인스타 리뷰 링크"
          />
        </label>
      </div>

      <div className="application-footer">
        <button
          type="button"
          className="mini-link"
          onClick={() => onSaveMeta(application, { memo, review_url: normalizeUrl(reviewUrl) })}
          disabled={saving}
        >
          {saving ? "저장 중" : "메모 저장"}
        </button>
        {campaign && (
          <button type="button" className="mini-link" onClick={() => onSelect(campaign)}>
            상세 보기
          </button>
        )}
        {application.campaign_url ? (
          <button type="button" className="mini-link" onClick={() => window.open(application.campaign_url, "_blank", "noopener,noreferrer")}>
            원문 보기
          </button>
        ) : null}
      </div>
    </article>
  );
}

function StatusPage({
  user,
  favorites,
  applications,
  campaigns,
  onFav,
  onSelect,
  onAuthOpen,
  onExplore,
  loadApplications,
  showToast,
}) {
  const [activeTab, setActiveTab] = useState("지원현황");
  const [savingId, setSavingId] = useState("");

  const stats = useMemo(() => {
    const selected = applications.filter((application) => SELECTED_STATUSES.includes(normalizeStatus(application.status))).length;
    const waitingConfirmation = applications.filter((application) => normalizeStatus(application.status) === "지원 페이지 열림").length;
    const writing = applications.filter((application) => normalizeStatus(application.status) === "리뷰 작성중").length;
    const done = applications.filter((application) => normalizeStatus(application.status) === "완료").length;
    const active = applications.filter((application) => ACTIVE_STATUSES.includes(normalizeStatus(application.status))).length;

    return {
      total: applications.length,
      active,
      waitingConfirmation,
      selected,
      writing,
      done,
      selectionRate: applications.length > 0 ? Math.round((selected / applications.length) * 100) : 0,
    };
  }, [applications]);

  const focusItems = useMemo(() => buildFocusItems(applications, campaigns), [applications, campaigns]);

  if (!user) {
    return (
      <div className="page">
        <div className="page-title">현황</div>
        <div className="login-prompt">
          <div className="login-prompt-icon">S</div>
          <div className="login-prompt-title">로그인이 필요합니다</div>
          <div className="login-prompt-sub">로그인하면 즐겨찾기와 지원 현황을 같은 계정으로 이어서 볼 수 있습니다.</div>
          <button className="login-prompt-btn" onClick={onAuthOpen}>로그인 / 회원가입</button>
        </div>
      </div>
    );
  }

  async function updateStatus(application, status) {
    const now = new Date().toISOString();
    const campaign = getFreshCampaign(application, campaigns);
    const previousStatus = normalizeStatus(application.status);
    const payload = { status };

    if (SELECTED_STATUSES.includes(status) && !application.selected_at) {
      payload.selected_at = now;
    }
    if (status === "완료") {
      payload.completed_at = application.completed_at || now;
    }
    if (status !== "완료" && application.completed_at) {
      payload.completed_at = null;
    }

    setSavingId(application.id);
    const { error } = await supabase.from("applications").update(payload).eq("id", application.id);
    setSavingId("");

    if (error) {
      showToast?.(error.message || "상태 변경에 실패했습니다.", "error");
      return;
    }
    if (previousStatus !== status) {
      trackAnalyticsEvent("application_status_update", buildApplicationAnalyticsPayload(application, campaign, {
        previousStatus,
        nextStatus: status,
        selectedAtSet: Boolean(payload.selected_at),
        completedAtSet: status === "완료",
      }), user);
    }
    await loadApplications();
    showToast?.("지원 상태를 저장했습니다.");
  }

  async function saveApplicationMeta(application, nextValues) {
    const campaign = getFreshCampaign(application, campaigns);
    const previousMemo = String(application.memo || "").trim();
    const nextMemo = String(nextValues.memo || "").trim();
    const previousReviewUrl = String(application.review_url || "").trim();
    const nextReviewUrl = String(nextValues.review_url || "").trim();

    setSavingId(application.id);
    const { error } = await supabase
      .from("applications")
      .update({
        memo: nextMemo,
        review_url: nextReviewUrl || null,
      })
      .eq("id", application.id);
    setSavingId("");

    if (error) {
      showToast?.(error.message || "메모 저장에 실패했습니다.", "error");
      return;
    }
    if (previousMemo !== nextMemo) {
      trackAnalyticsEvent("application_memo_update", buildApplicationAnalyticsPayload(application, campaign, {
        previousMemoLength: Math.min(previousMemo.length, 1000),
        nextMemoLength: Math.min(nextMemo.length, 1000),
        nextHasMemo: Boolean(nextMemo),
      }), user);
    }
    if (previousReviewUrl !== nextReviewUrl) {
      trackAnalyticsEvent("application_review_url_update", buildApplicationAnalyticsPayload(application, campaign, {
        previousHasReviewUrl: Boolean(previousReviewUrl),
        nextHasReviewUrl: Boolean(nextReviewUrl),
      }), user);
    }
    await loadApplications();
    showToast?.("메모를 저장했습니다.");
  }

  return (
    <div className="page">
      <section className="status-hero">
        <div>
          <div className="command-eyebrow">Activity Board</div>
          <div className="page-title command-title">지원 현황</div>
          <div className="page-sub command-sub">지원 페이지를 연 기록과 실제 지원 상태를 분리하고, 리뷰까지 이어지는 다음 액션을 관리합니다.</div>
        </div>
        <div className="status-hero-side">
          <div className="status-hero-card">
            <span>진행 중</span>
            <strong>{stats.active}</strong>
          </div>
          <div className="status-hero-card">
            <span>확인 필요</span>
            <strong>{stats.waitingConfirmation}</strong>
          </div>
        </div>
      </section>

      <div className="status-command-panel">
        <div>
          <div className="status-panel-title">오늘 볼 것</div>
          <div className="status-panel-sub">확인 필요, 선정, 리뷰 작성 중인 항목을 우선 보여줍니다.</div>
        </div>
        {focusItems.length === 0 ? (
          <div className="status-focus-empty">지금 바로 처리할 항목이 없습니다.</div>
        ) : (
          <div className="status-focus-list">
            {focusItems.map(({ application, dDay }) => (
              <button key={application.id} type="button" className="status-focus-item" onClick={() => setActiveTab("지원현황")}>
                <span>{getNextAction(application, dDay)}</span>
                <strong>{application.campaign_title}</strong>
                <em>{getDDayLabel(dDay)}</em>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="tab-bar">
        {["지원현황", "즐겨찾기", "분석"].map((tab) => (
          <button key={tab} type="button" className={`chip ${activeTab === tab ? "active" : ""}`} onClick={() => setActiveTab(tab)}>
            {tab === "즐겨찾기" ? `즐겨찾기 (${favorites.length})` : tab}
          </button>
        ))}
      </div>

      {activeTab === "지원현황" && (
        <>
          <div className="stats-grid status-stats-grid">
            {[
              [stats.total, "전체 기록", "#111111"],
              [stats.waitingConfirmation, "지원 확인 필요", "#B45309"],
              [stats.writing, "리뷰 작성중", "#1D4ED8"],
              [`${stats.selectionRate}%`, "선정률", "#047857"],
            ].map(([value, label, color]) => (
              <div key={label} className="stat-box">
                <div className="stat-num" style={{ color }}>{value}</div>
                <div className="stat-label">{label}</div>
              </div>
            ))}
          </div>

          {applications.length === 0 ? (
            <div className="empty">
              <div className="empty-text">아직 관리 중인 캠페인이 없습니다.</div>
              <div className="empty-sub">캠페인 신청 버튼을 누르면 이곳에 기록되고, 실제 지원 여부를 직접 확정할 수 있습니다.</div>
              <button type="button" className="login-prompt-btn" onClick={onExplore}>캠페인 찾기</button>
            </div>
          ) : (
            <div className="application-list">
              {applications.map((application) => (
                <ApplicationCard
                  key={application.id}
                  application={application}
                  campaigns={campaigns}
                  onSelect={onSelect}
                  onStatusChange={updateStatus}
                  onSaveMeta={saveApplicationMeta}
                  saving={savingId === application.id}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === "즐겨찾기" && (
        <>
          {favorites.length === 0 ? (
            <div className="empty">
              <div className="empty-text">즐겨찾기한 캠페인이 없습니다.</div>
              <div className="empty-sub">마음에 드는 공고를 저장해두고 나중에 비교해보세요.</div>
              <button type="button" className="login-prompt-btn" onClick={onExplore}>캠페인 찾기</button>
            </div>
          ) : (
            <div className="fav-grid">
              {favorites.map((favorite) => {
                const campaign = campaigns.find((item) => item.id === favorite.campaign_id);
                const platform = PLATFORMS.find((item) => item.id === favorite.platform_id);
                return (
                  <div key={favorite.id} className="fav-card" onClick={() => campaign && onSelect(campaign)}>
                    <div className="fav-thumb" style={{ background: BG_MAP[favorite.category] || "#F6F0EA" }}>
                      {EMOJI_MAP[favorite.category] || "G"}
                    </div>
                    <div className="fav-copy">
                      <div className="fav-title">{favorite.campaign_title}</div>
                      <div className="fav-meta">{platform?.name || favorite.platform} · {getDDayLabel(getNumericDDay(favorite.d_day))}</div>
                    </div>
                    <button
                      type="button"
                      className="fav-remove"
                      onClick={(event) => {
                        event.stopPropagation();
                        campaign && onFav(campaign);
                      }}
                    >
                      저장 해제
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {activeTab === "분석" && (
        <div className="status-analytics-grid">
          <div className="chart-card">
            <div className="status-panel-title">플랫폼별 선정률</div>
            {SUPPORTED_PLATFORMS.map((platform) => {
              const total = applications.filter((application) => application.platform_id === platform.id).length;
              const selected = applications.filter(
                (application) => application.platform_id === platform.id && SELECTED_STATUSES.includes(normalizeStatus(application.status)),
              ).length;
              const rate = total > 0 ? Math.round((selected / total) * 100) : 0;

              return (
                <div key={platform.id} className="bar-item">
                  <div className="bar-label">
                    <span>{platform.name}</span>
                    <strong>{rate}%</strong>
                  </div>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${rate}%`, background: platform.color }} /></div>
                </div>
              );
            })}
          </div>

          <div className="chart-card">
            <div className="status-panel-title">한눈에 보기</div>
            <div className="status-quick-grid">
              <div className="stat-box">
                <div className="stat-num">{favorites.length}</div>
                <div className="stat-label">저장한 공고</div>
              </div>
              <div className="stat-box">
                <div className="stat-num">{stats.done}</div>
                <div className="stat-label">완료</div>
              </div>
              <div className="stat-box">
                <div className="stat-num">{stats.selectionRate}%</div>
                <div className="stat-label">전체 선정률</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default StatusPage;
