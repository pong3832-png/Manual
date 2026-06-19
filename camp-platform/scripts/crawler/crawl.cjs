const axios = require("axios");
const cheerio = require("cheerio");
const fs = require("fs");
const https = require("https");
const path = require("path");
const { chromium } = require("playwright");
const { TextDecoder } = require("util");
const { createClient } = require("@supabase/supabase-js");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const CACHE_DIR = path.join(PROJECT_ROOT, ".cache");

loadDotEnv();
applyCrawlerRuntimeDefaults();

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || "";
const KAKAO_REST_API_KEY = process.env.KAKAO_REST_API_KEY || "";
const supabase =
  SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY
    ? createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
      auth: { persistSession: false },
    })
    : null;

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
  Referer: "https://www.google.com/",
};

const DEFAULT_REQUEST_TIMEOUT_MS = 15000;
const SUPABASE_BATCH_SIZE = Number(process.env.SUPABASE_BATCH_SIZE || 500);
const SUPABASE_OPERATION_ATTEMPTS = Math.max(1, Number(process.env.SUPABASE_OPERATION_ATTEMPTS || 4) || 4);
const SUPABASE_RETRY_DELAY_MS = Math.max(500, Number(process.env.SUPABASE_RETRY_DELAY_MS || 2000) || 2000);
const KAKAO_GEOCODE_CONCURRENCY = Math.max(1, Number(process.env.KAKAO_GEOCODE_CONCURRENCY || 2) || 2);
const KAKAO_GEOCODE_BATCH_DELAY_MS = Math.max(0, Number(process.env.KAKAO_GEOCODE_BATCH_DELAY_MS || 250) || 250);
const SERVICE_CAMPAIGNS_PATH = path.join(PROJECT_ROOT, "public", "campaigns.json");
const CRAWLER_ARTIFACT_DIR = path.resolve(
  PROJECT_ROOT,
  process.env.CRAWLER_ARTIFACT_DIR || ".cache/crawl-artifacts",
);
const QUALITY_GATE_MODE = String(process.env.QUALITY_GATE_MODE || "early").toLowerCase();
const QUALITY_GATE_ENABLED = !["0", "false", "off", "disabled"].includes(QUALITY_GATE_MODE);
const QUALITY_GATE_ENFORCE = QUALITY_GATE_ENABLED && QUALITY_GATE_MODE !== "warn";
const QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT || 70) || 70),
);
const QUALITY_GATE_MIN_COORDINATE_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_MIN_COORDINATE_PCT || 70) || 70),
);
const QUALITY_GATE_WARN_COORDINATE_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_WARN_COORDINATE_PCT || 80) || 80),
);
const QUALITY_GATE_WARN_ADDRESS_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_WARN_ADDRESS_PCT || 70) || 70),
);
const QUALITY_GATE_MIN_COORDINATE_SAMPLE = Math.max(
  1,
  Number(process.env.QUALITY_GATE_MIN_COORDINATE_SAMPLE || 20) || 20,
);
const QUALITY_GATE_MAX_PLATFORM_DROP_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_MAX_PLATFORM_DROP_PCT || 80) || 80),
);
const QUALITY_GATE_MAX_PLATFORM_COORDINATE_DROP_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_MAX_PLATFORM_COORDINATE_DROP_PCT || 80) || 80),
);
const QUALITY_GATE_MAX_PLATFORM_ADDRESS_DROP_PCT = Math.max(
  0,
  Math.min(100, Number(process.env.QUALITY_GATE_MAX_PLATFORM_ADDRESS_DROP_PCT || 80) || 80),
);
const QUALITY_GATE_MIN_PLATFORM_BASELINE = Math.max(
  1,
  Number(process.env.QUALITY_GATE_MIN_PLATFORM_BASELINE || 20) || 20,
);
const QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT = Math.max(
  1,
  Math.min(100, Number(process.env.QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT || 30) || 30),
);
const QUALITY_GATE_MIN_COORDINATE_CLUSTER = Math.max(
  20,
  Number(process.env.QUALITY_GATE_MIN_COORDINATE_CLUSTER || 50) || 50,
);
const CAMPAIGN_STALE_WARN_DAYS = Math.max(
  1,
  Number(process.env.CAMPAIGN_STALE_WARN_DAYS || 2) || 2,
);
const CAMPAIGN_STALE_HIDE_DAYS = Math.max(
  CAMPAIGN_STALE_WARN_DAYS,
  Number(process.env.CAMPAIGN_STALE_HIDE_DAYS || 7) || 7,
);
const MRBLOG_STORAGE_STATE_PATH = path.join(CACHE_DIR, "mrblog-storage-state.json");
const KAKAO_GEOCODE_CACHE_PATH = path.join(CACHE_DIR, "kakao-geocode-cache.json");
const RETRYABLE_NETWORK_CODES = new Set([
  "ECONNABORTED",
  "ECONNRESET",
  "ETIMEDOUT",
  "ERR_NETWORK",
  "EAI_AGAIN",
]);
const LEGACY_TLS_AGENT = new https.Agent({
  ciphers: "DEFAULT@SECLEVEL=0",
  minVersion: "TLSv1",
});

const PLATFORM_SEEDS = [
  {
    id: "reviewnote",
    name: "reviewnote",
    base_url: "https://www.reviewnote.co.kr/campaigns",
    description: "reviewnote public campaigns",
    color: "#E53935",
    emoji: "R",
  },
  {
    id: "mrblog",
    name: "mrblog",
    base_url: "https://www.mrblog.net",
    description: "mrblog public campaigns",
    color: "#FB8C00",
    emoji: "M",
  },
  {
    id: "reviewplace",
    name: "reviewplace",
    base_url: "https://www.reviewplace.co.kr",
    description: "reviewplace public campaigns",
    color: "#5E35B1",
    emoji: "P",
  },
  {
    id: "revu",
    name: "revu",
    base_url: "https://www.revu.net",
    description: "revu experience campaigns",
    color: "#1E88E5",
    emoji: "V",
  },
  {
    id: "seouloba",
    name: "seouloba",
    base_url: "https://seoulouba.co.kr",
    description: "seouloba public campaigns",
    color: "#F57C00",
    emoji: "S",
  },
  {
    id: "dinner",
    name: "dinnerqueen",
    base_url: "https://dinnerqueen.net",
    description: "dinnerqueen public campaigns",
    color: "#D81B60",
    emoji: "D",
  },
  {
    id: "tqueens",
    name: "택배의여왕",
    base_url: "https://tqueens.net",
    description: "tqueens delivery campaigns",
    color: "#7E57C2",
    emoji: "TQ",
  },
  {
    id: "gangnam",
    name: "gangnam",
    base_url: "https://xn--939au0g4vj8sq.net",
    description: "gangnam public campaigns",
    color: "#8E24AA",
    emoji: "G",
  },
  {
    id: "pavlo",
    name: "pavlo",
    base_url: "https://pavlovu.com",
    description: "pavlo public campaigns",
    color: "#00897B",
    emoji: "P",
  },
  {
    id: "popomon",
    name: "popomon",
    base_url: "https://popomon.com",
    description: "popomon public campaigns",
    color: "#7C4DFF",
    emoji: "O",
  },
  {
    id: "comeplay",
    name: "놀러와체험단",
    base_url: "https://www.cometoplay.kr",
    description: "놀러와체험단 public campaigns",
    color: "#3949AB",
    emoji: "C",
  },
  {
    id: "tble",
    name: "tble",
    base_url: "https://tble.kr",
    description: "tble public campaigns",
    color: "#5C6BC0",
    emoji: "T",
  },
  {
    id: "ringble",
    name: "ringble",
    base_url: "https://www.ringble.co.kr",
    description: "ringble public campaigns",
    color: "#F4511E",
    emoji: "RG",
  },
  {
    id: "chvu",
    name: "체험뷰",
    base_url: "https://chvu.co.kr",
    description: "체험뷰 public campaigns",
    color: "#00A8A8",
    emoji: "C",
  },
];

const REVU_API_URL = "https://api.weble.net/v1/campaigns";
const REVU_MEDIA = ["blog", "instagram", "youtube", "clip"];
const REVU_CATEGORIES = ["지역", "제품"];
const INSTRUCTION_DIR = path.join(PROJECT_ROOT, "docs", "research", "crawl-source-snippets");
const INSTRUCTION_CACHE = loadInstructionFiles();
const REVIEWNOTE_COOKIE =
  process.env.REVIEWNOTE_COOKIE || getInstructionHeaderValue("由щ럭?명듃", "cookie") || "";
const MRBLOG_COOKIE = process.env.MRBLOG_COOKIE || "";
const MRBLOG_X_CSRF_TOKEN = process.env.MRBLOG_X_CSRF_TOKEN || "";
const MRBLOG_LOGIN_ID =
  process.env.MRBLOG_LOGIN_ID || process.env.MRBLOG_EMAIL || process.env.MRBLOG_USERNAME || "";
const MRBLOG_LOGIN_PASSWORD =
  process.env.MRBLOG_LOGIN_PASSWORD || process.env.MRBLOG_PASSWORD || "";
const REVIEWPLACE_COOKIE =
  process.env.REVIEWPLACE_COOKIE || getInstructionHeaderValue("리뷰 플레이스", "cookie") || "";
const DINNERQUEEN_COOKIE =
  process.env.DINNERQUEEN_COOKIE || getInstructionHeaderValue("디너의 여왕", "cookie") || "";
const GANGNAM_COOKIE =
  process.env.GANGNAM_COOKIE || getInstructionHeaderValue("강남맛집", "cookie") || "";
const POPOMON_COOKIE =
  process.env.POPOMON_COOKIE || getInstructionHeaderValue("포포몬", "cookie") || "";
const REVU_AUTHORIZATION =
  normalizeBearerToken(
    process.env.REVU_AUTHORIZATION ||
    process.env.REVU_COOKIE ||
    getInstructionHeaderValue("레뷰", "authorization"),
  ) || "";
const REVU_LOGIN_ID =
  process.env.REVU_LOGIN_ID || process.env.REVU_EMAIL || "";
const REVU_LOGIN_PASSWORD =
  process.env.REVU_LOGIN_PASSWORD || process.env.REVU_PASSWORD || "";
const REVU_AUTH_CACHE_PATH = path.join(CACHE_DIR, "revu-auth-token.json");
const CRAWLER_TIMEOUT_MS = Number(process.env.CRAWLER_TIMEOUT_MS || 300000);
const DETAIL_ENRICH_CONCURRENCY = Math.max(1, Number(process.env.DETAIL_ENRICH_CONCURRENCY || 8) || 8);
const REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY = Math.max(
  1,
  Number(process.env.REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY || 2) || 2,
);
const REVIEWNOTE_DETAIL_BATCH_DELAY_MS = Math.max(
  0,
  Number(process.env.REVIEWNOTE_DETAIL_BATCH_DELAY_MS || 1200) || 1200,
);
const REVIEWNOTE_DETAIL_MAX_CONSECUTIVE_403 = Math.max(
  1,
  Number(process.env.REVIEWNOTE_DETAIL_MAX_CONSECUTIVE_403 || 24) || 24,
);
const REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS = Math.max(
  0,
  Number.isFinite(Number(process.env.REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS))
    ? Number(process.env.REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS)
    : 12,
);
const REVIEWNOTE_IGNORE_COOLDOWN = ["1", "true", "yes", "on"].includes(
  String(process.env.REVIEWNOTE_IGNORE_COOLDOWN || "").trim().toLowerCase(),
);
const REVIEWNOTE_FORBIDDEN_COOLDOWN_PATH = path.join(CACHE_DIR, "reviewnote-forbidden-cooldown.json");
const DINNERQUEEN_DETAIL_ENRICH_CONCURRENCY = Math.max(
  1,
  Number(process.env.DINNERQUEEN_DETAIL_ENRICH_CONCURRENCY || DETAIL_ENRICH_CONCURRENCY)
    || DETAIL_ENRICH_CONCURRENCY,
);
const DINNERQUEEN_DETAIL_ENRICH_LIMIT = (() => {
  const raw = process.env.DINNERQUEEN_DETAIL_ENRICH_LIMIT;
  if (raw === undefined || String(raw).trim() === "") return 1200;
  return Math.max(0, Number(raw) || 0);
})();
const DINNERQUEEN_DETAIL_TIMEOUT_MS = Math.max(
  5000,
  Number(process.env.DINNERQUEEN_DETAIL_TIMEOUT_MS || 12000) || 12000,
);
const DINNERQUEEN_DETAIL_BATCH_DELAY_MS = Math.max(
  0,
  Number(process.env.DINNERQUEEN_DETAIL_BATCH_DELAY_MS || 250) || 250,
);
const POPOMON_RENDERED_DETAIL_ENRICH_LIMIT = Math.max(
  0,
  Number(process.env.POPOMON_RENDERED_DETAIL_ENRICH_LIMIT || 240) || 240,
);
const POPOMON_RENDERED_DETAIL_ENRICH_CONCURRENCY = Math.max(
  1,
  Number(process.env.POPOMON_RENDERED_DETAIL_ENRICH_CONCURRENCY || 3) || 3,
);
const POPOMON_RENDERED_DETAIL_TIMEOUT_MS = Math.max(
  10000,
  Number(process.env.POPOMON_RENDERED_DETAIL_TIMEOUT_MS || 20000) || 20000,
);
const POPOMON_DETAIL_ENRICH_LIMIT = Math.max(
  0,
  Number(process.env.POPOMON_DETAIL_ENRICH_LIMIT || 720) || 720,
);
const SEOULOBA_DETAIL_ENRICH_LIMIT = Math.max(
  0,
  Number(process.env.SEOULOBA_DETAIL_ENRICH_LIMIT || 120) || 120,
);
const SEOULOBA_DETAIL_TIMEOUT_MS = Math.max(
  5000,
  Number(process.env.SEOULOBA_DETAIL_TIMEOUT_MS || 10000) || 10000,
);
const CHVU_DETAIL_ENRICH_LIMIT = Math.max(
  0,
  Number(process.env.CHVU_DETAIL_ENRICH_LIMIT || 240) || 240,
);
const CHVU_DETAIL_ENRICH_CONCURRENCY = Math.max(
  1,
  Number(process.env.CHVU_DETAIL_ENRICH_CONCURRENCY || 8) || 8,
);
const CHVU_DETAIL_ENRICH_MODE = String(process.env.CHVU_DETAIL_ENRICH_MODE || "missing").toLowerCase();
const CHVU_DETAIL_TIMEOUT_MS = Math.max(
  5000,
  Number(process.env.CHVU_DETAIL_TIMEOUT_MS || 12000) || 12000,
);
let activeCrawlerContext = null;
const kakaoGeocodeCache = loadJsonCache(KAKAO_GEOCODE_CACHE_PATH);

function loadDotEnv() {
  const envPath = path.join(PROJECT_ROOT, ".env");
  if (!fs.existsSync(envPath)) return;

  const envContent = fs.readFileSync(envPath, "utf-8");
  for (const rawLine of envContent.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const separatorIndex = line.indexOf("=");
    if (separatorIndex === -1) continue;

    const key = line.slice(0, separatorIndex).trim();
    let value = line.slice(separatorIndex + 1).trim();
    if (
      (value.startsWith("\"") && value.endsWith("\""))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key && !(key in process.env)) process.env[key] = value;
  }
}

function applyCrawlerRuntimeDefaults() {
  const runtimeDefaults = {
    CRAWLER_TIMEOUT_MS: "7200000",
    DETAIL_ENRICH_CONCURRENCY: "8",
    REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY: "2",
    REVIEWNOTE_DETAIL_BATCH_DELAY_MS: "1200",
    REVIEWNOTE_DETAIL_MAX_CONSECUTIVE_403: "24",
    DINNERQUEEN_DETAIL_ENRICH_CONCURRENCY: "24",
    DINNERQUEEN_DETAIL_ENRICH_LIMIT: "1200",
    DINNERQUEEN_DETAIL_TIMEOUT_MS: "12000",
    POPOMON_DETAIL_ENRICH_LIMIT: "720",
    POPOMON_RENDERED_DETAIL_ENRICH_LIMIT: "240",
    POPOMON_RENDERED_DETAIL_ENRICH_CONCURRENCY: "3",
    POPOMON_RENDERED_DETAIL_TIMEOUT_MS: "20000",
    CHVU_DETAIL_ENRICH_LIMIT: "240",
    CHVU_DETAIL_ENRICH_CONCURRENCY: "8",
    CHVU_DETAIL_ENRICH_MODE: "missing",
    CHVU_DETAIL_TIMEOUT_MS: "12000",
    SEOULOBA_DETAIL_ENRICH_LIMIT: "240",
    SEOULOBA_DETAIL_TIMEOUT_MS: "10000",
    SUPABASE_OPERATION_ATTEMPTS: "4",
    SUPABASE_RETRY_DELAY_MS: "2000",
    QUALITY_GATE_MODE: "early",
    QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT: "70",
    QUALITY_GATE_MIN_COORDINATE_PCT: "70",
    QUALITY_GATE_WARN_COORDINATE_PCT: "80",
    QUALITY_GATE_WARN_ADDRESS_PCT: "70",
    QUALITY_GATE_MIN_COORDINATE_SAMPLE: "20",
    QUALITY_GATE_MAX_PLATFORM_DROP_PCT: "80",
    QUALITY_GATE_MAX_PLATFORM_COORDINATE_DROP_PCT: "80",
    QUALITY_GATE_MAX_PLATFORM_ADDRESS_DROP_PCT: "80",
    QUALITY_GATE_MIN_PLATFORM_BASELINE: "20",
    QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT: "30",
    QUALITY_GATE_MIN_COORDINATE_CLUSTER: "50",
    CAMPAIGN_STALE_WARN_DAYS: "2",
    CAMPAIGN_STALE_HIDE_DAYS: "7",
  };

  for (const [key, value] of Object.entries(runtimeDefaults)) {
    if (!(key in process.env) || process.env[key] === "") {
      process.env[key] = value;
    }
  }

  if (!process.env.CRAWL_ONLY) {
    delete process.env.CRAWL_ONLY;
  }
}

function loadJsonCache(filePath) {
  try {
    if (!fs.existsSync(filePath)) return new Map();
    const raw = JSON.parse(fs.readFileSync(filePath, "utf-8"));
    return new Map(Object.entries(raw || {}));
  } catch {
    return new Map();
  }
}

function saveJsonCache(filePath, cache) {
  try {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(Object.fromEntries(cache), null, 2), "utf-8");
  } catch {
    // Cache save failure should not stop crawling.
  }
}

function loadInstructionFiles() {
  if (!fs.existsSync(INSTRUCTION_DIR)) return new Map();

  const files = fs.readdirSync(INSTRUCTION_DIR, { withFileTypes: true });
  const instructions = new Map();

  for (const file of files) {
    if (!file.isFile() || !file.name.toLowerCase().endsWith(".txt")) continue;

    const fullPath = path.join(INSTRUCTION_DIR, file.name);
    const raw = fs.readFileSync(fullPath);
    const text = decodeInstructionText(raw);
    instructions.set(file.name, text);
  }

  return instructions;
}

function decodeInstructionText(buffer) {
  const normalizedBuffer = Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  const encodings = ["utf-8", "euc-kr", "utf-16le"];

  for (const encoding of encodings) {
    try {
      const decoded = new TextDecoder(encoding, { fatal: true }).decode(normalizedBuffer);
      return decoded.replace(/^\uFEFF/, "");
    } catch {
      // Keep trying fallback encodings captured from the source TXT files.
    }
  }

  return new TextDecoder("utf-8").decode(normalizedBuffer).replace(/^\uFEFF/, "");
}

function getInstructionText(fileNameKeyword = "") {
  const entry = [...INSTRUCTION_CACHE.entries()].find(([name]) => name.includes(fileNameKeyword));
  return entry ? entry[1] : "";
}

function getInstructionHeaderValue(fileNameKeyword = "", headerName = "") {
  const text = getInstructionText(fileNameKeyword);
  if (!text || !headerName) return "";

  const escapedHeader = headerName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const patterns = [
    new RegExp(`${escapedHeader}\\s*[:=]\\s*([^\\r\\n]+)`, "i"),
    new RegExp(`${escapedHeader}\\s*[\\r\\n]+([^\\r\\n]+)`, "i"),
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    const value = match?.[1]?.trim();
    if (value) {
      return value.replace(/^["']|["']$/g, "");
    }
  }

  return "";
}

function createCrawlerContext(label) {
  const controller = new AbortController();
  const cleanups = new Set();

  return {
    label,
    signal: controller.signal,
    startedAt: Date.now(),
    abort(reason = "crawler timeout") {
      if (!controller.signal.aborted) {
        controller.abort(new Error(`${label}: ${reason}`));
      }
    },
    registerCleanup(cleanup) {
      if (typeof cleanup !== "function") return () => { };
      cleanups.add(cleanup);
      return () => cleanups.delete(cleanup);
    },
    async runCleanups() {
      const tasks = [...cleanups].map(async (cleanup) => {
        try {
          await cleanup();
        } catch {
          // Cleanup is best-effort after timeout/failure.
        }
      });
      cleanups.clear();
      await Promise.allSettled(tasks);
    },
  };
}

function getActiveCrawlerContext() {
  return activeCrawlerContext;
}

function withCrawlerContext(context, run) {
  const previousContext = activeCrawlerContext?.signal?.aborted ? null : activeCrawlerContext;
  activeCrawlerContext = context;
  return Promise.resolve()
    .then(run)
    .finally(() => {
      if (activeCrawlerContext === context) {
        activeCrawlerContext = previousContext;
      }
    });
}

function formatDurationMs(ms) {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function throwIfCrawlerAborted() {
  const context = getActiveCrawlerContext();
  if (context?.signal?.aborted) {
    throw context.signal.reason || new Error(`${context.label}: aborted`);
  }
}

function sleep(ms) {
  const context = getActiveCrawlerContext();
  if (!context?.signal) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  if (context.signal.aborted) {
    return Promise.reject(context.signal.reason || new Error(`${context.label}: aborted`));
  }

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup();
      resolve();
    }, ms);

    const onAbort = () => {
      clearTimeout(timer);
      cleanup();
      reject(context.signal.reason || new Error(`${context.label}: aborted`));
    };

    const unregisterCleanup = context.registerCleanup(() => {
      clearTimeout(timer);
      context.signal.removeEventListener("abort", onAbort);
    });

    function cleanup() {
      unregisterCleanup();
      context.signal.removeEventListener("abort", onAbort);
    }

    context.signal.addEventListener("abort", onAbort, { once: true });
  });
}

function isRetryableRequestError(error) {
  if (!error) return false;

  if (RETRYABLE_NETWORK_CODES.has(error.code)) {
    return true;
  }

  const status = error.response?.status;
  return typeof status === "number" && status >= 500;
}

function formatRequestError(error) {
  const status = error?.response?.status;
  const statusText = error?.response?.statusText;
  const responseMessage = error?.response?.data?.msg
    || error?.response?.data?.message
    || error?.response?.data?.error
    || "";
  return [
    error?.code || error?.message || "unknown",
    status ? `status ${status}` : "",
    statusText || "",
    responseMessage,
  ].filter(Boolean).join(" | ");
}

function isRetryableSupabaseError(error) {
  if (!error) return false;
  if (isRetryableRequestError(error)) return true;

  const message = `${error.message || ""} ${error.details || ""}`;
  return /fetch failed|ENOTFOUND|ECONNRESET|ETIMEDOUT|EAI_AGAIN|network/i.test(message);
}

async function runSupabaseOperation(label, task) {
  let lastError = null;

  for (let attempt = 1; attempt <= SUPABASE_OPERATION_ATTEMPTS; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      if (attempt === SUPABASE_OPERATION_ATTEMPTS || !isRetryableSupabaseError(error)) {
        break;
      }

      console.log(`  - supabase retry ${attempt}/${SUPABASE_OPERATION_ATTEMPTS - 1}: ${label} (${error.message})`);
      await sleep(SUPABASE_RETRY_DELAY_MS * attempt);
    }
  }

  throw lastError;
}

function normalizeBearerToken(value = "") {
  const trimmed = String(value).trim();
  if (!trimmed) return "";
  return trimmed.startsWith("Bearer ") ? trimmed : `Bearer ${trimmed}`;
}

let mrblogAuthState = {
  cookie: MRBLOG_COOKIE,
  csrfToken: MRBLOG_X_CSRF_TOKEN,
  source: MRBLOG_COOKIE && MRBLOG_X_CSRF_TOKEN ? "env" : "",
};

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function parseCookieHeader(cookieHeader = "") {
  return String(cookieHeader)
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const separatorIndex = part.indexOf("=");
      if (separatorIndex === -1) return null;

      const name = part.slice(0, separatorIndex).trim();
      const value = part.slice(separatorIndex + 1).trim();
      return name ? { name, value } : null;
    })
    .filter(Boolean);
}

function buildCookieHeader(cookieEntries = []) {
  return cookieEntries
    .filter((entry) => entry?.name)
    .map((entry) => `${entry.name}=${entry.value || ""}`)
    .join("; ");
}

function mergeCookieEntries(baseEntries = [], incomingEntries = []) {
  const merged = new Map();

  for (const entry of [...baseEntries, ...incomingEntries]) {
    if (!entry?.name) continue;
    merged.set(entry.name, {
      name: entry.name,
      value: entry.value || "",
    });
  }

  return [...merged.values()];
}

function parseSetCookieHeaders(setCookieHeaders = []) {
  return setCookieHeaders
    .map((header) => String(header || "").split(";")[0].trim())
    .filter(Boolean)
    .map((cookiePair) => {
      const separatorIndex = cookiePair.indexOf("=");
      if (separatorIndex === -1) return null;

      return {
        name: cookiePair.slice(0, separatorIndex).trim(),
        value: cookiePair.slice(separatorIndex + 1).trim(),
      };
    })
    .filter(Boolean);
}

function extractMrblogXsrfToken(cookieEntries = []) {
  const xsrfEntry = cookieEntries.find((entry) => entry.name === "XSRF-TOKEN");
  if (!xsrfEntry?.value) return "";

  try {
    return decodeURIComponent(xsrfEntry.value).replace(/^["']|["']$/g, "");
  } catch {
    return xsrfEntry.value.replace(/^["']|["']$/g, "");
  }
}

function hasMrblogSession(cookieEntries = []) {
  const names = new Set(cookieEntries.map((entry) => entry.name));
  return names.has("laravel_session") && names.has("XSRF-TOKEN");
}

async function getMetaContent(page, selector) {
  const locator = page.locator(selector).first();
  if ((await locator.count()) === 0) return "";

  const content = await locator.getAttribute("content").catch(() => "");
  return String(content || "").trim();
}

function createMrblogPlaywrightCookies(cookieHeader = "") {
  return parseCookieHeader(cookieHeader).map((entry) => ({
    name: entry.name,
    value: entry.value,
    domain: ".mrblog.net",
    path: "/",
    secure: true,
    httpOnly: entry.name === "laravel_session",
    sameSite: "Lax",
  }));
}

async function refreshMrblogSession({ reason = "session refresh" } = {}) {
  throwIfCrawlerAborted();
  const browser = await chromium.launch({ headless: process.env.MRBLOG_HEADLESS !== "0" });
  let context;
  let page;
  const crawlerContext = getActiveCrawlerContext();
  const unregisterBrowserCleanup = crawlerContext?.registerCleanup(async () => {
    await page?.close().catch(() => null);
    await context?.close().catch(() => null);
    await browser.close().catch(() => null);
  });

  try {
    const contextOptions = {
      locale: "ko-KR",
      userAgent: HEADERS["User-Agent"],
    };

    if (fs.existsSync(MRBLOG_STORAGE_STATE_PATH)) {
      contextOptions.storageState = MRBLOG_STORAGE_STATE_PATH;
    }

    context = await browser.newContext(contextOptions);

    if (MRBLOG_COOKIE) {
      const seededCookies = createMrblogPlaywrightCookies(MRBLOG_COOKIE);
      if (seededCookies.length > 0) {
        await context.addCookies(seededCookies);
      }
    }

    page = await context.newPage();
    console.log(`  - mrblog auth refresh: ${reason}`);
    await page.goto("https://www.mrblog.net/campaigns/region", {
      waitUntil: "domcontentloaded",
      timeout: 45000,
    });

    if (page.url().includes("/login") && MRBLOG_LOGIN_ID && MRBLOG_LOGIN_PASSWORD) {
      const idLocator = page
        .locator(
          'input[name="email"], input[name="login_id"], input[name="user_id"], input[name="id"], input[type="email"], input[type="text"]',
        )
        .first();
      const passwordLocator = page.locator('input[name="password"], input[type="password"]').first();
      await idLocator.fill(MRBLOG_LOGIN_ID);
      await passwordLocator.fill(MRBLOG_LOGIN_PASSWORD);

      const submitLocator = page
        .locator('button[type="submit"], input[type="submit"], button')
        .filter({ hasText: /濡쒓렇??LOGIN|Login/ })
        .first();

      if ((await submitLocator.count()) > 0) {
        await Promise.all([
          page.waitForLoadState("networkidle", { timeout: 45000 }).catch(() => null),
          submitLocator.click(),
        ]);
      } else {
        await passwordLocator.press("Enter");
        await page.waitForLoadState("networkidle", { timeout: 45000 }).catch(() => null);
      }
    }

    const csrfMetaToken = await getMetaContent(page, 'meta[name="csrf-token"]');
    if (page.url().includes("/login") && !MRBLOG_LOGIN_ID) {
      throw new Error(
        "mrblog session refresh reached login page. MRBLOG_LOGIN_ID/MRBLOG_LOGIN_PASSWORD is required for automatic renewal.",
      );
    }

    const cookieEntries = (await context.cookies("https://www.mrblog.net")).map((cookie) => ({
      name: cookie.name,
      value: cookie.value,
    }));

    if (!hasMrblogSession(cookieEntries)) {
      throw new Error(
        "mrblog session refresh failed: valid laravel_session/XSRF-TOKEN not found. " +
        "Set MRBLOG_LOGIN_ID/MRBLOG_LOGIN_PASSWORD or refresh MRBLOG_COOKIE.",
      );
    }

    ensureParentDir(MRBLOG_STORAGE_STATE_PATH);
    await context.storageState({ path: MRBLOG_STORAGE_STATE_PATH });

    mrblogAuthState = {
      cookie: buildCookieHeader(cookieEntries),
      csrfToken: csrfMetaToken || extractMrblogXsrfToken(cookieEntries),
      source: fs.existsSync(MRBLOG_STORAGE_STATE_PATH) ? "playwright-storage" : "playwright",
    };
    return mrblogAuthState;
  } finally {
    unregisterBrowserCleanup?.();
    await page?.close().catch(() => null);
    if (context) {
      await context.close().catch(() => null);
    }
    await browser.close().catch(() => null);
  }
}

async function syncMrblogPageSession({
  refererUrl = "https://www.mrblog.net/campaigns/region",
  cookieHeader = "",
} = {}) {
  const crawlerContext = getActiveCrawlerContext();
  const response = await axios({
    method: "get",
    url: refererUrl,
    httpsAgent: shouldUseLegacyTls(refererUrl) ? LEGACY_TLS_AGENT : undefined,
    maxRedirects: 5,
    validateStatus: (status) => status >= 200 && status < 300,
    headers: {
      ...HEADERS,
      Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
    },
    timeout: 30000,
    signal: crawlerContext?.signal,
    responseType: "text",
  });

  const html = String(response.data || "");
  if (/name=["']password["']|<form[^>]+login/i.test(html) || /\/login(?:[/?]|$)/.test(response.request?.res?.responseUrl || "")) {
    throw new Error("mrblog page session is not authenticated");
  }

  const $ = cheerio.load(html);
  const csrfMetaToken = cleanText($('meta[name="csrf-token"]').attr("content"));
  const mergedCookies = mergeCookieEntries(
    parseCookieHeader(cookieHeader),
    parseSetCookieHeaders(response.headers?.["set-cookie"] || []),
  );

  if (!hasMrblogSession(mergedCookies)) {
    throw new Error("mrblog page session sync failed: valid laravel_session/XSRF-TOKEN not found");
  }

  mrblogAuthState = {
    cookie: buildCookieHeader(mergedCookies),
    csrfToken: csrfMetaToken || extractMrblogXsrfToken(mergedCookies),
    source: "page-sync",
  };

  return mrblogAuthState;
}

async function getMrblogAuthState(forceRefresh = false, refererUrl = "https://www.mrblog.net/campaigns/region") {
  if (!forceRefresh && mrblogAuthState.cookie && mrblogAuthState.csrfToken && mrblogAuthState.source === "page-sync") {
    return mrblogAuthState;
  }

  if (mrblogAuthState.cookie) {
    try {
      return await syncMrblogPageSession({
        refererUrl,
        cookieHeader: mrblogAuthState.cookie,
      });
    } catch (error) {
      if (!MRBLOG_LOGIN_ID) {
        throw error;
      }
    }
  }

  return refreshMrblogSession({
    reason: forceRefresh ? "expired or rejected session" : "missing auth state",
  });
}

async function fetchRevuPage({ authorization, cat, page }) {
  const crawlerContext = getActiveCrawlerContext();
  let delay = 4000;

  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const response = await axios.get(REVU_API_URL, {
        headers: {
          ...HEADERS,
          Accept: "application/json, text/plain, */*",
          Origin: "https://www.revu.net",
          Referer: "https://www.revu.net/",
          Authorization: authorization,
        },
        params: {
          cat,
          class: "campaign",
          type: "play",
          enablePreferredMedia: "n",
          latestOnly: "n",
          sort: "latest",
          page,
          limit: 35,
          media: REVU_MEDIA,
        },
        timeout: 30000,
        signal: crawlerContext?.signal,
      });

      return response.data || {};
    } catch (error) {
      if (error?.response?.status !== 429 || attempt === 4) {
        throw error;
      }
      await sleep(delay);
      delay *= 2;
    }
  }

  return {};
}

function decodeHtml(buffer, encoding = "utf-8") {
  try {
    return new TextDecoder(encoding).decode(buffer);
  } catch {
    return new TextDecoder("utf-8").decode(buffer);
  }
}

async function fetchHtml(
  url,
  {
    method = "get",
    encoding = "utf-8",
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    attempts = 1,
    retryDelayMs = 1200,
    headers = {},
    params,
    data,
  } = {},
) {
  const crawlerContext = getActiveCrawlerContext();
  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await axios({
        method,
        url,
        httpsAgent: shouldUseLegacyTls(url) ? LEGACY_TLS_AGENT : undefined,
        headers: {
          ...HEADERS,
          ...headers,
        },
        params,
        data,
        timeout: timeoutMs,
        signal: crawlerContext?.signal,
        responseType: "arraybuffer",
      });

      return decodeHtml(response.data, encoding);
    } catch (error) {
      lastError = error;
      if (crawlerContext?.signal?.aborted) {
        throw crawlerContext.signal.reason || error;
      }
      if (attempt === attempts || !isRetryableRequestError(error)) {
        break;
      }

      console.log(`  - retry ${attempt}/${attempts - 1}: ${url} (${formatRequestError(error)})`);
      await sleep(retryDelayMs * attempt);
    }
  }

  throw lastError;
}

async function fetchJson(
  url,
  {
    method = "get",
    timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS,
    attempts = 1,
    retryDelayMs = 1200,
    headers = {},
    params,
    data,
  } = {},
) {
  const crawlerContext = getActiveCrawlerContext();
  let lastError = null;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await axios({
        method,
        url,
        httpsAgent: shouldUseLegacyTls(url) ? LEGACY_TLS_AGENT : undefined,
        headers: {
          ...HEADERS,
          Accept: "application/json, text/plain, */*",
          "X-Requested-With": "XMLHttpRequest",
          ...headers,
        },
        params,
        data,
        timeout: timeoutMs,
        signal: crawlerContext?.signal,
        responseType: "json",
      });

      return response.data;
    } catch (error) {
      lastError = error;
      if (crawlerContext?.signal?.aborted) {
        throw crawlerContext.signal.reason || error;
      }
      if (attempt === attempts || !isRetryableRequestError(error)) {
        break;
      }

      console.log(`  - retry ${attempt}/${attempts - 1}: ${url} (${formatRequestError(error)})`);
      await sleep(retryDelayMs * attempt);
    }
  }

  throw lastError;
}

