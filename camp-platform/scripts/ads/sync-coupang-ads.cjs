const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const ENV_PATH = path.join(PROJECT_ROOT, ".env");
const ADS_PATH = path.join(PROJECT_ROOT, "public", "ads.json");
const GENERATED_BY = "coupang-partners-sync";
const DEFAULT_SLOTS = ["home_top", "explore_top", "explore_inline", "map_bottom"];
const DEFAULT_KEYWORDS = [
  "리뷰 촬영 장비",
  "촬영 조명",
  "휴대폰 삼각대",
  "블루투스 마이크",
  "보조배터리",
  "소품 촬영 배경",
];
const DEFAULT_CATEGORY_KEYWORDS = {
  맛집: ["휴대폰 거치대", "보조배터리", "미니 삼각대"],
  카페: ["소품 촬영 배경", "미니 조명", "휴대폰 삼각대"],
  뷰티: ["LED 거울", "촬영 조명", "화장품 정리함"],
  숙박: ["여행 파우치", "멀티 충전기", "보조배터리"],
  생활: ["생활용품 정리함", "무선 청소기", "수납 바구니"],
  서비스: ["노트북 거치대", "블루투스 마이크", "보조배터리"],
};
const DEFAULT_DISCLOSURE =
  "쿠팡 파트너스 활동의 일환으로 이에 따른 일정액의 수수료를 제공받습니다.";

function loadEnvFile() {
  if (!fs.existsSync(ENV_PATH)) return;

  const envContent = fs.readFileSync(ENV_PATH, "utf8");
  for (const rawLine of envContent.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const equalIndex = line.indexOf("=");
    if (equalIndex === -1) continue;

    const key = line.slice(0, equalIndex).trim();
    let value = line.slice(equalIndex + 1).trim();

    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (key && !(key in process.env)) process.env[key] = value;
  }
}

function getEnv(name, fallback = "") {
  return String(process.env[name] || fallback).trim();
}

function getEnvInt(name, fallback) {
  const value = Number(getEnv(name));
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback;
}

function getCsvEnv(name, fallback) {
  const values = getEnv(name)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  return values.length ? values : fallback;
}

function getCategoryKeywordEnv(name, fallback) {
  const raw = getEnv(name);
  if (!raw) return fallback;

  const entries = raw
    .split(";")
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const [category, keywords] = chunk.split("=");
      return [
        String(category || "").trim(),
        String(keywords || "")
          .split("|")
          .map((keyword) => keyword.trim())
          .filter(Boolean),
      ];
    })
    .filter(([category, keywords]) => category && keywords.length);

  return entries.length ? Object.fromEntries(entries) : fallback;
}

function looksUnset(value) {
  return !value || /^your-|^replace-|^here$/i.test(value);
}

function getConfig() {
  const baseUrl = getEnv("COUPANG_PARTNERS_BASE_URL", "https://api-gateway.coupang.com").replace(/\/+$/, "");
  const apiBasePath = getEnv(
    "COUPANG_PARTNERS_API_BASE_PATH",
    "/v2/providers/affiliate_open_api/apis/openapi/v1",
  ).replace(/\/+$/, "");

  return {
    accessKey: getEnv("COUPANG_PARTNERS_ACCESS_KEY"),
    secretKey: getEnv("COUPANG_PARTNERS_SECRET_KEY"),
    subId: getEnv("COUPANG_PARTNERS_SUB_ID", "cheheommoa"),
    baseUrl,
    apiBasePath,
    disclosure: getEnv("COUPANG_PARTNERS_DISCLOSURE", DEFAULT_DISCLOSURE),
    keywords: getCsvEnv("COUPANG_AD_KEYWORDS", DEFAULT_KEYWORDS),
    categoryKeywords: getCategoryKeywordEnv("COUPANG_AD_CATEGORY_KEYWORDS", DEFAULT_CATEGORY_KEYWORDS),
    categorySlots: getCsvEnv("COUPANG_AD_CATEGORY_SLOTS", ["home_top", "explore_top", "explore_inline", "map_bottom"]),
    categoryPerSlot: Math.min(3, getEnvInt("COUPANG_AD_CATEGORY_PER_SLOT", 2)),
    slots: getCsvEnv("COUPANG_AD_SLOTS", DEFAULT_SLOTS),
    productLimit: Math.min(100, getEnvInt("COUPANG_AD_PRODUCT_LIMIT", 8)),
    perSlot: Math.min(5, getEnvInt("COUPANG_AD_PER_SLOT", 4)),
    imageSize: getEnv("COUPANG_AD_IMAGE_SIZE", "512x512"),
    replaceExisting: getEnv("COUPANG_AD_REPLACE_EXISTING", "1") !== "0",
  };
}

