import argparse
import getpass
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta


TASK_PREFIX = "NaverBlogAutoPost_skssj2628"
REFRESH_TASK_NAME = f"{TASK_PREFIX}_RefreshDaily"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
HELPER_DIR = os.path.join(BASE_DIR, "자동발행실행보조파일")
STATE_DIR = os.path.join(BASE_DIR, "자동발행상태기록파일")
SCHEDULE_FILE = os.path.join(STATE_DIR, "daily_schedule.json")
PEER_SCHEDULE_FILES = [
    os.path.join(PROJECT_ROOT, "자동발행상태기록파일", "daily_schedule.json"),
]
MIN_CROSS_ACCOUNT_GAP_MINUTES = 30
POST_TYPES = ["일상"] * 7 + ["쿠팡"] * 3
REPO_ROOT = os.path.dirname(PROJECT_ROOT)
PREFERRED_PYTHON = os.path.join(REPO_ROOT, "티스토리 자동화 ing", ".venv", "Scripts", "python.exe")


def parse_args():
    parser = argparse.ArgumentParser(description="네이버 블로그 작업 스케줄러 등록")
    parser.add_argument(
        "--target-date",
        choices=["auto", "today", "tomorrow"],
        default="auto",
        help="발행 일자 선택",
    )
    parser.add_argument(
        "--refresh-time",
        default="00:05",
        help="매일 랜덤 스케줄을 다시 등록할 시간 (HH:MM)",
    )
    return parser.parse_args()


def run_command(command):
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise RuntimeError(
            f"명령 실행 실패: {' '.join(command)}\nSTDOUT: {completed.stdout}\nSTDERR: {completed.stderr}"
        )
    return completed


def task_exists(task_name):
    completed = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode == 0


def delete_task_if_exists(task_name):
    if task_exists(task_name):
        run_command(["schtasks", "/Delete", "/TN", task_name, "/F"])


def candidate_minutes_for_date(target_date):
    minutes = list(range(30, 1410, 1))
    now = datetime.now()
    if target_date == now.date():
        minimum_dt = now + timedelta(minutes=5)
        minutes = [
            minute
            for minute in minutes
            if datetime.combine(target_date, datetime.min.time()) + timedelta(minutes=minute) >= minimum_dt
        ]
    return minutes


def load_peer_schedule_minutes(target_date):
    peer_minutes = []
    for schedule_path in PEER_SCHEDULE_FILES:
        if not os.path.exists(schedule_path):
            continue
        try:
            with open(schedule_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if payload.get("target_date") != target_date.isoformat():
                continue
            for item in payload.get("items", []):
                time_text = str(item.get("time") or "")
                hour_text, minute_text = time_text.split(":", 1)
                peer_minutes.append(int(hour_text) * 60 + int(minute_text))
        except Exception as e:
            print(f"[주의] 상대 계정 스케줄을 읽지 못했습니다: {schedule_path} ({e})")
    return peer_minutes


def filter_minutes_away_from_peers(candidate_minutes, peer_minutes):
    if not peer_minutes:
        return candidate_minutes
    return [
        minute
        for minute in candidate_minutes
        if all(abs(minute - peer_minute) >= MIN_CROSS_ACCOUNT_GAP_MINUTES for peer_minute in peer_minutes)
    ]


def resolve_target_date(mode):
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    if mode == "today":
        return today
    if mode == "tomorrow":
        return tomorrow

    if len(candidate_minutes_for_date(today)) >= 10:
        return today
    return tomorrow


def build_schedule_items(target_date):
    candidate_minutes = candidate_minutes_for_date(target_date)
    if len(candidate_minutes) < 10:
        raise RuntimeError(
            f"{target_date.isoformat()}에는 남은 시간 슬롯이 부족합니다. "
            "좀 더 이른 시간에 등록하거나 내일 날짜로 등록하세요."
        )

    peer_minutes = load_peer_schedule_minutes(target_date)
    filtered_minutes = filter_minutes_away_from_peers(candidate_minutes, peer_minutes)
    schedule_count = len(POST_TYPES)
    if len(filtered_minutes) >= schedule_count:
        candidate_minutes = filtered_minutes
    elif peer_minutes:
        print("[주의] 상대 계정 스케줄과 30분 이상 떨어진 슬롯이 부족해 기본 후보로 생성합니다.")

    random_minutes = []
    for _ in range(2000):
        temp = sorted(random.sample(candidate_minutes, schedule_count))
        if all(temp[i+1] - temp[i] >= 15 for i in range(schedule_count - 1)):
            random_minutes = temp
            break
    if not random_minutes:
        random_minutes = sorted(random.sample(candidate_minutes, schedule_count))

    post_types = POST_TYPES[:]
    random.shuffle(post_types)

    items = []
    for index, (minutes, post_type) in enumerate(zip(random_minutes, post_types), start=1):
        scheduled_at = datetime.combine(target_date, datetime.min.time()) + timedelta(minutes=minutes)
        items.append(
            {
                "index": index,
                "post_type": post_type,
                "scheduled_at": scheduled_at,
            }
        )
    return items


def build_task_command(post_type):
    python_exe = resolve_python_exe()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "skssj2628.py")
    return f'"{python_exe}" "{script_path}" --post-type "{post_type}" --naver-id "skssj2628" --scheduled'