async function fetchFirstAvailableHtml(urls, options) {
  let lastError = null;

  for (const url of urls) {
    try {
      return await fetchHtml(url, options);
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError;
}

async function fetchRenderedHtml(url, {
  waitForSelector = "body",
  timeoutMs = 30000,
  scrollSteps = 0,
  waitAfterLoadMs = 0,
  referer = "https://www.google.com/",
  headers = {},
} = {}) {
  const browser = await chromium.launch({ headless: process.env.CRAWLER_HEADLESS !== "0" });
  let context;
  let page;
  const crawlerContext = getActiveCrawlerContext();
  const unregisterBrowserCleanup = crawlerContext?.registerCleanup(async () => {
    await page?.close().catch(() => null);
    await context?.close().catch(() => null);
    await browser.close().catch(() => null);
  });

  try {
    context = await browser.newContext({
      locale: "ko-KR",
      userAgent: HEADERS["User-Agent"],
      extraHTTPHeaders: { Referer: referer, ...headers },
    });
    page = await context.newPage();
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    await page.waitForSelector(waitForSelector, { timeout: Math.min(timeoutMs, 15000) }).catch(() => null);

    for (let index = 0; index < scrollSteps; index += 1) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(900);
    }
    if (waitAfterLoadMs > 0) {
      await page.waitForTimeout(waitAfterLoadMs);
    }

    return await page.content();
  } finally {
    unregisterBrowserCleanup?.();
    await page?.close().catch(() => null);
    await context?.close().catch(() => null);
    await browser.close().catch(() => null);
  }
}

function cleanText(text = "") {
  return String(text ?? "")
    .replace(/<[^>]*>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&nbsp;/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isLikelyHashtagText(text = "") {
  const normalized = cleanText(text);
  if (!normalized) return false;

  const compact = normalized.replace(/\s+/g, "");
  const hashtagCount = (normalized.match(/#[^\s#]+/g) || []).length;
  return hashtagCount >= 1 && (
    compact === (normalized.match(/#[^\s#]+/g) || []).join("") ||
    /^#[^\s#]+(?:\s+#[^\s#]+)+$/.test(normalized)
  );
}

function normalizeProvisionText(text = "") {
  const normalized = cleanText(text)
    .replace(/^제공\s*내역\s*:?\s*/i, "")
    .replace(/^혜택\s*:?\s*/i, "")
    .replace(/^체험\s*상품\s*:?\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!normalized) return "";
  if (isLikelyHashtagText(normalized)) return "";
  if (/^(?:신청|모집|마감|주소|위치|방문형|배송형|기자단|릴스|클립)$/i.test(normalized)) return "";

  return normalized;
}

function isProvisionLabel(text = "") {
  return /(?:제공\s*내역|제공내역|혜택|체험\s*상품|체험상품)/.test(cleanText(text));
}

function extractComeplayProvisionFromDetail($) {
  const candidates = [];

  $(".etc_list2").each((_, element) => {
    const block = $(element);
    const label = cleanText(block.find(".tit_etc2").first().text());
    if (!isProvisionLabel(label)) return;

    candidates.push(block.find(".etc2").first().text());

    const clone = block.clone();
    clone.find(".tit_etc2").remove();
    candidates.push(clone.text());
  });

  $(".tit_etc2").each((_, element) => {
    const label = cleanText($(element).text());
    if (!isProvisionLabel(label)) return;

    candidates.push($(element).siblings(".etc2").first().text());
    candidates.push($(element).nextAll(".etc2").first().text());
  });

  return candidates
    .map((value) => normalizeProvisionText(value))
    .find(Boolean) || "";
}

function extractMrblogProvisionFromDetail($) {
  const candidates = [];

  $(".info_row").each((_, element) => {
    const block = $(element);
    const label = cleanText(block.find("dt").first().text());
    if (!isProvisionLabel(label)) return;

    const value = block.find("dd").first();
    candidates.push(value.find(".c_blue").first().text());
    candidates.push(value.text());
  });

  $("dt").each((_, element) => {
    const label = cleanText($(element).text());
    if (!isProvisionLabel(label)) return;

    const value = $(element).next("dd");
    candidates.push(value.find(".c_blue").first().text());
    candidates.push(value.text());
  });

  return candidates
    .map((value) => normalizeProvisionText(value))
    .find(Boolean) || "";
}

function extractDinnerqueenProvisionFromDetail($) {
  const candidates = [];
  const provisionSelector = [
    "p.qz-body-kr.mb-qz-body2-kr strong.w-600",
    "p.qz-body-kr strong.w-600",
    ".qz-body-kr strong.w-600",
  ].join(", ");
  const addProvisionCandidates = (scope) => {
    scope.find(provisionSelector).each((_, element) => {
      candidates.push($(element).text());
    });
  };

  $(".qz-collapse").each((_, element) => {
    const block = $(element);
    const label = cleanText(block.find("h1,h2,h3,h4,h5,dt,strong").first().text());
    if (!isProvisionLabel(label)) return;

    const content = block.find(".qz-collapse__content").first();
    const value = content.find("p.qz-body-kr.mb-qz-body2-kr strong.w-600").first();
    candidates.push(value.text());
  });

  $("h1,h2,h3,h4,h5,p,span,div,dt,li").each((_, element) => {
    const node = $(element);
    const clone = node.clone();
    clone.children().remove();
    const directLabel = cleanText(clone.text());
    const label = directLabel || cleanText(node.text());
    if (!isProvisionLabel(label) || label.length > 40) return;

    addProvisionCandidates(node.next());
    addProvisionCandidates(node.nextAll("p.qz-body-kr").first());
    addProvisionCandidates(node.parent());
    addProvisionCandidates(node.parent().next());
    addProvisionCandidates(node.closest("section,article,div"));
  });

  $(provisionSelector).each((_, element) => {
    candidates.push($(element).text());
  });

  return [...new Set(candidates)]
    .map((value) => normalizeProvisionText(value))
    .find(Boolean) || "";
}

function isReviewplaceProvisionCandidate(text = "") {
  const normalized = normalizeProvisionText(text);
  if (!normalized) return false;
  if (/^(?:주소|위치|장소|캠페인|선정|발표|리뷰|방문\s*위치)\b/i.test(normalized)) return false;
  return /(?:제공|이용권|입장권|무료|메뉴|선택|서비스|음료|간식|식사|PT|개월권|관리권|체험권|\d[\d,]*\s*원|\+)/i
    .test(normalized);
}

function extractReviewplaceProvisionFromDetail($) {
  const candidates = [];
  const addBstyleCandidates = (scope) => {
    scope.find("dd.bstyle, .bstyle").each((_, element) => {
      candidates.push($(element).text());
    });
  };

  $("dt,th,strong,b,p,span,div,li").each((_, element) => {
    const node = $(element);
    const clone = node.clone();
    clone.children().remove();
    const directLabel = cleanText(clone.text());
    const label = directLabel || cleanText(node.text());
    if (!isProvisionLabel(label) || label.length > 40) return;

    addBstyleCandidates(node.next());
    addBstyleCandidates(node.nextAll("dd.bstyle, .bstyle").first());
    addBstyleCandidates(node.parent());
    addBstyleCandidates(node.parent().next());
    addBstyleCandidates(node.closest("dl,tr,li,section,article,div"));
  });

  $("dd.bstyle").each((_, element) => {
    const text = $(element).text();
    if (isReviewplaceProvisionCandidate(text)) {
      candidates.push(text);
    }
  });

  return [...new Set(candidates)]
    .map((value) => normalizeProvisionText(value))
    .find((value) => isReviewplaceProvisionCandidate(value)) || "";
}

function isGangnamProvisionCandidate(text = "") {
  const normalized = normalizeProvisionText(text);
  if (!normalized) return false;
  if (/^(?:주소|위치|장소|업체|홈페이지|지도|예약|문의)\b/i.test(normalized)) return false;
  return /(?:체험권|이용권|식사권|상품권|관리권|제공|무료|상당|\d[\d,]*\s*원|만\s*원|PT|교정|시술|메뉴)/i
    .test(normalized);
}

function extractGangnamProvisionFromDetail($) {
  const candidates = [];

  [
    "p.sub_tit a[alt*='업체 홈페이지 링크']",
    "p.sub_tit a[href]",
    ".sub_tit a[style*='font-size']",
    ".sub_tit a",
  ].forEach((selector) => {
    $(selector).each((_, element) => {
      candidates.push($(element).text());
    });
  });

  $(".sub_tit").each((_, element) => {
    candidates.push($(element).text());
  });

  return [...new Set(candidates)]
    .map((value) => normalizeProvisionText(value))
    .find((value) => isGangnamProvisionCandidate(value)) || "";
}

const GANGNAM_BASE_URL = "https://xn--939au0g4vj8sq.net";

function getGangnamUrl(href = "") {
  try {
    return new URL(href, GANGNAM_BASE_URL).toString();
  } catch {
    return "";
  }
}

function mapGangnamListType(text = "", category = "") {
  const normalized = cleanText(text);
  if (
    String(category) === "30" ||
    normalized.includes("\uC81C\uD488") ||
    normalized.includes("\uBC30\uC1A1") ||
    normalized.includes("\uD3EC\uC7A5")
  ) {
    return "delivery";
  }
  if (normalized.includes("\uAE30\uC790\uB2E8")) return "reporter";
  return "visit";
}

function parseGangnamListCampaigns(html = "", { category = "", seenIds = new Set() } = {}) {
  const $ = cheerio.load(`<ul>${html || ""}</ul>`);
  const campaigns = [];
  let parsedCount = 0;

  $("li.list_item").each((index, element) => {
    const item = $(element);
    const href = item.find("a[href*='/cp/?id='], a[href*='?id=']").first().attr("href") || "";
    const hrefMatch = href.match(/[?&]id=(\d+)/);
    const dataProduct = cleanText(item.attr("data-product") || "");
    const campaignId = hrefMatch?.[1] || (dataProduct.match(/^\d+$/) ? dataProduct : "");
    if (!campaignId) return;
    parsedCount += 1;

    const id = `gn_${campaignId}`;
    if (seenIds.has(id)) return;

    const imageSrc = item.find("img.thumb_img[src], img[src]").first().attr("src") || "";
    const textRoot = item.clone();
    textRoot.find("img,script,style,noscript").remove();
    const full = cleanText(textRoot.text());
    const title =
      cleanText(item.find(".tit a, .tit, strong").first().text()) ||
      full.split(/\s{2,}/).map(cleanText).filter(isValidTitle)[0];
    if (!title) return;

    const provision = cleanText(
      item.find("dd.sub_tit, .sub_tit").first().text() ||
      item.find("a[href][style*='font-size']").first().text() ||
      item.find(".sect_desc, .desc_provision").first().text(),
    ) || null;
    const campaignUrl = href ? getGangnamUrl(href) : getGangnamUrl(`/cp/?id=${campaignId}`);

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: campaignUrl,
        platform: "gangnam",
        platformId: "gangnam",
        dDay: parseDDay(full),
        applyCount: parseNumber((full.match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber((full.match(/\uBAA8\uC9D1\s*([\d,]+)/) || [])[1] || ""),
        point: provision,
        type: mapGangnamListType(full, category),
        category: guessCategory(`${title} ${provision || ""} ${full}`),
        imageUrl: imageSrc ? getGangnamUrl(imageSrc) : "",
      }),
    );
    seenIds.add(id);
  });

  campaigns.parsedCount = parsedCount;
  campaigns.addedCount = campaigns.length;
  return campaigns;
}

function applyGangnamDetailLocationEnrichment(campaign, { extractedAddress = "", coords = null } = {}) {
  if (!campaign || campaign.type === "delivery") return campaign;

  if (extractedAddress) {
    campaign.locationRaw = extractedAddress;
    campaign.addressRaw = extractedAddress;
  }
  if (coords) {
    campaign.lat = coords.lat;
    campaign.lng = coords.lng;
    campaign.coordinateSource = coords.coordinateSource || "html";
  }

  return campaign;
}

function cleanAddressText(text = "") {
  return cleanText(String(text)
    .replace(/^(?:방문\s*(?:주소|위치)|주소|위치|장소)\s*:?\s*/i, "")
    .replace(/^諛⑸Ц\s*?꾩튂\s*:?\s*/i, ""))
    .replace(/\s*[.。]\s*$/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const KOREAN_ADDRESS_START_PATTERN =
  /(?:서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|제주특별자치도|제주도|서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)/;

function stripLeadingTextBeforeKoreanAddress(text = "") {
  const normalized = cleanText(text);
  const match = normalized.match(KOREAN_ADDRESS_START_PATTERN);
  if (!match || match.index === 0) return normalized;

  const leadingText = normalized.slice(0, match.index).trim();
  return leadingText.length <= 16 ? normalized.slice(match.index).trim() : normalized;
}

const LOCATION_TEXT_REJECT_PATTERN =
  /(?:체험|리뷰|캠페인|미션|가이드|필수|선정|모집|신청|제공|식사권|이용권|상품권|할인권|메뉴|추가주문|추가비용|본인부담|비용|청구|페널티|사진|동영상|본문|콘텐츠|인스타|해시태그|네이버\s*지도|플레이스|스폰서|예약|영업시간|전화번호|업체|광고주|등록|수정|삭제|문의|카카오톡|카톡|블로그|릴스|클립)/i;

function hasLocationTextSignal(text = "") {
  const normalized = cleanAddressText(text);
  if (!normalized) return false;

  return (
    /(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|[가-힣]+도)\s*[가-힣0-9]+(?:시|군|구)/.test(normalized) ||
    /[가-힣0-9]+(?:시|군|구)\s+[가-힣0-9.-]+(?:읍|면|동|리|로|길)/.test(normalized) ||
    /[가-힣0-9.-]+(?:로|길)\s*\d/.test(normalized) ||
    /[가-힣0-9]+(?:동|읍|면|리)\s*\d/.test(normalized) ||
    /[가-힣0-9]+역(?:\s*\d+\s*번\s*출구)?/.test(normalized)
  );
}

function getLocationTextScore(text = "") {
  const normalized = cleanAddressText(text);
  let score = 0;

  if (/(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|[가-힣]+도)\s*[가-힣0-9]+(?:시|군|구)/.test(normalized)) score += 50;
  if (/[가-힣0-9.-]+(?:로|길)\s*\d/.test(normalized)) score += 45;
  if (/[가-힣0-9]+(?:동|읍|면|리)\s*\d/.test(normalized)) score += 35;
  if (/[가-힣0-9]+역/.test(normalized)) score += 30;
  if (/\d/.test(normalized)) score += 5;
  if (normalized.length <= 80) score += 10;
  if (normalized.length > 100) score -= 20;

  return score;
}

function getReviewnoteRegionText(item = {}) {
  const city = cleanText(item.city || "");
  const sido = cleanText(item.sido?.name || "");
  return [city, sido]
    .filter((value) => value && !/^(재택|전국)$/i.test(value))
    .join(" ");
}

function getReviewnoteNumericId(campaign = {}) {
  const match = String(campaign.id || "").match(/^rn_(\d+)$/);
  return match ? match[1] : "";
}

function getReviewnoteDetailPayload(payload) {
  if (!payload || typeof payload !== "object") return null;
  return payload.campaign || payload.object || payload.data || payload;
}

function getReviewnoteDateIso(value) {
  const parsed = parseDateInput(value);
  return parsed ? parsed.toISOString() : null;
}

function isReviewnoteClosedStatus(value = "") {
  const normalized = cleanText(value).toLowerCase();
  if (!normalized) return false;
  return /closed|ended|expired|completed|rejected|cancel|마감|종료|완료|취소/.test(normalized);
}

function applyReviewnoteDetailData(campaign, payload) {
  const detail = getReviewnoteDetailPayload(payload);
  if (!detail) return false;

  const address = pickBestLocationText(
    [detail.address1, detail.address2].filter(Boolean).join(" "),
    detail.fullAddress,
    detail.roadAddress,
    detail.jibunAddress,
    detail.address,
  );
  const coords = buildCoordinate(
    detail.lat ?? detail.latitude,
    detail.lng ?? detail.longitude ?? detail.lon,
    "reviewnote_api",
  );
  const sourceStartedAt = getReviewnoteDateIso(detail.applyStartAt);
  const sourceEndedAt = getReviewnoteDateIso(detail.applyEndAt);
  const dDay = sourceEndedAt ? daysUntilKstDate(sourceEndedAt) : parseDDayOrDate(detail.dDay ?? detail.dday);
  const regionText = getReviewnoteRegionText(detail);
  const city = cleanText(detail.city || "");
  const sido = cleanText(detail.sido?.name || detail.sido || "");
  let changed = false;

  if (address) {
    campaign.locationRaw = address;
    campaign.addressRaw = address;
    changed = true;
  }

  if (coords && !isKnownBadMapCoordinate(coords.lat, coords.lng)) {
    campaign.lat = coords.lat;
    campaign.lng = coords.lng;
    campaign.coordinateSource = coords.coordinateSource;
    changed = true;
  }

  if (sourceStartedAt) {
    campaign.sourceStartedAt = sourceStartedAt;
    changed = true;
  }
  if (sourceEndedAt) {
    campaign.sourceEndedAt = sourceEndedAt;
    changed = true;
  }
  if (Number.isFinite(dDay)) {
    campaign.dDay = dDay;
    changed = true;
    if (dDay < 0) {
      closeCampaignFromDetail(campaign, "reviewnote_api_deadline_past", dDay);
    }
  }
  if (isReviewnoteClosedStatus(detail.status)) {
    closeCampaignFromDetail(campaign, "reviewnote_api_status_closed", Number.isFinite(dDay) ? dDay : -1);
    changed = true;
  }
  if (city) {
    campaign.region = city;
    changed = true;
  }
  if (sido) {
    campaign.city = sido;
    changed = true;
  }
  if (regionText) {
    campaign.locationHint = regionText;
    changed = true;
  }
  if (Number.isFinite(Number(detail.applicantCount))) {
    campaign.applyCount = Number(detail.applicantCount);
    changed = true;
  }
  if (Number.isFinite(Number(detail.infNum))) {
    campaign.selectedCount = Number(detail.infNum);
    changed = true;
  }
  if (detail.infPoint !== undefined && detail.infPoint !== null) {
    campaign.point = `${detail.infPoint}P`;
    changed = true;
  }
  if (detail.category?.title) {
    campaign.category = normalizeCampaignCategory(
      cleanText(detail.category.title),
      getCampaignCategoryFallbackText(campaign),
      campaign.platformId,
    );
    changed = true;
  }

  return changed;
}

async function fetchReviewnoteDetailData(campaign) {
  const numericId = getReviewnoteNumericId(campaign);
  if (!numericId) return null;

  return fetchJson("https://www.reviewnote.co.kr/api/campaign", {
    timeoutMs: 15000,
    attempts: 1,
    retryDelayMs: 1200,
    params: { id: numericId },
    headers: {
      Referer: campaign.url,
      Origin: "https://www.reviewnote.co.kr",
      Cookie: REVIEWNOTE_COOKIE,
    },
  });
}

async function enrichReviewnoteDetails(campaigns) {
  const targets = campaigns.filter((campaign) => getReviewnoteNumericId(campaign));
  const chunks = chunkArray(targets, REVIEWNOTE_DETAIL_ENRICH_CONCURRENCY);
  const stats = {
    attempted: 0,
    enriched: 0,
    withAddress: 0,
    withCoordinates: 0,
    forbidden: 0,
    failed: 0,
    skipped: 0,
    consecutiveForbidden: 0,
    stopped: false,
  };

  for (let index = 0; index < chunks.length; index += 1) {
    throwIfCrawlerAborted();

    const results = await Promise.all(chunks[index].map(async (campaign) => {
      try {
        const payload = await fetchReviewnoteDetailData(campaign);
        const changed = applyReviewnoteDetailData(campaign, payload);
        return {
          status: "ok",
          changed,
          hasAddress: Boolean(getCampaignAddressText(campaign)),
          hasCoordinates: hasUsableCoordinates(campaign),
        };
      } catch (error) {
        const status = error?.response?.status;
        if (status === 403) return { status: "forbidden" };
        return { status: "failed", reason: formatRequestError(error) };
      }
    }));

    for (const result of results) {
      stats.attempted += 1;
      if (result.status === "ok") {
        stats.consecutiveForbidden = 0;
        if (result.changed) stats.enriched += 1;
        if (result.hasAddress) stats.withAddress += 1;
        if (result.hasCoordinates) stats.withCoordinates += 1;
      } else if (result.status === "forbidden") {
        stats.forbidden += 1;
        stats.consecutiveForbidden += 1;
      } else {
        stats.failed += 1;
      }
    }

    if (stats.consecutiveForbidden >= REVIEWNOTE_DETAIL_MAX_CONSECUTIVE_403) {
      stats.stopped = true;
      stats.skipped = Math.max(0, targets.length - stats.attempted);
      console.log(
        `  - reviewnote detail API stopped after ${stats.consecutiveForbidden} consecutive 403 responses; `
        + `${stats.skipped} remaining skipped`,
      );
      break;
    }

    if (
      chunks.length > 1
      && (index === 0 || index === chunks.length - 1 || (index + 1) % 10 === 0)
    ) {
      console.log(`  - reviewnote enrich ${Math.min(stats.attempted, targets.length)}/${targets.length}`);
    }

    if (REVIEWNOTE_DETAIL_BATCH_DELAY_MS > 0 && index < chunks.length - 1) {
      await sleep(REVIEWNOTE_DETAIL_BATCH_DELAY_MS);
    }
  }

  console.log(
    `  - reviewnote detail API summary: attempted ${stats.attempted}/${targets.length}, `
    + `enriched ${stats.enriched}, address ${stats.withAddress}, coords ${stats.withCoordinates}, `
    + `403 ${stats.forbidden}, failed ${stats.failed}, skipped ${stats.skipped}`,
  );

  return stats;
}

function getPopomonLocationTexts($) {
  const texts = [];

  $("span")
    .filter((_, element) => String($(element).attr("class") || "").includes("w-[calc(100%_-_20px)]"))
    .add($('div[class*="text-b-2"] > span:first-child'))
    .each((_, element) => {
      const cleaned = cleanAddressText($(element).text());
      if (isMeaningfulLocationText(cleaned)) {
        texts.push(cleaned);
      }
    });

  return [...new Set(texts)];
}

function parsePopomonTitle(rawTitle = "") {
  const normalized = cleanText(rawTitle);
  const match = normalized.match(/^\[([^\]]+)\]\s*(.+)$/);

  if (!match) {
    return {
      title: normalized,
      placeName: normalized,
      locationHint: "",
    };
  }

  const region = cleanCampaignAreaText((match[1] || "").replace(/[/>|]+/g, " "));
  const placeName = cleanText(match[2] || "");
  const keywordLocationHint = cleanAddressText(`${region} ${placeName}`);
  const locationHint = isMeaningfulCampaignAreaText(region) && placeName
    ? keywordLocationHint
    : pickBestLocationText(keywordLocationHint);

  return {
    title: placeName || normalized.replace(/^\[[^\]]+\]\s*/, "").trim() || normalized,
    placeName,
    locationHint,
  };
}

function extractPopomonDetailEnrichment(html = "") {
  const $ = cheerio.load(html);
  const bodyText = cleanText($("body").text());
  const popomonLocationTexts = getPopomonLocationTexts($);
  const candidateTexts = $(".address, .place")
    .map((_, element) => cleanAddressText($(element).text()))
    .get();
  const extractedAddress = pickBestLocationText(
    popomonLocationTexts,
    candidateTexts,
    extractAddressCandidates(bodyText),
  );
  const coords = extractLatLngFromHtml(html);
  const sourceStartedAt = extractSourceStartedAt($, bodyText);
  const deadlineInfo = extractDetailDeadlineInfo($, bodyText);
  const closedReason = detectClosedCampaignDetail($, bodyText);

  return { extractedAddress, coords, sourceStartedAt, deadlineInfo, closedReason };
}

function applyPopomonDetailEnrichment(campaign, enrichment = {}) {
  let changed = false;
  const { extractedAddress, coords, sourceStartedAt, deadlineInfo = {}, closedReason } = enrichment;

  if (extractedAddress) {
    campaign.locationRaw = extractedAddress;
    campaign.addressRaw = extractedAddress;
    changed = true;
  }
  if (sourceStartedAt) {
    campaign.sourceStartedAt = sourceStartedAt;
    changed = true;
  }
  if (deadlineInfo.sourceStartedAt && !campaign.sourceStartedAt) {
    campaign.sourceStartedAt = deadlineInfo.sourceStartedAt;
    changed = true;
  }
  if (deadlineInfo.sourceEndedAt) {
    campaign.sourceEndedAt = deadlineInfo.sourceEndedAt;
    changed = true;
  }
  if (Number.isFinite(deadlineInfo.dDay)) {
    campaign.dDay = deadlineInfo.dDay;
    changed = true;
    if (deadlineInfo.dDay < 0) {
      closeCampaignFromDetail(campaign, "detail_deadline_past", deadlineInfo.dDay);
    }
  }
  if (closedReason) {
    closeCampaignFromDetail(campaign, closedReason);
    changed = true;
  }
  if (coords) {
    campaign.lat = coords.lat;
    campaign.lng = coords.lng;
    campaign.coordinateSource = coords.coordinateSource || "html";
    changed = true;
  }

  return changed;
}

function isMeaningfulLocationText(text = "") {
  const normalized = cleanAddressText(text);
  if (!normalized || normalized.length < 2 || normalized.length > 120) return false;
  if (/^(지도|map|위치|주소|장소|배송|전국|전체|기타)$/i.test(normalized)) return false;
  if (/https?:\/\//i.test(normalized)) return false;
  if (LOCATION_TEXT_REJECT_PATTERN.test(normalized)) return false;
  if ((normalized.match(/[.!?。※]/g) || []).length > 1) return false;
  if (normalized.split(/\s+/).length > 18) return false;
  return hasLocationTextSignal(normalized);
}

function cleanCampaignAreaText(text = "") {
  return cleanAddressText(text)
    .replace(/(?:블로그|인스타그램?|릴스|클립)/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isMeaningfulCampaignAreaText(text = "") {
  const normalized = cleanCampaignAreaText(text);
  if (!normalized || normalized.length < 2 || normalized.length > 32) return false;
  if (/^(배송|전국|전체|기타|제품|구매평|기자단|맛집|카페|뷰티|생활|패션|서비스|체험|테스트)$/i.test(normalized)) return false;
  if (LOCATION_TEXT_REJECT_PATTERN.test(normalized)) return false;
  return hasLocationTextSignal(normalized) || /^[가-힣]{2,10}\s+[가-힣0-9]{2,10}(?:동|역|구|군|시|읍|면|리)?$/.test(normalized);
}

function pickBestCampaignAreaText(...values) {
  const candidates = values
    .flatMap((value) => {
      if (!value) return [];
      return Array.isArray(value) ? value : [value];
    })
    .map((value) => cleanCampaignAreaText(value))
    .filter(isMeaningfulCampaignAreaText);

  return candidates[0] || "";
}

function cleanCampaignPlaceNameForGeocoding(text = "") {
  return cleanText(text)
    .replace(/\[[^\]]+\]/g, " ")
    .replace(/\([^)]{1,40}\)/g, " ")
    .replace(/\s*신청하기\s*$/i, " ")
    .replace(/\s*(?:체험단|캠페인)\s*$/i, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isMeaningfulCampaignPlaceName(text = "") {
  const normalized = cleanCampaignPlaceNameForGeocoding(text);
  if (!normalized || normalized.length < 2 || normalized.length > 80) return false;
  if (/^(?:배송|전국|전체|기타|제품|구매평|기자단|릴스|클립|맛집|카페|뷰티|생활|패션|서비스|체험|테스트)$/i.test(normalized)) {
    return false;
  }
  if (/(?:신청|모집|제공|체험단|캠페인|원고료|포인트|랜덤픽|실속형|A세트|B세트)$/i.test(normalized)) {
    return false;
  }
  return /[가-힣A-Za-z0-9]{2,}/.test(normalized);
}

function parseRegionalPlaceTitle(rawTitle = "") {
  const original = cleanText(rawTitle);
  let rest = original;
  let region = "";

  while (rest) {
    const match = rest.match(/^\[([^\]]+)\]\s*/);
    if (!match) break;

    const bracketText = cleanCampaignAreaText((match[1] || "").replace(/[/>|·,]+/g, " "));
    if (!region && isMeaningfulCampaignAreaText(bracketText)) {
      region = bracketText;
    }

    rest = rest.slice(match[0].length).trim();
  }

  const placeName = cleanCampaignPlaceNameForGeocoding(rest || original.replace(/^\[[^\]]+\]\s*/, ""));
  if (!region || !isMeaningfulCampaignPlaceName(placeName)) {
    return { region: "", placeName: "", locationHint: "" };
  }

  return {
    region,
    placeName,
    locationHint: cleanAddressText(`${region} ${placeName}`),
  };
}

function extractAddressCandidates(text = "") {
  const normalized = stripLeadingTextBeforeKoreanAddress(cleanText(text));
  if (!normalized) return [];

  const patterns = [
    /([가-힣]+(?:특별시|광역시|자치시|자치도|도)?\s+[가-힣0-9]+(?:시|군|구)\s+[가-힣0-9.-]+(?:읍|면|동|리|로|길)\s*[0-9-]*(?:\s*[0-9-]+)?(?:\s*\d+층)?(?:\s*[가-힣A-Za-z0-9&().-]+)?)/g,
    /([가-힣]+(?:도)?\s+[가-힣0-9]+(?:시|군|구)\s+[가-힣0-9.-]+(?:읍|면|동|리|로|길)\s*[0-9-]*(?:\s*[0-9-]+)?(?:\s*\d+층)?(?:\s*[가-힣A-Za-z0-9&().-]+)?)/g,
  ];

  const matches = [];
  for (const pattern of patterns) {
    for (const match of normalized.matchAll(pattern)) {
      const value = cleanAddressText(match[1] || "");
      if (isMeaningfulLocationText(value)) {
        matches.push(value);
      }
    }
  }

  return [...new Set(matches)];
}

function pickBestLocationText(...values) {
  const candidates = values
    .flatMap((value) => {
      if (!value) return [];
      return Array.isArray(value) ? value : [value];
    })
    .map((value) => stripLeadingTextBeforeKoreanAddress(cleanAddressText(value)))
    .filter(isMeaningfulLocationText);

  if (!candidates.length) return "";
  return candidates.sort((left, right) => (
    getLocationTextScore(right) - getLocationTextScore(left) ||
    left.length - right.length
  ))[0];
}

function normalizeAddressForGeocoding(text = "") {
  return stripLeadingTextBeforeKoreanAddress(cleanAddressText(text))
    .replace(/https?:\/\/\S+/gi, " ")
    .replace(/\[[^\]]+\]/g, " ")
    .replace(/[|◈•]/g, " ")
    .replace(/\b(?:COPYRIGHT|ALL\s+RIGHTS\s+RESERVED).*$/i, " ")
    .replace(/\b(?:카카오톡|카카오채널|인스타|인스타그램|블로그문의|예약|영업시간)\b.*$/i, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function isMeaningfulGeocodeQuery(text = "", campaign = {}) {
  const normalized = cleanAddressText(text);
  if (isMeaningfulLocationText(normalized)) return true;
  if (isRegionalPlaceGeocodeQuery(normalized, campaign)) return true;
  if (campaign.platformId !== "popomon" || campaign.type === "delivery") return false;
  if (!normalized || normalized.length < 4 || normalized.length > 100) return false;
  if (/https?:\/\//i.test(normalized)) return false;
  if (LOCATION_TEXT_REJECT_PATTERN.test(normalized)) return false;
  if (/^(배송|전국|전체|기타|제품|구매평|기자단)\b/i.test(normalized)) return false;
  if (!KOREAN_ADDRESS_START_PATTERN.test(normalized)) return false;

  const tokens = normalized.split(/\s+/).filter(Boolean);
  if (tokens.length < 3 || tokens.length > 10) return false;

  const locationTokenCount = tokens.filter((token) => (
    KOREAN_ADDRESS_START_PATTERN.test(token) ||
    /[가-힣0-9]+(?:시|군|구|읍|면|동|리|역)$/.test(token)
  )).length;
  return locationTokenCount >= 1 && tokens.some((token) => /[가-힣A-Za-z0-9]{2,}/.test(token));
}

function isRegionalPlaceGeocodeQuery(text = "", campaign = {}) {
  if (!["dinner", "chvu", "popomon"].includes(campaign.platformId)) return false;

  const hint = parseRegionalPlaceTitle(campaign.title);
  if (!hint.locationHint) return false;

  const normalized = normalizeAddressForGeocoding(text);
  const normalizedHint = normalizeAddressForGeocoding(hint.locationHint);
  return normalized === normalizedHint;
}

function isRingbleTitleFallbackGeocodeQuery(text = "", campaign = {}) {
  const normalized = normalizeAddressForGeocoding(text);
  if (!normalized) return true;

  const hint = parseRegionalPlaceTitle(campaign.title);
  const normalizedRegion = normalizeAddressForGeocoding(hint.region);
  const normalizedLocationHint = normalizeAddressForGeocoding(hint.locationHint);

  if (normalizedRegion && normalized === normalizedRegion) return true;
  if (normalizedLocationHint && normalized === normalizedLocationHint) return true;
  return /^(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주|[가-힣]+도)\s+[가-힣0-9]+(?:시|군|구)$/.test(normalized);
}

function getRingbleGeocodeQuery(campaign = {}) {
  const candidates = [
    campaign.addressRaw,
    pickBestLocationText(campaign.addressRaw),
    ...extractAddressCandidates(campaign.addressRaw || ""),
  ]
    .map((value) => normalizeAddressForGeocoding(value))
    .filter((value) => {
      if (isRingbleTitleFallbackGeocodeQuery(value, campaign)) return false;
      return isMeaningfulLocationText(value);
    });

  return candidates[0] || "";
}

function getCampaignGeocodeQuery(campaign) {
  if (campaign?.platformId === "ringble") return getRingbleGeocodeQuery(campaign);

  const allowRegionalTitleHint = ["dinner", "chvu", "popomon"].includes(campaign.platformId);
  const titleLocationHint = allowRegionalTitleHint
    ? parseRegionalPlaceTitle(campaign.title).locationHint
    : "";
  const candidates = [
    campaign.addressRaw,
    campaign.locationRaw,
    campaign.placeName,
    campaign.stationName,
    titleLocationHint,
    pickBestLocationText(campaign.addressRaw, campaign.locationRaw),
    ...extractAddressCandidates(`${campaign.addressRaw || ""} ${campaign.locationRaw || ""}`),
  ]
    .map((value) => normalizeAddressForGeocoding(value))
    .filter((value) => isMeaningfulGeocodeQuery(value, campaign));

  // ✅ 실주소 있으면 최우선 반환
  if (candidates.length) return candidates[0];

  // ✅ 실주소 없을 때만 타이틀 [지역명] fallback
  // 예: "[강남] 스파 체험단" → "강남"
  const titleBracket = String(campaign.title || "").match(/^\[([^\]]{2,20})\]/);
  if (titleBracket) {
    const bracketed = normalizeAddressForGeocoding(titleBracket[1]);
    if (isMeaningfulLocationText(bracketed)) return bracketed;
  }

  return "";
}

async function geocodeAddressWithKakao(query) {
  const normalizedQuery = normalizeAddressForGeocoding(query);
  if (!normalizedQuery || !KAKAO_REST_API_KEY) return null;

  if (kakaoGeocodeCache.has(normalizedQuery)) {
    const cached = kakaoGeocodeCache.get(normalizedQuery) || null;
    if (!cached || !isKnownBadMapCoordinate(cached.lat, cached.lng)) {
      return cached;
    }
    kakaoGeocodeCache.delete(normalizedQuery);
  }

  const kakaoHeaders = {
    Authorization: `KakaoAK ${KAKAO_REST_API_KEY}`,
    Referer: "https://developers.kakao.com/",
  };

  // Step 1: full address search
  try {
    const payload = await fetchJson("https://dapi.kakao.com/v2/local/search/address.json", {
      timeoutMs: 12000,
      attempts: 2,
      retryDelayMs: 1000,
      params: { query: normalizedQuery, analyze_type: "similar" },
      headers: kakaoHeaders,
    });

    const [doc] = Array.isArray(payload?.documents) ? payload.documents : [];
    const result = normalizeKakaoGeocodeDocument(doc, "kakao_address");
    if (result) {
      kakaoGeocodeCache.set(normalizedQuery, result);
      return result;
    }
  } catch { }

  // Step 2: keyword search for landmark-like queries

  try {
    const payload = await fetchJson("https://dapi.kakao.com/v2/local/search/keyword.json", {
      timeoutMs: 12000,
      attempts: 2,
      retryDelayMs: 1000,
      params: { query: normalizedQuery, size: 1 },
      headers: kakaoHeaders,
    });

    const [doc] = Array.isArray(payload?.documents) ? payload.documents : [];
    const result = normalizeKakaoGeocodeDocument(doc, "kakao_keyword");
    if (result) {
      kakaoGeocodeCache.set(normalizedQuery, result);
      return result;
    }
  } catch { }

  // Step 3: retry with a shortened query
  // 예: "서울 강남구 OO로 12 2층 카페XX" -> "서울 강남구 OO로 12"
  const shortenedQuery = normalizedQuery
    .replace(/\s+\d+층.*$/, "")       // 층수 이하 제거
    .replace(/\s+[가-힣A-Za-z0-9]+$/, "") // 지점명 제거
    .trim();

  if (shortenedQuery && shortenedQuery !== normalizedQuery && shortenedQuery.length >= 5) {
    try {
      const payload = await fetchJson("https://dapi.kakao.com/v2/local/search/keyword.json", {
        timeoutMs: 12000,
        attempts: 1,
        retryDelayMs: 1000,
        params: { query: shortenedQuery, size: 1 },
        headers: kakaoHeaders,
      });

      const [doc] = Array.isArray(payload?.documents) ? payload.documents : [];
      const result = normalizeKakaoGeocodeDocument(doc, "kakao_keyword_short");
      if (result) {
        kakaoGeocodeCache.set(normalizedQuery, result);
        return result;
      }
    } catch {
      // 理쒖쥌 ?ㅽ뙣
    }
  }

  kakaoGeocodeCache.set(normalizedQuery, null);
  return null;
}

async function geocodeCampaignCoordinates(campaigns) {
  if (!KAKAO_REST_API_KEY) {
    console.log("  - KAKAO_REST_API_KEY is missing. Skip Kakao geocoding.");
    return;
  }

  const targets = campaigns.filter((campaign) => {
    if (!campaign) return false;
    if (isClosedCampaign(campaign)) return false;
    const hasBadCoords = isKnownBadMapCoordinate(campaign.lat, campaign.lng);
    // 실좌표(HTML 파싱) 있는 경우 → skip
    if (campaign.lat && campaign.lng && campaign.coordinateSource === "html" && !hasBadCoords) return false;
    // Kakao geocoded 좌표 이미 있는 경우 → skip
    if (campaign.lat && campaign.lng && campaign.coordinateSource?.startsWith("kakao") && !hasBadCoords) return false;
    // Naver rendered marker 좌표 이미 있는 경우 → skip
    if (campaign.lat && campaign.lng && campaign.coordinateSource?.startsWith("naver") && !hasBadCoords) return false;
    // 그 외 (좌표 없음 or unresolved) → geocode 대상
    return Boolean(getCampaignGeocodeQuery(campaign));
  });

  if (!targets.length) {
    saveJsonCache(KAKAO_GEOCODE_CACHE_PATH, kakaoGeocodeCache);
    return;
  }

  await processCampaignsInBatches("kakao-geocode", targets, async (campaign) => {
    try {
      const result = await geocodeAddressWithKakao(getCampaignGeocodeQuery(campaign));
      if (!result) return;
      campaign.lat = result.lat;
      campaign.lng = result.lng;
      campaign.coordinateSource = result.coordinateSource;
    } catch (error) {
      console.log(`  - kakao geocode failed (${campaign.id}): ${error.message}`);
    }
  }, { batchSize: KAKAO_GEOCODE_CONCURRENCY, batchDelayMs: KAKAO_GEOCODE_BATCH_DELAY_MS });

  saveJsonCache(KAKAO_GEOCODE_CACHE_PATH, kakaoGeocodeCache);
}

function extractLatLngFromHtml(html = "") {
  const text = String(html);
  const latLngMatch = text.match(/LatLng\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)/i);
  if (latLngMatch) {
    const coords = { lat: Number(latLngMatch[1]), lng: Number(latLngMatch[2]), coordinateSource: "html" };
    if (!isKnownBadMapCoordinate(coords.lat, coords.lng)) return coords;
  }

  const centerMatch = text.match(/center\s*:\s*new\s+kakao\.maps\.LatLng\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)/i);
  if (centerMatch) {
    const coords = { lat: Number(centerMatch[1]), lng: Number(centerMatch[2]), coordinateSource: "html" };
    if (!isKnownBadMapCoordinate(coords.lat, coords.lng)) return coords;
  }

  const naverMarkerCoords = extractNaverRenderedMapLatLngFromHtml(text);
  if (naverMarkerCoords) return naverMarkerCoords;

  return extractKakaoRenderedMapLatLngFromHtml(text);
}

function buildCoordinate(lat, lng, coordinateSource) {
  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  if (!isKoreaLatLng(parsedLat, parsedLng) || isKnownBadMapCoordinate(parsedLat, parsedLng)) {
    return null;
  }

  return { lat: parsedLat, lng: parsedLng, coordinateSource };
}

function extractLatLngFromObject(value, coordinateSource = "api") {
  if (!value || typeof value !== "object") return null;

  const stack = [value];
  const seen = new Set();
  const latKeys = ["lat", "latitude", "$lat", "mapLat", "placeLat", "addressLat", "gpsLat"];
  const lngKeys = ["lng", "lon", "long", "longitude", "$lng", "mapLng", "placeLng", "addressLng", "gpsLng"];

  while (stack.length) {
    const current = stack.shift();
    if (!current || typeof current !== "object" || seen.has(current)) continue;
    seen.add(current);

    for (const latKey of latKeys) {
      if (!(latKey in current)) continue;
      for (const lngKey of lngKeys) {
        if (!(lngKey in current)) continue;
        const coords = buildCoordinate(current[latKey], current[lngKey], coordinateSource);
        if (coords) return coords;
      }
    }

    for (const child of Object.values(current)) {
      if (child && typeof child === "object") {
        stack.push(child);
      }
    }
  }

  return null;
}

function parseCssPx(style = "", property = "") {
  const normalizedProperty = String(property).trim().toLowerCase();
  const declarations = String(style)
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);

  for (const declaration of declarations) {
    const separatorIndex = declaration.indexOf(":");
    if (separatorIndex < 0) continue;

    const key = declaration.slice(0, separatorIndex).trim().toLowerCase();
    if (key !== normalizedProperty) continue;

    const value = declaration.slice(separatorIndex + 1).trim();
    const match = value.match(/^(-?\d+(?:\.\d+)?)px$/i);
    return match ? Number(match[1]) : null;
  }

  return null;
}

function isKoreaLatLng(lat, lng) {
  return Number.isFinite(lat) && Number.isFinite(lng) && lat >= 32 && lat <= 39.5 && lng >= 124 && lng <= 132;
}

const KNOWN_BAD_MAP_COORDINATES = [
  // Kakao Maps sample/default center. This appears in source snippets even when it is not the shop location.
  { lat: 33.450701, lng: 126.570667 },
  // Generic Seoul center/default value seen in rendered map bootstrap code.
  { lat: 37.5665, lng: 126.978 },
  // Legacy Reviewnote fallback/company address coordinate. It is not a campaign shop location.
  { lat: 35.1720591571479, lng: 129.128432630796 },
  // Broad Kakao address fallback seen when Ringble only exposes title region hints instead of a visit address.
  { lat: 37.574703, lng: 127.002749 },
];

function isKnownBadMapCoordinate(lat, lng) {
  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) return false;

  return KNOWN_BAD_MAP_COORDINATES.some((coord) => (
    Math.abs(parsedLat - coord.lat) < 0.00001 &&
    Math.abs(parsedLng - coord.lng) < 0.00001
  ));
}

function normalizeKakaoGeocodeDocument(doc, coordinateSource) {
  if (!doc) return null;

  const lat = Number(doc.y);
  const lng = Number(doc.x);
  if (!isKoreaLatLng(lat, lng)) return null;
  if (isKnownBadMapCoordinate(lat, lng)) return null;

  return { lat, lng, coordinateSource };
}

function extractNaverRenderedMapLatLngFromHtml(html = "") {
  const text = String(html);
  if (!/(?:marker-default\.png|nmarker-|pstatic\.net\/static\/maps|경위도)/i.test(text)) {
    return null;
  }

  for (const match of text.matchAll(/(-?\d{2,3}\.\d{5,})\s*,\s*(-?\d{2,3}\.\d{5,})/g)) {
    const lng = Number(match[1]);
    const lat = Number(match[2]);
    if (isKoreaLatLng(lat, lng)) {
      return { lat, lng, coordinateSource: "naver_marker" };
    }
  }

  return null;
}

function wtmToWgs84(x, y) {
  const axis = 6378137;
  const flattening = 1 / 298.257222101;
  const eccentricitySquared = (2 * flattening) - (flattening * flattening);
  const secondEccentricitySquared = eccentricitySquared / (1 - eccentricitySquared);
  const originLat = 38 * Math.PI / 180;
  const originLng = 127 * Math.PI / 180;
  const falseEasting = 200000;
  const falseNorthing = 500000;
  const scale = 1;

  const meridionalArc = (phi) => {
    const e4 = eccentricitySquared * eccentricitySquared;
    const e6 = e4 * eccentricitySquared;
    return axis * (
      (1 - eccentricitySquared / 4 - (3 * e4) / 64 - (5 * e6) / 256) * phi
      - ((3 * eccentricitySquared) / 8 + (3 * e4) / 32 + (45 * e6) / 1024) * Math.sin(2 * phi)
      + ((15 * e4) / 256 + (45 * e6) / 1024) * Math.sin(4 * phi)
      - ((35 * e6) / 3072) * Math.sin(6 * phi)
    );
  };

  const e4 = eccentricitySquared * eccentricitySquared;
  const e6 = e4 * eccentricitySquared;
  const m0 = meridionalArc(originLat);
  const meridianDistance = m0 + ((y - falseNorthing) / scale);
  const mu = meridianDistance / (axis * (1 - eccentricitySquared / 4 - (3 * e4) / 64 - (5 * e6) / 256));
  const e1 = (1 - Math.sqrt(1 - eccentricitySquared)) / (1 + Math.sqrt(1 - eccentricitySquared));
  const footprintLat = mu
    + ((3 * e1) / 2 - (27 * (e1 ** 3)) / 32) * Math.sin(2 * mu)
    + ((21 * (e1 ** 2)) / 16 - (55 * (e1 ** 4)) / 32) * Math.sin(4 * mu)
    + ((151 * (e1 ** 3)) / 96) * Math.sin(6 * mu)
    + ((1097 * (e1 ** 4)) / 512) * Math.sin(8 * mu);

  const sinFootprint = Math.sin(footprintLat);
  const cosFootprint = Math.cos(footprintLat);
  const tanFootprint = Math.tan(footprintLat);
  const c1 = secondEccentricitySquared * cosFootprint * cosFootprint;
  const t1 = tanFootprint * tanFootprint;
  const n1 = axis / Math.sqrt(1 - eccentricitySquared * sinFootprint * sinFootprint);
  const r1 = axis * (1 - eccentricitySquared)
    / ((1 - eccentricitySquared * sinFootprint * sinFootprint) ** 1.5);
  const d = (x - falseEasting) / (n1 * scale);

  const lat = footprintLat - ((n1 * tanFootprint) / r1) * (
    (d ** 2) / 2
    - (5 + 3 * t1 + 10 * c1 - 4 * (c1 ** 2) - 9 * secondEccentricitySquared) * (d ** 4) / 24
    + (61 + 90 * t1 + 298 * c1 + 45 * (t1 ** 2) - 252 * secondEccentricitySquared - 3 * (c1 ** 2)) * (d ** 6) / 720
  );
  const lng = originLng + (
    d
    - (1 + 2 * t1 + c1) * (d ** 3) / 6
    + (5 - 2 * c1 + 28 * t1 - 3 * (c1 ** 2) + 8 * secondEccentricitySquared + 24 * (t1 ** 2)) * (d ** 5) / 120
  ) / cosFootprint;

  return { lat: lat * 180 / Math.PI, lng: lng * 180 / Math.PI };
}

function extractKakaoRenderedMapLatLngFromHtml(html = "") {
  const text = String(html);
  const markerSourcePattern = /(?:mapjsapi\/images\/(?:2x\/)?marker\.png|\/img\/myplace\.png)/i;
  if (!/mts\.daumcdn\.net\/api\/v1\/tile/i.test(text) || !markerSourcePattern.test(text)) {
    return null;
  }

  const markerIndex = text.search(markerSourcePattern);
  const markerContext = markerIndex >= 0 ? text.slice(Math.max(0, markerIndex - 700), markerIndex) : "";
  const markerMatches = [...markerContext.matchAll(/left\s*:\s*(-?\d+(?:\.\d+)?)px;[^"<>]*top\s*:\s*(-?\d+(?:\.\d+)?)px/gi)];
  const markerMatch = markerMatches.at(-1);
  if (!markerMatch) return null;

  const markerX = Number(markerMatch[1]);
  const markerY = Number(markerMatch[2]);
  if (!Number.isFinite(markerX) || !Number.isFinite(markerY)) return null;

  const tiles = [];
  const imageTagRegex = /<img\b[^>]*>/gi;
  for (const imageMatch of text.matchAll(imageTagRegex)) {
    const imageTag = imageMatch[0];
    const src = imageTag.match(/\bsrc=["']([^"']*mts\.daumcdn\.net\/api\/v1\/tile\/[^"']*\/latest\/(\d+)\/(\d+)\/(\d+)\.png[^"']*)["']/i);
    const styleAttribute = imageTag.match(/\bstyle=["']([^"']*)["']/i);
    if (!src || !styleAttribute) continue;

    const style = styleAttribute[1];
    const left = parseCssPx(style, "left");
    const top = parseCssPx(style, "top");
    const width = parseCssPx(style, "width");
    const height = parseCssPx(style, "height");
    const tileLevel = Number(src[2]);
    const tileY = Number(src[3]);
    const tileX = Number(src[4]);
    if ([left, top, width, height, tileLevel, tileX, tileY].every(Number.isFinite)) {
      tiles.push({ left, top, width, height, tileLevel, tileX, tileY });
    }
  }

  if (!tiles.length) return null;

  const containingTile = tiles.find((tile) => (
    markerX >= tile.left
    && markerX <= tile.left + tile.width
    && markerY >= tile.top
    && markerY <= tile.top + tile.height
  ));
  const tile = containingTile || tiles
    .map((candidate) => ({
      candidate,
      distance: Math.hypot(
        markerX - (candidate.left + candidate.width / 2),
        markerY - (candidate.top + candidate.height / 2),
      ),
    }))
    .sort((a, b) => a.distance - b.distance)[0]?.candidate;

  if (!tile) return null;

  const markerOffsetX = markerX - tile.left;
  const markerOffsetY = markerY - tile.top;
  const cssPixelToMeter = (2 ** (tile.tileLevel - 3)) * (256 / tile.width);
  const wtmX = (tile.tileX * tile.width * cssPixelToMeter) - 30000 + (markerOffsetX * cssPixelToMeter);
  const wtmY = (tile.tileY * tile.height * cssPixelToMeter) - 60000 + ((tile.height - markerOffsetY) * cssPixelToMeter);
  const coords = wtmToWgs84(wtmX, wtmY);

  if (!isKoreaLatLng(coords.lat, coords.lng)) return null;
  return { lat: coords.lat, lng: coords.lng, coordinateSource: "kakao_tile" };
}

function shouldUseLegacyTls(url = "") {
  return /https:\/\/tble\.kr/i.test(String(url));
}

function chunkArray(items, size) {
  const chunks = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

async function processCampaignsInBatches(label, campaigns, handler, { batchSize = DETAIL_ENRICH_CONCURRENCY, batchDelayMs = 0 } = {}) {
  const size = Math.max(1, Number(batchSize) || 1);
  const delayMs = Math.max(0, Number(batchDelayMs) || 0);
  const chunks = chunkArray(campaigns, size);

  for (let index = 0; index < chunks.length; index += 1) {
    throwIfCrawlerAborted();
    await Promise.all(chunks[index].map((campaign) => handler(campaign)));

    if (chunks.length > 1 && (index === 0 || index === chunks.length - 1 || (index + 1) % 10 === 0)) {
      console.log(`  - ${label} enrich ${Math.min((index + 1) * size, campaigns.length)}/${campaigns.length}`);
    }

    if (delayMs > 0 && index < chunks.length - 1) {
      await sleep(delayMs);
    }
  }
}

function isValidTitle(text = "") {
  return text.length > 3 && /[A-Za-z0-9\u3131-\uD79D]/.test(text) && !text.includes("javascript");
}
function parseDDay(text = "") {
  const normalized = cleanText(text);
  if (!normalized) return 99;
  if (/\uB9C8\uAC10|\uC885\uB8CC|\uC644\uB8CC|closed/i.test(normalized)) return -1;
  if (/\uC624\uB298\s*\uB9C8\uAC10|today\s*close/i.test(normalized)) return 0;
  if (/D\s*(?:-\s*)?day(?!\s*\d)/i.test(normalized)) return 0;

  const remainMatch = normalized.match(/(\d+)\s*(\uC77C\s*\uB0A8\uC74C|days?\s*left)/i);
  if (remainMatch) return Number(remainMatch[1]);

  const ddayMatch = normalized.match(/D\s*(?:-\s*)?(?:day\s*)?(\d+)/i);
  if (ddayMatch) return Number(ddayMatch[1]);
  return 99;
}

function isUnknownDDay(value) {
  const parsed = Number(value);
  return !Number.isFinite(parsed) || parsed >= 90;
}

function getKstDateParts(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(date.getTime())) return null;

  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "numeric",
    day: "numeric",
  })
    .formatToParts(date)
    .reduce((acc, part) => {
      if (part.type !== "literal") acc[part.type] = Number(part.value);
      return acc;
    }, {});
}

function parseSourceDateToken(match, now = new Date()) {
  const [, rawYear, rawMonth, rawDay] = match;
  const currentParts = getKstDateParts(now);
  if (!currentParts) return null;

  let year = currentParts.year;
  if (rawYear) {
    year = rawYear.length === 2
      ? (Number(rawYear) >= 70 ? 1900 : 2000) + Number(rawYear)
      : Number(rawYear);
  }

  const month = Number(rawMonth);
  const day = Number(rawDay);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;

  if (!rawYear && currentParts.month === 12 && month === 1) {
    year += 1;
  }

  const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}T00:00:00+09:00`;
  const parsed = Date.parse(iso);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
}

function extractSourceDateTokens(text = "", now = new Date()) {
  const normalized = cleanText(text);
  const datePattern = /(?:(\d{4}|\d{2})[./-])?(\d{1,2})[./-](\d{1,2})/g;
  return [...normalized.matchAll(datePattern)]
    .map((match) => parseSourceDateToken(match, now))
    .filter(Boolean);
}

function parseSourceDateRange(text = "", now = new Date()) {
  const tokens = extractSourceDateTokens(text, now);
  if (tokens.length < 2) return null;

  return {
    sourceStartedAt: tokens[0],
    sourceEndedAt: tokens[1],
  };
}

function parseDateInput(value) {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isFinite(value.getTime()) ? value : null;
  }

  const text = cleanText(String(value));
  if (/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text) || /(?:Z|[+-]\d{2}:?\d{2})$/.test(text)) {
    const parsedIso = Date.parse(text);
    if (Number.isFinite(parsedIso)) return new Date(parsedIso);
  }

  const timestampMatch = text.match(/^\d{10,13}$/);
  if (timestampMatch) {
    const timestamp = Number(text.length === 10 ? `${text}000` : text);
    const parsedTimestamp = new Date(timestamp);
    return Number.isFinite(parsedTimestamp.getTime()) ? parsedTimestamp : null;
  }
  if (/^\d+$/.test(text) && text.length !== 8) return null;
  const dateMatch = text.match(/(\d{4})[./-](\d{1,2})[./-](\d{1,2})/)
    || text.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/)
    || text.match(/(?:^|[^\d])(\d{4})(\d{2})(\d{2})(?:[^\d]|$)/);
  if (dateMatch) {
    const [, year, month, day] = dateMatch;
    const parsed = Date.parse(
      `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}T00:00:00+09:00`,
    );
    return Number.isFinite(parsed) ? new Date(parsed) : null;
  }

  const parsed = Date.parse(text);
  return Number.isFinite(parsed) ? new Date(parsed) : null;
}

function getKstDayNumber(value) {
  const date = parseDateInput(value);
  if (!date) return null;

  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .formatToParts(date)
    .reduce((acc, part) => {
      if (part.type !== "literal") acc[part.type] = Number(part.value);
      return acc;
    }, {});

  return Date.UTC(parts.year, parts.month - 1, parts.day) / 86400000;
}

function daysUntilKstDate(value, now = new Date()) {
  const targetDay = getKstDayNumber(value);
  const currentDay = getKstDayNumber(now);
  if (!Number.isFinite(targetDay) || !Number.isFinite(currentDay)) return null;
  return targetDay - currentDay;
}

function parseDDayOrDate(value, now = new Date()) {
  if (value === undefined || value === null || value === "") return null;
  if (typeof value === "number" && Number.isFinite(value)) {
    if (Math.abs(value) >= 1000000000) {
      const parsedDate = parseDateInput(value);
      if (parsedDate) {
        const dDay = daysUntilKstDate(parsedDate, now);
        if (Number.isFinite(dDay)) return dDay;
      }
    }
    return value;
  }

  const normalized = cleanText(String(value));
  if (!normalized) return null;

  const parsedDate = parseDateInput(normalized);
  if (parsedDate) {
    const dDay = daysUntilKstDate(parsedDate, now);
    if (Number.isFinite(dDay)) return dDay;
  }

  const numeric = normalized.replace(/,/g, "");
  if (/^-?\d+$/.test(numeric)) {
    return Number(numeric);
  }

  const parsedDDay = parseDDay(normalized);
  return isUnknownDDay(parsedDDay) ? null : parsedDDay;
}

function parseNumber(text = "") {
  const digits = String(text).replace(/[^\d]/g, "");
  return digits ? Number(digits) : 0;
}

function parseSourceDate(text = "") {
  const normalized = cleanText(text).replace(/\s+/g, "");
  const match = normalized.match(/(\d{4})[./-](\d{1,2})[./-](\d{1,2})/);
  const shortMatch = match ? null : normalized.match(/(?:^|[^\d])(\d{2})[./-](\d{1,2})[./-](\d{1,2})/);
  if (!match && !shortMatch) return null;

  const [, rawYear, month, day] = match || shortMatch;
  const year = rawYear.length === 2
    ? String((Number(rawYear) >= 70 ? 1900 : 2000) + Number(rawYear))
    : rawYear;
  const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}T00:00:00+09:00`;
  const parsed = Date.parse(iso);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
}

function extractSourceStartedAt($, bodyText = "") {
  const startLabels = [
    "\uBAA8\uC9D1 \uAE30\uAC04",
    "\uC2E0\uCCAD \uAE30\uAC04",
    "\uCEA0\uD398\uC778 \uAE30\uAC04",
    "\uC9C4\uD589 \uAE30\uAC04",
    "\uCCB4\uD5D8 \uAE30\uAC04",
    "\uC811\uC218 \uAE30\uAC04",
    "\uC774\uBCA4\uD2B8 \uAE30\uAC04",
    "모집시작일",
  ];

  for (const label of startLabels) {
    const labeledNode = $("dt, th, strong, b, span, div")
      .filter((_, element) => cleanText($(element).text()) === label)
      .first();

    if (labeledNode.length) {
      const candidateTexts = [
        labeledNode.next("dd").text(),
        labeledNode.next("td").text(),
        labeledNode.parent().find("dd").first().text(),
        labeledNode.parent().find("td").first().text(),
        labeledNode.parent().text(),
      ];

      for (const candidateText of candidateTexts) {
        const parsed = parseSourceDate(candidateText);
        if (parsed) return parsed;
      }
    }

    const fallbackMatch = cleanText(bodyText).match(
      new RegExp(`${label.replace(/\s+/g, "\\s*")}[^\\d]{0,20}(\\d{4}[./-]\\d{1,2}[./-]\\d{1,2})`, "i"),
    );
    if (fallbackMatch) {
      const parsed = parseSourceDate(fallbackMatch[1]);
      if (parsed) return parsed;
    }
  }

  return null;
}

function getDetailLabelTexts($, labels) {
  const normalizedLabels = labels.map((label) => cleanText(label).replace(/\s+/g, ""));
  const texts = [];

  $("dt, th, strong, b, span, div, p, li").each((_, element) => {
    const node = $(element);
    const clone = node.clone();
    clone.find("script,style,noscript").remove();
    const nodeText = cleanText(clone.text());
    const compactText = nodeText.replace(/\s+/g, "");
    if (!compactText || nodeText.length > 120) return;

    const matched = normalizedLabels.some((label) => compactText === label || compactText.startsWith(label));
    if (!matched) return;

    texts.push(
      node.next("dd").text(),
      node.next("td").text(),
      node.parent().find("dd").first().text(),
      node.parent().find("td").first().text(),
      node.parent().text(),
      nodeText,
    );
  });

  return texts.map(cleanText).filter(Boolean);
}

function extractDetailDeadlineInfo($, bodyText = "", now = new Date()) {
  const periodLabels = [
    "\uBAA8\uC9D1 \uAE30\uAC04",
    "\uC2E0\uCCAD \uAE30\uAC04",
    "\uCEA0\uD398\uC778 \uC2E0\uCCAD\uAE30\uAC04",
    "\uCEA0\uD398\uC778 \uC2E0\uCCAD \uAE30\uAC04",
    "\uB9AC\uBDF0\uC5B4 \uC2E0\uCCAD",
    "\uB9AC\uBDF0\uC5B4 \uC2E0\uCCAD\uAE30\uAC04",
    "\uCCB4\uD5D8\uB2E8 \uC2E0\uCCAD",
    "\uCCB4\uD5D8\uB2E8 \uBAA8\uC9D1\uAE30\uAC04",
    "\uCEA0\uD398\uC778 \uAE30\uAC04",
    "\uC811\uC218 \uAE30\uAC04",
    "\uC774\uBCA4\uD2B8 \uAE30\uAC04",
  ];
  const endLabels = [
    "\uBAA8\uC9D1 \uB9C8\uAC10\uC77C",
    "\uC2E0\uCCAD \uB9C8\uAC10\uC77C",
    "\uC811\uC218 \uB9C8\uAC10\uC77C",
    "\uB9C8\uAC10\uC77C",
    "\uBAA8\uC9D1 \uC885\uB8CC\uC77C",
    "\uC2E0\uCCAD \uC885\uB8CC\uC77C",
  ];

  const periodTexts = [
    ...getDetailLabelTexts($, periodLabels),
    ...periodLabels.flatMap((label) => {
      const match = cleanText(bodyText).match(new RegExp(`${label.replace(/\s+/g, "\\s*")}.{0,140}`, "i"));
      return match ? [match[0]] : [];
    }),
  ];

  for (const text of periodTexts) {
    const range = parseSourceDateRange(text, now);
    if (range) {
      return {
        ...range,
        dDay: daysUntilKstDate(range.sourceEndedAt, now),
      };
    }
  }

  const endTexts = [
    ...getDetailLabelTexts($, endLabels),
    ...endLabels.flatMap((label) => {
      const match = cleanText(bodyText).match(new RegExp(`${label.replace(/\s+/g, "\\s*")}.{0,80}`, "i"));
      return match ? [match[0]] : [];
    }),
  ];

  for (const text of endTexts) {
    const [sourceEndedAt] = extractSourceDateTokens(text, now);
    if (sourceEndedAt) {
      return {
        sourceEndedAt,
        dDay: daysUntilKstDate(sourceEndedAt, now),
      };
    }
  }

  return {};
}

function getDeadlineInfoFromDateText(text = "", now = new Date()) {
  const range = parseSourceDateRange(text, now);
  if (range) {
    return {
      ...range,
      dDay: daysUntilKstDate(range.sourceEndedAt, now),
    };
  }

  const [sourceEndedAt] = extractSourceDateTokens(text, now);
  if (!sourceEndedAt) return {};

  return {
    sourceEndedAt,
    dDay: daysUntilKstDate(sourceEndedAt, now),
  };
}

function isGangnamApplicationPeriodLabel(text = "") {
  const compact = cleanText(text).replace(/\s+/g, "");
  if (!compact) return false;
  if (/(?:리뷰등록|리뷰기간|리뷰어발표|결과발표|발표|체험기간|방문기간)/.test(compact)) return false;

  return /(?:캠페인)?(?:신청|모집|접수)기간/.test(compact)
    || /(?:신청|모집|접수)마감일/.test(compact);
}

function extractGangnamApplicationDeadlineInfo($, bodyText = "", now = new Date()) {
  const candidateTexts = [];

  $(".cmp_info dl, dl, tr").each((_, element) => {
    const node = $(element);
    const label = cleanText(node.find("dt, th").first().text());
    if (!isGangnamApplicationPeriodLabel(label)) return;

    candidateTexts.push(
      node.find("dd, td").first().text(),
      node.text(),
    );
  });

  const labelTexts = getDetailLabelTexts($, [
    "\uCEA0\uD398\uC778 \uC2E0\uCCAD\uAE30\uAC04",
    "\uCEA0\uD398\uC778 \uC2E0\uCCAD \uAE30\uAC04",
    "\uC2E0\uCCAD\uAE30\uAC04",
    "\uC2E0\uCCAD \uAE30\uAC04",
    "\uBAA8\uC9D1\uAE30\uAC04",
    "\uBAA8\uC9D1 \uAE30\uAC04",
    "\uC811\uC218\uAE30\uAC04",
    "\uC811\uC218 \uAE30\uAC04",
  ]);
  candidateTexts.push(...labelTexts);

  const compactBodyText = cleanText(bodyText);
  for (const label of ["캠페인 신청기간", "신청기간", "신청 기간", "모집기간", "모집 기간", "접수기간", "접수 기간"]) {
    const match = compactBodyText.match(new RegExp(`${label.replace(/\s+/g, "\\s*")}.{0,60}`));
    if (match) candidateTexts.push(match[0]);
  }

  for (const candidateText of candidateTexts.map(cleanText).filter(Boolean)) {
    const deadlineInfo = getDeadlineInfoFromDateText(candidateText, now);
    if (deadlineInfo.sourceEndedAt && Number.isFinite(deadlineInfo.dDay)) {
      return {
        ...deadlineInfo,
        deadlineSource: "gangnam_application_period",
      };
    }
  }

  return {};
}

function getClosedReasonFromText(text = "", { allowShortState = false } = {}) {
  const normalized = cleanText(text);
  if (!normalized) return "";

  const compact = normalized.replace(/\s+/g, "");
  const explicitPatterns = [
    /(?:모집|신청|접수|캠페인|체험단|리뷰어)(?:이|가)?(?:마감|종료|완료)(?:되었|됐|되었습니다|되었습니다|했|했습니다)/,
    /(?:마감|종료|완료)된(?:캠페인|공고|체험단|이벤트|모집|신청)/,
    /이미(?:마감|종료|완료)(?:된|되었습니다|됐습니다)/,
    /(?:신청|지원|참여)(?:불가|불가능|할수없|할수없습니다)/,
    /(?:closed|expired|ended|applicationclosed)/i,
  ];
  if (explicitPatterns.some((pattern) => pattern.test(compact))) return "detail_closed_text";

  if (allowShortState) {
    const shortStatePatterns = [
      /(?:모집|신청|접수)(?:마감|종료)(?!일|일시|날짜|기간|까지)/,
      /(?:신청|지원|참여)(?:불가|불가능)/,
      /(?:종료|마감|완료)$/,
    ];
    if (shortStatePatterns.some((pattern) => pattern.test(compact))) return "detail_closed_state";
  }

  return "";
}

function detectClosedCampaignDetail($, bodyText = "") {
  const stateTexts = $("button, a, .status, .state, .badge, .d_day, .dday, [class*='status'], [class*='State'], [class*='badge'], [class*='Badge'], [class*='dday'], [class*='Dday']")
    .map((_, element) => cleanText($(element).text()))
    .get()
    .filter((text) => text && text.length <= 80);

  for (const text of stateTexts) {
    const reason = getClosedReasonFromText(text, { allowShortState: true });
    if (reason) return reason;
  }

  return getClosedReasonFromText(bodyText);
}

function closeCampaignFromDetail(campaign, reason, dDay = -1) {
  const parsedDDay = Number(dDay);
  campaign.status = "closed";
  campaign.closedReason = reason;
  campaign.dDay = Number.isFinite(parsedDDay) && parsedDDay < 0 ? parsedDDay : -1;
}

function applyCampaignDetailState(campaign, html, $ = null, now = new Date(), {
  applyDeadline = true,
  closePastDeadline = true,
  detectClosedState = true,
} = {}) {
  const doc = $ || cheerio.load(html || "");
  const bodyText = cleanText(doc("body").text());
  const deadlineInfo = extractDetailDeadlineInfo(doc, bodyText, now);

  if (deadlineInfo.sourceStartedAt && !campaign.sourceStartedAt) {
    campaign.sourceStartedAt = deadlineInfo.sourceStartedAt;
  }
  if (deadlineInfo.sourceEndedAt) {
    campaign.sourceEndedAt = deadlineInfo.sourceEndedAt;
  }
  if (applyDeadline && Number.isFinite(deadlineInfo.dDay)) {
    campaign.dDay = deadlineInfo.dDay;
    if (closePastDeadline && deadlineInfo.dDay < 0) {
      closeCampaignFromDetail(campaign, "detail_deadline_past", deadlineInfo.dDay);
    }
  }

  const closedReason = detectClosedState ? detectClosedCampaignDetail(doc, bodyText) : "";
  if (closedReason) {
    closeCampaignFromDetail(campaign, closedReason);
  }

  return { bodyText, deadlineInfo, closedReason };
}

const GENERIC_CATEGORY_LABELS = new Set([
  "",
  "기타",
  "지역_기타",
  "방문",
  "방문형",
  "배송",
  "배송형",
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
const CAMPAIGN_TYPE_ALIASES = new Map([
  ["visit", "visit"],
  ["방문", "visit"],
  ["방문형", "visit"],
  ["delivery", "delivery"],
  ["shipping", "delivery"],
  ["배송", "delivery"],
  ["배송형", "delivery"],
  ["배달", "delivery"],
  ["포장", "delivery"],
  ["reporter", "reporter"],
  ["press", "reporter"],
  ["기자단", "reporter"],
  ["구매평", "reporter"],
  ["purchase", "purchase"],
  ["구매", "purchase"],
  ["구매형", "purchase"],
  ["instagram", "instagram"],
  ["insta", "instagram"],
  ["인스타", "instagram"],
  ["인스타그램", "instagram"],
  ["reels", "reels"],
  ["reel", "reels"],
  ["릴스", "reels"],
  ["clip", "clip"],
  ["clips", "clip"],
  ["클립", "clip"],
  ["쇼츠", "clip"],
]);

function normalizeCampaignTypeForLaunch(value = LAUNCH_CAMPAIGN_TYPE) {
  const normalized = cleanText(value).toLowerCase();
  return CAMPAIGN_TYPE_ALIASES.get(normalized) || LAUNCH_CAMPAIGN_TYPE;
}

function guessCategory(title = "") {
  const normalizedTitle = String(title).toLowerCase();
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
    if (keywords.some((keyword) => normalizedTitle.includes(keyword))) {
      return category;
    }
  }

  return "기타";
}

function getGenericCategoryFallback(text = "", platformId = "") {
  if (/(제품|상품)/i.test(String(text))) return "생활용품";
  return PLATFORM_CATEGORY_DEFAULTS[platformId] || "";
}

function normalizeCampaignCategory(category = "", fallbackText = "", platformId = "") {
  const raw = cleanText(category);
  const searchText = `${raw} ${fallbackText}`;
  const aliases = {
    뷰티샵: "뷰티",
    뷰티체험: "뷰티",
    병원: "서비스",
    생활서비스: "서비스",
    서비스체험: "서비스",
    문화: "체험",
    방문체험: "체험",
  };
  const canonicalCategories = new Set([
    "맛집",
    "카페",
    "뷰티",
    "숙박",
    "생활용품",
    "패션",
    "서비스",
    "체험",
    "기타",
  ]);

  if (aliases[raw]) return aliases[raw];
  if (canonicalCategories.has(raw) && !GENERIC_CATEGORY_LABELS.has(raw)) {
    const guessed = guessCategory(searchText);
    if (guessed === "서비스" && ["생활용품", "체험"].includes(raw)) return guessed;
    return raw;
  }

  const guessed = guessCategory(searchText);
  if (guessed !== "기타") return guessed;

  return getGenericCategoryFallback(searchText, platformId) || (canonicalCategories.has(raw) ? raw : "기타");
}

function getCampaignCategoryFallbackText(campaign = {}) {
  return [
    campaign.title,
    campaign.point,
    campaign.type,
    campaign.locationRaw,
    campaign.addressRaw,
    campaign.stationName,
    campaign.placeName,
  ].filter(Boolean).join(" ");
}

function buildCampaign(base) {
  const campaign = {
    applyCount: 0,
    selectedCount: 3,
    point: null,
    type: "visit",
    locationRaw: "",
    addressRaw: "",
    stationName: "",
    placeName: "",
    sourceStartedAt: null,
    sourcePostedAt: null,
    coordinateSource: "unresolved",
    crawledAt: new Date().toISOString(),
    ...base,
  };
  campaign.type = normalizeCampaignTypeForLaunch(campaign.type);
  campaign.category = normalizeCampaignCategory(
    campaign.category,
    getCampaignCategoryFallbackText(campaign),
    campaign.platformId,
  );
  return campaign;
}

function isClosedCampaign(campaign) {
  return String(campaign?.status || "").toLowerCase() === "closed" || Number(campaign?.dDay ?? 99) < 0;
}

function getVisibleCampaigns(successfulCrawls) {
  const campaigns = successfulCrawls
    .flatMap((item) => item.campaigns)
    .filter((campaign) => campaign.title && campaign.title.length > 3)
    .map((campaign) => sanitizeCampaignForSnapshot(campaign))
    .sort((left, right) => left.dDay - right.dDay);

  const seen = new Set();
  const deduped = campaigns.filter((campaign) => {
    if (seen.has(campaign.id)) return false;
    seen.add(campaign.id);
    return true;
  });

  return {
    deduped,
    visibleCampaigns: deduped.filter((campaign) => !isClosedCampaign(campaign)),
  };
}

function loadExistingSnapshotCampaigns() {
  if (!fs.existsSync(SERVICE_CAMPAIGNS_PATH)) {
    return [];
  }

  try {
    const payload = JSON.parse(fs.readFileSync(SERVICE_CAMPAIGNS_PATH, "utf-8"));
    return Array.isArray(payload?.campaigns) ? payload.campaigns : [];
  } catch {
    return [];
  }
}

function sanitizeCampaignForSnapshot(campaign) {
  const next = { ...campaign };
  next.type = normalizeCampaignTypeForLaunch(next.type);
  next.category = normalizeCampaignCategory(
    next.category,
    getCampaignCategoryFallbackText(next),
    next.platformId,
  );
  if (next.sourceEndedAt && String(next.status || "").toLowerCase() !== "closed") {
    const recalculatedDDay = daysUntilKstDate(next.sourceEndedAt);
    if (Number.isFinite(recalculatedDDay)) {
      next.dDay = recalculatedDDay;
      if (recalculatedDDay < 0) {
        closeCampaignFromDetail(next, "source_deadline_past", recalculatedDDay);
      }
    }
  }
  if (next.platformId === "popomon" && next.platformDdayOffsetApplied === "popomon_minus_one") {
    delete next.platformDdayOffsetApplied;
  }
  if (next.platformId === "comeplay" && next.platformDdayOffsetApplied === "comeplay_minus_one") {
    const parsedDDay = Number(next.dDay);
    if (Number.isFinite(parsedDDay) && !isUnknownDDay(parsedDDay)) {
      next.dDay = parsedDDay + 1;
      if (next.dDay >= 0 && String(next.status || "").toLowerCase() === "closed" && !next.closedReason) {
        next.status = "open";
      }
    }
    delete next.platformDdayOffsetApplied;
  }
  if (next.platformId === "gangnam" && next.closedReason === "detail_closed_state" && next.sourceEndedAt) {
    const restoredDDay = daysUntilKstDate(next.sourceEndedAt);
    if (Number.isFinite(restoredDDay) && restoredDDay >= 0) {
      next.dDay = restoredDDay;
      next.status = "open";
      next.closedReason = null;
      next.detailStateIgnored = "gangnam_future_deadline";
    }
  }
  if (isKnownBadCampaignAddress(next, getCampaignAddressText(next))) {
    next.locationRaw = "";
    next.addressRaw = "";
    next.stationName = "";
  }
  if (isKnownBadMapCoordinate(next.lat, next.lng)) {
    next.lat = null;
    next.lng = null;
    next.coordinateSource = "unresolved";
  }
  return next;
}

function getCampaignIdentity(campaign) {
  return `${campaign?.platformId || "unknown"}:${campaign?.id || ""}`;
}

function getDaysBetween(startIso, endIso) {
  const start = Date.parse(startIso || "");
  const end = Date.parse(endIso || "");
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return 0;
  return Math.floor((end - start) / 86400000);
}

function createPreviousCampaignIndex(previousCampaigns = []) {
  return new Map(
    (previousCampaigns || [])
      .filter((campaign) => campaign?.id)
      .map((campaign) => [getCampaignIdentity(campaign), campaign]),
  );
}

function isKnownBadCampaignAddress(campaign, addressText = "") {
  const address = cleanAddressText(addressText);
  if (!address) return false;

  if (campaign?.platformId === "reviewnote" && /(?:김환수|해운대구\s*센텀서로\s*30|센텀서로\s*30)/.test(address)) {
    return true;
  }

  return false;
}

function hasReliableCarryForwardCoordinates(campaign) {
  if (!hasUsableCoordinates(campaign)) return false;
  if (isKnownBadMapCoordinate(campaign.lat, campaign.lng)) return false;

  const quality = classifyCoordinateQuality(campaign);
  return quality === "exact" || quality === "geocoded";
}

function canReusePreviousCoordinatesForAddress(currentAddress, previousAddress) {
  const currentKey = normalizeAddressForGeocoding(currentAddress);
  const previousKey = normalizeAddressForGeocoding(previousAddress);

  if (!currentKey) return true;
  if (!previousKey) return false;
  return currentKey === previousKey;
}

function carryForwardPreviousLocationData(campaign, previousCampaign) {
  if (
    !previousCampaign ||
    campaign?.platformId !== previousCampaign.platformId ||
    String(campaign?.id || "") !== String(previousCampaign.id || "")
  ) {
    return campaign;
  }

  const next = { ...campaign };
  const currentAddress = getCampaignAddressText(next);
  const previousAddress = getCampaignAddressText(previousCampaign);
  const previousAddressIsBad = isKnownBadCampaignAddress(previousCampaign, previousAddress);

  if (!currentAddress && previousAddress && !previousAddressIsBad) {
    const previousRawAddress = previousCampaign.addressRaw || previousCampaign.locationRaw || previousAddress;
    next.addressRaw = next.addressRaw || previousRawAddress;
    next.locationRaw = next.locationRaw || previousCampaign.locationRaw || previousRawAddress;
    next.placeName = next.placeName || previousCampaign.placeName || "";
    next.stationName = next.stationName || previousCampaign.stationName || "";
  }

  const mergedAddress = getCampaignAddressText(next);
  if (
    !previousAddressIsBad &&
    !hasUsableCoordinates(next) &&
    hasReliableCarryForwardCoordinates(previousCampaign) &&
    canReusePreviousCoordinatesForAddress(mergedAddress, previousAddress)
  ) {
    next.lat = previousCampaign.lat;
    next.lng = previousCampaign.lng;
    next.coordinateSource = previousCampaign.coordinateSource || "previous_snapshot";
  }

  return next;
}

function carryForwardPreviousDinnerqueenPoint(campaign, previousCampaign) {
  if (
    !previousCampaign ||
    campaign?.platformId !== "dinner" ||
    previousCampaign.platformId !== "dinner" ||
    String(campaign?.id || "") !== String(previousCampaign.id || "") ||
    cleanText(campaign?.point)
  ) {
    return campaign;
  }

  const previousPoint = cleanText(previousCampaign.point);
  if (!previousPoint) return campaign;

  return {
    ...campaign,
    point: previousPoint,
  };
}

function applyFreshLifecycleToCampaigns(campaigns = [], previousCampaigns = [], crawlStartedAt = new Date().toISOString()) {
  const previousIndex = createPreviousCampaignIndex(previousCampaigns);
  return campaigns.map((campaign) => applyCampaignLifecycle(campaign, {
    previousCampaign: previousIndex.get(getCampaignIdentity(campaign)) || null,
    isFresh: true,
    now: crawlStartedAt,
  }));
}

function getLifecycleCampaignsFromCrawls(successfulCrawls, previousCampaigns = [], crawlStartedAt = new Date().toISOString(), {
  visibleOnly = false,
} = {}) {
  const { deduped, visibleCampaigns } = getVisibleCampaigns(successfulCrawls);
  const campaigns = visibleOnly ? visibleCampaigns : deduped;

  return applyFreshLifecycleToCampaigns(campaigns, previousCampaigns, crawlStartedAt);
}

function getPlatformCampaigns(campaigns = [], platformId = "") {
  return Array.isArray(campaigns)
    ? campaigns.filter((campaign) => campaign?.platformId === platformId)
    : [];
}

function hasUnreliableDeadline(campaign = {}) {
  return isUnknownDDay(campaign.dDay) && !campaign.sourceEndedAt;
}

function shouldSkipPlatformDropBaseline(platformId, previousCampaigns = []) {
  const platformCampaigns = getPlatformCampaigns(previousCampaigns, platformId);
  if (platformCampaigns.length < QUALITY_GATE_MIN_PLATFORM_BASELINE) return false;

  const unreliableCount = platformCampaigns.filter(hasUnreliableDeadline).length;
  return getPercent(unreliableCount, platformCampaigns.length) >= 70;
}

function applyCampaignLifecycle(campaign, {
  previousCampaign = null,
  isFresh = false,
  now = new Date().toISOString(),
} = {}) {
  const sanitizedBase = sanitizeCampaignForSnapshot(campaign);
  const withPreviousLocation = carryForwardPreviousLocationData(sanitizedBase, previousCampaign);
  const withPreviousDinnerqueenPoint = carryForwardPreviousDinnerqueenPoint(withPreviousLocation, previousCampaign);
  const sanitized = sanitizeCampaignForSnapshot(withPreviousDinnerqueenPoint);
  const firstSeenAt = sanitized.firstSeenAt || previousCampaign?.firstSeenAt || previousCampaign?.crawledAt || now;
  const lastSeenAt = isFresh
    ? now
    : sanitized.lastSeenAt || previousCampaign?.lastSeenAt || previousCampaign?.crawledAt || firstSeenAt;
  const staleDays = isFresh ? 0 : getDaysBetween(lastSeenAt, now);
  const isStale = !isFresh && staleDays >= CAMPAIGN_STALE_WARN_DAYS;
  const isExpiredStale = !isFresh && staleDays >= CAMPAIGN_STALE_HIDE_DAYS;
  const parsedDDay = Number(sanitized.dDay);
  const dDay = isClosedCampaign(sanitized)
    ? (Number.isFinite(parsedDDay) && parsedDDay < 0 ? parsedDDay : -1)
    : !isFresh && Number.isFinite(parsedDDay)
      ? parsedDDay - staleDays
      : sanitized.dDay;

  return {
    ...sanitized,
    dDay,
    status: dDay < 0 ? "closed" : sanitized.status || "open",
    firstSeenAt,
    lastSeenAt,
    lastRefreshedAt: isFresh ? now : sanitized.lastRefreshedAt || previousCampaign?.lastRefreshedAt || null,
    dataState: isFresh ? "fresh" : isStale ? "stale" : "preserved",
    isStale,
    staleDays,
    staleHiddenAt: isExpiredStale ? now : null,
  };
}

function getPreservedSnapshotCampaigns(previousCampaigns, successfulCrawls) {
  const replacedPlatformIds = new Set(successfulCrawls.map((crawl) => crawl.platformId));
  return Array.isArray(previousCampaigns)
    ? previousCampaigns.filter((campaign) => !replacedPlatformIds.has(campaign.platformId))
    : [];
}

function quarantineLowVisibleCountCrawls(successfulCrawls, failedCrawls, previousCampaigns = []) {
  const previousByPlatform = countCampaignsByPlatform(previousCampaigns);

  for (let index = successfulCrawls.length - 1; index >= 0; index -= 1) {
    const crawl = successfulCrawls[index];
    const platformId = crawl.platformId;
    const previousCount = previousByPlatform.get(platformId) || 0;
    if (previousCount < QUALITY_GATE_MIN_PLATFORM_BASELINE) continue;
    if (shouldSkipPlatformDropBaseline(platformId, previousCampaigns)) {
      console.log(
        `  - ${crawl.label || platformId} drop baseline skipped: previous deadline data was unreliable`,
      );
      continue;
    }

    const minimumAllowed = Math.floor(previousCount * (1 - QUALITY_GATE_MAX_PLATFORM_DROP_PCT / 100));
    const freshCount = getVisibleCampaigns([crawl]).visibleCampaigns.length;
    if (freshCount >= minimumAllowed) continue;

    successfulCrawls.splice(index, 1);
    failedCrawls.push({
      platformId,
      label: crawl.label,
      reason: `quarantined: visible campaign count ${freshCount} is below minimum ${minimumAllowed} from previous ${previousCount}`,
      durationMs: crawl.durationMs || 0,
      quarantined: true,
      previousCount,
      freshCount,
      minimumAllowed,
    });
    console.log(`  - ${crawl.label || platformId} quarantined: visible count ${freshCount}/${previousCount}, previous data will be preserved`);
  }
}

function shouldQuarantinePlatformQualityDrop({
  platformId,
  label,
  previousSummary,
  freshSummary,
}) {
  const checks = [
    {
      metric: "coordinates",
      previous: previousSummary.withCoordinates,
      fresh: freshSummary.withCoordinates,
      maxDropPct: QUALITY_GATE_MAX_PLATFORM_COORDINATE_DROP_PCT,
    },
    {
      metric: "addresses",
      previous: previousSummary.withAddress,
      fresh: freshSummary.withAddress,
      maxDropPct: QUALITY_GATE_MAX_PLATFORM_ADDRESS_DROP_PCT,
    },
  ];

  for (const check of checks) {
    if (check.previous < QUALITY_GATE_MIN_PLATFORM_BASELINE) continue;
    const minimumAllowed = Math.floor(check.previous * (1 - check.maxDropPct / 100));
    if (check.fresh >= minimumAllowed) continue;

    return {
      metric: check.metric,
      reason: `quarantined: ${check.metric} ${check.fresh} is below minimum ${minimumAllowed} from previous ${check.previous}`,
      platformId,
      label,
      previousCount: previousSummary.campaigns,
      freshCount: freshSummary.campaigns,
      previousMetricCount: check.previous,
      freshMetricCount: check.fresh,
      minimumAllowed,
    };
  }

  return null;
}

function quarantineLowDataQualityCrawls(
  successfulCrawls,
  failedCrawls,
  previousCampaigns = [],
  crawlStartedAt = new Date().toISOString(),
) {
  for (let index = successfulCrawls.length - 1; index >= 0; index -= 1) {
    const crawl = successfulCrawls[index];
    const platformId = crawl.platformId;
    const previousPlatformCampaigns = getPlatformCampaigns(previousCampaigns, platformId)
      .filter((campaign) => !isClosedCampaign(campaign));
    if (previousPlatformCampaigns.length < QUALITY_GATE_MIN_PLATFORM_BASELINE) continue;

    const freshCampaigns = getLifecycleCampaignsFromCrawls(
      [crawl],
      previousCampaigns,
      crawlStartedAt,
      { visibleOnly: true },
    );
    const previousSummary = summarizeCampaignSet(previousPlatformCampaigns);
    const freshSummary = summarizeCampaignSet(freshCampaigns);
    const quarantine = shouldQuarantinePlatformQualityDrop({
      platformId,
      label: crawl.label,
      previousSummary,
      freshSummary,
    });
    if (!quarantine) continue;

    successfulCrawls.splice(index, 1);
    failedCrawls.push({
      platformId,
      label: crawl.label,
      reason: quarantine.reason,
      durationMs: crawl.durationMs || 0,
      quarantined: true,
      previousCount: quarantine.previousCount,
      freshCount: quarantine.freshCount,
      metric: quarantine.metric,
      previousMetricCount: quarantine.previousMetricCount,
      freshMetricCount: quarantine.freshMetricCount,
      minimumAllowed: quarantine.minimumAllowed,
    });
    console.log(
      `  - ${crawl.label || platformId} quarantined: ${quarantine.metric} `
      + `${quarantine.freshMetricCount}/${quarantine.previousMetricCount}, previous data will be preserved`,
    );
  }
}

function normalizeDuplicateText(value) {
  return cleanText(value)
    .normalize("NFKC")
    .toLowerCase()
    .replace(/^\[[^\]]+\]\s*/g, "")
    .replace(/\[[^\]]+\]/g, " ")
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function normalizeDuplicateTitle(title) {
  return normalizeDuplicateText(title).slice(0, 80);
}

function normalizeDuplicateAddress(campaign) {
  return normalizeDuplicateText(getCampaignAddressText(campaign)).slice(0, 120);
}

function getCoordinateDuplicateKey(campaign) {
  if (!hasUsableCoordinates(campaign)) return "";
  return `${Number(campaign.lat).toFixed(4)},${Number(campaign.lng).toFixed(4)}`;
}

function makeCampaignDuplicateKey(campaign) {
  const platformKey = String(campaign.platformId || "unknown");
  const titleKey = normalizeDuplicateTitle(campaign.title);
  if (titleKey.length < 2) return null;

  const addressKey = normalizeDuplicateAddress(campaign);
  if (addressKey.length >= 8) return `${platformKey}:addr:${titleKey}:${addressKey}`;

  const coordKey = getCoordinateDuplicateKey(campaign);
  const rewardKey = normalizeDuplicateText(campaign.point || "").slice(0, 40);
  if (coordKey && rewardKey.length >= 2) return `${platformKey}:coord:${titleKey}:${coordKey}:${rewardKey}`;
  if (coordKey) return `${platformKey}:coord:${titleKey}:${coordKey}`;

  return null;
}

function getDuplicateRepresentativeScore(campaign) {
  const quality = classifyCoordinateQuality(campaign);
  const qualityScore = {
    exact: 80,
    geocoded: 70,
    estimated: 45,
    derived: 20,
    unknown: 10,
    missing: 0,
  }[quality] || 0;

  return [
    campaign.dataState === "fresh" ? 100 : campaign.dataState === "preserved" ? 40 : 0,
    qualityScore,
    getCampaignAddressText(campaign) ? 30 : 0,
    Number.isFinite(Number(campaign.applyCount)) ? Math.min(Number(campaign.applyCount), 30) : 0,
    Number.isFinite(Number(campaign.selectedCount)) ? Math.min(Number(campaign.selectedCount), 20) : 0,
    Number.isFinite(Number(campaign.dDay)) ? Math.max(0, 20 - Number(campaign.dDay)) : 0,
  ].reduce((sum, value) => sum + value, 0);
}

function summarizeDuplicateAlternate(campaign) {
  return {
    id: campaign.id,
    platformId: campaign.platformId,
    title: campaign.title,
    url: campaign.url,
    dDay: campaign.dDay,
    coordinateSource: campaign.coordinateSource || null,
    dataState: campaign.dataState || null,
  };
}

function deduplicateCampaignsForPublish(campaigns) {
  const groupsByKey = new Map();
  const passthrough = [];

  for (const campaign of campaigns) {
    const duplicateKey = makeCampaignDuplicateKey(campaign);
    if (!duplicateKey) {
      passthrough.push(campaign);
      continue;
    }
    if (!groupsByKey.has(duplicateKey)) groupsByKey.set(duplicateKey, []);
    groupsByKey.get(duplicateKey).push(campaign);
  }

  const visibleCampaigns = [...passthrough];
  const duplicateGroups = [];
  const hiddenDuplicateCampaigns = [];

  for (const [duplicateKey, group] of groupsByKey.entries()) {
    if (group.length === 1) {
      visibleCampaigns.push(group[0]);
      continue;
    }

    const sorted = [...group].sort((left, right) => {
      const scoreDiff = getDuplicateRepresentativeScore(right) - getDuplicateRepresentativeScore(left);
      if (scoreDiff !== 0) return scoreDiff;
      const dDayDiff = Number(left.dDay ?? 99) - Number(right.dDay ?? 99);
      if (dDayDiff !== 0) return dDayDiff;
      return String(left.platformId || "").localeCompare(String(right.platformId || ""));
    });
    const representative = sorted[0];
    const alternates = sorted.slice(1);
    const duplicateGroupId = `dup_${duplicateKey.slice(0, 96)}`;

    visibleCampaigns.push({
      ...representative,
      duplicateGroupId,
      duplicateCount: group.length,
      duplicateAlternates: alternates.map(summarizeDuplicateAlternate),
    });

    for (const alternate of alternates) {
      hiddenDuplicateCampaigns.push({
        ...alternate,
        duplicateGroupId,
        duplicateOf: representative.id,
        visibilityStatus: "duplicate_hidden",
      });
    }

    duplicateGroups.push({
      duplicateGroupId,
      duplicateKey,
      representative: summarizeDuplicateAlternate(representative),
      alternates: alternates.map(summarizeDuplicateAlternate),
      count: group.length,
    });
  }

  visibleCampaigns.sort((left, right) => {
    const dDayDiff = Number(left.dDay ?? 99) - Number(right.dDay ?? 99);
    if (dDayDiff !== 0) return dDayDiff;
    return String(left.title || "").localeCompare(String(right.title || ""));
  });

  return {
    campaigns: visibleCampaigns,
    duplicateGroups,
    hiddenDuplicateCampaigns,
  };
}

function buildCampaignSnapshotResult(successfulCrawls, preservedCampaigns = [], {
  previousCampaigns = [],
  crawlStartedAt = new Date().toISOString(),
} = {}) {
  const preserved = Array.isArray(preservedCampaigns)
    ? preservedCampaigns.filter((campaign) => campaign?.id && campaign?.title)
    : [];
  const { visibleCampaigns } = getVisibleCampaigns([
    ...successfulCrawls,
    {
      platformId: "__preserved__",
      label: "__preserved__",
      campaigns: preserved,
      durationMs: 0,
    },
  ]);
  const freshIds = new Set(
    successfulCrawls.flatMap((crawl) => crawl.campaigns.map((campaign) => getCampaignIdentity(campaign))),
  );
  const previousIndex = createPreviousCampaignIndex(previousCampaigns);
  const lifecycleCampaigns = visibleCampaigns.map((campaign) => applyCampaignLifecycle(campaign, {
    previousCampaign: previousIndex.get(getCampaignIdentity(campaign)) || null,
    isFresh: freshIds.has(getCampaignIdentity(campaign)),
    now: crawlStartedAt,
  }));
  const hiddenStaleCampaigns = lifecycleCampaigns.filter((campaign) => campaign.staleDays >= CAMPAIGN_STALE_HIDE_DAYS);
  const hiddenExpiredCampaigns = lifecycleCampaigns.filter((campaign) => isClosedCampaign(campaign));
  const publishableLifecycleCampaigns = lifecycleCampaigns.filter((campaign) => (
    campaign.staleDays < CAMPAIGN_STALE_HIDE_DAYS &&
    !isClosedCampaign(campaign)
  ));
  neutralizeSuspiciousCoordinateClusters(publishableLifecycleCampaigns);
  const deduped = deduplicateCampaignsForPublish(publishableLifecycleCampaigns);

  return {
    campaigns: deduped.campaigns,
    beforeDuplicateCount: publishableLifecycleCampaigns.length,
    hiddenStaleCampaigns,
    hiddenExpiredCampaigns,
    duplicateGroups: deduped.duplicateGroups,
    hiddenDuplicateCampaigns: deduped.hiddenDuplicateCampaigns,
    totals: {
      fresh: lifecycleCampaigns.filter((campaign) => campaign.dataState === "fresh").length,
      preserved: lifecycleCampaigns.filter((campaign) => campaign.dataState === "preserved").length,
      stale: lifecycleCampaigns.filter((campaign) => campaign.dataState === "stale").length,
      hiddenStale: hiddenStaleCampaigns.length,
      hiddenExpired: hiddenExpiredCampaigns.length,
      duplicateGroups: deduped.duplicateGroups.length,
      hiddenDuplicates: deduped.hiddenDuplicateCampaigns.length,
      beforeDuplicateCount: publishableLifecycleCampaigns.length,
      afterDuplicateCount: deduped.campaigns.length,
    },
  };
}

function buildCampaignSnapshot(successfulCrawls, preservedCampaigns = [], options = {}) {
  return buildCampaignSnapshotResult(successfulCrawls, preservedCampaigns, options).campaigns;
}

function writeJsonFileAtomic(filePath, payload) {
  const outDir = path.dirname(filePath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  const tmpPath = `${filePath}.tmp`;
  try {
    fs.writeFileSync(tmpPath, JSON.stringify(payload, null, 2), "utf-8");
    fs.renameSync(tmpPath, filePath);
  } catch (error) {
    try {
      if (fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath);
    } catch { }
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf-8");
    console.log(`  - artifact write fallback (${path.basename(filePath)}): ${error.message}`);
  }
}

function writeJsonArtifact(fileName, payload) {
  writeJsonFileAtomic(path.join(PROJECT_ROOT, "public", fileName), payload);
}

function writeCrawlerArtifact(fileName, payload) {
  writeJsonFileAtomic(path.join(CRAWLER_ARTIFACT_DIR, fileName), payload);
}

function countCampaignTypes(campaigns = []) {
  const counts = {};
  for (const campaign of campaigns) {
    const type = campaign?.type || "unknown";
    counts[type] = (counts[type] || 0) + 1;
  }
  return counts;
}

function isForbiddenRequestError(error) {
  return error?.response?.status === 403;
}

function readJsonFileSafe(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

function getReviewnoteForbiddenCooldown(nowMs = Date.now()) {
  if (REVIEWNOTE_IGNORE_COOLDOWN || REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS <= 0) return null;

  const cooldown = readJsonFileSafe(REVIEWNOTE_FORBIDDEN_COOLDOWN_PATH);
  if (!cooldown?.expiresAt) return null;

  const expiresAtMs = Date.parse(cooldown.expiresAt);
  if (!Number.isFinite(expiresAtMs) || expiresAtMs <= nowMs) return null;

  return cooldown;
}

function recordReviewnoteForbiddenCooldown(error) {
  if (REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS <= 0) return null;

  const blockedAtMs = Date.now();
  const cooldown = {
    platformId: "reviewnote",
    reason: formatRequestError(error) || "HTTP 403 Forbidden",
    blockedAt: new Date(blockedAtMs).toISOString(),
    expiresAt: new Date(blockedAtMs + REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS * 60 * 60 * 1000).toISOString(),
    cooldownHours: REVIEWNOTE_FORBIDDEN_COOLDOWN_HOURS,
  };
  writeJsonFileAtomic(REVIEWNOTE_FORBIDDEN_COOLDOWN_PATH, cooldown);
  return cooldown;
}

function clearReviewnoteForbiddenCooldown() {
  try {
    if (fs.existsSync(REVIEWNOTE_FORBIDDEN_COOLDOWN_PATH)) {
      fs.unlinkSync(REVIEWNOTE_FORBIDDEN_COOLDOWN_PATH);
    }
  } catch (error) {
    console.log(`  - reviewnote cooldown clear failed: ${error.message}`);
  }
}

function publishCampaignSnapshot(campaigns, qualityGate = null) {
  const visibleCampaigns = Array.isArray(campaigns) ? campaigns : [];
  writeJsonFileAtomic(SERVICE_CAMPAIGNS_PATH, {
    campaigns: visibleCampaigns,
    updatedAt: new Date().toISOString(),
    qualityGate: qualityGate
      ? {
        status: qualityGate.status,
        mode: qualityGate.mode,
        checkedAt: qualityGate.checkedAt,
      }
      : null,
  });
  writeCrawlerArtifact("published-campaigns.json", {
    generatedAt: new Date().toISOString(),
    campaigns: visibleCampaigns,
    qualityGate,
  });
  return visibleCampaigns;
}

function hasUsableCoordinates(campaign) {
  const lat = Number(campaign?.lat);
  const lng = Number(campaign?.lng);
  return isKoreaLatLng(lat, lng) && !isKnownBadMapCoordinate(lat, lng);
}

function classifyCoordinateQuality(campaign) {
  if (!hasUsableCoordinates(campaign)) return "missing";
  const source = String(campaign.coordinateSource || "").toLowerCase();

  if (/^(html|naver|kakao_tile|.*_api)/.test(source)) return "exact";
  if (source === "kakao_address") return "geocoded";
  if (source.startsWith("kakao_keyword")) return "estimated";
  if (source === "derived") return "derived";
  return "unknown";
}

function getCampaignAddressText(campaign) {
  return cleanAddressText(
    campaign?.addressRaw ||
    campaign?.locationRaw ||
    campaign?.placeName ||
    campaign?.stationName ||
    "",
  );
}

function makeIssueSample(campaign) {
  return {
    id: campaign.id,
    platformId: campaign.platformId,
    title: campaign.title,
    url: campaign.url,
    address: getCampaignAddressText(campaign) || null,
    coordinateSource: campaign.coordinateSource || null,
    dataState: campaign.dataState || null,
    staleDays: Number.isFinite(Number(campaign.staleDays)) ? Number(campaign.staleDays) : null,
    duplicateGroupId: campaign.duplicateGroupId || null,
    duplicateOf: campaign.duplicateOf || null,
  };
}

function getPercent(part, total) {
  return total > 0 ? Number(((part / total) * 100).toFixed(1)) : 0;
}

function getCoordinateClusterKey(campaign) {
  if (!hasUsableCoordinates(campaign)) return "";
  return `${Number(campaign.lat).toFixed(6)},${Number(campaign.lng).toFixed(6)}|${campaign.coordinateSource || "unknown"}`;
}

function getAddressClusterKey(campaign) {
  return normalizeAddressForGeocoding(getCampaignAddressText(campaign));
}

function findSuspiciousCoordinateClusters(campaigns = []) {
  const byPlatform = new Map();

  for (const campaign of campaigns) {
    if (!campaign?.platformId || isClosedCampaign(campaign)) continue;
    if (!byPlatform.has(campaign.platformId)) {
      byPlatform.set(campaign.platformId, {
        platformId: campaign.platformId,
        total: 0,
        coordinateClusters: new Map(),
        addressClusters: new Map(),
      });
    }

    const platform = byPlatform.get(campaign.platformId);
    platform.total += 1;

    const coordinateKey = getCoordinateClusterKey(campaign);
    if (coordinateKey) {
      if (!platform.coordinateClusters.has(coordinateKey)) {
        platform.coordinateClusters.set(coordinateKey, { key: coordinateKey, count: 0, samples: [] });
      }
      const cluster = platform.coordinateClusters.get(coordinateKey);
      cluster.count += 1;
      if (cluster.samples.length < 5) cluster.samples.push(makeIssueSample(campaign));
    }

    const addressKey = getAddressClusterKey(campaign);
    if (addressKey) {
      platform.addressClusters.set(addressKey, (platform.addressClusters.get(addressKey) || 0) + 1);
    }
  }

  const suspicious = [];
  for (const platform of byPlatform.values()) {
    if (platform.total < QUALITY_GATE_MIN_COORDINATE_SAMPLE) continue;
    const topCoordinate = [...platform.coordinateClusters.values()]
      .sort((left, right) => right.count - left.count)[0];
    if (!topCoordinate) continue;

    const clusterPct = getPercent(topCoordinate.count, platform.total);
    if (
      topCoordinate.count < QUALITY_GATE_MIN_COORDINATE_CLUSTER ||
      clusterPct < QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT
    ) {
      continue;
    }

    const [latLng, source = "unknown"] = topCoordinate.key.split("|");
    const topAddress = [...platform.addressClusters.entries()]
      .sort((left, right) => right[1] - left[1])[0] || ["", 0];
    suspicious.push({
      platformId: platform.platformId,
      total: platform.total,
      key: topCoordinate.key,
      latLng,
      source,
      count: topCoordinate.count,
      pct: clusterPct,
      topAddress: topAddress[0],
      topAddressCount: topAddress[1],
      topAddressPct: getPercent(topAddress[1], platform.total),
      samples: topCoordinate.samples,
    });
  }

  return suspicious;
}

function neutralizeSuspiciousCoordinateClusters(campaigns = []) {
  const suspicious = findSuspiciousCoordinateClusters(campaigns);
  if (!suspicious.length) return suspicious;

  const byPlatformAndKey = new Map(suspicious.map((cluster) => [`${cluster.platformId}:${cluster.key}`, cluster]));

  for (const campaign of campaigns) {
    const cluster = byPlatformAndKey.get(`${campaign.platformId}:${getCoordinateClusterKey(campaign)}`);
    if (!cluster) continue;

    const addressKey = getAddressClusterKey(campaign);
    campaign.lat = null;
    campaign.lng = null;
    campaign.coordinateSource = "unresolved";
    campaign.coordinateInvalidatedReason = "suspicious_platform_coordinate_cluster";

    if (
      cluster.topAddress &&
      addressKey === cluster.topAddress &&
      cluster.topAddressCount >= QUALITY_GATE_MIN_COORDINATE_CLUSTER &&
      cluster.topAddressPct >= QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT
    ) {
      campaign.locationRaw = "";
      campaign.addressRaw = "";
      campaign.addressInvalidatedReason = "suspicious_platform_address_cluster";
    }
  }

  return suspicious;
}

function buildDataQualityReport(campaigns, successfulCrawls, failedCrawls, {
  crawlStartedAt,
  generatedAt = new Date().toISOString(),
  qualityGate = null,
  pipelineStats = null,
} = {}) {
  const byPlatform = new Map();
  const coordinateSources = {};
  const coordinateQuality = {};
  const issues = {
    missingCoordinates: [],
    badCoordinates: [],
    missingAddress: [],
    lowConfidenceCoordinates: [],
    staleCampaigns: [],
    duplicateCampaigns: [],
  };

  for (const campaign of campaigns) {
    const platformId = campaign.platformId || "unknown";
    if (!byPlatform.has(platformId)) {
      byPlatform.set(platformId, {
        platformId,
        total: 0,
        withCoordinates: 0,
        missingCoordinates: 0,
        exactCoordinates: 0,
        geocodedCoordinates: 0,
        estimatedCoordinates: 0,
        lowConfidenceCoordinates: 0,
        withAddress: 0,
        missingAddress: 0,
        coordinateSources: {},
      });
    }

    const platform = byPlatform.get(platformId);
    const source = campaign.coordinateSource || "unknown";
    const quality = classifyCoordinateQuality(campaign);
    const hasCoords = hasUsableCoordinates(campaign);
    const hasAddress = Boolean(getCampaignAddressText(campaign));

    platform.total += 1;
    platform.coordinateSources[source] = (platform.coordinateSources[source] || 0) + 1;
    coordinateSources[source] = (coordinateSources[source] || 0) + 1;
    coordinateQuality[quality] = (coordinateQuality[quality] || 0) + 1;

    if (hasCoords) platform.withCoordinates += 1;
    else platform.missingCoordinates += 1;

    if (quality === "exact") platform.exactCoordinates += 1;
    if (quality === "geocoded") platform.geocodedCoordinates += 1;
    if (quality === "estimated") platform.estimatedCoordinates += 1;
    if (["estimated", "derived", "unknown"].includes(quality)) platform.lowConfidenceCoordinates += 1;

    if (hasAddress) platform.withAddress += 1;
    else platform.missingAddress += 1;

    if (!hasCoords && issues.missingCoordinates.length < 80) {
      issues.missingCoordinates.push(makeIssueSample(campaign));
    }
    if (isKnownBadMapCoordinate(campaign.lat, campaign.lng) && issues.badCoordinates.length < 80) {
      issues.badCoordinates.push(makeIssueSample(campaign));
    }
    if (!hasAddress && issues.missingAddress.length < 80) {
      issues.missingAddress.push(makeIssueSample(campaign));
    }
    if (["estimated", "derived", "unknown"].includes(quality) && issues.lowConfidenceCoordinates.length < 80) {
      issues.lowConfidenceCoordinates.push(makeIssueSample(campaign));
    }
    if (campaign.isStale && issues.staleCampaigns.length < 80) {
      issues.staleCampaigns.push(makeIssueSample(campaign));
    }
    if (campaign.duplicateCount > 1 && issues.duplicateCampaigns.length < 80) {
      issues.duplicateCampaigns.push({
        ...makeIssueSample(campaign),
        duplicateCount: campaign.duplicateCount,
        duplicateAlternates: campaign.duplicateAlternates || [],
      });
    }
  }

  const platformQuality = [...byPlatform.values()]
    .map((platform) => ({
      ...platform,
      coordinateCompletenessPct: getPercent(platform.withCoordinates, platform.total),
      exactCoordinatePct: getPercent(platform.exactCoordinates, platform.total),
      addressCompletenessPct: getPercent(platform.withAddress, platform.total),
    }))
    .sort((left, right) => left.platformId.localeCompare(right.platformId));

  const totals = {
    campaigns: campaigns.length,
    withCoordinates: campaigns.filter(hasUsableCoordinates).length,
    missingCoordinates: campaigns.filter((campaign) => !hasUsableCoordinates(campaign)).length,
    withAddress: campaigns.filter((campaign) => Boolean(getCampaignAddressText(campaign))).length,
    missingAddress: campaigns.filter((campaign) => !getCampaignAddressText(campaign)).length,
    staleCampaigns: campaigns.filter((campaign) => campaign.isStale).length,
    duplicateGroups: pipelineStats?.totals?.duplicateGroups || 0,
    hiddenDuplicates: pipelineStats?.totals?.hiddenDuplicates || 0,
    hiddenStaleCampaigns: pipelineStats?.totals?.hiddenStale || 0,
    hiddenExpiredCampaigns: pipelineStats?.totals?.hiddenExpired || 0,
    successfulPlatforms: successfulCrawls.length,
    failedPlatforms: failedCrawls.length,
  };

  const warnings = [];
  for (const platform of platformQuality) {
    if (platform.total >= 20 && platform.coordinateCompletenessPct < QUALITY_GATE_WARN_COORDINATE_PCT) {
      warnings.push({
        severity: "high",
        platformId: platform.platformId,
        message: `coordinate completeness below ${QUALITY_GATE_WARN_COORDINATE_PCT}% (${platform.coordinateCompletenessPct}%)`,
      });
    }
    if (platform.total >= 20 && platform.addressCompletenessPct < QUALITY_GATE_WARN_ADDRESS_PCT) {
      warnings.push({
        severity: "medium",
        platformId: platform.platformId,
        message: `address completeness below ${QUALITY_GATE_WARN_ADDRESS_PCT}% (${platform.addressCompletenessPct}%)`,
      });
    }
  }
  for (const cluster of findSuspiciousCoordinateClusters(campaigns)) {
    warnings.push({
      severity: "critical",
      platformId: cluster.platformId,
      message: `suspicious coordinate cluster: ${cluster.count}/${cluster.total} campaigns at ${cluster.latLng}`,
    });
  }
  for (const failed of failedCrawls) {
    warnings.push({
      severity: "critical",
      platformId: failed.platformId || failed.label,
      message: `crawler failed: ${failed.reason}`,
    });
  }
  if ((pipelineStats?.totals?.hiddenDuplicates || 0) > 0) {
    warnings.push({
      severity: "medium",
      platformId: "pipeline",
      message: `hidden duplicate campaigns: ${pipelineStats.totals.hiddenDuplicates}`,
    });
  }
  if ((pipelineStats?.totals?.hiddenStale || 0) > 0) {
    warnings.push({
      severity: "high",
      platformId: "pipeline",
      message: `hidden stale campaigns: ${pipelineStats.totals.hiddenStale}`,
    });
  }
  if ((pipelineStats?.totals?.hiddenExpired || 0) > 0) {
    warnings.push({
      severity: "medium",
      platformId: "pipeline",
      message: `hidden expired preserved campaigns: ${pipelineStats.totals.hiddenExpired}`,
    });
  }

  return {
    generatedAt,
    crawlStartedAt,
    totals: {
      ...totals,
      coordinateCompletenessPct: getPercent(totals.withCoordinates, totals.campaigns),
      addressCompletenessPct: getPercent(totals.withAddress, totals.campaigns),
    },
    coordinateQuality,
    coordinateSources,
    platforms: platformQuality,
    warnings,
    issues,
    qualityGate,
    pipeline: pipelineStats,
  };
}

function summarizeCampaignSet(campaigns) {
  const total = Array.isArray(campaigns) ? campaigns.length : 0;
  const withCoordinates = Array.isArray(campaigns) ? campaigns.filter(hasUsableCoordinates).length : 0;
  const withAddress = Array.isArray(campaigns)
    ? campaigns.filter((campaign) => Boolean(getCampaignAddressText(campaign))).length
    : 0;

  return {
    campaigns: total,
    withCoordinates,
    missingCoordinates: total - withCoordinates,
    coordinateCompletenessPct: getPercent(withCoordinates, total),
    withAddress,
    missingAddress: total - withAddress,
    addressCompletenessPct: getPercent(withAddress, total),
  };
}

function countCampaignsByPlatform(campaigns) {
  const counts = new Map();
  for (const campaign of campaigns || []) {
    const platformId = campaign?.platformId || "unknown";
    counts.set(platformId, (counts.get(platformId) || 0) + 1);
  }
  return counts;
}

function makeQualityGateRule(id, passed, severity, message, details = {}) {
  return {
    id,
    passed: Boolean(passed),
    severity,
    message,
    details,
  };
}

function evaluateQualityGate({
  candidateCampaigns = [],
  freshCampaigns = [],
  previousCampaigns = [],
  successfulCrawls = [],
  failedCrawls = [],
  activeCrawlers = [],
  crawlOnly = [],
} = {}) {
  const checkedAt = new Date().toISOString();
  const candidateTotals = summarizeCampaignSet(candidateCampaigns);
  const freshTotals = summarizeCampaignSet(freshCampaigns);
  const previousTotals = summarizeCampaignSet(previousCampaigns);
  const previousByPlatform = countCampaignsByPlatform(previousCampaigns);
  const freshByPlatform = countCampaignsByPlatform(freshCampaigns);
  const attemptedPlatformCount = Math.max(
    activeCrawlers.length,
    successfulCrawls.length + failedCrawls.length,
  );
  const successfulPlatformPct = getPercent(successfulCrawls.length, attemptedPlatformCount);
  const rules = [];

  rules.push(makeQualityGateRule(
    "successful_crawler_exists",
    successfulCrawls.length > 0,
    "critical",
    "at least one crawler must complete successfully",
    { successfulPlatforms: successfulCrawls.length, activePlatforms: activeCrawlers.length },
  ));

  rules.push(makeQualityGateRule(
    "candidate_not_empty",
    candidateTotals.campaigns > 0,
    "critical",
    "publish candidate must contain campaigns",
    { candidateCampaigns: candidateTotals.campaigns },
  ));

  rules.push(makeQualityGateRule(
    "successful_platform_rate",
    successfulPlatformPct >= QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT,
    "critical",
    `successful crawler rate must be at least ${QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT}% to publish`,
    {
      successfulPlatforms: successfulCrawls.length,
      failedPlatforms: failedCrawls.length,
      activePlatforms: activeCrawlers.length,
      attemptedPlatforms: attemptedPlatformCount,
      actualPct: successfulPlatformPct,
      minimumPct: QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT,
    },
  ));

  if (freshTotals.campaigns >= QUALITY_GATE_MIN_COORDINATE_SAMPLE) {
    rules.push(makeQualityGateRule(
      "fresh_coordinate_completeness",
      true,
      "low",
      "fresh coordinate completeness is tracked as map coverage only",
      {
        actualPct: freshTotals.coordinateCompletenessPct,
        targetPct: QUALITY_GATE_MIN_COORDINATE_PCT,
        freshCampaigns: freshTotals.campaigns,
      },
    ));

    rules.push(makeQualityGateRule(
      "fresh_coordinate_completeness_warning",
      true,
      "low",
      "fresh coordinate completeness is below the old map coverage target",
      {
        actualPct: freshTotals.coordinateCompletenessPct,
        targetPct: QUALITY_GATE_WARN_COORDINATE_PCT,
        freshCampaigns: freshTotals.campaigns,
      },
    ));
  } else if (freshTotals.campaigns > 0) {
    rules.push(makeQualityGateRule(
      "fresh_coordinate_sample_size",
      true,
      "low",
      "fresh coordinate sample is too small for a hard completeness gate",
      {
        freshCampaigns: freshTotals.campaigns,
        minimumSample: QUALITY_GATE_MIN_COORDINATE_SAMPLE,
        actualPct: freshTotals.coordinateCompletenessPct,
      },
    ));
  }

  if (freshTotals.campaigns >= QUALITY_GATE_MIN_COORDINATE_SAMPLE) {
    rules.push(makeQualityGateRule(
      "fresh_address_completeness_warning",
      true,
      freshTotals.addressCompletenessPct < QUALITY_GATE_WARN_ADDRESS_PCT ? "medium" : "low",
      `fresh address completeness target is ${QUALITY_GATE_WARN_ADDRESS_PCT}%`,
      {
        actualPct: freshTotals.addressCompletenessPct,
        targetPct: QUALITY_GATE_WARN_ADDRESS_PCT,
        freshCampaigns: freshTotals.campaigns,
      },
    ));
  }

  for (const crawl of successfulCrawls) {
    const platformId = crawl.platformId;
    const previousCount = previousByPlatform.get(platformId) || 0;
    const freshCount = freshByPlatform.get(platformId) || 0;
    if (previousCount < QUALITY_GATE_MIN_PLATFORM_BASELINE) continue;
    if (shouldSkipPlatformDropBaseline(platformId, previousCampaigns)) {
      rules.push(makeQualityGateRule(
        `platform_count_drop_baseline_skipped:${platformId}`,
        true,
        "medium",
        `${platformId} previous campaign count baseline ignored because deadline data was unreliable`,
        {
          platformId,
          previousCount,
          freshCount,
        },
      ));
      continue;
    }

    const minimumAllowed = Math.floor(previousCount * (1 - QUALITY_GATE_MAX_PLATFORM_DROP_PCT / 100));
    rules.push(makeQualityGateRule(
      `platform_count_drop:${platformId}`,
      freshCount >= minimumAllowed,
      "critical",
      `${platformId} campaign count dropped more than ${QUALITY_GATE_MAX_PLATFORM_DROP_PCT}%`,
      {
        platformId,
        previousCount,
        freshCount,
        minimumAllowed,
      },
    ));
  }

  for (const failed of failedCrawls) {
    const platformId = failed.platformId || failed.label || "unknown";
    const previousCount = previousByPlatform.get(platformId) || 0;
    const canPreserveFailedPlatform = previousCount > 0;
    rules.push(makeQualityGateRule(
      `failed_platform_preserved:${platformId}`,
      canPreserveFailedPlatform,
      canPreserveFailedPlatform ? "high" : "critical",
      canPreserveFailedPlatform
        ? `${platformId} failed and previous campaigns will be preserved`
        : `${platformId} failed and no previous campaigns are available to preserve`,
      {
        platformId,
        previousCount,
        reason: failed.reason,
      },
    ));
  }

  if (candidateTotals.campaigns > 0 && candidateTotals.coordinateCompletenessPct < QUALITY_GATE_WARN_COORDINATE_PCT) {
    rules.push(makeQualityGateRule(
      "candidate_coordinate_completeness_warning",
      true,
      "low",
      "published dataset coordinate completeness is tracked as map coverage only",
      {
        actualPct: candidateTotals.coordinateCompletenessPct,
        targetPct: QUALITY_GATE_WARN_COORDINATE_PCT,
      },
    ));
  }

  for (const [scope, clusters] of [
    ["fresh", findSuspiciousCoordinateClusters(freshCampaigns)],
    ["candidate", findSuspiciousCoordinateClusters(candidateCampaigns)],
  ]) {
    for (const cluster of clusters) {
      rules.push(makeQualityGateRule(
        `${scope}_coordinate_cluster:${cluster.platformId}`,
        false,
        "critical",
        `${cluster.platformId} has too many campaigns on one coordinate cluster`,
        {
          scope,
          platformId: cluster.platformId,
          coordinate: cluster.latLng,
          coordinateSource: cluster.source,
          count: cluster.count,
          total: cluster.total,
          pct: cluster.pct,
          maxPct: QUALITY_GATE_MAX_COORDINATE_CLUSTER_PCT,
          minCluster: QUALITY_GATE_MIN_COORDINATE_CLUSTER,
          topAddress: cluster.topAddress || null,
          topAddressCount: cluster.topAddressCount,
        },
      ));
    }
  }

  const blockingFailures = rules.filter((rule) => !rule.passed && rule.severity === "critical");
  const warnings = rules.filter((rule) => rule.passed && ["critical", "high", "medium"].includes(rule.severity))
    .concat(rules.filter((rule) => !rule.passed && rule.severity !== "critical"));
  const canPublish = !QUALITY_GATE_ENFORCE || blockingFailures.length === 0;

  return {
    status: canPublish
      ? warnings.length > 0
        ? "passed_with_warnings"
        : "passed"
      : "blocked",
    mode: QUALITY_GATE_MODE,
    enforce: QUALITY_GATE_ENFORCE,
    enabled: QUALITY_GATE_ENABLED,
    canPublish,
    checkedAt,
    crawlOnly,
    thresholds: {
      minSuccessfulPlatformPct: QUALITY_GATE_MIN_SUCCESSFUL_PLATFORM_PCT,
      minCoordinatePct: QUALITY_GATE_MIN_COORDINATE_PCT,
      warnCoordinatePct: QUALITY_GATE_WARN_COORDINATE_PCT,
      warnAddressPct: QUALITY_GATE_WARN_ADDRESS_PCT,
      minCoordinateSample: QUALITY_GATE_MIN_COORDINATE_SAMPLE,
      maxPlatformDropPct: QUALITY_GATE_MAX_PLATFORM_DROP_PCT,
      minPlatformBaseline: QUALITY_GATE_MIN_PLATFORM_BASELINE,
    },
    totals: {
      previous: previousTotals,
      fresh: freshTotals,
      candidate: candidateTotals,
    },
    blockingFailures,
    warnings,
    rules,
  };
}

function writeCrawlerPipelineArtifacts({
  crawlStartedAt,
  stage,
  successfulCrawls = [],
  failedCrawls = [],
  freshCampaigns = [],
  publishCandidate = [],
  previousCampaigns = [],
  qualityGate = null,
  pipelineStats = null,
}) {
  const generatedAt = new Date().toISOString();

  writeCrawlerArtifact("raw-campaigns.json", {
    generatedAt,
    crawlStartedAt,
    stage,
    successfulCrawls: successfulCrawls.map((crawl) => ({
      platformId: crawl.platformId,
      label: crawl.label,
      durationMs: crawl.durationMs,
      campaigns: crawl.campaigns,
    })),
    failedCrawls,
  });

  writeCrawlerArtifact("clean-campaigns.json", {
    generatedAt,
    crawlStartedAt,
    stage,
    totals: summarizeCampaignSet(freshCampaigns),
    campaigns: freshCampaigns,
  });

  writeCrawlerArtifact("publish-candidate.json", {
    generatedAt,
    crawlStartedAt,
    stage,
    totals: summarizeCampaignSet(publishCandidate),
    previousTotals: summarizeCampaignSet(previousCampaigns),
    campaigns: publishCandidate,
  });

  writeCrawlerArtifact("duplicates.json", {
    generatedAt,
    crawlStartedAt,
    stage,
    totals: {
      duplicateGroups: pipelineStats?.totals?.duplicateGroups || 0,
      hiddenDuplicates: pipelineStats?.totals?.hiddenDuplicates || 0,
    },
    duplicateGroups: pipelineStats?.duplicateGroups || [],
    hiddenDuplicateCampaigns: pipelineStats?.hiddenDuplicateCampaigns || [],
  });

  writeCrawlerArtifact("stale-campaigns.json", {
    generatedAt,
    crawlStartedAt,
    stage,
    policy: {
      warnDays: CAMPAIGN_STALE_WARN_DAYS,
      hideDays: CAMPAIGN_STALE_HIDE_DAYS,
    },
    totals: {
      preserved: pipelineStats?.totals?.preserved || 0,
      stale: pipelineStats?.totals?.stale || 0,
      hiddenStale: pipelineStats?.totals?.hiddenStale || 0,
      hiddenExpired: pipelineStats?.totals?.hiddenExpired || 0,
    },
    hiddenStaleCampaigns: pipelineStats?.hiddenStaleCampaigns || [],
    hiddenExpiredCampaigns: pipelineStats?.hiddenExpiredCampaigns || [],
  });

  if (qualityGate) {
    writeCrawlerArtifact("quality-gate.json", qualityGate);
  }
}

function buildCrawlStatus({
  crawlStartedAt,
  completedAt = null,
  crawlOnly = [],
  activeCrawlers = [],
  successfulCrawls = [],
  failedCrawls = [],
  campaigns = [],
  supabaseSync = null,
  qualityGate = null,
  pipelineStats = null,
}) {
  const now = completedAt || new Date().toISOString();
  const status = qualityGate?.status === "blocked"
    ? "blocked"
    : failedCrawls.length > 0 || supabaseSync?.status === "failed"
    ? "completed_with_errors"
    : completedAt
      ? "completed"
      : "running";

  return {
    status,
    startedAt: crawlStartedAt,
    updatedAt: now,
    completedAt,
    durationMs: Date.parse(now) - Date.parse(crawlStartedAt),
    crawlOnly,
    activePlatforms: activeCrawlers.map((crawler) => crawler.platformId),
    totals: {
      campaigns: campaigns.length,
      activePlatforms: activeCrawlers.length,
      successfulPlatforms: successfulCrawls.length,
      failedPlatforms: failedCrawls.length,
      coordinateCompletenessPct: getPercent(campaigns.filter(hasUsableCoordinates).length, campaigns.length),
    },
    successfulCrawls: successfulCrawls.map((crawl) => ({
      platformId: crawl.platformId,
      label: crawl.label,
      campaigns: crawl.campaigns.length,
      durationMs: crawl.durationMs,
      duration: formatDurationMs(crawl.durationMs || 0),
    })),
    failedCrawls: failedCrawls.map((crawl) => ({
      platformId: crawl.platformId || null,
      label: crawl.label,
      reason: crawl.reason,
      durationMs: crawl.durationMs,
      duration: formatDurationMs(crawl.durationMs || 0),
    })),
    supabaseSync,
    qualityGate,
    pipeline: pipelineStats,
  };
}

function writeOperationalArtifacts({
  crawlStartedAt,
  completedAt = null,
  crawlOnly = [],
  activeCrawlers = [],
  successfulCrawls = [],
  failedCrawls = [],
  campaigns = [],
  supabaseSync = null,
  qualityGate = null,
  pipelineStats = null,
}) {
  const generatedAt = completedAt || new Date().toISOString();
  writeJsonArtifact("crawl-status.json", buildCrawlStatus({
    crawlStartedAt,
    completedAt,
    crawlOnly,
    activeCrawlers,
    successfulCrawls,
    failedCrawls,
    campaigns,
    supabaseSync,
    qualityGate,
    pipelineStats,
  }));
  writeJsonArtifact("data-quality.json", buildDataQualityReport(campaigns, successfulCrawls, failedCrawls, {
    crawlStartedAt,
    generatedAt,
    qualityGate,
    pipelineStats,
  }));
}

function parseLastPageFromPaging($, selector = ".paging a[href*='page=']") {
  let maxPage = 1;

  $(selector).each((index, element) => {
    const href = $(element).attr("href") || "";
    const match = href.match(/[?&]page=(\d+)/);
    if (!match) return;

    const page = Number(match[1]);
    if (Number.isFinite(page) && page > maxPage) {
      maxPage = page;
    }
  });

  return maxPage;
}

const CRAWLER_LOG_ORDER = [
  { platformId: "reviewnote", label: "reviewnote" },
  { platformId: "mrblog", label: "mrblog" },
  { platformId: "reviewplace", label: "reviewplace" },
  { platformId: "dinner", label: "dinnerqueen" },
  { platformId: "tqueens", label: "tqueens" },
  { platformId: "pavlo", label: "pavlo" },
  { platformId: "seouloba", label: "seouloba" },
  { platformId: "revu", label: "revu" },
  { platformId: "gangnam", label: "gangnam" },
  { platformId: "popomon", label: "popomon" },
  { platformId: "comeplay", label: "comeplay" },
  { platformId: "tble", label: "tble" },
  { platformId: "ringble", label: "ringble" },
  { platformId: "chvu", label: "chvu" },
];
const DEFAULT_EXCLUDED_CRAWLER_IDS = new Set(["reviewnote"]);

function resolveActiveCrawlers(crawlers, crawlOnly = new Set()) {
  if (crawlOnly.size) {
    return crawlers.filter((crawler) => crawlOnly.has(crawler.platformId) || crawlOnly.has(crawler.label));
  }
  return crawlers.filter((crawler) => !DEFAULT_EXCLUDED_CRAWLER_IDS.has(crawler.platformId));
}


function logCrawlerStep(platformId, label) {
  const index = CRAWLER_LOG_ORDER.findIndex((crawler) => crawler.platformId === platformId);
  const total = CRAWLER_LOG_ORDER.length;
  const step = index >= 0 ? index + 1 : "?";
  console.log(`[${step}/${total}] ${label}`);
}

function waitForPromiseToSettle(promise, timeoutMs) {
  return Promise.race([
    promise.then(
      () => true,
      () => true,
    ),
    new Promise((resolve) => setTimeout(() => resolve(false), timeoutMs)),
  ]);
}

async function runCrawlerWithTimeout(crawler) {
  const context = createCrawlerContext(crawler.label);
  let timer = null;
  let timedOut = false;
  const crawlerPromise = withCrawlerContext(context, () => crawler.run(context));
  const timeoutPromise = new Promise((_, reject) => {
    timer = setTimeout(() => {
      timedOut = true;
      context.abort(`timeout after ${CRAWLER_TIMEOUT_MS}ms`);
      reject(context.signal.reason || new Error(`${crawler.label}: timeout after ${CRAWLER_TIMEOUT_MS}ms`));
    }, CRAWLER_TIMEOUT_MS);
  });

  try {
    return await Promise.race([crawlerPromise, timeoutPromise]);
  } catch (error) {
    if (timedOut) {
      const stopped = await waitForPromiseToSettle(crawlerPromise, 10000);
      if (!stopped) {
        crawlerPromise.catch(() => null);
        console.log(`  - ${crawler.label} cleanup still pending after timeout; continuing safely`);
      }
      if (activeCrawlerContext === context) {
        activeCrawlerContext = null;
      }
    }
    throw error;
  } finally {
    if (timer) clearTimeout(timer);
    await context.runCleanups();
  }
}
function mapCampaignForSupabase(campaign) {
  const [regionMatch] = campaign.title.match(/\[[^\]]+\]/) || [];
  const hasBadCoords = isKnownBadMapCoordinate(campaign.lat, campaign.lng);
  const isClosed = isClosedCampaign(campaign);

  return {
    platform_id: campaign.platformId,
    external_id: campaign.id,
    source_url: campaign.url,
    title: campaign.title,
    campaign_type: normalizeCampaignTypeForLaunch(campaign.type),
    category: campaign.category || null,
    region: regionMatch ? regionMatch.replace(/^\[|\]$/g, "") : null,
    location_raw: campaign.locationRaw || null,
    address_raw: campaign.addressRaw || null,
    station_name: campaign.stationName || null,
    place_name: campaign.placeName || null,
    reward_text: campaign.point ? String(campaign.point) : null,
    apply_count: campaign.applyCount || 0,
    selected_count: campaign.selectedCount || 0,
    lat: !hasBadCoords && Number.isFinite(Number(campaign.lat)) ? Number(campaign.lat) : null,
    lng: !hasBadCoords && Number.isFinite(Number(campaign.lng)) ? Number(campaign.lng) : null,
    competition_score: campaign.selectedCount
      ? Number((campaign.applyCount / campaign.selectedCount).toFixed(2))
      : null,
    d_day: isClosed ? Math.min(Number(campaign.dDay ?? -1), -1) : campaign.dDay ?? 99,
    source_started_at: campaign.sourceStartedAt || null,
    source_posted_at: campaign.sourcePostedAt || null,
    coordinate_source: campaign.coordinateSource || null,
    status: isClosed ? "closed" : "open",
    crawled_at: campaign.crawledAt || new Date().toISOString(),
  };
}

const LEGACY_CAMPAIGN_DB_COLUMNS = new Set([
  "platform_id",
  "external_id",
  "source_url",
  "title",
  "campaign_type",
  "category",
  "region",
  "reward_text",
  "apply_count",
  "selected_count",
  "competition_score",
  "d_day",
  "status",
  "crawled_at",
]);

function isMissingColumnSchemaError(error) {
  const message = `${error?.code || ""} ${error?.message || ""} ${error?.details || ""}`;
  return /PGRST204|schema cache|Could not find .* column/i.test(message);
}

function pickCampaignDbColumns(row, columns) {
  return Object.fromEntries(Object.entries(row).filter(([key]) => columns.has(key)));
}

async function upsertToSupabase(campaigns) {
  if (!supabase) {
    console.log("  - SUPABASE_SERVICE_ROLE_KEY is missing. Skip DB upsert.");
    return;
  }

  await runSupabaseOperation("platforms upsert", async () => {
    const { error: platformError } = await supabase
      .from("platforms")
      .upsert(PLATFORM_SEEDS, { onConflict: "id" });
    if (platformError) throw platformError;
  });

  const rows = campaigns.map(mapCampaignForSupabase);
  const rowChunks = chunkArray(rows, SUPABASE_BATCH_SIZE);
  let useLegacyCampaignColumns = false;

  for (let index = 0; index < rowChunks.length; index += 1) {
    const batch = rowChunks[index];
    await runSupabaseOperation(`campaigns upsert batch ${index + 1}/${rowChunks.length}`, async () => {
      const rowsForUpsert = useLegacyCampaignColumns
        ? batch.map((row) => pickCampaignDbColumns(row, LEGACY_CAMPAIGN_DB_COLUMNS))
        : batch;
      const { error: campaignError } = await supabase
        .from("campaigns")
        .upsert(rowsForUpsert, { onConflict: "platform_id,external_id" });

      if (!campaignError) return;
      if (useLegacyCampaignColumns || !isMissingColumnSchemaError(campaignError)) {
        throw campaignError;
      }

      useLegacyCampaignColumns = true;
      console.log("  - campaigns table is missing location/date columns; retrying with legacy column set");

      const { error: legacyCampaignError } = await supabase
        .from("campaigns")
        .upsert(batch.map((row) => pickCampaignDbColumns(row, LEGACY_CAMPAIGN_DB_COLUMNS)), {
          onConflict: "platform_id,external_id",
        });
      if (legacyCampaignError) throw legacyCampaignError;
    });
  }

  console.log(`  - Supabase upsert complete: ${rows.length}`);
}

async function closeExpiredCampaigns() {
  if (!supabase) return;

  const data = await runSupabaseOperation("close_expired_campaigns", async () => {
    const { data: rpcData, error } = await supabase.rpc("close_expired_campaigns");
    if (error) throw error;
    return rpcData;
  });

  console.log(`  - Closed by d_day rule: ${typeof data === "number" ? data : 0}`);
}

async function closeMissingCampaigns(successfulCrawls, crawlStartedAt) {
  if (!supabase) return;

  for (const crawl of successfulCrawls) {
    await runSupabaseOperation(`close missing ${crawl.platformId}`, async () => {
      const { error } = await supabase
        .from("campaigns")
        .update({
          status: "closed",
          crawled_at: new Date().toISOString(),
        })
        .eq("platform_id", crawl.platformId)
        .eq("status", "open")
        .lt("crawled_at", crawlStartedAt);

      if (error) throw error;
    });
  }
}

async function crawlReviewnote() {
  logCrawlerStep("reviewnote", "reviewnote");
  const cooldown = getReviewnoteForbiddenCooldown();
  if (cooldown) {
    console.log(
      `  - reviewnote cooldown active until ${cooldown.expiresAt}; `
      + `skipping network requests (${cooldown.reason || "previous 403"})`,
    );
    throw new Error(`cooldown active after 403 until ${cooldown.expiresAt}`);
  }

  const campaigns = [];
  const seenIds = new Set();
  const endpoint = "https://www.reviewnote.co.kr/api/v2/campaigns";
  const configs = [
    {
      label: "default",
      referer: "https://www.reviewnote.co.kr/campaigns",
      params: {
        gugunSelected: "",
        s: "default",
        limit: 16,
      },
    },
    {
      label: "home",
      referer: "https://www.reviewnote.co.kr/campaigns?city=%EC%9E%AC%ED%83%9D",
      params: {
        city: "\uC7AC\uD0DD",
        gugunSelected: "",
        s: "default",
        limit: 16,
      },
    },
    {
      label: "seoul",
      referer: "https://www.reviewnote.co.kr/campaigns?city=%EC%84%9C%EC%9A%B8",
      params: {
        city: "\uC11C\uC6B8",
        gugunSelected: "",
        s: "default",
        limit: 16,
      },
    },
    {
      label: "reporter",
      referer: "https://www.reviewnote.co.kr/campaigns?sort=REPORTER",
      params: {
        sort: "REPORTER",
        gugunSelected: "",
        s: "default",
        limit: 16,
      },
    },
  ];

  try {
    for (const config of configs) {
      for (let page = 1; page <= 200; page += 1) {
        const before = campaigns.length;
        const data = await fetchJson(endpoint, {
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            ...config.params,
            page,
          },
          headers: {
            Referer: config.referer,
            Origin: "https://www.reviewnote.co.kr",
            ...(REVIEWNOTE_COOKIE ? { Cookie: REVIEWNOTE_COOKIE } : {}),
          },
        });

        const objects = Array.isArray(data?.objects) ? data.objects : [];
        if (objects.length === 0) {
          break;
        }

        for (const item of objects) {
          const id = `rn_${item.id}`;
          if (seenIds.has(id)) continue;

          let type = "\uBC29\uBB38\uD615";
          if (item.sort === "TAKEOUT" || item.offer?.includes("\uD3EC\uC7A5")) {
            type = "\uBC30\uC1A1\uD615";
          } else if (config.label === "reporter") {
            type = "\uAE30\uC790\uB2E8";
          } else if (item.channel === "INSTAGRAM") {
            type = "\uC778\uC2A4\uD0C0";
          }

          const applyEndDday = daysUntilKstDate(item.applyEndAt);
          const endText = Number.isFinite(applyEndDday) ? `D-${Math.max(0, applyEndDday)}` : "";
          const regionText = getReviewnoteRegionText(item);
          campaigns.push(
            buildCampaign({
              id,
              title: cleanText(item.title),
              url: `https://www.reviewnote.co.kr/campaigns/${item.id}`,
              platform: "reviewnote",
              platformId: "reviewnote",
              dDay: Number.isFinite(applyEndDday) ? applyEndDday : parseDDay(endText),
              applyCount: Number(item.applicantCount || 0),
              selectedCount: Number(item.infNum || 0),
              point: item.infPoint ? `${item.infPoint}P` : null,
              type,
              category: cleanText(item.category?.title || "") || undefined,
              region: cleanText(item.city || "") || undefined,
              city: cleanText(item.sido?.name || "") || undefined,
              locationHint: regionText || undefined,
            }),
          );
          seenIds.add(id);
        }

        const addedOnPage = campaigns.length - before;
        if (addedOnPage === 0) {
          console.log(`  - reviewnote ${config.label} page ${page}: duplicate-only page`);
          break;
        }

        const totalPages = Number(data?.total_pages || 0);
        if (totalPages > 0 && page >= totalPages) {
          break;
        }
      }
    }

    if (REVIEWNOTE_COOKIE) {
      await enrichReviewnoteDetails(campaigns);
    } else {
      console.log("  - reviewnote detail enrich skipped: REVIEWNOTE_COOKIE missing; public detail page has no address data");
    }

    console.log(`  - reviewnote: ${campaigns.length}`);
    clearReviewnoteForbiddenCooldown();
    return campaigns;
  } catch (error) {
    if (!REVIEWNOTE_COOKIE && error.response?.status === 403) {
      console.log("  - reviewnote auth-like cookie required: set REVIEWNOTE_COOKIE from browser request headers");
    }
    if (isForbiddenRequestError(error)) {
      const nextCooldown = recordReviewnoteForbiddenCooldown(error);
      if (nextCooldown) {
        console.log(`  - reviewnote 403 cooldown recorded until ${nextCooldown.expiresAt}`);
      }
    }
    console.log(`  - reviewnote failed: ${error.message}`);
    throw error;
  }
}
const MRBLOG_BASE_URL = "https://www.mrblog.net";
const MRBLOG_LIST_CONFIGS = [
  {
    label: "today",
    referer: `${MRBLOG_BASE_URL}/campaigns/today`,
    params: {
      type: "today",
      category: "",
      order_by: 1,
      "is_instagram[0]": 0,
      "is_instagram[1]": 1,
    },
  },
  {
    label: "region",
    referer: `${MRBLOG_BASE_URL}/campaigns/region`,
    params: {
      type: "region",
      category: "",
      order_by: 1,
      "is_instagram[0]": 0,
      "is_instagram[1]": 1,
      category_seq: "",
    },
  },
  {
    label: "delivery",
    referer: `${MRBLOG_BASE_URL}/campaigns/delivery`,
    params: {
      type: "delivery",
      category: "",
      order_by: 1,
      "is_instagram[0]": 0,
      "is_instagram[1]": 1,
      category_seq: "",
    },
  },
  {
    label: "instagram",
    referer: `${MRBLOG_BASE_URL}/campaigns?is_instagram=1`,
    params: {
      type: "all",
      category: "",
      order_by: 1,
      "is_instagram[0]": 1,
      category_seq: "",
    },
  },
];

function getMrblogConfigs() {
  const scope = cleanText(process.env.MRBLOG_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488"].includes(scope)) {
    return MRBLOG_LIST_CONFIGS.filter((config) => config.label === "delivery");
  }
  return [...MRBLOG_LIST_CONFIGS];
}

function getMrblogUrl(href = "") {
  try {
    return new URL(href, `${MRBLOG_BASE_URL}/campaigns/`).toString();
  } catch {
    return "";
  }
}

function parseMrblogListCampaigns(html, { fallbackType = "visit", seenIds = new Set() } = {}) {
  const $ = cheerio.load(`<ul>${html || ""}</ul>`);
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  $("a.campaign_item[href*='/campaigns/']").each((index, element) => {
    const card = $(element);
    const href = card.attr("href") || "";
    const match = href.match(/\/campaigns\/(\d+)/);
    if (!match) return;

    const id = `mb_${match[1]}`;
    if (parsedIds.has(id)) return;

    const title = cleanText(card.find(".subject").text());
    if (!title) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    const rawArea = cleanText(card.find(".area").text());
    const area = cleanCampaignAreaText(rawArea);
    const desc = cleanText(card.find(".desc").text());
    const countText = cleanText(card.find(".count").text());
    const imageSrc = card.find(".thumb img, img").first().attr("src") || "";
    const fullText = cleanText([title, area, desc, card.find(".status").text()].join(" "));

    let type = fallbackType === "delivery" ? "delivery" : "visit";
    if (type !== "delivery") {
      if (rawArea.includes("\uB9B4\uC2A4") || desc.includes("[\uB9B4\uC2A4")) {
        type = "reels";
      } else if (rawArea.includes("\uD074\uB9BD") || desc.includes("[\uD074\uB9BD")) {
        type = "clip";
      } else if (rawArea.includes("\uBC30\uC1A1") || desc.includes("\uD3EC\uC7A5") || desc.includes("\uBC30\uC1A1")) {
        type = "delivery";
      } else if (desc.includes("\uAE30\uC790\uB2E8")) {
        type = "reporter";
      }
    }

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getMrblogUrl(href),
        platform: "\uBBF8\uBE14",
        platformId: "mrblog",
        dDay: parseDDay(card.find(".d_day").text() || fullText),
        applyCount: parseNumber((countText.match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber((countText.match(/\uBAA8\uC9D1\s*([\d,]+)/) || [])[1] || ""),
        point: desc || null,
        type,
        category: guessCategory(`${title} ${desc}`),
        locationRaw: pickBestCampaignAreaText(area),
        ...(imageSrc ? { imageUrl: getMrblogUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return { campaigns, parsedCount, addedCount };
}

async function crawlMrblog() {
  logCrawlerStep("mrblog", "mrblog");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = `${MRBLOG_BASE_URL}/xhr/campaigns`;
  const configs = getMrblogConfigs();

  const enrichMrblogCampaignLocations = async () => {
    await processCampaignsInBatches("mrblog", campaigns, async (campaign) => {
      try {
        const authState = await getMrblogAuthState(false, campaign.url);
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://www.mrblog.net/campaigns/region",
            ...(authState.cookie ? { Cookie: authState.cookie } : {}),
            ...(authState.csrfToken ? { "X-CSRF-TOKEN": authState.csrfToken } : {}),
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const provisionText = extractMrblogProvisionFromDetail($);
        const labeledTexts = $("dt")
          .filter((_, element) => /주소|위치|장소|방문/.test(cleanText($(element).text())))
          .map((_, element) => cleanAddressText($(element).next("dd").text()))
          .get();
        const dataTexts = $(".data")
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const sectionTexts = $(".place, .location, .address")
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const bodyText = cleanText($("body").text());
        const extractedAddress = pickBestLocationText(
          labeledTexts,
          dataTexts,
          sectionTexts,
          extractAddressCandidates(bodyText),
        );
        const recruitPeriodText = cleanText(
          $("dt")
            .filter((_, element) => cleanText($(element).text()) === "\uBAA8\uC9D1 \uAE30\uAC04")
            .first()
            .next("dd")
            .text(),
        );
        const sourceStartedAt = parseSourceDate(recruitPeriodText);

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (provisionText) {
          campaign.point = provisionText;
        }
      } catch (error) {
        console.log(`  - mrblog location enrich failed (${campaign.id}): ${error.message}`);
      }
    });
  };

  const fetchMrblogCampaignPage = async (config, page, forceRefresh = false) => {
    try {
      const crawlerContext = getActiveCrawlerContext();
      const authState = await getMrblogAuthState(forceRefresh, config.referer);
      const response = await axios({
        method: "get",
        url: endpoint,
        httpsAgent: shouldUseLegacyTls(endpoint) ? LEGACY_TLS_AGENT : undefined,
        maxRedirects: 0,
        validateStatus: (status) => (status >= 200 && status < 300) || status === 302,
        headers: {
          ...HEADERS,
          Accept: "application/json, text/plain, */*",
          "X-Requested-With": "XMLHttpRequest",
          Referer: config.referer,
          ...(authState.cookie ? { Cookie: authState.cookie } : {}),
          ...(authState.csrfToken ? { "X-CSRF-TOKEN": authState.csrfToken } : {}),
        },
        params: {
          ...config.params,
          page,
        },
        timeout: 25000,
        signal: crawlerContext?.signal,
        responseType: "json",
      });

      const redirectedToLogin =
        response.status === 302 ||
        /\/login(?:[/?]|$)/.test(String(response.headers?.location || ""));
      const returnedLoginMarkup =
        typeof response.data === "string" &&
        /<form[^>]*[^>](login|password)|name=["']password["']/i.test(response.data);

      if (redirectedToLogin || returnedLoginMarkup) {
        if (forceRefresh) {
          throw new Error("mrblog auth rejected after session refresh");
        }

        console.log(`  - mrblog ${config.label} page ${page}: session rejected, refreshing`);
        return fetchMrblogCampaignPage(config, page, true);
      }

      return response.data;
    } catch (error) {
      const status = error.response?.status;
      if (!forceRefresh && [401, 403, 419].includes(status)) {
        console.log(`  - mrblog ${config.label} page ${page}: ${status}, refreshing session`);
        await getMrblogAuthState(true, config.referer);
        return fetchMrblogCampaignPage(config, page, true);
      }

      throw error;
    }
  };

  try {
    for (const config of configs) {
      for (let page = 1; page <= 200; page += 1) {
        const data = await fetchMrblogCampaignPage(config, page);

        const html = typeof data?.html === "string" ? data.html : "";
        const count = Number(data?.count || 0);
        if (!html.trim() || count === 0) {
          break;
        }

        const parsed = parseMrblogListCampaigns(html, {
          fallbackType: config.label,
          seenIds,
        });
        campaigns.push(...parsed.campaigns);
        const added = parsed.addedCount;

        if (added === 0) {
          console.log(`  - mrblog ${config.label} page ${page}: duplicate-only page`);
        }

        if (count < 24) {
          break;
        }
      }
    }

    await enrichMrblogCampaignLocations();
    console.log(`  - mrblog: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    if (!MRBLOG_COOKIE && !MRBLOG_LOGIN_ID) {
      console.log(
        "  - mrblog auth required: set MRBLOG_COOKIE/MRBLOG_X_CSRF_TOKEN or MRBLOG_LOGIN_ID/MRBLOG_LOGIN_PASSWORD",
      );
    }
    console.log(`  - mrblog failed: ${error.message}`);
    throw error;
  }
}

const REVIEWPLACE_BASE_URL = "https://www.reviewplace.co.kr";
const REVIEWPLACE_LIST_CATEGORIES = [
  { label: "\uC81C\uD488", fallbackType: "delivery", fallbackCategory: "\uC0DD\uD65C\uC6A9\uD488" },
  { label: "\uC9C0\uC5ED", fallbackType: "visit", fallbackCategory: "\uB9DB\uC9D1" },
  { label: "\uAE30\uC790\uB2E8", fallbackType: "reporter", fallbackCategory: "\uAE30\uD0C0" },
  { label: "\uAD6C\uB9E4\uD3C9", fallbackType: "purchase", fallbackCategory: "\uC0DD\uD65C\uC6A9\uD488" },
  { label: "N\uC778\uD50C\uB8E8\uC5B8\uC11C", fallbackType: "instagram", fallbackCategory: "\uAE30\uD0C0" },
  { label: "T\ub054", fallbackType: "visit", fallbackCategory: "\uAE30\uD0C0" },
];

function getReviewplaceCategories() {
  const scope = cleanText(process.env.REVIEWPLACE_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488"].includes(scope)) {
    return REVIEWPLACE_LIST_CATEGORIES.filter((category) => category.label === "\uC81C\uD488");
  }
  return [...REVIEWPLACE_LIST_CATEGORIES];
}

function getReviewplaceUrl(href = "") {
  try {
    return new URL(href, `${REVIEWPLACE_BASE_URL}/pr/`).toString();
  } catch {
    return "";
  }
}

function parseReviewplaceListCampaigns(html, { category, seenIds = new Set() } = {}) {
  const $ = cheerio.load(`<div>${html || ""}</div>`);
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  $("a[href*='/pr/?id=']").each((index, element) => {
    const card = $(element);
    const href = card.attr("href") || "";
    const match = href.match(/\/pr\/\?id=(\d+)/);
    if (!match) return;

    const id = `rp_${match[1]}`;
    if (parsedIds.has(id)) return;

    const block = card.closest(".item").length ? card.closest(".item") : card;
    const title =
      cleanText(block.find(".tit").first().text()) ||
      cleanText(block.find(".subject, strong").first().text()) ||
      cleanText(card.attr("title") || "");
    if (!title) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    const desc = cleanText(block.find(".txt_wrap .txt, .txt").first().text());
    const pointTag = cleanText(block.find(".txt_tag").first().text());
    const dateText = cleanText(block.find(".date_wrap .date, .date").first().text());
    const countText = cleanText(block.find(".date_wrap .num, .num").first().text());
    const imageSrc = block.find(".img img, img.thumbimg, img").first().attr("src") || "";
    const textBlock = block.clone();
    textBlock.find("img,svg,script,style,noscript").remove();
    const full = cleanText(textBlock.text());

    let type = category?.fallbackType || "visit";
    if (type !== "delivery") {
      if (full.includes("\uAE30\uC790\uB2E8")) {
        type = "reporter";
      } else if (full.includes("\uAD6C\uB9E4\uD3C9")) {
        type = "purchase";
      } else if (full.includes("\uBC30\uC1A1") || category?.label === "\uC81C\uD488") {
        type = "delivery";
      } else if (full.includes("\uB9B4\uC2A4")) {
        type = "reels";
      } else if (full.includes("\uD074\uB9BD")) {
        type = "clip";
      } else if (full.includes("\uC778\uC2A4\uD0C0")) {
        type = "instagram";
      }
    }

    const pointFromP = (pointTag.match(/[+]?[\d,]+\s*P/) || full.match(/[+]?[\d,]+\s*P/) || [])[0] || "";
    const sectDesc = cleanText(block.find(".sect_desc").first().text());
    const point = desc || sectDesc || pointFromP || null;

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getReviewplaceUrl(href),
        platform: "reviewplace",
        platformId: "reviewplace",
        dDay: parseDDay(dateText || full),
        applyCount: parseNumber((countText.match(/\uC2E0\uCCAD\s*([\d,]+)/) || full.match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber((countText.match(/\/\s*([\d,]+)\uBA85/) || full.match(/\/\s*([\d,]+)\uBA85/) || [])[1] || ""),
        point,
        type,
        category: category?.fallbackCategory || guessCategory(`${title} ${desc}`),
        ...(imageSrc ? { imageUrl: getReviewplaceUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return { campaigns, parsedCount, addedCount };
}

async function crawlReviewplace() {
  logCrawlerStep("reviewplace", "reviewplace");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = `${REVIEWPLACE_BASE_URL}/theme/rp/_ajax_cmp_list_tpl.php`;
  const categories = getReviewplaceCategories();

  try {
    for (const category of categories) {
      for (let page = 1; page <= 200; page += 1) {
        throwIfCrawlerAborted();
        const before = campaigns.length;
        const html = await fetchHtml(endpoint, {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            ct1: category.label,
            device: "pc",
            rpage: page,
          },
          headers: {
            Referer: `https://www.reviewplace.co.kr/pr/?ct1=${encodeURIComponent(category.label)}&device=pc`,
            "X-Requested-With": "XMLHttpRequest",
            Accept: "text/html, */*; q=0.01",
            ...(REVIEWPLACE_COOKIE ? { Cookie: REVIEWPLACE_COOKIE } : {}),
          },
        });

        const parsed = parseReviewplaceListCampaigns(html, { category, seenIds });
        campaigns.push(...parsed.campaigns);
        const addedOnPage = campaigns.length - before;
        if (parsed.parsedCount === 0) {
          break;
        }

        if (addedOnPage === 0) {
          console.log(`  - reviewplace ${category.label} page ${page}: duplicate-only page`);
          break;
        }
      }
    }

    await processCampaignsInBatches("reviewplace", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://www.reviewplace.co.kr/pr/",
            ...(REVIEWPLACE_COOKIE ? { Cookie: REVIEWPLACE_COOKIE } : {}),
          },
        });

        const $ = cheerio.load(html);
        const provisionText = extractReviewplaceProvisionFromDetail($);
        const mapAddressTexts = $("dd.bstyle")
          .map((_, element) => {
            const clone = $(element).clone();
            clone.find("#map, #mapp, [id*='map'], .map, script, style").remove();
            return cleanAddressText(clone.text());
          })
          .get();
        const candidateTexts = $("dd.bstyle > p, dd.bstyle p, .address, .place")
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          mapAddressTexts,
          candidateTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (provisionText) {
          campaign.point = provisionText;
        }
      } catch (error) {
        console.log(`  - reviewplace location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - reviewplace: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - reviewplace failed: ${error.message}`);
    throw error;
  }
}

function compareDinnerqueenDetailTargets(left, right) {
  const leftClosed = isClosedCampaign(left) ? 1 : 0;
  const rightClosed = isClosedCampaign(right) ? 1 : 0;
  if (leftClosed !== rightClosed) return leftClosed - rightClosed;

  const leftHasPoint = cleanText(left?.point) ? 1 : 0;
  const rightHasPoint = cleanText(right?.point) ? 1 : 0;
  if (leftHasPoint !== rightHasPoint) return leftHasPoint - rightHasPoint;

  const leftDDay = Number(left?.dDay);
  const rightDDay = Number(right?.dDay);
  const normalizedLeftDDay = Number.isFinite(leftDDay) && leftDDay >= 0 ? leftDDay : 999;
  const normalizedRightDDay = Number.isFinite(rightDDay) && rightDDay >= 0 ? rightDDay : 999;
  if (normalizedLeftDDay !== normalizedRightDDay) return normalizedLeftDDay - normalizedRightDDay;

  return Number(left?.applyCount || 0) - Number(right?.applyCount || 0);
}

function selectDinnerqueenDetailTargets(campaigns = [], limit = DINNERQUEEN_DETAIL_ENRICH_LIMIT) {
  if (!Array.isArray(campaigns)) return [];
  const prioritizedCampaigns = [...campaigns].sort(compareDinnerqueenDetailTargets);
  if (Number(limit) <= 0) return prioritizedCampaigns;
  return prioritizedCampaigns.slice(0, Number(limit));
}

function getDinnerqueenUrl(href = "") {
  try {
    return new URL(href, "https://dinnerqueen.net").toString();
  } catch {
    return "";
  }
}

function cleanDinnerqueenListTitle(text = "") {
  return cleanText(text)
    .replace(/\s*신청하기\s*$/i, "")
    .replace(/\[\s*([^\]]+?)\s*\]/g, "[$1]")
    .replace(/\s+/g, " ")
    .trim();
}

function parseDinnerqueenListResponse(html = "") {
  try {
    const parsed = JSON.parse(html || "{}");
    const hasNext = typeof parsed.has_next === "boolean" ? parsed.has_next : null;
    if (typeof parsed.layout === "string") {
      return { layout: parsed.layout, hasNext };
    }
    return { layout: html || "", hasNext };
  } catch { }

  return { layout: html || "", hasNext: null };
}

function extractDinnerqueenListLayout(html = "") {
  return parseDinnerqueenListResponse(html).layout;
}

function mapDinnerqueenListType(text = "", fallbackType = LAUNCH_CAMPAIGN_TYPE) {
  const normalized = cleanText(text);
  if (normalized.includes("배달")) return "delivery";
  if (normalized.includes("배송") || normalized.includes("포장")) return "delivery";
  if (normalized.includes("릴스")) return "reels";
  if (normalized.includes("클립")) return "clip";
  if (normalized.includes("기자단")) return "reporter";
  return fallbackType;
}

function parseDinnerqueenListCampaigns(html, { seenIds = new Set(), fallbackType = LAUNCH_CAMPAIGN_TYPE } = {}) {
  const layout = extractDinnerqueenListLayout(html);
  const $ = cheerio.load(`<div>${layout}</div>`);
  const campaigns = [];
  let parsedCount = 0;

  $("a.qz-dq-card__link[href*='/taste/'], a[href*='/taste/']").each((index, element) => {
    const card = $(element);
    const href = card.attr("href") || "";
    const match = href.match(/\/taste\/(\d+)/);
    if (!match) return;
    parsedCount += 1;

    const id = `dq_${match[1]}`;
    if (seenIds.has(id)) return;

    const root = card.closest(".qz-dq-card, .qz-col");
    const imageSrc = root.find("img[src]").first().attr("src") || "";
    const textRoot = root.clone();
    textRoot.find("img,script,style,noscript").remove();
    const full = cleanText(textRoot.text());
    const title =
      cleanDinnerqueenListTitle(root.find(".qz-dq-card__link").attr("title") || "") ||
      cleanDinnerqueenListTitle(root.find(".qz-body2-kr--line.ellipsis, .qz-body2-kr--line").first().text()) ||
      full.split(/\s{2,}/).map(cleanDinnerqueenListTitle).filter(isValidTitle)[0] ||
      cleanDinnerqueenListTitle(full.slice(0, 80));
    if (!title) return;

    const titleLocationHint = parseRegionalPlaceTitle(title);
    const dqProvision = cleanText(root.find("p.qz-body-kr strong.w-600, .qz-body-kr strong").first().text()) || null;
    const selectedText = (full.match(/(?:\/\s*)?모집\s*([\d,]+)/) || full.match(/\/\s*([\d,]+)\s*명/) || [])[1] || "";

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getDinnerqueenUrl(href),
        platform: "dinnerqueen",
        platformId: "dinner",
        dDay: parseDDay(full),
        applyCount: parseNumber((full.match(/신청\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber(selectedText),
        point: dqProvision,
        type: mapDinnerqueenListType(full, fallbackType),
        category: guessCategory(`${title} ${dqProvision || ""} ${full}`),
        locationRaw: pickBestLocationText(full) || titleLocationHint.locationHint,
        placeName: titleLocationHint.placeName,
        imageUrl: imageSrc ? getDinnerqueenUrl(imageSrc) : "",
      }),
    );
    seenIds.add(id);
  });

  return {
    campaigns,
    parsedCount,
    addedCount: campaigns.length,
  };
}

const TQUEENS_BASE_URL = "https://tqueens.net";

function getTqueensUrl(href = "") {
  try {
    return new URL(href, TQUEENS_BASE_URL).toString();
  } catch {
    return "";
  }
}

function parseTqueensListResponse(html = "") {
  return parseDinnerqueenListResponse(html);
}

function buildTqueensListRequest(page = 1) {
  return {
    params: {
      area1: "",
      area2: "",
      cate: "",
      page,
      query: "",
      deal: "",
    },
    referer: `${TQUEENS_BASE_URL}/taste?lpage=${page}&query=&deal=&cate=&order=&area1=&area2=`,
  };
}

function parseTqueensListCampaigns(html, { seenIds = new Set() } = {}) {
  const pageResult = parseTqueensListResponse(html);
  const $ = cheerio.load(`<div>${pageResult.layout}</div>`);
  const campaigns = [];
  let parsedCount = 0;
  let addedCount = 0;

  $("a.qz-dq-card__link[href*='/taste/'], a[href*='/taste/']").each((index, element) => {
    const card = $(element);
    const href = card.attr("href") || "";
    const match = href.match(/\/taste\/(\d+)/);
    if (!match) return;

    parsedCount += 1;
    const id = `tq_${match[1]}`;
    if (seenIds.has(id)) return;

    const root = card.closest(".qz-dq-card, .qz-col");
    const imageSrc = root.find("img[src]").first().attr("src") || "";
    const textRoot = root.clone();
    textRoot.find("img,script,style,noscript").remove();
    const full = cleanText(textRoot.text());
    const title =
      cleanDinnerqueenListTitle(card.attr("title") || "") ||
      cleanDinnerqueenListTitle(root.find(".color-title .keep-a, .color-title strong").first().text()) ||
      cleanDinnerqueenListTitle(root.find(".qz-body-kr--line.ellipsis, .qz-body2-kr--line.ellipsis").first().text()) ||
      full.split(/\s{2,}/).map(cleanDinnerqueenListTitle).filter(isValidTitle)[0] ||
      cleanDinnerqueenListTitle(full.slice(0, 80));
    if (!title) return;

    const provision = cleanText(root.find(".color-placeholder").first().text()) || null;
    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getTqueensUrl(href),
        platform: "택배의여왕",
        platformId: "tqueens",
        dDay: parseDDay(full),
        point: provision,
        type: "delivery",
        category: guessCategory(`${title} ${provision || ""} ${full}`),
        ...(imageSrc ? { imageUrl: getTqueensUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return {
    campaigns,
    parsedCount,
    addedCount,
    hasNext: pageResult.hasNext,
  };
}

function extractTqueensProvisionFromDetail(input) {
  const $ = typeof input === "function" ? input : cheerio.load(input || "");
  return extractDinnerqueenProvisionFromDetail($);
}

function getDinnerqueenListConfigs() {
  const allConfig = { label: "all", ct: "전체", fallbackType: "visit" };
  const deliveryConfig = { label: "delivery", ct: "배송", fallbackType: "delivery" };
  const scope = cleanText(process.env.DINNERQUEEN_LIST_SCOPE || "").toLowerCase();

  if (["delivery", "shipping", "배송", "배송형"].includes(scope)) {
    return [deliveryConfig];
  }
  if (["all", "전체", "visit", "방문", "방문형"].includes(scope)) {
    return [allConfig];
  }

  return [allConfig, deliveryConfig];
}

function buildDinnerqueenListRequest(config, page) {
  const ct = config?.ct || "";
  const area1 = "\uC804\uAD6D";
  const area2 = "\uC804\uCCB4";
  const ctype = config?.ctype || "";

  return {
    params: {
      ct,
      area1,
      area2,
      page,
      ctype,
      query: "",
    },
    referer:
      `https://dinnerqueen.net/taste?ct=${encodeURIComponent(ct)}` +
      `&lpage=${page}&query=&deal=&cate=&order=&area1=${encodeURIComponent(area1)}` +
      `&area2=${encodeURIComponent(area2)}&ctype=${encodeURIComponent(ctype)}`,
  };
}

function shouldContinueDinnerqueenListPage({ parsedCount, addedOnPage, hasNext }) {
  if (hasNext === false) return false;
  if (parsedCount === 0) return false;
  if (addedOnPage === 0 && hasNext !== true) return false;
  return true;
}

async function crawlDinnerqueen() {
  logCrawlerStep("dinner", "dinnerqueen");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = "https://dinnerqueen.net/taste/taste_list";

  try {
    const listConfigs = getDinnerqueenListConfigs();
    if (process.env.DINNERQUEEN_LIST_SCOPE) {
      console.log(`  - dinnerqueen list scope: ${listConfigs.map((config) => config.label).join(", ")}`);
    }

    for (const config of listConfigs) {
      for (let page = 1; page <= 300; page += 1) {
        const before = campaigns.length;
        const request = buildDinnerqueenListRequest(config, page);
        const html = await fetchHtml(endpoint, {
          method: "post",
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: request.params,
          headers: {
            Origin: "https://dinnerqueen.net",
            Referer: request.referer,
            "X-Requested-With": "XMLHttpRequest",
            Accept: "*/*",
            ...(DINNERQUEEN_COOKIE ? { Cookie: DINNERQUEEN_COOKIE } : {}),
          },
        });
        const pageResult = parseDinnerqueenListResponse(html);

        const parsed = parseDinnerqueenListCampaigns(pageResult.layout, {
          seenIds,
          fallbackType: config.fallbackType,
        });
        campaigns.push(...parsed.campaigns);

        const addedOnPage = campaigns.length - before;

        if (addedOnPage === 0) {
          console.log(`  - dinnerqueen ${config.label} page ${page}: duplicate-only page`);
        }

        if (!shouldContinueDinnerqueenListPage({
          parsedCount: parsed.parsedCount,
          addedOnPage,
          hasNext: pageResult.hasNext,
        })) {
          break;
        }
      }
    }

    const dinnerqueenDetailTargets = selectDinnerqueenDetailTargets(campaigns, DINNERQUEEN_DETAIL_ENRICH_LIMIT);

    if (DINNERQUEEN_DETAIL_ENRICH_LIMIT > 0 && campaigns.length > dinnerqueenDetailTargets.length) {
      console.log(
        `  - dinnerqueen detail enrich limited to ${dinnerqueenDetailTargets.length}/${campaigns.length} campaigns`,
      );
    }

    const _dqEnrichErrorCounts = new Map();
    await processCampaignsInBatches("dinnerqueen", dinnerqueenDetailTargets, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: DINNERQUEEN_DETAIL_TIMEOUT_MS,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://dinnerqueen.net/taste",
            ...(DINNERQUEEN_COOKIE ? { Cookie: DINNERQUEEN_COOKIE } : {}),
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const provisionText = extractDinnerqueenProvisionFromDetail($);
        const labeledTexts = $("p, li, div")
          .map((_, element) => {
            const text = cleanText($(element).text());
            return /\uBC29\uBB38\s*\uC704\uCE58/.test(text) ? cleanAddressText(text) : "";
          })
          .get();
        const extractedAddress = pickBestLocationText(
          labeledTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (provisionText) {
          campaign.point = provisionText;
        }
      } catch (error) {
        if (getActiveCrawlerContext()?.signal?.aborted) {
          throw error;
        }
        const _dqErrKey = error.message || "unknown";
        const _dqErrCount = (_dqEnrichErrorCounts.get(_dqErrKey) || 0) + 1;
        _dqEnrichErrorCounts.set(_dqErrKey, _dqErrCount);
        if (_dqErrCount === 1) {
          console.log(`  - dinnerqueen location enrich failed (${campaign.id}): ${error.message}`);
        }
      }
    }, {
      batchSize: DINNERQUEEN_DETAIL_ENRICH_CONCURRENCY,
      batchDelayMs: DINNERQUEEN_DETAIL_BATCH_DELAY_MS,
    });

    const dinnerqueenProvisionCount = campaigns.filter((campaign) => cleanText(campaign.point)).length;
    console.log(
      `  - dinnerqueen provision enrich: ${dinnerqueenProvisionCount}/${campaigns.length} campaigns`,
    );
    for (const [_dqErrMsg, _dqErrCnt] of _dqEnrichErrorCounts) {
      if (_dqErrCnt > 1) {
        console.log(`  - dinnerqueen location enrich: same error repeated ${_dqErrCnt}x total ("${_dqErrMsg}")`);
      }
    }

    console.log(`  - dinnerqueen: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - dinnerqueen failed: ${error.message}`);
    throw error;
  }
}

async function crawlTqueens() {
  logCrawlerStep("tqueens", "tqueens");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = `${TQUEENS_BASE_URL}/taste/taste_list`;

  try {
    for (let page = 1; page <= 300; page += 1) {
      const before = campaigns.length;
      const request = buildTqueensListRequest(page);
      const html = await fetchHtml(endpoint, {
        method: "post",
        encoding: "utf-8",
        timeoutMs: 25000,
        attempts: 3,
        retryDelayMs: 1500,
        params: request.params,
        headers: {
          Origin: TQUEENS_BASE_URL,
          Referer: request.referer,
          "X-Requested-With": "XMLHttpRequest",
          Accept: "*/*",
        },
      });

      const parsed = parseTqueensListCampaigns(html, { seenIds });
      campaigns.push(...parsed.campaigns);

      const addedOnPage = campaigns.length - before;
      if (addedOnPage === 0) {
        console.log(`  - tqueens page ${page}: duplicate-only page`);
      }

      if (!shouldContinueDinnerqueenListPage({
        parsedCount: parsed.parsedCount,
        addedOnPage,
        hasNext: parsed.hasNext,
      })) {
        break;
      }
    }

    await processCampaignsInBatches("tqueens", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: DINNERQUEEN_DETAIL_TIMEOUT_MS,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: `${TQUEENS_BASE_URL}/taste`,
          },
        });

        const $ = cheerio.load(html);
        const detailState = applyCampaignDetailState(campaign, html, $);
        const provisionText = extractTqueensProvisionFromDetail($);
        const sourceStartedAt = extractSourceStartedAt($, detailState.bodyText);
        const deadlineInfo = extractDetailDeadlineInfo($, detailState.bodyText);

        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (deadlineInfo.sourceStartedAt) {
          campaign.sourceStartedAt = deadlineInfo.sourceStartedAt;
        }
        if (deadlineInfo.sourceEndedAt) {
          campaign.sourceEndedAt = deadlineInfo.sourceEndedAt;
        }
        if (Number.isFinite(deadlineInfo.dDay)) {
          campaign.dDay = deadlineInfo.dDay;
        }
        if (provisionText) {
          campaign.point = provisionText;
          campaign.category = guessCategory(`${campaign.title} ${provisionText}`);
        }
      } catch (error) {
        console.log(`  - tqueens detail enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - tqueens: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - tqueens failed: ${error.message}`);
    throw error;
  }
}

const PAVLO_BASE_URL = "https://pavlovu.com";
const PAVLO_SEED_URLS = [
  `${PAVLO_BASE_URL}/review_hit_campaign_list.php`,
  `${PAVLO_BASE_URL}/review_everyone_campaign_list.php`,
  `${PAVLO_BASE_URL}/review_always_campaign_list.php`,
];
const PAVLO_LIST_CONFIGS = [
  {
    label: "delivery",
    categoryId: "001A",
    referer: `${PAVLO_BASE_URL}/review_campaign_list.php?category_id=001A`,
  },
  {
    label: "category-002A",
    categoryId: "002A",
    referer: `${PAVLO_BASE_URL}/review_campaign_list.php?category_id=002A`,
  },
];

function getPavloConfigs() {
  const scope = cleanText(process.env.PAVLO_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488", "001a"].includes(scope)) {
    return PAVLO_LIST_CONFIGS.filter((config) => config.categoryId === "001A");
  }
  return [...PAVLO_LIST_CONFIGS];
}

function getPavloSeedUrls() {
  const scope = cleanText(process.env.PAVLO_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488", "001a"].includes(scope)) {
    return [];
  }
  return [...PAVLO_SEED_URLS];
}

function getPavloUrl(href = "") {
  try {
    return new URL(href, `${PAVLO_BASE_URL}/review_campaign_list.php`).toString();
  } catch {
    return "";
  }
}

function parsePavloListCampaigns(html, { seenIds = new Set() } = {}) {
  const $ = cheerio.load(html);
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  const addCampaign = (item, link) => {
    const href = link.attr("href") || "";
    const match = href.match(/cp_id=(\d+)/);
    if (!match) return;

    const id = `pv_${match[1]}`;
    if (parsedIds.has(id)) return;

    const title =
      cleanText(item.find(".it_name").first().text()) ||
      cleanText(link.attr("title") || "");
    const point =
      cleanText(item.find(".it_description").first().text()) ||
      null;
    const dDayText = cleanText(item.find(".dday").first().text());
    const recruitText = cleanText(item.find(".option").first().text());
    const typeText = cleanText(`${item.find(".option2").text()} ${item.find(".sns_info").text()} ${title}`);
    const imageSrc = item.find(".thumb img.it_img, img.it_img, .thumb img, img").first().attr("src") || "";

    const textItem = item.clone();
    textItem.find("img,script,style").remove();
    const full = cleanText(textItem.text());
    const lines = full.split(/\s{2,}/).map(cleanText).filter(isValidTitle);
    const normalizedTitle = title || lines[0];
    if (!normalizedTitle) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    let type = "visit";
    if (typeText.includes("\uBC30\uC1A1") || typeText.includes("\uD3EC\uC7A5")) {
      type = "delivery";
    } else if (typeText.includes("\uAD6C\uB9E4")) {
      type = "purchase";
    } else if (typeText.includes("\uAE30\uC790\uB2E8")) {
      type = "reporter";
    } else if (typeText.includes("\uB9B4\uC2A4")) {
      type = "reels";
    } else if (typeText.includes("\uC1FC\uCE20") || typeText.includes("N\uD074\uB9BD")) {
      type = "clip";
    } else if (typeText.includes("\uC778\uC2A4\uD0C0")) {
      type = "instagram";
    }

    campaigns.push(
      buildCampaign({
        id,
        title: normalizedTitle,
        url: getPavloUrl(href),
        platform: "pavlo",
        platformId: "pavlo",
        point,
        dDay: parseDDay(dDayText || full),
        applyCount: parseNumber(((recruitText || full).match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber(
          ((recruitText || full).match(/\uBAA8\uC9D1\s*([\d,]+)/) || [])[1] || "",
        ),
        type,
        category: guessCategory(`${normalizedTitle} ${point || ""}`),
        ...(imageSrc ? { imageUrl: getPavloUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  };

  const items = $(".box, .tanz_campaign_list_wrap li, .item_box_list li, li:has(a[href*='review_campaign.php'])");
  if (items.length > 0) {
    items.each((index, element) => {
      const item = $(element);
      const link = item.find("a[href*='review_campaign.php']").first();
      if (link.length > 0) addCampaign(item, link);
    });
    return { campaigns, parsedCount, addedCount };
  }

  $("a[href*='review_campaign.php']").each((index, element) => {
    const link = $(element);
    addCampaign(link, link);
  });

  return { campaigns, parsedCount, addedCount };
}

async function crawlPavlo() {
  logCrawlerStep("pavlo", "pavlo");
  const campaigns = [];
  const seenIds = new Set();
  const urls = getPavloSeedUrls();
  const pagedConfigs = getPavloConfigs();

  try {
    for (const url of urls) {
      const html = await fetchHtml(url, { encoding: "utf-8" });
      const parsed = parsePavloListCampaigns(html, { seenIds });
      campaigns.push(...parsed.campaigns);
      await sleep(700);
    }

    for (const config of pagedConfigs) {
      for (let page = 1; page <= 300; page += 1) {
        const html = await fetchHtml("https://pavlovu.com/review_campaign_list.php", {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          params: {
            keyword_type: "",
            keyword: "",
            period_type: "",
            period_sdate: "",
            period_edate: "",
            orderby: "cp_id desc",
            cp_type: "",
            area_id: "",
            category_id: config.categoryId,
            cp_media: "",
            json: "list",
            page,
          },
          headers: {
            Referer: config.referer,
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        const { campaigns: parsedCampaigns, parsedCount, addedCount } = parsePavloListCampaigns(html, { seenIds });
        campaigns.push(...parsedCampaigns);
        if (parsedCount === 0) {
          break;
        }
        if (addedCount === 0) {
          console.log(`  - pavlo ${config.label} page ${page}: duplicate-only page`);
          break;
        }
        await sleep(250);
      }
    }

    await processCampaignsInBatches("pavlo", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://pavlovu.com/",
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const bodyText = $("body").text();
        const pavloAddressTexts = $(
          ".map_wrap .address, .map_con .address, b.address, .map_wrap b[class*='address']",
        )
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          pavloAddressTexts,
          extractAddressCandidates(cleanText(bodyText)),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
      } catch (error) {
        console.log(`  - pavlo detail enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - pavlo: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - pavlo failed: ${error.message}`);
    throw error;
  }
}
async function crawlSeouloba() {
  logCrawlerStep("seouloba", "seouloba");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = "https://www.seoulouba.co.kr/campaign/ajax/list.ajax.php";
  const categories = [
    "377",
    "378",
    "379",
    "380",
    "381",
    "382",
    "383",
    "384",
    "385",
    "386",
    "387",
    "388",
    "389",
    "390",
    "391",
    "446",
    "448",
    "449",
    "505",
    "510",
  ];

  try {
    for (const category of categories) {
      for (let page = 1; page <= 200; page += 1) {
        throwIfCrawlerAborted();
        const before = campaigns.length;
        const html = await fetchHtml(endpoint, {
          method: "post",
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          data: new URLSearchParams({
            cat: category,
            qq: "",
            q: "",
            q1: "",
            q2: "",
            ar1: "",
            ar2: "",
            sort: "",
            page: String(page),
            more: String(page * 36 + 120),
            rows: "36",
          }).toString(),
          headers: {
            Origin: "https://www.seoulouba.co.kr",
            Referer: `https://www.seoulouba.co.kr/campaign/?cat=${category}`,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            Accept: "*/*",
          },
        });

        const $ = cheerio.load(`<ul>${html || ""}</ul>`);
        let parsedCount = 0;

        $("li.campaign_content").each((index, element) => {
          const item = $(element);
          const link = item.find("a[href*='?c=']").first();
          const href = link.attr("href") || "";
          const match = href.match(/c=(\d+)/);
          if (!match) return;
          parsedCount += 1;

          const id = `so_${match[1]}`;
          if (seenIds.has(id)) return;

          const point =
            cleanText(item.find(".basic_blue").first().text()) ||
            cleanText(item.find(".t_basic").first().text()) ||
            null;
          const dDayText = cleanText(item.find(".d_day").first().text());
          const recruitText = cleanText(item.find(".recruit").first().text());
          const tagText = cleanText(item.find(".icon_tag").first().text());
          const mediaText = item
            .find(".icon_box img")
            .map((_, image) => cleanText($(image).attr("alt") || ""))
            .get()
            .filter(Boolean)
            .join(" ");

          item.find("img,script,style,noscript").remove();
          const full = cleanText(item.text());
          const title =
            cleanText(item.find(".s_campaign_title").first().text()) ||
            cleanText(item.find(".load_title, .tit, strong").first().text()) ||
            cleanText(link.attr("title") || "") ||
            full.split(/\s{2,}/).map(cleanText).filter(isValidTitle)[0];
          if (!title) return;

          const typeText = `${tagText} ${mediaText} ${title} ${full}`;
          let type = "\uBC29\uBB38\uD615";
          if (typeText.includes("\uBC30\uC1A1") || typeText.includes("\uD3EC\uC7A5")) {
            type = "\uBC30\uC1A1\uD615";
          } else if (typeText.includes("\uAD6C\uB9E4")) {
            type = "\uAD6C\uB9E4\uD615";
          } else if (typeText.includes("\uAE30\uC790\uB2E8")) {
            type = "\uAE30\uC790\uB2E8";
          } else if (typeText.includes("\uB9B4\uC2A4")) {
            type = "\uB9B4\uC2A4";
          } else if (typeText.includes("\uD074\uB9BD") || typeText.includes("\uC1FC\uCE20")) {
            type = "\uD074\uB9BD";
          } else if (typeText.includes("\uC778\uC2A4\uD0C0")) {
            type = "\uC778\uC2A4\uD0C0";
          }

          campaigns.push(
            buildCampaign({
              id,
              title,
              url: href.startsWith("http") ? href : `https://www.seoulouba.co.kr${href}`,
              platform: "seouloba",
              platformId: "seouloba",
              point,
              dDay: parseDDay(dDayText || full),
              applyCount: parseNumber(
                ((recruitText || full).match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || "",
              ),
              selectedCount: parseNumber(
                ((recruitText || full).match(/\uBAA8\uC9D1\s*([\d,]+)/) || [])[1] || "",
              ),
              type,
              category: guessCategory(`${title} ${point || ""}`),
            }),
          );
          seenIds.add(id);
        });

        if (parsedCount === 0) {
          break;
        }

        if (campaigns.length === before) {
          console.log(`  - seouloba ${category} page ${page}: duplicate-only page`);
          break;
        }
      }
    }

    const seoulobaDetailTargets = campaigns
      .filter((campaign) => (campaign.dDay ?? 99) <= 1 || (!campaign.locationRaw && !campaign.addressRaw))
      .sort((left, right) => (left.dDay ?? 99) - (right.dDay ?? 99))
      .slice(0, SEOULOBA_DETAIL_ENRICH_LIMIT);

    if (campaigns.length > seoulobaDetailTargets.length) {
      console.log(
        `  - seouloba detail enrich limited to ${seoulobaDetailTargets.length}/${campaigns.length}`,
      );
    }

    await processCampaignsInBatches("seouloba", seoulobaDetailTargets, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: SEOULOBA_DETAIL_TIMEOUT_MS,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://www.seoulouba.co.kr/campaign/",
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const candidateTexts = $(".map_adress .txt_short, .map_adress, .address, .place")
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          candidateTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
      } catch (error) {
        console.log(`  - seouloba location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - seouloba: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - seouloba failed: ${error.message}`);
    throw error;
  }
}
function getRevuCategories() {
  const scope = cleanText(process.env.REVU_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "배송", "배송형", "제품"].includes(scope)) {
    return ["제품"];
  }

  return [...REVU_CATEGORIES];
}

function isRevuProductCategory(item = {}) {
  const categories = Array.isArray(item.category) ? item.category : [item.category];
  return categories.some((category) => cleanText(category) === "제품");
}

function getRevuImageUrl(item = {}) {
  return (
    item.thumbnail ||
    item.thumb ||
    item.image ||
    item.imageUrl ||
    item.campaignData?.thumbnail ||
    item.campaignData?.image ||
    item.campaignData?.imageUrl ||
    ""
  );
}

function mapRevuType(item) {
  if (isRevuProductCategory(item) || item.campaignOptions?.publicReviewerDelivery === "1") return "delivery";
  if (item.media === "clip") return "clip";
  if (item.media === "instagram" && item.campaignOptions?.shortForm === "reels_only") return "reels";
  if (item.media === "instagram") return "instagram";
  if (item.media === "youtube") return "youtube";
  if (item.type === "press") return "reporter";
  return "visit";
}

function getRevuDday(item) {
  const statusText = cleanText(
    [
      item.status,
      item.state,
      item.progress,
      item.campaignStatus,
      item.displayStatus,
      item.requestStatus,
      item.reviewStatus,
      item.campaignData?.status,
      item.campaignData?.state,
    ]
      .filter(Boolean)
      .join(" "),
  );

  if (/마감|종료|완료|closed|ended|finish|finished|expired/i.test(statusText)) {
    return -1;
  }

  const endedOnDday = daysUntilKstDate(
    item.requestEndedOn ||
    item.requestEndOn ||
    item.requestEndAt ||
    item.campaignData?.requestEndedOn ||
    item.campaignData?.requestEndOn ||
    item.campaignData?.requestEndAt,
  );
  if (Number.isFinite(endedOnDday)) {
    return endedOnDday;
  }

  if (Number.isFinite(item.byDeadline)) {
    return item.byDeadline;
  }

  return parseDDay(item.requestEndedOn || "");
}

function loadCachedRevuToken() {
  try {
    if (!fs.existsSync(REVU_AUTH_CACHE_PATH)) return "";
    const raw = JSON.parse(fs.readFileSync(REVU_AUTH_CACHE_PATH, "utf-8"));
    return normalizeBearerToken(raw?.token || "");
  } catch {
    return "";
  }
}

async function refreshRevuAuth({ reason = "token refresh" } = {}) {
  throwIfCrawlerAborted();

  if (!REVU_LOGIN_ID || !REVU_LOGIN_PASSWORD) {
    throw new Error(
      "revu auto-login failed: REVU_LOGIN_ID / REVU_LOGIN_PASSWORD not set in .env",
    );
  }

  const browser = await chromium.launch({ headless: process.env.REVU_HEADLESS !== "0" });
  let context;
  let page;
  const crawlerContext = getActiveCrawlerContext();
  const unregisterBrowserCleanup = crawlerContext?.registerCleanup(async () => {
    await page?.close().catch(() => null);
    await context?.close().catch(() => null);
    await browser.close().catch(() => null);
  });

  try {
    context = await browser.newContext({
      locale: "ko-KR",
      userAgent: HEADERS["User-Agent"],
    });

    let capturedToken = "";

    page = await context.newPage();

    // api.weble.net ?붿껌 ?명꽣?됲듃 ??Authorization ?ㅻ뜑 罹≪쿂
    page.on("request", (request) => {
      if (request.url().includes("api.weble.net") && !capturedToken) {
        const auth = request.headers()["authorization"] || "";
        if (auth.startsWith("Bearer ")) {
          capturedToken = auth;
        }
      }
    });

    console.log(`  - revu auth refresh: ${reason}`);
    await page.goto("https://www.revu.net/login", {
      waitUntil: "domcontentloaded",
      timeout: 45000,
    });

    const emailLocator = page
      .locator('input[type="email"], input[name="email"], input[name="id"]')
      .first();
    const passwordLocator = page.locator('input[type="password"]').first();

    await emailLocator.fill(REVU_LOGIN_ID);
    await passwordLocator.fill(REVU_LOGIN_PASSWORD);

    const submitLocator = page
      .locator('button[type="submit"], input[type="submit"]')
      .filter({ hasText: /로그인|LOGIN|Login/i })
      .first();

    if ((await submitLocator.count()) > 0) {
      await submitLocator.click();
    } else {
      await passwordLocator.press("Enter");
    }

    await page
      .waitForURL((url) => !url.href.includes("/login"), { timeout: 30000 })
      .catch(() => null);

    if (!capturedToken) {
      await page.goto("https://www.revu.net/category/지역", {
        waitUntil: "networkidle",
        timeout: 30000,
      });
      await sleep(3000);
    }

    if (!capturedToken) {
      throw new Error(
        "revu auth refresh failed: Authorization token not captured. 로그인 실패 또는 REVU 페이지 구조 변경 가능성 확인 필요.",
      );
    }

    ensureParentDir(REVU_AUTH_CACHE_PATH);
    fs.writeFileSync(
      REVU_AUTH_CACHE_PATH,
      JSON.stringify({ token: capturedToken, savedAt: new Date().toISOString() }, null, 2),
      "utf-8",
    );

    console.log(`  - revu auth refresh: token captured and cached (${REVU_AUTH_CACHE_PATH})`);
    return capturedToken;
  } finally {
    unregisterBrowserCleanup?.();
    await page?.close().catch(() => null);
    await context?.close().catch(() => null);
    await browser.close().catch(() => null);
  }
}

function buildRevuCampaignFromApiItem(item) {
  if (!item?.id || !item?.item) return null;

  const apiCoords = extractLatLngFromObject(item, "revu_api");
  const imageUrl = getRevuImageUrl(item);

  return buildCampaign({
    id: `revu_${item.id}`,
    title: cleanText(item.item),
    url: `https://www.revu.net/campaign/${item.id}`,
    platform: "revu",
    platformId: "revu",
    dDay: getRevuDday(item),
    applyCount: item.campaignStats?.requestCount || 0,
    selectedCount: item.reviewerLimit || 3,
    point:
      item.campaignData?.reward ||
      (item.campaignData?.point ? `${item.campaignData.point}P` : null),
    type: mapRevuType(item),
    category:
      Array.isArray(item.category) && item.category.length > 0
        ? item.category[0]
        : guessCategory(item.item),
    ...(imageUrl ? { imageUrl } : {}),
    ...(apiCoords
      ? {
        lat: apiCoords.lat,
        lng: apiCoords.lng,
        coordinateSource: apiCoords.coordinateSource,
      }
      : {}),
  });
}

async function crawlRevu() {
  logCrawlerStep("revu", "revu");

  // 우선순위: .env 직접 지정 -> 캐시 토큰 -> 자동 로그인
  let authorization = REVU_AUTHORIZATION || loadCachedRevuToken();

  if (!authorization) {
    console.log("  - revu: cached token missing. trying auto-login...");
    authorization = await refreshRevuAuth({ reason: "initial login" });
  }

  try {
    const seenIds = new Set();
    const campaigns = [];

    for (const cat of getRevuCategories()) {
      let page = 1;
      let totalPages = 1;

      while (page <= totalPages) {
        let payload;
        try {
          payload = await fetchRevuPage({ authorization, cat, page });
        } catch (error) {
          if (error?.response?.status === 401) {
            console.log("  - revu: 401 detected. refreshing token...");
            authorization = await refreshRevuAuth({ reason: "token expired (401)" });
            payload = await fetchRevuPage({ authorization, cat, page });
          } else {
            throw error;
          }
        }

        const items = Array.isArray(payload.items) ? payload.items : [];
        totalPages = Math.max(
          1,
          Math.ceil((payload.total || items.length || 0) / (payload.limit || 35)),
        );

        for (const item of items) {
          const campaign = buildRevuCampaignFromApiItem(item);
          if (!campaign) continue;

          const id = campaign.id;
          if (seenIds.has(id)) continue;
          if (campaign.dDay < 0) continue;
          seenIds.add(id);
          campaigns.push(campaign);
        }

        if (items.length === 0) break;
        page += 1;
        await sleep(500);
      }
    }

    await processCampaignsInBatches("revu", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://www.revu.net/",
            Authorization: authorization,
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const candidateTexts = $("span.desc.address, .address, .place, [data-clipboard-text]")
          .map((_, element) => cleanAddressText($(element).text()))
          .get()
          .concat(
            $("[data-clipboard-text]")
              .map((_, element) => cleanAddressText($(element).attr("data-clipboard-text") || ""))
              .get(),
          )
          .filter(Boolean);
        const renderedMapTexts = $("render-map")
          .closest(".map")
          .find("span.desc.address, [data-clipboard-text]")
          .map((_, element) => cleanAddressText($(element).text() || $(element).attr("data-clipboard-text") || ""))
          .get();
        const extractedAddress = pickBestLocationText(
          renderedMapTexts,
          candidateTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
      } catch (error) {
        console.log(`  - revu location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - revu: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - revu failed: ${error.message}`);
    throw error;
  }
}

async function crawlGangnam() {
  logCrawlerStep("gangnam", "gangnam");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = `${GANGNAM_BASE_URL}/theme/go/_list_cmp_tpl.php`;
  const gangnamScope = cleanText(process.env.GANGNAM_LIST_SCOPE || "").toLowerCase();
  const categories = ["delivery", "shipping", "product", "products", "배송", "배송형", "제품", "30"].includes(
    gangnamScope,
  )
    ? ["30"]
    : ["20", "30", "40"];

  try {
    for (const category of categories) {
      for (let page = 1; page <= 200; page += 1) {
        const before = campaigns.length;
        const html = await fetchHtml(endpoint, {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            ca: category,
            rpage: page,
            row_num: 28,
          },
          headers: {
            Referer: `https://xn--939au0g4vj8sq.net/cp/?ca=${category}`,
            "X-Requested-With": "XMLHttpRequest",
            Accept: "text/html, */*; q=0.01",
            ...(GANGNAM_COOKIE ? { Cookie: GANGNAM_COOKIE } : {}),
          },
        });

        const parsedCampaigns = parseGangnamListCampaigns(html, { category, seenIds });
        campaigns.push(...parsedCampaigns);
        const parsedCount = parsedCampaigns.parsedCount || 0;

        if (parsedCount === 0) {
          break;
        }

        if (campaigns.length === before) {
          console.log(`  - gangnam ${category} page ${page}: duplicate-only page`);
          break;
        }
      }
    }

    await processCampaignsInBatches("gangnam", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://xn--939au0g4vj8sq.net/cp/",
            ...(GANGNAM_COOKIE ? { Cookie: GANGNAM_COOKIE } : {}),
          },
        });

        const $ = cheerio.load(html);
        const now = new Date();
        const detailState = applyCampaignDetailState(campaign, html, $, now);
        const provisionText = extractGangnamProvisionFromDetail($);
        const gangnamDeadlineInfo = extractGangnamApplicationDeadlineInfo($, detailState.bodyText, now);
        const shouldEnrichLocation = campaign.type !== "delivery";
        const mapSiblingAddressTexts = shouldEnrichLocation
          ? $("#cont_map")
            .nextAll("div")
            .map((_, element) => cleanAddressText($(element).text()))
            .get()
          : [];
        const candidateTexts = shouldEnrichLocation
          ? $("dd > div:not(#cont_map), .address, .place")
            .map((_, element) => cleanAddressText($(element).text()))
            .get()
          : [];
        const extractedAddress = shouldEnrichLocation
          ? pickBestLocationText(
            mapSiblingAddressTexts,
            candidateTexts,
            extractAddressCandidates(cleanText($("body").text())),
          )
          : "";
        const coords = shouldEnrichLocation ? extractLatLngFromHtml(html) : null;
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (gangnamDeadlineInfo.sourceStartedAt) {
          campaign.sourceStartedAt = gangnamDeadlineInfo.sourceStartedAt;
        }
        if (gangnamDeadlineInfo.sourceEndedAt) {
          campaign.sourceEndedAt = gangnamDeadlineInfo.sourceEndedAt;
          campaign.deadlineSource = gangnamDeadlineInfo.deadlineSource;
        }
        if (Number.isFinite(gangnamDeadlineInfo.dDay)) {
          campaign.dDay = gangnamDeadlineInfo.dDay;
          if (gangnamDeadlineInfo.dDay < 0) {
            closeCampaignFromDetail(campaign, "gangnam_application_deadline_past", gangnamDeadlineInfo.dDay);
          } else if (campaign.closedReason === "detail_deadline_past") {
            campaign.status = "open";
            campaign.closedReason = null;
          }
        }
        applyGangnamDetailLocationEnrichment(campaign, { extractedAddress, coords });
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (provisionText) {
          campaign.point = provisionText;
        }
      } catch (error) {
        console.log(`  - gangnam location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - gangnam: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - gangnam failed: ${error.message}`);
    return [];
  }
}

const POPOMON_BASE_URL = "https://popomon.com";
const POPOMON_LIST_CONFIGS = [
  {
    label: "visiting",
    referer:
      `${POPOMON_BASE_URL}/next/campaign?searchAlign=latest&bigRecruitType=Lvisiting&recruitType=visiting&interestsFilter=ALL&&pageNum=1&snsSubFilter=`,
    params: {
      searchAlign: "latest",
      bigRecruitType: "Lvisiting",
      recruitType: "visiting",
      interestsFilter: "ALL",
      pageNum: 1,
      snsSubFilter: "",
    },
    type: "visit",
  },
  {
    label: "shipping",
    referer:
      `${POPOMON_BASE_URL}/next/campaign?searchAlign=latest&bigRecruitType=Pshipping&recruitType=shipping&interestsFilter=ALL&&pageNum=1&snsSubFilter=`,
    params: {
      searchAlign: "latest",
      bigRecruitType: "Pshipping",
      recruitType: "shipping",
      interestsFilter: "ALL",
      pageNum: 1,
      snsSubFilter: "",
    },
    type: "delivery",
  },
  {
    label: "reporting",
    referer:
      `${POPOMON_BASE_URL}/next/campaign?searchAlign=latest&bigRecruitType=Lvisiting&recruitType=reporting&interestsFilter=ALL&&pageNum=1&snsSubFilter=`,
    params: {
      searchAlign: "latest",
      bigRecruitType: "Lvisiting",
      recruitType: "reporting",
      interestsFilter: "ALL",
      pageNum: 1,
      snsSubFilter: "",
    },
    type: "reporter",
  },
];

function getPopomonConfigs() {
  const scope = cleanText(process.env.POPOMON_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488", "pshipping"].includes(scope)) {
    return POPOMON_LIST_CONFIGS.filter((config) => config.label === "shipping");
  }
  return [...POPOMON_LIST_CONFIGS];
}

function getPopomonUrl(href = "") {
  try {
    return new URL(href, POPOMON_BASE_URL).toString();
  } catch {
    return "";
  }
}

function getPopomonImageUrl(src = "") {
  const raw = cleanText(src);
  if (!raw) return "";

  try {
    const url = new URL(raw, POPOMON_BASE_URL);
    const originalUrl = url.searchParams.get("url");
    if (originalUrl) return originalUrl;
    return url.toString();
  } catch {
    return "";
  }
}

function parsePopomonListCampaigns(html, { config, seenIds = new Set() } = {}) {
  const $ = cheerio.load(html || "");
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  $("a[href*='/next/campaign/']").each((index, element) => {
    const link = $(element);
    const href = link.attr("href") || "";
    const match = href.match(/\/next\/campaign\/(\d+)/);
    if (!match) return;

    const id = `pm_${match[1]}`;
    if (parsedIds.has(id)) return;

    const block = link.find("li").first().length ? link.find("li").first() : link;
    const rawTitle = cleanText(block.find("h3").first().text()) || cleanText(link.attr("title") || "");
    if (!rawTitle) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    const { title, placeName, locationHint } = parsePopomonTitle(rawTitle);
    const provisionBlock = block
      .find("p")
      .filter((_, element) => /\d+\s*일\s*남음/.test(cleanText($(element).text())))
      .first();
    const dDayText = cleanText(provisionBlock.find("span").first().text());
    const provisionClone = provisionBlock.clone();
    provisionClone.find("span").remove();
    const provision = cleanText(provisionClone.text());
    const countText = cleanText(block.text());
    const countMatch = countText.match(/\uC2E0\uCCAD\s*([\d,]+)\s*\/\s*([\d,]+)/);
    const imageSrc =
      block.find("img[src*='CAMPAIGN_THUMB'], img[src*='_next/image'], img[data-nimg='fill'], img").first().attr("src") || "";

    const type = config?.type || (countText.includes("\uBC30\uC1A1\uD615") ? "delivery" : "visit");
    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getPopomonUrl(href),
        platform: "popomon",
        platformId: "popomon",
        dDay: parseDDay(dDayText || countText),
        applyCount: parseNumber(countMatch?.[1] || ""),
        selectedCount: parseNumber(countMatch?.[2] || ""),
        point: provision || null,
        type,
        locationRaw: type === "delivery" ? "" : locationHint,
        placeName,
        category: guessCategory(`${title} ${provision || ""}`),
        ...(imageSrc ? { imageUrl: getPopomonImageUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return { campaigns, parsedCount, addedCount };
}

async function crawlPopomon() {
  logCrawlerStep("popomon", "popomon");
  const campaigns = [];
  const seenIds = new Set();
  const endpoint = `${POPOMON_BASE_URL}/api_p/campaign/fetch_getcampaignlist`;
  const configs = getPopomonConfigs();

  try {
    for (const config of configs) {
      let totalCount = null;
      const pageSize = 12;

      for (let pageOffset = 0; pageOffset <= 3600; pageOffset += pageSize) {
        const payload = await fetchJson(endpoint, {
          method: "post",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            ...config.params,
            pageNum: pageOffset,
          },
          headers: {
            Origin: "https://popomon.com",
            Referer: config.referer,
            "Content-Length": "0",
            ...(POPOMON_COOKIE ? { Cookie: POPOMON_COOKIE } : {}),
          },
          data: "",
        });

        const items = Array.isArray(payload?.data?.contentsData) ? payload.data.contentsData : [];
        if (items.length === 0) {
          if (pageOffset === 0) {
            continue;
          }
          break;
        }

        if (totalCount === null) {
          const parsedTotalCount = parseNumber(payload?.data?.campCount);
          totalCount = parsedTotalCount > 0 ? parsedTotalCount : null;
        }

        let addedOnPage = 0;

        for (const item of items) {
          if (!item?.C_idx || !item?.C_title) continue;

          const id = `pm_${item.C_idx}`;
          if (seenIds.has(id)) continue;

          const rawTitle = cleanText(item.C_title);
          const { title, placeName, locationHint } = parsePopomonTitle(rawTitle);
          const sourceEndedAt = parseSourceDate(item.C_regi_end_date || "");
          const endDateDDay = sourceEndedAt ? daysUntilKstDate(sourceEndedAt) : null;
          const apiDDay = parseDDayOrDate(item.C_regi_end_date_count);
          campaigns.push(
            buildCampaign({
              id,
              title,
              url: `https://popomon.com/next/campaign/${item.C_idx}`,
              platform: "popomon",
              platformId: "popomon",
              dDay: Number.isFinite(apiDDay) && !isUnknownDDay(apiDDay)
                  ? apiDDay
                  : Number.isFinite(endDateDDay)
                    ? endDateDDay
                    : parseDDay(item.C_regi_end_date || ""),
              applyCount: parseNumber(item.C_volunteer_count),
              selectedCount: parseNumber(item.C_choice_count),
              point: cleanText(item.transformedPrice || item.C_provision || ""),
              type:
                config.type === "visit" && String(item.CS_type || "").includes("INSTA")
                  ? "instagram"
                  : config.type,
              locationRaw: locationHint,
              placeName,
              sourceStartedAt: parseSourceDate(item.C_regi_start_date || ""),
              sourceEndedAt,
              category: guessCategory(`${title} ${cleanText(item.C_provision || "")}`),
            }),
          );
          seenIds.add(id);
          addedOnPage += 1;
        }

        if (addedOnPage === 0) {
          console.log(`  - popomon ${config.label} offset ${pageOffset}: duplicate-only page`);
          break;
        }

        if (totalCount && pageOffset + items.length >= totalCount) {
          break;
        }
      }
    }

    const sortedPopomonCampaigns = [...campaigns]
      .sort((left, right) => {
        if ((left.dDay ?? 999) !== (right.dDay ?? 999)) return (left.dDay ?? 999) - (right.dDay ?? 999);
        return (left.applyCount ?? 0) - (right.applyCount ?? 0);
      });
    const popomonDetailTargets = POPOMON_DETAIL_ENRICH_LIMIT > 0
      ? sortedPopomonCampaigns.slice(0, POPOMON_DETAIL_ENRICH_LIMIT)
      : sortedPopomonCampaigns;

    if (POPOMON_DETAIL_ENRICH_LIMIT > 0 && campaigns.length > popomonDetailTargets.length) {
      console.log(
        `  - popomon detail enrich limited to ${popomonDetailTargets.length}/${campaigns.length} campaigns`,
      );
    }

    await processCampaignsInBatches("popomon", popomonDetailTargets, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://popomon.com/next/campaign",
            ...(POPOMON_COOKIE ? { Cookie: POPOMON_COOKIE } : {}),
          },
        });

        applyPopomonDetailEnrichment(campaign, extractPopomonDetailEnrichment(html));
      } catch (error) {
        console.log(`  - popomon location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    const renderedDetailCandidates = campaigns.filter((campaign) => (
      campaign.type !== "delivery" &&
      (!campaign.addressRaw || !hasUsableCoordinates(campaign))
    ));
    const renderedDetailTargets = POPOMON_RENDERED_DETAIL_ENRICH_LIMIT > 0
      ? renderedDetailCandidates.slice(0, POPOMON_RENDERED_DETAIL_ENRICH_LIMIT)
      : renderedDetailCandidates;
    if (renderedDetailTargets.length) {
      if (renderedDetailTargets.length !== renderedDetailCandidates.length) {
        console.log(
          `  - popomon rendered detail enrich limited to ${renderedDetailTargets.length}/${renderedDetailCandidates.length}`,
        );
      }
      await processCampaignsInBatches("popomon-rendered", renderedDetailTargets, async (campaign) => {
        if (campaign.addressRaw && hasUsableCoordinates(campaign)) return;

        try {
          const renderedHtml = await fetchRenderedHtml(campaign.url, {
            timeoutMs: POPOMON_RENDERED_DETAIL_TIMEOUT_MS,
            scrollSteps: 1,
            waitAfterLoadMs: 1500,
            referer: "https://popomon.com/next/campaign",
            headers: {
              ...(POPOMON_COOKIE ? { Cookie: POPOMON_COOKIE } : {}),
            },
          });
          applyPopomonDetailEnrichment(campaign, extractPopomonDetailEnrichment(renderedHtml));
        } catch (error) {
          console.log(`  - popomon rendered enrich failed (${campaign.id}): ${error.message}`);
        }
      }, {
        batchSize: POPOMON_RENDERED_DETAIL_ENRICH_CONCURRENCY,
        batchDelayMs: 250,
      });
    }

    console.log(`  - popomon: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - popomon failed: ${error.message}`);
    throw error;
  }
}

const COMEPLAY_BASE_URL = "https://www.cometoplay.kr";
const COMEPLAY_LIST_CONFIGS = [
  { categoryId: "001", type: "visit" },
  { categoryId: "002", type: "delivery" },
  { categoryId: "004", type: "reporter" },
];

function getComeplayConfigs() {
  const scope = cleanText(process.env.COMEPLAY_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488", "002"].includes(scope)) {
    return COMEPLAY_LIST_CONFIGS.filter((config) => config.categoryId === "002");
  }
  return [...COMEPLAY_LIST_CONFIGS];
}

function getComeplayUrl(href = "") {
  try {
    return new URL(href, `${COMEPLAY_BASE_URL}/item_list.php`).toString();
  } catch {
    return "";
  }
}

function parseComeplayListCampaigns(html, { config, seenIds = new Set() } = {}) {
  const $ = cheerio.load(html || "");
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  $("a[href*='item.php?it_id='], a[href*='item_view.php?it_id=']").each((index, element) => {
    const link = $(element);
    const href = link.attr("href") || "";
    const match = href.match(/it_id=(\d+)/);
    if (!match) return;

    const id = `cply_${match[1]}`;
    if (parsedIds.has(id)) return;

    const item = link.closest("li, .item_li, .item_box, .gallery_item, .item_box_list li");
    const block = item.length ? item : link.parent();
    const title = cleanText(block.find(".it_name").first().text()) || cleanText(link.attr("title") || link.text());
    if (!title) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    const desc = cleanText(block.find(".it_description").first().text());
    const listProvision = normalizeProvisionText(desc);
    const meta = cleanText(block.find(".option_re").first().text());
    const full = cleanText(`${title} ${desc} ${meta}`);
    const imageSrc = block.find(".thumb img.it_img, img.it_img, .thumb img, img").first().attr("src") || "";

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getComeplayUrl(href),
        platform: "comeplay",
        platformId: "comeplay",
        dDay: parseDDay(full),
        applyCount: parseNumber((full.match(/\uC2E0\uCCAD\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber((full.match(/\uBAA8\uC9D1\s*([\d,]+)/) || [])[1] || ""),
        point: listProvision || null,
        type: config?.type || "visit",
        category: guessCategory(`${title} ${desc}`),
        ...(imageSrc ? { imageUrl: getComeplayUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return {
    campaigns,
    parsedCount,
    addedCount,
  };
}

async function crawlComeplay() {
  logCrawlerStep("comeplay", "comeplay");
  const campaigns = [];
  const seenIds = new Set();
  const configs = getComeplayConfigs();

  try {
    for (const config of configs) {
      let totalPages = null;

      for (let page = 1; page <= 300; page += 1) {
        const html = await fetchHtml(`${COMEPLAY_BASE_URL}/item_list.php`, {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            category_id: config.categoryId,
            sst: "",
            sod: "",
            page,
          },
          headers: {
            Referer: `${COMEPLAY_BASE_URL}/item_list.php?category_id=${config.categoryId}`,
          },
        });

        const $ = cheerio.load(html);
        totalPages = Math.max(totalPages || 1, parseLastPageFromPaging($));
        const parsed = parseComeplayListCampaigns(html, { config, seenIds });
        campaigns.push(...parsed.campaigns);

        if (parsed.parsedCount === 0) {
          break;
        }

        if (parsed.addedCount === 0) {
          console.log(`  - comeplay ${config.categoryId} page ${page}: duplicate-only page`);
          break;
        }

        if (totalPages && page >= totalPages) {
          break;
        }
      }
    }

    await processCampaignsInBatches("comeplay", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://www.cometoplay.kr/",
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const detailProvision = extractComeplayProvisionFromDetail($);
        const infoAddressTexts = $("li.info")
          .map((_, element) => {
            const clone = $(element).clone();
            clone.find("#map, script, style").remove();
            return cleanAddressText(clone.text());
          })
          .get();
        const candidateTexts = $(".address, .place")
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          infoAddressTexts,
          candidateTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
        if (detailProvision) {
          campaign.point = detailProvision;
          campaign.category = guessCategory(`${campaign.title} ${detailProvision}`);
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
      } catch (error) {
        console.log(`  - comeplay location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - comeplay: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - comeplay failed: ${error.message}`);
    throw error;
  }
}

const TBLE_BASE_URL = "https://tble.kr";
const TBLE_LIST_CONFIGS = [
  { categoryType: "l", type: "visit" },
  { categoryType: "p", type: "delivery" },
  { categoryType: "r", type: "reporter" },
  { categoryType: "c", type: "purchase" },
];

function getTbleConfigs() {
  const scope = cleanText(process.env.TBLE_LIST_SCOPE || "").toLowerCase();
  if (["delivery", "shipping", "product", "products", "\uBC30\uC1A1", "\uBC30\uC1A1\uD615", "\uC81C\uD488", "p"].includes(scope)) {
    return TBLE_LIST_CONFIGS.filter((config) => config.categoryType === "p");
  }
  return [...TBLE_LIST_CONFIGS];
}

function getTbleUrl(href = "") {
  try {
    return new URL(href, `${TBLE_BASE_URL}/category.php`).toString();
  } catch {
    return "";
  }
}

function parseTbleListCampaigns(html, { config, seenIds = new Set() } = {}) {
  const $ = cheerio.load(html || "");
  const campaigns = [];
  const parsedIds = new Set();
  let parsedCount = 0;
  let addedCount = 0;

  $("a[href*='view.php?cp_id=']").each((index, element) => {
    const link = $(element);
    const href = link.attr("href") || "";
    const match = href.match(/cp_id=(\d+)/);
    if (!match) return;

    const id = `tble_${match[1]}`;
    if (parsedIds.has(id)) return;

    const card = link.closest(".item, li, .list_item, .campaign_item, .box");
    const block = card.length ? card : link.parent();
    const title = cleanText(block.find(".t2").first().text()) || cleanText(link.attr("title") || link.text());
    if (!title) return;

    parsedIds.add(id);
    parsedCount += 1;
    if (seenIds.has(id)) return;

    const desc = cleanText(block.find(".t3").first().text());
    const people = cleanText(block.find(".t4").first().text());
    const remain = cleanText(block.find(".ps_remain").first().text());
    const full = cleanText(`${title} ${desc} ${people} ${remain}`);
    const imageSrc = block.find(".img a[href*='view.php'] img, a[href*='view.php'] img").first().attr("src") || "";

    let type = config?.type || "visit";
    if (type === "visit" && block.find(".sns_img.insta").length > 0) {
      type = "instagram";
    } else if (type === "visit" && /\b릴스\b/.test(full)) {
      type = "reels";
    }

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: getTbleUrl(href),
        platform: "tble",
        platformId: "tble",
        dDay: parseDDay(full),
        applyCount: parseNumber((people.match(/신청\s*([\d,]+)/) || [])[1] || ""),
        selectedCount: parseNumber((people.match(/모집\s*([\d,]+)/) || [])[1] || ""),
        point: desc || null,
        type,
        category: guessCategory(`${title} ${desc}`),
        ...(imageSrc ? { imageUrl: getTbleUrl(imageSrc) } : {}),
      }),
    );
    seenIds.add(id);
    addedCount += 1;
  });

  return {
    campaigns,
    parsedCount,
    addedCount,
  };
}

async function crawlTble() {
  logCrawlerStep("tble", "tble");
  const campaigns = [];
  const seenIds = new Set();
  const configs = getTbleConfigs();

  try {
    for (const config of configs) {
      let totalPages = null;

      for (let page = 1; page <= 300; page += 1) {
        const html = await fetchHtml("https://tble.kr/category.php", {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 3,
          retryDelayMs: 1500,
          params: {
            type: config.categoryType,
            page,
          },
          headers: {
            Referer: `https://tble.kr/category.php?type=${config.categoryType}`,
          },
        });

        const $ = cheerio.load(html);
        if (page === 1) {
          totalPages = parseLastPageFromPaging($, ".paging a[href*='page='], .page a[href*='page=']");
        }
        const parsed = parseTbleListCampaigns(html, { config, seenIds });
        campaigns.push(...parsed.campaigns);

        if (parsed.parsedCount === 0) {
          break;
        }

        if (parsed.addedCount === 0) {
          console.log(`  - tble ${config.categoryType} page ${page}: duplicate-only page`);
          break;
        }

        if (totalPages && page >= totalPages) {
          break;
        }
      }
    }

    await processCampaignsInBatches("tble", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: "https://tble.kr/",
          },
        });

        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const candidateTexts = $('div[style*="min-width: 170px"], .address, .place')
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          candidateTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
      } catch (error) {
        console.log(`  - tble location enrich failed (${campaign.id}): ${error.message}`);
      }
    });

    console.log(`  - tble: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - tble failed: ${error.message}`);
    throw error;
  }
}

const RINGBLE_BASE_URL = "https://www.ringble.co.kr";
const RINGBLE_VISIT_CATEGORY_ID = "832";

function getRingbleUrl(href = "") {
  try {
    return new URL(href, RINGBLE_BASE_URL).toString();
  } catch {
    return "";
  }
}

function parseRingbleLastPage($) {
  let maxPage = 1;

  $(".page_now a[href*='start='], .page_nomal a[href*='start='], a[href*='category.php'][href*='start=']").each((_, element) => {
    const href = $(element).attr("href") || "";
    const match = href.match(/[?&]start=(\d+)/);
    if (!match) return;

    const page = Number(match[1]);
    if (Number.isFinite(page) && page > maxPage) {
      maxPage = page;
    }
  });

  return maxPage;
}

function parseRingbleDateToken(match) {
  const [, rawYear, rawMonth, rawDay] = match;
  const year = rawYear.length === 2
    ? (Number(rawYear) >= 70 ? 1900 : 2000) + Number(rawYear)
    : Number(rawYear);
  const month = Number(rawMonth);
  const day = Number(rawDay);
  if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) return null;

  const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}T00:00:00+09:00`;
  const parsed = Date.parse(iso);
  return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
}

function extractRingbleDateTokens(text = "") {
  const normalized = cleanText(text);
  const datePattern = /(\d{2}|\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/g;
  return [...normalized.matchAll(datePattern)]
    .map((match) => parseRingbleDateToken(match))
    .filter(Boolean);
}

function parseRingbleKoreanDateRange(text = "", now = new Date()) {
  const tokens = extractRingbleDateTokens(text);
  if (tokens.length < 2) return null;

  return {
    sourceStartedAt: tokens[0],
    sourceEndedAt: tokens[1],
    dDay: daysUntilKstDate(tokens[1], now),
  };
}

function isRingbleDDayText(text = "") {
  return /(?:오늘\s*마감|\d+\s*일\s*남음|D\s*-?\s*\d+|마감|종료|완료)/i.test(cleanText(text));
}

function parseRingbleDDay(text = "") {
  const normalized = cleanText(text);
  if (!normalized) return 99;
  if (/오늘\s*마감/i.test(normalized)) return 0;
  return parseDDay(normalized);
}

function parseRingbleListCampaigns(html, { categoryId = RINGBLE_VISIT_CATEGORY_ID } = {}) {
  const $ = cheerio.load(html);
  const groups = new Map();

  $(`a[href*='detail.php?number='][href*='category=${categoryId}']`).each((_, element) => {
    const link = $(element);
    const href = link.attr("href") || "";
    const match = href.match(/[?&]number=(\d+)/);
    if (!match) return;

    const id = `ringble_${match[1]}`;
    const group = groups.get(id) || {
      id,
      url: getRingbleUrl(href),
      title: "",
      dDayText: "",
      imageUrl: "",
      text: "",
    };

    const text = cleanText(link.text());
    const imageSrc = link.find("img[src]").first().attr("src")
      || link.closest("td, li, div").find("img[src]").first().attr("src")
      || "";

    if (imageSrc && !group.imageUrl) {
      group.imageUrl = getRingbleUrl(imageSrc);
    }
    if (text) {
      group.text = cleanText(`${group.text} ${text}`);
    }
    if (text && isRingbleDDayText(text) && !group.dDayText) {
      group.dDayText = text;
    }
    if (
      text
      && !group.title
      && isValidTitle(text)
      && !isRingbleDDayText(text)
      && !/^(?:상세보기|자세히|신청하기)$/i.test(text)
    ) {
      group.title = text;
    }

    groups.set(id, group);
  });

  return [...groups.values()]
    .filter((group) => group.title && group.url)
    .map((group) => {
      const titleLocationHint = parseRegionalPlaceTitle(group.title);
      return buildCampaign({
        id: group.id,
        title: group.title,
        url: group.url,
        platform: "링블",
        platformId: "ringble",
        dDay: parseRingbleDDay(group.dDayText || group.text),
        applyCount: 0,
        selectedCount: 3,
        point: null,
        type: "visit",
        category: guessCategory(group.title),
        locationRaw: titleLocationHint.locationHint,
        placeName: titleLocationHint.placeName,
        imageUrl: group.imageUrl || "",
      });
    });
}

function getRingbleDetailCellText($, labelPattern) {
  let result = "";

  $("tr").each((_, element) => {
    const cells = $(element).find("th, td");
    if (cells.length < 2) return;

    const label = cleanText(cells.eq(0).text()).replace(/\s+/g, "");
    if (!labelPattern.test(label)) return;

    const clone = cells.eq(1).clone();
    clone.find("script, style, noscript").remove();
    result = cleanText(clone.text());
    return false;
  });

  return result;
}

function isRingbleProvisionCandidate(text = "") {
  const normalized = normalizeProvisionText(text);
  if (!normalized) return false;
  if (/^(?:주소|위치|장소|신청|모집|리뷰\s*등록|당첨자)\b/i.test(normalized)) return false;
  if (/(?:모집\s*기간|당첨자\s*발표|리뷰\s*등록\s*기간|리뷰어\s*신청하기|신청\s*[\d,]+\s*\/\s*모집\s*[\d,]+)/.test(normalized)) {
    return false;
  }
  return /(?:식사권|이용권|상품권|체험권|제공|무료|협찬|포인트|원|만원|메뉴|세트)/i.test(normalized);
}

function extractRingbleProvisionFromDetail($) {
  const candidates = [];

  $("tr").each((_, element) => {
    const cells = $(element).find("th, td");
    if (cells.length < 2) return;

    const label = cleanText(cells.eq(0).text());
    if (!isProvisionLabel(label)) return;

    const clone = cells.eq(1).clone();
    clone.find("script, style, noscript").remove();
    candidates.push(clone.text());
  });

  $("td.font11, .font11").each((_, element) => {
    candidates.push($(element).text());
  });

  return [...new Set(candidates)]
    .map((value) => normalizeProvisionText(value))
    .find((value) => isRingbleProvisionCandidate(value)) || "";
}

function extractRingbleLocationUrl($) {
  const href = $("#descURL a[href]").first().attr("href")
    || $("a[href*='naver.me'], a[href*='map.naver.com'], a[href*='naver.com']").first().attr("href")
    || "";
  return /^https?:\/\//i.test(href) ? href : "";
}

function applyRingbleDetailEnrichment(campaign, html, now = new Date()) {
  const $ = cheerio.load(html || "");
  const { bodyText } = applyCampaignDetailState(campaign, html, $, now, {
    applyDeadline: false,
    closePastDeadline: false,
    detectClosedState: false,
  });

  const title = cleanText($(".detail_page_title").first().text());
  if (title && isValidTitle(title)) {
    campaign.title = title;
  }

  const titleLocationHint = parseRegionalPlaceTitle(campaign.title);
  if (titleLocationHint.locationHint && !campaign.locationRaw) {
    campaign.locationRaw = titleLocationHint.locationHint;
  }
  if (titleLocationHint.placeName && !campaign.placeName) {
    campaign.placeName = titleLocationHint.placeName;
  }

  const countText = cleanText(`${$(".detail_list_mem_total_wrap").text()} ${bodyText}`);
  const countMatch = countText.match(/신청\s*([\d,]+)\s*\/\s*모집\s*([\d,]+)/);
  if (countMatch) {
    campaign.applyCount = parseNumber(countMatch[1]);
    campaign.selectedCount = parseNumber(countMatch[2]);
  }

  const periodText = cleanText($("#10").first().text())
    || getRingbleDetailCellText($, /(?:모집기간|신청기간|캠페인기간)/);
  const deadlineInfo = parseRingbleKoreanDateRange(periodText, now);
  if (deadlineInfo) {
    campaign.sourceStartedAt = deadlineInfo.sourceStartedAt;
    campaign.sourceEndedAt = deadlineInfo.sourceEndedAt;
    if (Number.isFinite(deadlineInfo.dDay)) {
      campaign.dDay = deadlineInfo.dDay;
      if (deadlineInfo.dDay < 0) {
        closeCampaignFromDetail(campaign, "ringble_deadline_past", deadlineInfo.dDay);
      }
    }
  }

  const provision = extractRingbleProvisionFromDetail($);
  if (provision) {
    campaign.point = provision;
    campaign.category = guessCategory(`${campaign.title} ${provision}`);
  }

  const locationUrl = extractRingbleLocationUrl($);
  if (locationUrl) {
    campaign.sourceLocationUrl = locationUrl;
  }

  const exactAddress = pickBestLocationText(
    getRingbleDetailCellText($, /(?:방문주소|주소|위치|장소)/),
    $(".address, .place, #map, #descURL").map((_, element) => cleanAddressText($(element).text())).get(),
    extractAddressCandidates(bodyText),
  );
  if (exactAddress) {
    campaign.locationRaw = exactAddress;
    campaign.addressRaw = exactAddress;
  }

  const coords = extractLatLngFromHtml(html);
  if (coords) {
    campaign.lat = coords.lat;
    campaign.lng = coords.lng;
    campaign.coordinateSource = coords.coordinateSource || "html";
  }

  return campaign;
}

async function crawlRingble() {
  logCrawlerStep("ringble", "ringble");
  const campaigns = [];
  const seenIds = new Set();
  let totalPages = null;

  try {
    for (let page = 1; page <= 300; page += 1) {
      const html = await fetchHtml(`${RINGBLE_BASE_URL}/category.php`, {
        encoding: "utf-8",
        timeoutMs: 25000,
        attempts: 3,
        retryDelayMs: 1500,
        params: {
          ...(page > 1 ? { start: page } : {}),
          category: RINGBLE_VISIT_CATEGORY_ID,
        },
        headers: {
          Referer: `${RINGBLE_BASE_URL}/category.php?category=${RINGBLE_VISIT_CATEGORY_ID}`,
        },
      });

      const $ = cheerio.load(html);
      totalPages = Math.max(totalPages || 1, parseRingbleLastPage($));
      const pageCampaigns = parseRingbleListCampaigns(html, { categoryId: RINGBLE_VISIT_CATEGORY_ID });
      let addedOnPage = 0;

      for (const campaign of pageCampaigns) {
        if (seenIds.has(campaign.id)) continue;
        campaigns.push(campaign);
        seenIds.add(campaign.id);
        addedOnPage += 1;
      }

      if (pageCampaigns.length === 0) {
        break;
      }

      if (addedOnPage === 0) {
        console.log(`  - ringble page ${page}: duplicate-only page`);
        break;
      }

      if (totalPages && page >= totalPages) {
        break;
      }
    }

    await processCampaignsInBatches("ringble", campaigns, async (campaign) => {
      try {
        const html = await fetchHtml(campaign.url, {
          encoding: "utf-8",
          timeoutMs: 25000,
          attempts: 2,
          retryDelayMs: 1200,
          headers: {
            Referer: `${RINGBLE_BASE_URL}/category.php?category=${RINGBLE_VISIT_CATEGORY_ID}`,
          },
        });

        applyRingbleDetailEnrichment(campaign, html);
      } catch (error) {
        console.log(`  - ringble detail enrich failed (${campaign.id}): ${error.message}`);
      }
    }, { batchDelayMs: 250 });

    console.log(`  - ringble: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - ringble failed: ${error.message}`);
    throw error;
  }
}

function mapChvuType(text = "") {
  const normalized = cleanText(text);
  if (/\bdelivery\b|shipping|배송형|배송/i.test(normalized)) return "delivery";
  if (/\breporter\b|reporting|기자단/i.test(normalized)) return "reporter";
  if (/\bpurchase\b|구매형|구매/i.test(normalized)) return "purchase";
  if (/\breels?\b/i.test(normalized)) return "reels";
  if (/\bclips?\b/i.test(normalized)) return "clip";
  if (/\binsta(?:gram)?\b|Instagram/i.test(normalized)) return "instagram";
  if (/\bvisit\b|방문형|방문/i.test(normalized)) return "visit";
  if (/Reels/i.test(normalized)) return "reels";
  if (/Clip/i.test(normalized)) return "clip";
  if (/Instagram/i.test(normalized)) return "instagram";
  if (/구매형/.test(normalized)) return "purchase";
  if (/배송형|배송/.test(normalized)) return "delivery";
  if (/기자단/.test(normalized)) return "reporter";
  return "visit";
}

const CHVU_START_DATE_KEYS = [
  "openAt",
  "open_at",
  "startAt",
  "start_at",
  "startDate",
  "start_date",
  "recruitStartAt",
  "recruit_start_at",
  "recruitStartDate",
  "recruit_start_date",
];

const CHVU_CLOSE_DATE_KEYS = [
  "closeAt",
  "close_at",
  "closeDate",
  "close_date",
  "endAt",
  "end_at",
  "endedAt",
  "ended_at",
  "endDate",
  "end_date",
  "recruitEndAt",
  "recruit_end_at",
  "recruitEndDate",
  "recruit_end_date",
  "applyEndAt",
  "apply_end_at",
  "applyEndDate",
  "apply_end_date",
  "applicationEndAt",
  "application_end_at",
  "applicationEndDate",
  "application_end_date",
  "deadline",
  "deadlineAt",
  "deadline_at",
  "expiredAt",
  "expired_at",
];

const CHVU_DDAY_KEYS = [
  "dDay",
  "dday",
  "d_day",
  "remainingDay",
  "remainingDays",
  "remainDay",
  "remain_day",
];

const CHVU_STATUS_KEYS = [
  "status",
  "state",
  "campaignStatus",
  "campaign_status",
  "progressStatus",
  "progress_status",
];

function getChvuDateIso(item, keys) {
  const value = getFirstDefinedValue(item, keys);
  const parsedDate = parseDateInput(value);
  return parsedDate ? parsedDate.toISOString() : null;
}

function isChvuClosedStatus(value = "") {
  const normalized = cleanText(value).toLowerCase();
  if (!normalized) return false;
  return /completed|closed|ended|expired|finish|finished|done|cancel|마감|종료|완료/.test(normalized);
}

function getChvuAddressText(item = {}) {
  const address = cleanAddressText([
    getFirstDefinedValue(item, ["address1", "address", "addr", "roadAddress", "road_address"]),
    getFirstDefinedValue(item, ["address2", "addressDetail", "address_detail", "addrDetail", "addr_detail"]),
  ].filter(Boolean).join(" "));

  return isMeaningfulLocationText(address) ? address : "";
}

function getChvuApiItem(payload) {
  if (!payload || typeof payload !== "object") return null;
  if (payload.data && !Array.isArray(payload.data) && typeof payload.data === "object") {
    return payload.data;
  }
  return payload;
}

function getChvuCampaignNumericId(campaignOrItem = {}) {
  const rawId = getFirstDefinedValue(campaignOrItem, [
    "campaignId",
    "campaign_id",
    "id",
    "_id",
    "idx",
    "seq",
    "no",
  ]) || campaignOrItem.id || campaignOrItem.url || "";
  const match = String(rawId).match(/\d+/);
  return match ? match[0] : "";
}

function buildChvuCampaignFromApiItem(item) {
  if (!item || typeof item !== "object") return null;

  const numericId = getChvuCampaignNumericId(item);
  if (!numericId) return null;

  const title = cleanText(getFirstDefinedValue(item, [
    "title",
    "name",
    "subject",
    "campaignTitle",
    "campaign_title",
    "campaignName",
    "campaign_name",
    "shopName",
    "shop_name",
  ]));
  if (!title) return null;

  const titleLocationHint = parseRegionalPlaceTitle(title);
  const subtitle = cleanText(getFirstDefinedValue(item, [
    "subtitle",
    "subTitle",
    "sub_title",
  ]));
  const details = cleanText(getFirstDefinedValue(item, [
    "details",
    "detail",
    "description",
    "content",
    "offer",
    "offerDetail",
    "provision",
    "provided",
    "reward",
    "benefit",
  ]));
  const pointText = cleanText(getFirstDefinedValue(item, [
    "points",
    "point",
    "pointText",
    "rewardPoint",
    "reward_point",
    "providedPoint",
    "provided_point",
  ]));
  const typeText = cleanText([
    getFirstDefinedValue(item, ["activity", "activityType", "activity_type"]),
    getFirstDefinedValue(item, ["channel", "channelType", "channel_type", "media", "sns"]),
    getFirstDefinedValue(item, ["contentType", "content_type"]),
    getFirstDefinedValue(item, ["type", "campaignType", "campaign_type", "recruitType", "recruit_type"]),
    title,
  ].filter(Boolean).join(" "));
  const sourceStartedAt = getChvuDateIso(item, CHVU_START_DATE_KEYS);
  const sourceEndedAt = getChvuDateIso(item, CHVU_CLOSE_DATE_KEYS);
  const dDayFromCloseAt = sourceEndedAt ? daysUntilKstDate(sourceEndedAt) : null;
  const dDayFromApi = parseDDayOrDate(getFirstDefinedValue(item, CHVU_DDAY_KEYS));
  const dDay = Number.isFinite(dDayFromCloseAt)
    ? dDayFromCloseAt
    : Number.isFinite(dDayFromApi) && !isUnknownDDay(dDayFromApi)
      ? dDayFromApi
      : 99;
  const statusText = getFirstDefinedValue(item, CHVU_STATUS_KEYS);
  const addressText = getChvuAddressText(item);
  const apiCoords = extractLatLngFromObject(item, "chvu_api");
  const campaign = buildCampaign({
    id: `chvu_${numericId}`,
    title,
    url: `https://chvu.co.kr/campaign/${numericId}`,
    platform: "체험뷰",
    platformId: "chvu",
    dDay,
    applyCount: parseNumber(getFirstDefinedValue(item, [
      "currentApplicants",
      "current_applicants",
      "applyCount",
      "apply_count",
      "applicationCount",
      "application_count",
      "applicantCount",
      "applicant_count",
      "currentApply",
      "current_apply",
      "applied",
    ])),
    selectedCount: parseNumber(getFirstDefinedValue(item, [
      "reviewerLimit",
      "reviewer_limit",
      "selectedCount",
      "selected_count",
      "recruitCount",
      "recruit_count",
      "recruitmentCount",
      "recruitment_count",
      "maxApplyCount",
      "max_apply_count",
      "capacity",
      "quota",
      "limit",
    ])) || 3,
    point: subtitle || details || pointText || null,
    type: mapChvuType(typeText),
    category: guessCategory(`${title} ${subtitle} ${details}`),
    locationRaw: addressText || titleLocationHint.locationHint,
    addressRaw: addressText,
    placeName: titleLocationHint.placeName,
    sourceStartedAt,
    sourceEndedAt,
    ...(apiCoords
      ? {
        lat: apiCoords.lat,
        lng: apiCoords.lng,
        coordinateSource: apiCoords.coordinateSource,
      }
      : {}),
  });

  if (isChvuClosedStatus(statusText)) {
    closeCampaignFromDetail(campaign, "chvu_api_status_closed", dDay);
  } else if (Number.isFinite(dDay) && dDay < 0) {
    closeCampaignFromDetail(campaign, "chvu_api_deadline_past", dDay);
  }

  return campaign;
}

function applyChvuApiCampaignEnrichment(campaign, item) {
  const apiCampaign = buildChvuCampaignFromApiItem(item);
  if (!apiCampaign) return false;

  const alwaysFields = [
    "title",
    "dDay",
    "status",
    "closedReason",
    "applyCount",
    "selectedCount",
    "point",
    "type",
    "category",
    "sourceStartedAt",
    "sourceEndedAt",
  ];
  for (const field of alwaysFields) {
    if (apiCampaign[field] !== undefined) {
      campaign[field] = apiCampaign[field];
    }
  }

  for (const field of ["locationRaw", "addressRaw", "placeName", "lat", "lng", "coordinateSource"]) {
    if (apiCampaign[field]) {
      campaign[field] = apiCampaign[field];
    }
  }

  if (isClosedCampaign(apiCampaign)) {
    closeCampaignFromDetail(campaign, apiCampaign.closedReason || "chvu_api_closed", apiCampaign.dDay);
  }

  return true;
}

function parseChvuCampaignCards(html = "") {
  const $ = cheerio.load(html);
  const campaigns = [];
  const seenIds = new Set();

  $("a[href*='/campaign/']").each((index, element) => {
    const link = $(element);
    const href = link.attr("href") || "";
    const match = href.match(/\/campaign\/(\d+)/);
    if (!match) return;

    const id = `chvu_${match[1]}`;
    if (seenIds.has(id)) return;

    const title = cleanText(link.find('div[class*="Title"]').first().text());
    if (!title) return;
    const titleLocationHint = parseRegionalPlaceTitle(title);

    const details = cleanText(link.find('div[class*="Details"]').first().text());
    const pointText = cleanText(link.find('div[class*="Points"]').first().text()).replace(/^제공포인트\s*:\s*/i, "");
    const headerText = cleanText(link.find('div[class*="ItemHeader"]').first().text());
    const applicationText = cleanText(link.find('div[class*="Application"]').first().text());
    const applyMatch = applicationText.match(/신청\s*([\d,]+)\s*\/\s*([\d,]+)/);

    campaigns.push(
      buildCampaign({
        id,
        title,
        url: href.startsWith("http") ? href : `https://chvu.co.kr${href}`,
        platform: "체험뷰",
        platformId: "chvu",
        dDay: parseDDay(applicationText),
        applyCount: parseNumber(applyMatch?.[1] || ""),
        selectedCount: parseNumber(applyMatch?.[2] || "") || 3,
        point: details || pointText || null,
        type: mapChvuType(`${headerText} ${title}`),
        category: guessCategory(`${title} ${details}`),
        locationRaw: titleLocationHint.locationHint,
        placeName: titleLocationHint.placeName,
      }),
    );
    seenIds.add(id);
  });

  return campaigns;
}

function getFirstDefinedValue(source, keys) {
  if (!source || typeof source !== "object") return undefined;
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== null && source[key] !== "") {
      return source[key];
    }
  }
  return undefined;
}

function collectChvuApiItems(payload) {
  if (Array.isArray(payload)) return payload;

  const candidates = [
    payload?.campaigns,
    payload?.items,
    payload?.rows,
    payload?.list,
    payload?.data,
    payload?.data?.campaigns,
    payload?.data?.items,
    payload?.data?.rows,
    payload?.data?.list,
    payload?.data?.contents,
    payload?.result,
    payload?.result?.campaigns,
    payload?.result?.items,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) return candidate;
  }

  const stack = [payload];
  const visited = new Set();
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current || typeof current !== "object" || visited.has(current)) continue;
    visited.add(current);

    for (const value of Object.values(current)) {
      if (Array.isArray(value) && value.some((item) => item && typeof item === "object")) {
        return value;
      }
      if (value && typeof value === "object") {
        stack.push(value);
      }
    }
  }

  return [];
}

