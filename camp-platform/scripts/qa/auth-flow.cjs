const { chromium } = require("playwright");

const BASE_URL = process.env.QA_BASE_URL || "http://127.0.0.1:5173";
const EMAIL = process.env.QA_EMAIL || "";
const PASSWORD = process.env.QA_PASSWORD || "";
const PROFILE_NAME = process.env.QA_PROFILE_NAME || "QA 자동검증";
const PROFILE_BLOG_URL = process.env.QA_PROFILE_BLOG_URL || "https://blog.naver.com/cheheommoa-qa";
const PROFILE_INSTAGRAM_URL = process.env.QA_PROFILE_INSTAGRAM_URL || "https://instagram.com/cheheommoa.qa";
const PROFILE_YOUTUBE_URL = process.env.QA_PROFILE_YOUTUBE_URL || "https://www.youtube.com/@GoogleDevelopers";
const RUN_ID = new Date().toISOString();
const PROFILE_MESSAGE = process.env.QA_PROFILE_MESSAGE || `안녕하세요. 캠페인 취지에 맞춰 성실하게 체험하고 정성껏 리뷰하겠습니다. QA ${RUN_ID}`;
const YOUTUBE_SYNC_URL = process.env.QA_YOUTUBE_SYNC_URL || "";
const TIMEOUT_MS = Number(process.env.QA_TIMEOUT_MS || 20000);
const ALLOW_NETWORK_DENIED = process.env.QA_ALLOW_NETWORK_DENIED === "1";
let currentStep = "start";
const networkEvents = [];

function maskEmail(value) {
  return String(value || "").replace(/^(.{2}).*(@.*)$/, "$1***$2");
}

function maskSensitiveText(value) {
  const text = String(value || "");
  return EMAIL ? text.replaceAll(EMAIL, maskEmail(EMAIL)) : text;
}

if (!EMAIL || !PASSWORD) {
  console.error("QA_EMAIL and QA_PASSWORD are required for authenticated QA.");
  process.exit(2);
}

async function expectVisible(page, text, label) {
  currentStep = label;
  try {
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
  } catch (error) {
    throw new Error(await buildStepError(page, `Timed out waiting for "${text}"`, error));
  }
  return label;
}

async function expectAnyVisible(page, texts, label) {
  currentStep = label;
  try {
    const matched = await page.waitForFunction((needles) => {
      const visibleText = Array.from(document.body.querySelectorAll("*"))
        .filter((element) => {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.visibility !== "hidden"
            && style.display !== "none"
            && rect.width > 0
            && rect.height > 0;
        })
        .map((element) => element.textContent)
        .join("\n");
      return needles.find((text) => visibleText.includes(text)) || false;
    }, texts, { timeout: TIMEOUT_MS });
    return matched.jsonValue();
  } catch (error) {
    throw new Error(await buildStepError(page, `Timed out waiting for any of "${texts.join(", ")}"`, error));
  }
}

async function expectVisibleOrKnownError(page, successText, knownErrorTexts, label) {
  currentStep = label;
  try {
    await page.waitForFunction(({ success, errors }) => {
      const visibleText = Array.from(document.body.querySelectorAll("*"))
        .filter((element) => {
          const style = window.getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.visibility !== "hidden"
            && style.display !== "none"
            && rect.width > 0
            && rect.height > 0;
        })
        .map((element) => element.textContent)
        .join("\n");
      if (visibleText.includes(success)) return { type: "success" };
      const matchedError = errors.find((text) => visibleText.includes(text));
      if (matchedError) return { type: "known-error", message: matchedError };
      return false;
    }, { success: successText, errors: knownErrorTexts }, { timeout: TIMEOUT_MS });
  } catch (error) {
    throw new Error(await buildStepError(page, `Timed out waiting for "${successText}"`, error));
  }

  const visibleText = await getVisibleText(page);
  const matchedError = knownErrorTexts.find((text) => visibleText.includes(text));
  if (matchedError) {
    throw new Error(await buildStepError(page, `Known app error: ${matchedError}`));
  }

  return label;
}

async function getVisibleText(page) {
  return page.evaluate(() => {
    return Array.from(document.body.querySelectorAll("*"))
      .filter((element) => {
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.visibility !== "hidden"
          && style.display !== "none"
          && rect.width > 0
          && rect.height > 0;
      })
      .map((element) => element.textContent)
      .join("\n")
      .replace(/\s+/g, " ")
      .slice(0, 1200);
  });
}

async function buildStepError(page, message, cause = null) {
  const visibleText = maskSensitiveText(await getVisibleText(page).catch(() => ""));
  const diagnostics = await page.evaluate(() => {
    const profileSave = document.querySelector(".profile-primary-btn");
    return {
      profileSaveText: profileSave?.textContent || "",
      profileSaveDisabled: profileSave?.disabled ?? null,
      profileNameValue: document.querySelector(".profile-field input")?.value || "",
      profileInputs: Array.from(document.querySelectorAll(".profile-field input")).map((input) => input.value),
    };
  }).catch(() => null);
  return [
    message,
    `step=${currentStep}`,
    `url=${page.url()}`,
    visibleText ? `visibleText=${visibleText}` : "",
    diagnostics ? `diagnostics=${maskSensitiveText(JSON.stringify(diagnostics))}` : "",
    networkEvents.length ? `networkEvents=${JSON.stringify(networkEvents.slice(-12), null, 2)}` : "",
    cause?.message ? `cause=${cause.message}` : "",
  ].filter(Boolean).join("\n");
}

