import { useMemo } from "react";
import MonetizedAdSlot from "../features/ads/components/MonetizedAdSlot";
import CampaignCard from "../features/campaigns/components/CampaignCard";
import {
  getCampaignRewardValue,
  getCampaignScoreProfile,
  getPlatformDiverseCampaigns,
  isFreshDeadlineCampaign,
  isVisitFocusedCampaign,
} from "../features/campaigns/lib/campaigns";
import { BG_MAP, CATEGORIES } from "../shared/config/platforms";

const HOME_SECTION_LIMIT = 5;
const ALL_LABEL = "전체";
const CATEGORY_DISCOVERY_LIMIT = 6;
const REGION_DISCOVERY_LIMIT = 6;
const REGION_DISCOVERY_ORDER = ["서울", "경기", "인천", "부산", "대구", "대전", "광주", "울산", "제주"];

function getCompetitionRatio(campaign) {
  return Number(campaign.applyCount || 0) / Number(campaign.selectedCount || 1);
}

function getLatestTimestamp(campaign) {
  return Date.parse(
    campaign?.sourceStartedAt
    || campaign?.sourcePostedAt
    || campaign?.firstSeenAt
    || campaign?.crawledAt
    || "",
  ) || 0;
}

function formatCount(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function buildRankedDiscoveryItems(campaigns, preferredItems, selector, limit, excludedItems = []) {
  const excluded = new Set(excludedItems);
  const counts = new Map();

  campaigns.forEach((campaign) => {
    const label = selector(campaign);
    if (!label || excluded.has(label)) return;
    counts.set(label, (counts.get(label) || 0) + 1);
  });

  const preferredSet = new Set(preferredItems);
  const preferred = preferredItems
    .filter((label) => counts.has(label))
    .map((label) => ({ label, count: counts.get(label) }));
  const rest = [...counts.entries()]
    .filter(([label]) => !preferredSet.has(label))
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "ko"))
    .map(([label, count]) => ({ label, count }));

  return [...preferred, ...rest].slice(0, limit);
}

function compareCampaignId(left, right) {
  return String(left.id).localeCompare(String(right.id), undefined, { numeric: true });
}

function collectRankedCampaigns(campaigns, predicate, compare, limit, excludedIds = new Set()) {
  const poolLimit = Math.max(limit, limit * 5);
  const selected = [];

  campaigns.forEach((campaign) => {
    if (excludedIds.has(campaign.id) || !predicate(campaign)) return;

    if (selected.length < poolLimit) {
      selected.push(campaign);
      selected.sort(compare);
      return;
    }

    if (compare(campaign, selected[selected.length - 1]) < 0) {
      selected[selected.length - 1] = campaign;
      selected.sort(compare);
    }
  });

  return getPlatformDiverseCampaigns(selected, limit);
}

function compareDeadlineCampaign(left, right) {
  return (
    getCampaignScoreProfile(right).score - getCampaignScoreProfile(left).score
    || getCompetitionRatio(left) - getCompetitionRatio(right)
    || compareCampaignId(left, right)
  );
}

function compareLowCompetitionCampaign(left, right) {
  return (
    getCompetitionRatio(left) - getCompetitionRatio(right)
    || (left.dDay ?? 99) - (right.dDay ?? 99)
    || compareCampaignId(left, right)
  );
}

function compareLatestCampaign(left, right) {
  return (
    getLatestTimestamp(right) - getLatestTimestamp(left)
    || (left.dDay ?? 99) - (right.dDay ?? 99)
    || compareCampaignId(left, right)
  );
}

function compareManySelectedCampaign(left, right) {
  return (
    Number(right.selectedCount || 0) - Number(left.selectedCount || 0)
    || getCompetitionRatio(left) - getCompetitionRatio(right)
    || compareCampaignId(left, right)
  );
}

function compareFoodCafeCampaign(left, right) {
  return (
    getCampaignScoreProfile(right).score - getCampaignScoreProfile(left).score
    || getCampaignRewardValue(right) - getCampaignRewardValue(left)
    || getCompetitionRatio(left) - getCompetitionRatio(right)
    || compareCampaignId(left, right)
  );
}

