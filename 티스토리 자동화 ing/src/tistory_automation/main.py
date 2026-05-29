"""
티스토리 쿠팡 파트너스 자동화 스크립트

실행 방법
  일반 실행: python 챗지피티웹.py
  로그인 저장: python 챗지피티웹.py --login
  발행까지 실행: python 챗지피티웹.py --publish
"""

import sys
import io

# 한글 깨짐 방지 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
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

AUTOMATION_LOCK_PATH = str(Path(__file__).resolve().parents[2] / "runtime" / "locks" / "automation.lock")

import sys as _sys
_SRC_DIR = str(Path(__file__).resolve().parent.parent.parent / "src")
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
# ------------------------------------------------------------------

PACKAGE_DIR          = Path(__file__).resolve().parent
PROJECT_ROOT         = PACKAGE_DIR.parents[1]
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
COUPANG_TOPIC_PERFORMANCE_DEFAULT_CSV_PATH = DATA_DIR / "coupang_topic_performance.csv"
COUPANG_TOPIC_HISTORY_PATH = RUNTIME_DIR / "state" / "coupang_used_topics.json"
COUPANG_TOPIC_HISTORY_LIMIT = 200
DAILY_TOPIC_HISTORY_PATH = RUNTIME_DIR / "state" / "daily_used_topics.json"
DAILY_TOPIC_HISTORY_LIMIT = 60
GENERATED_RESULT_DIR = RUNTIME_DIR / "outputs" / "generated_results_coupang"
COUPANG_QUALITY_REPORT_DIR = RUNTIME_DIR / "reports" / "coupang_quality"
TISTORY_ONE_TIME_IMAGE_DIR = Path(os.getenv("TISTORY_ONE_TIME_IMAGE_DIR", str(Path.home() / "백업용")))
CHROMEDRIVER_PATH    = Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.117" / "chromedriver.exe"
SCHEDULED_LOG_DIR    = LOG_DIR / "scheduled"


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
    "https://chatgpt.com/g/g-p-69cf51a2939481918246bae2859b49ff"
    "-tiseutori-geul-balhaeng/project"
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
TISTORY_NEW_POST_LINK_XPATH    = '//a[contains(@href, "daniever2217.tistory.com/manage/newpost")]'
TISTORY_NEW_POST_URL           = "https://daniever2217.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"
TISTORY_SAVED_SESSION_RECOVERY_SECONDS = 30
TISTORY_EDITOR_MODE_BTN_XPATH  = '//*[@id="editor-mode-layer-btn-open"]'
TISTORY_EDITOR_HTML_XPATH      = '//*[@id="editor-mode-html-text"]'
TISTORY_EDITOR_BASIC_MENU_XPATH = '//*[@id="editor-mode-kakao-tistory"]'
TISTORY_COUPANG_CATEGORY_XPATH = '//*[@id="category-item-1226150"]/span'
TISTORY_DAILY_CATEGORY_XPATH   = '//*[@id="category-item-1226151"]/span'
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

# 카테고리 이름 fallback
TISTORY_COUPANG_CATEGORY_NAME = "데이터분석하는 청년의 꿀템"
TISTORY_DAILY_CATEGORY_NAME   = "일상을 누려보자"

TISTORY_ID       = os.getenv("TISTORY_ID")
TISTORY_PASSWORD = os.getenv("TISTORY_PASSWORD")

COUPANG_ACCESS_KEY = os.getenv("COUPANG_ACCESS_KEY")
COUPANG_SECRET_KEY = os.getenv("COUPANG_SECRET_KEY")
COUPANG_SUB_ID     = os.getenv("COUPANG_SUB_ID", "").strip()
COUPANG_API_ENABLED = os.getenv("COUPANG_API_ENABLED", "0").strip() in {"1", "true", "TRUE", "yes", "YES"}
COUPANG_API_HOST    = "https://api-gateway.coupang.com"
COUPANG_DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
EXACT_COUPANG_DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
COUPANG_EDITORIAL_NOTE_LABEL = "작성 기준과 확인 범위"
COUPANG_EDITORIAL_NOTE_REQUIRED_TERMS = (
    "공개 상품 정보",
    "작성일",
    "상세페이지",
    "최신",
    "변동",
    "최종 구매 전",
)
COUPANG_COMMERCIAL_OVERSELL_TERMS = (
    "구매하기",
    "지금 바로",
    "최저가",
    "역대급",
    "특가",
    "인생템",
    "무조건 추천",
    "강력 추천",
    "놓치면",
    "품절 전",
    "마감 임박",
    "바로가기",
)
COUPANG_NEUTRAL_CTA_TEXTS = (
    "가격과 옵션 확인",
    "상세 스펙 확인",
    "리뷰 수 확인",
)
COUPANG_CARD_LINK_STYLE = (
    "display:flex; align-items:center; gap:14px; padding:16px; margin:18px 0; "
    "border:1px solid #d8dee4; border-radius:8px; background:#fff; "
    "text-decoration:none; color:#24292f;"
)
COUPANG_CARD_IMAGE_STYLE = (
    "width:132px; height:132px; object-fit:contain; border-radius:6px; "
    "background:#fff; flex-shrink:0;"
)
COUPANG_CARD_PRICE_STYLE = (
    "display:block; font-size:18px; font-weight:700; color:#495057; margin:6px 0 2px;"
)
COUPANG_CARD_BADGE_STYLE = (
    "display:inline-block; background:#eef2f7; color:#495057; font-size:12px; "
    "font-weight:700; padding:2px 8px; border-radius:5px; margin-left:6px; vertical-align:middle;"
)
COUPANG_CARD_CTA_STYLE = (
    "display:inline-block; margin-top:10px; padding:8px 12px; background:#f8f9fa; "
    "color:#495057; font-size:14px; font-weight:700; border:1px solid #ced4da; "
    "border-radius:6px; text-align:center;"
)
COUPANG_SELECTION_REASON_TERMS = (
    "선정 이유",
    "선정한 이유",
    "고른 이유",
    "비교 대상으로 본 이유",
    "비교 대상으로 넣은 이유",
    "후보로 본 이유",
    "선택한 이유",
)
COUPANG_QUALITY_MIN_SCORE = 75
COUPANG_QUANTITATIVE_TERMS = (
    "정량",
    "가격",
    "할인",
    "할인율",
    "평점",
    "리뷰",
    "리뷰수",
    "배송",
    "설치",
    "옵션",
    "크기",
    "용량",
    "소비전력",
    "면적",
    "무게",
    "원",
    "%",
    "cm",
    "mm",
    "kg",
    "㎡",
    "평",
)
COUPANG_COMPARISON_TERMS = ("비교", "차이", "기준", "선택 기준", "핵심 차이", "비교 기준")
COUPANG_DOWNSIDE_TERMS = ("단점", "아쉬", "주의", "부담", "제한", "불편", "부족", "신중", "확인 필요")
COUPANG_FIT_TERMS = ("맞는 사람", "추천 대상", "이런 분", "어울리는", "적합한", "잘 맞")
COUPANG_CAUTIOUS_FIT_TERMS = ("신중히", "피할", "맞지 않는", "아쉬울 수", "비추천", "주의할 사람", "다시 확인")
COUPANG_EVIDENCE_TERMS = ("근거", "기준", "상품 정보", "상세페이지", "가격", "평점", "리뷰", "리뷰수", "배송", "설치", "옵션")
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

RUN_LOG_PATH              = LOG_DIR / "chatgpt_web_runs.csv"
USED_COUPANG_URL_LOG_PATH = LOG_DIR / "used_coupang_urls.csv"
PROMPT_CONFIG_PATH        = CONFIG_DIR / "prompts" / "chatgpt_web_prompts.json"
COUPANG_HTML_GUIDE_PATH   = CONFIG_DIR / "prompts" / "coupang_html_guide.md"
TISTORY_SESSION_MARKER    = TISTORY_SESSION_DIR / ".session_ready"
CURRENT_RUN_COUPANG_URL_KEYS: set[str] = set()


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
    value = (post_type or "coupang").strip().lower()
    if value in {"쿠팡", "coupang"}:
        return "coupang"
    if value in {"일상", "daily"}:
        return "daily"
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
COUPANG_HTML_GUIDE = _load_text_file(COUPANG_HTML_GUIDE_PATH, "쿠팡 HTML 지침서")
PROMPT_BODY = _PROMPT_CONFIG["body"]
PROMPT_TITLE = _PROMPT_CONFIG["title"]
PROMPT_HASHTAGS = _PROMPT_CONFIG["hashtags"]
PROMPT_IMAGE_1 = _PROMPT_CONFIG["image_1"]
PROMPT_IMAGE_2 = _PROMPT_CONFIG["image_2"]
PROMPT_DAILY_IMAGE = _PROMPT_CONFIG["daily_image"]
PROMPT_DAILY_BODY = _PROMPT_CONFIG["daily_body"]
PROMPT_DAILY_META = _PROMPT_CONFIG["daily_meta"]

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


def _replace_prompt_section(prompt_text: str, section_title: str, replacement: str) -> str:
    pattern = r"\[" + re.escape(section_title) + r"\]\n.*?(?=\n\n\[|$)"
    updated, count = re.subn(pattern, replacement.strip(), prompt_text, count=1, flags=re.DOTALL)
    if count:
        return updated
    return prompt_text.rstrip() + "\n\n" + replacement.strip()


def _rewrite_coupang_body_prompt_as_buying_guide(prompt_text: str, values: dict | None = None) -> str:
    keyword_label = str((values or {}).get("keyword") or "대표 키워드").strip() or "대표 키워드"
    image_rules = """
[이미지 삽입 규칙]
- 생성 이미지는 1장만 사용한다.
- 이미지는 초반의 문제 정의와 구매 전 판단 기준 설명이 끝난 뒤 자연스럽게 삽입한다.
- 이미지 placeholder는 입력값에 제공된 이미지 URL 토큰만 사용한다.
- 추가 이미지나 별도 이미지 placeholder는 만들거나 언급하지 않는다.
- 이미지는 특정 상품 실물 재현이 아니라 카테고리와 사용 상황을 이해시키는 중립 이미지로 다룬다.
- 이미지 직후 바로 제휴 링크만 붙이는 광고형 배치는 피한다.
"""
    link_rules = """
[링크 배치 규칙]
- 쿠팡 링크는 제품별 상세 분석이 끝난 직후 해당 제품 링크 1개만 넣는다.
- 마지막 요약, FAQ, 마무리, 하단 재정리 구간에는 쿠팡 링크를 다시 넣지 않는다.
- 전체 상품 링크를 글 맨 아래에 다시 묶는 <ul>{cta_links}</ul>, CTA 버튼 묶음, 링크 재정리 섹션은 만들지 않는다.
- 첫 쿠팡 링크가 나오기 전에는 독자의 문제, 선택 기준, 정량 비교축, 가격/리뷰/배송 확인법을 충분히 설명한다.
- 링크 문구는 가격과 옵션 확인, 상세 스펙 확인, 리뷰 수 확인처럼 정보 확인형으로만 쓴다.
- 링크/카드 표현은 구매 버튼처럼 보이는 강한 색상, 특가 강조, 구매 압박 문구 없이 정보 확인 요소처럼 다룬다.
"""
    structure_rules = f"""
[본문 구성 순서]
- 파트너스 고지 (맨 첫 줄): <p style="font-size:12px; color:#999; background:#f8f9fa; border-left:3px solid #ccc; padding:10px 14px; margin:0 0 24px; border-radius:0 6px 6px 0;">{EXACT_COUPANG_DISCLOSURE}</p>
- 작성 기준과 확인 범위: 공개 상품 정보 기준 비교이며, 가격/할인율/평점/리뷰수/배송/옵션은 작성일 기준이라 변동될 수 있고 최종 구매 전 상세페이지의 최신 정보를 확인해야 함을 밝힌다.
- 첫 문단: 독자가 겪는 문제와 구매 전 판단이 필요한 이유를 설명한다.
- <p><strong>한눈에 보는 선택 기준:</strong> ...</p>
- 이 글에서 다루는 내용 목차형 <ul>
- <h2>{keyword_label} 구매 전 먼저 정할 기준</h2>
- <h2>가격·리뷰·배송을 볼 때 주의할 점</h2>
- <h2>정량 비교 기준</h2>
- <h2>상황별 선택 가이드</h2>
- <h2>제품별 상세 분석</h2>
- 각 제품은 <h3>로 구분한다.
- 각 제품은 선정 이유 -> 장점 -> 아쉬운 점 -> 맞는 사람 -> 신중히 볼 사람 -> 해당 제품 링크 1개 순서로 쓴다.
- <h2>구매 전 체크 포인트</h2>
- <h2>자주 묻는 질문 (FAQ)</h2>
- 마지막 요약 문단: 링크 반복 없이 선택 기준과 확인할 항목만 정리한다.
- 하단 링크 재정리, 전체 링크 묶음, <ul>{{cta_links}}</ul> 출력은 금지한다.
"""
    prompt_text = _replace_prompt_section(prompt_text, "이미지 삽입 규칙", image_rules)
    prompt_text = _replace_prompt_section(prompt_text, "링크 배치 규칙", link_rules)
    prompt_text = _replace_prompt_section(prompt_text, "본문 구성 순서", structure_rules)
    return prompt_text


def build_coupang_body_prompt(values: dict) -> str:
    keyword = _clean(values.get("keyword"), "상품 비교")
    related_keywords = _clean(values.get("related_keywords"), _clean(values.get("keywords"), keyword))
    target_reader = _clean(values.get("target_reader"), "구매 전 비교 기준을 찾는 독자")
    use_case = _clean(values.get("use_case"), _clean(values.get("usage_scenario"), "가격, 옵션, 리뷰, 배송을 함께 비교하는 상황"))
    products_summary = _clean(values.get("products_summary"), "")
    combined = f"""
너는 한국어 티스토리 제휴 리뷰 에디터다.
아래 입력값만 근거로 구매 전 비교 가이드 HTML 본문을 작성한다.

[출력 규칙]
- HTML 본문만 출력한다. 설명, 코드블록, 마크다운, JSON은 금지한다.
- 첫 글자는 반드시 <p>로 시작한다.
- 허용 태그: <p> <h2> <h3> <ul> <li> <strong> <blockquote> <a> <figure> <figcaption> <img> <div> <span>
- 첫 줄은 반드시 아래 고지문 단독 <p>다.
<p>{EXACT_COUPANG_DISCLOSURE}</p>
- 본문 길이는 2200~3200자 정도로 쓴다.
- 광고문이 아니라 실제 구매 전 기준을 정리하는 정보형 문체로 쓴다.
- 직접 써봤다, 내돈내산, 무조건 추천, 최저가, 특가, 역대급, 지금 바로, 놓치면 손해 표현은 금지한다.

[입력값]
- 대표 키워드: {keyword}
- 연관 키워드: {related_keywords}
- 타깃 독자: {target_reader}
- 사용 시나리오: {use_case}
- 이미지 토큰: %%IMAGE1_PLACEHOLDER%%
- 상품 정보:
{products_summary}

[구성]
1. 고지문 다음에 "{COUPANG_EDITORIAL_NOTE_LABEL}" 문단을 넣고, 공개 상품 정보 기준이며 가격/평점/리뷰수/배송/옵션은 변동될 수 있어 상세페이지 최신 정보를 확인해야 한다고 쓴다.
2. 첫 두 문장 안에 대표 키워드를 자연스럽게 넣는다.
3. <p><strong>한눈에 보는 선택 기준:</strong> ...</p> 문단을 넣는다.
4. 목차형 <ul>을 넣는다.
5. 초반 문제 정의와 선택 기준을 설명한 뒤 <figure><img src="%%IMAGE1_PLACEHOLDER%%" alt="{keyword} 비교 이미지"><figcaption>...</figcaption></figure>를 1회만 넣는다.
6. <h2>구매 전 먼저 정할 기준</h2>, <h2>가격·리뷰·배송 확인법</h2>, <h2>정량 비교 기준</h2>, <h2>상황별 선택 가이드</h2>, <h2>제품별 상세 분석</h2>, <h2>구매 전 체크 포인트</h2>, <h2>자주 묻는 질문 (FAQ)</h2> 순서로 쓴다.
7. 제품별 상세 분석은 각 상품을 <h3>로 구분하고, 선정 이유 -> 장점 -> 아쉬운 점 -> 맞는 사람 -> 신중히 볼 사람 -> 정보 확인 링크 순서로 쓴다.

[링크 규칙]
- 상품별 링크는 상품 설명 끝에 정확히 1회만 넣는다.
- href에는 상품 정보에 있는 [PRODUCT_LINK_1], [PRODUCT_LINK_2], [PRODUCT_LINK_3] 같은 마커를 그대로 넣는다.
- 링크 문구는 "가격·옵션·리뷰 수 확인하기"처럼 정보 확인형으로만 쓴다.
- 마지막 요약, FAQ, 마무리에는 링크를 다시 넣지 않는다.
- 전체 링크 묶음이나 CTA 버튼 묶음은 만들지 않는다.

[품질 기준]
- 첫 링크 전에는 선택 기준, 비교 기준, 가격 변동 확인법을 충분히 설명한다.
- 정량 비교 기준 섹션에는 가격, 할인율, 평점, 리뷰수, 배송/설치/옵션처럼 확인 가능한 항목을 비교한다.
- 각 상품에는 확인 가능한 선정 이유와 아쉬운 점을 반드시 넣는다.
- 마지막 문단은 링크 없이 선택 기준과 최종 확인 항목만 정리한다.
""".strip()
    _assert_prompt_text_clean(combined, "쿠팡 본문")
    return combined


# ------------------------------------------------------------------
# 드라이버 생명주기
# ------------------------------------------------------------------

def _build_options(user_data_dir: Path) -> Options:
    opts = Options()
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    opts.add_argument("--start-maximized")
    return opts


