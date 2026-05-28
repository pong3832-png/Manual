from __future__ import annotations

import csv
import os
import re
import socket
import subprocess
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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
K_SCORE = "\uC810\uC218"
K_SCENARIO = "\uBB38\uC81C\uC0C1\uD669"
K_TARGET = "\uB300\uC0C1\uB3C5\uC790"
K_PLACE = "\uC0AC\uC6A9\uC7A5\uC18C"
K_SEASON = "\uC2DC\uC98C\uD0DC\uADF8"
K_PAIN = "\uBD88\uD3B8\uD3EC\uC778\uD2B8"
K_POINT1 = "\uC7A5\uC8101"
K_POINT2 = "\uC7A5\uC8102"
K_POINT3 = "\uC7A5\uC8103"
K_CAUTION = "\uC8FC\uC758\uC810"
K_INTENT = "\uAC80\uC0C9\uC758\uB3C4"
K_ANGLE = "\uAE00\uAD00\uC810"
K_TITLE_SEED = "\uC81C\uBAA9\uC2DC\uB4DC"
K_THUMBNAIL = "\uC378\uB124\uC77C\uD504\uB86C\uD504\uD2B8"
K_CTA = "CTA\uBB38\uAD6C"
K_DISCLOSURE = "\uAD11\uACE0\uACE0\uC9C0\uBB38"
K_USED = "used"
K_USED_AT = "used_at"
K_POST_TITLE = "post_title"
K_CLICK_PRIORITY = "click_priority"

COUPANG_HOME_URL = "https://www.coupang.com/"
GOOGLE_HOME_URL = "https://www.google.com/"
ROCKET_DELIVERY_URL = "https://www.coupang.com/np/campaigns/82"

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
}

DISCLOSURE_TEXT = (
    "\uC774 \uD3EC\uC2A4\uD305\uC740 \uCFE0\uD321 \uD30C\uD2B8\uB108\uC2A4 \uD65C\uB3D9\uC758 "
    "\uC77C\uD658\uC73C\uB85C, \uC774\uC5D0 \uB530\uB978 \uC77C\uC815\uC561\uC758 "
    "\uC218\uC218\uB8CC\uB97C \uC81C\uACF5\uBC1B\uC2B5\uB2C8\uB2E4."
)


