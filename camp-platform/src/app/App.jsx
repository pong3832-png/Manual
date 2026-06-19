import { Suspense, lazy, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { supabase } from "../shared/api/supabase";
import { PLATFORMS, CATEGORIES, CAMPAIGN_TYPE_FILTERS } from "../shared/config/platforms";
import {
  campaignMatchesType,
  campaignTypeToSlug,
  categoryToSlug,
  getCampaignFacetProfile,
  getCampaignRewardValue,
  getCityGroups,
  getPlatformDiverseCampaigns,
  getProvinceGroups,
  isCampaignOpen,
  isFreshDeadlineCampaign,
  slugToCampaignType,
  slugToCategory,
} from "../features/campaigns/lib/campaigns";
import useAuthSession from "../features/auth/hooks/useAuthSession";
import useCampaigns from "../features/campaigns/hooks/useCampaigns";
import useUserActivity from "../features/user/hooks/useUserActivity";
import AdSenseLoader from "../features/ads/components/AdSenseLoader";
import { sanitizeSearchMetadata, trackAnalyticsEvent, trackTrafficSourceOnce } from "../features/analytics/lib/analytics";
import { SITE_NAME } from "../shared/config/site";
import { normalizeAppTab } from "./appRouting";

const HomePage = lazy(() => import("../screens/HomePage"));
const MapPage = lazy(() => import("../screens/MapPage"));
const ExplorePage = lazy(() => import("../screens/ExplorePage"));
const StatusPage = lazy(() => import("../screens/StatusPage"));
const OpsPage = lazy(() => import("../screens/OpsPage"));
const ProfilePage = lazy(() => import("../screens/ProfilePage"));
const DetailModal = lazy(() => import("../features/campaigns/components/DetailModal"));
const AuthModal = lazy(() => import("../features/auth/components/AuthModal"));
const LegalModal = lazy(() => import("../shared/components/LegalModal"));

const DEFAULT_CATEGORY = CATEGORIES[0] || "전체";
const DEFAULT_CAMPAIGN_TYPE = CAMPAIGN_TYPE_FILTERS[0] || "전체";
const DEFAULT_PROVINCE = "전체";
const DEFAULT_CITY = "전체";
const DEFAULT_SORT = "platform";
const DEFAULT_PRESET = "";
const SORT_OPTIONS = ["platform", "dDay", "comp", "latest", "selected", "reward"];
const MAX_CAMPAIGN_IMPRESSIONS_PER_SESSION = 160;
const PRESET_LABELS = {
  foodCafe: "맛집/카페",
  lowCompetition: "경쟁 낮음",
  deadline: "오늘·내일 마감",
  blog: "블로그",
  instagram: "인스타·릴스",
  selectedMany: "선정 인원 많음",
  highReward: "고보상",
  beginner: "초보자 추천",
};
const TAB_ITEMS = [
  { key: "home", label: "홈", icon: "H" },
  { key: "map", label: "지도", icon: "M" },
  { key: "explore", label: "탐색", icon: "E" },
  { key: "status", label: "현황", icon: "S" },
  { key: "ops", label: "운영", icon: "O" },
  { key: "profile", label: "마이", icon: "P" },
];

function parseCampaignTimestamp(value) {
  const parsed = Date.parse(value || "");
  return Number.isFinite(parsed) ? parsed : 0;
}

function getCampaignLatestTimestamp(campaign) {
  return (
    parseCampaignTimestamp(campaign?.sourceStartedAt)
    || parseCampaignTimestamp(campaign?.sourcePostedAt)
    || parseCampaignTimestamp(campaign?.firstSeenAt)
    || parseCampaignTimestamp(campaign?.crawledAt)
  );
}

function matchesArea(campaign, province, city) {
  if (province !== DEFAULT_PROVINCE && campaign.province !== province) return false;
  if (city !== DEFAULT_CITY && campaign.city !== city) return false;
  return true;
}

function getCompetitionRatio(campaign) {
  return Number(campaign.applyCount || 0) / Number(campaign.selectedCount || 1);
}

function getCampaignUrlDomain(campaign) {
  try {
    return new URL(campaign?.url || "").hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

function compareCampaignId(left, right) {
  return String(left.id).localeCompare(String(right.id), undefined, { numeric: true });
}

function compareCampaignsBySort(left, right, sortBy) {
  if (sortBy === "comp") {
    const compDiff = getCompetitionRatio(left) - getCompetitionRatio(right);
    if (compDiff !== 0) return compDiff;
    const dDiff = left.dDay - right.dDay;
    if (dDiff !== 0) return dDiff;
    return compareCampaignId(left, right);
  }

  if (sortBy === "latest") {
    const latestDiff = getCampaignLatestTimestamp(right) - getCampaignLatestTimestamp(left);
    if (latestDiff !== 0) return latestDiff;
    const compDiff = getCompetitionRatio(left) - getCompetitionRatio(right);
    if (compDiff !== 0) return compDiff;
    return compareCampaignId(left, right);
  }

  if (sortBy === "selected") {
    const selectedDiff = Number(right.selectedCount || 0) - Number(left.selectedCount || 0);
    if (selectedDiff !== 0) return selectedDiff;
    const compDiff = getCompetitionRatio(left) - getCompetitionRatio(right);
    if (compDiff !== 0) return compDiff;
    return compareCampaignId(left, right);
  }

  if (sortBy === "reward") {
    const rewardDiff = getCampaignRewardValue(right) - getCampaignRewardValue(left);
    if (rewardDiff !== 0) return rewardDiff;
    const compDiff = getCompetitionRatio(left) - getCompetitionRatio(right);
    if (compDiff !== 0) return compDiff;
    return compareCampaignId(left, right);
  }

  const dDiff = left.dDay - right.dDay;
  if (dDiff !== 0) return dDiff;
  const compDiff = getCompetitionRatio(left) - getCompetitionRatio(right);
  if (compDiff !== 0) return compDiff;
  return compareCampaignId(left, right);
}

function matchesExplorePreset(campaign, preset) {
  if (!preset) return true;

  const dDay = Number(campaign.dDay ?? 999);
  const competitionRatio = getCompetitionRatio(campaign);
  const selectedCount = Number(campaign.selectedCount || 0);

  if (preset === "foodCafe") {
    return ["맛집", "카페"].includes(campaign.category);
  }
  if (preset === "lowCompetition") {
    return competitionRatio < 30;
  }
  if (preset === "deadline") {
    return isFreshDeadlineCampaign(campaign);
  }
  if (preset === "blog") {
    const facets = getCampaignFacetProfile(campaign);
    return facets.snsLabel === "블로그";
  }
  if (preset === "instagram") {
    const facets = getCampaignFacetProfile(campaign);
    return ["인스타", "릴스", "숏폼"].includes(facets.snsLabel);
  }
  if (preset === "selectedMany") {
    return selectedCount >= 5;
  }
  if (preset === "highReward") {
    return getCampaignRewardValue(campaign) > 0;
  }
  if (preset === "beginner") {
    return competitionRatio < 30 && selectedCount >= 3 && dDay >= 1;
  }

  return true;
}

function readFilterStateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const categoryParam = params.get("category") || "";
  const nextCategory = slugToCategory(categoryParam);
  const nextCampaignType = slugToCampaignType(params.get("type") || categoryParam);
  const nextProvince = params.get("province");
  const nextCity = params.get("city");
  const nextSort = params.get("sort");
  const nextPreset = params.get("preset") || DEFAULT_PRESET;

  return {
    tab: params.get("tab") || "home",
    search: params.get("q") || "",
    campaignType: CAMPAIGN_TYPE_FILTERS.includes(nextCampaignType) ? nextCampaignType : DEFAULT_CAMPAIGN_TYPE,
    category: CATEGORIES.includes(nextCategory) ? nextCategory : DEFAULT_CATEGORY,
    province: nextProvince || DEFAULT_PROVINCE,
    city: nextCity || DEFAULT_CITY,
    sortBy: SORT_OPTIONS.includes(nextSort) ? nextSort : DEFAULT_SORT,
    preset: Object.keys(PRESET_LABELS).includes(nextPreset) ? nextPreset : DEFAULT_PRESET,
  };
}

function upsertMeta(selector, attribute, value) {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, selector.match(/"([^"]+)"/)?.[1] || "");
    document.head.appendChild(element);
  }
  element.setAttribute("content", value);
}

