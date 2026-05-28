import hashlib
import hmac
import json
import re
import time
import urllib.parse
import urllib.request


COUPANG_API_DOMAIN = "https://api-gateway.coupang.com"
COUPANG_API_BASE_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1"


def _clean(value, default=""):
    text = (value or "").strip()
    return text if text else default


def _get_field(row: dict, *keys: str, default: str = "") -> str:
    for key in keys:
        value = _clean(row.get(key))
        if value:
            return value
    return default


def _set_field(row: dict, key: str, value: str) -> None:
    row[key] = value


def _parse_int(value, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = re.sub(r"[^0-9]", "", str(value))
    return int(text) if text else default


def _parse_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^0-9.]", "", str(value))
    try:
        return float(text) if text else default
    except ValueError:
        return default


def _generate_hmac(method: str, path_with_query: str, secret_key: str, access_key: str) -> str:
    parts = path_with_query.split("?", 1)
    path = parts[0]
    query = parts[1] if len(parts) > 1 else ""
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = signed_date + method + path + query
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        "CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"
    )


def _call_coupang_api(method: str, path_with_query: str, *, access_key: str, secret_key: str, payload=None, timeout: int = 15):
    if not access_key or not secret_key:
        raise RuntimeError("COUPANG_ACCESS_KEY 또는 COUPANG_SECRET_KEY가 없어 쿠팡 API를 호출할 수 없습니다.")

    headers = {
        "Authorization": _generate_hmac(method, path_with_query, secret_key, access_key),
        "Content-Type": "application/json;charset=UTF-8",
    }
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{COUPANG_API_DOMAIN}{path_with_query}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode(response.headers.get_content_charset() or "utf-8")
    parsed = json.loads(body)
    if str(parsed.get("rCode", "0")) != "0":
        raise RuntimeError(f"쿠팡 API 오류: {parsed.get('rMessage') or parsed}")
    return parsed


def search_coupang_products(keyword: str, *, access_key: str, secret_key: str, sub_id: str = "", limit: int = 10):
    keyword = (keyword or "").strip()
    if not keyword:
        return [], ""

    limit = max(1, min(limit, 10))
    query_params = [
        ("keyword", keyword),
        ("limit", str(limit)),
        ("imageSize", "512x512"),
        ("srpLinkOnly", "false"),
    ]
    if sub_id:
        query_params.insert(2, ("subId", sub_id))

    query = urllib.parse.urlencode(query_params)
    path_with_query = f"{COUPANG_API_BASE_PATH}/products/search?{query}"
    result = _call_coupang_api(
        "GET",
        path_with_query,
        access_key=access_key,
        secret_key=secret_key,
    )
    data = result.get("data") or {}
    return data.get("productData") or [], data.get("landingUrl") or ""


def _api_review_count(product: dict) -> int:
    for key in (
        "reviewCount",
        "reviewCnt",
        "productReviewCount",
        "ratingCount",
        "productRatingCount",
        "review",
        "reviews",
    ):
        count = _parse_int(product.get(key))
        if count:
            return count
    return 0


def _api_rating(product: dict) -> float:
    for key in ("rating", "productRating", "starRating", "averageRating"):
        rating = _parse_float(product.get(key))
        if rating:
            return rating
    return 0.0


def _score_api_product(product: dict) -> int:
    rank = int(product.get("rank") or 999)
    score = max(0, 1000 - rank)
    review_count = _api_review_count(product)
    if review_count:
        score += min(review_count, 50000) // 5
    rating = _api_rating(product)
    if rating:
        score += int(min(rating, 5.0) * 100)
    if product.get("isRocket"):
        score += 30
    if product.get("isFreeShipping"):
        score += 15
    if product.get("productUrl"):
        score += 20
    if product.get("productPrice"):
        score += 5
    return score


def _review_first_api_product_score(product: dict) -> tuple[int, int]:
    return (_api_review_count(product), _score_api_product(product))


def _pick_best_api_product(
    products: list[dict],
    excluded_urls: set[str],
    excluded_url_keys: set[str] | None = None,
    url_key_func=None,
    score_key=None,
):
    candidates = []
    excluded_url_keys = excluded_url_keys or set()
    score_key = score_key or _score_api_product
    for product in products:
        product_url = str(product.get("productUrl") or "").strip()
        product_name = str(product.get("productName") or "").strip()
        if not product_url or not product_name:
            continue
        if product_url in excluded_urls:
            continue
        if excluded_url_keys and url_key_func:
            try:
                product_key = url_key_func(product_url)
            except Exception:
                product_key = ""
            if product_key and product_key in excluded_url_keys:
                continue
        candidates.append(product)
    if not candidates:
        return None
    return max(candidates, key=score_key)


def _merge_coupang_api_product(seed_row: dict, api_product: dict, landing_url: str = "") -> dict:
    row = dict(seed_row)
    if not api_product:
        return row

    product_name = str(api_product.get("productName") or "").strip()
    product_url = str(api_product.get("productUrl") or landing_url or "").strip()
    product_image = str(api_product.get("productImage") or "").strip()
    product_price = api_product.get("productPrice")
    is_rocket = bool(api_product.get("isRocket"))
    is_free_shipping = bool(api_product.get("isFreeShipping"))
    review_count = _api_review_count(api_product)
    rating = _api_rating(api_product)

    if product_name:
        _set_field(row, "상품명", product_name)
    if product_url:
        _set_field(row, "쿠팡링크", product_url)
    if product_image:
        _set_field(row, "상품이미지", product_image)
    if product_price is not None:
        _set_field(row, "상품가격", str(int(product_price)))
    _set_field(row, "로켓배송", "Y" if is_rocket else "N")
    _set_field(row, "무료배송", "Y" if is_free_shipping else "N")
    if review_count:
        _set_field(row, "리뷰수", str(review_count))
    if rating:
        _set_field(row, "평점", str(rating))
    _set_field(row, "API매칭방식", _clean(row.get("API매칭방식"), "keyword"))
    return row