TARGET_CATEGORY_NAME = "가전디지털"
TARGET_SUBCATEGORY_NAME = "가전디지털"
TARGET_PRODUCT_NAME = "가전디지털"
MIN_PRODUCT_PRICE = 0
TARGET_PRODUCT_COUNT = 150
ROCKET_DIGITAL_COMPONENT_URL = "https://www.coupang.com/np/campaigns/82/components/178155"
ROCKET_SEASONAL_COMPONENT_URL = "https://www.coupang.com/np/campaigns/82/components/227712"
DEFAULT_DEBUG_CHROME_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]
DEFAULT_DEBUG_PROFILE = Path.home() / "ChromeCoupangDebugStable"


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

    @staticmethod
    def _format_price(price: int) -> str:
        return f"{price:,}원" if price else ""

    def to_csv_row(self) -> dict[str, object]:
        return {
            "상품명": self.product_name,
            "키워드": self.product_keyword,
            "쿠팡링크": self.source_url,
            "카테고리": self.category_name,
            "가격": self._format_price(self.price),
            "할인율": self.discount_rate,
            "로켓정보": self.rocket_badges,
            "평점": self.rating,
            "리뷰수": self.review_count,
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


def _parse_debugger_address(debugger_address: str) -> tuple[str, int]:
    host, port_text = debugger_address.rsplit(":", 1)
    return host.strip(), int(port_text.strip())


def _is_debugger_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _resolve_debug_chrome_path() -> Path:
    custom = os.getenv("COUPANG_CHROME_PATH", "").strip()
    if custom:
        path = Path(custom)
        if path.exists():
            return path

    for path in DEFAULT_DEBUG_CHROME_PATHS:
        if path.exists():
            return path

    raise FileNotFoundError("could not find a stable Chrome executable for debugger launch")


def _ensure_debugger_browser(debugger_address: str) -> None:
    host, port = _parse_debugger_address(debugger_address)
    if _is_debugger_port_open(host, port):
        return

    chrome_path = _resolve_debug_chrome_path()
    profile_path = Path(os.getenv("COUPANG_DEBUG_PROFILE", "").strip() or DEFAULT_DEBUG_PROFILE)
    profile_path.mkdir(parents=True, exist_ok=True)

    print(f"[debug] launching Chrome automatically: {chrome_path}")
    subprocess.Popen(
        [
            str(chrome_path),
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_path}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.time() + 15
    while time.time() < deadline:
        if _is_debugger_port_open(host, port):
            time.sleep(1.0)
            return
        time.sleep(0.5)

    raise TimeoutException(f"debugger Chrome did not open on {debugger_address}")


def _candidate_chromedriver_paths() -> list[Path]:
    configured = os.getenv("CHROMEDRIVER_PATH", "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))

    candidates.extend(
        [
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.117" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.56" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "146.0.7680.165" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "145.0.7632.117" / "chromedriver.exe",
        ]
    )

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        resolved = str(path)
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _create_attached_driver(options: Options) -> webdriver.Chrome:
    last_error: Exception | None = None
    for chromedriver_path in _candidate_chromedriver_paths():
        try:
            print(f"[debug] trying chromedriver: {chromedriver_path}")
            return webdriver.Chrome(service=Service(str(chromedriver_path)), options=options)
        except Exception as exc:
            last_error = exc
            print(f"[warn] chromedriver attach failed: {chromedriver_path} -> {exc}")

    if last_error is not None:
        raise last_error
    return webdriver.Chrome(options=options)


def create_driver() -> webdriver.Chrome:
    debugger_address = os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip()
    options = Options()

    if debugger_address:
        _ensure_debugger_browser(debugger_address)
        options.add_experimental_option("debuggerAddress", debugger_address)
        driver = _create_attached_driver(options)
        if driver.window_handles:
            chosen_handle = driver.window_handles[0]
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    current_url = (driver.current_url or "").lower()
                    if "coupang.com" in current_url:
                        chosen_handle = handle
                        break
                except Exception:
                    continue
            driver.switch_to.window(chosen_handle)
        try:
            driver.maximize_window()
        except WebDriverException:
            pass
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


def wait_for_products(driver: webdriver.Chrome) -> list:
    product_list_selector = "#product-list"
    product_item_selector = "#product-list > li"

    for _ in range(18):
        items = driver.find_elements(By.CSS_SELECTOR, product_item_selector)
        if items:
            return items

        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1.5)

        if driver.find_elements(By.CSS_SELECTOR, product_list_selector):
            items = driver.find_elements(By.CSS_SELECTOR, product_item_selector)
            if items:
                return items

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, product_list_selector))
    )
    return driver.find_elements(By.CSS_SELECTOR, product_item_selector)


def collect_scrolled_products(
    driver: webdriver.Chrome,
    max_scrolls: int = 40,
    pause_seconds: float = 1.2,
    stable_round_limit: int = 4,
) -> list:
    product_item_selector = "#product-list > li"
    last_count = 0
    stable_rounds = 0

    items = wait_for_products(driver)

    for _ in range(max_scrolls):
        current_count = len(items)
        driver.execute_script("window.scrollBy(0, Math.max(window.innerHeight, 1200));")
        time.sleep(pause_seconds)
        items = driver.find_elements(By.CSS_SELECTOR, product_item_selector)

        if len(items) <= current_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= stable_round_limit:
            break

        last_count = len(items)

    if last_count:
        print(f"[crawl] collected visible products after scroll: {last_count}")
    return items


def get_max_pages() -> int:
    raw = os.getenv("COUPANG_MAX_PAGES", "").strip()
    if raw.isdigit():
        return max(1, min(int(raw), 50))
    return 10


def human_pause(base_seconds: float = 2.0, spread_seconds: float = 1.4) -> None:
    time.sleep(base_seconds + (spread_seconds * 0.5))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def get_min_reviews() -> int:
    raw = os.getenv("COUPANG_MIN_REVIEWS", "").strip()
    if raw.isdigit():
        return max(0, int(raw))
    return 80


def get_min_rating() -> float:
    raw = os.getenv("COUPANG_MIN_RATING", "").strip()
    try:
        if raw:
            return max(0.0, min(float(raw), 5.0))
    except ValueError:
        pass
    return 4.2


def get_excluded_keywords() -> set[str]:
    raw = os.getenv("COUPANG_EXCLUDE_KEYWORDS", "").strip()
    if not raw:
        return set()
    tokens = [normalize_text(token) for token in raw.split(",")]
    return {token for token in tokens if token}