function CampaignSection({
  kicker,
  sectionKey,
  title,
  countLabel,
  campaigns,
  onSelect,
  favIds,
  onFav,
  onApply,
  onImpression,
  onViewAll,
}) {
  if (!campaigns.length) return null;

  return (
    <section className="platform-preview-section">
      <div className="platform-preview-header">
        <div>
          <span className="platform-preview-kicker">{kicker}</span>
          <strong>{title}</strong>
        </div>
        <div className="platform-preview-header-action">
          <span className="platform-preview-count">{countLabel}</span>
          {onViewAll && (
            <button type="button" className="home-view-all-btn" onClick={onViewAll}>
              전체보기
            </button>
          )}
        </div>
      </div>
      <div className="campaign-list">
        {campaigns.map((campaign, index) => (
          <CampaignCard
            key={campaign.id}
            c={campaign}
            onSelect={onSelect}
            isFav={favIds.has(campaign.id)}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            impressionContext={{
              page: "home",
              section: sectionKey || kicker,
              position: index + 1,
              slotId: `home_${sectionKey || "section"}`,
            }}
          />
        ))}
      </div>
    </section>
  );
}

function HomeDiscoveryPanel({ categoryItems, regionItems, totalCount, onExplore }) {
  if (!onExplore || (!categoryItems.length && !regionItems.length)) return null;

  return (
    <section className="home-discovery-panel">
      <div className="home-discovery-header">
        <div>
          <span className="platform-preview-kicker">Start Exploring</span>
          <strong>카테고리나 지역을 누르면 전체 목록으로 이어집니다</strong>
        </div>
        <button type="button" className="home-discovery-all" onClick={() => onExplore()}>
          전체 캠페인
          <span>{formatCount(totalCount)}개</span>
        </button>
      </div>

      {categoryItems.length > 0 && (
        <div className="home-discovery-block">
          <div className="home-discovery-label">카테고리 전체보기</div>
          <div className="home-discovery-grid">
            {categoryItems.map((item) => (
              <button
                key={item.label}
                type="button"
                className="home-discovery-button"
                onClick={() => onExplore({ category: item.label, sortBy: "platform" })}
              >
                <span
                  className="home-discovery-swatch"
                  style={{ background: BG_MAP[item.label] || "#F4F4F5" }}
                  aria-hidden="true"
                />
                <span className="home-discovery-text">
                  <strong>{item.label}</strong>
                  <small>전체보기</small>
                </span>
                <span className="home-discovery-count">{formatCount(item.count)}개</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {regionItems.length > 0 && (
        <div className="home-discovery-block">
          <div className="home-discovery-label">지역 전체보기</div>
          <div className="home-discovery-grid">
            {regionItems.map((item) => (
              <button
                key={item.label}
                type="button"
                className="home-discovery-button"
                onClick={() => onExplore({ province: item.label, sortBy: "dDay" })}
              >
                <span className="home-discovery-swatch home-discovery-swatch--region" aria-hidden="true" />
                <span className="home-discovery-text">
                  <strong>{item.label}</strong>
                  <small>마감순 전체보기</small>
                </span>
                <span className="home-discovery-count">{formatCount(item.count)}개</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function SkeletonRow() {
  return (
    <div className="campaign-list-item campaign-list-item--skeleton">
      <div className="campaign-list-main">
        <div className="skeleton" style={{ height: 10, width: 72, borderRadius: 999 }} />
        <div className="skeleton" style={{ height: 18, width: "72%", borderRadius: 8, marginTop: 10 }} />
        <div className="skeleton" style={{ height: 12, width: "56%", borderRadius: 8, marginTop: 12 }} />
      </div>
      <div className="campaign-list-side campaign-list-side--skeleton">
        <div className="skeleton" style={{ height: 22, width: 78, borderRadius: 999 }} />
      </div>
    </div>
  );
}

function HomePage({ campaigns, onSelect, favIds, onFav, onApply, onImpression, loading, onExplore, onOpenMap }) {
  const curatedCampaigns = useMemo(() => {
    const visitCampaigns = campaigns.filter(isVisitFocusedCampaign);
    return visitCampaigns.length ? visitCampaigns : campaigns;
  }, [campaigns]);

  const homeMetrics = useMemo(() => {
    const platformIds = new Set();
    let lowCompetitionCount = 0;
    let freshDeadlineCount = 0;
    let manySelectedCount = 0;
    let foodCafeCount = 0;

    curatedCampaigns.forEach((campaign) => {
      if (getCompetitionRatio(campaign) < 30) lowCompetitionCount += 1;
      if (isFreshDeadlineCampaign(campaign)) freshDeadlineCount += 1;
      if (Number(campaign.selectedCount || 0) >= 5) manySelectedCount += 1;
      if (["맛집", "카페"].includes(campaign.category)) foodCafeCount += 1;
      if (campaign.platformId || campaign.platform) platformIds.add(campaign.platformId || campaign.platform);
    });

    return {
      lowCompetitionCount,
      freshDeadlineCount,
      manySelectedCount,
      foodCafeCount,
      platformCount: platformIds.size,
    };
  }, [curatedCampaigns]);

  const deadlineCampaigns = useMemo(() => collectRankedCampaigns(
    curatedCampaigns,
    (campaign) => isFreshDeadlineCampaign(campaign),
    compareDeadlineCampaign,
    HOME_SECTION_LIMIT,
  ), [curatedCampaigns]);

  const deadlineIds = useMemo(() => new Set(deadlineCampaigns.map((campaign) => campaign.id)), [deadlineCampaigns]);

  const lowCompetitionCampaigns = useMemo(() => collectRankedCampaigns(
    curatedCampaigns,
    (campaign) => getCompetitionRatio(campaign) < 30,
    compareLowCompetitionCampaign,
    HOME_SECTION_LIMIT,
    deadlineIds,
  ), [curatedCampaigns, deadlineIds]);

  const firstHighlightedIds = useMemo(() => new Set([
    ...deadlineCampaigns.map((campaign) => campaign.id),
    ...lowCompetitionCampaigns.map((campaign) => campaign.id),
  ]), [deadlineCampaigns, lowCompetitionCampaigns]);

  const latestCampaigns = useMemo(() => collectRankedCampaigns(
    curatedCampaigns,
    () => true,
    compareLatestCampaign,
    HOME_SECTION_LIMIT,
    firstHighlightedIds,
  ), [curatedCampaigns, firstHighlightedIds]);

  const secondHighlightedIds = useMemo(() => new Set([
    ...firstHighlightedIds,
    ...latestCampaigns.map((campaign) => campaign.id),
  ]), [firstHighlightedIds, latestCampaigns]);

  const manySelectedCampaigns = useMemo(() => collectRankedCampaigns(
    curatedCampaigns,
    (campaign) => Number(campaign.selectedCount || 0) >= 5,
    compareManySelectedCampaign,
    HOME_SECTION_LIMIT,
    secondHighlightedIds,
  ), [curatedCampaigns, secondHighlightedIds]);

  const thirdHighlightedIds = useMemo(() => new Set([
    ...secondHighlightedIds,
    ...manySelectedCampaigns.map((campaign) => campaign.id),
  ]), [manySelectedCampaigns, secondHighlightedIds]);

  const foodCafeCampaigns = useMemo(() => collectRankedCampaigns(
    curatedCampaigns,
    (campaign) => ["맛집", "카페"].includes(campaign.category),
    compareFoodCafeCampaign,
    HOME_SECTION_LIMIT,
    thirdHighlightedIds,
  ), [curatedCampaigns, thirdHighlightedIds]);

  const categoryDiscoveryItems = useMemo(() => buildRankedDiscoveryItems(
    curatedCampaigns,
    CATEGORIES.filter((item) => item !== ALL_LABEL && item !== "기타"),
    (campaign) => campaign.category,
    CATEGORY_DISCOVERY_LIMIT,
    [ALL_LABEL, "기타"],
  ), [curatedCampaigns]);
  const regionDiscoveryItems = useMemo(() => buildRankedDiscoveryItems(
    curatedCampaigns,
    REGION_DISCOVERY_ORDER,
    (campaign) => campaign.province,
    REGION_DISCOVERY_LIMIT,
    [ALL_LABEL, "지역 미정", "전국"],
  ), [curatedCampaigns]);
  const hasCampaigns = curatedCampaigns.length > 0;

  return (
    <div className="page page--simple">
      <section className="simple-hero">
        <div className="simple-hero-copy">
          <div className="command-eyebrow">Campaign Feed</div>
          <h1 className="simple-hero-title">여러 체험단 사이트를 카테고리별로 모아봅니다</h1>
          <p className="simple-hero-sub">
            카테고리 안에서 특정 사이트 공고가 한쪽으로 몰리지 않게 섞어 보여줍니다.
            마감, 경쟁률, 지도는 보조 정보로 두고 여러 플랫폼을 한 번에 비교하는 데 집중합니다.
          </p>
          {(onExplore || onOpenMap) && (
            <div className="simple-hero-actions">
              {onExplore && (
                <button type="button" className="simple-hero-btn simple-hero-btn--primary" onClick={() => onExplore()}>
                  전체 캠페인 보기
                </button>
              )}
              {onOpenMap && (
                <button type="button" className="simple-hero-btn" onClick={onOpenMap}>
                  지도에서 보기
                </button>
              )}
            </div>
          )}
        </div>
        <div className="simple-hero-meta">
          <div className="simple-hero-metric">
            <strong>{formatCount(curatedCampaigns.length)}</strong>
            <span>방문형 캠페인</span>
          </div>
          <div className="simple-hero-metric">
            <strong>{homeMetrics.platformCount}</strong>
            <span>통합 플랫폼</span>
          </div>
        </div>
      </section>

      <MonetizedAdSlot slotId="home_top" context={{ page: "home" }} />

      {!loading && hasCampaigns && (
        <HomeDiscoveryPanel
          categoryItems={categoryDiscoveryItems}
          regionItems={regionDiscoveryItems}
          totalCount={curatedCampaigns.length}
          onExplore={onExplore}
        />
      )}

      {loading && (
        <div className="campaign-list">
          {Array.from({ length: 7 }).map((_, index) => <SkeletonRow key={index} />)}
        </div>
      )}

      {!loading && !hasCampaigns && (
        <div className="empty empty--simple">
          <div className="empty-text">표시할 캠페인이 없습니다.</div>
          <div className="empty-sub">크롤링 데이터가 준비되면 방문형 캠페인 후보가 표시됩니다.</div>
        </div>
      )}

      {!loading && hasCampaigns && (
        <div className="platform-preview-list">
          <CampaignSection
            kicker="Verified Deadline"
            sectionKey="deadline"
            title="최근 확인된 오늘·내일 마감"
            countLabel={`${deadlineCampaigns.length}/${homeMetrics.freshDeadlineCount}개`}
            campaigns={deadlineCampaigns}
            onSelect={onSelect}
            favIds={favIds}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            onViewAll={() => onExplore?.({ preset: "deadline", sortBy: "dDay" })}
          />
          <CampaignSection
            kicker="Low Competition"
            sectionKey="low_competition"
            title="경쟁 낮은 방문 캠페인"
            countLabel={`${lowCompetitionCampaigns.length}/${homeMetrics.lowCompetitionCount}개`}
            campaigns={lowCompetitionCampaigns}
            onSelect={onSelect}
            favIds={favIds}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            onViewAll={() => onExplore?.({ preset: "lowCompetition", sortBy: "comp" })}
          />
          <CampaignSection
            kicker="Newly Found"
            sectionKey="newly_found"
            title="새로 올라온 방문 캠페인"
            countLabel={`${latestCampaigns.length}/${curatedCampaigns.length}개`}
            campaigns={latestCampaigns}
            onSelect={onSelect}
            favIds={favIds}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            onViewAll={() => onExplore?.({ sortBy: "latest" })}
          />
          <CampaignSection
            kicker="Large Pool"
            sectionKey="large_pool"
            title="선정 인원 많은 캠페인"
            countLabel={`${manySelectedCampaigns.length}/${homeMetrics.manySelectedCount}개`}
            campaigns={manySelectedCampaigns}
            onSelect={onSelect}
            favIds={favIds}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            onViewAll={() => onExplore?.({ preset: "selectedMany", sortBy: "selected" })}
          />
          <CampaignSection
            kicker="Food & Cafe"
            sectionKey="food_cafe"
            title="맛집/카페 빠른 신청"
            countLabel={`${foodCafeCampaigns.length}/${homeMetrics.foodCafeCount}개`}
            campaigns={foodCafeCampaigns}
            onSelect={onSelect}
            favIds={favIds}
            onFav={onFav}
            onApply={onApply}
            onImpression={onImpression}
            onViewAll={() => onExplore?.({ preset: "foodCafe", sortBy: "platform" })}
          />
        </div>
      )}
    </div>
  );
}

export default HomePage;
