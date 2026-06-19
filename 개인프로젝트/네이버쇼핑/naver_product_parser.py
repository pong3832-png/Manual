import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional


REVIEW_LINK_SELECTOR = "a[data-shp-area-id='rvmore'], a.faVe5_Gpsq"
REVIEW_ITEM_SELECTOR = "li[id^='REVIEW_ITEM_']"
REVIEW_MORE_BUTTON_SELECTOR = f"{REVIEW_ITEM_SELECTOR} a.VMyQHeqVPn"
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


@dataclass(frozen=True)
class ProductSummary:
    product_name: str
    rating: float
    recent_six_month_rating: float
    price_krw: int
    review_count: int


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    rating: Optional[int]
    content: str


class _ProductSummaryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._capture_stack = []
        self._buffers = {
            "product_name": [],
            "rating": [],
            "recent_six_month_rating": [],
            "price_krw": [],
            "review_count": [],
        }

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())
        captures = []

        if tag == "h3" and "y67cdgB6Ve" in classes:
            captures.append("product_name")
        if tag == "span" and "QDu1sxdjM6" in classes:
            captures.append("rating")
        if tag == "span" and attrs_dict.get("id", "").startswith("tooltip_text_"):
            captures.append("recent_six_month_rating")
        if tag == "span" and "weP_mymkqG" in classes:
            captures.append("price_krw")
        if tag == "a" and (
            attrs_dict.get("data-shp-area-id") == "rvmore" or "faVe5_Gpsq" in classes
        ):
            captures.append("review_count")

        self._capture_stack.append(captures)

    def handle_endtag(self, tag):
        if self._capture_stack:
            self._capture_stack.pop()

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        active_captures = {
            capture
            for captures in self._capture_stack
            for capture in captures
        }
        for capture in active_captures:
            self._buffers[capture].append(text)

    def value(self, key):
        return " ".join(self._buffers[key]).strip()


class _ReviewListParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.reviews = []
        self._current_review = None
        self._review_depth = 0
        self._capture_stack = []

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return

        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())
        element_id = attrs_dict.get("id", "")
        captures = []

        if tag == "li" and element_id.startswith("REVIEW_ITEM_"):
            if self._current_review is not None:
                self._finish_current_review()
            self._current_review = {
                "review_id": element_id.replace("REVIEW_ITEM_", "", 1),
                "rating": [],
                "content": [],
            }
            self._review_depth = 1
        elif self._current_review is not None:
            self._review_depth += 1
            if tag == "div" and "F6N7Rr56mQ" in classes:
                captures.append("rating")
            if tag == "p" and element_id.startswith("review_content_"):
                captures.append("content")

        self._capture_stack.append(captures)

    def handle_startendtag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self._capture_stack:
            self._capture_stack.pop()

        if self._current_review is None:
            return

        self._review_depth -= 1
        if self._review_depth == 0:
            self._finish_current_review()

    def handle_data(self, data):
        if self._current_review is None:
            return

        text = data.strip()
        if not text:
            return

        active_captures = {
            capture
            for captures in self._capture_stack
            for capture in captures
        }
        for capture in active_captures:
            self._current_review[capture].append(text)

    def close(self):
        super().close()
        if self._current_review is not None:
            self._finish_current_review()

    def _finish_current_review(self):
        content = _normalize_text(" ".join(self._current_review["content"]))
        if content:
            rating_text = " ".join(self._current_review["rating"])
            rating = _extract_int(rating_text, "review_rating") if rating_text else None
            self.reviews.append(
                ReviewItem(
                    review_id=self._current_review["review_id"],
                    rating=rating,
                    content=content,
                )
            )

        self._current_review = None
        self._review_depth = 0


def parse_product_summary(html):
    parser = _ProductSummaryParser()
    parser.feed(html)

    product_name = parser.value("product_name")
    rating = _extract_float(parser.value("rating"), "rating")
    recent_rating = _extract_last_float(
        parser.value("recent_six_month_rating"),
        "recent_six_month_rating",
    )
    price_krw = _extract_int(parser.value("price_krw"), "price_krw")
    review_count = _extract_int(parser.value("review_count"), "review_count")

    if not product_name:
        raise ValueError("product_name was not found")

    return ProductSummary(
        product_name=product_name,
        rating=rating,
        recent_six_month_rating=recent_rating,
        price_krw=price_krw,
        review_count=review_count,
    )


def parse_reviews(html):
    parser = _ReviewListParser()
    parser.feed(html)
    parser.close()
    return parser.reviews


def _normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def _extract_float(text, field_name):
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        raise ValueError(f"{field_name} was not found")
    return _normalize_rating(float(match.group(0)))


def _extract_last_float(text, field_name):
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        raise ValueError(f"{field_name} was not found")
    return _normalize_rating(float(matches[-1]))


def _normalize_rating(value):
    while value > 5 and value >= 10:
        value = value / 10
    return round(value, 2)


def _extract_int(text, field_name):
    match = re.search(r"\d[\d,]*", text)
    if not match:
        raise ValueError(f"{field_name} was not found")
    return int(match.group(0).replace(",", ""))