def get_target_product_count(default_count: int = TARGET_PRODUCT_COUNT) -> int:
    raw = os.getenv("TARGET_PRODUCT_COUNT", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return default_count


def load_existing_products(db_path: Path) -> tuple[set[str], set[str]]:
    existing_names: set[str] = set()
    existing_urls: set[str] = set()

    if not db_path.exists():
        return existing_names, existing_urls

    try:
        with db_path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                existing_name = normalize_text(row.get(K_PRODUCT_NAME, ""))
                existing_url = (row.get(K_COUPANG_LINK, "") or row.get(K_SOURCE_URL, "")).strip()
                if existing_name:
                    existing_names.add(existing_name)
                if existing_url:
                    existing_urls.add(existing_url)
    except Exception as exc:
        print(f"[warn] failed to load existing products: {exc}")

    return existing_names, existing_urls


def load_existing_csv_rows(db_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return [], []

    with db_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), (reader.fieldnames or [])


def ensure_csv_schema(output_path: Path, fieldnames: list[str]) -> None:
    existing_rows, existing_fieldnames = load_existing_csv_rows(output_path)
    if not existing_rows and not existing_fieldnames:
        return
    if existing_fieldnames == fieldnames:
        return

    normalized_rows: list[dict[str, str]] = []
    for row in existing_rows:
        normalized_rows.append({field: row.get(field, "") for field in fieldnames})

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)
    print("[save] upgraded CSV schema with latest columns")


def open_page_via_click(driver: webdriver.Chrome, page_number: int) -> bool:
    try:
        if page_number == 1:
            return True

        candidates = driver.find_elements(By.CSS_SELECTOR, f'a[href*="page={page_number}"]')
        for candidate in candidates:
            if candidate.text.strip() == str(page_number):
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", candidate)
                human_pause(1.2, 0.8)
                driver.execute_script("arguments[0].click();", candidate)
                human_pause(3.2, 1.4)
                return True
    except Exception:
        return False

    return False


def build_page_url(current_url: str, page_number: int) -> str:
    parsed = urlsplit(current_url)
    query_pairs = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() != "page"]
    query_pairs.append(("page", str(page_number)))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query_pairs), parsed.fragment))


def open_page_number(driver: webdriver.Chrome, base_url: str, page_number: int) -> list:
    if page_number == 1:
        if driver.current_url != base_url:
            driver.get(base_url)
            human_pause(3.0, 1.5)
    else:
        opened = open_page_via_click(driver, page_number)
        if not opened:
            page_url = build_page_url(base_url, page_number)
            driver.get(page_url)
            human_pause(3.0, 1.5)

    if is_access_denied(driver):
        if wait_for_manual_clear(driver):
            return collect_scrolled_products(driver)
        raise TimeoutException(f"blocked on category page {page_number}")

    return collect_scrolled_products(driver)


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
        "자동화된 접근",
        "비정상적인 접근",
        "접근이 제한",
    ]
    return any(marker in page_source for marker in blocked_markers) or "errors.edgesuite.net" in current_url


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


def wait_for_manual_clear(driver: webdriver.Chrome, seconds: int = 90) -> bool:
    print("[info] waiting for manual unblock in Chrome...")
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not is_access_denied(driver):
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "#product-list > li")
                if items:
                    return True
            except Exception:
                pass
        time.sleep(2)
    return False


def _click_link_by_href(driver: webdriver.Chrome, href: str, timeout: int = 10) -> None:
    link = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, f"//a[@href='{href}']"))
    )
    try:
        ActionChains(driver).move_to_element(link).pause(0.2).click(link).perform()
    except Exception:
        driver.execute_script("arguments[0].click();", link)
    time.sleep(2.0)


def click_sales_count_sort(driver: webdriver.Chrome, timeout: int = 10) -> None:
    sort_input_xpath = "//input[@id='sorter-SALES_COUNT']"
    sort_label_xpath = "//label[@for='sorter-SALES_COUNT' and normalize-space()='판매량순']"

    sort_label = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, sort_label_xpath))
    )
    sort_input = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, sort_input_xpath))
    )

    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", sort_label)
    except Exception:
        pass

    for _ in range(3):
        try:
            ActionChains(driver).move_to_element(sort_label).pause(0.2).click(sort_label).perform()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", sort_label)
            except Exception:
                driver.execute_script("arguments[0].click();", sort_input)

        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.find_element(By.XPATH, sort_input_xpath).is_selected()
            )
            time.sleep(2.5)
            return
        except Exception:
            time.sleep(1.0)

    raise TimeoutException("failed to apply sales count sort")


