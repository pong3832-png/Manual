from __future__ import annotations

import csv
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse


from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, WebDriverException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TARGET_CSV = PROJECT_ROOT / "data" / "products" / "products_db_category.csv"
USED_COUPANG_URL_LOG_PATH = PROJECT_ROOT / "runtime" / "logs" / "used_coupang_urls.csv"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

K_PRODUCT_NAME = "\uC0C1\uD488\uBA85"
K_KEYWORD = "\uD0A4\uC6CC\uB4DC"
K_SOURCE_URL = "\uC0C1\uD488\uC6D0\uBCF8URL"
K_COUPANG_LINK = "\uCFE0\uD321\uB9C1\uD06C"
K_CATEGORY = "\uCE74\uD14C\uACE0\uB9AC"
K_PRICE = "\uAC00\uACA9"
K_DISCOUNT = "\uD560\uC778\uC728"
K_ROCKET = "\uB85C\uCF13\uC815\uBCF4"
K_RATING = "\uD3C9\uC810"
K_REVIEW = "\uB9AC\uBDF0\uC218"

CATEGORY_NAME = "\uC2DD\uD488 > \uAC74\uAC15\uC2DD\uD488"
COUPANG_HOME_URL = "https://www.coupang.com/"
GOOGLE_HOME_URL = "https://www.google.com/"
ROCKET_DELIVERY_URL = "https://www.coupang.com/np/campaigns/82"
FOOD_COMPONENT_URL = "https://www.coupang.com/np/campaigns/82/components/194176"
HEALTH_FOOD_URL = "https://www.coupang.com/np/campaigns/82/components/195976"

PRODUCT_LIST_SELECTOR = "#product-list"
PRODUCT_ITEM_SELECTOR = "#product-list > li.ProductUnit_productUnit__Qd6sv"

STOPWORDS = {
    "\uAD6D\uB0B4\uC0B0",
    "\uC815\uD488",
    "\uC138\uD2B8",
    "\uB300\uC6A9\uB7C9",
    "\uBB34\uB8CC\uBC30\uC1A1",
    "\uB85C\uCF13\uBC30\uC1A1",
    "\uAC00\uC815\uC6A9",
    "\uC2E0\uD615",
    "\uD504\uB9AC\uBBF8\uC5C4",
    "\uAC74\uAC15\uC2DD\uD488",
}


def _canonical_coupang_url(raw_url: str) -> str:
    value = (raw_url or "").strip().replace("&amp;", "&")
    match = re.search(r"https?://[^\s\"'<>]+", value)
    if match:
        value = match.group(0)
    return value.strip().strip(".,);]}'\"")


def _coupang_product_key(raw_url: str) -> str:
    url = _canonical_coupang_url(raw_url)
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    query = parse_qs(parsed.query)

    page_key = (query.get("pageKey") or [""])[0].strip()
    if page_key:
        return f"product:{page_key}"

    path_match = re.search(r"/(?:vp/)?products/(\d+)", parsed.path)
    if path_match:
        return f"product:{path_match.group(1)}"

    if "ads-partners.coupang.com" in host:
        return ""
    if "coupang.com" in host or "coupa.ng" in host:
        return f"url:{url}"
    return ""


def _load_used_coupang_url_keys(path: Path | None = None) -> set[str]:
    path = path or USED_COUPANG_URL_LOG_PATH
    if not path.exists():
        return set()
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return {
            key
            for key in (
                _coupang_product_key(row.get("coupang_url", ""))
                for row in csv.DictReader(f)
            )
            if key
        }


@dataclass
class ProductRow:
    product_name: str
    product_keyword: str
    source_url: str
    category_name: str
    price: int
    discount_rate: int
    rocket_badges: str
    rating: float
    review_count: int

    def to_csv_row(self) -> dict[str, object]:
        return {
            "상품명": self.product_name,
            "키워드": self.product_keyword,
            "쿠팡링크": self.source_url,
            "카테고리": self.category_name,
            "상품군": "",
            "계절태그": "",
            "대상독자": "",
            "사용장소": "",
            "문제상황": "",
            "장점1": "",
            "장점2": "",
            "장점3": "",
            "주의점": "",
            "글관점": "",
            "제목시드": "",
            "썸네일프롬프트": "",
            "CTA문구": "",
            "used": "",
            "used_at": "",
            "post_title": "",
        }


