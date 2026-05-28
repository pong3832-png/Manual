import argparse
import getpass
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta

try:
    from filelock import FileLock
except ModuleNotFoundError:
    import msvcrt

    class FileLock:
        def __init__(self, path: str, timeout: int = 600):
            self.path = path
            self.timeout = timeout
            self._fh = None

        def acquire(self):
            deadline = time.time() + self.timeout
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
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
                        raise TimeoutError(f"failed to acquire schedule register lock: {self.path}")
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

# ── 터미널 한글 깨짐 방지 ──
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


TASK_PREFIX = "TistoryChatGPTAutoPost"
REFRESH_TASK_NAME = f"{TASK_PREFIX}_RefreshDaily"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
HELPER_DIR = os.path.join(PROJECT_ROOT, "scripts", "scheduled")
STATE_DIR = os.path.join(PROJECT_ROOT, "runtime", "scheduled_state")
SCHEDULE_FILE = os.path.join(STATE_DIR, "daily_schedule.json")
LOCK_DIR = os.path.join(PROJECT_ROOT, "runtime", "locks")
SCHEDULE_REGISTER_LOCK_PATH = os.path.join(LOCK_DIR, "schedule_register.lock")


def parse_args():
    parser = argparse.ArgumentParser(description="티스토리 ChatGPT 임시저장 스케줄러 등록")
    parser.add_argument(
        "--target-date",
        choices=["auto", "today", "tomorrow"],
        default="auto",
        help="발행 날짜 선택",
    )
    parser.add_argument(
        "--refresh-time",
        default="00:05",
        help="매일 새 스케줄을 다시 등록할 시간 (HH:MM)",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        default=True,
        help="예약 작업을 임시저장 모드로 등록",
    )
    return parser.parse_args()


def run_command(command):
    # schtasks는 시스템 코드페이지(CP949)로 출력하므로 mbcs 사용
    completed = subprocess.run(
        command, capture_output=True, text=True,
        encoding="mbcs", errors="replace",
    )
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
        encoding="mbcs",
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
            f"{target_date.isoformat()}에는 예약 가능한 시간이 부족합니다. "
            "더 이른 시간에 등록하거나 내일 날짜로 등록하세요."
        )

    random_minutes = []
    for _ in range(2000):
        temp = sorted(random.sample(candidate_minutes, 10))
        if all(temp[i+1] - temp[i] >= 15 for i in range(9)):
            random_minutes = temp
            break
    if not random_minutes:
        random_minutes = sorted(random.sample(candidate_minutes, 10))
    # Keep scheduled task arguments ASCII. Korean arguments can render badly in
    # Task Scheduler/PowerShell windows on some Windows code pages.
    post_types = ["coupang", "daily"] * 5
    if random.choice([True, False]):
        post_types = ["daily", "coupang"] * 5

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


def build_task_command(post_type, draft=True):
    wrapper_path = os.path.join(HELPER_DIR, "run_scheduled_post.ps1")
    command = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass '
        f'-File "{wrapper_path}" -PostType "{post_type}"'
    )
    command += " -Draft"
    return command


def format_schedule_date(target_date):
    return target_date.strftime("%Y/%m/%d")


def save_schedule_file(items, target_date):
    os.makedirs(STATE_DIR, exist_ok=True)
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
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return SCHEDULE_FILE


def register_post_tasks(items, target_date, draft=True):
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
                build_task_command(item["post_type"], draft=draft),
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


def register_refresh_task(refresh_time, draft=True):
    username = getpass.getuser()
    wrapper_path = os.path.join(HELPER_DIR, "run_refresh_schedule.ps1")
    delete_task_if_exists(REFRESH_TASK_NAME)
    run_command(
        [
            "schtasks",
            "/Create",
            "/TN",
            REFRESH_TASK_NAME,
            "/TR",
            (
                f'powershell.exe -NoProfile -ExecutionPolicy Bypass '
                f'-File "{wrapper_path}" -RefreshTime "{refresh_time}"'
                + " -Draft"
            ),
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


def print_schedule(items, target_date, schedule_path, draft=True):
    print("\n" + "=" * 60)
    print(f"[{target_date.isoformat()}] 작업 스케줄러 등록 결과")
    print(f"모드: {'임시저장' if draft else '공개 발행'}")
    print("=" * 60)
    for item in items:
        print(f"  {item['index']:2d}. {item['scheduled_at'].strftime('%H:%M')}  ->  {item['post_type']}")
    print(f"\n>> 스케줄 파일 저장: {schedule_path}")
    print(f">> 매일 재등록 작업: {REFRESH_TASK_NAME}")


def main():
    args = parse_args()
    os.makedirs(LOCK_DIR, exist_ok=True)
    schedule_lock = FileLock(SCHEDULE_REGISTER_LOCK_PATH, timeout=600)
    print(f"[schedule-lock] 등록 락 확인 중: {SCHEDULE_REGISTER_LOCK_PATH}")
    schedule_lock.acquire()
    print("[schedule-lock] 등록 락 획득")
    try:
        target_date = resolve_target_date(args.target_date)
        items = build_schedule_items(target_date)
        register_post_tasks(items, target_date, draft=args.draft)
        register_refresh_task(args.refresh_time, draft=args.draft)
        schedule_path = save_schedule_file(items, target_date)
        print_schedule(items, target_date, schedule_path, draft=args.draft)
    finally:
        schedule_lock.release()
        print("[schedule-lock] 등록 락 해제")
    if len(sys.argv) == 1:
        input("\n[안내] 스케줄 등록을 완료했습니다. 창을 닫으려면 엔터를 누르세요...")


if __name__ == "__main__":
    main()
