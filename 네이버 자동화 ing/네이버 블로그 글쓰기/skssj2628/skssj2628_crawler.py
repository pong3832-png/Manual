from __future__ import annotations

import csv
import json
import os
import re
import shutil
import socket
import subprocess
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


try:
    from selenium import webdriver
    from selenium.common.exceptions import NoSuchWindowException, TimeoutException, WebDriverException
    from selenium.webdriver import ActionChains
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ModuleNotFoundError:
    webdriver = None
    NoSuchWindowException = TimeoutException = WebDriverException = Exception
    ActionChains = Options = Service = By = EC = WebDriverWait = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TARGET_CSV = Path(__file__).resolve().parent / "skssj2628_db.csv"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

K_PRODUCT_NAME = "\uC0C1\uD488\uBA85"
K_KEYWORD = "\uD0A4\uC6CC\uB4DC"
K_SOURCE_URL = "\uC0C1\uD488\uC6D0\uBCF8URL"
K_COUPANG_LINK = "\uCFE0\uD321\uB9C1\uD06C"
K_PRODUCT_IMAGE_URL = "\uC0C1\uD488\uC774\uBBF8\uC9C0URL"
K_PRODUCT_ID = "\uC0C1\uD488ID"
K_ITEM_ID = "\uC544\uC774\uD15CID"
K_CATEGORY = "\uCE74\uD14C\uACE0\uB9AC"
K_PRICE = "\uAC00\uACA9"
K_DISCOUNT = "\uD560\uC778\uC728"
K_ROCKET = "\uB85C\uCF13\uC815\uBCF4"
K_RATING = "\uD3C9\uC810"
K_REVIEW = "\uB9AC\uBDF0\uC218"
K_SCORE = "\uC810\uC218"
K_PRODUCT_GROUP = "\uC0C1\uD488\uAD70"
K_SCENARIO = "\uBB38\uC81C\uC0C1\uD669"
K_TARGET = "\uB300\uC0C1\uB3C5\uC790"
K_PLACE = "\uC0AC\uC6A9\uC7A5\uC18C"
K_SEASON = "\uACC4\uC808\uD0DC\uADF8"
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
K_PRICE_BAND = "\uAC00\uACA9\uB300"
K_SOURCE_PATH = "\uC218\uC9D1\uACBD\uB85C"
K_SOURCE_KEYWORD = "\uC218\uC9D1\uD0A4\uC6CC\uB4DC"
K_SOURCE_RANK = "\uC218\uC9D1\uC21C\uC704"
K_COLLECTED_AT = "\uC218\uC9D1\uC77C\uC2DC"

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