function validateConfig(config) {
  const missing = [];
  if (looksUnset(config.accessKey)) missing.push("COUPANG_PARTNERS_ACCESS_KEY");
  if (looksUnset(config.secretKey)) missing.push("COUPANG_PARTNERS_SECRET_KEY");
  return missing;
}

function formatSignedDate(date = new Date()) {
  const yy = String(date.getUTCFullYear()).slice(-2);
  const mm = String(date.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(date.getUTCDate()).padStart(2, "0");
  const hh = String(date.getUTCHours()).padStart(2, "0");
  const mi = String(date.getUTCMinutes()).padStart(2, "0");
  const ss = String(date.getUTCSeconds()).padStart(2, "0");
  return `${yy}${mm}${dd}T${hh}${mi}${ss}Z`;
}

function createAuthorization(config, method, pathName, queryString = "") {
  const signedDate = formatSignedDate();
  const message = `${signedDate}${method.toUpperCase()}${pathName}${queryString}`;
  const signature = crypto
    .createHmac("sha256", config.secretKey)
    .update(message)
    .digest("hex");

  return `CEA algorithm=HmacSHA256, access-key=${config.accessKey}, signed-date=${signedDate}, signature=${signature}`;
}

function buildQuery(params) {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    searchParams.append(key, String(value));
  }
  return searchParams.toString();
}