def resolve_python_exe():
    if os.path.exists(PREFERRED_PYTHON):
        return PREFERRED_PYTHON
    return sys.executable


def format_schedule_date(target_date):
    return target_date.strftime("%Y/%m/%d")


def save_schedule_file(items, target_date):
    os.makedirs(STATE_DIR, exist_ok=True)
    schedule_path = SCHEDULE_FILE
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_date": target_date.isoformat(),
        "items": [
            {
                "index": item["index"],
                "post_type": item["post_type"],
                "time": item["scheduled_at"].strftime("%H:%M"),
            }
            for item in items
        ],
    }
    with open(schedule_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return schedule_path


def register_post_tasks(items, target_date):
    username = getpass.getuser()
    for item in items:
        task_name = f"{TASK_PREFIX}_{item['index']:02d}"
        delete_task_if_exists(task_name)
        run_command(
            [
                "schtasks",
                "/Create",
                "/TN",
                task_name,
                "/TR",
                build_task_command(item["post_type"]),
                "/SC",
                "ONCE",
                "/SD",
                format_schedule_date(target_date),
                "/ST",
                item["scheduled_at"].strftime("%H:%M"),
                "/RL",
                "LIMITED",
                "/RU",
                username,
                "/IT",
                "/F",
            ]
        )


def register_refresh_task(refresh_time):
    username = getpass.getuser()
    python_exe = resolve_python_exe()
    script_path = os.path.abspath(__file__)
    delete_task_if_exists(REFRESH_TASK_NAME)
    run_command(
        [
            "schtasks",
            "/Create",
            "/TN",
            REFRESH_TASK_NAME,
            "/TR",
            f'"{python_exe}" "{script_path}" --target-date auto --refresh-time {refresh_time}',
            "/SC",
            "DAILY",
            "/ST",
            refresh_time,
            "/RL",
            "LIMITED",
            "/RU",
            username,
            "/IT",
            "/F",
        ]
    )


def print_schedule(items, target_date, schedule_path):
    print("\n" + "=" * 60)
    print(f"[{target_date.isoformat()}] 작업 스케줄러 등록 결과")
    print("=" * 60)
    for item in items:
        label = "일상" if item["post_type"] == "일상" else "쿠팡"
        print(f"  {item['index']:2d}. {item['scheduled_at'].strftime('%H:%M')}  ->  {label}")
    print(f"\n>> 스케줄 파일 저장: {schedule_path}")
    print(f">> 매일 재등록 작업: {REFRESH_TASK_NAME}")



def main():
    args = parse_args()
    target_date = resolve_target_date(args.target_date)
    items = build_schedule_items(target_date)
    register_post_tasks(items, target_date)
    register_refresh_task(args.refresh_time)
    schedule_path = save_schedule_file(items, target_date)
    print_schedule(items, target_date, schedule_path)
    if len(sys.argv) == 1:
        input("\n[안내] 스케줄 등록을 완료했습니다. 창을 닫으려면 엔터를 누르세요...")


if __name__ == "__main__":
    main()