function upsertCanonical(url) {
  let link = document.head.querySelector('link[rel="canonical"]');
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  link.setAttribute("href", url);
}

function shouldShowOpsTab() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("ops") === "1") return true;

  try {
    return window.localStorage.getItem("showOps") === "1";
  } catch {
    return false;
  }
}

function StageFallback() {
  return (
    <div className="page">
      <div className="stage-fallback">
        <div className="stage-fallback-copy">
          <div className="command-eyebrow">Loading View</div>
          <div className="page-title" style={{ marginBottom: 6 }}>화면을 준비하고 있습니다</div>
          <div className="page-sub" style={{ marginBottom: 0 }}>필요한 모듈만 불러와서 첫 진입 속도를 줄였습니다.</div>
        </div>
        <div className="stage-fallback-grid">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="stage-fallback-card">
              <div className="stage-fallback-bar stage-fallback-bar--short" />
              <div className="stage-fallback-bar" />
              <div className="stage-fallback-bar stage-fallback-bar--tiny" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const initialFilters = readFilterStateFromUrl();
  const showOpsTab = useMemo(() => shouldShowOpsTab(), []);
  const [tab, setTab] = useState(() => normalizeAppTab(initialFilters.tab, { showOps: showOpsTab }));
  const { user } = useAuthSession();
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const { campaigns, campaignLoadError, loading } = useCampaigns();
  const { profile, favorites, applications, setFavorites, setApplications, loadApplications, loadProfile } = useUserActivity(user);
  const [search, setSearch] = useState(initialFilters.search);
  const deferredSearch = useDeferredValue(search);
  const [campaignType, setCampaignType] = useState(initialFilters.campaignType);
  const [category, setCategory] = useState(initialFilters.category);
  const [province, setProvince] = useState(initialFilters.province);
  const [city, setCity] = useState(initialFilters.city);
  const [sortBy, setSortBy] = useState(initialFilters.sortBy);
  const [preset, setPreset] = useState(initialFilters.preset);
  const [selected, setSelected] = useState(null);
  const [toast, setToast] = useState(null);
  const [legalView, setLegalView] = useState("");
  const visibleTabItems = useMemo(
    () => TAB_ITEMS.filter((item) => item.key !== "ops" || showOpsTab),
    [showOpsTab],
  );

  const showToast = useCallback((msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  }, []);

  const openLegal = useCallback((view) => {
    const nextView = ["privacy", "terms", "contact"].includes(view) ? view : "privacy";
    setLegalView(nextView);
    trackAnalyticsEvent("legal_open", { metadata: { view: nextView } }, user);

    const params = new URLSearchParams(window.location.search);
    params.delete("contact");
    params.set("legal", nextView);
    const nextSearch = params.toString();
    window.history.replaceState({}, "", `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`);
  }, [user]);

  const closeLegal = useCallback(() => {
    setLegalView("");

    const params = new URLSearchParams(window.location.search);
    params.delete("legal");
    params.delete("contact");
    const nextSearch = params.toString();
    window.history.replaceState({}, "", `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`);
  }, []);

  const resetFilters = useCallback(() => {
    setSearch("");
    setCampaignType(DEFAULT_CAMPAIGN_TYPE);
    setCategory(DEFAULT_CATEGORY);
    setProvince(DEFAULT_PROVINCE);
    setCity(DEFAULT_CITY);
    setSortBy(DEFAULT_SORT);
    setPreset(DEFAULT_PRESET);
  }, []);

  const openExplore = useCallback((nextFilters = {}) => {
    const {
      search: nextSearch = "",
      campaignType: nextCampaignType = DEFAULT_CAMPAIGN_TYPE,
      category: nextCategory = DEFAULT_CATEGORY,
      province: nextProvince = DEFAULT_PROVINCE,
      city: nextCity = DEFAULT_CITY,
      sortBy: nextSortBy = DEFAULT_SORT,
      preset: nextPreset = DEFAULT_PRESET,
    } = nextFilters;

    setSearch(nextSearch);
    setCampaignType(CAMPAIGN_TYPE_FILTERS.includes(nextCampaignType) ? nextCampaignType : DEFAULT_CAMPAIGN_TYPE);
    setCategory(CATEGORIES.includes(nextCategory) ? nextCategory : DEFAULT_CATEGORY);
    setProvince(nextProvince || DEFAULT_PROVINCE);
    setCity(nextCity || DEFAULT_CITY);
    setSortBy(SORT_OPTIONS.includes(nextSortBy) ? nextSortBy : DEFAULT_SORT);
    setPreset(Object.keys(PRESET_LABELS).includes(nextPreset) ? nextPreset : DEFAULT_PRESET);
    setTab("explore");
    trackAnalyticsEvent("home_discovery_click", {
      category: nextCategory,
      region: nextProvince,
      city: nextCity,
      metadata: {
        campaignType: nextCampaignType,
        sortBy: nextSortBy,
        preset: nextPreset,
        ...sanitizeSearchMetadata(nextSearch),
      },
    }, user);
  }, [user]);

  const openMap = useCallback(() => {
    setTab("map");
  }, []);

  const handleTabChange = useCallback((nextTab) => {
    setTab(nextTab);
  }, []);

  const campaignImpressionKeysRef = useRef(new Set());

  const handleCampaignImpression = useCallback((campaign, context = {}) => {
    if (!campaign?.id) return;

    const page = String(context.page || tab || "unknown").slice(0, 40);
    const section = String(context.section || "list").slice(0, 40);
    const impressionKey = `${page}:${section}:${campaign.id}`;
    const seenKeys = campaignImpressionKeysRef.current;
    if (seenKeys.has(impressionKey) || seenKeys.size >= MAX_CAMPAIGN_IMPRESSIONS_PER_SESSION) return;
    seenKeys.add(impressionKey);

    trackAnalyticsEvent("campaign_impression", {
      campaignId: campaign.id,
      platformId: campaign.platformId,
      category: campaign.category,
      region: campaign.province || campaign.region,
      city: campaign.city,
      slotId: context.slotId || `${page}_${section}`,
      metadata: {
        page,
        section,
        position: Number(context.position || 0),
        resultCount: Number(context.resultCount || 0),
        visibleCount: Number(context.visibleCount || 0),
        sortBy: context.sortBy || "",
        preset: context.preset || "",
        dDay: campaign.dDay,
        applyCount: campaign.applyCount,
        selectedCount: campaign.selectedCount,
      },
    }, user);
  }, [tab, user]);

  const handleSelectCampaign = useCallback((campaign) => {
    if (!campaign) return;
    trackAnalyticsEvent("campaign_open", {
      campaignId: campaign.id,
      platformId: campaign.platformId,
      category: campaign.category,
      region: campaign.province || campaign.region,
      city: campaign.city,
      metadata: {
        tab,
        dDay: campaign.dDay,
        applyCount: campaign.applyCount,
        selectedCount: campaign.selectedCount,
      },
    }, user);
    setSelected(campaign);
  }, [tab, user]);

  const activeFilterSummary = useMemo(() => {
    const summary = [];
    if (preset) summary.push(`프리셋 ${PRESET_LABELS[preset] || preset}`);
    if (search) summary.push(`검색어 ${search}`);
    if (campaignType !== DEFAULT_CAMPAIGN_TYPE) summary.push(`유형 ${campaignType}`);
    if (province !== DEFAULT_PROVINCE) summary.push(`시도 ${province}`);
    if (city !== DEFAULT_CITY) summary.push(`시군구 ${city}`);
    if (category !== DEFAULT_CATEGORY) summary.push(`카테고리 ${category}`);
    summary.push(
      sortBy === "platform"
        ? "사이트 골고루"
        : sortBy === "comp"
          ? "경쟁률순"
          : sortBy === "latest"
            ? "최신순"
            : sortBy === "selected"
              ? "선정 인원순"
              : sortBy === "reward"
                ? "고보상순"
                : "마감순",
    );
    return summary.join(" | ");
  }, [search, campaignType, category, city, province, preset, sortBy]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (tab !== "home") params.set("tab", tab); else params.delete("tab");
    if (search) params.set("q", search); else params.delete("q");
    if (campaignType !== DEFAULT_CAMPAIGN_TYPE) params.set("type", campaignTypeToSlug(campaignType)); else params.delete("type");
    if (province !== DEFAULT_PROVINCE) params.set("province", province); else params.delete("province");
    if (city !== DEFAULT_CITY) params.set("city", city); else params.delete("city");
    if (category !== DEFAULT_CATEGORY) params.set("category", categoryToSlug(category)); else params.delete("category");
    params.delete("platform");
    if (sortBy !== DEFAULT_SORT) params.set("sort", sortBy); else params.delete("sort");
    if (preset) params.set("preset", preset); else params.delete("preset");
    const nextSearch = params.toString();
    const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`;
    window.history.replaceState({}, "", nextUrl);
  }, [tab, search, campaignType, category, city, province, preset, sortBy]);

  useEffect(() => {
    const syncRecoveryMode = () => {
      if (window.location.hash.includes("type=recovery")) {
        setAuthMode("reset");
        setShowAuth(true);
      }
    };
    syncRecoveryMode();
    window.addEventListener("hashchange", syncRecoveryMode);
    return () => window.removeEventListener("hashchange", syncRecoveryMode);
  }, []);

  useEffect(() => {
    const syncLegalRoute = () => {
      const params = new URLSearchParams(window.location.search);
      const requestedView = params.get("contact") === "1" ? "contact" : params.get("legal");
      if (["privacy", "terms", "contact"].includes(requestedView)) {
        setLegalView(requestedView);
      }
    };

    syncLegalRoute();
    window.addEventListener("popstate", syncLegalRoute);
    return () => window.removeEventListener("popstate", syncLegalRoute);
  }, []);

  useEffect(() => {
    const titleBase = {
      home: "체험단 캠페인 모음",
      map: "지도에서 찾기",
      explore: "카테고리 탐색",
      status: "지원 현황",
      ops: "운영 관리",
      profile: "마이페이지",
    }[tab] || SITE_NAME;
    const description = tab === "home"
      ? "여러 체험단 캠페인을 한 화면에서 비교하고 바로 지원 페이지로 이동할 수 있습니다."
      : `${titleBase} 화면입니다.`;
    const canonicalUrl = `${window.location.origin}${window.location.pathname}${window.location.search}`;
    document.title = `${titleBase} | ${SITE_NAME}`;
    upsertMeta('meta[name="description"]', "name", description);
    upsertMeta('meta[property="og:title"]', "property", document.title);
    upsertMeta('meta[property="og:description"]', "property", description);
    upsertMeta('meta[property="og:url"]', "property", canonicalUrl);
    upsertCanonical(canonicalUrl);
  }, [tab]);

  useEffect(() => {
    trackAnalyticsEvent("tab_view", { metadata: { tab } }, user);
  }, [tab, user]);

  useEffect(() => {
    trackTrafficSourceOnce(user);
  }, [user]);

  const toggleFav = useCallback(async (campaign) => {
    if (!user) {
      setShowAuth(true);
      return;
    }
    const isFav = favorites.some((favorite) => favorite.campaign_id === campaign.id);
    const platform = PLATFORMS.find((item) => item.id === campaign.platformId);
    if (isFav) {
      await supabase.from("favorites").delete().eq("user_id", user.id).eq("campaign_id", campaign.id);
      setFavorites((prev) => prev.filter((favorite) => favorite.campaign_id !== campaign.id));
      trackAnalyticsEvent("favorite_remove", {
        campaignId: campaign.id,
        platformId: campaign.platformId,
        category: campaign.category,
        region: campaign.province || campaign.region,
        city: campaign.city,
      }, user);
      showToast("즐겨찾기에서 제거했습니다.");
      return;
    }
    const { data } = await supabase.from("favorites").insert({
      user_id: user.id,
      campaign_id: campaign.id,
      campaign_title: campaign.title,
      campaign_url: campaign.url,
      platform: platform?.name || "",
      platform_id: campaign.platformId,
      category: campaign.category,
      d_day: campaign.dDay,
    }).select().single();
    if (data) setFavorites((prev) => [data, ...prev]);
    trackAnalyticsEvent("favorite_add", {
      campaignId: campaign.id,
      platformId: campaign.platformId,
      category: campaign.category,
      region: campaign.province || campaign.region,
      city: campaign.city,
    }, user);
    showToast("즐겨찾기에 추가했습니다.");
  }, [favorites, setFavorites, showToast, user]);

  const handleApply = useCallback(async (campaign) => {
    const externalWindowFeatures = campaign.platformId === "mrblog" ? "noopener" : "noopener,noreferrer";
    const applicationMessageTemplate = String(profile?.application_message_template || "").trim();
    let copiedApplicationMessage = false;

    trackAnalyticsEvent("apply_click", {
      campaignId: campaign.id,
      platformId: campaign.platformId,
      category: campaign.category,
      region: campaign.province || campaign.region,
      city: campaign.city,
      metadata: {
        loggedIn: Boolean(user),
        externalApply: true,
        applyDomain: getCampaignUrlDomain(campaign),
        deadlineDays: Number.isFinite(Number(campaign.dDay)) ? Number(campaign.dDay) : null,
      },
    }, user);

    if (applicationMessageTemplate && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(applicationMessageTemplate);
        copiedApplicationMessage = true;
      } catch {
        copiedApplicationMessage = false;
      }
    }

    if (!user) {
      window.open(campaign.url, "_blank", externalWindowFeatures);
      setSelected(null);
      return;
    }

    const existing = applications.find((application) => application.campaign_id === campaign.id);
    if (!existing) {
      const platform = PLATFORMS.find((item) => item.id === campaign.platformId);
      const { data, error } = await supabase.from("applications").insert({
        user_id: user.id,
        campaign_id: campaign.id,
        campaign_title: campaign.title,
        campaign_url: campaign.url,
        platform: platform?.name || "",
        platform_id: campaign.platformId,
        category: campaign.category,
        d_day: campaign.dDay,
        status: "지원 페이지 열림",
      }).select().single();
      if (error) {
        showToast(error.message || "지원 현황 추가에 실패했습니다.", "error");
      } else if (data) {
        setApplications((prev) => [data, ...prev]);
        await loadApplications(user.id);
        showToast(copiedApplicationMessage
          ? "지원 페이지를 열고 신청 멘트를 복사했습니다."
          : "지원 페이지를 열었습니다. 실제 지원 여부는 현황에서 확인하세요.");
      }
    } else {
      await loadApplications(user.id);
      showToast(copiedApplicationMessage
        ? "이미 지원 현황에 있는 캠페인입니다. 신청 멘트는 복사했습니다."
        : "이미 지원 현황에 있는 캠페인입니다.", "error");
    }
    window.open(campaign.url, "_blank", externalWindowFeatures);
    setSelected(null);
  }, [applications, loadApplications, profile?.application_message_template, setApplications, showToast, user]);

  const favIds = useMemo(() => new Set(favorites.map((favorite) => favorite.campaign_id)), [favorites]);
  const visibleCampaigns = useMemo(() => campaigns.filter(isCampaignOpen), [campaigns]);
  const regionScopeCampaigns = useMemo(
    () => visibleCampaigns.filter((campaign) =>
      campaignMatchesType(campaign, campaignType)
      && (category === DEFAULT_CATEGORY || campaign.category === category),
    ),
    [campaignType, category, visibleCampaigns],
  );
  const availableProvinces = useMemo(() => {
    const groups = getProvinceGroups(regionScopeCampaigns).filter(Boolean);
    return groups.length ? groups : [DEFAULT_PROVINCE];
  }, [regionScopeCampaigns]);
  const effectiveProvince = availableProvinces.includes(province) ? province : DEFAULT_PROVINCE;
  const availableCities = useMemo(
    () => getCityGroups(regionScopeCampaigns, effectiveProvince),
    [effectiveProvince, regionScopeCampaigns],
  );
  const effectiveCity = availableCities.includes(city) ? city : DEFAULT_CITY;

  const normalizedSearch = useMemo(() => deferredSearch.trim().toLowerCase(), [deferredSearch]);

  const filtered = useMemo(() => {
    if (tab !== "explore" && tab !== "map") return visibleCampaigns;

    const filteredCampaigns = visibleCampaigns
      .filter((campaign) => {
        const searchableText = campaign.searchText || String(campaign.title || "").toLowerCase();
        return (!normalizedSearch || searchableText.includes(normalizedSearch))
        && campaignMatchesType(campaign, campaignType)
        && matchesArea(campaign, effectiveProvince, effectiveCity)
        && (category === DEFAULT_CATEGORY || campaign.category === category)
        && matchesExplorePreset(campaign, preset);
      })
      .sort((left, right) => compareCampaignsBySort(left, right, sortBy));

    return getPlatformDiverseCampaigns(filteredCampaigns);
  }, [visibleCampaigns, normalizedSearch, campaignType, category, effectiveCity, effectiveProvince, preset, sortBy, tab]);

  return (
    <div className="shell">
      <AdSenseLoader />
      {campaignLoadError && <div className="page-alert">{campaignLoadError}</div>}
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-logo">체험단<span>플랫폼</span></div>
          {visibleTabItems.map((item) => (
            <div key={item.key} className={`sidebar-item ${tab === item.key ? "active" : ""}`} onClick={() => handleTabChange(item.key)}>
              <span className="sidebar-icon">{item.icon}</span>
              {item.label}
              {item.key === "status" && favorites.length + applications.length > 0 && <span className="sidebar-badge">{favorites.length + applications.length}</span>}
            </div>
          ))}
          <div className="sidebar-footer">
            {user ? (
              <div className="sidebar-user">
                <div className="sidebar-user-name">{profile?.name || "사용자"}</div>
                <div className="sidebar-user-email">{user.email}</div>
              </div>
            ) : (
              <button className="sidebar-login" onClick={() => { setShowAuth(true); setAuthMode("login"); }}>로그인 / 회원가입</button>
            )}
            <div className="sidebar-legal-links" aria-label="서비스 정책">
              <button type="button" onClick={() => openLegal("privacy")}>개인정보</button>
              <button type="button" onClick={() => openLegal("terms")}>약관</button>
              <button type="button" onClick={() => openLegal("contact")}>문의</button>
            </div>
          </div>
        </aside>

        <main className="main">
          <div className="mobile-header">
            <div className="mobile-header-inner">
              <div className="mobile-header-left">
                <div className="mobile-logo">체험단<span>플랫폼</span></div>
                <div className="mobile-tab-indicator">{visibleTabItems.find((item) => item.key === tab)?.label}</div>
              </div>
              {!user
                ? <button className="mobile-login" onClick={() => { setShowAuth(true); setAuthMode("login"); }}>로그인</button>
                : <div className="mobile-avatar">ID</div>}
            </div>
          </div>

          <Suspense fallback={<StageFallback />}>
            <div className="main-stage fade-in" key={tab}>
              {tab === "home" && (
                <HomePage
                  campaigns={visibleCampaigns}
                  onSelect={handleSelectCampaign}
                  favIds={favIds}
                  onFav={toggleFav}
                  onApply={handleApply}
                  onImpression={handleCampaignImpression}
                  loading={loading}
                  onExplore={openExplore}
                  onOpenMap={openMap}
                />
              )}
              {tab === "map" && <MapPage campaigns={filtered} onSelect={handleSelectCampaign} user={user} />}
              {tab === "explore" && (
                <ExplorePage
                  campaigns={visibleCampaigns}
                  filtered={filtered}
                  search={search}
                  setSearch={setSearch}
                  campaignType={campaignType}
                  setCampaignType={setCampaignType}
                  category={category}
                  setCategory={setCategory}
                  province={effectiveProvince}
                  setProvince={setProvince}
                  availableProvinces={availableProvinces}
                  city={effectiveCity}
                  setCity={setCity}
                  availableCities={availableCities}
                  sortBy={sortBy}
                  setSortBy={setSortBy}
                  preset={preset}
                  setPreset={setPreset}
                  user={user}
                  onSelect={handleSelectCampaign}
                  favIds={favIds}
                  onFav={toggleFav}
                  onApply={handleApply}
                  onImpression={handleCampaignImpression}
                  loading={loading}
                  activeFilterSummary={activeFilterSummary}
                  onResetFilters={resetFilters}
                  onOpenMap={openMap}
                />
              )}
              {tab === "status" && (
                <StatusPage
                  user={user}
                  favorites={favorites}
                  applications={applications}
                  campaigns={visibleCampaigns}
                  onFav={toggleFav}
                  onSelect={handleSelectCampaign}
                  onAuthOpen={() => setShowAuth(true)}
                  onExplore={() => handleTabChange("explore")}
                  loadApplications={() => user && loadApplications(user.id)}
                  showToast={showToast}
                />
              )}
              {tab === "ops" && <OpsPage />}
              {tab === "profile" && (
                <ProfilePage
                  user={user}
                  profile={profile}
                  applications={applications}
                  favorites={favorites}
                  onAuthOpen={() => setShowAuth(true)}
                  onExplore={() => handleTabChange("explore")}
                  onStatus={() => handleTabChange("status")}
                  onMap={() => handleTabChange("map")}
                  onProfileSaved={() => user && loadProfile(user.id)}
                  showToast={showToast}
                  onLogout={async () => {
                    await supabase.auth.signOut();
                    showToast("로그아웃했습니다.");
                  }}
                />
              )}
            </div>
          </Suspense>

          <div className="app-legal-links" aria-label="서비스 정책">
            <button type="button" onClick={() => openLegal("privacy")}>개인정보처리방침</button>
            <button type="button" onClick={() => openLegal("terms")}>이용약관</button>
            <button type="button" onClick={() => openLegal("contact")}>문의</button>
          </div>

          <nav className="mobile-nav">
            <div className="mobile-nav-inner">
              {visibleTabItems.map((item) => (
                <div key={item.key} className={`mobile-nav-item ${tab === item.key ? "active" : ""}`} onClick={() => handleTabChange(item.key)}>
                  <div className="mobile-nav-icon">{item.icon}</div>
                  <span className="mobile-nav-label">{item.label}</span>
                  {item.key === "status" && favorites.length + applications.length > 0 && <span className="nav-dot" />}
                </div>
              ))}
            </div>
          </nav>
        </main>
      </div>

      <Suspense fallback={null}>
        {selected && (
          <DetailModal
            c={selected}
            onClose={() => setSelected(null)}
            onApply={handleApply}
            isFav={favIds.has(selected.id)}
            onFav={toggleFav}
            hasApplicationMessage={Boolean(profile?.application_message_template)}
          />
        )}
        {showAuth && <AuthModal mode={authMode} setMode={setAuthMode} onClose={() => setShowAuth(false)} showToast={showToast} />}
        {legalView && <LegalModal view={legalView} onSelectView={openLegal} onClose={closeLegal} />}
      </Suspense>
      {toast && <div className="toast" style={{ background: toast.type === "error" ? "#DC2626" : "#1D9E75", color: "white" }}>{toast.msg}</div>}
    </div>
  );
}
