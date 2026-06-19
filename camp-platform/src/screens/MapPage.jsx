import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MonetizedAdSlot from "../features/ads/components/MonetizedAdSlot";
import { trackAnalyticsEvent } from "../features/analytics/lib/analytics";
import { CATEGORIES, CAMPAIGN_TYPE_FILTERS, PLATFORMS } from "../shared/config/platforms";
import useKakaoMapLoader from "../features/map/hooks/useKakaoMapLoader";
import {
  campaignMatchesType,
  getCityGroups,
  getCampaignFacetProfile,
  getCampaignLocationLabel,
  getProvinceGroups,
} from "../features/campaigns/lib/campaigns";

const DEFAULT_CENTER = { lat: 36.3504, lng: 127.3845 };
const DEFAULT_PROVINCE = "전체";
const DEFAULT_CITY = "전체";
const DEFAULT_CATEGORY = "전체";
const DEFAULT_CAMPAIGN_TYPE = "전체";
const MAX_VIEW_CAMPAIGNS = 300;
const MAX_NATIONWIDE_VIEW_CAMPAIGNS = 160;
const LIST_LIMIT = MAX_VIEW_CAMPAIGNS;
const REGIONAL_LIST_LIMIT = 8;
const REGIONAL_GROUP_LIMIT = 8;
const MAX_MAP_ZOOM_OUT_LEVEL = 11;
const VIEWPORT_MARKER_MAX_LEVEL = 7;
const PIN_COORDINATE_SOURCES = new Set(["html", "naver", "naver_marker", "kakao_tile", "revu_api"]);
const NON_REGIONAL_LABELS = new Set(["", "전체", "기타", "위치 미확인", "미확인"]);

function getAreaLevel(province, city) {
  if (province === DEFAULT_PROVINCE) return MAX_MAP_ZOOM_OUT_LEVEL;
  if (city === DEFAULT_CITY) return 9;
  return 6;
}

function getClusterCellSize(level) {
  if (level <= 4) return 0.0045;
  if (level <= 6) return 0.009;
  if (level <= 8) return 0.018;
  if (level <= 10) return 0.035;
  return 0.08;
}

function getCampaignBucketKey(campaign, cellSize, level) {
  if (isPinCoordinateSource(campaign.coordinateSource) && level <= 6) {
    return `exact:${Number(campaign.lat).toFixed(6)}:${Number(campaign.lng).toFixed(6)}`;
  }

  return `${Math.round(campaign.lat / cellSize)}:${Math.round(campaign.lng / cellSize)}`;
}

function isPinCoordinateSource(source = "") {
  const normalized = String(source || "").toLowerCase();
  if (PIN_COORDINATE_SOURCES.has(normalized)) return true;
  return normalized.endsWith("_api") && !normalized.includes("keyword") && !normalized.includes("region");
}

function isGeocodedCoordinateSource(source = "") {
  return String(source || "").toLowerCase() === "kakao_address";
}

function clusterCampaigns(campaigns, level) {
  const cellSize = getClusterCellSize(level);
  const buckets = new Map();

  campaigns.forEach((campaign) => {
    const key = getCampaignBucketKey(campaign, cellSize, level);
    const current = buckets.get(key);

    if (current) {
      current.items.push(campaign);
      current.lat += campaign.lat;
      current.lng += campaign.lng;
      return;
    }

    buckets.set(key, {
      key,
      lat: campaign.lat,
      lng: campaign.lng,
      items: [campaign],
    });
  });

  return [...buckets.values()].map((bucket) => {
    const items = [...bucket.items].sort((left, right) => {
      if ((left.dDay ?? 999) !== (right.dDay ?? 999)) return (left.dDay ?? 999) - (right.dDay ?? 999);
      return (left.applyCount ?? 0) - (right.applyCount ?? 0);
    });

    if (items.length === 1) {
      return { type: "single", campaign: items[0] };
    }

    return {
      type: "cluster",
      id: bucket.key,
      lat: bucket.lat / items.length,
      lng: bucket.lng / items.length,
      items,
    };
  });
}

function getCampaignSortValue(campaign) {
  const dDay = Number(campaign.dDay ?? 999);
  const applyCount = Number(campaign.applyCount ?? 0);
  return { dDay, applyCount };
}

function formatCount(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatPercent(part, total) {
  if (!total) return "0%";
  return `${Math.round((part / total) * 100)}%`;
}

function formatDday(campaign) {
  const dDay = Number(campaign.dDay ?? 999);
  if (dDay <= 0) return "오늘";
  if (dDay === 1) return "내일";
  return `D-${dDay}`;
}

function sortMapCampaigns(campaigns) {
  return [...campaigns].sort((left, right) => {
    const leftValue = getCampaignSortValue(left);
    const rightValue = getCampaignSortValue(right);
    if (leftValue.dDay !== rightValue.dDay) return leftValue.dDay - rightValue.dDay;
    if (leftValue.applyCount !== rightValue.applyCount) return rightValue.applyCount - leftValue.applyCount;
    return String(left.id).localeCompare(String(right.id), undefined, { numeric: true });
  });
}

function getCurrentMapBounds(map) {
  const bounds = map.getBounds();
  const southWest = bounds.getSouthWest();
  const northEast = bounds.getNorthEast();

  return {
    swLat: southWest.getLat(),
    swLng: southWest.getLng(),
    neLat: northEast.getLat(),
    neLng: northEast.getLng(),
  };
}

function isCampaignInBounds(campaign, bounds) {
  if (!bounds) return false;
  const lat = Number(campaign.lat);
  const lng = Number(campaign.lng);

  return lat >= bounds.swLat
    && lat <= bounds.neLat
    && lng >= bounds.swLng
    && lng <= bounds.neLng;
}

function createClusterContent(count, urgentCount) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `kmap-cluster${urgentCount > 0 ? " is-urgent" : ""}`;
  btn.innerHTML = `
    <span>${count}</span>
    ${urgentCount > 0 ? `<small>${urgentCount}개 임박</small>` : ""}
  `;
  return btn;
}

