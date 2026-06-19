import { BG_MAP, EMOJI_MAP, PLATFORMS } from "../../../shared/config/platforms";
import { supabase } from "../../../shared/api/supabase";

const CANONICAL_CATEGORIES = ["맛집", "카페", "뷰티", "숙박", "생활용품", "패션", "서비스", "체험", "기타"];
const GENERIC_CATEGORY_LABELS = new Set([
  "",
  "기타",
  "지역_기타",
  "방문",
  "방문형",
  "배송",
  "배달",
  "구매평",
  "기자단",
  "제품",
  "전체",
  "전국",
]);
const PLATFORM_CATEGORY_DEFAULTS = {
  dinner: "맛집",
  gangnam: "맛집",
};
const LAUNCH_CAMPAIGN_TYPE = "visit";
const LAUNCH_CAMPAIGN_MODE_LABEL = "방문형";
const CATEGORY_ALIASES = {
  제품: "생활용품",
  뷰티체험: "뷰티",
  뷰티샵: "뷰티",
  병원: "서비스",
  생활서비스: "서비스",
  서비스체험: "서비스",
  문화: "체험",
  방문체험: "체험",
};
const CATEGORY_TO_SLUG = {
  전체: "all",
  맛집: "food",
  카페: "cafe",
  뷰티: "beauty",
  숙박: "stay",
  생활용품: "living",
  패션: "fashion",
  서비스: "service",
  체험: "experience",
  기타: "etc",
};
const SLUG_TO_CATEGORY = Object.fromEntries(
  Object.entries(CATEGORY_TO_SLUG).map(([category, slug]) => [slug, category]),
);
const CAMPAIGN_TYPE_TO_SLUG = {
  전체: "all",
  방문형: "visit",
  배송형: "delivery",
};
const SLUG_TO_CAMPAIGN_TYPE = Object.fromEntries(
  Object.entries(CAMPAIGN_TYPE_TO_SLUG).map(([label, slug]) => [slug, label]),
);

const REGION_GROUPS = [
  { label: "전체", keywords: [] },
  { label: "강남·서초", keywords: ["강남", "서초", "청담", "역삼", "논현", "신사", "압구정"] },
  { label: "성수·건대", keywords: ["성수", "건대", "광진", "구의", "군자"] },
  { label: "홍대·합정", keywords: ["홍대", "합정", "마포", "상수", "연남", "서교"] },
  { label: "용산·이태원", keywords: ["용산", "이태원", "한남", "동작", "반포"] },
  { label: "송파·잠실", keywords: ["송파", "잠실", "문정", "가락", "방이"] },
];

const PROVINCE_GROUPS = [
  { label: "서울", aliases: ["서울특별시", "서울"] },
  { label: "경기", aliases: ["경기도", "경기"] },
  { label: "인천", aliases: ["인천광역시", "인천"] },
  { label: "부산", aliases: ["부산광역시", "부산"] },
  { label: "대구", aliases: ["대구광역시", "대구"] },
  { label: "광주", aliases: ["광주광역시", "광주"] },
  { label: "대전", aliases: ["대전광역시", "대전"] },
  { label: "울산", aliases: ["울산광역시", "울산"] },
  { label: "세종", aliases: ["세종특별자치시", "세종"] },
  { label: "강원", aliases: ["강원특별자치도", "강원도", "강원"] },
  { label: "충북", aliases: ["충청북도", "충북"] },
  { label: "충남", aliases: ["충청남도", "충남"] },
  { label: "전북", aliases: ["전북특별자치도", "전라북도", "전북"] },
  { label: "전남", aliases: ["전라남도", "전남"] },
  { label: "경북", aliases: ["경상북도", "경북"] },
  { label: "경남", aliases: ["경상남도", "경남"] },
  { label: "제주", aliases: ["제주특별자치도", "제주도", "제주"] },
];

const PROVINCE_CITY_GROUPS = {
  서울: [
    "종로", "중구", "용산", "성동", "광진", "동대문", "중랑", "성북", "강북", "도봉", "노원", "은평", "서대문",
    "마포", "양천", "강서", "구로", "금천", "영등포", "동작", "관악", "서초", "강남", "송파", "강동",
  ],
  경기: [
    "수원", "성남", "의정부", "안양", "부천", "광명", "평택", "동두천", "안산", "고양", "과천", "구리",
    "남양주", "오산", "시흥", "군포", "의왕", "하남", "용인", "파주", "이천", "안성", "김포", "화성",
    "광주", "양주", "포천", "여주", "연천", "가평", "양평",
  ],
  인천: ["중구", "동구", "미추홀", "연수", "남동", "부평", "계양", "서구", "강화", "옹진"],
  부산: ["중구", "서구", "동구", "영도", "부산진", "동래", "남구", "북구", "해운대", "사하", "금정", "강서", "연제", "수영", "사상", "기장"],
  대구: ["중구", "동구", "서구", "남구", "북구", "수성", "달서", "달성", "군위"],
  광주: ["동구", "서구", "남구", "북구", "광산"],
  대전: ["동구", "중구", "서구", "유성", "대덕"],
  울산: ["중구", "남구", "동구", "북구", "울주"],
  세종: ["세종"],
  강원: ["춘천", "원주", "강릉", "동해", "태백", "속초", "삼척", "홍천", "횡성", "영월", "평창", "정선", "철원", "화천", "양구", "인제", "고성", "양양"],
  충북: ["청주", "충주", "제천", "보은", "옥천", "영동", "증평", "진천", "괴산", "음성", "단양"],
  충남: ["천안", "공주", "보령", "아산", "서산", "논산", "계룡", "당진", "금산", "부여", "서천", "청양", "홍성", "예산", "태안"],
  전북: ["전주", "군산", "익산", "정읍", "남원", "김제", "완주", "진안", "무주", "장수", "임실", "순창", "고창", "부안"],
  전남: ["목포", "여수", "순천", "나주", "광양", "담양", "곡성", "구례", "고흥", "보성", "화순", "장흥", "강진", "해남", "영암", "무안", "함평", "영광", "장성", "완도", "진도", "신안"],
  경북: ["포항", "경주", "김천", "안동", "구미", "영주", "영천", "상주", "문경", "경산", "의성", "청송", "영양", "영덕", "청도", "고령", "성주", "칠곡", "예천", "봉화", "울진", "울릉"],
  경남: ["창원", "진주", "통영", "사천", "김해", "밀양", "거제", "양산", "의령", "함안", "창녕", "고성", "남해", "하동", "산청", "함양", "거창", "합천"],
  제주: ["제주", "서귀포"],
};

