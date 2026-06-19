# 텔레그램 사용 완료 코드. (다음은 본문 글 디테일 추가하는 중)

from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
# webdriver_manager 제거 → 고정 chromedriver 경로 사용
import requests
import pyperclip
import time
import random 
import csv 
import hmac
import hashlib
import json
import re
import os
import subprocess
import schedule
from filelock import FileLock

import sys
import argparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = BASE_DIR
AUTOMATION_LOCK_PATH = os.path.join(PROJECT_ROOT, "자동발행상태기록파일", "automation.lock")
DEFAULT_NAVER_CONNECT_ID = "skssj2629"
BLOG_PERSONA_CONCEPT = (
    "모든 것에 예민한 청담 사는 자녀 둔 어머니. "
    "성분, 면 소재, 마감, 사용 연령, 관리 편의성, 아이 생활 동선까지 세세하게 따지고, "
    "좋아 보이는 이유보다 내 아이와 우리 집 기준에 맞는지를 먼저 보는 사람."
)
os.makedirs(os.path.dirname(AUTOMATION_LOCK_PATH), exist_ok=True)


def load_env_file(path):
    """같은 폴더의 .env 값을 환경변수로 읽는다. 이미 설정된 환경변수는 덮어쓰지 않는다."""
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env_file(os.path.join(BASE_DIR, ".env"))

# =============================================================
# 텔레그램 알림 설정
# =============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
_telegram_warning_shown = False
STATE_DIR = os.path.join(BASE_DIR, "자동발행상태기록파일")
LOGS_DIR = os.path.join(STATE_DIR, "logs")


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

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


def enable_scheduled_logging(post_type):
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_post_type = (post_type or "unknown").strip()
    log_path = os.path.join(LOGS_DIR, f"{timestamp}_{safe_post_type}.log")
    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)
    print(f"[log] scheduled run log: {log_path}")
    return log_file

def send_telegram(message):
    """텔레그램으로 알림 메시지 전송"""
    global _telegram_warning_shown

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        if not _telegram_warning_shown:
            print("   >> [안내] TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 없어 텔레그램 알림을 건너뜁니다.")
            _telegram_warning_shown = True
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except:
        print("   >> [주의] 텔레그램 알림 전송 실패")

print("=" * 80)
print(" 네이버 블로그 자동 글쓰기 (ChatGPT 네이버 전용 - 세션 유지 + 텔레그램 알림)")
print("=" * 80)
print("\n")


def resolve_default_csv_path():
    """환경변수 또는 자주 쓰는 위치에서 CSV 기본 경로를 찾는다."""
    candidates = [
        os.getenv("NAVER_CONNECT_CSV_PATH", "").strip(),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "skssj2629_naver.csv"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return candidates[1]


def create_chrome_driver(options):
    """
    ChromeDriver 경로가 지정돼 있으면 우선 사용하고,
    없으면 로컬에 있는 일반적인 ChromeDriver 경로를 먼저 찾고,
    마지막으로 Selenium Manager 기본 동작을 시도한다.
    """
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
    if chromedriver_path:
        if not os.path.exists(chromedriver_path):
            raise FileNotFoundError(
                f"CHROMEDRIVER_PATH 경로를 찾을 수 없습니다: {chromedriver_path}"
            )
        return webdriver.Chrome(service=Service(chromedriver_path), options=options)

    candidate_paths = [
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "147.0.7727.117", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "147.0.7727.56", "chromedriver.exe"),
        r"C:\py_temp\chromedriver.exe",
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "146.0.7680.165", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "145.0.7632.117", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver", "win64", "146.0.7680.165", "chromedriver-win32", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), "workspace", "chromedriver", "chromedriver-win64", "chromedriver.exe"),
    ]
    for candidate_path in candidate_paths:
        if os.path.exists(candidate_path):
            print(f"   >> [안내] 로컬 ChromeDriver 사용: {candidate_path}")
            return webdriver.Chrome(service=Service(candidate_path), options=options)

    try:
        return webdriver.Chrome(options=options)
    except Exception as e:
        raise RuntimeError(
            "Chrome WebDriver를 시작하지 못했습니다. "
            "CHROMEDRIVER_PATH 환경변수를 설정하거나, 크롬 버전에 맞는 chromedriver.exe를 준비하세요. "
            "이 PC에서는 Selenium Manager가 보안 정책으로 차단될 수 있습니다."
        ) from e


def validate_runtime_requirements(csv_path):
    """실행 전에 바로 확인 가능한 필수 조건을 점검한다."""
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 이상이 필요합니다.")

    if not csv_path:
        raise FileNotFoundError("네이버 쇼핑커넥트 상품 CSV 경로가 비어 있습니다.")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"네이버 쇼핑커넥트 상품 CSV 파일을 찾을 수 없습니다: {csv_path}")


def sanitize_profile_name(name):
    """프로필 폴더명으로 쓸 수 있게 영문/숫자/일부 기호만 남긴다."""
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name.strip())
    return safe_name or "default"


def resolve_naver_profile_path(naver_id):
    env_profile_path = os.getenv("NAVER_CONNECT_PROFILE_PATH", "").strip()
    if env_profile_path:
        return env_profile_path

    legacy_env_profile_path = os.getenv("NAVER_PROFILE_PATH", "").strip()
    if legacy_env_profile_path:
        print(
            "   >> [안내] 네이버커넥팅은 계정 혼선을 막기 위해 NAVER_PROFILE_PATH 대신 "
            "NAVER_CONNECT_PROFILE_PATH 또는 계정별 기본 프로필을 사용합니다."
        )

    home_dir = os.path.expanduser("~")
    id_profile = os.path.join(home_dir, f"ChromeNaverBot_{sanitize_profile_name(naver_id)}")
    legacy_fixed_profile = os.path.join(home_dir, "ChromeNaverBot")

    if os.path.exists(id_profile):
        return id_profile

    # Older runs may have used a single shared profile. Do not reuse it automatically,
    # because it can keep the wrong Naver account logged in.
    if os.path.exists(legacy_fixed_profile):
        print(f"   >> [안내] 공용 네이버 프로필은 자동 사용하지 않습니다: {legacy_fixed_profile}")

    return id_profile


def get_naver_write_url(naver_id):
    return f"https://blog.naver.com/{naver_id}?Redirect=Write&"


def parse_args():
    parser = argparse.ArgumentParser(description="네이버 블로그 자동 글쓰기")
    parser.add_argument("--post-type", choices=["일상", "네이버", "쿠팡"], help="한 번 실행 시 발행할 글 종류")
    parser.add_argument("--naver-id", help="네이버 로그인 ID")
    parser.add_argument("--naver-password", help="네이버 로그인 비밀번호")
    parser.add_argument("--csv-path", help="네이버 쇼핑커넥트 상품 CSV 경로")
    parser.add_argument("--scheduled", action="store_true", help="작업 스케줄러 등 비대화형 실행 모드")
    parser.add_argument(
        "--login",
        "--chatgpt-login",
        dest="chatgpt_login",
        action="store_true",
        help="ChatGPT 네이버 전용 프로젝트 로그인 세션만 저장하고 종료",
    )
    parser.add_argument(
        "--naver-login",
        action="store_true",
        help="네이버 블로그 로그인 세션만 저장하고 종료",
    )
    return parser.parse_args()


def load_runtime_settings(args):
    """환경변수/인자/대화형 입력 순서로 실행 설정을 결정한다."""
    settings = {
        "naver_id": (
            args.naver_id
            or os.getenv("NAVER_CONNECT_NAVER_ID", "")
            or os.getenv("NAVER_CONNECT_ID", "")
            or DEFAULT_NAVER_CONNECT_ID
        ).strip(),
        "naver_password": (
            args.naver_password
            or os.getenv("NAVER_CONNECT_NAVER_PASSWORD", "")
            or os.getenv("NAVER_CONNECT_PASSWORD", "")
            or os.getenv("NAVER_PASSWORD", "")
        ).strip(),
        "csv_file_path": (args.csv_path or os.getenv("NAVER_CONNECT_CSV_PATH", "")).strip(),
    }

    if not settings["csv_file_path"]:
        settings["csv_file_path"] = resolve_default_csv_path()

    if args.scheduled:
        missing = [key for key in ("naver_id", "naver_password") if not settings[key]]
        if missing:
            raise RuntimeError(
                "비대화형 실행에는 NAVER_CONNECT_PASSWORD 또는 NAVER_PASSWORD 환경변수, "
                "또는 동등한 명시 인자가 필요합니다."
            )
        return settings

    if not settings["naver_id"]:
        settings["naver_id"] = input("🔑 네이버 로그인 ID를 입력하세요: ").strip()
    if not settings["naver_password"]:
        settings["naver_password"] = input("🔑 네이버 로그인 비밀번호를 입력하세요: ").strip()
    if not args.csv_path and not os.getenv("NAVER_CONNECT_CSV_PATH", ""):
        entered_csv_path = input("📂 네이버 쇼핑커넥트 상품 CSV 경로 (엔터 시 기본값): ").strip()
        if entered_csv_path:
            settings["csv_file_path"] = entered_csv_path

    return settings

# =============================================================
# 1. 사용자 입력 (최초 1회만) - API Key 불필요!
# =============================================================
v_id = ""
v_passwd = ""
csv_file_path = resolve_default_csv_path()

# 오늘 발행 카운터
daily_stats = {"일상": 0, "네이버": 0, "쿠팡": 0, "에러": 0}
AFFILIATE_POST_TYPES = ("네이버", "쿠팡")
KOREAN_WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

SEASONAL_TOPIC_BANK = {
    "봄": [
        "봄 외출 전 아이 선크림과 얇은 겉옷 기준",
        "아이와 봄 전시를 예약할 때 보는 동선",
        "청담 브런치에서 아이 메뉴와 좌석을 보는 기준",
        "봄철 아기 옷 면 소재와 세탁 후 촉감",
        "미세먼지 있는 날 아이 동반 외출 코스 고르는 기준",
    ],
    "여름": [
        "여름철 아이 선크림 성분과 사용 연령 확인",
        "냉방 강한 레스토랑에서 아이 옷차림 기준",
        "호텔 애프터눈티 아이 동반 예약 전 체크",
        "여름 실내복과 밤부 메쉬 소재를 보는 기준",
        "물놀이 전후 아기 세정과 보습을 보는 기준",
    ],
    "가을": [
        "아이와 클래식 공연 갈 때 좌석과 시간을 보는 기준",
        "가을 전시 나들이에서 아이 컨디션을 지키는 동선",
        "가을 등원복 소재와 겉옷 레이어링 기준",
        "청담 가족 외식 예약 전 아이 메뉴 확인",
        "환절기 아기 보습 제품 성분표 보는 기준",
    ],
    "겨울": [
        "겨울 호텔 라운지에서 아이와 앉기 좋은 자리 기준",
        "아이 실내복 보온성과 면 소재를 함께 보는 기준",
        "겨울 전시와 공연을 아이 컨디션에 맞추는 법",
        "선물용 유아용품 고를 때 성분과 포장을 보는 기준",
        "추운 날 브런치 예약 전 주차와 실내 동선 확인",
    ],
}

WEATHER_MOOD_BANK = {
    "맑음": ["햇살이 좋아서 괜히 밖에 나가고 싶은 기분", "하늘이 유난히 깨끗해 보이는 날"],
    "흐림": ["몸은 살짝 늘어지는데 이상하게 집중은 잘 되는 날", "괜히 커피 한 잔이 길어지는 분위기"],
    "비": ["빗소리 때문에 집 안 분위기가 더 또렷해지는 날", "우산 챙기느라 하루가 조금 더 복잡해진 날"],
    "바람": ["겉옷을 잘못 골랐나 싶을 정도로 바람이 신경 쓰인 날", "머리는 흐트러지는데 기분은 묘하게 개운한 날"],
    "더위": ["가만히 있어도 체력이 빨리는 느낌이 드는 날", "시원한 음료 하나에 기분이 확 달라지는 날"],
    "추위": ["밖에 잠깐만 있어도 손끝이 먼저 반응하는 날", "따뜻한 음식 생각이 계속 나는 날"],
}

LIFESTYLE_TREND_BANK = [
    "아이 동반 공간도 좌석 간격과 동선까지 따져 예약하는 흐름",
    "브런치와 호텔 티타임에서도 아이 메뉴와 소음 정도를 먼저 보는 습관",
    "전시와 공연을 아이 컨디션에 맞춰 고르는 문화생활 흐름",
    "육아용품을 성분, 면 소재, 마감, 세탁 편의성 기준으로 비교하는 관심",
    "유명한 곳보다 우리 아이와 우리 집 기준에 맞는지를 먼저 보는 소비 습관",
    "프리미엄 살림도 예쁜 사진보다 소재와 관리 난이도를 따지는 흐름",
    "키즈 클래스와 체험수업을 선생님 방식과 아이 성향 기준으로 보는 관심",
    "청담, 압구정, 한남 주변 미식 공간을 가족 동선까지 함께 보는 흐름",
]

DAILY_SCENE_BANK = [
    "아이 등원 후 조용한 브런치 예약 시간을 다시 확인한 순간",
    "전시 예약 페이지를 보며 아이가 지치지 않을 동선을 따져본 장면",
    "호텔 라운지 좌석 사진을 보며 아이와 앉기 편한 자리를 고르는 상황",
    "아기 옷 라벨과 봉제선을 손으로 만져보고 다시 접어둔 장면",
    "키즈 클래스 상담 전 아이 성향과 수업 인원을 메모한 순간",
    "선물용 육아용품을 고르며 성분표와 포장 상태를 함께 본 상황",
    "주방용품을 고르기 전 식탁 분위기와 세척 동선을 같이 생각한 장면",
    "청담에서 아이와 외식할 때 주차와 화장실 동선을 먼저 보는 상황",
]

PHOTO_STYLE_BANK = [
    "청담에 사는 30대 한국인 엄마가 자연스럽게 등장하는 고급스러운 라이프스타일 스냅 사진",
    "아이와 함께 외출 준비를 하는 세련된 한국형 자연광 실내 사진",
    "프리미엄 브런치, 전시, 호텔 티타임 분위기를 담은 블로그용 라이프스타일 사진",
    "성분표, 면 소재, 아이 식기, 엄마의 노트가 정갈하게 보이는 사진",
]

DAILY_CATEGORY_BANK = [
    "청담미식",
    "프리미엄문화생활",
    "청담키즈라이프",
    "엄마취향살림",
    "아이교육체험",
    "호텔브런치티타임",
]

