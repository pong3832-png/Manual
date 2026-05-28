from __future__ import annotations

import argparse
import csv
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, quote_plus, urlparse



from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, WebDriverException
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

PRODUCT_ITEM_SELECTOR = "#product-list > li.ProductUnit_productUnit__Qd6sv"
MIN_REVIEW_COUNT = 1000
MIN_RATING = 4.3

K_QUERY = "검색어"
K_COMPARISON_GROUP = "비교그룹"
K_PRODUCT_NAME = "상품명"
K_KEYWORD = "키워드"
K_SOURCE_URL = "상품원본URL"
K_CATEGORY = "카테고리"
K_PRICE = "가격"
K_DISCOUNT = "할인율"
K_ROCKET = "로켓정보"
K_RATING = "평점"
K_REVIEW = "리뷰수"
K_SCORE = "점수"
K_POSITION = "포지션"
K_TARGET = "추천대상"
K_POINT = "불편포인트"

STOPWORDS = {
    "국내산",
    "정품",
    "세트",
    "대용량",
    "무료배송",
    "로켓배송",
    "가정용",
    "신형",
    "프리미엄",
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
class SearchProductRow:
    query: str
    comparison_group: str
    product_name: str
    product_keyword: str
    source_url: str
    category_name: str
    price: int
    discount_rate: int
    rocket_badges: str
    rating: float
    review_count: int
    score: float
    position: str
    target_reader: str
    key_point: str

    def to_csv_row(self) -> dict[str, object]:
        return {
            "상품명": self.product_name,
            "키워드": self.product_keyword,
            "쿠팡링크": self.source_url,
            "카테고리": self.category_name,
            "상품군": self.comparison_group,
            "대상독자": self.target_reader,
            "장점1": self.key_point,
            "계절태그": "",
            "사용장소": "",
            "문제상황": "",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="쿠팡 검색어 기반 비교 후보 수집")
    parser.add_argument("--query", default="", help="검색할 키워드. 비우면 실행 중 입력")
    parser.add_argument("--max-pages", type=int, default=3, help="수집할 검색 결과 페이지 수")
    parser.add_argument(
        "--output-csv",
        default=str(TARGET_CSV),
        help="비교 후보 CSV 출력 경로",
    )
    args = parser.parse_args()
    args.query = (args.query or "").strip()
    if not args.query:
        try:
            args.query = input("검색할 키워드를 입력하세요: ").strip()
        except EOFError:
            parser.error("--query가 없고 입력을 받을 수 없습니다.")
        if not args.query:
            parser.error("검색어가 비어 있습니다.")
    return args


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
                "Referer": "https://www.google.com/",
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


def human_pause(base_seconds: float = 2.0, spread_seconds: float = 1.2) -> None:
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
        "?먮룞?붾맂 ?묎렐",
        "鍮꾩젙?곸쟻???묎렐",
        "?묎렐???쒗븳",
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


def wait_for_products(driver: webdriver.Chrome) -> list:
    for _ in range(18):
        items = driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)
        if items:
            return items
        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1.5)

    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#product-list"))
    )
    return driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)


def collect_scrolled_products(
    driver: webdriver.Chrome,
    max_scrolls: int = 24,
    pause_seconds: float = 1.1,
    stable_round_limit: int = 4,
) -> list:
    last_count = 0
    stable_rounds = 0
    items = wait_for_products(driver)

    for _ in range(max_scrolls):
        current_count = len(items)
        driver.execute_script("window.scrollBy(0, Math.max(window.innerHeight, 1200));")
        time.sleep(pause_seconds)
        items = driver.find_elements(By.CSS_SELECTOR, PRODUCT_ITEM_SELECTOR)

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


def build_search_url(query: str, page_number: int) -> str:
    return f"https://www.coupang.com/np/search?component=&q={quote_plus(query)}&page={page_number}"


def open_search_page(driver: webdriver.Chrome, query: str, page_number: int) -> list:
    driver.get(build_search_url(query, page_number))
    human_pause(3.0, 1.2)

    if is_access_denied(driver):
        if wait_for_manual_clear_if_debugger(driver, seconds=120):
            return collect_scrolled_products(driver)
        raise TimeoutException(f"blocked on search page {page_number} for query={query}")

    return collect_scrolled_products(driver)


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


def extract_price_from_text(text: str) -> int:
    prices: list[int] = []
    text = text or ""
    for match in re.finditer("(\\d[\\d,]*)\\s*\uc6d0", text):
        if "\ub2f9" in text[max(0, match.start() - 4):match.start()]:
            continue
        value = clean_number(match.group(1))
        if value >= 1000:
            prices.append(value)
    if not prices:
        return 0
    return min(prices)


def extract_discount_from_text(text: str) -> int:
    match = re.search(r"(\d{1,2})\s*%", text or "")
    return int(match.group(1)) if match else 0