const CITY_ALIAS_RULES = [
  { province: "서울", city: "강남", keywords: ["강남", "역삼", "선릉", "논현", "신사", "압구정", "청담"] },
  { province: "서울", city: "서초", keywords: ["서초", "교대", "방배", "반포"] },
  { province: "서울", city: "송파", keywords: ["송파", "잠실", "문정", "가락", "방이"] },
  { province: "서울", city: "마포", keywords: ["마포", "홍대", "합정", "상수", "연남", "서교"] },
  { province: "서울", city: "용산", keywords: ["용산", "이태원", "한남", "이촌"] },
  { province: "서울", city: "성동", keywords: ["성수", "성동", "왕십리"] },
  { province: "서울", city: "광진", keywords: ["건대", "광진", "구의", "군자"] },
  { province: "경기", city: "성남", keywords: ["성남", "분당", "판교", "정자", "서현", "야탑"] },
  { province: "경기", city: "수원", keywords: ["수원", "광교", "영통", "권선"] },
  { province: "경기", city: "용인", keywords: ["용인", "기흥", "수지", "죽전", "동백"] },
  { province: "경기", city: "고양", keywords: ["고양", "일산", "화정", "주엽"] },
  { province: "경기", city: "안양", keywords: ["안양", "범계", "평촌", "인덕원"] },
  { province: "경기", city: "부천", keywords: ["부천", "상동", "중동"] },
  { province: "인천", city: "인천", keywords: ["인천", "구월", "송도", "부평", "계양", "청라"] },
  { province: "부산", city: "부산진", keywords: ["부산진", "서면"] },
  { province: "부산", city: "해운대", keywords: ["해운대"] },
  { province: "부산", city: "수영", keywords: ["수영", "광안"] },
];

const LOCATION_COORDS = [
  { key: "서울", lat: 37.5665, lng: 126.9780 },
  { key: "강남", lat: 37.4979, lng: 127.0276 },
  { key: "서초", lat: 37.4837, lng: 127.0324 },
  { key: "송파", lat: 37.5145, lng: 127.1059 },
  { key: "잠실", lat: 37.5133, lng: 127.1002 },
  { key: "성수", lat: 37.5446, lng: 127.0557 },
  { key: "건대", lat: 37.5400, lng: 127.0693 },
  { key: "홍대", lat: 37.5563, lng: 126.9220 },
  { key: "합정", lat: 37.5496, lng: 126.9139 },
  { key: "마포", lat: 37.5637, lng: 126.9084 },
  { key: "이태원", lat: 37.5347, lng: 126.9947 },
  { key: "용산", lat: 37.5299, lng: 126.9648 },
  { key: "부산", lat: 35.1796, lng: 129.0756 },
  { key: "서면", lat: 35.1578, lng: 129.0592 },
  { key: "해운대", lat: 35.1632, lng: 129.1636 },
  { key: "대구", lat: 35.8714, lng: 128.6014 },
  { key: "인천", lat: 37.4563, lng: 126.7052 },
  { key: "수원", lat: 37.2636, lng: 127.0286 },
  { key: "판교", lat: 37.3943, lng: 127.1112 },
  { key: "성남", lat: 37.4200, lng: 127.1265 },
  { key: "용인", lat: 37.2411, lng: 127.1776 },
  { key: "고양", lat: 37.6584, lng: 126.8320 },
  { key: "일산", lat: 37.6580, lng: 126.7702 },
  { key: "대전", lat: 36.3504, lng: 127.3845 },
  { key: "광주", lat: 35.1595, lng: 126.8526 },
  { key: "울산", lat: 35.5384, lng: 129.3114 },
  { key: "제주", lat: 33.4996, lng: 126.5312 },
  { key: "청주", lat: 36.6424, lng: 127.4890 },
  { key: "천안", lat: 36.8151, lng: 127.1139 },
  { key: "춘천", lat: 37.8813, lng: 127.7298 },
  { key: "강릉", lat: 37.7519, lng: 128.8761 },
  { key: "전주", lat: 35.8242, lng: 127.1480 },
  // 추가 지역 키워드 (좌표 정밀도 향상)
  { key: "분당", lat: 37.3844, lng: 127.1233 },
  { key: "노원", lat: 37.6541, lng: 127.0568 },
  { key: "은평", lat: 37.6027, lng: 126.9290 },
  { key: "강서", lat: 37.5510, lng: 126.8495 },
  { key: "구로", lat: 37.4955, lng: 126.8874 },
  { key: "영등포", lat: 37.5264, lng: 126.8962 },
  { key: "동대문", lat: 37.5745, lng: 127.0398 },
  { key: "종로", lat: 37.5729, lng: 126.9793 },
  { key: "중구", lat: 37.5641, lng: 126.9979 },
  { key: "명동", lat: 37.5636, lng: 126.9856 },
  { key: "여의도", lat: 37.5219, lng: 126.9242 },
  { key: "신촌", lat: 37.5556, lng: 126.9369 },
  { key: "신림", lat: 37.4843, lng: 126.9291 },
  { key: "동작", lat: 37.5124, lng: 126.9393 },
  { key: "관악", lat: 37.4784, lng: 126.9516 },
  { key: "광명", lat: 37.4784, lng: 126.8644 },
  { key: "안산", lat: 37.3220, lng: 126.8309 },
  { key: "안양", lat: 37.3943, lng: 126.9568 },
  { key: "평택", lat: 36.9921, lng: 127.1128 },
  { key: "의정부", lat: 37.7381, lng: 127.0338 },
  { key: "김포", lat: 37.6154, lng: 126.7155 },
  { key: "파주", lat: 37.7599, lng: 126.7796 },
  { key: "광주시", lat: 37.4296, lng: 127.2556 }, // 경기 광주 (전남 광주와 구분)
  { key: "하남", lat: 37.5397, lng: 127.2146 },
  { key: "남양주", lat: 37.6358, lng: 127.2165 },
];

const KNOWN_BAD_MAP_COORDINATES = [
  { lat: 33.450701, lng: 126.570667 },
  { lat: 37.5665, lng: 126.978 },
];
const DEADLINE_FRESH_WINDOW_MS = 36 * 60 * 60 * 1000;

function isKnownBadMapCoordinate(lat, lng) {
  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) return false;

  return KNOWN_BAD_MAP_COORDINATES.some((coord) => (
    Math.abs(parsedLat - coord.lat) < 0.000001 &&
    Math.abs(parsedLng - coord.lng) < 0.000001
  ));
}

// ─── 헬퍼: 주어진 캠페인이 유효한 지도 좌표를 갖고 있는지 확인 ───────────────
function hasValidCoordinates(campaign) {
  return (
    campaign.lat != null &&
    campaign.lng != null &&
    Number.isFinite(Number(campaign.lat)) &&
    Number.isFinite(Number(campaign.lng)) &&
    campaign.coordinateSource !== "unresolved" &&
    !isKnownBadMapCoordinate(campaign.lat, campaign.lng)
  );
}

function getCompLevel(applyCount = 0, selectedCount = 3) {
  const safeSelectedCount = selectedCount || 1;
  const ratio = applyCount / safeSelectedCount;

  if (ratio < 30) return { label: "낮음", color: "#1D9E75", bg: "#E8F8F0", icon: "↓" };
  if (ratio < 100) return { label: "보통", color: "#D97706", bg: "#FEF3C7", icon: "→" };
  return { label: "높음", color: "#DC2626", bg: "#FEE2E2", icon: "↑" };
}

