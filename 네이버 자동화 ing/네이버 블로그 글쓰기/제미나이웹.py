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
print(" 네이버 블로그 자동 글쓰기 (Gemini 웹 전용 - 세션 유지 + 텔레그램 알림)")
print("=" * 80)
print("\n")


def resolve_default_csv_path():
    """환경변수 또는 자주 쓰는 위치에서 CSV 기본 경로를 찾는다."""
    candidates = [
        os.getenv("COUPANG_CSV_PATH", "").strip(),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "skssj2627_db.csv"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return candidates[1]


def get_installed_chrome_major_version():
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for chrome_path in chrome_paths:
        if not os.path.exists(chrome_path):
            continue
        try:
            safe_path = chrome_path.replace("'", "''")
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-Item -LiteralPath '{safe_path}').VersionInfo.ProductVersion"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            match = re.search(r"(\d+)\.", completed.stdout or "")
            if match:
                return match.group(1)
        except Exception:
            continue
    return None


def get_chromedriver_major_version(chromedriver_path):
    try:
        completed = subprocess.run(
            [chromedriver_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        match = re.search(r"ChromeDriver\s+(\d+)\.", completed.stdout or "")
        if match:
            return match.group(1)
    except Exception:
        return None
    return None


def is_chromedriver_compatible(chromedriver_path):
    chrome_major = get_installed_chrome_major_version()
    driver_major = get_chromedriver_major_version(chromedriver_path)
    if not chrome_major or not driver_major:
        return True
    if chrome_major != driver_major:
        print(
            "   >> [주의] ChromeDriver 버전 불일치로 건너뜁니다: "
            f"Chrome {chrome_major}, Driver {driver_major}, {chromedriver_path}"
        )
        return False
    return True


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
        if is_chromedriver_compatible(chromedriver_path):
            return webdriver.Chrome(service=Service(chromedriver_path), options=options)

    candidate_paths = [
        os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver", "win64", "148.0.7778.167", "chromedriver-win32", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "147.0.7727.117", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "147.0.7727.56", "chromedriver.exe"),
        r"C:\py_temp\chromedriver.exe",
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "146.0.7680.165", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".cache", "selenium", "chromedriver", "win64", "145.0.7632.117", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver", "win64", "146.0.7680.165", "chromedriver-win32", "chromedriver.exe"),
        os.path.join(os.path.expanduser("~"), "workspace", "chromedriver", "chromedriver-win64", "chromedriver.exe"),
    ]
    for candidate_path in candidate_paths:
        if os.path.exists(candidate_path) and is_chromedriver_compatible(candidate_path):
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
        raise FileNotFoundError("쿠팡 상품 CSV 경로가 비어 있습니다.")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"쿠팡 상품 CSV 파일을 찾을 수 없습니다: {csv_path}")


def sanitize_profile_name(name):
    """프로필 폴더명으로 쓸 수 있게 영문/숫자/일부 기호만 남긴다."""
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name.strip())
    return safe_name or "default"


def resolve_naver_profile_path(naver_id):
    env_profile_path = os.getenv("NAVER_PROFILE_PATH", "").strip()
    if env_profile_path:
        return env_profile_path

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
    return f"https://blog.naver.com/{naver_id}?Redirect=Write"


def parse_args():
    parser = argparse.ArgumentParser(description="네이버 블로그 자동 글쓰기")
    parser.add_argument("--post-type", choices=["일상", "쿠팡"], help="한 번 실행 시 발행할 글 종류")
    parser.add_argument("--naver-id", help="네이버 로그인 ID")
    parser.add_argument("--naver-password", help="네이버 로그인 비밀번호")
    parser.add_argument("--csv-path", help="쿠팡 상품 CSV 경로")
    parser.add_argument("--scheduled", action="store_true", help="작업 스케줄러 등 비대화형 실행 모드")
    return parser.parse_args()


def load_runtime_settings(args):
    """환경변수/인자/대화형 입력 순서로 실행 설정을 결정한다."""
    settings = {
        "naver_id": (args.naver_id or os.getenv("NAVER_ID", "")).strip(),
        "naver_password": (args.naver_password or os.getenv("NAVER_PASSWORD", "")).strip(),
        "csv_file_path": (args.csv_path or os.getenv("COUPANG_CSV_PATH", "")).strip(),
    }

    if not settings["csv_file_path"]:
        settings["csv_file_path"] = resolve_default_csv_path()

    if args.scheduled:
        missing = [key for key in ("naver_id", "naver_password") if not settings[key]]
        if missing:
            raise RuntimeError(
                "비대화형 실행에는 NAVER_ID, NAVER_PASSWORD 환경변수 또는 동등한 명시 인자가 필요합니다."
            )
        return settings

    if not settings["naver_id"]:
        settings["naver_id"] = input("🔑 네이버 로그인 ID를 입력하세요: ").strip()
    if not settings["naver_password"]:
        settings["naver_password"] = input("🔑 네이버 로그인 비밀번호를 입력하세요: ").strip()
    if not args.csv_path and not os.getenv("COUPANG_CSV_PATH", ""):
        entered_csv_path = input("📂 쿠팡 상품 CSV 경로 (엔터 시 기본값): ").strip()
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
daily_stats = {"일상": 0, "쿠팡": 0, "에러": 0}
KOREAN_WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