def extract_price_from_item(item) -> int:
    selectors = (
        "strong.Price_priceValue__A4KOr",
        "[class*='PriceArea'] span",
        "[class*='priceArea'] span",
    )
    for selector in selectors:
        for element in item.find_elements(By.CSS_SELECTOR, selector):
            value = extract_price_from_text(element.text or "")
            if value:
                return value
    return extract_price_from_text(item.text or "")


def extract_discount_from_item(item) -> int:
    selectors = (
        "span.PriceInfo_discountRate__EsQ8I",
        "[class*='PriceArea'] div",
        "[class*='priceArea'] div",
    )
    for selector in selectors:
        for element in item.find_elements(By.CSS_SELECTOR, selector):
            value = extract_discount_from_text(element.text or "")
            if value:
                return value
    return extract_discount_from_text(item.text or "")


def extract_rating_from_item(item) -> float:
    selectors = (
        "div.ProductRating_star__RGSlV",
        "[class*='ProductRating'] [aria-label]",
    )
    for selector in selectors:
        for element in item.find_elements(By.CSS_SELECTOR, selector):
            for raw in (element.text, element.get_attribute("aria-label")):
                value = clean_rating(raw or "")
                if value:
                    return value
    return 0.0


def extract_review_count_from_item(item) -> int:
    selectors = (
        "span.ProductRating_ratingCount__R0Vhz",
        "[class*='ProductRating'] span",
    )
    for selector in selectors:
        for element in item.find_elements(By.CSS_SELECTOR, selector):
            value = clean_number(element.text or "")
            if value:
                return value
    match = re.search(r"\(([\d,]+)\)", item.text or "")
    return clean_number(match.group(1)) if match else 0


def extract_rocket_badges(item) -> str:
    badge_names: list[str] = []
    badge_map = {
        "ROCKET": "濡쒖폆諛곗넚",
        "ROCKET_MERCHANT": "濡쒖폆?ㅼ튂",
        "TOMORROW": "?댁씪?꾩갑",
    }

    for badge in item.find_elements(By.CSS_SELECTOR, "img[data-badge-id]"):
        badge_id = (badge.get_attribute("data-badge-id") or "").strip()
        if badge_id and badge_id in badge_map:
            badge_names.append(badge_map[badge_id])

    return ", ".join(dict.fromkeys(badge_names))