function getCampaignFreshnessTimestamp(campaign) {
  return [
    campaign?.lastSeenAt,
    campaign?.crawledAt,
    campaign?.sourcePostedAt,
    campaign?.sourceStartedAt,
    campaign?.firstSeenAt,
  ].reduce((latest, value) => {
    const parsed = Date.parse(value || "");
    return Number.isFinite(parsed) ? Math.max(latest, parsed) : latest;
  }, 0);
}

function isFreshDeadlineCampaign(campaign, now = Date.now()) {
  const dDay = normalizeCampaignDDay(campaign?.dDay);
  if (dDay < 0 || dDay > 1) return false;

  const freshAt = getCampaignFreshnessTimestamp(campaign);
  if (!freshAt) return false;

  return now - freshAt <= DEADLINE_FRESH_WINDOW_MS;
}

function getCampaignRewardValue(campaign) {
  const source = `${campaign?.point || ""} ${campaign?.reward || ""} ${campaign?.title || ""}`;
  const matches = [...String(source).matchAll(/(\d+(?:[.,]\d+)*)\s*(만원|만|원|포인트|point|pts|p)/gi)];

  return matches.reduce((maxValue, match) => {
    const numericValue = Number(String(match[1]).replace(/,/g, ""));
    if (!Number.isFinite(numericValue)) return maxValue;

    const unit = String(match[2]).toLowerCase();
    const value = unit.includes("만") ? numericValue * 10000 : numericValue;
    return Math.max(maxValue, value);
  }, 0);
}

function extractCampaignLocation(title = "") {
  const match = String(title).match(/^\[([^\]]+)\]/);
  return match?.[1]?.trim() || "";
}

function normalizeAreaText(value = "") {
  return String(value)
    .replace(/\[[^\]]+\]/g, (match) => ` ${match.replace(/[[\]]/g, "")} `)
    .replace(/[|(),]/g, " ")
    .replace(/\//g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeCityToken(token = "") {
  return String(token)
    .replace(/특별자치시|특별자치도|특별시|광역시|자치시|자치도/g, "")
    .replace(/시|군|구$/g, "")
    .trim();
}

function getProvinceCityList(province = "") {
  return PROVINCE_CITY_GROUPS[province] || [];
}

function findCityInProvince(province = "", source = "") {
  const normalized = normalizeAreaText(source).replace(/\s+/g, "");
  if (!province || !normalized) return "";

  return [...getProvinceCityList(province)]
    .sort((left, right) => right.length - left.length)
    .find((city) => {
      const cityName = String(city).trim();
      const cityStem = normalizeCityToken(cityName);
      const candidates = new Set([
        cityName,
        `${cityStem}시`,
        `${cityStem}군`,
        `${cityStem}구`,
      ]);
      if (cityName === cityStem) candidates.add(cityStem);
      return [...candidates].some((candidate) => candidate && normalized.includes(candidate));
    }) || "";
}

function findProvinceLabel(source = "") {
  return PROVINCE_GROUPS.find(({ aliases }) => aliases.some((alias) => source.includes(alias)))?.label || "";
}

function findProvinceByCity(source = "") {
  const matches = [];
  for (const province of Object.keys(PROVINCE_CITY_GROUPS)) {
    const city = findCityInProvince(province, source);
    if (city) matches.push({ province, city });
  }

  const uniqueProvinces = [...new Set(matches.map((match) => match.province))];
  return uniqueProvinces.length === 1 ? uniqueProvinces[0] : "";
}

function findCityAlias(province = "", source = "") {
  return CITY_ALIAS_RULES.find(
    (rule) => rule.province === province && rule.keywords.some((keyword) => source.includes(keyword)),
  )?.city || "";
}

const LOCATION_TEXT_REJECT_PATTERN =
  /(?:체험|리뷰|캠페인|미션|가이드|필수|선정|모집|신청|제공|식사권|이용권|상품권|할인권|메뉴|추가주문|추가비용|본인부담|비용|청구|페널티|사진|동영상|본문|콘텐츠|인스타|해시태그|네이버\s*지도|플레이스|스폰서|예약|영업시간|전화번호|업체|광고주|등록|수정|삭제|문의|카카오톡|카톡|블로그|릴스|클립)/i;