def click_target_product(driver: webdriver.Chrome, timeout: int = 10) -> None:
    target_text = TARGET_PRODUCT_NAME.strip()
    target_xpath = (
        "//a[normalize-space()=$name] | "
        "//button[normalize-space()=$name] | "
        "//span[normalize-space()=$name]/ancestor::a[1] | "
        "//span[normalize-space()=$name]/ancestor::button[1]"
    )

    target = WebDriverWait(driver, timeout).until(
        lambda d: d.find_element(By.XPATH, target_xpath.replace("$name", f"'{target_text}'"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
    time.sleep(0.8)
    try:
        ActionChains(driver).move_to_element(target).pause(0.2).click(target).perform()
    except Exception:
        driver.execute_script("arguments[0].click();", target)
    time.sleep(2.5)


def click_category_flow(driver: webdriver.Chrome) -> None:
    driver.get(ROCKET_DELIVERY_URL)
    time.sleep(2.5)
    _click_link_by_href(driver, ROCKET_DIGITAL_COMPONENT_URL)
    _click_link_by_href(driver, ROCKET_SEASONAL_COMPONENT_URL)


def open_category_page(driver: webdriver.Chrome) -> list:
    warm_up_coupang_session(driver)

    for attempt in range(1, 4):
        try:
            click_category_flow(driver)
        except TimeoutException:
            print(f"[retry] category open timeout on attempt {attempt}: {TARGET_SUBCATEGORY_NAME}")
            if wait_for_manual_clear(driver, seconds=120):
                return wait_for_products(driver)
            time.sleep(3 * attempt)
            warm_up_coupang_session(driver)
            continue

        if is_access_denied(driver):
            print(f"[retry] access denied on attempt {attempt}: {TARGET_SUBCATEGORY_NAME}")
            if wait_for_manual_clear(driver):
                return wait_for_products(driver)
            time.sleep(5 * attempt)
            warm_up_coupang_session(driver)
            continue

        try:
            return wait_for_products(driver)
        except TimeoutException:
            print(f"[retry] product wait timeout on attempt {attempt}: {TARGET_SUBCATEGORY_NAME}")
            time.sleep(3 * attempt)
            warm_up_coupang_session(driver)

    raise TimeoutException(f"failed to open category page: {TARGET_SUBCATEGORY_NAME}")


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
        "ROCKET": "로켓배송",
        "ROCKET_MERCHANT": "로켓판매자",
        "TOMORROW": "내일도착",
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

    intent_tokens = []
    for token in tokens:
        if any(key in token for key in ("\uC6D0\uB8F8", "\uC790\uCDE8", "\uC0AC\uBB34\uC2E4", "\uBB34\uC120", "\uBBF8\uB2C8", "\uC800\uC18C\uC74C", "\uAC00\uC131\uBE44", "\uD734\uB300\uC6A9")):
            intent_tokens.append(token)

    selected = (intent_tokens + tokens)[:3]
    return " ".join(dict.fromkeys(selected))[:30].strip() or name[:20]


def infer_metadata(product_name: str, keyword: str, category_name: str) -> dict[str, str]:
    base = {
        K_SCENARIO: f"{keyword}\uC774 \uD544\uC694\uD558\uC9C0\uB9CC \uC5B4\uB5A4 \uC81C\uD488\uC744 \uACE8\uB77C\uC57C \uD560\uC9C0 \uC560\uB9E4\uD560 \uB54C",
        K_TARGET: "\uAD6C\uB9E4 \uC804 \uD6C4\uAE30\uC640 \uD604\uC2E4\uC801\uC778 \uCD94\uCC9C \uD3EC\uC778\uD2B8\uB97C \uD568\uAED8 \uBCF4\uB294 \uC0AC\uB78C",
        K_PLACE: "\uC9D1\uC774\uB098 \uAC1C\uC778 \uC791\uC5C5 \uACF5\uAC04",
        K_SEASON: "\uC0AC\uACC4\uC808",
        K_PAIN: "\uAD11\uACE0\uC131 \uC815\uBCF4\uB294 \uB9CE\uC740\uB370 \uB0B4 \uC0C1\uD669\uC5D0 \uB9DE\uB294 \uD310\uB2E8\uC774 \uC5B4\uB824\uC6B4 \uC810",
        K_POINT1: "\uC2E4\uC0AC\uC6A9 \uAE30\uC900\uC73C\uB85C \uC811\uADFC\uD558\uAE30 \uC26C\uC6B4 \uC810",
        K_POINT2: "\uAC00\uACA9 \uB300\uBE44 \uB9CC\uC871\uB3C4\uB97C \uAE30\uB300\uD558\uAE30 \uC26C\uC6B4 \uC810",
        K_POINT3: "\uD6C4\uAE30\uC640 \uC815\uBCF4\uB7C9\uC774 \uBE44\uAD50\uC801 \uB9CE\uC740 \uC810",
        K_CAUTION: "\uC0AC\uC6A9 \uD658\uACBD\uACFC \uC608\uC0B0\uC5D0 \uB530\uB77C \uB9CC\uC871\uB3C4\uAC00 \uB2EC\uB77C\uC9C8 \uC218 \uC788\uC74C",
        K_INTENT: "\uBB38\uC81C\uD574\uACB0\uD615 \uCD94\uCC9C",
        K_ANGLE: "\uC9C1\uC811 \uC368\uBCF8 \uB4EF\uD55C \uC2E4\uC0AC\uC6A9 \uD6C4\uAE30\uD615",
        K_CTA: "\uC81C\uD488 \uC0C1\uC138\uC815\uBCF4\uC640 \uD604\uC7AC \uAC00\uACA9\uC740 \uC544\uB798 \uB9C1\uD06C\uC5D0\uC11C \uBC14\uB85C \uD655\uC778 \uAC00\uB2A5",
    }

    rules = [
        (
            ("\uAC00\uC2B5\uAE30",),
            {
                K_SCENARIO: "\uC6D0\uB8F8\uC774\uB098 \uBC29 \uC548\uC774 \uAC74\uC870\uD574\uC11C \uC544\uCE68\uB9C8\uB2E4 \uBAA9\uC774 \uCE7C\uCE7C\uD560 \uB54C",
                K_TARGET: "\uC6D0\uB8F8 \uAC70\uC8FC\uC790\uB098 \uBC29\uC5D0\uC11C \uC624\uB798 \uC788\uB294 \uC0AC\uB78C",
                K_PLACE: "\uCE68\uC2E4, \uCC45\uC0C1, \uC6D0\uB8F8",
                K_SEASON: "\uACA8\uC6B8, \uD658\uC808\uAE30",
                K_PAIN: "\uC18C\uC74C\uC774 \uD06C\uAC70\uB098 \uC138\uCC99\uC774 \uBC88\uAC70\uB85C\uC6B0\uBA74 \uC624\uB798 \uC4F0\uAE30 \uD798\uB4E6",
                K_POINT1: "\uAC74\uC870\uD55C \uACF5\uAC04\uC5D0\uC11C \uCCB4\uAC10 \uBCC0\uD654\uAC00 \uBE60\uB978 \uD3B8",
                K_POINT2: "\uCC45\uC0C1\uC774\uB098 \uCE68\uB300 \uC606\uC5D0 \uB450\uAE30 \uC26C\uC6B4 \uD06C\uAE30",
                K_POINT3: "\uAC00\uC2B5\uB7C9\uACFC \uAD00\uB9AC \uD3B8\uC758\uC131 \uADE0\uD615\uC744 \uBCF4\uAE30 \uC88B\uC74C",
                K_CAUTION: "\uD070 \uACF5\uAC04\uC5D0\uC11C\uB294 \uAC00\uC2B5\uB7C9\uC774 \uBD80\uC871\uD558\uAC8C \uB290\uAEF4\uC9C8 \uC218 \uC788\uC74C",
            },
        ),
        (
            ("\uC120\uD48D\uAE30", "\uC368\uD058\uB808\uC774\uD130", "\uB0C9\uD48D\uAE30"),
            {
                K_SCENARIO: "\uC5EC\uB984\uCCA0 \uBC29 \uC548 \uACF5\uAE30\uAC00 \uB2F5\uB2F5\uD558\uACE0 \uC5F4\uAC10\uC774 \uC798 \uBE60\uC9C0\uC9C0 \uC54A\uC744 \uB54C",
                K_TARGET: "\uC790\uCDE8\uC0DD, \uC0AC\uBB34\uC2E4 \uC0AC\uC6A9\uC790, \uB354\uC704\uB97C \uB9CE\uC774 \uD0C0\uB294 \uC0AC\uB78C",
                K_PLACE: "\uC6D0\uB8F8, \uCC45\uC0C1, \uAC70\uC2E4",
                K_SEASON: "\uC5EC\uB984",
                K_PAIN: "\uC18C\uC74C\uC774\uB098 \uBC14\uB78C \uC138\uAE30\uAC00 \uC560\uB9E4\uD558\uBA74 \uD2C0\uC5B4\uB450\uACE0 \uC4F0\uAE30 \uBD88\uD3B8\uD568",
                K_POINT1: "\uC881\uC740 \uACF5\uAC04\uC5D0\uC11C\uB3C4 \uCCB4\uAC10 \uC2DC\uC6D0\uD568\uC744 \uB9CC\uB4E4\uAE30 \uC88B\uC74C",
                K_POINT2: "\uC0C1\uD669\uC5D0 \uB530\uB77C \uC774\uB3D9\uD558\uAC70\uB098 \uBC29\uD5A5 \uC870\uC808\uD558\uAE30 \uD3B8\uD568",
                K_POINT3: "\uC804\uAE30\uC694\uAE08 \uBD80\uB2F4\uC744 \uBE44\uAD50\uC801 \uB35C \uB290\uB07C\uAE30 \uC26C\uC6C0",
                K_CAUTION: "\uB0C9\uBC29\uAE30\uAE30 \uB300\uCCB4\uC7AC\uB77C\uAE30\uBCF4\uB2E4 \uBCF4\uC870\uC6A9\uC73C\uB85C \uBCF4\uB294 \uD3B8\uC774 \uB9DE\uC74C",
            },
        ),
        (
            ("\uC81C\uC2B5\uAE30",),
            {
                K_SCENARIO: "\uC7A5\uB9C8\uCCA0\uC774\uB098 \uBE68\uB798 \uAC74\uC870\uD560 \uB54C \uC9D1 \uC548 \uC2B5\uAE30 \uB54C\uBB38\uC5D0 \uB0C4\uC0C8\uAC00 \uB0A0 \uB54C",
                K_TARGET: "\uC6D0\uB8F8 \uAC70\uC8FC\uC790, \uBE68\uB798\uB97C \uC2E4\uB0B4\uC5D0\uC11C \uB9D0\uB9AC\uB294 \uC0AC\uB78C",
                K_PLACE: "\uC6D0\uB8F8, \uC138\uD0C1\uC2E4, \uB4DC\uB808\uC2A4\uB8F8",
                K_SEASON: "\uC7A5\uB9C8\uCCA0, \uC5EC\uB984",
                K_PAIN: "\uC2B5\uAE30\uAC00 \uC313\uC774\uBA74 \uB0C4\uC0C8\uC640 \uACF0\uD321\uC774 \uB54C\uBB38\uC5D0 \uC2A4\uD2B8\uB808\uC2A4\uAC00 \uD07C",
                K_POINT1: "\uC2E4\uB0B4 \uC2B5\uB3C4 \uAD00\uB9AC \uCCB4\uAC10\uC774 \uBE44\uAD50\uC801 \uBE60\uB978 \uD3B8",
                K_POINT2: "\uBE68\uB798 \uB9D0\uB9B4 \uB54C \uB2F5\uB2F5\uD568\uC744 \uC904\uC774\uAE30 \uC88B\uC74C",
                K_POINT3: "\uACC4\uC808\uC131 \uC218\uC694\uAC00 \uAC15\uD574\uC11C \uAC80\uC0C9 \uC804\uD658\uC774 \uC798 \uB098\uC624\uB294 \uD3B8",
                K_CAUTION: "\uC18C\uC74C\uACFC \uBB3C\uD1B5 \uC6A9\uB7C9\uC740 \uAF2D \uAC19\uC774 \uBD10\uC57C \uD568",
            },
        ),
        (
            ("\uC804\uAE30\uD3EC\uD2B8", "\uC8FC\uC804\uC790"),
            {
                K_SCENARIO: "\uC790\uCDE8\uBC29\uC774\uB098 \uC0AC\uBB34\uC2E4\uC5D0\uC11C \uBB3C\uC744 \uC790\uC8FC \uB04A\uC5EC\uC57C \uD558\uB294\uB370 \uBC88\uAC70\uB85C\uC6B8 \uB54C",
                K_TARGET: "\uC790\uCDE8\uC0DD, \uC0AC\uBB34\uC2E4 \uC0AC\uC6A9\uC790, \uAC04\uB2E8\uD55C \uC870\uB9AC \uC790\uC8FC \uD558\uB294 \uC0AC\uB78C",
                K_PLACE: "\uC8FC\uBC29, \uD0D5\uBE44\uC2E4, \uC6D0\uB8F8",
                K_SEASON: "\uC0AC\uACC4\uC808",
                K_PAIN: "\uB04A\uB294 \uC18D\uB3C4\uC640 \uC138\uCC99 \uD3B8\uC758\uC131\uC774 \uC560\uB9E4\uD558\uBA74 \uAE08\uBC29 \uC190\uC774 \uC548 \uAC10",
                K_POINT1: "\uB77C\uBA74, \uCEE4\uD53C, \uCC28\uCC98\uB7FC \uC989\uC2DC \uD544\uC694\uD55C \uC0C1\uD669\uC5D0 \uC798 \uB9DE\uC74C",
                K_POINT2: "\uACF5\uAC04\uC744 \uB9CE\uC774 \uCC28\uC9C0\uD558\uC9C0 \uC54A\uB294 \uC81C\uD488\uC774 \uB9CE\uC74C",
                K_POINT3: "\uAC00\uACA9 \uB300\uBE44 \uB9CC\uC871\uB3C4\uAC00 \uBE44\uAD50\uC801 \uC798 \uB098\uC624\uB294 \uCE74\uD14C\uACE0\uB9AC",
                K_CAUTION: "\uC6A9\uB7C9\uC774 \uC791\uC73C\uBA74 \uC5EC\uB7EC \uBA85\uC774 \uC4F8 \uB54C \uBD88\uD3B8\uD560 \uC218 \uC788\uC74C",
            },
        ),
    ]

    merged = f"{product_name} {keyword} {category_name}"
    for needles, rule in rules:
        if any(needle in merged for needle in needles):
            base.update(rule)
            break

    base[K_TITLE_SEED] = f"{base[K_TARGET]} \uAE30\uC900\uC73C\uB85C {keyword} \uACE0\uB97C \uB54C \uBCF4\uAE30 \uC26C\uC6B4 \uC2E4\uC0AC\uC6A9 \uD6C4\uAE30"
    base[K_THUMBNAIL] = (
        f"{keyword}\uB97C \uC2E4\uC81C \uC0DD\uD65C \uACF5\uAC04\uC5D0\uC11C \uC0AC\uC6A9\uD558\uB294 \uD55C\uAD6D\uD615 \uB77C\uC774\uD504\uC2A4\uD0C0\uC77C \uC7A5\uBA74. "
        f"{base[K_PLACE]} \uBC30\uACBD, \uC790\uC5F0\uAD11, \uACFC\uD55C \uAD11\uACE0 \uB290\uB08C \uC5C6\uB294 \uD604\uC2E4\uC801\uC778 \uBD84\uC704\uAE30."
    )
    return base


def compute_score(price: int, rating: float, review_count: int, keyword: str) -> float:
    keyword_bonus = 0
    for token in ("\uC6D0\uB8F8", "\uC790\uCDE8", "\uC0AC\uBB34\uC2E4", "\uAC00\uC131\uBE44", "\uC800\uC18C\uC74C", "\uBB34\uC120", "\uD734\uB300\uC6A9", "\uBBF8\uB2C8"):
        if token in keyword:
            keyword_bonus += 8

    review_score = min(review_count, 5000) * 0.06
    rating_score = rating * 20
    price_score = 15 if 10000 <= price <= 150000 else 5
    return review_score + rating_score + price_score + keyword_bonus


def compute_click_priority(score: float, review_count: int, rating: float) -> str:
    if score >= 140 and review_count >= 300 and rating >= 4.5:
        return "high"
    if score >= 95:
        return "medium"
    return "low"


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
    keyword = extract_product_keyword(product_name)

    return ProductRow(
        product_name=product_name,
        product_keyword=keyword,
        source_url=source_url,
        category_name=category_name,
        price=price,
        discount_rate=discount_rate,
        rocket_badges=rocket_badges,
        rating=rating,
        review_count=review_count,
    )


def scrape_products(
    driver: webdriver.Chrome,
    existing_names: set[str] | None = None,
    existing_urls: set[str] | None = None,
    target_count: int = TARGET_PRODUCT_COUNT,
) -> list[ProductRow]:
    collected: list[ProductRow] = []
    seen_names: set[str] = set(existing_names or set())
    seen_urls: set[str] = set(existing_urls or set())

    print(
        f"[crawl] 로켓배송 > {TARGET_CATEGORY_NAME} > {TARGET_SUBCATEGORY_NAME} > "
        f"{TARGET_PRODUCT_NAME} > 판매량순 > {MIN_PRODUCT_PRICE:,}원 이상"
    )
    try:
        open_category_page(driver)
    except TimeoutException:
        print(f"[skip] failed to load category: {TARGET_SUBCATEGORY_NAME}")
        return collected

    base_url = driver.current_url
    max_pages = get_max_pages()

    for page_number in range(1, max_pages + 1):
        try:
            items = open_page_number(driver, base_url, page_number)
        except TimeoutException:
            print(f"[skip] failed to load page {page_number}: {TARGET_SUBCATEGORY_NAME}")
            break

        print(f"[crawl] parsing page {page_number} / visible items {len(items)}")
        page_new_count = 0

        for item in items:
            try:
                product_name = item.find_element(By.CSS_SELECTOR, "div.ProductUnit_productNameV2__cV9cw").text.strip()
                normalized_name = normalize_text(product_name)
                if not product_name or normalized_name in seen_names:
                    continue

                price = clean_number(item.find_element(By.CSS_SELECTOR, "strong.Price_priceValue__A4KOr").text)
                if price < MIN_PRODUCT_PRICE:
                    continue

                try:
                    discount_rate = clean_discount(item.find_element(By.CSS_SELECTOR, "span.PriceInfo_discountRate__EsQ8I").text)
                except Exception:
                    discount_rate = 0

                rocket_badges = extract_rocket_badges(item)
                rating = clean_rating(item.find_element(By.CSS_SELECTOR, "div.ProductRating_star__RGSlV").text)
                review_count = clean_number(item.find_element(By.CSS_SELECTOR, "span.ProductRating_ratingCount__R0Vhz").text)

                try:
                    href = item.find_element(By.CSS_SELECTOR, "a[href*='/vp/products/']").get_attribute("href") or ""
                    product_link = href.split("?")[0]
                except Exception:
                    product_link = driver.current_url.split("?")[0]
                if product_link in seen_urls:
                    continue

                collected.append(
                    build_row(
                        product_name=product_name,
                        source_url=product_link,
                        category_name=TARGET_SUBCATEGORY_NAME,
                        price=price,
                        discount_rate=discount_rate,
                        rocket_badges=rocket_badges,
                        rating=rating,
                        review_count=review_count,
                    )
                )
                seen_names.add(normalized_name)
                if product_link:
                    seen_urls.add(product_link)
                page_new_count += 1

                if len(collected) >= target_count:
                    print(f"[crawl] reached target count: {target_count}")
                    return collected
            except Exception:
                continue

        print(f"[crawl] page {page_number} added {page_new_count} new products")

        if page_new_count == 0:
            break

    return collected


def filter_products(rows: Iterable[ProductRow]) -> list[ProductRow]:
    min_reviews = get_min_reviews()
    min_rating = get_min_rating()
    excluded_keywords = get_excluded_keywords()
    filtered = []
    for row in rows:
        if row.review_count < min_reviews:
            continue
        if row.rating < min_rating:
            continue
        normalized_name = normalize_text(row.product_name)
        normalized_keyword = normalize_text(row.product_keyword)
        if excluded_keywords and any(
            keyword in normalized_name or keyword in normalized_keyword
            for keyword in excluded_keywords
        ):
            continue
        filtered.append(row)

    filtered.sort(
        key=lambda item: (
            item.review_count,
            item.rating,
            item.discount_rate,
            -item.price,
        ),
        reverse=True,
    )
    return filtered


def save_products(rows: Iterable[ProductRow], output_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print("[save] no products to store")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].to_csv_row().keys())
    ensure_csv_schema(output_path, fieldnames)
    file_exists = output_path.exists() and output_path.stat().st_size > 0

    existing_urls = set()
    used_urls = set()
    used_names = set()
    if file_exists:
        with output_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                link = r.get("쿠팡링크", "").strip()
                if link:
                    existing_urls.add(link)
                used = (r.get("used", "") or "").strip().upper()
                post_title = (r.get("post_title", "") or "").strip()
                if used == "Y" or post_title:
                    if link:
                        used_urls.add(link)
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
            if row_url in existing_urls:
                continue
            if row_url in used_urls or row_name in used_names:
                continue
            writer.writerow(row_dict)
            added_count += 1

    print(f"[done] Appended {added_count} new rows to {output_path}")


def main(target_count: int | None = None) -> None:
    csv_input = input("어디로 저장 할 건지 저장 경로(파일)를 입력하세요 (엔터 시 기본값 사용): ").strip()
    target_csv_path = Path(csv_input) if csv_input else TARGET_CSV

    driver = create_driver()
    debugger_mode = bool(os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip())
    resolved_target_count = target_count or get_target_product_count()
    try:
        print(f"[start] building {target_csv_path.name}")
        if debugger_mode:
            print("[info] using existing Chrome session via remote debugger")
        existing_names, existing_urls = load_existing_products(target_csv_path)
        print(
            "[filter] "
            f"min_price={MIN_PRODUCT_PRICE:,} "
            f"target_count={resolved_target_count} "
            f"existing_products={len(existing_names)}"
        )
        rows = scrape_products(
            driver,
            existing_names=existing_names,
            existing_urls=existing_urls,
            target_count=resolved_target_count,
        )
        save_products(rows[:resolved_target_count], target_csv_path)
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
