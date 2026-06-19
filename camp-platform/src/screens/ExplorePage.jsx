import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import MonetizedAdSlot from "../features/ads/components/MonetizedAdSlot";
import { sanitizeSearchMetadata, trackAnalyticsEvent } from "../features/analytics/lib/analytics";
import CampaignCard from "../features/campaigns/components/CampaignCard";
import { campaignMatchesType } from "../features/campaigns/lib/campaigns";
import { CATEGORIES, CAMPAIGN_TYPE_FILTERS } from "../shared/config/platforms";

const INITIAL_VISIBLE_COUNT = 20;
const LOAD_MORE_COUNT = 20;
const ALL_LABEL = "전체";
const EXPLORE_PRESETS = [
  { key: "foodCafe", label: "맛집/카페", sortBy: "platform" },
  { key: "lowCompetition", label: "경쟁 낮음", sortBy: "comp" },
  { key: "deadline", label: "오늘·내일 마감", sortBy: "dDay" },
  { key: "blog", label: "블로그", sortBy: "comp" },
  { key: "instagram", label: "인스타·릴스", sortBy: "comp" },
  { key: "selectedMany", label: "선정 인원 많음", sortBy: "selected" },
  { key: "highReward", label: "고보상", sortBy: "reward" },
  { key: "beginner", label: "초보자 추천", sortBy: "comp" },
];

