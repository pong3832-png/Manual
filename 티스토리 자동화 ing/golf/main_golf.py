"""
티스토리 프리미엄 골프 블로그 자동화 스크립트
  - 국내 골프 3대장: 웰링턴 CC, 트리니티 CC, 잭니클라우스 GC
  - 타겟: 40~50대 프리미엄 골퍼
  - 컨셉: 공개 정보 기반 국내외 명문 골프장 SEO 정보 블로그

실행 방법
  일반 실행(공개 발행): python main_golf.py --post-type golf
  건강식품 쿠팡 글: python main_golf.py --post-type health
  로그인 저장: python main_golf.py --login
  임시저장만 실행: python main_golf.py --post-type golf --draft
  스케줄 공개 발행: python main_golf.py --post-type golf --scheduled --publish
"""

import argparse
import base64
import codecs
import csv
import hashlib
import hmac
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import encodings.idna
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

try:
    from filelock import FileLock
except ModuleNotFoundError:
    import msvcrt

    class FileLock:  # fallback when filelock isn't installed
        def __init__(self, path: str, timeout: int = 1800):
            self.path = path
            self.timeout = timeout
            self._fh = None

        def acquire(self):
            deadline = time.time() + self.timeout
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "a+b")
            while True:
                try:
                    self._fh.seek(0)
                    self._fh.write(b"0")
                    self._fh.flush()
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                    return self
                except OSError:
                    if time.time() >= deadline:
                        self._fh.close()
                        self._fh = None
                        raise TimeoutError(f"failed to acquire automation lock: {self.path}")
                    time.sleep(1.0)

        def release(self):
            if not self._fh:
                return
            try:
                self._fh.seek(0)
                try:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except PermissionError:
                    pass
            finally:
                self._fh.close()
                self._fh = None

AUTOMATION_LOCK_PATH = str(Path(__file__).resolve().parents[1] / "runtime" / "locks" / "automation.lock")

import sys as _sys
_FILE_DIR_FOR_IMPORT = Path(__file__).resolve().parent
_PROJECT_ROOT_FOR_IMPORT = _FILE_DIR_FOR_IMPORT.parent
_SRC_DIR = str(_PROJECT_ROOT_FOR_IMPORT / "src")
if _SRC_DIR not in _sys.path:
    _sys.path.insert(0, _SRC_DIR)
from tistory_automation.coupang.api import enrich_products_with_coupang_links
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)


# ------------------------------------------------------------------
# 경로 설정
# main_golf.py 위치: PROJECT_ROOT / "golf" / "main_golf.py"
# PROJECT_ROOT 위치: "티스토리 자동화 ing"
# src 패키지 위치: PROJECT_ROOT / "src"
# ------------------------------------------------------------------

PACKAGE_DIR          = Path(__file__).resolve().parent
PROJECT_ROOT         = PACKAGE_DIR.parent
CONFIG_DIR           = PROJECT_ROOT / "config"
DATA_DIR             = PROJECT_ROOT / "data"
DOCS_DIR             = PROJECT_ROOT / "docs"
SCRIPTS_DIR          = PROJECT_ROOT / "scripts"
RUNTIME_DIR          = PROJECT_ROOT / "runtime"
LOG_DIR              = RUNTIME_DIR / "logs"
CHATGPT_SESSION_DIR  = RUNTIME_DIR / "sessions" / "chatgpt"
TISTORY_SESSION_DIR  = RUNTIME_DIR / "sessions" / "tistory"
RUNTIME_SESSION_ROOT = RUNTIME_DIR / ".tmp" / "chrome-runtime-sessions"
PRODUCT_DB_PATH      = DATA_DIR / "products" / "products_db_category.csv"
HEALTH_PRODUCT_DB_DEFAULT_PATH = DATA_DIR / "products" / "건강식품_db.csv"
HEALTH_PRODUCT_DB_FALLBACK_PATH = PACKAGE_DIR / "건강식품_db.csv"
GENERATED_RESULT_DIR = RUNTIME_DIR / "outputs" / "generated_results_golf"
TISTORY_ONE_TIME_IMAGE_DIR = Path(os.getenv("TISTORY_ONE_TIME_IMAGE_DIR", str(Path.home() / "백업용")))
CHROMEDRIVER_PATH    = Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.117" / "chromedriver.exe"
SCHEDULED_LOG_DIR    = LOG_DIR / "scheduled_golf"


def _load_local_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_local_env(PROJECT_ROOT / ".env")

# Work around intermittent codec lookup issues in the embedded base Python
codecs.lookup("idna")

for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


# ------------------------------------------------------------------
# ChatGPT 설정
# ------------------------------------------------------------------

CHATGPT_URL         = "https://chatgpt.com/"
CHATGPT_PROJECT_URL = (
    "https://chatgpt.com/g/g-p-6a028cbb296081918d731dad5595cc54-golpeu"
    "/project"
)
PROMPT_TEXTAREA_XPATHS = [
    '//div[@id="prompt-textarea"]',
    '//*[@id="prompt-textarea"]/p',
    '//div[@contenteditable="true" and @id="prompt-textarea"]',
    '//div[@data-testid="composer-input"]',
    '//textarea[@id="prompt-textarea"]',
]
PROMPT_TEXTAREA_WAIT_TIMEOUT = 30

CHATGPT_RESPONSE_XPATHS = [
    '//article//div[contains(@class, "markdown")]',
    '//div[@data-message-author-role="assistant"]//div[contains(@class, "markdown")]',
    '//div[contains(@class, "markdown")]',
]
CHATGPT_GENERATED_IMAGE_XPATH = '//img[contains(@src, "backend-api/estuary/content")]'
CHATGPT_GENERATED_IMAGE_CSS   = 'img[src*="backend-api/estuary/content"]'
CHATGPT_BUSY_XPATHS = [
    '//button[@data-testid="stop-button"]',
    '//button[contains(@aria-label, "Stop")]',
    '//button[contains(@aria-label, "stop")]',
    '//button[contains(., "Stop generating")]',
]


# ------------------------------------------------------------------
# Tistory 설정
# ------------------------------------------------------------------

TISTORY_URL                    = "https://www.tistory.com/"
TISTORY_KAKAO_START_XPATH      = '//*[@id="mArticle"]/div/div[2]/div/div[1]/a'
TISTORY_KAKAO_LOGIN_XPATH      = "/html/body/div[5]/div/div/a[2]"
TISTORY_LOGIN_ID_XPATH         = '//*[@id="loginId--1"]'
TISTORY_PASSWORD_XPATH         = '//*[@id="password--2"]'
TISTORY_LOGIN_SUBMIT_XPATH     = '//button[@type="submit" and contains(@class, "submit")]'
TISTORY_NEW_POST_LINK_XPATH    = '//a[contains(@href, "jxbooklove.tistory.com/manage/newpost")]'
TISTORY_NEW_POST_URL           = "https://jxbooklove.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"
TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 30
TISTORY_EDITOR_MODE_BTN_XPATH  = '//*[@id="editor-mode-layer-btn-open"]'
TISTORY_EDITOR_HTML_XPATH      = '//*[@id="editor-mode-html-text"]'
TISTORY_EDITOR_BASIC_MENU_XPATH = '//*[@id="editor-mode-kakao-tistory"]'
TISTORY_COUPANG_CATEGORY_XPATH = '//*[@id="category-item-1226150"]/span'
TISTORY_DAILY_CATEGORY_XPATH   = '//*[@id="category-item-1226151"]/span'
TISTORY_GOLF_CATEGORY_XPATH    = '//*[@id="category-item-1226152"]/span'   # 골프 카테고리 ID → 실제 ID로 교체
TISTORY_TITLE_XPATH            = '//*[@id="post-title-inp"]'
TISTORY_BODY_PRE_XPATH         = (
    '//*[@id="html-editor-container"]/div[2]/div/div/div[6]'
    '/div[1]/div/div/div/div[5]/div/pre'
)
TISTORY_BODY_TEXTAREA_XPATH    = '//*[@id="html-editor-container"]/div[2]/div/div/div[1]/textarea'
TISTORY_BODY_FOCUS_XPATHS      = [
    TISTORY_BODY_PRE_XPATH,
    '//*[@id="html-editor-container"]//pre',
    '//*[@id="html-editor-container"]//*[contains(@class,"CodeMirror-scroll")]',
    '//*[@id="html-editor-container"]//*[contains(@class,"CodeMirror")]',
    '//*[@id="html-editor-container"]//*[contains(@class,"monaco-editor")]',
    '//*[@id="html-editor-container"]',
]
TISTORY_BODY_TEXTAREA_XPATHS   = [
    TISTORY_BODY_TEXTAREA_XPATH,
    '//*[@id="html-editor-container"]//textarea',
    '//textarea[contains(@class,"CodeMirror")]',
    '//textarea',
]
TISTORY_TAG_XPATH              = '//*[@id="tagText"]'
TISTORY_MAX_GOLF_BODY_IMAGE_UPLOADS = int(os.getenv("TISTORY_MAX_GOLF_BODY_IMAGE_UPLOADS", "4"))
HEALTH_PRODUCT_SELECTION_SCAN_LIMIT = int(os.getenv("HEALTH_PRODUCT_SELECTION_SCAN_LIMIT", "10000"))
HEALTH_PRODUCT_ENRICH_BATCH_SIZE = int(os.getenv("HEALTH_PRODUCT_ENRICH_BATCH_SIZE", "12"))

# 카테고리 이름 fallback
TISTORY_COUPANG_CATEGORY_NAME = "데이터분석하는 청년의 꿀템"
TISTORY_DAILY_CATEGORY_NAME   = "일상을 누려보자"
TISTORY_GOLF_CATEGORY_NAME    = "국내 명문 골프장"   # 티스토리 카테고리명과 일치시킬 것
TISTORY_GOLF_CATEGORY_DEFAULT = TISTORY_GOLF_CATEGORY_NAME

TISTORY_GOLF_CATEGORY_NAMES = {
    "domestic": "국내 명문 골프장",
    "wellington": "웰링턴CC",
    "trinity": "트리니티클럽",
    "jack_nicklaus": "잭니클라우스GC 코리아",
    "comparison": "골프장 비교",
    "overseas": "해외 명문 골프장",
    "usa": "미국 명문 골프장",
    "japan": "일본 명문 골프장",
    "europe": "유럽 명문 골프장",
}

TISTORY_GOLF_CATEGORY_FALLBACKS = {
    TISTORY_GOLF_CATEGORY_NAMES["wellington"]: [TISTORY_GOLF_CATEGORY_NAMES["domestic"]],
    TISTORY_GOLF_CATEGORY_NAMES["trinity"]: [TISTORY_GOLF_CATEGORY_NAMES["domestic"]],
    TISTORY_GOLF_CATEGORY_NAMES["jack_nicklaus"]: [TISTORY_GOLF_CATEGORY_NAMES["domestic"]],
    TISTORY_GOLF_CATEGORY_NAMES["comparison"]: [TISTORY_GOLF_CATEGORY_NAMES["domestic"]],
    TISTORY_GOLF_CATEGORY_NAMES["usa"]: [TISTORY_GOLF_CATEGORY_NAMES["overseas"]],
    TISTORY_GOLF_CATEGORY_NAMES["japan"]: [TISTORY_GOLF_CATEGORY_NAMES["overseas"]],
    TISTORY_GOLF_CATEGORY_NAMES["europe"]: [TISTORY_GOLF_CATEGORY_NAMES["overseas"]],
}

TISTORY_ID       = os.getenv("TISTORY_ID")
TISTORY_PASSWORD = os.getenv("TISTORY_PASSWORD")

COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
COUPANG_SUB_ID     = os.getenv("COUPANG_SUB_ID", "").strip()
COUPANG_API_ENABLED = os.getenv("COUPANG_API_ENABLED", "0").strip() in {"1", "true", "TRUE", "yes", "YES"}
COUPANG_API_HOST    = "https://api-gateway.coupang.com"
COUPANG_DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
EXACT_COUPANG_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
SUSPICIOUS_ENCODING_TOKENS = (
    "\ufffd",
    "?곗",
    "癒",
    "袁",
    "野",
    "醫",
    "移댄",
)


# ------------------------------------------------------------------
# 로그 경로
# ------------------------------------------------------------------

RUN_LOG_PATH              = LOG_DIR / "chatgpt_web_runs_golf.csv"
USED_COUPANG_URL_LOG_PATH = LOG_DIR / "used_coupang_urls_golf.csv"
PROMPT_ARCHIVE_DIR        = LOG_DIR / "prompts_golf"
PROMPT_CONFIG_PATH        = CONFIG_DIR / "prompts" / "chatgpt_web_prompts.json"
COUPANG_HTML_GUIDE_PATH   = CONFIG_DIR / "prompts" / "coupang_html_guide.md"
TISTORY_SESSION_MARKER    = TISTORY_SESSION_DIR / ".session_ready"


class TeeStream:
    def __init__(self, *streams):
        self.streams = [s for s in streams if s is not None]

    def write(self, data):
        for stream in self.streams:
            try:
                stream.write(data)
            except UnicodeEncodeError:
                encoding = getattr(stream, "encoding", None) or "utf-8"
                safe_data = data.encode(encoding, errors="replace").decode(encoding, errors="replace")
                stream.write(safe_data)
            stream.flush()
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def enable_scheduled_logging(post_type: str) -> object:
    SCHEDULED_LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_post_type = normalize_post_type(post_type)
    log_path = SCHEDULED_LOG_DIR / f"{timestamp}_{safe_post_type}.log"
    log_file = log_path.open("a", encoding="utf-8")
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)
    print(f"[log] scheduled run log: {log_path}")
    return log_file


def normalize_post_type(post_type: str | None) -> str:
    value = (post_type or "golf").strip().lower()
    if value in {"쿠팡", "coupang", "건강", "건강식품", "health", "healthfood", "supplement"}:
        return "health"
    if value in {"일상", "daily"}:
        return "daily"
    if value in {"골프", "golf"}:
        return "golf"
    raise ValueError(f"지원하지 않는 post_type 입니다: {post_type}")

def _load_prompt_config() -> dict[str, str]:
    if not PROMPT_CONFIG_PATH.exists():
        raise FileNotFoundError(f"프롬프트 설정 파일이 없습니다: {PROMPT_CONFIG_PATH}")
    config = json.loads(PROMPT_CONFIG_PATH.read_text(encoding="utf-8"))
    required_keys = {
        "body",
        "title",
        "hashtags",
        "image_1",
        "image_2",
        "daily_image",
        "daily_body",
        "daily_meta",
    }
    missing = sorted(required_keys - set(config))
    if missing:
        raise KeyError(f"프롬프트 설정 누락: {', '.join(missing)}")
    return config


def _load_text_file(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{label} 파일이 비어 있습니다: {path}")
    return text


def _assert_prompt_text_clean(prompt_text: str, label: str) -> None:
    detected = [token for token in SUSPICIOUS_ENCODING_TOKENS if token in prompt_text]
    if detected:
        raise ValueError(
            f"{label} 프롬프트에 깨진 문자(인코딩 오류)가 감지되어 실행을 중단합니다. "
            f"config/prompts 파일을 UTF-8로 복구하세요. detected={detected!r}"
        )


# ------------------------------------------------------------------
# 프롬프트 설정
# ------------------------------------------------------------------
_PROMPT_CONFIG = _load_prompt_config()
COUPANG_HTML_GUIDE = ""
PROMPT_BODY = _PROMPT_CONFIG["body"]
PROMPT_TITLE = _PROMPT_CONFIG["title"]
PROMPT_HASHTAGS = _PROMPT_CONFIG["hashtags"]
PROMPT_IMAGE_1 = _PROMPT_CONFIG["image_1"]
PROMPT_IMAGE_2 = _PROMPT_CONFIG["image_2"]
PROMPT_DAILY_IMAGE = _PROMPT_CONFIG["daily_image"]
PROMPT_DAILY_BODY = _PROMPT_CONFIG["daily_body"]
PROMPT_DAILY_META = _PROMPT_CONFIG["daily_meta"]

HEALTH_COUPANG_BODY_PROMPT_TEMPLATE = """
너는 구글 SEO와 쿠팡 파트너스에 특화된 한국어 티스토리 블로그 에디터다.
아래 상품 정보만 바탕으로 건강식품/영양제 구매 전 비교 가이드 HTML 본문을 작성한다.

[출력 규칙]
- HTML 본문만 출력한다. 설명, 메모, 코드블록, 마크다운, JSON은 출력하지 않는다.
- 첫 글자는 반드시 <p>로 시작한다.
- 허용 태그: <p>, <h2>, <h3>, <ul>, <li>, <strong>, <a>
- style 속성, class 속성, <img>, <figure>, <table>, <script>, <style>은 쓰지 않는다. 티스토리 인라인 스타일은 로컬 코드가 자동 적용한다.
- 본문 내용은 1800~2400자 정도로 작성한다.
- 생성 이미지 placeholder와 두 번째 이미지는 절대 쓰지 않는다.

[필수 고지]
첫 줄은 아래 문장만 담은 <p>로 시작한다.
{disclosure}

[상품 정보]
- 대표 키워드: {keyword}
- 연관 키워드: {keywords}
- 비교 상품 수: {product_count}개
- 타깃 독자: {target_reader}
- 사용 시나리오: {usage_scenario}
- 독자 고민: {pain_point}
{products_summary}

[건강식품 작성 원칙]
- 질병 치료, 예방, 완치, 의학적 효능 보장처럼 보이는 표현은 금지한다.
- 골프 실력 향상, 통증 개선, 체중감량 보장도 금지한다.
- 성분표, 섭취량, 용량, 가격 확인 기준, 리뷰 수, 배송, 휴대성, 당류/카페인/알레르기 주의 여부를 비교한다.
- "가장 무난한 기준점 1개 + 상황별 대안 1~2개" 구조로 설명한다.
- 건강 상태, 복용 중인 약, 임신/수유, 알레르기, 수술 전후, 만성질환이 있으면 상세페이지 표시사항과 전문가 상담이 필요하다고 안내한다.

[구성]
1. 문제 인식과 구매 전 확인이 필요한 이유
2. 한눈에 보는 선택 기준
3. 성분표와 섭취량을 볼 때 주의할 점
4. 1순위 기준점 후보와 이유
5. 상황별 대안 후보
6. 구매 전 체크 포인트
7. FAQ 3개
8. 링크 반복 없는 마무리

[링크 규칙]
- 각 상품 섹션 끝에만 링크를 1개씩 넣는다.
- 링크 href는 상품 정보의 링크 마커를 그대로 사용한다. 예: <a href="[PRODUCT_LINK_1]">가격, 성분표, 리뷰 수 확인</a>
- 링크 바로 앞 문장은 "가격, 성분표, 섭취량, 리뷰 수를 최종 확인할 때"처럼 정보 확인형으로 쓴다.
- 하단에 링크를 다시 모으지 않는다.
""".strip()

HEALTH_COUPANG_IMAGE_PROMPT_TEMPLATE = """
Create one realistic blog thumbnail image for a Korean affiliate product review article. No explanation.

[Article context]
- Main topic: {keyword}
- Primary advertised product use scene: {health_image_focus}
- Product group cues: {health_image_cues}
- Reader: 40s-50s people who compare daily nutrition products before purchase.

[Image]
- The main subject must be a person naturally using the primary advertised product type described above.
- Show hands or a partial adult figure using the product in a realistic daily setting, such as kitchen counter, desk, or post-round home routine.
- The product type must be visually clear: for lemon juice show pouring/squeezing into water; for protein drink show drinking or pouring into a glass; for supplement tablets show taking/preparing capsules with water.
- Include only secondary comparison cues in the background, such as a checklist notebook or another generic supplement item.
- The image must look like the product is actually being used, not just a random healthy lifestyle scene.
- Bright realistic photo style, premium but practical, 16:9 horizontal ratio.

[Forbidden]
- Brand names, product names, logos, package text, readable letters, watermark
- Exact package recreation or copying a real retail product appearance
- Medical treatment imagery, hospital imagery, disease cure mood
- Ad-like purchase-pushing composition
- Illustration, cartoon, 3D render
""".strip()

HEALTH_COUPANG_TITLE_RULES = """
[건강식품 제목 추가 규칙]
- 치료, 예방, 효과 보장, 체중감량 보장처럼 의료 효능으로 보이는 단어는 제목에 쓰지 않는다.
- 대표 키워드를 제목 맨 앞에 그대로 반복하지 않는다. 특히 "중년 단백질", "40대", "50대", "중년", "건강식품", "영양제", "추천"으로 시작하는 제목은 실패다.
- 제목은 실제 검색자가 입력할 만한 롱테일 검색어처럼 만든다. 비교 후보 상품명에서 보이는 구체 제품군, 성분, 제형, 섭취 상황을 먼저 잡고 구매 전 확인 의도를 붙인다.
- 상품명이 검색 유입에 도움이 되면 대표 상품명 또는 상품명 일부를 1개만 자연스럽게 포함한다. 단, 상품명 2개 이상을 나열하지 않는다.
- "중년"은 꼭 필요할 때만 제목 중간이나 뒤쪽에 1회 사용한다. 모든 제목의 핵심을 "중년 단백질"로 고정하지 않는다.
- 권장 구조는 다음 중 하나를 고른다: "구체 제품군 + 성분표/섭취량 체크", "대표 상품명 + 구매 전 확인", "제품군 + 가격·리뷰 비교", "섭취 상황 + 선택 기준".
- 제목 끝은 비교, 선택 기준, 구매 전 확인, 성분표 체크, 리뷰 확인 중 하나로 자연스럽게 마무리한다.
- 복잡한 말장난보다 검색 의도가 분명한 제목을 우선한다. 30~48자 안에서 제품군과 확인 포인트가 바로 보여야 한다.
""".strip()

HEALTH_COUPANG_HASHTAG_RULES = """
[건강식품 해시태그 추가 규칙]
- 건강식품, 영양제, 성분표, 섭취량, 중년건강, 쿠팡비교, 구매전확인 계열 태그를 우선 고려한다.
- 질병명, 치료, 완치, 효과보장, 다이어트보장 계열 태그는 쓰지 않는다.
""".strip()

MASTER_PROMPTS = {
    "body": PROMPT_BODY,
    "title": PROMPT_TITLE,
    "hashtags": PROMPT_HASHTAGS,
}


# ------------------------------------------------------------------
# 유틸리티
# ------------------------------------------------------------------
def random_sleep(min_sec: float = 2, max_sec: float = 4) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def fill_prompt(template: str, values: dict) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def build_coupang_body_prompt(values: dict) -> str:
    global COUPANG_HTML_GUIDE
    if values.get("content_vertical") == "health_supplement":
        combined = fill_prompt(HEALTH_COUPANG_BODY_PROMPT_TEMPLATE, values).strip()
        _assert_prompt_text_clean(combined, "건강식품 쿠팡 본문")
        return combined

    if not COUPANG_HTML_GUIDE:
        COUPANG_HTML_GUIDE = _load_text_file(COUPANG_HTML_GUIDE_PATH, "쿠팡 HTML 지침서")
    body_template = MASTER_PROMPTS["body"]
    prompt_parts = [
        COUPANG_HTML_GUIDE.strip(),
        fill_prompt(body_template, values).strip(),
    ]
    combined = "\n\n".join(part for part in prompt_parts if part)
    _assert_prompt_text_clean(combined, "쿠팡 본문")
    return combined


def build_health_coupang_image_prompt(values: dict) -> str:
    prompt = fill_prompt(HEALTH_COUPANG_IMAGE_PROMPT_TEMPLATE, values).strip()
    _assert_prompt_text_clean(prompt, "건강식품 쿠팡 이미지")
    return prompt


def build_coupang_title_prompt(values: dict) -> str:
    prompt = fill_prompt(MASTER_PROMPTS["title"], values).strip()
    if values.get("content_vertical") == "health_supplement":
        prompt = "\n\n".join([prompt, HEALTH_COUPANG_TITLE_RULES])
    _assert_prompt_text_clean(prompt, "쿠팡 제목")
    return prompt


def build_coupang_hashtags_prompt(values: dict) -> str:
    prompt = fill_prompt(MASTER_PROMPTS["hashtags"], values).strip()
    if values.get("content_vertical") == "health_supplement":
        prompt = "\n\n".join([prompt, HEALTH_COUPANG_HASHTAG_RULES])
    _assert_prompt_text_clean(prompt, "쿠팡 해시태그")
    return prompt


# ------------------------------------------------------------------
# 드라이버 생명주기
# ------------------------------------------------------------------

def _browser_headless_enabled() -> bool:
    return os.getenv("TISTORY_HEADLESS", "0").strip().lower() in {"1", "true", "yes", "y"}


def _running_in_scheduled_mode() -> bool:
    return os.getenv("TISTORY_SCHEDULED", "0").strip().lower() in {"1", "true", "yes", "y"}


def _build_options(user_data_dir: Path, *, headless: bool = False) -> Options:
    opts = Options()
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1440,1200")
    else:
        opts.add_argument("--start-maximized")
    return opts


def _version_tuple(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value or "")
    return tuple(int(part) for part in numbers[:4]) if numbers else (0,)


def _get_installed_chrome_major() -> str | None:
    if os.getenv("CHROME_MAJOR_VERSION"):
        return os.getenv("CHROME_MAJOR_VERSION", "").strip() or None

    app_dirs: list[Path] = []
    if os.getenv("CHROME_BINARY_PATH"):
        app_dirs.append(Path(os.getenv("CHROME_BINARY_PATH", "")).expanduser().parent)
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base_dir = os.getenv(env_name)
        if base_dir:
            app_dirs.append(Path(base_dir) / "Google" / "Chrome" / "Application")

    version_names: list[str] = []
    for app_dir in app_dirs:
        if not app_dir.exists():
            continue
        try:
            version_names.extend(
                child.name
                for child in app_dir.iterdir()
                if child.is_dir() and re.match(r"^\d+\.", child.name)
            )
        except OSError:
            continue

    if not version_names:
        return None
    version_names.sort(key=_version_tuple, reverse=True)
    return version_names[0].split(".", 1)[0]


def _matching_chromedriver_paths(chrome_major: str | None) -> list[Path]:
    if not chrome_major:
        return []

    candidates: list[Path] = []
    roots = [
        Path.home() / ".wdm" / "drivers" / "chromedriver" / "win64",
        Path.home() / ".cache" / "selenium" / "chromedriver" / "win64",
    ]
    for root in roots:
        if not root.exists():
            continue
        try:
            version_dirs = sorted(
                [path for path in root.iterdir() if path.is_dir() and path.name.startswith(f"{chrome_major}.")],
                key=lambda path: _version_tuple(path.name),
                reverse=True,
            )
        except OSError:
            continue
        for version_dir in version_dirs:
            candidates.extend(
                [
                    version_dir / "chromedriver.exe",
                    version_dir / "chromedriver-win32" / "chromedriver.exe",
                    version_dir / "chromedriver-win64" / "chromedriver.exe",
                ]
            )
    return candidates


def _driver_path_matches_chrome_major(driver_path: Path, chrome_major: str | None) -> bool:
    if not chrome_major:
        return True
    return any(part.startswith(f"{chrome_major}.") for part in driver_path.parts)


def _candidate_chromedriver_paths() -> list[Path]:
    env_driver = Path(os.getenv("CHROMEDRIVER_PATH", "")).expanduser() if os.getenv("CHROMEDRIVER_PATH") else None
    chrome_major = _get_installed_chrome_major()
    matching_drivers = _matching_chromedriver_paths(chrome_major)
    candidates: list[Path] = []
    if env_driver and _driver_path_matches_chrome_major(env_driver, chrome_major):
        candidates.append(env_driver)
    candidates.extend(matching_drivers)
    if env_driver and not _driver_path_matches_chrome_major(env_driver, chrome_major):
        candidates.append(env_driver)
    candidates.extend(
        [
            CHROMEDRIVER_PATH,
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.117" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.56" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "146.0.7680.165" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "145.0.7632.117" / "chromedriver.exe",
        ]
    )

    existing: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        existing.append(path)
    return existing


def _create_chrome_driver_with_local_binary(opts: Options) -> webdriver.Chrome | None:
    for driver_path in _candidate_chromedriver_paths():
        try:
            print(f"[ChromeDriver] 로컬 드라이버 사용: {driver_path}")
            return webdriver.Chrome(service=Service(str(driver_path)), options=opts)
        except Exception as exc:
            print(f"[ChromeDriver] 실패: {driver_path} -> {exc}")
    return None


def create_driver(save_session: bool = False, session_dir: Path = CHATGPT_SESSION_DIR) -> webdriver.Chrome:
    # 세션 폴더를 직접 사용해 SQLite 복사 충돌과 로그 분리를 함께 처리합니다.
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # 비정상 종료 뒤 남아 있는 잠금 파일을 제거해 드라이버 생성 충돌을 막습니다.
    lock_file = session_dir / "SingletonLock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except OSError:
            pass
            
    headless = _browser_headless_enabled()
    opts = _build_options(session_dir, headless=headless)
    driver = _create_chrome_driver_with_local_binary(opts)
    if driver is None:
        driver = webdriver.Chrome(options=opts)

    if headless:
        driver.set_window_size(1440, 1200)
    else:
        driver.maximize_window()
    return driver


def quit_driver(driver: webdriver.Chrome, *, keep_browser: bool = False) -> None:
    if not keep_browser:
        try:
            driver.quit()
        except Exception:
            pass


def _reset_browser_session_dir(session_dir: Path) -> None:
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    session_dir.mkdir(parents=True, exist_ok=True)


CAPTCHA_LOCK_FILE = RUNTIME_DIR / "locks" / "captcha_lock.txt"

def check_captcha_lock() -> bool:
    if CAPTCHA_LOCK_FILE.exists():
        try:
            lock_time = float(CAPTCHA_LOCK_FILE.read_text(encoding="utf-8").strip())
            elapsed = time.time() - lock_time
            if elapsed < 3 * 3600:
                left_minutes = int((3 * 3600 - elapsed) / 60)
                print(f"[안내] 캡챠(로봇 방지) 쿨타임 중입니다. 스케줄러 실행을 건너뜁니다. (남은 시간: {left_minutes}분)")
                return True
        except Exception:
            pass
    return False

def set_captcha_lock() -> None:
    try:
        CAPTCHA_LOCK_FILE.write_text(str(time.time()), encoding="utf-8")
        print("[안내] 캡챠 락(3시간 대기)을 설정했습니다.")
    except Exception as e:
        print(f"[경고] 캡챠 락 설정 실패: {e}")

def _has_saved_tistory_session() -> bool:
    if not TISTORY_SESSION_MARKER.exists():
        return False
    if not TISTORY_SESSION_DIR.exists():
        return False
    default_dir = TISTORY_SESSION_DIR / "Default"
    local_state = TISTORY_SESSION_DIR / "Local State"
    login_data = default_dir / "Login Data"
    cookies = default_dir / "Network" / "Cookies"
    return (
        default_dir.exists()
        and local_state.exists()
        and (login_data.exists() or cookies.exists())
    )


def _handle_tistory_editor_alert(driver: webdriver.Chrome, timeout: int = 2) -> None:
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        text = alert.text or ""
        if "저장된 글" in text or "이어서 작성" in text:
            print("[Tistory] 저장된 글 이어쓰기 알림 감지 - 새 글 작성을 위해 취소합니다.")
            alert.dismiss()
        else:
            print(f"[Tistory] 알림 감지 - 확인 처리합니다: {text}")
            alert.accept()
        random_sleep(0.5, 1.0)
    except TimeoutException:
        pass
    except Exception as exc:
        print(f"[Tistory] 알림 처리 중 경고: {exc}")


def _save_tistory_session_once(attempt: int) -> None:
    print(f"\n[로그인 저장 모드] Tistory 세션 저장 경로: {TISTORY_SESSION_DIR}")
    print(f"[Tistory] 세션 저장 시도 {attempt}/2")
    print("기존 티스토리 세션 폴더를 초기화한 뒤 다시 저장합니다.")
    _reset_browser_session_dir(TISTORY_SESSION_DIR)
    if TISTORY_SESSION_MARKER.exists():
        try:
            TISTORY_SESSION_MARKER.unlink()
        except OSError:
            pass

    print("브라우저가 열리면 Tistory(카카오) 로그인 후 글쓰기 화면까지 연 다음 엔터를 누르세요.\n")
    driver = create_driver(save_session=True, session_dir=TISTORY_SESSION_DIR)
    try:
        driver.get(TISTORY_NEW_POST_URL)
        input("→ Tistory 로그인 및 글쓰기 화면 진입 확인 후 엔터를 누르세요...")
        print("[검증 중] 저장한 티스토리 세션으로 글쓰기 화면 진입을 다시 확인합니다...")
        login_and_open_tistory_editor(driver)
        TISTORY_SESSION_MARKER.write_text(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            encoding="utf-8",
        )
        if not _has_saved_tistory_session():
            raise RuntimeError("티스토리 세션 파일 검증에 실패했습니다.")
        print("[저장 중] Tistory 브라우저를 정상 종료합니다...")
    finally:
        try:
            quit_driver(driver, keep_browser=False)
        except Exception:
            pass


def save_tistory_session() -> None:
    last_error = None
    for attempt in (1, 2):
        try:
            _save_tistory_session_once(attempt)
            print(f"[완료] Tistory 세션 저장: {TISTORY_SESSION_DIR}")
            return
        except Exception as exc:
            last_error = exc
            print(f"[경고] 티스토리 세션 저장 실패: {exc}")
            print("[경고] 티스토리 세션 폴더를 삭제하고 다시 시도합니다.")
            _reset_browser_session_dir(TISTORY_SESSION_DIR)
            if TISTORY_SESSION_MARKER.exists():
                try:
                    TISTORY_SESSION_MARKER.unlink()
                except OSError:
                    pass
    raise RuntimeError(f"티스토리 세션 저장에 두 번 실패했습니다: {last_error}")


# ------------------------------------------------------------------
# ChatGPT 동작
# ------------------------------------------------------------------

def prepare_chatgpt_project(driver: webdriver.Chrome) -> None:
    print("[ChatGPT] 프로젝트 접속 중...")
    driver.get(CHATGPT_PROJECT_URL)
    random_sleep(0.6, 1.2)


def _find_textarea(driver: webdriver.Chrome):
    combined = " | ".join(PROMPT_TEXTAREA_XPATHS)
    try:
        WebDriverWait(driver, PROMPT_TEXTAREA_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, combined))
        )
    except TimeoutException:
        raise TimeoutException(
            f"ChatGPT 입력창을 {PROMPT_TEXTAREA_WAIT_TIMEOUT}초 안에 찾지 못했습니다. "
            "페이지 로 로드 상태와 로그인 여부를 확인하세요."
        )
    for xpath in PROMPT_TEXTAREA_XPATHS:
        elements = driver.find_elements(By.XPATH, xpath)
        if elements:
            return elements[0]
    raise NoSuchElementException("ChatGPT 입력창을 찾을 수 없습니다.")


def _set_clipboard(text: str) -> None:
    """
    Windows 기본 clip 명령으로 클립보드에 텍스트를 복사합니다.
    tkinter 방식은 root.destroy() 시점에 클립보드 소유권이 사라져
    Ctrl+V 시점에 내용이 비어 버리는 문제가 있어 이 방식으로 대체합니다.
    """
    proc = subprocess.Popen(
        ["clip"],
        stdin=subprocess.PIPE,
        shell=True,
    )
    proc.communicate(input=text.encode("utf-16le"))


def _paste_via_js(driver: webdriver.Chrome, textarea, prompt_text: str) -> bool:
    """
    JavaScript execCommand('insertText')로 직접 텍스트를 넣습니다.
    ChatGPT의 React contenteditable에서 Ctrl+V가 실패할 때 쓰는 보조 방식입니다.
    성공하면 True, 실패하면 False를 반환합니다.
    """
    try:
        driver.execute_script(
            """
            const el = arguments[0];
            el.focus();
            const inserted = document.execCommand('insertText', false, arguments[1]);
            if (!inserted) {
                // execCommand 미지원 환경 대비 input 이벤트를 수동으로 발생
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLElement.prototype, 'textContent'
                );
                el.textContent = arguments[1];
                el.dispatchEvent(new InputEvent('input', {bubbles: true}));
            }
            """,
            textarea,
            prompt_text,
        )
        return True
    except Exception as e:
        print(f"[경고] JS 입력 실패: {e}")
        return False


def _paste_via_clipboard(driver: webdriver.Chrome, textarea, prompt_text: str) -> bool:
    try:
        _set_clipboard(prompt_text)
        time.sleep(0.5)
        textarea.click()
        textarea.send_keys(Keys.CONTROL, "v")
        return True
    except Exception as exc:
        print(f"[경고] 클립보드 입력 실패: {exc}")
        return False


def _paste_via_cdp(driver: webdriver.Chrome, textarea, prompt_text: str) -> bool:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
        textarea.click()
        driver.execute_cdp_cmd("Input.insertText", {"text": prompt_text})
        return True
    except Exception as exc:
        print(f"[경고] CDP 입력 실패: {exc}")
        return False


def _clear_prompt_textarea(driver: webdriver.Chrome, textarea) -> None:
    try:
        textarea.click()
        textarea.send_keys(Keys.CONTROL, "a")
        textarea.send_keys(Keys.DELETE)
        random_sleep(0.2, 0.4)
    except Exception:
        try:
            driver.execute_script(
                """
                const el = arguments[0];
                el.focus();
                el.textContent = '';
                el.dispatchEvent(new InputEvent('input', {bubbles: true}));
                """,
                textarea,
            )
        except Exception:
            pass


def _prompt_input_has_expected_length(driver: webdriver.Chrome, prompt_text: str) -> tuple[bool, int]:
    current_text = _get_prompt_textarea_text(driver)
    expected_len = len(prompt_text)
    if expected_len >= 12000:
        required_len = int(expected_len * 0.82)
    elif expected_len >= 3000:
        required_len = int(expected_len * 0.75)
    else:
        required_len = max(1, int(expected_len * 0.55))
    return len(current_text) >= required_len, len(current_text)


def input_prompt(driver: webdriver.Chrome, prompt_text: str) -> None:
    """
    프롬프트를 ChatGPT 입력창에 입력합니다.
    1차는 Windows clip 명령으로 클립보드 복사 후 Ctrl+V,
    2차는 1차 실패 시 JavaScript execCommand로 직접 삽입합니다.
    """
    _assert_prompt_text_clean(prompt_text, "입력 대상")

    textarea = _find_textarea(driver)
    textarea.click()
    random_sleep(0.5, 1)

    _clear_prompt_textarea(driver, textarea)

    is_long_prompt = len(prompt_text) >= 12000
    if is_long_prompt:
        attempts = [
            ("Chrome DevTools 직접 입력", _paste_via_cdp),
            ("클립보드 붙여넣기", _paste_via_clipboard),
            ("JavaScript 직접 입력", _paste_via_js),
        ]
    else:
        attempts = [
            ("클립보드 붙여넣기", _paste_via_clipboard),
            ("Chrome DevTools 직접 입력", _paste_via_cdp),
            ("JavaScript 직접 입력", _paste_via_js),
        ]

    last_len = 0
    for attempt_idx, (label, inserter) in enumerate(attempts, start=1):
        if attempt_idx > 1:
            _clear_prompt_textarea(driver, textarea)
        print(f"[입력] {label} 시도 ({attempt_idx}/{len(attempts)}, {len(prompt_text)}자)")
        if not inserter(driver, textarea, prompt_text):
            continue
        random_sleep(1.0, 1.5)
        ok, actual_len = _prompt_input_has_expected_length(driver, prompt_text)
        last_len = actual_len
        if ok:
            print(f"[입력] 프롬프트 입력 길이 확인 완료 ({actual_len}/{len(prompt_text)}자)")
            print(f"[입력] 프롬프트 입력 완료 ({len(prompt_text)}자)")
            return
        print(f"[경고] {label} 후 입력 길이 부족: {actual_len}/{len(prompt_text)}자")

    raise RuntimeError(
        f"프롬프트 입력에 실패했습니다. 입력창 글자 수가 부족합니다: {last_len}/{len(prompt_text)}자"
    )


def _wait_for_prompt_settle(prompt_text: str) -> None:
    prompt_len = len(prompt_text)
    if prompt_len >= 6000:
        wait_seconds = 7.0
    elif prompt_len >= 3500:
        wait_seconds = 5.5
    elif prompt_len >= 1800:
        wait_seconds = 4.0
    elif prompt_len >= 900:
        wait_seconds = 2.5
    else:
        wait_seconds = 1.5
    print(f"[대기] 입력 반영 대기 {wait_seconds:.1f}초")
    time.sleep(wait_seconds)


def _get_prompt_textarea_text(driver: webdriver.Chrome) -> str:
    try:
        textarea = _find_textarea(driver)
        text = (textarea.text or "").strip()
        if not text:
            text = (driver.execute_script(
                "return arguments[0].value || arguments[0].innerText || arguments[0].textContent || '';",
                textarea,
            ) or "").strip()
        return text
    except Exception:
        return ""


def _click_chatgpt_send_button(driver: webdriver.Chrome) -> bool:
    send_button_xpaths = [
        '//button[@data-testid="send-button"]',
        '//button[@data-testid="composer-submit-button"]',
        '//button[contains(@data-testid, "send")]',
        '//button[contains(@data-testid, "submit")]',
        '//button[contains(@aria-label, "Send")]',
        '//button[contains(@aria-label, "send")]',
        '//button[contains(@aria-label, "보내기")]',
        '//button[contains(@aria-label, "전송")]',
        '//button[contains(@class, "send")]',
    ]
    for xpath in send_button_xpaths:
        try:
            for button in driver.find_elements(By.XPATH, xpath):
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].click();", button)
                    random_sleep(0.5, 1.0)
                    return True
        except Exception:
            continue
    return False


def _verify_prompt_submitted(driver: webdriver.Chrome, before_text: str, timeout: float = 8.0) -> None:
    started_at = time.time()
    while time.time() - started_at < timeout:
        current_text = _get_prompt_textarea_text(driver)
        if not current_text:
            print("[전송] 프롬프트 전송 확인: 입력창 비워짐")
            return
        if before_text and current_text != before_text:
            print("[전송] 프롬프트 전송 확인: 입력창 내용 변경")
            return
        time.sleep(0.5)
    raise RuntimeError("ChatGPT 프롬프트가 전송되지 않았습니다. 입력창에 프롬프트가 남아 있어 중단합니다.")


def submit_prompt(driver: webdriver.Chrome) -> None:
    """프롬프트를 전송하고 입력창이 실제로 비워졌는지 확인합니다."""
    textarea = _find_textarea(driver)
    before_text = _get_prompt_textarea_text(driver)

    if _click_chatgpt_send_button(driver):
        print("[전송] 전송 버튼 클릭")
        _verify_prompt_submitted(driver, before_text)
        return

    print("[전송] 전송 버튼을 찾지 못해 Enter 전송 시도")
    textarea.send_keys(Keys.ENTER)
    random_sleep(0.8, 1.2)

    if _click_chatgpt_send_button(driver):
        print("[전송] Enter 후 전송 버튼 클릭")

    _verify_prompt_submitted(driver, before_text)


def _get_response_elements(driver: webdriver.Chrome) -> list:
    for xpath in CHATGPT_RESPONSE_XPATHS:
        els = driver.find_elements(By.XPATH, xpath)
        if els:
            return els
    return []


def _latest_non_empty_response_text(elements: list, previous_count: int = 0) -> str:
    candidates = elements[previous_count:] if previous_count and len(elements) > previous_count else elements
    for el in reversed(candidates):
        try:
            text = el.text.strip()
        except Exception:
            continue
        if text:
            return text
    return ""


def _get_image_urls(driver: webdriver.Chrome) -> list[str]:
    # lazy 이미지 강제 로딩을 위해 ChatGPT 응답 영역까지 스크롤
    try:
        driver.execute_script("""
            const imgs = document.querySelectorAll('img[src*="backend-api/estuary/content"]');
            for (const img of imgs) {
                img.scrollIntoView({block: 'center'});
            }
        """)
        time.sleep(1.5)  # 스크롤 후 lazy 이미지 로딩 대기
    except Exception:
        pass

    try:
        raw_urls = driver.execute_script(
            """
            const urls = [];
            const seen = new Set();
            const selectors = [
                'img[src*="backend-api/estuary/content"]',
                'img[data-src*="backend-api/estuary/content"]',
                '[id^="image-"] img'
            ];
            for (const selector of selectors) {
                for (const el of document.querySelectorAll(selector)) {
                    // 우선순위: el.src(브라우저 디코딩 완료) > currentSrc > getAttribute(raw, &amp; 포함 가능)
                    let src = '';
                    if (el.src && el.src.includes('backend-api/estuary/content')) {
                        src = el.src;
                    } else if (el.currentSrc && el.currentSrc.includes('backend-api/estuary/content')) {
                        src = el.currentSrc;
                    } else {
                        const rawAttr = el.getAttribute('src') || el.getAttribute('data-src') || '';
                        src = rawAttr.replace(/&amp;/g, '&').replace(/\\u0026/g, '&');
                    }
                    if (!src || !src.includes('backend-api/estuary/content') || seen.has(src)) {
                        continue;
                    }
                    seen.add(src);
                    urls.push(src);
                }
            }
            return urls;
            """
        )
    except Exception:
        return []
    return [url for url in raw_urls if isinstance(url, str) and url]



def _save_live_image_urls(urls: list[str]) -> None:
    if not urls:
        return
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_RESULT_DIR / "image_urls_live.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")


def _is_chatgpt_busy(driver: webdriver.Chrome) -> bool:
    for xpath in CHATGPT_BUSY_XPATHS:
        try:
            if driver.find_elements(By.XPATH, xpath):
                return True
        except Exception:
            continue
    return False


def _get_chatgpt_generation_error(driver: webdriver.Chrome) -> str:
    """ChatGPT 화면에 표시된 생성 실패/중단 문구를 감지합니다."""
    try:
        body_text = driver.execute_script("return document.body ? (document.body.innerText || '') : '';") or ""
    except Exception:
        return ""
    normalized = re.sub(r"\s+", " ", str(body_text)).strip()
    if not normalized:
        return ""

    hard_error_phrases = (
        "Something went wrong while generating the response",
        "If this issue persists please contact us",
        "문제가 발생",
        "응답을 생성하는 중",
        "다시 시도",
    )
    soft_stall_phrases = (
        "스트리밍이 중지되었습니다",
        "메시지 완료를 기다리는 중",
        "Streaming stopped",
        "waiting for the message to complete",
    )
    for phrase in hard_error_phrases:
        if phrase.lower() in normalized.lower():
            return phrase
    for phrase in soft_stall_phrases:
        if phrase.lower() in normalized.lower():
            return phrase
    return ""


def _wait_until_chatgpt_ready(driver: webdriver.Chrome, timeout: int = 180, stable_seconds: int = 10) -> None:
    started_at = time.time()
    last_busy_at = time.time()
    while time.time() - started_at < timeout:
        if _is_chatgpt_busy(driver):
            last_busy_at = time.time()
            time.sleep(1)
            continue
        if time.time() - last_busy_at >= stable_seconds:
            return
        time.sleep(1)
    raise TimeoutError("ChatGPT 응답 완료 대기 시간 초과")


def _wait_for_text(
    driver: webdriver.Chrome,
    previous_count: int = 0,
    timeout: int = 240,
    stable_seconds: int = 8,
    max_timeout: int = 900,
) -> str:
    started_at = time.time()
    effective_timeout = timeout          # busy/텍스트 변화 시 자동 연장될 수 있음
    last_text = ""
    last_changed_at = time.time()
    response_detected = False
    no_response_warned = False
    last_log_at = 0.0                    # 경과 로그 중복 방지
    while time.time() - started_at < effective_timeout:
        elapsed = time.time() - started_at
        els = _get_response_elements(driver)
        busy = _is_chatgpt_busy(driver)

        # 새 응답 DOM 감지가 늦어도 같은 프롬프트를 다시 보내면 ChatGPT가 본문을 중복 생성한다.
        # 따라서 여기서는 경고만 남기고, timeout까지 기다린 뒤 실패 처리한다.
        if not response_detected and not no_response_warned and elapsed > 45:
            no_response_warned = True
            print(
                f"[경고] {int(elapsed)}초 경과, 새 응답 요소 미감지. "
                "중복 생성을 막기 위해 프롬프트를 재전송하지 않고 계속 대기합니다."
            )

        if len(els) > previous_count:
            if not response_detected:
                response_detected = True
                print(f"[응답] 새 응답 감지 ({int(elapsed)}초 경과)")
            current = _latest_non_empty_response_text(els, previous_count=previous_count)
            if current and current != last_text:
                last_text = current
                last_changed_at = time.time()

            # ── 핵심: ChatGPT가 아직 답변 중이거나 텍스트가 변하고 있으면 timeout 연장 ──
            text_still_changing = (time.time() - last_changed_at) < stable_seconds
            if (busy or text_still_changing) and effective_timeout < max_timeout:
                effective_timeout = min(effective_timeout + 30, max_timeout)

            # 60초마다 경과 로그 출력 (응답 생성 중임을 알려줌)
            if elapsed - last_log_at >= 60:
                last_log_at = elapsed
                text_len = len(last_text) if last_text else 0
                status = "생성 중..." if (busy or text_still_changing) else "안정화 대기"
                print(f"[대기] {int(elapsed)}초 경과 | 응답 {text_len}자 | {status} (제한: {effective_timeout}초)")

            # 텍스트 안정 + busy 해제 → 완료
            if last_text and not text_still_changing and not busy:
                _wait_until_chatgpt_ready(driver, timeout=min(120, effective_timeout), stable_seconds=6)
                return last_text
        time.sleep(2)
    raise TimeoutError("ChatGPT 텍스트 응답 대기 시간 초과")


def _wait_for_images(
    driver: webdriver.Chrome,
    previous_count: int = 0,
    needed: int = 2,
    timeout: int = 300,
) -> list[str]:
    existing_urls = _get_image_urls(driver)
    baseline_urls = set(existing_urls[:previous_count]) if previous_count else set(existing_urls)
    captured_urls: list[str] = []
    started_at = time.time()
    first_error_at: float | None = None
    while time.time() - started_at < timeout:
        current_urls = _get_image_urls(driver)
        for url in current_urls:
            if url in baseline_urls or url in captured_urls:
                continue
            captured_urls.append(url)
            _save_live_image_urls(captured_urls)
            print(f"[이미지 감지] {len(captured_urls)}/{needed}: {url}")
        if len(captured_urls) >= needed:
            print("[이미지 감지] 필요한 이미지 URL 확보. 메시지 완료 대기를 건너뛰고 다음 단계로 이동합니다.")
            return captured_urls[:needed]

        error_text = _get_chatgpt_generation_error(driver)
        if error_text and not captured_urls:
            if "Something went wrong" in error_text or "If this issue persists" in error_text or "문제가 발생" in error_text:
                raise RuntimeError(f"ChatGPT 이미지 생성 오류 감지: {error_text}")
            if first_error_at is None:
                first_error_at = time.time()
                print(f"[경고] ChatGPT 이미지 생성 지연/중단 문구 감지: {error_text}")
            elif time.time() - first_error_at >= 25 and not _is_chatgpt_busy(driver):
                raise RuntimeError(f"ChatGPT 이미지 생성이 중단된 상태로 보입니다: {error_text}")
        time.sleep(1)
    raise TimeoutError("ChatGPT 이미지 생성 대기 시간 초과")


def clean_generated_text(text: str) -> str:
    """ChatGPT citation artifacts that should never be published."""
    if not text:
        return text

    cleaned = text
    citation_patterns = [
        r"::contentReference\[[^\]]*\]\{[^}]*\}",
        r"【[^】]*†[^】]*】",
        "\ue200cite\ue202.*?\ue201",
    ]
    for pattern in citation_patterns:
        cleaned = re.sub(pattern, "", cleaned)

    cleaned = re.sub(r"<p>\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def clean_generated_html_body(html_body: str) -> str:
    cleaned = clean_generated_text(html_body)

    cleaned = re.sub(r"^```(?:html)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    for _ in range(3):
        if "&lt;" not in cleaned and "&gt;" not in cleaned and "&amp;lt;" not in cleaned:
            break
        unescaped = html.unescape(cleaned)
        if unescaped == cleaned:
            break
        cleaned = unescaped

    cleaned = re.sub(r"<p>\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()



def _disable_responsive_golf_html(html_body: str) -> str:
    """
    골프 본문을 웹 브라우저에서 읽기 좋은 폭으로 보정합니다.
    본문 폭은 티스토리 스킨의 article-view 폭을 따르게 하고,
    생성 HTML이 자체 max-width로 한 번 더 좁아지는 것만 막습니다.
    """
    if not html_body:
        return html_body

    fixed = html_body

    # 1) 생성 HTML이 스킨 본문 폭보다 좁게 고정되지 않도록 정리
    fixed = re.sub(r"max-width\s*:\s*(?:640|680|720|760|800|860|880|900|960|1000|1080|1200)px\s*;?", "max-width:100%;", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"width\s*:\s*calc\([^)]*\)\s*;?", "width:100%;", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"width\s*:\s*(?:640|680|720|760|800|860|880|900|960|1000|1080|1200)px\s*;?", "width:100%; max-width:100%;", fixed, flags=re.IGNORECASE)

    # 2) 사이드 스킨과 충돌하기 쉬운 속성 제거/무력화
    fixed = re.sub(r"position\s*:\s*(?:absolute|fixed|sticky)\s*;?", "position:static;", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"left\s*:\s*-?\d+px\s*;?", "", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"right\s*:\s*-?\d+px\s*;?", "", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"transform\s*:\s*translate[XY]?\([^)]*\)\s*;?", "", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"margin-left\s*:\s*-\d+px\s*;?", "margin-left:0;", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"margin-right\s*:\s*-\d+px\s*;?", "margin-right:0;", fixed, flags=re.IGNORECASE)

    # 3) 카드/표가 옆으로 밀려나지 않도록 고정
    fixed = re.sub(r"flex-wrap\s*:\s*nowrap\s*;?", "flex-wrap:wrap;", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"min-width\s*:\s*\d+px\s*;?", "", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"overflow\s*:\s*visible\s*;?", "overflow-x:auto;", fixed, flags=re.IGNORECASE)

    # 4) 혹시 생성된 media query 제거
    fixed = re.sub(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", "", fixed, flags=re.IGNORECASE | re.DOTALL)

    # 5) 최상위 래퍼에 스킨 안전 속성 보강
    fixed = re.sub(
        r'(<div\b[^>]*style="[^"]*)',
        r'\1clear:both; overflow-x:auto; box-sizing:border-box; ',
        fixed,
        count=1,
        flags=re.IGNORECASE,
    )

    return fixed

def send_text_prompt(driver: webdriver.Chrome, prompt_text: str, timeout: int = 240, max_retries: int = 1) -> str:
    """텍스트 프롬프트를 전송하고 응답을 반환합니다. 기본값은 중복 생성 방지를 위해 재전송하지 않습니다."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            _wait_until_chatgpt_ready(driver, timeout=timeout, stable_seconds=8)
            prev = len(_get_response_elements(driver))
            input_prompt(driver, prompt_text)
            _wait_for_prompt_settle(prompt_text)
            submit_prompt(driver)
            return clean_generated_text(_wait_for_text(driver, previous_count=prev, timeout=timeout))
        except TimeoutError as e:
            last_error = e
            if attempt < max_retries:
                print(f"\n[재시도] 텍스트 응답 타임아웃 (시도 {attempt}/{max_retries}). 현재 화면에서 대기 후 재시도...")
                try:
                    _wait_until_chatgpt_ready(driver, timeout=60, stable_seconds=6)
                except Exception:
                    random_sleep(3, 5)
            else:
                print(f"\n[오류] 텍스트 응답 타임아웃 (최대 {max_retries}회 시도 완료)")
    raise last_error


def prepare_chatgpt_for_next_golf_prompt(driver: webdriver.Chrome, label: str) -> None:
    """이미지 생성 뒤에도 현재 대화의 입력창을 우선 재사용합니다."""
    print(f"[ChatGPT] {label} 전 현재 대화 입력창을 안정화합니다.")
    try:
        _wait_until_chatgpt_ready(driver, timeout=180, stable_seconds=6)
        textarea = _find_textarea(driver)
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
            textarea.click()
        except Exception:
            pass
        return
    except Exception as exc:
        raise RuntimeError(f"ChatGPT 현재 대화 입력창을 찾지 못해 본문 프롬프트 전송을 중단합니다: {exc}") from exc


def open_chatgpt_text_thread_after_image(driver: webdriver.Chrome) -> None:
    """저장된 이미지는 로컬에서 쓰고, 본문은 같은 탭의 새 프로젝트 대화에서 생성합니다."""
    print("[ChatGPT] 이미지 저장 완료. 같은 탭에서 본문 생성용 프로젝트 대화로 이동합니다.")
    try:
        current_handle = driver.current_window_handle
        if current_handle in driver.window_handles:
            driver.switch_to.window(current_handle)
    except Exception:
        pass
    driver.get(CHATGPT_PROJECT_URL)
    random_sleep(2.0, 4.0)
    _wait_until_chatgpt_ready(driver, timeout=180, stable_seconds=6)
    _find_textarea(driver)


def send_golf_body_prompt(driver: webdriver.Chrome, prompt_text: str, timeout: int = 600) -> str:
    """골프 본문 HTML은 이미지 저장 후 준비된 텍스트 대화에서 전송합니다."""
    prepare_chatgpt_for_next_golf_prompt(driver, "골프 본문 생성")
    return send_text_prompt_after_image_with_refresh(driver, prompt_text, "골프 본문 생성", timeout=timeout)


CHATGPT_INTERRUPTION_NOTICE_SNIPPETS = (
    "스트리밍이 중지",
    "메시지 완료를 기다리는",
    "streaming was interrupted",
    "waiting for the message to complete",
)


def _chatgpt_page_text(driver: webdriver.Chrome) -> str:
    try:
        return driver.execute_script("return document.body ? document.body.innerText : '';") or ""
    except Exception:
        return ""


def _has_chatgpt_interruption_notice(driver: webdriver.Chrome) -> bool:
    text = _chatgpt_page_text(driver).lower()
    return any(snippet.lower() in text for snippet in CHATGPT_INTERRUPTION_NOTICE_SNIPPETS)


def _wait_for_interruption_notice_to_clear(
    driver: webdriver.Chrome,
    notice_timeout: int = 75,
    clear_timeout: int = 180,
) -> bool:
    started_at = time.time()
    while time.time() - started_at < notice_timeout:
        if _has_chatgpt_interruption_notice(driver):
            print("[ChatGPT] 스트리밍 중지 문구 감지. 문구가 사라질 때까지 기다립니다.")
            break
        time.sleep(1)
    else:
        print("[ChatGPT] 스트리밍 중지 문구가 감지되지 않았습니다.")
        return False

    last_seen_at = time.time()
    started_clear_at = time.time()
    while time.time() - started_clear_at < clear_timeout:
        if _has_chatgpt_interruption_notice(driver):
            last_seen_at = time.time()
        elif time.time() - last_seen_at >= 2:
            print("[ChatGPT] 스트리밍 중지 문구가 사라졌습니다.")
            return True
        time.sleep(1)

    print("[ChatGPT] 스트리밍 중지 문구가 제한 시간 안에 사라지지 않았습니다.")
    return False


def _wait_current_interruption_notice_to_clear(driver: webdriver.Chrome, clear_timeout: int = 180) -> bool:
    last_seen_at = time.time()
    started_at = time.time()
    while time.time() - started_at < clear_timeout:
        if _has_chatgpt_interruption_notice(driver):
            last_seen_at = time.time()
        elif time.time() - last_seen_at >= 2:
            print("[ChatGPT] 스트리밍 중지 문구가 사라졌습니다.")
            return True
        time.sleep(1)
    print("[ChatGPT] 스트리밍 중지 문구가 제한 시간 안에 사라지지 않았습니다.")
    return False


def _refresh_after_interruption_notice_if_needed(
    driver: webdriver.Chrome,
    previous_count: int,
    notice_timeout: int = 75,
    clear_timeout: int = 180,
    refresh_delay_seconds: int = 3,
) -> bool:
    started_at = time.time()
    response_seen_at: float | None = None
    while time.time() - started_at < notice_timeout:
        if _has_chatgpt_interruption_notice(driver):
            print("[ChatGPT] 스트리밍 중지 문구 감지. 문구가 사라질 때까지 기다립니다.")
            if _wait_current_interruption_notice_to_clear(driver, clear_timeout=clear_timeout):
                print(f"[ChatGPT] 중지 문구가 사라진 뒤 {refresh_delay_seconds}초 대기합니다.")
                time.sleep(refresh_delay_seconds)
                print("[ChatGPT] 대화창을 한 번 새로고침합니다.")
                driver.refresh()
                random_sleep(5, 8)
                return True
            return False

        response_text = _latest_non_empty_response_text(_get_response_elements(driver), previous_count=previous_count)
        if response_text:
            if response_seen_at is None:
                response_seen_at = time.time()
            if len(response_text) >= 500 or time.time() - response_seen_at >= 8:
                print("[ChatGPT] 정상 응답이 시작되어 새로고침 감시를 종료합니다.")
                return False
        time.sleep(1)

    print("[ChatGPT] 스트리밍 중지 문구가 감지되지 않았습니다.")
    return False


def wait_after_image_before_text_prompt(label: str, wait_seconds: int = 10) -> None:
    print(f"[ChatGPT] 이미지 보관 완료 후 {label} 전 {wait_seconds}초 대기...")
    time.sleep(wait_seconds)


def send_text_prompt_after_image_with_refresh(
    driver: webdriver.Chrome,
    prompt_text: str,
    label: str,
    timeout: int = 600,
) -> str:
    """이미지 직후 첫 본문 프롬프트는 중지 문구가 사라진 뒤 3초 기다리고 1회 새로고침합니다."""
    _wait_until_chatgpt_ready(driver, timeout=timeout, stable_seconds=8)
    prev = len(_get_response_elements(driver))
    input_prompt(driver, prompt_text)
    _wait_for_prompt_settle(prompt_text)
    submit_prompt(driver)
    _refresh_after_interruption_notice_if_needed(driver, previous_count=prev)
    return clean_generated_text(_wait_for_text(driver, previous_count=prev, timeout=timeout))


def send_health_body_prompt_after_image(driver: webdriver.Chrome, prompt_text: str, timeout: int = 600) -> str:
    """건강식품 쿠팡 본문은 이미지 직후 전송한 뒤 중지 문구가 사라지면 1회 새로고침합니다."""
    return send_text_prompt_after_image_with_refresh(driver, prompt_text, "건강식품 쿠팡 본문 생성", timeout=timeout)


def send_image_prompt(
    driver: webdriver.Chrome, prompt_text: str, timeout: int = 300, needed: int = 2
) -> tuple[str, ...]:
    _wait_until_chatgpt_ready(driver, timeout=timeout, stable_seconds=8)
    prev = len(_get_image_urls(driver))
    input_prompt(driver, prompt_text)
    _wait_for_prompt_settle(prompt_text)
    submit_prompt(driver)
    urls = _wait_for_images(driver, previous_count=prev, needed=needed, timeout=timeout)
    return tuple(urls[:needed])


def download_image_as_base64(driver: webdriver.Chrome, url: str, max_retries: int = 3) -> str:
    if not url:
        print("[경고] 이미지 URL이 비어 있습니다.")
        return ""

    fixed_url = (
        url.strip()
        .replace("&amp;", "&")
        .replace("\\u0026", "&")
        .replace("&amp;amp;", "&")  # 이중 인코딩 방어
    )

    if fixed_url.startswith("/backend-api/estuary/content"):
        fixed_url = "https://chatgpt.com" + fixed_url
    elif fixed_url.startswith("backend-api/estuary/content"):
        fixed_url = "https://chatgpt.com/" + fixed_url

    print(f"[ChatGPT] 이미지 base64 다운로드 시도: {fixed_url[:120]}...")

    for attempt in range(1, max_retries + 1):
        try:
            driver.set_script_timeout(60)
            b64_data = driver.execute_async_script("""
                const url = arguments[0];
                const done = arguments[arguments.length - 1];

                fetch(url, {
                    method: "GET",
                    credentials: "include",
                    cache: "no-store"
                })
                .then(res => {
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.blob();
                })
                .then(blob => {
                    const reader = new FileReader();
                    reader.onloadend = () => done(reader.result || "");
                    reader.onerror = () => done("");
                    reader.readAsDataURL(blob);
                })
                .catch(err => {
                    console.error("image fetch failed", err.message);
                    done("");
                });
            """, fixed_url)

            if b64_data and isinstance(b64_data, str) and b64_data.startswith("data:image/"):
                print(f"[ChatGPT] 이미지 base64 변환 성공 (시도 {attempt}/{max_retries}): {len(b64_data)}자")
                return b64_data

            print(f"[경고] 시도 {attempt}/{max_retries}: base64 결과 없음 또는 형식 불일치")

        except Exception as e:
            print(f"[경고] 시도 {attempt}/{max_retries}: 다운로드 오류 — {e}")

        if attempt < max_retries:
            time.sleep(2.0 * attempt)  # 지수 백오프

    print("[오류] 이미지 base64 변환 최종 실패 — 이미지 없이 계속합니다.")
    return ""


# ------------------------------------------------------------------
# Tistory 동작 (이미지 파일 처리 및 DOM 동기화 완벽 구현)
# ------------------------------------------------------------------

def _write_temp_image_from_src(src: str, slot_idx: int) -> Path | None:
    """Base64 데이터를 티스토리 업로드용 일회성 파일로 디코딩하여 저장합니다."""
    if not src.startswith("data:image/"):
        return None
    header, encoded = src.split(",", 1)
    ext = "png"
    mime_match = re.match(r"data:image/([^;]+);base64", header, re.IGNORECASE)
    if mime_match:
        ext = mime_match.group(1).lower().replace("jpeg", "jpg")
    TISTORY_ONE_TIME_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_path = TISTORY_ONE_TIME_IMAGE_DIR / f"tistory_once_golf_{timestamp}_{slot_idx}.{ext}"
    image_path.write_bytes(base64.b64decode(encoded))
    print(f"[Tistory] 업로드용 일회성 이미지 저장 완료: {image_path}")
    return image_path


def _image_extension_from_url_or_type(url: str, content_type: str = "") -> str:
    content_type = (content_type or "").lower()
    if "png" in content_type:
        return "png"
    if "webp" in content_type:
        return "webp"
    if "gif" in content_type:
        return "gif"
    if "jpeg" in content_type or "jpg" in content_type:
        return "jpg"

    path = urllib.parse.urlparse(url).path.lower()
    for ext in ("jpg", "jpeg", "png", "webp", "gif"):
        if path.endswith(f".{ext}"):
            return "jpg" if ext == "jpeg" else ext
    return "jpg"


def _write_temp_image_from_url(url: str, slot_idx: int) -> Path | None:
    url = html.unescape(str(url or "").strip())
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return None

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.bing.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type.lower():
                print(f"[경고] 외부 이미지 URL이 image Content-Type이 아닙니다: {url} ({content_type})")
                return None
            content = response.read(15 * 1024 * 1024)
    except Exception as exc:
        print(f"[경고] 외부 이미지 다운로드 실패: {url} | {exc}")
        return None

    if not content:
        print(f"[경고] 외부 이미지 다운로드 결과가 비어 있습니다: {url}")
        return None

    TISTORY_ONE_TIME_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ext = _image_extension_from_url_or_type(url, content_type)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_path = TISTORY_ONE_TIME_IMAGE_DIR / f"tistory_once_golf_body_{timestamp}_{slot_idx}.{ext}"
    image_path.write_bytes(content)
    print(f"[Tistory] 본문 외부 이미지 저장 완료: {image_path}")
    return image_path


def _copy_image_file_to_clipboard(image_path: Path) -> None:
    """Windows PowerShell을 사용하여 이미지를 OS 클립보드에 복사합니다."""
    safe_img_path = str(image_path).replace("\\", "/")
    ps_script = f'''
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile("{safe_img_path}")
    [System.Windows.Forms.Clipboard]::SetImage($img)
    '''
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, check=True)


def _select_token_in_basic_editor(driver: webdriver.Chrome, token: str) -> bool:
    """기본모드(WYSIWYG)에서 특정 텍스트 토큰을 찾아 블록(선택) 지정합니다."""
    return bool(driver.execute_script(
        """
        const token = arguments[0];
        const editorBody = document.querySelector('.editor-body, .contents_style, [contenteditable="true"]');
        if (!editorBody) return false;
        
        const walker = document.createTreeWalker(editorBody, NodeFilter.SHOW_TEXT, null, false);
        let node;
        while ((node = walker.nextNode())) {
            const idx = node.nodeValue.indexOf(token);
            if (idx >= 0) {
                const range = document.createRange();
                range.setStart(node, idx);
                range.setEnd(node, idx + token.length);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
                
                let target = node.parentElement;
                while (target && target !== document.body) {
                    const editable = target.closest('[contenteditable="true"]');
                    if (editable) {
                        editable.focus();
                        break;
                    }
                    target = target.parentElement;
                }
                return true;
            }
        }
        return false;
        """,
        token,
    ))


def _paste_image_into_basic_editor(driver: webdriver.Chrome, token: str, image_path: Path) -> None:
    """찾은 토큰 위치에 OS 클립보드의 이미지를 붙여넣어 티스토리 자체 CDN 업로드를 유도합니다."""
    if not _select_token_in_basic_editor(driver, token):
        print(f"[경고] 기본모드에서 이미지 슬롯({token})을 찾지 못했습니다.")
        return

    _copy_image_file_to_clipboard(image_path)
    random_sleep(0.5, 1.0)
    ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
    print(f"[Tistory] 이미지 위치({token})에 붙여넣기 성공. 카카오 CDN 업로드 대기중...")
    random_sleep(4.0, 6.0)  # 티스토리 서버가 이미지를 업로드하고 태그를 렌더링할 시간을 보장합니다.


TISTORY_NATIVE_IMAGE_MARKER_PREFIX = "__TISTORY_NATIVE_IMAGE_SLOT_"
TISTORY_NATIVE_IMAGE_MARKER = "__TISTORY_NATIVE_IMAGE_SLOT_1__"


def _native_image_marker(slot_idx: int) -> str:
    return f"{TISTORY_NATIVE_IMAGE_MARKER_PREFIX}{slot_idx}__"


def _marker_paragraph(marker: str = TISTORY_NATIVE_IMAGE_MARKER) -> str:
    return f'<p style="text-align:center; margin:0 0 28px;">{marker}</p>'


def _strip_broken_image_placeholder_tags(html_body: str, token: str) -> str:
    html_body = re.sub(
        rf'<figure[^>]*>.*?{re.escape(token)}.*?</figure>',
        '',
        html_body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_body = re.sub(
        rf'<img[^>]*{re.escape(token)}[^>]*>',
        '',
        html_body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html_body.replace(token, "")


def _strip_embedded_data_image_tags(html_body: str) -> str:
    html_body = re.sub(
        r'<figure[^>]*>.*?<img\b[^>]*\ssrc=(["\'])data:image/[^"\']+\1[^>]*>.*?</figure>',
        '',
        html_body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    html_body = re.sub(
        r'<img\b[^>]*\ssrc=(["\'])data:image/[^"\']+\1[^>]*>',
        '',
        html_body,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return re.sub(r'data:image/[^"\'\s<>]+', '', html_body, flags=re.IGNORECASE)


def _remove_generated_image_placeholders(html_body: str) -> str:
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")
    for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%"):
        html_body = _strip_broken_image_placeholder_tags(html_body, token)
    html_body = re.sub(
        rf'<p[^>]*>\s*{re.escape(TISTORY_NATIVE_IMAGE_MARKER)}\s*</p>',
        '',
        html_body,
        flags=re.IGNORECASE,
    ).replace(TISTORY_NATIVE_IMAGE_MARKER, "")
    return _strip_embedded_data_image_tags(html_body)


def _extract_img_attr(img_tag: str, attr_name: str) -> str:
    pattern = rf'\b{re.escape(attr_name)}\s*=\s*(["\'])(.*?)\1'
    match = re.search(pattern, img_tag, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2).strip()) if match else ""


def _is_native_upload_candidate_url(url: str) -> bool:
    url = html.unescape(str(url or "").strip())
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return False
    lowered = url.lower()
    blocked_hosts = (
        "kakaocdn.net",
        "daumcdn.net",
        "tistory.com",
        "coupang.com",
        "ads-partners.coupang.com",
        "backend-api/estuary/content",
        "oaiusercontent.com",
        "oaidalle",
    )
    return not any(host in lowered for host in blocked_hosts)


def _candidate_urls_from_img_tag(img_tag: str) -> list[str]:
    candidates = []
    for attr_name in ("data-url", "data-src", "data-original", "data-lazy-src", "alt", "src"):
        value = _extract_img_attr(img_tag, attr_name)
        if _is_native_upload_candidate_url(value) and value not in candidates:
            candidates.append(value)

    srcset = _extract_img_attr(img_tag, "srcset")
    if srcset:
        for part in srcset.split(","):
            value = part.strip().split(" ", 1)[0]
            if _is_native_upload_candidate_url(value) and value not in candidates:
                candidates.append(value)
    return candidates


def _find_external_image_blocks(html_body: str) -> list[dict]:
    blocks = []
    used_ranges: list[tuple[int, int]] = []
    for match in re.finditer(r"<img\b[^>]*>", html_body or "", flags=re.IGNORECASE | re.DOTALL):
        img_tag = match.group(0)
        candidates = _candidate_urls_from_img_tag(img_tag)
        if not candidates:
            continue

        block_start, block_end = match.start(), match.end()
        figure_start = html_body.rfind("<figure", 0, match.start())
        if figure_start >= 0:
            figure_close = html_body.find("</figure>", match.end())
            previous_figure_close = html_body.rfind("</figure>", 0, match.start())
            if figure_close >= 0 and previous_figure_close < figure_start:
                block_start = figure_start
                block_end = figure_close + len("</figure>")

        if any(not (block_end <= start or block_start >= end) for start, end in used_ranges):
            continue
        used_ranges.append((block_start, block_end))
        blocks.append(
            {
                "start": block_start,
                "end": block_end,
                "html": html_body[block_start:block_end],
                "candidates": candidates,
            }
        )
    return blocks


def _latest_chatgpt_response_outer_html(driver: webdriver.Chrome) -> str:
    for element in reversed(_get_response_elements(driver)):
        try:
            outer_html = driver.execute_script("return arguments[0].outerHTML || '';", element)
        except Exception:
            continue
        if isinstance(outer_html, str) and "<img" in outer_html.lower():
            return outer_html
    return ""


def _existing_external_image_candidate_urls(html_body: str) -> set[str]:
    urls: set[str] = set()
    for block in _find_external_image_blocks(html_body):
        urls.update(block["candidates"])
    return urls


def _append_latest_chatgpt_response_images_to_html_body(
    driver: webdriver.Chrome,
    html_body: str,
    max_images: int = TISTORY_MAX_GOLF_BODY_IMAGE_UPLOADS,
) -> str:
    response_html = _latest_chatgpt_response_outer_html(driver)
    if not response_html:
        return html_body

    existing_urls = _existing_external_image_candidate_urls(html_body)
    figures: list[str] = []
    for match in re.finditer(r"<img\b[^>]*>", response_html, flags=re.IGNORECASE | re.DOTALL):
        img_tag = match.group(0)
        candidates = _candidate_urls_from_img_tag(img_tag)
        if not candidates:
            continue

        source_url = candidates[0]
        if source_url in existing_urls:
            continue

        display_url = (
            _extract_img_attr(img_tag, "src")
            or _extract_img_attr(img_tag, "data-src")
            or source_url
        )
        if not _is_native_upload_candidate_url(display_url):
            display_url = source_url

        figures.append(
            '<figure style="text-align:center; margin:26px 0;">'
            f'<img src="{html.escape(display_url, quote=True)}" '
            f'alt="{html.escape(source_url, quote=True)}" '
            'style="width:100%; max-width:100%; height:auto; border-radius:10px; display:block; margin:0 auto;" '
            'loading="lazy" />'
            '</figure>'
        )
        existing_urls.update(candidates)
        if len(figures) >= max_images:
            break

    if not figures:
        return html_body

    print(f"[ChatGPT] 최신 본문 응답에서 관련 이미지 {len(figures)}장을 추가 감지했습니다.")
    return html_body.rstrip() + "\n\n" + "\n".join(figures)


def _write_temp_image_from_candidate_urls(candidates: list[str], slot_idx: int, used_urls: set[str]) -> tuple[Path | None, str]:
    for url in candidates:
        normalized_url = html.unescape(url).strip()
        if normalized_url in used_urls:
            continue
        image_path = _write_temp_image_from_url(normalized_url, slot_idx)
        if image_path:
            used_urls.add(normalized_url)
            return image_path, normalized_url
    return None, ""


def _replace_golf_external_images_with_upload_markers(
    html_body: str,
    start_slot_idx: int,
    max_images: int = TISTORY_MAX_GOLF_BODY_IMAGE_UPLOADS,
) -> tuple[str, list[dict]]:
    blocks = _find_external_image_blocks(html_body)
    if not blocks:
        return html_body, []

    rebuilt = []
    uploads: list[dict] = []
    used_urls: set[str] = set()
    last_pos = 0
    for block in blocks:
        rebuilt.append(html_body[last_pos:block["start"]])
        last_pos = block["end"]

        if len(uploads) >= max_images:
            print("[Tistory] 본문 외부 이미지 최대 업로드 수를 넘어 추가 이미지는 제거합니다.")
            continue

        slot_idx = start_slot_idx + len(uploads)
        image_path, source_url = _write_temp_image_from_candidate_urls(block["candidates"], slot_idx, used_urls)
        if not image_path:
            print("[경고] 본문 외부 이미지 저장 실패. hotlink 방지를 위해 해당 이미지 태그를 제거합니다.")
            continue

        marker = _native_image_marker(slot_idx)
        rebuilt.append(_marker_paragraph(marker))
        uploads.append({"path": image_path, "marker": marker, "source_url": source_url})

    rebuilt.append(html_body[last_pos:])
    if uploads:
        print(f"[Tistory] 본문 외부 이미지 {len(uploads)}장을 네이티브 업로드 대상으로 준비했습니다.")
    return "".join(rebuilt), uploads


def _insert_native_image_marker_after_first_coupang_link(
    html_body: str,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> str:
    html_body = _remove_generated_image_placeholders(html_body)
    marker_html = _marker_paragraph(marker)
    if marker in html_body:
        return html_body

    coupang_anchor_pattern = re.compile(
        r'<a\b(?=[^>]*href=["\']https?://(?:link\.coupang\.com|www\.coupang\.com|coupa\.ng)[^"\']*["\'])[^>]*>.*?</a>',
        re.IGNORECASE | re.DOTALL,
    )
    match = coupang_anchor_pattern.search(html_body)
    if not match:
        raise RuntimeError("첫 번째 쿠팡 링크를 찾지 못해 이미지 삽입 위치를 결정할 수 없습니다.")

    print("[Tistory] 첫 번째 쿠팡 링크 아래에 사진 업로드 마커를 삽입했습니다.")
    return html_body[:match.end()] + "\n" + marker_html + "\n" + html_body[match.end():]


def _insert_native_image_marker_for_body(
    html_body: str,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> str:
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")
    marker_html = _marker_paragraph(marker)

    if marker in html_body:
        html_body = _strip_embedded_data_image_tags(html_body)
        for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%"):
            html_body = _strip_broken_image_placeholder_tags(html_body, token)
        return html_body

    replacements = [
        rf'<figure[^>]*>.*?{re.escape("%%IMAGE1_PLACEHOLDER%%")}.*?</figure>',
        rf'<img[^>]*{re.escape("%%IMAGE1_PLACEHOLDER%%")}[^>]*>',
        r'<figure[^>]*>.*?<img\b[^>]*\ssrc=(["\'])data:image/[^"\']+\1[^>]*>.*?</figure>',
        r'<img\b[^>]*\ssrc=(["\'])data:image/[^"\']+\1[^>]*>',
    ]
    replaced = False
    for pattern in replacements:
        html_body, count = re.subn(
            pattern,
            marker_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if count:
            replaced = True
            break

    html_body = _strip_broken_image_placeholder_tags(html_body, "%%IMAGE2_PLACEHOLDER%%")
    html_body = _strip_broken_image_placeholder_tags(html_body, "%%IMAGE1_PLACEHOLDER%%")
    html_body = _strip_embedded_data_image_tags(html_body)
    if not replaced and marker not in html_body:
        html_body = marker_html + "\n" + html_body

    print("[Tistory] 사진 업로드 마커를 본문에 배치했습니다.")
    return html_body


def _prepare_html_for_native_tistory_image_upload(html_body: str, post_type: str, has_image: bool) -> str:
    if not has_image:
        return _remove_generated_image_placeholders(html_body)
    if post_type in {"coupang", "health"}:
        return _insert_native_image_marker_after_first_coupang_link(html_body)
    return _insert_native_image_marker_for_body(html_body)


def _get_tistory_html_body_value(driver: webdriver.Chrome) -> str:
    try:
        value = driver.execute_script(
            """
            const root = document.querySelector('#html-editor-container');
            const cmHost =
              root?.querySelector('.CodeMirror') ||
              root?.querySelector('.CodeMirror-scroll')?.closest('.CodeMirror') ||
              document.querySelector('.CodeMirror');
            if (cmHost && cmHost.CodeMirror) {
              return cmHost.CodeMirror.getValue() || '';
            }
            const textarea = root?.querySelector('textarea') || document.querySelector('#html-editor-container textarea');
            return textarea ? (textarea.value || '') : '';
            """
        )
        return value if isinstance(value, str) else ""
    except Exception:
        return ""


def _looks_like_tistory_image_fragment(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return (
        "##image" in lowered
        or "kage@" in lowered
        or "kakaocdn.net" in lowered
        or "imageblock" in lowered
        or "data-origin-width" in lowered
    )


def _find_tistory_image_file_input(driver: webdriver.Chrome, timeout: int = 8):
    end_at = time.time() + timeout
    while time.time() < end_at:
        try:
            input_el = driver.find_element(By.XPATH, '//*[@id="attach-image"]')
            return input_el
        except Exception:
            pass
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        for input_el in inputs:
            accept = (input_el.get_attribute("accept") or "").lower()
            if not accept or "image" in accept or ".jpg" in accept or ".png" in accept or ".jpeg" in accept:
                return input_el
        time.sleep(0.3)
    return None


def _open_tistory_image_file_input(driver: webdriver.Chrome):
    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, '//*[@id="attach-layer-btn"]')))
        driver.find_element(By.XPATH, '//*[@id="attach-layer-btn"]').click()
        time.sleep(random.randrange(2, 4))
        input_el = _find_tistory_image_file_input(driver, timeout=5)
        if input_el:
            return input_el
    except Exception as exc:
        print(f"[경고] 티스토리 사진 버튼 직접 클릭 실패, fallback 시도: {exc}")

    input_el = _find_tistory_image_file_input(driver, timeout=2)
    if input_el:
        return input_el

    upload_button_xpaths = [
        '//*[@id="attach-layer-btn"]',
        '//*[self::button or self::a or @role="button"][contains(@aria-label, "사진")]',
        '//*[self::button or self::a or @role="button"][contains(@aria-label, "이미지")]',
        '//*[self::button or self::a or @role="button"][contains(@title, "사진")]',
        '//*[self::button or self::a or @role="button"][contains(@title, "이미지")]',
        '//*[self::button or self::a or @role="button"][contains(normalize-space(), "사진")]',
        '//*[self::button or self::a or @role="button"][contains(normalize-space(), "이미지")]',
        '//*[contains(@class, "toolbar")]//*[contains(@aria-label, "사진") or contains(@title, "사진")]',
        '//*[contains(@class, "toolbar")]//*[contains(@aria-label, "이미지") or contains(@title, "이미지")]',
    ]
    for xpath in upload_button_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if not el.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                random_sleep(0.2, 0.4)
                driver.execute_script("arguments[0].click();", el)
                input_el = _find_tistory_image_file_input(driver, timeout=5)
                if input_el:
                    return input_el
        except Exception:
            continue
    return _find_tistory_image_file_input(driver, timeout=5)


def _select_token_in_html_editor(driver: webdriver.Chrome, marker: str) -> bool:
    try:
        return bool(driver.execute_script(
            """
            const marker = arguments[0];
            const root = document.querySelector('#html-editor-container');
            const cmHost =
              root?.querySelector('.CodeMirror') ||
              root?.querySelector('.CodeMirror-scroll')?.closest('.CodeMirror') ||
              document.querySelector('.CodeMirror');

            if (cmHost && cmHost.CodeMirror) {
              const editor = cmHost.CodeMirror;
              const value = editor.getValue() || '';
              const idx = value.indexOf(marker);
              if (idx < 0) return false;
              editor.focus();
              editor.setSelection(editor.posFromIndex(idx), editor.posFromIndex(idx + marker.length));
              editor.scrollIntoView(editor.posFromIndex(idx), 80);
              return true;
            }

            const textarea = root?.querySelector('textarea') || document.querySelector('#html-editor-container textarea');
            if (!textarea) return false;
            const value = textarea.value || '';
            const idx = value.indexOf(marker);
            if (idx < 0) return false;
            textarea.focus();
            textarea.setSelectionRange(idx, idx + marker.length);
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            return true;
            """,
            marker,
        ))
    except Exception:
        return False


def _upload_one_time_image_at_marker(
    driver: webdriver.Chrome,
    image_path: Path,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> None:
    print("[Tistory] HTML 모드에서 사진 업로드 위치 선택 중...")
    _verify_tistory_editor_mode(driver, "html", timeout=10)

    if not _select_token_in_html_editor(driver, marker):
        raise RuntimeError(f"HTML 본문에서 사진 업로드 마커를 찾지 못했습니다: {marker}")
    random_sleep(0.3, 0.6)

    before_html = _get_tistory_html_body_value(driver)
    input_el = _open_tistory_image_file_input(driver)
    if not input_el:
        raise RuntimeError("티스토리 사진 업로드 input(#attach-image)을 찾지 못했습니다.")

    driver.execute_script(
        """
        arguments[0].removeAttribute('disabled');
        arguments[0].style.display = 'block';
        arguments[0].style.visibility = 'visible';
        arguments[0].style.opacity = 1;
        arguments[0].style.width = '1px';
        arguments[0].style.height = '1px';
        """,
        input_el,
    )
    input_el.send_keys(str(image_path.resolve()))
    print(f"[Tistory] 사진 파일 업로드 전송 완료: {image_path}")

    started_at = time.time()
    while time.time() - started_at < 75:
        current_html = _get_tistory_html_body_value(driver)
        if current_html != before_html and _looks_like_tistory_image_fragment(current_html):
            print("[Tistory] HTML 모드 사진 업로드 반영 확인 완료")
            return
        time.sleep(1)

    raise TimeoutError("HTML 모드 사진 업로드 반영을 확인하지 못했습니다.")


def _remove_native_image_marker_after_upload(
    driver: webdriver.Chrome,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> None:
    print("[Tistory] HTML 모드 사진 마커 잔여 여부 확인 중...")
    _verify_tistory_editor_mode(driver, "html", timeout=10)
    current_html = _get_tistory_html_body_value(driver)
    if marker not in current_html:
        print("[Tistory] 사진 마커 잔여 없음")
        return

    current_html = re.sub(
        rf'<p[^>]*>\s*{re.escape(marker)}\s*</p>',
        '',
        current_html,
        flags=re.IGNORECASE,
    ).replace(marker, "")
    _set_tistory_html_body(driver, current_html)
    print("[Tistory] 사진 마커 잔여 텍스트 제거 완료")


def _validate_tistory_html_before_injection(html_body: str) -> None:
    if "&lt;img" in html_body.lower():
        raise RuntimeError("티스토리 주입 전 HTML에 이스케이프된 img 태그(&lt;img)가 남아 있습니다.")
    if "data:image/" in html_body.lower():
        raise RuntimeError(
            "티스토리 HTML 모드에서는 data:image base64 직접 주입이 깨질 수 있어 중단합니다. "
            "티스토리 업로드 이미지 조각 방식으로 치환해야 합니다."
        )


def _type_human(element, text: str) -> None:
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.01, 0.04))


def _normalize_tags(tags) -> list[str]:
    raw = tags.replace(",", " ").split() if isinstance(tags, str) else list(tags)
    return [t.strip().lstrip("#") for t in raw if t.strip().lstrip("#")]


def _wait_and_click_xpath_with_js_fallback(driver: webdriver.Chrome, xpath: str, timeout: int = 15) -> None:
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        driver.find_element(By.XPATH, xpath).click()
        return
    except Exception:
        pass

    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    random_sleep(0.2, 0.5)
    driver.execute_script("arguments[0].click();", element)


def _click_tistory_draft_save(driver: webdriver.Chrome) -> None:
    """티스토리 에디터 상단의 임시저장 버튼을 클릭합니다."""
    draft_xpaths = [
        '//a[@role="button" and contains(concat(" ", normalize-space(@class), " "), " action ") and normalize-space()="임시저장"]',
        '//a[@role="button" and normalize-space()="임시저장"]',
        '//*[self::button or self::a][contains(normalize-space(), "임시저장") and not(contains(@aria-label, "개수"))]',
    ]

    last_error = None
    for xpath in draft_xpaths:
        try:
            _wait_and_click_xpath_with_js_fallback(driver, xpath, timeout=8)
            random_sleep(1.5, 2.5)
            print("[Tistory] 임시저장 버튼 클릭 완료")
            return
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"티스토리 임시저장 버튼을 찾지 못했습니다: {last_error}")


def _select_tistory_public_visibility(driver: webdriver.Chrome) -> None:
    """발행 레이어에서 공개 상태를 명시적으로 선택합니다."""
    public_xpaths = [
        '//*[@id="open20"]',
        '//input[@type="radio" and (@value="20" or @value="public" or @value="open")]',
        '//label[@for="open20"]',
        '//label[contains(normalize-space(), "공개")]',
        '//*[self::button or self::a or self::span][normalize-space()="공개"]',
    ]

    for xpath in public_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if not element.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                random_sleep(0.2, 0.4)
                driver.execute_script("arguments[0].click();", element)
                random_sleep(0.4, 0.8)
                print("[Tistory] 공개 상태 선택 완료")
                return
        except Exception:
            continue

    print("[경고] 공개 상태 선택 버튼을 찾지 못했습니다. 현재 발행 레이어 기본값으로 진행합니다.")


def _select_tistory_private_visibility(driver: webdriver.Chrome) -> None:
    """발행 레이어에서 비공개 상태를 명시적으로 선택합니다."""
    private_xpaths = [
        '//*[@id="open0"]',
        '//input[@type="radio" and (@value="0" or @value="private" or @value="closed")]',
        '//label[@for="open0"]',
        '//label[contains(normalize-space(), "비공개")]',
        '//*[self::button or self::a or self::span][normalize-space()="비공개"]',
    ]

    for xpath in private_xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                if not element.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                random_sleep(0.2, 0.4)
                driver.execute_script("arguments[0].click();", element)
                random_sleep(0.4, 0.8)
                print("[Tistory] 비공개 상태 선택 완료")
                return
        except Exception:
            continue

    raise RuntimeError("비공개 상태 선택 버튼을 찾지 못했습니다. 공개 발행 위험이 있어 중단합니다.")


def _upload_representative_image_in_publish_layer(driver: webdriver.Chrome, image_path: Path) -> None:
    """발행 레이어의 '대표이미지 추가' 파일 input에 이미지를 지정합니다."""
    print("[Tistory] 발행창 대표이미지 추가 input 대기 중...")
    input_xpaths = [
        '//div[contains(concat(" ", normalize-space(@class), " "), " inner_box ")][.//span[contains(concat(" ", normalize-space(@class), " "), " txt_thumb ") and contains(normalize-space(), "대표이미지 추가")]]//input[@type="file" and contains(concat(" ", normalize-space(@class), " "), " inp_g ") and contains(@accept, "image")]',
        '//input[@type="file" and contains(concat(" ", normalize-space(@class), " "), " inp_g ") and contains(@accept, "image")]',
        '//input[@type="file" and contains(@accept, "image") and contains(@class, "inp_g")]',
        '//input[@type="file" and contains(@accept, "image")]',
    ]

    def find_input(timeout: float = 5.0):
        last = None
        end_at = time.time() + timeout
        while time.time() < end_at:
            for xpath in input_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        return element, last
                except Exception as exc:
                    last = exc
            time.sleep(0.3)
        return None, last

    input_el, last_error = find_input(timeout=5.0)

    add_button_xpaths = [
        '//div[contains(concat(" ", normalize-space(@class), " "), " inner_box ")][.//input[@type="file" and contains(concat(" ", normalize-space(@class), " "), " inp_g ")]][.//span[contains(concat(" ", normalize-space(@class), " "), " txt_thumb ") and contains(normalize-space(), "대표이미지 추가")]]',
        '//*[self::button or self::a or self::label or self::div or self::span][contains(normalize-space(), "대표이미지") and contains(normalize-space(), "추가")]',
        '//*[self::button or self::a or self::label or self::div or self::span][contains(normalize-space(), "대표 이미지") and contains(normalize-space(), "추가")]',
        '//*[self::button or self::a or self::label][contains(normalize-space(), "이미지") and contains(normalize-space(), "추가")]',
    ]
    clicked_add_button = False
    for xpath in add_button_xpaths:
        try:
            candidates = driver.find_elements(By.XPATH, xpath)
            for candidate in candidates:
                if not candidate.is_displayed():
                    continue
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", candidate)
                random_sleep(0.2, 0.4)
                driver.execute_script("arguments[0].click();", candidate)
                random_sleep(0.5, 1.0)
                clicked_add_button = True
                print("[Tistory] 발행창 대표이미지 추가 영역 클릭 완료")
                break
            if clicked_add_button:
                break
        except Exception as exc:
            last_error = exc

    if not input_el:
        input_el, last_error = find_input(timeout=10.0)

    if not input_el:
        raise RuntimeError(f"발행창 대표이미지 추가 input(.inp_g)을 찾지 못했습니다: {last_error}")

    driver.execute_script(
        """
        arguments[0].removeAttribute('disabled');
        arguments[0].style.display = 'block';
        arguments[0].style.visibility = 'visible';
        arguments[0].style.opacity = 1;
        arguments[0].style.width = '1px';
        arguments[0].style.height = '1px';
        """,
        input_el,
    )
    input_el.send_keys(str(image_path.resolve()))
    random_sleep(1.0, 2.0)
    print(f"[Tistory] 발행창 대표이미지 파일 지정 완료: {image_path}")


def _click_first_editor_image_for_representative(driver: webdriver.Chrome) -> bool:
    try:
        return bool(driver.execute_script(
            """
            const roots = Array.from(document.querySelectorAll(
              '.contents_style, .editor-body, [contenteditable="true"]'
            )).filter(el => {
              const rect = el.getBoundingClientRect();
              const text = el.id || '';
              return rect.width > 0 && rect.height > 0 && text !== 'prompt-textarea';
            });
            const root = roots[0] || document;
            const images = Array.from(root.querySelectorAll('img')).filter(img => {
              const rect = img.getBoundingClientRect();
              const src = img.getAttribute('src') || '';
              return rect.width > 10 && rect.height > 10 && !src.startsWith('data:image/');
            });
            const image = images[0];
            if (!image) return false;

            image.scrollIntoView({block: 'center', inline: 'center'});
            const rect = image.getBoundingClientRect();
            const x = rect.left + Math.min(rect.width / 2, 40);
            const y = rect.top + Math.min(rect.height / 2, 40);
            for (const type of ['pointerdown', 'mousedown', 'mouseup', 'click']) {
              image.dispatchEvent(new MouseEvent(type, {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: x,
                clientY: y
              }));
            }
            return true;
            """
        ))
    except Exception:
        return False


def _set_tistory_representative_image(driver: webdriver.Chrome) -> None:
    print("[Tistory] 대표 이미지 설정을 위해 기본모드 전환 중...")
    _switch_tistory_editor_mode_strict(driver, "basic")
    random_sleep(1.0, 1.8)

    clicked_image = False
    for attempt in range(1, 4):
        if _click_first_editor_image_for_representative(driver):
            clicked_image = True
            print(f"[Tistory] 대표 이미지 후보 사진 클릭 완료 (시도 {attempt}/3)")
            break
        random_sleep(0.8, 1.2)

    if not clicked_image:
        raise RuntimeError("기본모드에서 대표 이미지로 설정할 사진을 찾지 못했습니다.")

    represent_button_xpaths = [
        '//div[contains(concat(" ", normalize-space(@class), " "), " mce-represent-image-btn ") and not(contains(@style, "display: none"))]',
        '//*[contains(concat(" ", normalize-space(@class), " "), " mce-represent-image-btn ")]',
    ]

    last_error = None
    for xpath in represent_button_xpaths:
        try:
            end_at = time.time() + 10
            while time.time() < end_at:
                buttons = driver.find_elements(By.XPATH, xpath)
                for button in buttons:
                    try:
                        if not button.is_displayed():
                            continue
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
                        random_sleep(0.2, 0.4)
                        driver.execute_script("arguments[0].click();", button)
                        random_sleep(0.8, 1.3)
                        print("[Tistory] 대표 이미지 설정 버튼 클릭 완료")
                        return
                    except Exception as exc:
                        last_error = exc
                time.sleep(0.3)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"대표 이미지 설정 버튼(.mce-represent-image-btn)을 클릭하지 못했습니다: {last_error}")


def _compact_category_source(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).lower()


def _topic_field_text(topic: dict | None, *keys: str) -> str:
    if not isinstance(topic, dict):
        return ""
    parts = []
    for key in keys:
        value = topic.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts)


def _resolve_tistory_golf_category(title: str, html_body: str = "", topic: dict | None = None) -> str:
    """Map generated golf topic/title to the actual Tistory category tree."""
    topic_text = _topic_field_text(
        topic,
        "club",
        "topic",
        "category",
        "main_keyword",
        "search_intent",
        "body_angle",
        "title_angle",
        "sub_keywords",
    )
    body_text = _strip_html_to_text(html_body)[:3000] if html_body else ""
    core_source = f"{title} {topic_text}"
    source = f"{core_source} {body_text}"
    compact_core = _compact_category_source(core_source)
    compact = _compact_category_source(source)
    internal_category = str(topic.get("category", "")).strip() if isinstance(topic, dict) else ""

    club_markers = [
        ("웰링턴", "wellington"),
        ("트리니티", "trinity"),
        ("잭니클라우스", "jack"),
        ("잭 니클라우스", "jack"),
        ("jacknicklaus", "jack"),
    ]
    matched_clubs = {
        marker_id
        for marker, marker_id in club_markers
        if _compact_category_source(marker) in compact_core
    }
    comparison_keywords = ("비교", "vs", "v.s", "순위", "랭킹", "선택기준", "어디가", "국내vs해외")
    if internal_category == "비교분석" or len(matched_clubs) >= 2 or any(keyword in compact_core for keyword in comparison_keywords):
        return TISTORY_GOLF_CATEGORY_NAMES["comparison"]

    if "wellington" in matched_clubs:
        return TISTORY_GOLF_CATEGORY_NAMES["wellington"]
    if "trinity" in matched_clubs:
        return TISTORY_GOLF_CATEGORY_NAMES["trinity"]
    if "jack" in matched_clubs:
        return TISTORY_GOLF_CATEGORY_NAMES["jack_nicklaus"]

    japan_keywords = ("일본", "규슈", "이바라키", "오키나와", "홋카이도", "도쿄", "오사카", "japan", "kyushu", "ibaraki")
    usa_keywords = ("미국", "하와이", "캘리포니아", "플로리다", "라스베가스", "페블비치", "오거스타", "파인허스트", "pebblebeach", "augusta", "pinehurst", "bandondunes", "sawgrass")
    europe_keywords = ("유럽", "스코틀랜드", "영국", "아일랜드", "스페인", "포르투갈", "프랑스", "이탈리아", "세인트앤드루스", "standrews", "oldcourse")
    overseas_keywords = (
        "해외",
        "베트남",
        "다낭",
        "태국",
        "방콕",
        "파타야",
        "필리핀",
        "마닐라",
        "클락",
        "세부",
        "동남아",
        "말레이시아",
        "코타키나발루",
        "괌",
        "사이판",
        "여행자보험",
        "골프백",
        "수하물",
    )

    if any(_compact_category_source(keyword) in compact for keyword in japan_keywords):
        return TISTORY_GOLF_CATEGORY_NAMES["japan"]
    if any(_compact_category_source(keyword) in compact for keyword in usa_keywords):
        return TISTORY_GOLF_CATEGORY_NAMES["usa"]
    if any(_compact_category_source(keyword) in compact for keyword in europe_keywords):
        return TISTORY_GOLF_CATEGORY_NAMES["europe"]
    if internal_category in {"해외여행", "보험·수하물", "여행준비"} or any(
        _compact_category_source(keyword) in compact for keyword in overseas_keywords
    ):
        return TISTORY_GOLF_CATEGORY_NAMES["overseas"]

    return TISTORY_GOLF_CATEGORY_DEFAULT


def _select_tistory_category(driver: webdriver.Chrome, category_name: str, fallback_names: list[str] | None = None) -> None:
    category_candidates = [category_name]
    for fallback_name in fallback_names or []:
        if fallback_name and fallback_name not in category_candidates:
            category_candidates.append(fallback_name)

    last_error = None
    for idx, candidate in enumerate(category_candidates):
        print(f"[Tistory] '{candidate}' 카테고리 선택 시도...")
        try:
            category_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "category-btn"))
            )

            if candidate in category_btn.text:
                print(f"[Tistory] '{candidate}' 카테고리가 이미 선택되어 있습니다. 스킵합니다.")
                return

            print("[Tistory] 카테고리 메뉴 여는 중...")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", category_btn)
            time.sleep(0.2)
            driver.execute_script("arguments[0].click();", category_btn)
            random_sleep(0.5, 1.0)

            print(f"[Tistory] '{candidate}' 항목 클릭 중...")
            item_xpath = f'//*[starts-with(@id, "category-item-") and contains(., "{candidate}")]'
            item_el = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, item_xpath))
            )
            driver.execute_script("arguments[0].click();", item_el)
            print(f"[Tistory] 카테고리 클릭 완료: {candidate}")
            random_sleep(0.5, 1.0)
            return

        except Exception as e:
            last_error = e
            if idx + 1 < len(category_candidates):
                print(f"[경고] '{candidate}' 카테고리 선택 실패. fallback으로 재시도합니다: {e}")
            else:
                print(f"[경고] 카테고리 선택 실패 (현재 선택값으로 진행): {e}")

    if last_error:
        print(f"[경고] 모든 카테고리 선택 후보가 실패했습니다: {last_error}")


def _display_length_for_log(html_body: str) -> int:
    collapsed = re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[embedded-image]", html_body)
    return len(collapsed)


def _clear_input_like_human(element) -> None:
    element.send_keys(Keys.CONTROL, "a")
    time.sleep(random.uniform(0.08, 0.18))
    element.send_keys(Keys.DELETE)
    time.sleep(random.uniform(0.08, 0.18))


def _find_first_present_by_xpaths(
    driver: webdriver.Chrome,
    xpaths: list[str],
    timeout: int = 15,
):
    last_error = None
    end_at = time.time() + timeout
    while time.time() < end_at:
        for xpath in xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element:
                        return element
            except Exception as exc:
                last_error = exc
        time.sleep(0.5)
    raise TimeoutException(f"요소를 찾지 못했습니다. candidates={xpaths} last_error={last_error}")


def _focus_tistory_html_body(driver: webdriver.Chrome) -> None:
    last_error = None
    for xpath in TISTORY_BODY_FOCUS_XPATHS:
        try:
            element = _find_first_present_by_xpaths(driver, [xpath], timeout=4)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            random_sleep(0.2, 0.5)
            try:
                element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", element)
            random_sleep(0.2, 0.6)
            return
        except Exception as exc:
            last_error = exc
    raise TimeoutException(f"HTML 본문 영역을 찾지 못했습니다. last_error={last_error}")


def _find_tistory_html_textarea(driver: webdriver.Chrome):
    textarea = _find_first_present_by_xpaths(driver, TISTORY_BODY_TEXTAREA_XPATHS, timeout=15)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
    return textarea


def _verify_tistory_editor_mode(driver: webdriver.Chrome, mode: str, timeout: int = 10) -> None:
    if mode == "html":
        _find_first_present_by_xpaths(driver, TISTORY_BODY_TEXTAREA_XPATHS, timeout=timeout)
        return
    if mode == "basic":
        basic_xpaths = [
            '//*[contains(@class,"contents_style")]',
            '//*[contains(@class,"editor-body")]',
            '//*[@contenteditable="true" and not(@id="prompt-textarea")]',
        ]
        _find_first_present_by_xpaths(driver, basic_xpaths, timeout=timeout)
        return
    raise ValueError(f"unsupported editor mode verification: {mode}")


def _set_tistory_html_body_via_codemirror(driver: webdriver.Chrome, html_body: str) -> bool:
    try:
        applied = driver.execute_script(
            """
            const value = arguments[0];
            const root = document.querySelector('#html-editor-container');
            if (!root) return false;

            const cmHost =
              root.querySelector('.CodeMirror') ||
              root.querySelector('.CodeMirror-scroll')?.closest('.CodeMirror') ||
              document.querySelector('.CodeMirror');
            if (!cmHost || !cmHost.CodeMirror) return false;

            const editor = cmHost.CodeMirror;
            editor.focus();
            editor.setValue(value);
            editor.save && editor.save();
            editor.refresh && editor.refresh();

            const hiddenTextarea = root.querySelector('textarea');
            if (hiddenTextarea) {
              hiddenTextarea.value = value;
              hiddenTextarea.dispatchEvent(new Event('input', { bubbles: true }));
              hiddenTextarea.dispatchEvent(new Event('change', { bubbles: true }));
            }
            return true;
            """,
            html_body,
        )
        return applied
    except Exception:
        return False


def _set_tistory_html_body(driver: webdriver.Chrome, html_body: str) -> None:
    # 1. API 주입 시도
    if not _set_tistory_html_body_via_codemirror(driver, html_body):
        textarea = _find_tistory_html_textarea(driver)
        time.sleep(random.uniform(0.2, 0.4))
        driver.execute_script(
            """
            arguments[0].focus();
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
            textarea,
            html_body,
        )

    # 2. [중요] 티스토리 시스템이 내용 변경을 '사용자 입력'으로 강제 인식하도록 만드는 0.01%의 트릭
    # HTML 에디터를 클릭한 뒤, 스페이스바를 누르고 지워버립니다. 
    # 이 네이티브 이벤트가 발생해야 티스토리가 "아, 뭔가 입력됐구나" 하고 상태를 동기화(저장)합니다.
    print("[Tistory] HTML 가상 DOM 동기화 이벤트 강제 발생 중...")
    try:
        editor_area = driver.find_element(By.CSS_SELECTOR, '.CodeMirror-scroll')
        editor_area.click()
        time.sleep(0.3)
        ActionChains(driver).send_keys(Keys.SPACE).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
    except Exception as e:
        print(f"[경고] DOM 동기화 키보드 이벤트 우회 실패: {e}")


def _verify_tistory_html_body_injection(driver: webdriver.Chrome, expected_html: str) -> None:
    current_html = _get_tistory_html_body_value(driver)
    if "[Pasted Content" in current_html:
        raise RuntimeError("티스토리 본문에 실제 HTML 대신 [Pasted Content ...] 텍스트가 들어가 중단합니다.")

    expected_len = _display_length_for_log(expected_html)
    current_len = _display_length_for_log(current_html)
    if expected_len >= 1000 and current_len < int(expected_len * 0.75):
        raise RuntimeError(
            f"티스토리 본문 주입 길이가 비정상적으로 짧습니다. expected={expected_len}, actual={current_len}"
        )

    if "<table" in expected_html.lower() and "<table" not in current_html.lower():
        raise RuntimeError("ChatGPT 본문에 있던 표가 티스토리 HTML 본문 주입 후 사라져 중단합니다.")

    print(f"[Tistory] 본문 HTML 주입 검증 완료 ({current_len}자)")


def _scroll_tistory_to_page_bottom(driver: webdriver.Chrome) -> None:
    for _ in range(8):
        driver.execute_script(
            """
            const targets = [
              document.scrollingElement,
              document.documentElement,
              document.body,
              document.querySelector('#mArticle'),
              document.querySelector('.editor-wrap'),
              document.querySelector('#html-editor-container'),
              document.querySelector('.CodeMirror'),
              document.querySelector('.CodeMirror-scroll'),
              document.querySelector('.contents_style'),
              document.querySelector('.editor-body')
            ].filter(Boolean);

            window.scrollTo(0, document.body.scrollHeight);
            for (const el of targets) {
              if (typeof el.scrollHeight === 'number') {
                el.scrollTop = el.scrollHeight;
              }
            }
            """
        )
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            random_sleep(0.1, 0.2)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys(Keys.END).key_up(Keys.CONTROL).perform()
            random_sleep(0.1, 0.2)
            body.send_keys(Keys.END)
            random_sleep(0.1, 0.2)
            body.send_keys(Keys.PAGE_DOWN)
        except Exception:
            pass
        random_sleep(0.25, 0.45)

    print("[Tistory] 본문 입력 후 페이지 맨 아래로 스크롤 완료")


def _scroll_to_tistory_tags(driver: webdriver.Chrome) -> None:
    tag_xpath_combined = f'{TISTORY_TAG_XPATH} | //input[contains(@placeholder, "태그")]'
    _scroll_tistory_to_page_bottom(driver)
    for _ in range(12):
        driver.execute_script(
            """
            const scrollTargets = [
              window,
              document.scrollingElement,
              document.documentElement,
              document.body,
              document.querySelector('#mArticle'),
              document.querySelector('.editor-wrap'),
              document.querySelector('#html-editor-container'),
              document.querySelector('.CodeMirror'),
              document.querySelector('.CodeMirror-scroll')
            ].filter(Boolean);

            for (const target of scrollTargets) {
              if (target === window) {
                window.scrollTo(0, document.body.scrollHeight);
                continue;
              }
              if (typeof target.scrollHeight === 'number') {
                target.scrollTop = target.scrollHeight;
              }
            }
            """
        )
        try:
            active = driver.switch_to.active_element
            active.send_keys(Keys.END)
            random_sleep(0.1, 0.2)
            active.send_keys(Keys.PAGE_DOWN)
            random_sleep(0.1, 0.2)
            active.send_keys(Keys.END)
        except Exception:
            pass
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        random_sleep(0.3, 0.6)
        tag_elements = driver.find_elements(By.XPATH, tag_xpath_combined)
        if tag_elements:
            tag_el = tag_elements[0]
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tag_el)
            random_sleep(0.4, 0.8)
            print("[Tistory] 페이지 맨 아래까지 스크롤 후 해시태그 영역 이동 완료")
            return

    print("[경고] 페이지 맨 아래 스크롤 확인 실패. 태그 입력 단계에서 다시 시도합니다.")


def _switch_tistory_editor_mode(driver: webdriver.Chrome, mode: str) -> None:
    print(f"[Tistory] 에디터 모드 전환 시도: {mode}")
    try:
        # 1. 제시해주신 정확한 ID로 모드 드롭다운 버튼 열기
        btn_open = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "editor-mode-layer-btn-open"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_open)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", btn_open)
        random_sleep(0.5, 1.0)

        # 2. 제시해주신 정확한 ID로 대상 모드 클릭
        if mode == "html":
            target_id = "editor-mode-html"
        elif mode == "basic":
            target_id = "editor-mode-kakao-tistory"
        else:
            raise ValueError(f"지원하지 않는 에디터 모드입니다: {mode}")

        mode_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, target_id))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", mode_btn)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", mode_btn)
        print(f"[Tistory] {mode.upper()} 모드 클릭 완료")

        random_sleep(1.0, 2.0)
        
        # 3. 혹시나 발생할 수 있는 경고창(Alert) 방어
        try:
            WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            alert.accept()
            random_sleep(0.5, 1.0)
        except TimeoutException:
            pass

    except Exception as e:
        print(f"[경고] 에디터 모드 전환 실패: {e}")

def _switch_tistory_editor_mode_strict(driver: webdriver.Chrome, mode: str) -> None:
    print(f"[Tistory] switching editor mode: {mode}")

    btn_open = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "editor-mode-layer-btn-open"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn_open)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", btn_open)
    random_sleep(0.5, 1.0)

    if mode == "html":
        target_xpaths = [
            TISTORY_EDITOR_HTML_XPATH,
            '//*[@id="editor-mode-html"]',
            '//button[@id="editor-mode-html-text"]',
            '//button[@id="editor-mode-html"]',
            '//span[normalize-space()="HTML"]',
        ]
    elif mode == "basic":
        target_xpaths = [
            TISTORY_EDITOR_BASIC_MENU_XPATH,
            '//*[@id="editor-mode-kakao-tistory"]',
            '//span[contains(normalize-space(), "기본")]',
        ]
    else:
        raise ValueError(f"unsupported editor mode: {mode}")

    mode_btn = _find_first_present_by_xpaths(driver, target_xpaths, timeout=10)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", mode_btn)
    time.sleep(0.2)
    driver.execute_script("arguments[0].click();", mode_btn)
    random_sleep(1.0, 2.0)

    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
        random_sleep(0.5, 1.0)
    except TimeoutException:
        pass

    _verify_tistory_editor_mode(driver, mode, timeout=12)
    print(f"[Tistory] {mode.upper()} mode verified")


def write_tistory_html_post(
    driver: webdriver.Chrome,
    title: str,
    html_body: str,
    tags,
    post_type: str = "coupang",
    publish: bool = False,
    visibility: str = "public",
    image1_data_url: str = "",
    image2_data_url: str = "",
    golf_topic: dict | None = None,
) -> None:
    """Tistory HTML editor flow with native Image Paste logic"""
    visibility = (visibility or "public").strip().lower()
    if visibility not in {"public", "private"}:
        raise ValueError(f"지원하지 않는 발행 공개 범위입니다: {visibility}")

    if post_type in {"coupang", "health"}:
        category_name = TISTORY_COUPANG_CATEGORY_NAME
        category_fallbacks = []
    elif post_type == "golf":
        category_name = _resolve_tistory_golf_category(title, html_body, golf_topic)
        category_fallbacks = TISTORY_GOLF_CATEGORY_FALLBACKS.get(category_name, [])
    else:
        category_name = TISTORY_DAILY_CATEGORY_NAME
        category_fallbacks = []

    print(f"[Tistory] 카테고리 선택 중... (type={post_type}, name={category_name})")
    _select_tistory_category(driver, category_name, category_fallbacks)
    random_sleep(0.6, 1.2)

    print("[Tistory] HTML 모드 전환 중...")
    _switch_tistory_editor_mode_strict(driver, "html")

    temp_image_paths: list[Path] = []
    upload_items: list[dict] = []
    main_image_path = None
    if image1_data_url:
        main_image_path = _write_temp_image_from_src(image1_data_url, 1)
        if not main_image_path:
            raise RuntimeError("이미지 data URL을 일회성 업로드 파일로 변환하지 못했습니다.")
        temp_image_paths.append(main_image_path)
        upload_items.append({"path": main_image_path, "marker": TISTORY_NATIVE_IMAGE_MARKER, "source_url": "generated"})
    elif image2_data_url:
        print("[경고] image1_data_url이 없어 image2_data_url을 사진 업로드에 사용합니다.")
        main_image_path = _write_temp_image_from_src(image2_data_url, 1)
        if not main_image_path:
            raise RuntimeError("이미지 data URL을 일회성 업로드 파일로 변환하지 못했습니다.")
        temp_image_paths.append(main_image_path)
        upload_items.append({"path": main_image_path, "marker": TISTORY_NATIVE_IMAGE_MARKER, "source_url": "generated"})

    try:

        if "clean_generated_html_body" in globals():
            html_body = clean_generated_html_body(html_body)
        if post_type == "golf":
            html_body = _disable_responsive_golf_html(html_body)
            _log_golf_image_state("Tistory 처리 전", html_body, image1_data_url)
        html_body = _prepare_html_for_native_tistory_image_upload(
            html_body,
            post_type=post_type,
            has_image=bool(main_image_path),
        )
        if post_type == "golf":
            _log_golf_image_state("Tistory 최종", html_body, image1_data_url)
            validate_golf_generated_content(html_body, title)
        if not upload_items:
            print("[경고] 업로드할 사진이 없어 본문만 입력합니다.")
        else:
            print(f"[Tistory] HTML 모드 네이티브 사진 업로드 준비 완료: {len(upload_items)}장")

        _validate_tistory_html_before_injection(html_body)

        print("[Tistory] 최종 HTML 모드 확인 중...")
        _switch_tistory_editor_mode_strict(driver, "html")

        print(f"[Tistory] 제목 입력 중... ({len(title)}자)")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, TISTORY_TITLE_XPATH)))
        driver.find_element(By.XPATH, TISTORY_TITLE_XPATH).click()
        random_sleep(0.3, 0.8)
        title_el = driver.find_element(By.XPATH, TISTORY_TITLE_XPATH)
        _type_human(title_el, title)
        random_sleep(0.8, 1.5)

        print(f"[Tistory] 본문 텍스트 HTML 주입 시작... ({_display_length_for_log(html_body)}자)")
        _focus_tistory_html_body(driver)
        random_sleep(0.3, 0.8)
        _set_tistory_html_body(driver, html_body)
        _verify_tistory_html_body_injection(driver, html_body)
        random_sleep(0.8, 1.5)

        for idx, item in enumerate(upload_items, start=1):
            print(f"[Tistory] HTML 모드 사진 업로드 진행 중... ({idx}/{len(upload_items)})")
            _upload_one_time_image_at_marker(driver, item["path"], item["marker"])
            _remove_native_image_marker_after_upload(driver, item["marker"])

        _scroll_tistory_to_page_bottom(driver)
        _scroll_to_tistory_tags(driver)

        # 태그 입력은 자동화에서 자주 멈추는 구간입니다.
        # 실패해도 발행 단계로 넘어가도록 태그별로 짧게 처리합니다.
        tag_list = _normalize_tags(tags)[:8]
        print(f"[Tistory] 해시태그 입력 시도... ({len(tag_list)}개)")

        tag_xpath_candidates = [
            TISTORY_TAG_XPATH,
            '//input[contains(@placeholder, "태그")]',
            '//input[contains(@placeholder, "태그를 입력")]',
            '//input[contains(@class, "tag")]',
            '//*[@id="tagText"]',
        ]

        tag_el = None
        for xpath in tag_xpath_candidates:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        tag_el = el
                        break
                if tag_el:
                    break
            except Exception:
                continue

        if not tag_el:
            print("[경고] 해시태그 입력창을 찾지 못했습니다. 태그 없이 발행 단계로 진행합니다.")
        else:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tag_el)
                random_sleep(0.3, 0.6)
                tag_el.click()
                random_sleep(0.2, 0.4)

                for tag in tag_list:
                    try:
                        tag_el = driver.switch_to.active_element
                        tag_el.send_keys(tag)
                        random_sleep(0.15, 0.3)
                        tag_el.send_keys(Keys.ENTER)
                        random_sleep(0.25, 0.5)
                        print(f"[Tistory] 태그 입력 완료: {tag}")
                    except Exception as e:
                        print(f"[경고] 태그 '{tag}' 입력 실패. 다음 태그로 진행: {e}")
                        continue
            except Exception as e:
                print(f"[경고] 해시태그 입력 전체 실패. 태그 없이 발행 단계로 진행: {e}")

        if publish:
            print("[Tistory] '완료' 버튼 클릭 중...")
            _wait_and_click_xpath_with_js_fallback(driver, '//*[@id="publish-layer-btn"]', timeout=10)
            random_sleep(1.0, 1.5)

            representative_image_path = main_image_path or (upload_items[0]["path"] if upload_items else None)
            if representative_image_path:
                print("[Tistory] 본문 업로드 이미지와 같은 파일을 대표이미지로 지정합니다.")
                _upload_representative_image_in_publish_layer(driver, representative_image_path)
            else:
                print("[경고] 대표이미지로 지정할 사진 파일이 없어 발행창 대표이미지 추가를 건너뜁니다.")

            if visibility == "private":
                print("[Tistory] 비공개 상태 선택 중...")
                _select_tistory_private_visibility(driver)
                visibility_label = "비공개"
            else:
                print("[Tistory] 공개 상태 선택 중...")
                _select_tistory_public_visibility(driver)
                visibility_label = "공개"
            
            print(f"[Tistory] '{visibility_label} 발행' 버튼 클릭 중...")
            _wait_and_click_xpath_with_js_fallback(driver, '//*[@id="publish-btn"]', timeout=10)
            
            # 발행 클릭 후 로봇 확인 팝업 대기 (AI/봇 판별)
            print("[Tistory] 로봇 확인(캡챠) 팝업 여부 감시 중...")
            for _ in range(15):
                time.sleep(1)
                try:
                    # reCAPTCHA iframe이 나타나면 캡챠가 뜬 것
                    if driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]"):
                        print("\n🚨 [경고] 티스토리 '로봇이 아닙니다' 캡챠 팝업 감지됨! 🚨")
                        print("👉 스케줄러를 즉시 중단하고 3시간 뒤에 재개하도록 락을 설정합니다.")
                        set_captcha_lock()
                        raise RuntimeError("티스토리 캡챠(로봇 방지) 팝업이 발생하여 실행을 중단합니다.")
                except Exception as e:
                    if "티스토리 캡챠" in str(e):
                        raise e
                    pass

            random_sleep(2.0, 3.0)
            print(f"[Tistory] {visibility_label} 발행 완료")
        else:
            print("[Tistory] 임시저장 버튼 클릭 중...")
            _click_tistory_draft_save(driver)
    finally:
        # 안전한 임시 이미지 파일 삭제
        for path in temp_image_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass


def _health_product_db_path() -> Path:
    env_path = os.getenv("HEALTH_PRODUCT_DB_PATH")
    if env_path:
        return Path(env_path).expanduser()
    if HEALTH_PRODUCT_DB_DEFAULT_PATH.exists():
        return HEALTH_PRODUCT_DB_DEFAULT_PATH
    return HEALTH_PRODUCT_DB_FALLBACK_PATH


def _read_product_rows(product_db_path: Path | str | None = None) -> list[dict]:
    path = Path(product_db_path or PRODUCT_DB_PATH)
    if not path.exists():
        raise FileNotFoundError(f"상품 DB CSV가 없습니다: {path}")
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with path.open("r", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def _clean(value, default: str = "") -> str:
    v = (value or "").strip()
    return v if v else default


def _is_a_grade_row(row: dict) -> bool:
    grade = _clean(row.get("추천등급") or row.get("등급"))
    return grade == "A"


def _is_already_posted_row(row: dict) -> bool:
    used = _clean(row.get("used")).upper()
    post_title = _clean(row.get("post_title"))
    return used == "Y" or bool(post_title)


def select_products(count: int = 3, product_db_path: Path | str | None = None) -> list[dict]:
    all_rows = _read_product_rows(product_db_path)
    unused_rows = [r for r in all_rows if not _is_already_posted_row(r)]
    a_grade_rows = [r for r in unused_rows if _is_a_grade_row(r)]
    fallback_rows = [r for r in unused_rows if not _is_a_grade_row(r)]
    rows = a_grade_rows + fallback_rows
    products = rows[:count]
    if len(products) < 2:
        raise ValueError("비교 상품은 최소 2개 이상 필요합니다.")
    return products


def mark_products_as_used(
    products: list[dict],
    post_title: str = "",
    product_db_path: Path | str | None = None,
) -> None:
    path = Path(product_db_path or PRODUCT_DB_PATH)
    rows = _read_product_rows(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name_key = "\uC0C1\uD488\uBA85"
    keyword_key = "\uD0A4\uC6CC\uB4DC"
    targets = {(p.get(name_key, "").strip(), p.get(keyword_key, "").strip()) for p in products}

    if not targets or not rows:
        return

    for row in rows:
        key = (row.get(name_key, "").strip(), row.get(keyword_key, "").strip())
        if key in targets and (row.get("used") or "").strip() == "":
            row["used"] = "Y"
            row["used_at"] = now
            if post_title:
                row["post_title"] = post_title
            targets.remove(key)
        if not targets:
            break

    fieldnames = list(rows[0].keys())
    for required_field in ("used", "used_at", "post_title"):
        if required_field not in fieldnames:
            fieldnames.append(required_field)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_products_summary(products: list[dict]) -> str:
    lines = []
    for i, p in enumerate(products, 1):
        name = _clean(p.get("\uC0C1\uD488\uBA85"), f"상품{i}")
        price = _clean(p.get("상품가격"), _clean(p.get("가격"), "가격 확인 필요"))
        rating = _clean(p.get("평점"), "")
        review_count = _clean(p.get("리뷰수"), "")
        rocket_info = _clean(p.get("로켓정보"), _clean(p.get("로켓배송"), ""))
        ingredient = _clean(
            p.get("주요성분")
            or p.get("성분")
            or p.get("기능성원료")
            or p.get("원료"),
            "성분표 확인 필요",
        )
        serving = _clean(
            p.get("섭취량")
            or p.get("1일섭취량")
            or p.get("용량")
            or p.get("규격"),
            "섭취량/용량 확인 필요",
        )
        s = [
            _clean(p.get("\uC7A5\uC8101"), "상품 상세페이지와 리뷰에서 장점을 먼저 확인해 두는 편이 좋습니다."),
            _clean(p.get("\uC7A5\uC8102"), "비슷한 상품과 비교하면서 선택 기준을 세우기 좋습니다."),
            _clean(p.get("\uC7A5\uC8103"), "구매 전 가격과 옵션을 다시 확인해 두는 편이 안전합니다."),
        ]
        caution = _clean(p.get("\uC8FC\uC758\uC810"), "개인 상황에 따라 체감 차이가 있을 수 있습니다.")
        url = _clean(p.get("\uCFE0\uD321\uB9C1\uD06C"), "")
        facts = [f"가격 {price}", f"성분 {ingredient}", f"섭취/용량 {serving}"]
        if rating:
            facts.append(f"평점 {rating}")
        if review_count:
            facts.append(f"리뷰수 {review_count}")
        if rocket_info:
            facts.append(f"배송 {rocket_info}")
        lines.append(
            f"{i}. {name} / 확인 정보: {', '.join(facts)}"
            f" / 핵심 포인트: {s[0]}, {s[1]}, {s[2]}"
            f" / 주의사항: {caution} / 쿠팡 링크: {url}"
        )
    return "\n".join(lines)


def _format_price_for_prompt(value: str) -> str:
    text = _clean(value, "")
    digits = re.sub(r"[^0-9]", "", text)
    if digits:
        return f"{int(digits):,}원"
    return text or "가격 확인 필요"


def _build_health_products_summary(products: list[dict]) -> str:
    lines = []
    for i, p in enumerate(products, 1):
        name = _clean(p.get("\uC0C1\uD488\uBA85"), f"상품{i}")
        price = _format_price_for_prompt(_clean(p.get("상품가격"), _clean(p.get("가격"), "")))
        rating = _clean(p.get("평점"), "평점 확인 필요")
        review_count = _clean(p.get("리뷰수"), _clean(p.get("리뷰개수"), "리뷰 수 확인 필요"))
        rocket_info = _clean(p.get("로켓정보"), _clean(p.get("로켓배송"), "배송 확인 필요"))
        ingredient = _clean(
            p.get("주요성분")
            or p.get("성분")
            or p.get("기능성원료")
            or p.get("원료"),
            "성분표 확인 필요",
        )
        serving = _clean(
            p.get("섭취량")
            or p.get("1일섭취량")
            or p.get("용량")
            or p.get("규격"),
            "섭취량/용량 확인 필요",
        )
        caution = _clean(p.get("\uC8FC\uC758\uC810"), "개인 건강 상태와 표시사항을 확인해야 합니다.")
        lines.append(
            f"{i}. 상품명: {name}\n"
            f"   - 가격 확인 기준: {price}\n"
            f"   - 성분/원료: {ingredient}\n"
            f"   - 섭취량/용량: {serving}\n"
            f"   - 리뷰/배송: 평점 {rating}, 리뷰수 {review_count}, 배송 {rocket_info}\n"
            f"   - 신중히 볼 점: {caution}\n"
            f"   - 링크 마커: [PRODUCT_LINK_{i}]"
        )
    return "\n".join(lines)


def _build_health_image_cues(products: list[dict]) -> str:
    cues: list[str] = []
    for p in products:
        text = " ".join(
            _clean(p.get(key), "")
            for key in ("\uC0C1\uD488\uBA85", "\uD0A4\uC6CC\uB4DC", "\uCE74\uD14C\uACE0\uB9AC")
        ).lower()
        if any(token in text for token in ("레몬", "lemon")):
            cues.append("generic lemon juice stick packets, fresh lemon slices, clear water glass")
        elif any(token in text for token in ("프로틴", "단백", "protein", "드링크")):
            cues.append("generic protein drink glass, shaker cup, neutral carton without text")
        elif any(token in text for token in ("관절", "콘드로이친", "연골", "joint", "chondroitin")):
            cues.append("generic supplement bottle, tablets or capsules, serving checklist")
        elif any(token in text for token in ("비타민", "vitamin", "멀티")):
            cues.append("generic vitamin bottle, small tablets, daily nutrition checklist")
        elif any(token in text for token in ("오메가", "omega")):
            cues.append("generic omega supplement bottle, softgel capsules, water glass")
        else:
            cues.append("generic health supplement bottle, water glass, comparison checklist")
    deduped = list(dict.fromkeys(cues))
    return "; ".join(deduped[:3])


def _health_product_text(product: dict) -> str:
    return " ".join(
        _clean(product.get(key), "")
        for key in ("\uC0C1\uD488\uBA85", "\uD0A4\uC6CC\uB4DC", "\uCE74\uD14C\uACE0\uB9AC")
    ).lower()


def _build_health_image_focus(products: list[dict]) -> str:
    first = products[0] if products else {}
    text = _health_product_text(first)
    if any(token in text for token in ("레몬", "lemon")):
        return "adult hand tearing or squeezing a small unbranded lemon juice stick into a clear water glass, with lemon slices nearby"
    if any(token in text for token in ("프로틴", "단백", "protein", "드링크")):
        return "adult hand pouring or drinking a neutral protein drink in a glass or shaker cup, no visible brand or text"
    if any(token in text for token in ("관절", "콘드로이친", "연골", "joint", "chondroitin")):
        return "adult hand preparing generic supplement tablets or capsules with a water glass from an unbranded bottle"
    if any(token in text for token in ("비타민", "vitamin", "멀티")):
        return "adult hand preparing generic vitamin tablets with a water glass and a daily checklist"
    if any(token in text for token in ("오메가", "omega")):
        return "adult hand preparing generic softgel capsules with a water glass from an unbranded bottle"
    return "adult hand using the main health product type from the article in a clean daily routine setting, unbranded and text-free"


def _build_cta_links(products: list[dict]) -> str:
    """상품 이미지 + 가격이 포함된 카드형 CTA HTML을 생성합니다."""
    cards = []
    cta_texts = [
        "가격과 옵션 확인",
        "상세 정보 확인",
        "리뷰 수 확인",
    ]
    for i, p in enumerate(products, 1):
        name = _clean(p.get("상품명"), f"상품{i}")
        url = _clean(p.get("쿠팡링크"), "#")
        image = _clean(p.get("상품이미지"), "")
        price = _clean(p.get("상품가격"), "")
        is_rocket = _clean(p.get("로켓배송"), "N") == "Y"
        cta_text = cta_texts[(i - 1) % len(cta_texts)]

        # 가격 포맷팅
        price_html = ""
        if price:
            try:
                price_formatted = f"{int(price):,}원"
                price_html = (
                    f'<span style="display:block; font-size:24px; font-weight:900; '
                    f'color:#333333; margin:6px 0 2px;">{price_formatted}</span>'
                )
            except ValueError:
                pass

        # 로켓배송 뱃지
        rocket_html = ""
        if is_rocket:
            rocket_html = (
                '<span style="display:inline-block; background:#00bcd4; color:#fff; '
                'font-size:13px; font-weight:700; padding:3px 10px; border-radius:5px; '
                'margin-left:6px; vertical-align:middle;">로켓배송</span>'
            )

        # 이미지 영역
        if image:
            img_html = (
                f'<img src="{image}" alt="{name}" '
                f'style="width:160px; height:160px; object-fit:contain; '
                f'border-radius:8px; background:#fff; flex-shrink:0;" />'
            )
        else:
            img_html = (
                '<span style="display:flex; align-items:center; justify-content:center; '
                'width:160px; height:160px; background:#f5f5f5; border-radius:8px; '
                'color:#bbb; font-size:24px; flex-shrink:0;">상품</span>'
            )

        card = (
            f'<a href="{url}" target="_blank" rel="nofollow sponsored noopener" '
            f'style="display:flex; align-items:center; gap:16px; '
            f'padding:20px; margin:20px 0; border:1px solid #e0e0e0; '
            f'border-radius:14px; background:#fff; text-decoration:none; '
            f'color:#333; box-shadow:0 4px 16px rgba(0,0,0,0.10);">'
            f'{img_html}'
            f'<span style="display:flex; flex-direction:column; flex:1; min-width:0;">'
            f'<span style="font-size:17px; font-weight:800; color:#222; '
            f'line-height:1.4; word-break:keep-all;">{name}{rocket_html}</span>'
            f'{price_html}'
            f'<span style="display:inline-block; margin-top:10px; padding:12px 24px; '
            f'background:#3f4a45; color:#fff; '
            f'font-size:16px; font-weight:800; border-radius:10px; text-align:center; '
            f'letter-spacing:0.3px;">{cta_text}</span>'
            f'</span></a>'
        )
        cards.append(card)
    return "\n".join(cards)

def build_prompt_values(products: list[dict], content_vertical: str = "coupang") -> dict:
    first    = products[0]
    category = _clean(first.get("\uCE74\uD14C\uACE0\uB9AC"), "건강관리")
    keyword  = _clean(first.get("\uD0A4\uC6CC\uB4DC"), _clean(first.get("\uC0C1\uD488\uBA85"), "쿠팡 상품 추천"))
    keywords = ", ".join(
        _clean(p.get("\uD0A4\uC6CC\uB4DC"), _clean(p.get("\uC0C1\uD488\uBA85"), ""))
        for p in products
        if _clean(p.get("\uD0A4\uC6CC\uB4DC"), _clean(p.get("\uC0C1\uD488\uBA85"), ""))
    )
    if content_vertical == "health_supplement":
        category = _clean(first.get("\uCE74\uD14C\uACE0\uB9AC"), "건강식품")
        keyword = _clean(first.get("\uD0A4\uC6CC\uB4DC"), _clean(first.get("\uC0C1\uD488\uBA85"), "40대 50대 건강식품 비교"))
        default_target_reader = "라운딩과 일상을 병행하는 40~50대 골퍼와 중년 독자"
        default_usage_scenario = "라운딩 전후 컨디션 관리와 평소 영양 보충을 위해 건강식품을 비교하는 상황"
        default_pain_point = "성분, 섭취량, 가격, 리뷰, 주의사항이 달라 무엇을 먼저 봐야 할지 어려운 경우"
        tone = "차분하고 프리미엄 정보형"
        products_summary = _build_health_products_summary(products)
        cta_links = ""
    else:
        default_target_reader = "비슷한 상품 중 무엇을 고를지 고민하는 독자"
        default_usage_scenario = "일상에서 제품을 비교하고 구매하려는 상황"
        default_pain_point = "비슷한 상품이 많아 선택이 어려운 경우"
        tone = "깔끔하고 정보형"
        products_summary = _build_products_summary(products)
        cta_links = _build_cta_links(products)
    return {
        "keyword":          keyword,
        "keywords":         keywords,
        "product_count":    len(products),
        "products_summary": products_summary,
        "target_reader":    _clean(first.get("\uD0C0\uAC9F\uB3C5\uC790"), default_target_reader),
        "usage_scenario":   _clean(first.get("\uC0AC\uC6A9\uC7A5\uC18C"), _clean(first.get("\uBB38\uC81C\uC0C1\uD669"), default_usage_scenario)),
        "product_names":    ", ".join(_clean(p.get("\uC0C1\uD488\uBA85"), "상품") for p in products),
        "category":         category,
        "tone":             tone,
        "pain_point":       _clean(first.get("\uBB38\uC81C\uC0C1\uD669"), default_pain_point),
        "cta_links":        cta_links,
        "health_image_focus": _build_health_image_focus(products) if content_vertical == "health_supplement" else category,
        "health_image_cues": _build_health_image_cues(products) if content_vertical == "health_supplement" else category,
        "image1_url":       "",
        "image2_url":       "",
        "content_vertical":  content_vertical,
        "disclosure":       EXACT_COUPANG_DISCLOSURE,
    }


def _coupang_url_key(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    parsed = urllib.parse.urlsplit(text)
    if not parsed.netloc:
        return text.rstrip("/")
    query = urllib.parse.parse_qs(parsed.query)
    stable_query = []
    for key in ("productId", "itemId", "vendorItemId"):
        value = query.get(key, [""])[0]
        if value:
            stable_query.append(f"{key}={value}")
    base = f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    return base + ("?" + "&".join(stable_query) if stable_query else "")


def _row_coupang_url_key(row: dict) -> str:
    return _coupang_url_key(
        _clean(row.get("쿠팡링크"))
        or _clean(row.get("coupang_partners_link"))
        or _clean(row.get("product_url"))
        or _clean(row.get("url"))
    )


def _load_used_coupang_url_keys() -> set[str]:
    return {key for key in (_coupang_url_key(url) for url in _load_used_coupang_urls()) if key}


def _choose_health_products(
    seed_products: list[dict],
    enriched_products: list[dict],
    count: int = 3,
    used_keys: set[str] | None = None,
    seen_keys: set[str] | None = None,
    require_minimum: bool = True,
) -> tuple[list[dict], list[dict]]:
    used_keys = set(used_keys) if used_keys is not None else _load_used_coupang_url_keys()
    selected_seed: list[dict] = []
    selected_enriched: list[dict] = []
    seen_keys = seen_keys if seen_keys is not None else set()

    for seed, enriched in zip(seed_products, enriched_products):
        key = _row_coupang_url_key(enriched) or _row_coupang_url_key(seed)
        if not _row_coupang_url_key(enriched):
            print(f"[Products] API 파트너스 상품 URL이 없어 제외: {seed.get('상품명') or seed.get('키워드') or '상품'}")
            continue
        if key and key in used_keys:
            print(f"[Products] 이미 사용한 쿠팡 상품 제외: {enriched.get('상품명') or seed.get('상품명') or key}")
            continue
        if key and key in seen_keys:
            print(f"[Products] 이번 실행 내 중복 쿠팡 상품 제외: {enriched.get('상품명') or seed.get('상품명') or key}")
            continue
        if key:
            seen_keys.add(key)
        selected_seed.append(seed)
        selected_enriched.append(enriched)
        if len(selected_enriched) >= count:
            break

    if require_minimum and len(selected_enriched) < 2:
        raise ValueError("건강식품 비교 상품은 최소 2개 이상 필요합니다.")
    return selected_seed, selected_enriched


def prepare_health_coupang_products(count: int = 3) -> tuple[Path, list[dict], list[dict]]:
    if not COUPANG_API_ENABLED:
        raise RuntimeError("건강식품 쿠팡 글은 쿠팡 API 사용이 필요합니다. COUPANG_API_ENABLED=1로 설정하세요.")
    if not COUPANG_ACCESS_KEY or not COUPANG_SECRET_KEY:
        raise RuntimeError("COUPANG_ACCESS_KEY 또는 COUPANG_SECRET_KEY가 없어 쿠팡 API를 사용할 수 없습니다.")

    product_db_path = _health_product_db_path()
    scan_limit = max(count, HEALTH_PRODUCT_SELECTION_SCAN_LIMIT)
    batch_size = max(count, HEALTH_PRODUCT_ENRICH_BATCH_SIZE)
    seed_products = select_products(count=scan_limit, product_db_path=product_db_path)
    used_keys = _load_used_coupang_url_keys()
    seen_keys: set[str] = set()
    selected_seed: list[dict] = []
    selected_enriched: list[dict] = []

    for batch_start in range(0, len(seed_products), batch_size):
        remaining = count - len(selected_enriched)
        if remaining <= 0:
            break
        batch_seed_products = seed_products[batch_start:batch_start + batch_size]
        excluded_url_keys = set(used_keys) | set(seen_keys)
        enriched_products = enrich_products_with_coupang_links(
            batch_seed_products,
            api_enabled=COUPANG_API_ENABLED,
            access_key=COUPANG_ACCESS_KEY or "",
            secret_key=COUPANG_SECRET_KEY or "",
            sub_id=COUPANG_SUB_ID,
            fallback_to_similar=True,
            require_api_product=True,
            excluded_url_keys=excluded_url_keys,
            url_key_func=_coupang_url_key,
        )
        batch_selected_seed, batch_selected_enriched = _choose_health_products(
            batch_seed_products,
            enriched_products,
            count=remaining,
            used_keys=used_keys,
            seen_keys=seen_keys,
            require_minimum=False,
        )
        selected_seed.extend(batch_selected_seed)
        selected_enriched.extend(batch_selected_enriched)

    if len(selected_enriched) < 2:
        raise ValueError(
            "건강식품 비교 상품은 최소 2개 이상 필요합니다. "
            f"확인 후보 {len(seed_products)}개 중 API 파트너스 링크 확보/중복 제외 후 {len(selected_enriched)}개만 남았습니다."
        )
    print(f"[Products] 건강식품 DB: {product_db_path}")
    print(f"[Products] 건강식품 쿠팡 비교 상품 확정: {len(selected_enriched)}개 / 확인 후보 {len(seed_products)}개")
    return product_db_path, selected_seed, selected_enriched


# ------------------------------------------------------------------
# 로그
# ------------------------------------------------------------------

def _append_csv(path: Path, fieldnames: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def _extract_coupang_urls(text: str) -> list[str]:
    urls = []
    for token in text.replace("\n", " ").split():
        t = token.strip().strip(",)(")
        if "coupang.com" in t:
            urls.append(t)
    return urls


def _load_used_coupang_urls() -> set[str]:
    if not USED_COUPANG_URL_LOG_PATH.exists():
        return set()
    with USED_COUPANG_URL_LOG_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        return {r["coupang_url"] for r in csv.DictReader(f) if r.get("coupang_url")}


def validate_coupang_urls(prompt_text: str) -> None:
    used_keys = _load_used_coupang_url_keys()
    duplicated = sorted(
        url for url in set(_extract_coupang_urls(prompt_text))
        if _coupang_url_key(url) and _coupang_url_key(url) in used_keys
    )
    if duplicated:
        raise ValueError("중복 쿠팡 URL 감지:\n" + "\n".join(duplicated))


def log_run(label: str, prompt_text: str) -> None:
    _append_csv(
        RUN_LOG_PATH,
        ["run_at", "prompt_label", "prompt_length"],
        {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "prompt_label": label, "prompt_length": len(prompt_text)},
    )


def archive_prompt(label: str, prompt_text: str) -> None:
    PROMPT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    safe_label = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", label).strip("_") or "prompt"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PROMPT_ARCHIVE_DIR / f"{timestamp}_{safe_label}.txt"
    path.write_text(prompt_text, encoding="utf-8")


def log_coupang_urls(prompt_text: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for url in _extract_coupang_urls(prompt_text):
        _append_csv(USED_COUPANG_URL_LOG_PATH, ["used_at", "coupang_url"], {"used_at": now, "coupang_url": url})


def _log_product_coupang_urls(products: list[dict]) -> None:
    urls = "\n".join(_clean(p.get("쿠팡링크"), "") for p in products)
    if urls.strip():
        log_coupang_urls(urls)


def _replace_product_link_markers(html_body: str, products: list[dict]) -> str:
    result = html_body or ""
    for i, product in enumerate(products, 1):
        url = _clean(product.get("쿠팡링크"), "")
        if not url:
            continue
        marker = f"[PRODUCT_LINK_{i}]"
        for token in {marker, html.escape(marker), urllib.parse.quote(marker, safe="")}:
            result = result.replace(token, url)
    return result


def _ensure_style_attr(attrs: str, style: str) -> str:
    if re.search(r'\sstyle\s*=', attrs or "", flags=re.IGNORECASE):
        return attrs
    return f'{attrs} style="{style}"'


def _style_opening_tag(html_body: str, tag_name: str, style: str) -> str:
    pattern = re.compile(rf'<{tag_name}\b([^>]*)>', flags=re.IGNORECASE)
    return pattern.sub(lambda m: f'<{tag_name}{_ensure_style_attr(m.group(1), style)}>', html_body)


def _style_coupang_html_for_tistory(html_body: str, keyword: str = "") -> str:
    if not html_body:
        return html_body

    html_body = re.sub(
        r'<(p|h2|h3|li|strong|a)\b([^>]*)>\s*</\1>',
        '',
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )

    h2_style = "font-size:21px; font-weight:700; color:#1a1a2e; padding:0 0 12px; border-bottom:2px solid #f0f0f0; margin:36px 0 16px;"
    h2_marker = '<span style="display:inline-block; width:8px; height:8px; background:#ff9500; border-radius:50%; margin-right:8px; vertical-align:middle;"></span>'

    def _style_h2(match):
        attrs = _ensure_style_attr(match.group(1), h2_style)
        content = match.group(2).strip()
        if not re.match(r'<span\b', content, flags=re.IGNORECASE):
            content = h2_marker + content
        return f'<h2{attrs}>{content}</h2>'

    html_body = re.sub(r'<h2\b([^>]*)>(.*?)</h2>', _style_h2, html_body, flags=re.IGNORECASE | re.DOTALL)

    html_body = _style_opening_tag(html_body, "h3", "font-size:18px; font-weight:700; color:#333; margin:24px 0 12px; padding-left:12px; border-left:3px solid #ff9500;")
    html_body = _style_opening_tag(html_body, "p", "font-size:16px; line-height:1.95; color:#333; margin:0 0 18px; word-break:keep-all;")
    html_body = _style_opening_tag(html_body, "ul", "list-style:none; padding:0; margin:0 0 24px;")
    html_body = _style_opening_tag(html_body, "strong", "font-weight:700; color:#1a1a2e;")

    li_style = "font-size:15px; color:#444; padding:10px 16px 10px 40px; background:#fafafa; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:8px; position:relative; line-height:1.7;"
    li_marker = '<span style="position:absolute; left:16px; color:#ff9500; font-weight:700;">✔</span>'

    def _style_li(match):
        attrs = _ensure_style_attr(match.group(1), li_style)
        content = match.group(2).strip()
        if not re.match(r'<span\b', content, flags=re.IGNORECASE):
            content = li_marker + content
        return f'<li{attrs}>{content}</li>'

    html_body = re.sub(r'<li\b([^>]*)>(.*?)</li>', _style_li, html_body, flags=re.IGNORECASE | re.DOTALL)

    cta_main_style = "display:block; background:linear-gradient(90deg,#ff6b35,#ff9500); color:#fff; text-align:center; padding:15px 20px; border-radius:10px; text-decoration:none; font-weight:700; font-size:15px; letter-spacing:0.5px; margin:18px 0;"
    cta_sub_style = "display:block; background:#1a1a2e; color:#fff; text-align:center; padding:15px 20px; border-radius:10px; text-decoration:none; font-weight:700; font-size:15px; border:1px solid #333; margin:18px 0;"
    link_index = {"value": 0}

    def _style_anchor(match):
        attrs = match.group(1)
        if re.search(r'\sstyle\s*=', attrs, flags=re.IGNORECASE):
            return match.group(0)
        href_match = re.search(r'\shref\s*=\s*(["\'])(.*?)\1', attrs, flags=re.IGNORECASE | re.DOTALL)
        href = html.unescape(href_match.group(2)) if href_match else ""
        if "coupang.com" not in href:
            return match.group(0)
        link_index["value"] += 1
        style = cta_main_style if link_index["value"] == 1 else cta_sub_style
        return f'<a{_ensure_style_attr(attrs, style)}>'

    html_body = re.sub(r'<a\b([^>]*)>', _style_anchor, html_body, flags=re.IGNORECASE | re.DOTALL)

    img_style = "max-width:100%; border-radius:12px; display:block; margin:0 auto;"
    escaped_keyword = html.escape(keyword or "상품 비교", quote=True)

    def _style_img(match):
        attrs = match.group(1)
        self_closing = attrs.rstrip().endswith("/")
        if self_closing:
            attrs = attrs.rstrip()[:-1].rstrip()
        attrs = _ensure_style_attr(attrs, img_style)
        if not re.search(r'\salt\s*=', attrs, flags=re.IGNORECASE):
            attrs = f'{attrs} alt="{escaped_keyword} 이미지"'
        return f'<img{attrs} />' if self_closing else f'<img{attrs}>'

    return re.sub(r'<img\b([^>]*)>', _style_img, html_body, flags=re.IGNORECASE | re.DOTALL)



def _replace_inline_coupang_links_with_cards(html_body: str, products: list[dict]) -> str:
    """본문 내 쿠팡 인라인 링크를 카드형 HTML로 후처리 변환합니다."""
    if not products:
        return html_body
    
    # products에서 URL → 상품 정보 매핑
    url_to_product = {}
    for p in products:
        url = _clean(p.get("쿠팡링크"), "")
        if url and "coupang.com" in url:
            url_to_product[url] = p
    
    if not url_to_product:
        return html_body
    
    # <a href="...coupang...">텍스트</a> 패턴 찾기
    pattern = re.compile(
        r'<a\s[^>]*href="(https?://[^"]*coupang\.com[^"]*)"[^>]*>([^<]+(?:<[^/a][^<]*>)*[^<]*)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    
    def _make_card(match):
        url = match.group(1)
        original_text = match.group(2)
        
        # URL에서 매칭되는 상품 찾기
        product = None
        for purl, pdata in url_to_product.items():
            if purl in url or url in purl:
                product = pdata
                break
        
        if not product:
            # 매칭 실패 시 원본 유지
            return match.group(0)
        
        name = _clean(product.get("상품명"), "")
        image = _clean(product.get("상품이미지"), "")
        price = _clean(product.get("상품가격"), "")
        is_rocket = _clean(product.get("로켓배송"), "N") == "Y"
        
        if not name:
            return match.group(0)
        
        # 가격 HTML
        price_html = ""
        if price:
            try:
                price_html = (
                    f'<span style="display:block; font-size:24px; font-weight:900; '
                    f'color:#333333; margin:6px 0 2px;">{int(price):,}원</span>'
                )
            except ValueError:
                pass
        
        # 로켓배송 뱃지
        rocket_html = ""
        if is_rocket:
            rocket_html = (
                '<span style="display:inline-block; background:#00bcd4; color:#fff; '
                'font-size:13px; font-weight:700; padding:3px 10px; border-radius:5px; '
                'margin-left:6px; vertical-align:middle;">로켓배송</span>'
            )
        
        # 이미지
        if image:
            img_html = (
                f'<img src="{image}" alt="{name}" '
                f'style="width:160px; height:160px; object-fit:contain; '
                f'border-radius:8px; background:#fff; flex-shrink:0;" />'
            )
        else:
            img_html = (
                '<span style="display:flex; align-items:center; justify-content:center; '
                'width:160px; height:160px; background:#f5f5f5; border-radius:8px; '
                'color:#bbb; font-size:24px; flex-shrink:0;">상품</span>'
            )
        
        card = (
            f'<a href="{url}" target="_blank" rel="nofollow sponsored noopener" '
            f'style="display:flex; align-items:center; gap:16px; '
            f'padding:20px; margin:20px 0; border:1px solid #e0e0e0; '
            f'border-radius:14px; background:#fff; text-decoration:none; '
            f'color:#333; box-shadow:0 4px 16px rgba(0,0,0,0.10);">'
            f'{img_html}'
            f'<span style="display:flex; flex-direction:column; flex:1; min-width:0;">'
            f'<span style="font-size:17px; font-weight:800; color:#222; '
            f'line-height:1.4; word-break:keep-all;">{name}{rocket_html}</span>'
            f'{price_html}'
            f'<span style="display:inline-block; margin-top:10px; padding:12px 24px; '
            f'background:#3f4a45; color:#fff; '
            f'font-size:16px; font-weight:800; border-radius:10px; text-align:center; '
            f'letter-spacing:0.3px;">상세 정보 확인</span>'
            f'</span></a>'
        )
        return card
    
    result = pattern.sub(_make_card, html_body)
    replaced_count = len(pattern.findall(html_body)) - len(pattern.findall(result))
    if replaced_count > 0:
        print(f"[CTA] 본문 내 {replaced_count}개 쿠팡 링크를 카드형으로 변환")
    
    return result

def ensure_exact_coupang_disclosure(html_body: str) -> str:
    """쿠팡 파트너스 고지 문구를 HTML 본문 맨 위에 삽입합니다."""
    disclosure_html = (
        '<p style="font-size:12px; color:#999; background:#f8f9fa; '
        'border-left:3px solid #ccc; padding:10px 14px; margin:0 0 24px; '
        'border-radius:0 6px 6px 0;">'
        f'{EXACT_COUPANG_DISCLOSURE}</p>'
    )

    html_body = re.sub(
        r'<p\b[^>]*>\s*' + re.escape(EXACT_COUPANG_DISCLOSURE) + r'\s*</p>\s*',
        '',
        html_body or '',
        flags=re.IGNORECASE,
    )
    html_body = re.sub(
        re.escape(EXACT_COUPANG_DISCLOSURE) + r'\s*',
        '',
        html_body,
        count=1,
    )

    old_disclosures = [
        "쿠팡 파트너스 활동의 일환으로 일정 수수료를 제공받을 수 있습니다.",
    ]
    for old in old_disclosures:
        html_body = re.sub(
            r'<p[^>]*>' + re.escape(old) + r'</p>\s*',
            '',
            html_body,
        )

    return disclosure_html + "\n" + html_body.lstrip()


# ------------------------------------------------------------------
# 결과 저장
# ------------------------------------------------------------------

def save_results(
    title_text: str,
    html_body: str,
    hashtags: str,
    image1_url: str,
    image2_url: str,
    image1_data_url: str = "",
    image2_data_url: str = "",
) -> None:
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "title_candidates.txt": clean_generated_text(title_text),
        "body.html":            clean_generated_html_body(html_body),
        "hashtags.txt":         clean_generated_text(hashtags),
        "image_urls.txt":       f"{image1_url}\n{image2_url}\n",
        "image1_data_url.txt":  image1_data_url,
        "image2_data_url.txt":  image2_data_url,
    }.items():
        (GENERATED_RESULT_DIR / name).write_text(content, encoding="utf-8")
    print(f"[저장] {GENERATED_RESULT_DIR}")


def save_golf_image_result(image_url: str, image_data_url: str) -> None:
    """골프 대표 이미지를 받은 즉시 재사용 가능한 형태로 보관합니다."""
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_RESULT_DIR / "image_urls.txt").write_text(f"{image_url}\n\n", encoding="utf-8")
    (GENERATED_RESULT_DIR / "image1_data_url.txt").write_text(image_data_url or "", encoding="utf-8")
    (GENERATED_RESULT_DIR / "image2_data_url.txt").write_text("", encoding="utf-8")

    if not image_data_url or not image_data_url.startswith("data:image/") or "," not in image_data_url:
        print("[저장] 골프 대표 이미지 URL만 보관했습니다.")
        return

    header, encoded = image_data_url.split(",", 1)
    mime_match = re.match(r"data:image/([^;]+);base64", header, re.IGNORECASE)
    ext = (mime_match.group(1).lower() if mime_match else "png").replace("jpeg", "jpg")
    image_path = GENERATED_RESULT_DIR / f"image1.{ext}"
    image_path.write_bytes(base64.b64decode(encoded))
    print(f"[저장] 골프 대표 이미지 보관 완료: {image_path}")


def load_saved_result() -> dict:
    title_candidates_path = GENERATED_RESULT_DIR / "title_candidates.txt"
    body_path = GENERATED_RESULT_DIR / "body.html"
    hashtags_path = GENERATED_RESULT_DIR / "hashtags.txt"

    missing = [str(p.name) for p in (title_candidates_path, body_path, hashtags_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"저장된 생성 결과가 부족합니다: {', '.join(missing)}")

    title_text = clean_generated_text(title_candidates_path.read_text(encoding="utf-8").strip())
    html_body = clean_generated_html_body(body_path.read_text(encoding="utf-8"))
    hashtags_text = clean_generated_text(hashtags_path.read_text(encoding="utf-8").strip())

    image_urls_path = GENERATED_RESULT_DIR / "image_urls.txt"
    image_urls = []
    if image_urls_path.exists():
        image_urls = [line.strip() for line in image_urls_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    image1_url = image_urls[0] if len(image_urls) >= 1 else ""
    image2_url = image_urls[1] if len(image_urls) >= 2 else ""
    image1_data_url = (GENERATED_RESULT_DIR / "image1_data_url.txt").read_text(encoding="utf-8").strip() if (GENERATED_RESULT_DIR / "image1_data_url.txt").exists() else ""
    image2_data_url = (GENERATED_RESULT_DIR / "image2_data_url.txt").read_text(encoding="utf-8").strip() if (GENERATED_RESULT_DIR / "image2_data_url.txt").exists() else ""
    topic_strategy = {}
    topic_strategy_path = GENERATED_RESULT_DIR / "topic_strategy.json"
    if topic_strategy_path.exists():
        try:
            topic_strategy = json.loads(topic_strategy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[경고] 저장된 골프 주제 전략 JSON을 읽지 못했습니다: {exc}")

    return {
        "title":            pick_first_title(title_text),
        "title_candidates": title_text,
        "html_body":        html_body,
        "hashtags":         hashtags_text,
        "image1_url":       image1_url,
        "image2_url":       image2_url,
        "image1_data_url":  image1_data_url,
        "image2_data_url":  image2_data_url,
        "topic_strategy":   topic_strategy,
    }


def pick_first_title(title_text: str) -> str:
    for line in title_text.splitlines():
        line = line.strip()
        if not line:
            continue
        title = line.split(". ", 1)[1].strip() if ". " in line[:5] else line
        cleaned = re.sub(r"^(?:2026년?|2026)\s*[:：,\-–—]?\s*", "", title).strip()
        return cleaned if len(cleaned) >= 10 else title
    raise ValueError("제목 후보를 찾을 수 없습니다.")


# ==================================================================
# ██████╗  ██████╗ ██╗     ███████╗    ███████╗██╗   ██╗███████╗
# ██╔════╝ ██╔═══██╗██║     ██╔════╝    ██╔════╝╚██╗ ██╔╝██╔════╝
# ██║  ███╗██║   ██║██║     █████╗      ███████╗ ╚████╔╝ ███████╗
# ██║   ██║██║   ██║██║     ██╔══╝      ╚════██║  ╚██╔╝  ╚════██║
# ╚██████╔╝╚██████╔╝███████╗██║         ███████║   ██║   ███████║
#  ╚═════╝  ╚═════╝ ╚══════╝╚═╝         ╚══════╝   ╚═╝   ╚══════╝
# 프리미엄 골프 블로그 자동화 시스템
# 대상: 웰링턴 CC / 트리니티 CC / 잭니클라우스 GC
# 타겟 독자: 40~50대 프리미엄 골퍼
# ==================================================================

GOLF_TOPIC_LOG_PATH = LOG_DIR / "golf_topics_used.json"
GOLF_TOPIC_STRATEGY_PATH = GENERATED_RESULT_DIR / "topic_strategy.json"
GOLF_RESEARCH_SOURCE_LOG_PATH = GENERATED_RESULT_DIR / "research_source_log.md"
GOLF_TOPIC_PERFORMANCE_CSV_PATH = Path(
    os.getenv("GOLF_TOPIC_PERFORMANCE_CSV_PATH", str(DATA_DIR / "golf_topic_performance.csv"))
)


# ------------------------------------------------------------------
# 골프 주제 풀 — 3개 클럽 × 다각도 주제 (200개+)
# ------------------------------------------------------------------
GOLF_TOPIC_POOL: list[dict] = [

    # ── 웰링턴 CC ─────────────────────────────────────────────────
    {"club": "웰링턴 CC", "topic": "코스 레이아웃 완전 분석 — 18홀 전략 가이드", "category": "코스분석"},
    {"club": "웰링턴 CC", "topic": "그린 빠르기와 공략법 — 시즌별 스팀프미터 분석", "category": "코스분석"},
    {"club": "웰링턴 CC", "topic": "멤버십 등급별 혜택 비교 — 정회원과 주중회원의 차이", "category": "멤버십"},
    {"club": "웰링턴 CC", "topic": "멤버십 시세와 권리금 흐름 — 2025년 최신 시장 분석", "category": "멤버십"},
    {"club": "웰링턴 CC", "topic": "비회원 부킹 방법 완전 정리 — 캐디피·카트피 포함 실비용", "category": "예약·비용"},
    {"club": "웰링턴 CC", "topic": "그린피 시즌별 차이 — 성수기·비수기·주말·주중 완전 비교", "category": "예약·비용"},
    {"club": "웰링턴 CC", "topic": "캐디 서비스 수준과 팁 문화 — 실제 경험자 후기 종합", "category": "서비스"},
    {"club": "웰링턴 CC", "topic": "클럽하우스 식당 메뉴와 가격 — 라운딩 후 식사 완벽 가이드", "category": "부대시설"},
    {"club": "웰링턴 CC", "topic": "락커룸·사우나 시설 수준 — 프리미엄 CC 비교 분석", "category": "부대시설"},
    {"club": "웰링턴 CC", "topic": "드레스코드와 코스 에티켓 — 처음 방문자가 꼭 알아야 할 것", "category": "에티켓"},
    {"club": "웰링턴 CC", "topic": "베스트 시즌은 언제? — 월별 코스 컨디션과 예약 전략", "category": "시즌"},
    {"club": "웰링턴 CC", "topic": "봄 시즌 코스 컨디션 리포트 — 페어웨이·그린 상태 점검", "category": "시즌"},
    {"club": "웰링턴 CC", "topic": "가을 단풍 시즌 라운딩 — 경관과 코스 컨디션의 황금기", "category": "시즌"},
    {"club": "웰링턴 CC", "topic": "동반자 규정 완전 정리 — 비회원 동반 조건과 제한사항", "category": "규정"},
    {"club": "웰링턴 CC", "topic": "접근성과 주차 — 교통 편의성 실제 평가", "category": "접근성"},
    {"club": "웰링턴 CC", "topic": "전동카트 vs 캐디카트 — 어느 쪽이 더 유리한가", "category": "서비스"},
    {"club": "웰링턴 CC", "topic": "코스 난이도별 공략 홀 TOP5 — 멤버들이 꼽은 함정 홀", "category": "코스분석"},
    {"club": "웰링턴 CC", "topic": "퍼블릭 vs 프라이빗 — 웰링턴 CC를 선택해야 하는 이유", "category": "비교분석"},
    {"club": "웰링턴 CC", "topic": "프로샵 장비 라인업과 수선 서비스", "category": "부대시설"},
    {"club": "웰링턴 CC", "topic": "법인회원 활용 전략 — 비즈니스 골프를 위한 스마트 선택", "category": "멤버십"},
    {"club": "웰링턴 CC", "topic": "연습 시설 수준 — 드라이빙 레인지·퍼팅 그린 상세 가이드", "category": "부대시설"},
    {"club": "웰링턴 CC", "topic": "코스 세팅 트릭 — 핀 포지션 패턴으로 읽는 공략 전략", "category": "코스분석"},
    {"club": "웰링턴 CC", "topic": "주요 대회 히스토리와 코스 변화 기록", "category": "히스토리"},
    {"club": "웰링턴 CC", "topic": "실제 회원이 말하는 웰링턴 CC의 장단점 솔직 후기", "category": "후기"},
    {"club": "웰링턴 CC", "topic": "새벽 조 vs 오후 조 — 시간대별 라운딩 경험 비교", "category": "팁"},
    {"club": "웰링턴 CC", "topic": "골프 카트 GPS 시스템 활용법 — 숨겨진 기능 완전 공개", "category": "팁"},
    {"club": "웰링턴 CC", "topic": "코스 설계 철학 분석 — 아키텍트의 의도를 읽으면 스코어가 준다", "category": "코스분석"},
    {"club": "웰링턴 CC", "topic": "기업 접대 골프에 웰링턴 CC를 쓰는 이유 — 이미지 전략", "category": "멤버십"},
    {"club": "웰링턴 CC", "topic": "웰링턴 CC 주변 맛집 & 숙소 — 골프 여행 완벽 패키지", "category": "주변정보"},
    {"club": "웰링턴 CC", "topic": "회원권 분양 vs 중고 매입 — 어떤 방법이 더 유리한가", "category": "멤버십"},

    # ── 트리니티 CC ───────────────────────────────────────────────
    {"club": "트리니티 CC", "topic": "3개 코스 완전 분석 — A·B·C 코스 난이도와 특징 비교", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "시그니처 홀 집중 공략 — 트리니티만의 전략적 명홀", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "멤버십 종류와 입회 절차 — 2025 최신 가이드", "category": "멤버십"},
    {"club": "트리니티 CC", "topic": "회원권 시세 추이 분석 — 언제 사고 언제 파는 것이 유리한가", "category": "멤버십"},
    {"club": "트리니티 CC", "topic": "비회원 라운딩 예약 전략 — 경쟁률 낮은 시간대 공략법", "category": "예약·비용"},
    {"club": "트리니티 CC", "topic": "2025 그린피 완전 정리 — 시즌·요일·코스별 가격표", "category": "예약·비용"},
    {"club": "트리니티 CC", "topic": "캐디 배정 시스템과 퀄리티 — 트리니티만의 특이한 점", "category": "서비스"},
    {"club": "트리니티 CC", "topic": "클럽하우스 F&B 완전 정리 — 식사 메뉴·주류 서비스·가격", "category": "부대시설"},
    {"club": "트리니티 CC", "topic": "VIP 라운지와 특별 서비스 — 상위 회원만 누리는 혜택", "category": "서비스"},
    {"club": "트리니티 CC", "topic": "코스 관리 수준 평가 — 페어웨이·러프·그린 컨디션 정기 리포트", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "최적 라운딩 시즌 가이드 — 월별 코스 상태와 예약 팁", "category": "시즌"},
    {"club": "트리니티 CC", "topic": "겨울 시즌에도 라운딩이 가능한가 — 동절기 코스 운영 현황", "category": "시즌"},
    {"club": "트리니티 CC", "topic": "동반자 룰 심층 분석 — 비회원 동반 횟수 제한과 우회 방법", "category": "규정"},
    {"club": "트리니티 CC", "topic": "드레스코드 세부 기준 — 어떤 복장이 OK이고 어떤 게 NG인가", "category": "에티켓"},
    {"club": "트리니티 CC", "topic": "셀프 라운딩 가능 여부와 조건 — 고수들이 선호하는 이유", "category": "서비스"},
    {"club": "트리니티 CC", "topic": "코스별 핵심 공략 포인트 — A코스 18홀 홀별 가이드", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "코스별 핵심 공략 포인트 — B코스 18홀 홀별 가이드", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "코스별 핵심 공략 포인트 — C코스 18홀 홀별 가이드", "category": "코스분석"},
    {"club": "트리니티 CC", "topic": "트리니티 CC 설계 배경 — 코스 아키텍트와 설계 철학", "category": "히스토리"},
    {"club": "트리니티 CC", "topic": "회원 커뮤니티 문화 — 트리니티만의 사교 분위기와 인맥 형성", "category": "후기"},
    {"club": "트리니티 CC", "topic": "골프 연습 환경 — 드라이빙 레인지·숏게임 구역 상세 리뷰", "category": "부대시설"},
    {"club": "트리니티 CC", "topic": "트리니티 CC 법인 활용 — 접대 골프에서 가장 선호하는 이유", "category": "멤버십"},
    {"club": "트리니티 CC", "topic": "주차 환경과 발레파킹 서비스 — 편의성 실제 평가", "category": "접근성"},
    {"club": "트리니티 CC", "topic": "트리니티 CC 10년 변화사 — 리뉴얼과 코스 개선 히스토리", "category": "히스토리"},
    {"club": "트리니티 CC", "topic": "실회원이 공개하는 트리니티 CC 최고의 홀과 최악의 홀", "category": "후기"},
    {"club": "트리니티 CC", "topic": "프로 대회 개최 이력과 그 코스가 특별한 이유", "category": "히스토리"},
    {"club": "트리니티 CC", "topic": "웰빙 시설 현황 — 사우나·마사지·피트니스 상세 가이드", "category": "부대시설"},
    {"club": "트리니티 CC", "topic": "트리니티 CC vs 웰링턴 CC — 같은 급 클럽의 솔직 비교", "category": "비교분석"},
    {"club": "트리니티 CC", "topic": "초보 골퍼가 트리니티 CC에서 살아남는 방법", "category": "팁"},
    {"club": "트리니티 CC", "topic": "트리니티 주변 프리미엄 레스토랑 & 호텔 가이드", "category": "주변정보"},

    # ── 잭니클라우스 GC ───────────────────────────────────────────
    {"club": "잭니클라우스 GC", "topic": "잭 니클라우스 친설계 코스의 의미 — 세계적 골프 설계가의 철학", "category": "히스토리"},
    {"club": "잭니클라우스 GC", "topic": "18홀 완전 전략 가이드 — 설계 의도를 알면 스코어가 달라진다", "category": "코스분석"},
    {"club": "잭니클라우스 GC", "topic": "한국에서 가장 어려운 코스 TOP5 — 잭니클라우스 GC의 순위", "category": "비교분석"},
    {"club": "잭니클라우스 GC", "topic": "멤버십 가격과 등급 체계 — 현재 시세와 투자가치 분석", "category": "멤버십"},
    {"club": "잭니클라우스 GC", "topic": "입회 절차 완전 가이드 — 추천인 시스템과 심사 과정", "category": "멤버십"},
    {"club": "잭니클라우스 GC", "topic": "비회원 그린피 실비용 계산 — 캐디·카트·식사 포함 총액", "category": "예약·비용"},
    {"club": "잭니클라우스 GC", "topic": "예약 경쟁에서 이기는 법 — 비회원도 원하는 날짜 잡는 전략", "category": "예약·비용"},
    {"club": "잭니클라우스 GC", "topic": "캐디 서비스 퀄리티 심층 분석 — 최상급 클럽의 기준은 다르다", "category": "서비스"},
    {"club": "잭니클라우스 GC", "topic": "클럽하우스 다이닝 완전 리뷰 — 음식·서비스·가격 솔직 평가", "category": "부대시설"},
    {"club": "잭니클라우스 GC", "topic": "부대시설 전체 리뷰 — 락커룸·사우나·프로샵 수준 평가", "category": "부대시설"},
    {"club": "잭니클라우스 GC", "topic": "코스 관리의 비밀 — 세계 수준 그린 관리 방법 공개", "category": "코스분석"},
    {"club": "잭니클라우스 GC", "topic": "시그니처 홀 7번 파5 완전 정복 — 버디 확률 높이는 루트", "category": "코스분석"},
    {"club": "잭니클라우스 GC", "topic": "핸디캡별 공략 전략 — 보기 플레이어·싱글 플레이어별 가이드", "category": "팁"},
    {"club": "잭니클라우스 GC", "topic": "최초 라운딩 전 반드시 알아야 할 10가지", "category": "팁"},
    {"club": "잭니클라우스 GC", "topic": "드레스코드 세부 기준 — 잭니클라우스 GC가 가장 까다로운 이유", "category": "에티켓"},
    {"club": "잭니클라우스 GC", "topic": "라운딩 페이스 매너 — 슬로우 플레이 없이 즐기는 법", "category": "에티켓"},
    {"club": "잭니클라우스 GC", "topic": "시즌별 코스 컨디션 리포트 — 봄·여름·가을·겨울 완전 분석", "category": "시즌"},
    {"club": "잭니클라우스 GC", "topic": "가을 황금 시즌 라운딩 가이드 — 연중 가장 아름다운 코스", "category": "시즌"},
    {"club": "잭니클라우스 GC", "topic": "동반자 정책 — 비회원 초청 횟수·조건·주의사항 완전 정리", "category": "규정"},
    {"club": "잭니클라우스 GC", "topic": "법인회원권 활용법 — 기업 골프 접대의 최강 카드", "category": "멤버십"},
    {"club": "잭니클라우스 GC", "topic": "잭니클라우스 GC 10년 후 가치 전망 — 회원권 투자 분석", "category": "멤버십"},
    {"club": "잭니클라우스 GC", "topic": "세계 명문 클럽과 비교 — 오거스타·페블비치와 무엇이 다른가", "category": "비교분석"},
    {"club": "잭니클라우스 GC", "topic": "한국 개최 국제 대회 이력과 코스의 위상", "category": "히스토리"},
    {"club": "잭니클라우스 GC", "topic": "잭 니클라우스가 직접 설명한 이 코스의 설계 의도", "category": "히스토리"},
    {"club": "잭니클라우스 GC", "topic": "실회원이 6개월 사용 후 느낀 솔직한 장단점", "category": "후기"},
    {"club": "잭니클라우스 GC", "topic": "와이프·파트너 동반 시 즐길 수 있는 시설과 프로그램", "category": "부대시설"},
    {"club": "잭니클라우스 GC", "topic": "스카이뷰로 보는 코스 전략 — 드론 시점으로 분석하는 18홀", "category": "코스분석"},
    {"club": "잭니클라우스 GC", "topic": "퍼팅 라인 완전 공개 — 그린 경사 패턴과 공략 루트", "category": "코스분석"},
    {"club": "잭니클라우스 GC", "topic": "연습 시설과 레슨 프로그램 — 회원 전용 클래스 정보", "category": "부대시설"},
    {"club": "잭니클라우스 GC", "topic": "주변 프리미엄 숙박과 다이닝 — 1박2일 골프 여행 완벽 가이드", "category": "주변정보"},

    # ── 3대장 비교 · 심층 분석 ───────────────────────────────────
    {"club": "3대장 비교", "topic": "웰링턴 vs 트리니티 vs 잭니클라우스 — 총체적 비교 분석 2025", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "3대 클럽 그린피 완전 비교 — 어디서 치는 게 가장 합리적인가", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "3대 클럽 멤버십 가성비 비교 — 1억 투자 시 어디가 유리한가", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "코스 난이도 3사 비교 — 싱글 핸디캡 기준 어디가 가장 어려운가", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "클럽하우스 서비스 3사 비교 — 식사·락커·캐디 퀄리티 랭킹", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "접근성 비교 — 수도권 기준 교통·주차·소요시간 완전 정리", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "비즈니스 골프에 가장 적합한 클럽은 어디인가 — 실무자 관점 분석", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "처음 회원권 살 때 어디를 골라야 하나 — 투자 vs 이용 목적별 가이드", "category": "멤버십"},
    {"club": "3대장 비교", "topic": "3대 클럽 코스 컨디션 연간 비교 — 관리 수준 객관적 평가", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "한국 프리미엄 CC 시장 트렌드 — 2025년 명문 클럽의 현주소", "category": "시장분석"},
    {"club": "3대장 비교", "topic": "명문 CC 회원권 거품론 vs 희소가치론 — 전문가 시각 정리", "category": "시장분석"},
    {"club": "3대장 비교", "topic": "40대에 골프 회원권을 사야 하는 7가지 이유", "category": "멤버십"},
    {"club": "3대장 비교", "topic": "50대 은퇴 전 반드시 알아야 할 골프 클럽 선택 기준", "category": "멤버십"},
    {"club": "3대장 비교", "topic": "국내 명문 CC와 해외 골프 원정 — 어디에 돈을 써야 더 행복한가", "category": "비교분석"},
    {"club": "3대장 비교", "topic": "3대 클럽 캐디 팁 문화 비교 — 얼마가 적당한가", "category": "에티켓"},
    {"club": "3대장 비교", "topic": "명문 CC 첫 방문 전 반드시 읽어야 할 완벽 준비 가이드", "category": "팁"},
    {"club": "3대장 비교", "topic": "한국 골프 클럽 등급 체계 이해 — 어떻게 서열이 정해지는가", "category": "시장분석"},
    {"club": "3대장 비교", "topic": "골프 회원권 세금과 법적 이슈 — 증여·매매·취득세 완전 정리", "category": "법률·세금"},
    {"club": "3대장 비교", "topic": "회원권 담보대출 활용법 — 유동성 확보와 리스크 관리", "category": "법률·세금"},
    {"club": "3대장 비교", "topic": "아시아 명문 CC로 확장하기 전 국내 3대장으로 실력 쌓는 법", "category": "팁"},

    # ── 해슬리 나인브릿지 (명문CC, 글 공급 얇음) ──────────────────
    {"club": "해슬리 나인브릿지", "topic": "비회원 예약 가능성과 회원동반 조건 완전 정리", "category": "예약·비용"},
    {"club": "해슬리 나인브릿지", "topic": "그린피·캐디피·카트비 2026 기준 총비용 체크", "category": "예약·비용"},
    {"club": "해슬리 나인브릿지", "topic": "18홀 코스 난이도와 공략 포인트", "category": "코스분석"},
    {"club": "해슬리 나인브릿지", "topic": "클럽하우스 식당과 부대시설 수준 리뷰", "category": "부대시설"},
    {"club": "해슬리 나인브릿지", "topic": "웰링턴 CC vs 해슬리 나인브릿지 — 선택 기준 비교", "category": "비교분석"},
    {"club": "해슬리 나인브릿지", "topic": "법인회원권 활용과 접대 골프 적합성 분석", "category": "멤버십"},
    {"club": "해슬리 나인브릿지", "topic": "첫 방문 전 드레스코드와 동반 규정 총정리", "category": "에티켓"},
    {"club": "해슬리 나인브릿지", "topic": "주차 동선과 수도권 접근성 완전 가이드", "category": "접근성"},

    # ── 아난티클럽서울 (서울 최상위 CC, 정보 극소) ────────────────
    {"club": "아난티클럽서울", "topic": "비회원 예약과 회원동반 조건 — 가장 까다로운 서울 CC", "category": "예약·비용"},
    {"club": "아난티클럽서울", "topic": "그린피와 총비용 — 국내 최고가 CC의 실제 비용 구조", "category": "예약·비용"},
    {"club": "아난티클럽서울", "topic": "18홀 코스 레이아웃과 핵심 공략", "category": "코스분석"},
    {"club": "아난티클럽서울", "topic": "회원권 가격 수준과 멤버십 입회 조건", "category": "멤버십"},
    {"club": "아난티클럽서울", "topic": "클럽하우스·다이닝·부대시설 — 서울 CC 최상위의 실체", "category": "부대시설"},
    {"club": "아난티클럽서울", "topic": "잭니클라우스 GC vs 아난티클럽서울 — 어디가 더 상위인가", "category": "비교분석"},

    # ── 베트남 다낭 골프여행 (수요 급증, 공급 극소) ───────────────
    {"club": "베트남 다낭 골프", "topic": "다낭 골프 패키지 총비용 — 항공·숙박·그린피 포함 실제 계산", "category": "해외여행"},
    {"club": "베트남 다낭 골프", "topic": "다낭 인기 골프장 TOP5 — 한국인이 가장 많이 찾는 코스 비교", "category": "해외여행"},
    {"club": "베트남 다낭 골프", "topic": "다낭 골프 현지 캐디 팁과 에티켓 — 처음 가는 분 필독", "category": "해외여행"},
    {"club": "베트남 다낭 골프", "topic": "다낭 골프 최적 시즌 — 우기·건기 날씨와 방문 타이밍", "category": "해외여행"},
    {"club": "베트남 다낭 골프", "topic": "다낭 골프 + 관광 1박2일 vs 3박4일 — 일정별 비용과 코스 선택", "category": "해외여행"},
    {"club": "베트남 다낭 골프", "topic": "국내 골프장 vs 다낭 골프 — 비용·경험 솔직 비교", "category": "비교분석"},

    # ── 태국 골프여행 ──────────────────────────────────────────
    {"club": "태국 방콕·파타야 골프", "topic": "태국 골프 패키지 총비용 — 그린피·숙박·항공 포함 실비용", "category": "해외여행"},
    {"club": "태국 방콕·파타야 골프", "topic": "방콕 vs 파타야 골프 — 코스 수준과 비용 비교", "category": "해외여행"},
    {"club": "태국 방콕·파타야 골프", "topic": "태국 골프장 예약 방법과 현지 팁 — 한국인 완전 가이드", "category": "해외여행"},
    {"club": "태국 방콕·파타야 골프", "topic": "태국 골프 vs 베트남 골프 — 한국인 선호도 비교 2026", "category": "비교분석"},
    {"club": "태국 방콕·파타야 골프", "topic": "태국 캐디 문화와 팁 기준 — 처음 방문자 필수 체크리스트", "category": "해외여행"},

    # ── 일본 골프여행 ──────────────────────────────────────────
    {"club": "일본 이바라키·규슈 골프", "topic": "일본 골프 패키지 — 이바라키·규슈 총비용과 추천 코스", "category": "해외여행"},
    {"club": "일본 이바라키·규슈 골프", "topic": "일본 vs 동남아 골프 — 한국인 관점 비용·경험 비교", "category": "비교분석"},
    {"club": "일본 이바라키·규슈 골프", "topic": "일본 골프장 예약 방법 — 언어 장벽 없이 예약하는 법", "category": "해외여행"},
    {"club": "일본 이바라키·규슈 골프", "topic": "규슈 골프 코스 TOP5 — 한국인이 선호하는 이유", "category": "해외여행"},

    # ── 해외 골프여행 보험·수하물·준비물 ───────────────────────
    {"club": "해외 골프여행 보험", "topic": "골프 여행자보험 예상 보험료와 보장 항목 — 골프채 파손·휴대품손해 체크", "category": "보험·수하물"},
    {"club": "해외 골프여행 보험", "topic": "해외 골프 중 상해·배상책임·항공기 지연 보장 확인 기준", "category": "보험·수하물"},
    {"club": "해외 골프여행 수하물", "topic": "골프백 위탁수하물 규정과 초과요금 예상 — 항공권 예약 전 체크", "category": "보험·수하물"},
    {"club": "해외 골프여행 준비", "topic": "해외 라운딩 준비물 체크리스트 — 거리측정기·골프화·우비·어댑터", "category": "여행준비"},
    {"club": "해외 골프여행 준비", "topic": "골프 패키지 포함·불포함 항목 — 송영·캐디팁·식사비 예상 비용표", "category": "해외여행"},

    # ── 2026 정책·규칙 (검색 폭증) ────────────────────────────
    {"club": "골프 제도·규칙", "topic": "2026 골프 규칙 핵심 변경사항 — 아마추어 골퍼가 꼭 알아야 할 6가지", "category": "정책·제도"},
    {"club": "골프 제도·규칙", "topic": "노캐디제 골프장 목록 2026 — 수도권 중심 완전 정리", "category": "정책·제도"},
    {"club": "골프 제도·규칙", "topic": "캐디 선택제 도입 골프장 현황과 비용 절감 효과", "category": "정책·제도"},
    {"club": "골프 제도·규칙", "topic": "골프장 개별소비세 구조와 그린피 가격 영향 분석", "category": "정책·제도"},
    {"club": "골프 제도·규칙", "topic": "LIV 골프 2026 부산 개최 — 일정·관람·티켓 정보 정리", "category": "정책·제도"},
    {"club": "골프 제도·규칙", "topic": "비회원제 골프장 제도 — 그린피 규제와 선택 방법", "category": "정책·제도"},

    # ── 가성비·공공골프장 ──────────────────────────────────────
    {"club": "공공·가성비 골프장", "topic": "수도권 공공골프장 그린피 비교 2026 — 가장 저렴하게 치는 법", "category": "가성비"},
    {"club": "공공·가성비 골프장", "topic": "경기도 비회원제 골프장 목록과 예약 방법 완전 정리", "category": "가성비"},
    {"club": "공공·가성비 골프장", "topic": "평일 주중 저렴한 골프 방법 — 타임 활용과 야간 라운딩", "category": "가성비"},
    {"club": "공공·가성비 골프장", "topic": "회원제 vs 비회원제 골프장 — 어떤 게 더 유리한가", "category": "비교분석"},
    {"club": "공공·가성비 골프장", "topic": "1인당 10만원대 수도권 골프장 TOP10 — 2026 최신 기준", "category": "가성비"},

    # ── 여성·입문 골퍼 ──────────────────────────────────────────
    {"club": "여성·입문 골퍼", "topic": "여성 골프 입문 비용 완전 정리 — 레슨·장비·필드 데뷔까지 총액", "category": "입문·여성"},
    {"club": "여성·입문 골퍼", "topic": "30·40대 여성 골퍼가 고르는 입문 드라이버 추천 2026", "category": "입문·여성"},
    {"club": "여성·입문 골퍼", "topic": "골프 레슨 vs 독학 — 어떤 게 빠르고 저렴한가", "category": "입문·여성"},
    {"club": "여성·입문 골퍼", "topic": "처음 필드 나가기 전 준비물과 에티켓 체크리스트", "category": "입문·여성"},
    {"club": "여성·입문 골퍼", "topic": "스크린골프장 vs 실외 연습장 vs 필드 — 입문 루트 비교", "category": "입문·여성"},

    # ── 용품·앱 (높은 CPC) ─────────────────────────────────────
    {"club": "골프 용품·앱", "topic": "골프 거리측정기 추천 2026 — 레이저 vs GPS 실사용 비교", "category": "용품·기술"},
    {"club": "골프 용품·앱", "topic": "카카오골프 vs 티샷 vs 스마트스코어 — 예약앱 기능 비교", "category": "용품·기술"},
    {"club": "골프 용품·앱", "topic": "스크린골프 vs 실외 골프 — 비용·실력 향상 효과 솔직 비교", "category": "용품·기술"},
    {"club": "골프 용품·앱", "topic": "골프 GPS 워치 추천 2026 — 10만원대 vs 30만원대 비교", "category": "용품·기술"},
]


GOLF_DOMESTIC_CLUBS = (
    "웰링턴 CC",
    "트리니티 CC",
    "잭니클라우스 GC",
    "해슬리 나인브릿지",
    "아난티클럽서울",
    "클럽 나인브릿지",
)

GOLF_OVERSEAS_DESTINATIONS = (
    "베트남 다낭 골프",
    "태국 방콕·파타야 골프",
    "일본 이바라키·규슈 골프",
    "필리핀 클락·세부 골프",
    "말레이시아 조호르·코타키나발루 골프",
    "괌·사이판 골프",
    "해외 골프여행 보험",
    "해외 골프여행 수하물",
    "해외 골프여행 준비",
)

GOLF_CORE_CLUBS = GOLF_DOMESTIC_CLUBS + GOLF_OVERSEAS_DESTINATIONS

GOLF_TOPIC_PILLARS: list[tuple[str, str]] = [
    # 공개 SERP 확인 기준: 검색 수요는 크지만 프리미엄 구장 세부 정보가 얇은 키워드군 우선
    ("예약·비용", "비회원 예약 가능성과 회원동반 조건"),
    ("예약·비용", "그린피·캐디피·카트비 총비용 체크"),
    ("예약·비용", "주중·주말 예약 난이도와 부킹 전략"),
    ("예약·비용", "성수기·비수기 비용 차이와 방문 타이밍"),

    ("멤버십", "회원권 매수 전 체크포인트"),
    ("멤버십", "법인회원권 활용과 접대 골프 전략"),
    ("멤버십", "정회원·법인회원·동반자 혜택 비교"),
    ("멤버십", "프라이빗 회원제 골프장 입장 조건"),

    ("코스분석", "18홀 코스 공략과 난이도 분석"),
    ("코스분석", "티샷 랜딩존과 세컨드 샷 의사결정"),
    ("코스분석", "그린 스피드와 퍼팅 라인 공략"),
    ("코스분석", "벙커·해저드·러프 리스크 관리"),

    ("비교분석", "웰링턴·트리니티·잭니클라우스 비교"),
    ("비교분석", "국내 명문 골프장 순위와 선택 기준"),
    ("비교분석", "수도권 프리미엄 골프장 비교"),
    ("비교분석", "상위 1% 골퍼 관점의 명문 코스 검토"),

    ("부대시설", "클럽하우스 식당과 다이닝 동선"),
    ("부대시설", "락커·사우나·프로샵 시설 체크"),
    ("서비스", "캐디 서비스와 라운딩 운영 품질"),
    ("접근성", "수도권 접근성과 주차 동선"),
    ("에티켓", "첫 방문 드레스코드와 동반 라운딩 매너"),
    ("주변정보", "1박 2일 골프 여행 숙소와 맛집"),

    # ── 2026 신규 블루오션 ──
    ("해외여행", "그린피·숙박·항공 포함 총비용과 코스 선택 가이드"),
    ("해외여행", "한국인 골퍼 선호 코스와 현지 예약 방법"),
    ("해외여행", "동반 골퍼 구성과 투어 패키지 비교"),
    ("해외여행", "현지 캐디 문화·팁·에티켓 완전 정리"),
    ("해외여행", "3박5일·4박6일 일정별 예상 비용표"),
    ("해외여행", "패키지 포함·불포함 항목과 현지 추가비 체크"),
    ("보험·수하물", "해외 골프여행 여행자보험 보장 항목과 예상 보험료"),
    ("보험·수하물", "골프백 위탁수하물 규정과 초과요금 예상 체크"),
    ("보험·수하물", "골프채 파손·휴대품손해·배상책임 보장 확인"),
    ("여행준비", "해외 골프여행 준비물과 장비·앱 체크리스트"),
    ("여행준비", "항공권·숙박·송영·환전 예약 전 확인 순서"),

    ("정책·제도", "노캐디제·캐디선택제 도입 골프장 현황"),
    ("정책·제도", "골프 개별소비세 구조와 그린피 영향 분석"),
    ("정책·제도", "2026 골프 규칙 변경 핵심 정리"),

    ("용품·기술", "거리측정기 추천과 선택 기준"),
    ("용품·기술", "스크린골프 vs 필드 비용·효과 비교"),
    ("용품·기술", "골프 예약앱 비교 — 카카오골프·티샷·스마트스코어"),

    ("입문·여성", "여성 골퍼 입문 비용과 레슨 선택 가이드"),
    ("입문·여성", "MZ세대 골퍼를 위한 첫 라운딩 준비"),
    ("가성비", "수도권 공공골프장 그린피 비교와 예약법"),
    ("가성비", "평일 저렴하게 치는 법 — 비회원제 골프장 활용"),
]

GOLF_READER_SEGMENTS = (
    # 검색 수요 + 구매력 + 프리미엄 포지션이 동시에 있는 독자군
    "40대 법인대표",
    "50대 프리미엄 골퍼",
    "회원권 첫 매수 검토자",
    "비회원 라운딩 준비자",
    "법인 접대 골프 담당자",
    "수도권 프리미엄 골퍼",
    "골프 모임 총무",
)

GOLF_CONTEXTS = (
    # 검색자가 실제로 붙여 검색할 가능성이 높은 상황 키워드
    "최신 기준",
    "주말 라운딩 전",
    "평일 1부 예약 전",
    "성수기 방문 전",
    "비수기 방문 전",
    "첫 방문 전",
    "법인 라운드 전",
    "항공권 예약 전",
    "여행자보험 가입 전",
    "골프백 위탁 전",
)

GOLF_ANGLES = (
    # 반복 제목을 줄이기 위한 고의도 롱테일 각도
    "체크리스트",
    "총비용 분석",
    "예약 전 확인사항",
    "비용 대비 만족도 분석",
    "실패하지 않는 준비법",
    "명문 골프장 비교 기준",
    "상위 1% 골퍼 관점",
    "예상 비용표",
    "포함·불포함 항목",
    "보험·수하물 체크",
)

GOLF_TOPIC_TARGET_COUNT = 800

GOLF_HIGH_INTENT_KEYWORDS = (
    # 1차 수요 키워드: 검색자가 실제로 많이 찾는 정보형 조합
    "그린피",
    "캐디피",
    "카트비",
    "총비용",
    "비용",
    "예약",
    "부킹",
    "예약방법",
    "예약 난이도",
    "비회원",
    "회원동반",
    "회원 동반",
    "동반 라운딩",

    # 프리미엄/법인 타깃 키워드: 정보는 적지만 구매력과 클릭 의도가 높은 조합
    "회원권",
    "법인회원",
    "법인 회원권",
    "정회원",
    "매수",
    "체크포인트",
    "법인 골프",
    "접대 골프",
    "비즈니스 골프",
    "대표",
    "VIP",
    "프리미엄",
    "프라이빗",
    "하이엔드",

    # 코스 공략 키워드: 체류시간이 길어지는 실전형 조합
    "코스",
    "18홀",
    "홀별",
    "홀별 공략",
    "공략",
    "난이도",
    "티샷",
    "랜딩존",
    "세컨드 샷",
    "그린",
    "그린 스피드",
    "퍼팅",
    "벙커",
    "해저드",
    "러프",

    # 비교/순위 키워드: 상위노출용 정보 탐색형 조합
    "명문",
    "명문 골프장",
    "국내 명문",
    "순위",
    "비교",
    "수도권 골프장",
    "고급 골프장",

    # 시설/동선 키워드: 프리미엄 구장인데 세부 정보가 상대적으로 약한 조합
    "클럽하우스",
    "식당",
    "다이닝",
    "락커",
    "사우나",
    "프로샵",
    "주차",
    "접근성",
    "동선",
    "드레스코드",
    "첫 방문",

    # 시즌/여행 키워드: 검색 유입 보조 키워드
    "시즌",
    "성수기",
    "비수기",
    "겨울",
    "여름",
    "봄",
    "가을",
    "1박 2일",
    "숙소",
    "맛집",

    # 해외 골프여행 (62% 수요 급증)
    "해외 골프여행",
    "베트남 골프",
    "다낭 골프",
    "태국 골프",
    "일본 골프",
    "골프 패키지",
    "동남아 골프",
    "해외 골프 총비용",
    "현지 캐디",
    "캐디팁",
    "송영",
    "항공권",
    "골프백 수하물",
    "위탁수하물",
    "초과수하물",
    "여행자보험",
    "골프 여행자보험",
    "골프보험",
    "휴대품손해",
    "배상책임",
    "항공기 지연",
    "골프채 파손",
    "환전",
    "우기",

    # 2026 정책·규칙 (검색 폭증)
    "2026 골프 규칙",
    "노캐디제",
    "캐디선택제",
    "캐디 선택",
    "개별소비세",
    "LIV 골프",
    "LIV 골프 부산",

    # 용품·앱 (높은 CPC)
    "거리측정기",
    "거리측정기 추천",
    "카카오골프",
    "스마트스코어",
    "티샷 예약",
    "골프 예약앱",

    # 입문·여성·가성비 (신규 세그먼트)
    "여성 골퍼",
    "골프 입문",
    "공공골프장",
    "비회원제 골프장",
    "가성비 골프장",
    "스크린골프",
)

GOLF_LOW_INTENT_EXCLUDE_KEYWORDS = (
    "상위 1%",
    "회원만 아는",
    "비공개",
    "실회원이 공개",
    "와이프",
    "파트너",
    "숨겨진",
    "최악의 홀",
)


def _golf_topic_priority_score(item: dict) -> int:
    """
    주제 우선순위를 계산합니다.
    실제 검색량 API를 쓰는 것은 아니므로, 네이버·구글에서 검색 의도가 강한
    골프장 정보형 키워드군을 기준으로 내부 점수를 매깁니다.
    """
    club = str(item.get("club", ""))
    topic = str(item.get("topic", ""))
    category = str(item.get("category", ""))
    target = f"{club} {topic} {category}"

    score = 0

    # 골프장명 자체는 핵심 검색 키워드입니다.
    if club in GOLF_CORE_CLUBS:
        score += 15
    elif club == "3대장 비교":
        score += 12

    # 검색 의도가 강한 키워드일수록 우선 유지합니다.
    for keyword in GOLF_HIGH_INTENT_KEYWORDS:
        if keyword in target:
            score += 4

    # 돈/예약/회원권/코스 공략은 전환율과 체류시간이 높은 축입니다.
    for keyword in ("그린피", "예약", "부킹", "비용", "회원권", "비회원", "코스", "공략", "비교"):
        if keyword in target:
            score += 8

    # 너무 자극적이거나 검색 의도가 좁은 표현은 감점합니다.
    for keyword in GOLF_LOW_INTENT_EXCLUDE_KEYWORDS:
        if keyword in target:
            score -= 20

    # 데이터 갭 가중치: 수요 신호는 큰데 프리미엄 구장별 정리 글이 상대적으로 얇은 조합
    gap_keyword_weights = {
        "비회원 예약": 18,
        "회원동반": 18,
        "회원 동반": 18,
        "법인회원권": 20,
        "법인 골프": 20,
        "접대 골프": 20,
        "총비용": 18,
        "그린피": 12,
        "캐디피": 10,
        "카트비": 10,
        "예약 난이도": 16,
        "클럽하우스 식당": 14,
        "락커": 10,
        "사우나": 10,
        "주차 동선": 12,
        "첫 방문": 12,
        "세컨드 샷": 14,
        "그린 스피드": 14,
        "상위 1% 골퍼": 10,
    }
    for keyword, weight in gap_keyword_weights.items():
        if keyword in target:
            score += weight

    return score


def _build_expanded_golf_topics(seed_topics: list[dict], limit: int = GOLF_TOPIC_TARGET_COUNT) -> list[dict]:
    """
    골프 주제 풀을 500개로 제한합니다.

    기존 5400개 조합은 너무 세분화되어 제목·본문·이미지가 서로 비슷해질 수 있으므로,
    검색 의도가 강한 키워드군(그린피, 예약, 회원권, 코스 공략, 명문 골프장 비교,
    클럽하우스, 주차, 계절별 컨디션) 중심으로만 확장합니다.
    """
    topics: list[dict] = []
    seen: set[str] = set()
    overseas_categories = {"해외여행", "보험·수하물", "여행준비"}
    domestic_only_categories = {"멤버십", "부대시설", "서비스", "접근성", "에티켓"}

    def is_overseas_club(club: str) -> bool:
        return club in GOLF_OVERSEAS_DESTINATIONS

    def add_topic(club: str, topic: str, category: str) -> None:
        if len(topics) >= limit:
            return
        if category in overseas_categories and not is_overseas_club(club):
            return
        if category in domestic_only_categories and is_overseas_club(club):
            return
        key = f"{club}|{topic}"
        if key in seen:
            return
        candidate = {"club": club, "topic": topic, "category": category}
        if _golf_topic_priority_score(candidate) < 8:
            return
        seen.add(key)
        topics.append(candidate)

    # 기존 수동 주제도 모두 살리지 않고, 검색 의도가 강한 것만 우선 유지합니다.
    ranked_seed_topics = sorted(
        seed_topics,
        key=lambda item: _golf_topic_priority_score(item),
        reverse=True,
    )
    for item in ranked_seed_topics:
        add_topic(item["club"], item["topic"], item["category"])

    # 검색형 제목에 가까운 조합을 우선 생성합니다.
    for club in GOLF_CORE_CLUBS:
        for category, pillar in GOLF_TOPIC_PILLARS:
            for context in GOLF_CONTEXTS:
                for angle in GOLF_ANGLES:
                    topic = f"{context} {pillar} — {angle}"
                    add_topic(club, topic, category)

    # 독자군이 필요한 주제는 마지막에 제한적으로 추가합니다.
    for club in GOLF_CORE_CLUBS:
        for category, pillar in GOLF_TOPIC_PILLARS:
            for reader in GOLF_READER_SEGMENTS:
                for angle in ("체크리스트", "비용 대비 만족도 분석", "예약 전 확인사항"):
                    topic = f"{pillar} — {reader}를 위한 {angle}"
                    add_topic(club, topic, category)

    # 3대장 비교 키워드는 별도 검색 유입 가능성이 있어 일부 유지합니다.
    comparison_topics = [
        ("3대장 비교", "웰링턴 CC 트리니티 CC 잭니클라우스 GC 그린피·예약·회원권 비교", "비교분석"),
        ("3대장 비교", "국내 명문 골프장 순위 기준과 3대 프리미엄 CC 비교", "비교분석"),
        ("3대장 비교", "수도권 명문 골프장 접근성·주차·클럽하우스 비교", "비교분석"),
        ("3대장 비교", "법인 접대 골프장 선택 기준과 3대장 비교", "비교분석"),
        ("3대장 비교", "회원권 첫 매수 전 웰링턴·트리니티·잭니클라우스 비교", "멤버십"),
    ]
    for club, topic, category in comparison_topics:
        add_topic(club, topic, category)

    # 혹시 500개 미만이면 핵심 키워드 조합으로 채웁니다.
    fallback_contexts = ("최신", "주말", "평일", "성수기", "비수기")
    fallback_pillars = (
        ("예약·비용", "그린피 예약 비용"),
        ("멤버십", "회원권 매수 체크포인트"),
        ("코스분석", "코스 공략 난이도"),
        ("비교분석", "명문 골프장 비교"),
        ("부대시설", "클럽하우스 식당 락커"),
    )
    fallback_angles = ("완전 정리", "방문 전 체크", "실전 가이드", "비교 분석", "주의사항")
    for club in GOLF_CORE_CLUBS:
        for context in fallback_contexts:
            for category, pillar in fallback_pillars:
                for angle in fallback_angles:
                    topic = f"{context} {pillar} — {angle}"
                    add_topic(club, topic, category)

    return topics[:limit]


GOLF_TOPIC_POOL = _build_expanded_golf_topics(GOLF_TOPIC_POOL, limit=GOLF_TOPIC_TARGET_COUNT)
print(f"[골프 주제 풀] 검색 의도 중심 {len(GOLF_TOPIC_POOL)}개 주제로 제한")


# ------------------------------------------------------------------
# 골프 주제 로테이션 시스템
# ------------------------------------------------------------------

def _load_used_golf_topics() -> list[str]:
    """이미 사용된 주제 키를 로드합니다."""
    if not GOLF_TOPIC_LOG_PATH.exists():
        return []
    try:
        return json.loads(GOLF_TOPIC_LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_used_golf_topic(topic_key: str) -> None:
    """사용된 주제 키를 저장합니다."""
    GOLF_TOPIC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    used = _load_used_golf_topics()
    if topic_key not in used:
        used.append(topic_key)
    GOLF_TOPIC_LOG_PATH.write_text(json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_golf_topic_performance_rows() -> list[dict]:
    if not GOLF_TOPIC_PERFORMANCE_CSV_PATH.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with GOLF_TOPIC_PERFORMANCE_CSV_PATH.open("r", newline="", encoding=enc) as f:
                rows = [row for row in csv.DictReader(f) if any((value or "").strip() for value in row.values())]
            print(f"[골프 주제 성과 CSV] 로드 완료: {GOLF_TOPIC_PERFORMANCE_CSV_PATH} ({len(rows)}행)")
            return rows
        except UnicodeDecodeError:
            continue
    with GOLF_TOPIC_PERFORMANCE_CSV_PATH.open("r", newline="", errors="replace") as f:
        rows = [row for row in csv.DictReader(f) if any((value or "").strip() for value in row.values())]
    print(f"[골프 주제 성과 CSV] 대체 인코딩 로드 완료: {GOLF_TOPIC_PERFORMANCE_CSV_PATH} ({len(rows)}행)")
    return rows


def _row_value(row: dict, names: tuple[str, ...], default: str = "") -> str:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _row_number(row: dict, names: tuple[str, ...], default: float = 0.0) -> float:
    value = _row_value(row, names)
    if not value:
        return default
    value = value.replace(",", "").replace("%", "").strip()
    try:
        return float(value)
    except ValueError:
        return default


def _row_list(row: dict, names: tuple[str, ...], fallback: list[str] | None = None) -> list[str]:
    raw = _row_value(row, names)
    if not raw:
        return fallback or []
    return [item.strip() for item in re.split(r"[,/;\n]", raw) if item.strip()]


def _is_disabled_performance_row(row: dict) -> bool:
    status = _row_value(row, ("status", "상태", "enabled", "사용", "exclude", "제외")).lower()
    return status in {"n", "no", "false", "0", "skip", "exclude", "excluded", "used", "사용안함", "제외", "완료"}


def _infer_golf_category_from_query(query: str) -> str:
    overseas_terms = ("해외", "다낭", "베트남", "태국", "방콕", "파타야", "일본", "규슈", "필리핀", "클락", "세부", "괌", "사이판", "동남아")
    insurance_terms = ("보험", "수하물", "골프백", "골프채 파손", "휴대품손해", "항공기 지연")
    equipment_terms = ("거리측정기", "gps", "워치", "앱", "골프화", "준비물", "장비")
    policy_terms = ("규칙", "노캐디", "캐디선택제", "개별소비세", "비회원제", "세금")
    comparison_terms = ("비교", "vs", "순위", "랭킹", "국내 vs 해외")
    lowered = query.lower()
    if any(term in query for term in insurance_terms):
        return "보험·수하물"
    if any(term in query for term in overseas_terms):
        return "해외여행"
    if any(term.lower() in lowered for term in equipment_terms):
        return "용품·기술"
    if any(term in query for term in policy_terms):
        return "정책·제도"
    if any(term.lower() in lowered for term in comparison_terms):
        return "비교분석"
    if any(term in query for term in ("비용", "그린피", "예약", "회원권", "캐디피", "카트비")):
        return "예약·비용"
    return "가성비"


def _infer_golf_club_from_query(query: str) -> str:
    known_terms = (
        "다낭",
        "방콕",
        "파타야",
        "규슈",
        "이바라키",
        "클락",
        "세부",
        "괌",
        "사이판",
        "웰링턴",
        "트리니티",
        "잭니클라우스",
    )
    for term in known_terms:
        if term in query:
            return f"{term} 골프"
    cleaned = re.sub(r"\s+", " ", query).strip()
    return cleaned[:28] if cleaned else "골프"


def _performance_topic_score(row: dict) -> float:
    query = _row_value(row, ("query", "queries", "검색어", "키워드", "main_keyword", "메인키워드", "topic", "주제"))
    clicks = _row_number(row, ("clicks", "클릭수", "클릭"))
    impressions = _row_number(row, ("impressions", "노출수", "노출"))
    ctr = _row_number(row, ("ctr", "CTR"))
    position = _row_number(row, ("position", "avg_position", "average position", "게재순위", "평균 게재순위"), 99.0)
    priority = _row_number(row, ("priority", "우선순위", "score", "점수"))

    intent_terms = ("비용", "총비용", "가격", "그린피", "캐디피", "카트비", "예약", "패키지", "보험", "수하물", "골프백", "비교", "체크", "준비물")
    broad_penalty_terms = ("골프 추천", "골프장 추천", "골프 잘 치는 법", "골프장 순위")
    score = priority * 1000
    score += clicks * 8
    score += impressions * 0.08
    score += ctr * 4
    if position > 0:
        score += max(0, 25 - position) * 2
        if 5 <= position <= 20:
            score += 30
    score += sum(18 for term in intent_terms if term in query)
    score -= sum(50 for term in broad_penalty_terms if term in query)
    return score


def _build_topic_from_performance_row(row: dict) -> dict:
    query = _row_value(row, ("query", "queries", "검색어", "키워드", "main_keyword", "메인키워드", "topic", "주제"))
    if not query:
        raise ValueError("성과 CSV 행에 query/검색어/main_keyword/topic 값이 없습니다.")

    club = _row_value(row, ("club", "골프장", "지역", "destination", "목적지"), _infer_golf_club_from_query(query))
    category = _row_value(row, ("category", "카테고리"), _infer_golf_category_from_query(query))
    topic = _row_value(row, ("topic", "주제", "title_topic", "글주제"))
    if not topic:
        if category == "해외여행":
            topic = f"{query} 3박5일 비용·동선·골프장 후보 확인"
        elif category == "보험·수하물":
            topic = f"{query} 보장 항목·수하물 기준·예상 비용 확인"
        else:
            topic = f"{query} 비용·예약·선택 기준 체크"

    sub_keywords = _row_list(
        row,
        ("sub_keywords", "보조키워드", "related_queries", "연관검색어"),
        [query, category, "비용", "예약", "비교", "확인 기준"],
    )

    return {
        "club": club,
        "topic": topic,
        "category": category,
        "main_keyword": _row_value(row, ("main_keyword", "메인키워드", "query", "검색어", "키워드"), query),
        "sub_keywords": sub_keywords[:8],
        "search_intent": _row_value(row, ("search_intent", "검색의도"), f"{query} 검색자가 비용·예약·준비 기준을 빠르게 판단하려는 의도"),
        "reader_problem": _row_value(row, ("reader_problem", "독자문제"), "정보가 흩어져 있어 실제 비용, 예약 조건, 준비 항목을 한 번에 비교하기 어렵습니다."),
        "promised_answer": _row_value(row, ("promised_answer", "약속답변"), "방문 전 확인할 비용, 예약, 준비 기준을 실행 가능한 체크 항목으로 정리합니다."),
        "adsense_value_reason": _row_value(row, ("adsense_value_reason", "광고가치"), "여행, 숙박, 예약, 보험, 장비 광고와 문맥상 연결되는 결정 직전 검색 주제입니다."),
        "title_angle": _row_value(row, ("title_angle", "제목방향"), "검색어와 비용·예약·준비 체크포인트를 제목에 명확히 드러냅니다."),
        "body_angle": _row_value(row, ("body_angle", "본문방향"), "성과가 확인된 검색어를 중심으로 비용, 예약, 준비, 주의사항 순서로 전개합니다."),
        "image_angle": _row_value(row, ("image_angle", "이미지방향"), "골프여행 또는 라운딩 준비를 떠올릴 수 있는 차분한 정보형 장면"),
        "concrete_points": _row_list(
            row,
            ("concrete_points", "구체포인트"),
            ["예상 총비용", "예약 전 확인 항목", "이동 동선", "골프장 후보", "보험·수하물", "주의할 변동 정보"],
        )[:8],
        "outline_sections": _row_list(
            row,
            ("outline_sections", "소제목"),
            ["먼저 확인할 핵심 기준", "비용 항목별 체크", "예약과 이동 동선", "보험·수하물·준비물", "마지막 판단 기준"],
        )[:6],
        "table_plan": _row_list(
            row,
            ("table_plan", "표계획"),
            ["예상 비용표", "일정표", "예약 확인 항목", "주의 항목"],
        )[:6],
        "checklist_items": _row_list(
            row,
            ("checklist_items", "체크리스트"),
            ["공식 홈페이지 확인", "예약 가능 시간 확인", "그린피·캐디피 확인", "수하물 규정 확인", "보험 보장 항목 확인", "취소 규정 확인"],
        )[:8],
        "risk_notes": _row_list(
            row,
            ("risk_notes", "주의표현"),
            ["가격 단정 금지", "예약 가능 여부 단정 금지", "실제 방문 후기처럼 단정 금지"],
        )[:5],
        "source": "performance_csv",
        "performance_score": round(_performance_topic_score(row), 2),
    }


def pick_golf_topic_from_performance_csv() -> dict | None:
    rows = [row for row in _read_golf_topic_performance_rows() if not _is_disabled_performance_row(row)]
    if not rows:
        return None

    used_keys = set(_load_used_golf_topics())
    candidates = []
    for row in rows:
        try:
            topic = _build_topic_from_performance_row(row)
        except ValueError as exc:
            print(f"[골프 주제 성과 CSV] 행 스킵: {exc}")
            continue
        topic_key = f"{topic['club']}|{topic['topic']}"
        if topic_key in used_keys:
            continue
        candidates.append((_performance_topic_score(row), topic))

    if not candidates:
        print("[골프 주제 성과 CSV] 사용 가능한 미사용 후보가 없어 기존 주제 선택으로 fallback합니다.")
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    topic = candidates[0][1]
    topic_key = f"{topic['club']}|{topic['topic']}"
    _save_used_golf_topic(topic_key)
    save_golf_topic_strategy(topic)
    print(
        f"[골프 주제 성과 CSV] 선택: {topic['club']} — {topic['topic']} "
        f"(score={topic.get('performance_score')})"
    )
    return topic


def pick_golf_topic() -> dict:
    """
    사용하지 않은 주제를 랜덤 선택합니다.
    모든 주제가 소진되면 자동 리셋 후 재시작합니다.
    """
    used_keys = set(_load_used_golf_topics())
    available = [t for t in GOLF_TOPIC_POOL if f"{t['club']}|{t['topic']}" not in used_keys]

    if not available:
        print("[골프 주제] 전체 주제 소진 → 자동 리셋하고 처음부터 재시작합니다.")
        GOLF_TOPIC_LOG_PATH.write_text("[]", encoding="utf-8")
        available = GOLF_TOPIC_POOL[:]

    overseas_available = [
        item for item in available
        if item.get("category") in {"해외여행", "보험·수하물", "여행준비"}
        or any(keyword in f"{item.get('club', '')} {item.get('topic', '')}" for keyword in ("해외", "다낭", "태국", "일본", "동남아", "베트남", "필리핀", "클락", "세부", "말레이시아", "코타키나발루", "괌", "사이판", "여행자보험", "수하물"))
    ]
    if overseas_available and random.random() < 0.90:
        chosen = random.choice(overseas_available)
    else:
        chosen = random.choice(available)
    topic_key = f"{chosen['club']}|{chosen['topic']}"
    _save_used_golf_topic(topic_key)
    remaining = len(available) - 1
    print(f"[골프 주제 선택] {chosen['club']} — {chosen['topic']} (남은 주제: {remaining}개)")
    return chosen


# ------------------------------------------------------------------
# 골프 프롬프트 빌더
# ------------------------------------------------------------------

def _today_korean() -> str:
    now = datetime.now()
    return f"{now.year}년 {now.month}월 {now.day}일"


def _topic_text(topic: dict, key: str, fallback: str = "") -> str:
    value = topic.get(key, fallback)
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or fallback).strip()


def _topic_list(topic: dict, key: str, fallback: list[str] | None = None) -> list[str]:
    value = topic.get(key)
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        items = [item.strip() for item in re.split(r"[,/\n]", value) if item.strip()]
    else:
        items = []
    return items or (fallback or [])


def _format_topic_list(items: list[str], fallback: str = "주제에 맞는 구체 항목") -> str:
    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if not clean_items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in clean_items)


def build_golf_adsense_topic_prompt() -> str:
    used_topics = _load_used_golf_topics()[-50:]
    used_text = "\n".join(f"- {item}" for item in used_topics) if used_topics else "- 아직 기록된 사용 주제가 없습니다."
    today = _today_korean()
    market_focus = random.choice([
        "해외 골프여행",
        "해외 골프여행",
        "해외 골프여행",
        "해외 골프여행",
        "해외 골프여행",
        "해외 골프여행 보험·수하물",
        "해외 골프여행 보험·수하물",
        "해외 골프여행 장비·앱",
        "국내 vs 해외 골프비용 비교",
        "국내 명문 CC",
    ])
    prompt = f"""당신은 골프 전문 티스토리를 애드센스 수익형 미디어로 키우는 편집장입니다.
오늘 날짜는 {today}입니다.
오늘의 시장 범위: {market_focus}

목표:
- 지금 티스토리에 발행할 골프/골프장/골프여행/골프비용/골프용품/골프규칙 관련 정보글 주제 1개를 선정합니다.
- 단순 조회수보다 애드센스 RPM이 붙기 쉬운 "결정 직전 검색"을 우선합니다.
- 검색자가 돈, 예약, 비교, 이동, 숙박, 장비, 레슨, 보험, 멤버십, 규정 중 하나를 해결하려는 주제를 고릅니다.
- 실시간 검색량, CPC, 광고 단가 숫자를 모르면 절대 지어내지 말고 검색 의도와 광고 친화 업종을 근거로 판단합니다.
- 광고 클릭을 유도하는 표현은 금지합니다. 글 자체가 충분히 유용해서 체류시간과 자연 노출 가능성이 생기게 설계합니다.

[국내·해외 랜덤 발행 규칙]
- 오늘의 시장 범위가 "해외 골프여행"이면 반드시 해외 골프여행 주제를 고릅니다.
- 해외 골프여행 주제는 "도시/권역 + 3박5일 또는 4박6일 + 실제 동선 + 골프장 후보 + 예상 비용"이 보이게 선정합니다.
- "해외 골프여행 비용 체크", "패키지 확인사항"처럼 넓고 추상적인 주제만 고르면 실패입니다.
- 오늘의 시장 범위가 "해외 골프여행 보험·수하물"이면 여행자보험, 골프채 파손, 휴대품손해, 배상책임, 골프백 위탁수하물, 초과수하물 중 하나를 중심 주제로 고릅니다.
- 오늘의 시장 범위가 "해외 골프여행 장비·앱"이면 거리측정기, GPS 워치, 골프 예약앱, 번역앱, 환율앱, 여행 준비물 중 하나를 해외 라운딩 맥락으로 고릅니다.
- 오늘의 시장 범위가 "국내 vs 해외 골프비용 비교"이면 국내 골프와 해외 골프를 비용·일정·예약 난이도로 비교하는 주제를 고릅니다.
- 오늘의 시장 범위가 "국내 명문 CC"이면 국내 골프장 주제를 고릅니다. 단, 전체 발행 비중은 국내 10% 이하로 유지합니다.
- 해외 후보는 베트남 다낭, 태국 방콕·파타야, 일본 규슈·이바라키, 동남아 골프 패키지, 해외 골프 총비용, 현지 캐디·팁, 항공·숙박·그린피 비교를 우선합니다.
- 해외 글도 막연한 여행기가 아니라 총비용, 예약 방법, 최적 시즌, 패키지 비교, 현지 에티켓처럼 검색자가 결정 직전에 찾는 정보로 구성합니다.
- 국내 주제는 10% 보조축입니다. 해외 골프여행, 보험, 수하물, 항공, 숙박, 장비, 앱을 메인축으로 봅니다.
- 해외 일정형 주제의 concrete_points에는 공항→호텔, 호텔→골프장, 골프장→식당/관광지, 예상 이동시간, 예상 교통비, 라운딩 비용, 추천 티오프 시간대를 반드시 포함합니다.
- 해외 일정형 주제의 table_plan에는 "3박5일 시간대별 일정표"와 "1인 예상 총비용표"가 들어가야 합니다.

[최근 사용한 주제]
{used_text}

[수익형 주제 선정 프레임]
1. 수요: 40~60대 골퍼가 실제로 검색창에 칠 법한 롱테일 키워드를 고릅니다.
2. 공급: 이미 흔한 "골프장 추천", "명문 골프장 순위", "골프장 후기"보다 덜 포화된 질문형·비교형·비용형 주제를 고릅니다.
3. 광고 친화도: 여행, 숙박, 예약앱, 렌터카, 자동차, 장비, 거리측정기, 골프웨어, 레슨, 보험, 건강관리, 멤버십 광고와 문맥상 연결될 주제를 고릅니다.
4. 체류시간: 독자가 표, 체크리스트, 상황별 판단 기준을 읽어야 결론이 나는 주제를 고릅니다.
5. 신뢰성: 공식 확인이 필요한 가격·규정·시세는 단정하지 않고 확인 항목으로 설계합니다.
6. 반복 회피: 최근 사용 주제와 같은 골프장, 같은 문제, 같은 제목 각도는 피합니다.

[주제 포맷 다양화]
매번 아래 포맷 중 하나를 골라 body_angle과 outline_sections에 반영합니다. 최근 주제와 같은 포맷을 반복하지 마세요.
- 비용분해형: 총비용, 그린피, 캐디피, 카트비, 식사비, 취소 수수료를 나눠 판단
- 예약전략형: 비회원 예약, 회원동반, 예약앱, 전화 예약, 취소 규정 확인
- 비교판단형: 국내 vs 해외, 퍼블릭 vs 회원제, 평일 vs 주말, 노캐디 vs 캐디
- 실수방지형: 처음 가는 사람이 놓치는 준비물, 복장, 동선, 결제, 시간 관리
- 일정설계형: 1박 2일, 새벽 라운딩, 가족 동반, 접대 골프, 골프여행 루트
- 장비선택형: 거리측정기, GPS 워치, 골프화, 우천 준비물, 라운딩 가방 구성
- 규정해설형: 골프 규칙, 노캐디제, 캐디선택제, 비회원제, 세금·요금 변화
- 지역탐색형: 수도권, 강원, 제주, 일본, 동남아 등 이동 시간과 비용 비교

[구체성 기준]
- 주제는 누가, 언제, 무엇을 확인해야 하는지가 보여야 합니다.
- 본문에서 다룰 비용 항목, 비교 기준, 체크리스트 항목, 공식 확인 위치를 미리 지정합니다.
- "좋은", "편리한", "많은", "다양한", "합리적인" 같은 애매한 표현만으로 설명하지 않습니다.
- 가격이나 규정처럼 변동되는 정보는 "공식 홈페이지/예약처에서 확인할 항목"으로 구체화합니다.
- "월 얼마 벌 수 있다", "무조건 상위노출", "광고 클릭률"처럼 독자에게 보이면 신뢰를 해치는 표현은 본문 전략에 넣지 않습니다.

[오늘 피해야 할 주제]
- 너무 넓은 주제: 골프 추천, 골프장 추천, 골프 잘 치는 법, 골프장 순위
- 해외여행에서 너무 넓은 주제: 해외 골프여행 체크리스트, 비용 확인사항, 패키지 고르는 법처럼 도시·일정·동선·골프장명이 없는 주제
- 검증 불가 주제: 실제 회원권 시세 단정, 내부자 예약 루트, 비공개 정보, 직접 방문 후기 가장
- 광고만 노린 주제: 제품 구매 유도만 있는 글, 특정 앱 가입 유도 글
- 제목이 매번 비슷해지는 주제: "완전 정리", "총정리", "가이드"만으로 설명되는 주제

아래 JSON 하나만 출력하세요. 코드블록, 설명문, 마크다운은 출력하지 마세요.

{{
  "club": "골프장명 또는 키워드 묶음",
  "topic": "30~70자 사이의 구체적인 글 주제",
  "category": "해외여행|보험·수하물|여행준비|비교분석|용품·기술|예약·비용|코스분석|정책·제도|입문·여성|가성비 중 하나",
  "main_keyword": "검색자가 그대로 입력할 핵심 키워드",
  "sub_keywords": ["보조 키워드 1", "보조 키워드 2", "보조 키워드 3", "보조 키워드 4", "보조 키워드 5", "보조 키워드 6"],
  "search_intent": "검색자가 이 글에서 얻고 싶은 결론을 한 문장으로 명확히 작성",
  "reader_problem": "독자가 실제로 헷갈리는 문제를 한 문장으로 작성",
  "promised_answer": "글이 끝났을 때 독자가 가져갈 구체적인 답을 한 문장으로 작성",
  "adsense_value_reason": "광고 수익 가능성이 있는 이유를 광고 업종과 연결해서 작성",
  "title_angle": "클릭을 유도할 제목 방향을 구체적으로 작성",
  "body_angle": "본문을 어떤 판단 기준으로 전개할지 작성",
  "image_angle": "대표 이미지가 보여줘야 할 장면을 구체적으로 작성",
  "concrete_points": ["본문에서 반드시 답할 구체 포인트 1", "본문에서 반드시 답할 구체 포인트 2", "본문에서 반드시 답할 구체 포인트 3", "본문에서 반드시 답할 구체 포인트 4", "본문에서 반드시 답할 구체 포인트 5", "본문에서 반드시 답할 구체 포인트 6"],
  "outline_sections": ["소제목 1", "소제목 2", "소제목 3", "소제목 4", "소제목 5"],
  "table_plan": ["표 행 1", "표 행 2", "표 행 3", "표 행 4"],
  "checklist_items": ["체크리스트 1", "체크리스트 2", "체크리스트 3", "체크리스트 4", "체크리스트 5", "체크리스트 6"],
  "risk_notes": ["주의 표현 1", "주의 표현 2", "주의 표현 3"]
}}"""
    _assert_prompt_text_clean(prompt, "골프 수익형 주제 선정")
    return prompt


def parse_golf_adsense_topic(topic_text: str) -> dict:
    cleaned = clean_generated_text(topic_text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("수익형 주제 JSON을 찾지 못했습니다.")
        data = json.loads(match.group(0))

    required_text_fields = [
        "club",
        "topic",
        "category",
        "main_keyword",
        "search_intent",
        "reader_problem",
        "promised_answer",
        "adsense_value_reason",
        "title_angle",
        "body_angle",
        "image_angle",
    ]
    for key in required_text_fields:
        if not str(data.get(key, "")).strip():
            raise ValueError(f"수익형 주제 필드 누락: {key}")

    normalized = {key: str(data.get(key, "")).strip() for key in required_text_fields}
    list_fields = {
        "sub_keywords": 5,
        "concrete_points": 4,
        "outline_sections": 4,
        "table_plan": 3,
        "checklist_items": 4,
        "risk_notes": 2,
    }
    for key, minimum in list_fields.items():
        values = _topic_list(data, key)
        if len(values) < minimum:
            raise ValueError(f"수익형 주제 리스트 필드가 부족합니다: {key}")
        normalized[key] = values
    return normalized


def save_golf_topic_strategy(topic: dict) -> None:
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    GOLF_TOPIC_STRATEGY_PATH.write_text(json.dumps(topic, ensure_ascii=False, indent=2), encoding="utf-8")


def build_fallback_adsense_topic() -> dict:
    base = pick_golf_topic()
    club = base["club"]
    subject = base["topic"]
    category = base["category"]
    main_keyword = f"{club} {subject.split('—', 1)[0].strip()}"
    return {
        "club": club,
        "topic": subject,
        "category": category,
        "main_keyword": main_keyword,
        "sub_keywords": [club, category, "그린피", "예약", "비용", "방문 전 확인"],
        "search_intent": f"{main_keyword} 정보를 방문 전 빠르게 판단하려는 검색 의도",
        "reader_problem": "예약, 비용, 동반 조건, 코스 정보가 흩어져 있어 무엇부터 확인해야 할지 모르는 상황",
        "promised_answer": "방문 전 확인할 비용 항목과 예약 판단 기준을 한 번에 정리합니다.",
        "adsense_value_reason": "골프 예약, 여행, 장비, 숙박, 레슨 광고와 연결될 수 있는 정보형 검색 주제입니다.",
        "title_angle": "방문 전 확인해야 할 비용과 예약 기준을 제목에 명확히 드러냅니다.",
        "body_angle": "비용, 예약, 시설, 주의사항 순서로 독자가 바로 판단할 수 있게 전개합니다.",
        "image_angle": "골프장 방문 전 비용과 예약을 떠올릴 수 있는 차분한 코스 또는 클럽하우스 장면",
        "concrete_points": ["예약 전 확인 항목", "그린피·캐디피·카트비 구분", "회원동반 여부", "취소 규정", "주차 동선", "방문 전 체크리스트"],
        "outline_sections": ["예약 전 확인할 핵심 기준", "비용 항목별 체크 방법", "방문 당일 동선과 준비물", "공식 확인이 필요한 정보", "마지막 판단 기준"],
        "table_plan": ["예약 항목", "비용 항목", "시설 항목", "주의 항목"],
        "checklist_items": ["공식 홈페이지 확인", "예약 가능 시간 확인", "그린피 확인", "캐디피·카트비 확인", "취소 규정 확인", "동반자 조건 확인"],
        "risk_notes": ["가격 단정 금지", "비공개 정보처럼 보이는 표현 금지", "실제 방문 후기처럼 단정 금지"],
    }


def select_golf_adsense_topic(driver: webdriver.Chrome) -> dict:
    performance_topic = pick_golf_topic_from_performance_csv()
    if performance_topic:
        return performance_topic

    prompt = build_golf_adsense_topic_prompt()
    archive_prompt("golf_topic_strategy_prompt", prompt)
    print("[STEP 0/5] 애드센스 수익형 주제 선정 중...")
    try:
        topic_text = send_text_prompt(driver, prompt, timeout=240)
        log_run("golf_topic_strategy", prompt)
        archive_prompt("golf_topic_strategy_response", topic_text)
        topic = parse_golf_adsense_topic(topic_text)
        topic_key = f"{topic['club']}|{topic['topic']}"
        _save_used_golf_topic(topic_key)
        save_golf_topic_strategy(topic)
        print(f"[수익형 주제 선택] {topic['club']} — {topic['topic']}")
        return topic
    except Exception as exc:
        print(f"[경고] 수익형 주제 선정 실패: {exc} — 기존 주제 로테이션으로 대체합니다.")
        topic = build_fallback_adsense_topic()
        save_golf_topic_strategy(topic)
        return topic


def _is_overseas_golf_topic(topic: dict) -> bool:
    joined = " ".join(
        str(topic.get(key, ""))
        for key in ("club", "topic", "category", "main_keyword", "search_intent", "body_angle")
    )
    return (
        str(topic.get("category", "")).strip() in {"해외여행", "보험·수하물", "여행준비"}
        or any(
            keyword in joined
            for keyword in (
                "해외",
                "다낭",
                "베트남",
                "태국",
                "방콕",
                "파타야",
                "일본",
                "규슈",
                "이바라키",
                "필리핀",
                "클락",
                "세부",
                "말레이시아",
                "코타키나발루",
                "괌",
                "사이판",
                "여행자보험",
                "골프백",
                "수하물",
            )
        )
    )


def _is_overseas_itinerary_topic(topic: dict) -> bool:
    if not _is_overseas_golf_topic(topic):
        return False
    category = str(topic.get("category", "")).strip()
    joined = " ".join(
        str(topic.get(key, ""))
        for key in ("club", "topic", "main_keyword", "search_intent", "body_angle")
    )
    if category == "해외여행":
        return True
    return any(keyword in joined for keyword in ("3박", "4박", "패키지", "총비용", "일정", "동선", "여행"))


def _strip_html_to_text(html_text: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text or "", flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _count_money_patterns(text: str) -> int:
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    suffix = r"(?:만\s*원|만원|원|바트|동|엔|달러|불|THB|VND|JPY|USD|KRW)"
    prefix = r"(?:US\$|USD|KRW|THB|VND|JPY|₩|\$)"
    patterns = [
        rf"(?:약|예상|대략|범위|1인\s*기준|1회\s*기준|3박5일\s*기준)?\s*{number}\s*{suffix}",
        rf"(?:약|예상|대략|범위|1인\s*기준|1회\s*기준|3박5일\s*기준)?\s*{prefix}\s*{number}",
    ]
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def build_golf_research_brief_prompt(topic: dict) -> str:
    club = topic["club"]
    subject = topic["topic"]
    category = topic["category"]
    today = _today_korean()
    main_keyword = _topic_text(topic, "main_keyword", f"{club} {subject}")
    search_intent = _topic_text(topic, "search_intent", "검색자가 실제 일정과 비용을 판단하려는 의도")
    concrete_points_text = _format_topic_list(_topic_list(topic, "concrete_points"))
    checklist_items_text = _format_topic_list(_topic_list(topic, "checklist_items"))

    itinerary_rule = """
[해외 골프여행 일정형 필수 리서치]
- 3박5일 또는 4박6일로 떠난다는 가정의 시간대별 동선을 만듭니다.
- 시간은 "08:20", "13:40"처럼 시:분으로 씁니다. 항공편 번호는 지어내지 말고 "오전 출발 항공권 가정"처럼 처리합니다.
- 이동은 공항명, 호텔 지역, 골프장명, 식당·관광지명, 이동수단, 예상 이동시간, 예상 비용을 함께 씁니다.
- 골프장은 후보 3~5곳을 실명으로 정리하고, 도심/호텔 지역에서의 예상 이동시간과 18홀 예상 비용 구성(그린피·카트·캐디·캐디팁)을 나눕니다.
- 맛집·관광은 실제 독자가 동선에 넣을 수 있는 후보명을 씁니다. 단, 영업시간·가격은 변동 가능하므로 예상 범위와 확인 필요 문구를 붙입니다.
""".strip()
    support_rule = """
[보험·수하물·준비형 필수 리서치]
- 여행자보험은 예상 보험료만 쓰지 말고 해외의료비, 휴대품손해, 배상책임, 항공기 지연, 골프채 파손 또는 골프용품 보장 여부를 분리합니다.
- 골프백 위탁수하물은 항공권 예약 전 확인할 무게 기준, 특수수하물 접수 방식, 초과수하물 예상 비용 항목을 나눕니다.
- 준비물·앱·장비는 실제 사용 장면, 예상 비용, 확인 위치를 함께 씁니다.
""".strip()
    detail_rule = itinerary_rule if _is_overseas_itinerary_topic(topic) else support_rule

    prompt = f"""당신은 해외 골프여행 전문 리서처입니다.
오늘 날짜는 {today}입니다.
아래 주제로 티스토리 본문을 쓰기 전에 사용할 "사전 리서치 브리프"만 작성합니다.

[주제]
- 골프장/키워드: {club}
- 세부 주제: {subject}
- 카테고리: {category}
- 메인 검색 키워드: {main_keyword}
- 검색 의도: {search_intent}

[주제 선정 단계에서 반드시 답하라고 지정한 항목]
{concrete_points_text}

[체크리스트 후보]
{checklist_items_text}

[리서치 방식]
- 가능한 경우 웹 검색을 사용해 공식 관광/골프장/예약처/항공사/보험사/지도 정보와 상위 블로그 후기를 함께 봅니다.
- 검색 쿼리는 "{main_keyword} 3박5일 골프여행 비용", "{main_keyword} 골프장 그린피 캐디피", "{main_keyword} 공항 호텔 골프장 이동", "{main_keyword} 맛집 관광 일정", "{main_keyword} 골프백 수하물 여행자보험"처럼 실제 여행자가 쓰는 조합으로 넓혀 봅니다.
- 실제 공개 사이트와 블로그 후기에서 반복적으로 보이는 항목을 우선합니다.
- 단일 블로그 후기나 단일 판매 페이지를 확정 근거처럼 쓰지 않습니다.
- 금액·시간·수하물 규정·보험료는 변동 가능성이 크므로 반드시 "예상", "대략", "범위", "1인 기준", "확인 필요"를 붙입니다.
- 확인하지 못한 값은 지어내지 말고 "확인 필요"로 표시합니다. 대신 어떤 사이트/예약처/지도에서 확인할지 구체적으로 적습니다.
- 본문에 바로 넣을 수 있도록 실명 지명, 이동수단, 예상 이동시간, 예상 비용 범위를 최대한 구체적으로 작성합니다.

{detail_rule}

[출력 형식]
마크다운 표를 사용해도 됩니다. 단, 아래 9개 블록은 모두 채우세요.

1. 목적지·일정 가정
- 출발지, 도착 공항, 숙박 추천 지역, 권장 여행기간, 라운드 횟수, 최적 시즌을 작성합니다.

2. 시간대별 동선 초안
- Day, 시간, 활동, 출발→도착 지역, 이동수단, 예상 이동시간, 예상 비용, 확인처를 표로 작성합니다.
- 해외 골프여행 일정형이면 최소 12개 행을 작성합니다.

3. 골프장 후보
- 골프장명, 어느 지역에서 가까운지, 예상 이동시간, 18홀 예상 비용 구성, 추천 티오프 시간대, 주의점을 작성합니다.

4. 교통·송영
- 공항→호텔, 호텔→골프장, 골프장→식당/관광지 이동수단과 예상 비용 범위를 작성합니다.

5. 식당·관광 후보
- 후보명, 어느 일정에 넣기 좋은지, 이동 이유, 예상 예산 또는 확인 항목을 작성합니다.

6. 예상 총비용
- 항공, 숙박, 라운딩, 카트, 캐디, 캐디팁, 송영, 식사, 보험, 수하물/골프백 항목을 1인 기준 예상 범위로 작성합니다.

7. 보험·수하물·장비·앱
- 여행자보험, 골프채 파손/휴대품손해, 항공 지연, 골프백 수하물, 번역/지도/환율/골프 예약 앱 확인 항목을 작성합니다.

8. 본문에서 단정하지 말아야 할 항목
- 변동 가능성이 큰 금액, 규정, 영업시간, 예약 가능 여부를 분리해서 작성합니다.

9. 리서치 확인처 로그
- 이 블록은 공개 본문이 아니라 내부 검수 로그로 저장됩니다.
- 확인처 유형, 확인한 항목, 검색어 또는 확인 위치, URL을 알 수 있으면 URL을 작성합니다.
- URL을 정확히 모르면 절대 지어내지 말고 "URL 확인 필요"라고 씁니다.
- 최소 5개 행을 작성합니다. 예: 공식 골프장 사이트, 지도앱, 항공사 수하물 안내, 보험사 다이렉트 계산, 예약 플랫폼, 여행사 상품 페이지, 상위 블로그 후기.
- 각 행에는 "확인처 유형 / 확인 항목 / 검색어 또는 위치 / URL 또는 확인 필요 / 신뢰도"를 포함합니다.
"""
    _assert_prompt_text_clean(prompt, "골프 사전 리서치")
    return prompt


def validate_golf_research_brief(topic: dict, research_brief: str) -> None:
    if not _is_overseas_golf_topic(topic):
        return
    text = _strip_html_to_text(clean_generated_text(research_brief))
    if len(text) < 900:
        raise ValueError("사전 리서치 브리프가 너무 짧아 해외 골프여행 글을 만들기 어렵습니다.")
    if _is_overseas_itinerary_topic(topic):
        checks = {
            "시:분 일정": len(re.findall(r"\b\d{1,2}:\d{2}\b", text)) >= 6,
            "예상 금액": _count_money_patterns(text) >= 5,
            "공항·호텔·골프장 동선": all(term in text for term in ("공항", "호텔", "골프장")),
            "이동수단": any(term in text for term in ("택시", "송영", "차량", "렌터카", "셔틀", "그랩", "Grab")),
            "식당·관광 후보": any(term in text for term in ("맛집", "식당", "레스토랑", "관광", "시장", "해변", "야시장")),
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise ValueError("사전 리서치 브리프의 실전 정보가 부족합니다: " + ", ".join(failed))


def build_golf_research_rewrite_prompt(topic: dict, research_brief: str, reason: Exception | str) -> str:
    club = str(topic.get("club", "")).strip()
    topic_name = str(topic.get("topic", "")).strip()
    category = str(topic.get("category", "")).strip()
    main_keyword = str(topic.get("main_keyword", "")).strip()
    previous_brief = clean_generated_text(research_brief).strip()
    if len(previous_brief) > 12000:
        previous_brief = previous_brief[:12000] + "\n\n[기존 브리프 일부 생략]"

    prompt = f"""
[골프 사전 리서치 브리프 보강 요청]

직전 리서치 브리프가 자동 검증을 통과하지 못했습니다.
검출된 문제: {reason}

주제 정보:
- 골프장/키워드: {club}
- 세부 주제: {topic_name}
- 카테고리: {category}
- 메인 검색 키워드: {main_keyword}

아래 기존 브리프를 버리지 말고, 누락된 실전 정보를 보강해 전체 브리프를 다시 작성하세요.

필수 보강 규칙:
- 3박5일 또는 4박6일 일정형이면 시:분 형식의 일정 후보를 최소 8개 포함
- 예상 금액은 원/만원/바트/엔/달러/USD/$ 표기를 섞어 최소 6개 포함
- 공항, 호텔 지역, 골프장 후보, 이동수단, 식당 또는 관광 후보를 각각 실명으로 포함
- 보험, 수하물, 골프백, 골프채 파손 또는 휴대품손해 확인 항목을 포함
- 금액과 시간은 예상/대략/범위/1인 기준 표현을 붙이고 단정하지 않기
- 마지막에는 "9. 리서치 확인처 로그" 섹션을 두고 확인처 유형, 확인 항목, 검색어 또는 위치, URL 또는 확인 필요, 신뢰도를 적기

[기존 브리프]
{previous_brief}
"""
    _assert_prompt_text_clean(prompt, "골프 사전 리서치 보강")
    return prompt


def _split_golf_research_source_log(research_brief: str) -> tuple[str, str]:
    """Separate the internal source/checkpoint log from the public body brief."""
    text = clean_generated_text(research_brief).strip()
    heading_patterns = [
        r"(?im)^\s*9[.)]\s*(?:리서치\s*)?(?:확인처|출처)[^\n]*(?:로그|기록)?[^\n]*$",
        r"(?im)^\s*#{1,6}\s*(?:리서치\s*)?(?:확인처|출처)[^\n]*(?:로그|기록)[^\n]*$",
        r"(?im)^\s*\[(?:리서치\s*)?(?:확인처|출처)[^\]]*(?:로그|기록)[^\]]*\]\s*$",
    ]
    matches = []
    for pattern in heading_patterns:
        match = re.search(pattern, text)
        if match:
            matches.append(match)
    if not matches:
        return text, ""

    match = min(matches, key=lambda item: item.start())
    brief_without_sources = text[:match.start()].rstrip()
    source_log = text[match.start():].strip()
    return brief_without_sources or text, source_log


def _build_golf_research_source_log_fallback(topic: dict, research_brief: str) -> str:
    source_terms = (
        "공식",
        "지도",
        "항공사",
        "보험",
        "예약",
        "여행사",
        "블로그",
        "후기",
        "확인처",
        "출처",
        "URL",
        "http",
    )
    lines = []
    for raw_line in clean_generated_text(research_brief).splitlines():
        line = raw_line.strip()
        if line and any(term in line for term in source_terms):
            lines.append(line)

    if not lines:
        lines = [
            f"- 공식 골프장 사이트 / {topic.get('club', '골프장')} 그린피·예약·코스 정보 / URL 확인 필요 / 중",
            "- 지도앱 / 공항·호텔·골프장 이동시간 / URL 확인 필요 / 중",
            "- 항공사 수하물 안내 / 골프백 위탁수하물·초과수하물 기준 / URL 확인 필요 / 중",
            "- 보험사 다이렉트 계산 / 여행자보험·휴대품손해·골프채 파손 보장 / URL 확인 필요 / 중",
            "- 예약 플랫폼 또는 여행사 상품 페이지 / 패키지 포함·불포함 항목 / URL 확인 필요 / 중",
        ]

    unique_lines = []
    seen = set()
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        unique_lines.append(line)
        if len(unique_lines) >= 40:
            break

    return "\n".join(
        [
            "9. 리서치 확인처 로그",
            "- 원본 응답에서 전용 확인처 로그 블록을 찾지 못해 관련 문장을 추출했습니다.",
            *unique_lines,
        ]
    )


def save_golf_research_source_log(topic: dict, research_brief: str) -> str:
    brief_without_sources, source_log = _split_golf_research_source_log(research_brief)
    if not source_log:
        source_log = _build_golf_research_source_log_fallback(topic, research_brief)

    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = "\n".join(
        [
            "# 골프 리서치 확인처 로그",
            "",
            f"- 저장시각: {saved_at}",
            f"- 골프장/키워드: {topic.get('club', '')}",
            f"- 세부 주제: {topic.get('topic', '')}",
            f"- 카테고리: {topic.get('category', '')}",
            f"- 메인 검색 키워드: {topic.get('main_keyword', '')}",
            "",
            source_log.strip(),
            "",
        ]
    )
    GOLF_RESEARCH_SOURCE_LOG_PATH.write_text(log_text, encoding="utf-8")
    print(f"[STEP 1/5] 리서치 확인처 로그 저장 완료: {GOLF_RESEARCH_SOURCE_LOG_PATH}")
    return brief_without_sources


def validate_golf_travel_specificity(topic: dict, html_body: str) -> None:
    if not _is_overseas_golf_topic(topic):
        return
    text = _strip_html_to_text(html_body)
    if _is_overseas_itinerary_topic(topic):
        checks = {
            "시간대별 일정": len(re.findall(r"\b\d{1,2}:\d{2}\b", text)) >= 5,
            "예상 금액": _count_money_patterns(text) >= 5,
            "공항·호텔·골프장": all(term in text for term in ("공항", "호텔", "골프장")),
            "이동수단": any(term in text for term in ("택시", "송영", "차량", "렌터카", "셔틀", "그랩", "Grab")),
            "식당·관광": any(term in text for term in ("맛집", "식당", "레스토랑", "관광", "시장", "해변", "야시장")),
            "보험·수하물": any(term in text for term in ("여행자보험", "수하물", "골프백", "휴대품손해", "골프채 파손")),
        }
        failed = [name for name, ok in checks.items() if not ok]
        if failed:
            raise ValueError("해외 골프여행 본문 상세 정보가 부족합니다: " + ", ".join(failed))
    else:
        support_terms = ("여행자보험", "보험료", "휴대품손해", "배상책임", "항공기 지연", "골프백", "위탁수하물", "초과수하물", "골프채 파손")
        if sum(1 for term in support_terms if term in text) < 3 or _count_money_patterns(text) < 2:
            raise ValueError("보험·수하물·준비형 본문에 보장 항목 또는 예상 비용이 부족합니다.")

GOLF_SYSTEM_PERSONA = """
당신은 골프 예약, 비용, 여행, 장비, 규정 정보를 공개 자료 기반으로 해설하는 티스토리 골프 전문 편집자입니다.
티스토리 HTML 모드에 바로 넣어도 깨지지 않는 완성형 HTML 본문을 작성합니다.
글은 40~60대 골퍼가 검색 후 바로 판단할 수 있도록 차분하고 명확하게 작성합니다.
목표는 광고 클릭 유도가 아니라, 독자가 예약·비용·준비·비교 문제를 해결해 오래 머무는 고품질 정보글입니다.
디자인은 과한 매거진형 구성이 아니라, 골프 정보를 읽기 좋게 정리하는 실용적인 문서형 UI를 유지합니다.
확인되지 않은 내부 정보, 비공개 예약 루트, 회원권 가격, 실제 방문 후기처럼 보이는 표현은 절대 쓰지 않습니다.
"""

GOLF_STYLE_GUIDE = """
[골프 정보 HTML 작성 가이드]
- 목적: 실제 본문 내용까지 채워진 티스토리 발행용 HTML 생성.
- 디자인: 흰 배경, 짙은 회색 본문, 차분한 딥 그린 포인트만 사용합니다.
- 구조: 글마다 다른 흐름을 사용하되 큰 제목, 짧은 요약, 본문 섹션, 확인 체크리스트, 필요 시 간단한 표, 마지막 판단 기준은 포함합니다.
- 안정성: 티스토리에서 CSS가 텍스트로 보이지 않도록 <style> 태그를 절대 쓰지 말고, 필요한 스타일은 각 태그의 style 속성에 직접 넣습니다.
- 웹형: 데스크톱에서 좁은 앱 화면처럼 보이지 않도록 전체 본문은 width:100%; max-width:100%; margin:0 auto; 구조를 사용하고, 실제 폭은 티스토리 스킨 본문 영역을 따릅니다.
- 표와 정보 박스는 본문 폭을 넓게 활용하되, 화려한 카드형 앱 UI처럼 보이지 않게 문서형 레이아웃을 유지합니다.
- 문체: 정보형, 신뢰감 있는 골프 블로그 톤. 과장보다 비교와 정리 중심.
- 금지: 코드블록, 마크다운, 빈 템플릿, placeholder, URL 나열, 각주, 제휴 링크, 제품 구매 유도 문구.
- 허용: 공식 확인처 이름, 예약처 유형, 보험사·항공사·여행사에서 확인해야 할 항목을 본문에 자연스럽게 설명하는 것.
- 금지 UI: 화려한 히어로, 그라데이션 배경, 과한 그림자, 카드 3개 이상 나열, 배지 남발, 버튼형 링크, 장식용 이모지.
- 반복 회피: 매 글마다 같은 소제목 순서, 같은 첫 문장, 같은 마무리 문장, 같은 표 제목을 반복하지 않습니다.
"""


def build_golf_body_prompt(topic: dict, research_brief: str = "") -> str:
    club    = topic["club"]
    subject = topic["topic"]
    category = topic["category"]
    today = _today_korean()
    main_keyword = _topic_text(topic, "main_keyword", f"{club} {subject}")
    search_intent = _topic_text(topic, "search_intent", "검색자가 방문 전 판단 기준을 알고 싶어 합니다.")
    reader_problem = _topic_text(topic, "reader_problem", "독자가 비용과 예약 조건을 한 번에 비교하기 어렵습니다.")
    promised_answer = _topic_text(topic, "promised_answer", "방문 전 확인할 기준을 구체적으로 정리합니다.")
    adsense_value_reason = _topic_text(topic, "adsense_value_reason", "예약, 여행, 장비, 레슨 광고와 연결될 수 있습니다.")
    body_angle = _topic_text(topic, "body_angle", "비용, 예약, 비교 기준 중심으로 전개합니다.")
    sub_keywords_text = _format_topic_list(_topic_list(topic, "sub_keywords"))
    concrete_points_text = _format_topic_list(_topic_list(topic, "concrete_points"))
    outline_sections_text = _format_topic_list(_topic_list(topic, "outline_sections"))
    table_plan_text = _format_topic_list(_topic_list(topic, "table_plan"))
    checklist_items_text = _format_topic_list(_topic_list(topic, "checklist_items"))
    risk_notes_text = _format_topic_list(_topic_list(topic, "risk_notes"))
    research_brief_text = clean_generated_text(research_brief).strip()
    if not research_brief_text:
        research_brief_text = "사전 리서치 브리프 없음. 공개 정보 확인이 어려운 값은 단정하지 말고, 구체적인 확인처와 확인 항목을 제시하세요."

    prompt = f"""{GOLF_SYSTEM_PERSONA}

{GOLF_STYLE_GUIDE}

[오늘의 글 주제]
오늘 날짜: {today}
골프장/키워드: {club}
세부 주제: {subject}
카테고리: {category}
메인 검색 키워드: {main_keyword}

[수익형 주제 전략]
- 검색 의도: {search_intent}
- 독자 문제: {reader_problem}
- 글에서 약속할 답: {promised_answer}
- 애드센스 가치 근거: {adsense_value_reason}
- 본문 전개 방향: {body_angle}

[반드시 자연스럽게 포함할 보조 키워드]
{sub_keywords_text}

[본문에서 반드시 구체적으로 답할 항목]
{concrete_points_text}

[권장 소제목 방향]
{outline_sections_text}

[표에 넣을 비교 항목 후보]
{table_plan_text}

[체크리스트에 넣을 항목]
{checklist_items_text}

[주의해야 할 표현]
{risk_notes_text}

[사전 리서치 브리프]
아래 브리프는 본문 작성 전에 별도로 만든 리서치 결과입니다. 본문은 이 브리프의 시간표, 지명, 이동수단, 예상 금액, 골프장 후보, 식당·관광 후보, 보험·수하물 확인 항목을 반드시 반영해야 합니다.

{research_brief_text}

[사전 리서치 브리프 사용 규칙]
- 해외 골프여행 글은 브리프의 "시간대별 동선 초안"을 본문 첫 절반 안에 일정표로 재구성합니다.
- "확인해야 합니다"만 반복하지 말고, 확인 항목마다 예상 범위, 이동수단, 지명, 비용 기준, 시간대를 함께 붙입니다.
- 브리프에 나온 골프장 후보명, 공항명, 숙박 지역, 식당·관광 후보를 본문에 실명으로 넣습니다. 확인이 필요한 값은 "예상", "대략", "확인 필요"를 붙입니다.
- 브리프가 "확인 필요"라고 표시한 금액·규정·영업시간은 확정처럼 쓰지 않습니다.
- 브리프와 충돌하는 내용을 새로 지어내지 않습니다. 부족한 정보는 "예약처/지도앱/항공사/보험사에서 확인할 항목"으로 처리합니다.

[출력 목표]
티스토리 HTML 모드에 그대로 붙여넣고 바로 발행할 수 있는 완성형 골프 정보글 HTML을 출력하세요.
디자인만 만들지 말고, 실제 독자가 읽을 수 있는 본문 내용을 모두 채우세요.

[애드센스 수익형 편집 원칙]
- 광고 클릭을 직접 유도하지 않습니다. 대신 검색자가 오래 머물 만큼 의사결정에 필요한 정보를 촘촘히 제공합니다.
- 글의 첫 250자 안에 메인 검색 키워드와 독자의 문제를 자연스럽게 넣어 검색 의도를 즉시 맞춥니다.
- 본문은 "왜 헷갈리는지 → 어떤 항목을 봐야 하는지 → 상황별 판단 → 공식 확인 항목 → 마지막 기준" 흐름 중 글 주제에 맞는 순서로 재구성합니다.
- 독자가 중간에 이탈하지 않도록 450~650자마다 요약 박스, 비교 문단, 체크 항목, 표 중 하나를 배치합니다.
- "다른 글을 더 검색해야 알 수 있는 글"이 아니라, 이 글 하나로 다음 행동이 정리되는 글을 만듭니다.
- 가격, 규정, 예약 가능 여부처럼 변동되는 정보는 숫자를 만들지 말고 확인 위치와 판단 방법을 제시합니다.

[실제 사이트·블로그 분석 기반 수치 작성 규칙]
- 웹 검색 또는 최신 공개 정보 확인이 가능한 경우, 공식 사이트·예약 플랫폼·여행사 상품 페이지·보험사 다이렉트 페이지·항공사 수하물 규정·상위 블로그 후기에서 반복적으로 보이는 항목을 비교해 작성합니다.
- 단일 글이나 단일 판매 페이지 하나만 근거로 확정하지 말고, "공식 확인 항목", "예약처별 차이", "후기에서 자주 빠지는 비용"을 분리합니다.
- 금액은 확정값처럼 쓰지 말고 반드시 "예상", "대략", "범위", "1인 기준", "1회 라운드 기준", "3박5일 기준" 같은 기준 단어를 붙입니다.
- 숫자를 쓸 때는 통화와 기준을 붙입니다. 예: 1인 예상, 1회 라운드 예상, 3박5일 패키지 예상, 골프백 1개 기준, 여행자보험 1인 기준.
- 현재 확인이 어려운 금액은 지어내지 말고 "예약처에서 확인할 항목"으로 바꿉니다.
- 해외 골프여행 글에는 가능한 한 예상 비용 표를 1개 넣습니다. 항목 예: 항공권, 숙박, 그린피, 카트비, 캐디피, 캐디팁, 송영, 식사, 여행자보험, 골프백 수하물.
- 여행자보험을 다룰 때는 보험료만 쓰지 말고 보장 항목을 나눕니다. 예: 해외의료비, 상해·질병, 휴대품손해, 배상책임, 항공기 지연, 골프채 파손 또는 골프용품 보장 여부.
- 보험·수하물·장비·앱은 말로만 언급하지 말고, "왜 필요한지", "예상 비용 또는 확인 기준", "가입·예약 전 체크할 문구"를 3줄 이상으로 씁니다.
- 특정 보험사나 여행사를 최고라고 단정하지 않습니다. 비교 기준과 확인 항목 중심으로 씁니다.

[글 전개 다양화 규칙]
아래 전개 방식 중 주제와 가장 맞는 1개를 고르고, 소제목과 문단 순서를 그 방식에 맞게 바꿉니다. 어떤 방식을 골랐는지 본문에 쓰지는 마세요.
- 비용분해형: 예상 지출 항목을 나누고 마지막에 총비용 체크 순서로 정리
- 예약전략형: 예약 가능성, 회원동반, 시간대, 취소 규정을 먼저 다룸
- 비교판단형: 두 선택지를 놓고 비용·접근성·난이도·편의성을 비교
- 실수방지형: 처음 가는 사람이 놓치는 준비물과 동선을 실수 목록으로 구성
- 일정설계형: 이동, 식사, 라운딩, 숙박, 귀가 순서로 1일/1박 2일 흐름 구성
- 장비선택형: 필요한 장비와 굳이 필요 없는 장비를 구분
- 규정해설형: 새 규정이나 제도를 쉬운 말로 풀고 실제 확인 항목으로 연결
- 보험·수하물형: 여행자보험, 골프백 위탁, 골프채 파손, 항공 지연, 휴대품손해를 예상 비용과 확인 항목으로 정리
- 해외준비형: 항공, 숙박, 송영, 환전, 보험, 장비, 앱, 현지 에티켓 순서로 준비 흐름 구성

[데이터 기반 키워드 운영]
- 글의 세부 주제와 자연스럽게 맞는 경우 아래 키워드군을 본문 소제목 또는 카드 문장에 포함하세요.
- 억지로 모두 넣지 말고, 주제와 맞는 키워드 4~7개만 선택하세요.
- 오늘 날짜: {today}. 본문에서 시점 설명이 필요하면 "최신 기준"처럼 자연스럽게 쓰고, 연도 표기는 규정·제도 글에서 꼭 필요할 때만 본문 안에 1회 사용하세요.

[국내 명문 CC 주제일 때 우선 키워드]
비회원 예약, 회원동반, 그린피, 캐디피, 카트비, 총비용, 예약 난이도, 법인회원권, 법인 골프, 접대 골프, 18홀 코스 공략, 세컨드 샷, 그린 스피드, 클럽하우스 식당, 락커·사우나, 주차 동선, 국내 명문 골프장 비교

[해외 골프여행 주제일 때 우선 키워드]
해외 골프여행, 골프 패키지, 총비용, 그린피, 현지 캐디, 팁 기준, 최적 시즌, 예약 방법, 한국인 추천 코스, 항공+숙박+라운딩 비용, 동남아 골프, 국내 vs 해외 비용 비교, 여행자보험, 골프백 수하물, 골프채 파손, 휴대품손해, 송영 비용, 환전

[해외 골프여행 보험·수하물 주제일 때 우선 키워드]
해외 골프여행 여행자보험, 골프 여행자보험, 골프채 파손 보장, 휴대품손해, 배상책임, 항공기 지연, 골프백 위탁수하물, 초과수하물, 항공사 수하물 규정, 골프용품 보험, 해외의료비, 캐디팁, 송영

[정책·제도·규칙 주제일 때 우선 키워드]
2026 골프 규칙, 노캐디제, 캐디선택제, 개별소비세, 비회원제 골프장, LIV 골프, 그린피 규제

[용품·앱·가성비 주제일 때 우선 키워드]
거리측정기, GPS 워치, 예약앱 비교, 카카오골프, 스마트스코어, 공공골프장, 비회원제, 가성비, 스크린골프

[입문·여성 주제일 때 우선 키워드]
골프 입문 비용, 레슨 비용, 드라이버 추천, 첫 라운딩 준비물, 에티켓, 스크린골프 연습, 여성 골퍼

- 가격·시세·예약 가능 여부는 변동 가능성이 있으므로 단정하지 말고 "공식 홈페이지 또는 예약처 확인 필요" 문맥으로 작성하세요.
- 해외 골프여행 주제에서는 현지 정보(환율, 비자, 항공편)도 간략히 언급하되, 변동 정보는 단정하지 마세요.

[해외 골프여행 실전 정보 강제 규칙]
- 해외 골프여행 일정형 글은 3박5일 또는 4박6일 기준의 "시간대별 일정표"를 반드시 넣습니다.
- 일정표에는 최소 10개 행을 넣고, 각 행에 시간, 지역, 이동수단, 예상 이동시간, 예상 비용 또는 확인 항목을 씁니다.
- 본문에는 공항→숙소, 숙소→골프장, 골프장→식당/관광지, 귀국 전 동선을 실제 여행자가 따라갈 수 있게 적습니다.
- 골프장 정보는 "어디가 좋다"가 아니라 후보명, 이동시간, 추천 티오프 시간대, 그린피·카트·캐디·캐디팁 예상 범위로 씁니다.
- 식당·관광은 말로만 "맛집을 가면 좋다"라고 쓰지 말고, 후보명 또는 지역명, 어느 날 일정에 넣을지, 예상 예산 또는 확인 항목을 붙입니다.
- 보험·수하물·앱은 글 후반의 별도 섹션으로 넣고, 여행자보험 보장 항목, 골프백 수하물, 골프채 파손/휴대품손해, 지도·번역·환율 앱 확인 기준을 실제 체크 항목으로 작성합니다.
- "가격을 봐야 한다", "동선을 확인해야 한다" 같은 추상 문장만 있으면 실패입니다. 반드시 예시 숫자, 시간, 장소, 교통수단을 함께 적습니다.

[구체성 강제 규칙]
1. 각 본문 섹션은 "무엇을 확인할지", "어디서 확인할지", "어떻게 판단할지"를 포함합니다.
2. "좋습니다", "추천합니다", "확인해보세요", "상황에 따라 다릅니다"로 끝내지 말고, 바로 뒤에 구체 조건을 붙입니다.
3. 비용 관련 문단은 최소한 그린피, 캐디피, 카트비, 식사비, 취소 수수료 중 주제와 맞는 항목을 분리해서 설명합니다.
4. 예약 관련 문단은 공식 홈페이지, 예약앱, 전화 예약, 회원동반 여부, 취소 규정 중 확인 위치를 구체적으로 씁니다.
5. 비교 관련 문단은 비교 기준을 3개 이상 제시합니다. 예: 비용, 접근성, 예약 난이도, 시설, 코스 난이도.
6. 변동 가능 정보는 숫자를 지어내지 말고 "확인해야 할 항목명"과 "판단 기준"을 제시합니다.
7. 독자가 글을 읽고 바로 실행할 수 있도록 방문 전 체크리스트는 명령형이 아니라 확인 항목형으로 씁니다.
8. 본문 전체에서 추상 표현보다 구체 명사를 우선합니다. 예: "비용"만 쓰지 말고 "그린피·캐디피·카트비·취소 수수료"라고 씁니다.
9. 실제 경험담처럼 보이게 꾸미지 말고, 공개 정보 기반 편집자의 판단 기준으로 씁니다.
10. 같은 단락 구조를 반복하지 않습니다. 짧은 문단, 설명 문단, 비교 문단, 체크 문단을 섞습니다.
11. 해외 골프여행 글은 최소 1개 이상의 예상 비용 범위 표를 넣습니다. 확정 금액처럼 보이면 실패입니다.
12. 보험·수하물·장비·앱 관련 내용은 "필요합니다" 한 문장으로 끝내지 말고, 보장 항목·예상 비용·확인 위치를 함께 씁니다.

[반드시 지킬 규칙]
1. HTML 본문만 출력합니다.
2. 코드블록, 마크다운, 설명 문구는 출력하지 않습니다.
3. 외부 CSS, JS, 폰트, 이미지 라이브러리는 사용하지 않습니다.
4. <style> 태그를 절대 사용하지 않습니다. CSS 코드가 본문에 보이면 실패입니다.
5. 모든 디자인은 각 태그의 style 속성으로 처리합니다.
6. "제목 입력", "본문 입력", "항목 입력", "숫자 입력", "placeholder" 같은 빈 템플릿 문구는 절대 쓰지 않습니다.
7. 이미지 태그, figure 태그, %%IMAGE1_PLACEHOLDER%%, %%IMAGE2_PLACEHOLDER%%를 절대 출력하지 않습니다.
8. 본문 HTML만 출력합니다.
9. 대표 이미지는 파이썬 코드에서 자동 삽입되므로 본문에는 이미지 영역을 만들지 않습니다.
10. 출처 인용 토큰, 각주, ::contentReference, oaicite, citation 표시는 절대 출력하지 않습니다.
11. 티스토리에서 깨질 가능성이 큰 복잡한 CSS, position: fixed, script, form 태그는 쓰지 않습니다.
12. 공백 제외 최소 1,800자 이상의 실제 본문 내용을 작성합니다.
13. 확인되지 않은 회원권 가격, 예약 가능 여부, 내부자 정보는 단정하지 않습니다.
14. "직접 다녀왔다", "회원만 아는", "비공개 루트", "상위 1%만 아는" 같은 표현은 쓰지 않습니다.
15. "광고", "애드센스", "수익", "클릭"이라는 단어는 본문에 쓰지 않습니다.

[반드시 포함할 UI 블록]
- 상단 제목 영역: 큰 제목과 한 줄 설명만 사용합니다.
- 대표 이미지 영역은 만들지 않습니다. 이미지는 코드에서 본문 맨 앞에 자동 삽입합니다.
- 짧은 요약 박스: 핵심 판단 기준 3~4줄.
- 본문 섹션 4개 이상: 각 섹션에 실제 설명 문단 작성.
- 방문 전 확인 체크리스트: 실제 확인 항목 4~6개 작성.
- 주의 문단: 그린피, 예약, 회원권 등 변동 가능 정보는 공식 확인이 필요하다고 안내.
- 표 UI는 주제에 꼭 필요할 때만 1개 사용합니다. 비용·비교·일정 글이면 표 1개를 넣고, 코스 해설·규정 글이면 표 없이 소제목과 체크리스트를 우선합니다.
- 해외 골프여행 글은 "예상 비용표" 또는 "포함·불포함 항목표"를 반드시 1개 넣습니다.
- 해외 골프여행 글은 "보험·수하물·장비·앱 체크" 섹션을 반드시 넣습니다.
- 마지막 문단은 구매나 광고가 아니라 "내 상황에서 먼저 확인할 1순위 기준"으로 끝냅니다.

[디자인 세부 요구]
- 전체 폭은 width:100%; max-width:100%; margin:0 auto; 로 스킨 본문 영역을 꽉 채웁니다.
- 데스크톱 웹에서 양쪽 여백이 과하게 남지 않도록 생성 HTML 자체에서 작은 고정폭을 걸지 않습니다.
- 바탕은 #ffffff 또는 #fbfbf8 계열로 밝게 유지합니다.
- 본문 글씨는 17~18px, line-height는 1.85~1.95로 둡니다.
- 본문 색은 #333333 또는 #3a3a3a로 하여 눈이 피로하지 않게 합니다.
- 제목 색은 #18392f 또는 #243b34 정도의 차분한 딥 그린만 사용합니다.
- 포인트 색은 한 가지 딥 그린 계열만 사용하고, 금색/주황/빨강 포인트는 사용하지 않습니다.
- 카드형 박스는 1~2개 이내만 사용하고, box-shadow는 쓰지 않거나 매우 약하게 사용합니다. 앱 대시보드처럼 카드만 나열하지 않습니다.
- border-radius는 6~10px 정도로 낮춥니다.
- 배경 그라데이션, 진한 컬러 헤더, 큰 배지, 버튼형 장식은 사용하지 않습니다.
- 전체적으로 신문 칼럼이나 골프장 이용 가이드처럼 차분하게 보이게 합니다.
- 최상위 래퍼에는 width:100%와 max-width:100%를 함께 사용합니다. min-width나 화면 밖으로 넘기는 넓은 고정폭은 사용하지 않습니다.
- 표와 체크리스트는 본문 폭을 자연스럽게 채우되, 좁은 모바일 앱 카드처럼 가운데 작은 박스로 몰아넣지 않습니다.

[권장 HTML 시작 구조]
<div style="width:100%; max-width:100%; margin:0 auto; padding:30px 34px 46px; color:#333333; font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',Arial,sans-serif; line-height:1.9; background:#ffffff; box-sizing:border-box;">
  <header style="padding:0 0 18px; border-bottom:2px solid #e4ebe6; margin:0 0 22px;">
    <p style="margin:0 0 8px; color:#557064; font-size:14px; font-weight:700;">{category}</p>
    <h1 style="margin:0; color:#18392f; font-size:31px; line-height:1.36; font-weight:800;">{club} {subject}</h1>
    <p style="margin:14px 0 0; color:#555555; font-size:17px; line-height:1.85;">주제에 맞는 핵심 요약을 실제 문장으로 작성합니다.</p>
  </header>
  <!-- 요약, 본문 섹션, 체크리스트, 필요 시 표, 마지막 정리를 실제 내용으로 추가 -->
</div>

위 구조를 참고하되, 반드시 실제 내용이 채워진 완성 HTML만 출력하세요.
"""
    _assert_prompt_text_clean(prompt, "골프 본문")
    return prompt


def compact_golf_research_brief_for_body(topic: dict, research_brief: str) -> str:
    """본문 품질에 필요한 숫자·동선·확인 항목을 보존하면서 ChatGPT 웹 입력량을 줄입니다."""
    text = clean_generated_text(research_brief).strip()
    if not text:
        return "사전 리서치 브리프 없음. 확인되지 않은 값은 단정하지 말고 공식 확인 항목으로 처리하세요."

    max_chars = 3600 if _is_overseas_golf_topic(topic) else 2800
    if len(text) <= max_chars:
        return text

    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in raw_lines if line]
    money_pattern = re.compile(
        r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:만\s*원|만원|원|VND|THB|JPY|USD|KRW|엔|달러|바트|동)",
        re.IGNORECASE,
    )
    section_specs = [
        (
            "기본 가정",
            ("기준일", "대표 일정", "출발지", "도착", "숙박", "권장", "라운드", "검색 의도"),
            420,
        ),
        (
            "시간·동선 핵심",
            ("Day", "공항", "호텔", "골프장", "이동", "택시", "Grab", "송영", "셔틀", "분", "시간"),
            780,
        ),
        (
            "비용·요금 핵심",
            ("비용", "요금", "예상", "그린피", "캐디", "카트", "팁", "항공", "숙박", "총액", "환율"),
            760,
        ),
        (
            "골프장·식당·관광 후보",
            ("후보", "BRG", "Ba Na", "Laguna", "Montgomerie", "Hoiana", "식당", "관광", "호이안", "미케", "한강", "마사지"),
            520,
        ),
        (
            "보험·수하물·장비 체크",
            ("보험", "수하물", "골프백", "골프채", "위탁", "초과", "파손", "휴대품손해", "배상책임", "항공기 지연", "하드케이스", "포장"),
            760,
        ),
    ]

    used: set[int] = set()

    def pick_lines(keywords: tuple[str, ...], char_limit: int) -> list[str]:
        picked: list[str] = []
        total = 0
        for idx, line in enumerate(lines):
            if idx in used:
                continue
            is_money = bool(money_pattern.search(line))
            if not is_money and not any(keyword in line for keyword in keywords):
                continue
            next_total = total + len(line) + 1
            if next_total > char_limit and picked:
                continue
            picked.append(line)
            used.add(idx)
            total = next_total
            if total >= char_limit:
                break
        return picked

    output_lines = [
        "사전 리서치 핵심 압축본",
        f"- 원본 {len(text)}자 중 본문 품질에 필요한 시간·지명·비용·규정·확인 항목만 압축했습니다.",
        "- 아래 값은 확정값이 아니라 본문에서 예상/대략/확인 필요 표현과 함께 사용합니다.",
        "",
    ]
    for title, keywords, char_limit in section_specs:
        picked = pick_lines(keywords, char_limit)
        if not picked:
            continue
        output_lines.append(f"[{title}]")
        output_lines.extend(f"- {line}" for line in picked)
        output_lines.append("")

    compact = "\n".join(output_lines).strip()
    if len(compact) > max_chars:
        compact = compact[:max_chars].rsplit("\n", 1)[0].rstrip()
        compact += "\n- 이하 세부값은 원본 리서치 브리프와 확인처 로그 기준으로 단정 없이 처리합니다."
    return compact


def build_golf_body_prompt_stable(topic: dict, research_brief: str = "") -> str:
    """ChatGPT 웹 안정성을 위해 긴 원본 가이드를 본문 품질 계약 중심으로 압축한 골프 본문 프롬프트."""
    club = topic["club"]
    subject = topic["topic"]
    category = topic["category"]
    today = _today_korean()
    main_keyword = _topic_text(topic, "main_keyword", f"{club} {subject}")
    search_intent = _topic_text(topic, "search_intent", "검색자가 방문 전 판단 기준을 알고 싶어 합니다.")
    reader_problem = _topic_text(topic, "reader_problem", "독자가 비용과 예약 조건을 한 번에 비교하기 어렵습니다.")
    promised_answer = _topic_text(topic, "promised_answer", "방문 전 확인할 기준을 구체적으로 정리합니다.")
    body_angle = _topic_text(topic, "body_angle", "비용, 예약, 비교 기준 중심으로 전개합니다.")
    sub_keywords_text = _format_topic_list(_topic_list(topic, "sub_keywords"))
    concrete_points_text = _format_topic_list(_topic_list(topic, "concrete_points"))
    outline_sections_text = _format_topic_list(_topic_list(topic, "outline_sections"))
    table_plan_text = _format_topic_list(_topic_list(topic, "table_plan"))
    checklist_items_text = _format_topic_list(_topic_list(topic, "checklist_items"))
    risk_notes_text = _format_topic_list(_topic_list(topic, "risk_notes"))
    research_brief_text = clean_generated_text(research_brief).strip()
    if not research_brief_text:
        research_brief_text = "사전 리서치 브리프 없음. 공개 정보 확인이 어려운 값은 단정하지 말고, 구체적인 확인처와 확인 항목을 제시하세요."

    prompt = f"""티스토리 HTML 모드에 넣을 골프 정보글 본문 HTML만 작성하세요.

[주제]
- 날짜: {today}
- 키워드: {club}
- 세부 주제: {subject}
- 카테고리: {category}
- 메인 검색어: {main_keyword}
- 검색 의도: {search_intent}
- 독자 문제: {reader_problem}
- 약속할 답: {promised_answer}
- 전개 방향: {body_angle}

[반영할 항목]
- 보조 키워드: {sub_keywords_text}
- 구체 답변: {concrete_points_text}
- 권장 소제목: {outline_sections_text}
- 표 후보: {table_plan_text}
- 체크리스트: {checklist_items_text}
- 주의 표현: {risk_notes_text}

[리서치 핵심]
{research_brief_text}

[작성 규칙]
1. HTML 본문만 출력합니다. 코드블록, 마크다운, 설명 문구는 쓰지 않습니다.
2. 직접 다녀온 후기처럼 쓰지 말고 공개 정보 기반 편집 글로 씁니다.
3. 가격·규정·예약 가능 여부는 확정하지 말고 예상, 범위, 확인 필요, 공식 페이지/예약처 확인 문맥으로 씁니다.
4. 첫 250자 안에 {main_keyword}와 독자의 문제를 자연스럽게 넣습니다.
5. 구조: 상단 제목 영역, 3~4줄 요약, 본문 섹션 4개 이상, 표 1개, 방문 전 체크리스트, 주의 문단, 마지막 판단 기준.
6. 해외 골프여행 글이면 일정/동선, 그린피·캐디피·카트비·팁, 송영/교통, 보험·수하물·장비·앱 체크를 반드시 넣습니다.
7. 표는 5열 이하로 작성하고, 항목/예상 범위 또는 확인 기준/어디서 확인할지/판단 포인트를 포함합니다.
8. 공백 제외 최소 1,500자 이상의 실제 내용을 작성합니다.
9. 마지막 문단은 구매 유도가 아니라 내 상황에서 먼저 확인할 1순위 기준으로 끝냅니다.
10. "광고", "애드센스", "수익", "클릭", "VIP", "프리미엄"은 본문에 쓰지 않습니다.

[골프 전문성 표현 규칙]
- 본문 섹션마다 골프 전문 용어를 1~3개 자연스럽게 사용하되, 용어만 나열하지 말고 쉬운 설명과 실제 판단 기준을 붙입니다.
- 예: 세컨드 샷은 "티샷 뒤 그린을 노리는 두 번째 샷"처럼 풀고, 캐리 거리는 "공이 공중으로 날아가 떨어지는 거리"처럼 독자가 바로 이해하게 씁니다.
- 코스·라운딩 설명에는 주제에 맞게 세컨드 샷, 페어웨이 안착률, 레귤러 온, 그린 스피드, 언듈레이션, 도그레그, 레이업, 캐리 거리, 런, 워터 해저드, 벙커 턱, 핀 포지션, 어프로치 각도, 오르막/내리막 라이, 카트 동선, 티오프 간격 중 필요한 용어를 고릅니다.
- 비용·예약 글에서도 용어를 억지로 넣지 말고, 그린피·캐디피·카트비·캐디팁·티오프 시간·취소 규정·회원동반 여부 같은 실제 결제/예약 판단어와 연결합니다.
- 해외 골프여행 글은 일정·비용 중심을 유지하되, 골프장 후보 설명에서는 세컨드 샷 지점, 해저드 위치, 카트 이동, 티오프 시간대, 캐디팁 기준처럼 라운딩 의사결정에 도움이 되는 표현을 넣습니다.
- 전문 용어가 들어간 문장은 반드시 "그래서 무엇을 확인해야 하는지"로 끝나야 합니다. 예: 그린 스피드가 빠른 코스라면 퍼팅 난도보다 동반자 평균 핸디와 티오프 시간대를 같이 확인해야 한다.
- 같은 용어를 반복하지 말고, 글 전체에서 6~10개 정도만 분산해 사용합니다.

[HTML 규칙]
- 최상위 래퍼: <div style="width:100%; max-width:100%; margin:0 auto; padding:30px 34px 46px; color:#333333; font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',Arial,sans-serif; line-height:1.9; background:#ffffff; box-sizing:border-box;">
- 모든 스타일은 style 속성으로만 씁니다.
- <style>, <script>, 외부 CSS, 이미지 태그, figure 태그, %%IMAGE1_PLACEHOLDER%%, %%IMAGE2_PLACEHOLDER%%는 절대 쓰지 않습니다.
- 본문 글씨는 17~18px, line-height는 1.85~1.95, 색상은 흰 배경/짙은 회색/딥 그린 포인트만 사용합니다.
- 화려한 히어로, 그라데이션, 큰 그림자, 버튼형 링크, 이모지는 쓰지 않습니다.

완성된 HTML 본문만 출력하세요.
"""
    if len(prompt) > 9000:
        print(f"[Golf] 본문 프롬프트 길이 경고: {len(prompt)}자")
    _assert_prompt_text_clean(prompt, "골프 본문")
    return prompt


def build_golf_title_prompt(topic: dict, html_body: str) -> str:
    club    = topic["club"]
    subject = topic["topic"]
    today = _today_korean()
    main_keyword = _topic_text(topic, "main_keyword", f"{club} {subject}")
    title_angle = _topic_text(topic, "title_angle", "방문 전 확인할 비용과 예약 기준을 제목에 명확히 드러냅니다.")
    search_intent = _topic_text(topic, "search_intent", "검색자가 방문 전 판단 기준을 알고 싶어 합니다.")
    sub_keywords_text = _format_topic_list(_topic_list(topic, "sub_keywords"))
    prompt = f"""아래 티스토리 골프 정보글에 어울리는 구글 SEO 제목 후보 5개를 작성하세요.

골프장/키워드: {club}
세부 주제: {subject}
메인 검색 키워드: {main_keyword}
오늘 날짜: {today}

[제목 전략]
- 검색 의도: {search_intent}
- 제목 방향: {title_angle}
- 아래 보조 키워드 중 제목마다 1~2개를 자연스럽게 포함하세요.
{sub_keywords_text}

[최우선 목표]
- 제목만 봐도 골프 정보를 차분하게 정리한 글처럼 보여야 합니다.
- 40~60대 골퍼가 검색 후 바로 읽고 싶은 명확한 정보형 제목을 만드세요.
- 과시적이거나 고급 이미지를 강조하기보다 예약, 비용, 코스, 시설, 방문 전 확인사항이 분명히 드러나게 작성하세요.
- 단, 확인되지 않은 사실을 단정하거나 내부자 정보처럼 보이게 만들면 안 됩니다.
- 클릭만 노린 낚시 제목이 아니라, 검색자가 기대한 답을 정확히 예고하는 제목이어야 합니다.

[데이터 기반 우선 키워드]
아래 키워드는 실제 검색 수요 신호가 강하고, 독자에게 직접 도움이 되는 조합입니다.
제목 후보 5개 중 최소 3개에 주제에 맞는 키워드군을 자연스럽게 포함하세요.
오늘 날짜: {today}. 제목에는 "2026" 또는 "2026년"을 쓰지 마세요. 시점성이 필요하면 "최신 기준", "예약 전", "방문 전"처럼 표현하세요.

▶ 국내 CC 주제:
- 비회원 예약 / 회원동반 / 그린피 / 캐디피 / 카트비 / 총비용
- 예약 난이도 / 법인회원권 / 법인 골프 / 접대 골프
- 18홀 코스 공략 / 세컨드 샷 / 그린 스피드
- 클럽하우스 식당 / 락커·사우나 / 주차 동선
- 국내 명문 골프장 비교

▶ 해외 골프여행 주제:
- 골프 패키지 / 총비용 / 항공+숙박+그린피
- 한국인 추천 코스 / 현지 캐디 / 팁 기준
- 최적 시즌 / 예약 방법 / 국내 vs 해외 비교
- 여행자보험 / 골프백 수하물 / 골프채 파손 보장
- 송영 비용 / 포함·불포함 항목 / 현지 추가비

▶ 정책·규칙 주제:
- 2026 골프 규칙 / 노캐디제 / 캐디선택제
- 개별소비세 / 비회원제 골프장 / LIV 골프 부산

▶ 가성비·공공 주제:
- 수도권 공공골프장 / 그린피 비교 / 평일 저렴
- 비회원제 골프장 / 가성비 / 주중 라운딩

▶ 용품·입문 주제:
- 거리측정기 추천 / 예약앱 비교 / 카카오골프
- 골프 입문 비용 / 여성 골퍼 / 첫 라운딩

[제목에 반드시 반영할 요소]
- 5개 제목 모두 {club} 또는 {main_keyword}를 포함합니다.
- 5개 제목 모두 검색자가 실제로 입력할 만한 골프 검색어를 포함합니다.
- {main_keyword} 안에 2026 또는 2026년이 들어 있다면 제목에서는 그 연도 표현만 빼고 자연스럽게 바꿔 씁니다.
- 5개 제목 중 최소 3개는 숫자 또는 구체 명칭을 포함합니다.
  사용 가능 예: 40대, 50대, 18홀, 1박 2일, 주말, 평일, 예약 전, 총비용, 코스 공략, 시설 체크
- 가격, 회원권 시세, 예약 가능 여부처럼 변동되는 숫자는 만들지 않습니다.
- "정리", "추천", "가이드"만으로 끝내지 말고 비용 항목, 예약 조건, 비교 기준, 체크 항목 중 하나를 제목에 넣습니다.
- 모든 제목의 문장 구조가 달라야 합니다. "{club} + 주제 + 정리" 형태를 반복하면 실패입니다.
- 제목 첫 단어가 연도나 날짜로 시작하면 실패입니다.
- 제목에 2026, 2026년, 최신년도, 올해 같은 연도 후킹 표현을 넣지 않습니다.

[랜덤 제목 컨셉]
아래 컨셉 중 서로 다른 방향으로 5개를 섞어 작성하세요.
매번 같은 제목 구조가 반복되지 않도록 문장 시작과 끝 표현을 다르게 만드세요.

1. 정보 정리형
- 예: {club} 방문 전 확인할 예약과 비용 기준
- 예: {club} 처음 가기 전 보는 코스 체크포인트

2. 40~50대 독자 타깃형
- 예: 40~50대 골퍼를 위한 {club} 방문 준비
- 예: {club} 라운딩 전 확인할 비용과 동선

3. 숫자 후킹형
- 예: {club} 18홀 코스 공략과 총비용 체크
- 예: {club} 방문 전 꼭 볼 7가지 기준

4. 예약·비용형
- 예: {club} 비회원 예약과 회원동반 조건
- 예: {club} 그린피·캐디피·카트비 총정리

5. 비교·검토형
- 예: {club} 명문 골프장 비교 포인트
- 예: {club} 예약 전 비교해야 할 코스와 시설

6. 질문 해결형
- 예: {main_keyword} 검색 전 가장 헷갈리는 비용 기준
- 예: {club} 예약은 어디서부터 확인해야 할까

7. 실수 방지형
- 예: {club} 처음 가는 사람이 놓치기 쉬운 준비 항목
- 예: {main_keyword} 전에 확인할 실수 방지 체크

8. 일정 설계형
- 예: {club} 새벽 라운딩 전 이동과 준비 순서
- 예: {main_keyword} 하루 동선과 비용 체크

9. 선택 기준형
- 예: {club} 내 상황에 맞는 예약 기준 고르는 법
- 예: {main_keyword} 판단할 때 먼저 볼 조건

10. 비교 대조형
- 예: {club} 평일과 주말 라운딩 기준 차이
- 예: {main_keyword} 국내와 해외 비용 비교 포인트

11. 보험·수하물형
- 예: {club} 여행자보험과 골프백 수하물 확인 기준
- 예: {main_keyword} 예약 전 보험과 추가비 체크

12. 포함·불포함형
- 예: {club} 패키지 가격에 빠지기 쉬운 항목
- 예: {main_keyword} 항공 숙박 그린피 외 비용 기준

[금지 표현]
- 회원만 아는
- 상위 1%만 아는
- 비공개 예약 루트
- 내부 정보
- 직접 다녀온 후기
- 무조건 최고
- 공식 3대장
- 확정 가격
- 실제 회원권 가격 단정
- 과장된 투자 수익 표현
- VIP
- 프리미엄
- 하이엔드
- 고소득 골퍼

[출력 규칙]
- 제목은 30~52자 사이를 권장합니다.
- 각 제목은 한 줄로 작성합니다.
- 번호는 1. 2. 3. 4. 5. 형식으로 붙입니다.
- 코드블록, 따옴표, 설명 문구는 출력하지 않습니다.
- 1번 제목은 클릭률이 높고 정보가 명확한 제목으로 작성합니다.
- 2번 제목은 검색 유입형으로 작성합니다.
- 3번 제목은 비교·체크리스트형으로 작성합니다.
- 4번 제목은 실수 방지형 또는 질문 해결형으로 작성합니다.
- 5번 제목은 사람 냄새가 나되 과장 없는 자연어 제목으로 작성합니다.

제목 후보 5개만 출력하세요."""
    _assert_prompt_text_clean(prompt, "골프 제목")
    return prompt


def build_golf_hashtags_prompt(topic: dict) -> str:
    club     = topic["club"]
    subject  = topic["topic"]
    category = topic["category"]
    main_keyword = _topic_text(topic, "main_keyword", f"{club} {subject}")
    sub_keywords_text = _format_topic_list(_topic_list(topic, "sub_keywords"))
    prompt = f"""'{club}' 관련 티스토리 글 해시태그를 작성하세요.

주제: {subject}
카테고리: {category}
메인 검색 키워드: {main_keyword}

[우선 반영할 보조 키워드]
{sub_keywords_text}

조건:
- 정확히 8개의 해시태그
- 쉼표(,)로 구분하여 한 줄로 출력
- # 기호 없이 단어만 출력
- 한국어 키워드 중심
- 첫 번째 태그는 반드시 메인 검색 키워드를 12자 이내로 자연스럽게 줄인 핵심 태그
- 최소 5개는 메인 키워드, 주제, 보조 키워드와 직접 관련된 롱테일 태그
- 최대 2개만 넓은 카테고리 태그 허용
- 너무 넓은 태그보다 구체 태그 우선. 예: 골프보다 그린피, 비회원예약, 거리측정기, 골프패키지
- 수요·공급 관점에서 너무 흔한 단어보다 실제 검색 의도가 있는 태그를 우선합니다.
- 주제 유형에 따라 아래 키워드군에서 선택하되, 글 주제와 직접 맞지 않으면 사용하지 마세요:
  · 국내 CC: 골프장명, 국내명문골프장, 그린피, 회원권, 코스공략, 비회원예약, 법인골프
  · 해외여행: 해외골프여행, 다낭골프, 태국골프, 일본골프, 골프패키지, 동남아골프, 여행자보험, 골프백수하물, 캐디팁
  · 보험·수하물: 골프여행자보험, 골프채파손, 휴대품손해, 배상책임, 항공기지연, 골프백위탁수하물, 초과수하물
  · 정책·규칙: 2026골프규칙, 노캐디제, 캐디선택제, 개별소비세, LIV골프
  · 가성비: 공공골프장, 비회원제골프장, 수도권골프장, 가성비골프
  · 입문·용품: 골프입문, 여성골퍼, 거리측정기, 골프레슨, 첫라운딩
- 너무 일반적인 태그("골프", "운동", "취미") 금지
- 2026 또는 날짜 관련 태그는 규정 주제일 때만 1개 허용
- 광고, 애드센스, 수익, 클릭, 협찬, 제휴 태그 금지

[8개 태그 구성]
1. 메인 키워드 축약 태그
2. 세부 문제 태그
3. 비용/예약/규정/장비/여행 중 핵심 의도 태그
4. 독자 상황 태그
5. 비교 기준 태그
6. 공식 확인 또는 체크리스트 성격 태그
7. 카테고리 태그
8. 보조 롱테일 태그

해시태그만 출력하세요."""
    _assert_prompt_text_clean(prompt, "골프 해시태그")
    return prompt


def build_golf_image_prompt(topic: dict) -> str:
    club = topic["club"]
    subject = topic["topic"]
    category = topic.get("category", "코스분석")
    image_angle = _topic_text(topic, "image_angle", "")

    subject_text = f"{club} {subject} {category}"

    scene_hint = """
Main visual direction:
- A premium Korean private golf course atmosphere
- Square editorial thumbnail for a Korean Tistory representative image
- Realistic fairway, green, bunkers, rough, pin flag, cart path, and clubhouse only when relevant
""".strip()

    # 주제별로 장면을 강제 분기해서 매번 비슷한 페어웨이 사진만 나오는 문제를 줄입니다.
    if any(k in subject_text for k in ["겨울", "동절기", "비수기"]):
        scene_hint = """
Main visual direction:
- Winter off-season premium golf course
- Dormant beige fairway, frost-touched rough, low winter sunlight, quiet empty tee box
- Strategic second-shot view toward a guarded green with bunkers
""".strip()
    elif any(k in subject_text for k in ["여름", "한여름", "오전 티타임"]):
        scene_hint = """
Main visual direction:
- Early summer morning tee time
- Fresh green fairway with soft haze, dew on grass, bright but calm sunlight
- Refined middle-aged golfers in the scene, with an approach-shot view toward the green
""".strip()
    elif any(k in subject_text for k in ["가을", "단풍"]):
        scene_hint = """
Main visual direction:
- Autumn premium golf course
- Golden foliage, deep green putting surface, warm afternoon light
- Elegant fairway curve with a strategic bunker near the landing zone
""".strip()
    elif any(k in subject_text for k in ["봄", "시즌 코스 컨디션"]):
        scene_hint = """
Main visual direction:
- Spring course condition report
- Fresh fairway grass, clean green surface, newly maintained bunkers, clear sky
- Maintenance-quality editorial look
""".strip()
    elif any(k in subject_text for k in ["세컨드 샷", "홀별 공략", "공략", "난이도", "시그니처 홀", "그린", "퍼팅"]):
        scene_hint = """
Main visual direction:
- Strategic golf course analysis scene
- View from the fairway landing area toward the green, showing second-shot decision points
- Visible bunker, water hazard or elevation change, flagstick as the focal point
""".strip()
    elif any(k in subject_text for k in ["회원권", "멤버십", "법인", "비즈니스", "접대", "자산가", "대표"]):
        scene_hint = """
Main visual direction:
- Premium membership and business golf mood
- Elegant clubhouse exterior, luxury cart path, manicured entrance landscaping, refined private-club atmosphere
- Up to four refined middle-aged golfers or companions, no logos, no readable signs
""".strip()
    elif any(k in subject_text for k in ["비용", "그린피", "가성비", "만족도", "예약", "부킹"]):
        scene_hint = """
Main visual direction:
- Practical golf trip and cost-analysis mood
- Clean golf cart near tee box, scorecard-like planning atmosphere without text, fairway in background
- Informative editorial composition suitable for price and booking guide
""".strip()
    elif any(k in subject_text for k in ["클럽하우스", "식당", "다이닝", "라운지", "락커", "사우나", "프로샵", "부대시설"]):
        scene_hint = """
Main visual direction:
- Premium golf club facility review
- Elegant clubhouse, terrace, restaurant exterior mood, refined interior-inspired composition
- Golf course visible in background, up to four refined middle-aged golfers or companions, no readable signs
""".strip()
    elif any(k in subject_text for k in ["숙소", "맛집", "주변", "1박 2일", "골프 여행"]):
        scene_hint = """
Main visual direction:
- Premium 1-night 2-day golf travel mood
- Golf course landscape with clubhouse and hotel-like resort atmosphere
- Travel-planning editorial feel, calm and aspirational
""".strip()
    elif any(k in subject_text for k in ["드레스코드", "에티켓", "매너"]):
        scene_hint = """
Main visual direction:
- Golf etiquette and dress-code article mood
- Clean tee box, neatly placed golf bag and clubs, refined private-club atmosphere
- Refined middle-aged golfers in tasteful golfwear, no brand logos
""".strip()
    elif any(k in subject_text for k in ["비교", "vs", "3대장", "순위", "시장"]):
        scene_hint = """
Main visual direction:
- Premium golf course comparison article
- Split-depth editorial composition showing multiple course elements: fairway, green, clubhouse, bunker
- Neutral comparison mood, not tied to one exact real-world course
""".strip()

    prompt = f"""Create ONE clean, premium editorial golf image for a Korean Tistory golf information blog.

Article topic:
- Golf club / keyword: {club}
- Detailed subject: {subject}
- Category: {category}
- Revenue article visual angle: {image_angle or "Match the article topic with a concrete, non-generic golf information scene"}

{scene_hint}

Critical relevance rules:
- The image must visually match the detailed subject, not just show a generic golf course.
- Use the season, article angle, and decision context from the subject when present.
- If the subject mentions strategy, show course-management elements such as bunkers, water hazard, dogleg, elevation, landing zone, green approach, or flagstick.
- If the subject mentions membership, business golf, cost, booking, facilities, or travel, make that article angle visually obvious through the scene composition.
- Do not create the same generic lush fairway image repeatedly.

Style:
- Premium Korean private country club editorial photography
- Calm, trustworthy, informative, refined
- Realistic, high-quality, natural light
- No exaggerated fantasy, no cartoon, no illustration
- Photorealistic people, natural posture, natural hands, realistic clothing texture

Tistory representative image composition:
- Create a 1:1 square image, ideal output 1200x1200 pixels.
- Tistory representative thumbnails commonly crop with cover behavior, so keep every important subject inside the central 70% safe area.
- Do not place the clubhouse, flagstick, golf cart, golf bag, person silhouette, title-like object, or main visual detail near the left or right edge.
- Leave generous clean background around all four edges so the image still works if Tistory crops it to square, card, or list thumbnail.
- Center-weighted composition: main focus in the middle, secondary scenery around it, no edge-dependent panorama.

Human presence:
- Include 1 to 4 affluent-looking Korean middle-aged adults in their 40s to 50s when it fits the scene.
- They should look like refined golf travelers or private-club members, not young models.
- Use natural candid poses: walking near a cart, checking clubs, talking before tee time, or looking toward the fairway.
- Faces may be visible only at normal editorial distance; avoid close-up portrait framing and avoid celebrity likeness.
- Keep people inside the central 70% safe area, with the golf course and article topic still clearly visible.

Restrictions:
- No logos, trademarked signage, readable text, club emblems, scorecard text, watermarks, or private property signs
- No close-up faces, no celebrity likeness, no distorted hands or artificial-looking people
- No text overlays
- Square orientation, 1:1 ratio
- High quality, realistic but not an exact real-world course reproduction"""
    return prompt



def validate_golf_generated_content(html_body: str, title_text: str = "") -> None:
    banned_phrases = [
        "비공개 예약 루트",
        "회원만 아는",
        "상위 1%만 아는",
        "내부 정보",
        "직접 다녀왔습니다",
        "제가 방문했을 때",
        "실제 방문 후기",
        "공식 3대장",
        "공식 3대 골프장",
        "무조건 국내 최고",
        "누구나 예약 가능",
        "확정 가격",
        "::contentReference",
        "oaicite",
        "contentReference",
        "<style",
        "</style",
        "제목 입력",
        "본문 입력",
        "항목 입력",
        "숫자 입력",
        "placeholder",
        "주제에 맞는 핵심 요약을 실제 문장으로 작성합니다",
        "실제 내용으로 추가",
    ]
    target = f"{title_text}\n{html_body}"
    detected = [phrase for phrase in banned_phrases if phrase in target]
    if detected:
        raise ValueError(
            "골프 생성 결과에 위험 표현이 감지되어 발행을 중단합니다: "
            + ", ".join(detected)
        )


def _build_golf_main_image_html(image_data_url: str, alt_text: str) -> str:
    safe_alt = html.escape(re.sub(r'[\"<>]', "", alt_text).strip() or "골프 대표 이미지", quote=True)
    return (
        '<figure style="text-align:center; margin:24px 0;">'
        f'<img src="{image_data_url}" alt="{safe_alt}" '
        'style="width:100%; max-width:100%; height:auto; border-radius:10px; display:block; margin:0 auto;" />'
        '</figure>\n'
    )


def _log_golf_image_state(label: str, html_body: str, image_data_url: str = "") -> None:
    placeholders = [
        token for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%")
        if token in html_body
    ]
    placeholder_text = ", ".join(placeholders) if placeholders else "없음"
    print(f"[Golf Image Debug] {label} placeholder 포함 여부: {bool(placeholders)} ({placeholder_text})")
    print(f"[Golf Image Debug] {label} image_data_url 존재 여부: {bool(image_data_url)}")
    print(f"[Golf Image Debug] {label} html_body data:image 포함 여부: {'data:image/' in html_body}")
    print(f"[Golf Image Debug] {label} html_body 길이: {len(html_body)}")


def _ensure_golf_main_image_html(
    html_body: str,
    image_data_url: str,
    alt_text: str,
    context: str = "Golf",
) -> str:
    if not image_data_url:
        if "%%IMAGE1_PLACEHOLDER%%" in html_body:
            html_body = re.sub(
                r'<figure[^>]*>.*?%%IMAGE1_PLACEHOLDER%%.*?</figure>',
                '',
                html_body,
                flags=re.DOTALL | re.IGNORECASE,
            )
            html_body = html_body.replace("%%IMAGE1_PLACEHOLDER%%", "")
            print(f"[{context}] 대표 이미지 data URL이 없어 IMAGE1 placeholder를 제거했습니다.")
        else:
            print(f"[{context}] 대표 이미지 data URL이 없어 이미지 HTML 삽입을 건너뜁니다.")
        return html_body

    if "%%IMAGE1_PLACEHOLDER%%" in html_body:
        html_body = html_body.replace("%%IMAGE1_PLACEHOLDER%%", image_data_url)
        print(f"[{context}] 기존 IMAGE1 placeholder를 data URL로 치환했습니다.")

    if "data:image/" in html_body:
        print(f"[{context}] 본문에 data:image가 이미 있어 대표 이미지 자동 삽입을 건너뜁니다.")
        return html_body

    html_body = _build_golf_main_image_html(image_data_url, alt_text) + html_body
    print(f"[{context}] 본문 맨 앞에 대표 이미지 HTML을 코드로 직접 삽입했습니다.")
    return html_body


def _strip_data_images_for_prompt(html_body: str) -> str:
    return re.sub(
        r'data:image/[^"\']+',
        "[대표 이미지 data URL 생략]",
        html_body,
        flags=re.IGNORECASE,
    )

# ------------------------------------------------------------------
# 골프 글 생성 플로우
# ------------------------------------------------------------------

def generate_golf_article(driver: webdriver.Chrome) -> dict:
    """
    골프 전용 자동화 플로우
    STEP 1: 사전 리서치 브리프 생성
    STEP 2: 썸네일 이미지 생성
    STEP 3: 본문 HTML 생성
    STEP 4: 제목 생성
    STEP 5: 해시태그 생성
    """
    print("\n[골프 모드 시작] 프리미엄 골프 블로그 글쓰기를 시작합니다.")

    # 주제 선택
    topic = select_golf_adsense_topic(driver)
    print(f"[주제] {topic['club']} — {topic['topic']}")

    # STEP 1: 사전 리서치
    research_prompt = build_golf_research_brief_prompt(topic)
    archive_prompt("golf_research_brief_prompt", research_prompt)
    print("[STEP 1/5] 사전 리서치 브리프 생성 중...")
    research_brief = send_text_prompt(driver, research_prompt, timeout=420)
    research_brief = clean_generated_text(research_brief)
    try:
        validate_golf_research_brief(topic, research_brief)
    except Exception as exc:
        print(f"[STEP 1/5] 사전 리서치 브리프 보강 필요: {exc} — 1회 보강합니다.")
        archive_prompt("golf_research_brief_response_initial", research_brief)
        rewrite_prompt = build_golf_research_rewrite_prompt(topic, research_brief, exc)
        archive_prompt("golf_research_brief_rewrite_prompt", rewrite_prompt)
        research_brief = send_text_prompt(driver, rewrite_prompt, timeout=420)
        research_brief = clean_generated_text(research_brief)
        validate_golf_research_brief(topic, research_brief)
        archive_prompt("golf_research_brief_rewrite_response", research_brief)
    archive_prompt("golf_research_brief_response", research_brief)
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    research_brief_for_body = save_golf_research_source_log(topic, research_brief)
    (GENERATED_RESULT_DIR / "research_brief.txt").write_text(research_brief_for_body, encoding="utf-8")
    (GENERATED_RESULT_DIR / "research_brief_with_sources.txt").write_text(research_brief, encoding="utf-8")
    research_brief_for_body_compact = compact_golf_research_brief_for_body(topic, research_brief_for_body)
    (GENERATED_RESULT_DIR / "research_brief_for_body_compact.txt").write_text(
        research_brief_for_body_compact,
        encoding="utf-8",
    )
    log_run("golf_research_brief", research_prompt)
    print(f"[STEP 1/5] 완료 ({len(research_brief)}자)")

    # STEP 2: 썸네일 이미지
    print("[STEP 2/5] 프리미엄 골프 이미지 생성 중...")
    image_prompt = build_golf_image_prompt(topic)
    archive_prompt("golf_image_prompt", image_prompt)
    try:
        image_url = send_image_prompt(driver, image_prompt, timeout=180, needed=1)[0]
        image_data_url = download_image_as_base64(driver, image_url)
        save_golf_image_result(image_url, image_data_url)
        log_run("golf_image", image_prompt)
        print("[STEP 2/5] 완료")
    except Exception as e:
        print(f"[STEP 2/5] 이미지 생성 실패: {e} — 이미지 없이 계속 진행합니다.")
        image_url = ""
        image_data_url = ""

    wait_after_image_before_text_prompt("골프 본문 생성", wait_seconds=10)
    open_chatgpt_text_thread_after_image(driver)

    # STEP 3: 본문
    body_prompt = build_golf_body_prompt_stable(topic, research_brief_for_body_compact)
    archive_prompt("golf_body_prompt", body_prompt)
    print("[STEP 3/5] 프리미엄 본문 HTML 생성 중...")
    html_body = send_golf_body_prompt(driver, body_prompt, timeout=600)
    html_body = clean_generated_html_body(html_body)
    try:
        validate_golf_generated_content(html_body)
        validate_golf_travel_specificity(topic, html_body)
    except Exception as exc:
        print(f"[STEP 3/5] 본문 상세도 부족 감지: {exc} — 리서치 기반으로 1회 재작성합니다.")
        rewrite_prompt = body_prompt + f"""

[재작성 강제 지시]
직전 결과는 사용자가 요구한 실전 정보가 부족했습니다.
아래 조건을 빠뜨리면 실패입니다.
- 3박5일 또는 4박6일 일정형이면 시:분이 들어간 일정표를 최소 10행 작성
- 공항, 호텔 지역, 골프장 후보, 식당·관광 후보, 이동수단, 예상 비용을 실명과 숫자로 작성
- "확인해야 한다"만 반복하지 말고 예상 범위와 확인처를 함께 작성
- 보험·수하물·장비·앱 섹션을 별도로 작성
- 모든 금액은 예상/대략/범위/1인 기준 표현을 붙여 단정하지 않기

검출된 문제: {exc}
"""
        _assert_prompt_text_clean(rewrite_prompt, "골프 본문 재작성")
        archive_prompt("golf_body_rewrite_prompt", rewrite_prompt)
        html_body = send_golf_body_prompt(driver, rewrite_prompt, timeout=600)
        html_body = clean_generated_html_body(html_body)
        validate_golf_generated_content(html_body)
        validate_golf_travel_specificity(topic, html_body)
    _log_golf_image_state("본문 생성 직후", html_body, image_data_url)
    if image_data_url:
        print("[Golf] 대표 이미지는 티스토리 HTML 모드 업로드 단계에서 파일로 삽입합니다.")
    _log_golf_image_state("본문 저장 전", html_body, image_data_url)
    validate_golf_generated_content(html_body)
    validate_golf_travel_specificity(topic, _strip_data_images_for_prompt(html_body))
    log_run("golf_body", body_prompt)
    print(f"[STEP 3/5] 완료 ({len(html_body)}자)")

    # STEP 4: 제목
    title_prompt = build_golf_title_prompt(topic, _strip_data_images_for_prompt(html_body))
    archive_prompt("golf_title_prompt", title_prompt)
    print("[STEP 4/5] SEO 최적화 제목 생성 중...")
    title_text = send_text_prompt(driver, title_prompt, timeout=180)
    validate_golf_generated_content(html_body, title_text)
    log_run("golf_title", title_prompt)
    print("[STEP 4/5] 완료")

    # STEP 5: 해시태그
    hashtags_prompt = build_golf_hashtags_prompt(topic)
    archive_prompt("golf_hashtags_prompt", hashtags_prompt)
    print("[STEP 5/5] 해시태그 생성 중...")
    hashtags_text = send_text_prompt(driver, hashtags_prompt, timeout=180)
    log_run("golf_hashtags", hashtags_prompt)
    print("[STEP 5/5] 완료")

    save_results(title_text, html_body, hashtags_text, image_url, "", image_data_url, "")

    return {
        "title":           pick_first_title(title_text),
        "title_candidates": title_text,
        "html_body":       html_body,
        "hashtags":        hashtags_text,
        "image1_url":      image_url,
        "image1_data_url": image_data_url,
        "image2_data_url": "",
        "topic_strategy":  topic,
    }


# ------------------------------------------------------------------
# 일상글 자동화 플로우
# ------------------------------------------------------------------
# 글 생성
# ------------------------------------------------------------------

def generate_article(driver: webdriver.Chrome, values: dict, products: list[dict] = None) -> dict:
    """STEP1 image -> STEP2 body -> STEP3 title -> STEP4 hashtags"""
    if products is None:
        products = []

    single_image_mode = values.get("content_vertical") == "health_supplement"
    image_prompt_1 = build_health_coupang_image_prompt(values) if single_image_mode else fill_prompt(PROMPT_IMAGE_1, values)
    validate_coupang_urls(image_prompt_1)
    image_prompt_2 = ""
    if not single_image_mode:
        image_prompt_2 = fill_prompt(PROMPT_IMAGE_2, values)
        validate_coupang_urls(image_prompt_2)

    print("[STEP 1/4] 이미지 1 생성 중...")
    image1_url = send_image_prompt(driver, image_prompt_1, timeout=180, needed=1)[0]
    image1_data_url = download_image_as_base64(driver, image1_url)
    values["image1_url"] = image1_url
    log_run("image_1", image_prompt_1)
    log_coupang_urls(image_prompt_1)
    
    print("[STEP 1/4] 이미지 1 URL 확보 완료")
    print("[STEP 1/4] 이미지 1 완료")

    image2_url = ""
    image2_data_url = ""
    if single_image_mode:
        values["image2_url"] = ""
        print("[STEP 1/4] 건강식품 쿠팡 글은 이미지 1장만 사용합니다. 이미지 2 생성을 건너뜁니다.")
        wait_after_image_before_text_prompt("건강식품 쿠팡 본문 생성", wait_seconds=10)
    else:
        print("[STEP 1/4] 이미지 2 생성 중...")
        image2_url = send_image_prompt(driver, image_prompt_2, timeout=180, needed=1)[0]
        image2_data_url = download_image_as_base64(driver, image2_url)
        values["image2_url"] = image2_url
        log_run("image_2", image_prompt_2)
        log_coupang_urls(image_prompt_2)

        print("[STEP 1/4] 이미지 2 URL 확보 완료")
        print("[STEP 1/4] 이미지 2 완료")
        wait_after_image_before_text_prompt("쿠팡 본문 생성", wait_seconds=10)

    body_prompt = build_coupang_body_prompt(values)
    validate_coupang_urls(body_prompt)
    print("[STEP 2/4] 본문 생성 중...")
    if single_image_mode:
        html_body = send_health_body_prompt_after_image(driver, body_prompt, timeout=600)
    else:
        html_body = send_text_prompt_after_image_with_refresh(driver, body_prompt, "쿠팡 본문 생성", timeout=600)
    html_body = _replace_product_link_markers(html_body, products)
    html_body = ensure_exact_coupang_disclosure(html_body)
    html_body = _replace_inline_coupang_links_with_cards(html_body, products)
    html_body = _style_coupang_html_for_tistory(html_body, values.get("keyword", ""))
    
    # HTML은 '%%IMAGE1_PLACEHOLDER%%' 같은 플레이스홀더를 원본 그대로 유지해야 WAF를 피합니다.
    log_run("body", body_prompt)
    log_coupang_urls(body_prompt)
    print(f"[STEP 2/4] 완료 ({len(html_body)}자)")

    title_prompt = build_coupang_title_prompt(values)
    print("[STEP 3/4] 제목 생성 중...")
    title_text = send_text_prompt(driver, title_prompt, timeout=180)
    log_run("title", title_prompt)
    print("[STEP 3/4] 완료")

    hashtags_prompt = build_coupang_hashtags_prompt(values)
    print("[STEP 4/4] 해시태그 생성 중...")
    hashtags_text = send_text_prompt(driver, hashtags_prompt, timeout=180)
    log_run("hashtags", hashtags_prompt)
    print("[STEP 4/4] 완료")

    save_results(
        title_text,
        html_body,
        hashtags_text,
        image1_url,
        image2_url,
        image1_data_url,
        image2_data_url,
    )

    return {
        "title":            pick_first_title(title_text),
        "title_candidates": title_text,
        "html_body":        html_body,
        "hashtags":         hashtags_text,
        "image1_url":       image1_url,
        "image2_url":       image2_url,
        "image1_data_url":  image1_data_url,
        "image2_data_url":  image2_data_url,
    }


def parse_daily_meta_json(json_text: str) -> tuple[str, str]:
    import re
    import json
    match = re.search(r"\{.*?\}", json_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data.get("title", "오늘의 핫이슈 트렌드 분석"), data.get("tags", "")
        except:
            pass
    return "오늘의 핫이슈 트렌드 분석", ""


def generate_daily_article(driver: webdriver.Chrome) -> dict:
    print("\n[일상글 모드 시작] 트렌드 기반 자동 글쓰기를 시작합니다.")

    print("[STEP 1/3] 오늘의 랜덤 핫이슈 주제 선정 및 썸네일 생성 중...")
    image_url = send_image_prompt(driver, PROMPT_DAILY_IMAGE, timeout=180, needed=1)[0]
    log_run("daily_image", PROMPT_DAILY_IMAGE)

    print("[STEP 1/3] 썸네일 data URL 변환 중...")
    image_data_url = download_image_as_base64(driver, image_url)
    print("[STEP 1/3] 완료")

    print("[STEP 2/3] 인플루언서 로직 탑재 HTML 본문 생성 중...")
    wait_after_image_before_text_prompt("일상 본문 생성", wait_seconds=10)
    html_body = send_text_prompt_after_image_with_refresh(driver, PROMPT_DAILY_BODY, "일상 본문 생성", timeout=240)
    log_run("daily_body", PROMPT_DAILY_BODY)
    
    # 일상글에서도 WAF 방지를 위해 Base64가 아닌 토큰으로 치환
    if "[BASE64_IMAGE_1]" in html_body:
        html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    print("[STEP 2/3] 완료")

    print("[STEP 3/3] 최적화된 제목 및 해시태그 추출 중...")
    meta_json_text = send_text_prompt(driver, PROMPT_DAILY_META, timeout=120)
    log_run("daily_meta", PROMPT_DAILY_META)
    
    title_text, hashtags_text = parse_daily_meta_json(meta_json_text)
    print("[STEP 3/3] 완료")
    
    save_results(title_text, html_body, hashtags_text, image_url, "", image_data_url, "")

    return {
        "title": title_text,
        "html_body": html_body,
        "hashtags": hashtags_text,
        "image1_url": image_url,
        "image1_data_url": image_data_url,
        "image2_data_url": "",
    }


def login_and_open_tistory_editor(driver: webdriver.Chrome, allow_manual_login: bool = True) -> None:
    """
    Tistory 글쓰기 화면 진입.
    중요:
    - 같은 카카오/구글 로그인으로 여러 티스토리 블로그가 연결되어 있으면
      티스토리 홈의 글쓰기 링크가 대표 블로그로 빠질 수 있습니다.
    - 따라서 링크 클릭 방식은 사용하지 않고, 항상 jxbooklove 관리 글쓰기 URL로 직접 진입합니다.
    """
    target_url = TISTORY_NEW_POST_URL

    print(f"[Tistory] target editor URL: {target_url}")
    driver.get(target_url)
    random_sleep(1.0, 2.0)
    _handle_tistory_editor_alert(driver)

    def _is_editor_ready() -> bool:
        try:
            if driver.find_elements(By.XPATH, TISTORY_TITLE_XPATH):
                return True
        except Exception:
            pass
        return "manage/newpost" in (driver.current_url or "") and "jxbooklove.tistory.com" in (driver.current_url or "")

    def _is_login_required() -> bool:
        current_url = driver.current_url or ""
        if "accounts.kakao.com" in current_url:
            return True
        if "login" in current_url.lower():
            return True
        try:
            if driver.find_elements(By.XPATH, TISTORY_LOGIN_ID_XPATH):
                return True
        except Exception:
            pass
        return False

    def _wait_for_saved_session_auto_recovery() -> bool:
        timeout = max(0, int(TISTORY_SAVED_SESSION_RECOVERY_SECONDS))
        if timeout <= 0:
            return _is_editor_ready()

        print(f"[Tistory] 로그인 화면 감지 - 저장 세션 자동 복귀를 {timeout}초 확인합니다.")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _is_editor_ready():
                return True
            if not _is_login_required():
                driver.get(target_url)
                random_sleep(0.8, 1.4)
                _handle_tistory_editor_alert(driver)
                if _is_editor_ready():
                    return True
            time.sleep(2)
        return _is_editor_ready()

    # 이미 jxbooklove 글쓰기 화면이면 통과
    if not _is_editor_ready() and _is_login_required():
        if not allow_manual_login:
            if _wait_for_saved_session_auto_recovery():
                print("[Tistory] 저장 세션으로 글쓰기 화면 자동 복귀 확인")
            else:
                raise RuntimeError(
                    "티스토리 저장 세션이 로그인 화면으로 이동했습니다. "
                    "--tistory-login-only로 티스토리 세션을 다시 저장하세요."
                )
        else:
            print("[Tistory] 로그인이 필요합니다. 로그인 화면으로 이동합니다.")

            # 카카오 로그인 진입
            driver.get(TISTORY_URL)
            random_sleep(0.8, 1.5)

            try:
                if driver.find_elements(By.XPATH, TISTORY_KAKAO_START_XPATH):
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, TISTORY_KAKAO_START_XPATH))
                    )
                    driver.find_element(By.XPATH, TISTORY_KAKAO_START_XPATH).click()
                    random_sleep(0.5, 1.0)
            except Exception as exc:
                print(f"[경고] 카카오 시작 버튼 클릭 실패 또는 불필요: {exc}")

            try:
                if driver.find_elements(By.XPATH, TISTORY_KAKAO_LOGIN_XPATH):
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, TISTORY_KAKAO_LOGIN_XPATH))
                    )
                    driver.find_element(By.XPATH, TISTORY_KAKAO_LOGIN_XPATH).click()
                    random_sleep(1.0, 1.8)
            except Exception as exc:
                print(f"[경고] 카카오 로그인 버튼 클릭 실패 또는 불필요: {exc}")

            print("[Tistory] 로그인 완료 대기 중입니다. 로그인 후 자동으로 jxbooklove 글쓰기 화면으로 이동합니다.")

            started_at = time.time()
            while time.time() - started_at < 300:
                current_url = driver.current_url or ""

                # 로그인 완료로 판단되는 순간 jxbooklove 글쓰기 URL로 다시 강제 이동
                if (
                    "accounts.kakao.com" not in current_url
                    and "login" not in current_url.lower()
                ):
                    driver.get(target_url)
                    random_sleep(1.2, 2.0)
                    _handle_tistory_editor_alert(driver)
                    if _is_editor_ready():
                        break

                time.sleep(2)
            else:
                raise TimeoutError("Tistory 로그인 대기 시간 초과")

    # 대표 블로그 글쓰기 화면으로 빠졌다면 즉시 jxbooklove로 재진입
    current_url = driver.current_url or ""
    if "manage/newpost" in current_url and "jxbooklove.tistory.com" not in current_url:
        print(f"[Tistory] 다른 블로그 글쓰기 화면 감지: {current_url}")
        print("[Tistory] jxbooklove 글쓰기 화면으로 재진입합니다.")
        driver.get(target_url)
        random_sleep(1.2, 2.0)
        _handle_tistory_editor_alert(driver)

    # 마지막으로 한 번 더 직접 진입
    if not _is_editor_ready():
        driver.get(target_url)
        random_sleep(1.2, 2.0)
        _handle_tistory_editor_alert(driver)

    _handle_tistory_editor_alert(driver)
    WebDriverWait(driver, 25).until(
        EC.presence_of_element_located((By.XPATH, TISTORY_TITLE_XPATH))
    )

    final_url = driver.current_url or ""
    if "jxbooklove.tistory.com" not in final_url:
        raise RuntimeError(
            "jxbooklove 글쓰기 화면이 아닙니다. 현재 URL: " + final_url
        )

    print("[Tistory] jxbooklove 글쓰기 화면 진입 완료")



def run_tistory_only_flow(
    publish: bool = False,
    post_type: str = "golf",
    visibility: str = "public",
    allow_manual_login: bool = True,
) -> dict:
    if check_captcha_lock():
        sys.exit(0)
    post_type = normalize_post_type(post_type)
    if not TISTORY_SESSION_DIR.exists() or not any(TISTORY_SESSION_DIR.iterdir()):
        raise RuntimeError(
            "저장된 로그인 세션이 없습니다.\n"
            "먼저 python 챗지피티웹.py --login 을 실행해 세션을 저장하세요."
        )

    result = load_saved_result()
    driver = create_driver(save_session=False, session_dir=TISTORY_SESSION_DIR)
    error_occurred = False

    try:
        print("\n[Tistory] 저장된 결과로 글쓰기 진입 중...")
        login_and_open_tistory_editor(driver, allow_manual_login=allow_manual_login)
        write_tistory_html_post(
            driver,
            title           = result["title"],
            html_body       = result["html_body"],
            tags            = result["hashtags"],
            post_type       = post_type,
            publish         = publish,
            visibility      = visibility,
            image1_data_url = result.get("image1_data_url", ""),
            image2_data_url = result.get("image2_data_url", ""),
            golf_topic      = result.get("topic_strategy"),
        )

        return result

    except Exception as e:
        error_occurred = True
        print(f"\n[오류] {e}")
        print("[오류] 브라우저를 열어 둡니다. 확인 후 수동으로 닫아주세요.")
        raise

    finally:
        quit_driver(driver, keep_browser=error_occurred)


def run_full_flow(
    publish: bool = False,
    post_type: str = "golf",
    visibility: str = "public",
    keep_browser_on_error: bool = True,
) -> dict:
    if check_captcha_lock():
        sys.exit(0)
    post_type = normalize_post_type(post_type)
    if not CHATGPT_SESSION_DIR.exists() or not any(CHATGPT_SESSION_DIR.iterdir()):
        raise RuntimeError(
            "저장된 로그인 세션이 없습니다.\\n"
            "먼저 python 챗지피티웹.py --login 을 실행해 세션을 저장하세요."
        )

    selected_products: list[dict] = []
    product_db_path: Path | None = None
    coupang_products: list[dict] = []
    coupang_values: dict = {}
    if post_type == "health":
        product_db_path, selected_products, coupang_products = prepare_health_coupang_products(count=3)
        coupang_values = build_prompt_values(coupang_products, content_vertical="health_supplement")

    driver = create_driver(save_session=False, session_dir=CHATGPT_SESSION_DIR)
    tistory_driver = None
    error_occurred = False

    try:
        prepare_chatgpt_project(driver)
        
        if post_type == "golf":
            result = generate_golf_article(driver)
        elif post_type == "health":
            result = generate_article(driver, coupang_values, coupang_products)
        elif post_type == "daily":
            result = generate_daily_article(driver)
        else:
            raise ValueError(f"main_golf.py에서 지원하지 않는 post_type 입니다: {post_type}")

        has_tistory_session = _has_saved_tistory_session()
        if not has_tistory_session:
            print("\n[Tistory] 저장된 티스토리 세션이 없거나 검증되지 않았습니다.")
            save_tistory_session()
            has_tistory_session = _has_saved_tistory_session()
        if has_tistory_session:
            print("\n[Tistory] 티스토리 전용 세션으로 브라우저를 다시 엽니다...")
            quit_driver(driver, keep_browser=False)
            tistory_driver = create_driver(save_session=False, session_dir=TISTORY_SESSION_DIR)
            driver = tistory_driver
        else:
            print("\n[Tistory] 저장된 티스토리 세션이 없어 현재 브라우저에서 이어서 진행합니다...")

        print("\n[Tistory] 로그인 및 에디터 진입 중...")
        login_and_open_tistory_editor(driver, allow_manual_login=keep_browser_on_error)
        
        write_tistory_html_post(
            driver,
            title           = result["title"],
            html_body       = result["html_body"],
            tags            = result["hashtags"],
            post_type       = post_type,
            publish         = publish,
            visibility      = visibility,
            image1_data_url = result.get("image1_data_url", ""),
            image2_data_url = result.get("image2_data_url", ""),
            golf_topic      = result.get("topic_strategy"),
        )

        if publish and post_type == "health":
            mark_products_as_used(selected_products, post_title=result["title"], product_db_path=product_db_path)
            _log_product_coupang_urls(coupang_products)
        print(f"\n[완료] {'발행 완료' if publish else '임시 저장 완료 (수동 발행 필요)'}")
        return result

    except Exception as e:
        error_occurred = True
        print(f"\n[오류] {e}")
        if keep_browser_on_error:
            print("[오류] 브라우저를 열어 둡니다. 확인 후 수동으로 닫아주세요.")
        else:
            print("[오류] 스케줄 실행 중 오류라 브라우저를 닫고 다음 작업과 세션 충돌을 방지합니다.")
        raise

    finally:
        quit_driver(driver, keep_browser=(error_occurred and keep_browser_on_error))


# ------------------------------------------------------------------
# 로그인 세션 저장
# ------------------------------------------------------------------

def save_login_session() -> None:
    print(f"\n[로그인 저장 모드] ChatGPT 세션 저장 경로: {CHATGPT_SESSION_DIR}")
    print("브라우저가 열리면 ChatGPT에 로그인한 뒤 콘솔에서 엔터를 누르세요.\n")
    driver = create_driver(save_session=True, session_dir=CHATGPT_SESSION_DIR)
    try:
        driver.get(CHATGPT_URL)
        input("→ ChatGPT 로그인 완료 후 엔터를 누르세요...")
        print("[저장 중] ChatGPT 브라우저를 정상 종료합니다...")
    finally:
        try:
            quit_driver(driver, keep_browser=False)
        except Exception:
            pass
    print(f"[완료] ChatGPT 세션 저장: {CHATGPT_SESSION_DIR}\n")
    save_tistory_session()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="티스토리 프리미엄 골프 자동화")
    parser.add_argument("--login", action="store_true", help="로그인 세션 저장 모드 실행")
    parser.add_argument("--tistory-login-only", action="store_true", help="티스토리 로그인 세션만 저장 및 검증")
    parser.add_argument("--headless", action="store_true", help="Chrome을 헤드리스 모드로 실행")
    parser.add_argument("--publish", action="store_true", help="작성 완료 후 자동 발행 (기본값)")
    parser.add_argument("--draft", action="store_true", help="자동 발행하지 않고 임시저장만 실행")
    parser.add_argument("--resume-tistory", action="store_true", help="저장된 결과로 티스토리 작성만 실행")
    parser.add_argument("--resume-tistory-publish", action="store_true", help="저장된 결과로 바로 발행")
    parser.add_argument("--scheduled", action="store_true", help="스케줄러 백그라운드 실행 모드")
    parser.add_argument("--private", action="store_true", help="발행 시 비공개로 등록")
    parser.add_argument("--post-type", default="golf", help="글 유형 (golf, health/건강식품, daily)")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    scheduled_log_file = None
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # 클립보드 충돌 방지: 다른 자동화 스크립트 완료까지 대기 (최대 30분)
    _automation_lock = FileLock(AUTOMATION_LOCK_PATH, timeout=1800)
    print("[Lock] 다른 자동화 작업 확인 중...")
    _automation_lock.acquire()
    print("[Lock] 락 획득 완료 — 작업을 시작합니다.")

    try:
        if cli_args.headless:
            os.environ["TISTORY_HEADLESS"] = "1"

        if cli_args.scheduled:
            scheduled_log_file = enable_scheduled_logging(cli_args.post_type)

        post_type = normalize_post_type(cli_args.post_type)
        visibility = "private" if cli_args.private else "public"

        if cli_args.login:
            save_login_session()
        elif cli_args.tistory_login_only:
            save_tistory_session()
        elif cli_args.resume_tistory_publish:
            run_tistory_only_flow(
                publish=True,
                post_type=post_type,
                visibility=visibility,
                allow_manual_login=not cli_args.scheduled,
            )
        elif cli_args.resume_tistory:
            run_tistory_only_flow(
                publish=False,
                post_type=post_type,
                visibility=visibility,
                allow_manual_login=not cli_args.scheduled,
            )
        else:
            publish = not cli_args.draft
            run_full_flow(
                publish=publish,
                post_type=post_type,
                visibility=visibility,
                keep_browser_on_error=not cli_args.scheduled,
            )
    finally:
        _automation_lock.release()
        print("[Lock] 락 해제 완료")
        if scheduled_log_file:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            scheduled_log_file.close()
