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
from PIL import Image
from io import BytesIO
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
import urllib.parse
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
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
    """항상 skssj2628 폴더 내부의 skssj2628_db.csv 파일을 강제로 사용한다."""
    return os.path.join(BASE_DIR, "skssj2628_db.csv")


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

    id_profile = os.path.join(BASE_DIR, f"ChromeNaverBot_{sanitize_profile_name(naver_id)}")

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
        "naver_id": "skssj2628",
        "naver_password": "bh4563",
        "csv_file_path": (args.csv_path or resolve_default_csv_path()).strip(),
    }

    if not settings["csv_file_path"]:
        settings["csv_file_path"] = resolve_default_csv_path()

    if not args.scheduled and not args.csv_path and not os.getenv("COUPANG_CSV_PATH", ""):
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
        "벚꽃 시즌 산책 루틴",
        "봄맞이 방 정리와 옷장 정돈",
        "햇살 좋은 날 동네 카페 탐방",
        "봄비 오는 날 집콕 취미",
        "새로운 계획을 세우는 기분",
    ],
    "여름": [
        "무더위 피하는 하루 루틴",
        "에어컨과 선풍기 사이의 현실 고민",
        "장마철 집안 관리와 기분 전환",
        "저녁 산책과 야식의 유혹",
        "한낮 더위를 버티는 소소한 팁",
    ],
    "가을": [
        "선선한 날씨에 걷고 싶어지는 동네",
        "가을 감성 카페와 혼자만의 시간",
        "옷차림이 애매한 환절기 일상",
        "책 읽기 좋은 계절의 루틴",
        "해 질 무렵 산책하며 든 생각",
    ],
    "겨울": [
        "추운 날 집에서 보내는 저녁",
        "패딩 입고 나간 동네 산책",
        "연말 분위기와 소소한 소비",
        "난방 때문에 고민되는 하루",
        "추운 계절에 더 생각나는 음식",
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
    "가벼운 러닝이나 산책 챌린지",
    "저속노화 식단이나 건강 루틴에 대한 관심",
    "무지출 또는 절약 습관 기록",
    "집 정리와 미니멀한 생활",
    "혼자 보내는 시간의 만족감",
    "동네 안에서 작은 즐거움을 찾는 흐름",
    "짧고 자주 기록하는 콘텐츠 습관",
    "디카 감성이나 아날로그 취미",
    "카페 대신 집에서 즐기는 홈카페",
    "하루 컨디션을 관리하는 현실 루틴",
]

DAILY_SCENE_BANK = [
    "출근 전 잠깐의 여유",
    "점심시간에 혼자 걷는 순간",
    "퇴근 후 바로 집에 들어가기 아쉬운 시간",
    "주말 오후 늦잠 후 시작한 하루",
    "할 일을 미루다가 갑자기 몰아서 처리한 저녁",
    "빨래와 청소를 끝내고 앉은 순간",
    "약속 없는 날 혼자 보내는 오후",
    "배달 대신 직접 챙겨 먹은 한 끼",
]

PHOTO_STYLE_BANK = [
    "20대 성인 한국인 여자가 자연스럽게 등장하는 현실적인 일상 스냅 사진",
    "20대 성인 한국인 여자가 편안하게 머무는 따뜻한 자연광 사진",
    "20대 성인 한국인 여자가 생활 속에 자연스럽게 보이는 블로그용 라이프스타일 사진",
    "20대 성인 한국인 여자의 동네 산책이나 카페 기록처럼 보이는 사진",
]

DAILY_CATEGORY_BANK = [
    "계절생활문제",
    "건강루틴",
    "절약소비",
    "집안관리",
    "식품장보기",
    "생활뉴스해석",
]