function parseChvuApiCampaigns(payload) {
  const campaigns = [];
  const seenIds = new Set();
  const items = collectChvuApiItems(payload);

  for (const item of items) {
    const campaign = buildChvuCampaignFromApiItem(item);
    if (!campaign || seenIds.has(campaign.id)) continue;
    campaigns.push(campaign);
    seenIds.add(campaign.id);
  }

  return campaigns;
}

async function fetchChvuListPageCampaigns(page = 1) {
  const params = {
    category: "search",
    searchQuery: "",
    sort: "-created",
    page,
    count: 22,
  };
  const apiPayload = await fetchJson("https://chvu.co.kr/v2/campaigns", {
    timeoutMs: 25000,
    attempts: 2,
    retryDelayMs: 1200,
    params,
    headers: {
      Referer: "https://chvu.co.kr/campaign",
      Accept: "application/json, text/plain, */*",
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  }).catch(() => null);

  const apiCampaigns = parseChvuApiCampaigns(apiPayload);
  if (apiCampaigns.length > 0) {
    return apiCampaigns;
  }

  const url = "https://chvu.co.kr/campaign";
  const staticHtml = await fetchHtml(url, {
    timeoutMs: 25000,
    attempts: 2,
    retryDelayMs: 1200,
    params,
    headers: {
      Referer: "https://chvu.co.kr/",
    },
  });

  const staticCampaigns = parseChvuCampaignCards(staticHtml);
  if (staticCampaigns.length > 0) {
    return staticCampaigns;
  }

  console.log(`  - chvu: rendered list fallback page ${page}`);
  const renderedUrl = `${url}?${new URLSearchParams(params).toString()}`;
  const renderedHtml = await fetchRenderedHtml(renderedUrl, {
    waitForSelector: "a[href^='/campaign/']",
    timeoutMs: 45000,
    scrollSteps: page === 1 ? 6 : 0,
    referer: "https://chvu.co.kr/",
  });
  return parseChvuCampaignCards(renderedHtml);
}

async function fetchChvuDetailApiCampaign(campaign) {
  const campaignId = getChvuCampaignNumericId(campaign);
  if (!campaignId) return null;

  const payload = await fetchJson(`https://chvu.co.kr/v2/campaigns/${campaignId}`, {
    timeoutMs: CHVU_DETAIL_TIMEOUT_MS,
    attempts: 2,
    retryDelayMs: 1000,
    headers: {
      Referer: campaign.url || `https://chvu.co.kr/campaign/${campaignId}`,
      Accept: "application/json, text/plain, */*",
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });

  return getChvuApiItem(payload);
}

async function fetchChvuDetailHtml(url) {
  const staticHtml = await fetchHtml(url, {
    timeoutMs: CHVU_DETAIL_TIMEOUT_MS,
    attempts: 1,
    retryDelayMs: 800,
    headers: {
      Referer: "https://chvu.co.kr/campaign",
    },
  });

  if (
    extractLatLngFromHtml(staticHtml) ||
    pickBestLocationText(
      extractAddressCandidates(cleanText(cheerio.load(staticHtml)("body").text())),
    )
  ) {
    return staticHtml;
  }

  return fetchRenderedHtml(url, {
    waitForSelector: "body",
    timeoutMs: Math.max(CHVU_DETAIL_TIMEOUT_MS, 15000),
    scrollSteps: 1,
    referer: "https://chvu.co.kr/campaign",
  });
}

function shouldEnrichChvuDetail(campaign) {
  if (CHVU_DETAIL_ENRICH_MODE === "all") return true;
  if (["none", "off", "disabled", "0"].includes(CHVU_DETAIL_ENRICH_MODE)) return false;
  return (campaign.dDay ?? 99) <= 1 || !hasUsableCoordinates(campaign) || !getCampaignAddressText(campaign);
}

function closeChvuCampaignsWithoutReliableDeadline(campaigns) {
  const targets = campaigns.filter((campaign) => hasUnreliableDeadline(campaign));
  for (const campaign of targets) {
    closeCampaignFromDetail(campaign, "chvu_missing_deadline", -1);
  }
  return targets.length;
}

async function crawlChvu() {
  logCrawlerStep("chvu", "chvu");

  try {
    const campaigns = [];
    const seenIds = new Set();

    for (let page = 1; page <= 300; page += 1) {
      const pageCampaigns = await fetchChvuListPageCampaigns(page);
      if (pageCampaigns.length === 0) {
        break;
      }

      let addedOnPage = 0;
      for (const campaign of pageCampaigns) {
        if (seenIds.has(campaign.id)) continue;
        campaigns.push(campaign);
        seenIds.add(campaign.id);
        addedOnPage += 1;
      }

      if (addedOnPage === 0) {
        console.log(`  - chvu page ${page}: duplicate-only page`);
        break;
      }

      if (pageCampaigns.length < 22) {
        break;
      }

      await sleep(250);
    }

    const detailCandidates = campaigns.filter(shouldEnrichChvuDetail);
    const detailTargets = CHVU_DETAIL_ENRICH_LIMIT > 0
      ? detailCandidates.slice(0, CHVU_DETAIL_ENRICH_LIMIT)
      : detailCandidates;
    if (detailTargets.length !== campaigns.length) {
      console.log(
        `  - chvu detail enrich targets ${detailTargets.length}/${campaigns.length} campaigns `
        + `(mode=${CHVU_DETAIL_ENRICH_MODE}, concurrency=${CHVU_DETAIL_ENRICH_CONCURRENCY})`,
      );
    }
    if (CHVU_DETAIL_ENRICH_LIMIT > 0 && detailCandidates.length > detailTargets.length) {
      console.log(`  - chvu detail enrich limited to ${detailTargets.length}/${detailCandidates.length} targets`);
    }

    await processCampaignsInBatches("chvu", detailTargets, async (campaign) => {
      try {
        let apiEnriched = false;
        try {
          const apiItem = await fetchChvuDetailApiCampaign(campaign);
          apiEnriched = applyChvuApiCampaignEnrichment(campaign, apiItem);
        } catch (apiError) {
          console.log(`  - chvu api detail failed (${campaign.id}): ${apiError.message}`);
        }

        if (
          apiEnriched
          && (isClosedCampaign(campaign) || (getCampaignAddressText(campaign) && !hasUnreliableDeadline(campaign)))
        ) {
          return;
        }

        const html = await fetchChvuDetailHtml(campaign.url);
        const $ = cheerio.load(html);
        applyCampaignDetailState(campaign, html, $);
        const dataClipboardTexts = $("[data-clipboard-text]")
          .map((_, element) => cleanAddressText($(element).attr("data-clipboard-text") || ""))
          .get();
        const addressTexts = $('[class*="Address"], .address, .place')
          .map((_, element) => cleanAddressText($(element).text()))
          .get();
        const extractedAddress = pickBestLocationText(
          dataClipboardTexts,
          addressTexts,
          extractAddressCandidates(cleanText($("body").text())),
        );
        const coords = extractLatLngFromHtml(html);
        const sourceStartedAt = extractSourceStartedAt($, $("body").text());

        if (extractedAddress) {
          campaign.locationRaw = extractedAddress;
          campaign.addressRaw = extractedAddress;
        }
        if (coords) {
          campaign.lat = coords.lat;
          campaign.lng = coords.lng;
          campaign.coordinateSource = coords.coordinateSource || "html";
        }
        if (sourceStartedAt) {
          campaign.sourceStartedAt = sourceStartedAt;
        }
      } catch (error) {
        console.log(`  - chvu location enrich failed (${campaign.id}): ${error.message}`);
      }
    }, { batchSize: CHVU_DETAIL_ENRICH_CONCURRENCY });

    const hiddenNoDeadlineCount = closeChvuCampaignsWithoutReliableDeadline(campaigns);
    if (hiddenNoDeadlineCount > 0) {
      console.log(
        `  - chvu hidden without reliable deadline: ${hiddenNoDeadlineCount}/${campaigns.length}`,
      );
    }

    console.log(`  - chvu: ${campaigns.length}`);
    return campaigns;
  } catch (error) {
    console.log(`  - chvu failed: ${error.message}`);
    throw error;
  }
}

async function main() {
  const crawlStartedAt = new Date().toISOString();
  const crawlOnly = new Set(
    String(process.env.CRAWL_ONLY || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );

  console.log("========================================");
  console.log(" campaign crawl started");
  console.log("========================================");
  if (crawlOnly.size) {
    console.log(` crawl filter: ${[...crawlOnly].join(", ")}`);
  }

  const crawlers = [
    { platformId: "reviewnote", label: "reviewnote", run: crawlReviewnote },
    { platformId: "mrblog", label: "mrblog", run: crawlMrblog },
    { platformId: "reviewplace", label: "reviewplace", run: crawlReviewplace },
    { platformId: "dinner", label: "dinnerqueen", run: crawlDinnerqueen },
    { platformId: "tqueens", label: "tqueens", run: crawlTqueens },
    { platformId: "pavlo", label: "pavlo", run: crawlPavlo },
    { platformId: "seouloba", label: "seouloba", run: crawlSeouloba },
    { platformId: "revu", label: "revu", run: crawlRevu },
    { platformId: "gangnam", label: "gangnam", run: crawlGangnam },
    { platformId: "popomon", label: "popomon", run: crawlPopomon },
    { platformId: "comeplay", label: "comeplay", run: crawlComeplay },
    { platformId: "tble", label: "tble", run: crawlTble },
    { platformId: "ringble", label: "ringble", run: crawlRingble },
    { platformId: "chvu", label: "chvu", run: crawlChvu },
  ];
  const activeCrawlers = resolveActiveCrawlers(crawlers, crawlOnly);
  const defaultExcludedCrawlers = crawlers.filter(
    (crawler) => !crawlOnly.size && DEFAULT_EXCLUDED_CRAWLER_IDS.has(crawler.platformId),
  );
  if (defaultExcludedCrawlers.length) {
    console.log(` default skipped: ${defaultExcludedCrawlers.map((crawler) => crawler.platformId).join(", ")}`);
  }
  const previousSnapshotCampaigns = loadExistingSnapshotCampaigns();
  const successfulCrawls = [];
  const failedCrawls = [];
  const qualityGateActiveCrawlers = activeCrawlers;
  const qualityGateCrawlOnly = [...crawlOnly];
  let currentFreshCampaigns = [];
  let currentFreshUpsertCampaigns = [];
  let currentSnapshotCampaigns = previousSnapshotCampaigns;
  let publishedSnapshotCampaigns = previousSnapshotCampaigns;
  let currentSnapshotMeta = null;
  let qualityGate = null;
  let supabaseSync = supabase
    ? { status: "pending", startedAt: null, completedAt: null, reason: null }
    : { status: "skipped", startedAt: null, completedAt: null, reason: "SUPABASE_SERVICE_ROLE_KEY is missing" };

  const refreshPipelineArtifacts = (stage) => {
    currentFreshCampaigns = getLifecycleCampaignsFromCrawls(
      successfulCrawls,
      previousSnapshotCampaigns,
      crawlStartedAt,
      { visibleOnly: true },
    );
    const snapshotResult = buildCampaignSnapshotResult(
      successfulCrawls,
      getPreservedSnapshotCampaigns(previousSnapshotCampaigns, successfulCrawls),
      { previousCampaigns: previousSnapshotCampaigns, crawlStartedAt },
    );
    currentSnapshotCampaigns = snapshotResult.campaigns;
    currentSnapshotMeta = snapshotResult;
    writeCrawlerPipelineArtifacts({
      crawlStartedAt,
      stage,
      successfulCrawls,
      failedCrawls,
      freshCampaigns: currentFreshCampaigns,
      publishCandidate: currentSnapshotCampaigns,
      previousCampaigns: previousSnapshotCampaigns,
      qualityGate,
      pipelineStats: currentSnapshotMeta,
    });
    writeOperationalArtifacts({
      crawlStartedAt,
      crawlOnly: qualityGateCrawlOnly,
      activeCrawlers: qualityGateActiveCrawlers,
      successfulCrawls,
      failedCrawls,
      campaigns: currentSnapshotCampaigns,
      supabaseSync,
      qualityGate,
      pipelineStats: currentSnapshotMeta,
    });
  };

  writeOperationalArtifacts({
    crawlStartedAt,
    crawlOnly: qualityGateCrawlOnly,
    activeCrawlers: qualityGateActiveCrawlers,
    successfulCrawls,
    failedCrawls,
    campaigns: currentSnapshotCampaigns,
    supabaseSync,
    qualityGate,
    pipelineStats: currentSnapshotMeta,
  });

  for (const crawler of activeCrawlers) {
    const startedAt = Date.now();
    console.log(` > ${crawler.label}: started (${new Date(startedAt).toISOString()})`);
    try {
      const campaigns = await runCrawlerWithTimeout(crawler);
      try {
        await geocodeCampaignCoordinates(campaigns);
      } catch (geocodeError) {
        console.log(`  - ${crawler.label} geocode pass failed: ${geocodeError.message}`);
      }
      const typeCounts = countCampaignTypes(campaigns);
      writeCrawlerArtifact(`${crawler.platformId}-last-crawl.json`, {
        generatedAt: new Date().toISOString(),
        platformId: crawler.platformId,
        label: crawler.label,
        totals: {
          campaigns: campaigns.length,
          types: typeCounts,
          delivery: typeCounts.delivery || 0,
          nonDelivery: campaigns.length - (typeCounts.delivery || 0),
        },
        campaigns,
      });
      console.log(`  - ${crawler.label} type summary: ${JSON.stringify(typeCounts)}`);
      const durationMs = Date.now() - startedAt;
      successfulCrawls.push({
        platformId: crawler.platformId,
        label: crawler.label,
        campaigns,
        durationMs,
      });
      refreshPipelineArtifacts("crawl_progress");
      console.log(` > ${crawler.label}: completed in ${formatDurationMs(durationMs)} (${campaigns.length} campaigns)`);
    } catch (error) {
      const durationMs = Date.now() - startedAt;
      failedCrawls.push({
        platformId: crawler.platformId,
        label: crawler.label,
        reason: error?.message || "unknown error",
        durationMs,
      });
      refreshPipelineArtifacts("crawl_progress");
      console.log(`  - ${crawler.label} failed after ${formatDurationMs(durationMs)}: ${error?.message || "unknown error"}`);
    }
  }

  quarantineLowVisibleCountCrawls(successfulCrawls, failedCrawls, previousSnapshotCampaigns);
  quarantineLowDataQualityCrawls(successfulCrawls, failedCrawls, previousSnapshotCampaigns, crawlStartedAt);

  const { deduped } = getVisibleCampaigns(successfulCrawls);
  await geocodeCampaignCoordinates(deduped);
  const suspiciousCoordinateClusters = neutralizeSuspiciousCoordinateClusters(
    successfulCrawls.flatMap((crawl) => crawl.campaigns || []),
  );
  for (const cluster of suspiciousCoordinateClusters) {
    console.log(
      `  - ${cluster.platformId} coordinate cluster invalidated: ${cluster.count}/${cluster.total} `
      + `campaigns at ${cluster.latLng} (${cluster.source})`,
    );
  }
  currentFreshCampaigns = getLifecycleCampaignsFromCrawls(
    successfulCrawls,
    previousSnapshotCampaigns,
    crawlStartedAt,
    { visibleOnly: true },
  );
  currentFreshUpsertCampaigns = applyFreshLifecycleToCampaigns(deduped, previousSnapshotCampaigns, crawlStartedAt);
  const snapshotResult = buildCampaignSnapshotResult(
    successfulCrawls,
    getPreservedSnapshotCampaigns(previousSnapshotCampaigns, successfulCrawls),
    { previousCampaigns: previousSnapshotCampaigns, crawlStartedAt },
  );
  currentSnapshotCampaigns = snapshotResult.campaigns;
  currentSnapshotMeta = snapshotResult;
  qualityGate = evaluateQualityGate({
    candidateCampaigns: currentSnapshotCampaigns,
    freshCampaigns: currentFreshCampaigns,
    previousCampaigns: previousSnapshotCampaigns,
    successfulCrawls,
    failedCrawls,
    activeCrawlers: qualityGateActiveCrawlers,
    crawlOnly: qualityGateCrawlOnly,
  });
  writeCrawlerPipelineArtifacts({
    crawlStartedAt,
    stage: "quality_checked",
    successfulCrawls,
    failedCrawls,
    freshCampaigns: currentFreshCampaigns,
    publishCandidate: currentSnapshotCampaigns,
    previousCampaigns: previousSnapshotCampaigns,
    qualityGate,
    pipelineStats: currentSnapshotMeta,
  });
  writeOperationalArtifacts({
    crawlStartedAt,
    crawlOnly: qualityGateCrawlOnly,
    activeCrawlers: qualityGateActiveCrawlers,
    successfulCrawls,
    failedCrawls,
    campaigns: currentSnapshotCampaigns,
    supabaseSync,
    qualityGate,
    pipelineStats: currentSnapshotMeta,
  });

  if (qualityGate.canPublish) {
    publishedSnapshotCampaigns = publishCampaignSnapshot(currentSnapshotCampaigns, qualityGate);
    console.log(`  - publish gate ${qualityGate.status}: public/campaigns.json updated`);
  } else {
    supabaseSync = {
      status: "skipped",
      startedAt: null,
      completedAt: new Date().toISOString(),
      reason: "quality gate blocked publication",
    };
    console.log("  - publish gate blocked: public/campaigns.json kept unchanged");
    for (const failure of qualityGate.blockingFailures) {
      console.log(`    * ${failure.id}: ${failure.message}`);
    }
  }

  if (supabase && qualityGate.canPublish) {
    const supabaseStartedAt = new Date().toISOString();
    supabaseSync = { status: "running", startedAt: supabaseStartedAt, completedAt: null, reason: null };
    writeOperationalArtifacts({
      crawlStartedAt,
      crawlOnly: qualityGateCrawlOnly,
      activeCrawlers: qualityGateActiveCrawlers,
      successfulCrawls,
      failedCrawls,
      campaigns: currentSnapshotCampaigns,
      supabaseSync,
      qualityGate,
      pipelineStats: currentSnapshotMeta,
    });

    try {
      await upsertToSupabase(currentFreshUpsertCampaigns);
      await closeExpiredCampaigns();
      await closeMissingCampaigns(successfulCrawls, crawlStartedAt);
      supabaseSync = {
        status: "completed",
        startedAt: supabaseStartedAt,
        completedAt: new Date().toISOString(),
        reason: null,
      };
    } catch (error) {
      supabaseSync = {
        status: "failed",
        startedAt: supabaseStartedAt,
        completedAt: new Date().toISOString(),
        reason: error.message,
      };
      console.log(`  - Supabase sync failed: ${error.message}`);
    }
  }

  const completedAt = new Date().toISOString();
  writeOperationalArtifacts({
    crawlStartedAt,
    completedAt,
    crawlOnly: qualityGateCrawlOnly,
    activeCrawlers: qualityGateActiveCrawlers,
    successfulCrawls,
    failedCrawls,
    campaigns: currentSnapshotCampaigns,
    supabaseSync,
    qualityGate,
    pipelineStats: currentSnapshotMeta,
  });

  console.log("========================================");
  for (const crawl of successfulCrawls) {
    console.log(` ${crawl.label}: ${crawl.campaigns.length} (${formatDurationMs(crawl.durationMs || 0)})`);
  }
  for (const failed of failedCrawls) {
    console.log(` ${failed.label}: failed (${failed.reason}) [${formatDurationMs(failed.durationMs || 0)}]`);
  }
  if (qualityGate) {
    console.log(` quality gate: ${qualityGate.status} (${qualityGate.mode})`);
  }
  console.log(` candidate total: ${currentSnapshotCampaigns.length}`);
  console.log(` published total: ${publishedSnapshotCampaigns.length}`);
  console.log(" output: public/campaigns.json");
  console.log(` pipeline: ${path.relative(PROJECT_ROOT, CRAWLER_ARTIFACT_DIR)}`);
  console.log(" ops: public/crawl-status.json, public/data-quality.json");
  console.log("========================================");
}

if (process.env.CRAWLER_TEST_EXPORTS === "1") {
  module.exports = {
    PLATFORM_SEEDS,
    applyGangnamDetailLocationEnrichment,
    buildDinnerqueenListRequest,
    buildCampaignSnapshotResult,
    buildRevuCampaignFromApiItem,
    buildTqueensListRequest,
    extractComeplayProvisionFromDetail,
    extractDinnerqueenProvisionFromDetail,
    extractGangnamProvisionFromDetail,
    extractMrblogProvisionFromDetail,
    extractRingbleProvisionFromDetail,
    extractReviewplaceProvisionFromDetail,
    extractTqueensProvisionFromDetail,
    evaluateQualityGate,
    getComeplayConfigs,
    getDinnerqueenListConfigs,
    getMrblogConfigs,
    getPavloConfigs,
    getPopomonConfigs,
    getReviewplaceCategories,
    getTbleConfigs,
    getCampaignGeocodeQuery,
    getRevuCategories,
    isKnownBadMapCoordinate,
    isProvisionLabel,
    mapRevuType,
    normalizeKakaoGeocodeDocument,
    normalizeCampaignTypeForLaunch,
    parseComeplayListCampaigns,
    parseDinnerqueenListCampaigns,
    parseDinnerqueenListResponse,
    parseGangnamListCampaigns,
    parseMrblogListCampaigns,
    parsePavloListCampaigns,
    parsePopomonListCampaigns,
    parseReviewplaceListCampaigns,
    parseRingbleKoreanDateRange,
    parseRingbleListCampaigns,
    parseTbleListCampaigns,
    parseTqueensListCampaigns,
    parseTqueensListResponse,
    applyRingbleDetailEnrichment,
    resolveActiveCrawlers,
    selectDinnerqueenDetailTargets,
    shouldContinueDinnerqueenListPage,
    normalizeProvisionText,
  };
} else {
  main()
    .then(() => {
      process.exit(0);
    })
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });
}