async function clickVisibleText(page, text) {
  currentStep = `click ${text}`;
  await expectVisible(page, text, `${text} visible`);
  const items = await page.getByText(text, { exact: true }).all();
  for (const item of items) {
    if (await item.isVisible()) {
      await item.click();
      return;
    }
  }
  throw new Error(`Visible text not found: ${text}`);
}

async function clickVisibleButtonText(page, text, label = `click button ${text}`) {
  currentStep = label;
  await expectVisible(page, text, `${text} visible`);
  const items = await page.locator("button").filter({ hasText: text }).all();
  for (const item of items) {
    if (await item.isVisible()) {
      const actualText = (await item.textContent())?.trim() || "";
      if (actualText === text) {
        await item.click();
        return;
      }
    }
  }
  throw new Error(await buildStepError(page, `Visible button not found: ${text}`));
}

async function clickTab(page, label) {
  currentStep = `click tab ${label}`;
  const clicked = await page.evaluate((targetLabel) => {
    const items = Array.from(document.querySelectorAll(".mobile-nav-item, .sidebar-item"));
    const visibleItem = items.find((element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.visibility !== "hidden"
        && style.display !== "none"
        && rect.width > 0
        && rect.height > 0
        && element.textContent.trim().endsWith(targetLabel);
    });

    if (!visibleItem) return false;
    visibleItem.click();
    return true;
  }, label);

  if (!clicked) {
    throw new Error(await buildStepError(page, `Visible tab not found: ${label}`));
  }
}

async function fillFieldByLabel(page, label, value) {
  currentStep = `fill ${label}`;
  const field = page.locator(".auth-field, .profile-field").filter({ hasText: label }).locator("input").first();
  await field.waitFor({ state: "visible", timeout: TIMEOUT_MS });
  await field.fill(value);
}

async function fillProfileFieldIfEditable(page, label, value) {
  currentStep = `fill ${label}`;
  const field = page.locator(".profile-field").filter({ hasText: label }).locator("input").first();
  await field.waitFor({ state: "visible", timeout: TIMEOUT_MS });
  const isReadOnly = await field.evaluate((input) => Boolean(input.readOnly));
  if (!isReadOnly) await field.fill(value);
}

async function fillProfileTextareaByLabel(page, label, value) {
  currentStep = `fill ${label}`;
  const field = page.locator(".profile-field").filter({ hasText: label }).locator("textarea").first();
  await field.waitFor({ state: "visible", timeout: TIMEOUT_MS });
  await field.fill(value);
}

async function clickFirstVisible(page, selector, label) {
  currentStep = label;
  try {
    await page.locator(selector).first().waitFor({ state: "visible", timeout: TIMEOUT_MS });
  } catch (error) {
    throw new Error(await buildStepError(page, `Visible element not found: ${label}`, error));
  }

  const items = await page.locator(selector).all();
  for (const item of items) {
    if (await item.isVisible()) {
      await item.click();
      return;
    }
  }
  throw new Error(await buildStepError(page, `Visible element not found: ${label}`));
}

async function waitForDetailModalClosed(page, label) {
  currentStep = label;
  try {
    await page.waitForFunction(() => !document.querySelector(".dmodal-btn-apply"), null, { timeout: TIMEOUT_MS });
  } catch (error) {
    throw new Error(await buildStepError(page, "Detail modal did not close after apply", error));
  }
}

function isIgnorableBrowserConsoleError(message) {
  return message.includes("googleads.g.doubleclick.net")
    || message.includes("pagead/ads")
    || message.includes("ERR_BLOCKED_BY_CLIENT")
    || (ALLOW_NETWORK_DENIED && message.includes("ERR_NETWORK_ACCESS_DENIED"));
}