def create_driver() -> webdriver.Chrome:
    debugger_address = os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip()
    options = Options()

    if debugger_address:
        options.add_experimental_option("debuggerAddress", debugger_address)
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
        if chromedriver_path and Path(chromedriver_path).exists():
            driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
        else:
            driver = webdriver.Chrome(options=options)
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        driver.maximize_window()
        print(f"[debug] attached tab url: {driver.current_url}")
        return driver

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=ko-KR")
    options.add_argument(f"--user-agent={os.getenv('COUPANG_USER_AGENT', DEFAULT_USER_AGENT)}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    profile_path = os.getenv("COUPANG_PROFILE_PATH", "").strip()
    if profile_path:
        Path(profile_path).mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument("--profile-directory=Default")

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
    if chromedriver_path and Path(chromedriver_path).exists():
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=options)
    else:
        driver = webdriver.Chrome(options=options)

    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {
            "userAgent": os.getenv("COUPANG_USER_AGENT", DEFAULT_USER_AGENT),
            "acceptLanguage": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "platform": "Windows",
        },
    )
    driver.execute_cdp_cmd(
        "Network.setExtraHTTPHeaders",
        {
            "headers": {
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": GOOGLE_HOME_URL,
                "Upgrade-Insecure-Requests": "1",
            }
        },
    )
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'language', {get: () => 'ko-KR'});
                Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            """
        },
    )
    return driver


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def get_expected_item_count() -> int:
    raw = os.getenv("COUPANG_EXPECTED_ITEM_COUNT", "").strip()
    if raw.isdigit():
        return max(1, min(int(raw), 120))
    return 120


def human_pause(base_seconds: float = 2.0, spread_seconds: float = 1.4) -> None:
    time.sleep(base_seconds + (spread_seconds * 0.5))


def is_access_denied(driver: webdriver.Chrome) -> bool:
    page_source = (driver.page_source or "").lower()
    current_url = (driver.current_url or "").lower()
    blocked_markers = [
        "you don't have permission to access",
        "errors.edgesuite.net",
        "access denied",
        "reference #",
        "bot verification",
        "captcha",
    ]
    return any(marker in page_source for marker in blocked_markers) or "errors.edgesuite.net" in current_url


def wait_for_manual_clear_if_debugger(driver: webdriver.Chrome, seconds: int = 90) -> bool:
    if not os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip():
        return False

    print("[info] debugger mode detected; waiting for manual unblock in Chrome")
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not is_access_denied(driver):
            try:
                items = driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)
                if items:
                    return True
            except Exception:
                pass
        time.sleep(2)
    return False


def warm_up_coupang_session(driver: webdriver.Chrome) -> None:
    try:
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
        driver.get(GOOGLE_HOME_URL)
        time.sleep(1.5)
        driver.get(COUPANG_HOME_URL)
        time.sleep(3)
    except NoSuchWindowException as exc:
        raise TimeoutException("chrome window was closed during warm-up") from exc
    except WebDriverException as exc:
        raise TimeoutException(f"failed to warm up browser session: {exc.msg}") from exc


def wait_for_products(driver: webdriver.Chrome) -> list:
    for _ in range(18):
        items = driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)
        if items:
            return items
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.2)

    WebDriverWait(driver, 8).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_LIST_SELECTOR))
    )
    return driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)


def safe_click(driver: webdriver.Chrome, locator: tuple[str, str], timeout: int = 10) -> None:
    element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    human_pause(0.8, 0.4)
    driver.execute_script("arguments[0].click();", element)
    human_pause(2.0, 0.8)


def open_health_food_category(driver: webdriver.Chrome) -> None:
    warm_up_coupang_session(driver)
    driver.get(COUPANG_HOME_URL)
    human_pause(2.0, 1.0)

    safe_click(driver, (By.CSS_SELECTOR, f'a[href="{ROCKET_DELIVERY_URL}"]'))
    safe_click(driver, (By.CSS_SELECTOR, f'a[href="{FOOD_COMPONENT_URL}"]'))
    safe_click(driver, (By.CSS_SELECTOR, f'a[href="{HEALTH_FOOD_URL}"]'))


def apply_sales_sort(driver: webdriver.Chrome) -> None:
    sorter_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[id="sorter-SALES_COUNT"]'))
    )
    if sorter_input.is_selected():
        return

    safe_click(driver, (By.CSS_SELECTOR, 'label[for="sorter-SALES_COUNT"]'))
    WebDriverWait(driver, 10).until(
        lambda current_driver: current_driver.find_element(
            By.CSS_SELECTOR, 'input[id="sorter-SALES_COUNT"]'
        ).is_selected()
    )


def apply_list_size_120(driver: webdriver.Chrome) -> None:
    option_120_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[id="listSize-120"]'))
    )
    if option_120_input.is_selected():
        return

    selected_size = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "li.ListSizeOption_selected__Ym5KI"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", selected_size)
    ActionChains(driver).move_to_element(selected_size).pause(1.0).perform()
    human_pause(0.8, 0.4)

    option_120_label = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'label[for="listSize-120"]'))
    )
    driver.execute_script("arguments[0].click();", option_120_label)
    human_pause(2.0, 1.0)
    WebDriverWait(driver, 10).until(
        lambda current_driver: current_driver.find_element(
            By.CSS_SELECTOR, 'input[id="listSize-120"]'
        ).is_selected()
    )


def prepare_listing(driver: webdriver.Chrome) -> None:
    if is_access_denied(driver):
        if wait_for_manual_clear_if_debugger(driver):
            return
        raise TimeoutException("blocked while opening health food listing")

    wait_for_products(driver)
    apply_sales_sort(driver)
    wait_for_products(driver)
    apply_list_size_120(driver)
    wait_for_products(driver)


def collect_scrolled_products(
    driver: webdriver.Chrome,
    expected_count: int = 120,
    max_scrolls: int = 50,
    pause_seconds: float = 1.1,
    stable_round_limit: int = 5,
) -> list:
    stable_rounds = 0
    items = wait_for_products(driver)
    last_count = len(items)

    for _ in range(max_scrolls):
        driver.execute_script("window.scrollBy(0, Math.max(window.innerHeight * 0.8, 700));")
        time.sleep(pause_seconds)
        items = driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)
        current_count = len(items)

        if current_count >= expected_count:
            break

        if current_count <= last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
            last_count = current_count

        if stable_rounds >= stable_round_limit:
            break

    print(f"[crawl] collected visible products after scroll: {len(items)}")
    return items[:expected_count]


def clean_number(text: str) -> int:
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else 0


def clean_rating(text: str) -> float:
    try:
        return float((text or "").strip())
    except ValueError:
        return 0.0


def clean_discount(text: str) -> int:
    return clean_number(text)


def extract_rocket_badges(item) -> str:
    badge_names: list[str] = []
    badge_map = {
        "ROCKET": "\uB85C\uCF13\uBC30\uC1A1",
        "ROCKET_MERCHANT": "\uB85C\uCF13\uC81C\uD734",
        "TOMORROW": "\uB0B4\uC77C\uB3C4\uCC29",
    }

    for badge in item.find_elements(By.CSS_SELECTOR, "img[data-badge-id]"):
        badge_id = (badge.get_attribute("data-badge-id") or "").strip()
        if badge_id and badge_id in badge_map:
            badge_names.append(badge_map[badge_id])

    return ", ".join(dict.fromkeys(badge_names))


def extract_product_keyword(name: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", name)
    tokens = [token for token in cleaned.split() if len(token) >= 2 and token not in STOPWORDS]
    if not tokens:
        return name[:20]
    return " ".join(dict.fromkeys(tokens[:3]))[:30].strip() or name[:20]


def build_row(
    product_name: str,
    source_url: str,
    category_name: str,
    price: int,
    discount_rate: int,
    rocket_badges: str,
    rating: float,
    review_count: int,
) -> ProductRow:
    return ProductRow(
        product_name=product_name,
        product_keyword=extract_product_keyword(product_name),
        source_url=source_url,
        category_name=category_name,
        price=price,
        discount_rate=discount_rate,
        rocket_badges=rocket_badges,
        rating=rating,
        review_count=review_count,
    )


def scrape_products(driver: webdriver.Chrome) -> list[ProductRow]:
    collected: list[ProductRow] = []
    seen_names: set[str] = set()
    seen_urls: set[str] = set()

    print(f"[crawl] {CATEGORY_NAME}")
    open_health_food_category(driver)
    prepare_listing(driver)

    expected_count = get_expected_item_count()
    items = collect_scrolled_products(driver, expected_count=expected_count)
    print(f"[crawl] parsing page 1 / visible items {len(items)}")

    for item in items:
        try:
            product_name = item.find_element(By.CSS_SELECTOR, "div.ProductUnit_productNameV2__cV9cw").text.strip()
            normalized_name = normalize_text(product_name)
            if not product_name or normalized_name in seen_names:
                continue

            price = clean_number(item.find_element(By.CSS_SELECTOR, "strong.Price_priceValue__A4KOr").text)
            try:
                discount_rate = clean_discount(item.find_element(By.CSS_SELECTOR, "span.PriceInfo_discountRate__EsQ8I").text)
            except Exception:
                discount_rate = 0

            rocket_badges = extract_rocket_badges(item)
            rating = clean_rating(item.find_element(By.CSS_SELECTOR, "div.ProductRating_star__RGSlV").text)
            review_count = clean_number(item.find_element(By.CSS_SELECTOR, "span.ProductRating_ratingCount__R0Vhz").text)

            href = item.find_element(By.CSS_SELECTOR, 'a[href*="/vp/products/"]').get_attribute("href") or ""
            product_link = href.split("?")[0]
            if not product_link or product_link in seen_urls:
                continue

            collected.append(
                build_row(
                    product_name=product_name,
                    source_url=product_link,
                    category_name=CATEGORY_NAME,
                    price=price,
                    discount_rate=discount_rate,
                    rocket_badges=rocket_badges,
                    rating=rating,
                    review_count=review_count,
                )
            )
            seen_names.add(normalized_name)
            seen_urls.add(product_link)
        except Exception:
            continue

    print(f"[crawl] page 1 added {len(collected)} products")

    return collected


def filter_products(rows: Iterable[ProductRow]) -> list[ProductRow]:
    return list(rows)


def save_products(rows: Iterable[ProductRow], output_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print("[save] no products to store")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    fieldnames = list(rows[0].to_csv_row().keys())

    existing_url_keys = set()
    used_url_keys = _load_used_coupang_url_keys()
    used_names = set()
    if file_exists:
        with output_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                link = r.get("쿠팡링크", "").strip()
                link_key = _coupang_product_key(link)
                if link_key:
                    existing_url_keys.add(link_key)
                used = (r.get("used", "") or "").strip().upper()
                post_title = (r.get("post_title", "") or "").strip()
                if used == "Y" or post_title:
                    if link_key:
                        used_url_keys.add(link_key)
                    name = (r.get("상품명", "") or "").strip()
                    if name:
                        used_names.add(name)

    added_count = 0
    with output_path.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            row_dict = row.to_csv_row()
            grade = (row_dict.get("추천등급", "") or row_dict.get("등급", "")).strip()
            if grade and grade != "A":
                continue
            row_url = row_dict.get("쿠팡링크", "").strip()
            row_name = row_dict.get("상품명", "").strip()
            row_key = _coupang_product_key(row_url)
            if not row_key:
                continue
            if row_key in existing_url_keys:
                continue
            if row_key in used_url_keys or row_name in used_names:
                continue
            writer.writerow(row_dict)
            existing_url_keys.add(row_key)
            added_count += 1

    print(f"[done] Appended {added_count} new rows to {output_path}")


def main() -> None:
    driver = create_driver()
    debugger_mode = bool(os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip())
    try:
        print("[start] building health food candidates")
        if debugger_mode:
            print("[info] using existing Chrome session via remote debugger")
        print(f"[filter] expected_item_count={get_expected_item_count()}")
        rows = scrape_products(driver)
        selected = filter_products(rows)
        save_products(selected, TARGET_CSV)
    finally:
        if debugger_mode:
            print("[info] keeping attached Chrome session open")
        else:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()


