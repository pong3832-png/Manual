function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function isPublishAllowed(qualityGate = {}) {
  if (!qualityGate) return false;
  if (qualityGate.canPublish === false) return false;
  return qualityGate.status !== "blocked";
}

function getQualityGateIntegrityFailures(qualityGate = null) {
  if (!qualityGate || !isPublishAllowed(qualityGate)) return [];

  return asArray(qualityGate.rules)
    .filter((rule) => String(rule?.id || "").startsWith("failed_platform_preserved:"))
    .filter((rule) => {
      const previousCount = Number(rule?.details?.previousCount || 0);
      return previousCount <= 0 && rule?.passed !== false;
    })
    .map((rule) => {
      const platformId = rule?.details?.platformId || String(rule?.id || "").split(":")[1] || "unknown";
      return `quality gate allows publish but ${platformId} has no previous campaigns to preserve`;
    });
}

module.exports = {
  getQualityGateIntegrityFailures,
};