SEASONAL_TOPIC_BANK = {
    "봄": [
        "이사 전 월세 계약서 확인 순서",
        "전입신고와 확정일자를 챙기는 순서",
        "인터넷 이전 설치 전에 확인할 조건",
        "입주 청소 예약 전 확인할 범위",
        "관리비와 공과금 정산을 나눠보는 기준",
    ],
    "여름": [
        "전기요금 자동이체 변경 전 확인할 것",
        "관리비 고지서에서 사용량 항목 보는 법",
        "이사 후 공과금 정산을 확인하는 순서",
        "알뜰폰 요금제 변경 전 확인할 사용량",
        "통신비와 구독료를 같이 점검하는 방법",
    ],
    "가을": [
        "월세 계약 갱신 전 특약 다시 보기",
        "관리비가 오른 달 고지서 항목 나누기",
        "인터넷 약정 만료 전에 비교할 기준",
        "알뜰폰 요금제 변경 전 확인할 사용량",
        "이사 후 주소 변경과 공과금 정산 순서",
    ],
    "겨울": [
        "난방비와 관리비 고지서를 같이 보는 법",
        "전기요금 자동이체 변경 전 확인할 것",
        "인터넷 약정 만료 전에 볼 위약금 조건",
        "이사 전 공과금 자동이체 정리 순서",
        "월세 계약 갱신 전 특약 다시 보기",
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
    "생활비를 줄이기 전에 약정과 고정지출을 먼저 확인하려는 흐름",
    "월세 계약과 이사 준비에서 서류 순서를 검색하는 관심",
    "통신 약정과 알뜰폰 요금제를 바꾸기 전에 조건을 비교하는 소비 습관",
    "이사 전후 공과금과 자동이체를 먼저 정리하려는 흐름",
    "월세 계약 특약과 관리비 항목을 따로 확인하는 생활 패턴",
    "관리비와 공과금 고지서를 그냥 넘기지 않고 항목별로 보는 습관",
    "추천보다 계약서와 공식 안내에서 확인할 기준을 먼저 찾는 검색 습관",
    "한 번 결정하면 오래 가는 지출을 체크리스트로 정리하려는 흐름",
]

DAILY_SCENE_BANK = [
    "계약서나 고지서를 열어두고 체크할 항목을 메모하는 순간",
    "이사 날짜를 달력에 표시해두고 서류 순서를 다시 보는 상황",
    "통신비와 구독료가 빠져나간 내역을 확인하다가 멈춘 장면",
    "이사 전 주소 변경과 자동이체 목록을 따로 적는 장면",
    "인터넷 약정 종료일과 위약금 항목을 확인하는 상황",
    "월세 계약서 특약과 관리비 항목을 다시 읽어보는 장면",
    "관리비 고지서를 보다가 낯선 항목을 다시 확인한 순간",
]

PHOTO_STYLE_BANK = [
    "20대 성인 한국인 여성이 노트북과 서류를 보며 체크리스트를 정리하는 현실적인 사진",
    "20대 성인 한국인 여성이 스마트폰 청구서와 메모장을 함께 확인하는 자연광 실내 사진",
    "20대 성인 한국인 여성이 계약서, 달력, 펜을 놓고 생활비를 점검하는 블로그용 생활 정보 사진",
    "20대 성인 한국인 여성이 책상 앞에서 공식 안내와 메모를 대조하는 차분한 실내 사진",
]

DAILY_CATEGORY_BANK = [
    "월세계약",
    "이사입주",
    "인터넷통신",
    "생활비공과금",
]

DAILY_SEARCH_INTENT_BANK = {
    "월세계약": [
        {
            "search_phrase": "월세 계약 전 확인할 것",
            "reader_problem": "월세집을 계약하려는데 보증금, 관리비, 특약, 등기부등본을 어디부터 봐야 할지 헷갈리는 상황",
            "reader_promise": "계약서, 등기부등본, 관리비, 특약, 입금 계좌를 계약 전 확인 순서로 정리",
            "practical_points": ["등기부등본의 주소와 소유자 정보를 계약서와 맞춰보기", "보증금과 월세 외 관리비 포함 항목을 따로 확인하기", "특약에 수리, 원상복구, 반려동물, 주차 조건이 있는지 보기", "계약금 입금 전 계좌 명의와 계약 당사자를 다시 대조하기"],
            "mistakes_to_avoid": ["방이 마음에 든다는 이유로 계약서 세부 항목을 급하게 넘기기", "관리비 포함 항목을 말로만 듣고 기록하지 않기"],
            "faq_questions": ["월세 계약 전에 등기부등본은 왜 봐야 할까?", "관리비는 어떤 항목까지 확인해야 할까?"],
            "related_keywords": ["월세 계약", "등기부등본", "관리비", "특약", "보증금"],
            "image_scene": "책상 위에 계약서와 체크리스트, 펜이 놓인 현실적인 실내 장면",
        },
        {
            "search_phrase": "전입신고 확정일자 차이",
            "reader_problem": "이사 후 전입신고와 확정일자를 언제 어떻게 챙겨야 하는지 순서가 헷갈리는 상황",
            "reader_promise": "전입신고, 확정일자, 임대차계약서, 보증금 보호 관점의 확인 순서를 정리",
            "practical_points": ["이사 날짜와 실제 거주 시작일을 기준으로 처리 순서 잡기", "임대차계약서 원본과 주소 표기를 다시 확인하기", "전입신고와 확정일자는 공식 안내에서 처리 방법을 확인하기", "보증금 관련 판단은 계약서와 공적 서류를 함께 보기"],
            "mistakes_to_avoid": ["전입신고와 확정일자를 같은 말처럼 이해하기", "주소의 동호수 표기를 대충 보고 넘기기"],
            "faq_questions": ["전입신고와 확정일자는 무엇이 다를까?", "이사 당일 무엇부터 챙겨야 할까?"],
            "related_keywords": ["전입신고", "확정일자", "임대차계약서", "보증금", "이사"],
            "image_scene": "달력과 임대차계약서, 스마트폰 화면을 보며 이사 서류를 확인하는 장면",
        },
    ],
    "이사입주": [
        {
            "search_phrase": "이사 전 체크리스트",
            "reader_problem": "이사 날짜는 잡혔는데 전입신고, 공과금, 인터넷 이전, 입주 청소 순서가 뒤섞이는 상황",
            "reader_promise": "이사 전후로 나눠 주소 변경, 요금 정산, 인터넷 이전, 입주 점검 순서를 정리",
            "practical_points": ["이사 전에는 현재 집 관리비와 공과금 정산 일정을 확인하기", "새집 주소 변경이 필요한 서비스 목록을 따로 적기", "인터넷 이전 설치 가능 날짜를 이사일보다 먼저 확인하기", "입주 당일에는 계량기, 벽지, 수도, 전기 상태를 사진으로 남기기"],
            "mistakes_to_avoid": ["이사 업체 예약만 끝내고 주소 변경을 미루기", "입주 하자를 확인하지 않고 짐부터 전부 들이기"],
            "faq_questions": ["이사 전에 주소 변경은 어디까지 해야 할까?", "입주 당일 사진은 왜 남기는 게 좋을까?"],
            "related_keywords": ["이사 체크리스트", "주소 변경", "공과금 정산", "인터넷 이전", "입주 점검"],
            "image_scene": "이사 체크리스트와 박스, 달력이 놓인 밝은 실내 장면",
        },
        {
            "search_phrase": "입주 청소 전 확인할 것",
            "reader_problem": "입주 청소를 예약하려는데 범위, 추가 비용, 하자 확인을 어디까지 봐야 할지 모르는 상황",
            "reader_promise": "청소 범위, 옵션, 현장 확인, 입주 하자 기록을 나눠 예약 전 확인 기준을 정리",
            "practical_points": ["기본 청소 범위와 추가 옵션을 업체 안내에서 나눠 보기", "창틀, 배수구, 후드, 욕실 실리콘처럼 확인할 위치를 적어두기", "청소 전 하자와 오염을 사진으로 구분해두기", "예약 변경, 취소, 추가 요금 조건을 공식 안내에서 확인하기"],
            "mistakes_to_avoid": ["가격만 보고 청소 범위를 확인하지 않기", "청소 후 발견한 하자를 청소 문제로만 생각하기"],
            "faq_questions": ["입주 청소 범위는 어디까지 확인해야 할까?", "청소 전후 사진은 어떤 부분을 찍어야 할까?"],
            "related_keywords": ["입주 청소", "이사 준비", "청소 범위", "추가 비용", "하자 확인"],
            "image_scene": "빈 방 한쪽에 청소 체크리스트와 휴대폰이 놓인 입주 전 실내 장면",
        },
    ],
    "인터넷통신": [
        {
            "search_phrase": "인터넷 약정 만료 전 확인",
            "reader_problem": "인터넷 약정이 끝나가는데 재약정, 이전 설치, 위약금, 결합 할인을 어떻게 비교해야 할지 모르는 상황",
            "reader_promise": "약정 기간, 위약금, 결합 상품, 설치 주소, 사은 조건을 공식 안내 기준으로 확인하는 순서 정리",
            "practical_points": ["현재 약정 종료일과 남은 기간을 고객센터나 앱에서 확인하기", "이전 설치가 필요한 주소와 설치 가능 여부를 먼저 보기", "결합 할인은 휴대폰, TV, 인터넷을 분리해서 비교하기", "재약정 혜택은 구두 안내보다 문자나 공식 화면으로 남기기"],
            "mistakes_to_avoid": ["월요금만 보고 약정 기간과 위약금을 빼먹기", "사은 조건만 보고 실제 설치 가능 여부를 늦게 확인하기"],
            "faq_questions": ["인터넷 약정 만료 전에는 무엇부터 확인해야 할까?", "재약정과 신규 가입은 어떤 기준으로 봐야 할까?"],
            "related_keywords": ["인터넷 약정", "재약정", "위약금", "결합 할인", "이전 설치"],
            "image_scene": "노트북 옆에 공유기와 통신비 메모가 놓인 책상 장면",
        },
        {
            "search_phrase": "알뜰폰 요금제 바꾸기 전 체크",
            "reader_problem": "알뜰폰 요금제가 저렴해 보여도 데이터, 통화, 유심, 결합 조건을 어떻게 봐야 할지 헷갈리는 상황",
            "reader_promise": "월 사용량, 데이터 속도, 통화량, 유심 배송, 기존 결합 해지 영향을 나눠 정리",
            "practical_points": ["최근 몇 달 데이터와 통화 사용량을 먼저 확인하기", "기본 데이터 소진 뒤 속도 제한 조건을 살펴보기", "유심 배송, 개통 가능 시간, 번호 이동 절차를 확인하기", "기존 통신사 결합 할인이나 약정 영향이 있는지 따로 보기"],
            "mistakes_to_avoid": ["최저 월요금만 보고 실제 사용량을 무시하기", "번호 이동 전 기존 약정과 결합 상태를 확인하지 않기"],
            "faq_questions": ["알뜰폰은 데이터 속도를 어떻게 봐야 할까?", "번호 이동 전에 어떤 조건을 확인해야 할까?"],
            "related_keywords": ["알뜰폰", "요금제", "번호 이동", "데이터", "유심"],
            "image_scene": "스마트폰 요금 내역과 메모장이 함께 놓인 차분한 책상 장면",
        },
    ],
    "생활비공과금": [
        {
            "search_phrase": "관리비 고지서 보는 법",
            "reader_problem": "매달 관리비가 나오지만 공용관리비, 개별사용료, 장기수선충당금이 무엇인지 헷갈리는 상황",
            "reader_promise": "고지서 항목을 공용, 개별, 별도 부과, 정산 항목으로 나눠 확인하는 방법 정리",
            "practical_points": ["공용관리비와 개별사용료를 먼저 나눠 보기", "전기, 수도, 난방처럼 사용량이 반영되는 항목을 따로 확인하기", "장기수선충당금이나 별도 부과 항목은 계약 관계에 맞게 확인하기", "갑자기 오른 항목은 전월 고지서와 비교해 원인을 찾기"],
            "mistakes_to_avoid": ["총액만 보고 어떤 항목이 올랐는지 확인하지 않기", "임차인과 임대인 부담 항목을 단정해서 말하기"],
            "faq_questions": ["관리비 고지서는 어떤 순서로 보면 좋을까?", "전월보다 오른 항목은 어떻게 확인해야 할까?"],
            "related_keywords": ["관리비", "공용관리비", "개별사용료", "장기수선충당금", "공과금"],
            "image_scene": "관리비 고지서와 계산기, 메모장이 놓인 책상 장면",
        },
        {
            "search_phrase": "전기요금 자동이체 변경",
            "reader_problem": "이사나 카드 변경 때문에 전기요금 자동이체를 바꿔야 하는데 처리 순서가 헷갈리는 상황",
            "reader_promise": "고객번호, 납부자 정보, 자동이체 해지와 재등록, 이사 정산 확인 순서를 정리",
            "practical_points": ["고객번호와 주소가 맞는지 고지서나 공식 화면에서 확인하기", "기존 자동이체 해지일과 새 결제수단 등록일을 겹치지 않게 보기", "이사 정산이 있다면 사용 종료일 기준으로 따로 확인하기", "변경 완료 여부는 문자나 공식 화면으로 다시 확인하기"],
            "mistakes_to_avoid": ["카드만 바꾸면 자동으로 변경된다고 생각하기", "이사 정산과 다음 달 요금을 같은 항목으로 착각하기"],
            "faq_questions": ["전기요금 자동이체 변경 전 무엇을 준비해야 할까?", "이사할 때 공과금 정산은 어떤 순서로 볼까?"],
            "related_keywords": ["전기요금", "자동이체", "공과금", "이사 정산", "고객번호"],
            "image_scene": "전기요금 고지서와 스마트폰 자동이체 화면을 확인하는 책상 장면",
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
    "월세 계약과 이사 서류 순서를 함께 보는 글",
    "통신비와 약정 만료일을 같이 점검하는 글",
    "이사 전후 주소 변경과 공과금 정산을 함께 보는 글",
    "관리비와 전기요금 고지서를 전월 기준으로 비교하는 글",
    "월세 계약 특약과 관리비 포함 항목을 함께 확인하는 글",
    "관리비와 공과금 고지서를 항목별로 보는 글",
]

DAILY_CATEGORY_ROTATION_FILE = "daily_category_rotation.json"
COUPANG_ANGLE_ROTATION_FILE = "coupang_angle_rotation.json"
COUPANG_SELECTION_HISTORY_FILE = "coupang_selection_history.json"
COUPANG_USED_PRODUCTS_FILE = "coupang_used_products.json"
COUPANG_SELECTION_HISTORY_LIMIT = 6
COUPANG_API_DOMAIN = "https://api-gateway.coupang.com"
COUPANG_API_BASE_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1"

COUPANG_GROUP_RULES = [
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
        "post_angle": "생활 속 불편을 줄이기 위해 구매 전 확인할 조건을 정리하는 글",
        "title_seed": "어떤 상황에서 이 제품군을 확인하면 좋은지 드러나는 제목",
        "thumbnail_prompt": "집 안에서 실제 문제를 해결하는 순간이 보이는 장면",
        "cta_text": "비슷한 고민이 있었다면 상세 정보부터 가볍게 확인해보면 좋겠다",
    },
    {
        "name": "비교고민정리형",
        "post_angle": "비슷한 제품을 비교할 때 놓치기 쉬운 기준을 정리하는 글",
        "title_seed": "비교 전에 먼저 봐야 할 조건이 드러나는 제목",
        "thumbnail_prompt": "여러 선택지 중 하나를 고르는 현실적인 책상이나 거실 장면",
        "cta_text": "직접 비교해볼수록 왜 많이 찾는지 이해되는 제품이라는 흐름",
    },
    {
        "name": "자취실사용형",
        "post_angle": "원룸, 자취, 작은 공간 기준으로 구매 조건을 따져보는 글",
        "title_seed": "작은 공간에서 체감한 장단점이 보이는 제목",
        "thumbnail_prompt": "원룸이나 작은 방에서 자연스럽게 사용 중인 장면",
        "cta_text": "좁은 공간에서 쓸 제품을 찾는다면 특히 체크해볼 만하다는 흐름",
    },
    {
        "name": "계절이슈형",
        "post_angle": "계절이나 날씨 이슈와 연결해 제품 필요성을 푸는 글",
        "title_seed": "계절 고민과 연결되는 제목",
        "thumbnail_prompt": "계절감이 느껴지고 제품 쓰임새가 바로 보이는 장면",
        "cta_text": "지금 같은 시즌에 왜 이런 제품을 많이 찾는지 연결되는 흐름",
    },
    {
        "name": "가성비판단형",
        "post_angle": "가격 대비 만족도와 실제 체감 포인트를 설명하는 글",
        "title_seed": "가성비 판단 근거가 드러나는 제목",
        "thumbnail_prompt": "실용성과 만족감이 느껴지는 생활형 사용 장면",
        "cta_text": "가격만 보지 말고 실제 체감 포인트를 같이 보면 판단이 쉬워진다는 흐름",
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

    if any(keyword in text_blob for keyword in ["포트", "주전자", "전기포트", "인덕션", "전자레인지", "오븐"]):
        return (
            "- 주방 소형가전은 용량, 세척 편의, 보관 위치, 전원선, 안전 기능 확인을 중심으로 쓴다.\n"
            "- 끓는 속도나 내구성을 임의로 단정하지 말고 상세 스펙에서 확인할 부분으로 안내한다.\n"
            "- 1인 가구, 사무실, 가족용처럼 사용량이 다른 상황을 나눠 설명한다."
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
        "고지서나 계약서를 펼친 장면으로 시작해 확인 순서로 확장하는 글",
        "놓치기 쉬운 실수담을 짧게 넣고 체크리스트로 정리하는 글",
        "검색자가 바로 따라 할 수 있는 서류와 공식 확인 순서형 글",
        "월 지출과 계약 조건을 나눠 판단하는 기준 중심 글",
    ])
    intent_candidates = DAILY_SEARCH_INTENT_BANK.get(content_category) or DAILY_SEARCH_INTENT_BANK["월세계약"]
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
        "비슷한 생활비와 계약 체크 기준을 계속 정리해두고 있으니 필요할 때 찾아보기 편하게 이웃 추가해두셔도 좋습니다.",
        "월세, 이사, 통신, 공과금처럼 한 번 놓치면 귀찮아지는 기준을 다시 볼 수 있게 정리하고 있으니 이웃 추가해두면 편합니다.",
        "고정지출과 서류 확인 순서는 계속 다룰 예정이라 이웃으로 남겨두시면 나중에 찾기 쉽습니다.",
        "돈이 나가기 전에 볼 체크 기준을 꾸준히 정리하고 있으니 필요할 때 다시 보실 분들은 이웃 추가해두셔도 괜찮습니다.",
        "비슷한 고민이 자주 생긴다면 계약과 고지서 확인 기준을 이어서 볼 수 있게 이웃으로 저장해두셔도 좋습니다.",
    ])

    return f"""
너는 네이버 블로그에서 월세·이사·통신·공과금처럼 돈이 나가기 전 확인할 기준을 다루는 생활비 체크형 블로거다.

이 글은 단순한 일상글이 아니다.
아래에서 확정한 검색어와 독자 고민을 기준으로 네이버 블로그에 올릴 수 있는 깊이 있는 정보성 본문을 작성해야 한다.
주제를 새로 고르거나 다른 소재로 바꾸지 마라.

최종 글은 광고글처럼 보이면 안 된다.
또 AI가 정리한 설명문처럼 보여도 안 된다.
생활 속에서 겪는 불편을 출발점으로 삼아, 실제 사람이 검색해보고 정리한 듯한 자연스러운 글이어야 한다.

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

[skssj2627 블로그 방향]
이 블로그는 월세·이사·통신·공과금 중심으로 생활비와 계약 조건을 다루는 정보형 블로그다.

아래 방향과 맞는 글만 작성한다.
- 월세 계약 전 확인할 것
- 전입신고와 확정일자 차이
- 이사 전 체크리스트
- 인터넷 약정 만료 전 확인
- 알뜰폰 요금제 변경 전 체크
- 관리비 고지서 보는 법
- 전기요금 자동이체 변경
- 공과금 이사 정산 확인 순서
- 주소 변경과 자동이체 정리 순서

맛집, 데이트, 카페, 여행, 단순 산책, 감정 일기, MBTI 잡담, 경제 뉴스 감상문으로 가지 마라.

[A급 주제 선정 기준]
이미 확정된 핵심 검색어가 A급 생활비 체크 글처럼 보이도록 본문을 구성한다.
최종 출력에는 선정 과정, 점수표, 후보 목록을 쓰지 마라.
확정 핵심 검색어를 다른 주제로 바꾸지 말고 바로 본문을 작성한다.

A급 주제는 아래 8가지 조건 중 최소 6개 이상을 만족해야 한다.

1. 검색 문장으로 자연스럽다
- 사람이 네이버에 그대로 검색할 법한 문장이어야 한다.
- 예: 월세 계약 전 확인할 것
- 예: 전입신고 확정일자 차이
- 예: 인터넷 약정 만료 전 확인
- 나쁜 예: 오늘의 소비 일기
- 나쁜 예: 돈 아끼는 소소한 생각

2. 돈이 나가거나 조건을 놓칠 수 있는 불편이 분명하다
- 월세 계약, 이사, 약정, 자동이체, 관리비처럼 독자가 바로 확인해야 할 문제가 있어야 한다.
- 추상적인 기분이나 감상만 있는 주제는 제외한다.

3. 시기성이 있거나 반복 검색 수요가 있다
- 이사철이면 월세 계약, 전입신고, 확정일자, 입주 청소, 인터넷 이전을 우선한다.
- 월말과 월초에는 관리비, 공과금, 자동이체, 통신비를 우선한다.
- 월세 갱신, 인터넷 약정 만료, 이사 정산, 관리비 고지서처럼 주기적으로 다시 검색되는 주제를 우선한다.

4. 집에서 바로 서류나 공식 안내로 확인할 수 있다
- 독자가 글을 읽고 바로 확인할 수 있는 기준이 있어야 한다.
- 예: 계약서, 고지서, 약정 종료일, 고객번호, 등기부등본, 공식 안내, 자동이체 화면

5. 특정 업체 추천 없이 판단 기준만 남긴다
- 통신사, 부동산 중개업소, 이사 업체, 관리업체를 특정해서 추천하지 않는다.
- 본문은 가입 유도나 상담 유도가 아니라 확인 순서와 주의점 중심이어야 한다.

6. 사진 없이도 글만으로 정보 가치가 있다
- 맛집, 데이트, 여행처럼 직접 방문 사진이 없으면 설득력이 떨어지는 주제는 피한다.
- 계약서, 고지서, 약정, 청구 서류처럼 글만으로도 확인 순서를 설명할 수 있는 주제를 우선한다.

7. 특정 회사명이나 상품명 중심이 아니다
- 특정 통신사, 부동산 중개업소, 이사 업체, 관리업체 이름 중심으로 가지 않는다.
- 비교가 필요한 경우에도 회사 추천이 아니라 조건 비교 기준으로만 풀어라.
- 예: 인터넷 약정 만료 전 확인은 가능
- 나쁜 예: 특정 통신사 요금제 무조건 추천

8. 조회수와 블로그 주제 신뢰도를 동시에 노릴 수 있다
- 단순 조회수만 위한 맛집, 데이트, 이슈성 잡담은 제외한다.
- skssj2627이 생활비와 계약 체크 블로그로 보이는 데 도움이 되는 주제를 고른다.

[A급 주제 우선순위]
아래 목록은 주제 감각을 맞추기 위한 참고용이다.
이미 확정된 핵심 검색어가 있으면 그 검색어를 우선하고, 아래 목록으로 주제를 바꾸지 마라.

1순위:
- 월세 계약 전 확인할 것
- 전입신고 확정일자 차이
- 인터넷 약정 만료 전 확인
- 관리비 고지서 보는 법
- 전기요금 자동이체 변경

2순위:
- 이사 전 체크리스트
- 입주 청소 전 확인할 것
- 알뜰폰 요금제 바꾸기 전 체크
- 관리비 고지서 보는 법
- 공과금 이사 정산 확인 순서

3순위:
- 월세 계약 갱신 전 특약 확인
- 인터넷 이전 설치 전 확인할 것
- 주소 변경 체크리스트
- 전기요금 자동이체 변경
- 공과금 이사 정산 확인 순서

[주제 선택 금지 조건]
아래 조건에 해당하는 방향으로 본문을 흐리지 마라.
- 검색자가 무엇을 얻을지 불분명한 주제
- 일기처럼 감정만 남는 주제
- 맛집, 데이트, 카페, 여행 주제
- 실제 방문 사진이 필요한 주제
- 특정 상품을 사라고 해야만 완성되는 주제
- 확인되지 않은 수치를 많이 만들어야 하는 주제
- 의료, 법률, 투자, 세금처럼 전문 판단을 단정해야 하는 고위험 조언 주제
- 보장, 환급, 가입 가능, 법적 효력, 세금 절감 같은 결과를 보장하는 문장
- 너무 넓어서 글이 흐려지는 주제
  예: 생활비 줄이는 법 전체
  예: 이사 준비 잘하는 법 전체

[좋은 주제 변환 예시]
너무 넓은 주제는 구체적인 생활비와 계약 확인 문제로 바꿔라.

- 이사 준비
   이사 전 체크리스트, 전입신고 확정일자 차이

- 통신비 절약
   인터넷 약정 만료 전 확인, 알뜰폰 요금제 바꾸기 전 체크

- 관리비 확인
   관리비 고지서 보는 법, 전월보다 오른 항목 확인

- 공과금 정리
   전기요금 자동이체 변경, 공과금 이사 정산 확인 순서


[본문 품질 기준]
본문은 아래 조건을 반드시 만족해야 한다.

[애드포스트 수익형 읽기 흐름 기준]
이 기준은 광고 클릭 유도가 아니라 독자가 본문을 오래 읽게 만드는 내부 작성 기준이다.
최종 본문에는 광고, 클릭, 하단 광고, 수익, 애드포스트 같은 단어를 절대 쓰지 않는다.

- 모바일 본문에서는 첫 5줄 안에 결론을 모두 소진하지 마라.
- 도입부에는 독자가 바로 확인할 핵심 기준 1개만 먼저 보여주고, 나머지 기준은 본문 중반과 후반에 나눠 배치한다.
- 모바일에서 스크롤을 이어가도록 2~4줄마다 "내 상황에서는 무엇부터 봐야 하는지"가 드러나는 짧은 판단 문장을 넣는다.
- 글 중반 이후에는 독자가 계약서, 고지서, 약정 화면, 자동이체 화면을 실제로 열어보고 싶게 만드는 확인 순서를 구체화한다.
- PC 화면에서는 글 하단까지 내려왔을 때 정보 가치가 남아 있어야 한다. 후반부는 인사말로 힘을 빼지 말고 정리표, 체크리스트, FAQ로 구성한다.
- 마지막 25~35% 구간에는 앞 내용을 반복하지 말고 "상황별 확인 순서", "놓치면 번거로운 항목", "오늘 바로 확인할 3가지"를 새롭게 정리한다.
- 독자가 다 읽고 나서 저장하거나 이웃 추가를 고민할 만큼 실용적인 마무리여야 한다.

[네이버 공식 품질 기준 반영]
이 기준은 작성 내부 기준이며 최종 본문에는 직접 언급하지 않는다.
- D.I.A. 관점에서 주제 적합도, 경험 정보, 정보의 충실성, 문서 의도, 독창성, 적시성을 높인다.
- C-Rank 관점에서 생활비와 계약 체크라는 관심사 집중도를 유지한다.
- 같은 블로그의 이전 글처럼 보이지 않도록 도입, 예시, 목록 항목, 마무리 문장을 매번 다르게 만든다.
- 검색자가 AI 브리핑이나 요약 영역에서 바로 가져갈 수 있도록 섹션마다 핵심 한 문장 답을 자연스럽게 넣는다.
- 단, 최종 본문에는 D.I.A., C-Rank, AI 브리핑, 상위노출, 검색 알고리즘, SEO라는 단어를 절대 쓰지 않는다.

1. 첫 문단은 검색 의도와 생활 장면을 함께 잡는다
- 첫 문장에는 확정 핵심 검색어를 자연스럽게 넣고, 독자가 겪는 문제 상황을 바로 요약한다.
- 두 번째 문장에는 이 글에서 확인할 기준 2~3가지를 짧게 예고한다.
- 세 번째 문장부터 생활 장면으로 자연스럽게 이어간다.
- 예: 월세 계약 전 확인할 것은 방 상태보다 계약서와 공적 서류를 먼저 나눠보는 순서입니다.
- 예: 인터넷 약정 만료 전 확인할 것은 월요금뿐 아니라 약정 종료일, 위약금, 결합 조건입니다.
- 예: 관리비 고지서 보는 법은 총액보다 오른 항목을 먼저 나눠보는 데서 시작합니다.
- 단, 오늘은 ~에 대해 알아보겠습니다로 시작하지 마라.

2. 3문단 안에 정보글로 전환한다
- 감정 묘사만 길게 끌지 마라.
- 생활 장면은 짧게 쓰고, 곧바로 확인 순서와 기준으로 넘어간다.

3. 확인 대상을 2단계 이상으로 나눈다
- 단순히 계약서를 보세요라고 끝내지 마라.
- 예: 계약서 + 공적 서류 + 입금 계좌 + 특약
- 예: 약정 종료일 + 위약금 + 결합 할인 + 설치 가능 여부
- 예: 고지서 + 전월 금액 + 사용량 항목 + 자동이체 화면

4. 독자가 바로 확인할 체크포인트를 제공한다
- 추상적인 관리하세요 금지
- 구체적으로 써라.
- 예: 주소의 동호수 표기가 계약서와 같은지
- 예: 약정 종료일과 위약금 조건이 공식 화면에 어떻게 보이는지
- 예: 관리비 고지서에서 전월 대비 오른 항목이 무엇인지
- 예: 전기요금 자동이체 변경 완료 여부가 공식 화면에 보이는지
- 확인 대상이 공식 안내, 계약서, 고지서, 앱 화면, 자동이체 화면 중 어디인지 분명히 적는다.

5. 상황별 기준을 넣는다
- 월세 계약 전
- 이사 당일
- 약정 만료 전
- 인터넷 이전 설치 전
- 자동이체 변경 전
- 관리비가 갑자기 오른 달
이 중 주제와 맞는 2~3개를 골라 설명한다.

6. 특정 업체나 상품을 강요하지 않는다
- 특정 회사 추천처럼 쓰지 마라.
- 조건 확인 기준을 먼저 쓰고, 업체나 상품은 비교 대상처럼만 언급한다.

7. 확인되지 않은 수치를 만들지 않는다
- 요금, 할인율, 위약금, 관리비 금액, 법적 효력, 세금 수치를 지어내지 마라.
- 필요하면 공식 안내와 계약서를 기준으로 다시 확인하는 편이 안전하다라고 쓴다.
- 정책, 요금, 법률, 세금처럼 변동 가능하거나 개인 조건에 따라 달라지는 내용은 단정하지 않는다.

8. 마지막은 광고가 아니라 정리로 끝낸다
- 구매하세요, 추천합니다, 링크 확인하세요 금지
- 먼저 볼 기준을 다시 짧게 정리한다.

[사람이 쓴 듯한 문장 무드]
아래 문장감을 참고하되 그대로 복사하지 말고 자연스럽게 변형하라.

- 막상 계약서를 펼치면 생각보다 볼 항목이 많습니다.
- 처음에는 월요금만 보면 될 줄 알았는데, 약정과 위약금에서 차이가 납니다.
- 가격보다 먼저 봐야 할 건 내가 묶인 조건이었습니다.
- 생각보다 놓치기 쉬운 부분이 여기서 갈립니다.
- 같은 계약도 이사 전과 갱신 전에는 보는 순서가 달라집니다.
- 글을 쓰려고 정리해보니, 결국 순서는 공식 안내 확인이 먼저였습니다.
- 이런 건 한 번에 처리하려고 하면 오히려 더 헷갈립니다.
- 먼저 계약서, 고지서, 공식 화면을 나눠보는 게 낫습니다.

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
- AI 브리핑
- D.I.A.
- C-Rank

[본문 구조]
아래 순서로 작성한다.

1. 검색어와 문제 상황으로 시작
- 첫 문장에는 선택한 핵심 키워드를 자연스럽게 1회 포함한다.
- 첫 문장은 독자가 검색한 이유가 바로 보이도록 문제 상황을 요약한다.
- 두 번째 문장은 이 글에서 확인할 기준 2~3가지를 짧게 말한다.
- 세 번째 문장부터 날짜, 계절, 날씨, 실제 장면 중 2개 이상을 자연스럽게 반영한다.
- 시작은 짧고 구체적으로 쓰되, 검색어만 억지로 반복하지 않는다.

2. 헷갈리는 이유
- 확인 대상을 2~4개로 나눠 설명한다.
- 계약서, 고지서, 약정 기간, 위약금, 청구 서류, 공식 안내, 주소 표기, 계좌 명의 중 주제와 맞는 요소를 반영한다.
- 확인되지 않은 수치는 만들지 않는다.
- 첫 문단 끝에는 검색자가 바로 이해할 수 있는 한 문장 답을 넣는다.

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
- 이사 전, 계약 당일, 약정 만료 전, 청구 전, 갱신 전, 설치 전, 고지서가 오른 달 중 주제와 맞는 2~3개를 골라 설명한다.
- 무조건 하나의 정답처럼 말하지 않는다.
- 계약 조건과 현재 상황에 따라 달라진다는 점을 자연스럽게 넣는다.

[구분선]

5. 놓치기 쉬운 부분
- 검색자가 자주 놓치는 부분을 2~3개 정리한다.
- 예: 주소 표기, 계약 기간, 위약금, 특약, 고객번호, 청구 서류, 계좌 명의, 공식 안내, 고지서 항목
- 특정 업체나 상품을 추천하지 말고 체크 기준으로만 설명한다.
- 앞 문단과 동일한 문장 구조 반복으로 보이지 않게 예시와 어미를 바꾼다.

6. 하단까지 읽히는 정리표
아래 마커를 정확히 사용한다.

[목록주제]오늘 바로 확인할 순서
- 지금 상황에서 먼저 열어볼 화면이나 서류 1개
- 두 번째로 대조해야 할 조건 1개
- 마지막으로 놓치기 쉬운 확인 항목 1개
[목록끝]

- 앞에서 이미 쓴 문장을 그대로 반복하지 말고, 실제 확인 순서처럼 정리한다.
- PC 하단에서 읽어도 새 정보가 남아 있어야 하므로 단순 요약만 쓰지 마라.

7. 짧은 FAQ
- 주제와 맞는 질문 2개를 자연스러운 문장으로 넣고 바로 답한다.
- 질문은 독자가 마지막까지 내려와서 확인할 만한 실전형 질문이어야 한다.
- 예: 계약서와 공식 화면이 다르면 무엇을 먼저 봐야 할까?
- 예: 자동이체 변경은 언제 다시 확인하는 게 좋을까?
- 답변은 단정하지 말고 공식 안내, 계약서, 고지서, 앱 화면을 기준으로 다시 확인하는 방향으로 쓴다.

8. 마지막 정리
- 오늘의 생활 장면으로 살짝 돌아오며 정리한다.
- 광고성 문장 없이 끝낸다.
- 제품 구매를 직접 유도하지 않는다.
- 아래 이웃 추가 문장을 마지막 정리 안에서 1회만 자연스럽게 넣는다.
- 이웃 추가 문장을 여러 번 반복하거나 명령형으로 바꾸지 않는다.
- 이웃 추가 문장: {daily_neighbor_cta}
- 다음에 관련 계약이나 고지서를 볼 때 어떤 기준부터 보면 좋은지만 말한다.
- 마지막 문단은 3~5줄로 끝내고, 독자가 저장해두고 다시 볼 만한 기준을 남긴다.

[인용구 규칙]
글 중간에 아래 형식의 인용구를 1~2개 넣는다.
[인용구]문장내용[/인용구]

인용구는 광고처럼 쓰지 말고, 글의 핵심 판단 기준을 담아라.
인용구 안의 문장내용은 반드시 20자 이상 60자 이하의 완성된 한국어 문장이어야 한다.
절대 [인용구][/인용구], [인용구] [/인용구], [인용구]문장내용[/인용구]처럼 비어 있거나 예시 문구가 그대로 남은 형태를 출력하지 마라.
인용구에 넣을 문장이 확실하지 않으면 인용구 마커 자체를 만들지 말고, 빈 인용구는 절대 만들지 마라.
예:
[인용구]돈이 나가기 전에는 조건을 먼저 나눠보는 게 순서였습니다[/인용구]
[인용구]서류와 공식 안내를 같이 보면 놓치는 항목이 줄어듭니다[/인용구]

[SEO 키워드 규칙]
- 선택한 핵심 키워드는 본문에 4~6회만 자연스럽게 포함한다.
- 관련 키워드는 자연스럽게 5~8개 정도만 섞는다.
- 가능한 관련 키워드:
  월세 계약, 전입신고, 확정일자, 이사 체크리스트, 인터넷 약정, 알뜰폰, 관리비 고지서, 전기요금 자동이체, 공과금, 주소 변경, 위약금, 계약서, 공식 안내, 구매 전 체크
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
- 월세계약, 전입신고, 확정일자, 이사준비, 인터넷약정, 알뜰폰, 관리비, 전기요금, 자동이체, 생활비절약, 공과금, 구매전체크 중 문맥에 맞는 태그를 고른다.
- 너무 긴 태그 금지
- 광고 느낌 강한 태그 금지
- 쿠팡, 로켓배송, 구매링크 같은 태그는 일상글에는 쓰지 마라.

[출력 규칙]
- 제목 없이 본문만 출력
- 3000자 이상 3600자 이하를 목표로 작성
- 글자수를 늘리기 위해 같은 기준이나 표현을 반복하지 말고, 원인, 확인 기준, 상황별 차이, 실수 방지를 구체화한다
- 각 소제목 역할의 문단마다 핵심 한 문장 답이 드러나게 쓴다
- 자연스러운 한국어만 사용
- 영어 문장, 영어 제목 후보, 작업 메모 출력 금지
- 마크다운 서식 금지
- [구분선]은 정확히 2~3회
- [인용구]문장[/인용구] 형식 1~2회
- 인용구 내부 문장은 반드시 20자 이상이어야 하며, 빈 인용구 출력 금지
- [목록주제]와 [목록끝] 마커는 철자 그대로 유지
- 본문 마지막에 [해시태그대기]와 해시태그 10개를 반드시 출력한다
- 문단 사이에는 빈 줄을 충분히 넣는다
- 일반 본문 문장은 한 줄 40자 안팎으로 쓰고, 길어도 45자를 넘기지 않는다
- 한 문장을 길게 한 문단으로 늘어쓰지 말고, 의미 단위마다 엔터를 눌러 아래 줄로 내려쓴다
- 긴 문단으로 쭉 나열하지 말고 2~4줄이 하나의 자연스러운 흐름이 되게 작성한다
- 목록 항목도 너무 짧게 쪼개지 말고 40자 안팎의 자연스러운 호흡으로 쓰며, 마커와 해시태그 형식은 그대로 유지한다
- 후반부에는 반드시 정리표와 짧은 FAQ가 있어야 하며, 마지막까지 새 확인 기준이 남아 있어야 한다

[절대 금지]
- 광고 고지문 출력 금지
- 쿠팡 링크 출력 금지
- 광고, 클릭, 하단 광고, 수익, 애드포스트라는 단어 출력 금지
- 특정 상품 직접 구매 후기처럼 작성 금지
- 내돈내산 표현 금지
- 직접 사용했다고 단정 금지
- 확인되지 않은 수치 생성 금지
- 상위노출, 검색 알고리즘, SEO라는 단어를 본문에 직접 쓰기 금지
- AI 브리핑, D.I.A., C-Rank라는 단어를 본문에 직접 쓰기 금지
- 여러 블로그를 분석했다고 직접 말하기 금지
- AI가 쓴 것처럼 보이는 정리문 금지
- 동일한 문장 구조 반복으로 분량 채우기 금지
"""


def build_daily_image_prompt(daily_context):
    return (
        f"{daily_context['photo_style']}, {daily_context['season']} 분위기, "
        f"{daily_context['weather_key']} 느낌, {daily_context['image_scene']}, "
        f"{daily_context['search_phrase']}와 관련된 생활비 체크 정보형 블로그 사진, "
        "20대 성인 한국인 여성이 반드시 등장하고 자연스러운 표정과 생활감이 보이는 장면, "
        "회사 로고, 개인정보, 읽을 수 있는 글자가 보이지 않는 자연스러운 실내 생활 장면"
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
    product_link = str(row.get("쿠팡링크") or "").strip()
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
            "product_link": str(row.get("쿠팡링크") or "").strip(),
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
    """사용하지 않은 쿠팡 상품 한 개를 랜덤 선택한다."""
    rows, fieldnames, _encoding = load_csv_rows(csv_path)
    api_enabled = is_coupang_api_enabled()
    required_fields = ["상품명", "키워드", "쿠팡링크"]
    missing_fields = [field for field in required_fields if field not in fieldnames]
    if missing_fields:
        raise RuntimeError(f"CSV 필수 컬럼이 없습니다: {', '.join(missing_fields)}")

    used_products = migrate_used_rows_to_state(rows)
    available_indexes = [
        idx for idx, row in enumerate(rows)
        if not is_coupang_product_already_used(row, used_products)
    ]
    if not available_indexes:
        raise RuntimeError("사용 가능한 쿠팡 상품이 없습니다. 사용 이력 파일을 초기화하거나 새 상품을 추가하세요.")

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

    seed_key = get_coupang_product_key(selected_row)
    if api_enabled:
        original_url = get_product_field(selected_row, "상품원본URL", "쿠팡링크")
        converted_url = generate_coupang_deeplink(original_url)
        if converted_url and converted_url != original_url:
            selected_row["상품원본URL"] = selected_row.get("상품원본URL") or original_url
            selected_row["쿠팡링크"] = converted_url
            print(f"   >> 쿠팡 딥링크 변환 성공: {selected_row.get('상품명')}")
        else:
            print("   >> [안내] 쿠팡 딥링크 변환 결과가 없어 CSV 링크를 유지합니다.")

    if not get_product_field(selected_row, "상품명") or not get_product_field(selected_row, "쿠팡링크"):
        raise RuntimeError("쿠팡 상품명 또는 쿠팡링크가 비어 있습니다. API 키를 확인하거나 CSV에 쿠팡링크를 넣어주세요.")

    return {
        "selected_index": selected_index,
        "selected_row": selected_row,
        "selected_group": selected_candidate["group"],
        "seed_key": seed_key,
    }


def mark_coupang_product_as_used(csv_path, product_state, blog_title):
    """쿠팡 글 발행 성공 후 해당 상품의 사용 이력을 기록한다."""
    selected_row = product_state["selected_row"]
    used_products = load_coupang_used_products()
    used_entry = {
        "product_name": str(selected_row.get("상품명") or "").strip(),
        "keyword": str(selected_row.get("키워드") or "").strip(),
        "product_link": str(selected_row.get("쿠팡링크") or "").strip(),
        "used_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "post_title": blog_title,
    }
    product_key = get_coupang_product_key(selected_row)
    used_products[product_key] = used_entry
    seed_key = product_state.get("seed_key")
    if seed_key and seed_key != product_key:
        used_products[seed_key] = used_entry
    save_coupang_used_products(used_products)
    record_coupang_selection_history(selected_row)


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
        f"🛒 {product_name}\n"
        f"{product_link}"
    )


def distribute_coupang_links(raw_content, product_name, product_link, cta_text):
    """
    쿠팡 파트너스 링크를 네이버 블로그 본문에 2회만 삽입한다.
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
        "가격과 후기 확인",
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

    print("   >> 쿠팡 링크 삽입 완료: 2회")
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
# 2. GeminiWebBot - 웹사이트에서 텍스트+이미지 모두 생성
# =============================================================
class GeminiWebBot:
    """Gemini 웹사이트 하나의 세션에서 텍스트/이미지 모두 처리"""
    
    def __init__(self):
        gem_options = Options()
        automation_profile = os.path.join(os.path.expanduser("~"), "ChromeGeminiBot")
        gem_options.add_argument(f"--user-data-dir={automation_profile}")
        gem_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        gem_options.add_experimental_option("useAutomationExtension", False)
        gem_options.add_argument("--disable-blink-features=AutomationControlled")
        
        self.driver = create_chrome_driver(gem_options)
        self.driver.maximize_window()
        
        print("   >> 🌐 Gemini 웹사이트 접속 중...")
        self.driver.get("https://gemini.google.com/app")
        time.sleep(5)
        
        # 로그인 필요 여부 확인
        if "accounts.google.com" in self.driver.current_url or "signin" in self.driver.current_url.lower():
            print("   >> 🔑 Google 로그인이 필요합니다! 브라우저에서 직접 로그인해주세요 (최대 5분 대기)")
            print("   >>     ※ 최초 실행 시에만 필요합니다. 이후에는 자동 로그인됩니다.")
            WebDriverWait(self.driver, 300).until(
                lambda d: "gemini.google.com" in d.current_url and "accounts.google.com" not in d.current_url
            )
            time.sleep(3)
            print("   >> ✅ Google 로그인 완료!")
        
        print("   >> ✅ Gemini 페이지 진입 완료!")
        time.sleep(3)
        
        # 임시 채팅 버튼 클릭 (채팅 목록에 쌓이지 않도록)
        self._click_temp_chat()
        
        # Gemini 3.1 Pro 모델 선택
        self._select_thinking_model()
        
        self.response_count = 0  # 현재 대화에서 응답 수 추적
    
    def _click_temp_chat(self):
        """임시 채팅 버튼 클릭 (채팅 기록에 남지 않도록)
        1차: 화면에 임시 채팅 버튼이 바로 보이면 클릭
        2차: 안 보이면 기본 메뉴(햄버거) 버튼을 열어서 임시 채팅 클릭
        """
        try:
            temp_chat_selectors = [
                'button[data-test-id="temp-chat-button"]',
                'button[aria-label="임시 채팅"]',
                'button.temp-chat-button',
            ]
            
            # 1차 시도: 임시 채팅 버튼이 바로 보이면 클릭
            for sel in temp_chat_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(2)
                        print("   >> 🔒 임시 채팅 모드 활성화!")
                        return True
                except:
                    continue
            
            # 2차 시도: 기본 메뉴(햄버거) 버튼을 눌러서 사이드바 열기
            print("   >> 임시 채팅 버튼이 바로 안 보여서 기본 메뉴를 열겠습니다...")
            menu_btn_selectors = [
                'button[data-test-id="side-nav-menu-button"]',
                'button[aria-label="기본 메뉴"]',
            ]
            menu_opened = False
            for sel in menu_btn_selectors:
                try:
                    menu_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if menu_btn.is_displayed():
                        menu_btn.click()
                        time.sleep(2)
                        print("   >> 📂 기본 메뉴 열기 완료!")
                        menu_opened = True
                        break
                except:
                    continue
            
            if not menu_opened:
                print("   >> [주의] 기본 메뉴 버튼도 찾지 못했습니다. 일반 채팅으로 진행합니다.")
                return False
            
            # 메뉴가 열린 상태에서 임시 채팅 버튼 다시 찾기
            for sel in temp_chat_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(2)
                        print("   >> 🔒 임시 채팅 모드 활성화!")
                        return True
                except:
                    continue
            
            # XPath 폴백: 텍스트로 임시 채팅 찾기
            try:
                btn = self.driver.find_element(By.XPATH, 
                    '//button[contains(., "임시") and contains(., "채팅")]')
                if btn.is_displayed():
                    btn.click()
                    time.sleep(2)
                    print("   >> 🔒 임시 채팅 모드 활성화! (텍스트 검색)")
                    return True
            except:
                pass
            
            print("   >> [주의] 임시 채팅 버튼을 찾지 못했습니다. 일반 채팅으로 진행합니다.")
            return False
        except:
            return False
    
    def _select_thinking_model(self):
        """Gemini 3.1 Pro 선택 (모드 선택 드롭다운 → 3.1 Pro 클릭)"""
        try:
            # 1) 모드 선택 버튼 클릭
            mode_btn_selectors = [
                'button[data-test-id="bard-mode-menu-button"]',
                'button.input-area-switch',
            ]
            mode_btn = None
            for sel in mode_btn_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if btn.is_displayed():
                        mode_btn = btn
                        break
                except:
                    continue

            if not mode_btn:
                mode_btn_xpaths = [
                    '//*[self::button or @role="button"][contains(@aria-label, "모델")]',
                    '//*[self::button or @role="button"][contains(@aria-label, "Model")]',
                    '//*[self::button or @role="button"][contains(normalize-space(.), "Gemini") and (contains(normalize-space(.), "Pro") or contains(normalize-space(.), "프로"))]',
                ]
                for xpath in mode_btn_xpaths:
                    try:
                        buttons = self.driver.find_elements(By.XPATH, xpath)
                        for btn in buttons:
                            if btn.is_displayed():
                                mode_btn = btn
                                break
                        if mode_btn:
                            break
                    except:
                        continue
            
            if not mode_btn:
                print("   >> [주의] 모드 선택 버튼을 찾지 못했습니다.")
                return False
            
            try:
                mode_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", mode_btn)
            time.sleep(2)
            
            # 2) Gemini 3.1 Pro 옵션 클릭
            model_option_xpaths = [
                '//*[self::button or @role="menuitem" or @role="option"][contains(normalize-space(.), "3.1") and contains(normalize-space(.), "Pro")]',
                '//*[self::button or @role="menuitem" or @role="option"][contains(normalize-space(.), "3.1") and contains(normalize-space(.), "프로")]',
                '//*[contains(@class, "bard-mode-list-button")][contains(normalize-space(.), "3.1") and contains(normalize-space(.), "Pro")]',
                '//*[contains(@class, "bard-mode-list-button")][contains(normalize-space(.), "3.1") and contains(normalize-space(.), "프로")]',
            ]
            for xpath in model_option_xpaths:
                try:
                    options = self.driver.find_elements(By.XPATH, xpath)
                    for option in options:
                        if option.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", option)
                            time.sleep(0.3)
                            try:
                                option.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", option)
                            time.sleep(2)
                            print("   >> 🧠 Gemini 3.1 Pro 선택 완료!")
                            return True
                except:
                    continue
            
            # 드롭다운 닫기 (선택 실패 시)
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
            except:
                pass
            
            print("   >> [주의] Gemini 3.1 Pro 모델을 찾지 못했습니다. 현재 선택된 모델로 진행합니다.")
            return False
        except:
            return False
    
    def _find_input(self):
        """입력창 찾기"""
        selectors = [
            "div.ql-editor[contenteditable='true']",
            "rich-textarea .ql-editor",
            "div[contenteditable='true'][role='textbox']",
            "rich-textarea",
            "textarea",
            "div[contenteditable='true']",
        ]
        for sel in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if el.is_displayed() and el.size['height'] > 10:
                        return el
            except:
                continue
        return None
    
    def _extract_last_response(self):
        """마지막 응답 텍스트 추출"""
        response_selectors = [
            "model-response .markdown-main-panel",
            "div.model-response-text .markdown",
            "div.response-container-content",
            "div[data-message-author-role='model']",
            "message-content .markdown",
            "div.model-response",
            ".response-container .markdown",
        ]
        
        for sel in response_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if elements:
                    last_el = elements[-1]
                    text = last_el.get_attribute('innerText') or last_el.text
                    if text and len(text.strip()) > 10:
                        return text.strip()
            except:
                continue
        
        # JavaScript 폴백: 모든 model-response 텍스트 가져오기
        try:
            text = self.driver.execute_script("""
                var responses = document.querySelectorAll('model-response, div.model-response, [data-message-author-role="model"]');
                if (responses.length > 0) {
                    return responses[responses.length - 1].innerText;
                }
                return null;
            """)
            if text and len(text.strip()) > 10:
                return text.strip()
        except:
            pass
        
        return None

    def _is_placeholder_response(self, text):
        text = (text or "").strip()
        if not text:
            return True
        placeholder_patterns = [
            "생각하는 중",
            "생각 중",
            "응답 생성 중",
            "답변 생성 중",
            "작성 중",
            "thinking",
            "generating",
        ]
        lowered = text.lower()
        return len(text) < 80 and any(pattern in lowered for pattern in placeholder_patterns)
    
    def _is_thinking(self):
        """Gemini 사고 모델이 현재 '생각 중' 상태인지 감지"""
        try:
            # 사고 중 표시 요소들 확인
            thinking_selectors = [
                'div.thinking-indicator',
                'div[data-test-id="thinking-indicator"]',
                '.thought-process',
                'div.is-thinking',
                'mat-progress-bar',
                'div.thinking-content',
            ]
            for sel in thinking_selectors:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            return True
                except:
                    continue
            
            # JavaScript로 로딩/사고 중 상태 감지
            is_loading = self.driver.execute_script("""
                // 스피너/로딩 애니메이션 감지
                var spinners = document.querySelectorAll(
                    '.loading-indicator, .spinner, [role="progressbar"], ' +
                    'mat-progress-bar, .thinking-indicator, .thought-chip'
                );
                for (var i = 0; i < spinners.length; i++) {
                    if (spinners[i].offsetParent !== null) return true;
                }
                // 전송 버튼이 비활성화 = 아직 응답 생성 중
                var sendBtns = document.querySelectorAll(
                    'button.send-button[disabled], button[data-test-id="send-button"][disabled]'
                );
                if (sendBtns.length > 0) return true;

                // 중지(Stop) 버튼이 화면에 보이면 = 아직 응답 생성 중
                var stopSelectors = [
                    'button[aria-label*="Stop"]',
                    'button[aria-label*="중지"]',
                    'button[data-test-id="stop-button"]'
                ];
                for (var i = 0; i < stopSelectors.length; i++) {
                    var stopButtons = document.querySelectorAll(stopSelectors[i]);
                    for (var j = 0; j < stopButtons.length; j++) {
                        if (stopButtons[j].offsetParent !== null && !stopButtons[j].disabled) {
                            return true;
                        }
                    }
                }
                
                return false;
            """)
            return bool(is_loading)
        except:
            return False

    def _is_ready_for_next_prompt(self):
        """다음 프롬프트를 보내도 되는 입력 가능 상태인지 확인"""
        try:
            if self._is_thinking():
                return False

            ready_state = self.driver.execute_script("""
                var stopSelectors = [
                    'button[aria-label*="Stop"]',
                    'button[aria-label*="중지"]',
                    'button[data-test-id="stop-button"]'
                ];
                for (var i = 0; i < stopSelectors.length; i++) {
                    var stopButtons = document.querySelectorAll(stopSelectors[i]);
                    for (var j = 0; j < stopButtons.length; j++) {
                        if (stopButtons[j].offsetParent !== null && !stopButtons[j].disabled) {
                            return false;
                        }
                    }
                }

                var sendSelectors = [
                    'button.send-button',
                    'button[data-test-id="send-button"]'
                ];
                for (var k = 0; k < sendSelectors.length; k++) {
                    var sendButtons = document.querySelectorAll(sendSelectors[k]);
                    for (var m = 0; m < sendButtons.length; m++) {
                        if (sendButtons[m].offsetParent !== null) {
                            return !sendButtons[m].disabled;
                        }
                    }
                }

                var editors = document.querySelectorAll(
                    "div.ql-editor[contenteditable='true'], div[contenteditable='true'][role='textbox'], textarea"
                );
                for (var n = 0; n < editors.length; n++) {
                    var editor = editors[n];
                    if (editor.offsetParent !== null && !editor.disabled && editor.getAttribute('aria-disabled') !== 'true') {
                        return true;
                    }
                }

                return false;
            """)
            return bool(ready_state)
        except:
            return False

    def _wait_until_ready_for_next_prompt(self, timeout=120, stable_seconds=5):
        """입력 가능 상태가 몇 초간 유지될 때까지 대기"""
        stable_count = 0
        for wait_sec in range(timeout):
            if self._is_ready_for_next_prompt():
                stable_count += 1
                if stable_count >= stable_seconds:
                    if wait_sec > 0:
                        print(f"   >> ⏱️ 다음 프롬프트 전송 가능 상태 확인 완료 ({wait_sec}초 대기)")
                    return True
            else:
                stable_count = 0

            if wait_sec > 0 and wait_sec % 20 == 0:
                print(f"   >> ⏳ Gemini 입력 가능 상태 대기 중... ({wait_sec}초)")
            time.sleep(1)

        return False
    
    def send_prompt(self, prompt, max_wait=300):
        """프롬프트 전송 → 텍스트 응답 반환 (사고 모델 대응)"""
        if not self._wait_until_ready_for_next_prompt(timeout=120, stable_seconds=3):
            print("   >> [주의] 입력창 준비 상태를 충분히 확인하지 못했지만 전송을 시도합니다.")

        input_el = self._find_input()
        if not input_el:
            print("   >> [에러] Gemini 입력창을 찾지 못했습니다.")
            return None
        
        # 프롬프트 입력
        input_el.click()
        time.sleep(0.5)
        pyperclip.copy(prompt)
        actions = ActionChains(self.driver)
        actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(1)
        
        # 전송
        actions.send_keys(Keys.RETURN).perform()
        print("   >> ⏳ Gemini 응답 대기 중 (사고 모델)...")
        time.sleep(10)  # 사고 모델은 생각 시작까지 시간이 더 걸림
        
        # 1단계: 사고 중(thinking) 단계 대기
        thinking_waited = 0
        while thinking_waited < 120:  # 사고 단계 최대 120초 대기
            if self._is_thinking():
                if thinking_waited % 15 == 0:
                    print(f"   >> 🧠 사고 중... ({thinking_waited}초)")
                time.sleep(1)
                thinking_waited += 1
            else:
                if thinking_waited > 0:
                    print(f"   >> 🧠 사고 완료! ({thinking_waited}초 소요)")
                break
        
        # 2단계: 실제 텍스트 응답 안정화 대기
        prev_text = ""
        stable_count = 0
        required_stable = 5  # 사고 모델은 5초 연속 변화 없어야 완료 판정
        
        for wait_sec in range(max_wait):
            current_text = self._extract_last_response()
            if self._is_placeholder_response(current_text):
                current_text = None
            
            # 아직 사고 중이면 카운터 리셋
            if self._is_thinking():
                stable_count = 0
                if wait_sec % 20 == 0:
                    print(f"   >> 🧠 아직 사고 중... ({wait_sec}초)")
                time.sleep(1)
                continue
            
            if current_text and len(current_text) > 20:
                if current_text == prev_text:
                    stable_count += 1
                    if stable_count >= required_stable:
                        if self._wait_until_ready_for_next_prompt(timeout=60, stable_seconds=8):
                            self.response_count += 1
                            print(f"   >> ✅ 응답 수신 완료! ({len(current_text)}자, 안정화 {required_stable}초 + 준비 상태 확인)")
                            return current_text
                        stable_count = 0
                else:
                    stable_count = 0
                prev_text = current_text
            
            time.sleep(1)
            if wait_sec % 30 == 0 and wait_sec > 0:
                text_len = len(prev_text) if prev_text else 0
                print(f"   >> 아직 생성 중... ({wait_sec}초, 현재 {text_len}자)")
        
        # 타임아웃이어도 마지막 텍스트 반환 시도
        if prev_text and len(prev_text) > 50:
            self._wait_until_ready_for_next_prompt(timeout=30, stable_seconds=5)
            print(f"   >> ⚠️ 타임아웃이지만 응답 반환 ({len(prev_text)}자)")
            return prev_text
        
        print("   >> [에러] 응답을 가져올 수 없습니다.")
        return None
    
    def new_chat(self):
        """새 대화 시작 (이전 대화 컨텍스트 초기화)"""
        try:
            # 새 채팅 버튼 클릭 시도
            new_chat_selectors = [
                'a[href="/app"]',
                'button[aria-label*="New chat"]',
                'button[aria-label*="새 채팅"]',
                'a.new-chat',
            ]
            for sel in new_chat_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(3)
                        self.response_count = 0
                        print("   >> 🔄 새 대화 시작!")
                        return True
                except:
                    continue
            
            # URL로 직접 이동
            self.driver.get("https://gemini.google.com/app")
            time.sleep(5)
            self.response_count = 0
            print("   >> 🔄 새 대화 시작! (페이지 이동)")
            return True
        except:
            return False
    
    def generate_image(self, img_description, save_path):
        """이미지 생성 → 다운로드 (사고 모델 대응)"""
        img_prompt = f"다음 제품과 어울리는 고품질 사진 1장을 나노바나나2로 생성해줘. 텍스트 없이 깔끔한 제품 사진만:\n\n{img_description}"
        
        input_el = self._find_input()
        if not input_el:
            print("   >> [에러] Gemini 입력창을 찾지 못했습니다.")
            return None
        
        input_el.click()
        time.sleep(0.5)
        pyperclip.copy(img_prompt)
        actions = ActionChains(self.driver)
        actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(1)
        
        actions.send_keys(Keys.RETURN).perform()
        print("   >> 🎨 이미지 생성 요청 전송! 사고 모델 응답 대기 중 (최대 180초)...")
        time.sleep(15)  # 사고 모델 초기 대기
        
        # 사고 단계 대기
        thinking_waited = 0
        while thinking_waited < 90:  # 이미지 생성 사고 단계 최대 90초
            if self._is_thinking():
                if thinking_waited % 15 == 0:
                    print(f"   >> 🧠 이미지 생성 사고 중... ({thinking_waited}초)")
                time.sleep(1)
                thinking_waited += 1
            else:
                if thinking_waited > 0:
                    print(f"   >> 🧠 이미지 생성 사고 완료! ({thinking_waited}초 소요)")
                break
        
        # 이미지 나타날 때까지 대기
        downloaded = False
        for wait_sec in range(180):  # 최대 180초 대기
            try:
                images = self.driver.find_elements(By.CSS_SELECTOR, 
                    "img[src*='lh3.googleusercontent.com'], "
                    "img[src*='blob:'], "
                    "img.generated-image, "
                    "img[data-test-id], "
                    "div.response-container img, "
                    "div.model-response img"
                )
                
                for img in images:
                    if not img.is_displayed():
                        continue
                    width = img.size.get('width', 0)
                    height = img.size.get('height', 0)
                    src = img.get_attribute("src") or ""
                    
                    if width > 150 and height > 150 and src and "icon" not in src.lower():
                        time.sleep(3)  # 이미지 렌더링 안정화 대기
                        
                        if src.startswith("http") and "blob:" not in src:
                            try:
                                cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
                                img_resp = requests.get(src, cookies=cookies, timeout=15)
                                with open(save_path, 'wb') as f:
                                    f.write(img_resp.content)
                                downloaded = True
                            except:
                                img.screenshot(save_path)
                                downloaded = True
                        else:
                            img.screenshot(save_path)
                            downloaded = True
                        
                        if downloaded:
                            print(f"   >> 🎨 Gemini 이미지 다운로드 완료: {save_path}")
                            return save_path
                
            except Exception:
                pass
            
            time.sleep(1)
            if wait_sec % 20 == 0 and wait_sec > 0:
                print(f"   >> 아직 이미지 생성 중... ({wait_sec}초)")
        
        print("   >> [주의] 이미지를 찾지 못했습니다. 텍스트만 업로드합니다.")
        return None
    
    def close(self):
        """브라우저 닫기"""
        try:
            self.driver.quit()
        except:
            pass


# =============================================================
# 3. 콘텐츠 생성 함수 (Gemini 웹 전용)
# =============================================================
def generate_content(post_type):
    """
    post_type: '일상' 또는 '쿠팡'
    Gemini 웹사이트 하나의 세션에서 텍스트+이미지 모두 생성
    """
    img_path = os.path.join(BASE_DIR, f'temp_blog_img_{int(time.time())}.png')
    
    # GeminiWebBot 세션 시작
    bot = GeminiWebBot()
    
    try:
        product_state = None
        if post_type == "\uc77c\uc0c1":
            daily_context = build_daily_topic_context()
            prompt = build_daily_post_prompt(daily_context)

            print("   >> 일상 주제 컨텍스트 선정 완료...")
            print(f"   >> 검색 주제: {daily_context['search_phrase']} | 카테고리: {daily_context['content_category']} | 날씨: {daily_context['weather_key']}")

            print("   >> 블로그 본문 생성 중 (사고 모델, 최대 5분 대기)...")
            blog_content = bot.send_prompt(prompt, max_wait=300)
            if not blog_content:
                return None, None, None, "", None

            print("   >> 제목 생성 중 (사고 모델)...")
            title_prompt = f"""
너는 네이버 검색 유입과 클릭률을 함께 고려하는 블로그 제목 편집자입니다.
아래 검색 의도와 본문을 보고 제목 1개만 작성하세요.

[검색 의도]
- 확정 핵심 검색어: {daily_context['search_phrase']}
- 독자 고민: {daily_context['reader_problem']}
- 글에서 해결할 약속: {daily_context['reader_promise']}

[제목 규칙]
- 제목은 단순 일상 제목이 아니라 사람들이 실제로 검색할 만한 생활 문제형 제목이어야 한다
- 확정 핵심 검색어 또는 자연스러운 변형을 제목 앞쪽에 넣는다
- 문제 상황 + 확인 기준 + 해결 기대가 제목만 봐도 보여야 한다
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

        if post_type == '쿠팡':
            product_state = select_unused_coupang_product(csv_file_path)
            target = product_state["selected_row"]
            coupang_angle = get_next_coupang_angle(datetime.now())
            angle_name = coupang_angle.get("name", "구매체크형")
            angle_direction = coupang_angle.get("post_angle", "구매 전 확인할 조건을 정리하는 글")
            p_name = target['상품명']
            p_keyword = target['키워드']
            p_link = target['쿠팡링크']
            product_group = product_state.get("selected_group") or infer_coupang_product_group(target)
            
            problem_scenario = get_product_field(target, "문제상황", default=f"{p_keyword}이 필요한데 어떤 제품을 골라야 할지 애매한 상황")
            target_reader = get_product_field(target, "대상독자", default="구매 전에 자기 환경에 맞는 확인 기준을 먼저 보고 싶은 사람")
            usage_place = get_product_field(target, "사용장소", default="집이나 개인 작업 공간")
            season_tag = get_product_field(target, "시즌태그", "계절태그", default="사계절")
            pain_point = get_product_field(target, "불편포인트", default="광고성 정보는 많은데 내 상황에 맞는 판단이 어려운 점")
            selling_point_1 = get_product_field(target, "장점1", default="사용 환경 기준으로 무난하게 접근하기 쉬운 점")
            selling_point_2 = get_product_field(target, "장점2", default="가격 대비 만족도를 기대하기 쉬운 점")
            selling_point_3 = get_product_field(target, "장점3", default="후기와 정보량이 비교적 많은 점")
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
                default="이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.",
            )

            # 1단계: 본문 생성 (사고 모델 → 최대 300초 대기)
            print("   >> 📝 블로그 본문 생성 중 (사고 모델, 최대 5분 대기)...")
            prompt = f"""
너는 네이버 블로그에서 계절 생활문제와 집안관리 고민을 먼저 진단하는 생활 정보형 블로거다.
이 글은 네이버 블로그 에디터에 그대로 들어갈 본문이므로 HTML, 마크다운, 코드블록을 절대 쓰지 않는다.

이 글의 목적은 단순 상품 홍보가 아니다.
검색자가 상품을 사기 전에 겪는 생활 문제의 원인을 먼저 나누고, 자기 집이나 사용 환경에 맞는 확인 순서를 잡아준 뒤, 필요한 경우 상세정보 확인으로 이어지게 만드는 것이다.
상품은 글의 출발점이 아니라 문제 해결을 검토할 때 참고하는 후보로만 다룬다.

광고 고지문은 코드에서 disclosure_text로 본문 최상단에 자동으로 붙는다.
따라서 본문 안에서 쿠팡 파트너스 광고 고지문을 다시 출력하지 마라.
상품 링크도 본문 안에 직접 출력하지 마라. 링크는 코드가 따로 삽입한다.

[오늘 진단할 생활문제와 연결 상품]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
- 상품군: {product_group}
- 대상 독자: {target_reader}
- 사용 상황: {problem_scenario}
- 사용 장소: {usage_place}
- 시즌/시기: {season_tag}
- 독자가 겪는 불편: {pain_point}
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

[skssj2627 블로그 방향]
이 블로그는 계절 생활문제와 집안관리 고민을 먼저 풀고, 필요한 경우 생활가전과 관련 제품을 확인할 기준을 정리해주는 블로그다.
중심 주제는 제습기, 선풍기, 서큘레이터, 이동식 에어컨, 창문형 에어컨, 공기청정기, 청소기, 가습기, 모기퇴치용품, 계절 생활가전, 집안 습도, 냉방, 환기, 공기질, 청소, 빨래건조, 원룸 생활, 사무실 환경이다.
현재 상품이 위 범위와 완전히 일치하지 않더라도 억지로 가전제품인 척하지 마라.
대신 사용 장소, 계절성, 생활 불편, 구매 전 체크포인트 중심으로 자연스럽게 연결하라.

[문제 진단형 작성 원칙]
- 글의 주어는 상품이 아니라 독자가 겪는 불편, 공간, 계절, 사용 조건이어야 한다.
- 본문 앞부분에서는 상품 장점보다 문제가 왜 생기는지와 무엇부터 확인해야 하는지를 먼저 설명한다.
- '{p_name}'은 해결 후보를 확인하는 예시로만 언급하고, 글 전체를 상품 소개문처럼 만들지 않는다.
- 독자가 글을 읽고 "내 상황에서는 무엇을 먼저 보면 되는지" 알 수 있어야 한다.
- 좋은 흐름 예시: 방이 꿉꿉한 이유 진단 -> 환기/습기 위치/공간 크기 확인 -> 제습기 같은 제품을 볼 때 용량과 관리 조건 확인.
- 나쁜 흐름 예시: 상품명 소개 -> 장점 나열 -> 추천 대상 -> 바로 구매 유도.

[가장 중요한 작성 원칙]
- AI가 정리한 설명문처럼 쓰지 마라.
- 사람이 네이버 블로그에 직접 남긴 생활 기록처럼 자연스럽게 써라.
- 다만 실제 사용하지 않았는데 직접 사용했다고 꾸미지는 마라.
- 내돈내산, 직접 써봤다, 제가 샀다, 며칠 써보니, 집에서 계속 써보니, 협찬 아님 같은 표현은 절대 쓰지 마라.
- "후기들을 보면", "상세페이지 기준으로 보면", "구매 전 확인할 부분은", "사용 환경에 따라" 같은 표현을 자연스럽게 활용하라.
- 확인되지 않은 가격, 할인율, 판매량, 순위, 최저가, 재고, 배송 보장, 전기요금 수치, 소음 수치, 면적 수치, 성능 수치는 절대 지어내지 마라.
- 상품을 무조건 좋다고 하지 말고, 먼저 확인해야 할 환경과 신중히 볼 환경을 분명히 나눠라.
- 과장된 구매 유도보다 구매 전 판단 기준을 우선한다.
- {post_angle} 관점을 자연스럽게 반영하라.
- 오늘 글 변주인 {angle_name} 흐름을 반영하되, 실제 구매나 직접 사용을 한 것처럼 꾸미지는 마라.

[사람이 쓴 듯한 문장감]
- 문장은 너무 반듯하게만 쓰지 말고, 중간중간 생활감 있는 흐름을 넣어라.
- 예: "이런 제품은 막상 사려고 보면 생각보다 볼 게 많습니다."
- 예: "처음에는 가격만 보면 될 줄 알았는데, 실제로는 놓치기 쉬운 부분이 꽤 있더라고요."
- 예: "특히 원룸이나 작은 방에서는 크기와 소음이 생각보다 크게 느껴질 수 있습니다."
- 단, 위 예문을 그대로 반복하지 말고 자연스럽게 변형하라.
- 너무 깔끔한 보고서 문장, 교과서 문장, AI 안내문 같은 말투는 피하라.
- "본 글에서는", "살펴보겠습니다", "알아보겠습니다", "도움이 되시길 바랍니다" 같은 흔한 AI식 표현은 쓰지 마라.
- 이모티콘은 쓰지 마라.
- 과한 감탄사도 쓰지 마라.

[SEO 규칙]
- 상품명 '{p_name}'은 본문에 3~5회만 자연스럽게 포함한다.
- 메인 키워드 '{p_keyword}'는 본문에 4~6회만 자연스럽게 포함한다.
- 키워드를 억지로 반복하지 마라.
- 계절, 사용공간, 선택기준, 관리 편의성, 소음, 크기, 전기요금, 로켓배송, 상세정보 확인 같은 유사 키워드를 자연스럽게 섞어라.
- 제목은 출력하지 말고 본문만 작성한다.
- 해시태그도 본문에 넣지 마라.

[본문 구조 - 아래 순서를 반드시 지켜라]

1. 도입부: 현실적인 생활 문제로 시작
- 첫 문단에서 {problem_scenario} 상황을 자연스럽게 풀어라.
- '{p_keyword}'를 1회 포함하라.
- 상품을 바로 추천하지 말고, 왜 원인 확인이 먼저인지 말하라.
- 광고 느낌으로 시작하지 말고, 독자가 공감할 만한 생활 장면으로 시작하라.

2. 문제가 반복되는 이유
- 독자가 {pain_point} 때문에 헷갈릴 수 있다는 흐름으로 작성하라.
- 계절, 공간, 사용 시간, 보관, 관리, 소음, 크기 중 관련 있는 요소를 2~4개로 나눠 설명하라.
- 이 단계에서는 제품을 사야 한다고 말하지 말고, 먼저 집에서 확인할 원인을 정리하라.
- 이 구간 끝에 아래 마커를 정확히 1회 넣어라.

[사진삽입]

[구분선]

3. 제품을 보기 전에 먼저 확인할 기준
- '{p_name}'을 자연스럽게 언급하되, 문제 해결 후보를 살필 때의 예시처럼 다루어라.
- 강조 포인트 3개를 그대로 복붙하지 말고, 불편 원인을 확인한 뒤 볼 기준으로 풀어라.
- 아래 목록 마커를 정확히 사용하라.

[목록주제]제품을 보기 전 먼저 볼 기준
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
[목록끝]

4. 도움이 될 수 있는 조건과 주의점
- 장점은 생활 속 문제가 어떤 조건에서 줄어들 수 있는지와 연결해서 작성하라.
- {selling_point_1}, {selling_point_2}, {selling_point_3}을 자연스럽게 반영하라.
- 주의점은 반드시 포함하라.
- {caution_note}를 자연스럽게 반영하라.
- 단점은 과하게 부정하지 말고 "이런 경우에는 한 번 더 확인이 필요하다"는 방식으로 써라.
- 감정이 살아있는 문장을 아래 형식으로 1개 넣어라.
- 인용구 안에는 반드시 20자 이상 60자 이하의 완성된 한국어 문장을 넣어라.
- 빈 인용구, 공백만 있는 인용구, 예시 문구가 그대로 남은 인용구는 절대 출력하지 마라.

[인용구]제품보다 먼저 봐야 할 건 우리 집에서 문제가 생기는 이유였습니다[/인용구]

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
- 계절가전이면 용량, 소음, 크기, 전기요금, 설치 조건, 물통 용량, 이동성, 관리 편의성을 우선 고려하라.
- 생활가전이면 사용 공간, 보관성, 세척, 관리, 내구성, 옵션, 배송 조건을 우선 고려하라.

[구분선]

7. 상황별 진단 후 선택 기준
- 무조건 이 상품을 사라고 하지 마라.
- 상황별로 선택 기준을 나눠라.
- 예: 원룸이라면, 가족용이라면, 사무실용이라면, 장마철용이라면, 더위 대비용이라면
- '{p_name}'을 마지막에 1회 자연스럽게 언급하라.

8. 상세정보 확인 단계
- 구매 강요가 아니라 확인 유도형으로 작성하라.
- {cta_text} 방향을 자연스럽게 반영하라.
- 링크는 코드가 별도 정보 확인 구간으로 자동 삽입한다.
- 따라서 아래 링크, 하단 링크, 마지막 링크, 위 링크처럼 위치를 가리키는 표현은 쓰지 마라.
- 본문 안에 URL이나 상품 링크 문장을 직접 만들지 마라.
- 반드시 아래 의미를 포함하라.
  - 현재 가격과 구성은 변동될 수 있음
  - 로켓배송 여부도 상품과 시점에 따라 달라질 수 있음
  - 구매 전 상세정보, 옵션, 후기, 배송 조건을 확인하는 것이 좋음
  - 내 사용 환경에 맞는지 확인 후 선택하는 것이 안전함

[인용구]원인을 나눠보고 나면 상세정보에서 확인할 부분도 훨씬 또렷해집니다[/인용구]

9. FAQ
- 마지막에 실제 검색자가 궁금해할 만한 질문 4개와 실용적인 답변을 작성하라.
- 질문은 "{p_keyword} 보기 전에 무엇부터 확인해야 하나요", "우리 집에 맞는 기준은 무엇인가요", "배송 조건은 어디서 확인하나요" 같은 문제 진단형 검색 의도를 반영하라.
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
- 일반 본문 문장은 한 줄 40자 안팎으로 쓰고, 길어도 45자를 넘기지 마라
- 한 문장을 길게 한 문단으로 늘어쓰지 말고, 의미 단위마다 엔터를 눌러 아래 줄로 내려써라
- 긴 문단으로 쭉 나열하지 말고 2~4줄이 하나의 자연스러운 흐름이 되게 작성하라
- 목록 항목도 너무 짧게 쪼개지 말고 40자 안팎의 자연스러운 호흡으로 쓰며, URL과 마커 형식은 그대로 유지하라

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
- 쿠팡 공식 추천, 판매 1위, 100% 만족, 완벽한 제품 금지
"""
            prompt += "\n\n[언어 규칙]\n- 결과는 반드시 자연스러운 한국어로만 작성할 것\n- 영어 문장, 영어 제목, 영어 작업 메모를 절대 출력하지 말 것"
            raw_content = bot.send_prompt(prompt, max_wait=300)
            if not raw_content:
                return None, None, None, "", None
            
            ad_disclaimer = disclosure_text + "\n\n"
            linked_content = distribute_coupang_links(raw_content, p_name, p_link, cta_text)
            blog_content = ad_disclaimer + linked_content
            
            # 2단계: 해시태그 생성 (사고 모델 → 최대 180초 대기)
            print("   >> #️⃣ 해시태그 생성 중 (사고 모델)...")
            hashtag_prompt = f"""
너는 네이버 블로그 쿠팡파트너스 글의 해시태그를 만드는 실전형 검색 유입 편집자다.
아래 상품과 직접 관련 있는 태그만 10~12개 만들어라.

[상품 정보]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
- 대상 독자: {target_reader}
- 사용 상황: {problem_scenario}
- 사용 장소: {usage_place}
- 시즌/시기: {season_tag}
- 상품군/성격 참고: 계절 생활가전, 집안관리, 생활가전, 구매 전 체크
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
- 계절가전이면 크기, 소음, 전기요금, 설치, 관리, 사용공간, 계절수요 같은 기준을 우선
- 생활가전이면 사용공간, 보관성, 세척, 관리, 내구성, 옵션, 배송 조건을 우선
- 소모품이면 구성, 개수, 보관, 교체주기, 사용장소 같은 기준을 우선

[절대 금지 태그]
- #일상 #소통 #맞팔 #데일리 #오늘 #감성 #리뷰 #후기 #추천템 #핫딜 #최저가 #인생템
- 상품과 무관한 #원룸용 #가정용 #사무실용 #생활가전추천 #계절가전 #가격비교 #구성비교 남발 금지
- 쿠팡, 쿠팡파트너스, 광고, 협찬, 로켓배송만 단독으로 강조하는 태그 금지

[출력 규칙]
- '#태그' 형식만 사용
- 정확히 10~12개
- 한 줄에 공백으로 구분
- 설명 금지
- 영어 태그 금지
- 같은 의미의 태그 반복 금지
- 상품과 직접 관련 없는 태그 금지

출력 예시 형식
#메인키워드 #품목명 #구매전체크 #크기확인 #소음체크 #관리편의성 #사용공간 #비교기준 #상세정보확인 #구매전확인
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

[황금 키워드 추출 방식]
- 상품명은 키워드 분석용 원재료일 뿐, 상품명은 제목에 쓰지 않는다.
- 먼저 상품명에서 브랜드명, 모델명, 영문/숫자 코드, 용량, 수량, 색상, 구성 옵션을 빼고 독자가 실제로 검색할 일반 품목명만 남긴다.
- 메인 키워드, 대상 독자, 사용 상황, 사용 장소, 본문 일부를 함께 보고 검색 수요는 넓지만 공급이 너무 많은 단독 단어는 피한다.
- 너무 넓은 단어만 쓰면 공급이 많아 불리하다. 예: 선풍기, 에어컨, 커피, 세제처럼 품목명 1단어만 쓰지 마라.
- 너무 좁은 상품명, 브랜드명, 모델명, 용량 조합은 검색 수요가 작으니 제목에 넣지 마라.
- 내부적으로 후보를 3~5개 만든 뒤, 품목명 + 상황/고민 + 선택 기준이 함께 보이는 황금 키워드를 제목 앞쪽에 배치한다.
- 실제 검색량이나 문서 수 수치는 확인하지 못하므로 검색량 많음, 공급 적음 같은 설명은 출력하지 않는다.

[본문 일부]
{blog_content[:900]}

[제목 원칙]
- 상품명은 제목에 쓰지 않는다.
- '{p_keyword}'도 상품명에 가까우면 그대로 넣지 말고 일반 검색 키워드로 바꿔라.
- 최종 제목 앞쪽에는 분석해서 뽑은 황금 키워드를 자연스럽게 넣어라.
- 구매 전 확인할 조건이 제목에서 보여야 한다.
- 상품군에 맞는 생활 문제와 사용 환경이 보여야 한다.
- 원룸, 가정용, 사무실용, 장마철, 여름 대비, 겨울 대비, 소음, 크기, 전기요금, 관리, 설치 조건, 보관, 용량, 교체주기, 비교 기준 중 문맥에 맞는 표현을 활용하라.
- 광고성 제목보다 정보형 제목으로 작성하라.
- 실제 사용한 것처럼 오해될 제목은 피하라.
- "직접 써보니", "내돈내산", "결국 정착", "인생템", "역대급", "무조건", "최저가"는 쓰지 마라.
- 매번 같은 구조가 반복되지 않도록 문장 순서를 변형하라.
- 클릭은 끌되 과장은 하지 마라.

[금지 제목 패턴]
{chr(10).join("- " + item for item in title_forbidden_patterns)}

[가능한 제목 방향 예시]
- 품목명 고를 때 먼저 볼 크기소음관리 기준
- 사용 장소에 맞는 품목명 선택 전 확인할 점
- 계절 고민 있을 때 품목명 비교 체크포인트
- 생활용품 구매 전 비교할 보관용량관리 기준
- 품목명 고민될 때 먼저 확인할 사용 환경 기준
- 원룸에서 품목명 고를 때 놓치기 쉬운 기준
- 계절가전 구매 전 보는 크기소음전기요금 기준

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
        print("   >> 🌐 Gemini에서 이미지 생성 시작...")
        bot.new_chat()
        result_path = bot.generate_image(img_description, img_path)
        if not result_path:
            img_path = None
            if post_type == "쿠팡":
                print("   >> [에러] 쿠팡 글 이미지를 생성하지 못해 이번 발행은 중단합니다.")
                return None, None, None, "", None
            
        p_name_val = p_name if post_type == '쿠팡' else ""
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

            # 사진 업로드 (일상글만 본문 앞에 배치, 쿠팡글은 [사진삽입] 위치에서 삽입)
            if post_type != '쿠팡' and img_path and os.path.exists(img_path):
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
            bold_triggers = ['쿠팡 파트너스', '구매 링크', '제품 상세정보', '───']
            section_emojis = ['✨', '📌', '👍', '💡', '⭐', '🛒']
            cta_triggers = ['바로가기', '쿠팡링크', '상세정보', '구매 링크']

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
                if '[사진삽입]' in line_s and post_type == '쿠팡':
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
                    # 인용구 탈출 (방향키 ↓ ↓ + 엔터 1회)
                    if quote_inserted:
                        actions.send_keys(Keys.ARROW_DOWN).perform()
                        time.sleep(0.2)
                        actions.send_keys(Keys.ARROW_DOWN).perform()
                        time.sleep(0.2)
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
                    # 인용구 탈출 (방향키 ↓ ↓ + 엔터 1회)
                    if quote_inserted:
                        actions.send_keys(Keys.ARROW_DOWN).perform()
                        time.sleep(0.2)
                        actions.send_keys(Keys.ARROW_DOWN).perform()
                        time.sleep(0.2)
                    actions.send_keys(Keys.ENTER).perform()
                    time.sleep(0.2)
                    force_sync_state()
                    reset_formatting()
                    continue

                # 📌 구조 ③: 번호 + 큰 글씨 (소제목) 
                is_section_title = any(line_s.startswith(e) for e in section_emojis) or \
                                   (line_s and line_s[0] in '①②③④⑤⑥⑦⑧⑨⑩') or \
                                   (len(line_s)>2 and line_s[0].isdigit() and line_s[1] == '.')
                
                is_disclaimer = '쿠팡 파트너스 활동의 일환' in line_s or '수수료를 제공받습니다' in line_s
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
    """post_type: '일상' 또는 '쿠팡' — 전역 naver_bot 사용 (클립보드 충돌 방지 락 포함)"""
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
        print("   >> 🤖 Gemini 웹에서 콘텐츠를 생성 중...")
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
            if post_type == "쿠팡" and product_state:
                mark_coupang_product_as_used(csv_file_path, product_state, blog_title)
            msg = f"✅ [{post_type}] 발행 성공! 제목: {blog_title[:30]}...\n(오늘: 일상 {daily_stats['일상']}건, 쿠팡 {daily_stats['쿠팡']}건)"
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
# 6. 랜덤 스케줄 생성 (하루 10건: 일상 5 + 쿠팡 5)
# =============================================================
def generate_daily_schedule():
    """
    하루 24시간을 10개의 랜덤 시간으로 나누고,
    일상 5건 + 쿠팡 5건을 랜덤으로 섞어 배치
    """
    # 기존 스케줄 전부 제거
    schedule.clear()
    
    # 오늘 통계 초기화
    daily_stats["일상"] = 0
    daily_stats["쿠팡"] = 0
    daily_stats["에러"] = 0
    
    # 00:30 ~ 23:30 사이에서 1분 단위 후보를 쓰되, 자체 작업끼리는 최소 15분 간격 유지
    candidate_minutes = list(range(30, 1410, 1))
    random_minutes = []
    for _ in range(2000):
        temp = sorted(random.sample(candidate_minutes, 10))
        if all(temp[i + 1] - temp[i] >= 15 for i in range(9)):
            random_minutes = temp
            break
    if not random_minutes:
        random_minutes = sorted(random.sample(candidate_minutes, 10))
    
    # 글 종류 배정: 일상 5 + 쿠팡 5 → 섞기
    post_types = ['일상'] * 5 + ['쿠팡'] * 5
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
        
        emoji = "🌸" if p_type == "일상" else "🛒"
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
            selected_post_type = input("📝 발행할 글 종류를 입력하세요 (일상/쿠팡, 엔터 시 쿠팡): ").strip() or "쿠팡"
        if selected_post_type not in ("일상", "쿠팡"):
            raise RuntimeError("글 종류는 '일상' 또는 '쿠팡'만 사용할 수 있습니다.")

        print(f"\n🚀 [1회 실행] '{selected_post_type}' 글 1건 발행을 시작합니다.\n")
        publish_one_post(selected_post_type)
    
    except KeyboardInterrupt:
        print(f"\n\n🛑 프로그램을 수동 종료합니다.")
        send_telegram(f"🛑 프로그램 수동 종료\n오늘 결과: 일상 {daily_stats['일상']}건, 쿠팡 {daily_stats['쿠팡']}건, 에러 {daily_stats['에러']}건")
    
    except Exception as e:
        print(f"\n\n🚨 치명적 에러: {e}")
        send_telegram(f"🚨 치명적 에러로 프로그램 종료!\n에러: {e}")
    
    finally:
        if naver_bot:
            naver_bot.close()
        print(f"   오늘 결과: 일상 {daily_stats['일상']}건, 쿠팡 {daily_stats['쿠팡']}건, 에러 {daily_stats['에러']}건")
        if scheduled_log_file:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            scheduled_log_file.close()
