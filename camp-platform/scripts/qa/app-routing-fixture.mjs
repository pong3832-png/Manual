import assert from "node:assert/strict";
import { normalizeAppTab } from "../../src/app/appRouting.js";

assert.equal(normalizeAppTab("explore"), "explore");
assert.equal(normalizeAppTab("map"), "map");
assert.equal(normalizeAppTab("ops"), "home");
assert.equal(normalizeAppTab("ops", { showOps: true }), "ops");
assert.equal(normalizeAppTab("unknown"), "home");
assert.equal(normalizeAppTab(""), "home");

console.log(JSON.stringify({ ok: true }, null, 2));