function formatCount(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function SkeletonRow() {
  return (
    <div className="campaign-list-item campaign-list-item--skeleton">
      <div className="campaign-list-main">
        <div className="skeleton" style={{ height: 10, width: 72, borderRadius: 999 }} />
        <div className="skeleton" style={{ height: 18, width: "72%", borderRadius: 8, marginTop: 10 }} />
        <div className="skeleton" style={{ height: 12, width: "56%", borderRadius: 8, marginTop: 12 }} />
        <div className="campaign-list-checks">
          <div className="skeleton" style={{ height: 12, width: "84%", borderRadius: 8 }} />
          <div className="skeleton" style={{ height: 12, width: "68%", borderRadius: 8 }} />
        </div>
      </div>
      <div className="campaign-list-side campaign-list-side--skeleton">
        <div className="skeleton" style={{ height: 22, width: 78, borderRadius: 999 }} />
        <div className="skeleton" style={{ height: 36, width: 96, borderRadius: 12, marginTop: 12 }} />
      </div>
    </div>
  );
}

function ExplorePage({
  campaigns,
  filtered,
  search,
  setSearch,
  campaignType,
  setCampaignType,
  category,
  setCategory,
  province,
  setProvince,
  availableProvinces,
  city,
  setCity,
  availableCities,
  sortBy,
  setSortBy,
  preset,
  setPreset,
  user,
  onSelect,
  favIds,
  onFav,
  onApply,
  onImpression,
  loading,
  activeFilterSummary,
  onResetFilters,
  onOpenMap,
}) {
  const filterSignature = `${search}|${campaignType}|${category}|${province}|${city}|${sortBy}|${preset}|${filtered.length}`;
  const [visibleState, setVisibleState] = useState({
    signature: filterSignature,
    count: INITIAL_VISIBLE_COUNT,
  });
  const [showMoreFilters, setShowMoreFilters] = useState(false);
  const visibleCount = visibleState.signature === filterSignature
    ? visibleState.count
    : INITIAL_VISIBLE_COUNT;
  const loadMoreRef = useRef(null);
  const loadMoreReadyRef = useRef(true);
  const lastSearchEventRef = useRef("");

  const buildFilterMetadata = useCallback((extra = {}) => ({
    ...sanitizeSearchMetadata(search),
    campaignType,
    sortBy,
    preset,
    resultCount: filtered.length,
    ...extra,
  }), [campaignType, filtered.length, preset, search, sortBy]);

  const handleSearchChange = (value) => {
    setSearch(value);
  };

  const handlePresetChange = (item) => {
    const nextPreset = preset === item.key ? "" : item.key;
    trackAnalyticsEvent("preset_filter", {
      category,
      region: province,
      city,
      metadata: buildFilterMetadata({
        previousPreset: preset,
        nextPreset,
        nextSortBy: nextPreset ? item.sortBy : sortBy,
      }),
    }, user);

    if (!nextPreset) {
      setPreset("");
      return;
    }

    setPreset(item.key);
    setSearch("");
    setCampaignType(ALL_LABEL);
    setCategory(ALL_LABEL);
    setSortBy(item.sortBy);
  };

  const handleCampaignTypeChange = (item) => {
    if (campaignType !== item) {
      trackAnalyticsEvent("category_filter", {
        category,
        region: province,
        city,
        metadata: buildFilterMetadata({ previousCampaignType: campaignType, nextCampaignType: item, filterLevel: "campaign_type" }),
      }, user);
    }
    setPreset("");
    setCampaignType(item);
    setCategory(ALL_LABEL);
    setProvince(ALL_LABEL);
    setCity(ALL_LABEL);
  };

  const handleCategoryChange = (item) => {
    if (category !== item) {
      trackAnalyticsEvent("category_filter", {
        category: item,
        region: province,
        city,
        metadata: buildFilterMetadata({ previousCategory: category }),
      }, user);
    }
    setPreset("");
    setCategory(item);
    setProvince(ALL_LABEL);
    setCity(ALL_LABEL);
  };

  const handleProvinceChange = (item) => {
    if (province !== item) {
      trackAnalyticsEvent("region_filter", {
        category,
        region: item,
        city: ALL_LABEL,
        metadata: buildFilterMetadata({ previousProvince: province, filterLevel: "province" }),
      }, user);
    }
    setProvince(item);
    setCity(ALL_LABEL);
  };

  const handleCityChange = (item) => {
    if (city !== item) {
      trackAnalyticsEvent("region_filter", {
        category,
        region: province,
        city: item,
        metadata: buildFilterMetadata({ previousCity: city, filterLevel: "city" }),
      }, user);
    }
    setCity(item);
  };

  const handleSortChange = (key) => {
    if (sortBy !== key) {
      trackAnalyticsEvent("sort_filter", {
        category,
        region: province,
        city,
        metadata: buildFilterMetadata({ previousSortBy: sortBy, nextSortBy: key }),
      }, user);
    }
    setSortBy(key);
  };

  const handleResetFilters = () => {
    trackAnalyticsEvent("filter_reset", {
      category,
      region: province,
      city,
      metadata: buildFilterMetadata(),
    }, user);
    onResetFilters?.();
  };

  useEffect(() => {
    loadMoreReadyRef.current = true;
  }, [filterSignature]);

  useEffect(() => {
    const node = loadMoreRef.current;
    if (!node) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) {
          loadMoreReadyRef.current = true;
          return;
        }
        if (!loadMoreReadyRef.current) return;
        loadMoreReadyRef.current = false;
        setVisibleState((current) => {
          const currentCount = current.signature === filterSignature
            ? current.count
            : INITIAL_VISIBLE_COUNT;

          if (currentCount >= filtered.length) {
            return current.signature === filterSignature
              ? current
              : { signature: filterSignature, count: currentCount };
          }

          return {
            signature: filterSignature,
            count: Math.min(currentCount + LOAD_MORE_COUNT, filtered.length),
          };
        });
      },
      { rootMargin: "280px 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [filtered.length, filterSignature]);

  useEffect(() => {
    const trimmedSearch = search.trim();
    if (!trimmedSearch) {
      lastSearchEventRef.current = "";
      return undefined;
    }

    const searchSignature = `${trimmedSearch}|${campaignType}|${category}|${province}|${city}|${sortBy}|${preset}`;
    const timeoutId = window.setTimeout(() => {
      if (lastSearchEventRef.current === searchSignature) return;
      lastSearchEventRef.current = searchSignature;
      trackAnalyticsEvent("search_filter", {
        category,
        region: province,
        city,
        metadata: buildFilterMetadata(),
      }, user);
    }, 700);

    return () => window.clearTimeout(timeoutId);
  }, [search, campaignType, category, province, city, sortBy, preset, user, buildFilterMetadata]);

  const hasActiveFilters =
    Boolean(search)
    || Boolean(preset)
    || campaignType !== ALL_LABEL
    || province !== ALL_LABEL
    || city !== ALL_LABEL
    || category !== ALL_LABEL
    || sortBy !== "platform";
  const hasAdvancedFilters = province !== ALL_LABEL || city !== ALL_LABEL || sortBy !== "platform";
  const showAdvancedFilters = showMoreFilters || hasAdvancedFilters;

  const availableCampaignTypes = useMemo(
    () => CAMPAIGN_TYPE_FILTERS.filter(
      (item) => item === ALL_LABEL || campaigns.some((campaign) => campaignMatchesType(campaign, item)),
    ),
    [campaigns],
  );

  const campaignTypeCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCampaignTypes.map((item) => [item, 0]));
    counts[ALL_LABEL] = campaigns.length;
    campaigns.forEach((campaign) => {
      for (const item of CAMPAIGN_TYPE_FILTERS) {
        if (item !== ALL_LABEL && campaignMatchesType(campaign, item)) {
          counts[item] = (counts[item] || 0) + 1;
        }
      }
    });
    return counts;
  }, [availableCampaignTypes, campaigns]);

  const campaignTypeScopeCampaigns = useMemo(
    () => campaigns.filter((campaign) => campaignMatchesType(campaign, campaignType)),
    [campaignType, campaigns],
  );

  const availableCategories = useMemo(
    () => CATEGORIES.filter(
      (item) => item === ALL_LABEL || campaignTypeScopeCampaigns.some((campaign) => campaign.category === item),
    ),
    [campaignTypeScopeCampaigns],
  );

  const categoryCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCategories.map((item) => [item, 0]));
    counts[ALL_LABEL] = campaignTypeScopeCampaigns.length;
    campaignTypeScopeCampaigns.forEach((campaign) => {
      if (Object.hasOwn(counts, campaign.category)) {
        counts[campaign.category] += 1;
      }
    });
    return counts;
  }, [availableCategories, campaignTypeScopeCampaigns]);

  const regionScopeCampaigns = useMemo(
    () => campaignTypeScopeCampaigns.filter((campaign) =>
      category === ALL_LABEL || campaign.category === category,
    ),
    [campaignTypeScopeCampaigns, category],
  );

  const provinceCounts = useMemo(() => {
    const counts = Object.fromEntries(availableProvinces.map((item) => [item, 0]));
    counts[ALL_LABEL] = regionScopeCampaigns.length;
    regionScopeCampaigns.forEach((campaign) => {
      if (Object.hasOwn(counts, campaign.province)) {
        counts[campaign.province] += 1;
      }
    });
    return counts;
  }, [availableProvinces, regionScopeCampaigns]);

  const cityCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCities.map((item) => [item, 0]));
    regionScopeCampaigns.forEach((campaign) => {
      const inProvince = province === ALL_LABEL || campaign.province === province;
      if (inProvince) counts[ALL_LABEL] = (counts[ALL_LABEL] || 0) + 1;
      if (campaign.province === province && Object.hasOwn(counts, campaign.city)) {
        counts[campaign.city] += 1;
      }
    });
    return counts;
  }, [availableCities, province, regionScopeCampaigns]);

  const sortLabel = sortBy === "platform"
    ? "사이트 골고루"
    : sortBy === "comp"
      ? "경쟁률순"
      : sortBy === "latest"
        ? "최신순"
        : sortBy === "selected"
          ? "선정 인원순"
          : sortBy === "reward"
            ? "고보상순"
            : "마감순";
  const quickScopeLabel = campaignType === "배송형"
    ? "배송형 보기"
    : campaignType === "방문형"
      ? "방문형 우선"
      : "전체 유형";
  const visibleCards = useMemo(() => filtered.slice(0, visibleCount), [filtered, visibleCount]);
  const hasMoreCards = visibleCount < filtered.length;
  const platformCount = useMemo(() => new Set(
    campaigns.map((campaign) => campaign.platformId || campaign.platform).filter(Boolean),
  ).size, [campaigns]);
  return (
    <div className="page page--simple">
      <section className="control-panel">
        <div className="search-box search-box--simple">
          <span className="search-box-icon" aria-hidden="true">⌕</span>
          <input
            value={search}
            onChange={(event) => handleSearchChange(event.target.value)}
            placeholder="지역, 카테고리, 체험단 이름 검색"
            aria-label="캠페인 검색"
          />
          {search && (
            <button
              type="button"
              className="search-box-clear"
              onClick={() => handleSearchChange("")}
            >
              지우기
            </button>
          )}
        </div>

        <div className="preset-panel">
          <div className="preset-panel-header">
            <span>빠른 탐색</span>
            <strong>{quickScopeLabel}</strong>
          </div>
          <div className="preset-chip-row">
            {EXPLORE_PRESETS.map((item) => (
              <button
                key={item.key}
                type="button"
                className={`preset-chip${preset === item.key ? " active" : ""}`}
                onClick={() => handlePresetChange(item)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {hasActiveFilters && (
          <div className="active-filter-banner active-filter-banner--simple">
            <div className="active-filter-text">
              현재 조건 <strong>{activeFilterSummary}</strong>
            </div>
            <button type="button" className="active-filter-reset" onClick={handleResetFilters}>
              초기화
            </button>
          </div>
        )}

        <div className="filter-wrapper filter-wrapper--simple">
          <div className="filter-row filter-row--category">
            <span className="filter-row-label">유형</span>
            <div className="filter-section">
              {availableCampaignTypes.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip chip--minimal ${campaignType === item ? "active" : ""}`}
                  onClick={() => handleCampaignTypeChange(item)}
                >
                  {item}
                  <span className="region-chip-count">{formatCount(campaignTypeCounts[item] || 0)}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="filter-divider" />
          <div className="filter-row filter-row--category">
            <span className="filter-row-label">카테고리</span>
            <div className="filter-section">
              {availableCategories.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`chip chip--minimal ${category === item ? "active" : ""}`}
                  onClick={() => handleCategoryChange(item)}
                >
                  {item}
                  <span className="region-chip-count">{formatCount(categoryCounts[item] || 0)}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="filter-compact-actions">
            <button
              type="button"
              className={`filter-toggle-btn${showAdvancedFilters ? " active" : ""}`}
              aria-expanded={showAdvancedFilters}
              onClick={() => setShowMoreFilters((current) => !current)}
            >
              지역·정렬
              {hasAdvancedFilters && <span>적용 중</span>}
            </button>
            {hasActiveFilters && (
              <button type="button" className="filter-reset-btn" onClick={handleResetFilters}>
                초기화
              </button>
            )}
          </div>
          {showAdvancedFilters && (
            <div className="advanced-filter-block">
              <div className="filter-divider" />
              <div className="filter-row">
                <span className="filter-row-label">시도</span>
                <div className="filter-section">
                  {availableProvinces.map((item) => (
                    <button
                      key={item}
                      type="button"
                      className={`chip chip--minimal ${province === item ? "active" : ""}`}
                      onClick={() => handleProvinceChange(item)}
                    >
                      {item}
                      <span className="region-chip-count">{provinceCounts[item] || 0}</span>
                    </button>
                  ))}
                </div>
              </div>
              {availableCities.length > 1 && (
                <>
                  <div className="filter-divider" />
                  <div className="filter-row">
                    <span className="filter-row-label">시군구</span>
                    <div className="filter-section">
                      {availableCities.map((item) => (
                        <button
                          key={item}
                          type="button"
                          className={`chip chip--minimal ${city === item ? "active" : ""}`}
                          onClick={() => handleCityChange(item)}
                        >
                          {item}
                          <span className="region-chip-count">{cityCounts[item] || 0}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}
              <div className="filter-divider" />
              <div className="filter-row">
                <span className="filter-row-label">정렬</span>
                <div className="filter-section">
                  {[
                    ["platform", "사이트 골고루"],
                    ["dDay", "마감순"],
                    ["comp", "경쟁률 낮은 순"],
                    ["latest", "최신순"],
                    ["selected", "선정 인원 많은 순"],
                    ["reward", "고보상순"],
                  ].map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      className={`chip chip--minimal chip--dark ${sortBy === key ? "active" : ""}`}
                      onClick={() => handleSortChange(key)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="explore-status-strip" aria-label="탐색 현황">
        <div>
          <strong>{formatCount(filtered.length)}</strong>
          <span>현재 결과</span>
        </div>
        <div>
          <strong>{platformCount}</strong>
          <span>통합 플랫폼</span>
        </div>
        <div className="explore-status-actions">
          {onOpenMap && (
            <button type="button" onClick={onOpenMap}>
              지도 보기
            </button>
          )}
          {hasActiveFilters && (
            <button type="button" onClick={handleResetFilters}>
              초기화
            </button>
          )}
        </div>
      </section>

      {!loading && filtered.length > 0 && (
        <div className="result-header result-header--simple">
          <div>
            <div className="result-header-meta">{sortLabel} 기준</div>
            <span className="result-title">{search ? `"${search}" 검색 결과` : "조건별 목록"}</span>
          </div>
          <span className="result-count">{filtered.length}개</span>
        </div>
      )}

      {loading && (
        <div className="campaign-list">
          {Array.from({ length: 7 }).map((_, index) => <SkeletonRow key={index} />)}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="empty empty--simple">
          <div className="empty-text">조건에 맞는 공고가 없습니다.</div>
          <div className="empty-sub">검색어를 줄이거나 필터를 초기화해서 다시 확인해보세요.</div>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <>
          <div className="campaign-list">
            {visibleCards.map((campaign, index) => (
              <Fragment key={campaign.id}>
                {index === 8 && (
                  <MonetizedAdSlot
                    slotId="explore_inline"
                    context={{ page: "explore", category, province, city, index }}
                    variant="inline"
                  />
                )}
                <CampaignCard
                  c={campaign}
                  onSelect={onSelect}
                  isFav={favIds.has(campaign.id)}
                  onFav={onFav}
                  onApply={onApply}
                  onImpression={onImpression}
                  impressionContext={{
                    page: "explore",
                    section: "results",
                    position: index + 1,
                    resultCount: filtered.length,
                    visibleCount,
                    sortBy,
                    preset,
                    category,
                    province,
                    city,
                    slotId: "explore_results",
                  }}
                />
              </Fragment>
            ))}
          </div>
          <div className="infinite-scroll-sentinel" ref={loadMoreRef}>
            {hasMoreCards ? "더 많은 공고를 불러오는 중" : "모든 공고를 확인했습니다."}
          </div>
        </>
      )}
    </div>
  );
}

export default ExplorePage;
