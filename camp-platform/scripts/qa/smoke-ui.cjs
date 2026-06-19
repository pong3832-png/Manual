const { chromium } = require("playwright");

const BASE_URL = process.env.QA_BASE_URL || "http://127.0.0.1:5173";
const TIMEOUT_MS = Number(process.env.QA_TIMEOUT_MS || 15000);
const ALLOW_NETWORK_DENIED = process.env.QA_ALLOW_NETWORK_DENIED === "1";

async function expectVisible(page, text, label) {
  await page.waitForFunction((needle) => {
    return Array.from(document.body.querySelectorAll("*")).some((element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== "hidden"
        && style.display !== "none"
        && rect.width > 0
        && rect.height > 0
        && element.textContent.includes(needle);
    });
  }, text, { timeout: TIMEOUT_MS });
  return label;
}

async function clickNav(page, label) {
  await expectVisible(page, label, `${label} nav visible`);
  const items = await page.getByText(label, { exact: true }).all();
  for (const item of items) {
    if (await item.isVisible()) {
      await item.click();
      return;
    }
  }
  throw new Error(`Visible nav item not found: ${label}`);
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const browserConsoleErrors = [];

  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") browserConsoleErrors.push(message.text());
    });

    await page.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await expectVisible(page, "체험단", "home renders");

    await clickNav(page, "현황");
    await expectVisible(page, "로그인이 필요합니다", "status auth guard");

    await clickNav(page, "마이");
    await expectVisible(page, "로그인이 필요합니다", "profile auth guard");

    await page.goto(`${BASE_URL}/?legal=privacy`, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await expectVisible(page, "개인정보", "privacy route");

    await page.goto(`${BASE_URL}/?contact=1`, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await expectVisible(page, "문의", "contact route");

    const filteredConsoleErrors = ALLOW_NETWORK_DENIED
      ? browserConsoleErrors.filter((message) => !message.includes("ERR_NETWORK_ACCESS_DENIED"))
      : browserConsoleErrors;

    if (errors.length || filteredConsoleErrors.length) {
      throw new Error(`Browser errors found: ${JSON.stringify({ errors, browserConsoleErrors: filteredConsoleErrors }, null, 2)}`);
    }

    console.log(JSON.stringify({
      ok: true,
      baseUrl: BASE_URL,
      allowedNetworkDenied: ALLOW_NETWORK_DENIED,
      checks: [
        "home renders",
        "status auth guard",
        "profile auth guard",
        "privacy route",
        "contact route",
      ],
    }, null, 2));
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