def extract_product_keyword(name: str, query: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", name)
    tokens = [token for token in cleaned.split() if len(token) >= 2 and token not in STOPWORDS]
    selected = [part for part in query.split() if len(part) >= 2]
    selected.extend(tokens[:3])
    return " ".join(dict.fromkeys(selected))[:40].strip() or query[:20]


def infer_comparison_group(query: str) -> str:
    compact = re.sub(r"\s+", "_", query.strip())
    compact = re.sub(r"[^0-9A-Za-z가-힣_]+", "", compact)
    return compact or "비교그룹"


def infer_position(price: int, rating: float, review_count: int) -> str:
    if review_count >= 1000 and rating >= 4.6:
        return "베스트셀러"
    if price <= 30000:
        return "가성비"
    if rating >= 4.7:
        return "만족도강점"
    return "비교후보"


def infer_target_reader(query: str) -> str:
    joined = query.replace(" ", "")
    if "원룸" in joined or "자취" in joined:
        return "원룸 거주자나 자취생"
    if "사무실" in joined or "책상" in joined:
        return "책상이나 사무실에서 쓸 제품을 찾는 사람"
    return f"{query}를 비교해보고 싶은 구매 검토자"


def infer_key_point(query: str, position: str, price: int, rating: float, review_count: int) -> str:
    if position == "베스트셀러":
        return f"{query} 비교군 중 리뷰 수와 평점이 모두 강한 편"
    if position == "가성비":
        return f"{query} 비교군 중 가격 부담이 비교적 낮은 편"
    if position == "만족도강점":
        return f"{query} 비교군 중 만족도 지표가 특히 강한 편"
    return f"가격 {price:,}원, 평점 {rating:.1f}, 리뷰 {review_count:,}개 기준의 비교 후보"


def compute_score(price: int, rating: float, review_count: int, query: str) -> float:
    query_bonus = 0
    for token in ("원룸", "자취", "사무실", "가성비", "휴대용", "무선", "미니"):
        if token in query:
            query_bonus += 6

    review_score = min(review_count, 5000) * 0.06
    rating_score = rating * 20
    price_score = 15 if 10000 <= price <= 150000 else 5
    return review_score + rating_score + price_score + query_bonus


def build_row(
    query: str,
    product_name: str,
    source_url: str,
    category_name: str,
    price: int,
    discount_rate: int,
    rocket_badges: str,
    rating: float,
    review_count: int,
) -> SearchProductRow:
    keyword = extract_product_keyword(product_name, query)
    score = compute_score(price, rating, review_count, query)
    position = infer_position(price, rating, review_count)
    return SearchProductRow(
        query=query,
        comparison_group=infer_comparison_group(query),
        product_name=product_name,
        product_keyword=keyword,
        source_url=source_url,
        category_name=category_name,
        price=price,
        discount_rate=discount_rate,
        rocket_badges=rocket_badges,
        rating=rating,
        review_count=review_count,
        score=score,
        position=position,
        target_reader=infer_target_reader(query),
        key_point=infer_key_point(query, position, price, rating, review_count),
    )


def scrape_search_products(driver: webdriver.Chrome, query: str, max_pages: int) -> list[SearchProductRow]:
    collected: list[SearchProductRow] = []
    seen_names: set[str] = set()

    for page_number in range(1, max_pages + 1):
        try:
            items = open_search_page(driver, query, page_number)
        except TimeoutException:
            print(f"[skip] failed to load search page {page_number}: {query}")
            break

        print(f"[crawl] query={query} page={page_number} visible_items={len(items)}")
        page_new_count = 0

        for item in items:
            try:
                product_name = item.find_element(By.CSS_SELECTOR, "div.ProductUnit_productNameV2__cV9cw").text.strip()
                if not product_name or product_name in seen_names:
                    continue

                price = extract_price_from_item(item)
                discount_rate = extract_discount_from_item(item)
                rocket_badges = extract_rocket_badges(item)
                rating = extract_rating_from_item(item)
                review_count = extract_review_count_from_item(item)

                try:
                    href = item.find_element(By.CSS_SELECTOR, "a[href*='/vp/products/']").get_attribute("href") or ""
                    product_link = href.split("?")[0]
                except Exception:
                    product_link = driver.current_url.split("?")[0]

                category_name = "검색결과"
                collected.append(
                    build_row(
                        query=query,
                        product_name=product_name,
                        source_url=product_link,
                        category_name=category_name,
                        price=price,
                        discount_rate=discount_rate,
                        rocket_badges=rocket_badges,
                        rating=rating,
                        review_count=review_count,
                    )
                )
                seen_names.add(product_name)
                page_new_count += 1
            except Exception:
                continue

        print(f"[crawl] page {page_number} added {page_new_count} new products")
        if page_new_count == 0:
            break

    return collected


def filter_products(rows: Iterable[SearchProductRow]) -> list[SearchProductRow]:
    filtered: list[SearchProductRow] = []
    for row in rows:
        if row.review_count < MIN_REVIEW_COUNT:
            continue
        if row.rating < MIN_RATING:
            continue
        filtered.append(row)

    filtered.sort(
        key=lambda item: (
            item.review_count,
            item.rating,
            item.score,
            -item.price,
        ),
        reverse=True,
    )
    return filtered


def recommend_grade(row: SearchProductRow) -> tuple[str, str]:
    if row.review_count >= 3000 and row.rating >= 4.5:
        return "A", f"리뷰 {row.review_count:,}개, 평점 {row.rating:.1f} 기준 상위 후보"
    return "B", f"리뷰 {row.review_count:,}개, 평점 {row.rating:.1f} 기준 검토 후보"


def output_fieldnames(output_path: Path, sample_row: SearchProductRow) -> tuple[list[str], bool]:
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    if file_exists:
        with output_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                return list(reader.fieldnames), True
    return list(sample_row.to_csv_row().keys()), file_exists


def save_products(rows: Iterable[SearchProductRow], output_path: Path) -> None:
    rows = list(rows)
    if not rows:
        print("[save] no products to store")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames, file_exists = output_fieldnames(output_path, rows[0])

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
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for row in rows:
            row_dict = row.to_csv_row()
            grade, reason = recommend_grade(row)
            row_dict.setdefault("검색의도점수", "")
            row_dict.setdefault("제목품질점수", "")
            row_dict.setdefault("가격적합점수", "")
            row_dict.setdefault("기본점수", f"{row.score:.2f}")
            row_dict.setdefault("광고추천점수", f"{row.score:.2f}")
            row_dict["추천등급"] = grade
            row_dict["추천사유"] = reason
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
    args = parse_args()
    output_csv = Path(args.output_csv)
    max_pages = max(1, min(int(args.max_pages), 10))

    driver = create_driver()
    debugger_mode = bool(os.getenv("COUPANG_DEBUGGER_ADDRESS", "").strip())

    try:
        print(f"[start] building comparison candidates for query={args.query}")
        if debugger_mode:
            print("[info] using existing Chrome session via remote debugger")
        rows = scrape_search_products(driver, args.query, max_pages)
        ranked = filter_products(rows)
        save_products(ranked, output_csv)
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
