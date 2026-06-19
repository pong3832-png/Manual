const fs = require("fs");
const path = require("path");
const { getQualityGateIntegrityFailures } = require("./check-crawl-rules.cjs");

const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const PUBLIC_DIR = path.join(PROJECT_ROOT, "public");
const ARTIFACT_DIR = path.join(PROJECT_ROOT, ".cache", "crawl-artifacts");

const DEFAULT_MIN_COORDINATE_PCT = 50;
const DEFAULT_WARN_COORDINATE_PCT = 80;
const DEFAULT_WARN_ADDRESS_PCT = 50;
const DEFAULT_MAX_REPORT_AGE_HOURS = 24;

const thresholds = {
  minCoordinatePct: readNumberEnv("CHECK_MIN_COORDINATE_PCT", DEFAULT_MIN_COORDINATE_PCT),
  warnCoordinatePct: readNumberEnv("CHECK_WARN_COORDINATE_PCT", DEFAULT_WARN_COORDINATE_PCT),
  warnAddressPct: readNumberEnv("CHECK_WARN_ADDRESS_PCT", DEFAULT_WARN_ADDRESS_PCT),
  maxReportAgeHours: readNumberEnv("CHECK_MAX_REPORT_AGE_HOURS", DEFAULT_MAX_REPORT_AGE_HOURS),
};

const files = {
  crawlStatus: path.join(PUBLIC_DIR, "crawl-status.json"),
  dataQuality: path.join(PUBLIC_DIR, "data-quality.json"),
  campaigns: path.join(PUBLIC_DIR, "campaigns.json"),
  qualityGate: path.join(ARTIFACT_DIR, "quality-gate.json"),
  output: path.join(PUBLIC_DIR, "crawl-check.json"),
};

function readNumberEnv(name, fallback) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) ? value : fallback;
}

function readJsonFile(filePath, label) {
  if (!fs.existsSync(filePath)) {
    return { ok: false, value: null, error: `${label} is missing`, path: filePath };
  }

  try {
    return {
      ok: true,
      value: JSON.parse(fs.readFileSync(filePath, "utf-8")),
      error: null,
      path: filePath,
    };
  } catch (error) {
    return {
      ok: false,
      value: null,
      error: `${label} is not valid JSON: ${error.message}`,
      path: filePath,
    };
  }
}