function cleanCampaignLocationText(value = "") {
  return String(value || "")
    .replace(/^(?:방문\s*(?:주소|위치)|주소|위치|장소)\s*:?\s*/i, "")
    .replace(/\s*(?:©\s*)?copyright\b.*$/i, "")
    .replace(/\s*[.。]\s*$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function hasLocationTextSignal(value = "") {
  const normalized = cleanCampaignLocationText(value);
  if (!normalized) return false;

  return (
    /(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|[가-힣]+도)\s*[가-힣0-9]+(?:시|군|구)/.test(normalized) ||
    /[가-힣0-9]+(?:시|군|구)\s+[가-힣0-9.-]+(?:읍|면|동|리|로|길)/.test(normalized) ||
    /[가-힣0-9.-]+(?:로|길)\s*\d/.test(normalized) ||
    /[가-힣0-9]+(?:동|읍|면|리)\s*\d/.test(normalized) ||
    /[가-힣0-9]+역(?:\s*\d+\s*번\s*출구)?/.test(normalized)
  );
}

function isKnownAreaText(value = "") {
  const normalized = normalizeAreaText(cleanCampaignLocationText(value));
  const compact = normalized.replace(/\s+/g, "");
  if (!compact) return false;

  return Boolean(
    findProvinceLabel(normalized) ||
    findProvinceByCity(normalized) ||
    CITY_ALIAS_RULES.some((rule) => rule.keywords.some((keyword) => compact.includes(keyword))) ||
    LOCATION_COORDS.some(({ key }) => compact.includes(String(key).replace(/\s+/g, ""))) ||
    /^[가-힣]{2,10}\s+[가-힣0-9]{2,10}(?:동|역|구|군|시|읍|면|리)?$/.test(normalized),
  );
}

function isMeaningfulCampaignLocationText(value = "") {
  const normalized = cleanCampaignLocationText(value);
  if (!normalized || normalized.length < 2 || normalized.length > 120) return false;
  if (/^(지도|map|위치|주소|장소|배송|전국|전체|기타|제품|구매평|기자단|맛집|카페|뷰티|생활|패션|서비스|체험|테스트)$/i.test(normalized)) return false;
  if (/https?:\/\//i.test(normalized)) return false;
  if (LOCATION_TEXT_REJECT_PATTERN.test(normalized)) return false;
  if ((normalized.match(/[.!?。※]/g) || []).length > 1) return false;
  if (normalized.split(/\s+/).length > 18) return false;
  return hasLocationTextSignal(normalized) || isKnownAreaText(normalized);
}

function sanitizeCampaignLocationText(value = "") {
  const normalized = cleanCampaignLocationText(value);
  return isMeaningfulCampaignLocationText(normalized) ? normalized : "";
}

function getSanitizedCampaignLocationParts(campaign) {
  return [
    campaign.addressRaw,
    campaign.locationRaw,
    campaign.stationName,
    campaign.placeName,
    campaign.region,
  ]
    .map((value) => sanitizeCampaignLocationText(value))
    .filter(Boolean);
}

function getCampaignAreaInfoFromSource(source = "", title = "") {
  if (!source) {
    return { province: "기타", city: "전체", label: "기타" };
  }

  const province = findProvinceLabel(source) || findProvinceByCity(source);
  if (province) {
    const city = findCityInProvince(province, source) || findCityAlias(province, source) || "전체";
    return { province, city, label: city === "전체" ? province : `${province} ${city}` };
  }

  for (const rule of CITY_ALIAS_RULES) {
    if (rule.keywords.some((keyword) => source.includes(keyword))) {
      return { province: rule.province, city: rule.city, label: `${rule.province} ${rule.city}` };
    }
  }

  const fallbackRegion = extractCampaignRegion(title);
  if (fallbackRegion && fallbackRegion !== "기타") {
    const city = fallbackRegion.split("·")[0];
    return { province: "서울", city, label: `서울 ${city}` };
  }

  return { province: "기타", city: "전체", label: "기타" };
}

function getCampaignAreaInfo(campaign) {
  const titleLocation = extractCampaignLocation(campaign.title);
  const titleAreaInfo = titleLocation
    ? getCampaignAreaInfoFromSource(normalizeAreaText(titleLocation), campaign.title)
    : null;
  const source = normalizeAreaText([
    ...getSanitizedCampaignLocationParts(campaign),
    titleLocation,
  ].filter(Boolean).join(" "));
  const areaInfo = getCampaignAreaInfoFromSource(source, campaign.title);

  if (titleAreaInfo && titleAreaInfo.province !== "기타") {
    const provinceConflict = areaInfo.province !== "기타" && areaInfo.province !== titleAreaInfo.province;
    const cityConflict = (
      areaInfo.province === titleAreaInfo.province &&
      titleAreaInfo.city !== "전체" &&
      areaInfo.city !== "전체" &&
      areaInfo.city !== titleAreaInfo.city
    );

    if (provinceConflict || cityConflict) {
      return titleAreaInfo;
    }
  }

  return areaInfo;
}

function getProvinceGroups(campaigns) {
  const provinces = PROVINCE_GROUPS.map((item) => item.label);
  const hasOther = campaigns.some((campaign) => getCampaignAreaInfo(campaign).province === "기타");
  return ["전체", ...provinces, ...(hasOther ? ["기타"] : [])];
}

function getCityGroups(campaigns, province = "전체") {
  if (province === "전체") return ["전체"];
  return ["전체", ...getProvinceCityList(province)];
}

function extractCampaignRegion(title = "") {
  const location = extractCampaignLocation(title);

  if (!location) return "기타";

  const normalized = location.replaceAll(" ", "");
  const matchedGroup = REGION_GROUPS.find(({ label, keywords }) => {
    if (label === "전체") return false;
    return keywords.some((keyword) => normalized.includes(keyword));
  });

  return matchedGroup?.label || "기타";
}

function getCampaignLocationLabel(campaign) {
  return getSanitizedCampaignLocationParts(campaign)[0]
    || extractCampaignLocation(campaign.title)
    || extractCampaignRegion(campaign.title);
}

function getCampaignFacetProfile(campaign) {
  const source = `${campaign.sourceType || ""} ${campaign.campaignType || ""} ${campaign.type || ""} ${campaign.category || ""} ${campaign.title || ""} ${campaign.point || ""}`.toLowerCase();

  let snsLabel = "미정";
  if (source.includes("릴스") || source.includes("reels")) {
    snsLabel = "릴스";
  } else if (source.includes("클립") || source.includes("clip") || source.includes("shorts")) {
    snsLabel = "숏폼";
  } else if (source.includes("인스타") || source.includes("insta") || source.includes("instagram")) {
    snsLabel = "인스타";
  } else if (source.includes("blog") || source.includes("블로그")) {
    snsLabel = "블로그";
  }

  const baseModeLabel = campaign.campaignMode || getCampaignModeLabel(campaign.campaignType || campaign.type);
  const modeLabel = getCampaignFulfillmentModeLabel(campaign, baseModeLabel);

  return { snsLabel, modeLabel };
}

function isUnknownDisplayLabel(value = "") {
  return ["", "기타", "전체", "미정", "지역 미정"].includes(String(value || "").trim());
}

function parseCampaignDdayForDisplay(value) {
  if (value == null || String(value).trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatCampaignDdayLabel(value) {
  const dDay = parseCampaignDdayForDisplay(value);
  if (dDay == null || dDay < 0 || dDay >= 90) return "마감일 확인";
  if (dDay <= 0) return "오늘";
  if (dDay === 1) return "내일";
  return `D-${dDay}`;
}

function hasPackagingDisplaySignal(campaign) {
  const source = [
    campaign?.sourceType,
    campaign?.rawType,
    campaign?.type,
    campaign?.campaignType,
    campaign?.title,
    campaign?.point,
    campaign?.reward,
    campaign?.provision,
  ].filter(Boolean).join(" ").toLowerCase();

  if (/(?:포장|픽업|take\s*out|takeout)\s*(?:불가|안\s*됨|제외|불가능|not\s*available|unavailable)/i.test(source)) {
    return false;
  }

  return /포장|픽업|take\s*out|takeout/.test(source);
}

function getCampaignFulfillmentModeLabel(campaign, fallbackModeLabel = "") {
  if (fallbackModeLabel === "배송형" && hasPackagingDisplaySignal(campaign)) {
    return "포장형";
  }

  return fallbackModeLabel;
}

function getCampaignDisplayProfile(campaign) {
  const facets = getCampaignFacetProfile(campaign);
  const rawLocationLabel = getCampaignLocationLabel(campaign);
  const campaignMode = facets.modeLabel || getCampaignModeLabel(campaign?.campaignType || campaign?.type);
  const isDeliveryLike = normalizeCampaignType(campaign?.campaignType || campaign?.type) === "delivery"
    || ["배송형", "포장형"].includes(campaignMode);
  let locationLabel = "지역 확인";
  if (isDeliveryLike) {
    locationLabel = campaignMode;
  } else if (!isUnknownDisplayLabel(rawLocationLabel)) {
    locationLabel = rawLocationLabel;
  }
  const dDay = parseCampaignDdayForDisplay(campaign?.dDay);

  return {
    locationLabel,
    snsLabel: facets.snsLabel === "미정" ? "" : facets.snsLabel,
    modeLabel: campaignMode,
    dDayLabel: formatCampaignDdayLabel(campaign?.dDay),
    isUrgent: dDay != null && dDay >= 0 && dDay <= 1,
  };
}

function cleanCampaignBenefitText(value = "") {
  return String(value || "")
    .replace(/https?:\/\/\S+/gi, "")
    .replace(/\s*(?:\*+\s*)?본\s*체험단은.*$/i, "")
    .replace(/\s*자세한\s*(?:내용|상품|사항)?은?\s*가이드라인.*$/i, "")
    .replace(/\s*(?:©\s*)?copyright\b.*$/i, "")
    .replace(/^[★☆*\s]+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function truncateDisplayText(value = "", maxLength = 96) {
  const normalized = String(value || "").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength).trim()}...`;
}

function getCampaignBenefitLabel(campaign, { maxLength = 96 } = {}) {
  const rawBenefit = campaign?.point || campaign?.reward || campaign?.provision || "";
  const cleaned = cleanCampaignBenefitText(rawBenefit);
  return truncateDisplayText(cleaned, maxLength);
}

function isVisitFocusedCampaign(campaign) {
  return Boolean(campaign);
}

function getRegionGroups(campaigns) {
  const activeGroups = REGION_GROUPS
    .filter(({ label }) => label === "전체" || campaigns.some((campaign) => extractCampaignRegion(campaign.title) === label))
    .map(({ label }) => label);

  if (campaigns.some((campaign) => extractCampaignRegion(campaign.title) === "기타")) {
    activeGroups.push("기타");
  }

  return [...new Set(activeGroups)];
}

function guessCategory(text = "") {
  const normalizedText = String(text).toLowerCase();
  const rules = {
    카페: [
      "카페", "까페", "커피", "coffee", "cafe", "베이커리", "bakery", "브런치", "디저트",
      "dessert", "빵집", "제과", "제빵", "브레드", "bread", "케이크", "마카롱", "도넛",
      "와플", "빙수", "라떼", "로스터리", "티룸", "tea room", "다방", "카공",
    ],
    맛집: [
      "맛집", "식당", "레스토랑", "restaurant", "다이닝", "밥집", "집밥", "밥상", "밥엔",
      "분식", "김밥", "떡볶이", "떡", "라면", "버거", "피자", "치킨", "튀김", "고기",
      "고깃집", "삼겹", "목살", "갈비", "갈비살", "한우", "소고기", "돼지", "족발",
      "보쌈", "곱창", "막창", "대창", "닭갈비", "닭발", "찜닭", "오리", "양꼬치",
      "훠궈", "마라", "초밥", "스시", "횟집", "대게", "홍게", "해물", "조개", "수산",
      "건어물", "젓갈", "꼼장어", "장어", "탕", "국밥", "해장", "감자탕", "찌개",
      "전골", "칼국수", "수제비", "냉면", "막국수", "국수", "우동", "돈까스", "돈카츠",
      "돈가츠", "카츠", "덮밥", "오마카세", "샤브", "파스타", "스테이크", "양식", "한식", "중식",
      "중화", "중국집", "반점", "짬뽕", "짜장", "일식", "쌀국수", "쭈꾸미", "낙지",
      "아구찜", "코다리", "동태", "순대", "추어탕", "솥밥", "샐러드", "샐러브러리",
      "게장", "혼술", "포차", "주점", "이자카야", "비스트로", "호프", "맥주", "술집", "와인바", "키친",
      "kitchen", "그릴", "요리", "도시락", "반찬", "식사권", "금액권",
    ],
    뷰티: [
      "뷰티", "네일", "헤어", "미용실", "살롱", "바버샵", "에스테틱", "피부", "스킨",
      "스캘프", "마사지", "스파", "왁싱", "속눈썹", "눈썹", "태닝", "두피", "탈모",
      "아로마", "제모", "smp", "필라테스", "헬스", "pt", "피티", "요가", "피트니스", "짐", "체형",
      "다이어트", "관리센터", "안마원", "메이크업",
    ],
    숙박: [
      "호텔", "숙박", "펜션", "리조트", "모텔", "스테이", "풀빌라", "게스트하우스",
      "민박", "캠핑", "글램핑", "카라반", "독채", "호스텔",
    ],
    생활용품: [
      "생활", "주방", "가전", "청소", "가구", "용품", "전자", "생활용품", "인테리어",
      "침구", "수납", "육아", "유아", "반려", "펫", "강아지", "고양이", "문구", "식품",
      "밀키트", "건강식품", "영양제", "즙", "차량용", "자동차용품", "화장지", "세제",
      "플랜트", "침대", "홈케어", "클린홈", "렌즈세척", "클렌져", "책갈피", "바스켓",
      "스티커", "노트", "통조림",
    ],
    패션: [
      "패션", "의류", "옷", "신발", "가방", "액세서리", "악세서리", "주얼리", "쥬얼리",
      "귀걸이", "목걸이", "반지", "팔찌", "시계", "안경", "콘택트", "선글라스", "실내복",
      "속옷", "테일러", "스커트", "셋업",
    ],
    서비스: [
      "워크스페이스", "공유오피스", "공간대여", "렌탈스튜디오", "병원", "의원",
      "약국", "법률", "법무", "변호사", "상조", "장례", "금융", "보험", "금거래소",
      "멤버십", "시설제휴", "사주", "타로", "신점", "보살", "점집", "운세", "상담",
      "소개팅", "자동차", "랩핑", "ppf", "썬팅", "디테일링", "광택", "코팅", "크리닝",
      "내외장", "복원", "카샵",
    ],
    체험: [
      "체험", "전시", "공연", "레저", "공방", "도자기", "사진관", "스튜디오", "문화",
      "테마파크", "키즈카페", "입장권", "클래스", "원데이", "방탈출", "vr", "게임",
      "놀이", "꽃", "플라워", "화훼", "농원", "요트", "서핑", "낚시", "캠프", "마법학교",
      "사육공간", "골프", "아카데미", "학원", "어학원", "미술", "복싱", "탁구",
      "크로스핏", "dmz", "생태평화공원", "관광", "여가",
    ],
  };

  for (const [category, keywords] of Object.entries(rules)) {
    if (keywords.some((keyword) => normalizedText.includes(keyword))) return category;
  }

  return "기타";
}

function getGenericCategoryFallback(text = "", platformId = "") {
  if (/(제품|상품)/i.test(String(text))) return "생활용품";
  return PLATFORM_CATEGORY_DEFAULTS[platformId] || "";
}

function isDeliveryCampaignType(value = "") {
  const normalized = String(value).trim().toLowerCase();
  return ["delivery", "shipping", "배송", "배송형", "배달", "포장"].includes(normalized);
}

function normalizeCampaignType(value = "") {
  return isDeliveryCampaignType(value) ? "delivery" : LAUNCH_CAMPAIGN_TYPE;
}

function getCampaignModeLabel(value = "") {
  return normalizeCampaignType(value) === "delivery" ? "배송형" : LAUNCH_CAMPAIGN_MODE_LABEL;
}

function campaignTypeToSlug(type = "전체") {
  return CAMPAIGN_TYPE_TO_SLUG[type] || CAMPAIGN_TYPE_TO_SLUG.전체;
}

function slugToCampaignType(slug = "") {
  if (slug === "전체" || Object.hasOwn(CAMPAIGN_TYPE_TO_SLUG, slug)) return slug;
  return SLUG_TO_CAMPAIGN_TYPE[slug] || "전체";
}

function campaignMatchesType(campaign, type = "전체") {
  const typeLabel = slugToCampaignType(type);
  if (typeLabel === "전체") return true;
  return (campaign?.campaignMode || getCampaignModeLabel(campaign?.campaignType || campaign?.type)) === typeLabel;
}

function normalizeCampaignCategory(category = "", fallbackText = "", platformId = "", campaignType = "") {
  void campaignType;

  const raw = String(category).trim();
  const searchText = `${raw} ${fallbackText}`;

  if (CATEGORY_ALIASES[raw]) return CATEGORY_ALIASES[raw];
  if (CANONICAL_CATEGORIES.includes(raw) && !GENERIC_CATEGORY_LABELS.has(raw)) {
    const guessed = guessCategory(searchText);
    if (guessed === "서비스" && ["생활용품", "체험"].includes(raw)) return guessed;
    return raw;
  }

  const guessed = guessCategory(searchText);
  if (guessed !== "기타") return guessed;

  return getGenericCategoryFallback(searchText, platformId) || (CANONICAL_CATEGORIES.includes(raw) ? raw : "기타");
}

function getCategoryName(category, fallbackText = "", platformId = "", campaignType = "") {
  return normalizeCampaignCategory(category, fallbackText, platformId, campaignType);
}

function categoryToSlug(category = "전체") {
  return CATEGORY_TO_SLUG[category] || CATEGORY_TO_SLUG.전체;
}

function slugToCategory(slug = "") {
  if (slug === "전체" || CANONICAL_CATEGORIES.includes(slug)) return slug;
  return SLUG_TO_CATEGORY[slug] || "전체";
}

function getCampaignActionChecklist(campaign) {
  const checklist = [];
  const competition = getCompLevel(campaign.applyCount, campaign.selectedCount);

  if ((campaign.dDay ?? 99) <= 1) {
    checklist.push("오늘 안에 지원 조건과 방문 가능 여부를 먼저 확인하는 편이 좋습니다.");
  } else if ((campaign.dDay ?? 99) <= 3) {
    checklist.push("이번 주 안에 일정과 제공 내역이 맞는지 빠르게 검토하는 편이 좋습니다.");
  } else {
    checklist.push("지원 조건과 제공 내역, 방문 조건을 천천히 비교해도 됩니다.");
  }

  if (competition.label === "낮음") {
    checklist.push("경쟁률이 비교적 낮아 보입니다.");
  } else if (competition.label === "보통") {
    checklist.push("경쟁률이 무난해 조건만 맞으면 검토할 가치가 있습니다.");
  } else {
    checklist.push("지원자가 많을 수 있어 조건이 잘 맞을 때 들어가는 편이 좋습니다.");
  }

  return checklist;
}

function getCampaignScoreProfile(campaign) {
  let score = 50;
  const reasons = [];

  if ((campaign.dDay ?? 99) <= 1) {
    score += 8;
    reasons.push("마감이 가까워 우선 확인할 가치가 높음");
  } else if ((campaign.dDay ?? 99) <= 3) {
    score += 4;
    reasons.push("이번 주 안에 판단이 필요한 공고");
  }

  const competition = getCompLevel(campaign.applyCount, campaign.selectedCount);
  if (competition.label === "낮음") {
    score += 18;
    reasons.push("경쟁률이 비교적 낮음");
  } else if (competition.label === "보통") {
    score += 8;
    reasons.push("경쟁률이 과열되지 않음");
  } else {
    score -= 8;
    reasons.push("경쟁률이 높음");
  }

  if (campaign.point) {
    score += 10;
    reasons.push("제공 내역이 명확함");
  }

  if ((campaign.selectedCount || 0) >= 5) {
    score += 6;
    reasons.push("모집 인원이 비교적 넉넉함");
  }

  const boundedScore = Math.max(20, Math.min(98, score));
  const tone = boundedScore >= 78 ? "지금 보기 좋음" : boundedScore >= 62 ? "검토할 가치 있음" : "조건 확인 필요";

  return {
    score: boundedScore,
    tone,
    reasons: reasons.slice(0, 3),
    competition,
  };
}

function tokenizeLocationText(value = "") {
  return String(value)
    .replace(/[[\](),]/g, " ")
    .split(/[/\s|&·]+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

function findLocationCoordMatch(text = "") {
  const normalized = String(text).replaceAll(" ", "");
  if (!normalized) return null;

  const matches = LOCATION_COORDS.filter(({ key }) => normalized.includes(String(key).replaceAll(" ", "")));
  if (!matches.length) return null;

  // 더 긴 키워드 우선 (예: "해운대" > "부산")
  matches.sort((a, b) => b.key.length - a.key.length);
  return matches[0];
}

/**
 * 캠페인의 주소/위치 텍스트에서 좌표를 추론합니다.
 *
 * ⚠️ CHANGED: 매칭 실패 시 DEFAULT_COORDS 대신 null 반환.
 * null 반환 → enrichCampaign이 coordinateSource: "unresolved" 처리
 * → MapPage에서 지도 마커 제외 (클러스터링 오염 방지)
 *
 * @returns {{ lat: number, lng: number, source: string } | null}
 */
function resolveCampaignCoordinates(campaign) {
  const location = getCampaignLocationLabel(campaign);
  const title = String(campaign.title || "");
  const locationParts = getSanitizedCampaignLocationParts(campaign);

  // 1차: addressRaw + locationRaw + location 토큰에서 여러 지역 키워드 매칭 → 평균 좌표
  const tokenMatches = tokenizeLocationText(
    [...locationParts, location].join(" "),
  )
    .map((token) => findLocationCoordMatch(token))
    .filter(Boolean);

  if (tokenMatches.length > 1) {
    const uniqueMatches = [...new Map(tokenMatches.map((item) => [item.key, item])).values()];
    return {
      lat: uniqueMatches.reduce((sum, item) => sum + item.lat, 0) / uniqueMatches.length,
      lng: uniqueMatches.reduce((sum, item) => sum + item.lng, 0) / uniqueMatches.length,
      source: "region_keyword_multi",
    };
  }

  // 2차: location 라벨 또는 타이틀 직접 매칭
  const directMatch = findLocationCoordMatch(location) || findLocationCoordMatch(title);
  if (directMatch) {
    return { lat: directMatch.lat, lng: directMatch.lng, source: "region_keyword" };
  }

  // 3차: region 필드 단독 매칭 (DB에 region 컬럼이 있는 경우)
  if (campaign.region) {
    const regionMatch = findLocationCoordMatch(campaign.region);
    if (regionMatch) {
      return { lat: regionMatch.lat, lng: regionMatch.lng, source: "region_field" };
    }
  }

  // ✅ FIX: 매칭 실패 → null 반환 (이전: DEFAULT_COORDS 반환으로 대전에 수백 개 집결)
  return null;
}

function normalizeCampaignDDay(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : -1;
}

function getCampaignPlatformKey(campaign) {
  return String(campaign?.platformId || campaign?.platform || "unknown");
}

function getPlatformDiverseCampaigns(campaigns = [], limit = null) {
  const source = Array.isArray(campaigns) ? campaigns : [];
  const maxCount = limit == null ? source.length : Math.max(0, Number(limit) || 0);
  if (source.length <= 1 || maxCount === 0) {
    return source.slice(0, maxCount);
  }

  const byPlatform = new Map();
  source.forEach((campaign, index) => {
    const platformKey = getCampaignPlatformKey(campaign);
    if (!byPlatform.has(platformKey)) {
      byPlatform.set(platformKey, { firstIndex: index, queue: [] });
    }
    byPlatform.get(platformKey).queue.push(campaign);
  });

  if (byPlatform.size <= 1) return source.slice(0, maxCount);

  const platformQueues = [...byPlatform.values()]
    .sort((left, right) => left.firstIndex - right.firstIndex);
  const balanced = [];

  while (balanced.length < maxCount) {
    let added = false;

    for (const entry of platformQueues) {
      const campaign = entry.queue.shift();
      if (!campaign) continue;

      balanced.push(campaign);
      added = true;
      if (balanced.length >= maxCount) break;
    }

    if (!added) break;
  }

  return balanced;
}

function normalizeDuplicateText(value) {
  return String(value || "")
    .normalize("NFKC")
    .toLowerCase()
    .replace(/^\[[^\]]+\]\s*/g, "")
    .replace(/\[[^\]]+\]/g, " ")
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function makeViewDuplicateKey(campaign) {
  const platformKey = String(campaign.platformId || "unknown");
  const titleKey = normalizeDuplicateText(campaign.title).slice(0, 80);
  if (titleKey.length < 2) return null;

  const addressKey = normalizeDuplicateText(
    campaign.addressRaw || campaign.locationRaw || campaign.placeName || campaign.stationName || "",
  ).slice(0, 120);
  if (addressKey.length >= 8) return `${platformKey}:addr:${titleKey}:${addressKey}`;

  if (
    campaign.lat != null &&
    campaign.lng != null &&
    Number.isFinite(Number(campaign.lat)) &&
    Number.isFinite(Number(campaign.lng)) &&
    !isKnownBadMapCoordinate(campaign.lat, campaign.lng)
  ) {
    const coordKey = `${Number(campaign.lat).toFixed(4)},${Number(campaign.lng).toFixed(4)}`;
    const rewardKey = normalizeDuplicateText(campaign.point || "").slice(0, 40);
    return rewardKey
      ? `${platformKey}:coord:${titleKey}:${coordKey}:${rewardKey}`
      : `${platformKey}:coord:${titleKey}:${coordKey}`;
  }

  return null;
}

function getViewDuplicateScore(campaign) {
  return [
    campaign.dataState === "fresh" ? 100 : campaign.dataState === "preserved" ? 40 : 0,
    campaign.lat != null && campaign.lng != null ? 70 : 0,
    campaign.addressRaw || campaign.locationRaw ? 30 : 0,
    Number.isFinite(Number(campaign.applyCount)) ? Math.min(Number(campaign.applyCount), 30) : 0,
    Number.isFinite(Number(campaign.selectedCount)) ? Math.min(Number(campaign.selectedCount), 20) : 0,
    Number.isFinite(Number(campaign.dDay)) ? Math.max(0, 20 - Number(campaign.dDay)) : 0,
  ].reduce((sum, value) => sum + value, 0);
}

function collapseDuplicateCampaigns(campaigns) {
  const groups = new Map();
  const passthrough = [];

  for (const campaign of campaigns || []) {
    const duplicateKey = campaign.duplicateGroupId
      ? `${campaign.platformId || "unknown"}:${campaign.duplicateGroupId}`
      : makeViewDuplicateKey(campaign);
    if (!duplicateKey) {
      passthrough.push(campaign);
      continue;
    }
    if (!groups.has(duplicateKey)) groups.set(duplicateKey, []);
    groups.get(duplicateKey).push(campaign);
  }

  const collapsed = [...passthrough];
  for (const [duplicateKey, group] of groups.entries()) {
    if (group.length === 1) {
      collapsed.push(group[0]);
      continue;
    }

    const sorted = [...group].sort((left, right) => (
      getViewDuplicateScore(right) - getViewDuplicateScore(left)
      || normalizeCampaignDDay(left.dDay) - normalizeCampaignDDay(right.dDay)
      || String(left.platformId || "").localeCompare(String(right.platformId || ""))
    ));
    const representative = sorted[0];
    const alternates = sorted.slice(1);

    collapsed.push({
      ...representative,
      duplicateGroupId: representative.duplicateGroupId || `view_${duplicateKey.slice(0, 96)}`,
      duplicateCount: Math.max(Number(representative.duplicateCount || 0), group.length),
      duplicateAlternates: representative.duplicateAlternates || alternates.map((campaign) => ({
        id: campaign.id,
        platformId: campaign.platformId,
        title: campaign.title,
        url: campaign.url,
      })),
    });
  }

  return collapsed.sort((left, right) => (
    normalizeCampaignDDay(left.dDay) - normalizeCampaignDDay(right.dDay)
    || String(left.title || "").localeCompare(String(right.title || ""))
  ));
}

function enrichCampaign(campaign, platformMap = null) {
  const platformMeta = platformMap?.get(campaign.platformId) || PLATFORMS.find((platform) => platform.id === campaign.platformId);
  const sourceType = campaign.sourceType || campaign.rawType || campaign.type || "";
  const campaignType = normalizeCampaignType(sourceType);
  const campaignMode = getCampaignModeLabel(campaignType);
  const categoryFallbackText = [
    campaign.title,
    campaign.point,
    sourceType,
    campaign.locationRaw,
    campaign.addressRaw,
    campaign.stationName,
    campaign.placeName,
  ].filter(Boolean).join(" ");
  const category = getCategoryName(campaign.category, categoryFallbackText, campaign.platformId);
  const region = campaign.region || extractCampaignLocation(campaign.title);
  const addressRaw = sanitizeCampaignLocationText(campaign.addressRaw);
  const locationRaw = sanitizeCampaignLocationText(campaign.locationRaw);
  const stationName = sanitizeCampaignLocationText(campaign.stationName);
  const placeName = sanitizeCampaignLocationText(campaign.placeName);
  const campaignForLocation = {
    ...campaign,
    region,
    addressRaw,
    locationRaw,
    stationName,
    placeName,
  };

  // ✅ FIX: DB에 lat/lng 있으면 그대로 사용, 없으면 키워드 추론 (null 허용)
  let lat = null;
  let lng = null;
  let coordinateSource = campaign.coordinateSource || null;

  if (campaign.lat != null && campaign.lng != null &&
    Number.isFinite(Number(campaign.lat)) &&
    Number.isFinite(Number(campaign.lng)) &&
    !isKnownBadMapCoordinate(campaign.lat, campaign.lng)) {
    // DB에서 가져온 실좌표 (kakao geocoded / html extracted)
    lat = Number(campaign.lat);
    lng = Number(campaign.lng);
    coordinateSource = coordinateSource || "db";
  } else {
    // DB에 좌표 없음 → 키워드 기반 추론 시도
    const resolved = resolveCampaignCoordinates(campaignForLocation);
    if (resolved) {
      lat = resolved.lat;
      lng = resolved.lng;
      coordinateSource = resolved.source;
    } else {
      // 추론 실패 → null 유지 (지도 마커 제외 대상)
      coordinateSource = "unresolved";
    }
  }

  const areaInfo = getCampaignAreaInfo(campaignForLocation);
  const province = areaInfo.province !== "기타"
    ? areaInfo.province
    : campaign.province || areaInfo.province;
  const rawCity = String(campaign.city || "").trim();
  const city = areaInfo.city !== "전체"
    ? areaInfo.city
    : (rawCity === "전체" || getProvinceCityList(province).includes(rawCity) ? rawCity : areaInfo.city);
  const areaLabel = areaInfo.label !== "기타"
    ? areaInfo.label
    : campaign.areaLabel || (city === "전체" ? province : `${province} ${city}`);
  const platform = campaign.platform || platformMeta?.name || "";
  const searchText = [
    campaign.title,
    campaign.point,
    campaign.reward,
    campaign.provision,
    category,
    platform,
    province,
    city,
    areaLabel,
    region,
    locationRaw,
    addressRaw,
    stationName,
    placeName,
  ].filter(Boolean).join(" ").toLowerCase();

  return {
    ...campaign,
    type: campaignType,
    sourceType,
    campaignType,
    campaignMode,
    category,
    emoji: EMOJI_MAP[category] || EMOJI_MAP.기타,
    bg: BG_MAP[category] || BG_MAP.기타,
    lat,
    lng,
    region,
    locationRaw,
    addressRaw,
    stationName,
    placeName,
    province,
    city,
    areaLabel,
    sourceStartedAt: campaign.sourceStartedAt || null,
    sourcePostedAt: campaign.sourcePostedAt || null,
    firstSeenAt: campaign.firstSeenAt || campaign.createdAt || null,
    crawledAt: campaign.crawledAt || null,
    coordinateSource,
    dDay: normalizeCampaignDDay(campaign.dDay),
    selectedCount: campaign.selectedCount || 3,
    platform,
    searchText,
  };
}

function mapDbCampaignToView(campaign, platformMap) {
  const platformMeta = platformMap.get(campaign.platform_id);

  return enrichCampaign(
    {
      id: campaign.external_id,
      title: campaign.title,
      url: campaign.source_url,
      type: campaign.campaign_type || "기타",
      category: campaign.category || "기타",
      platform: platformMeta?.name || campaign.platform_id,
      platformId: campaign.platform_id,
      dDay: campaign.d_day ?? 99,
      applyCount: campaign.apply_count ?? 0,
      selectedCount: campaign.selected_count ?? 3,
      point: campaign.reward_text || null,
      lat: campaign.lat,
      lng: campaign.lng,
      region: campaign.region || "",
      locationRaw: campaign.location_raw || "",
      addressRaw: campaign.address_raw || "",
      stationName: campaign.station_name || "",
      placeName: campaign.place_name || "",
      sourceStartedAt: campaign.source_started_at || null,
      sourcePostedAt: campaign.source_posted_at || null,
      firstSeenAt: campaign.first_seen_at || campaign.created_at || null,
      crawledAt: campaign.crawled_at,
      coordinateSource: campaign.coordinate_source || null,
      status: campaign.status || "open",
    },
    platformMap,
  );
}

function isCampaignOpen(campaign) {
  if (!campaign) return false;

  if (String(campaign.status || "").toLowerCase() === "closed") {
    return false;
  }

  return normalizeCampaignDDay(campaign.dDay) >= 0;
}

async function fetchCampaignsFromSupabase() {
  const pageSize = 1000;
  const fetchCampaignPage = async (selectClause, from) => supabase
    .from("campaigns")
    .select(selectClause)
    .eq("status", "open")
    .order("d_day", { ascending: true })
    .range(from, from + pageSize - 1);

  const fetchAllCampaignPages = async (selectClause) => {
    const rows = [];
    let from = 0;

    while (true) {
      const { data, error } = await fetchCampaignPage(selectClause, from);
      if (error) return { data: null, error };

      rows.push(...(data || []));
      if (!data || data.length < pageSize) {
        return { data: rows, error: null };
      }

      from += pageSize;
    }
  };

  const [{ data: platformRows, error: platformError }, campaignResult] = await Promise.all([
    supabase.from("platforms").select("id, name, description, color, emoji, base_url").eq("is_active", true),
    fetchAllCampaignPages("platform_id, external_id, source_url, title, campaign_type, category, region, location_raw, address_raw, station_name, place_name, reward_text, apply_count, selected_count, lat, lng, d_day, source_started_at, source_posted_at, coordinate_source, first_seen_at, created_at, crawled_at, status"),
  ]);

  if (platformError) throw platformError;

  let { data: campaignRows, error: campaignError } = campaignResult;

  // Older production databases can lag behind the local schema. Retry with the
  // stable core columns so the app stays readable instead of showing 0 items.
  if (campaignError?.code === "42703") {
    const fallbackResult = await fetchAllCampaignPages(
      "platform_id, external_id, source_url, title, campaign_type, category, region, reward_text, apply_count, selected_count, d_day, status, crawled_at, created_at",
    );

    campaignRows = fallbackResult.data;
    campaignError = fallbackResult.error;
  }

  if (campaignError) throw campaignError;

  const platformMap = new Map(
    (platformRows || []).map((platform) => [
      platform.id,
      {
        id: platform.id,
        name: platform.name,
        desc: platform.description,
        color: platform.color,
        emoji: platform.emoji,
        url: platform.base_url,
      },
    ]),
  );

  return collapseDuplicateCampaigns(
    (campaignRows || []).map((campaign) => mapDbCampaignToView(campaign, platformMap)).filter(isCampaignOpen),
  );
}

export {
  campaignMatchesType,
  campaignTypeToSlug,
  categoryToSlug,
  REGION_GROUPS,
  collapseDuplicateCampaigns,
  enrichCampaign,
  getCampaignAreaInfo,
  extractCampaignLocation,
  extractCampaignRegion,
  fetchCampaignsFromSupabase,
  getCampaignActionChecklist,
  getCampaignBenefitLabel,
  getCampaignDisplayProfile,
  getCityGroups,
  getCampaignFacetProfile,
  getCampaignFreshnessTimestamp,
  getCampaignLocationLabel,
  getCampaignRewardValue,
  getProvinceGroups,
  getCampaignScoreProfile,
  getCompLevel,
  getPlatformDiverseCampaigns,
  getRegionGroups,
  formatCampaignDdayLabel,
  hasValidCoordinates,
  isCampaignOpen,
  isFreshDeadlineCampaign,
  isVisitFocusedCampaign,
  mapDbCampaignToView,
  normalizeCampaignCategory,
  normalizeCampaignType,
  slugToCampaignType,
  slugToCategory,
};