DAILY_SEARCH_INTENT_BANK = {
    "청담미식": [
        {
            "search_phrase": "청담동 가족 브런치 고를 때 보는 기준",
            "reader_problem": "아이와 함께 갈 브런치 공간을 고를 때 음식 맛뿐 아니라 좌석 간격, 소음, 서비스, 메뉴 구성이 모두 신경 쓰이는 상황",
            "reader_promise": "예약 전 확인할 좌석, 동선, 아이 메뉴, 분위기, 주차 기준을 청담 엄마 시선으로 정리",
            "practical_points": ["유모차나 아이 동선이 불편하지 않은지 보기", "좌석 간격과 소음 정도를 먼저 확인하기", "아이와 나눠 먹기 좋은 메뉴 구성이 있는지 보기", "주차와 예약 시간 여유를 함께 체크하기"],
            "mistakes_to_avoid": ["분위기 사진만 보고 예약하기", "아이 식사 시간과 피크 타임을 겹치게 잡기"],
            "faq_questions": ["아이와 브런치 예약 전 무엇을 먼저 봐야 할까?", "청담 브런치 공간은 분위기 말고 어떤 기준이 중요할까?"],
            "related_keywords": ["청담동 브런치", "아이동반식사", "가족브런치", "프리미엄미식", "예약기준"],
            "image_scene": "청담 스타일의 밝은 브런치 테이블과 아이 식기, 정갈한 꽃 장식이 보이는 장면",
        },
        {
            "search_phrase": "아이와 파인다이닝 갈 때 확인할 것",
            "reader_problem": "특별한 날 아이와 좋은 레스토랑을 가고 싶지만 분위기, 메뉴, 시간대가 맞을지 걱정되는 상황",
            "reader_promise": "예약 전 아이 동반 가능 여부, 코스 시간, 좌석, 메뉴, 복장과 매너 기준을 정리",
            "practical_points": ["아이 동반 가능 시간대와 좌석 위치 확인하기", "코스 진행 시간이 아이 컨디션과 맞는지 보기", "맵거나 향이 강한 메뉴가 많은지 확인하기", "주차와 대기 동선을 미리 체크하기"],
            "mistakes_to_avoid": ["유명하다는 이유만으로 예약하기", "아이 컨디션과 식사 시간을 고려하지 않기"],
            "faq_questions": ["아이와 파인다이닝은 몇 시 예약이 좋을까?", "메뉴보다 먼저 확인할 조건은 무엇일까?"],
            "related_keywords": ["아이동반파인다이닝", "청담레스토랑", "가족외식", "예약체크", "미식생활"],
            "image_scene": "고급 레스토랑 테이블 세팅과 아이용 작은 식기가 함께 놓인 정갈한 장면",
        },
    ],
    "프리미엄문화생활": [
        {
            "search_phrase": "아이와 전시회 갈 때 확인할 기준",
            "reader_problem": "아이와 전시를 보러 가고 싶지만 관람 시간, 동선, 작품 분위기, 체험 요소가 맞을지 고민되는 상황",
            "reader_promise": "전시 난이도, 관람 동선, 대기 시간, 사진 가능 여부, 아이 집중 시간을 기준으로 정리",
            "practical_points": ["아이 눈높이에서 볼 수 있는 작품인지 확인하기", "관람 시간이 너무 길지 않은지 보기", "대기 줄과 입장 시간을 미리 체크하기", "전시 후 식사나 카페 동선을 같이 잡기"],
            "mistakes_to_avoid": ["전시명만 보고 바로 예약하기", "아이 집중 시간을 생각하지 않고 긴 코스를 잡기"],
            "faq_questions": ["아이와 전시회는 어떤 기준으로 고르면 좋을까?", "청담 엄마들이 전시 동선을 볼 때 중요한 점은 무엇일까?"],
            "related_keywords": ["아이와전시회", "서울전시", "문화생활", "청담라이프", "주말나들이"],
            "image_scene": "갤러리 복도에서 아이와 작품을 조용히 바라보는 세련된 한국형 장면",
        },
        {
            "search_phrase": "아이와 클래식 공연 갈 때 체크할 것",
            "reader_problem": "아이에게 공연 경험을 만들어주고 싶지만 공연 시간, 좌석, 소리 크기, 관람 예절이 걱정되는 상황",
            "reader_promise": "연령 제한, 러닝타임, 좌석 위치, 공연장 동선, 아이 컨디션 기준을 정리",
            "practical_points": ["연령 제한과 관람 가능 시간을 먼저 확인하기", "좌석이 너무 앞쪽이거나 소리가 강하지 않은지 보기", "공연 전후 대기 공간과 화장실 동선 보기", "아이에게 관람 예절을 미리 짧게 알려주기"],
            "mistakes_to_avoid": ["유명 공연이라는 이유만으로 예매하기", "러닝타임과 아이 컨디션을 따로 보지 않기"],
            "faq_questions": ["아이와 클래식 공연은 어느 좌석이 편할까?", "처음 공연을 볼 때 무엇부터 확인해야 할까?"],
            "related_keywords": ["아이와공연", "클래식공연", "문화생활", "예매기준", "청담엄마"],
            "image_scene": "공연장 로비에서 프로그램북과 아이 재킷을 정리하는 고급스러운 장면",
        },
    ],
    "청담키즈라이프": [
        {
            "search_phrase": "아기 옷 소재 고르는 기준",
            "reader_problem": "아기 옷을 고를 때 디자인보다 면 소재, 봉제, 세탁 후 촉감, 계절감이 더 신경 쓰이는 상황",
            "reader_promise": "면 소재, 봉제선, 라벨 위치, 세탁 편의성, 활동성을 기준으로 정리",
            "practical_points": ["피부에 닿는 면 소재와 혼용률 확인하기", "목과 겨드랑이 봉제선이 거슬리지 않는지 보기", "세탁 후 줄어듦과 건조 속도 생각하기", "등원복인지 실내복인지 용도를 나누기"],
            "mistakes_to_avoid": ["색감과 사진만 보고 고르기", "세탁 후 촉감과 활동성을 빼고 보기"],
            "faq_questions": ["아기 옷은 소재를 어디까지 봐야 할까?", "등원복과 실내복 기준은 어떻게 다를까?"],
            "related_keywords": ["아기옷소재", "유아내복", "면소재", "등원룩", "청담엄마"],
            "image_scene": "아기 옷장 앞에서 면 소재와 라벨을 확인하는 세련된 한국형 장면",
        },
        {
            "search_phrase": "아기용품 성분 확인하는 방법",
            "reader_problem": "물티슈, 선크림, 세정제처럼 아이 피부에 닿는 제품을 고를 때 성분표와 사용 연령이 복잡하게 느껴지는 상황",
            "reader_promise": "성분표, 사용 연령, 향, 세정 방식, 보관 조건을 차분히 보는 기준 정리",
            "practical_points": ["사용 연령과 사용 부위를 먼저 확인하기", "향이 강한지 무향인지 보기", "피부에 남는 제품인지 씻어내는 제품인지 나누기", "개봉 후 보관과 휴대 방식을 함께 확인하기"],
            "mistakes_to_avoid": ["저자극 문구만 보고 바로 고르기", "성분과 사용 연령을 따로 확인하지 않기"],
            "faq_questions": ["아기용품 성분은 어디부터 보면 좋을까?", "향이 있는 제품은 어떤 점을 확인해야 할까?"],
            "related_keywords": ["아기용품성분", "유아선크림", "아기물티슈", "저자극", "육아템체크"],
            "image_scene": "깔끔한 욕실 선반에서 아기용품 성분표를 확인하는 청담 스타일 장면",
        },
    ],
    "엄마취향살림": [
        {
            "search_phrase": "프리미엄 주방용품 고를 때 기준",
            "reader_problem": "주방용품을 고를 때 예쁜 디자인보다 소재, 마감, 세척, 아이와 함께 쓰기 편한지가 더 신경 쓰이는 상황",
            "reader_promise": "소재, 코팅, 세척 동선, 보관성, 식탁 분위기를 함께 보는 기준 정리",
            "practical_points": ["음식이 닿는 소재와 마감 확인하기", "세척이 어렵지 않은 구조인지 보기", "아이 식기와 같이 써도 분위기가 맞는지 보기", "수납장 안에서 자리 차지를 생각하기"],
            "mistakes_to_avoid": ["사진 예쁜 제품만 보고 고르기", "관리 난이도와 수납을 빼고 보기"],
            "faq_questions": ["프리미엄 주방용품은 무엇부터 봐야 할까?", "소재와 디자인 중 무엇을 먼저 봐야 할까?"],
            "related_keywords": ["프리미엄주방용품", "소재체크", "청담살림", "식탁세팅", "육아살림"],
            "image_scene": "고급스러운 주방 조리대 위에 정갈한 식기와 아이 컵이 놓인 장면",
        },
    ],
    "아이교육체험": [
        {
            "search_phrase": "아이 체험수업 고를 때 보는 기준",
            "reader_problem": "발레, 미술, 영어, 음악 같은 체험수업을 고를 때 분위기보다 선생님 방식과 아이 성향이 더 중요하게 느껴지는 상황",
            "reader_promise": "수업 인원, 선생님 피드백, 아이 성향, 이동 동선, 수업 후 피로도를 기준으로 정리",
            "practical_points": ["아이 성향과 수업 방식이 맞는지 보기", "한 반 인원과 피드백 방식을 확인하기", "수업 시간대가 아이 컨디션과 맞는지 보기", "이동 거리와 대기 공간까지 생각하기"],
            "mistakes_to_avoid": ["유명하다는 이유만으로 등록하기", "아이 성향보다 엄마 취향만 앞세우기"],
            "faq_questions": ["아이 체험수업은 몇 번 보고 결정하는 게 좋을까?", "청담 엄마들이 수업을 볼 때 따지는 기준은 무엇일까?"],
            "related_keywords": ["아이체험수업", "키즈클래스", "청담육아", "문화센터", "교육체크"],
            "image_scene": "아이 체험수업 가방과 엄마의 노트가 정갈하게 놓인 고급스러운 장면",
        },
    ],
    "호텔브런치티타임": [
        {
            "search_phrase": "호텔 애프터눈티 아이와 갈 때 기준",
            "reader_problem": "호텔 애프터눈티를 아이와 가고 싶지만 좌석, 메뉴 구성, 소음, 시간대가 맞을지 신경 쓰이는 상황",
            "reader_promise": "예약 시간, 좌석 간격, 디저트 구성, 아이가 먹기 쉬운 메뉴, 동선을 기준으로 정리",
            "practical_points": ["아이 컨디션이 좋은 시간대로 예약하기", "좌석 간격과 대화 소음 정도 보기", "디저트 구성이 너무 달거나 향이 강하지 않은지 확인하기", "호텔 주차와 화장실 동선을 미리 생각하기"],
            "mistakes_to_avoid": ["사진만 보고 예약하기", "아이 식사와 낮잠 시간을 고려하지 않기"],
            "faq_questions": ["아이와 애프터눈티는 어떤 시간대가 좋을까?", "호텔 라운지는 어떤 기준을 먼저 봐야 할까?"],
            "related_keywords": ["호텔애프터눈티", "아이동반호텔", "청담라이프", "티타임", "프리미엄미식"],
            "image_scene": "호텔 라운지 테이블 위 애프터눈티 세트와 아이용 작은 접시가 놓인 장면",
        },
    ],
    "장마습기": [
        {
            "search_phrase": "장마철 집 습도 낮추는 방법",
            "reader_problem": "비가 이어지면 방 안 공기가 무겁고 바닥, 창가, 옷장 주변이 눅눅해지는 상황",
            "reader_promise": "환기 시간, 습기 위치, 빨래 간격, 제습 선택 기준을 집 구조별로 정리",
            "practical_points": ["습기가 먼저 모이는 창가와 벽면 확인하기", "비가 잠깐 그친 시간에 짧게 맞바람 환기하기", "젖은 수건과 빨래를 한곳에 오래 쌓아두지 않기", "제습기는 방 크기보다 물이 생기는 위치부터 보고 판단하기"],
            "mistakes_to_avoid": ["창문을 계속 닫고 방향제만 쓰기", "빨래가 마르기 전에 옷장이나 서랍에 넣기"],
            "faq_questions": ["비 오는 날에도 환기를 해도 될까?", "제습기 전에 먼저 확인할 것은 뭘까?"],
            "related_keywords": ["실내 습도", "장마철 빨래", "환기", "제습기", "곰팡이"],
            "image_scene": "비 오는 날 창가와 빨래 건조대가 보이는 현실적인 실내 장면",
        },
        {
            "search_phrase": "방이 꿉꿉할 때 해결 방법",
            "reader_problem": "방에 들어올 때마다 공기가 무겁고 냄새가 남아 원인을 찾고 싶은 상황",
            "reader_promise": "습도, 환기, 빨래, 창문 구조를 나눠 꿉꿉함의 원인을 확인하는 순서 정리",
            "practical_points": ["냄새가 나는 위치와 습기가 모이는 위치를 따로 보기", "창문 하나뿐인 방은 선풍기로 공기 흐름 만들기", "침구와 커튼처럼 습기를 머금는 물건 확인하기", "바닥보다 벽면과 창가를 먼저 살펴보기"],
            "mistakes_to_avoid": ["냄새를 향으로만 덮기", "환기 없이 제습 제품만 먼저 찾기"],
            "faq_questions": ["방이 꿉꿉한 이유는 습도 때문일까?", "창문이 하나뿐인 방은 어떻게 환기할까?"],
            "related_keywords": ["방 습도", "집안 냄새", "환기", "선풍기", "실내 공기"],
            "image_scene": "작은 방 창문과 선풍기, 정리된 침구가 함께 보이는 생활 사진",
        },
    ],
    "냉방전기세": [
        {
            "search_phrase": "에어컨 전기세 줄이는 법",
            "reader_problem": "더워서 에어컨은 켜야 하지만 전기세가 걱정돼 사용 기준이 필요한 상황",
            "reader_promise": "에어컨, 선풍기, 창문 방향, 사용 시간 기준을 생활 동선에 맞춰 정리",
            "practical_points": ["먼저 햇빛이 오래 들어오는 창문부터 가리기", "에어컨 바람이 방 전체로 흐르도록 선풍기 방향 잡기", "문을 자주 여닫는 공간은 냉방 범위를 줄이기", "필터 먼지와 냄새를 사용 전 확인하기"],
            "mistakes_to_avoid": ["온도 설정만 낮추고 공기 흐름을 보지 않기", "방문과 창문 틈을 그대로 둔 채 오래 켜두기"],
            "faq_questions": ["에어컨과 선풍기를 같이 쓰면 왜 도움이 될까?", "냉방비를 줄이려면 무엇부터 확인해야 할까?"],
            "related_keywords": ["냉방비", "에어컨 전기세", "선풍기", "서큘레이터", "에어컨 필터"],
            "image_scene": "에어컨과 선풍기가 함께 놓인 여름철 거실 또는 원룸 장면",
        },
        {
            "search_phrase": "선풍기 틀어도 시원하지 않은 이유",
            "reader_problem": "선풍기를 틀어도 바람만 오고 방 전체는 더운 느낌이 계속되는 상황",
            "reader_promise": "선풍기 위치, 바람 방향, 창문 상태, 실내 열기를 나눠 확인하는 기준 정리",
            "practical_points": ["선풍기를 사람 쪽만 보게 두지 말고 공기 흐름을 만들기", "뜨거운 창가와 벽면 근처 열기 확인하기", "문과 창문을 이용해 빠지는 바람길 만들기", "서큘레이터가 필요한 상황과 선풍기로 충분한 상황 나누기"],
            "mistakes_to_avoid": ["가장 센 바람만 계속 쓰기", "뜨거운 공기가 빠질 곳을 만들지 않기"],
            "faq_questions": ["선풍기는 창문 쪽과 사람 쪽 중 어디로 두는 게 좋을까?", "서큘레이터와 선풍기는 언제 차이가 날까?"],
            "related_keywords": ["선풍기", "서큘레이터", "공기 흐름", "냉방", "원룸"],
            "image_scene": "창문 근처에 선풍기가 놓이고 커튼이 살짝 움직이는 원룸 장면",
        },
    ],
    "환기공기질": [
        {
            "search_phrase": "비 오는 날 환기해도 될까",
            "reader_problem": "비가 오면 창문을 열어야 할지 닫아야 할지 헷갈리는 상황",
            "reader_promise": "비의 세기, 바람 방향, 실내 냄새, 습도 느낌을 기준으로 환기 여부 정리",
            "practical_points": ["비가 들이치지 않는 창문부터 짧게 열기", "요리나 빨래 후에는 환기 시간을 따로 잡기", "창문을 하나만 여는 대신 방문과 현관 쪽 흐름 보기", "환기 후 습기가 남는 위치를 다시 확인하기"],
            "mistakes_to_avoid": ["비가 오면 무조건 창문을 닫아두기", "환기 후 물기 닦는 과정을 빼먹기"],
            "faq_questions": ["비 오는 날 환기는 몇 번 하는 게 좋을까?", "비가 들이치면 어떻게 환기해야 할까?"],
            "related_keywords": ["환기", "실내 공기", "습도", "장마철", "집안 냄새"],
            "image_scene": "비 오는 날 살짝 열린 창문과 깨끗한 실내 공기가 느껴지는 장면",
        },
        {
            "search_phrase": "미세먼지 심한 날 환기해도 되는지",
            "reader_problem": "공기가 안 좋은 날 창문을 열기 불안하지만 집 안 공기도 답답한 상황",
            "reader_promise": "환기 타이밍, 창문 여는 방식, 공기청정기 필터 확인 기준을 정리",
            "practical_points": ["외부 공기 상태를 확인한 뒤 짧게 환기하기", "청소 직후에는 먼지가 가라앉는 시간을 고려하기", "공기청정기 필터 냄새와 먼지 상태 보기", "요리 후 냄새는 공기청정기만 믿지 않고 배출 먼저 하기"],
            "mistakes_to_avoid": ["공기청정기만 켜두고 환기를 전혀 하지 않기", "먼지가 많은 날 창문을 오래 열어두기"],
            "faq_questions": ["미세먼지 많은 날에도 짧은 환기가 필요할까?", "공기청정기 필터는 언제 확인하는 게 좋을까?"],
            "related_keywords": ["미세먼지", "환기", "공기청정기", "필터", "실내 공기"],
            "image_scene": "공기청정기와 창문, 먼지 없는 밝은 실내가 보이는 생활 사진",
        },
    ],
    "빨래냄새": [
        {
            "search_phrase": "장마철 빨래 냄새 없애는 법",
            "reader_problem": "빨래를 했는데도 수건이나 옷에서 꿉꿉한 냄새가 나는 상황",
            "reader_promise": "세탁 전 보관, 세탁 후 건조, 빨래 간격, 환기 순서를 나눠 정리",
            "practical_points": ["젖은 수건을 세탁 전 오래 쌓아두지 않기", "세탁 후 바로 꺼내 넓게 펴서 말리기", "빨래 사이 간격을 벌려 바람길 만들기", "냄새가 심한 수건은 보관 위치부터 따로 보기"],
            "mistakes_to_avoid": ["섬유유연제만 많이 넣기", "덜 마른 빨래를 바로 접어 넣기"],
            "faq_questions": ["빨래 냄새는 세제 문제일까 건조 문제일까?", "비 오는 날 빨래는 어디에 널어야 할까?"],
            "related_keywords": ["장마철 빨래", "빨래 냄새", "건조", "환기", "제습기"],
            "image_scene": "실내 빨래 건조대와 창가, 수건이 넓게 널린 현실적인 장면",
        },
        {
            "search_phrase": "빨래가 잘 안 마르는 이유",
            "reader_problem": "하루가 지나도 빨래가 축축하고 냄새까지 생기는 상황",
            "reader_promise": "빨래 양, 간격, 바람 방향, 실내 습기를 기준으로 원인 확인 순서 정리",
            "practical_points": ["한 번에 너무 많은 빨래를 몰아 널지 않기", "두꺼운 옷과 얇은 옷을 섞어 간격 조절하기", "선풍기 바람이 빨래 사이로 지나가게 두기", "창가와 벽면에 습기가 차는지 확인하기"],
            "mistakes_to_avoid": ["빨래를 촘촘하게 붙여 널기", "바람이 빨래 앞에서만 멈추게 두기"],
            "faq_questions": ["빨래는 실내 어디에 널어야 빨리 마를까?", "선풍기를 빨래에 직접 틀어도 될까?"],
            "related_keywords": ["빨래 건조", "빨래 냄새", "선풍기", "실내 습도", "장마철"],
            "image_scene": "선풍기 바람이 빨래 건조대 사이로 지나가는 실내 장면",
        },
    ],
    "집안냄새곰팡이": [
        {
            "search_phrase": "여름철 집안 냄새 제거 방법",
            "reader_problem": "더운 날 집에 들어오면 음식 냄새, 습기 냄새, 하수구 냄새가 섞이는 상황",
            "reader_promise": "냄새 위치를 나누고 환기, 배수구, 쓰레기, 섬유류 순서로 확인하는 방법 정리",
            "practical_points": ["냄새가 나는 위치를 주방, 욕실, 창가, 옷장으로 나누기", "배수구와 음식물 쓰레기 주변을 먼저 확인하기", "커튼과 러그처럼 냄새를 머금는 물건 보기", "환기 후에도 남는 냄새는 습기 위치와 함께 확인하기"],
            "mistakes_to_avoid": ["방향제만 두고 원인을 확인하지 않기", "냄새 나는 공간을 닫아둔 채 방치하기"],
            "faq_questions": ["집안 냄새는 어디부터 확인해야 할까?", "환기해도 냄새가 남는 이유는 뭘까?"],
            "related_keywords": ["집안 냄새", "환기", "배수구", "습기", "공기청정기"],
            "image_scene": "깨끗하게 정리된 주방과 창문 환기가 함께 보이는 생활 사진",
        },
        {
            "search_phrase": "곰팡이 생기기 쉬운 곳 확인법",
            "reader_problem": "습한 계절에 창가, 벽면, 옷장 주변 곰팡이가 걱정되는 상황",
            "reader_promise": "눈에 잘 안 보이는 습기 위치와 곰팡이 전조 신호를 집 안 동선별로 정리",
            "practical_points": ["가구 뒤와 창가 아래쪽을 먼저 확인하기", "옷장 안 냄새와 벽면 차가운 부분 보기", "욕실 문틀과 실리콘 주변 물기 확인하기", "환기와 제습이 닿지 않는 구석을 따로 관리하기"],
            "mistakes_to_avoid": ["보이는 곳만 닦고 가구 뒤를 빼먹기", "물기 있는 상태로 문을 닫아두기"],
            "faq_questions": ["곰팡이는 집 안 어디에 먼저 생길까?", "곰팡이를 줄이려면 환기와 제습 중 무엇이 먼저일까?"],
            "related_keywords": ["곰팡이", "습기", "창문 결로", "옷장 냄새", "제습기"],
            "image_scene": "창가와 옷장 주변을 점검하는 듯한 깔끔한 실내 장면",
        },
    ],
    "생활가전체크": [
        {
            "search_phrase": "제습기 10L 16L 차이",
            "reader_problem": "제습기를 알아보는데 용량 차이가 실제 생활에서 어떻게 다른지 헷갈리는 상황",
            "reader_promise": "방 크기, 빨래 양, 사용 위치, 물통 관리 기준으로 용량 차이를 정리",
            "practical_points": ["사용할 공간이 원룸인지 거실인지 먼저 나누기", "빨래 건조 보조용인지 방 습도 관리용인지 구분하기", "물통 비우는 빈도와 이동 편의성 확인하기", "상세정보의 적용 면적과 소비전력을 함께 보기"],
            "mistakes_to_avoid": ["무조건 큰 용량만 고르기", "보관 공간과 소음 확인을 빼먹기"],
            "faq_questions": ["제습기는 큰 용량이 항상 좋을까?", "원룸에서는 어떤 기준을 먼저 봐야 할까?"],
            "related_keywords": ["제습기", "제습기 용량", "원룸", "빨래 건조", "구매 전 체크"],
            "image_scene": "작은 방 한쪽에 제습기가 놓이고 빨래 건조대가 보이는 장면",
        },
        {
            "search_phrase": "서큘레이터 선풍기 차이",
            "reader_problem": "선풍기와 서큘레이터 중 어떤 걸 골라야 집에 맞을지 고민되는 상황",
            "reader_promise": "시원함, 공기 순환, 냉방 보조, 소음과 보관 기준으로 차이를 정리",
            "practical_points": ["사람에게 직접 바람을 맞힐지 공기를 돌릴지 목적 정하기", "에어컨과 같이 쓸 공간인지 확인하기", "소음이 신경 쓰이는 밤 사용 여부 보기", "보관할 공간과 청소 편의성 확인하기"],
            "mistakes_to_avoid": ["둘을 같은 용도로만 생각하기", "바람 세기만 보고 공기 흐름을 보지 않기"],
            "faq_questions": ["서큘레이터는 선풍기보다 무조건 시원할까?", "에어컨과 같이 쓸 때는 어떤 게 나을까?"],
            "related_keywords": ["서큘레이터", "선풍기", "냉방", "공기 순환", "구매 전 체크"],
            "image_scene": "선풍기와 서큘레이터가 함께 놓인 여름철 실내 비교 장면",
        },
    ],
}

HEALTH_TOPIC_BANK = [
    "피곤할 때 생활 루틴 점검",
    "수면 습관과 하루 집중력",
    "가벼운 걷기와 컨디션 회복",
    "물 마시는 습관과 몸 반응",
    "스트레칭을 미루지 않는 법",
]

ECONOMY_TOPIC_BANK = [
    "요즘 체감 물가와 소비 습관",
    "월급날 전후 지출 흐름",
    "절약과 만족감 사이의 균형",
    "커피값, 배달비처럼 작은 고정지출",
    "요즘 투자 뉴스를 볼 때 드는 생각",
]

NEWS_TOPIC_BANK = [
    "오늘 눈에 띈 생활 뉴스 한두 가지",
    "건강 이슈와 일상 습관의 연결",
    "경제 뉴스가 실제 소비에 미치는 느낌",
    "트렌드 뉴스와 내 생활의 거리감",
    "화제 이슈를 가볍게 정리해보는 관점",
]

COMBO_TOPIC_BANK = [
    "날씨와 아이 외출복 소재를 함께 보는 생활 기록",
    "청담 브런치 예약과 아이 동반 동선을 같이 점검하는 글",
    "호텔 티타임과 아이 컨디션 체크를 함께 정리하는 글",
    "전시 관람 동선과 키즈 클래스 선택 기준을 엮은 글",
    "아기용품 성분표와 엄마 취향 살림 기준을 함께 보는 글",
    "프리미엄 문화생활과 아이 생활 리듬을 함께 정리하는 글",
]

DAILY_CATEGORY_ROTATION_FILE = "daily_category_rotation.json"
COUPANG_ANGLE_ROTATION_FILE = "naver_connect_angle_rotation.json"
COUPANG_SELECTION_HISTORY_FILE = "naver_connect_selection_history.json"
COUPANG_USED_PRODUCTS_FILE = "naver_connect_used_products.json"
COUPANG_SELECTION_HISTORY_LIMIT = 6
COUPANG_API_DOMAIN = "https://api-gateway.coupang.com"
COUPANG_API_BASE_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1"

COUPANG_GROUP_RULES = [
    ("이유식분유", ["분유", "이유식", "야채큐브", "단호박", "브로콜리", "큐브", "토핑", "미음", "산양분유", "트루맘", "후디스"]),
    ("수유용품", ["젖병", "젖꼭지", "보틀워머", "분유쉐이커", "모유", "액상분유", "분유 제조기"]),
    ("유아스킨위생", ["물티슈", "선크림", "치약", "칫솔", "샴푸", "바디오일", "소독티슈", "소독", "크림", "저자극"]),
    ("유아의류", ["아기내복", "내복", "실내복", "스와들", "양말", "윈드브레이커", "후드", "신생아", "밤부", "메쉬"]),
    ("유아장난감교구", ["장난감", "자석", "블럭", "블록", "아기체육관", "교구", "액티비티", "스피너"]),
    ("유아식기보관", ["이유식 용기", "식기", "용기", "실리콘캡", "락앤락", "보관용기"]),
    ("선풍기", ["선풍기", "써큘레이터", "서큘레이터", "테이블팬", "탁상용", "bldc"]),
    ("에어컨", ["에어컨", "냉방"]),
    ("냉풍기", ["냉풍기"]),
    ("제습기", ["제습기"]),
    ("가습기", ["가습기"]),
    ("모기퇴치", ["모기", "훈증기", "홈매트", "살충"]),
    ("건조대", ["건조대", "빨래"]),
    ("전기포트", ["전기포트", "전기 주전자", "포트", "주전자"]),
]

COUPANG_ANGLE_BANK = [
    {
        "name": "생활문제해결형",
        "post_angle": "아이를 키우며 생기는 작은 불편을 줄이기 위해 구매 전 확인할 조건을 정리하는 글",
        "title_seed": "엄마 입장에서 어떤 조건을 먼저 보면 좋은지 드러나는 제목",
        "thumbnail_prompt": "청담 아파트나 외출 준비 공간에서 아이 용품을 차분히 살피는 장면",
        "cta_text": "비슷한 고민이 있었다면 상세 정보와 후기 흐름을 먼저 확인해보면 좋겠다는 흐름",
    },
    {
        "name": "비교고민정리형",
        "post_angle": "비슷한 유아용품을 비교할 때 성분, 소재, 월령, 관리 편의성을 나눠보는 글",
        "title_seed": "성분소재월령관리 기준이 드러나는 제목",
        "thumbnail_prompt": "여러 유아용품 라벨과 상세 정보를 비교하는 세련된 엄마의 책상 장면",
        "cta_text": "평점과 리뷰 흐름까지 같이 보면 판단이 조금 더 또렷해진다는 흐름",
    },
    {
        "name": "아이동반동선형",
        "post_angle": "아이와 외출하거나 등원 전후에 쓰는 상황을 기준으로 휴대, 세척, 보관 동선을 따져보는 글",
        "title_seed": "아이 동반 상황에서 놓치기 쉬운 조건이 보이는 제목",
        "thumbnail_prompt": "유모차, 기저귀 가방, 아이 외출복이 자연스럽게 놓인 청담 엄마의 외출 준비 장면",
        "cta_text": "아이와 움직이는 날 자주 확인하게 되는 조건부터 상세정보에서 보는 흐름",
    },
    {
        "name": "성분소재검토형",
        "post_angle": "성분, 면 소재, 마감, 세탁과 세척 조건을 예민한 엄마의 기준으로 검토하는 글",
        "title_seed": "성분과 소재를 먼저 보는 엄마 기준이 드러나는 제목",
        "thumbnail_prompt": "성분표나 의류 라벨을 손으로 살피는 차분한 한국형 육아 라이프스타일 장면",
        "cta_text": "좋아 보이는 이유보다 내 아이 기준에 맞는지 상세정보에서 확인하는 흐름",
    },
    {
        "name": "후기흐름확인형",
        "post_angle": "평점과 리뷰 개수를 참고하되 보장처럼 말하지 않고 후기 흐름에서 볼 기준을 정리하는 글",
        "title_seed": "후기와 상세정보에서 먼저 볼 기준이 드러나는 제목",
        "thumbnail_prompt": "노트북이나 휴대폰으로 후기와 상세정보를 확인하는 청담 엄마의 테이블 장면",
        "cta_text": "리뷰가 많이 쌓인 제품일수록 내 아이와 맞는 조건을 먼저 가려보자는 흐름",
    },
]


def get_daily_category_rotation_path():
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, DAILY_CATEGORY_ROTATION_FILE)


def get_coupang_angle_rotation_path():
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, COUPANG_ANGLE_ROTATION_FILE)


def get_coupang_selection_history_path():
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, COUPANG_SELECTION_HISTORY_FILE)


def get_coupang_used_products_path():
    os.makedirs(STATE_DIR, exist_ok=True)
    return os.path.join(STATE_DIR, COUPANG_USED_PRODUCTS_FILE)