def _get_installed_chrome_major() -> str | None:
    chrome_paths: list[Path] = []
    if os.environ.get("CHROME_BINARY_PATH"):
        chrome_paths.append(Path(os.environ["CHROME_BINARY_PATH"]))
    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base_dir = os.environ.get(env_name)
        if base_dir:
            chrome_paths.append(Path(base_dir) / "Google" / "Chrome" / "Application" / "chrome.exe")
    for chrome_path in chrome_paths:
        if not chrome_path.exists():
            continue
        version_dirs = [
            path.name
            for path in chrome_path.parent.iterdir()
            if path.is_dir() and re.match(r"^\d+\.", path.name)
        ]
        if version_dirs:
            version_dirs.sort(key=lambda value: [int(part) for part in value.split(".") if part.isdigit()], reverse=True)
            return version_dirs[0].split(".", 1)[0]
        try:
            completed = subprocess.run(
                [str(chrome_path), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            match = re.search(r"(\d+)\.", completed.stdout or completed.stderr or "")
            if match:
                return match.group(1)
        except Exception:
            continue
    return None


def _cached_chromedriver_paths_for_major(major: str | None) -> list[Path]:
    if not major:
        return []
    roots = [
        Path.home() / ".cache" / "selenium" / "chromedriver" / "win64",
        Path.home() / ".wdm" / "drivers" / "chromedriver" / "win64",
    ]
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        matches.extend(root.glob(f"{major}.*/chromedriver.exe"))
        matches.extend(root.glob(f"{major}.*/chromedriver-win32/chromedriver.exe"))
    return sorted(
        {path.resolve() for path in matches if path.exists()},
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _candidate_chromedriver_paths() -> list[Path]:
    chrome_major = _get_installed_chrome_major()
    fixed_candidates = [CHROMEDRIVER_PATH]
    matching_fixed_candidates = [
        path
        for path in fixed_candidates
        if chrome_major and path.exists() and path.parent.name.startswith(f"{chrome_major}.")
    ]
    fallback_fixed_candidates = [path for path in fixed_candidates if path not in matching_fixed_candidates]
    candidates = matching_fixed_candidates
    candidates.extend(_cached_chromedriver_paths_for_major(chrome_major))
    candidates.extend(fallback_fixed_candidates)
    candidates.extend(
        [
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.117" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "147.0.7727.56" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "146.0.7680.165" / "chromedriver.exe",
            Path.home() / ".cache" / "selenium" / "chromedriver" / "win64" / "145.0.7632.117" / "chromedriver.exe",
        ]
    )
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if not path.exists():
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        deduped.append(path)
        seen.add(resolved)
    return deduped


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

    opts = _build_options(session_dir)
    driver = _create_chrome_driver_with_local_binary(opts)
    if driver is None:
        driver = webdriver.Chrome(options=opts)

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


def _dismiss_tistory_continue_draft_popup_with_escape(driver: webdriver.Chrome, timeout: int = 2) -> bool:
    started_at = time.time()
    try:
        while time.time() - started_at < timeout:
            current_url = driver.current_url or ""
            if "manage/newpost" in current_url or driver.find_elements(By.XPATH, TISTORY_TITLE_XPATH):
                break
            time.sleep(0.2)
        else:
            return False

        already_sent = driver.execute_script("return window.__tistoryInitialEditorEscSent === true;")
        if already_sent:
            return False
        driver.execute_script("window.__tistoryInitialEditorEscSent = true;")

        print("[Tistory] 글쓰기 진입 직후 팝업 정리용 ESC를 1회 전송합니다.")
        time.sleep(0.7)
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        random_sleep(0.5, 1.0)
        return True
    except TimeoutException:
        return False
    except Exception as exc:
        print(f"[Tistory] 작성하던 글 팝업 ESC 처리 중 경고: {exc}")
        return False


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

    # 우선 1차 clip 명령 + Ctrl+V를 시도합니다.
    _set_clipboard(prompt_text)
    time.sleep(0.5)  # clip 명령이 클립보드에 반영될 때까지 잠깐 대기
    textarea.send_keys(Keys.CONTROL, "v")
    random_sleep(1, 1.5)

    # 실제 입력 여부를 확인하고, 비어 있으면 JS 방식으로 다시 시도합니다.
    current_text = ""
    try:
        current_text = (textarea.text or "").strip()
        if not current_text:
            current_text = (driver.execute_script("return arguments[0].textContent;", textarea) or "").strip()
    except Exception:
        pass

    if not current_text:
        print("[경고] Ctrl+V 입력 실패. JavaScript 방식으로 재시도합니다...")
        textarea.click()
        random_sleep(0.3, 0.5)
        # 기존 내용을 지운 뒤 JS 삽입으로 전환합니다.
        textarea.send_keys(Keys.CONTROL, "a")
        textarea.send_keys(Keys.DELETE)
        random_sleep(0.2, 0.4)
        success = _paste_via_js(driver, textarea, prompt_text)
        if not success:
            raise RuntimeError("프롬프트 입력에 실패했습니다. 입력창 상태를 확인하세요.")
        random_sleep(0.5, 1)

    print(f"[입력] 프롬프트 입력 완료 ({len(prompt_text)}자)")


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


def submit_prompt(driver: webdriver.Chrome) -> None:
    """프롬프트를 전송합니다. Enter 키 실패 시 전송 버튼 클릭으로 재시도합니다."""
    textarea = _find_textarea(driver)
    textarea.send_keys(Keys.ENTER)
    random_sleep(0.8, 1.2)

    # Enter 키가 전송 역할을 하지 못할 경우 전송 버튼을 직접 클릭합니다.
    _SEND_BTN_XPATHS = [
        '//button[@data-testid="send-button"]',
        '//button[contains(@aria-label, "Send")]',
        '//button[contains(@aria-label, "send")]',
        '//button[contains(@class, "send")]',
    ]
    for xpath in _SEND_BTN_XPATHS:
        try:
            btns = driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                if btn.is_displayed() and btn.is_enabled():
                    print("[전송] Enter 미작동 감지 → 전송 버튼 직접 클릭")
                    btn.click()
                    random_sleep(0.5, 1.0)
                    return
        except Exception:
            continue


def _get_response_elements(driver: webdriver.Chrome) -> list:
    for xpath in CHATGPT_RESPONSE_XPATHS:
        els = driver.find_elements(By.XPATH, xpath)
        if els:
            return els
    return []


def _response_element_text(driver: webdriver.Chrome | None, element) -> str:
    try:
        text = (element.text or "").strip()
    except Exception:
        text = ""
    if text:
        return text

    if driver is None:
        return ""
    try:
        return (
            driver.execute_script(
                "return arguments[0].innerText || arguments[0].textContent || '';",
                element,
            )
            or ""
        ).strip()
    except Exception:
        return ""


def _latest_non_empty_response_text(
    elements: list,
    previous_count: int = 0,
    driver: webdriver.Chrome | None = None,
) -> str:
    candidates = elements[previous_count:] if previous_count and len(elements) > previous_count else elements
    for element in reversed(candidates):
        text = _response_element_text(driver, element)
        if text:
            return text
    return ""


def _get_image_urls(driver: webdriver.Chrome) -> list[str]:
    # lazy 이미지 강제 로딩을 위해 ChatGPT 응답 영역까지 스크롤
    try:
        driver.execute_script("""
            const imgs = document.querySelectorAll(
                'img[src*="backend-api/estuary/content"], ' +
                'img[data-src*="backend-api/estuary/content"], ' +
                '[id^="image-"] img, ' +
                'img[alt="생성된 이미지"]'
            );
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
                '[id^="image-"] img',
                'img[alt="생성된 이미지"]'
            ];
            for (const selector of selectors) {
                for (const el of document.querySelectorAll(selector)) {
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
    allow_resubmit: bool = True,
) -> str:
    started_at = time.time()
    effective_timeout = timeout          # busy/텍스트 변화 시 자동 연장될 수 있음
    last_text = ""
    last_changed_at = time.time()
    response_detected = False
    resubmit_attempted = False
    last_log_at = 0.0                    # 경과 로그 중복 방지
    while time.time() - started_at < effective_timeout:
        elapsed = time.time() - started_at
        els = _get_response_elements(driver)
        busy = _is_chatgpt_busy(driver)

        # --- 초기 응답 미감지 감지 & 자동 재전송 ---
        if allow_resubmit and not response_detected and not resubmit_attempted and elapsed > 45:
            print(f"[경고] {int(elapsed)}초 경과, 새 응답 요소 미감지. 프롬프트 재전송 시도...")
            resubmit_attempted = True
            try:
                textarea = _find_textarea(driver)
                textarea.click()
                time.sleep(0.5)
                textarea.send_keys(Keys.ENTER)
                time.sleep(1.5)
                _SEND_BTN_XPATHS = [
                    '//button[@data-testid="send-button"]',
                    '//button[contains(@aria-label, "Send")]',
                    '//button[contains(@aria-label, "send")]',
                ]
                for xpath in _SEND_BTN_XPATHS:
                    try:
                        btns = driver.find_elements(By.XPATH, xpath)
                        for btn in btns:
                            if btn.is_displayed() and btn.is_enabled():
                                print("[전송] 전송 버튼 직접 클릭으로 재시도")
                                btn.click()
                                random_sleep(1, 2)
                                break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[경고] 재전송 시도 실패: {e}")

        if len(els) > previous_count:
            if not response_detected:
                response_detected = True
                print(f"[응답] 새 응답 감지 ({int(elapsed)}초 경과)")
            current = _latest_non_empty_response_text(els, previous_count=previous_count, driver=driver)
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
            if current and not text_still_changing and not busy:
                _wait_until_chatgpt_ready(driver, timeout=min(120, effective_timeout), stable_seconds=6)
                return current
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
    while time.time() - started_at < timeout:
        current_urls = _get_image_urls(driver)
        for url in current_urls:
            if url in baseline_urls or url in captured_urls:
                continue
            captured_urls.append(url)
            _save_live_image_urls(captured_urls)
            print(f"[이미지 감지] {len(captured_urls)}/{needed}: {url}")
        if len(captured_urls) >= needed and not _is_chatgpt_busy(driver):
            _wait_until_chatgpt_ready(driver, timeout=min(120, timeout), stable_seconds=6)
            return captured_urls[:needed]
        time.sleep(1)
    raise TimeoutError("ChatGPT 이미지 생성 대기 시간 초과")


def send_text_prompt(driver: webdriver.Chrome, prompt_text: str, timeout: int = 240, max_retries: int = 2) -> str:
    """텍스트 프롬프트를 전송하고 응답을 반환합니다. 타임아웃 시 자동 재시도합니다."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            _wait_until_chatgpt_ready(driver, timeout=timeout, stable_seconds=8)
            prev = len(_get_response_elements(driver))
            input_prompt(driver, prompt_text)
            _wait_for_prompt_settle(prompt_text)
            submit_prompt(driver)
            return _wait_for_text(driver, previous_count=prev, timeout=timeout)
        except TimeoutError as e:
            last_error = e
            if attempt < max_retries:
                print(f"\n[재시도] 텍스트 응답 타임아웃 (시도 {attempt}/{max_retries}). 페이지 새로고침 후 재시도...")
                try:
                    # 페이지를 새로고침하여 깨끗한 상태에서 다시 시도합니다.
                    driver.refresh()
                    random_sleep(3, 5)
                except Exception:
                    pass
            else:
                print(f"\n[오류] 텍스트 응답 타임아웃 (최대 {max_retries}회 시도 완료)")
    raise last_error


def _latest_response_text_after(driver: webdriver.Chrome, previous_count: int = 0) -> str:
    elements = _get_response_elements(driver)
    return _latest_non_empty_response_text(elements, previous_count=previous_count, driver=driver)


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

        response_text = _latest_response_text_after(driver, previous_count=previous_count)
        if response_text:
            if response_seen_at is None:
                response_seen_at = time.time()
            if len(response_text) >= 500 or time.time() - response_seen_at >= 8:
                print("[ChatGPT] 정상 응답이 시작되어 새로고침 감시를 종료합니다.")
                return False
        time.sleep(1)

    print("[ChatGPT] 스트리밍 중지 문구가 감지되지 않았습니다.")
    return False


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

    return _wait_for_text(
        driver,
        previous_count=prev,
        timeout=timeout,
        allow_resubmit=False,
    )


def send_coupang_body_prompt_after_image(driver: webdriver.Chrome, prompt_text: str, timeout: int = 600) -> str:
    return send_text_prompt_after_image_with_refresh(driver, prompt_text, "쿠팡 본문 생성", timeout=timeout)


def prepare_chatgpt_for_next_text_prompt(driver: webdriver.Chrome, label: str) -> None:
    """이미지 생성 뒤 현재 대화 입력창을 안정화한 뒤 다음 텍스트 프롬프트를 보냅니다."""
    print(f"[ChatGPT] {label} 전 현재 대화 입력창을 안정화합니다.")
    try:
        _wait_until_chatgpt_ready(driver, timeout=180, stable_seconds=6)
        textarea = _find_textarea(driver)
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
            textarea.click()
        except Exception:
            pass
    except Exception as exc:
        raise RuntimeError(f"ChatGPT 입력창을 찾지 못해 {label} 프롬프트 전송을 중단합니다: {exc}") from exc


def wait_after_image_before_text_prompt(
    driver: webdriver.Chrome,
    label: str,
    wait_seconds: int = 10,
) -> None:
    """이미지 생성 직후 너무 빠르게 다음 프롬프트를 보내지 않도록 잠깐 기다립니다."""
    print(f"[ChatGPT] 이미지 보관 완료 후 {label} 전 {wait_seconds}초 대기...")
    time.sleep(wait_seconds)


CHATGPT_INTERRUPTION_NOTICE_SNIPPETS = (
    "스트리밍이 중지",
    "메시지 완료를 기다리는",
    "streaming was interrupted",
    "waiting for message completion",
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


def send_daily_body_prompt(driver: webdriver.Chrome, prompt_text: str, timeout: int = 240) -> str:
    """일상 본문도 이미지 직후 쿠팡과 같은 중지 문구 감시/새로고침 흐름을 사용합니다."""
    wait_after_image_before_text_prompt(driver, "일상 본문 생성", wait_seconds=10)
    return send_text_prompt_after_image_with_refresh(driver, prompt_text, "일상 본문 생성", timeout=timeout)


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


def clean_generated_text(text: str) -> str:
    """ChatGPT 응답에서 발행하면 안 되는 citation/빈 문단 잔여물을 제거합니다."""
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
    """
    일상글/쿠팡글 본문이 코드블록, 마크다운, escaped HTML 형태로 들어오는 것을 방지합니다.
    Tistory HTML 모드에는 실제 HTML 태그만 들어가야 합니다.
    """
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


def _strip_broken_image_placeholder_tags(html_body: str, token: str) -> str:
    """이미지 data URL이 없을 때 깨진 placeholder가 포함된 figure/img를 안전 제거합니다."""
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


def _ensure_daily_image_tag(html_body: str) -> str:
    """
    일상글 프롬프트가 [BASE64_IMAGE_1]만 단독 출력하면
    data:image 문자열이 본문에 그대로 노출되어 HTML이 깨져 보입니다.
    반드시 <figure><img src="%%IMAGE1_PLACEHOLDER%%"></figure> 구조로 변환합니다.
    """
    if not html_body:
        return html_body

    token = "%%IMAGE1_PLACEHOLDER%%"

    # 기존 토큰명 통일
    html_body = html_body.replace("[BASE64_IMAGE_1]", token)

    # 이미 img src 안에 있으면 그대로 둠
    if re.search(rf'<img\b[^>]*src=["\']{re.escape(token)}["\']', html_body, flags=re.IGNORECASE):
        return html_body

    # 토큰만 한 줄로 있는 경우 figure 이미지 태그로 교체
    figure_html = (
        '<figure style="text-align:center; margin:24px 0;">'
        '<img src="%%IMAGE1_PLACEHOLDER%%" alt="오늘 이슈 대표 이미지" '
        'style="width:100%; max-width:860px; height:auto; border-radius:14px; display:block; margin:0 auto;" />'
        '</figure>'
    )

    if token in html_body:
        html_body = html_body.replace(token, figure_html, 1)

    return html_body


DAILY_GOLF_FORBIDDEN_TERMS = (
    "골프",
    "골프여행",
    "골프백",
    "골프채",
    "라운딩",
    "그린피",
    "캐디",
    "캐디피",
    "카트비",
    "티오프",
    "골프장",
    "클럽하우스",
    "18홀",
)


def validate_daily_not_golf_topic(title: str = "", html_body: str = "", hashtags: str = "") -> None:
    text = html.unescape(_strip_html_tags(" ".join([title or "", html_body or "", hashtags or ""])))
    detected = [term for term in DAILY_GOLF_FORBIDDEN_TERMS if term in text]
    if detected:
        raise ValueError(
            "daily/main.py에서 골프 주제 감지: "
            + ", ".join(sorted(set(detected)))
            + " — 골프 글은 golf/main_golf.py에서만 생성해야 합니다."
        )


DAILY_MICRO_TOPICS = [
    {
        "topic_key": "japan_hita_mamedamachi_food_plan",
        "daily_topic": "일본 오이타현 히타 마메다마치 1박2일 맛집 3곳과 숙소 권역 계획",
        "daily_keyword": "히타 마메다마치 1박2일",
        "daily_destination": "일본 오이타현 히타",
        "daily_article_focus": "맛집 후보 3곳, 마메다마치 관광 동선, 히타역과 마메다마치 숙소 권역 비교",
        "daily_review_focus": "장어, 히타 야키소바, 카페, 사케 양조장 후기에서 반복되는 대기, 점심 피크, 도보 동선, 영업시간 변동",
        "daily_image_scene": "일본 소도시 강변과 전통 거리, 작은 식당 골목, 여행자가 도보 동선을 확인하는 장면",
        "required_terms": ["히타", "마메다마치", "히타역", "오이타"],
    },
    {
        "topic_key": "japan_nagoya_sakae_osu_hotel_area",
        "daily_topic": "일본 나고야 사카에·오스·나고야역 2박3일 숙소 위치 선택 계획",
        "daily_keyword": "나고야 숙소 위치 2박3일",
        "daily_destination": "일본 나고야",
        "daily_article_focus": "나고야역, 사카에, 오스 권역별 장단점과 2박3일 동선 계획",
        "daily_review_focus": "지하철 환승, 밤 이동, 쇼핑 동선, 조식, 역 접근성 후기에서 반복되는 만족/불편 포인트",
        "daily_image_scene": "나고야 도심 지하철역 주변, 쇼핑 거리, 여행자가 숙소 위치와 이동 동선을 비교하는 장면",
        "required_terms": ["나고야", "사카에", "오스", "나고야역"],
    },
    {
        "topic_key": "japan_kanazawa_higashi_chaya_omicho_plan",
        "daily_topic": "일본 가나자와 히가시차야·오미초시장 1박2일 동선 계획",
        "daily_keyword": "가나자와 1박2일 동선",
        "daily_destination": "일본 가나자와",
        "daily_article_focus": "히가시차야, 오미초시장, 겐로쿠엔을 묶는 권역별 동선과 숙소 위치 선택",
        "daily_review_focus": "시장 식사 대기, 눈·비 오는 날 이동, 버스 패스, 역 앞 숙소 후기에서 반복되는 체크포인트",
        "daily_image_scene": "일본 전통 찻집 거리와 시장 입구, 비 오는 날 우산을 든 여행자가 지도를 보는 장면",
        "required_terms": ["가나자와", "히가시차야", "오미초시장", "겐로쿠엔"],
    },
    {
        "topic_key": "japan_itoshima_day_trip_cafe_route",
        "daily_topic": "후쿠오카 근교 이토시마 당일치기 카페·해변 동선 계획",
        "daily_keyword": "이토시마 당일치기 카페 동선",
        "daily_destination": "일본 후쿠오카 이토시마",
        "daily_article_focus": "렌터카와 대중교통 선택, 해변 카페 3곳 후보, 선셋 시간대 동선 계획",
        "daily_review_focus": "버스 배차, 주차, 카페 대기, 해변 바람, 사진 명소 후기에서 반복되는 장단점",
        "daily_image_scene": "후쿠오카 근교 해변 도로와 작은 카페, 바닷가에서 이동 계획을 확인하는 장면",
        "required_terms": ["이토시마", "후쿠오카", "해변", "카페"],
    },
    {
        "topic_key": "taiwan_tainan_old_city_food_route",
        "daily_topic": "대만 타이난 구도심 미식 여행 1박2일 맛집 3곳 동선 계획",
        "daily_keyword": "타이난 구도심 미식 1박2일",
        "daily_destination": "대만 타이난",
        "daily_article_focus": "구도심 숙소 위치, 우육탕·단자이몐·야시장 맛집 후보 3곳, 도보/택시 동선",
        "daily_review_focus": "아침 영업, 줄 서는 시간, 현금 결제, 더위, 야시장 혼잡 후기에서 반복되는 체크포인트",
        "daily_image_scene": "대만 구도심 골목과 야시장 입구, 작은 로컬 식당 앞에서 동선을 확인하는 장면",
        "required_terms": ["타이난", "구도심", "우육탕", "야시장"],
    },
    {
        "topic_key": "vietnam_dalat_cafe_night_market_plan",
        "daily_topic": "베트남 달랏 카페거리·야시장 2박3일 숙소 권역과 동선 계획",
        "daily_keyword": "달랏 2박3일 카페 야시장",
        "daily_destination": "베트남 달랏",
        "daily_article_focus": "쑤언흐엉 호수, 야시장, 카페거리 주변 숙소 권역과 택시 이동 계획",
        "daily_review_focus": "고지대 날씨, 야시장 혼잡, 카페 전망, 차량 이동 시간, 우기 후기에서 반복되는 포인트",
        "daily_image_scene": "고원 도시 호수 주변 카페와 야시장 골목, 가벼운 외투를 든 여행자가 이동 계획을 보는 장면",
        "required_terms": ["달랏", "야시장", "쑤언흐엉", "카페"],
    },
    {
        "topic_key": "thailand_chiangmai_nimman_old_city_area",
        "daily_topic": "태국 치앙마이 님만해민·올드시티 숙소 권역 비교와 3박4일 계획",
        "daily_keyword": "치앙마이 님만 올드시티 숙소",
        "daily_destination": "태국 치앙마이",
        "daily_article_focus": "님만해민과 올드시티 숙소 권역, 카페·야시장·사원 동선, 3박4일 계획",
        "daily_review_focus": "그랩 이동비, 소음, 카페 접근성, 야시장 거리, 조식 후기에서 반복되는 장단점",
        "daily_image_scene": "치앙마이 골목 카페와 사원 근처 거리, 여행자가 숙소 권역을 비교하는 장면",
        "required_terms": ["치앙마이", "님만해민", "올드시티", "야시장"],
    },
]


def _load_daily_topic_history() -> list[str]:
    if not DAILY_TOPIC_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(DAILY_TOPIC_HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    history: list[str] = []
    for item in data:
        if not item:
            continue
        if isinstance(item, dict):
            key = item.get("topic_key") or item.get("query") or item.get("keyword") or ""
        else:
            key = item
        if key:
            history.append(str(key))
    return history


def _mark_daily_topic_used(topic: dict) -> None:
    DAILY_TOPIC_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    history = _load_daily_topic_history()
    topic_key = topic.get("topic_key", "")
    history = [key for key in history if key != topic_key]
    history.insert(0, topic_key)
    DAILY_TOPIC_HISTORY_PATH.write_text(
        json.dumps(history[:DAILY_TOPIC_HISTORY_LIMIT], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def pick_daily_micro_topic() -> dict:
    history = set(_load_daily_topic_history()[: len(DAILY_MICRO_TOPICS) - 1])
    candidates = [topic for topic in DAILY_MICRO_TOPICS if topic.get("topic_key") not in history]
    topic = random.choice(candidates or DAILY_MICRO_TOPICS)
    values = dict(topic)
    values["daily_required_terms"] = ", ".join(topic["required_terms"])
    return values


def validate_daily_micro_topic(topic: dict, title: str = "", html_body: str = "", hashtags: str = "") -> None:
    required_terms = [term for term in topic.get("required_terms", []) if term]
    text = html.unescape(_strip_html_tags(" ".join([title or "", html_body or "", hashtags or ""])))
    hits = [term for term in required_terms if term in text]
    if len(hits) < min(2, len(required_terms)):
        raise ValueError(
            "일상글 세부 주제 반영 부족: "
            f"필수 지역/키워드 {', '.join(required_terms)} 중 본문 반영이 부족합니다."
        )
    if title:
        title_hits = [term for term in required_terms if term in title]
        if not title_hits:
            raise ValueError(
                "일상글 제목이 너무 넓습니다. "
                f"제목에 {topic.get('daily_keyword')} 같은 세부 지역/키워드가 필요합니다."
            )


MAIN_IMAGE_PLACEHOLDER = "[BASE64_IMAGE_1]"
PRODUCT_CARD_PLACEHOLDER = "[PRODUCT_CARD_LIST]"
COUPANG_IMAGE_PREFIX = "https://ads-partners.coupang.com/image1/"
COUPANG_LINK_PREFIXES = (
    "https://link.coupang.com/",
    "https://www.coupang.com/",
    "https://coupa.ng/",
)
COUPANG_AFFILIATE_REL_TOKENS = ("sponsored", "nofollow", "noopener")
UNRESOLVED_HTML_PLACEHOLDERS = (
    "[BASE64_IMAGE_1]",
    "[PRODUCT_CARD_LIST]",
    "{BASE64_STRING}",
    "{COUPANG_PRODUCT_IMAGE_URL}",
    "{COUPANG_PARTNERS_LINK}",
)
MAIN_IMAGE_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _log_html_image(message: str) -> None:
    print(message)


def _error_html_image(message: str) -> None:
    print(f"ERROR: {message}")


def _read_main_image_as_data_uri(image_path: Path) -> str:
    if not image_path.exists():
        _error_html_image(f"MAIN_IMAGE_PATH 파일을 찾을 수 없음: {image_path}")
        raise FileNotFoundError(str(image_path))
    if not image_path.is_file():
        _error_html_image(f"MAIN_IMAGE_PATH가 파일이 아님: {image_path}")
        raise FileNotFoundError(str(image_path))

    _log_html_image(f"본문 이미지 파일 확인 완료: {image_path}")
    suffix = image_path.suffix.lower()
    mime_type = MAIN_IMAGE_MIME_BY_EXT.get(suffix)
    if not mime_type:
        _error_html_image(f"지원하지 않는 본문 이미지 확장자: {suffix}")
        raise ValueError(f"unsupported image extension: {suffix}")

    _log_html_image(f"본문 이미지 MIME 타입 확인 완료: {mime_type}")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    if not encoded:
        _error_html_image(f"본문 이미지 base64 변환 결과가 비어 있음: {image_path}")
        raise ValueError("empty base64 image")
    _log_html_image("본문 이미지 base64 변환 완료")
    return f"data:{mime_type};base64,{encoded}"


def _html_attr_value(tag: str, attr: str) -> str:
    match = re.search(rf'\s{re.escape(attr)}\s*=\s*(["\'])(.*?)\1', tag, flags=re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2)) if match else ""


def _set_html_attr(tag: str, attr: str, value: str) -> str:
    escaped_value = html.escape(value or "", quote=True)
    attr_re = re.compile(rf'(\s{re.escape(attr)}\s*=\s*)(["\'])(.*?)\2', flags=re.IGNORECASE | re.DOTALL)
    if attr_re.search(tag):
        return attr_re.sub(lambda match: f'{match.group(1)}"{escaped_value}"', tag, count=1)
    if tag.endswith("/>"):
        return f'{tag[:-2]} {attr}="{escaped_value}" />'
    if tag.endswith(">"):
        return f'{tag[:-1]} {attr}="{escaped_value}">'
    return tag


def _replace_first_img_tag_src(html_fragment: str, src: str, alt_text: str = "") -> tuple[str, bool]:
    def _replace(match: re.Match) -> str:
        img_tag = _set_html_attr(match.group(0), "src", src)
        current_alt = _html_attr_value(img_tag, "alt")
        if alt_text or not current_alt.strip():
            img_tag = _set_html_attr(img_tag, "alt", alt_text or "이미지")
        return img_tag

    updated, count = re.subn(r"<img\b[^>]*>", _replace, html_fragment, count=1, flags=re.IGNORECASE | re.DOTALL)
    return updated, count > 0


def _build_main_image_figure(data_uri: str, alt_text: str, caption: str = "") -> str:
    safe_alt = html.escape(alt_text or "본문 대표 이미지", quote=True)
    figure = (
        '<figure style="text-align: center; margin: 0 0 28px;">\n'
        '  <img\n'
        '    style="max-width: 100%; border-radius: 12px; display: block; margin: 0 auto;"\n'
        f'    src="{data_uri}"\n'
        f'    alt="{safe_alt}"\n'
        '  />\n'
    )
    if caption:
        figure += (
            '  <figcaption style="font-size: 12px; color: #999; margin-top: 8px;">\n'
            f'    {html.escape(caption)}\n'
            '  </figcaption>\n'
        )
    figure += '</figure>'
    return figure


def _ensure_figure_caption(figure_html: str, caption: str) -> str:
    if re.search(r"<figcaption\b", figure_html, flags=re.IGNORECASE):
        return figure_html
    if not caption:
        return figure_html
    caption_html = (
        '  <figcaption style="font-size: 12px; color: #999; margin-top: 8px;">\n'
        f'    {html.escape(caption)}\n'
        '  </figcaption>\n'
    )
    return re.sub(r"</figure\s*>", caption_html + "</figure>", figure_html, count=1, flags=re.IGNORECASE)


def _strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _insert_after_first_major_paragraph(html_body: str, insert_html: str) -> str:
    paragraph_re = re.compile(r"<p\b[^>]*>.*?</p>", flags=re.IGNORECASE | re.DOTALL)
    for match in paragraph_re.finditer(html_body):
        text = html.unescape(_strip_html_tags(match.group(0))).strip()
        if len(text) >= 20:
            _log_html_image("첫 번째 주요 본문 문단 뒤 figure 삽입 완료")
            return html_body[:match.end()] + "\n" + insert_html + "\n" + html_body[match.end():]

    first_p = paragraph_re.search(html_body)
    if first_p:
        _log_html_image("첫 번째 문단 뒤 figure 삽입 완료")
        return html_body[:first_p.end()] + "\n" + insert_html + "\n" + html_body[first_p.end():]

    body_close = re.search(r"</body\s*>", html_body, flags=re.IGNORECASE)
    if body_close:
        _log_html_image("body 닫힘 태그 직전 figure 삽입 완료")
        return html_body[:body_close.start()] + "\n" + insert_html + "\n" + html_body[body_close.start():]

    _log_html_image("본문 마지막에 figure 삽입 완료")
    return html_body.rstrip() + "\n" + insert_html + "\n"


def _apply_main_image_to_html(html_body: str, data_uri: str, alt_text: str, caption: str = "") -> str:
    if MAIN_IMAGE_PLACEHOLDER in html_body:
        img_with_placeholder = re.search(
            rf"<img\b[^>]*{re.escape(MAIN_IMAGE_PLACEHOLDER)}[^>]*>",
            html_body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if img_with_placeholder:
            def _replace_img(match: re.Match) -> str:
                img_tag = match.group(0).replace(MAIN_IMAGE_PLACEHOLDER, data_uri)
                img_tag = _set_html_attr(img_tag, "src", _html_attr_value(img_tag, "src") or data_uri)
                if not _html_attr_value(img_tag, "alt").strip():
                    img_tag = _set_html_attr(img_tag, "alt", alt_text or "본문 대표 이미지")
                return img_tag

            updated = re.sub(
                rf"<img\b[^>]*{re.escape(MAIN_IMAGE_PLACEHOLDER)}[^>]*>",
                _replace_img,
                html_body,
                count=1,
                flags=re.IGNORECASE | re.DOTALL,
            )
            updated = updated.replace(MAIN_IMAGE_PLACEHOLDER, data_uri)
            _log_html_image("본문 이미지 placeholder src 교체 완료")
            return updated

        figure_html = _build_main_image_figure(data_uri, alt_text, caption)
        updated = html_body.replace(MAIN_IMAGE_PLACEHOLDER, figure_html, 1)
        updated = updated.replace(MAIN_IMAGE_PLACEHOLDER, data_uri)
        _log_html_image("본문 이미지 placeholder 위치에 figure 삽입 완료")
        return updated

    figure_re = re.compile(r"<figure\b[^>]*>.*?<img\b[^>]*>.*?</figure>", flags=re.IGNORECASE | re.DOTALL)

    def _replace_figure(match: re.Match) -> str:
        figure, replaced = _replace_first_img_tag_src(match.group(0), data_uri, alt_text or "본문 대표 이미지")
        if not replaced:
            return match.group(0)
        return _ensure_figure_caption(figure, caption)

    updated, count = figure_re.subn(_replace_figure, html_body, count=1)
    if count:
        _log_html_image("기존 figure 이미지 src 교체 완료")
        return updated

    figure_html = _build_main_image_figure(data_uri, alt_text, caption)
    return _insert_after_first_major_paragraph(html_body, figure_html)


def _first_product_value(product: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = product.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_product(product: dict) -> dict:
    return {
        "product_name": _first_product_value(product, ("product_name", "상품명", "name", "title")),
        "product_description": _first_product_value(product, ("product_description", "상품설명", "description")),
        "product_price": _first_product_value(product, ("product_price", "상품가격", "price")),
        "cta_text": _first_product_value(product, ("cta_text", "cta", "button_text")),
        "coupang_partners_link": _first_product_value(
            product,
            ("coupang_partners_link", "쿠팡링크", "product_url", "url", "link"),
        ),
        "coupang_product_image_url": _first_product_value(
            product,
            ("coupang_product_image_url", "상품이미지", "product_image", "image_url", "image"),
        ),
    }


def _is_valid_coupang_image_url(url: str) -> bool:
    return (url or "").startswith(COUPANG_IMAGE_PREFIX)


def _is_valid_coupang_link(url: str) -> bool:
    return any((url or "").startswith(prefix) for prefix in COUPANG_LINK_PREFIXES)


def _affiliate_rel_value(existing_rel: str = "") -> str:
    tokens = []
    for token in COUPANG_AFFILIATE_REL_TOKENS:
        if token not in tokens:
            tokens.append(token)
    for token in re.split(r"\s+", existing_rel or ""):
        token = token.strip().lower()
        if token and token not in tokens:
            tokens.append(token)
    return " ".join(tokens)


def _enforce_coupang_affiliate_link_attrs(html_body: str) -> str:
    """Ensure every Coupang affiliate link is clearly marked for search engines."""
    patched_count = 0

    def _patch_anchor(match: re.Match) -> str:
        nonlocal patched_count
        tag = match.group(0)
        href = _html_attr_value(tag, "href")
        if not _is_valid_coupang_link(href):
            return tag
        tag = _set_html_attr(tag, "rel", _affiliate_rel_value(_html_attr_value(tag, "rel")))
        tag = _set_html_attr(tag, "target", "_blank")
        patched_count += 1
        return tag

    updated = re.sub(r"<a\b[^>]*>", _patch_anchor, html_body or "", flags=re.IGNORECASE | re.DOTALL)
    if patched_count:
        print(f"[CTA] 쿠팡 제휴 링크 rel/target 후처리 완료: {patched_count}개")
    return updated


def _validate_coupang_affiliate_link_attrs(html_body: str) -> None:
    invalid = []
    for idx, match in enumerate(re.finditer(r"<a\b[^>]*>", html_body or "", flags=re.IGNORECASE | re.DOTALL), 1):
        tag = match.group(0)
        href = _html_attr_value(tag, "href")
        if not _is_valid_coupang_link(href):
            continue
        rel_tokens = set(re.split(r"\s+", _html_attr_value(tag, "rel").lower()))
        missing = [token for token in ("sponsored", "nofollow") if token not in rel_tokens]
        if missing:
            invalid.append(f"{idx}번 링크 rel 누락({', '.join(missing)}): {href}")
    if invalid:
        raise RuntimeError("쿠팡 제휴 링크 rel 후처리 검증 실패:\n- " + "\n- ".join(invalid))


def _dedupe_coupang_affiliate_links(html_body: str) -> str:
    """Keep only the first visible link for each Coupang product."""
    seen_keys: set[str] = set()
    removed_count = 0

    def _replace_anchor(match: re.Match) -> str:
        nonlocal removed_count
        anchor_html = match.group(0)
        tag_match = re.search(r"<a\b[^>]*>", anchor_html, flags=re.IGNORECASE | re.DOTALL)
        if not tag_match:
            return anchor_html
        href = _html_attr_value(tag_match.group(0), "href")
        if not _is_valid_coupang_link(href):
            return anchor_html
        key = _coupang_product_key(href) or _canonical_coupang_url(href)
        if not key:
            return anchor_html
        if key in seen_keys:
            removed_count += 1
            return ""
        seen_keys.add(key)
        return anchor_html

    updated = re.sub(r"<a\b[^>]*>.*?</a>", _replace_anchor, html_body or "", flags=re.IGNORECASE | re.DOTALL)
    if removed_count:
        print(f"[CTA] 중복 쿠팡 링크 제거 완료: {removed_count}개")
    return updated


def _validate_coupang_affiliate_link_count(html_body: str, products: list[dict] | None = None) -> None:
    product_keys = {
        _row_coupang_key(product)
        for product in (products or [])
        if _row_coupang_key(product)
    }
    max_links = len(product_keys) if product_keys else 3
    links = []
    for match in re.finditer(r"<a\b[^>]*>", html_body or "", flags=re.IGNORECASE | re.DOTALL):
        href = _html_attr_value(match.group(0), "href")
        if _is_valid_coupang_link(href):
            links.append(href)
    if product_keys and len(links) < len(product_keys):
        raise RuntimeError(
            f"쿠팡 제휴 링크가 부족합니다. 상품 {len(product_keys)}개, 현재 링크 {len(links)}개"
        )
    if len(links) > max_links:
        raise RuntimeError(
            f"쿠팡 제휴 링크가 너무 많습니다. 최대 {max_links}개, 현재 {len(links)}개"
        )


def _neutral_coupang_cta_text(raw_text: str = "", index: int = 0) -> str:
    text = _strip_html_to_text_for_quality(raw_text or "").strip()
    if not text or any(term in text for term in COUPANG_COMMERCIAL_OVERSELL_TERMS):
        return COUPANG_NEUTRAL_CTA_TEXTS[index % len(COUPANG_NEUTRAL_CTA_TEXTS)]
    allowed_terms = ("가격", "옵션", "상세", "스펙", "리뷰", "정보", "조건", "배송", "확인")
    if not any(term in text for term in allowed_terms):
        return COUPANG_NEUTRAL_CTA_TEXTS[index % len(COUPANG_NEUTRAL_CTA_TEXTS)]
    return text[:24]


def _load_product_json(product_data_path: Path) -> list[dict]:
    if not product_data_path.exists():
        _error_html_image(f"PRODUCT_DATA_PATH 파일을 찾을 수 없음: {product_data_path}")
        raise FileNotFoundError(str(product_data_path))
    raw = json.loads(product_data_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw_products = raw.get("products") or raw.get("items") or []
    else:
        raw_products = raw
    if not isinstance(raw_products, list):
        _error_html_image("상품 데이터 JSON은 배열 또는 products 배열을 가진 객체여야 함")
        raise ValueError("invalid product json")
    products = [_normalize_product(item) for item in raw_products if isinstance(item, dict)]
    _log_html_image(f"상품 데이터 로드 완료: {len(products)}개")
    return products


def _validated_products(products: list[dict], emit_logs: bool = True) -> list[dict]:
    valid_products = []
    for idx, product in enumerate(products, 1):
        name = product.get("product_name") or f"상품 {idx}"
        image_url = product.get("coupang_product_image_url", "")
        link = product.get("coupang_partners_link", "")
        if not _is_valid_coupang_image_url(image_url):
            if emit_logs:
                _error_html_image(f"허용되지 않은 상품 이미지 URL: {name} / {image_url}")
            continue
        if emit_logs:
            _log_html_image(f"상품 {idx} 쿠팡 이미지 URL 검증 완료")
        if not _is_valid_coupang_link(link):
            if emit_logs:
                _error_html_image(f"허용되지 않은 쿠팡 링크: {name} / {link}")
            continue
        if emit_logs:
            _log_html_image(f"상품 {idx} 쿠팡 파트너스 링크 검증 완료")
        valid_products.append(product)
    return valid_products


def _build_product_card_html(product: dict) -> str:
    name = product.get("product_name") or "상품"
    price = product.get("product_price", "")
    cta_text = _neutral_coupang_cta_text(product.get("cta_text") or "", 0)
    link = product["coupang_partners_link"]
    image_url = product["coupang_product_image_url"]
    safe_name = html.escape(name)
    price_html = ""
    if price:
        price_html = (
            f'    <span style="{COUPANG_CARD_PRICE_STYLE}">\n'
            f'      {html.escape(price)}\n'
            '    </span>\n'
        )

    return (
        '<a\n'
        f'  style="{COUPANG_CARD_LINK_STYLE}"\n'
        f'  href="{html.escape(link, quote=True)}"\n'
        '  target="_blank"\n'
        f'  rel="{_affiliate_rel_value()}"\n'
        '>\n'
        '  <img\n'
        f'    style="{COUPANG_CARD_IMAGE_STYLE}"\n'
        f'    src="{html.escape(image_url, quote=True)}"\n'
        f'    alt="{html.escape(name, quote=True)}"\n'
        '  />\n'
        '  <span style="display: flex; flex-direction: column; flex: 1; min-width: 0;">\n'
        '    <span style="font-size: 17px; font-weight: 800; color: #222; line-height: 1.4; word-break: keep-all;">\n'
        f'      {safe_name}\n'
        '    </span>\n'
        f'{price_html}'
        f'    <span style="{COUPANG_CARD_CTA_STYLE}">\n'
        f'      {html.escape(cta_text)}\n'
        '    </span>\n'
        '  </span>\n'
        '</a>'
    )


def _is_product_card_anchor(anchor_html: str) -> bool:
    href = _html_attr_value(re.search(r"<a\b[^>]*>", anchor_html, flags=re.IGNORECASE | re.DOTALL).group(0), "href")
    lowered = anchor_html.lower()
    return (
        "<img" in lowered
        and (
            "coupang" in href.lower()
            or "{coupang_partners_link}" in lowered
            or "display:flex" in lowered
            or "display: flex" in lowered
            or "box-shadow" in lowered
        )
    )


def _iter_product_card_anchors(html_body: str) -> list[re.Match]:
    matches = []
    for match in re.finditer(r"<a\b[^>]*>.*?</a>", html_body, flags=re.IGNORECASE | re.DOTALL):
        try:
            if _is_product_card_anchor(match.group(0)):
                matches.append(match)
        except Exception:
            continue
    return matches


def _replace_product_name_area(card_html: str, product_name: str) -> str:
    if not product_name:
        return card_html
    pattern = re.compile(
        r'(<span\b(?=[^>]*font-size\s*:\s*17px)(?=[^>]*font-weight\s*:\s*800)[^>]*>)(.*?)(?=(?:<span\b|</span>))',
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(lambda m: m.group(1) + html.escape(product_name), card_html, count=1)


def _replace_price_area(card_html: str, product_price: str) -> str:
    if not product_price:
        return card_html
    pattern = re.compile(
        r'<span\b(?=[^>]*font-weight\s*:\s*(?:900|700))(?=[^>]*color\s*:\s*#(?:e53935|495057))[^>]*>.*?</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(
        f'<span style="{COUPANG_CARD_PRICE_STYLE}">{html.escape(product_price)}</span>',
        card_html,
        count=1,
    )


def _replace_cta_area(card_html: str, cta_text: str) -> str:
    cta_text = _neutral_coupang_cta_text(cta_text)
    pattern = re.compile(
        r'<span\b(?=[^>]*(?:linear-gradient\(135deg,#ff5722,#ff9800\)|letter-spacing\s*:\s*0\.3px|border\s*:\s*1px\s+solid\s+#ced4da))[^>]*>.*?</span>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    replacement = f'<span style="{COUPANG_CARD_CTA_STYLE}">{html.escape(cta_text)}</span>'
    updated, count = pattern.subn(replacement, card_html, count=1)
    if count:
        return updated
    return card_html.replace("</span></a>", f'<span style="{COUPANG_CARD_CTA_STYLE}">{html.escape(cta_text)}</span></span></a>', 1)


def _patch_product_card(card_html: str, product: dict) -> str:
    link = product["coupang_partners_link"]
    image_url = product["coupang_product_image_url"]
    name = product.get("product_name") or "상품"

    def _patch_anchor(match: re.Match) -> str:
        tag = _set_html_attr(match.group(0), "href", link)
        tag = _set_html_attr(tag, "target", "_blank")
        tag = _set_html_attr(tag, "rel", _affiliate_rel_value(_html_attr_value(tag, "rel")))
        tag = _set_html_attr(tag, "style", COUPANG_CARD_LINK_STYLE)
        return tag

    card_html = re.sub(r"<a\b[^>]*>", _patch_anchor, card_html, count=1, flags=re.IGNORECASE | re.DOTALL)

    def _patch_img(match: re.Match) -> str:
        tag = _set_html_attr(match.group(0), "src", image_url)
        tag = _set_html_attr(tag, "alt", name)
        tag = _set_html_attr(tag, "style", COUPANG_CARD_IMAGE_STYLE)
        return tag

    card_html = re.sub(r"<img\b[^>]*>", _patch_img, card_html, count=1, flags=re.IGNORECASE | re.DOTALL)
    card_html = _replace_product_name_area(card_html, product.get("product_name", ""))
    card_html = _replace_price_area(card_html, product.get("product_price", ""))
    card_html = _replace_cta_area(card_html, product.get("cta_text", ""))
    return card_html


def _insert_product_cards(html_body: str, cards_html: str) -> str:
    if PRODUCT_CARD_PLACEHOLDER in html_body:
        _log_html_image("상품 카드 placeholder 위치 삽입 완료")
        return html_body.replace(PRODUCT_CARD_PLACEHOLDER, cards_html, 1)

    h2_re = re.compile(r"<h2\b[^>]*>.*?(상품|추천|비교|쿠팡).*?</h2>", flags=re.IGNORECASE | re.DOTALL)
    h2_match = h2_re.search(html_body)
    if h2_match:
        _log_html_image("상품 비교/추천 h2 섹션 아래 상품 카드 삽입 완료")
        return html_body[:h2_match.end()] + "\n" + cards_html + "\n" + html_body[h2_match.end():]

    summary_re = re.compile(r"<h2\b[^>]*>.*?(요약|정리|마무리|결론).*?</h2>", flags=re.IGNORECASE | re.DOTALL)
    summary_match = summary_re.search(html_body)
    if summary_match:
        _log_html_image("본문 하단 요약 섹션 직전 상품 카드 삽입 완료")
        return html_body[:summary_match.start()] + cards_html + "\n" + html_body[summary_match.start():]

    last_p = None
    for last_p in re.finditer(r"<p\b[^>]*>.*?</p>", html_body, flags=re.IGNORECASE | re.DOTALL):
        pass
    if last_p:
        _log_html_image("본문 마지막 문단 뒤 상품 카드 삽입 완료")
        return html_body[:last_p.end()] + "\n" + cards_html + "\n" + html_body[last_p.end():]

    _log_html_image("본문 마지막에 상품 카드 삽입 완료")
    return html_body.rstrip() + "\n" + cards_html + "\n"


def _apply_products_to_html(html_body: str, products: list[dict]) -> str:
    valid_products = _validated_products(products)
    if not valid_products:
        if PRODUCT_CARD_PLACEHOLDER in html_body:
            html_body = html_body.replace(PRODUCT_CARD_PLACEHOLDER, "")
        return html_body

    card_matches = _iter_product_card_anchors(html_body)
    if card_matches:
        updated_parts = []
        cursor = 0
        for idx, match in enumerate(card_matches):
            updated_parts.append(html_body[cursor:match.start()])
            if idx < len(valid_products):
                updated_parts.append(_patch_product_card(match.group(0), valid_products[idx]))
                _log_html_image(f"상품 {idx + 1} 카드 href/src 교체 완료")
            else:
                updated_parts.append(match.group(0))
            cursor = match.end()
        updated_parts.append(html_body[cursor:])
        html_body = "".join(updated_parts)
        if PRODUCT_CARD_PLACEHOLDER in html_body:
            html_body = html_body.replace(PRODUCT_CARD_PLACEHOLDER, "")
        return html_body

    cards_html = "\n".join(_build_product_card_html(product) for product in valid_products)
    return _insert_product_cards(html_body, cards_html)


def _ensure_all_img_alt(html_body: str) -> str:
    def _ensure(match: re.Match) -> str:
        img_tag = match.group(0)
        if not _html_attr_value(img_tag, "alt").strip():
            img_tag = _set_html_attr(img_tag, "alt", "이미지")
        return img_tag

    updated = re.sub(r"<img\b[^>]*>", _ensure, html_body, flags=re.IGNORECASE | re.DOTALL)
    _log_html_image("모든 img alt 검증 완료")
    return updated


def _validate_final_html(html_body: str, expect_product_cards: bool = True) -> None:
    data_image_match = re.search(
        r'<img\b[^>]*\ssrc=(["\'])data:image/(?:png|jpeg|webp);base64,([A-Za-z0-9+/=]+)\1',
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not data_image_match or not data_image_match.group(2):
        _error_html_image("본문 대표 이미지 src에 base64 data URI가 없음")
        raise ValueError("missing main base64 image src")

    card_matches = _iter_product_card_anchors(html_body)
    if expect_product_cards and not card_matches:
        _error_html_image("검증 가능한 상품 카드가 없음")
        raise ValueError("missing product card")

    for idx, match in enumerate(card_matches, 1):
        card_html = match.group(0)
        a_tag = re.search(r"<a\b[^>]*>", card_html, flags=re.IGNORECASE | re.DOTALL).group(0)
        href = _html_attr_value(a_tag, "href")
        target = _html_attr_value(a_tag, "target")
        rel = _html_attr_value(a_tag, "rel")
        img_match = re.search(r"<img\b[^>]*>", card_html, flags=re.IGNORECASE | re.DOTALL)
        if not _is_valid_coupang_link(href):
            _error_html_image(f"상품 카드 {idx} href에 허용된 쿠팡 링크가 없음: {href}")
            raise ValueError("invalid product href")
        if target != "_blank":
            _error_html_image(f"상품 카드 {idx} target=\"_blank\" 누락")
            raise ValueError("missing product target")
        rel_tokens = set(re.split(r"\s+", rel.lower()))
        if not {"sponsored", "nofollow"}.issubset(rel_tokens):
            _error_html_image(f"상품 카드 {idx} rel 속성 오류: {rel}")
            raise ValueError("invalid product rel")
        if not img_match:
            _error_html_image(f"상품 카드 {idx} img 태그 누락")
            raise ValueError("missing product img")
        image_src = _html_attr_value(img_match.group(0), "src")
        if not _is_valid_coupang_image_url(image_src):
            _error_html_image(f"상품 카드 {idx} 이미지 src가 쿠팡 이미지 URL이 아님: {image_src}")
            raise ValueError("invalid product image src")

    for img_tag in re.findall(r"<img\b[^>]*>", html_body, flags=re.IGNORECASE | re.DOTALL):
        if not _html_attr_value(img_tag, "alt").strip():
            _error_html_image(f"alt 속성이 없는 img 태그 발견: {img_tag[:120]}")
            raise ValueError("missing image alt")

    unresolved = [token for token in UNRESOLVED_HTML_PLACEHOLDERS if token in html_body]
    if unresolved:
        _error_html_image(f"최종 HTML에 미처리 placeholder가 남아 있음: {', '.join(unresolved)}")
        raise ValueError("unresolved placeholders")
    _log_html_image("미처리 placeholder 없음")


def process_html_images_file(
    html_input_path: Path,
    html_output_path: Path,
    main_image_path: Path,
    product_data_path: Path,
    image_alt_text: str = "본문 대표 이미지",
    image_caption: str = "",
) -> None:
    if not html_input_path.exists():
        _error_html_image(f"HTML_INPUT_PATH 파일을 찾을 수 없음: {html_input_path}")
        raise FileNotFoundError(str(html_input_path))
    _log_html_image(f"HTML 입력 파일 확인 완료: {html_input_path}")
    html_body = html_input_path.read_text(encoding="utf-8")
    data_uri = _read_main_image_as_data_uri(main_image_path)
    products = _load_product_json(product_data_path)

    html_body = _apply_main_image_to_html(html_body, data_uri, image_alt_text, image_caption)
    html_body = _apply_products_to_html(html_body, products)
    html_body = ensure_exact_coupang_disclosure(html_body)
    html_body = _ensure_coupang_editorial_note(html_body, products)
    html_body = _enforce_coupang_affiliate_link_attrs(html_body)
    html_body = _dedupe_coupang_affiliate_links(html_body)
    _validate_coupang_affiliate_link_attrs(html_body)
    _validate_coupang_affiliate_link_count(html_body, products)
    validate_coupang_quality_content(html_body, products)
    html_body = _ensure_all_img_alt(html_body)
    _validate_final_html(html_body, expect_product_cards=bool(_validated_products(products, emit_logs=False)))

    html_output_path.parent.mkdir(parents=True, exist_ok=True)
    html_output_path.write_text(html_body, encoding="utf-8")
    _log_html_image(f"최종 HTML 저장 완료: {html_output_path}")



def download_image_as_base64(driver: webdriver.Chrome, url: str, max_retries: int = 3) -> str:
    """ChatGPT 세션을 이용해 이미지 data URL을 직접 다운로드합니다."""
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
    image_path = TISTORY_ONE_TIME_IMAGE_DIR / f"tistory_once_{timestamp}_{slot_idx}.{ext}"
    image_path.write_bytes(base64.b64decode(encoded))
    print(f"[Tistory] 업로드용 일회성 이미지 저장 완료: {image_path}")
    return image_path


def _copy_image_file_to_clipboard(image_path: Path) -> None:
    """Windows PowerShell을 사용하여 이미지를 OS 클립보드에 복사합니다."""
    safe_img_path = str(image_path).replace("\\", "/")
    ps_script = f'''
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $src = [System.Drawing.Image]::FromFile("{safe_img_path}")
    $bmp = New-Object System.Drawing.Bitmap $src
    $src.Dispose()
    [System.Windows.Forms.Clipboard]::SetImage($bmp)
    $bmp.Dispose()
    '''
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, check=True)


def _select_token_in_basic_editor(driver: webdriver.Chrome, token: str) -> bool:
    """기본모드(WYSIWYG)에서 특정 텍스트 토큰을 찾아 블록(선택) 지정합니다."""
    return bool(driver.execute_script(
        """
        const token = arguments[0];
        const candidates = Array.from(document.querySelectorAll(
            '.editor-body, .contents_style, [contenteditable="true"]'
        )).filter(el => {
            const text = el.innerText || el.textContent || '';
            const rect = el.getBoundingClientRect();
            return text.includes(token) && rect.width > 0 && rect.height > 0;
        });
        const editorBody = candidates[0];
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
        raise RuntimeError(f"기본모드에서 이미지 슬롯({token})을 찾지 못했습니다.")

    _copy_image_file_to_clipboard(image_path)
    random_sleep(0.5, 1.0)
    ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
    print(f"[Tistory] 이미지 위치({token})에 붙여넣기 성공. 카카오 CDN 업로드 대기중...")
    random_sleep(4.0, 6.0)  # 티스토리 서버가 이미지를 업로드하고 태그를 렌더링할 시간을 보장합니다.


def _type_human(element, text: str) -> None:
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.01, 0.04))


def _normalize_tags(tags) -> list[str]:
    raw = tags.replace(",", " ").split() if isinstance(tags, str) else list(tags)
    normalized = []
    seen = set()
    for item in raw:
        tag = re.sub(r"[^0-9A-Za-z가-힣_+-]", "", item.strip().lstrip("#"))
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized


def _find_tistory_tag_input(driver: webdriver.Chrome, timeout: int = 15):
    xpaths = [
        TISTORY_TAG_XPATH,
        '//input[@id="tagText"]',
        '//input[contains(@placeholder, "태그")]',
        '//input[contains(@placeholder, "태그를 입력")]',
        '//input[contains(@class, "tag")]',
        '//input[contains(@name, "tag")]',
    ]
    end_at = time.time() + timeout
    last_error = None
    _scroll_to_tistory_tags(driver)
    while time.time() < end_at:
        for xpath in xpaths:
            try:
                for el in driver.find_elements(By.XPATH, xpath):
                    if el.is_displayed() and el.is_enabled():
                        return el
            except Exception as exc:
                last_error = exc
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
    raise TimeoutException(f"태그 입력창을 찾지 못했습니다. last_error={last_error}")


def _input_tistory_tags(driver: webdriver.Chrome, tags) -> None:
    tag_list = _normalize_tags(tags)[:10]
    print(f"[Tistory] 해시태그 입력 중... ({len(tag_list)}개)")
    if not tag_list:
        print("[경고] 입력할 해시태그가 없습니다.")
        return

    try:
        print("[Tistory] 사진 삽입 후 맨 아래로 스크롤하여 해시태그 입력칸을 찾는 중...")
        _scroll_tistory_to_page_bottom(driver)
        _scroll_to_tistory_tags(driver)
        tag_el = _find_tistory_tag_input(driver, timeout=15)
    except Exception as e:
        print(f"[경고] 해시태그 입력창 대기 실패. 태그 없이 진행: {e}")
        return

    for tag in tag_list:
        try:
            if not tag_el.is_displayed() or not tag_el.is_enabled():
                tag_el = _find_tistory_tag_input(driver, timeout=5)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tag_el)
            random_sleep(0.2, 0.4)
            driver.execute_script("arguments[0].click();", tag_el)
            random_sleep(0.1, 0.2)
            tag_el.send_keys(tag)
            random_sleep(0.15, 0.3)
            tag_el.send_keys(Keys.ENTER)
            random_sleep(0.5, 0.9)
            print(f"[Tistory] 태그 입력 완료: {tag}")
        except Exception as e:
            print(f"[경고] 태그 '{tag}' 입력 실패: {e}")
            try:
                tag_el = _find_tistory_tag_input(driver, timeout=5)
            except Exception:
                pass


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
    """티스토리 에디터 또는 완료 레이어의 임시저장 버튼을 클릭합니다."""
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


def _close_tistory_publish_layer(driver: webdriver.Chrome) -> None:
    close_xpaths = [
        '//*[self::button or self::a][contains(@class, "btn_close")]',
        '//*[self::button or self::a][contains(@aria-label, "닫기")]',
        '//*[self::button or self::a][normalize-space()="취소"]',
    ]
    for xpath in close_xpaths:
        try:
            _wait_and_click_xpath_with_js_fallback(driver, xpath, timeout=3)
            random_sleep(0.5, 1.0)
            return
        except Exception:
            continue
    try:
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        random_sleep(0.5, 1.0)
    except Exception:
        pass


def _save_draft_with_representative_image(driver: webdriver.Chrome, image_path: Path | None) -> None:
    if image_path:
        print("[Tistory] 임시저장 전 대표이미지 지정 중...")
        _wait_and_click_xpath_with_js_fallback(driver, '//*[@id="publish-layer-btn"]', timeout=10)
        random_sleep(1.0, 1.5)
        _upload_representative_image_in_publish_layer(driver, image_path)
        try:
            print("[Tistory] 대표이미지 지정 후 임시저장 버튼 클릭 중...")
            _click_tistory_draft_save(driver)
            return
        except Exception as exc:
            print(f"[경고] 완료 레이어에서 임시저장 버튼 클릭 실패. 레이어를 닫고 에디터 임시저장을 시도합니다: {exc}")
            _close_tistory_publish_layer(driver)
    else:
        print("[경고] 대표이미지로 지정할 사진 파일이 없어 임시저장만 진행합니다.")

    print("[Tistory] 임시저장 버튼 클릭 중...")
    _click_tistory_draft_save(driver)


def _upload_representative_image_in_publish_layer(driver: webdriver.Chrome, image_path: Path) -> None:
    """발행 레이어의 '대표이미지 추가' input.inp_g에 같은 이미지 파일을 지정합니다."""
    print("[Tistory] 발행창 대표이미지 추가 input 대기 중...")

    def _find_representative_input(timeout: float = 5.0):
        input_xpaths = [
            '//input[@type="file" and contains(concat(" ", normalize-space(@class), " "), " inp_g ") and contains(@accept, "image")]',
            '//input[@type="file" and contains(@class, "inp_g") and contains(@accept, "image")]',
        ]
        last_error = None
        end_at = time.time() + timeout
        while time.time() < end_at:
            for xpath in input_xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xpath)
                    if elements:
                        return elements[0], last_error
                except Exception as exc:
                    last_error = exc
            time.sleep(0.3)
        return None, last_error

    input_el, last_error = _find_representative_input(timeout=4.0)
    if not input_el:
        add_button_xpaths = [
            '//*[self::button or self::a or self::label or self::div or self::span][contains(normalize-space(), "대표이미지") and contains(normalize-space(), "추가")]',
            '//*[self::button or self::a or self::label or self::div or self::span][contains(normalize-space(), "대표 이미지") and contains(normalize-space(), "추가")]',
        ]
        clicked_add_button = False
        for xpath in add_button_xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if not element.is_displayed():
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
                    random_sleep(0.2, 0.4)
                    driver.execute_script("arguments[0].click();", element)
                    random_sleep(0.5, 1.0)
                    clicked_add_button = True
                    break
                if clicked_add_button:
                    break
            except Exception as exc:
                last_error = exc
        input_el, last_error = _find_representative_input(timeout=10.0)

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


def _select_tistory_category(driver: webdriver.Chrome, category_name: str) -> None:
    print(f"[Tistory] '{category_name}' 카테고리 선택 시도...")
    try:
        category_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "category-btn"))
        )

        if category_name in category_btn.text:
            print(f"[Tistory] '{category_name}' 카테고리가 이미 선택되어 있습니다. 스킵합니다.")
            return

        print(f"[Tistory] 카테고리 메뉴 여는 중...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", category_btn)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", category_btn)
        random_sleep(0.5, 1.0)

        print(f"[Tistory] '{category_name}' 항목 클릭 중...")
        item_xpath = f'//*[starts-with(@id, "category-item-") and contains(., "{category_name}")]'
        item_el = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, item_xpath))
        )
        driver.execute_script("arguments[0].click();", item_el)
        print(f"[Tistory] 카테고리 클릭 완료: {category_name}")
        random_sleep(0.5, 1.0)

    except Exception as e:
        print(f"[경고] 카테고리 선택 실패 (기본값으로 진행): {e}")


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
        textarea.click()
        time.sleep(random.uniform(0.2, 0.4))
        _clear_input_like_human(textarea)
        textarea.send_keys(html_body)

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


def _image_token_paragraph(token: str) -> str:
    return f'<p style="text-align:center; margin:24px 0;">{token}</p>'


def ensure_image_placeholders_for_native_paste(
    html_body: str,
    image_slots: list[tuple[str, str, int]],
) -> str:
    """
    티스토리 기본 에디터에서 이미지를 붙여넣을 수 있도록 텍스트 토큰을 보장합니다.
    img src 안의 토큰은 기본모드에서 선택할 수 없고 깨진 이미지로 보일 수 있어
    독립된 p 태그 텍스트로 바꿉니다.
    """
    if not image_slots:
        return html_body

    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")

    prepend_tokens: list[str] = []
    for token, _data_url, _slot_idx in image_slots:
        token_html = _image_token_paragraph(token)

        html_body, figure_count = re.subn(
            rf'<figure[^>]*>.*?{re.escape(token)}.*?</figure>',
            token_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_body, img_count = re.subn(
            rf'<img[^>]*{re.escape(token)}[^>]*>',
            token_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if token not in html_body:
            prepend_tokens.append(token)
            continue

        if figure_count or img_count:
            print(f"[Tistory] {token} 이미지 태그를 붙여넣기용 텍스트 슬롯으로 변환했습니다.")

    if prepend_tokens:
        html_body = "\n".join(_image_token_paragraph(token) for token in prepend_tokens) + "\n" + html_body
        print(f"[Tistory] 누락된 이미지 placeholder {len(prepend_tokens)}개를 본문 상단에 자동 삽입했습니다.")

    return html_body


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


def _upload_image_in_tistory_html_mode(driver: webdriver.Chrome, image_path: Path) -> str:
    _switch_tistory_editor_mode_strict(driver, "html")
    _set_tistory_html_body(driver, "")
    random_sleep(0.4, 0.8)
    _focus_tistory_html_body(driver)
    random_sleep(0.2, 0.4)

    input_el = _open_tistory_image_file_input(driver)
    if not input_el:
        raise RuntimeError("HTML 모드에서 티스토리 이미지 업로드 input을 찾지 못했습니다.")

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

    started_at = time.time()
    last_value = ""
    while time.time() - started_at < 60:
        value = _get_tistory_html_body_value(driver).strip()
        if value and value != last_value:
            last_value = value
            if _looks_like_tistory_image_fragment(value):
                print(f"[Tistory] HTML 모드 이미지 업로드 조각 확보: {_display_length_for_log(value)}자")
                return value
        time.sleep(1)

    raise TimeoutError("HTML 모드 이미지 업로드 결과를 확인하지 못했습니다.")


def replace_image_placeholders_with_html_fragments(
    html_body: str,
    title: str,
    image_fragments: list[tuple[str, str]],
) -> str:
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")

    fragment_map = {token: fragment.strip() for token, fragment in image_fragments if fragment.strip()}
    if fragment_map.get("%%IMAGE1_PLACEHOLDER%%") and "%%IMAGE1_PLACEHOLDER%%" not in html_body:
        html_body = fragment_map["%%IMAGE1_PLACEHOLDER%%"] + "\n" + html_body
        print("[Tistory] IMAGE1 placeholder가 없어 상단에 업로드 이미지 조각을 삽입했습니다.")

    for token, fragment in fragment_map.items():
        if token not in html_body:
            continue
        html_body, figure_count = re.subn(
            rf'<figure[^>]*>.*?{re.escape(token)}.*?</figure>',
            fragment,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_body, img_count = re.subn(
            rf'<img[^>]*{re.escape(token)}[^>]*>',
            fragment,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not figure_count and not img_count:
            html_body = html_body.replace(token, fragment)
        print(f"[Tistory] HTML 이미지 조각 치환 완료: {token}")

    for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%"):
        if token in html_body:
            html_body = _strip_broken_image_placeholder_tags(html_body, token)

    return html_body


def replace_image_placeholders_with_data_urls(
    html_body: str,
    image_data_urls: list[tuple[str, str]],
) -> str:
    """HTML 모드 주입 전 이미지 토큰을 data URL로 직접 치환합니다."""
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")

    for token, data_url in image_data_urls:
        if not data_url:
            html_body = _strip_broken_image_placeholder_tags(html_body, token)
            continue
        if token in html_body:
            html_body = html_body.replace(token, data_url)
            print(f"[Tistory] 이미지 data URL 치환 완료: {token}")
        else:
            print(f"[경고] HTML에서 이미지 placeholder를 찾지 못함: {token}")

    for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%"):
        if token in html_body:
            html_body = _strip_broken_image_placeholder_tags(html_body, token)
    return html_body


TISTORY_NATIVE_IMAGE_MARKER = "__TISTORY_NATIVE_IMAGE_SLOT_1__"


def _marker_paragraph(marker: str = TISTORY_NATIVE_IMAGE_MARKER) -> str:
    return f'<p style="text-align:center; margin:24px 0;">{marker}</p>'


def _remove_generated_image_placeholders(html_body: str) -> str:
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")
    for token in ("%%IMAGE1_PLACEHOLDER%%", "%%IMAGE2_PLACEHOLDER%%"):
        html_body = _strip_broken_image_placeholder_tags(html_body, token)
    return html_body


def _insert_native_image_marker_after_first_coupang_link(
    html_body: str,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> str:
    marker_html = _marker_paragraph(marker)
    if marker in html_body:
        return html_body
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")

    if "%%IMAGE1_PLACEHOLDER%%" in html_body:
        html_body, figure_count = re.subn(
            rf'<figure[^>]*>.*?{re.escape("%%IMAGE1_PLACEHOLDER%%")}.*?</figure>',
            marker_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_body, img_count = re.subn(
            rf'<img[^>]*{re.escape("%%IMAGE1_PLACEHOLDER%%")}[^>]*>',
            marker_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not figure_count and not img_count:
            html_body = html_body.replace("%%IMAGE1_PLACEHOLDER%%", marker_html, 1)
        html_body = _strip_broken_image_placeholder_tags(html_body, "%%IMAGE2_PLACEHOLDER%%")
        print("[Tistory] 쿠팡글 사진 업로드 마커를 본문 placeholder 위치에 배치했습니다.")
        return html_body

    html_body = _remove_generated_image_placeholders(html_body)

    coupang_anchor_pattern = re.compile(
        r'<a\b(?=[^>]*href=["\']https?://(?:link\.coupang\.com|www\.coupang\.com|coupa\.ng)[^"\']*["\'])[^>]*>.*?</a>',
        re.IGNORECASE | re.DOTALL,
    )
    match = coupang_anchor_pattern.search(html_body)
    if not match:
        raise RuntimeError("첫 번째 쿠팡 링크를 찾지 못해 이미지 삽입 위치를 결정할 수 없습니다.")

    print("[Tistory] 첫 번째 쿠팡 링크 아래에 사진 업로드 마커를 삽입했습니다.")
    return html_body[:match.end()] + "\n" + marker_html + "\n" + html_body[match.end():]


def _insert_native_image_marker_for_daily(
    html_body: str,
    marker: str = TISTORY_NATIVE_IMAGE_MARKER,
) -> str:
    html_body = html_body.replace("[BASE64_IMAGE_1]", "%%IMAGE1_PLACEHOLDER%%")
    html_body = html_body.replace("[BASE64_IMAGE_2]", "%%IMAGE2_PLACEHOLDER%%")
    marker_html = _marker_paragraph(marker)

    if "%%IMAGE1_PLACEHOLDER%%" in html_body:
        html_body, figure_count = re.subn(
            rf'<figure[^>]*>.*?{re.escape("%%IMAGE1_PLACEHOLDER%%")}.*?</figure>',
            marker_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        html_body, img_count = re.subn(
            rf'<img[^>]*{re.escape("%%IMAGE1_PLACEHOLDER%%")}[^>]*>',
            marker_html,
            html_body,
            count=1,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not figure_count and not img_count:
            html_body = html_body.replace("%%IMAGE1_PLACEHOLDER%%", marker_html, 1)

    html_body = _strip_broken_image_placeholder_tags(html_body, "%%IMAGE2_PLACEHOLDER%%")
    if marker not in html_body:
        html_body = marker_html + "\n" + html_body
    print("[Tistory] 일상글 사진 업로드 마커를 본문에 배치했습니다.")
    return html_body


def _prepare_html_for_native_tistory_image_upload(html_body: str, post_type: str, has_image: bool) -> str:
    if not has_image:
        return _remove_generated_image_placeholders(html_body)
    if post_type == "coupang":
        return _insert_native_image_marker_after_first_coupang_link(html_body)
    return _insert_native_image_marker_for_daily(html_body)


def _count_images_in_tistory_basic_editor(driver: webdriver.Chrome) -> int:
    try:
        value = driver.execute_script(
            """
            const roots = Array.from(document.querySelectorAll(
              '.editor-body, .contents_style, [contenteditable="true"]'
            )).filter(el => {
              const rect = el.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0;
            });
            const root = roots[0] || document;
            return root.querySelectorAll('img').length;
            """
        )
        return int(value or 0)
    except Exception:
        return 0


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


def write_tistory_html_post(
    driver: webdriver.Chrome,
    title: str,
    html_body: str,
    tags,
    post_type: str = "coupang",
    publish: bool = False,
    image1_data_url: str = "",
    image2_data_url: str = "",
) -> None:
    """Tistory HTML editor flow: HTML mode -> title -> body -> tags -> publish."""

    if post_type == "coupang":
        category_name = TISTORY_COUPANG_CATEGORY_NAME
    else:
        category_name = TISTORY_DAILY_CATEGORY_NAME

    print(f"[Tistory] 카테고리 선택 중... (type={post_type}, name={category_name})")
    _select_tistory_category(driver, category_name)
    random_sleep(0.6, 1.2)

    print("[Tistory] HTML 모드 전환 중...")
    _switch_tistory_editor_mode_strict(driver, "html")

    if "clean_generated_html_body" in globals():
        html_body = clean_generated_html_body(html_body)
    if post_type == "coupang":
        html_body = _enforce_coupang_affiliate_link_attrs(html_body)
        html_body = _dedupe_coupang_affiliate_links(html_body)
        _validate_coupang_affiliate_link_attrs(html_body)
        _validate_coupang_affiliate_link_count(html_body)

    temp_image_paths = []
    image_path = None
    if image1_data_url:
        image_path = _write_temp_image_from_src(image1_data_url, 1)
        if not image_path:
            raise RuntimeError("이미지 data URL을 일회성 업로드 파일로 변환하지 못했습니다.")
        temp_image_paths.append(image_path)
    elif image2_data_url:
        print("[경고] image1_data_url이 없어 image2_data_url을 사진 업로드에 사용합니다.")
        image_path = _write_temp_image_from_src(image2_data_url, 2)
        if not image_path:
            raise RuntimeError("이미지 data URL을 일회성 업로드 파일로 변환하지 못했습니다.")
        temp_image_paths.append(image_path)

    try:
        html_body = _prepare_html_for_native_tistory_image_upload(
            html_body,
            post_type=post_type,
            has_image=bool(image_path),
        )
        if not image_path:
            print("[경고] image_data_url이 없어 이미지 없이 본문만 입력합니다.")

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
        random_sleep(0.8, 1.5)

        if image_path:
            _upload_one_time_image_at_marker(driver, image_path)
            _remove_native_image_marker_after_upload(driver)

        _scroll_tistory_to_page_bottom(driver)
        _scroll_to_tistory_tags(driver)

        _input_tistory_tags(driver, tags)

        if publish:
            print("[Tistory] '완료' 버튼 클릭 중...")
            _wait_and_click_xpath_with_js_fallback(driver, '//*[@id="publish-layer-btn"]', timeout=10)
            random_sleep(1.0, 1.5)

            if image_path:
                _upload_representative_image_in_publish_layer(driver, image_path)
            else:
                print("[경고] 대표이미지로 지정할 사진 파일이 없어 발행창 대표이미지 추가를 건너뜁니다.")

            print("[Tistory] '공개 발행' 버튼 클릭 중...")
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
            print("[Tistory] 공개 발행 완료")
        else:
            _save_draft_with_representative_image(driver, image_path)
            print("[Tistory] 임시저장 완료")
    finally:
        for path in temp_image_paths:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass


def _read_product_rows() -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with PRODUCT_DB_PATH.open("r", newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with PRODUCT_DB_PATH.open("r", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def _clean(value, default: str = "") -> str:
    v = (value or "").strip()
    return v if v else default


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", newline="", encoding=enc) as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    with path.open("r", newline="", errors="replace") as f:
        return list(csv.DictReader(f))


def _coupang_topic_performance_csv_path() -> Path:
    raw_path = os.getenv("COUPANG_TOPIC_PERFORMANCE_CSV_PATH", "").strip()
    return Path(raw_path) if raw_path else COUPANG_TOPIC_PERFORMANCE_DEFAULT_CSV_PATH


def _coupang_topic_cooldown_days() -> int:
    raw_value = os.getenv("COUPANG_TOPIC_COOLDOWN_DAYS", "").strip()
    if not raw_value:
        return 14
    try:
        return max(0, int(float(raw_value)))
    except ValueError:
        return 14


def _normalize_coupang_topic_key(value: str) -> str:
    normalized = html.unescape(value or "").lower()
    normalized = re.sub(r"[^\w가-힣]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _coupang_topic_key(topic: dict | str | None) -> str:
    if not topic:
        return ""
    if isinstance(topic, dict):
        raw_value = topic.get("query") or topic.get("keyword") or topic.get("topic_key") or ""
    else:
        raw_value = str(topic)
    return _normalize_coupang_topic_key(raw_value)


def _load_coupang_topic_history() -> list[dict]:
    if not COUPANG_TOPIC_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(COUPANG_TOPIC_HISTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []

    history = []
    for item in data:
        if isinstance(item, str):
            key = _normalize_coupang_topic_key(item)
            if key:
                history.append({"topic_key": key, "query": item, "used_at": ""})
            continue
        if not isinstance(item, dict):
            continue
        key = _normalize_coupang_topic_key(
            item.get("topic_key") or item.get("query") or item.get("keyword") or ""
        )
        if not key:
            continue
        entry = dict(item)
        entry["topic_key"] = key
        history.append(entry)
    return history


def _parse_topic_used_at(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def _is_coupang_topic_in_cooldown(
    topic: dict | str | None,
    history: list[dict] | None = None,
    now: datetime | None = None,
) -> bool:
    cooldown_days = _coupang_topic_cooldown_days()
    if cooldown_days <= 0:
        return False
    key = _coupang_topic_key(topic)
    if not key:
        return False
    now = now or datetime.now()
    history = history if history is not None else _load_coupang_topic_history()
    for item in history:
        if item.get("topic_key") != key:
            continue
        used_at = _parse_topic_used_at(item.get("used_at", ""))
        if used_at is None:
            return True
        if now - used_at < timedelta(days=cooldown_days):
            return True
    return False


def _filter_coupang_topic_cooldown(candidates: list[dict]) -> list[dict]:
    cooldown_days = _coupang_topic_cooldown_days()
    if cooldown_days <= 0:
        return candidates
    history = _load_coupang_topic_history()
    if not history:
        return candidates
    now = datetime.now()
    available = [
        topic
        for topic in candidates
        if not _is_coupang_topic_in_cooldown(topic, history=history, now=now)
    ]
    skipped_count = len(candidates) - len(available)
    if skipped_count:
        print(f"[Topic] 최근 {cooldown_days}일 내 사용한 쿠팡 주제 {skipped_count}개 제외")
    if available:
        return available
    print(
        "[Topic] 모든 쿠팡 성과 후보가 쿨다운 중이라 최고점 후보를 재사용합니다. "
        "CSV 후보를 늘리거나 COUPANG_TOPIC_COOLDOWN_DAYS를 낮추면 반복을 더 줄일 수 있습니다."
    )
    return candidates


def mark_coupang_topic_as_used(topic: dict | None, post_title: str = "") -> Path | None:
    if not topic:
        return None
    key = _coupang_topic_key(topic)
    if not key:
        return None

    history = [item for item in _load_coupang_topic_history() if item.get("topic_key") != key]
    history.insert(
        0,
        {
            "topic_key": key,
            "query": topic.get("query", ""),
            "keyword": topic.get("keyword", ""),
            "category": topic.get("category", ""),
            "score": topic.get("score", 0),
            "used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "post_title": post_title,
            "source_csv": str(_coupang_topic_performance_csv_path()),
            "cooldown_days": _coupang_topic_cooldown_days(),
        },
    )
    COUPANG_TOPIC_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    COUPANG_TOPIC_HISTORY_PATH.write_text(
        json.dumps(history[:COUPANG_TOPIC_HISTORY_LIMIT], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[Topic] 쿠팡 주제 사용 이력 저장: {COUPANG_TOPIC_HISTORY_PATH}")
    return COUPANG_TOPIC_HISTORY_PATH


def _row_value(row: dict, keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _row_number(row: dict, keys: tuple[str, ...], default: float = 0.0) -> float:
    value = _row_value(row, keys, "")
    if not value:
        return default
    normalized = value.replace(",", "").replace("%", "").strip()
    try:
        return float(normalized)
    except ValueError:
        return default


def _split_keyword_terms(value: str) -> list[str]:
    raw_terms = re.split(r"[,;/|\\\n\r\t ]+", value or "")
    stopwords = {
        "추천",
        "비교",
        "구매",
        "가이드",
        "체크",
        "체크포인트",
        "기준",
        "정리",
        "후기",
        "리뷰",
        "쿠팡",
        "상품",
        "best",
        "top",
    }
    terms = []
    for term in raw_terms:
        cleaned = re.sub(r"^[^\w가-힣]+|[^\w가-힣]+$", "", term.lower()).strip()
        if len(cleaned) < 2 or cleaned in stopwords:
            continue
        if cleaned not in terms:
            terms.append(cleaned)
    return terms


def _is_disabled_performance_row(row: dict) -> bool:
    status = _row_value(row, ("disabled", "exclude", "제외", "사용중지", "status", "상태"), "").lower()
    return status in {"1", "y", "yes", "true", "disabled", "exclude", "excluded", "pause", "paused", "stop", "중지", "제외"}


def _performance_topic_score(row: dict) -> float:
    explicit = _row_number(row, ("priority", "우선순위", "score", "점수"), 0.0)
    clicks = _row_number(row, ("clicks", "클릭수", "검색클릭", "search_clicks"), 0.0)
    impressions = _row_number(row, ("impressions", "노출수", "검색노출", "search_impressions"), 0.0)
    ctr = _row_number(row, ("ctr", "CTR", "클릭률"), 0.0)
    position = _row_number(row, ("position", "avg_position", "평균순위", "게재순위", "순위"), 0.0)
    revenue = _row_number(row, ("revenue", "수익", "adsense_revenue", "coupang_revenue"), 0.0)
    coupang_clicks = _row_number(row, ("coupang_clicks", "쿠팡클릭", "affiliate_clicks"), 0.0)
    conversions = _row_number(row, ("conversion", "conversions", "전환", "구매", "orders", "주문수"), 0.0)

    ctr_score = ctr * (3 if ctr <= 1 else 0.3)
    position_score = max(0.0, 20.0 - position) * 1.5 if position > 0 else 0.0
    return (
        explicit * 10
        + clicks * 1.0
        + impressions * 0.02
        + ctr_score
        + position_score
        + revenue * 0.05
        + coupang_clicks * 2
        + conversions * 20
    )


def _build_coupang_performance_topic(row: dict) -> dict:
    query = _row_value(row, ("query", "queries", "검색어", "키워드", "keyword", "main_keyword", "topic", "주제"))
    category = _row_value(row, ("category", "카테고리", "product_category", "상품군"), "")
    include_keywords = _row_value(row, ("include_keywords", "product_keywords", "상품키워드", "포함키워드"), "")
    exclude_keywords = _row_value(row, ("exclude_keywords", "제외키워드"), "")
    terms = _split_keyword_terms(include_keywords) or _split_keyword_terms(query)
    return {
        "query": query,
        "keyword": _row_value(row, ("main_keyword", "keyword", "키워드"), query),
        "category": category,
        "pain_point": _row_value(row, ("pain_point", "문제상황", "독자고민", "search_intent", "검색의도"), f"{query} 선택 기준이 필요한 상황"),
        "target_reader": _row_value(row, ("target_reader", "타깃독자", "독자"), f"{query} 구매 전 비교하는 독자"),
        "usage_scenario": _row_value(row, ("usage_scenario", "사용상황", "사용장소", "상황"), f"{query} 구매 전 가격, 리뷰, 배송을 비교하는 상황"),
        "match_terms": terms,
        "exclude_terms": _split_keyword_terms(exclude_keywords),
        "score": _performance_topic_score(row),
        "source_row": row,
    }


def pick_coupang_topic_from_performance_csv() -> dict | None:
    path = _coupang_topic_performance_csv_path()
    rows = _read_csv_rows(path)
    if not rows:
        print(f"[Topic] 쿠팡 성과 CSV 없음 또는 비어 있음: {path}")
        return None

    candidates = []
    for row in rows:
        if _is_disabled_performance_row(row):
            continue
        topic = _build_coupang_performance_topic(row)
        if not topic["query"] or not topic["match_terms"]:
            continue
        candidates.append(topic)

    if not candidates:
        print(f"[Topic] 쿠팡 성과 CSV 유효 후보 없음: {path}")
        return None

    candidates.sort(key=lambda item: item["score"], reverse=True)
    candidates = _filter_coupang_topic_cooldown(candidates)
    chosen = candidates[0]
    print(f"[Topic] 쿠팡 성과 CSV 주제 선택: {chosen['query']} (score={chosen['score']:.2f})")
    return chosen


def _product_topic_match_score(product: dict, topic: dict | None) -> float:
    if not topic:
        return 0.0
    text = " ".join(
        _clean(product.get(key))
        for key in (
            "상품명",
            "키워드",
            "카테고리",
            "상품설명",
            "장점1",
            "장점2",
            "장점3",
            "주의점",
            "product_name",
            "keyword",
            "category",
            "description",
        )
        if _clean(product.get(key))
    ).lower()
    if not text:
        return 0.0
    if any(term in text for term in topic.get("exclude_terms", [])):
        return 0.0

    score = 0.0
    for term in topic.get("match_terms", []):
        if term in text:
            score += 3.0
    category = (topic.get("category") or "").lower().strip()
    if category and category in text:
        score += 2.0
    if _is_a_grade_row(product):
        score += 1.0
    return score


COUPANG_TOPIC_GENERIC_TERMS = {
    "추천",
    "비교",
    "구매",
    "상품",
    "제품",
    "기준",
    "선택",
    "가격",
    "리뷰",
    "배송",
    "설치",
    "옵션",
    "가성비",
    "고르는",
    "확인",
}


def _topic_relevance_terms(topic: dict | None) -> list[str]:
    if not topic:
        return []
    raw_terms: list[str] = []
    for key in ("query", "keyword", "category"):
        value = _clean(topic.get(key))
        if value:
            raw_terms.extend(_split_keyword_terms(value))
            raw_terms.extend(re.findall(r"[0-9A-Za-z가-힣]{2,}", value.lower()))
    raw_terms.extend(_clean(term).lower() for term in topic.get("match_terms", []) if _clean(term))

    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        term = term.strip().lower()
        if len(term) < 2 or term in COUPANG_TOPIC_GENERIC_TERMS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def _api_product_topic_relevance_score(product: dict, topic: dict | None) -> int:
    terms = _topic_relevance_terms(topic)
    if not terms:
        return 1
    text = " ".join(
        _clean(product.get(key))
        for key in (
            "상품명",
            "product_name",
            "name",
            "title",
            "상품설명",
            "description",
        )
        if _clean(product.get(key))
    ).lower()
    if not text:
        return 0
    return sum(1 for term in terms if term in text)


def _topic_api_supplemental_seed_rows(topic: dict | None) -> list[dict]:
    if not topic:
        return []

    queries: list[str] = []
    seen: set[str] = set()

    def add_query(value: str) -> None:
        value = re.sub(r"\s+", " ", _clean(value)).strip()
        key = value.lower()
        if len(value) < 2 or key in seen:
            return
        seen.add(key)
        queries.append(value)

    query = _clean(topic.get("query"))
    keyword = _clean(topic.get("keyword"))
    category = _clean(topic.get("category"))
    terms = _topic_relevance_terms(topic)

    add_query(query)
    add_query(keyword)
    if category and query:
        add_query(f"{category} {query}")
    if terms:
        add_query(" ".join(terms[:4]))
        add_query(" ".join(terms[:3]))

    # DB가 소진된 상태에서도 한 주제에서 여러 API 후보를 받을 수 있게
    # 같은 의도의 구매형 검색어를 소량 확장한다.
    for base_query in list(queries):
        for suffix in ("추천", "비교", "가격", "리뷰", "로켓배송"):
            add_query(f"{base_query} {suffix}")

    if "에어컨" in terms or "에어컨" in query or "에어컨" in keyword:
        for candidate in (
            "벽걸이 인버터 에어컨",
            "6평 벽걸이 에어컨",
            "9평 벽걸이 에어컨",
            "소형 벽걸이 에어컨",
            "인버터 에어컨 방문설치",
            "가정용 벽걸이 에어컨",
        ):
            add_query(candidate)

    rows: list[dict] = []
    for value in queries:
        rows.append(
            {
                "상품명": value,
                "키워드": value,
                "카테고리": category,
                "추천등급": "A",
                "장점1": "같은 주제 안에서 가격과 옵션을 비교하기 위한 API 보강 후보",
                "장점2": "리뷰 수와 배송 조건을 함께 확인하기 좋음",
                "장점3": "주제 매칭 상품이 부족할 때 비교 후보를 넓히기 위한 검색어",
                "주의점": "최종 상품명과 상세 옵션은 쿠팡 상세페이지에서 다시 확인 필요",
            }
        )
    return rows


def _canonical_coupang_url(raw_url: str) -> str:
    value = html.unescape(raw_url or "").strip()
    match = re.search(r"https?://[^\s\"'<>]+", value)
    if match:
        value = match.group(0)
    value = value.strip().strip(".,);]}'\"")
    return value.replace("&amp;", "&")


def _coupang_product_key(raw_url: str) -> str:
    url = _canonical_coupang_url(raw_url)
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    query = urllib.parse.parse_qs(parsed.query)

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


def _row_coupang_key(row: dict) -> str:
    return _coupang_product_key(
        row.get("쿠팡링크")
        or row.get("coupang_partners_link")
        or row.get("product_url")
        or row.get("url")
        or ""
    )


def _product_name_key(row: dict) -> tuple[str, str]:
    return (_clean(row.get("상품명") or row.get("product_name")), _clean(row.get("키워드")))


def _is_a_grade_row(row: dict) -> bool:
    grade = _clean(row.get("추천등급") or row.get("등급"))
    return grade == "A"


def _is_already_posted_row(row: dict) -> bool:
    used = _clean(row.get("used")).upper()
    post_title = _clean(row.get("post_title"))
    return used == "Y" or bool(post_title)


def _ordered_available_product_rows(performance_topic: dict | None = None) -> list[dict]:
    all_rows = _read_product_rows()
    used_url_keys = _load_used_coupang_url_keys()
    unused_rows = [
        r for r in all_rows
        if not _is_already_posted_row(r) and _row_coupang_key(r) not in used_url_keys
    ]
    a_grade_rows = [r for r in unused_rows if _is_a_grade_row(r)]
    fallback_rows = [r for r in unused_rows if not _is_a_grade_row(r)]
    available_rows = a_grade_rows + fallback_rows

    rows = available_rows
    if performance_topic:
        scored_rows = [
            (_product_topic_match_score(row, performance_topic), idx, row)
            for idx, row in enumerate(available_rows)
        ]
        matched_rows = [
            (score, idx, row)
            for score, idx, row in scored_rows
            if score > 0
        ]
        if len(matched_rows) >= 2:
            performance_topic["_product_match_failed"] = False
            matched_rows.sort(key=lambda item: (-item[0], item[1]))
            matched_keys = {_row_coupang_key(row) or _product_name_key(row) for _, _, row in matched_rows}
            fill_rows = [
                row for row in available_rows
                if (_row_coupang_key(row) or _product_name_key(row)) not in matched_keys
            ]
            rows = [row for _, _, row in matched_rows] + fill_rows
            print(
                f"[Products] 성과 주제 매칭 상품 우선 선택: "
                f"{performance_topic.get('query')} / 후보 {len(matched_rows)}개"
            )
        else:
            performance_topic["_product_match_failed"] = True
            print(
                f"[Products] 성과 주제 매칭 상품이 부족해 기존 상품 선택으로 fallback: "
                f"{performance_topic.get('query')} / 후보 {len(matched_rows)}개"
            )

    return rows


def select_products(count: int = 3, performance_topic: dict | None = None) -> list[dict]:
    rows = _ordered_available_product_rows(performance_topic)
    products = rows[:count]
    if len(products) < 2:
        raise ValueError("비교 상품은 최소 2개 이상 필요합니다.")
    print(f"[Products] 사용 이력이 없는 상품 후보 선택 완료: {len(products)}개")
    return products


def mark_products_as_used(products: list[dict], post_title: str = "") -> None:
    rows = _read_product_rows()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_name_keys = {_product_name_key(p) for p in products}
    target_url_keys = {_row_coupang_key(p) for p in products if _row_coupang_key(p)}
    matched = 0

    if (not target_name_keys and not target_url_keys) or not rows:
        return

    for row in rows:
        row_name_key = _product_name_key(row)
        row_url_key = _row_coupang_key(row)
        if row_name_key in target_name_keys or (row_url_key and row_url_key in target_url_keys):
            was_unused = (row.get("used") or "").strip() == ""
            row["used"] = "Y"
            if was_unused or not _clean(row.get("used_at")):
                row["used_at"] = now
            if post_title:
                row["post_title"] = post_title
            matched += 1

    fieldnames = list(rows[0].keys())
    for field in ("used", "used_at", "post_title"):
        if field not in fieldnames:
            fieldnames.append(field)
    with PRODUCT_DB_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[Products] 사용 처리 완료: {matched}개 / 제목={post_title or '-'}")


def _choose_unused_enriched_products(
    seed_products: list[dict],
    enriched_products: list[dict],
    count: int = 3,
) -> tuple[list[dict], list[dict]]:
    used_url_keys = _load_used_coupang_url_keys()
    chosen_seed_products: list[dict] = []
    chosen_enriched_products: list[dict] = []
    seen_keys: set[str] = set()

    for seed, enriched in zip(seed_products, enriched_products):
        product_key = _row_coupang_key(enriched) or _row_coupang_key(seed)
        if product_key and product_key in used_url_keys:
            print(f"[Products] 이미 사용된 쿠팡 상품 제외: {enriched.get('상품명') or seed.get('상품명') or product_key}")
            continue
        if product_key and product_key in seen_keys:
            print(f"[Products] 이번 실행 내 중복 쿠팡 상품 제외: {enriched.get('상품명') or seed.get('상품명') or product_key}")
            continue
        if product_key:
            seen_keys.add(product_key)
        chosen_seed_products.append(seed)
        chosen_enriched_products.append(enriched)
        if len(chosen_enriched_products) >= count:
            break

    if len(chosen_enriched_products) < 2:
        print(
            "[Products] 사용 가능한 쿠팡 API 보강 상품이 2개 미만입니다. "
            f"seed={len(seed_products)}, enriched={len(enriched_products)}, "
            f"used_url_keys={len(used_url_keys)}, chosen={len(chosen_enriched_products)}"
        )
        raise ValueError("사용 이력이 없는 비교 상품은 최소 2개 이상 필요합니다.")
    if len(chosen_enriched_products) < count:
        print(f"[Products] 사용 가능한 상품이 {len(chosen_enriched_products)}개뿐이라 해당 개수로 진행합니다.")
    else:
        print(f"[Products] 최종 발행 상품 확정: {len(chosen_enriched_products)}개")
    return chosen_seed_products, chosen_enriched_products


def prepare_coupang_api_products(
    count: int = 3,
    performance_topic: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    if not COUPANG_API_ENABLED:
        raise RuntimeError("쿠팡 글은 쿠팡 API 상품 치환이 필요합니다. COUPANG_API_ENABLED=1로 설정하세요.")
    if not COUPANG_ACCESS_KEY or not COUPANG_SECRET_KEY:
        raise RuntimeError("COUPANG_ACCESS_KEY 또는 COUPANG_SECRET_KEY가 없어 쿠팡 API를 사용할 수 없습니다.")

    seed_pool = _ordered_available_product_rows(performance_topic)
    if len(seed_pool) < 2 and not performance_topic:
        raise ValueError("비교 상품은 최소 2개 이상 필요합니다.")

    used_url_keys = _load_used_coupang_url_keys()
    selected_seed_products: list[dict] = []
    selected_api_products: list[dict] = []
    seen_keys: set[str] = set()
    minimum_required_api_products = 2

    print(f"[Products] CSV 미사용 후보를 API 상품으로 순차 치환합니다: 후보 {len(seed_pool)}개")
    def _try_add_api_product(seed: dict, source_label: str) -> bool:
        candidate_name = seed.get("상품명") or seed.get("키워드") or "상품"
        try:
            enriched_list = enrich_products_with_coupang_links(
                [seed],
                api_enabled=True,
                access_key=COUPANG_ACCESS_KEY or "",
                secret_key=COUPANG_SECRET_KEY or "",
                sub_id=COUPANG_SUB_ID,
                fallback_to_similar=True,
                require_api_product=True,
                excluded_url_keys=used_url_keys | seen_keys,
                url_key_func=_coupang_product_key,
            )
        except Exception as exc:
            print(
                f"[Products] API 상품 조회 실패 - 후보 제외: "
                f"{candidate_name} / {type(exc).__name__}: {exc}"
            )
            return False
        enriched = enriched_list[0] if enriched_list else {}
        product_key = _row_coupang_key(enriched)
        if not product_key:
            print(f"[Products] API/유사 상품을 찾지 못해 제외: {candidate_name}")
            return False
        relevance_score = _api_product_topic_relevance_score(enriched, performance_topic)
        if performance_topic and relevance_score <= 0:
            print(
                f"[Products] 주제와 맞지 않는 API 상품 제외: "
                f"{enriched.get('상품명') or seed.get('상품명') or product_key} "
                f"/ topic={performance_topic.get('query')}"
            )
            return False
        if product_key in used_url_keys:
            print(f"[Products] 이미 사용된 API 상품 제외: {enriched.get('상품명') or seed.get('상품명') or product_key}")
            return False
        if product_key in seen_keys:
            print(f"[Products] 이번 실행 내 중복 API 상품 제외: {enriched.get('상품명') or seed.get('상품명') or product_key}")
            return False

        seen_keys.add(product_key)
        selected_seed_products.append(seed)
        selected_api_products.append(enriched)
        print(
            f"[Products] API 상품 확정 {len(selected_api_products)}/{count}: "
            f"{enriched.get('상품명') or seed.get('상품명') or product_key} "
            f"(source={source_label}, match={enriched.get('API매칭방식') or '-'})"
        )
        return True

    for seed in seed_pool:
        _try_add_api_product(seed, "csv")
        if len(selected_api_products) >= count:
            break
        if performance_topic and len(selected_api_products) >= minimum_required_api_products:
            print(
                f"[Products] API 치환 상품 {len(selected_api_products)}개 확보 - "
                "추가 API 조회를 줄이고 해당 개수로 진행합니다."
            )
            break

    if (
        performance_topic
        and len(selected_api_products) < count
        and len(selected_api_products) < minimum_required_api_products
    ):
        supplemental_seeds = _topic_api_supplemental_seed_rows(performance_topic)
        if supplemental_seeds:
            print(
                f"[Products] 주제 매칭 API 상품이 부족해 주제 검색어로 추가 보강합니다: "
                f"{len(selected_api_products)}/{count}개 확보"
            )
        for seed in supplemental_seeds:
            _try_add_api_product(seed, "topic-query")
            if len(selected_api_products) >= count:
                break
            if len(selected_api_products) >= minimum_required_api_products:
                print(
                    f"[Products] API 치환 상품 {len(selected_api_products)}개 확보 - "
                    "추가 API 조회를 줄이고 해당 개수로 진행합니다."
                )
                break

    if len(selected_api_products) < 2:
        raise ValueError(
            "사용 가능한 API 치환 상품은 최소 2개 이상 필요합니다. "
            f"seed_pool={len(seed_pool)}, used_url_keys={len(used_url_keys)}, chosen={len(selected_api_products)}"
        )
    if len(selected_api_products) < count:
        print(f"[Products] API 치환 상품이 {len(selected_api_products)}개뿐이라 해당 개수로 진행합니다.")
    else:
        print(f"[Products] 최종 API 치환 상품 확정: {len(selected_api_products)}개")
    return selected_seed_products, selected_api_products


def _product_selection_reason(product: dict) -> str:
    explicit_reason = _first_product_value(
        product,
        (
            "선정이유",
            "선정 이유",
            "비교선정이유",
            "추천이유",
            "selection_reason",
            "editorial_reason",
            "reason",
        ),
    )
    if explicit_reason:
        return explicit_reason

    price = _first_product_value(product, ("상품가격", "가격", "product_price", "price"))
    discount = _first_product_value(product, ("할인율", "discount_rate"))
    rating = _first_product_value(product, ("평점", "rating"))
    review_count = _first_product_value(product, ("리뷰수", "review_count"))
    rocket_info = _first_product_value(product, ("로켓정보", "로켓배송", "delivery_info"))
    option = _first_product_value(product, ("옵션", "option", "구성", "용량", "크기", "사이즈"))
    benefit = _first_product_value(product, ("장점1", "장점2", "장점3", "핵심장점", "benefit"))

    reasons = []
    if price:
        reasons.append(f"가격대 확인 가능({price})")
    if discount:
        reasons.append(f"할인율 비교 가능({discount}%)")
    if rating:
        reasons.append(f"평점 확인 가능({rating})")
    if review_count:
        reasons.append(f"리뷰수 확인 가능({review_count})")
    if rocket_info:
        reasons.append(f"배송/설치 조건 확인 가능({rocket_info})")
    if option:
        reasons.append(f"옵션/규격 비교 가능({option})")
    if benefit:
        reasons.append(f"핵심 장점 확인 가능({benefit})")

    if not reasons:
        return "가격, 리뷰, 배송, 옵션을 같은 기준으로 비교하기 위한 후보"
    return ", ".join(reasons[:3]) + " 기준으로 비교 가치가 있는 후보"


def _build_products_summary(products: list[dict]) -> str:
    lines = []
    for i, p in enumerate(products, 1):
        name = _clean(p.get("\uC0C1\uD488\uBA85"), f"상품{i}")
        price = _clean(p.get("상품가격"), _clean(p.get("가격"), "가격 확인 필요"))
        discount = _clean(p.get("할인율"), "")
        rating = _clean(p.get("평점"), "")
        review_count = _clean(p.get("리뷰수"), "")
        rocket_info = _clean(p.get("로켓정보"), _clean(p.get("로켓배송"), ""))
        s = [
            _clean(p.get("\uC7A5\uC8101"), "상품 상세페이지와 리뷰에서 장점을 먼저 확인해 두는 편이 좋습니다."),
            _clean(p.get("\uC7A5\uC8102"), "비슷한 상품과 비교하면서 선택 기준을 세우기 좋습니다."),
            _clean(p.get("\uC7A5\uC8103"), "구매 전 가격과 옵션을 다시 확인해 두는 편이 안전합니다."),
        ]
        caution = _clean(p.get("\uC8FC\uC758\uC810"), "개인 상황에 따라 체감 차이가 있을 수 있습니다.")
        url = _clean(p.get("\uCFE0\uD321\uB9C1\uD06C"), "")
        quant_facts = [f"가격 {price}"]
        if discount:
            quant_facts.append(f"할인율 {discount}%")
        if rating:
            quant_facts.append(f"평점 {rating}")
        if review_count:
            quant_facts.append(f"리뷰수 {review_count}")
        if rocket_info:
            quant_facts.append(f"배송/설치 {rocket_info}")
        selection_reason = _product_selection_reason(p)
        lines.append(
            f"{i}. {name} / 선정 이유: {selection_reason}"
            f" / 정량 근거: {', '.join(quant_facts)}"
            f" / 핵심 포인트: {s[0]}, {s[1]}, {s[2]}"
            f" / 주의사항: {caution} / 쿠팡 링크: {url}"
        )
    return "\n".join(lines)


def _product_link_marker(index: int) -> str:
    return f"[PRODUCT_LINK_{index}]"


def _products_with_link_markers(products: list[dict]) -> tuple[list[dict], dict[str, str]]:
    marker_products: list[dict] = []
    link_map: dict[str, str] = {}
    for index, product in enumerate(products, 1):
        marker = _product_link_marker(index)
        real_url = _clean(
            product.get("쿠팡링크"),
            _clean(product.get("coupang_partners_link"), _clean(product.get("product_url"), "")),
        )
        link_map[marker] = real_url
        marker_product = dict(product)
        marker_product["쿠팡링크"] = marker
        marker_product["coupang_partners_link"] = marker
        marker_products.append(marker_product)
    return marker_products, link_map


def _replace_product_link_markers(html_body: str, link_map: dict[str, str]) -> str:
    for marker, real_url in link_map.items():
        if not real_url:
            continue
        html_body = html_body.replace(marker, real_url)
    unresolved = sorted(marker for marker in link_map if marker in html_body)
    if unresolved:
        raise RuntimeError(f"쿠팡 링크 마커 치환 실패: {', '.join(unresolved)}")
    return html_body


def _build_cta_links(products: list[dict]) -> str:
    """상품 이미지 + 가격이 포함된 카드형 CTA HTML을 생성합니다."""
    cards = []
    for i, p in enumerate(products, 1):
        name = _clean(p.get("상품명"), f"상품{i}")
        url = _clean(p.get("쿠팡링크"), "#")
        image = _clean(p.get("상품이미지"), "")
        price = _clean(p.get("상품가격"), _clean(p.get("가격"), ""))
        is_rocket = _clean(p.get("로켓배송"), _clean(p.get("로켓정보"), "N")) == "Y"
        cta_text = _neutral_coupang_cta_text(_clean(p.get("cta_text"), ""), i - 1)

        # 가격 포맷팅
        price_html = ""
        if price:
            try:
                price_formatted = f"{int(price):,}원"
                price_html = (
                    f'<span style="{COUPANG_CARD_PRICE_STYLE}">{price_formatted}</span>'
                )
            except ValueError:
                pass

        # 로켓배송 뱃지
        rocket_html = ""
        if is_rocket:
            rocket_html = (
                f'<span style="{COUPANG_CARD_BADGE_STYLE}">로켓배송</span>'
            )

        # 이미지 영역
        if image:
            img_html = (
                f'<img src="{image}" alt="{name}" '
                f'style="{COUPANG_CARD_IMAGE_STYLE}" />'
            )
        else:
            img_html = (
                '<span style="display:flex; align-items:center; justify-content:center; '
                'width:132px; height:132px; background:#f5f5f5; border-radius:6px; '
                'color:#bbb; font-size:24px; flex-shrink:0;">상품</span>'
            )

        card = (
            f'<a href="{url}" target="_blank" rel="{_affiliate_rel_value()}" '
            f'style="{COUPANG_CARD_LINK_STYLE}">'
            f'{img_html}'
            f'<span style="display:flex; flex-direction:column; flex:1; min-width:0;">'
            f'<span style="font-size:17px; font-weight:800; color:#222; '
            f'line-height:1.4; word-break:keep-all;">{name}{rocket_html}</span>'
            f'{price_html}'
            f'<span style="{COUPANG_CARD_CTA_STYLE}">{cta_text}</span>'
            f'</span></a>'
        )
        cards.append(card)
    return "\n".join(cards)

def build_prompt_values(products: list[dict], performance_topic: dict | None = None) -> dict:
    first    = products[0]
    category = _clean(first.get("\uCE74\uD14C\uACE0\uB9AC"), "건강관리")
    keyword  = _clean(first.get("\uC0C1\uD488\uBA85"), _clean(first.get("\uD0A4\uC6CC\uB4DC"), "쿠팡 상품 추천"))
    keywords = ", ".join(
        _clean(p.get("\uC0C1\uD488\uBA85"), _clean(p.get("\uD0A4\uC6CC\uB4DC"), ""))
        for p in products
        if _clean(p.get("\uC0C1\uD488\uBA85"), _clean(p.get("\uD0A4\uC6CC\uB4DC"), ""))
    )
    if performance_topic:
        keyword = performance_topic.get("keyword") or performance_topic.get("query") or keyword
        if performance_topic.get("query") and performance_topic["query"] not in keywords:
            keywords = ", ".join(part for part in (performance_topic["query"], keywords) if part)
        category = performance_topic.get("category") or category

    return {
        "keyword":          keyword,
        "keywords":         keywords,
        "product_count":    len(products),
        "products_summary": _build_products_summary(products),
        "target_reader":    (performance_topic or {}).get("target_reader") or _clean(first.get("\uD0C0\uAC9F\uB3C5\uC790"), "비슷한 상품 중 무엇을 고를지 고민하는 독자"),
        "usage_scenario":   (performance_topic or {}).get("usage_scenario") or _clean(first.get("\uC0AC\uC6A9\uC7A5\uC18C"), _clean(first.get("\uBB38\uC81C\uC0C1\uD669"), "일상에서 제품을 비교하고 구매하려는 상황")),
        "product_names":    ", ".join(_clean(p.get("\uC0C1\uD488\uBA85"), "상품") for p in products),
        "category":         category,
        "tone":             "깔끔하고 정보형",
        "pain_point":       (performance_topic or {}).get("pain_point") or _clean(first.get("\uBB38\uC81C\uC0C1\uD669"), "비슷한 상품이 많아 선택이 어려운 경우"),
        "cta_links":        "",
        "image1_url":       "",
        "image2_url":       "",
    }


def save_coupang_performance_topic(topic: dict | None) -> Path | None:
    if not topic:
        return None
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic_key": _coupang_topic_key(topic),
        "query": topic.get("query", ""),
        "keyword": topic.get("keyword", ""),
        "category": topic.get("category", ""),
        "pain_point": topic.get("pain_point", ""),
        "target_reader": topic.get("target_reader", ""),
        "usage_scenario": topic.get("usage_scenario", ""),
        "match_terms": topic.get("match_terms", []),
        "exclude_terms": topic.get("exclude_terms", []),
        "score": topic.get("score", 0),
        "source_csv": str(_coupang_topic_performance_csv_path()),
        "cooldown_days": _coupang_topic_cooldown_days(),
    }
    path = GENERATED_RESULT_DIR / "performance_topic.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[Topic] 쿠팡 성과 주제 기록 저장: {path}")
    return path


def build_coupang_post_title(products: list[dict], generated_title: str = "") -> str:
    title = re.sub(r"\s+", " ", (generated_title or "").strip())
    title = title.strip("\"'“”‘’")
    if title:
        return title

    first = products[0] if products else {}
    keyword = _clean(first.get("키워드"), _clean(first.get("카테고리"), "쿠팡 상품"))
    if keyword and keyword != "쿠팡 상품":
        return f"{keyword} 구매 전 비교 체크포인트"
    return "쿠팡 상품 구매 전 비교 체크포인트"


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
    for match in re.finditer(r"https?://[^\s\"'<>]+", text or "", flags=re.IGNORECASE):
        url = _canonical_coupang_url(match.group(0))
        if not url:
            continue
        if "ads-partners.coupang.com" in url.lower():
            continue
        if "coupang.com" in url.lower() or "coupa.ng" in url.lower():
            urls.append(url)
    return urls


def _load_used_coupang_urls() -> set[str]:
    if not USED_COUPANG_URL_LOG_PATH.exists():
        return set()
    with USED_COUPANG_URL_LOG_PATH.open("r", newline="", encoding="utf-8-sig") as f:
        return {_canonical_coupang_url(r["coupang_url"]) for r in csv.DictReader(f) if r.get("coupang_url")}


def _load_used_coupang_url_keys() -> set[str]:
    return {key for key in (_coupang_product_key(url) for url in _load_used_coupang_urls()) if key}


def set_current_run_coupang_urls(products: list[dict]) -> None:
    CURRENT_RUN_COUPANG_URL_KEYS.clear()
    for product in products:
        key = _row_coupang_key(product)
        if key:
            CURRENT_RUN_COUPANG_URL_KEYS.add(key)


def validate_coupang_urls(prompt_text: str) -> None:
    used_keys = _load_used_coupang_url_keys()
    duplicated = []
    for url in set(_extract_coupang_urls(prompt_text)):
        key = _coupang_product_key(url)
        if key and key in used_keys and key not in CURRENT_RUN_COUPANG_URL_KEYS:
            duplicated.append(url)
    duplicated = sorted(duplicated)
    if duplicated:
        raise ValueError("중복 쿠팡 URL 감지:\n" + "\n".join(duplicated))


def log_run(label: str, prompt_text: str) -> None:
    _append_csv(
        RUN_LOG_PATH,
        ["run_at", "prompt_label", "prompt_length"],
        {"run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "prompt_label": label, "prompt_length": len(prompt_text)},
    )


def log_coupang_urls(prompt_text: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for url in _extract_coupang_urls(prompt_text):
        _append_csv(USED_COUPANG_URL_LOG_PATH, ["used_at", "coupang_url"], {"used_at": now, "coupang_url": url})


def log_product_coupang_urls(products: list[dict]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    seen: set[str] = set()
    for product in products:
        url = _canonical_coupang_url(
            product.get("쿠팡링크")
            or product.get("coupang_partners_link")
            or product.get("product_url")
            or product.get("url")
            or ""
        )
        key = _coupang_product_key(url)
        if not url or not key or key in seen:
            continue
        seen.add(key)
        _append_csv(USED_COUPANG_URL_LOG_PATH, ["used_at", "coupang_url"], {"used_at": now, "coupang_url": url})
    if seen:
        print(f"[Products] 쿠팡 URL 사용 로그 기록 완료: {len(seen)}개")



def _replace_inline_coupang_links_with_cards(html_body: str, products: list[dict]) -> str:
    """본문 내 쿠팡 인라인 링크를 카드형 HTML로 후처리 변환합니다."""
    if not products:
        return html_body

    # products에서 URL → 상품 정보 매핑
    url_to_product = {}
    for p in products:
        url = _clean(p.get("쿠팡링크"), "")
        if _is_valid_coupang_link(url):
            url_to_product[url] = p

    if not url_to_product:
        return html_body

    # <a href="...coupang...">텍스트</a> 패턴 찾기
    pattern = re.compile(
        r'<a\s[^>]*href="(https?://[^"]*(?:link\.coupang\.com|www\.coupang\.com|coupa\.ng)[^"]*)"[^>]*>([^<]+(?:<[^/a][^<]*>)*[^<]*)</a>',
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
        price = _clean(product.get("상품가격"), _clean(product.get("가격"), ""))
        is_rocket = _clean(product.get("로켓배송"), _clean(product.get("로켓정보"), "N")) == "Y"

        if not name:
            return match.group(0)

        # 가격 HTML
        price_html = ""
        if price:
            try:
                price_html = (
                f'<span style="{COUPANG_CARD_PRICE_STYLE}">{int(price):,}원</span>'
                )
            except ValueError:
                pass

        # 로켓배송 뱃지
        rocket_html = ""
        if is_rocket:
            rocket_html = (
                f'<span style="{COUPANG_CARD_BADGE_STYLE}">로켓배송</span>'
            )

        # 이미지
        if image:
            img_html = (
                f'<img src="{image}" alt="{name}" '
                f'style="{COUPANG_CARD_IMAGE_STYLE}" />'
            )
        else:
            img_html = (
                '<span style="display:flex; align-items:center; justify-content:center; '
                'width:132px; height:132px; background:#f5f5f5; border-radius:6px; '
                'color:#bbb; font-size:24px; flex-shrink:0;">상품</span>'
            )

        card = (
            f'<a href="{url}" target="_blank" rel="{_affiliate_rel_value()}" '
            f'style="{COUPANG_CARD_LINK_STYLE}">'
            f'{img_html}'
            f'<span style="display:flex; flex-direction:column; flex:1; min-width:0;">'
            f'<span style="font-size:17px; font-weight:800; color:#222; '
            f'line-height:1.4; word-break:keep-all;">{name}{rocket_html}</span>'
            f'{price_html}'
            f'<span style="{COUPANG_CARD_CTA_STYLE}">{COUPANG_NEUTRAL_CTA_TEXTS[0]}</span>'
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

    if EXACT_COUPANG_DISCLOSURE in html_body:
        html_body = re.sub(
            r'\s*<p\b[^>]*>.*?' + re.escape(EXACT_COUPANG_DISCLOSURE) + r'.*?</p>\s*',
            "\n",
            html_body,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return disclosure_html + "\n" + html_body.lstrip()

    # 옛 문구가 있으면 제거
    old_disclosures = [
        "쿠팡 파트너스 활동의 일환으로 일정 수수료를 제공받을 수 있습니다.",
    ]
    for old in old_disclosures:
        # <p>...옛문구...</p> 패턴 제거 (스타일 포함 여부 무관)
        html_body = re.sub(
            r'<p[^>]*>' + re.escape(old) + r'</p>\s*',
            '',
            html_body,
        )

    # 맨 위(첫 줄)에 고지 문구 삽입
    return disclosure_html + "\n" + html_body.lstrip()


def _coupang_data_checked_label() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _coupang_editorial_note_html(products: list[dict] | None = None) -> str:
    product_count = len(products or [])
    count_text = f"{product_count}개 상품" if product_count else "비교 상품"
    checked_at = _coupang_data_checked_label()
    return (
        '<p style="font-size:13px; color:#666; background:#f6f8fa; '
        'border-left:3px solid #adb5bd; padding:10px 14px; '
        'margin:0 0 22px; border-radius:0 6px 6px 0; line-height:1.7;">'
        f'<strong>{COUPANG_EDITORIAL_NOTE_LABEL}:</strong> '
        f'이 글은 공개 상품 정보와 {html.escape(checked_at)} 작성일 기준 '
        f'{html.escape(count_text)}의 가격, 할인율, 평점, 리뷰수, 배송/옵션을 '
        '같은 항목으로 비교한 구매 전 체크 가이드입니다. '
        '가격, 재고, 배송 조건, 옵션 구성은 변동될 수 있으므로 최종 구매 전 '
        '판매 상세페이지의 최신 가격, 옵션, 배송, 재고, 반품 조건을 함께 확인하는 것이 좋습니다.'
        '</p>'
    )


def _has_precise_coupang_editorial_note(html_body: str) -> bool:
    text = _strip_html_to_text_for_quality(html_body)
    return (
        COUPANG_EDITORIAL_NOTE_LABEL in text
        and all(term in text for term in COUPANG_EDITORIAL_NOTE_REQUIRED_TERMS)
    )


def _remove_loose_coupang_editorial_note(html_body: str) -> str:
    return re.sub(
        r"\s*<p\b[^>]*>.*?"
        + re.escape(COUPANG_EDITORIAL_NOTE_LABEL)
        + r".*?</p>\s*",
        "\n",
        html_body or "",
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _ensure_coupang_editorial_note(html_body: str, products: list[dict] | None = None) -> str:
    if _has_precise_coupang_editorial_note(html_body):
        return html_body

    html_body = _remove_loose_coupang_editorial_note(html_body)
    note_html = _coupang_editorial_note_html(products)
    disclosure_pattern = re.compile(
        r"(<p\b[^>]*>[^<]*" + re.escape(EXACT_COUPANG_DISCLOSURE) + r"[^<]*</p>\s*)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = disclosure_pattern.search(html_body or "")
    if match:
        return html_body[:match.end()] + note_html + "\n" + html_body[match.end():]
    return note_html + "\n" + (html_body or "").lstrip()


COUPANG_BODY_P_STYLE = "font-size:15px; line-height:1.95; color:#333; margin:0 0 18px; word-break:keep-all;"
COUPANG_BODY_H2_STYLE = "font-size:19px; font-weight:700; color:#1a1a2e; padding:0 0 12px; border-bottom:2px solid #f0f0f0; margin:36px 0 16px;"
COUPANG_BODY_H2_SPAN = '<span style="display:inline-block; width:4px; height:20px; background:#ff6b35; border-radius:2px; margin-right:10px; vertical-align:middle;"></span>'
COUPANG_BODY_H3_STYLE = "font-size:16px; font-weight:700; color:#333; margin:24px 0 12px; padding-left:12px; border-left:3px solid #ff9500;"
COUPANG_BODY_UL_STYLE = "list-style:none; padding:0; margin:0 0 24px;"
COUPANG_BODY_LI_STYLE = "font-size:14px; color:#444; padding:10px 16px 10px 40px; background:#fafafa; border:1px solid #f0f0f0; border-radius:8px; margin-bottom:8px; position:relative; line-height:1.7;"
COUPANG_BODY_LI_SPAN = '<span style="position:absolute; left:14px; color:#06d6a0; font-weight:700;">✔</span>'
COUPANG_BODY_BLOCKQUOTE_STYLE = "background:#f0f7ff; border-left:4px solid #4cc9f0; padding:14px 18px; margin:20px 0; border-radius:0 8px 8px 0; font-size:14px; color:#555; line-height:1.8;"
COUPANG_BODY_FIGURE_STYLE = "text-align:center; margin:0 0 28px;"
COUPANG_BODY_IMG_STYLE = "max-width:100%; border-radius:12px; display:block; margin:0 auto;"
COUPANG_BODY_FIGCAPTION_STYLE = "font-size:12px; color:#999; margin-top:8px;"
COUPANG_BODY_SUMMARY_DIV_STYLE = "background:#fff9f0; border:1px solid #ffe0bb; border-radius:12px; padding:20px 22px; margin:0 0 28px;"


def _style_opening_tag(match: re.Match, style: str) -> str:
    return _set_html_attr(match.group(0), "style", style)


def _apply_coupang_inline_styles(html_body: str) -> str:
    def _style_p(match: re.Match) -> str:
        full = match.group(0)
        text = _strip_html_to_text_for_quality(full)
        if EXACT_COUPANG_DISCLOSURE in text or COUPANG_EDITORIAL_NOTE_LABEL in text:
            return full
        opening = _set_html_attr(match.group(1), "style", COUPANG_BODY_P_STYLE)
        return opening + match.group(2) + "</p>"

    def _style_h2(match: re.Match) -> str:
        opening = _set_html_attr(match.group(1), "style", COUPANG_BODY_H2_STYLE)
        inner = match.group(2).strip()
        if not re.match(r"^<span\b", inner, flags=re.IGNORECASE):
            inner = COUPANG_BODY_H2_SPAN + inner
        return opening + inner + "</h2>"

    def _style_li(match: re.Match) -> str:
        opening = _set_html_attr(match.group(1), "style", COUPANG_BODY_LI_STYLE)
        inner = match.group(2).strip()
        if "position:absolute; left:14px;" not in inner:
            inner = COUPANG_BODY_LI_SPAN + inner
        return opening + inner + "</li>"

    html_body = re.sub(r"(<p\b[^>]*>)(.*?)</p>", _style_p, html_body, flags=re.IGNORECASE | re.DOTALL)
    html_body = re.sub(r"(<h2\b[^>]*>)(.*?)</h2>", _style_h2, html_body, flags=re.IGNORECASE | re.DOTALL)
    html_body = re.sub(
        r"<h3\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_H3_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(
        r"<ul\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_UL_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(r"(<li\b[^>]*>)(.*?)</li>", _style_li, html_body, flags=re.IGNORECASE | re.DOTALL)
    html_body = re.sub(
        r"<blockquote\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_BLOCKQUOTE_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(
        r"<figure\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_FIGURE_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(
        r"<figcaption\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_FIGCAPTION_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(
        r"<img\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_IMG_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    html_body = re.sub(
        r"<div\b[^>]*>",
        lambda match: _style_opening_tag(match, COUPANG_BODY_SUMMARY_DIV_STYLE),
        html_body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html_body


def _strip_html_to_text_for_quality(html_body: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html_body or "", flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?(?:p|li|h[1-6]|br|section|div|blockquote)\b[^>]*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _count_term_hits(text: str, terms: tuple[str, ...]) -> int:
    return sum(text.count(term) for term in terms)


def _product_quality_fact_values(products: list[dict]) -> list[str]:
    values = []
    field_groups = [
        ("상품가격", "가격", "product_price"),
        ("할인율", "discount_rate"),
        ("평점", "rating"),
        ("리뷰수", "review_count"),
        ("로켓정보", "로켓배송", "delivery_info"),
    ]
    for product in products or []:
        for keys in field_groups:
            value = _first_product_value(product, keys)
            if value:
                values.append(value)
    return values


def _coupang_affiliate_links(html_body: str) -> list[str]:
    links = []
    for match in re.finditer(r"<a\b[^>]*>", html_body or "", flags=re.IGNORECASE | re.DOTALL):
        href = _html_attr_value(match.group(0), "href")
        if _is_valid_coupang_link(href):
            links.append(href)
    return links


def _coupang_invalid_rel_count(html_body: str) -> int:
    invalid = 0
    for match in re.finditer(r"<a\b[^>]*>", html_body or "", flags=re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        href = _html_attr_value(tag, "href")
        if not _is_valid_coupang_link(href):
            continue
        rel_tokens = set(re.split(r"\s+", _html_attr_value(tag, "rel").lower()))
        if not {"sponsored", "nofollow"}.issubset(rel_tokens):
            invalid += 1
    return invalid


def _first_coupang_link_pre_text_length(html_body: str) -> int:
    first_coupang_link = re.search(
        r"<a\b[^>]*href=[\"'][^\"']*(?:link\.coupang\.com|www\.coupang\.com|coupa\.ng)[^\"']*[\"'][^>]*>",
        html_body or "",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not first_coupang_link:
        return 0
    return len(_strip_html_to_text_for_quality((html_body or "")[: first_coupang_link.start()]))


def analyze_coupang_quality_content(html_body: str, products: list[dict] | None = None) -> dict:
    text = _strip_html_to_text_for_quality(html_body)
    numeric_hits = len(re.findall(r"\d+(?:[,.]\d+)*\s*(?:원|만원|%|점|개|건|cm|mm|kg|g|W|㎡|평)?", text))
    quantitative_hits = sum(1 for term in COUPANG_QUANTITATIVE_TERMS if term in text)
    product_fact_hits = sum(1 for value in _product_quality_fact_values(products or []) if value and value in text)
    oversell_terms = [term for term in COUPANG_COMMERCIAL_OVERSELL_TERMS if term in text]
    selection_reason_hits = _count_term_hits(text, COUPANG_SELECTION_REASON_TERMS)
    required_selection_reasons = min(len(products or []), 3)
    downside_hits = _count_term_hits(text, COUPANG_DOWNSIDE_TERMS)
    evidence_term_hits = sum(1 for term in COUPANG_EVIDENCE_TERMS if term in text)
    links = _coupang_affiliate_links(html_body)
    product_keys = {
        _row_coupang_key(product)
        for product in (products or [])
        if _row_coupang_key(product)
    }
    expected_link_count = len(product_keys) if product_keys else len(products or [])
    first_link_pre_text_length = _first_coupang_link_pre_text_length(html_body)
    invalid_rel_count = _coupang_invalid_rel_count(html_body)

    criteria = {
        "text_length_ok": len(text) >= 2000,
        "first_link_info_ok": bool(links) and first_link_pre_text_length >= 500,
        "link_count_ok": bool(expected_link_count) and len(links) == expected_link_count,
        "affiliate_rel_ok": bool(links) and invalid_rel_count == 0,
        "quantitative_comparison_ok": _has_any_term(text, COUPANG_COMPARISON_TERMS) and quantitative_hits >= 3 and numeric_hits >= 3,
        "selection_reason_ok": (not required_selection_reasons) or selection_reason_hits >= required_selection_reasons,
        "downside_ok": downside_hits >= 2,
        "fit_ok": _has_any_term(text, COUPANG_FIT_TERMS),
        "cautious_fit_ok": _has_any_term(text, COUPANG_CAUTIOUS_FIT_TERMS),
        "evidence_ok": evidence_term_hits >= 4 and product_fact_hits >= min(2, max(1, len(products or []))),
        "editorial_note_ok": (
            COUPANG_EDITORIAL_NOTE_LABEL in text
            and all(term in text for term in COUPANG_EDITORIAL_NOTE_REQUIRED_TERMS)
        ),
        "oversell_ok": not oversell_terms,
    }

    weights = {
        "text_length_ok": 10,
        "first_link_info_ok": 10,
        "link_count_ok": 10,
        "affiliate_rel_ok": 5,
        "quantitative_comparison_ok": 15,
        "selection_reason_ok": 10,
        "downside_ok": 10,
        "fit_ok": 7,
        "cautious_fit_ok": 7,
        "evidence_ok": 10,
        "editorial_note_ok": 4,
        "oversell_ok": 2,
    }
    score = sum(weight for key, weight in weights.items() if criteria.get(key))

    failures = []
    if links and first_link_pre_text_length < 500:
        failures.append("제휴 링크 전 정보량 부족: 첫 쿠팡 링크 전에 선택 기준과 비교 근거를 충분히 제공해야 합니다.")
    if not criteria["link_count_ok"]:
        failures.append(f"쿠팡 링크 수 불일치: 필요 {expected_link_count}개, 현재 {len(links)}개")
    if invalid_rel_count:
        failures.append(f"쿠팡 제휴 링크 rel 누락: {invalid_rel_count}개")

    if not criteria["quantitative_comparison_ok"]:
        failures.append("정량 비교 부족: 가격/할인율/평점/리뷰수/배송/옵션 같은 수치 기반 비교가 필요합니다.")
    if required_selection_reasons and selection_reason_hits < required_selection_reasons:
        failures.append(
            f"제품별 선정 이유 부족: 상품별로 왜 비교 후보로 골랐는지 설명해야 합니다. "
            f"필요 {required_selection_reasons}개, 현재 {selection_reason_hits}개"
        )
    if not criteria["downside_ok"]:
        failures.append("단점/주의점 부족: 상품별 아쉬운 점이나 주의할 점이 충분하지 않습니다.")
    if not criteria["fit_ok"]:
        failures.append("맞는 사람 설명 누락: 어떤 독자에게 적합한지 분리해서 써야 합니다.")
    if not criteria["cautious_fit_ok"]:
        failures.append("피할 사람/신중히 볼 사람 설명 누락: 구매를 신중히 볼 조건이 필요합니다.")
    if not criteria["evidence_ok"]:
        failures.append("근거 부족: 상품 정보의 가격/평점/리뷰수/배송 등 확인 가능한 근거가 본문에 드러나야 합니다.")
    if not criteria["editorial_note_ok"]:
        failures.append("편집 신뢰도 고지 부족: 공개 상품 정보 기준, 작성일, 변동 가능성, 최종 구매 전 상세페이지 최신 정보 확인 안내가 필요합니다.")
    if oversell_terms:
        failures.append("구매 압박 문구 포함: " + ", ".join(sorted(set(oversell_terms))))

    return {
        "score": score,
        "min_score": COUPANG_QUALITY_MIN_SCORE,
        "passed": not failures and score >= COUPANG_QUALITY_MIN_SCORE,
        "criteria": criteria,
        "metrics": {
            "text_length": len(text),
            "first_link_pre_text_length": first_link_pre_text_length,
            "affiliate_link_count": len(links),
            "expected_affiliate_link_count": expected_link_count,
            "invalid_rel_count": invalid_rel_count,
            "numeric_hits": numeric_hits,
            "quantitative_term_hits": quantitative_hits,
            "product_fact_hits": product_fact_hits,
            "selection_reason_hits": selection_reason_hits,
            "required_selection_reasons": required_selection_reasons,
            "downside_hits": downside_hits,
            "evidence_term_hits": evidence_term_hits,
            "oversell_terms": sorted(set(oversell_terms)),
        },
        "failures": failures,
    }


def validate_coupang_quality_content(html_body: str, products: list[dict] | None = None) -> None:
    """
    Prevent thin affiliate posts from moving forward.
    The body must include quantitative comparison, drawbacks, audience fit,
    cautious-fit guidance, evidence/criteria wording, and product selection reasons.
    """
    report = analyze_coupang_quality_content(html_body, products)
    if report["failures"]:
        raise ValueError("쿠팡 글 품질 검증 실패:\n- " + "\n- ".join(report["failures"]))
    if report["score"] < COUPANG_QUALITY_MIN_SCORE:
        raise ValueError(f"쿠팡 글 품질 점수 부족: {report['score']}점 / 최소 {COUPANG_QUALITY_MIN_SCORE}점")

    print(f"[품질 검증] 쿠팡 글 품질 조건 통과 ({report['score']}점)")


def _quality_report_slug(text: str) -> str:
    cleaned = re.sub(r"[^\w가-힣.-]+", "_", text or "", flags=re.UNICODE).strip("._")
    return cleaned[:60] or "untitled"


def save_coupang_quality_report(title: str, html_body: str, products: list[dict] | None = None) -> Path:
    report = analyze_coupang_quality_content(html_body, products)
    report.update(
        {
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
            "product_count": len(products or []),
            "product_names": [_first_product_value(product, ("상품명", "product_name", "name", "title")) for product in (products or [])],
            "report_version": 1,
        }
    )
    COUPANG_QUALITY_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_quality_report_slug(title)}.json"
    report_path = COUPANG_QUALITY_REPORT_DIR / file_name
    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    report_path.write_text(report_json + "\n", encoding="utf-8")
    (COUPANG_QUALITY_REPORT_DIR / "latest.json").write_text(report_json + "\n", encoding="utf-8")
    (GENERATED_RESULT_DIR / "quality_report.json").write_text(report_json + "\n", encoding="utf-8")
    print(f"[품질 리포트] 쿠팡 글 품질 점수 {report['score']}점 저장: {report_path}")
    if report["score"] < COUPANG_QUALITY_MIN_SCORE:
        raise ValueError(f"쿠팡 글 품질 점수 부족: {report['score']}점 / 최소 {COUPANG_QUALITY_MIN_SCORE}점")
    return report_path


def _postprocess_and_validate_coupang_body(html_body: str, products: list[dict]) -> str:
    html_body = clean_generated_html_body(html_body)
    html_body = ensure_exact_coupang_disclosure(html_body)
    html_body = _ensure_coupang_editorial_note(html_body, products)
    html_body = _apply_coupang_inline_styles(html_body)
    html_body = _replace_inline_coupang_links_with_cards(html_body, products)
    html_body = _enforce_coupang_affiliate_link_attrs(html_body)
    html_body = _dedupe_coupang_affiliate_links(html_body)
    _validate_coupang_affiliate_link_attrs(html_body)
    _validate_coupang_affiliate_link_count(html_body, products)
    validate_coupang_quality_content(html_body, products)
    return html_body


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
        "title_candidates.txt": title_text,
        "body.html":            html_body,
        "hashtags.txt":         hashtags,
        "image_urls.txt":       f"{image1_url}\n{image2_url}\n",
        "image1_data_url.txt":  image1_data_url,
        "image2_data_url.txt":  image2_data_url,
    }.items():
        (GENERATED_RESULT_DIR / name).write_text(content, encoding="utf-8")
    print(f"[저장] {GENERATED_RESULT_DIR}")


def load_saved_result() -> dict:
    title_candidates_path = GENERATED_RESULT_DIR / "title_candidates.txt"
    body_path = GENERATED_RESULT_DIR / "body.html"
    hashtags_path = GENERATED_RESULT_DIR / "hashtags.txt"

    missing = [str(p.name) for p in (title_candidates_path, body_path, hashtags_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"저장된 생성 결과가 부족합니다: {', '.join(missing)}")

    title_text = title_candidates_path.read_text(encoding="utf-8").strip()
    html_body = body_path.read_text(encoding="utf-8")
    hashtags_text = hashtags_path.read_text(encoding="utf-8").strip()

    image_urls_path = GENERATED_RESULT_DIR / "image_urls.txt"
    image_urls = []
    if image_urls_path.exists():
        image_urls = [line.strip() for line in image_urls_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    image1_url = image_urls[0] if len(image_urls) >= 1 else ""
    image2_url = image_urls[1] if len(image_urls) >= 2 else ""
    image1_data_url = (GENERATED_RESULT_DIR / "image1_data_url.txt").read_text(encoding="utf-8").strip() if (GENERATED_RESULT_DIR / "image1_data_url.txt").exists() else ""
    image2_data_url = (GENERATED_RESULT_DIR / "image2_data_url.txt").read_text(encoding="utf-8").strip() if (GENERATED_RESULT_DIR / "image2_data_url.txt").exists() else ""

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


def pick_first_title(title_text: str) -> str:
    for line in title_text.splitlines():
        line = line.strip()
        if not line:
            continue
        return line.split(". ", 1)[1].strip() if ". " in line[:5] else line
    raise ValueError("제목 후보를 찾을 수 없습니다.")


# ------------------------------------------------------------------
# 일상글 자동화 플로우
# ------------------------------------------------------------------
# 글 생성
# ------------------------------------------------------------------

def generate_article(driver: webdriver.Chrome, values: dict, products: list[dict] = None) -> dict:
    """STEP1 image -> STEP2 body -> STEP3 title -> STEP4 hashtags"""
    if products is None:
        products = []
    prompt_products, link_marker_map = _products_with_link_markers(products)
    prompt_values = dict(values)
    prompt_values["products_summary"] = _build_products_summary(prompt_products)

    image_prompt_1 = fill_prompt(PROMPT_IMAGE_1, values)
    validate_coupang_urls(image_prompt_1)

    print("[STEP 1/4] 이미지 생성 중...")
    image1_url = send_image_prompt(driver, image_prompt_1, timeout=180, needed=1)[0]
    image1_data_url = download_image_as_base64(driver, image1_url)
    values["image1_url"] = image1_url
    values["image2_url"] = ""
    log_run("image", image_prompt_1)
    log_coupang_urls(image_prompt_1)

    image2_url = ""
    image2_data_url = ""
    print("[STEP 1/4] 이미지 URL 확보 완료")
    print("[STEP 1/4] 이미지 완료")
    wait_after_image_before_text_prompt(driver, "쿠팡 본문 생성", wait_seconds=10)

    body_prompt = build_coupang_body_prompt(prompt_values)
    validate_coupang_urls(body_prompt)
    print("[STEP 2/4] 본문 생성 중...")
    html_body = send_coupang_body_prompt_after_image(driver, body_prompt, timeout=600)
    html_body = _replace_product_link_markers(html_body, link_marker_map)
    try:
        html_body = _postprocess_and_validate_coupang_body(html_body, products)
    except (ValueError, RuntimeError) as exc:
        print(f"[STEP 2/4] 쿠팡 본문 품질 기준 미달: {exc}")
        print("[STEP 2/4] 정량 비교/단점/대상 독자/근거를 보강해 1회 재작성합니다.")
        rewrite_prompt = body_prompt + f"""

[재작성 지시]
아래 품질 검증 실패 사유를 모두 해결해 HTML 본문 전체를 처음부터 다시 작성하세요.
실패 사유:
{exc}

반드시 포함:
- 상품별 선정 이유: 왜 이 상품을 비교 후보로 골랐는지
- 상품별 가격, 할인율, 평점, 리뷰수, 배송/설치/옵션 중 확인 가능한 정량 비교
- 상품별 아쉬운 점 또는 주의할 점
- 맞는 사람
- 신중히 볼 사람 또는 피할 사람
- 어떤 상품 정보와 비교 기준을 근거로 판단했는지
- 첫 쿠팡 링크 전 충분한 선택 기준/비교 근거
- 가격, 재고, 배송 조건은 변동될 수 있고 상세페이지에서 다시 확인해야 한다는 고지
- 구매하기, 지금 바로, 최저가, 특가, 역대급, 강력 추천 같은 구매 압박 문구 금지

HTML 본문만 출력하세요.
"""
        _assert_prompt_text_clean(rewrite_prompt, "쿠팡 본문 재작성")
        html_body = send_text_prompt(driver, rewrite_prompt, timeout=600)
        html_body = _replace_product_link_markers(html_body, link_marker_map)
        html_body = _postprocess_and_validate_coupang_body(html_body, products)

    # HTML은 '%%IMAGE1_PLACEHOLDER%%' 같은 플레이스홀더를 원본 그대로 유지해야 WAF를 피합니다.
    log_run("body", body_prompt)
    log_coupang_urls(body_prompt)
    print(f"[STEP 2/4] 완료 ({len(html_body)}자)")

    title_prompt = fill_prompt(MASTER_PROMPTS["title"], values)
    print("[STEP 3/4] 제목 생성 중...")
    generated_title_text = send_text_prompt(driver, title_prompt, timeout=180)
    final_title = build_coupang_post_title(products, pick_first_title(generated_title_text))
    title_text = final_title
    print(f"[STEP 3/4] 검색 의도 중심 제목 확정: {final_title}")
    log_run("title", title_prompt)
    print("[STEP 3/4] 완료")

    hashtags_prompt = fill_prompt(MASTER_PROMPTS["hashtags"], values)
    print("[STEP 4/4] 해시태그 생성 중...")
    hashtags_text = send_text_prompt(driver, hashtags_prompt, timeout=180)
    log_run("hashtags", hashtags_prompt)
    print("[STEP 4/4] 완료")

    quality_report_path = save_coupang_quality_report(title_text, html_body, products)

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
        "quality_report":   str(quality_report_path),
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
    print("\n[일상글 모드 시작] 세분화 여행 주제 기반 자동 글쓰기를 시작합니다.")
    daily_topic = pick_daily_micro_topic()
    print(f"[Daily Topic] {daily_topic['daily_topic']}")

    daily_image_prompt = fill_prompt(PROMPT_DAILY_IMAGE, daily_topic)
    daily_body_prompt = fill_prompt(PROMPT_DAILY_BODY, daily_topic)
    daily_meta_prompt = fill_prompt(PROMPT_DAILY_META, daily_topic)

    print("[STEP 1/3] 세분화 주제 기반 썸네일 생성 중...")
    image_url = send_image_prompt(driver, daily_image_prompt, timeout=180, needed=1)[0]
    log_run("daily_image", daily_image_prompt)

    print("[STEP 1/3] 썸네일 data URL 변환 중...")
    image_data_url = download_image_as_base64(driver, image_url)
    print("[STEP 1/3] 완료")

    print("[STEP 2/3] 인플루언서 로직 탑재 HTML 본문 생성 중...")
    html_body = send_daily_body_prompt(driver, daily_body_prompt, timeout=240)
    log_run("daily_body", daily_body_prompt)

    # 일상글 HTML 깨짐 방지:
    # 1) 코드블록/escaped HTML 제거
    # 2) [BASE64_IMAGE_1] 또는 %%IMAGE1_PLACEHOLDER%% 토큰을 실제 img 태그 구조로 보정
    html_body = clean_generated_html_body(html_body)
    html_body = _ensure_daily_image_tag(html_body)
    validate_daily_not_golf_topic(html_body=html_body)
    validate_daily_micro_topic(daily_topic, html_body=html_body)

    print("[STEP 2/3] 완료")

    print("[STEP 3/3] 최적화된 제목 및 해시태그 추출 중...")
    meta_json_text = send_text_prompt(driver, daily_meta_prompt, timeout=120)
    log_run("daily_meta", daily_meta_prompt)

    title_text, hashtags_text = parse_daily_meta_json(meta_json_text)
    validate_daily_not_golf_topic(title=title_text, html_body=html_body, hashtags=hashtags_text)
    validate_daily_micro_topic(daily_topic, title=title_text, html_body=html_body, hashtags=hashtags_text)
    print("[STEP 3/3] 완료")

    save_results(title_text, html_body, hashtags_text, image_url, "", image_data_url, "")
    (GENERATED_RESULT_DIR / "daily_topic.json").write_text(
        json.dumps(daily_topic, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _mark_daily_topic_used(daily_topic)

    return {
        "title": title_text,
        "html_body": html_body,
        "hashtags": hashtags_text,
        "image1_url": image_url,
        "image1_data_url": image_data_url,
        "image2_data_url": "",
    }


def login_and_open_tistory_editor(driver: webdriver.Chrome, allow_manual_login: bool = True) -> None:
    def _switch_to_latest_window(previous_handles: list[str]) -> None:
        current_handles = driver.window_handles
        if len(current_handles) > len(previous_handles):
            driver.switch_to.window(current_handles[-1])

    def _click_new_post_link() -> bool:
        previous_handles = list(driver.window_handles)
        link_xpath = TISTORY_NEW_POST_LINK_XPATH
        fallback_xpath = '//a[contains(@href, "/manage/newpost")]'
        if not driver.find_elements(By.XPATH, link_xpath) and not driver.find_elements(By.XPATH, fallback_xpath):
            return False
        if driver.find_elements(By.XPATH, link_xpath):
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, link_xpath)))
            driver.find_element(By.XPATH, link_xpath).click()
        else:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, fallback_xpath)))
            driver.find_element(By.XPATH, fallback_xpath).click()
        random_sleep(1.0, 2.0)
        _switch_to_latest_window(previous_handles)
        return True

    def _is_editor_ready() -> bool:
        try:
            if driver.find_elements(By.XPATH, TISTORY_TITLE_XPATH):
                return True
        except Exception:
            pass
        current_url = driver.current_url or ""
        return "manage/newpost" in current_url and "daniever2217.tistory.com" in current_url

    def _is_login_required() -> bool:
        current_url = driver.current_url or ""
        if "accounts.kakao.com" in current_url:
            return True
        if "login" in current_url.lower():
            return True
        try:
            return bool(driver.find_elements(By.XPATH, TISTORY_LOGIN_ID_XPATH))
        except Exception:
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
                if _click_new_post_link():
                    return _is_editor_ready()
                driver.get(TISTORY_NEW_POST_URL)
                random_sleep(0.8, 1.4)
                _handle_tistory_editor_alert(driver)
                _dismiss_tistory_continue_draft_popup_with_escape(driver)
                if _is_editor_ready():
                    return True
            time.sleep(2)
        return _is_editor_ready()

    driver.get(TISTORY_NEW_POST_URL)
    random_sleep(0.8, 1.5)
    _handle_tistory_editor_alert(driver)
    _dismiss_tistory_continue_draft_popup_with_escape(driver)

    login_required = _is_login_required()

    if login_required:
        if not allow_manual_login:
            if _wait_for_saved_session_auto_recovery():
                print("[Tistory] 저장 세션으로 글쓰기 화면 자동 복귀 확인")
            else:
                raise RuntimeError(
                    "티스토리 저장 세션이 로그인 화면으로 이동했습니다. "
                    "--tistory-login-only로 티스토리 세션을 다시 저장하세요."
                )
        else:
            driver.get(TISTORY_URL)
            random_sleep(0.3, 0.8)

            if driver.find_elements(By.XPATH, TISTORY_KAKAO_START_XPATH):
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, TISTORY_KAKAO_START_XPATH)))
                driver.find_element(By.XPATH, TISTORY_KAKAO_START_XPATH).click()
                random_sleep(0.3, 0.8)

            if driver.find_elements(By.XPATH, TISTORY_KAKAO_LOGIN_XPATH):
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, TISTORY_KAKAO_LOGIN_XPATH)))
                driver.find_element(By.XPATH, TISTORY_KAKAO_LOGIN_XPATH).click()
                random_sleep(0.8, 1.5)

            print("[Tistory] 수동 로그인 대기 중... 로그인 후 글쓰기 화면이 열릴 때까지 최대 5분 대기합니다.")
            started_at = time.time()
            while time.time() - started_at < 300:
                current_url = driver.current_url
                if "manage/newpost" in current_url:
                    break
                if driver.find_elements(By.XPATH, TISTORY_TITLE_XPATH):
                    break
                if _click_new_post_link():
                    break
                time.sleep(2)
            else:
                raise TimeoutError("Tistory 수동 로그인 대기 시간 초과")

    if not driver.find_elements(By.XPATH, TISTORY_TITLE_XPATH):
        clicked = _click_new_post_link()
        if not clicked and "manage/newpost" not in driver.current_url:
            driver.get(TISTORY_NEW_POST_URL)
            random_sleep(1.0, 2.0)
        _handle_tistory_editor_alert(driver)
        _dismiss_tistory_continue_draft_popup_with_escape(driver)

    _handle_tistory_editor_alert(driver)
    _dismiss_tistory_continue_draft_popup_with_escape(driver)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, TISTORY_TITLE_XPATH))
    )


def run_tistory_only_flow(
    publish: bool = False,
    post_type: str = "coupang",
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
            image1_data_url = result.get("image1_data_url", ""),
            image2_data_url = result.get("image2_data_url", ""),
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
    post_type: str = "coupang",
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

    selected_products = []
    products = []
    values = {}
    performance_topic = None
    if post_type == "coupang":
        performance_topic = pick_coupang_topic_from_performance_csv()
        selected_products, products = prepare_coupang_api_products(
            count=3,
            performance_topic=performance_topic,
        )
        if performance_topic and performance_topic.get("_product_match_failed"):
            print("[Topic] 성과 주제와 매칭되는 상품이 부족해 프롬프트 주제도 기존 상품 기준으로 fallback합니다.")
            performance_topic = None
        set_current_run_coupang_urls(products)
        values = build_prompt_values(products, performance_topic=performance_topic)
        save_coupang_performance_topic(performance_topic)

    driver = create_driver(save_session=False, session_dir=CHATGPT_SESSION_DIR)
    tistory_driver = None
    error_occurred = False

    try:
        prepare_chatgpt_project(driver)

        if post_type == "daily":
            result = generate_daily_article(driver)
        else:
            result = generate_article(driver, values, products)

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
            image1_data_url = result.get("image1_data_url", ""),
            image2_data_url = result.get("image2_data_url", ""),
        )

        if post_type == "coupang":
            mark_products_as_used(selected_products, post_title=result["title"])
            log_product_coupang_urls(products)
            mark_coupang_topic_as_used(performance_topic, post_title=result["title"])
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
    parser = argparse.ArgumentParser(description="티스토리 쿠팡 파트너스 자동화")
    parser.add_argument("--login", action="store_true", help="로그인 세션 저장 모드 실행")
    parser.add_argument("--tistory-login-only", action="store_true", help="티스토리 로그인 세션만 저장 및 검증")
    parser.add_argument("--publish", action="store_true", help="호환용 옵션. main.py는 항상 임시저장으로 마무리")
    parser.add_argument("--draft", action="store_true", help="작성 완료 후 대표이미지까지 지정하고 임시저장")
    parser.add_argument("--resume-tistory", action="store_true", help="저장된 결과로 티스토리 작성만 실행")
    parser.add_argument("--resume-tistory-publish", action="store_true", help="호환용 옵션. 저장된 결과도 임시저장으로 마무리")
    parser.add_argument("--scheduled", action="store_true", help="스케줄러 백그라운드 실행 모드")
    parser.add_argument("--post-type", default="coupang", help="글 유형 (coupang 또는 daily)")
    parser.add_argument("--apply-html-images", action="store_true", help="기존 HTML 파일에 본문/상품 이미지만 삽입")
    parser.add_argument("--html-input-path", default=os.getenv("HTML_INPUT_PATH", ""), help="기존 HTML 입력 파일 경로")
    parser.add_argument("--html-output-path", default=os.getenv("HTML_OUTPUT_PATH", ""), help="이미지 적용 HTML 출력 파일 경로")
    parser.add_argument("--main-image-path", default=os.getenv("MAIN_IMAGE_PATH", ""), help="base64로 삽입할 본문 대표 이미지 경로")
    parser.add_argument("--product-data-path", default=os.getenv("PRODUCT_DATA_PATH", ""), help="쿠팡 상품 JSON 파일 경로")
    parser.add_argument("--image-alt-text", default=os.getenv("IMAGE_ALT_TEXT", "본문 대표 이미지"), help="본문 대표 이미지 alt")
    parser.add_argument("--image-caption", default=os.getenv("IMAGE_CAPTION", ""), help="본문 대표 이미지 캡션")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    scheduled_log_file = None
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # 클립보드 충돌 방지: 다른 자동화 스크립트 완료까지 대기 (최대 30분)
    _automation_lock = FileLock(AUTOMATION_LOCK_PATH, timeout=1800)
    print("[Lock] 다른 자동화 작업 확인 중...", flush=True)
    _automation_lock.acquire()
    print("[Lock] 락 획득 완료 — 작업을 시작합니다.", flush=True)

    try:
        if cli_args.scheduled:
            scheduled_log_file = enable_scheduled_logging(cli_args.post_type)

        post_type = normalize_post_type(cli_args.post_type)

        if cli_args.apply_html_images:
            required_paths = {
                "HTML_INPUT_PATH": cli_args.html_input_path,
                "HTML_OUTPUT_PATH": cli_args.html_output_path,
                "MAIN_IMAGE_PATH": cli_args.main_image_path,
                "PRODUCT_DATA_PATH": cli_args.product_data_path,
            }
            missing_paths = [name for name, value in required_paths.items() if not value]
            if missing_paths:
                raise ValueError(f"필수 경로가 비어 있음: {', '.join(missing_paths)}")
            process_html_images_file(
                html_input_path=Path(cli_args.html_input_path),
                html_output_path=Path(cli_args.html_output_path),
                main_image_path=Path(cli_args.main_image_path),
                product_data_path=Path(cli_args.product_data_path),
                image_alt_text=cli_args.image_alt_text,
                image_caption=cli_args.image_caption,
            )
        elif cli_args.login:
            save_login_session()
        elif cli_args.tistory_login_only:
            save_tistory_session()
        elif cli_args.resume_tistory_publish:
            print("[안전] main.py 공개 발행은 비활성화되어 있어 저장된 결과를 임시저장으로 마무리합니다.")
            run_tistory_only_flow(
                publish=False,
                post_type=post_type,
                allow_manual_login=not cli_args.scheduled,
            )
        elif cli_args.resume_tistory:
            run_tistory_only_flow(
                publish=False,
                post_type=post_type,
                allow_manual_login=not cli_args.scheduled,
            )
        else:
            if cli_args.publish:
                print("[안전] main.py 공개 발행은 비활성화되어 있어 임시저장으로 마무리합니다.")
            publish = False
            run_full_flow(
                publish=publish,
                post_type=post_type,
                keep_browser_on_error=not cli_args.scheduled,
            )
    finally:
        _automation_lock.release()
        print("[Lock] 락 해제 완료")
        if scheduled_log_file:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            scheduled_log_file.close()