async function requestCoupang(config, { method, pathName, query = "", body = null }) {
  const authorization = createAuthorization(config, method, pathName, query);
  const url = `${config.baseUrl}${pathName}${query ? `?${query}` : ""}`;
  const response = await fetch(url, {
    method,
    headers: {
      Authorization: authorization,
      "Content-Type": "application/json;charset=UTF-8",
      Accept: "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  let payload = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message = payload?.rMessage || payload?.message || response.statusText || "request failed";
    throw new Error(`Coupang API ${response.status}: ${message}`);
  }

  return payload;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function extractProductList(payload) {
  if (Array.isArray(payload?.data?.productData)) return payload.data.productData;
  if (Array.isArray(payload?.data?.products)) return payload.data.products;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.productData)) return payload.productData;
  return [];
}

async function fetchProductsForKeyword(config, keyword) {
  const pathName = `${config.apiBasePath}/products/search`;
  const query = buildQuery({
    keyword,
    limit: config.productLimit,
    subId: config.subId,
    imageSize: config.imageSize,
  });
  const payload = await requestCoupang(config, { method: "GET", pathName, query });
  return extractProductList(payload).filter((product) => product?.productUrl || product?.landingUrl);
}

async function getProductsForKeyword(config, cache, keyword) {
  if (!cache.has(keyword)) {
    cache.set(keyword, fetchProductsForKeyword(config, keyword));
  }
  return cache.get(keyword);
}

async function createSearchDeeplinks(config, keywords) {
  const pathName = `${config.apiBasePath}/deeplink`;
  const coupangUrls = keywords.map((keyword) => {
    const query = buildQuery({ component: "", q: keyword, channel: "user" });
    return `https://www.coupang.com/np/search?${query}`;
  });
  const payload = await requestCoupang(config, {
    method: "POST",
    pathName,
    body: {
      coupangUrls,
      subId: config.subId,
    },
  });
  return safeArray(payload?.data);
}

function hashId(value) {
  return crypto.createHash("sha1").update(String(value)).digest("hex").slice(0, 10);
}

function formatPrice(value) {
  const price = Number(value);
  if (!Number.isFinite(price) || price <= 0) return "";
  return `${price.toLocaleString("ko-KR")}원`;
}

function productDescription(product, keyword) {
  const parts = [
    formatPrice(product.productPrice || product.salePrice || product.price),
    product.isRocket ? "로켓배송" : "",
    product.isFreeShipping ? "무료배송" : "",
  ].filter(Boolean);

  if (parts.length) return `${keyword} 추천 상품 · ${parts.join(" · ")}`;
  return `${keyword} 관련 상품을 확인해보세요.`;
}

function buildProductAd(config, product, keyword, slotId, rank, priority, targetCategory = "전체") {
  const sourceUrl = product.productUrl || product.landingUrl || product.shortenUrl || "";
  const idSeed = `${targetCategory}:${product.productId || product.itemId || sourceUrl || `${slotId}:${keyword}:${rank}`}`;
  return {
    id: `coupang_auto_${slotId}_${hashId(idSeed)}`,
    slotId,
    provider: "coupang",
    enabled: true,
    label: "제휴 링크",
    sponsorName: "Coupang Partners",
    title: String(product.productName || `${keyword} 추천 상품`).trim(),
    description: productDescription(product, keyword),
    cta: "쿠팡에서 보기",
    targetUrl: sourceUrl,
    imageUrl: String(product.productImage || product.imageUrl || "").trim(),
    disclosure: config.disclosure,
    priority,
    targetCategory,
    targetRegion: "전체",
    generatedBy: GENERATED_BY,
    keyword,
    productId: product.productId || null,
  };
}

function buildDeeplinkAd(config, link, keyword, slotId, priority, targetCategory = "전체") {
  const targetUrl = link.shortenUrl || link.landingUrl || link.originalUrl || "";
  return {
    id: `coupang_auto_${slotId}_${hashId(`${targetCategory}:${targetUrl || keyword}`)}`,
    slotId,
    provider: "coupang",
    enabled: true,
    label: "제휴 링크",
    sponsorName: "Coupang Partners",
    title: `${keyword} 추천 상품 모아보기`,
    description: "체험단 콘텐츠 제작에 필요한 장비와 소모품을 확인해보세요.",
    cta: "쿠팡에서 보기",
    targetUrl,
    imageUrl: "",
    disclosure: config.disclosure,
    priority,
    targetCategory,
    targetRegion: "전체",
    generatedBy: GENERATED_BY,
    keyword,
    productId: null,
  };
}

async function appendProductAdsForSlot({
  ads,
  cache,
  config,
  keywords,
  maxAds,
  priorityBase,
  slotId,
  targetCategory = "전체",
}) {
  let generated = 0;

  for (let keywordIndex = 0; keywordIndex < keywords.length && generated < maxAds; keywordIndex += 1) {
    const keyword = keywords[keywordIndex];
    const products = await getProductsForKeyword(config, cache, keyword);

    products.slice(0, 1).forEach((product) => {
      if (generated >= maxAds) return;
      ads.push(
        buildProductAd(
          config,
          product,
          keyword,
          slotId,
          generated + 1,
          priorityBase - generated,
          targetCategory,
        ),
      );
      generated += 1;
    });
  }

  return generated;
}

async function buildGeneratedAds(config) {
  const ads = [];
  const productCache = new Map();

  try {
    for (let slotIndex = 0; slotIndex < config.slots.length; slotIndex += 1) {
      const slotId = config.slots[slotIndex];
      const keywordCount = Math.min(config.perSlot, config.keywords.length);
      const keywords = Array.from({ length: keywordCount }, (_, keywordIndex) =>
        config.keywords[(slotIndex + keywordIndex) % config.keywords.length],
      );

      await appendProductAdsForSlot({
        ads,
        cache: productCache,
        config,
        keywords,
        maxAds: config.perSlot,
        priorityBase: 100 - slotIndex * 10,
        slotId,
      });

      if (config.categorySlots.includes(slotId)) {
        const entries = Object.entries(config.categoryKeywords);
        for (let categoryIndex = 0; categoryIndex < entries.length; categoryIndex += 1) {
          const [targetCategory, categoryKeywords] = entries[categoryIndex];
          await appendProductAdsForSlot({
            ads,
            cache: productCache,
            config,
            keywords: safeArray(categoryKeywords),
            maxAds: config.categoryPerSlot,
            priorityBase: 80 - categoryIndex,
            slotId,
            targetCategory,
          });
        }
      }
    }

    if (ads.length) return ads;
  } catch (error) {
    console.warn(`[ads] product search unavailable, falling back to deeplink ads: ${error.message}`);
  }

  const keywords = config.slots.map((_, index) => config.keywords[index % config.keywords.length]);
  const links = await createSearchDeeplinks(config, keywords);

  return config.slots
    .map((slotId, index) => buildDeeplinkAd(config, links[index] || {}, keywords[index], slotId, 100 - index * 10))
    .filter((ad) => ad.targetUrl);
}

function readCurrentAds() {
  if (!fs.existsSync(ADS_PATH)) {
    return {
      version: 1,
      ads: [],
    };
  }

  const payload = JSON.parse(fs.readFileSync(ADS_PATH, "utf8"));
  return {
    version: Number(payload.version || 1),
    updatedAt: payload.updatedAt || null,
    ads: safeArray(payload.ads),
  };
}

function shouldReplaceAd(config, ad) {
  if (ad?.generatedBy === GENERATED_BY) return true;
  if (!config.replaceExisting) return false;
  if (ad?.managedBy === "manual" || ad?.preserve === true) return false;
  return ad?.provider === "coupang";
}

function mergeAds(currentPayload, generatedAds, config) {
  const keptAds = currentPayload.ads.filter((ad) => !shouldReplaceAd(config, ad));
  return {
    version: currentPayload.version || 1,
    updatedAt: new Date().toISOString(),
    ads: [...generatedAds, ...keptAds],
  };
}

function writeAds(payload) {
  fs.mkdirSync(path.dirname(ADS_PATH), { recursive: true });
  fs.writeFileSync(ADS_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
}

function printEnvCheck(config) {
  const missing = validateConfig(config);
  const rows = [
    ["COUPANG_PARTNERS_ACCESS_KEY", missing.includes("COUPANG_PARTNERS_ACCESS_KEY") ? "missing" : "set"],
    ["COUPANG_PARTNERS_SECRET_KEY", missing.includes("COUPANG_PARTNERS_SECRET_KEY") ? "missing" : "set"],
    ["COUPANG_PARTNERS_SUB_ID", config.subId ? "set" : "empty"],
    ["COUPANG_AD_KEYWORDS", `${config.keywords.length} keyword(s)`],
    ["COUPANG_AD_CATEGORY_KEYWORDS", `${Object.keys(config.categoryKeywords).length} categor(y/ies)`],
    ["COUPANG_AD_CATEGORY_SLOTS", `${config.categorySlots.length} slot(s)`],
    ["COUPANG_AD_SLOTS", `${config.slots.length} slot(s)`],
  ];

  for (const [name, status] of rows) console.log(`${name}: ${status}`);

  if (missing.length) {
    console.error(`[ads] missing required env: ${missing.join(", ")}`);
    process.exitCode = 1;
  }
}

async function main() {
  loadEnvFile();
  const config = getConfig();
  const args = new Set(process.argv.slice(2));

  if (args.has("--check-env")) {
    printEnvCheck(config);
    return;
  }

  const missing = validateConfig(config);
  if (missing.length) {
    throw new Error(`Missing required env: ${missing.join(", ")}`);
  }

  const generatedAds = await buildGeneratedAds(config);
  const currentPayload = readCurrentAds();
  const mergedPayload = mergeAds(currentPayload, generatedAds, config);

  if (args.has("--dry-run")) {
    console.log(`[ads] dry run: generated ${generatedAds.length} Coupang ad(s)`);
    console.log(`[ads] dry run: final ads.json would contain ${mergedPayload.ads.length} ad(s)`);
    return;
  }

  writeAds(mergedPayload);
  console.log(`[ads] generated ${generatedAds.length} Coupang ad(s)`);
  console.log(`[ads] wrote ${path.relative(PROJECT_ROOT, ADS_PATH)}`);
}

main().catch((error) => {
  console.error(`[ads] ${error.message}`);
  process.exitCode = 1;
});