async function failOnBrowserErrors(errors, browserConsoleErrors) {
  const filteredConsoleErrors = browserConsoleErrors.filter((message) => !isIgnorableBrowserConsoleError(message));

  if (errors.length || filteredConsoleErrors.length) {
    throw new Error(`Browser errors found: ${JSON.stringify({ errors, browserConsoleErrors: filteredConsoleErrors }, null, 2)}`);
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  const browserConsoleErrors = [];

  try {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") {
        const location = message.location();
        browserConsoleErrors.push(`${message.text()} @ ${location.url || "unknown"}`);
      }
    });
    page.on("requestfailed", (request) => {
      const url = request.url();
      if (url.includes("supabase") || url.includes("/rest/") || url.includes("/auth/") || url.includes("/api/social/")) {
        networkEvents.push({
          type: "requestfailed",
          method: request.method(),
          url,
          failure: request.failure()?.errorText || "",
        });
      }
    });
    page.on("response", async (response) => {
      const url = response.url();
      if (response.status() >= 400 || url.includes("supabase") || url.includes("/rest/") || url.includes("/auth/") || url.includes("/api/social/")) {
        const event = {
          type: "response",
          status: response.status(),
          url,
        };
        if (response.status() >= 400) {
          event.body = await response.text().catch(() => "");
          if (event.body.length > 1000) event.body = `${event.body.slice(0, 1000)}...`;
        }
        networkEvents.push(event);
      }
    });
    await page.addInitScript(() => {
      window.open = () => null;
    });

    await page.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await expectVisible(page, "체험단", "home loaded");
    await clickVisibleText(page, "로그인");
    await fillFieldByLabel(page, "이메일", EMAIL);
    await fillFieldByLabel(page, "비밀번호", PASSWORD);
    await clickFirstVisible(page, ".auth-submit", "login submit");
    await expectVisibleOrKnownError(page, "로그인되었습니다", [
      "이메일 또는 비밀번호가 올바르지 않습니다.",
      "Email not confirmed",
      "Invalid login credentials",
      "User not found",
    ], "login success toast");

    await clickTab(page, "마이");
    await expectVisible(page, "계정 정보", "profile page");
    await fillProfileFieldIfEditable(page, "표시 이름", PROFILE_NAME);
    await fillProfileFieldIfEditable(page, "블로그 주소", PROFILE_BLOG_URL);
    await fillProfileFieldIfEditable(page, "이웃수", "123");
    await fillProfileFieldIfEditable(page, "하루 방문자", "456");
    await fillProfileFieldIfEditable(page, "총 방문자", "7890");
    await fillProfileFieldIfEditable(page, "인스타그램 주소", PROFILE_INSTAGRAM_URL);
    await fillProfileFieldIfEditable(page, "팔로워 수", "321");
    await fillProfileFieldIfEditable(page, "유튜브 주소", PROFILE_YOUTUBE_URL);
    await fillProfileFieldIfEditable(page, "구독자 수", "12");
    await fillProfileTextareaByLabel(page, "기본 신청 멘트", PROFILE_MESSAGE);
    await clickFirstVisible(page, ".profile-primary-btn:not([disabled])", "profile save");
    await expectVisibleOrKnownError(page, "프로필을 저장했습니다", [
      "프로필 저장에 실패했습니다.",
      "표시 이름을 입력해 주세요.",
      "블로그 주소 형식을 확인해 주세요.",
      "인스타그램 주소 형식을 확인해 주세요.",
      "유튜브 주소 형식을 확인해 주세요.",
    ], "profile save toast");

    if (YOUTUBE_SYNC_URL) {
      await fillProfileFieldIfEditable(page, "유튜브 주소", YOUTUBE_SYNC_URL);
      await clickFirstVisible(page, ".profile-sync-btn:not([disabled])", "youtube sync");
      await expectVisibleOrKnownError(page, "유튜브 채널 지표를 연동했습니다", [
        "유튜브 연동에 실패했습니다.",
        "유튜브 채널 주소 또는 @핸들을 확인해 주세요.",
        "로그인 세션을 다시 확인해 주세요.",
      ], "youtube sync toast");
    }

    await clickTab(page, "탐색");
    await expectVisible(page, "조건별 목록", "explore page");
    await clickFirstVisible(page, ".ccard-title", "first campaign detail");
    await clickFirstVisible(page, ".dmodal-btn-apply", "apply button");
    await waitForDetailModalClosed(page, "application modal closed");

    await clickTab(page, "현황");
    await expectVisible(page, "지원 현황", "status page");
    await expectAnyVisible(page, ["지원 페이지 열림", "지원완료"], "application status visible");
    await clickVisibleButtonText(page, "지원완료", "status complete button");
    await expectVisible(page, "지원 상태를 저장했습니다", "status update toast");

    const memo = `QA memo ${new Date().toISOString()}`;
    await page.locator(".application-notes textarea").first().fill(memo);
    await page.locator(".application-notes input").first().fill(PROFILE_BLOG_URL);
    await clickVisibleText(page, "메모 저장");
    await expectVisible(page, "메모를 저장했습니다", "memo save toast");

    await clickTab(page, "마이");
    await expectVisible(page, PROFILE_NAME, "profile name reflected");
    await expectVisible(page, "최근 활동", "profile activity");

    await failOnBrowserErrors(errors, browserConsoleErrors);

    console.log(JSON.stringify({
      ok: true,
      baseUrl: BASE_URL,
      email: maskEmail(EMAIL),
      allowedNetworkDenied: ALLOW_NETWORK_DENIED,
      checks: [
        "login",
        "profile channel, metric, and message save",
        ...(YOUTUBE_SYNC_URL ? ["youtube sync"] : []),
        "application record",
        "status update",
        "memo and review URL save",
        "profile activity reflection",
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