def load_daily_category_rotation():
    rotation_path = get_daily_category_rotation_path()
    if not os.path.exists(rotation_path):
        return {}
    try:
        with open(rotation_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_daily_category_rotation(payload):
    rotation_path = get_daily_category_rotation_path()
    with open(rotation_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_coupang_angle_rotation():
    rotation_path = get_coupang_angle_rotation_path()
    if not os.path.exists(rotation_path):
        return {}
    try:
        with open(rotation_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_coupang_angle_rotation(payload):
    rotation_path = get_coupang_angle_rotation_path()
    with open(rotation_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_coupang_selection_history():
    history_path = get_coupang_selection_history_path()
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def save_coupang_selection_history(items):
    history_path = get_coupang_selection_history_path()
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(items[-COUPANG_SELECTION_HISTORY_LIMIT:], f, ensure_ascii=False, indent=2)


def load_coupang_used_products():
    used_path = get_coupang_used_products_path()
    if not os.path.exists(used_path):
        return {}
    try:
        with open(used_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def save_coupang_used_products(items):
    used_path = get_coupang_used_products_path()
    with open(used_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def get_next_daily_category(now):
    today_key = now.strftime("%Y-%m-%d")
    payload = load_daily_category_rotation()
    queue = payload.get(today_key)

    if isinstance(queue, list):
        queue = [item for item in queue if item in DAILY_CATEGORY_BANK]

    if not isinstance(queue, list) or not queue:
        queue = DAILY_CATEGORY_BANK[:]
        random.shuffle(queue)

    next_category = queue.pop(0)
    payload = {today_key: queue}
    save_daily_category_rotation(payload)
    return next_category


def get_next_coupang_angle(now):
    today_key = now.strftime("%Y-%m-%d")
    payload = load_coupang_angle_rotation()
    queue = payload.get(today_key)

    if isinstance(queue, list):
        valid_names = {item["name"] for item in COUPANG_ANGLE_BANK}
        queue = [item for item in queue if item in valid_names]

    if not isinstance(queue, list) or not queue:
        queue = [item["name"] for item in COUPANG_ANGLE_BANK]
        random.shuffle(queue)

    next_name = queue.pop(0)
    payload = {today_key: queue}
    save_coupang_angle_rotation(payload)

    for angle in COUPANG_ANGLE_BANK:
        if angle["name"] == next_name:
            return angle
    return COUPANG_ANGLE_BANK[0]


def normalize_coupang_text(text):
    return str(text or "").strip().lower()


def infer_coupang_product_group(row):
    explicit_group = get_product_field(row, "상품군", "카테고리")
    if explicit_group:
        return explicit_group

    text_blob = " ".join(
        [
            get_product_field(row, "상품명"),
            get_product_field(row, "키워드"),
        ]
    ).lower()

    for group_name, keywords in COUPANG_GROUP_RULES:
        if any(keyword in text_blob for keyword in keywords):
            return group_name
    return "기타생활용품"


def build_coupang_group_writing_guide(group_name, row):
    text_blob = " ".join(
        [
            group_name,
            get_product_field(row, "상품명"),
            get_product_field(row, "키워드"),
            get_product_field(row, "카테고리"),
            get_product_field(row, "상품군"),
        ]
    ).lower()

    if any(keyword in text_blob for keyword in ["이유식분유", "분유", "이유식", "야채큐브", "단호박", "브로콜리", "토핑", "미음", "산양분유", "트루맘", "후디스"]):
        return (
            "- 이유식/분유는 월령과 단계, 원재료, 알레르기 확인, 보관 방식, 소분과 조리 동선을 중심으로 쓴다.\n"
            "- 아이 먹거리이므로 맛이나 성장, 면역, 소화, 건강 개선을 보장하지 말고 보호자 기준의 확인 항목으로만 다룬다.\n"
            "- 처음 먹이는 식재료나 분유 단계 변경은 아이 상태와 전문가 안내를 함께 확인해야 한다는 신중한 톤을 둔다."
        )

    if any(keyword in text_blob for keyword in ["수유용품", "젖병", "젖꼭지", "보틀워머", "분유쉐이커", "모유", "액상분유", "분유 제조기"]):
        return (
            "- 수유용품은 소재, 용량, 젖꼭지 단계, 세척/열탕/소독 가능 여부, 누수와 휴대 동선을 중심으로 쓴다.\n"
            "- 실제 사용 편의를 단정하지 말고 새벽 수유, 외출, 호텔/브런치 동선처럼 엄마가 확인할 장면을 나눠 설명한다.\n"
            "- 세척법, 권장 사용 연령, 구성품, 호환 여부는 상세페이지에서 확인할 항목으로 안내한다."
        )

    if any(keyword in text_blob for keyword in ["유아스킨위생", "물티슈", "선크림", "치약", "칫솔", "샴푸", "바디오일", "소독티슈", "소독", "크림", "저자극"]):
        return (
            "- 유아 위생/스킨케어는 전성분, 사용 연령, 향 여부, 피부에 닿는 빈도, 휴대와 보관, 세척 편의를 중심으로 쓴다.\n"
            "- 저자극, 보습, 소독, 불소, 자외선 차단 같은 표현은 효능을 보장하지 말고 상세페이지 기준 확인 항목으로 다룬다.\n"
            "- 피부가 예민한 아이는 성분표와 사용법을 더 신중히 보고 필요하면 전문가 안내를 확인해야 한다는 톤을 둔다."
        )

    if any(keyword in text_blob for keyword in ["유아의류", "아기내복", "내복", "실내복", "스와들", "양말", "윈드브레이커", "후드", "신생아", "밤부", "메쉬"]):
        return (
            "- 유아 의류는 면 소재와 혼용률, 봉제선, 라벨 위치, 지퍼 마감, 세탁 후 촉감, 계절감을 중심으로 쓴다.\n"
            "- 예쁘다보다 아이 피부와 움직임에 맞는지, 등원복/실내복/외출복 중 어떤 용도인지 먼저 나눈다.\n"
            "- 사이즈, 세탁법, 소재 정보는 상세페이지에서 확인하도록 안내하고 착용감을 직접 경험한 것처럼 쓰지 않는다."
        )

    if any(keyword in text_blob for keyword in ["유아장난감교구", "장난감", "자석", "블럭", "블록", "아기체육관", "교구", "액티비티", "스피너"]):
        return (
            "- 유아 장난감/교구는 권장 연령, 부품 크기, 마감, 세척 가능 여부, 소리와 보관, 아이 집중 시간 기준으로 쓴다.\n"
            "- 발달 효과를 보장하지 말고 아이 성향과 보호자 관찰이 필요한 놀이 선택 기준으로 설명한다.\n"
            "- 자석, 작은 부품, 모서리, 구성품 누락 여부처럼 구매 전 상세페이지에서 확인할 항목을 구체화한다."
        )

    if any(keyword in text_blob for keyword in ["유아식기보관", "이유식 용기", "식기", "용기", "실리콘캡", "보관용기"]):
        return (
            "- 유아 식기/보관용품은 소재, 용량, 밀폐, 냉장/냉동 보관, 열탕/전자레인지/식기세척기 가능 여부, 세척 편의를 중심으로 쓴다.\n"
            "- 안전성과 내구성을 단정하지 말고 아이 식사량, 외출 도시락, 이유식 소분 동선에 따라 기준을 나눈다.\n"
            "- 온도 사용 범위와 세척 조건은 상세페이지에서 확인하도록 안내한다."
        )

    if any(keyword in text_blob for keyword in ["식품", "간식", "음료", "쌀", "김치", "커피", "차", "라면", "소스", "고기", "과일"]):
        return (
            "- 식품은 맛을 단정하지 말고 보관 방식, 용량, 소비 속도, 유통기한 확인, 가족 수 기준을 중심으로 쓴다.\n"
            "- 냉장/냉동/상온 보관 여부와 한 번에 소비하기 쉬운 양인지 같은 생활 판단을 구체적으로 다룬다.\n"
            "- 건강 개선, 체중감량, 치료, 효능 보장처럼 확인되지 않은 표현은 넣지 않는다."
        )

    if any(keyword in text_blob for keyword in ["선풍기", "써큘레이터", "서큘레이터", "에어컨", "냉풍기", "제습기", "가습기", "공기청정기"]):
        return (
            "- 계절가전은 소음, 전기 사용 부담, 필터/물통/청소 관리, 설치 공간, 방 크기를 중심으로 쓴다.\n"
            "- 성능을 보장하지 말고 사용 환경에 따라 체감이 달라질 수 있음을 분명히 둔다.\n"
            "- 계절 수요가 있는 제품은 지금 급한 환경과 천천히 비교해도 되는 환경을 나눠 설명한다."
        )

    if any(keyword in text_blob for keyword in ["모기", "훈증", "살충", "퇴치", "홈매트"]):
        return (
            "- 모기/벌레 관련 제품은 사용 공간, 환기, 아이나 반려동물 여부, 사용 시간대, 교체 주기를 중심으로 쓴다.\n"
            "- 완전 차단, 박멸 같은 과장 표현은 피하고 생활 불편을 줄이는 확인 기준으로 풀어낸다.\n"
            "- 성분이나 안전성은 단정하지 말고 상세페이지와 사용 설명 확인이 필요하다고 안내한다."
        )

    if any(keyword in text_blob for keyword in ["스마트폰", "아이폰", "자급제"]):
        return (
            "- 스마트폰은 저장공간, 색상, 자급제 개통 방식, 통신요금/약정 여부, 보증과 구성품 확인을 중심으로 쓴다.\n"
            "- 성능이나 가격 우위를 단정하지 말고 사진/영상 저장량, 교체 주기, 통신사 이용 방식에 따라 기준을 나눈다.\n"
            "- 색상과 용량은 재고와 가격이 달라질 수 있으므로 상세페이지 확인 흐름으로 연결한다."
        )

    if any(keyword in text_blob for keyword in ["이어폰", "에어팟", "이어팟", "노이즈", "usb-c", "블루투스"]):
        return (
            "- 이어폰은 연결 방식, 착용감, 노이즈캔슬링 필요 여부, 통화 사용, 충전/유선 사용 환경을 중심으로 쓴다.\n"
            "- 음질이나 차음 성능을 단정하지 말고 출퇴근, 사무실, 온라인 수업처럼 쓰는 장소별 기준을 나눈다.\n"
            "- 커넥터, 모델 구성, 호환 기기는 상세페이지에서 확인해야 할 항목으로 안내한다."
        )

    if any(keyword in text_blob for keyword in ["태블릿", "아이패드", "애플펜슬", "매직 키보드", "키보드", "pencil"]):
        return (
            "- 태블릿/액세서리는 호환 모델, 저장공간, 연결 방식, 필기/문서 작업 목적, 휴대성을 중심으로 쓴다.\n"
            "- 공부, 업무, 영상 시청, 드로잉처럼 사용 목적을 나눠 필요한 구성을 먼저 확인하게 한다.\n"
            "- 세대 호환, 색상, 용량, 구성품은 상세페이지에서 확인해야 한다고 안내한다."
        )

    if any(keyword in text_blob for keyword in ["스마트워치", "애플워치", "watch", "gps", "밴드"]):
        return (
            "- 스마트워치는 케이스 크기, GPS/셀룰러 여부, 밴드 사이즈, 운동 기록, 알림 사용 환경을 중심으로 쓴다.\n"
            "- 손목 크기와 착용 시간에 따라 체감이 달라질 수 있음을 설명하고 무조건 추천하지 않는다.\n"
            "- 색상, 밴드 구성, 모델별 기능 차이는 상세페이지에서 확인하도록 연결한다."
        )

    if any(keyword in text_blob for keyword in ["차량", "자동차", "테슬라", "모델 y", "선쉐이드", "주니퍼"]):
        return (
            "- 차량용품은 차종 호환, 설치 방식, 조작 방식, 전원/작동 조건, 시야와 안전 영향을 중심으로 쓴다.\n"
            "- 편리함을 단정하기보다 내 차종과 실내 구조에 맞는지 먼저 확인하는 흐름으로 쓴다.\n"
            "- 설치 난이도, 구성품, A/S 조건은 상세페이지에서 확인할 항목으로 안내한다."
        )

    if any(keyword in text_blob for keyword in ["골프", "장갑", "풋조이", "양피", "카브레타"]):
        return (
            "- 골프용품은 사이즈, 소재, 착용감, 그립감, 사용 빈도, 연습장/필드 사용 환경을 중심으로 쓴다.\n"
            "- 그립감이나 내구성을 과장하지 말고 손 크기와 사용 빈도에 따라 확인할 기준을 나눈다.\n"
            "- 사이즈표, 소재, 관리 방법은 상세페이지에서 확인하도록 안내한다."
        )

    if any(keyword in text_blob for keyword in ["드라이기", "드라이어", "jmw", "bldc", "항공모터"]):
        return (
            "- 헤어드라이어는 바람 세기, 무게, 소음, 소비전력, 손목 부담, 보관 위치를 중심으로 쓴다.\n"
            "- 건조 속도나 모발 손상 개선을 단정하지 말고 머리 길이와 사용 시간대에 따라 기준을 나눈다.\n"
            "- 구성품, 무게, 소비전력, 소음 관련 정보는 상세페이지 확인 항목으로 둔다."
        )

    if any(keyword in text_blob for keyword in ["스팀다리미", "다리미", "스팀", "보만"]):
        return (
            "- 스팀다리미는 예열 시간, 물통 관리, 옷감 호환, 무게, 보관성, 안전 사용 조건을 중심으로 쓴다.\n"
            "- 모든 주름이 해결된다고 단정하지 말고 셔츠, 니트, 외투처럼 소재별 확인 기준을 나눈다.\n"
            "- 물통 용량, 사용 시간, 브러쉬 구성은 상세페이지에서 확인하도록 안내한다."
        )

    if any(keyword in text_blob for keyword in ["청소기", "먼지", "물걸레", "브러시", "흡입"]):
        return (
            "- 청소 관련 제품은 바닥 재질, 먼지 종류, 보관 위치, 필터 관리, 소음, 무게를 중심으로 쓴다.\n"
            "- 청소 성능을 임의로 단정하지 말고 집 구조와 청소 빈도에 따라 확인할 기준을 나눈다.\n"
            "- 원룸, 가족 거실, 반려동물 있는 집처럼 먼지 상황이 달라지는 환경을 반영한다."
        )

    if any(keyword in text_blob for keyword in ["건조대", "빨래", "세탁", "건조"]):
        return (
            "- 세탁/건조 관련 제품은 설치 공간, 접었을 때 크기, 가족 빨래량, 이동 편의성, 습한 날 사용성을 중심으로 쓴다.\n"
            "- 튼튼함을 단정하지 말고 하중, 소재, 바닥 공간처럼 상세페이지에서 확인할 항목을 구체화한다.\n"
            "- 원룸, 베란다, 욕실 앞처럼 실제 배치 장면을 떠올릴 수 있게 문장을 만든다."
        )

    if any(keyword in text_blob for keyword in ["포트", "주전자", "전기포트", "인덕션", "전자레인지", "오븐", "식기세척기", "주방패키지", "디오스"]):
        return (
            "- 주방가전은 설치 공간, 전기 조건, 배수/급수 여부, 세척 편의, 가족 사용량, 주방 동선을 중심으로 쓴다.\n"
            "- 건조 성능이나 조리 성능을 임의로 단정하지 말고 설치 조건과 상세 스펙에서 확인할 부분으로 안내한다.\n"
            "- 1인 가구, 신혼집, 가족용처럼 사용량과 주방 구조가 다른 상황을 나눠 설명한다."
        )

    if any(keyword in text_blob for keyword in ["소모품", "휴지", "세제", "필터", "리필", "봉투", "수세미", "물티슈", "샴푸", "세정"]):
        return (
            "- 소모품은 개수, 리필 가능 여부, 보관 부피, 교체 주기, 사용 장소별 소비량을 중심으로 쓴다.\n"
            "- 싸다/오래 간다처럼 단정하지 말고 집의 소비 속도와 보관 공간에 맞는지 따지게 한다.\n"
            "- 대량 구성은 장점과 함께 보관 부담도 같이 다룬다."
        )

    return (
        "- 생활용품은 사용 장소, 보관 공간, 구성, 크기, 관리 편의성, 자주 쓰는 빈도를 중심으로 쓴다.\n"
        "- 상품군이 애매할수록 일반 칭찬보다 어떤 상황에서 확인할 만한지 구체적인 장면을 먼저 제시한다.\n"
        "- 가격보다 내 생활 방식과 맞는지 따지는 흐름을 유지한다."
    )


def score_coupang_candidate(row, recent_history):
    group_name = infer_coupang_product_group(row)
    keyword = get_product_field(row, "키워드")
    category = get_product_field(row, "카테고리", default=group_name)

    recent_groups = [item.get("group") for item in recent_history[-3:]]
    recent_keywords = [item.get("keyword") for item in recent_history[-2:]]
    recent_categories = [item.get("category") for item in recent_history[-3:]]

    score = 0
    if group_name not in recent_groups:
        score += 4
    if keyword not in recent_keywords:
        score += 3
    if category not in recent_categories:
        score += 1
    return score, group_name, category, keyword


def record_coupang_selection_history(row):
    history = load_coupang_selection_history()
    history.append(
        {
            "selected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": get_product_field(row, "상품명"),
            "keyword": get_product_field(row, "키워드"),
            "group": infer_coupang_product_group(row),
            "category": get_product_field(row, "카테고리", default=infer_coupang_product_group(row)),
        }
    )
    save_coupang_selection_history(history)


def get_season(now):
    month = now.month
    if month in (3, 4):
        return "봄"
    if month in (5, 6, 7, 8):
        return "여름"
    if month in (9, 10, 11):
        return "가을"
    return "겨울"


def choose_weather_hint(season):
    candidates = {
        "봄": ["맑음", "비", "바람", "흐림"],
        "여름": ["더위", "비", "맑음", "흐림"],
        "가을": ["맑음", "바람", "흐림", "추위"],
        "겨울": ["추위", "맑음", "바람", "흐림"],
    }
    weather_key = random.choice(candidates.get(season, ["맑음"]))
    return weather_key, random.choice(WEATHER_MOOD_BANK[weather_key])


def format_daily_prompt_items(items):
    return "\n".join([f"- {item}" for item in items if str(item).strip()])


def build_daily_topic_context():
    now = datetime.now()
    season = get_season(now)
    weekday_name = KOREAN_WEEKDAY_NAMES[now.weekday()]
    is_weekend = now.weekday() >= 5
    day_type = "주말" if is_weekend else "평일"
    weather_key, weather_mood = choose_weather_hint(season)
    content_category = get_next_daily_category(now)
    seasonal_topic = random.choice(SEASONAL_TOPIC_BANK[season])
    trend_keyword = random.choice(LIFESTYLE_TREND_BANK)
    daily_scene = random.choice(DAILY_SCENE_BANK)
    photo_style = random.choice(PHOTO_STYLE_BANK)
    health_topic = random.choice(HEALTH_TOPIC_BANK)
    economy_topic = random.choice(ECONOMY_TOPIC_BANK)
    news_topic = random.choice(NEWS_TOPIC_BANK)
    combo_topic = random.choice(COMBO_TOPIC_BANK)
    emotion_keyword = random.choice(["은근한 뿌듯함", "조금의 귀찮음", "소소한 만족감", "괜한 들뜸", "잔잔한 안정감"])
    writing_angle = random.choice([
        "생활 장면으로 시작해 원인과 기준으로 확장하는 글",
        "실수담을 짧게 넣고 체크리스트로 정리하는 글",
        "검색자가 바로 따라 할 수 있는 순서형 글",
        "집 구조별 판단 기준을 중심으로 쓰는 글",
    ])
    intent_candidates = DAILY_SEARCH_INTENT_BANK.get(content_category) or DAILY_SEARCH_INTENT_BANK["청담키즈라이프"]
    daily_intent = random.choice(intent_candidates)
    return {
        "now_label": f"{now.month}월 {now.day}일 {weekday_name}요일",
        "season": season,
        "day_type": day_type,
        "content_category": content_category,
        "weather_key": weather_key,
        "weather_mood": weather_mood,
        "seasonal_topic": seasonal_topic,
        "health_topic": health_topic,
        "economy_topic": economy_topic,
        "news_topic": news_topic,
        "combo_topic": combo_topic,
        "focus_topic": daily_intent["search_phrase"],
        "search_phrase": daily_intent["search_phrase"],
        "reader_problem": daily_intent["reader_problem"],
        "reader_promise": daily_intent["reader_promise"],
        "practical_points": daily_intent["practical_points"],
        "mistakes_to_avoid": daily_intent["mistakes_to_avoid"],
        "faq_questions": daily_intent["faq_questions"],
        "related_keywords": daily_intent["related_keywords"],
        "image_scene": daily_intent["image_scene"],
        "trend_keyword": trend_keyword,
        "daily_scene": daily_scene,
        "photo_style": photo_style,
        "emotion_keyword": emotion_keyword,
        "writing_angle": writing_angle,
    }


def build_daily_post_prompt(daily_context):
    practical_points = format_daily_prompt_items(daily_context.get("practical_points", []))
    mistakes_to_avoid = format_daily_prompt_items(daily_context.get("mistakes_to_avoid", []))
    faq_questions = format_daily_prompt_items(daily_context.get("faq_questions", []))
    related_keywords = ", ".join(daily_context.get("related_keywords", []))
    daily_neighbor_cta = random.choice([
        "청담에서 아이 키우며 고르는 기준을 계속 정리해둘 예정이라 필요할 때 찾아보기 편하게 이웃 추가해두셔도 좋습니다.",
        "아이와 함께 가는 공간, 먹는 것, 쓰는 것을 세세하게 보는 글을 이어갈 예정이라 관심 있는 분들은 이웃으로 남겨두셔도 괜찮습니다.",
        "미식과 문화생활도 아이 동선까지 함께 보는 기준으로 계속 기록할 예정이라 나중에 다시 찾기 편하실 거예요.",
        "성분, 소재, 동선처럼 엄마 입장에서 먼저 확인할 기준을 꾸준히 남겨둘 테니 필요할 때 이웃으로 찾아오셔도 좋습니다.",
        "비슷한 기준으로 고르는 분들이라면 다음 글도 이어서 보기 편하게 이웃으로 저장해두셔도 좋습니다.",
    ])

    return f"""
너는 네이버 블로그에서 청담에 사는 자녀 둔 어머니의 프리미엄 라이프스타일을 다루는 블로거다.

이 글은 단순한 일상글이 아니다.
아래에서 확정한 검색어와 독자 고민을 기준으로 네이버 블로그에 올릴 수 있는 깊이 있는 정보성 본문을 작성해야 한다.
주제를 새로 고르거나 다른 소재로 바꾸지 마라.

최종 글은 광고글처럼 보이면 안 된다.
또 AI가 정리한 설명문처럼 보여도 안 된다.
청담에서 아이를 키우며 미식, 문화생활, 교육 체험, 소재와 성분을 예민하게 고르는 엄마가 직접 기준을 정리한 듯한 자연스러운 글이어야 한다.

[블로그 컨셉]
{BLOG_PERSONA_CONCEPT}

- 말투는 실제 청담 사는 애엄마처럼 자연스럽게 쓴다.
- 과시만 하는 글이 아니라, 왜 이 공간과 경험을 고르는지 기준이 또렷해야 한다.
- 아이와 함께하는 상황에서는 좌석 간격, 동선, 소음, 성분, 소재, 위생, 관리 편의성까지 세세하게 따진다.
- 상위권 라이프스타일의 미식, 문화생활, 교육 체험, 살림 취향을 다루되 허세보다 취향과 기준이 먼저 보여야 한다.

[이번 글 컨텍스트]
- 날짜 감각: {daily_context['now_label']}
- 콘텐츠 카테고리: {daily_context['content_category']}
- 계절: {daily_context['season']}
- 요일 분위기: {daily_context['day_type']}
- 날씨 키워드: {daily_context['weather_key']}
- 날씨에서 출발한 기분: {daily_context['weather_mood']}
- 확정 핵심 검색어: {daily_context['search_phrase']}
- 독자 고민: {daily_context['reader_problem']}
- 글에서 해결할 약속: {daily_context['reader_promise']}
- 관련 키워드: {related_keywords}
- 생활형 보조 주제: {daily_context['seasonal_topic']}
- 요즘 생활 트렌드: {daily_context['trend_keyword']}
- 실제 장면: {daily_context['daily_scene']}
- 감정 톤: {daily_context['emotion_keyword']}
- 글 전개 방식: {daily_context['writing_angle']}

[반드시 담을 실천 포인트]
{practical_points}

[피해야 할 실수]
{mistakes_to_avoid}

[본문 안에서 자연스럽게 답할 질문]
{faq_questions}

[skssj2629 블로그 방향]
이 블로그는 청담 사는 자녀 둔 어머니가 미식, 문화생활, 교육 체험, 프리미엄 살림, 아이 용품 기준을 세세하게 정리하는 라이프스타일 블로그다.

아래 방향과 맞는 글만 작성한다.
- 청담, 압구정, 한남, 성수, 도산공원 주변의 미식과 브런치
- 호텔 애프터눈티, 파인다이닝, 가족 외식 예약 기준
- 아이와 함께 보는 전시, 클래식 공연, 갤러리, 키즈 클래스
- 성분, 면 소재, 봉제, 마감, 세척, 보관을 따지는 육아용품 기준
- 아이 등원복, 실내복, 선크림, 물티슈, 식기, 장난감, 교구를 고를 때 보는 기준
- 엄마의 취향이 드러나는 살림, 테이블 세팅, 주방용품, 선물 고르는 기준

대중적인 맛집 후기, 단순 방문 기록, 감정 일기, MBTI 잡담, 경제 뉴스 감상문으로 가지 마라.

[A급 주제 선정 기준]
이미 확정된 핵심 검색어가 A급 청담 엄마 라이프스타일 글처럼 보이도록 본문을 구성한다.
최종 출력에는 선정 과정, 점수표, 후보 목록을 쓰지 마라.
확정 핵심 검색어를 다른 주제로 바꾸지 말고 바로 본문을 작성한다.

A급 주제는 아래 8가지 조건 중 최소 6개 이상을 만족해야 한다.

1. 검색 문장으로 자연스럽다
- 사람이 네이버에 그대로 검색할 법한 문장이어야 한다.
- 예: 아이와 전시회 갈 때 확인할 기준
- 예: 청담동 가족 브런치 고를 때 보는 기준
- 예: 아기 옷 소재 고르는 기준
- 나쁜 예: 오늘의 소소한 일상
- 나쁜 예: 집에서 느낀 소소한 생각

2. 선택 기준이 분명하다
- 좌석, 동선, 소음, 성분, 면 소재, 마감, 세척, 보관, 아이 컨디션처럼 독자가 바로 공감할 기준이 있어야 한다.
- 추상적인 기분이나 감상만 있는 주제는 제외한다.

3. 계절성과 생활 장면이 있다
- 봄·여름이면 아이 외출복, 선크림, 호텔 티타임, 전시, 야외 동선, 냉방되는 식사 공간을 우선한다.
- 가을·겨울이면 공연, 전시, 실내 클래스, 보습, 소재, 니트와 실내복, 따뜻한 미식 공간을 우선한다.

4. 예약 전 또는 구매 전 바로 확인할 수 있다
- 독자가 글을 읽고 바로 확인할 수 있는 기준이 있어야 한다.
- 예: 예약 시간, 좌석 간격, 아이 메뉴, 주차 동선, 성분표, 소재, 세탁법, 사용 연령, 수업 인원

5. 청담 엄마의 안목으로 자연스럽게 연결된다
- 직접 상품을 광고하지 않아도 프리미엄 미식, 문화생활, 아이 교육, 성분과 소재를 따지는 육아 소비 신호가 쌓여야 한다.
- 단, 본문은 자랑글이 아니라 기준을 정리하는 정보글이어야 한다.

6. 사진 없이도 글만으로 정보 가치가 있다
- 장소나 제품을 직접 과장하지 않고도 예약 전 체크 기준, 아이 동반 기준, 소재와 성분 기준만으로 도움이 되어야 한다.

7. 너무 좁은 제품명 키워드가 아니다
- 특정 상품명이나 모델명 중심으로 가지 않는다.
- 제품 비교가 필요한 경우에도 생활문제를 먼저 잡고, 뒤에서 선택 기준으로만 풀어라.
- 예: 아기 옷 소재 고르는 기준은 가능
- 나쁜 예: 특정 브랜드 유아 내복 모델명 추천

8. 조회수와 블로그 주제 신뢰도를 동시에 노릴 수 있다
- 단순 조회수만 위한 자극적인 맛집, 데이트, 이슈성 잡담은 제외한다.
- skssj2629가 예민하고 기준이 분명한 청담 엄마 라이프스타일 블로그로 보이는 데 도움이 되는 주제를 고른다.

[A급 주제 우선순위]
아래 목록은 주제 감각을 맞추기 위한 참고용이다.
이미 확정된 핵심 검색어가 있으면 그 검색어를 우선하고, 아래 목록으로 주제를 바꾸지 마라.

오늘 컨텍스트가 미식, 브런치, 호텔, 레스토랑과 관련 있으면 아래 순서로 고른다.

1순위:
- 청담동 가족 브런치 고를 때 보는 기준
- 아이와 파인다이닝 갈 때 확인할 것
- 호텔 애프터눈티 아이와 갈 때 기준
- 아이 동반 레스토랑 예약 전 체크
- 가족 외식에서 좌석과 동선을 보는 기준

2순위:
- 전시회 아이와 갈 때 확인할 기준
- 아이와 클래식 공연 갈 때 체크할 것
- 키즈 클래스 고를 때 보는 기준
- 문화생활 예약 전 아이 컨디션 체크
- 갤러리 나들이 동선 정리

3순위:
- 아기 옷 소재 고르는 기준
- 아기용품 성분 확인하는 방법
- 프리미엄 주방용품 고를 때 기준
- 아이 선크림 성분 볼 때 체크할 것
- 유아 교구 고를 때 안전성과 마감 기준

[주제 선택 금지 조건]
아래 조건에 해당하는 방향으로 본문을 흐리지 마라.
- 검색자가 무엇을 얻을지 불분명한 주제
- 일기처럼 감정만 남는 주제
- 대중적인 맛집 순위 나열, 데이트 코스 추천, 여행 후기처럼 블로그 컨셉과 맞지 않는 주제
- 실제 방문 사진이 없으면 아무 정보도 남지 않는 감상형 주제
- 특정 상품을 사라고 해야만 완성되는 주제
- 확인되지 않은 수치를 많이 만들어야 하는 주제
- 의료, 법률, 투자처럼 조심해야 하는 고위험 조언 주제
- 너무 넓어서 글이 흐려지는 주제
  예: 청담 라이프 전체
  예: 육아템 잘 고르는 법 전체

[좋은 주제 변환 예시]
너무 넓은 주제는 구체적인 선택 기준으로 바꿔라.

- 청담 브런치
   아이와 청담 브런치 갈 때 좌석과 메뉴를 보는 기준

- 문화생활
   아이와 전시회 갈 때 관람 동선과 대기 시간을 보는 기준

- 육아용품
   아기용품 성분표와 사용 연령을 확인하는 기준

- 아이 옷
   면 소재, 봉제, 세탁 후 촉감을 보는 기준

[본문 품질 기준]
본문은 아래 조건을 반드시 만족해야 한다.

1. 첫 문단은 검색 의도와 생활 장면을 함께 잡는다
- 첫 문장에는 확정 핵심 검색어를 자연스럽게 넣고, 독자가 겪는 문제 상황을 바로 요약한다.
- 두 번째 문장에는 이 글에서 확인할 기준 2~3가지를 짧게 예고한다.
- 세 번째 문장부터 생활 장면으로 자연스럽게 이어간다.
- 예: 아이와 청담 브런치를 고를 때는 메뉴보다 좌석 간격, 대기 동선, 아이 컨디션을 먼저 보게 됩니다.
- 예: 아기 옷 소재를 볼 때는 디자인보다 피부에 닿는 면, 봉제선, 세탁 후 촉감이 더 오래 신경 쓰입니다.
- 예: 전시나 공연은 유명한 곳보다 아이가 지치지 않는 시간대와 이동 동선이 먼저 맞아야 편합니다.
- 단, 오늘은 ~에 대해 알아보겠습니다로 시작하지 마라.

2. 3문단 안에 정보글로 전환한다
- 감정 묘사만 길게 끌지 마라.
- 청담에서의 생활 장면은 짧게 쓰고, 곧바로 선택 기준과 확인 순서로 넘어간다.

3. 선택 기준을 2단계 이상으로 나눈다
- 단순히 분위기가 좋다, 유명하다, 좋아 보인다로 끝내지 마라.
- 예: 아이 컨디션 + 예약 시간 + 좌석 간격 + 화장실 동선
- 예: 면 소재 + 봉제선 + 세탁 후 촉감 + 계절감
- 예: 성분표 + 사용 연령 + 향 여부 + 보관과 휴대 편의성

4. 독자가 바로 확인할 체크포인트를 제공한다
- 추상적인 관리하세요 금지
- 구체적으로 써라.
- 예: 유모차를 두고도 옆 테이블과 간격이 충분한지
- 예: 아이 메뉴나 덜 자극적인 선택지가 있는지
- 예: 전시 동선 중 아이가 쉬어갈 수 있는 구간이 있는지
- 예: 라벨, 지퍼, 봉제선이 피부에 닿는 위치인지
- 예: 전성분, 사용 연령, 세척 방법을 상세페이지에서 확인할 수 있는지

5. 상황별 기준을 넣는다
- 아이 동반 브런치
- 호텔 애프터눈티
- 전시와 클래식 공연
- 키즈 클래스
- 등원 전후 외출
- 피부가 예민한 아이
- 선물용 유아용품
- 주말 가족 외식
이 중 주제와 맞는 2~3개를 골라 설명한다.

6. 특정 장소나 상품을 강요하지 않는다
- 유명한 곳이라서 좋다, 비싸서 좋다처럼 쓰지 마라.
- 방문 후기처럼 꾸미지 말고, 예약 전 또는 구매 전 확인할 기준을 먼저 정리한다.

7. 확인되지 않은 수치를 만들지 않는다
- 가격, 예약 가능 시간, 좌석 수, 성분 비율, 소재 혼용률, 사용 연령, 수업 인원, 공연 시간 같은 수치를 지어내지 마라.
- 필요하면 장소나 제품마다 다르므로 상세정보와 예약 페이지에서 확인하는 편이 안전하다라고 쓴다.

8. 마지막은 광고가 아니라 정리로 끝낸다
- 구매하세요, 추천합니다, 링크 확인하세요 금지
- 먼저 볼 기준을 다시 짧게 정리한다.

[사람이 쓴 듯한 문장 무드]
아래 문장감을 참고하되 그대로 복사하지 말고 자연스럽게 변형하라.

- 아이와 함께 가면 작은 불편도 생각보다 크게 남습니다.
- 예쁜 공간이어도 아이가 앉아 있기 어려우면 결국 다시 보게 됩니다.
- 가격보다 먼저 보는 건 우리 아이 피부와 생활 리듬에 맞는지입니다.
- 소재나 성분은 한 번 대충 넘기면 나중에 다시 확인하게 되더라고요.
- 같은 브런치라도 아이와 가는 날에는 좌석과 동선 기준이 완전히 달라집니다.
- 유명한 곳보다 우리 가족에게 편한 조건인지가 더 오래 남습니다.
- 청담에서 고른다고 해서 무조건 화려한 것만 보는 건 아닙니다.
- 결국 엄마 입장에서는 예쁜지보다 안전하고 오래 편한지가 먼저입니다.

[문장 금지 규칙]
아래 표현은 쓰지 마라.
- 본 글에서는
- 알아보겠습니다
- 살펴보겠습니다
- 도움이 되시길 바랍니다
- 완벽 정리
- 꿀팁 대방출
- 무조건
- 역대급
- 인생템
- 필수템
- 강력 추천
- 내돈내산
- 직접 써보니
- 제가 써봤는데
- 협찬 아님
- 상위노출
- SEO
- 검색 알고리즘
- 여러 블로그를 분석해보니

[본문 구조]
아래 순서로 작성한다.

1. 검색어와 문제 상황으로 시작
- 첫 문장에는 선택한 핵심 키워드를 자연스럽게 1회 포함한다.
- 첫 문장은 독자가 검색한 이유가 바로 보이도록 문제 상황을 요약한다.
- 두 번째 문장은 이 글에서 확인할 기준 2~3가지를 짧게 말한다.
- 세 번째 문장부터 날짜, 계절, 날씨, 실제 장면 중 2개 이상을 자연스럽게 반영한다.
- 시작은 짧고 구체적으로 쓰되, 검색어만 억지로 반복하지 않는다.

2. 기준이 갈리는 이유
- 선택 기준이 달라지는 이유를 2~4개로 나눠 설명한다.
- 아이 컨디션, 예약 시간, 좌석 간격, 이동 동선, 소음, 성분, 면 소재, 봉제, 세탁, 보관, 사용 연령 중 주제와 맞는 요소를 반영한다.
- 확인되지 않은 수치는 만들지 않는다.

[구분선]

3. 먼저 확인할 기준
아래 마커를 정확히 사용한다.

[목록주제]먼저 확인하면 좋은 기준
- 구체적인 기준 1개
- 구체적인 기준 1개
- 구체적인 기준 1개
- 필요하면 구체적인 기준 1개 추가
[목록끝]

4. 상황별로 다르게 봐야 할 점
- 아이 동반 브런치, 호텔 티타임, 전시 관람, 키즈 클래스, 등원 전후 외출, 선물용 유아용품, 피부가 예민한 아이 중 주제와 맞는 2~3개를 골라 설명한다.
- 무조건 하나의 정답처럼 말하지 않는다.
- 아이 성향과 가족 생활 패턴에 따라 달라진다는 점을 자연스럽게 넣는다.

[구분선]

5. 놓치기 쉬운 부분
- 검색자가 자주 놓치는 부분을 2~3개 정리한다.
- 예: 유모차 동선, 화장실 위치, 대기 시간, 아이 메뉴, 라벨 위치, 봉제선, 성분표, 사용 연령, 세척 편의성
- 특정 장소나 제품을 추천하지 말고 체크 기준으로만 설명한다.

6. 마지막 정리
- 오늘의 생활 장면으로 살짝 돌아오며 정리한다.
- 광고성 문장 없이 끝낸다.
- 제품 구매를 직접 유도하지 않는다.
- 아래 이웃 추가 문장을 마지막 정리 안에서 1회만 자연스럽게 넣는다.
- 이웃 추가 문장을 여러 번 반복하거나 명령형으로 바꾸지 않는다.
- 이웃 추가 문장: {daily_neighbor_cta}
- 다음에 관련 공간이나 제품을 볼 때 어떤 기준부터 보면 좋은지만 말한다.

[인용구 규칙]
글 중간에 아래 형식의 인용구를 1~2개 넣는다.
[인용구]문장내용[/인용구]

인용구는 광고처럼 쓰지 말고, 글의 핵심 판단 기준을 담아라.
인용구 안의 문장내용은 반드시 20자 이상 60자 이하의 완성된 한국어 문장이어야 한다.
절대 [인용구][/인용구], [인용구] [/인용구], [인용구]문장내용[/인용구]처럼 비어 있거나 예시 문구가 그대로 남은 형태를 출력하지 마라.
인용구에 넣을 문장이 확실하지 않으면 인용구 마커 자체를 만들지 말고, 빈 인용구는 절대 만들지 마라.
예:
[인용구]아이와 함께라면 예쁜 것보다 먼저 편한 동선을 봅니다[/인용구]
[인용구]성분과 소재는 엄마 입장에서 가장 오래 남는 기준입니다[/인용구]

[SEO 키워드 규칙]
- 선택한 핵심 키워드는 본문에 4~6회만 자연스럽게 포함한다.
- 관련 키워드는 자연스럽게 5~8개 정도만 섞는다.
- 가능한 관련 키워드:
  청담동 브런치, 아이동반식사, 호텔 애프터눈티, 파인다이닝, 아이와 전시회, 클래식 공연, 키즈 클래스, 청담 엄마, 아기 옷 소재, 유아용품 성분, 면 소재, 봉제, 세탁, 프리미엄 육아, 문화생활, 가족외식, 예약 기준, 좌석 간격, 아이 메뉴, 주차 동선, 사용 연령, 관리 편의성
- 모든 키워드를 억지로 넣지 마라.
- 같은 키워드를 반복해서 도배하지 마라.
- 제목은 출력하지 않는다.

[해시태그 생성 규칙]
본문 맨 마지막에는 반드시 아래 형식으로 해시태그를 붙인다.

[해시태그대기]
#태그 #태그 #태그 #태그 #태그 #태그 #태그 #태그 #태그 #태그

해시태그 조건:
- 정확히 10개
- 모두 '#태그' 형식
- 한 줄에 공백으로 구분
- 영어 태그 금지
- 설명 금지
- 본문 주제와 직접 관련된 태그만 사용
- 청담라이프, 청담엄마, 아이동반식사, 프리미엄미식, 문화생활, 키즈클래스, 아기용품, 성분체크, 소재체크, 육아일상 중 문맥에 맞는 태그를 고른다.
- 너무 긴 태그 금지
- 광고 느낌 강한 태그 금지
- 쇼핑커넥트, 광고, 구매링크 같은 태그는 일상글에는 쓰지 마라.

[출력 규칙]
- 제목 없이 본문만 출력
- 2600자 이상 3200자 이하를 목표로 작성
- 글자수를 늘리기 위해 같은 기준이나 표현을 반복하지 말고, 원인, 확인 기준, 상황별 차이, 실수 방지를 구체화한다
- 자연스러운 한국어만 사용
- 영어 문장, 영어 제목 후보, 작업 메모 출력 금지
- 마크다운 서식 금지
- [구분선]은 정확히 2~3회
- [인용구]문장[/인용구] 형식 1~2회
- 인용구 내부 문장은 반드시 20자 이상이어야 하며, 빈 인용구 출력 금지
- [목록주제]와 [목록끝] 마커는 철자 그대로 유지
- 본문 마지막에 [해시태그대기]와 해시태그 10개를 반드시 출력한다
- 문단 사이에는 빈 줄을 충분히 넣는다

[절대 금지]
- 광고 고지문 출력 금지
- 쇼핑커넥트 링크 출력 금지
- 특정 상품 직접 구매 후기처럼 작성 금지
- 내돈내산 표현 금지
- 직접 사용했다고 단정 금지
- 확인되지 않은 수치 생성 금지
- 상위노출, 검색 알고리즘, SEO라는 단어를 본문에 직접 쓰기 금지
- 여러 블로그를 분석했다고 직접 말하기 금지
- AI가 쓴 것처럼 보이는 정리문 금지
"""


def build_daily_image_prompt(daily_context):
    return (
        f"{daily_context['photo_style']}, {daily_context['season']} 분위기, "
        f"{daily_context['weather_key']} 느낌, {daily_context['image_scene']}, "
        f"{daily_context['search_phrase']}와 관련된 청담 엄마 라이프스타일 블로그 사진, "
        "30대 한국인 어머니와 어린 자녀가 자연스럽게 등장하고 세련되지만 과장되지 않은 표정과 생활감이 보이는 장면, "
        "제품 로고나 글자가 보이지 않는 프리미엄 미식, 문화생활, 육아용품 선택 장면"
    )


def load_csv_rows(csv_path):
    """CSV를 읽고 rows, fieldnames, encoding을 반환한다."""
    last_error = None
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                fieldnames = reader.fieldnames or []
                return rows, fieldnames, encoding
        except UnicodeDecodeError as e:
            last_error = e
            continue
    raise RuntimeError(f"CSV 파일 인코딩을 읽지 못했습니다: {csv_path}") from last_error


def is_used_value(value):
    return str(value or "").strip().lower() in {"true", "1", "y", "yes"}


def get_coupang_product_key(row):
    product_link = str(row.get("쇼핑커넥트링크") or row.get("쿠팡링크") or "").strip()
    if product_link:
        return product_link
    product_name = str(row.get("상품명") or "").strip()
    keyword = str(row.get("키워드") or "").strip()
    return f"{product_name}::{keyword}"


def migrate_used_rows_to_state(rows):
    used_products = load_coupang_used_products()
    changed = False
    for row in rows:
        if not is_used_value(row.get("used")):
            continue
        product_key = get_coupang_product_key(row)
        if product_key in used_products:
            continue
        used_products[product_key] = {
            "product_name": str(row.get("상품명") or "").strip(),
            "keyword": str(row.get("키워드") or "").strip(),
            "product_link": str(row.get("쇼핑커넥트링크") or row.get("쿠팡링크") or "").strip(),
            "used_at": str(row.get("used_at") or "").strip(),
            "post_title": str(row.get("post_title") or "").strip(),
        }
        changed = True
    if changed:
        save_coupang_used_products(used_products)
    return used_products


def is_coupang_product_already_used(row, used_products):
    return get_coupang_product_key(row) in used_products


def is_coupang_api_enabled():
    flag = os.getenv("COUPANG_API_ENABLED", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    return bool(os.getenv("COUPANG_ACCESS_KEY", "").strip() and os.getenv("COUPANG_SECRET_KEY", "").strip())


def generate_coupang_hmac(method, path_with_query, secret_key, access_key):
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


def call_coupang_api(method, path_with_query, payload=None):
    access_key = os.getenv("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.getenv("COUPANG_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError("COUPANG_ACCESS_KEY 또는 COUPANG_SECRET_KEY가 없어 쿠팡 API를 호출할 수 없습니다.")

    domain = os.getenv("COUPANG_API_DOMAIN", COUPANG_API_DOMAIN).strip() or COUPANG_API_DOMAIN
    timeout = int(os.getenv("COUPANG_API_TIMEOUT_SEC", "15") or "15")
    authorization = generate_coupang_hmac(method, path_with_query, secret_key, access_key)
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json;charset=UTF-8",
    }
    response = requests.request(
        method=method,
        url=f"{domain}{path_with_query}",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if str(data.get("rCode", "0")) != "0":
        raise RuntimeError(f"쿠팡 API 오류: {data.get('rMessage') or data}")
    return data

def generate_coupang_deeplink(original_url):
    original_url = (original_url or "").strip()
    if not original_url:
        return ""

    payload = {"coupangUrls": [original_url]}
    sub_id = os.getenv("COUPANG_SUB_ID", "").strip()
    if sub_id:
        payload["subId"] = sub_id

    try:
        result = call_coupang_api(
            "POST",
            f"{COUPANG_API_BASE_PATH}/deeplink",
            payload,
        )
        data = result.get("data") or []
        if data:
            return str(data[0].get("shortenUrl") or data[0].get("landingUrl") or original_url).strip()
    except Exception as e:
        print(f"   >> [안내] 쿠팡 딥링크 변환 실패: {e}")
    return original_url


def select_unused_coupang_product(csv_path):
    """사용하지 않은 네이버 쇼핑커넥트 상품 한 개를 랜덤 선택한다."""
    rows, fieldnames, _encoding = load_csv_rows(csv_path)
    required_fields = ["상품명", "키워드", "쇼핑커넥트링크"]
    missing_fields = [field for field in required_fields if field not in fieldnames]
    if missing_fields:
        raise RuntimeError(f"CSV 필수 컬럼이 없습니다: {', '.join(missing_fields)}")

    used_products = migrate_used_rows_to_state(rows)
    available_indexes = [
        idx for idx, row in enumerate(rows)
        if not is_coupang_product_already_used(row, used_products)
    ]
    if not available_indexes:
        raise RuntimeError("사용 가능한 네이버 쇼핑커넥트 상품이 없습니다. 사용 이력 파일을 초기화하거나 새 상품을 추가하세요.")

    recent_history = load_coupang_selection_history()
    candidate_scores = []
    for idx in available_indexes:
        row = rows[idx]
        score, group_name, category, keyword = score_coupang_candidate(row, recent_history)
        candidate_scores.append(
            {
                "index": idx,
                "score": score,
                "group": group_name,
                "category": category,
                "keyword": keyword,
            }
        )

    best_score = max(item["score"] for item in candidate_scores)
    best_candidates = [item for item in candidate_scores if item["score"] == best_score]
    selected_candidate = random.choice(best_candidates)
    selected_index = selected_candidate["index"]
    selected_row = dict(rows[selected_index])
    selected_row["쿠팡링크"] = get_product_field(selected_row, "쇼핑커넥트링크", "쿠팡링크")

    seed_key = get_coupang_product_key(selected_row)

    if not get_product_field(selected_row, "상품명") or not get_product_field(selected_row, "쇼핑커넥트링크", "쿠팡링크"):
        raise RuntimeError("네이버 쇼핑커넥트 상품명 또는 쇼핑커넥트링크가 비어 있습니다.")

    return {
        "selected_index": selected_index,
        "selected_row": selected_row,
        "selected_group": selected_candidate["group"],
        "seed_key": seed_key,
    }


def mark_coupang_product_as_used(csv_path, product_state, blog_title):
    """네이버 쇼핑커넥트 글 발행 성공 후 해당 상품의 사용 이력을 기록한다."""
    selected_row = product_state["selected_row"]
    used_products = load_coupang_used_products()
    used_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    used_entry = {
        "product_name": str(selected_row.get("상품명") or "").strip(),
        "keyword": str(selected_row.get("키워드") or "").strip(),
        "product_link": str(selected_row.get("쇼핑커넥트링크") or selected_row.get("쿠팡링크") or "").strip(),
        "used_at": used_at,
        "post_title": blog_title,
    }
    product_key = get_coupang_product_key(selected_row)
    used_products[product_key] = used_entry
    seed_key = product_state.get("seed_key")
    if seed_key and seed_key != product_key:
        used_products[seed_key] = used_entry
    save_coupang_used_products(used_products)
    mark_coupang_csv_row_as_used(csv_path, {product_key, seed_key}, used_at, blog_title)
    record_coupang_selection_history(selected_row)


def mark_coupang_csv_row_as_used(csv_path, product_keys, used_at, blog_title):
    """CSV에도 used/used_at/post_title을 남겨 운영자가 파일만 봐도 사용 여부를 알 수 있게 한다."""
    if not csv_path or not os.path.exists(csv_path):
        return False

    rows, fieldnames, encoding = load_csv_rows(csv_path)
    product_keys = {key for key in product_keys if key}
    if not product_keys:
        return False

    for field in ("used", "used_at", "post_title"):
        if field not in fieldnames:
            fieldnames.append(field)

    changed = False
    for row in rows:
        if get_coupang_product_key(row) not in product_keys:
            continue
        row["used"] = "true"
        row["used_at"] = used_at
        row["post_title"] = blog_title
        changed = True

    if not changed:
        print("   >> [주의] CSV에서 사용 처리할 네이버 쇼핑커넥트 상품 행을 찾지 못했습니다.")
        return False

    with open(csv_path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("   >> 네이버 쇼핑커넥트 CSV used 처리 완료")
    return True


def get_product_field(row, *keys, default=""):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def normalize_coupang_cta_text(text):
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    replacements = {
        "아래 링크": "상세정보 확인 링크",
        "하단 링크": "상세정보 확인 링크",
        "마지막 링크": "상세정보 확인 링크",
        "위 링크": "상세정보 확인 링크",
        "아래에서": "상세페이지에서",
        "하단에서": "상세페이지에서",
        "마지막에": "확인 단계에서",
        "마지막에는": "확인 단계에서는",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def build_coupang_link_block(label, message, product_name, product_link):
    return (
        f"{'─' * 25}\n\n"
        f"{label}\n"
        f"{message}\n"
        f"상품명: {product_name}\n"
        f"{product_link}"
    )


def distribute_coupang_links(raw_content, product_name, product_link, cta_text):
    """
    네이버 쇼핑커넥트 링크를 네이버 블로그 본문에 2회만 삽입한다.
    - 1회차: 본문 중간 이후 자연스러운 위치
    - 2회차: 본문 마지막
    - 상단 링크는 광고성 신호가 강해질 수 있어 넣지 않는다.
    """
    paragraphs = [part.strip() for part in raw_content.split("\n\n") if part.strip()]
    if not paragraphs:
        return raw_content

    custom_cta = normalize_coupang_cta_text(cta_text)
    mid_message = custom_cta or "본문을 읽다가 제품 조건이 궁금해졌다면 상세 정보와 현재 조건을 직접 확인해보면 좋다"
    bottom_message = "가격, 옵션, 후기, 배송 조건은 변동될 수 있으니 상세페이지에서 한 번 더 확인하는 편이 좋다"

    mid_block = build_coupang_link_block(
        "관련 정보 확인",
        mid_message,
        product_name,
        product_link
    )

    bottom_block = build_coupang_link_block(
        "상세정보와 후기 확인",
        bottom_message,
        product_name,
        product_link
    )

    if len(paragraphs) >= 5:
        mid_index = max(2, len(paragraphs) // 2)
    elif len(paragraphs) >= 3:
        mid_index = 2
    else:
        mid_index = len(paragraphs)

    paragraphs.insert(mid_index, mid_block)
    paragraphs.append(bottom_block)

    print("   >> 네이버 쇼핑커넥트 링크 삽입 완료: 2회")
    return "\n\n".join(paragraphs)


def extract_hashtag_line(text, min_count=5):
    tags = re.findall(r"#[0-9A-Za-z가-힣_]+", text or "")
    unique_tags = []
    seen = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        unique_tags.append(tag)
    if len(unique_tags) < min_count:
        return ""
    return " ".join(unique_tags[:15])


# =============================================================
# 2. ChatGPTWebBot - 네이버 전용 프로젝트에서 텍스트+이미지 생성
# =============================================================
CHATGPT_PROJECT_URL = "https://chatgpt.com/g/g-p-6a01727f21208191a66e53986f5cd0ae-neibeo-jeonyong/project"


def resolve_chatgpt_profile_path():
    env_profile_path = os.getenv("CHATGPT_PROFILE_PATH", "").strip()
    if env_profile_path:
        return env_profile_path
    return os.path.join(os.path.expanduser("~"), "ChromeChatGPTNaverConnectBot")


class ChatGPTWebBot:
    """ChatGPT 네이버 전용 프로젝트 하나의 세션에서 텍스트/이미지 모두 처리"""

    def __init__(self):
        chatgpt_options = Options()
        automation_profile = resolve_chatgpt_profile_path()
        os.makedirs(automation_profile, exist_ok=True)
        chatgpt_options.add_argument(f"--user-data-dir={automation_profile}")
        chatgpt_options.add_argument("--profile-directory=Default")
        chatgpt_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chatgpt_options.add_experimental_option("useAutomationExtension", False)
        chatgpt_options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = create_chrome_driver(chatgpt_options)
        self.driver.maximize_window()
        self.response_count = 0

        print(f"   >> [안내] ChatGPT 프로필 경로: {automation_profile}")
        print("   >> 🌐 ChatGPT 네이버 전용 프로젝트 접속 중...")
        self.driver.get(CHATGPT_PROJECT_URL)
        time.sleep(5)

        self._wait_for_login_if_needed()
        if not self._wait_until_ready_for_next_prompt(timeout=180, stable_seconds=3):
            raise RuntimeError("ChatGPT 네이버 전용 입력창을 찾지 못했습니다. 로그인 상태와 프로젝트 URL을 확인하세요.")
        print("   >> ✅ ChatGPT 네이버 전용 프로젝트 준비 완료!")

    def _is_login_page(self):
        url = (self.driver.current_url or "").lower()
        return (
            "auth.openai.com" in url
            or "/auth/login" in url
            or "login" in url
            or "signin" in url
        )

    def _wait_for_login_if_needed(self):
        if not self._is_login_page() and self._find_input(silent=True):
            return

        print("   >> 🔑 ChatGPT 로그인이 필요하면 열린 브라우저에서 직접 로그인해주세요 (최대 5분 대기)")
        print("   >>     ※ 최초 실행 시에만 필요합니다. 이후에는 같은 Chrome 프로필 세션을 재사용합니다.")

        WebDriverWait(self.driver, 300).until(
            lambda _driver: (not self._is_login_page()) and bool(self._find_input(silent=True))
        )
        time.sleep(2)
        self.driver.get(CHATGPT_PROJECT_URL)
        time.sleep(3)
        print("   >> ✅ ChatGPT 로그인/프로젝트 진입 확인 완료!")

    def _find_input(self, silent=False):
        """ChatGPT ProseMirror 입력창 찾기"""
        selectors = [
            "div#prompt-textarea.ProseMirror[contenteditable='true']",
            "div#prompt-textarea[contenteditable='true']",
            "div[contenteditable='true'][id='prompt-textarea']",
            "div[contenteditable='true'][aria-label*='네이버 전용']",
            "div[contenteditable='true'][role='textbox']",
            "textarea#prompt-textarea",
            "textarea",
        ]
        for sel in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if el.is_displayed() and el.size.get("height", 0) > 10:
                        return el
            except Exception:
                continue
        if not silent:
            print("   >> [주의] ChatGPT 입력창을 아직 찾지 못했습니다.")
        return None

    def _get_response_elements(self):
        selectors = [
            "div[data-message-author-role='assistant'] div.markdown",
            "article div.markdown",
            "div.markdown.prose",
            "div.markdown",
        ]
        for sel in selectors:
            try:
                elements = [
                    el for el in self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if el.is_displayed() and (el.text or "").strip()
                ]
                if elements:
                    return elements
            except Exception:
                continue
        return []

    def _extract_last_response(self):
        elements = self._get_response_elements()
        if elements:
            text = elements[-1].get_attribute("innerText") or elements[-1].text
            if text and len(text.strip()) > 10:
                return text.strip()
        return None

    def _is_placeholder_response(self, text):
        text = (text or "").strip()
        if not text:
            return True
        lowered = text.lower()
        placeholder_patterns = [
            "생각하는 중",
            "생각 중",
            "응답 생성 중",
            "답변 생성 중",
            "작성 중",
            "thinking",
            "generating",
        ]
        return len(text) < 80 and any(pattern in lowered for pattern in placeholder_patterns)

    def _is_generating(self):
        selectors = [
            "button[data-testid='stop-button']",
            "button[aria-label*='Stop']",
            "button[aria-label*='중지']",
        ]
        for sel in selectors:
            try:
                for el in self.driver.find_elements(By.CSS_SELECTOR, sel):
                    if el.is_displayed():
                        return True
            except Exception:
                continue
        return False

    def _is_ready_for_next_prompt(self):
        return (not self._is_generating()) and bool(self._find_input(silent=True))

    def _wait_until_ready_for_next_prompt(self, timeout=120, stable_seconds=5):
        stable_count = 0
        for wait_sec in range(timeout):
            if self._is_ready_for_next_prompt():
                stable_count += 1
                if stable_count >= stable_seconds:
                    if wait_sec > 0:
                        print(f"   >> ⏱️ ChatGPT 입력 가능 상태 확인 완료 ({wait_sec}초 대기)")
                    return True
            else:
                stable_count = 0

            if wait_sec > 0 and wait_sec % 20 == 0:
                print(f"   >> ⏳ ChatGPT 입력 가능 상태 대기 중... ({wait_sec}초)")
            time.sleep(1)

        return False

    def _wait_for_prompt_settle(self, prompt):
        prompt_len = len(prompt or "")
        if prompt_len >= 6000:
            wait_seconds = 10.0
        elif prompt_len >= 3500:
            wait_seconds = 6.0
        elif prompt_len >= 1800:
            wait_seconds = 4.0
        else:
            wait_seconds = 2.0
        print(f"   >> ⏳ 프롬프트 입력 안정화 대기 {wait_seconds:.1f}초")
        time.sleep(wait_seconds)

    def _paste_prompt(self, input_el, prompt):
        input_el.click()
        time.sleep(0.5)
        try:
            input_el.send_keys(Keys.CONTROL, "a")
            input_el.send_keys(Keys.DELETE)
            time.sleep(0.2)
        except Exception:
            pass

        pyperclip.copy(prompt)
        ActionChains(self.driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
        time.sleep(1)

        current_text = ""
        try:
            current_text = (input_el.text or "").strip()
            if not current_text:
                current_text = (self.driver.execute_script("return arguments[0].textContent;", input_el) or "").strip()
        except Exception:
            pass

        if current_text:
            return

        print("   >> [주의] Ctrl+V 입력 확인 실패. JavaScript 입력으로 재시도합니다.")
        self.driver.execute_script(
            """
            const el = arguments[0];
            const text = arguments[1];
            el.focus();
            const selection = window.getSelection();
            const range = document.createRange();
            range.selectNodeContents(el);
            selection.removeAllRanges();
            selection.addRange(range);
            document.execCommand('delete', false, null);
            const inserted = document.execCommand('insertText', false, text);
            if (!inserted) {
                el.textContent = text;
            }
            el.dispatchEvent(new InputEvent('input', {bubbles: true, inputType: 'insertText', data: text}));
            """,
            input_el,
            prompt,
        )
        time.sleep(0.8)

    def _submit_prompt(self):
        input_el = self._find_input()
        if not input_el:
            raise RuntimeError("ChatGPT 입력창을 찾지 못해 전송할 수 없습니다.")

        input_el.send_keys(Keys.ENTER)
        time.sleep(1.5)

        send_selectors = [
            "button[data-testid='send-button']",
            "button[aria-label*='Send']",
            "button[aria-label*='send']",
            "button[aria-label*='전송']",
        ]
        for sel in send_selectors:
            try:
                for btn in self.driver.find_elements(By.CSS_SELECTOR, sel):
                    if btn.is_displayed() and btn.is_enabled():
                        print("   >> [전송] Enter 미작동 가능성 감지, 전송 버튼 직접 클릭")
                        btn.click()
                        time.sleep(1)
                        return
            except Exception:
                continue

    def _wait_for_text(self, previous_count=0, timeout=300, stable_seconds=6):
        started_at = time.time()
        prev_text = ""
        stable_count = 0

        while time.time() - started_at < timeout:
            current_text = None
            elements = self._get_response_elements()
            if len(elements) > previous_count:
                current_text = self._extract_last_response()
                if self._is_placeholder_response(current_text):
                    current_text = None

            if self._is_generating():
                stable_count = 0
            elif current_text and len(current_text) > 20:
                if current_text == prev_text:
                    stable_count += 1
                    if stable_count >= stable_seconds:
                        self._wait_until_ready_for_next_prompt(timeout=60, stable_seconds=5)
                        self.response_count += 1
                        print(f"   >> ✅ ChatGPT 응답 수신 완료! ({len(current_text)}자)")
                        return current_text
                else:
                    stable_count = 0
                prev_text = current_text

            elapsed = int(time.time() - started_at)
            if elapsed > 0 and elapsed % 30 == 0:
                text_len = len(prev_text) if prev_text else 0
                print(f"   >> 아직 생성 중... ({elapsed}초, 현재 {text_len}자)")
                time.sleep(1)
            else:
                time.sleep(1)

        if prev_text and len(prev_text) > 50:
            self._wait_until_ready_for_next_prompt(timeout=30, stable_seconds=3)
            print(f"   >> ⚠️ 타임아웃이지만 마지막 응답 반환 ({len(prev_text)}자)")
            return prev_text

        print("   >> [에러] ChatGPT 응답을 가져올 수 없습니다.")
        return None

    def send_prompt(self, prompt, max_wait=300):
        """프롬프트 전송 후 텍스트 응답 반환"""
        if not self._wait_until_ready_for_next_prompt(timeout=120, stable_seconds=3):
            print("   >> [주의] 입력창 준비 상태를 충분히 확인하지 못했지만 전송을 시도합니다.")

        input_el = self._find_input()
        if not input_el:
            print("   >> [에러] ChatGPT 입력창을 찾지 못했습니다.")
            return None

        previous_count = len(self._get_response_elements())
        self._paste_prompt(input_el, prompt)
        self._wait_for_prompt_settle(prompt)
        self._submit_prompt()
        print("   >> ⏳ ChatGPT 응답 대기 중...")
        return self._wait_for_text(previous_count=previous_count, timeout=max_wait)

    def new_chat(self):
        """네이버 전용 프로젝트 새 채팅 화면으로 이동"""
        try:
            self.driver.get(CHATGPT_PROJECT_URL)
            time.sleep(4)
            self.response_count = 0
            self._wait_until_ready_for_next_prompt(timeout=120, stable_seconds=3)
            print("   >> 🔄 ChatGPT 네이버 전용 새 채팅 시작!")
            return True
        except Exception:
            return False

    def _visible_image_elements(self):
        selectors = [
            "img[src*='backend-api/estuary/content']",
            "img[src*='files.oaiusercontent.com']",
            "img[alt*='Generated']",
            "img[alt*='생성']",
            "article img",
        ]
        images = []
        seen = set()
        for sel in selectors:
            try:
                for img in self.driver.find_elements(By.CSS_SELECTOR, sel):
                    src = img.get_attribute("src") or img.get_attribute("currentSrc") or ""
                    key = src or str(id(img))
                    if key in seen:
                        continue
                    seen.add(key)
                    if not img.is_displayed():
                        continue
                    width = img.size.get("width", 0)
                    height = img.size.get("height", 0)
                    if width > 150 and height > 150 and "icon" not in src.lower():
                        images.append(img)
            except Exception:
                continue
        return images

    def _save_image_element(self, img, save_path):
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        src = img.get_attribute("src") or img.get_attribute("currentSrc") or ""
        if src.startswith("/"):
            src = "https://chatgpt.com" + src

        if src.startswith("http"):
            try:
                cookies = {c["name"]: c["value"] for c in self.driver.get_cookies()}
                headers = {"User-Agent": "Mozilla/5.0"}
                img_resp = requests.get(src, cookies=cookies, headers=headers, timeout=30)
                if img_resp.ok and len(img_resp.content) > 5000:
                    with open(save_path, "wb") as f:
                        f.write(img_resp.content)
                    return True
            except Exception:
                pass

        try:
            img.screenshot(save_path)
            return os.path.exists(save_path) and os.path.getsize(save_path) > 5000
        except Exception:
            return False

    def generate_image(self, img_description, save_path):
        """ChatGPT에서 이미지 생성 후 파일로 저장"""
        img_prompt = f"""다음 글 주제와 어울리는 고품질 블로그 썸네일 사진 1장을 생성해줘.
이미지 안에 글자나 로고 문구는 넣지 마.
광고 배너처럼 만들지 말고, 자연스러운 한국형 생활 장면으로 만들어줘.

{img_description}
"""
        if not self._wait_until_ready_for_next_prompt(timeout=120, stable_seconds=3):
            print("   >> [주의] 입력창 준비 상태를 충분히 확인하지 못했지만 이미지 요청을 시도합니다.")

        input_el = self._find_input()
        if not input_el:
            print("   >> [에러] ChatGPT 입력창을 찾지 못했습니다.")
            return None

        previous_count = len(self._visible_image_elements())
        self._paste_prompt(input_el, img_prompt)
        self._wait_for_prompt_settle(img_prompt)
        self._submit_prompt()
        print("   >> 🎨 ChatGPT 이미지 생성 요청 전송, 렌더링 대기 중...")

        for wait_sec in range(240):
            images = self._visible_image_elements()
            new_images = images[previous_count:] if len(images) > previous_count else images
            for img in reversed(new_images):
                time.sleep(2)
                if self._save_image_element(img, save_path):
                    print(f"   >> 🎨 ChatGPT 이미지 저장 완료: {save_path}")
                    return save_path

            if wait_sec > 0 and wait_sec % 20 == 0:
                print(f"   >> 아직 이미지 생성 중... ({wait_sec}초)")
            time.sleep(1)

        print("   >> [주의] 이미지를 찾지 못했습니다. 텍스트만 업로드합니다.")
        return None

    def close(self):
        """브라우저 닫기"""
        try:
            self.driver.quit()
        except Exception:
            pass


def save_chatgpt_login_session():
    print(f"\n[로그인 저장 모드] ChatGPT 네이버 전용 세션 저장 경로: {resolve_chatgpt_profile_path()}")
    print("브라우저가 열리면 ChatGPT에 로그인하고 네이버 전용 프로젝트 입력창이 보이는지 확인한 뒤 엔터를 누르세요.\n")
    bot = ChatGPTWebBot()
    try:
        input("→ ChatGPT 로그인/프로젝트 확인 완료 후 엔터를 누르세요...")
        print("   >> [저장 중] ChatGPT 브라우저를 정상 종료합니다...")
    finally:
        bot.close()
    print(f"[완료] ChatGPT 네이버 전용 세션 저장: {resolve_chatgpt_profile_path()}\n")


def save_naver_login_session(naver_id):
    naver_profile = resolve_naver_profile_path(naver_id)
    os.makedirs(naver_profile, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={naver_profile}")
    options.add_argument("--profile-directory=Default")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = create_chrome_driver(options)
    driver.maximize_window()
    try:
        write_url = get_naver_write_url(naver_id)
        print(f"\n[네이버 로그인 저장 모드] 네이버 ID: {naver_id}")
        print(f"[네이버 로그인 저장 모드] 프로필 경로: {naver_profile}")
        print(f"[네이버 로그인 저장 모드] 글쓰기 URL: {write_url}")
        print("브라우저에서 해당 네이버 계정으로 로그인하고 글쓰기 화면이 보이면 콘솔에서 엔터를 누르세요.\n")
        driver.get(write_url)
        input("→ 네이버 로그인/글쓰기 화면 확인 완료 후 엔터를 누르세요...")
        print("   >> [저장 중] 네이버 브라우저를 정상 종료합니다...")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    print(f"[완료] 네이버 세션 저장: {naver_profile}\n")


# =============================================================
# 3. 콘텐츠 생성 함수 (ChatGPT 웹 전용)
# =============================================================
def generate_content(post_type):
    """
    post_type: '일상', '네이버' 또는 '쿠팡'(호환)
    ChatGPT 네이버 전용 프로젝트 하나의 세션에서 텍스트+이미지 모두 생성
    """
    img_path = os.path.join(BASE_DIR, f'temp_blog_img_{int(time.time())}.png')
    
    # ChatGPTWebBot 세션 시작
    bot = ChatGPTWebBot()
    
    try:
        product_state = None
        if post_type == "\uc77c\uc0c1":
            daily_context = build_daily_topic_context()
            prompt = build_daily_post_prompt(daily_context)

            print("   >> 일상 주제 컨텍스트 선정 완료...")
            print(f"   >> 검색 주제: {daily_context['search_phrase']} | 카테고리: {daily_context['content_category']} | 날씨: {daily_context['weather_key']}")

            print("   >> 블로그 본문 생성 중 (ChatGPT, 최대 5분 대기)...")
            blog_content = bot.send_prompt(prompt, max_wait=300)
            if not blog_content:
                return None, None, None, "", None

            print("   >> 제목 생성 중 (ChatGPT)...")
            title_prompt = f"""
너는 네이버 검색 유입과 클릭률을 함께 고려하는 블로그 제목 편집자입니다.
아래 검색 의도와 본문을 보고 제목 1개만 작성하세요.

[검색 의도]
- 확정 핵심 검색어: {daily_context['search_phrase']}
- 독자 고민: {daily_context['reader_problem']}
- 글에서 해결할 약속: {daily_context['reader_promise']}

[제목 규칙]
- 제목은 단순 일상 제목이 아니라 사람들이 실제로 검색할 만한 청담 엄마 라이프스타일 정보형 제목이어야 한다
- 확정 핵심 검색어 또는 자연스러운 변형을 제목 앞쪽에 넣는다
- 아이 동반, 미식, 문화생활, 성분, 소재, 동선 중 문맥에 맞는 확인 기준이 제목만 봐도 보여야 한다
- 상품을 직접 사용한 것처럼 보이는 제목은 쓰지 않는다
- 내돈내산, 직접 써보니, 인생템, 역대급, 최저가, 무조건, 완벽정리, 꿀팁 같은 표현은 금지
- 오늘의 일상, 소소한 기록, 하루 기록 같은 일기형 제목 금지
- 22자 이상 48자 이하의 한국어 제목 1줄만 출력
- 영어, 따옴표, 해시태그, 이모티콘, 설명 문장 금지

[본문 일부]
{blog_content[:900]}
"""
            blog_title = bot.send_prompt(title_prompt, max_wait=180)
            if blog_title:
                blog_title = re.sub(r"[#\"'“”‘’]", "", blog_title).strip().split("\n")[0]
                if re.search(r"[A-Za-z]{3,}", blog_title):
                    blog_title = ""
            else:
                blog_title = ""
            if not blog_title:
                blog_title = f"{daily_context['search_phrase']} 체크 기준"

            img_description = build_daily_image_prompt(daily_context)
            p_name = ""
            post_type = "__daily_done__"

        if post_type in AFFILIATE_POST_TYPES:
            product_state = select_unused_coupang_product(csv_file_path)
            target = product_state["selected_row"]
            coupang_angle = get_next_coupang_angle(datetime.now())
            angle_name = coupang_angle.get("name", "구매체크형")
            angle_direction = coupang_angle.get("post_angle", "구매 전 확인할 조건을 정리하는 글")
            p_name = target['상품명']
            p_keyword = target['키워드']
            p_link = get_product_field(target, "쇼핑커넥트링크", "쿠팡링크")
            product_group = product_state.get("selected_group") or infer_coupang_product_group(target)
            
            problem_scenario = get_product_field(target, "문제상황", default=f"{p_keyword}이 필요한데 어떤 제품을 골라야 할지 애매한 상황")
            target_reader = get_product_field(target, "대상독자", default="구매 전에 자기 환경에 맞는 확인 기준을 먼저 보고 싶은 사람")
            usage_place = get_product_field(target, "사용장소", default="집이나 개인 작업 공간")
            season_tag = get_product_field(target, "시즌태그", "계절태그", default="사계절")
            pain_point = get_product_field(target, "불편포인트", default="광고성 정보는 많은데 내 상황에 맞는 판단이 어려운 점")
            selling_point_1 = get_product_field(target, "장점1", default="사용 환경 기준으로 무난하게 접근하기 쉬운 점")
            selling_point_2 = get_product_field(target, "장점2", default="가격 대비 만족도를 기대하기 쉬운 점")
            selling_point_3 = get_product_field(target, "장점3", default="후기와 정보량이 비교적 많은 점")
            product_rating = get_product_field(target, "평점", default="")
            product_review_count = get_product_field(target, "리뷰개수", "리뷰수", default="")
            caution_note = get_product_field(target, "주의점", default="사용 환경과 예산에 따라 만족도가 달라질 수 있음")
            post_angle = get_product_field(target, "글관점", default=angle_direction)
            title_seed = get_product_field(target, "제목시드", default=coupang_angle.get("title_seed", f"{p_keyword} 고를 때 구매 전 보기 쉬운 체크포인트"))
            thumbnail_prompt = get_product_field(target, "썸네일프롬프트", default=coupang_angle.get("thumbnail_prompt", f"{p_keyword}를 {usage_place}에서 실제로 사용하는 한국형 라이프스타일 장면"))
            cta_text = normalize_coupang_cta_text(
                get_product_field(
                    target,
                    "CTA문구",
                    default=coupang_angle.get("cta_text", "제품 상세정보와 현재 조건은 상세페이지에서 확인하는 흐름"),
                )
            )
            group_writing_guide = build_coupang_group_writing_guide(product_group, target)
            disclosure_text = get_product_field(
                target,
                "광고고지문",
                default="이 포스팅은 네이버 쇼핑커넥트 활동의 일환으로 이에 따른 일정액의 수수료를 제공받습니다.",
            )

            # 1단계: 본문 생성
            print("   >> 📝 블로그 본문 생성 중 (ChatGPT, 최대 5분 대기)...")
            prompt = f"""
너는 네이버 블로그에서 청담에 사는 자녀 둔 어머니의 기준으로 상품을 세밀하게 검토하는 라이프스타일 블로거다.
이 글은 네이버 블로그 에디터에 그대로 들어갈 본문이므로 HTML, 마크다운, 코드블록을 절대 쓰지 않는다.

이 글의 목적은 단순 상품 홍보가 아니다.
검색자가 상품을 사기 전에 성분, 소재, 마감, 월령, 세척, 보관, 아이 생활 동선처럼 실제로 따져볼 기준을 먼저 나누고, 자기 아이와 집에 맞는 확인 순서를 잡아준 뒤, 필요한 경우 상세정보 확인으로 이어지게 만드는 것이다.
상품은 글의 출발점이 아니라 문제 해결을 검토할 때 참고하는 후보로만 다룬다.

광고 고지문은 코드에서 disclosure_text로 본문 최상단에 자동으로 붙는다.
따라서 본문 안에서 네이버 쇼핑커넥트 광고 고지문을 다시 출력하지 마라.
상품 링크도 본문 안에 직접 출력하지 마라. 링크는 코드가 따로 삽입한다.

[블로그 컨셉]
{BLOG_PERSONA_CONCEPT}

- 말투는 실제 청담 사는 애엄마처럼 자연스럽게 쓴다.
- 예쁘다, 유명하다, 많이 산다보다 내 아이와 우리 집 기준에 맞는지 먼저 따진다.
- 광고글이어도 성분, 면 소재, 봉제, 마감, 세척, 보관, 월령, 외출 동선까지 왜 중요한지 분명히 설명한다.
- 부자처럼 과시하는 문장보다 좋은 것을 고를 때 세세하게 보는 안목이 드러나야 한다.

[오늘 진단할 생활문제와 연결 상품]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
- 상품군: {product_group}
- 대상 독자: {target_reader}
- 사용 상황: {problem_scenario}
- 사용 장소: {usage_place}
- 시즌/시기: {season_tag}
- 독자가 겪는 불편: {pain_point}
- 평점 참고값: {product_rating or "미제공"}
- 리뷰 개수 참고값: {product_review_count or "미제공"}
- 강조 포인트 1: {selling_point_1}
- 강조 포인트 2: {selling_point_2}
- 강조 포인트 3: {selling_point_3}
- 구매 전 주의점: {caution_note}
- 글 관점: {post_angle}
- 오늘 글 변주: {angle_name} / {angle_direction}
- 제목 방향 참고: {title_seed}
- CTA 방향: {cta_text}

[상품군별 밀도 기준]
{group_writing_guide}

[전문용어 사용 원칙]
- 본문에는 상품군에 맞는 전문용어를 2~4개 자연스럽게 포함하라.
- 전문용어를 쓴 직후에는 반드시 쉬운 말로 풀어서 설명하라.
- 전문용어만 나열하지 말고 "이 용어가 엄마 입장에서 왜 확인 기준이 되는지"까지 연결하라.
- 전문가처럼 진단하거나 효능을 보장하지 말고, 청담에서 아이를 키우는 엄마가 공부해서 쉽게 풀어주는 톤으로 쓴다.
- 전문용어는 성분, 소재, 월령, 세척, 보관, 안전성, 사용 동선과 연결해서 설명한다.
- 상품군과 맞지 않는 전문용어는 억지로 넣지 마라.

상품군별로 참고할 수 있는 전문용어 예시는 아래와 같다.
- 유아 의류: 면 소재, 혼용률, 밤부, 모달, 메쉬, 봉제선, 라벨 위치, 지퍼 마감
- 젖병/수유용품: PPSU, PP, BPA Free, 열탕 소독, 젖꼭지 단계, 유량, 배앓이 방지 밸브
- 선크림/스킨케어: 무기자차, 논나노, SPF, PA, 백탁, 워터프루프, 사용 연령, 전성분
- 물티슈/위생용품: 평량, 엠보싱, 캡형, 전성분, 향료, pH, 소독 성분
- 이유식/식품: 원재료, 유기농 인증, HACCP, 알레르기 유발 성분, 소분, 냉동 보관, 월령
- 교구/장난감: 권장 연령, 부품 크기, 마감, 모서리, 자석 부품, 세척 가능 여부
- 식기/보관용품: 소재, 밀폐력, 열탕 소독, 전자레인지 가능 여부, 식기세척기 가능 여부, 냉장/냉동 보관

좋은 문장 예시는 아래 느낌을 참고하되 그대로 복사하지 마라.
- PPSU는 열에 강한 소재로 많이 언급되지만, 엄마 입장에서는 열탕 소독 가능 여부와 젖꼭지 단계 호환을 같이 봐야 마음이 편합니다.
- 밤부 메쉬는 통기감 때문에 보게 되는 소재지만, 아이 피부에 닿는 제품이라면 혼용률, 봉제선, 세탁 후 촉감까지 같이 확인하는 편이 좋습니다.
- 무기자차 선크림은 피부 표면에서 자외선을 반사하는 방식으로 설명되지만, 아이용으로 볼 때는 백탁, 발림성, 사용 연령, 세안 편의성을 함께 봐야 합니다.
- HACCP이나 유기농 인증은 선택 기준이 될 수 있지만, 아이에게 맞는지는 원재료와 알레르기 유발 성분을 함께 확인해야 합니다.

[skssj2629 블로그 방향]
이 블로그는 청담 사는 자녀 둔 어머니가 미식과 문화생활을 즐기면서도, 아이에게 닿는 제품은 성분과 소재까지 세밀하게 보는 블로그다.
중심 주제는 유아용품, 이유식과 분유, 수유용품, 아이 의류, 유아 위생용품, 선크림, 물티슈, 젖병, 치약과 칫솔, 장난감과 교구, 키즈 라이프, 프리미엄 살림, 아이 동반 외출 동선이다.
현재 상품이 유아용품이 아니더라도 억지로 육아용품인 척하지 마라.
대신 청담 엄마의 기준으로 사용 장소, 계절성, 생활 불편, 구매 전 체크포인트 중심으로 자연스럽게 연결하라.

[기준 진단형 작성 원칙]
- 글의 주어는 상품이 아니라 아이, 엄마의 생활 동선, 성분과 소재, 사용 조건이어야 한다.
- 본문 앞부분에서는 상품 장점보다 왜 이 기준을 먼저 봐야 하는지와 무엇부터 확인해야 하는지를 설명한다.
- '{p_name}'은 해결 후보를 확인하는 예시로만 언급하고, 글 전체를 상품 소개문처럼 만들지 않는다.
- 독자가 글을 읽고 "우리 아이와 우리 집 기준에서는 무엇을 먼저 보면 되는지" 알 수 있어야 한다.
- 좋은 흐름 예시: 아이에게 닿는 제품을 고를 때 고민되는 지점 -> 성분/소재/월령/세척 기준 확인 -> '{p_name}' 같은 제품을 볼 때 상세정보와 후기 흐름 확인.
- 나쁜 흐름 예시: 상품명 소개 -> 장점 나열 -> 추천 대상 -> 바로 구매 유도.

[가장 중요한 작성 원칙]
- AI가 정리한 설명문처럼 쓰지 마라.
- 사람이 네이버 블로그에 직접 남긴 생활 기록처럼 자연스럽게 써라.
- 다만 실제 사용하지 않았는데 직접 사용했다고 꾸미지는 마라.
- 내돈내산, 직접 써봤다, 제가 샀다, 며칠 써보니, 집에서 계속 써보니, 협찬 아님 같은 표현은 절대 쓰지 마라.
- "후기들을 보면", "상세페이지 기준으로 보면", "구매 전 확인할 부분은", "사용 환경에 따라" 같은 표현을 자연스럽게 활용하라.
- 확인되지 않은 가격, 할인율, 판매량, 순위, 최저가, 재고, 배송 보장, 성분 비율, 소재 혼용률, 사용 연령, 성능 수치는 절대 지어내지 마라.
- 전문용어가 들어가더라도 의학적 진단, 치료, 성장, 면역, 피부 개선, 질병 예방처럼 고위험 효능을 단정하지 마라.
- 평점과 리뷰 개수가 제공된 경우에는 실제 제공값을 본문에 1~2회 자연스럽게 넣어라. 예: "상세페이지 기준 평점과 리뷰가 꽤 쌓여 있어 후기 흐름을 같이 볼 수 있습니다."
- 단, 평점과 리뷰 개수는 상세페이지 기준 참고 정보로만 다루고, 만족 보장이나 품질 보장처럼 단정하지 마라.
- 평점과 리뷰 개수가 미제공이면 본문에서 숫자를 절대 지어내지 마라.
- 상품을 무조건 좋다고 하지 말고, 먼저 확인해야 할 환경과 신중히 볼 환경을 분명히 나눠라.
- 과장된 구매 유도보다 구매 전 판단 기준을 우선한다.
- {post_angle} 관점을 자연스럽게 반영하라.
- 오늘 글 변주인 {angle_name} 흐름을 반영하되, 실제 구매나 직접 사용을 한 것처럼 꾸미지는 마라.

[사람이 쓴 듯한 문장감]
- 문장은 너무 반듯하게만 쓰지 말고, 중간중간 생활감 있는 흐름을 넣어라.
- 예: "아이에게 닿는 건 막상 고르려고 보면 성분표부터 다시 보게 됩니다."
- 예: "처음에는 디자인이 먼저 보이는데, 결국 오래 남는 건 소재와 세척이더라고요."
- 예: "청담에서 아이와 외출하다 보면 예쁜 것보다 동선이 편한지가 훨씬 크게 느껴집니다."
- 단, 위 예문을 그대로 반복하지 말고 자연스럽게 변형하라.
- 너무 깔끔한 보고서 문장, 교과서 문장, AI 안내문 같은 말투는 피하라.
- "본 글에서는", "살펴보겠습니다", "알아보겠습니다", "도움이 되시길 바랍니다" 같은 흔한 AI식 표현은 쓰지 마라.
- 이모티콘은 쓰지 마라.
- 과한 감탄사도 쓰지 마라.

[SEO 규칙]
- 상품명 '{p_name}'은 본문에 3~5회만 자연스럽게 포함한다.
- 메인 키워드 '{p_keyword}'는 본문에 4~6회만 자연스럽게 포함한다.
- 키워드를 억지로 반복하지 마라.
- 아이 월령, 사용 장소, 성분, 소재, 봉제, 마감, 세척, 보관, 휴대, 배송 조건, 후기 확인, 상세정보 확인 같은 유사 키워드를 자연스럽게 섞어라.
- 제목은 출력하지 말고 본문만 작성한다.
- 해시태그도 본문에 넣지 마라.

[본문 구조 - 아래 순서를 반드시 지켜라]

1. 도입부: 청담 엄마가 실제로 따지는 기준으로 시작
- 첫 문단에서 {problem_scenario} 상황을 자연스럽게 풀어라.
- '{p_keyword}'를 1회 포함하라.
- 상품을 바로 추천하지 말고, 왜 성분, 소재, 월령, 세척, 동선 확인이 먼저인지 말하라.
- 광고 느낌으로 시작하지 말고, 아이를 키우는 엄마가 공감할 만한 생활 장면으로 시작하라.

2. 기준을 먼저 나눠야 하는 이유
- 독자가 {pain_point} 때문에 헷갈릴 수 있다는 흐름으로 작성하라.
- 아이 월령, 피부 민감도, 소재, 성분, 외출 동선, 세척과 보관, 사용 빈도 중 관련 있는 요소를 2~4개로 나눠 설명하라.
- 이 단계에서는 제품을 사야 한다고 말하지 말고, 먼저 내 아이와 집 기준에서 확인할 항목을 정리하라.
- 이 구간 끝에 아래 마커를 정확히 1회 넣어라.

[사진삽입]

[구분선]

3. 제품을 보기 전에 먼저 확인할 기준
- '{p_name}'을 자연스럽게 언급하되, 엄마가 후보 제품을 살필 때의 예시처럼 다루어라.
- 강조 포인트 3개를 그대로 복붙하지 말고, 성분/소재/마감/세척/월령/동선 중 어떤 기준과 연결되는지 풀어라.
- 아래 목록 마커를 정확히 사용하라.

[목록주제]제품을 보기 전 먼저 볼 기준
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
[목록끝]

4. 도움이 될 수 있는 조건과 주의점
- 장점은 아이와 엄마의 생활에서 어떤 조건을 확인할 때 도움이 되는지와 연결해서 작성하라.
- {selling_point_1}, {selling_point_2}, {selling_point_3}을 자연스럽게 반영하라.
- 주의점은 반드시 포함하라.
- {caution_note}를 자연스럽게 반영하라.
- 단점은 과하게 부정하지 말고 "이런 경우에는 한 번 더 확인이 필요하다"는 방식으로 써라.
- 감정이 살아있는 문장을 아래 형식으로 1개 넣어라.
- 인용구 안에는 반드시 20자 이상 60자 이하의 완성된 한국어 문장을 넣어라.
- 빈 인용구, 공백만 있는 인용구, 예시 문구가 그대로 남은 인용구는 절대 출력하지 마라.

[인용구]아이에게 닿는 제품은 예쁜지보다 먼저 기준을 나눠봐야 합니다[/인용구]

[구분선]

5. 먼저 확인할 환경과 신중히 볼 환경
- 먼저 확인해볼 환경 3가지를 구체적으로 작성하라.
- 한 번 더 따져볼 환경 2가지를 작성하라.
- 이 구간은 신뢰도를 높이는 핵심 구간이다.
- 추천합니다, 비추천합니다 같은 판정형 표현보다 이 경우는 먼저 확인하세요에 가까운 문장으로 작성하라.

[목록주제]이런 환경이라면 먼저 확인하세요
- 먼저 확인할 환경 1
- 먼저 확인할 환경 2
- 먼저 확인할 환경 3
[목록끝]

[목록주제]이런 환경이라면 한 번 더 확인하세요
- 한 번 더 따져볼 환경 1
- 한 번 더 따져볼 환경 2
[목록끝]

6. 같은 문제를 해결할 때 비교할 관점
- 같은 생활 문제를 해결할 때 비교해야 할 기준을 설명하라.
- 특정 경쟁 상품을 근거 없이 깎아내리지 마라.
- '{p_keyword}'를 찾는 사람이 실제로 비교할 만한 기준을 말하라.
- 이유식/분유라면 월령과 단계, 원재료, 알레르기 확인, 보관, 조리 동선을 우선 고려하라.
- 수유용품이라면 소재, 용량, 세척/소독 조건, 젖꼭지 단계, 휴대성을 우선 고려하라.
- 유아 위생/스킨케어라면 전성분, 사용 연령, 향 여부, 피부에 닿는 빈도, 보관을 우선 고려하라.
- 유아 의류라면 면 소재와 혼용률, 봉제선, 라벨, 지퍼 마감, 세탁 후 촉감을 우선 고려하라.
- 장난감/교구라면 권장 연령, 부품 크기, 마감, 세척, 보관, 아이 성향을 우선 고려하라.
- 생활가전이면 사용 공간, 보관성, 세척, 관리, 내구성, 옵션, 배송 조건을 우선 고려하라.
- 디지털기기이면 호환 모델, 저장공간, 연결 방식, 사용 장소, 보증과 구성품을 우선 고려하라.
- 차량용품이면 차종 호환, 설치 방식, 조작 방식, 시야와 안전 영향을 우선 고려하라.
- 스포츠용품이면 사이즈, 소재, 착용감, 사용 빈도, 관리 방법을 우선 고려하라.

[구분선]

7. 상황별 진단 후 선택 기준
- 무조건 이 상품을 사라고 하지 마라.
- 상황별로 선택 기준을 나눠라.
- 예: 신생아라면, 등원복이라면, 외출용이라면, 피부가 예민한 아이라면, 선물용이라면, 청담 브런치나 호텔 외출에 챙길 용도라면
- '{p_name}'을 마지막에 1회 자연스럽게 언급하라.

8. 상세정보 확인 단계
- 구매 강요가 아니라 확인 유도형으로 작성하라.
- {cta_text} 방향을 자연스럽게 반영하라.
- 링크는 코드가 별도 정보 확인 구간으로 자동 삽입한다.
- 따라서 아래 링크, 하단 링크, 마지막 링크, 위 링크처럼 위치를 가리키는 표현은 쓰지 마라.
- 본문 안에 URL이나 상품 링크 문장을 직접 만들지 마라.
- 반드시 아래 의미를 포함하라.
  - 현재 가격과 구성은 변동될 수 있음
  - 배송 조건과 혜택은 상품과 시점에 따라 달라질 수 있음
  - 구매 전 상세정보, 옵션, 후기, 배송 조건을 확인하는 것이 좋음
  - 내 아이와 사용 환경에 맞는지 확인 후 선택하는 것이 안전함

[인용구]기준을 나눠보고 나면 상세정보에서 확인할 부분도 훨씬 또렷해집니다[/인용구]

9. FAQ
- 마지막에 실제 검색자가 궁금해할 만한 질문 4개와 실용적인 답변을 작성하라.
- 질문은 "{p_keyword} 보기 전에 무엇부터 확인해야 하나요", "우리 아이에게 맞는 기준은 무엇인가요", "배송 조건과 후기는 어디서 확인하나요" 같은 구매 전 확인 의도를 반영하라.
- 답변은 짧지만 실용적으로 작성하라.
- FAQ에도 '{p_keyword}'를 1~2회 자연스럽게 포함하라.
- FAQ 형식은 아래를 따라라.

Q. 질문 내용
A. 답변 내용

[출력 형식]
- 제목 없이 본문만 출력
- 1800자 이상 2500자 이하
- 자연스러운 한국어만 사용
- 영어 문장, 영어 제목, 영어 작업 메모 금지
- 마크다운 서식 금지
- 해설, 메모, 주석, 제목 후보, 해시태그를 함께 출력하지 말 것
- [사진삽입]은 정확히 1회
- [구분선]은 정확히 3회
- [인용구]문장[/인용구] 형식 정확히 2회
- 인용구 내부 문장은 반드시 20자 이상이어야 하며, 빈 인용구 출력 금지
- [목록주제]와 [목록끝] 마커는 철자 그대로 유지
- 문단 사이에는 빈 줄을 충분히 넣어라

[절대 금지]
- 광고 고지문 출력 금지
- 상품 링크 출력 금지
- 아래 링크, 하단 링크, 마지막 링크, 위 링크 같은 위치 지시 표현 금지
- [인용구][/인용구], [인용구] [/인용구], [인용구]문장[/인용구]처럼 내용 없는 인용구 출력 금지
- 가격, 할인율, 배송일, 리뷰 수, 평점, 순위 임의 생성 금지
- 내돈내산 표현 금지
- 직접 사용한 것처럼 단정 금지
- 근거 없는 비교 우위 금지
- 키워드 반복만으로 분량 채우기 금지
- 같은 문장 구조 반복 금지
- 추천합니다, 비추천합니다, 강력 추천합니다 같은 판정형 문장 금지
- "인생템", "역대급", "무조건", "최저가", "완전 강추", "진짜 대박" 같은 과장 표현 금지
- "설명드리겠습니다", "알아보겠습니다", "본 글에서는" 같은 AI식 문장 금지
- 네이버 공식 추천, 판매 1위, 100% 만족, 완벽한 제품 금지
"""
            prompt += "\n\n[언어 규칙]\n- 결과는 반드시 자연스러운 한국어로만 작성할 것\n- 영어 문장, 영어 제목, 영어 작업 메모를 절대 출력하지 말 것"
            raw_content = bot.send_prompt(prompt, max_wait=300)
            if not raw_content:
                return None, None, None, "", None
            
            ad_disclaimer = disclosure_text + "\n\n"
            linked_content = distribute_coupang_links(raw_content, p_name, p_link, cta_text)
            blog_content = ad_disclaimer + linked_content
            
            # 2단계: 해시태그 생성
            print("   >> #️⃣ 해시태그 생성 중 (ChatGPT)...")
            hashtag_prompt = f"""
너는 네이버 블로그 네이버 쇼핑커넥트 글의 해시태그를 만드는 실전형 검색 유입 편집자다.
아래 상품과 직접 관련 있는 태그만 10~12개 만들어라.

[상품 정보]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
- 대상 독자: {target_reader}
- 사용 상황: {problem_scenario}
- 사용 장소: {usage_place}
- 시즌/시기: {season_tag}
- 상품군/성격 참고: {product_group}, 구매 전 체크, 사용 환경 확인
- 핵심 장점: {selling_point_1}, {selling_point_2}, {selling_point_3}
- 구매 전 주의점: {caution_note}

[태그 작성 원칙]
- 첫 번째 태그는 반드시 메인 키워드 '{p_keyword}'를 공백 없이 자연스럽게 바꾼 태그로 작성
- 두 번째 태그는 상품군 또는 품목명이 바로 보이는 태그로 작성
- 나머지는 상품명, 품목, 사용장소, 사용상황, 구매 전 비교 기준에서만 뽑기
- 상품과 직접 관련 없는 범용 태그 금지
- 실제 검색자가 네이버에서 상품을 찾을 때 쓸 법한 구매 의도형 태그 위주로 작성
- 너무 넓은 광고성 태그보다 구체적인 롱테일 태그를 우선
- 상품명 전체를 그대로 길게 붙이지 말고, 브랜드/품목/용량/개수/핵심 속성 중 검색에 도움이 되는 부분만 사용
- 상품과 맞지 않으면 원룸용, 가정용, 사무실용, 생활가전추천 같은 태그를 넣지 말 것
- 유아용품이면 월령, 성분, 소재, 세척, 보관, 사용연령, 외출준비 같은 기준을 우선
- 유아 의류면 면소재, 봉제, 세탁, 등원복, 실내복, 외출복 같은 기준을 우선
- 이유식/분유/수유용품이면 단계, 용량, 원재료, 젖병, 세척, 휴대 같은 기준을 우선
- 장난감/교구면 권장연령, 마감, 세척, 보관, 놀이 기준을 우선

[절대 금지 태그]
- #일상 #소통 #맞팔 #데일리 #오늘 #감성 #리뷰 #후기 #추천템 #핫딜 #최저가 #인생템
- 상품과 무관한 #원룸용 #가정용 #사무실용 #생활가전추천 #계절가전 #가격비교 #구성비교 남발 금지
- 쇼핑커넥트, 광고, 협찬, 배송만 단독으로 강조하는 태그 금지

[출력 규칙]
- '#태그' 형식만 사용
- 정확히 10~12개
- 한 줄에 공백으로 구분
- 설명 금지
- 영어 태그 금지
- 같은 의미의 태그 반복 금지
- 상품과 직접 관련 없는 태그 금지

출력 예시 형식
#메인키워드 #품목명 #구매전체크 #성분확인 #소재체크 #세척편의성 #사용연령 #육아용품 #상세정보확인 #구매전확인
"""
            hashtags = ""
            for hashtag_attempt in range(2):
                raw_hashtags = bot.send_prompt(hashtag_prompt, max_wait=180)
                hashtags = extract_hashtag_line(raw_hashtags)
                if hashtags:
                    break
                print("   >> [주의] 해시태그 응답이 완성되지 않아 다시 요청합니다.")
                hashtag_prompt = f"""
아래 상품과 직접 관련 있는 네이버 블로그 해시태그만 다시 만들어줘.

상품명: {p_name}
메인 키워드: {p_keyword}
사용 상황: {problem_scenario}
사용 장소: {usage_place}
시즌/시기: {season_tag}
핵심 장점: {selling_point_1}, {selling_point_2}, {selling_point_3}
구매 전 주의점: {caution_note}

조건
- 반드시 '#태그' 형식 10~12개
- 한 줄에 공백으로 구분
- 설명, 문장, 생각 과정 출력 금지
- 해시태그 외 다른 텍스트 출력 금지
- 영어 태그 금지
- 첫 태그는 메인 키워드 기반으로 작성
- 두 번째 태그는 상품군 또는 품목명 기반으로 작성
- 상품명, 품목, 사용장소, 사용상황, 구매 전 비교 기준에서만 태그를 뽑기
- 유아용품이면 성분, 소재, 월령, 세척, 보관, 외출준비 중 관련 기준을 포함
- 상품과 무관한 범용 태그 금지
- #일상 #소통 #맞팔 #데일리 #후기 #핫딜 #최저가 #인생템 금지
- 상품과 맞지 않는 #원룸용 #가정용 #사무실용 #생활가전추천 #계절가전 #가격비교 #구성비교 남발 금지
- 상세정보확인 또는 구매전확인 태그 중 1개 포함
"""
            if hashtags:
                blog_content = blog_content + "\n\n[해시태그대기]\n" + hashtags
            else:
                print("   >> [주의] 유효한 해시태그를 받지 못해 해시태그 없이 진행합니다.")
            
            # 3단계: 제목 생성
            print("   >> 📌 제목 생성 중...")
            title_style = random.choice([
                "구매 전 체크형",
                "고민 해결형",
                "비교 기준형",
                "생활 문제 해결형",
                "사용 환경 추천형",
                "주의점 포함형",
                "계절 수요형",
            ])

            title_forbidden_patterns = [
                "써보니 결국 정착한 이유",
                "직접 써보니",
                "왜 다들",
                "알겠더라",
                "인생템",
                "역대급",
                "무조건",
                "최저가",
            ]

            title_prompt = f"""
너는 네이버 검색 유입과 클릭률을 함께 고려하는 블로그 제목 카피라이터다.

아래 본문과 상품 정보를 참고해서 네이버 블로그 제목을 1개만 작성해라.
제목은 광고 제목이 아니라 구매 전에 확인할 기준을 알려주는 정보형 제목이어야 한다.

[상품 정보]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
- 대상 독자: {target_reader}
- 사용 상황: {problem_scenario}
- 사용 장소: {usage_place}
- 시즌/시기: {season_tag}
- 오늘 글 변주: {angle_name}
- 제목 스타일: {title_style}
- 제목 방향 참고: {title_seed}

[본문 일부]
{blog_content[:900]}

[제목 원칙]
- 상품명 전체를 그대로 복사하지 마라.
- '{p_keyword}'는 가능하면 자연스럽게 포함하라.
- 구매 전 확인할 조건이 제목에서 보여야 한다.
- 상품군에 맞는 성분, 소재, 월령, 세척, 보관, 마감, 사용 장소, 후기 확인 기준이 보여야 한다.
- 용량, 색상, 호환, 크기, 소재, 사용 연령, 세척, 착용감, 보관, 배송 조건 중 문맥에 맞는 표현을 활용하라.
- 광고성 제목보다 정보형 제목으로 작성하라.
- 실제 사용한 것처럼 오해될 제목은 피하라.
- "직접 써보니", "내돈내산", "결국 정착", "인생템", "역대급", "무조건", "최저가"는 쓰지 마라.
- 매번 같은 구조가 반복되지 않도록 문장 순서를 변형하라.
- 클릭은 끌되 과장은 하지 마라.

[금지 제목 패턴]
{chr(10).join("- " + item for item in title_forbidden_patterns)}

[가능한 제목 방향 예시]
- {p_keyword} 구매 전 확인할 성분소재관리 기준
- {p_keyword} 찾는다면 아이 생활 기준으로 먼저 볼 점
- {season_tag}에 보기 좋은 {p_keyword} 선택 체크포인트
- {p_name} 구매 전 비교할 현실 조건
- {p_keyword} 고민될 때 먼저 확인할 사용 환경 기준
- 아이에게 닿는 {p_keyword} 고를 때 놓치기 쉬운 기준
- 구매 전 먼저 보는 소재월령세척 기준

[출력 조건]
- 제목 1개만 출력
- 22자 이상 38자 이하
- 따옴표 금지
- 특수기호 남발 금지
- 해시태그 금지
- 설명 금지
- 영어 금지
"""
            title_prompt += "\n\n[언어 규칙]\n- 결과는 반드시 자연스러운 한국어 제목 1개만 출력할 것\n- 영어 단어, 영어 문장, 영어 작업 메모를 절대 출력하지 말 것"

            blog_title = bot.send_prompt(title_prompt, max_wait=180)

            if blog_title:
                blog_title = blog_title.replace('"', '').replace("'", "").strip().split('\n')[0]
            else:
                blog_title = f"{p_keyword} 구매 전 확인할 현실 기준"

            if blog_title and re.search(r"[A-Za-z]{3,}", blog_title):
                blog_title = f"{p_keyword} 구매 전 확인할 현실 기준"
            elif not blog_title:
                blog_title = f"{p_keyword} 구매 전 확인할 현실 기준"

            img_description = f"""
{thumbnail_prompt}

Korean blog thumbnail feeling.
20대 성인 한국인 여성이 {p_name}을 실제로 사용하거나 살펴보며 만족감이 느껴지는 자연스러운 미소를 짓는 장면.
Make the person and product both clearly visible.
Realistic daily-life scene.
Natural lighting.
No text in image.
Not too commercial.
Show a believable problem-solving moment while using {p_name}.
"""
        
        # 4단계: 새 대화 시작 후 이미지 생성 (텍스트 컨텍스트 분리)
        print("   >> 🌐 ChatGPT에서 이미지 생성 시작...")
        bot.new_chat()
        result_path = bot.generate_image(img_description, img_path)
        if not result_path:
            img_path = None
            if post_type in AFFILIATE_POST_TYPES:
                print("   >> [에러] 네이버 쇼핑커넥트 글 이미지를 생성하지 못해 이번 발행은 중단합니다.")
                return None, None, None, "", None
            
        p_name_val = p_name if post_type in AFFILIATE_POST_TYPES else ""
        return blog_title, blog_content, img_path, p_name_val, product_state
    
    except Exception as e:
        print(f"   >> [에러] 콘텐츠 생성 실패: {e}")
        return None, None, None, "", None
    
    finally:
        bot.close()


# =============================================================
# 4. NaverBlogBot - Chrome 프로필 재사용 + 세션 유지 + 텔레그램 알림
# =============================================================
class NaverBlogBot:
    """네이버 블로그 봇 - Chrome 프로필 재사용으로 세션 유지, 캡차 시 텔레그램 알림"""
    
    def __init__(self, naver_id, naver_pw):
        self.v_id = naver_id
        self.v_pw = naver_pw
        
        options = Options()
        naver_profile = resolve_naver_profile_path(naver_id)
        os.makedirs(naver_profile, exist_ok=True)
        options.add_argument(f"--user-data-dir={naver_profile}")
        options.add_argument("--profile-directory=Default")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = create_chrome_driver(options)
        self.driver.maximize_window()
        
        print(f"   >> [안내] 네이버 프로필 경로: {naver_profile}")
        print("   >> 🌐 네이버 로그인 확인 중...")
        self._login()

    def _clear_unexpected_alert(self):
        """예상치 못한 경고창이 떠 있으면 닫고 메시지를 남긴다."""
        try:
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            print(f"   >> [안내] 네이버 알림창 감지: {alert_text}")
            alert.accept()
            time.sleep(1)
            return alert_text
        except:
            return None

    def _safe_current_url(self):
        """경고창 때문에 current_url 조회가 막히지 않도록 처리한다."""
        self._clear_unexpected_alert()
        try:
            return self.driver.current_url
        except:
            self._clear_unexpected_alert()
            time.sleep(1)
            return self.driver.current_url

    def _is_invalid_write_page(self):
        page_source = (self.driver.page_source or "")
        invalid_markers = [
            "삭제된 게시글",
            "존재하지 않는 게시글",
            "비공개 블로그",
            "접근이 제한된 페이지",
        ]
        return any(marker in page_source for marker in invalid_markers)

    def _is_write_page_ready(self):
        current_url = self._safe_current_url()
        if "nid.naver.com" in current_url or "nidlogin" in current_url:
            return False
        if self._is_invalid_write_page():
            return False
        return "blog.naver.com" in current_url
    
    def _login(self):
        """네이버 로그인 (프로필 재사용 → 이미 로그인됐으면 스킵)"""
        self.driver.get(get_naver_write_url(self.v_id))
        time.sleep(3)
        self._clear_unexpected_alert()
        
        # 이미 로그인 상태라면 스킵
        if self._is_write_page_ready():
            print("   >> ✅ 이전 세션 유지 중! 로그인 없이 바로 시작합니다!")
            send_telegram("✅ 네이버 로그인 세션 유지 — 캡차 없이 바로 시작!")
            return

        if self._is_invalid_write_page():
            print("   >> [안내] 삭제된 게시글/비정상 진입 페이지 감지 → 로그인 세션을 새로 잡습니다.")
        
        print("   >> 🔐 로그인이 필요합니다. 로그인을 시도합니다...")
        send_telegram("🔐 네이버 로그인을 시도합니다...")
        
        self.driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)
        
        # ID 입력
        eid = self.driver.find_element(By.NAME, 'id')
        eid.click()
        time.sleep(0.5)
        for char in self.v_id:
            pyperclip.copy(char)
            eid.send_keys(Keys.CONTROL, 'v')
            time.sleep(random.uniform(0.1, 0.35))
        time.sleep(random.uniform(0.5, 1.0))
        
        # 비밀번호 입력
        epwd = self.driver.find_element(By.NAME, 'pw')
        epwd.click()
        time.sleep(0.5)
        for char in self.v_pw:
            pyperclip.copy(char)
            epwd.send_keys(Keys.CONTROL, 'v')
            time.sleep(random.uniform(0.15, 0.5))
        time.sleep(random.uniform(0.5, 1.5))
        
        # 로그인 버튼 클릭
        try:
            keep_checkbox = self.driver.find_element(By.ID, "keep")
            if not keep_checkbox.is_selected():
                keep_label = self.driver.find_element(By.XPATH, '//label[@for="keep"]')
                keep_label.click()
                time.sleep(0.5)
        except:
            pass

        self.driver.find_element(By.XPATH, '//*[@id="log.login"]').click()
        time.sleep(2)
        current_url = self._safe_current_url()
        
        # 캡차 감지 → 텔레그램 알림
        if "nid.naver.com" in current_url:
            print("   >> 🚨 캡차/영수증 인증이 필요합니다!")
            send_telegram("🚨 캡차(영수증) 인증이 필요합니다!\n브라우저에서 직접 인증해주세요.\n⏰ 최대 5분 대기합니다.")
            
            WebDriverWait(self.driver, 300).until(
                lambda d: "nid.naver.com" not in d.current_url
            )
            send_telegram("✅ 캡차 인증 완료! 자동화를 재개합니다.")
        
        print("   >> ✅ 네이버 로그인 완료!")
        time.sleep(2)
    
    def write_post(self, blog_title, blog_content, img_path, post_type='일상', p_name=""):
        """블로그 에디터에 제목/사진/본문 입력 후 발행"""
        driver = self.driver  # 로컬 변수로 참조 (기존 에디터 코드 호환)
        
        try:
            # 블로그 글쓰기 페이지로 이동
            driver.get(get_naver_write_url(self.v_id))
            time.sleep(5)
            
            # 세션 만료 시 자동 재로그인
            if not self._is_write_page_ready():
                print("   >> ⚠️ 세션이 만료되었습니다. 재로그인합니다...")
                send_telegram("⚠️ 네이버 세션 만료! 재로그인을 시도합니다...")
                self._login()
                driver.get(get_naver_write_url(self.v_id))
                time.sleep(5)
            
            actions = ActionChains(driver)
            
            # 스마트 에디터 진입
            wait = WebDriverWait(driver, 10)
            driver.switch_to.frame("mainFrame")
        
            # 팝업 닫기 (작성 중인 글이 있습니다)
            try:
                time.sleep(2)
                cancel_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-popup-button-cancel')
                if cancel_btn.is_displayed():
                    cancel_btn.click()
                    time.sleep(1.5)
            except: pass
            try:
                time.sleep(1)
                help_close_btn = driver.find_element(By.CSS_SELECTOR, 'button.se-help-panel-close-button')
                if help_close_btn.is_displayed():
                    help_close_btn.click()
                    time.sleep(1)
            except: pass
        
            # 제목 입력
            print(f"   >> 제목 입력 중: {blog_title[:30]}...")
            title_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.se-documentTitle")))
            title_field.click()
            time.sleep(1)

            for char in blog_title:
                actions.send_keys(char).perform()
                time.sleep(random.uniform(0.01, 0.05))
            time.sleep(1)
        
            # 본문으로 이동
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(1)
            
            # ── [지침서 1. 에디터 기본 세팅] ──
            print("   >> 기본 문서 서식 적용 중 (가운데 정렬, 마루부리 서체, fs16, #000000)...")
            try:
                driver.find_element(By.CSS_SELECTOR, 'button.se-property-toolbar-drop-down-button[data-name="align-drop-down-with-justify"]').click()
                time.sleep(0.4)
                driver.find_element(By.CSS_SELECTOR, 'button.se-toolbar-option-align-center-button').click()
                time.sleep(0.3)
                driver.find_element(By.CSS_SELECTOR, 'button.se-text-format-toolbar-button').click()
                time.sleep(0.4)
                driver.find_element(By.CSS_SELECTOR, 'button[data-value="text"]').click()
                time.sleep(0.3)
                driver.find_element(By.CSS_SELECTOR, 'button.se-font-family-toolbar-button').click()
                time.sleep(0.4)
                driver.find_element(By.CSS_SELECTOR, 'button[data-value="nanummaruburi"]').click()
                time.sleep(0.3)
                driver.find_element(By.CSS_SELECTOR, 'button.se-font-size-code-toolbar-button').click()
                time.sleep(0.4)
                driver.find_element(By.CSS_SELECTOR, 'button[data-value="fs16"]').click()
                time.sleep(0.3)
                driver.find_element(By.CSS_SELECTOR, 'button.se-font-color-toolbar-button').click()
                time.sleep(0.4)
                driver.find_element(By.CSS_SELECTOR, 'button.se-color-palette[data-color="#000000"]').click()
                time.sleep(0.5)
            except Exception as e:
                print(f"   >> [주의] 기본 서식 초기화 버튼 클릭 실패: {e}")

            def click_ai_utilization_after_image():
                """업로드된 사진 선택 후 'AI 활용' 토글을 최대한 안정적으로 클릭한다."""
                candidate_selectors = [
                    'button.se-set-ai-mark-button-toggle',
                    'button[class*="ai"][class*="toggle"]',
                    'button[class*="Ai"][class*="toggle"]',
                    'button[aria-label*="AI 활용"]',
                    'button[aria-label*="AI"]',
                ]

                for selector in candidate_selectors:
                    try:
                        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                driver.execute_script("arguments[0].click();", button)
                                print(f"   >> 🤖 AI 활용 설정 클릭 완료! ({selector})")
                                time.sleep(1)
                                return True
                    except Exception:
                        pass

                xpath_candidates = [
                    '//button[contains(normalize-space(), "AI 활용")]',
                    '//button[.//span[contains(normalize-space(), "AI 활용")]]',
                    '//button[contains(normalize-space(), "AI")]',
                    '//button[.//span[contains(normalize-space(), "AI")]]',
                ]

                for xpath in xpath_candidates:
                    try:
                        buttons = driver.find_elements(By.XPATH, xpath)
                        for button in buttons:
                            if button.is_displayed() and button.is_enabled():
                                driver.execute_script("arguments[0].click();", button)
                                print(f"   >> 🤖 AI 활용 설정 클릭 완료! ({xpath})")
                                time.sleep(1)
                                return True
                    except Exception:
                        pass

                print("   >> [주의] AI 활용 설정 버튼을 찾지 못했습니다.")
                return False

            def set_image_clipboard(image_path):
                """이미지가 클립보드에 올라간 경우에만 True를 반환한다."""
                safe_img_path = image_path.replace('\\', '/')
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                [System.Windows.Forms.Clipboard]::Clear()
                $img = [System.Drawing.Image]::FromFile("{safe_img_path}")
                try {{
                    [System.Windows.Forms.Clipboard]::SetImage($img)
                    if (-not [System.Windows.Forms.Clipboard]::ContainsImage()) {{
                        throw "Clipboard image was not set"
                    }}
                }} finally {{
                    $img.Dispose()
                }}
                '''
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-STA", "-Command", ps_script],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    error_text = (result.stderr or result.stdout or "").strip()
                    print(f"   >> [주의] 이미지 클립보드 설정 실패: {error_text[:200]}")
                    return False
                return True

            # 사진 업로드 (일상글만 본문 앞에 배치, 상품형 글은 [사진삽입] 위치에서 삽입)
            if post_type not in AFFILIATE_POST_TYPES and img_path and os.path.exists(img_path):
                print("   >> 사진 클립보드 업로드 시도...")
                if set_image_clipboard(img_path):
                    time.sleep(2)

                    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    print("   >> 🎨 사진 업로드 대기 중 (15초)...")
                    time.sleep(15)

                    # 업로드된 사진 클릭
                    try:
                        uploaded_imgs = driver.find_elements(By.CSS_SELECTOR, 'img.se-image-resource')
                        if uploaded_imgs:
                            uploaded_imgs[-1].click()
                            print("   >> 📸 업로드된 사진 클릭 완료!")
                            time.sleep(1)
                    except Exception as e:
                        print(f"   >> [주의] 사진 클릭 실패: {e}")

                    # AI 활용 설정 버튼 클릭
                    click_ai_utilization_after_image()

                    actions.send_keys(Keys.ENTER).perform()
                else:
                    print("   >> [주의] 사진 클립보드 업로드 실패. 프롬프트 텍스트 붙여넣기 방지를 위해 사진 삽입을 건너뜁니다.")
                time.sleep(1)
        
            # ── [안정성 최강 버전] 오토메이션 서식 헬퍼 ──
            editor_state = {
                "font_family": "nanummaruburi",
                "font_color": "#000000",
                "bg_color": "",
                "font_size": "fs16",
                "text_format": "text",
                "align": "center",
                "bold": False,
                "underline": False,
            }
            tracker = {"underline_count": 0}

            def set_font_color(color_hex):
                if editor_state["font_color"] == color_hex: return True
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button.se-font-color-toolbar-button').click()
                    time.sleep(0.4)
                    if color_hex:
                        driver.find_element(By.CSS_SELECTOR, f'button.se-color-palette[data-color="{color_hex}"]').click()
                    else:
                        driver.find_element(By.CSS_SELECTOR, 'button.se-color-palette[data-color="#000000"]').click() # 지침서: #000000 원복
                    time.sleep(0.3)
                    editor_state["font_color"] = color_hex
                    return True
                except: return False
        
            def set_bg_color(color_hex):
                if editor_state["bg_color"] == color_hex: return True
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button.se-background-color-toolbar-button').click()
                    time.sleep(0.4)
                    if color_hex:
                        driver.find_element(By.CSS_SELECTOR, f'button.se-color-palette[data-color="{color_hex}"]').click()
                    else:
                        driver.find_element(By.CSS_SELECTOR, 'button.se-color-palette-no-color').click()
                    time.sleep(0.3)
                    editor_state["bg_color"] = color_hex
                    return True
                except: return False
        
            def set_font_size(size_num):
                if editor_state["font_size"] == f"fs{size_num}": return True
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button.se-font-size-code-toolbar-button').click()
                    time.sleep(0.4)
                    driver.find_element(By.CSS_SELECTOR, f'button[data-value="fs{size_num}"]').click()
                    time.sleep(0.3)
                    editor_state["font_size"] = f"fs{size_num}"
                    return True
                except: 
                    try: driver.find_element(By.CSS_SELECTOR, 'div.se-content').click(); time.sleep(0.3)
                    except: pass
                    return False
        
            def set_text_format(fmt_value): # text(본문), sectionTitle(소제목)
                if editor_state["text_format"] == fmt_value: return True
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button.se-text-format-toolbar-button').click()
                    time.sleep(0.4)
                    driver.find_element(By.CSS_SELECTOR, f'button[data-value="{fmt_value}"]').click()
                    time.sleep(0.3)
                    editor_state["text_format"] = fmt_value
                    # 소제목 등 포맷 변경 시 내부 글자 크기, 색상이 바뀔 수 있으므로 트래킹 업데이트용 플래그
                    editor_state["font_size"] = None
                    editor_state["font_color"] = None
                    editor_state["bg_color"] = None
                    editor_state["bold"] = False
                    return True
                except: return False
        
            def insert_quotation(style=None):
                quote_styles = ['quotation_line', 'quotation_bubble', 'quotation_underline', 'quotation_postit', 'quotation_corner']
                if style is None: style = random.choice(quote_styles)
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button[data-name="quotation"][data-type="icon-select"]').click()
                    time.sleep(0.5)
                    driver.find_element(By.CSS_SELECTOR, f'button[data-value="{style}"]').click()
                    time.sleep(0.5)
                    # 인용구 진입으로 인해 서식 초기화되므로 트래킹 업데이트
                    for k in ["font_size", "font_color", "bg_color", "bold", "underline"]:
                        editor_state[k] = None
                    return True
                except: return False

            def set_bold(activate=None):
                target_state = not bool(editor_state["bold"]) if activate is None else activate
                if editor_state["bold"] is not None and editor_state["bold"] == target_state: return
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button[data-name="bold"]').click()
                    time.sleep(0.1)
                except:
                    actions.key_down(Keys.CONTROL).send_keys('b').key_up(Keys.CONTROL).perform()
                    time.sleep(0.1)
                editor_state["bold"] = target_state
        
            def set_underline(activate=None):
                target_state = not bool(editor_state["underline"]) if activate is None else activate
                if target_state == True and not editor_state["underline"]:
                    if tracker["underline_count"] >= 3:
                        return # 3회 초과 시 발동 중지 (지침서 엄수)
                    tracker["underline_count"] += 1
                if editor_state["underline"] is not None and editor_state["underline"] == target_state: return
                try:
                    driver.find_element(By.CSS_SELECTOR, 'button[data-name="underline"]').click()
                    time.sleep(0.1)
                except:
                    actions.key_down(Keys.CONTROL).send_keys('u').key_up(Keys.CONTROL).perform()
                    time.sleep(0.1)
                editor_state["underline"] = target_state
        
            def force_sync_state():
                for k in ["font_size", "font_color", "bg_color", "text_format", "bold", "underline"]:
                    editor_state[k] = None

            def reset_formatting():
                set_bold(False)
                set_underline(False)
                set_font_color("#000000")
                set_bg_color("")
                set_font_size("16")
                set_text_format("text")
                time.sleep(0.2)

            def exit_quotation_to_plain_text():
                """인용구 다음 줄이 링크/해시태그를 삼키지 않도록 일반 본문 위치로 복귀한다."""
                for _ in range(3):
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.15)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.25)
                force_sync_state()
                reset_formatting()

            def type_line(text):
                for char in text:
                    actions.send_keys(char).perform()
                    time.sleep(random.uniform(0.005, 0.02))

            def type_formatted_line(text):
                """지침서: 상품명(p_name) 등장 시 무조건 19px + 굵기 처리 후 원상복구"""
                if not p_name or p_name not in text:
                    type_line(text)
                    return
                parts = text.split(p_name)
                for i, part in enumerate(parts):
                    if part:
                        type_line(part)
                    if i < len(parts) - 1:
                        # 상품명 강조!
                        set_font_size("19")
                        set_bold(True)
                        type_line(p_name)
                        set_bold(False)
                    # 복구
                        set_font_size("16")

            def clean_marker_text(text, *markers):
                cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff\xa0]", "", str(text or ""))
                for marker in markers:
                    cleaned = cleaned.replace(marker, "")
                cleaned = re.sub(r"\s+", " ", cleaned).strip().strip('"').strip("'").strip("“”‘’").strip()
                placeholder_values = {
                    "문장",
                    "문장내용",
                    "내용",
                    "핵심문장",
                    "인용구",
                    "quote",
                    "text",
                    "제품보다 먼저 봐야 할 건 우리 집에서 문제가 생기는 이유였습니다",
                    "원인을 나눠보고 나면 상세정보에서 확인할 부분도 훨씬 또렷해집니다",
                }
                if cleaned.lower() in placeholder_values:
                    return ""
                return cleaned

            def is_valid_quote_text(text):
                cleaned = clean_marker_text(text)
                compact = re.sub(r"\s+", "", cleaned)
                return len(compact) >= 12

            # ── 본문 타이핑 및 파싱 루프 ──
            print("   >> 지침서 반영 본문 타이핑 (상품강조, 목록구조 엄격 적용)...")
            bold_triggers = ['쇼핑커넥트', '구매 링크', '제품 상세정보', '───']
            section_emojis = ['✨', '📌', '👍', '💡', '⭐', '🛒']
            cta_triggers = ['바로가기', '쇼핑커넥트링크', '상세정보', '구매 링크']

            in_list_mode = False

            for line in blog_content.split('\n'):
                line_s = line.strip()
                if not line_s:
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.1)
                    continue

                # ==========================
                # 1. 특수 마커 단독 행동
                # ==========================
                if '[사진삽입]' in line_s and post_type in AFFILIATE_POST_TYPES:
                    if img_path and os.path.exists(img_path):
                        print("   >> 📸 본문 중간(문제 심화 뒤)에 사진 삽입 중...")
                        if set_image_clipboard(img_path):
                            time.sleep(2)
                            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                            print("   >> 🎨 사진 업로드 대기 중 (15초)...")
                            time.sleep(15)
                            try:
                                uploaded_imgs = driver.find_elements(By.CSS_SELECTOR, 'img.se-image-resource')
                                if uploaded_imgs:
                                    uploaded_imgs[-1].click()
                                    print("   >> 📸 업로드된 사진 클릭 완료!")
                                    time.sleep(1)
                            except Exception as e:
                                print(f"   >> [주의] 사진 클릭 실패: {e}")
                            click_ai_utilization_after_image()
                            actions.send_keys(Keys.ENTER).perform()
                            time.sleep(1)
                        else:
                            print("   >> [주의] 사진 클립보드 업로드 실패. 프롬프트 텍스트 붙여넣기 방지를 위해 사진 삽입을 건너뜁니다.")
                    else:
                        print("   >> [주의] [사진삽입] 위치가 있었지만 업로드할 이미지 파일이 없습니다.")
                    continue

                if line_s == '[구분선]':
                    try:
                        hr_btn = driver.find_element(By.CSS_SELECTOR, 'button[data-name="horizontal-line"]')
                        hr_btn.click()
                        time.sleep(0.5)
                        driver.find_element(By.CSS_SELECTOR, f'button[data-value="default"]').click()
                        time.sleep(0.5)
                    except:
                        for ch in '─' * 30:
                            actions.send_keys(ch).perform()
                            time.sleep(0.005)
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(0.3)
                    continue

                if line_s.startswith('[해시태그대기]'):
                    exit_quotation_to_plain_text()
                    time.sleep(7)
                    continue

                # ==========================
                # 2. 지침서 적용 심층 로직
                # ==========================
                is_quote = line_s.startswith('[인용구]') and '[/인용구]' in line_s
                is_list_topic = line_s.startswith('[목록주제]')
                is_list_end = line_s.startswith('[목록끝]')

                # 📌 구조 ①: 목록 주제 + 기호목록
                if is_list_topic:
                    topic_text = clean_marker_text(line_s, '[목록주제]', '[/목록주제]')
                    if not topic_text:
                        print("   >> [주의] 비어 있는 목록 주제는 건너뜁니다.")
                        continue
                    actions.send_keys(Keys.ENTER).perform() # 엔터
                    time.sleep(0.2) # 한 줄 띄움 (스마트 에디터 기본 간격)
                    quote_inserted = insert_quotation("quotation_underline") # 인용구(라인/따옴표)
                    set_font_size("16")
                    set_bold(True)
                    type_formatted_line(topic_text)
                    set_bold(False)
                    if quote_inserted:
                        exit_quotation_to_plain_text()
                    else:
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(0.2)
                        force_sync_state()
                        reset_formatting()
                    # 기호 목록 진입
                    try:
                        driver.find_element(By.CSS_SELECTOR, 'button[data-name="list"][data-type="drop-down"]').click()
                        time.sleep(0.4)
                        driver.find_element(By.CSS_SELECTOR, 'button[data-value="bullet"]').click()
                        time.sleep(0.4)
                        in_list_mode = True
                    except: pass
                    continue
                
                if is_list_end:
                    if in_list_mode:
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(0.2)
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(0.2)
                        in_list_mode = False
                        force_sync_state()
                        reset_formatting()
                    continue

                # 📌 구조 ②: 일반 인용구 탈출 (지침서 지정순서)
                if is_quote:
                    quote_text = clean_marker_text(line_s, '[인용구]', '[/인용구]')
                    if not is_valid_quote_text(quote_text):
                        print("   >> [주의] 비어 있거나 너무 짧은 인용구는 건너뜁니다.")
                        continue
                    quote_inserted = insert_quotation()
                    set_font_color("#0095e9")
                    set_bold(True)
                    type_formatted_line(quote_text)
                    set_bold(False)
                    set_font_color("#000000")
                    if quote_inserted:
                        exit_quotation_to_plain_text()
                    else:
                        actions.send_keys(Keys.ENTER).perform()
                        time.sleep(0.2)
                        force_sync_state()
                        reset_formatting()
                    continue

                # 📌 구조 ③: 번호 + 큰 글씨 (소제목) 
                is_section_title = any(line_s.startswith(e) for e in section_emojis) or \
                                   (line_s and line_s[0] in '①②③④⑤⑥⑦⑧⑨⑩') or \
                                   (len(line_s)>2 and line_s[0].isdigit() and line_s[1] == '.')
                
                is_disclaimer = '쇼핑커넥트 활동의 일환' in line_s or '수수료를 제공받습니다' in line_s
                is_cta = any(kw in line_s for kw in cta_triggers) and not in_list_mode
                is_url_line = line_s.startswith('http://') or line_s.startswith('https://')
                is_bold_trigger = any(kw in line_s for kw in bold_triggers) and not in_list_mode
                highlight_keywords = ['장점', '단점', '추천', '결론', '총평', '팁']
                is_highlight = any(kw in line_s for kw in highlight_keywords) and len(line_s) < 30 and not in_list_mode

                if is_section_title and not in_list_mode:
                    set_text_format("sectionTitle")
                    time.sleep(0.3)
                    set_font_color("#0078cb")
                    set_bold(True)
                    type_formatted_line(line_s)
                    set_bold(False)
                    set_font_color("#000000")
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.3)
                    # ★ 지침서 규칙: "다음 줄에서 본문 변경. 같은 줄 변경 금지"
                    set_text_format("text")
                    set_font_size("16")
                    continue
                
                if is_disclaimer:
                    # 지침서: 수익 고지는 별도 사이즈 꼬임 없이 일반 타이핑으로 기본(16) 유지!
                    type_line(line_s)
                elif is_highlight:
                    set_font_size("16")
                    set_font_color("#333333")
                    set_bg_color("#e3fdc8")
                    set_bold(True)
                    type_formatted_line(line_s)
                    set_bold(False)
                    set_bg_color("")
                    set_font_color("#000000")
                    set_font_size("16")
                elif is_cta:
                    set_bg_color("#c2f4db")
                    set_font_color("#00a84b")
                    set_font_size("16")
                    set_bold(True)
                    set_underline(True) # 내부적으로 3회 제한 확인
                    type_formatted_line(line_s)
                    set_underline(False)
                    set_bold(False)
                    set_font_color("#000000")
                    set_bg_color("")
                elif is_url_line:
                    exit_quotation_to_plain_text()
                    type_line(line_s)
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(1)
                    print("   >> 🔗 링크 프리뷰 이미지 로딩 대기 중 (최대 15초)...")
                    for wait_i in range(15):
                        try:
                            oglink = driver.find_elements(By.CSS_SELECTOR, 'div.se-oglink-thumbnail, div.se-module-oglink, div.se-oglink')
                            if oglink:
                                print("   >> ✅ 링크 프리뷰 로딩 완료!")
                                time.sleep(2)
                                break
                        except: pass
                        time.sleep(1)
                    continue
                elif is_bold_trigger:
                    set_font_size("16")
                    set_bold(True)
                    type_formatted_line(line_s)
                    set_bold(False)
                else:
                    if in_list_mode and line_s.startswith("-"):
                        # 리스트 모드일 때는 마크다운 대시 지우기 (불릿이 띄워져있으므로)
                        line_s = line_s.lstrip("-").strip()
                    type_formatted_line(line_s)

                actions.send_keys(Keys.ENTER).perform()
                time.sleep(random.uniform(0.1, 0.3))
        
            time.sleep(2)
            print("   >> 모든 컨텐츠 입력 완료!")
        
            # 발행
            print("   >> 1차 발행 버튼 클릭...")
            first_publish_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[class*='publish_btn'], button[data-click-area='tpb.publish']")
            ))
            first_publish_btn.click()
            time.sleep(3)
        
            print("   >> 최종 발행 버튼 클릭...")
            final_publish_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[class*='confirm_btn'], button[data-testid='seOnePublishBtn']")
            ))
            final_publish_btn.click()
            print("   >> 🚀 발행 완료!")
            time.sleep(7)
        
            return True
        
        except Exception as e:
            print(f"   >> [에러] 포스팅 실패: {e}")
            return False
        
        finally:
            # 메인 프레임으로 복귀 (브라우저는 닫지 않음 → 다음 글에서 재사용!)
            try:
                driver.switch_to.default_content()
            except: pass
            # 임시 이미지 삭제
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except: pass

    def close(self):
        """브라우저 닫기"""
        try:
            self.driver.quit()
        except: pass


# =============================================================
# 5. 하나의 글 발행 통합 함수
# =============================================================
def publish_one_post(post_type):
    """post_type: '일상', '네이버' 또는 '쿠팡'(호환) — 전역 naver_bot 사용 (클립보드 충돌 방지 락 포함)"""
    global naver_bot
    # 클립보드 충돌 방지: 다른 자동화 스크립트 완료까지 대기 (최대 30분)
    _lock = FileLock(AUTOMATION_LOCK_PATH, timeout=1800)
    print(f"[Lock] 다른 자동화 작업 확인 중...")
    print(f"[Lock] 전역 락 파일: {AUTOMATION_LOCK_PATH}")
    _lock.acquire()
    print(f"[Lock] 락 획득 완료 — '{post_type}' 작업을 시작합니다.")
    try:
        _publish_one_post_inner(post_type)
    finally:
        _lock.release()
        print(f"[Lock] 락 해제 완료")

def _publish_one_post_inner(post_type):
    global naver_bot
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"📝 [{now}] '{post_type}' 글 발행을 시작합니다!")
    print(f"{'='*60}")
    send_telegram(f"📝 [{now}] '{post_type}' 글 발행을 시작합니다!")
    
    try:
        # 1단계: 콘텐츠 생성
        print("   >> 🤖 ChatGPT 네이버 전용 프로젝트에서 콘텐츠를 생성 중...")
        result_tuple = generate_content(post_type)
        if result_tuple[0] is None:
            print("   >> [에러] 콘텐츠 생성 실패. 스킵합니다.")
            daily_stats["에러"] += 1
            send_telegram(f"❌ [{post_type}] 콘텐츠 생성 실패!")
            return
            
        blog_title, blog_content, img_path, p_name, product_state = result_tuple
        
        print(f"   >> 제목: {blog_title[:40]}...")
        print(f"   >> 본문: {len(blog_content)}자")
        
        # 2단계: 네이버 블로그 발행 (기존 브라우저 세션 재사용!)
        success = naver_bot.write_post(blog_title, blog_content, img_path, post_type, p_name)
        
        if success:
            daily_stats[post_type] += 1
            if post_type in AFFILIATE_POST_TYPES and product_state:
                mark_coupang_product_as_used(csv_file_path, product_state, blog_title)
            msg = f"✅ [{post_type}] 발행 성공! 제목: {blog_title[:30]}...\n(오늘: 일상 {daily_stats['일상']}건, 네이버 {daily_stats['네이버']}건, 쿠팡호환 {daily_stats['쿠팡']}건)"
            print(f"   >> {msg}")
            send_telegram(msg)
        else:
            daily_stats["에러"] += 1
            msg = f"❌ [{post_type}] 발행 실패 (에러 {daily_stats['에러']}건)"
            print(f"   >> {msg}")
            send_telegram(msg)
            
    except Exception as e:
        daily_stats["에러"] += 1
        msg = f"🚨 [{post_type}] 치명적 에러: {e}"
        print(f"   >> {msg}")
        send_telegram(msg)


# =============================================================
# 6. 랜덤 스케줄 생성 (하루 10건: 일상 5 + 네이버 쇼핑커넥트 5)
# =============================================================
def generate_daily_schedule():
    """
    하루 24시간을 10개의 랜덤 시간으로 나누고,
    일상 5건 + 네이버 쇼핑커넥트 5건을 랜덤으로 섞어 배치
    """
    # 기존 스케줄 전부 제거
    schedule.clear()
    
    # 오늘 통계 초기화
    daily_stats["일상"] = 0
    daily_stats["네이버"] = 0
    daily_stats["쿠팡"] = 0
    daily_stats["에러"] = 0
    
    # 00:30 ~ 23:30 사이에서 랜덤 10개 시각 생성 (최소 30분 간격)
    random_minutes = sorted(random.sample(range(30, 1410, 15), 10))  # 15분 단위 중 10개 선택
    
    # 글 종류 배정: 일상 5 + 네이버 쇼핑커넥트 5 → 섞기
    post_types = ['일상'] * 5 + ['네이버'] * 5
    random.shuffle(post_types)
    
    print(f"\n{'='*60}")
    print(f"📅 [{datetime.now().strftime('%Y-%m-%d')}] 오늘의 발행 스케줄")
    print(f"{'='*60}")
    
    for i, (minutes, p_type) in enumerate(zip(random_minutes, post_types), 1):
        hour = minutes // 60
        minute = minutes % 60
        time_str = f"{hour:02d}:{minute:02d}"
        
        # 스케줄 등록
        schedule.every().day.at(time_str).do(publish_one_post, post_type=p_type)
        
        emoji = "🌸" if p_type == "일상" else "🛍️"
        print(f"   {i:2d}. {time_str}  →  {emoji} {p_type}")
    
    # 매일 자정에 다시 스케줄 재생성 (다음날 새 랜덤 시간)
    schedule.every().day.at("00:01").do(generate_daily_schedule)
    
    print(f"\n>> ✅ 스케줄 등록 완료! 첫 발행까지 대기 중...\n")


# =============================================================
# 7. 메인 실행
# =============================================================
naver_bot = None  # 전역 네이버 봇 인스턴스

if __name__ == "__main__":
    args = parse_args()
    if args.chatgpt_login:
        save_chatgpt_login_session()
        sys.exit(0)
    if args.naver_login:
        naver_login_id = (
            args.naver_id
            or os.getenv("NAVER_CONNECT_NAVER_ID", "")
            or os.getenv("NAVER_CONNECT_ID", "")
            or DEFAULT_NAVER_CONNECT_ID
        ).strip()
        save_naver_login_session(naver_login_id)
        sys.exit(0)

    scheduled_log_file = None
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    if args.scheduled:
        scheduled_log_file = enable_scheduled_logging(args.post_type or "scheduled")
    settings = load_runtime_settings(args)
    v_id = settings["naver_id"]
    v_passwd = settings["naver_password"]
    csv_file_path = settings["csv_file_path"]
    validate_runtime_requirements(csv_file_path)
    
    # ★ 네이버 봇 초기화 (Chrome 프로필 재사용 → 로그인 1회만!)
    print("🚀 네이버 블로그 봇을 초기화합니다...\n")
    naver_bot = NaverBlogBot(v_id, v_passwd)
    send_telegram("🚀 블로그 자동화 프로그램이 시작되었습니다!")
    
    try:
        selected_post_type = args.post_type
        if not selected_post_type:
            selected_post_type = input("📝 발행할 글 종류를 입력하세요 (일상/네이버, 엔터 시 네이버): ").strip() or "네이버"
        if selected_post_type not in ("일상", "네이버", "쿠팡"):
            raise RuntimeError("글 종류는 '일상', '네이버', '쿠팡'만 사용할 수 있습니다.")

        print(f"\n🚀 [1회 실행] '{selected_post_type}' 글 1건 발행을 시작합니다.\n")
        publish_one_post(selected_post_type)
    
    except KeyboardInterrupt:
        print(f"\n\n🛑 프로그램을 수동 종료합니다.")
        send_telegram(f"🛑 프로그램 수동 종료\n오늘 결과: 일상 {daily_stats['일상']}건, 네이버 {daily_stats['네이버']}건, 쿠팡호환 {daily_stats['쿠팡']}건, 에러 {daily_stats['에러']}건")
    
    except Exception as e:
        print(f"\n\n🚨 치명적 에러: {e}")
        send_telegram(f"🚨 치명적 에러로 프로그램 종료!\n에러: {e}")
    
    finally:
        if naver_bot:
            naver_bot.close()
        print(f"   오늘 결과: 일상 {daily_stats['일상']}건, 네이버 {daily_stats['네이버']}건, 쿠팡호환 {daily_stats['쿠팡']}건, 에러 {daily_stats['에러']}건")
        if scheduled_log_file:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            scheduled_log_file.close()