function getAgeHours(iso) {
  const timestamp = Date.parse(iso || "");
  if (!Number.isFinite(timestamp)) return null;
  return Math.round(((Date.now() - timestamp) / 3600000) * 10) / 10;
}

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(1).replace(/\.0$/, "")}%` : "n/a";
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function pushUnique(items, value) {
  if (!value || items.includes(value)) return;
  items.push(value);
}

function getTopPlatforms(platforms, selector, limit = 5) {
  return asArray(platforms)
    .filter((platform) => Number(platform?.total || 0) > 0)
    .sort((left, right) => Number(selector(right) || 0) - Number(selector(left) || 0))
    .slice(0, limit);
}

function getWorstCoordinatePlatforms(platforms, limit = 5) {
  return asArray(platforms)
    .filter((platform) => Number(platform?.total || 0) >= 20)
    .sort((left, right) => Number(left.coordinateCompletenessPct || 0) - Number(right.coordinateCompletenessPct || 0))
    .slice(0, limit);
}

function makeReport() {
  const statusRead = readJsonFile(files.crawlStatus, "crawl-status.json");
  const qualityRead = readJsonFile(files.dataQuality, "data-quality.json");
  const campaignsRead = readJsonFile(files.campaigns, "campaigns.json");
  const gateRead = readJsonFile(files.qualityGate, "quality-gate.json");

  const status = statusRead.value || {};
  const quality = qualityRead.value || {};
  const campaigns = asArray(campaignsRead.value?.campaigns);
  const qualityGate = quality.qualityGate || gateRead.value || campaignsRead.value?.qualityGate || null;
  const totals = quality.totals || status.totals || {};
  const platforms = asArray(quality.platforms);
  const failedCrawls = asArray(status.failedCrawls);
  const warnings = asArray(quality.warnings);
  const issues = quality.issues || {};
  const completedAt = status.completedAt || quality.generatedAt || campaignsRead.value?.updatedAt || null;
  const reportAgeHours = getAgeHours(completedAt);

  const critical = [];
  const warning = [];

  if (!statusRead.ok) critical.push(statusRead.error);
  if (!campaignsRead.ok) critical.push(campaignsRead.error);
  if (!qualityRead.ok) {
    const isRunning = !status.completedAt || status.status === "running" || status.status === "completed_with_errors";
    const severity = isRunning ? warning : critical;
    pushUnique(severity, qualityRead.error);
  }

  if (!status.completedAt) {
    pushUnique(warning, "crawl appears to be still running or did not write completedAt yet");
  }

  if (reportAgeHours !== null && reportAgeHours > thresholds.maxReportAgeHours) {
    pushUnique(warning, `latest crawl report is old: ${reportAgeHours}h`);
  }

  if (status.status === "blocked" || qualityGate?.status === "blocked") {
    pushUnique(critical, "quality gate blocked publication");
  }

  for (const failure of getQualityGateIntegrityFailures(qualityGate)) {
    pushUnique(critical, failure);
  }

  if (failedCrawls.length > 0) {
    for (const failed of failedCrawls) {
      pushUnique(critical, `${failed.platformId || failed.label || "unknown"} crawler failed: ${failed.reason || "unknown"}`);
    }
  }
  const failedPlatformIds = new Set(
    failedCrawls.map((failed) => failed.platformId || failed.label || "unknown"),
  );

  const coordinatePct = Number(totals.coordinateCompletenessPct);
  if (Number.isFinite(coordinatePct)) {
    if (coordinatePct < thresholds.minCoordinatePct) {
      pushUnique(critical, `coordinate completeness below hard minimum: ${formatPercent(coordinatePct)}`);
    } else if (coordinatePct < thresholds.warnCoordinatePct) {
      pushUnique(warning, `coordinate completeness below target: ${formatPercent(coordinatePct)}`);
    }
  }

  const addressPct = Number(totals.addressCompletenessPct);
  if (Number.isFinite(addressPct) && addressPct < thresholds.warnAddressPct) {
    pushUnique(warning, `address completeness below target: ${formatPercent(addressPct)}`);
  }

  for (const item of warnings) {
    const line = `${item.platformId || "unknown"}: ${item.message || "warning"}`;
    if (item.severity === "critical") {
      if (failedPlatformIds.has(item.platformId) && /^crawler failed:/i.test(item.message || "")) continue;
      pushUnique(critical, line);
    }
    else pushUnique(warning, line);
  }

  const statusText = critical.length > 0 ? "fail" : warning.length > 0 ? "warn" : "pass";
  const missingCoordinateSamples = asArray(issues.missingCoordinates).slice(0, 10);
  const missingAddressSamples = asArray(issues.missingAddress).slice(0, 10);
  const lowConfidenceSamples = asArray(issues.lowConfidenceCoordinates).slice(0, 10);

  return {
    checkedAt: new Date().toISOString(),
    status: statusText,
    thresholds,
    crawl: {
      status: status.status || null,
      startedAt: status.startedAt || quality.crawlStartedAt || null,
      completedAt,
      reportAgeHours,
      crawlOnly: asArray(status.crawlOnly),
      activePlatforms: asArray(status.activePlatforms),
    },
    totals: {
      campaigns: Number(totals.campaigns ?? campaigns.length) || 0,
      coordinateCompletenessPct: Number.isFinite(coordinatePct) ? coordinatePct : null,
      addressCompletenessPct: Number.isFinite(addressPct) ? addressPct : null,
      missingCoordinates: Number(totals.missingCoordinates || 0),
      missingAddress: Number(totals.missingAddress || 0),
      staleCampaigns: Number(totals.staleCampaigns || 0),
      duplicateGroups: Number(totals.duplicateGroups || 0),
      hiddenDuplicates: Number(totals.hiddenDuplicates || 0),
      successfulPlatforms: Number(totals.successfulPlatforms ?? status.totals?.successfulPlatforms ?? 0),
      failedPlatforms: Number(totals.failedPlatforms ?? status.totals?.failedPlatforms ?? failedCrawls.length),
    },
    qualityGate: qualityGate
      ? {
        status: qualityGate.status || null,
        mode: qualityGate.mode || null,
        canPublish: qualityGate.canPublish ?? null,
      }
      : null,
    platformSummary: platforms.map((platform) => ({
      platformId: platform.platformId,
      total: platform.total,
      coordinateCompletenessPct: platform.coordinateCompletenessPct,
      addressCompletenessPct: platform.addressCompletenessPct,
      missingCoordinates: platform.missingCoordinates,
      missingAddress: platform.missingAddress,
    })),
    highlights: {
      worstCoordinatePlatforms: getWorstCoordinatePlatforms(platforms).map((platform) => ({
        platformId: platform.platformId,
        total: platform.total,
        coordinateCompletenessPct: platform.coordinateCompletenessPct,
        missingCoordinates: platform.missingCoordinates,
      })),
      mostMissingCoordinates: getTopPlatforms(platforms, (platform) => platform.missingCoordinates).map((platform) => ({
        platformId: platform.platformId,
        missingCoordinates: platform.missingCoordinates,
        coordinateCompletenessPct: platform.coordinateCompletenessPct,
      })),
      mostMissingAddress: getTopPlatforms(platforms, (platform) => platform.missingAddress).map((platform) => ({
        platformId: platform.platformId,
        missingAddress: platform.missingAddress,
        addressCompletenessPct: platform.addressCompletenessPct,
      })),
    },
    samples: {
      missingCoordinates: missingCoordinateSamples,
      missingAddress: missingAddressSamples,
      lowConfidenceCoordinates: lowConfidenceSamples,
    },
    failedCrawls,
    critical,
    warning,
    sourceFiles: {
      crawlStatus: statusRead.ok,
      dataQuality: qualityRead.ok,
      campaigns: campaignsRead.ok,
      qualityGate: gateRead.ok,
    },
  };
}

function printReport(report) {
  const totals = report.totals;
  console.log("========================================");
  console.log(`crawl check: ${report.status.toUpperCase()}`);
  console.log(`crawl status: ${report.crawl.status || "unknown"}`);
  console.log(`completed at: ${report.crawl.completedAt || "not completed"}`);
  console.log(`campaigns: ${totals.campaigns}`);
  console.log(`coordinates: ${formatPercent(totals.coordinateCompletenessPct)} (${totals.missingCoordinates} missing)`);
  console.log(`addresses: ${formatPercent(totals.addressCompletenessPct)} (${totals.missingAddress} missing)`);
  console.log(`platforms: ${totals.successfulPlatforms} success, ${totals.failedPlatforms} failed`);
  if (report.qualityGate) {
    console.log(`quality gate: ${report.qualityGate.status || "unknown"} (${report.qualityGate.mode || "unknown"})`);
  }

  if (report.critical.length > 0) {
    console.log("");
    console.log("critical:");
    for (const item of report.critical.slice(0, 12)) console.log(` - ${item}`);
  }

  if (report.warning.length > 0) {
    console.log("");
    console.log("warnings:");
    for (const item of report.warning.slice(0, 12)) console.log(` - ${item}`);
  }

  if (report.highlights.worstCoordinatePlatforms.length > 0) {
    console.log("");
    console.log("worst coordinate platforms:");
    for (const platform of report.highlights.worstCoordinatePlatforms) {
      console.log(
        ` - ${platform.platformId}: ${formatPercent(platform.coordinateCompletenessPct)} `
        + `(${platform.missingCoordinates} missing / ${platform.total} total)`,
      );
    }
  }

  console.log("");
  console.log(`report: ${path.relative(PROJECT_ROOT, files.output)}`);
  console.log("========================================");
}

function writeReport(report) {
  fs.mkdirSync(PUBLIC_DIR, { recursive: true });
  fs.writeFileSync(files.output, JSON.stringify(report, null, 2), "utf-8");
}

const report = makeReport();
writeReport(report);
printReport(report);

if (report.status === "fail") process.exitCode = 1;
else if (report.status === "warn") process.exitCode = 2;