function createMarkerContent(campaign) {
  const urgent = (campaign.dDay ?? 999) <= 1;
  // 좌표 출처별 마커 스타일 구분
  const sourceClass = isPinCoordinateSource(campaign.coordinateSource)
    ? " is-exact"
    : (isGeocodedCoordinateSource(campaign.coordinateSource) ? " is-geocoded" : "");

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `kmap-pin${urgent ? " is-urgent" : ""}${sourceClass}`;
  btn.setAttribute("aria-label", campaign.title);
  btn.innerHTML = `<span></span>`;
  return btn;
}

function createSelectionOverlayContent(campaign) {
  const facets = getCampaignFacetProfile(campaign);
  const platform = PLATFORMS.find((entry) => entry.id === campaign.platformId);
  const urgent = (campaign.dDay ?? 999) <= 1;

  return `
    <div class="kmap-selection-card">
      <div class="kmap-selection-top">
        <span class="kmap-selection-pill is-dark">${platform?.name || campaign.platform}</span>
        <span class="kmap-selection-pill">${campaign.category}</span>
        ${urgent ? '<span class="kmap-selection-pill is-urgent">마감 임박</span>' : ""}
      </div>
      <strong>${campaign.title}</strong>
      <p>${getCampaignLocationLabel(campaign)} | ${facets.snsLabel} | ${facets.modeLabel}</p>
      <div class="kmap-selection-metrics">
        <span>${formatDday(campaign)}</span>
        <span>${campaign.applyCount || 0}/${campaign.selectedCount || 0}</span>
      </div>
    </div>
  `;
}

function hasFiniteCoordinates(campaign) {
  return (
    campaign.lat != null &&
    campaign.lng != null &&
    Number.isFinite(Number(campaign.lat)) &&
    Number.isFinite(Number(campaign.lng))
  );
}

function campaignHasPreciseMapCoords(campaign) {
  return hasFiniteCoordinates(campaign)
    && (isPinCoordinateSource(campaign.coordinateSource) || isGeocodedCoordinateSource(campaign.coordinateSource));
}

function isMeaningfulRegionalPart(value = "") {
  return !NON_REGIONAL_LABELS.has(String(value || "").trim());
}

function getRegionalBucket(campaign) {
  const province = String(campaign.province || "").trim();
  const city = String(campaign.city || "").trim();

  if (isMeaningfulRegionalPart(province) && isMeaningfulRegionalPart(city)) {
    return { key: `${province}:${city}`, label: `${province} ${city}`, province, city };
  }

  if (isMeaningfulRegionalPart(province)) {
    return { key: `${province}:`, label: province, province, city: "" };
  }

  const areaLabel = String(campaign.areaLabel || "").trim();
  if (isMeaningfulRegionalPart(areaLabel)) {
    return { key: `area:${areaLabel}`, label: areaLabel, province: "", city: "" };
  }

  const locationLabel = getCampaignLocationLabel(campaign);
  const label = isMeaningfulRegionalPart(locationLabel) ? locationLabel : "위치 미확인";
  return { key: `label:${label}`, label, province: "", city: "" };
}

function buildRegionalGroups(campaigns, limit = REGIONAL_GROUP_LIMIT) {
  const groups = new Map();

  campaigns.forEach((campaign) => {
    const bucket = getRegionalBucket(campaign);
    const current = groups.get(bucket.key);

    if (current) {
      current.count += 1;
      return;
    }

    groups.set(bucket.key, {
      ...bucket,
      count: 1,
    });
  });

  return [...groups.values()]
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label, "ko-KR"))
    .slice(0, limit);
}

function campaignMatchesRegion(campaign, province, city) {
  return (
    (province === DEFAULT_PROVINCE || campaign.province === province) &&
    (city === DEFAULT_CITY || campaign.city === city)
  );
}