TARGET_CATEGORY_NAME = "식품"
TARGET_SUBCATEGORY_NAME = "식품"
TARGET_PRODUCT_NAME = "식품"
MIN_PRODUCT_PRICE = 0
TARGET_PRODUCT_COUNT = 100
ROCKET_DIGITAL_COMPONENT_URL = "https://www.coupang.com/np/campaigns/82/components/178155"
ROCKET_SEASONAL_COMPONENT_URL = "https://www.coupang.com/np/campaigns/82/components/227712"
DEFAULT_DEBUG_CHROME_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]
DEFAULT_DEBUG_PROFILE = Path.home() / "ChromeCoupangDebugStable"
_CSV_BACKUPS_CREATED: set[Path] = set()


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
    product_image_url: str = ""
    product_id: str = ""
    item_id: str = ""
    source_rank: int = 0
    collection_keyword: str = ""
    collected_at: str = ""

    @staticmethod
    def _format_price(price: int) -> str:
        return f"{price:,}원" if price else ""

    def to_csv_row(self) -> dict[str, object]:
        metadata = infer_metadata(self.product_name, self.product_keyword, self.category_name)
        score = compute_score(self.price, self.rating, self.review_count, self.product_keyword)
        return {
            "상품명": self.product_name,
            "키워드": self.product_keyword,
            "상품원본URL": self.source_url,
            "쿠팡링크": self.source_url,
            "상품이미지URL": self.product_image_url,
            "상품ID": self.product_id,
            "아이템ID": self.item_id,
            "카테고리": self.category_name,
            "가격": self._format_price(self.price),
            "할인율": self.discount_rate,
            "로켓정보": self.rocket_badges,
            "평점": self.rating,
            "리뷰수": self.review_count,
            "점수": round(score, 2),
            "click_priority": compute_click_priority(score, self.review_count, self.rating),
            "가격대": infer_price_band(self.price),
            "상품군": metadata.get(K_PRODUCT_GROUP, self.category_name),
            "계절태그": metadata.get(K_SEASON, ""),
            "대상독자": metadata.get(K_TARGET, ""),
            "사용장소": metadata.get(K_PLACE, ""),
            "문제상황": metadata.get(K_SCENARIO, ""),
            "불편포인트": metadata.get(K_PAIN, ""),
            "장점1": metadata.get(K_POINT1, ""),
            "장점2": metadata.get(K_POINT2, ""),
            "장점3": metadata.get(K_POINT3, ""),
            "주의점": metadata.get(K_CAUTION, ""),
            "검색의도": metadata.get(K_INTENT, ""),
            "글관점": metadata.get(K_ANGLE, ""),
            "제목시드": metadata.get(K_TITLE_SEED, ""),
            "썸네일프롬프트": metadata.get(K_THUMBNAIL, ""),
            "CTA문구": metadata.get(K_CTA, ""),
            "광고고지문": metadata.get(K_DISCLOSURE, DISCLOSURE_TEXT),
            "수집경로": f"로켓배송>{TARGET_CATEGORY_NAME}",
            "수집키워드": self.collection_keyword or TARGET_CATEGORY_NAME,
            "수집순위": self.source_rank,
            "수집일시": self.collected_at,
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
            Path(r"C:\py_temp\chromedriver.exe"),
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
    if webdriver is None:
        raise RuntimeError("selenium 패키지가 없어 쿠팡 크롤러 브라우저를 실행할 수 없습니다.")

    # 기본값으로 항상 디버거 주소를 사용하도록 수정
    debugger_address = os.getenv("COUPANG_DEBUGGER_ADDRESS", "127.0.0.1:9222").strip()
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


def is_used_marker(value: str) -> bool:
    return str(value or "").strip().casefold() in {"true", "1", "y", "yes"}


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


def build_product_identity_keys(
    product_name: str = "",
    product_url: str = "",
    product_id: str = "",
    item_id: str = "",
) -> set[str]:
    keys: set[str] = set()
    normalized_name = normalize_text(product_name)
    if normalized_name:
        keys.add(f"name:{normalized_name}")

    if product_url:
        keys.add(f"url:{product_url.strip()}")
        extracted_product_id, extracted_item_id = extract_product_ids_from_url(product_url)
        product_id = product_id or extracted_product_id
        item_id = item_id or extracted_item_id

    if product_id:
        keys.add(f"product:{product_id}")
    if item_id:
        keys.add(f"item:{item_id}")
    if product_id and item_id:
        keys.add(f"product_item:{product_id}:{item_id}")
    return keys


def load_existing_products(db_path: Path) -> tuple[set[str], set[str], set[str]]:
    existing_names: set[str] = set()
    existing_urls: set[str] = set()
    existing_product_keys: set[str] = set()

    if db_path.exists():
        try:
            with db_path.open("r", encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    existing_name = normalize_text(row.get(K_PRODUCT_NAME, ""))
                    existing_url = (row.get(K_COUPANG_LINK, "") or row.get(K_SOURCE_URL, "")).strip()
                    if existing_name:
                        existing_names.add(existing_name)
                    if existing_url:
                        existing_urls.add(existing_url)
                    existing_product_keys.update(
                        build_product_identity_keys(
                            product_name=row.get(K_PRODUCT_NAME, ""),
                            product_url=existing_url,
                            product_id=row.get(K_PRODUCT_ID, ""),
                            item_id=row.get(K_ITEM_ID, ""),
                        )
                    )
        except Exception as exc:
            print(f"[warn] failed to load existing products from csv: {exc}")

    # Load from used products JSON as well
    used_json_path = db_path.parent / "자동발행상태기록파일" / "coupang_used_products.json"
    if used_json_path.exists():
        try:
            with used_json_path.open("r", encoding="utf-8") as f:
                used_data = json.load(f)
                for key, val in used_data.items():
                    name = normalize_text(val.get("product_name", ""))
                    link = val.get("product_link", "").strip()
                    if name:
                        existing_names.add(name)
                    if link:
                        existing_urls.add(link)
                    existing_product_keys.update(
                        build_product_identity_keys(
                            product_name=val.get("product_name", ""),
                            product_url=link or key,
                        )
                    )
        except Exception as exc:
            print(f"[warn] failed to load used products from json: {exc}")

    return existing_names, existing_urls, existing_product_keys


def load_existing_csv_rows(db_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not db_path.exists() or db_path.stat().st_size == 0:
        return [], []

    with db_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader), (reader.fieldnames or [])


def parse_price_value(value: str) -> int:
    return clean_number(value)


def infer_price_band(price: int) -> str:
    if price <= 0:
        return ""
    if price < 10000:
        return "1만원 미만"
    if price < 30000:
        return "1만-3만원대"
    if price < 70000:
        return "3만-7만원대"
    if price < 150000:
        return "7만-15만원대"
    if price < 500000:
        return "15만-50만원대"
    return "50만원 이상"


def extract_product_ids_from_url(url: str) -> tuple[str, str]:
    if not url:
        return "", ""

    parsed = urlsplit(url)
    product_id_match = re.search(r"/vp/products/(\d+)", parsed.path)
    product_id = product_id_match.group(1) if product_id_match else ""
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    item_id = query.get("itemId", "")
    return product_id, item_id


def backup_csv_once(output_path: Path) -> Path | None:
    if not output_path.exists() or output_path.stat().st_size == 0:
        return None

    resolved_path = output_path.resolve()
    if resolved_path in _CSV_BACKUPS_CREATED:
        return None

    backup_dir = output_path.parent / "자동발행상태기록파일" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{output_path.stem}_backup_{timestamp}{output_path.suffix}"
    suffix = 1
    while backup_path.exists():
        backup_path = backup_dir / f"{output_path.stem}_backup_{timestamp}_{suffix}{output_path.suffix}"
        suffix += 1

    shutil.copy2(output_path, backup_path)
    _CSV_BACKUPS_CREATED.add(resolved_path)
    print(f"[backup] saved CSV backup: {backup_path}")
    return backup_path


def enrich_existing_csv_row(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    normalized = {field: row.get(field, "") for field in fieldnames}
    product_name = normalized.get(K_PRODUCT_NAME, "").strip()
    keyword = normalized.get(K_KEYWORD, "").strip() or extract_product_keyword(product_name)
    category_name = normalized.get(K_CATEGORY, "").strip() or TARGET_CATEGORY_NAME

    if not product_name:
        return normalized

    metadata = infer_metadata(product_name, keyword, category_name)
    price = parse_price_value(normalized.get(K_PRICE, ""))
    rating = clean_rating(normalized.get(K_RATING, ""))
    review_count = clean_number(normalized.get(K_REVIEW, ""))
    score = compute_score(price, rating, review_count, keyword)
    original_url = normalized.get(K_SOURCE_URL, "").strip() or normalized.get(K_COUPANG_LINK, "").strip()
    product_id, item_id = extract_product_ids_from_url(original_url)

    fallback_values = {
        K_KEYWORD: keyword,
        K_SOURCE_URL: original_url,
        K_COUPANG_LINK: normalized.get(K_COUPANG_LINK, "").strip() or original_url,
        K_PRODUCT_ID: product_id,
        K_ITEM_ID: item_id,
        K_SCORE: str(round(score, 2)) if score else "",
        K_CLICK_PRIORITY: compute_click_priority(score, review_count, rating) if score else "",
        K_PRICE_BAND: infer_price_band(price),
        K_PRODUCT_GROUP: metadata.get(K_PRODUCT_GROUP, category_name),
        K_SEASON: metadata.get(K_SEASON, ""),
        K_TARGET: metadata.get(K_TARGET, ""),
        K_PLACE: metadata.get(K_PLACE, ""),
        K_SCENARIO: metadata.get(K_SCENARIO, ""),
        K_PAIN: metadata.get(K_PAIN, ""),
        K_POINT1: metadata.get(K_POINT1, ""),
        K_POINT2: metadata.get(K_POINT2, ""),
        K_POINT3: metadata.get(K_POINT3, ""),
        K_CAUTION: metadata.get(K_CAUTION, ""),
        K_INTENT: metadata.get(K_INTENT, ""),
        K_ANGLE: metadata.get(K_ANGLE, ""),
        K_TITLE_SEED: metadata.get(K_TITLE_SEED, ""),
        K_THUMBNAIL: metadata.get(K_THUMBNAIL, ""),
        K_CTA: metadata.get(K_CTA, ""),
        K_DISCLOSURE: metadata.get(K_DISCLOSURE, DISCLOSURE_TEXT),
        K_SOURCE_PATH: normalized.get(K_SOURCE_PATH, "").strip() or f"로켓배송>{TARGET_CATEGORY_NAME}",
        K_SOURCE_KEYWORD: normalized.get(K_SOURCE_KEYWORD, "").strip() or category_name,
    }

    metadata_keys = {
        K_PRODUCT_GROUP,
        K_SEASON,
        K_TARGET,
        K_PLACE,
        K_SCENARIO,
        K_PAIN,
        K_POINT1,
        K_POINT2,
        K_POINT3,
        K_CAUTION,
        K_INTENT,
        K_ANGLE,
        K_TITLE_SEED,
        K_THUMBNAIL,
        K_CTA,
    }
    generic_group = str(normalized.get(K_PRODUCT_GROUP, "")).strip()

    for key, value in fallback_values.items():
        should_refresh_generic = key in metadata_keys and generic_group in {"", category_name, TARGET_CATEGORY_NAME}
        if key in normalized and value and (not str(normalized.get(key, "")).strip() or should_refresh_generic):
            normalized[key] = str(value)
    return normalized


def ensure_csv_schema(output_path: Path, fieldnames: list[str]) -> None:
    existing_rows, existing_fieldnames = load_existing_csv_rows(output_path)
    if not existing_rows and not existing_fieldnames:
        return

    normalized_rows: list[dict[str, str]] = []
    for row in existing_rows:
        normalized_rows.append(enrich_existing_csv_row(row, fieldnames))

    current_rows = [{field: row.get(field, "") for field in fieldnames} for row in existing_rows]
    if existing_fieldnames == fieldnames and normalized_rows == current_rows:
        return

    backup_csv_once(output_path)
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
        if wait_for_manual_clear_if_debugger(driver):
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


def wait_for_manual_clear_if_debugger(driver: webdriver.Chrome, seconds: int = 90) -> bool:
    if not os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip():
        return False

    print("[info] debugger mode detected; waiting for manual unblock in Chrome")
    deadline = time.time() + seconds
    while time.time() < deadline:
        if not is_access_denied(driver):
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "#product-list > li.ProductUnit_productUnit__Qd6sv")
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


def click_category_by_name(driver: webdriver.Chrome, name: str, timeout: int = 10) -> None:
    target_xpath = (
        "//a[normalize-space()=$name] | "
        "//button[normalize-space()=$name] | "
        "//span[normalize-space()=$name]/ancestor::a[1] | "
        "//span[normalize-space()=$name]/ancestor::button[1]"
    )

    target = WebDriverWait(driver, timeout).until(
        lambda d: d.find_element(By.XPATH, target_xpath.replace("$name", f"'{name}'"))
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
    click_category_by_name(driver, TARGET_CATEGORY_NAME)


def open_category_page(driver: webdriver.Chrome) -> list:
    warm_up_coupang_session(driver)

    for attempt in range(1, 4):
        try:
            click_category_flow(driver)
        except TimeoutException:
            print(f"[retry] category open timeout on attempt {attempt}: {TARGET_CATEGORY_NAME}")
            if wait_for_manual_clear_if_debugger(driver, seconds=120):
                return wait_for_products(driver)
            time.sleep(3 * attempt)
            warm_up_coupang_session(driver)
            continue

        if is_access_denied(driver):
            print(f"[retry] access denied on attempt {attempt}: {TARGET_CATEGORY_NAME}")
            if wait_for_manual_clear_if_debugger(driver):
                return wait_for_products(driver)
            time.sleep(5 * attempt)
            warm_up_coupang_session(driver)
            continue

        try:
            return wait_for_products(driver)
        except TimeoutException:
            print(f"[retry] product wait timeout on attempt {attempt}: {TARGET_CATEGORY_NAME}")
            time.sleep(3 * attempt)
            warm_up_coupang_session(driver)

    raise TimeoutException(f"failed to open category page: {TARGET_CATEGORY_NAME}")


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
        K_PRODUCT_GROUP: category_name or TARGET_PRODUCT_NAME,
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
        K_ANGLE: "\uAD6C\uB9E4 \uC804 \uC6A9\uB7C9, \uAD6C\uC131, \uBCF4\uAD00, \uC18C\uBE44 \uC18D\uB3C4\uB97C \uC815\uB9AC\uD558\uB294 \uCCB4\uD06C\uB9AC\uC2A4\uD2B8\uD615",
        K_CTA: "\uC81C\uD488 \uC0C1\uC138\uC815\uBCF4\uC640 \uD604\uC7AC \uAC00\uACA9\uC740 \uC544\uB798 \uB9C1\uD06C\uC5D0\uC11C \uBC14\uB85C \uD655\uC778 \uAC00\uB2A5",
        K_DISCLOSURE: DISCLOSURE_TEXT,
    }

    rules = [
        (
            ("사이다", "콜라", "제로", "탄산", "밀키스", "구론산", "까스활", "아몬드브리즈", "하늘보리", "뉴케어"),
            {
                K_PRODUCT_GROUP: "음료/탄산음료",
                K_SCENARIO: "집이나 사무실에 마실 음료를 박스 단위로 미리 준비하고 싶을 때",
                K_TARGET: "음료를 자주 마시는 가정, 사무실 탕비실, 손님용 음료를 준비하는 사람",
                K_PLACE: "냉장고, 주방, 사무실 탕비실, 팬트리",
                K_SEASON: "사계절, 여름",
                K_PAIN: "개수와 가격만 보면 당류, 카페인, 보관 공간을 놓치기 쉬움",
                K_POINT1: "개수와 용량을 기준으로 비교하기 좋음",
                K_POINT2: "제로, 소용량, 대용량처럼 선택 기준이 뚜렷함",
                K_POINT3: "가정용과 사무실용으로 쓰임이 분명함",
                K_CAUTION: "당류, 카페인, 보관 공간, 캔이나 페트 용량을 확인해야 함",
            },
        ),
        (
            ("과자", "초콜릿", "카스타드", "누룽지팝", "간식", "쿠키", "스낵", "에너지바"),
            {
                K_PRODUCT_GROUP: "간식/과자",
                K_SCENARIO: "집이나 사무실에 간단히 먹을 간식을 미리 준비하고 싶을 때",
                K_TARGET: "아이 간식, 사무실 간식, 손님용 간식을 찾는 사람",
                K_PLACE: "주방 수납장, 사무실 탕비실, 책상 서랍",
                K_SEASON: "사계절",
                K_PAIN: "묶음 개수와 보관 공간을 생각하지 않으면 남기거나 눅눅해질 수 있음",
                K_POINT1: "개별 포장 여부와 개수를 비교하기 좋음",
                K_POINT2: "사무실, 아이 간식, 손님용으로 용도가 분명함",
                K_POINT3: "가격대가 낮아 상세 조건 확인으로 이어지기 쉬움",
                K_CAUTION: "알레르기 성분, 당류, 보관법, 개별 포장 여부를 확인해야 함",
            },
        ),
        (
            ("오메가", "비타민", "프로바이오틱", "영양제", "나또", "소화제"),
            {
                K_PRODUCT_GROUP: "건강/기능식품",
                K_SCENARIO: "건강 관리를 위해 매일 챙길 식품이나 보조 제품을 고를 때",
                K_TARGET: "성분, 섭취량, 구성 수량을 구매 전에 확인하려는 사람",
                K_PLACE: "주방, 식탁, 사무실 서랍, 약 보관함",
                K_SEASON: "사계절",
                K_PAIN: "성분과 섭취 기준을 확인하지 않으면 내 상황에 맞는지 판단하기 어려움",
                K_POINT1: "성분과 1일 섭취량 확인이 중요함",
                K_POINT2: "수량과 섭취 기간을 비교하기 좋음",
                K_POINT3: "반복 구매 가능성이 있어 구성 확인이 필요함",
                K_CAUTION: "개인 건강 상태, 성분, 섭취 방법, 주의사항은 상세정보에서 확인해야 함",
            },
        ),
        (
            ("키위", "과일", "무,", "세척 무", "채소", "토마토", "바나나"),
            {
                K_PRODUCT_GROUP: "신선식품",
                K_SCENARIO: "신선한 과일이나 채소를 배송으로 받아보고 싶을 때",
                K_TARGET: "장보는 시간을 줄이고 싶은 가정, 자취생, 신선식품을 자주 먹는 사람",
                K_PLACE: "냉장고, 주방, 식탁",
                K_SEASON: "사계절",
                K_PAIN: "중량, 신선도, 보관 기간을 확인하지 않으면 만족도가 달라질 수 있음",
                K_POINT1: "중량과 개수 확인이 구매 판단에 중요함",
                K_POINT2: "배송 후 바로 보관해야 하는 식품이라 관리 기준이 분명함",
                K_POINT3: "가정용 장보기 수요와 잘 맞음",
                K_CAUTION: "신선도, 중량, 보관법, 배송 상태 안내를 확인해야 함",
            },
        ),
        (
            ("삼다수", "생수", "샘물", "무라벨", "물 "),
            {
                K_PRODUCT_GROUP: "생수/음료",
                K_SCENARIO: "생수를 매번 사러 가기 번거롭고 집이나 사무실에 미리 준비해두고 싶을 때",
                K_TARGET: "생수를 박스로 사두는 가정, 자취생, 사무실 탕비실 담당자",
                K_PLACE: "주방, 현관 옆 보관 공간, 사무실, 탕비실",
                K_SEASON: "사계절, 여름",
                K_PAIN: "용량과 개수, 보관 공간, 배송 무게를 같이 보지 않으면 주문 후 불편할 수 있음",
                K_POINT1: "반복 구매 수요가 높아 구성과 개수 비교가 중요함",
                K_POINT2: "500ml와 2L처럼 사용 상황에 따라 선택 기준이 분명함",
                K_POINT3: "무라벨 여부와 보관 편의성을 함께 판단하기 좋음",
                K_CAUTION: "박스 단위 무게, 보관 공간, 병 용량을 구매 전에 확인해야 함",
            },
        ),
        (
            ("커피", "카누", "맥심", "레쓰비", "캔커피", "원두", "믹스"),
            {
                K_PRODUCT_GROUP: "커피/음료",
                K_SCENARIO: "집이나 사무실에서 커피를 자주 마셔서 넉넉한 구성을 미리 준비하고 싶을 때",
                K_TARGET: "사무실 탕비실, 자취방, 집에서 커피를 자주 마시는 사람",
                K_PLACE: "탕비실, 책상, 주방, 사무실 냉장고",
                K_SEASON: "사계절",
                K_PAIN: "개수와 용량만 보고 고르면 당류, 카페인, 보관 공간을 놓치기 쉬움",
                K_POINT1: "개수 대비 가격과 소비 속도를 같이 보기 좋음",
                K_POINT2: "사무실용, 집비치용처럼 사용 목적이 분명함",
                K_POINT3: "로켓배송과 대량 구성 확인 수요가 높은 편",
                K_CAUTION: "당류, 카페인, 유통기한, 보관 공간은 상세정보에서 확인해야 함",
            },
        ),
        (
            ("라면", "안성탕면", "신라면", "짜파게티", "컵라면", "사발면", "너구리"),
            {
                K_PRODUCT_GROUP: "라면/간편식",
                K_SCENARIO: "간단히 먹을 비상식품이나 자취방 간편식을 미리 준비하고 싶을 때",
                K_TARGET: "자취생, 야식이 잦은 사람, 사무실 간식이나 비상식을 준비하는 사람",
                K_PLACE: "자취방, 주방 수납장, 사무실 탕비실",
                K_SEASON: "사계절",
                K_PAIN: "묶음 개수와 보관 공간, 소비기한을 생각하지 않으면 남기기 쉬움",
                K_POINT1: "개수와 개당 가격 비교가 구매 판단에 직접 연결됨",
                K_POINT2: "보관성이 좋아 비상식품으로 확인하기 쉬움",
                K_POINT3: "가족용, 자취용, 사무실용으로 용도가 뚜렷함",
                K_CAUTION: "나트륨, 소비기한, 보관 공간, 묶음 개수를 함께 확인해야 함",
            },
        ),
        (
            ("계란", "유정란", "구운란", "등급란", "대란", "특란"),
            {
                K_PRODUCT_GROUP: "계란/단백질 간식",
                K_SCENARIO: "아침이나 간식으로 먹을 단백질 식품을 미리 준비하고 싶을 때",
                K_TARGET: "아침을 간단히 챙기는 사람, 운동 후 간식을 찾는 사람, 아이 간식을 준비하는 가정",
                K_PLACE: "냉장고, 주방, 사무실 간식 공간",
                K_SEASON: "사계절",
                K_PAIN: "개수와 보관 방식, 배송 중 파손 가능성을 같이 봐야 안심하기 쉬움",
                K_POINT1: "아침, 간식, 도시락용으로 활용 상황이 분명함",
                K_POINT2: "30구 같은 묶음 구성은 가족용과 1인용 판단이 필요함",
                K_POINT3: "등급, 인증, 보관 조건을 비교하기 좋음",
                K_CAUTION: "냉장 보관, 소비기한, 파손 안내, 인증 정보를 확인해야 함",
            },
        ),
        (
            ("쌀", "햅쌀", "잡곡", "현미", "백미"),
            {
                K_PRODUCT_GROUP: "쌀/잡곡",
                K_SCENARIO: "집에서 밥을 자주 해먹어 쌀이나 잡곡을 안정적으로 준비하고 싶을 때",
                K_TARGET: "집밥을 자주 먹는 가정, 자취생, 대용량 식재료를 찾는 사람",
                K_PLACE: "주방, 쌀통, 팬트리",
                K_SEASON: "사계절",
                K_PAIN: "용량과 보관 환경을 놓치면 벌레, 습기, 신선도 관리가 어려울 수 있음",
                K_POINT1: "용량별 가격 비교가 구매 판단에 중요함",
                K_POINT2: "가족 수와 소비 속도에 따라 맞는 용량이 달라짐",
                K_POINT3: "도정일, 산지, 포장 단위를 같이 보기 좋음",
                K_CAUTION: "보관 장소, 도정일, 용량, 소비 속도를 구매 전에 확인해야 함",
            },
        ),
        (
            ("간장", "소스", "식용유", "콩기름", "설탕", "조미료", "참기름", "들기름", "카레", "식초", "당면", "참깨", "부침가루"),
            {
                K_PRODUCT_GROUP: "소스/조미료",
                K_SCENARIO: "집밥이나 반찬을 자주 만들 때 자주 쓰는 조미료를 미리 준비하고 싶을 때",
                K_TARGET: "집밥을 자주 해먹는 가정, 자취생, 대용량 조미료를 찾는 사람",
                K_PLACE: "주방, 팬트리, 조리대 주변",
                K_SEASON: "사계절",
                K_PAIN: "용량만 보고 고르면 보관 중 산패, 소비기한, 사용 빈도를 놓치기 쉬움",
                K_POINT1: "자주 쓰는 식재료라 용량 대비 가격 확인이 중요함",
                K_POINT2: "요리 빈도에 따라 대용량과 소용량 판단이 달라짐",
                K_POINT3: "보관 방식과 개봉 후 관리까지 같이 보기 좋음",
                K_CAUTION: "개봉 후 보관법, 소비기한, 용량, 원재료 표기를 확인해야 함",
            },
        ),
        (
            ("요거트", "요구르트", "불가리스", "비피더스", "우유", "치즈", "바이오", "플레인"),
            {
                K_PRODUCT_GROUP: "유제품/간식",
                K_SCENARIO: "아침이나 간식으로 먹을 냉장 식품을 묶음으로 준비하고 싶을 때",
                K_TARGET: "아이 간식, 아침 대용, 사무실 간식용 유제품을 찾는 사람",
                K_PLACE: "냉장고, 주방, 사무실 냉장고",
                K_SEASON: "사계절",
                K_PAIN: "냉장 보관과 소비기한을 놓치면 묶음 구매가 오히려 부담될 수 있음",
                K_POINT1: "개수와 소비기한을 함께 비교하기 좋음",
                K_POINT2: "가족용, 간식용, 아침 대용으로 용도가 분명함",
                K_POINT3: "당류와 용량을 같이 확인하기 쉬움",
                K_CAUTION: "냉장 배송, 소비기한, 당류, 보관 공간을 확인해야 함",
            },
        ),
        (
            ("김", "반찬", "닭", "고기", "양지", "백숙", "참치", "흰밥", "햇반", "즉석밥", "통조림", "황도"),
            {
                K_PRODUCT_GROUP: "반찬/식재료",
                K_SCENARIO: "집밥 반찬이나 조리용 식재료를 미리 준비하고 싶을 때",
                K_TARGET: "집밥을 자주 먹는 가정, 간단한 반찬을 준비하는 사람",
                K_PLACE: "주방, 냉장고, 냉동실, 팬트리",
                K_SEASON: "사계절",
                K_PAIN: "보관 방식과 조리 난이도를 놓치면 활용도가 낮아질 수 있음",
                K_POINT1: "반찬용, 조리용, 비상식품용으로 쓰임이 분명함",
                K_POINT2: "용량과 포장 단위를 비교하기 좋음",
                K_POINT3: "냉장/냉동/상온 보관 여부가 판단 기준이 됨",
                K_CAUTION: "보관 조건, 조리법, 소비기한, 원재료 정보를 확인해야 함",
            },
        ),
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

    base[K_TITLE_SEED] = f"{base[K_TARGET]} \uAE30\uC900\uC73C\uB85C {keyword} \uACE0\uB97C \uB54C \uBCF4\uAE30 \uC26C\uC6B4 \uAD6C\uB9E4 \uC804 \uCCB4\uD06C"
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
    product_image_url: str = "",
    product_id: str = "",
    item_id: str = "",
    source_rank: int = 0,
    collection_keyword: str = "",
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
        product_image_url=product_image_url,
        product_id=product_id,
        item_id=item_id,
        source_rank=source_rank,
        collection_keyword=collection_keyword,
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def scrape_products(
    driver: webdriver.Chrome,
    existing_names: set[str] | None = None,
    existing_urls: set[str] | None = None,
    existing_product_keys: set[str] | None = None,
    target_count: int = TARGET_PRODUCT_COUNT,
) -> list[ProductRow]:
    collected: list[ProductRow] = []
    seen_names: set[str] = set(existing_names or set())
    seen_urls: set[str] = set(existing_urls or set())
    seen_product_keys: set[str] = set(existing_product_keys or set())

    print(
        f"[crawl] 로켓배송 > {TARGET_CATEGORY_NAME} > 기본 화면 > {MIN_PRODUCT_PRICE:,}원 이상"
    )
    try:
        open_category_page(driver)
    except TimeoutException:
        print(f"[skip] failed to load category: {TARGET_CATEGORY_NAME}")
        return collected

    base_url = driver.current_url
    max_pages = get_max_pages()

    for page_number in range(1, max_pages + 1):
        try:
            items = open_page_number(driver, base_url, page_number)
        except TimeoutException:
            print(f"[skip] failed to load page {page_number}: {TARGET_CATEGORY_NAME}")
            break

        print(f"[crawl] parsing page {page_number} / visible items {len(items)}")
        page_new_count = 0

        for item in items:
            try:
                product_name = item.find_element(By.CSS_SELECTOR, "div.ProductUnit_productNameV2__cV9cw").text.strip()
                normalized_name = normalize_text(product_name)
                if not product_name:
                    continue
                if normalized_name in seen_names:
                    continue

                price = clean_number(item.find_element(By.CSS_SELECTOR, "strong.Price_priceValue__A4KOr").text)
                if price < MIN_PRODUCT_PRICE:
                    continue

                try:
                    discount_rate = clean_discount(item.find_element(By.CSS_SELECTOR, "span.PriceInfo_discountRate__EsQ8I").text)
                except Exception:
                    discount_rate = 0

                rocket_badges = extract_rocket_badges(item)
                
                try:
                    rating = clean_rating(item.find_element(By.CSS_SELECTOR, "div.ProductRating_star__RGSlV").text)
                except Exception:
                    rating = 0.0
                    
                try:
                    review_count = clean_number(item.find_element(By.CSS_SELECTOR, "span.ProductRating_ratingCount__R0Vhz").text)
                except Exception:
                    review_count = 0

                try:
                    href = item.find_element(By.CSS_SELECTOR, "a[href*='/vp/products/']").get_attribute("href") or ""
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(href)
                    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    qs = parse_qs(parsed.query)
                    product_id_match = re.search(r"/vp/products/(\d+)", parsed.path)
                    product_id = product_id_match.group(1) if product_id_match else ""
                    item_id = qs.get("itemId", [""])[0]
                    if 'itemId' in qs:
                        product_link = f"{base}?itemId={item_id}"
                    else:
                        product_link = base
                except Exception:
                    product_link = driver.current_url.split("?")[0]
                    product_id = ""
                    item_id = ""
                product_keys = build_product_identity_keys(
                    product_name=product_name,
                    product_url=product_link,
                    product_id=product_id,
                    item_id=item_id,
                )
                if product_link in seen_urls or seen_product_keys.intersection(product_keys):
                    continue

                try:
                    image = item.find_element(By.CSS_SELECTOR, "img")
                    product_image_url = (
                        image.get_attribute("src")
                        or image.get_attribute("data-src")
                        or image.get_attribute("data-original")
                        or ""
                    )
                except Exception:
                    product_image_url = ""

                collected.append(
                    build_row(
                        product_name=product_name,
                        source_url=product_link,
                        category_name=TARGET_CATEGORY_NAME,
                        price=price,
                        discount_rate=discount_rate,
                        rocket_badges=rocket_badges,
                        rating=rating,
                        review_count=review_count,
                        product_image_url=product_image_url,
                        product_id=product_id,
                        item_id=item_id,
                        source_rank=len(collected) + 1,
                        collection_keyword=TARGET_CATEGORY_NAME,
                    )
                )
                seen_names.add(normalized_name)
                if product_link:
                    seen_urls.add(product_link)
                seen_product_keys.update(product_keys)
                page_new_count += 1

                if len(collected) >= target_count:
                    print(f"[crawl] reached target count: {target_count}")
                    return collected
            except Exception:
                continue

        print(f"[crawl] page {page_number} added {page_new_count} new products")

        if page_new_count == 0:
            print("[crawl] page had no new products after skipping existing rows; continuing to next page")
            continue

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


def current_csv_fieldnames() -> list[str]:
    sample = ProductRow(
        product_name="샘플 상품",
        product_keyword="샘플 키워드",
        source_url="",
        category_name=TARGET_CATEGORY_NAME,
        price=0,
        discount_rate=0,
        rocket_badges="",
        rating=0.0,
        review_count=0,
    )
    return list(sample.to_csv_row().keys())


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
    existing_names = set()
    existing_product_keys = set()
    used_urls = set()
    used_names = set()
    if file_exists:
        with output_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for r in reader:
                link = r.get("쿠팡링크", "").strip()
                name = (r.get("상품명", "") or "").strip()
                if link:
                    existing_urls.add(link)
                if name:
                    existing_names.add(normalize_text(name))
                existing_product_keys.update(
                    build_product_identity_keys(
                        product_name=name,
                        product_url=link or r.get("상품원본URL", ""),
                        product_id=r.get("상품ID", ""),
                        item_id=r.get("아이템ID", ""),
                    )
                )
                used = r.get("used", "")
                post_title = (r.get("post_title", "") or "").strip()
                if is_used_marker(used) or post_title:
                    if link:
                        used_urls.add(link)
                    if name:
                        used_names.add(name)

    added_count = 0
    backup_created = False
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
            row_keys = build_product_identity_keys(
                product_name=row_name,
                product_url=row_url or row_dict.get("상품원본URL", ""),
                product_id=row_dict.get("상품ID", ""),
                item_id=row_dict.get("아이템ID", ""),
            )
            if row_url in existing_urls or normalize_text(row_name) in existing_names:
                continue
            if existing_product_keys.intersection(row_keys):
                continue
            if row_url in used_urls or row_name in used_names:
                continue
            if not backup_created:
                backup_csv_once(output_path)
                backup_created = True
            writer.writerow(row_dict)
            if row_url:
                existing_urls.add(row_url)
            if row_name:
                existing_names.add(normalize_text(row_name))
            existing_product_keys.update(row_keys)
            added_count += 1

    print(f"[done] Appended {added_count} new rows to {output_path}")


def main(target_count: int | None = None) -> None:
    resolved_target_count = target_count or get_target_product_count()
    ensure_csv_schema(TARGET_CSV, current_csv_fieldnames())

    driver = create_driver()
    debugger_mode = bool(os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip())
    try:
        print("[start] building products_candidates.csv")
        if debugger_mode:
            print("[info] using existing Chrome session via remote debugger")
        existing_names, existing_urls, existing_product_keys = load_existing_products(TARGET_CSV)
        print(
            "[filter] "
            f"min_price={MIN_PRODUCT_PRICE:,} "
            f"target_count={resolved_target_count} "
            f"existing_products={len(existing_names)} "
            f"existing_identity_keys={len(existing_product_keys)}"
        )
        rows = scrape_products(
            driver,
            existing_names=existing_names,
            existing_urls=existing_urls,
            existing_product_keys=existing_product_keys,
            target_count=max(resolved_target_count * 2, resolved_target_count),
        )
        filtered_rows = filter_products(rows)
        if not filtered_rows:
            print("[warn] no rows passed rating/review filters; saving unfiltered crawl results")
            filtered_rows = rows
        save_products(filtered_rows[:resolved_target_count], TARGET_CSV)
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