HEALTH_SIMILAR_TERMS = (
    "오메가3",
    "비타민C",
    "비타민D",
    "비타민B",
    "멀티비타민",
    "마그네슘",
    "칼슘",
    "아연",
    "루테인",
    "유산균",
    "프로폴리스",
    "밀크씨슬",
    "콜라겐",
    "비오틴",
    "아르기닌",
    "코엔자임",
    "코큐텐",
    "홍삼",
    "MSM",
    "글루코사민",
    "커큐민",
    "쏘팔메토",
    "철분",
    "엽산",
    "단백질",
    "프로틴",
)


def _normalise_product_query(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]|\([^)]*\)", " ", text or "")
    text = re.sub(r"\b\d+\s*(?:정|캡슐|포|개|병|g|kg|ml|mg|개월|일분|일|박스)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[,/|+]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _similar_search_keywords(row: dict) -> list[str]:
    keyword = _get_field(row, "키워드", default=_get_field(row, "상품명"))
    product_name = _get_field(row, "상품명")
    candidates: list[str] = []
    for value in (keyword, product_name):
        cleaned = _normalise_product_query(value)
        if cleaned:
            candidates.append(cleaned)

    joined = " ".join(candidates)
    for term in HEALTH_SIMILAR_TERMS:
        if term.lower() in joined.lower():
            candidates.append(term)
            candidates.append(f"{term} 영양제")

    tokens = [
        token
        for token in re.findall(r"[0-9A-Za-z가-힣]+", _normalise_product_query(keyword or product_name))
        if len(token) >= 2
        and token not in {"정품", "공식", "수입", "쇼핑백", "개별포장", "건강", "영양제"}
        and not token.isdigit()
    ]
    if len(tokens) >= 2:
        candidates.append(" ".join(tokens[:2]))
    if tokens:
        candidates.append(tokens[-1])

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return deduped


def _search_best_similar_product(
    row: dict,
    *,
    access_key: str,
    secret_key: str,
    sub_id: str,
    excluded_urls: set[str],
    excluded_url_keys: set[str] | None = None,
    url_key_func=None,
):
    best_product = None
    best_keyword = ""
    best_landing_url = ""
    best_score = (-1, -1)
    for keyword in _similar_search_keywords(row):
        products_data, landing_url = search_coupang_products(
            keyword,
            access_key=access_key,
            secret_key=secret_key,
            sub_id=sub_id,
        )
        candidate = _pick_best_api_product(
            products_data,
            excluded_urls,
            excluded_url_keys=excluded_url_keys,
            url_key_func=url_key_func,
            score_key=_review_first_api_product_score,
        )
        if not candidate:
            continue
        score = _review_first_api_product_score(candidate)
        if score > best_score:
            best_product = candidate
            best_keyword = keyword
            best_landing_url = landing_url
            best_score = score
    return best_product, best_keyword, best_landing_url


def enrich_products_with_coupang_links(
    products: list[dict],
    *,
    api_enabled: bool,
    access_key: str,
    secret_key: str,
    sub_id: str = "",
    fallback_to_similar: bool = False,
    require_api_product: bool = False,
    excluded_urls: set[str] | None = None,
    excluded_url_keys: set[str] | None = None,
    url_key_func=None,
) -> list[dict]:
    if not api_enabled:
        return [dict(product) for product in products]

    enriched = []
    excluded_urls = set(excluded_urls or set())
    excluded_url_keys = set(excluded_url_keys or set())

    for product in products:
        item = dict(product)
        keyword = _get_field(item, "키워드", default=_get_field(item, "상품명"))
        products_data, landing_url = search_coupang_products(
            keyword,
            access_key=access_key,
            secret_key=secret_key,
            sub_id=sub_id,
        )
        best_product = _pick_best_api_product(
            products_data,
            excluded_urls,
            excluded_url_keys=excluded_url_keys,
            url_key_func=url_key_func,
        )
        matched_keyword = keyword
        matched_by = "keyword"
        if not best_product and fallback_to_similar:
            best_product, matched_keyword, landing_url = _search_best_similar_product(
                item,
                access_key=access_key,
                secret_key=secret_key,
                sub_id=sub_id,
                excluded_urls=excluded_urls,
                excluded_url_keys=excluded_url_keys,
                url_key_func=url_key_func,
            )
            matched_by = "similar"
        if best_product:
            item = _merge_coupang_api_product(item, best_product, landing_url)
            _set_field(item, "API검색어", matched_keyword)
            _set_field(item, "API매칭방식", matched_by)
            product_url = str(best_product.get("productUrl") or "").strip()
            if product_url:
                excluded_urls.add(product_url)
                if url_key_func:
                    try:
                        product_key = url_key_func(product_url)
                    except Exception:
                        product_key = ""
                    if product_key:
                        excluded_url_keys.add(product_key)
        elif landing_url and not require_api_product:
            _set_field(item, "쿠팡링크", landing_url)
            excluded_urls.add(landing_url)
            if url_key_func:
                try:
                    product_key = url_key_func(landing_url)
                except Exception:
                    product_key = ""
                if product_key:
                    excluded_url_keys.add(product_key)
        elif require_api_product:
            _set_field(item, "쿠팡링크", "")
            _set_field(item, "API매칭방식", "missing")

        enriched.append(item)

    return enriched
