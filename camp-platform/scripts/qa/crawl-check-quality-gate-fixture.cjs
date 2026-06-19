const assert = require("node:assert/strict");

const {
  getQualityGateIntegrityFailures,
} = require("../crawler/check-crawl-rules.cjs");

assert.equal(typeof getQualityGateIntegrityFailures, "function");

const stalePassedGate = {
  status: "passed_with_warnings",
  canPublish: true,
  rules: [
    {
      id: "failed_platform_preserved:reviewnote",
      passed: true,
      severity: "critical",
      message: "reviewnote failed and previous campaigns will be preserved",
      details: {
        platformId: "reviewnote",
        previousCount: 0,
        reason: "Request failed with status code 403",
      },
    },
  ],
};

const failures = getQualityGateIntegrityFailures(stalePassedGate);
assert.equal(failures.length, 1);
assert.match(failures[0], /reviewnote/);
assert.match(failures[0], /previous campaigns/i);

assert.deepEqual(
  getQualityGateIntegrityFailures({
    status: "blocked",
    canPublish: false,
    blockingFailures: [{ id: "failed_platform_preserved:reviewnote" }],
    rules: [
      {
        id: "failed_platform_preserved:reviewnote",
        passed: false,
        severity: "critical",
        details: { platformId: "reviewnote", previousCount: 0 },
      },
    ],
  }),
  [],
  "already blocked gates should not add a duplicate integrity failure",
);

assert.deepEqual(
  getQualityGateIntegrityFailures({
    status: "passed_with_warnings",
    canPublish: true,
    rules: [
      {
        id: "failed_platform_preserved:reviewnote",
        passed: true,
        severity: "high",
        details: { platformId: "reviewnote", previousCount: 8 },
      },
    ],
  }),
  [],
  "failed platforms with previous campaigns can be preserved",
);

console.log(JSON.stringify({ ok: true }, null, 2));