DAILY_SEARCH_INTENT_BANK = {
    "계절생활문제": [
        {
            "search_phrase": "봄 환절기 옷차림",
            "reader_problem": "아침저녁 기온차 때문에 뭘 입어야 할지 애매한 상황",
            "reader_promise": "겉옷, 이너, 가방 속 준비물까지 하루 동선을 기준으로 정리",
            "practical_points": ["아침 최저기온과 낮 최고기온을 같이 보기", "벗고 들고 다니기 쉬운 겉옷 고르기", "실내 냉난방까지 고려해 얇은 옷을 겹쳐 입기"],
            "mistakes_to_avoid": ["낮 기온만 보고 너무 얇게 입기", "예쁜 옷만 보고 이동 시간을 빼먹기"],
            "faq_questions": ["환절기에는 외투를 꼭 챙기는 게 좋을까?", "출근길과 퇴근길 온도 차가 클 때는 어떻게 입을까?"],
        },
        {
            "search_phrase": "장마철 집안 습기 관리",
            "reader_problem": "비 오는 날 빨래 냄새와 방 안 눅눅함이 계속 신경 쓰이는 상황",
            "reader_promise": "환기 시간, 빨래 간격, 제습 위치를 현실적인 집 기준으로 정리",
            "practical_points": ["비가 그친 직후 짧게 맞바람 환기하기", "젖은 수건과 빨래를 한곳에 오래 두지 않기", "옷장과 신발장처럼 닫힌 공간을 먼저 관리하기"],
            "mistakes_to_avoid": ["창문을 종일 닫아두고 방향제만 쓰기", "마르지 않은 빨래를 바로 접어 넣기"],
            "faq_questions": ["장마철에는 환기를 언제 하는 게 나을까?", "빨래 냄새가 날 때 가장 먼저 확인할 것은 뭘까?"],
        },
        {
            "search_phrase": "겨울 난방비 아끼는 생활 습관",
            "reader_problem": "춥다고 계속 난방을 올리기에는 관리비가 부담되는 상황",
            "reader_promise": "온도 설정, 보온 동선, 창가 관리처럼 바로 바꿀 수 있는 습관 정리",
            "practical_points": ["방 전체보다 오래 머무는 공간부터 따뜻하게 만들기", "창가와 문틈에서 새는 냉기를 먼저 막기", "외출 전후 온도 설정을 습관처럼 확인하기"],
            "mistakes_to_avoid": ["난방 온도만 계속 올리기", "얇은 실내복으로 버티다 난방을 과하게 쓰기"],
            "faq_questions": ["난방비를 줄이려면 무엇부터 바꾸는 게 좋을까?", "방이 금방 식을 때 확인할 부분은 어디일까?"],
        },
    ],
    "건강루틴": [
        {
            "search_phrase": "피곤할 때 컨디션 회복 루틴",
            "reader_problem": "잠을 자도 몸이 무겁고 하루 집중력이 떨어지는 상황",
            "reader_promise": "수면, 물, 걷기, 식사 시간을 무리 없이 다시 맞추는 방법 정리",
            "practical_points": ["아침 햇빛을 짧게라도 보기", "카페인 마시는 시간을 오후 늦게 넘기지 않기", "밤에 할 일을 줄이고 잠들기 전 루틴을 단순하게 만들기"],
            "mistakes_to_avoid": ["피곤하다고 카페인으로만 버티기", "주말에 몰아서 자면 해결된다고 생각하기"],
            "faq_questions": ["피곤한 날 운동을 해도 괜찮을까?", "컨디션이 떨어질 때 가장 먼저 줄일 습관은 뭘까?"],
        },
        {
            "search_phrase": "걷기 운동 꾸준히 하는 법",
            "reader_problem": "운동을 시작해도 며칠 지나면 귀찮아서 흐지부지되는 상황",
            "reader_promise": "시간, 코스, 기록 부담을 낮춰 일상 속에서 걷기를 이어가는 방법 정리",
            "practical_points": ["처음부터 긴 코스보다 10분 코스부터 정하기", "출퇴근이나 장보기 동선에 걷기를 끼워 넣기", "걸음 수보다 나간 횟수를 먼저 기록하기"],
            "mistakes_to_avoid": ["첫날부터 무리해서 오래 걷기", "비 오는 날 한 번 쉬었다고 포기하기"],
            "faq_questions": ["걷기는 하루에 얼마나 해야 부담이 적을까?", "혼자 걷기가 지루할 때는 어떻게 이어갈까?"],
        },
        {
            "search_phrase": "수면 습관 바꾸는 법",
            "reader_problem": "늦게 자는 습관 때문에 아침마다 몸이 무거운 상황",
            "reader_promise": "잠드는 시간보다 저녁 루틴을 먼저 바꾸는 현실적인 방법 정리",
            "practical_points": ["잠들기 1시간 전 할 일을 줄이기", "침대에서 보는 콘텐츠 시간을 제한하기", "기상 시간을 크게 흔들지 않기"],
            "mistakes_to_avoid": ["하루 만에 수면 시간을 크게 당기기", "침대에서 업무나 쇼핑까지 같이 하기"],
            "faq_questions": ["잠이 안 올 때 억지로 누워 있어도 될까?", "수면 루틴은 며칠 정도 봐야 할까?"],
        },
    ],
    "절약소비": [
        {
            "search_phrase": "무지출 챌린지 현실적으로 하는 법",
            "reader_problem": "무지출을 해보고 싶지만 커피, 배달, 편의점 지출에서 자꾸 무너지는 상황",
            "reader_promise": "무조건 참는 방식이 아니라 대체 행동과 예외 기준을 정리",
            "practical_points": ["돈 쓰기 쉬운 시간대를 먼저 찾기", "완전 금지보다 허용 예산을 작게 정하기", "배달 대신 집에 있는 재료를 먼저 확인하기"],
            "mistakes_to_avoid": ["처음부터 한 달 무지출을 목표로 잡기", "실패한 날 기록을 멈춰버리기"],
            "faq_questions": ["무지출 챌린지는 며칠부터 시작하는 게 좋을까?", "커피값은 어떻게 줄이면 덜 스트레스 받을까?"],
        },
        {
            "search_phrase": "배달비 줄이는 방법",
            "reader_problem": "한 끼만 시켜도 배달비와 최소주문금액 때문에 지출이 커지는 상황",
            "reader_promise": "식사 계획, 묶음 주문, 대체 메뉴 기준으로 생활비를 줄이는 방법 정리",
            "practical_points": ["배달이 몰리는 요일과 시간을 피하기", "냉장고에 바로 먹을 수 있는 대체식을 준비하기", "쿠폰보다 최종 결제 금액을 먼저 보기"],
            "mistakes_to_avoid": ["할인 쿠폰 때문에 필요 없는 메뉴까지 담기", "배달비만 보고 음식값 합계를 놓치기"],
            "faq_questions": ["배달을 완전히 끊지 않아도 생활비를 줄일 수 있을까?", "혼자 살 때 배달비 부담을 줄이는 기준은 뭘까?"],
        },
        {
            "search_phrase": "장보기 지출 줄이는 기준",
            "reader_problem": "마트나 온라인 장보기를 하고 나면 예상보다 결제 금액이 커지는 상황",
            "reader_promise": "냉장고 재고, 소비 속도, 보관 기간을 기준으로 사야 할 것만 고르는 방법 정리",
            "practical_points": ["장보기 전 냉장고 사진을 찍어 확인하기", "대용량은 가격보다 소비 속도부터 계산하기", "이번 주 안에 먹을 메뉴를 2~3개만 정하기"],
            "mistakes_to_avoid": ["싸다는 이유로 보관 어려운 식품을 많이 사기", "이미 있는 양념과 소스를 또 사기"],
            "faq_questions": ["대용량 식품은 언제 사는 게 이득일까?", "장보기 목록은 얼마나 자세히 적어야 할까?"],
        },
    ],
    "집안관리": [
        {
            "search_phrase": "방 정리 순서",
            "reader_problem": "정리를 시작해도 어디부터 손대야 할지 몰라 금방 지치는 상황",
            "reader_promise": "버리기, 분류, 배치 순서를 작은 방 기준으로 정리",
            "practical_points": ["바닥에 나온 물건부터 한곳에 모으기", "자주 쓰는 물건과 가끔 쓰는 물건을 먼저 나누기", "수납용품은 정리 후 부족한 만큼만 사기"],
            "mistakes_to_avoid": ["정리 전에 수납함부터 사기", "추억 물건부터 꺼내 시간을 다 쓰기"],
            "faq_questions": ["방 정리는 어디부터 시작해야 덜 힘들까?", "버릴지 말지 애매한 물건은 어떻게 판단할까?"],
        },
        {
            "search_phrase": "빨래 냄새 줄이는 법",
            "reader_problem": "빨래를 했는데도 수건이나 옷에서 꿉꿉한 냄새가 나는 상황",
            "reader_promise": "세탁물 보관, 세탁기 관리, 건조 시간을 기준으로 원인을 줄이는 방법 정리",
            "practical_points": ["젖은 빨래를 세탁 전 오래 쌓아두지 않기", "세탁 후 바로 꺼내 넓게 말리기", "세제 양을 늘리기보다 헹굼과 건조를 확인하기"],
            "mistakes_to_avoid": ["냄새 난다고 섬유유연제만 많이 넣기", "세탁기 문을 항상 닫아두기"],
            "faq_questions": ["수건 냄새는 세제 문제일까 건조 문제일까?", "빨래를 밤에 널어도 괜찮을까?"],
        },
        {
            "search_phrase": "원룸 청소 루틴",
            "reader_problem": "공간이 좁은데도 금방 어지러워지고 청소가 밀리는 상황",
            "reader_promise": "매일 10분, 주 1회, 월 1회로 나눠 부담을 줄이는 청소 기준 정리",
            "practical_points": ["매일 바닥 물건만 제자리로 보내기", "주 1회 욕실과 주방을 한 번에 점검하기", "한 달에 한 번 버릴 물건을 따로 모으기"],
            "mistakes_to_avoid": ["하루에 전부 끝내려고 미루기", "청소 도구를 너무 많이 사서 보관만 늘리기"],
            "faq_questions": ["원룸 청소는 몇 분씩 나눠 하는 게 좋을까?", "좁은 방이 금방 지저분해지는 이유는 뭘까?"],
        },
    ],
    "식품장보기": [
        {
            "search_phrase": "간편식 고르는 기준",
            "reader_problem": "바쁠 때 먹으려고 산 간편식이 입맛이나 양에 안 맞아 남는 상황",
            "reader_promise": "보관, 조리 시간, 한 끼 포만감 기준으로 실패를 줄이는 방법 정리",
            "practical_points": ["냉장고와 냉동실 여유 공간 먼저 확인하기", "조리도구가 필요한지 미리 보기", "한 번에 많이 사기보다 자주 먹는 맛부터 확인하기"],
            "mistakes_to_avoid": ["후기만 보고 대용량부터 사기", "조리 시간이 짧아도 뒷정리를 빼먹기"],
            "faq_questions": ["간편식은 냉장과 냉동 중 어떤 걸 먼저 고를까?", "혼자 살 때 대용량 간편식은 언제 괜찮을까?"],
        },
        {
            "search_phrase": "생수 대량구매 체크포인트",
            "reader_problem": "생수를 한 번에 많이 사면 가격은 좋은데 보관과 배송이 부담되는 상황",
            "reader_promise": "용량, 보관 장소, 마시는 속도를 기준으로 대량구매 판단법 정리",
            "practical_points": ["하루 물 소비량을 대략 계산하기", "문 앞에서 보관 장소까지 옮기는 동선을 생각하기", "작은 병과 큰 병의 쓰임을 나눠 보기"],
            "mistakes_to_avoid": ["최저가만 보고 너무 많이 주문하기", "보관 장소를 정하지 않고 쌓아두기"],
            "faq_questions": ["생수는 몇 병 단위로 사는 게 부담이 적을까?", "작은 병과 큰 병 중 어떤 게 생활에 맞을까?"],
        },
        {
            "search_phrase": "계란 고르는 법",
            "reader_problem": "계란 종류와 수량이 많아 어떤 걸 사야 할지 헷갈리는 상황",
            "reader_promise": "소비 속도, 보관 기간, 조리 용도를 기준으로 고르는 방법 정리",
            "practical_points": ["일주일 안에 먹을 개수를 먼저 계산하기", "삶아 먹을지 요리에 쓸지 용도를 나누기", "보관 공간과 유통기한을 같이 확인하기"],
            "mistakes_to_avoid": ["가격만 보고 너무 많은 판을 사기", "자주 안 먹는데 대용량을 고르기"],
            "faq_questions": ["계란은 몇 구 단위로 사는 게 좋을까?", "혼자 살 때 계란을 남기지 않으려면 어떻게 할까?"],
        },
    ],
    "생활뉴스해석": [
        {
            "search_phrase": "물가 뉴스 생활비 관리",
            "reader_problem": "물가가 올랐다는 말은 많은데 실제로 어디서 줄여야 할지 막막한 상황",
            "reader_promise": "뉴스를 그대로 옮기지 않고 내 장보기와 고정지출에 연결해 보는 방법 정리",
            "practical_points": ["최근 결제 내역에서 반복 지출 찾기", "가격이 오른 품목은 대체재를 하나 정해두기", "한 달 예산보다 이번 주 지출부터 조정하기"],
            "mistakes_to_avoid": ["뉴스를 보고 불안해서 무조건 소비를 끊기", "작은 자동결제와 편의점 지출을 무시하기"],
            "faq_questions": ["물가가 오를 때 생활비는 어디서 먼저 줄일까?", "절약을 해도 답답하지 않게 하려면 어떻게 할까?"],
        },
        {
            "search_phrase": "날씨 뉴스 외출 준비",
            "reader_problem": "날씨 예보를 봐도 옷차림과 가방 준비가 매번 헷갈리는 상황",
            "reader_promise": "비, 바람, 기온차에 따라 외출 전에 확인할 포인트 정리",
            "practical_points": ["기온보다 체감 온도와 바람을 같이 보기", "우산, 얇은 겉옷, 여분 양말처럼 불편을 줄이는 물건 챙기기", "하루 중 가장 오래 밖에 있는 시간대를 기준으로 준비하기"],
            "mistakes_to_avoid": ["오전 날씨만 보고 하루 준비를 끝내기", "가방이 무거워 싫다고 꼭 필요한 물건까지 빼기"],
            "faq_questions": ["비 예보가 애매할 때 우산을 챙겨야 할까?", "바람 부는 날에는 어떤 옷차림이 덜 불편할까?"],
        },
        {
            "search_phrase": "소비 트렌드 절약 습관",
            "reader_problem": "유행하는 소비를 따라가다 보면 만족감보다 결제 피로가 커지는 상황",
            "reader_promise": "요즘 트렌드를 즐기되 내 예산 안에서 조절하는 기준 정리",
            "practical_points": ["따라 하고 싶은 소비를 저장만 해두고 하루 뒤 다시 보기", "경험 소비와 물건 소비를 나눠 예산 잡기", "한 번 쓰고 끝날 물건은 대여나 공유를 먼저 생각하기"],
            "mistakes_to_avoid": ["유행이 지나가기 전에 사야 한다고 조급해하기", "후기 많은 상품을 내 생활에 맞는지 확인하지 않기"],
            "faq_questions": ["트렌드를 즐기면서도 돈을 덜 쓰는 방법은 뭘까?", "충동구매를 줄이려면 구매 전에 무엇을 물어봐야 할까?"],
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
    "MBTI별 추천 주식 성향을 재미있게 풀어보기",
    "오늘 뉴스와 내 소비 습관을 엮어보기",
    "날씨와 투자 심리를 억지로 연결해보는 잡생각",
    "건강 루틴과 업무 효율을 주식 차트처럼 설명하기",
    "카페 소비 패턴과 MBTI를 엮은 관찰기",
    "운동 습관과 투자 멘탈을 비교해보는 글",
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
        "post_angle": "식품이나 소모품을 살 때 생활 속 불편을 줄이는 구매 전 기준을 정리하는 글",
        "title_seed": "어떤 상황에서 이 상품군을 확인하면 좋은지 드러나는 제목",
        "thumbnail_prompt": "집 안에서 실제 문제를 해결하는 순간이 보이는 장면",
        "cta_text": "비슷한 고민이 있었다면 상세 정보부터 가볍게 확인해보면 좋겠다",
    },
    {
        "name": "비교고민정리형",
        "post_angle": "비슷한 식품이나 소모품을 비교할 때 놓치기 쉬운 기준을 정리하는 글",
        "title_seed": "비교 전에 먼저 봐야 할 조건이 드러나는 제목",
        "thumbnail_prompt": "여러 선택지 중 하나를 고르는 현실적인 책상이나 거실 장면",
        "cta_text": "구성, 용량, 보관 조건을 같이 비교해보면 판단이 쉬워진다는 흐름",
    },
    {
        "name": "자취실사용형",
        "post_angle": "자취방, 사무실, 작은 주방 기준으로 보관과 소비 속도를 따져보는 글",
        "title_seed": "작은 공간에서 구매 전에 볼 조건이 보이는 제목",
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
    if month in (3, 4, 5):
        return "봄"
    if month in (6, 7, 8):
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
        "경험담으로 시작해 해결 기준으로 확장하는 글",
        "실수담을 짧게 넣고 체크리스트로 정리하는 글",
        "생활 장면은 가볍게, 실천 팁은 구체적으로 쓰는 글",
        "검색자가 바로 따라 할 수 있는 순서형 글",
    ])
    intent_candidates = DAILY_SEARCH_INTENT_BANK.get(content_category) or DAILY_SEARCH_INTENT_BANK["계절생활문제"]
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

    return f"""
당신은 네이버에서 오래 활동한 생활 정보형 블로거입니다.
이번 글은 겉으로는 자연스러운 일상글처럼 읽히지만, 실제로는 검색자가 문제를 해결하고 저장하고 싶어지는 생활 정보글이어야 합니다.
무가치한 하루 기록, 감정만 있는 일기, 카페에 갔다 온 이야기로 끝나는 글은 금지입니다.

[이번 글 컨텍스트]
- 날짜 감각: {daily_context['now_label']}
- 콘텐츠 카테고리: {daily_context['content_category']}
- 계절: {daily_context['season']}
- 요일 분위기: {daily_context['day_type']}
- 날씨 키워드: {daily_context['weather_key']}
- 날씨에서 출발한 기분: {daily_context['weather_mood']}
- 핵심 검색어: {daily_context['search_phrase']}
- 독자 고민: {daily_context['reader_problem']}
- 글에서 해결해줄 약속: {daily_context['reader_promise']}
- 생활형 보조 주제: {daily_context['seasonal_topic']}
- 건강 메모 주제: {daily_context['health_topic']}
- 경제 메모 주제: {daily_context['economy_topic']}
- 뉴스 정리 주제: {daily_context['news_topic']}
- 재밌는 조합 주제: {daily_context['combo_topic']}
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

[작성 핵심 원칙]
- 일상 장면은 도입과 연결에만 사용하고, 본문 중심은 구체적인 해결책과 판단 기준으로 채우세요.
- 글 비중은 생활 장면 30%, 실천 정보 70% 정도로 맞추세요.
- 핵심 검색어는 제목 없이도 본문 첫 300자 안에 자연스럽게 1회 넣고, 중간과 마무리에 변형 표현으로 1~2회 더 넣으세요.
- 독자가 글을 읽고 바로 따라 할 행동을 최소 4개 이상 제시하세요.
- 추상적인 조언 대신 언제, 어디서, 무엇을, 어떤 순서로 하면 좋은지 구체적으로 쓰세요.
- 본인이 실제로 구매하거나 사용한 것처럼 단정하지 말고, 생활 속에서 확인해볼 기준을 정리하는 톤으로 쓰세요.
- 네이버에서 검색해 들어온 사람이 빠르게 답을 찾을 수 있도록 소제목처럼 보이는 짧은 문장을 중간중간 넣어주세요.
- 트렌드 키워드는 억지로 설명하지 말고, 내 생활에서 왜 이 주제가 신경 쓰였는지 연결하는 정도로만 사용하세요.
- 날씨는 단순 배경이 아니라 행동 선택이나 불편 해결의 계기로 연결하세요.
- 실제 사람이 쓴 것처럼 자연스럽고, 약간의 망설임이나 생활감 있는 표현을 섞어주세요.
- AI 설명투, 과하게 모범적인 문장, 광고 같은 문장, 의미 없는 감성 문장은 피하세요.
- 뉴스/경제/주식이 나오더라도 확인되지 않은 수치, 종목 가격, 속보, 단정적 투자 추천은 꾸며내지 마세요.

[본문 구조]
- 시작: 독자가 공감할 문제 상황과 오늘의 실제 장면을 짧게 연결
- 문제 정리: 왜 이 주제가 요즘 생활에서 자주 검색될 만한지 설명
- 기준 제시: 상황별로 확인할 기준을 3가지 이상 구체적으로 정리
- 실천 순서: 오늘 바로 해볼 수 있는 행동을 순서대로 안내
- 흔한 실수: 독자가 놓치기 쉬운 부분을 짧게 짚기
- 자주 묻는 질문: 위 질문 2개에 자연스럽게 답하기
- 마무리: 오늘 내 생활에 적용할 한 줄 기준으로 정리

[출력 규칙]
- 인사말부터 마무리까지 블로그 본문만 출력
- 1500자 이상
- 자연스러운 한국어만 사용
- 영어 문장, 영어 제목 후보, 작업 메모 금지
- 마크다운 서식 금지
- 제목, 해시태그, 키워드 목록은 출력하지 말 것
- 확인되지 않은 수치나 외부 기사 내용을 지어내지 말 것

[서식 마킹 규칙 - 반드시 지킬 것]
- 글의 주요 흐름이 바뀌는 지점 2~3곳에 [구분선] 한 줄만 넣기
- 감정이 살아 있는 문장 1~2개는 [인용구]문장내용[/인용구] 형식으로 넣기
- 인용구의 문장내용은 반드시 20자 이상 60자 이하의 완성된 한국어 문장으로 작성하기
- [인용구][/인용구], [인용구] [/인용구], [인용구]문장내용[/인용구]처럼 비어 있거나 예시 문구가 남은 인용구는 절대 출력하지 말 것
- 쓸 만한 인용 문장이 없으면 빈 인용구를 만들지 말고 인용구 자체를 생략할 것
- 위 마킹은 정확한 형태로만 출력
"""


def build_daily_image_prompt(daily_context):
    return (
        f"{daily_context['photo_style']}, {daily_context['season']} 분위기, "
        f"{daily_context['weather_key']} 느낌, {daily_context['daily_scene']}, "
        f"{daily_context['seasonal_topic']}를 연상시키는 장면, "
        "20대 성인 한국인 여자가 반드시 등장하고 자연스러운 표정과 생활감이 보이는 사진, "
        "인물이 신뢰감을 주되 과하게 모델처럼 연출되지 않은 현실적인 네이버 블로그 사진"
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
    method = "POST"
    path = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    sub_id = os.getenv("COUPANG_SUB_ID", "").strip()
    
    payload = {
        "coupangUrls": [original_url]
    }
    if sub_id:
        payload["subId"] = sub_id
        
    try:
        result = call_coupang_api(method, path, payload)
        data = result.get("data") or []
        if data and len(data) > 0:
            return data[0].get("shortenUrl") or original_url
    except Exception as e:
        print(f"   >> [안내] 딥링크 생성 실패: {e}")
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

    # 점수순 정렬 후 순차적으로 딥링크 변환 시도
    candidate_scores.sort(key=lambda x: x["score"], reverse=True)
    
    for candidate in candidate_scores:
        idx = candidate["index"]
        selected_row = rows[idx].copy()  # 원본 훼손 방지
        seed_key = get_coupang_product_key(selected_row)
        original_url = get_product_field(selected_row, "상품원본URL", "쿠팡링크")
        
        if not get_product_field(selected_row, "상품명") or not original_url:
            continue
            
        if api_enabled:
            shorten_url = generate_coupang_deeplink(original_url)
            if shorten_url and shorten_url != original_url:
                selected_row["상품원본URL"] = selected_row.get("상품원본URL") or original_url
                selected_row["쿠팡링크"] = shorten_url
                print(f"   >> 쿠팡 딥링크 변환 성공: {shorten_url}")
                
                return {
                    "selected_index": idx,
                    "selected_row": selected_row,
                    "selected_group": candidate["group"],
                    "seed_key": seed_key,
                }
            else:
                print(f"   >> [주의] 딥링크 변환 실패 (원본 링크 사용 불가): {selected_row.get('상품명')}")
                continue  # 변환 실패 시 원본 링크 쓰지 않고 다음 상품으로 넘어감!
        else:
            # API를 사용하지 않는 환경이라면 그냥 반환 (직접 파트너스 링크를 넣은 경우)
            return {
                "selected_index": idx,
                "selected_row": selected_row,
                "selected_group": candidate["group"],
                "seed_key": seed_key,
            }

    raise RuntimeError("모든 쿠팡 상품 후보의 딥링크 변환이 실패했거나 유효한 상품이 없습니다. API 상태나 CSV 링크를 확인하세요.")


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


def build_coupang_link_block(label, message, product_name, product_link):
    return (
        f"{'─' * 25}\n\n"
        f"{label}\n"
        f"{message}\n"
        f"🛒 {product_name}\n"
        f"{product_link}"
    )


def distribute_coupang_links(raw_content, product_name, product_link, cta_text):
    paragraphs = [part.strip() for part in raw_content.split("\n\n") if part.strip()]
    if not paragraphs:
        return raw_content

    custom_cta = (cta_text or "").strip()
    mid_message = custom_cta or "구성, 용량, 보관 조건이 궁금해졌다면 상세 정보에서 한 번 더 확인해보면 좋다"
    bottom_message = "가격, 옵션, 후기, 배송 조건은 변동될 수 있으니 마지막에는 상세페이지에서 한 번 더 확인하는 편이 좋다"

    mid_block = build_coupang_link_block("관련 정보 확인", mid_message, product_name, product_link)
    bottom_block = build_coupang_link_block("가격과 후기 확인", bottom_message, product_name, product_link)

    if len(paragraphs) >= 5:
        mid_index = max(2, len(paragraphs) // 2)
    elif len(paragraphs) >= 3:
        mid_index = 2
    else:
        mid_index = len(paragraphs)
    if mid_index > len(paragraphs):
        mid_index = len(paragraphs)

    paragraphs.insert(mid_index, mid_block)
    print("   >> 쿠팡 링크 삽입 완료: 1회")
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
        _default_gemini_profile = os.path.join(os.path.expanduser("~"), "ChromeGeminiBot")
        automation_profile = os.getenv("GEMINI_PROFILE_PATH", "").strip() or _default_gemini_profile
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
        
        # 사고 모델 선택
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
        """사고 모델 선택 (모드 선택 드롭다운 → 사고 모델 클릭)"""
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
                print("   >> [주의] 모드 선택 버튼을 찾지 못했습니다.")
                return False
            
            mode_btn.click()
            time.sleep(2)
            
            # 2) 사고 모델 옵션 클릭
            thinking_selectors = [
                'button[data-test-id="bard-mode-option-사고모델"]',
                'button[data-mode-id="e051ce1aa80aa576"]',
            ]
            for sel in thinking_selectors:
                try:
                    option = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if option.is_displayed():
                        option.click()
                        time.sleep(2)
                        print("   >> 🧠 사고 모델 선택 완료!")
                        return True
                except:
                    continue
            
            # XPath 폴백: 텍스트로 찾기
            try:
                option = self.driver.find_element(By.XPATH, 
                    '//button[contains(@class, "bard-mode-list-button")]//span[contains(text(), "사고")]/..')
                option.click()
                time.sleep(2)
                print("   >> 🧠 사고 모델 선택 완료!")
                return True
            except:
                pass
            
            # 드롭다운 닫기 (선택 실패 시)
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
            except:
                pass
            
            print("   >> [주의] 사고 모델을 찾지 못했습니다. 기본 모델로 진행합니다.")
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
    # 스크립트 실행 경로를 기준으로 임시 이미지 저장 (System32 저장 및 가상화 방지)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(script_dir, f'temp_blog_img_{int(time.time())}.png')
    
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
너는 네이버 블로그 검색 유입과 클릭률을 함께 고려하는 제목 편집자입니다.
아래 본문과 검색 의도를 참고해 제목 1개만 작성하세요.

[검색 의도]
- 핵심 검색어: {daily_context['search_phrase']}
- 독자 고민: {daily_context['reader_problem']}
- 글의 약속: {daily_context['reader_promise']}

[제목 규칙]
- 22~38자 안에서 자연스러운 한국어 제목으로 작성
- 핵심 검색어 또는 핵심 검색어의 자연스러운 변형을 제목 앞쪽에 넣기
- 문제 상황과 해결 기대가 같이 보이게 작성
- 오늘의 일상, 소소한 하루, 그냥 기록 같은 무가치한 일기형 제목 금지
- 과장, 낚시, 허위 후기, 직접 써본 것처럼 보이는 표현 금지
- 따옴표, 괄호, 해시태그, 이모티콘, 영어 금지
- 제목 1줄만 출력

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
                blog_title = f"{daily_context['search_phrase']} 실생활 체크포인트"

            img_description = build_daily_image_prompt(daily_context)
            p_name = ""
            post_type = "__daily_done__"
        if post_type == '일상':
            prompt = """
        당신은 20~30대 한국인 블로거입니다. 
        오늘의 일상, 취미, 산책, 카페 투어, 맛집, 혹은 날씨에 대한 생각 중 하나를 골라 진짜 사람이 쓴 것처럼 자연스러운 일상글을 작성해주세요.
        단, 봇 탐지를 피하기 위해 인위적인 AI 말투는 완전히 배제하고, 의식의 흐름이나 감정을 잘 담아 구어체와 존댓말을 적절히 섞어주세요. 감탄사나 이모티콘도 중간중간 넣어주세요.
        인사말부터 마무리까지 블로그 본문 내용만 출력해야 하며, 글자 수가 1000자 이상이 되도록 구체적으로 적어주세요.
        결과는 반드시 자연스러운 한국어로만 작성하고, 영어 문장이나 영어 제목 후보, 작업 메모 같은 문구는 절대 쓰지 마세요.
        절대 마크다운 서식('**' 기호 등)을 사용하지 마세요. 번호를 매길 일이 있다면 평범하게 '1. 내용', '2. 내용' 처럼 적어주세요.
        
        [서식 마커 규칙 - 반드시 지켜줘]
        - 글의 주요 흐름이 바뀌는 곳(예: 인사→본문, 본문→마무리) 2~3곳에 새 줄로 [구분선] 이라고만 적어줘.
        - 글 중간에 감성적이거나 인상적인 문장 1~2개를 [인용구]문장내용[/인용구] 형식으로 감싸줘.
        - 인용구의 문장내용은 반드시 20자 이상 60자 이하의 완성된 한국어 문장이어야 해.
        - [인용구][/인용구], [인용구] [/인용구], [인용구]문장내용[/인용구]처럼 비어 있거나 예시 문구가 남은 인용구는 절대 출력하지 마.
        - 쓸 만한 인용 문장이 없으면 인용구를 생략하고, 빈 인용구만 덩그러니 만들지 마.
        - 위 마커들은 에디터 서식으로 자동 변환되므로 반드시 정확히 적어줘.
            """
            
            # 1단계: 본문 생성 (사고 모델 → 최대 300초 대기)
            print("   >> 📝 블로그 본문 생성 중 (사고 모델, 최대 5분 대기)...")
            blog_content = bot.send_prompt(prompt, max_wait=300)
            if not blog_content:
                return None, None, None, "", None
            
            # 2단계: 제목 생성 (사고 모델 → 최대 180초 대기)
            print("   >> 📌 제목 생성 중 (사고 모델)...")
            title_prompt = f"다음 블로그 본문에 어울리는 클릭하고 싶은 블로그 일상글 제목을 핵심만 딱 1줄로 작성해줘. 결과는 반드시 한국어 제목 1줄만 써주고 영어는 절대 쓰지 마. 특수문자나 따옴표 빼고:\n\n{blog_content[:500]}"
            blog_title = bot.send_prompt(title_prompt, max_wait=180)
            if blog_title:
                blog_title = blog_title.replace('"', '').strip().split('\n')[0]
                if re.search(r"[A-Za-z]{3,}", blog_title):
                    blog_title = ""
            else:
                blog_title = "오늘의 일상 기록"
            
            img_description = "20대 성인 한국인 여자가 등장하는 한국의 일상, 카페, 산책, 맛집 등 따뜻한 분위기의 고품질 사진"
            
        elif post_type == '쿠팡':
            product_state = select_unused_coupang_product(csv_file_path)
            target = product_state["selected_row"]
            coupang_angle = get_next_coupang_angle(datetime.now())
            angle_name = coupang_angle.get("name", "구매체크형")
            angle_direction = coupang_angle.get("post_angle", "구매 전 확인할 조건을 정리하는 글")
            p_name = target['상품명']
            p_keyword = target['키워드']
            p_link = target['쿠팡링크']
            
            problem_scenario = get_product_field(target, "문제상황", default=f"{p_keyword}이 필요한데 어떤 제품을 골라야 할지 애매한 상황")
            target_reader = get_product_field(target, "대상독자", default="구매 전에 실제 후기와 현실적인 추천 포인트를 같이 보고 싶은 사람")
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
            cta_text = get_product_field(target, "CTA문구", default=coupang_angle.get("cta_text", "제품 상세정보와 현재 가격은 아래 링크에서 바로 확인 가능"))
            disclosure_text = get_product_field(
                target,
                "광고고지문",
                default="이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.",
            )

            # 1단계: 본문 생성 (사고 모델 → 최대 300초 대기)
            print("   >> 📝 블로그 본문 생성 중 (사고 모델, 최대 5분 대기)...")
            prompt = f"""
너는 네이버 블로그에서 생활용품식품소모품계절가전 중심의 쿠팡파트너스 글을 작성하는 실전형 SEO 콘텐츠 전략가다.

이 글의 목표는 단순 상품 홍보가 아니다.
검색자가 구매 전에 겪는 고민을 먼저 해결하고, 상품 선택 기준을 정리한 뒤, 자연스럽게 상세정보 확인으로 이어지게 만드는 것이다.

광고 고지문은 코드에서 본문 최상단에 자동으로 붙인다.
따라서 너는 본문 안에 광고 고지문을 다시 출력하지 마라.

[오늘 작성할 상품 정보]
- 상품명: {p_name}
- 메인 키워드: {p_keyword}
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

[블로그 운영 방향]
이 블로그는 잡다한 상품 홍보 블로그가 아니라,
생활용품식품소모품계절가전 구매 전에 필요한 기준을 정리해주는 생활 구매 판단 블로그다.

따라서 글은 다음 방향을 따라야 한다.
- 상품을 무조건 좋다고 밀어붙이지 않는다.
- 독자의 상황별 선택 기준을 먼저 제시한다.
- 가격, 구성, 용량, 보관, 사용 공간, 소비 속도, 배송 조건처럼 실제 구매 판단에 필요한 요소를 다룬다.
- 장점만 쓰지 말고 맞지 않을 수 있는 사람도 함께 말한다.
- 검색자가 글을 끝까지 읽을 이유가 있어야 한다.
- 쿠팡 링크 클릭은 글의 결론이 아니라, 판단 후 확인 단계처럼 자연스럽게 연결한다.

[가장 중요한 작성 원칙]
- 실제 구매하거나 사용했다고 단정하지 마라.
- 내돈내산, 직접 써봤다, 제가 샀다, 며칠 써보니 같은 표현은 쓰지 마라.
- 대신 구매 전 확인해볼 부분, 상세페이지에서 확인할 부분, 선택 기준, 사용 환경에 따라 달라질 수 있는 부분 중심으로 쓴다.
- 확인되지 않은 수치, 성능, 인증, 성분, 배송 속도, 사용 기간, 할인율, 최저가, 재고 상황은 절대 지어내지 마라.
- 가격은 변동될 수 있으므로 단정하지 마라.
- 후기는 실제 사용자 후기를 인용한 것처럼 꾸미지 마라.
- 광고 느낌보다 정보형 구매 가이드 느낌을 우선한다.
- 오늘 글 변주인 {angle_name} 흐름을 반영하되, 실제 구매나 직접 사용을 한 것처럼 꾸미지는 마라.

[SEO 규칙]
- 상품명 '{p_name}'은 본문에 3~5회만 자연스럽게 포함한다.
- 메인 키워드 '{p_keyword}'는 본문에 4~6회만 자연스럽게 포함한다.
- 키워드를 억지로 반복하지 말고 문맥 안에 녹인다.
- 유사 키워드를 자연스럽게 섞는다.
  예: 구매 전 체크, 선택 기준, 가격 확인, 상세정보 확인, 구성 비교, 생활용품 추천, 가정용, 사무실용, 자취용, 대량구매
- 제목은 출력하지 말고 본문만 작성한다.

[글 전체 스타일]
- 40~50대 독자도 편하게 읽을 수 있는 차분한 한국어
- 네이버 블로그에 어울리는 자연스러운 구어체
- 너무 가볍거나 과한 감탄사 남발 금지
- 문단은 짧게 나누되, 내용은 얕지 않게 작성
- AI 설명투 금지
- 본 글에서는, 설명해드리겠습니다, 정리해보겠습니다 같은 표현 금지
- 역대급, 인생템, 무조건 추천, 완전 강추, 최저가, 가성비 끝판왕 같은 과장 표현 금지

[본문 구조]
아래 순서를 반드시 지켜라.

1. 도입부: 독자의 현실적인 고민으로 시작
- 첫 문단에서 {problem_scenario} 상황을 자연스럽게 풀어라.
- '{p_keyword}'를 1회 자연스럽게 포함하라.
- 상품을 바로 추천하지 말고, 왜 선택 기준이 필요한지 먼저 말하라.

2. 구매 전 고민이 생기는 이유
- 독자가 {pain_point} 때문에 헷갈릴 수 있다는 흐름으로 작성하라.
- 가격만 보고 고르면 생길 수 있는 문제를 설명하라.
- 이 구간 끝에 아래 마커를 정확히 1회 넣어라.

[사진삽입]

[구분선]

3. 이 상품을 볼 때 확인할 핵심 기준
- '{p_name}'을 자연스럽게 언급하라.
- 강조 포인트 3개를 그대로 복붙하지 말고, 독자가 이해하기 쉽게 풀어라.
- 아래 형식의 목록 마커를 사용하라.

[목록주제]구매 전 확인하면 좋은 기준
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
- 기준 1개를 구체적으로 작성
[목록끝]

4. 장점과 주의점
- 장점은 생활 속 상황과 연결해서 작성하라.
- 주의점은 반드시 포함하라.
- {caution_note}를 자연스럽게 반영하라.
- 단점이 있어도 과하게 부정하지 말고 이런 경우에는 한 번 더 확인이 필요하다는 방식으로 써라.

[구분선]

5. 추천 대상과 비추천 대상
- 추천 대상 3가지를 구체적으로 작성하라.
- 비추천 대상 또는 신중히 볼 대상 2가지를 작성하라.
- 이 구간은 신뢰도를 높이는 핵심 구간이다.
- 아래 형식의 목록 마커를 사용하라.

[목록주제]이런 분들에게 잘 맞을 수 있습니다
- 구체적인 대상 1
- 구체적인 대상 2
- 구체적인 대상 3
[목록끝]

[목록주제]이런 경우에는 한 번 더 확인하세요
- 신중히 볼 대상 1
- 신중히 볼 대상 2
[목록끝]

6. 비교 관점
- 같은 상품군을 고를 때 비교해야 할 기준을 설명하라.
- 특정 경쟁 상품을 근거 없이 깎아내리지 마라.
- '{p_keyword}'를 찾는 사람이 실제로 비교할 만한 기준을 말하라.
- 예: 용량, 구성, 크기, 보관성, 사용 공간, 소비 속도, 관리 편의성, 상세페이지 정보 확인

[구분선]

7. 최종 선택 가이드
- 무조건 이 상품을 사라고 하지 마라.
- 상황별로 선택 기준을 나눠라.
- 예: 1인 가구라면, 가족용이라면, 사무실용이라면, 계절용이라면, 자주 쓰는 사람이라면
- '{p_name}'을 마지막에 1회 자연스럽게 언급하라.

8. CTA 문장
- 구매 강요가 아니라 확인 유도형으로 작성하라.
- 아래 CTA 방향을 자연스럽게 반영하라.
- {cta_text}
- 반드시 아래 의미를 포함하라.
  - 현재 가격과 구성은 변동될 수 있음
  - 구매 전 상세정보와 옵션을 확인하는 것이 좋음
  - 내 사용 환경에 맞는지 확인 후 선택하는 것이 안전함
- 아래 인용구 2개는 반드시 내용이 있는 완성된 문장으로 출력하라.
- 인용구 안에는 반드시 20자 이상 60자 이하의 한국어 문장을 넣어라.
- 빈 인용구, 공백만 있는 인용구, 예시 문구가 그대로 남은 인용구는 절대 출력하지 마라.

[인용구]가격만 보고 고르기보다 내 생활 패턴에 맞는지 확인하는 게 더 중요했습니다[/인용구]
[인용구]결국 오래 쓰는 제품은 화려한 말보다 실제 상황에 잘 맞는지가 핵심이었습니다[/인용구]

9. FAQ
- 마지막에 FAQ 4개를 넣어라.
- 질문은 실제 검색자가 궁금해할 만한 문장으로 작성하라.
- 답변은 짧지만 실용적으로 작성하라.
- FAQ에도 '{p_keyword}'를 1~2회 자연스럽게 포함하라.

[출력 형식]
- 제목 없이 본문만 출력
- 1800자 이상
- 자연스러운 한국어만 사용
- 영어 문장, 영어 제목, 영어 작업 메모 금지
- 마크다운 서식 금지
- 해설, 주석, 제목 후보, 해시태그를 함께 출력하지 말 것
- [사진삽입]은 정확히 1회
- [구분선]은 정확히 3회 이상
- [인용구]문장[/인용구] 형식 2회 포함
- 인용구 내부 문장은 반드시 20자 이상이어야 하며, 빈 인용구 출력 금지
- [목록주제]와 [목록끝] 마커는 철자 그대로 유지

[절대 금지]
- 광고 고지문 출력 금지
- 상품 링크 출력 금지
- [인용구][/인용구], [인용구] [/인용구], [인용구]문장[/인용구]처럼 내용 없는 인용구 출력 금지
- 가격, 할인율, 배송일, 리뷰 수, 평점 임의 생성 금지
- 내돈내산 표현 금지
- 실제 사용한 것처럼 단정 금지
- 근거 없는 비교 우위 금지
- 키워드 반복만으로 분량 채우기 금지
- 같은 문장 구조 반복 금지
- 너무 짧은 문단만 반복하는 저품질 글 금지
"""
            raw_content = bot.send_prompt(prompt, max_wait=300)
            if not raw_content:
                return None, None, None, "", None
            
            ad_disclaimer = "🚨 본 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.\n\n"
            bottom_link = f"\n\n{'─' * 25}\n\n🛒 {p_name}\n✅ 제품 상세정보 및 구매 링크 바로가기:\n{p_link}\n"
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
- 상품군/성격 참고: 생활용품, 식품, 소모품, 계절가전, 구매 전 체크
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
- 상품과 맞지 않으면 가정용, 사무실용, 자취용, 생활용품추천 같은 태그를 넣지 말 것
- 식품이면 보관, 용량, 개수, 장보기, 대량구매, 소비속도 같은 기준을 우선
- 가전이면 크기, 소음, 전기요금, 설치, 관리, 사용공간 같은 기준을 우선
- 소모품이면 구성, 개수, 보관, 교체주기, 사용장소 같은 기준을 우선

[절대 금지 태그]
- #일상 #소통 #맞팔 #데일리 #오늘 #감성 #리뷰 #후기 #추천템 #핫딜 #최저가 #인생템
- 상품과 무관한 #가정용 #사무실용 #자취용 #생활용품추천 #가격비교 #구성비교 남발 금지
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
#메인키워드 #품목명 #구매전체크 #용량확인 #구성확인 #보관방법 #사용장소 #비교기준 #상세정보확인 #구매전확인
"""
            hashtags = ""
            for hashtag_attempt in range(2):
                raw_hashtags = bot.send_prompt(hashtag_prompt, max_wait=180)
                hashtags = extract_hashtag_line(raw_hashtags)
                if hashtags:
                    break
                print("   >> [주의] 해시태그 응답이 완성되지 않아 다시 요청합니다.")
            if hashtags:
                blog_content = blog_content + "\n\n[해시태그대기]\n" + hashtags
            else:
                print("   >> [주의] 유효한 해시태그를 받지 못해 해시태그 없이 진행합니다.")
            
            # 3단계: 제목 생성
            print("   >> 📌 제목 생성 중...")
            title_prompt = f"""
            너는 네이버 검색 상위노출과 클릭률을 동시에 잡는
            상위 0.1% 블로그 마케팅 카피라이터다.

            아래 본문을 참고하여 제목을 1개만 작성해라.

            [상품 정보]
            - 메인 키워드: {p_keyword}
            - 상품명: {p_name}
            - 대상 독자: {target_reader}
            - 사용 상황: {problem_scenario}
            - 오늘 글 변주: {angle_name}
            - 제목 방향 참고: {title_seed}

            [핵심 SEO 조건]
            - '{p_keyword}' 반드시 포함 (앞부분 배치)
            - 상품명 전체를 억지로 다 넣지 말고, 용량/개수/상품군 중 핵심만 자연스럽게 반영
            - 22~38자

            [클릭 유도 조건]
            - 아래 단어 중 최소 1개 포함:
            "구매 전", "확인", "비교", "고를 때", "보관", "구성"

            [고급 CTR 전략]
            - 너무 광고스럽지 않게
            - “궁금증 + 구매 전 체크” 구조
            - 실제 검색자가 누르기 쉬운 정보형 제목 느낌
            - 확인되지 않은 효과나 과장 표현으로 클릭을 낚지 말 것
            - 직접 사용, 내돈내산, 써보니, 정착 같은 실제 경험 오해 표현 금지

            [제목 예시 구조]
            - {p_keyword} 구매 전 확인할 구성과 보관 기준
            - {p_keyword} 고를 때 용량과 개수 비교 포인트
            - {p_keyword} 가격만 보기 전 확인할 조건

            [출력 조건]
            - 제목 1개만
            - 따옴표, 특수기호 없이
            - 제목 외 다른 설명 금지
            """
            title_prompt += "\n\n[언어 규칙]\n- 결과는 반드시 한국어 제목 1개만 출력할 것\n- 영어 단어, 영어 문장, 영어 작업 메모를 절대 출력하지 말 것"
            blog_title = bot.send_prompt(title_prompt, max_wait=180)

            if blog_title:
                blog_title = blog_title.replace('"', '').strip().split('\n')[0]
            else:
                blog_title = f"{p_keyword} 구매 전 확인할 구성 기준"

            if blog_title and re.search(r"[A-Za-z]{3,}", blog_title):
                blog_title = f"{p_keyword} 구매 전 확인할 구성 기준"
            elif not blog_title:
                blog_title = f"{p_keyword} 구매 전 확인할 구성 기준"

            img_description = img_prompt = f"""
{thumbnail_prompt}

Korean blog thumbnail feeling.
20대 성인 한국인 여성이 {p_name}을 실제로 사용하며 만족감과 행복함이 느껴지는 자연스러운 미소를 짓는 장면.
Product promotional lifestyle photo for Coupang Partners.
Make the product clearly visible and trustworthy.
Realistic daily-life scene.
Natural lighting.
No text in image.
Clean promotional photo, but not overly artificial.
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
        
        # 로그인 상태 유지 체크 (세션 저장용)
        try:
            keep_label = self.driver.find_element(By.XPATH, '//label[@for="keep"]')
            keep_label.click()
            time.sleep(0.5)
        except:
            pass
            
        # 로그인 버튼 클릭
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
                quote_styles = ['default', 'quotation_line', 'quotation_bubble', 'quotation_underline', 'quotation_postit', 'quotation_corner']
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
                cleaned = text
                for marker in markers:
                    cleaned = cleaned.replace(marker, "")
                cleaned = cleaned.strip().strip('"').strip("'").strip("“”‘’").strip()
                if cleaned in ("문장", "문장내용", "내용"):
                    return ""
                return cleaned

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
                    insert_quotation("quotation_underline") # 인용구(라인/따옴표)
                    set_font_size("16")
                    set_bold(True)
                    type_formatted_line(topic_text)
                    set_bold(False)
                    # 인용구 탈출 (방향키 ↓ ↓ + 엔터 1회)
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
                    if not quote_text:
                        print("   >> [주의] 비어 있는 인용구는 건너뜁니다.")
                        continue
                    insert_quotation()
                    set_font_color("#0095e9")
                    set_bold(True)
                    type_formatted_line(quote_text)
                    set_bold(False)
                    set_font_color("#000000")
                    # 인용구 탈출 (방향키 ↓ ↓ + 엔터 1회)
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
    """post_type: '일상' 또는 '쿠팡' — 전역 naver_bot 사용"""
    global naver_bot
    _publish_one_post_inner(post_type)


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
    
    # 00:30 ~ 23:30 사이에서 랜덤 10개 시각 생성 (최소 30분 간격)
    random_minutes = sorted(random.sample(range(30, 1410, 15), 10))  # 15분 단위 중 10개 선택
    
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
    
    # 클립보드 충돌 방지: 다른 자동화 스크립트 완료까지 대기 (최대 30분)
    _lock = FileLock(AUTOMATION_LOCK_PATH, timeout=1800)
    print(f"[Lock] 다른 자동화 작업 확인 중...")
    print(f"[Lock] 전역 락 파일: {AUTOMATION_LOCK_PATH}")
    _lock.acquire()
    print(f"[Lock] 락 획득 완료 — 스크립트 실행을 시작합니다.")
    
    try:
        # ★ 네이버 봇 초기화 (Chrome 프로필 재사용 → 로그인 1회만!)
        print("🚀 네이버 블로그 봇을 초기화합니다...\n")
        naver_bot = NaverBlogBot(v_id, v_passwd)
        send_telegram("🚀 블로그 자동화 프로그램이 시작되었습니다!")
        
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
        
        _lock.release()
        print(f"[Lock] 락 해제 완료")
        
        if scheduled_log_file:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            scheduled_log_file.close()