function MapPage({ campaigns, onSelect, user }) {
  const { ready, error } = useKakaoMapLoader();
  const mapRef = useRef(null);
  const mapNodeRef = useRef(null);
  const overlaysRef = useRef([]);
  const selectedOverlayRef = useRef(null);
  const lastAutoFitKeyRef = useRef("");

  const mapBaseCampaigns = useMemo(
    () => campaigns.filter((campaign) => campaign.platformId !== "pavlo"),
    [campaigns],
  );

  const [campaignType, setCampaignType] = useState(DEFAULT_CAMPAIGN_TYPE);
  const [category, setCategory] = useState(DEFAULT_CATEGORY);

  const availableCampaignTypes = useMemo(
    () => CAMPAIGN_TYPE_FILTERS.filter((item) =>
      item === DEFAULT_CAMPAIGN_TYPE || mapBaseCampaigns.some((campaign) => campaignMatchesType(campaign, item)),
    ),
    [mapBaseCampaigns],
  );
  const activeCampaignType = availableCampaignTypes.includes(campaignType) ? campaignType : DEFAULT_CAMPAIGN_TYPE;
  const typeScopedCampaigns = useMemo(
    () => mapBaseCampaigns.filter((campaign) => campaignMatchesType(campaign, activeCampaignType)),
    [activeCampaignType, mapBaseCampaigns],
  );

  const availableCategories = useMemo(
    () => CATEGORIES.filter((item) =>
      item === DEFAULT_CATEGORY || typeScopedCampaigns.some((campaign) => campaign.category === item),
    ),
    [typeScopedCampaigns],
  );
  const activeCategory = availableCategories.includes(category) ? category : DEFAULT_CATEGORY;

  const scopedCampaigns = useMemo(
    () => typeScopedCampaigns.filter((campaign) =>
      activeCategory === DEFAULT_CATEGORY || campaign.category === activeCategory,
    ),
    [activeCategory, typeScopedCampaigns],
  );

  const availableProvinces = useMemo(() => {
    const groups = getProvinceGroups(scopedCampaigns).filter(Boolean);
    const activeGroups = groups.filter(
      (group) => group === DEFAULT_PROVINCE || scopedCampaigns.some((campaign) => campaign.province === group),
    );
    return activeGroups.length ? activeGroups : [DEFAULT_PROVINCE];
  }, [scopedCampaigns]);

  const [province, setProvince] = useState(DEFAULT_PROVINCE);
  const [city, setCity] = useState(DEFAULT_CITY);
  const [mapLevel, setMapLevel] = useState(getAreaLevel(DEFAULT_PROVINCE, DEFAULT_CITY));
  const [mapBounds, setMapBounds] = useState(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState("");
  const [mapInitError, setMapInitError] = useState("");

  const activeProvince = availableProvinces.includes(province) ? province : DEFAULT_PROVINCE;
  const availableCities = useMemo(() => {
    const groups = getCityGroups(scopedCampaigns, activeProvince).filter(Boolean);
    if (activeProvince === DEFAULT_PROVINCE) return [DEFAULT_CITY];
    const activeGroups = groups.filter(
      (group) => group === DEFAULT_CITY || scopedCampaigns.some((campaign) =>
        campaign.province === activeProvince && campaign.city === group,
      ),
    );
    return activeGroups.length ? activeGroups : [DEFAULT_CITY];
  }, [activeProvince, scopedCampaigns]);
  const activeCity = availableCities.includes(city) ? city : DEFAULT_CITY;

  const regionFilteredCampaigns = useMemo(
    () => scopedCampaigns.filter((campaign) => campaignMatchesRegion(campaign, activeProvince, activeCity)),
    [activeCity, activeProvince, scopedCampaigns],
  );

  const visibleCampaigns = useMemo(
    () => regionFilteredCampaigns.filter(campaignHasPreciseMapCoords),
    [regionFilteredCampaigns],
  );

  const regionalVisibleCampaigns = useMemo(
    () => regionFilteredCampaigns.filter((campaign) => !campaignHasPreciseMapCoords(campaign)),
    [regionFilteredCampaigns],
  );

  const regionalGroups = useMemo(
    () => buildRegionalGroups(regionalVisibleCampaigns),
    [regionalVisibleCampaigns],
  );

  const regionalPreviewCampaigns = useMemo(
    () => sortMapCampaigns(regionalVisibleCampaigns).slice(0, REGIONAL_LIST_LIMIT),
    [regionalVisibleCampaigns],
  );

  const mapCoverageLabel = formatPercent(visibleCampaigns.length, regionFilteredCampaigns.length);
  const mapViewLimit = activeProvince === DEFAULT_PROVINCE
    ? MAX_NATIONWIDE_VIEW_CAMPAIGNS
    : MAX_VIEW_CAMPAIGNS;

  const canRenderViewportCampaigns = mapLevel <= VIEWPORT_MARKER_MAX_LEVEL;

  const campaignsInViewport = useMemo(
    () => visibleCampaigns.filter((campaign) => isCampaignInBounds(campaign, mapBounds)),
    [mapBounds, visibleCampaigns],
  );

  const campaignsInView = useMemo(() => {
    if (!canRenderViewportCampaigns) return [];
    return sortMapCampaigns(campaignsInViewport).slice(0, mapViewLimit);
  }, [campaignsInViewport, canRenderViewportCampaigns, mapViewLimit]);

  const hiddenCampaignCount = canRenderViewportCampaigns
    ? Math.max(0, campaignsInViewport.length - campaignsInView.length)
    : campaignsInViewport.length;

  const mapItems = useMemo(
    () => clusterCampaigns(campaignsInView, mapLevel),
    [campaignsInView, mapLevel],
  );

  const selectedCampaign = useMemo(
    () => campaignsInView.find((campaign) => campaign.id === selectedCampaignId) || null,
    [campaignsInView, selectedCampaignId],
  );
  const effectiveSelectedCampaignId = selectedCampaign?.id || "";
  const mapError = error || mapInitError;
  const mapOrigin = typeof window !== "undefined" ? window.location.origin : "";
  const isMapComputing = ready && !mapError && visibleCampaigns.length > 0 && !mapBounds;
  const mapStatusLabel = mapError
    ? "지도 로드 실패"
    : isMapComputing
      ? "지도 계산 중"
      : ready
        ? "지도 로드 완료"
        : "지도 로딩 중";
  const mapStatusDetail = mapError
    ? `${mapOrigin} 도메인/SDK 설정 확인`
    : isMapComputing
      ? "캠페인 묶음 계산 중"
      : "Kakao SDK 상태";
  const shouldPromptZoomForMarkers = ready
    && !mapError
    && !isMapComputing
    && visibleCampaigns.length > 0
    && !canRenderViewportCampaigns;

  const provinceCounts = useMemo(() => {
    const counts = Object.fromEntries(availableProvinces.map((item) => [item, 0]));
    counts[DEFAULT_PROVINCE] = scopedCampaigns.length;
    scopedCampaigns.forEach((campaign) => {
      if (Object.hasOwn(counts, campaign.province)) {
        counts[campaign.province] += 1;
      }
    });
    return counts;
  }, [availableProvinces, scopedCampaigns]);

  const cityCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCities.map((item) => [item, 0]));
    scopedCampaigns.forEach((campaign) => {
      const inProvince = activeProvince === DEFAULT_PROVINCE || campaign.province === activeProvince;
      if (inProvince) counts[DEFAULT_CITY] = (counts[DEFAULT_CITY] || 0) + 1;
      if (campaign.province === activeProvince && Object.hasOwn(counts, campaign.city)) {
        counts[campaign.city] += 1;
      }
    });
    return counts;
  }, [activeProvince, availableCities, scopedCampaigns]);

  const categoryCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCategories.map((item) => [item, 0]));
    counts[DEFAULT_CATEGORY] = typeScopedCampaigns.length;
    typeScopedCampaigns.forEach((campaign) => {
      if (Object.hasOwn(counts, campaign.category)) {
        counts[campaign.category] += 1;
      }
    });
    return counts;
  }, [availableCategories, typeScopedCampaigns]);

  const campaignTypeCounts = useMemo(() => {
    const counts = Object.fromEntries(availableCampaignTypes.map((item) => [item, 0]));
    counts[DEFAULT_CAMPAIGN_TYPE] = mapBaseCampaigns.length;
    mapBaseCampaigns.forEach((campaign) => {
      for (const item of CAMPAIGN_TYPE_FILTERS) {
        if (item !== DEFAULT_CAMPAIGN_TYPE && campaignMatchesType(campaign, item)) {
          counts[item] = (counts[item] || 0) + 1;
        }
      }
    });
    return counts;
  }, [availableCampaignTypes, mapBaseCampaigns]);

  const urgentCount = useMemo(
    () => campaignsInView.filter((campaign) => (campaign.dDay ?? 999) <= 1).length,
    [campaignsInView],
  );
  // 실좌표(HTML 파싱 or Kakao geocoded) 비율 표시
  const preciseCoordCount = useMemo(
    () => campaignsInView.filter(campaignHasPreciseMapCoords).length,
    [campaignsInView],
  );

  const buildMapEventPayload = useCallback((extra = {}) => ({
    campaignType: extra.campaignType ?? activeCampaignType,
    category: extra.category ?? activeCategory,
    region: extra.region ?? activeProvince,
    city: extra.city ?? activeCity,
    campaignId: extra.campaignId,
    platformId: extra.platformId,
    metadata: {
      mapLevel,
      resultCount: regionFilteredCampaigns.length,
      exactCount: visibleCampaigns.length,
      regionalCount: regionalVisibleCampaigns.length,
      inViewCount: campaignsInView.length,
      ...extra.metadata,
    },
  }), [
    activeCategory,
    activeCampaignType,
    activeCity,
    activeProvince,
    campaignsInView.length,
    mapLevel,
    regionFilteredCampaigns.length,
    regionalVisibleCampaigns.length,
    visibleCampaigns.length,
  ]);

  const trackMapFilter = useCallback((filterLevel, nextValues = {}, metadata = {}) => {
    trackAnalyticsEvent("map_filter", buildMapEventPayload({
      campaignType: nextValues.campaignType ?? activeCampaignType,
      category: nextValues.category ?? activeCategory,
      region: nextValues.region ?? activeProvince,
      city: nextValues.city ?? activeCity,
      metadata: {
        filterLevel,
        previousCampaignType: activeCampaignType,
        previousCategory: activeCategory,
        previousProvince: activeProvince,
        previousCity: activeCity,
        nextCampaignType: nextValues.campaignType ?? activeCampaignType,
        nextCategory: nextValues.category ?? activeCategory,
        nextProvince: nextValues.region ?? activeProvince,
        nextCity: nextValues.city ?? activeCity,
        ...metadata,
      },
    }), user);
  }, [activeCampaignType, activeCategory, activeCity, activeProvince, buildMapEventPayload, user]);

  const handleCampaignTypeChange = useCallback((item) => {
    if (item !== activeCampaignType) {
      trackMapFilter("campaign_type", {
        campaignType: item,
        category: DEFAULT_CATEGORY,
        region: DEFAULT_PROVINCE,
        city: DEFAULT_CITY,
      });
    }
    setCampaignType(item);
    setCategory(DEFAULT_CATEGORY);
    setProvince(DEFAULT_PROVINCE);
    setCity(DEFAULT_CITY);
  }, [activeCampaignType, trackMapFilter]);

  const handleCategoryChange = useCallback((item) => {
    if (item !== activeCategory) {
      trackMapFilter("category", {
        category: item,
        region: DEFAULT_PROVINCE,
        city: DEFAULT_CITY,
      });
    }
    setCategory(item);
    setProvince(DEFAULT_PROVINCE);
    setCity(DEFAULT_CITY);
  }, [activeCategory, trackMapFilter]);

  const handleProvinceChange = useCallback((item) => {
    if (item !== activeProvince) {
      trackMapFilter("province", {
        region: item,
        city: DEFAULT_CITY,
      });
    }
    setProvince(item);
    setCity(DEFAULT_CITY);
  }, [activeProvince, trackMapFilter]);

  const handleCityChange = useCallback((item) => {
    if (item !== activeCity) {
      trackMapFilter("city", { city: item });
    }
    setCity(item);
  }, [activeCity, trackMapFilter]);

  const handleRegionalGroupFilter = useCallback((group) => {
    const nextProvince = group.province || DEFAULT_PROVINCE;
    const nextCity = group.city || DEFAULT_CITY;
    trackMapFilter("regional_group", {
      region: nextProvince,
      city: nextCity,
    }, {
      groupCount: group.count,
      groupHasCity: Boolean(group.city),
    });
    setProvince(nextProvince);
    setCity(nextCity);
  }, [trackMapFilter]);

  const trackMapPinOpen = useCallback((campaign, source) => {
    trackAnalyticsEvent("map_pin_open", buildMapEventPayload({
      campaignId: campaign.id,
      platformId: campaign.platformId,
      category: campaign.category || activeCategory,
      region: campaign.province || activeProvince,
      city: campaign.city || activeCity,
      metadata: {
        source,
        dDay: campaign.dDay,
        applyCount: campaign.applyCount,
        selectedCount: campaign.selectedCount,
        coordinateSource: campaign.coordinateSource || "",
      },
    }), user);
  }, [activeCategory, activeCity, activeProvince, buildMapEventPayload, user]);

  const handleClusterClick = useCallback((item) => {
    const map = mapRef.current;
    const kakao = window.kakao;
    if (!map || !kakao?.maps) return;

    const urgentItems = item.items.filter((campaign) => (campaign.dDay ?? 999) <= 1).length;
    const nextLevel = Math.max(1, map.getLevel() - 2);
    trackAnalyticsEvent("map_cluster_interaction", buildMapEventPayload({
      metadata: {
        clusterSize: item.items.length,
        urgentCount: urgentItems,
        previousLevel: map.getLevel(),
        nextLevel,
      },
    }), user);
    map.setLevel(nextLevel, { anchor: new kakao.maps.LatLng(item.lat, item.lng), animate: true });
    map.panTo(new kakao.maps.LatLng(item.lat, item.lng));
  }, [buildMapEventPayload, user]);

  const syncViewport = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    setMapLevel(map.getLevel());
    setMapBounds(getCurrentMapBounds(map));
  }, []);

  useEffect(() => {
    if (!ready || !mapNodeRef.current || mapRef.current) return undefined;

    const kakao = window.kakao;
    if (!kakao?.maps) return undefined;

    let map;
    try {
      map = new kakao.maps.Map(mapNodeRef.current, {
        center: new kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng),
        level: getAreaLevel(DEFAULT_PROVINCE, DEFAULT_CITY),
        draggable: true,
        scrollwheel: true,
      });
      map.setMaxLevel(MAX_MAP_ZOOM_OUT_LEVEL);

      map.addControl(
        new kakao.maps.ZoomControl(),
        kakao.maps.ControlPosition.RIGHT,
      );
      map.addControl(
        new kakao.maps.MapTypeControl(),
        kakao.maps.ControlPosition.TOPRIGHT,
      );

      kakao.maps.event.addListener(map, "idle", syncViewport);

      mapRef.current = map;
      syncViewport();
    } catch (initError) {
      window.setTimeout(() => {
        setMapInitError(`지도 초기화 실패: ${initError?.message || "알 수 없는 오류"}`);
      }, 0);
      return undefined;
    }

    return () => {
      mapRef.current = null;
    };
  }, [ready, syncViewport]);

  useEffect(() => {
    const kakao = window.kakao;
    const map = mapRef.current;
    if (!kakao?.maps || !map) return;

    const autoFitKey = `${activeProvince}:${activeCity}:${visibleCampaigns.length}`;
    if (lastAutoFitKeyRef.current === autoFitKey) return;
    lastAutoFitKeyRef.current = autoFitKey;

    if (activeProvince === DEFAULT_PROVINCE) {
      map.setLevel(getAreaLevel(DEFAULT_PROVINCE, DEFAULT_CITY));
      map.setCenter(new kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng));
      syncViewport();
      return;
    }

    if (!visibleCampaigns.length) {
      map.setLevel(getAreaLevel(activeProvince, activeCity));
      map.setCenter(new kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng));
      syncViewport();
      return;
    }

    if (visibleCampaigns.length === 1) {
      map.setLevel(4);
      map.setCenter(new kakao.maps.LatLng(visibleCampaigns[0].lat, visibleCampaigns[0].lng));
      syncViewport();
      return;
    }

    const bounds = new kakao.maps.LatLngBounds();
    visibleCampaigns.forEach((campaign) => {
      bounds.extend(new kakao.maps.LatLng(campaign.lat, campaign.lng));
    });
    map.setBounds(bounds, 40, 40, 40, 40);
    syncViewport();
  }, [activeCity, activeProvince, syncViewport, visibleCampaigns]);

  useEffect(() => {
    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    overlaysRef.current = [];

    const kakao = window.kakao;
    const map = mapRef.current;
    if (!kakao?.maps || !map) return;

    mapItems.forEach((item) => {
      if (item.type === "cluster") {
        const urgentItems = item.items.filter((campaign) => (campaign.dDay ?? 999) <= 1).length;
        const overlay = new kakao.maps.CustomOverlay({
          position: new kakao.maps.LatLng(item.lat, item.lng),
          content: createClusterContent(item.items.length, urgentItems),
          xAnchor: 0.5,
          yAnchor: 0.5,
          clickable: true,
        });

        overlay.setMap(map);
        overlaysRef.current.push(overlay);

        const contentNode = overlay.getContent();
        contentNode?.addEventListener("click", () => handleClusterClick(item));
        return;
      }

      const campaign = item.campaign;
      const overlay = new kakao.maps.CustomOverlay({
        position: new kakao.maps.LatLng(campaign.lat, campaign.lng),
        content: createMarkerContent(campaign),
        xAnchor: 0.5,
        yAnchor: 0.5,
        clickable: true,
      });

      overlay.setMap(map);
      overlaysRef.current.push(overlay);

      const contentNode = overlay.getContent();
      if (campaign.id === effectiveSelectedCampaignId) {
        contentNode?.classList.add("is-selected");
      }

      contentNode?.addEventListener("click", () => {
        trackMapPinOpen(campaign, "marker");
        setSelectedCampaignId(campaign.id);
        map.panTo(new kakao.maps.LatLng(campaign.lat, campaign.lng));
      });
    });
  }, [effectiveSelectedCampaignId, handleClusterClick, mapItems, trackMapPinOpen]);

  useEffect(() => {
    const kakao = window.kakao;
    const map = mapRef.current;

    if (selectedOverlayRef.current) {
      selectedOverlayRef.current.setMap(null);
      selectedOverlayRef.current = null;
    }

    if (!kakao?.maps || !map || !selectedCampaign) return;

    const overlay = new kakao.maps.CustomOverlay({
      position: new kakao.maps.LatLng(selectedCampaign.lat, selectedCampaign.lng),
      content: createSelectionOverlayContent(selectedCampaign),
      xAnchor: 0.5,
      yAnchor: 1.18,
      clickable: true,
    });

    overlay.setMap(map);
    selectedOverlayRef.current = overlay;
  }, [selectedCampaign]);

  return (
    <div className="page page--map">
      <section className="map-shell">
        <div className="map-toolbar">
          <div className="map-toolbar-copy">
            <div className="command-eyebrow">Kakao Map</div>
            <h1 className="map-toolbar-title">정확 위치와 지역 기준 캠페인을 나눠 봅니다</h1>
            <p className="map-toolbar-sub">
              상세 위치가 확인된 캠페인만 지도 핀으로 표시하고, 주소가 넓거나 추정된 캠페인은 지역 묶음 목록으로 분리했습니다.
            </p>
          </div>
          <div className="map-toolbar-stats">
            <div className="map-stat">
              <strong>{formatCount(regionFilteredCampaigns.length)}</strong>
              <span>현재 조건</span>
            </div>
            <div className="map-stat">
              <strong>{formatCount(visibleCampaigns.length)}</strong>
              <span>정확 위치</span>
            </div>
            <div className="map-stat">
              <strong>{formatCount(campaignsInView.length)}</strong>
              <span>핀 표시</span>
            </div>
            <div className="map-stat">
              <strong>{formatCount(urgentCount)}</strong>
              <span>마감 임박</span>
            </div>
            <div className="map-stat is-muted" title="지역은 알 수 있지만 정확한 방문 지점으로 보기 어려운 캠페인">
              <strong>{formatCount(regionalVisibleCampaigns.length)}</strong>
              <span>지역 기준</span>
            </div>
            <div className="map-stat is-muted">
              <strong>{mapCoverageLabel}</strong>
              <span>정확 위치율</span>
            </div>
          </div>
        </div>

        <div className="map-trust-strip">
          <div className={mapError ? "is-error" : ""}>
            <strong>{mapStatusLabel}</strong>
            <span>{mapStatusDetail}</span>
          </div>
          <div>
            <strong>{formatCount(visibleCampaigns.length)}개 정확 위치</strong>
            <span>{regionalVisibleCampaigns.length > 0 ? `지역 기준 ${formatCount(regionalVisibleCampaigns.length)}개는 아래 목록에서 확인` : "현재 조건은 모두 정확 위치로 표시 가능"}</span>
          </div>
          <div>
            <strong>{canRenderViewportCampaigns ? formatCount(campaignsInViewport.length) : "확대 필요"}</strong>
            <span>현재 화면 핀 후보</span>
          </div>
        </div>

        <div className="map-region-stack">
          <div className="map-region-strip map-region-strip--category">
            {availableCampaignTypes.map((item) => (
              <button
                key={item}
                type="button"
                className={`map-region-chip${activeCampaignType === item ? " active" : ""}`}
                onClick={() => handleCampaignTypeChange(item)}
              >
                <span>{item}</span>
                <strong>{formatCount(campaignTypeCounts[item] || 0)}</strong>
              </button>
            ))}
          </div>

          <div className="map-region-strip map-region-strip--category">
            {availableCategories.map((item) => (
              <button
                key={item}
                type="button"
                className={`map-region-chip${activeCategory === item ? " active" : ""}`}
                onClick={() => handleCategoryChange(item)}
              >
                <span>{item}</span>
                <strong>{formatCount(categoryCounts[item] || 0)}</strong>
              </button>
            ))}
          </div>

          <div className="map-region-strip">
            {availableProvinces.map((item) => (
              <button
                key={item}
                type="button"
                  className={`map-region-chip${activeProvince === item ? " active" : ""}`}
                onClick={() => handleProvinceChange(item)}
              >
                <span>{item}</span>
                <strong>{formatCount(provinceCounts[item] || 0)}</strong>
              </button>
            ))}
          </div>

          {activeProvince !== DEFAULT_PROVINCE && (
            <div className="map-region-strip map-region-strip--city">
              {availableCities.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`map-region-chip${activeCity === item ? " active" : ""}`}
                  onClick={() => handleCityChange(item)}
                >
                <span>{item}</span>
                <strong>{formatCount(cityCounts[item] || 0)}</strong>
              </button>
            ))}
          </div>
          )}
        </div>

        <div className="map-layout-modern">
          <div className="map-canvas-panel">
            <div className="kmap-canvas" ref={mapNodeRef} />

            <div className="kmap-floating-panel" hidden>
              <div className="kmap-floating-head">
                <div>
                  <div className="kmap-floating-label">Viewport</div>
                  <strong>현재 화면 요약</strong>
                </div>
                <span className="kmap-floating-badge">Lv.{mapLevel}</span>
              </div>

              <div className="kmap-floating-grid">
                <div>
                  <strong>{campaignsInView.length}</strong>
                  <span>화면 안 핀</span>
                </div>
                <div>
                  <strong>{preciseCoordCount}</strong>
                  <span>정밀 좌표</span>
                </div>
              </div>

              {regionalVisibleCampaigns.length > 0 && (
                <p className="kmap-floating-copy kmap-floating-warn">
                  지역 기준 {formatCount(regionalVisibleCampaigns.length)}개는 오른쪽 목록에서 확인할 수 있습니다.
                </p>
              )}

              <p className="kmap-floating-copy">
                마커를 누르면 오른쪽 리스트와 선택 카드가 함께 갱신됩니다.
              </p>
            </div>

            {!ready && !mapError && (
              <div className="kmap-overlay-state">
                <strong>카카오맵 로딩 중</strong>
                <span>SDK를 불러오면서 지도를 초기화하고 있습니다.</span>
              </div>
            )}

            {mapError && (
              <div className="kmap-overlay-state is-error">
                <strong>지도를 불러오지 못했습니다</strong>
                <span>{mapError}</span>
              </div>
            )}

            {isMapComputing && (
              <div className="kmap-overlay-state">
                <strong>지도 데이터 계산 중</strong>
                <span>현재 화면의 캠페인을 묶어 표시하고 있습니다.</span>
              </div>
            )}

            {shouldPromptZoomForMarkers && (
              <div className="kmap-overlay-state">
                <strong>확대하면 핀이 표시됩니다</strong>
                <span>넓은 배율에서는 성능을 위해 캠페인 핀과 묶음을 숨깁니다.</span>
              </div>
            )}
          </div>

          <div className="map-side-panel">
            <div className="map-side-header">
              <div>
                <div className="map-side-title">정확 위치 캠페인</div>
                <div className="map-side-sub">
                  {canRenderViewportCampaigns
                    ? "상세 좌표가 확인된 캠페인만 지도 핀으로 표시합니다."
                    : "지도를 확대하면 정확 위치 핀을 표시합니다."}
                </div>
              </div>
              <div className="map-side-count">{campaignsInView.length}</div>
            </div>

            {hiddenCampaignCount > 0 && (
              <div className="map-density-note">
                {canRenderViewportCampaigns
                  ? `화면 안 캠페인이 많아 우선순위 ${mapViewLimit}개만 표시합니다.`
                  : "현재 배율에서는 과밀 구간을 숨겼습니다. 더 확대해 주세요."}
              </div>
            )}

            {selectedCampaign && (
              <div className="map-focus-card">
                <div className="map-focus-top">
                  <span>{PLATFORMS.find((entry) => entry.id === selectedCampaign.platformId)?.name || selectedCampaign.platform}</span>
                  <button type="button" onClick={() => onSelect(selectedCampaign)}>상세 보기</button>
                </div>
                <strong>{selectedCampaign.title}</strong>
                <div className="map-focus-meta">
                  <span>{getCampaignLocationLabel(selectedCampaign)}</span>
                  <span>{selectedCampaign.category}</span>
                  <span>{formatDday(selectedCampaign)}</span>
                </div>
                <p>{selectedCampaign.point || "제공 내역은 상세 페이지에서 확인"}</p>
              </div>
            )}

            {campaignsInView.length === 0 ? (
              <div className="map-side-empty">
                {canRenderViewportCampaigns
                  ? "현재 화면에 정확 위치 핀이 없습니다. 지역 기준 캠페인은 아래 묶음에서 확인하세요."
                  : "전국 또는 넓은 지역에서는 성능을 위해 핀을 숨깁니다. 원하는 동네까지 확대하면 최대 300개까지 표시됩니다."}
              </div>
            ) : (
              <div className="map-side-list">
                {campaignsInView.slice(0, LIST_LIMIT).map((campaign) => {
                  const platform = PLATFORMS.find((entry) => entry.id === campaign.platformId);
                  const facets = getCampaignFacetProfile(campaign);
                  const isUrgent = (campaign.dDay ?? 999) <= 1;

                  return (
                    <button
                      key={campaign.id}
                      type="button"
                      className={`map-list-item${isUrgent ? " urgent" : ""}${effectiveSelectedCampaignId === campaign.id ? " active" : ""}`}
                      onClick={() => {
                        trackMapPinOpen(campaign, "side_list");
                        setSelectedCampaignId(campaign.id);
                      }}
                    >
                      <div className="map-list-item-top">
                        <span className="map-list-platform">{platform?.name || campaign.platform}</span>
                        <span className="map-list-dday">{formatDday(campaign)}</span>
                      </div>
                      <strong>{campaign.title}</strong>
                      <div className="map-list-meta">{getCampaignLocationLabel(campaign)} | {campaign.category}</div>
                      <div className="map-list-meta">{facets.snsLabel} | {facets.modeLabel}</div>
                      <div className="map-list-bottom">
                        <span>{campaign.point || "제공 내역은 상세 페이지에서 확인"}</span>
                        <span>지원/모집 {campaign.applyCount || 0}/{campaign.selectedCount || 0}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            <div className="map-regional-panel">
              <div className="map-regional-header">
                <div>
                  <div className="map-regional-title">지역 기준 캠페인</div>
                  <p>상세 주소가 없거나 넓은 주소로 잡힌 항목은 지도 핀 대신 지역 묶음으로 보여줍니다.</p>
                </div>
                <div className="map-regional-count">{formatCount(regionalVisibleCampaigns.length)}</div>
              </div>

              {regionalGroups.length > 0 ? (
                <div className="map-regional-groups">
                  {regionalGroups.map((group) => {
                    const canFilterGroup = Boolean(group.province);
                    const isActiveGroup = group.province === activeProvince && (
                      group.city ? group.city === activeCity : activeCity === DEFAULT_CITY
                    );

                    return (
                      <button
                        key={group.key}
                        type="button"
                        className={`map-regional-group${isActiveGroup ? " active" : ""}`}
                        disabled={!canFilterGroup}
                        onClick={() => handleRegionalGroupFilter(group)}
                      >
                        <strong>{group.label}</strong>
                        <span>{formatCount(group.count)}개</span>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="map-regional-empty">현재 조건에는 지역 기준으로 분리된 캠페인이 없습니다.</div>
              )}

              {regionalPreviewCampaigns.length > 0 && (
                <div className="map-regional-list">
                  {regionalPreviewCampaigns.map((campaign) => {
                    const platform = PLATFORMS.find((entry) => entry.id === campaign.platformId);
                    const facets = getCampaignFacetProfile(campaign);
                    const bucket = getRegionalBucket(campaign);

                    return (
                      <button
                        key={campaign.id}
                        type="button"
                        className="map-list-item map-list-item--regional"
                        onClick={() => onSelect(campaign)}
                      >
                        <div className="map-list-item-top">
                          <span className="map-list-platform">{platform?.name || campaign.platform}</span>
                          <span className="map-list-dday">{formatDday(campaign)}</span>
                        </div>
                        <strong>{campaign.title}</strong>
                        <div className="map-list-meta">{bucket.label} | {campaign.category}</div>
                        <div className="map-list-meta">{facets.snsLabel} | {facets.modeLabel} | 지역 기준</div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        <MonetizedAdSlot
          slotId="map_bottom"
          context={{ page: "map", province: activeProvince, city: activeCity }}
          variant="compact"
        />
      </section>
    </div>
  );
}

export default MapPage;
