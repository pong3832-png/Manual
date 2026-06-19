# -*- coding: utf-8 -*-
"""
골프/건강식품 티스토리 24시간 랜덤 15회 자동 발행 스케줄러

핵심 동작:
1. 하루 24시간을 15개 슬롯으로 나눔
2. 각 슬롯 안에서 랜덤 발행 시간을 1개씩 생성
3. 생성된 시간마다 main_golf.py를 1회 실행하되, 기본 비율은 골프 7개 + 건강식품 7개
4. 총 하루 최대 15회 실행
5. 스케줄러 중복 실행 방지 락 사용
6. main_golf.py 내부 automation.lock은 그대로 사용되어 다른 자동화 작업과 충돌 방지
7. 날짜별 스케줄/상태 파일 저장

기본 실행:
python golf_24h_random_15_scheduler.py

작업 스케줄러 등록:
python golf_24h_random_15_scheduler.py --install

등록 확인:
schtasks /Query /TN "Tistory_Golf_24H_Random_15" /V /FO LIST

작업 스케줄러 삭제:
python golf_24h_random_15_scheduler.py --uninstall

오늘 랜덤 스케줄만 미리 보기:
python golf_24h_random_15_scheduler.py --print-plan

오늘 상태 초기화:
python golf_24h_random_15_scheduler.py --reset-today

테스트:
python golf_24h_random_15_scheduler.py --max-posts 3 --dry-run
"""

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path

try:
    from filelock import FileLock
except ModuleNotFoundError:
    import msvcrt

    class FileLock:
        def __init__(self, path: str, timeout: int = 1):
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
                        raise TimeoutError(f"failed to acquire scheduler lock: {self.path}")
                    time.sleep(0.5)

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


SCHEDULER_DIR = Path(__file__).resolve().parent
GOLF_DIR = SCHEDULER_DIR.parent
MAIN_GOLF_PATH = GOLF_DIR / "main_golf.py"

# main_golf.py 기준 프로젝트 루트: "티스토리 자동화 ing"
RUNTIME_DIR = GOLF_DIR.parent / "runtime"
LOG_DIR = RUNTIME_DIR / "logs" / "golf_24h_random_15"
STATE_DIR = RUNTIME_DIR / "state"
LOCK_DIR = RUNTIME_DIR / "locks"

SCHEDULER_LOCK_PATH = LOCK_DIR / "golf_24h_random_15_scheduler.lock"
SCHEDULE_REGISTER_LOCK_PATH = LOCK_DIR / "schedule_register.lock"
TASK_NAME = "Tistory_Golf_24H_Random_15"

DEFAULT_MAX_POSTS = 14
DEFAULT_GOLF_POSTS = 7
DEFAULT_HEALTH_POSTS = 7
MAX_ALLOWED_POSTS = 14
TASK_CLEANUP_LIMIT = 15
MAX_CONSECUTIVE_FAILURES = 3

# 각 슬롯의 앞뒤 몇 분은 피해서 너무 정각에 몰리지 않게 함
SLOT_EDGE_BUFFER_MINUTES = 7


def now() -> datetime:
    return datetime.now()


def now_text() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def today_key() -> str:
    return now().strftime("%Y-%m-%d")


def log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{today_key()}_24h_random_15.log"


def state_path() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / "golf_24h_random_15_current.json"


def write_log(message: str) -> None:
    line = f"[{now_text()}] {message}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with log_path().open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def acquire_schedule_register_lock():
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    schedule_lock = FileLock(str(SCHEDULE_REGISTER_LOCK_PATH), timeout=600)
    write_log(f"[schedule-lock] 등록 락 확인 중: {SCHEDULE_REGISTER_LOCK_PATH}")
    schedule_lock.acquire()
    write_log("[schedule-lock] 등록 락 획득")
    return schedule_lock


def release_schedule_register_lock(schedule_lock) -> None:
    schedule_lock.release()
    write_log("[schedule-lock] 등록 락 해제")


def validate_environment() -> None:
    if not MAIN_GOLF_PATH.exists():
        raise FileNotFoundError(f"main_golf.py를 찾지 못했습니다: {MAIN_GOLF_PATH}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


def make_random_plan(max_posts: int) -> list[str]:
    """
    00:00~24:00을 max_posts개 슬롯으로 나누고,
    각 슬롯 내부에서 랜덤 시각을 1개 생성합니다.
    반환값은 HH:MM 문자열 리스트입니다.
    """
    if max_posts < 1:
        raise ValueError("max_posts는 1 이상이어야 합니다.")
    if max_posts > MAX_ALLOWED_POSTS:
        raise ValueError(f"max_posts는 최대 {MAX_ALLOWED_POSTS}까지만 허용합니다.")

    run_start = now()
    slot_seconds = int(24 * 60 * 60 / max_posts)

    planned: list[datetime] = []
    for idx in range(max_posts):
        slot_start = run_start + timedelta(seconds=slot_seconds * idx)
        slot_end = run_start + timedelta(seconds=slot_seconds * (idx + 1))

        start_buffered = slot_start + timedelta(minutes=SLOT_EDGE_BUFFER_MINUTES)
        end_buffered = slot_end - timedelta(minutes=SLOT_EDGE_BUFFER_MINUTES)

        if end_buffered <= start_buffered:
            start_buffered = slot_start
            end_buffered = slot_end - timedelta(minutes=1)

        span_seconds = max(60, int((end_buffered - start_buffered).total_seconds()))
        random_offset = random.randint(0, span_seconds)
        planned_dt = start_buffered + timedelta(seconds=random_offset)

        # 초는 버리고 분 단위로 정리
        planned_dt = planned_dt.replace(second=0, microsecond=0)
        planned.append(planned_dt)

    planned = sorted(planned)

    # 혹시 같은 분이 나오면 1분씩 밀어서 중복 제거
    deduped: list[datetime] = []
    seen = set()
    for item in planned:
        candidate = item
        while candidate.strftime("%Y-%m-%d %H:%M") in seen:
            candidate += timedelta(minutes=1)
        seen.add(candidate.strftime("%Y-%m-%d %H:%M"))
        deduped.append(candidate)

    return [x.strftime("%Y-%m-%d %H:%M") for x in deduped]


def make_today_only_plan(max_posts: int) -> list[str]:
    """현재 시각부터 오늘 23:59 안에서만 max_posts개 랜덤 발행 시간을 만듭니다."""
    if max_posts < 1:
        raise ValueError("max_posts는 1 이상이어야 합니다.")
    if max_posts > MAX_ALLOWED_POSTS:
        raise ValueError(f"max_posts는 최대 {MAX_ALLOWED_POSTS}까지만 허용합니다.")

    run_start = now() + timedelta(minutes=8)
    day_end = datetime.combine(date.today(), datetime.max.time()).replace(second=0, microsecond=0)
    if run_start >= day_end:
        raise ValueError("오늘 안에 새 발행 시간을 만들 수 있는 시간이 부족합니다.")

    total_seconds = max(60, int((day_end - run_start).total_seconds()))
    slot_seconds = max(60, int(total_seconds / max_posts))
    edge_buffer_seconds = min(SLOT_EDGE_BUFFER_MINUTES * 60, max(0, int(slot_seconds / 4)))

    planned: list[datetime] = []
    for idx in range(max_posts):
        slot_start = run_start + timedelta(seconds=slot_seconds * idx)
        slot_end = run_start + timedelta(seconds=slot_seconds * (idx + 1))
        if idx == max_posts - 1:
            slot_end = day_end

        start_buffered = slot_start + timedelta(seconds=edge_buffer_seconds)
        end_buffered = slot_end - timedelta(seconds=edge_buffer_seconds)
        if end_buffered <= start_buffered:
            start_buffered = slot_start
            end_buffered = slot_end

        span_seconds = max(60, int((end_buffered - start_buffered).total_seconds()))
        planned_dt = start_buffered + timedelta(seconds=random.randint(0, span_seconds))
        planned.append(planned_dt.replace(second=0, microsecond=0))

    planned = sorted(planned)
    deduped: list[datetime] = []
    seen = set()
    for item in planned:
        candidate = item
        while candidate.strftime("%Y-%m-%d %H:%M") in seen and candidate < day_end:
            candidate += timedelta(minutes=1)
        seen.add(candidate.strftime("%Y-%m-%d %H:%M"))
        deduped.append(candidate)

    return [x.strftime("%Y-%m-%d %H:%M") for x in deduped]


def resolve_post_type_counts(
    max_posts: int,
    golf_posts: int | None = None,
    health_posts: int | None = None,
) -> tuple[int, int]:
    """발행 수에 맞춰 골프/건강식품 개수를 확정합니다."""
    if golf_posts is None and health_posts is None:
        if max_posts == DEFAULT_MAX_POSTS:
            golf_posts = DEFAULT_GOLF_POSTS
            health_posts = DEFAULT_HEALTH_POSTS
        else:
            golf_posts = max_posts
            health_posts = 0
    elif golf_posts is None:
        health_posts = int(health_posts or 0)
        golf_posts = max_posts - health_posts
    elif health_posts is None:
        golf_posts = int(golf_posts or 0)
        health_posts = max_posts - golf_posts

    golf_posts = int(golf_posts)
    health_posts = int(health_posts)
    if golf_posts < 0 or health_posts < 0:
        raise ValueError("골프/건강식품 발행 개수는 0 이상이어야 합니다.")
    if golf_posts + health_posts != max_posts:
        raise ValueError(
            f"골프/건강식품 발행 개수 합이 --max-posts와 맞지 않습니다: "
            f"golf={golf_posts}, health={health_posts}, max_posts={max_posts}"
        )
    return golf_posts, health_posts


def assign_post_types(plan: list[str], golf_posts: int, health_posts: int) -> list[dict]:
    post_types = ["golf"] * golf_posts + ["health"] * health_posts
    random.shuffle(post_types)
    return [
        {"time": target_time, "post_type": post_type}
        for target_time, post_type in zip(plan, post_types)
    ]


def plan_time(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("time") or "")
    return str(entry)


def plan_post_type(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("post_type") or "golf")
    return "golf"


def save_state(plan: list) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "date": today_key(),
        "plan": plan,
    }
    state_path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def reset_today_state() -> None:
    path = state_path()
    if path.exists():
        path.unlink()
    write_log("현재 랜덤 스케줄/상태 파일 초기화 완료")


def print_plan(max_posts: int) -> None:
    path = state_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            plan = data.get("plan", [])
            write_log("=" * 72)
            write_log(f"현재 예약된 발행 계획 (총 {len(plan)}개)")
            for idx, entry in enumerate(plan, 1):
                write_log(f"{idx:02d}. {plan_time(entry)} ({plan_post_type(entry)})")
            write_log("=" * 72)
            return
        except Exception:
            pass
    write_log("현재 저장된 스케줄이 없습니다.")


def run_scheduler(
    max_posts: int,
    dry_run: bool = False,
    today_only: bool = False,
    golf_posts: int | None = None,
    health_posts: int | None = None,
) -> None:
    validate_environment()

    if max_posts < 1:
        raise ValueError("--max-posts는 1 이상이어야 합니다.")
    if max_posts > MAX_ALLOWED_POSTS:
        raise ValueError(f"--max-posts는 최대 {MAX_ALLOWED_POSTS}까지만 허용합니다.")

    golf_count, health_count = resolve_post_type_counts(max_posts, golf_posts, health_posts)
    plan = make_today_only_plan(max_posts) if today_only else make_random_plan(max_posts)
    typed_plan = assign_post_types(plan, golf_count, health_count)
    save_state(typed_plan)

    write_log("=" * 72)
    if today_only:
        write_log("골프/건강식품 오늘 한정 랜덤 스케줄러 (Windows Task Scheduler 등록 방식)")
    else:
        write_log("골프/건강식품 24시간 랜덤 14회 스케줄러 (Windows Task Scheduler 등록 방식)")
    write_log(f"오늘 계획 수: {len(typed_plan)}개 (golf={golf_count}, health={health_count})")
    write_log("예정 시간: " + ", ".join(f"{plan_time(item)}({plan_post_type(item)})" for item in typed_plan))
    write_log("=" * 72)

    import getpass
    username = getpass.getuser()

    if not dry_run:
        cleanup_stale_subtasks(active_count=max_posts)

    for index, entry in enumerate(typed_plan, 1):
        target_time = plan_time(entry)
        post_type = plan_post_type(entry)
        dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M")
        sd = dt.strftime("%Y/%m/%d")
        st = dt.strftime("%H:%M")

        task_name = f"{TASK_NAME}_{index:02d}"

        # 실행할 명령 (Windows 작업 스케줄러용)
        # powershell의 쿼터 파싱 오류를 피하고 백그라운드에서 조용히 실행하기 위해 pythonw.exe 사용
        pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
        task_run_cmd = f'"{pythonw_exe}" "{MAIN_GOLF_PATH}" --post-type {post_type} --scheduled --publish'
        
        schtasks_cmd = [
            "schtasks",
            "/Create",
            "/TN",
            task_name,
            "/SC",
            "ONCE",
            "/SD",
            sd,
            "/ST",
            st,
            "/TR",
            task_run_cmd,
            "/RL",
            "LIMITED",
            "/RU",
            username,
            "/IT",
            "/F",
        ]

        if dry_run:
            write_log(f"[DRY-RUN] {index:02d}번 등록 시뮬레이션: {target_time} ({post_type}, {task_name})")
            continue

        proc = subprocess.run(
            schtasks_cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if proc.returncode == 0:
            write_log(f"{index:02d}번 발행 작업 등록 완료: {target_time} ({post_type}, {task_name})")
        else:
            write_log(f"{index:02d}번 발행 작업 등록 실패: {target_time} ({post_type})\n{proc.stderr.strip()}")

    write_log("=" * 72)
    write_log("모든 예약 작업 등록이 완료되었습니다. 스케줄러 스크립트를 종료합니다.")
    write_log("이후의 실제 실행은 Windows 작업 스케줄러가 알아서 담당합니다.")
    write_log("=" * 72)


def cleanup_stale_subtasks(active_count: int) -> None:
    """기본 발행 수를 줄였을 때 이전에 남은 초과 개별 작업을 삭제합니다."""
    if active_count >= TASK_CLEANUP_LIMIT:
        return
    for i in range(active_count + 1, TASK_CLEANUP_LIMIT + 1):
        sub_task_name = f"{TASK_NAME}_{i:02d}"
        cmd = ["schtasks", "/Delete", "/TN", sub_task_name, "/F"]
        proc = subprocess.run(
            cmd,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if proc.returncode == 0:
            write_log(f"초과 예약 작업 삭제 완료: {sub_task_name}")


def install_windows_task(start_time: str = "00:05") -> None:
    """
    Windows 작업 스케줄러에 매일 00:05 실행되도록 등록합니다.
    스크립트가 실행되면 그날의 랜덤 14개 발행 시간을 생성하고 하루 동안 대기/실행합니다.
    """
    validate_environment()

    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
    task_run_cmd = (
        f'"{pythonw_exe}" "{Path(__file__).resolve()}" '
        f'--max-posts {DEFAULT_MAX_POSTS} --golf-posts {DEFAULT_GOLF_POSTS} --health-posts {DEFAULT_HEALTH_POSTS}'
    )

    import getpass
    username = getpass.getuser()
    schtasks_cmd = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/SC",
        "DAILY",
        "/ST",
        start_time,
        "/TR",
        task_run_cmd,
        "/RL",
        "LIMITED",
        "/RU",
        username,
        "/IT",
        "/F",
    ]

    write_log("Windows 작업 스케줄러 등록 시작")
    write_log(" ".join(schtasks_cmd))

    proc = subprocess.run(
        schtasks_cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"작업 스케줄러 등록 실패: returncode={proc.returncode}")

    write_log(f"작업 스케줄러 등록 완료: {TASK_NAME} | 매일 {start_time}")


def uninstall_windows_task() -> None:
    cmd = ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"]
    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    if proc.returncode == 0:
        write_log(f"작업 스케줄러 삭제 완료: {TASK_NAME}")
    else:
        write_log(f"작업 스케줄러 삭제 실패 또는 이미 없음: {TASK_NAME}")

    for i in range(1, TASK_CLEANUP_LIMIT + 1):
        sub_task_name = f"{TASK_NAME}_{i:02d}"
        cmd_sub = ["schtasks", "/Delete", "/TN", sub_task_name, "/F"]
        subprocess.run(cmd_sub, text=True, encoding="utf-8", errors="replace", shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    write_log("등록된 개별 예약 작업들도 모두 삭제 시도 완료했습니다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="골프 티스토리 24시간 랜덤 14회 자동 발행 스케줄러")
    parser.add_argument("--max-posts", type=int, default=DEFAULT_MAX_POSTS, help="하루 최대 발행 개수, 기본 14")
    parser.add_argument("--golf-posts", type=int, default=None, help="골프 글 발행 개수. 기본은 14개 기준 7개")
    parser.add_argument("--health-posts", type=int, default=None, help="건강식품 쿠팡 글 발행 개수. 기본은 14개 기준 7개")
    parser.add_argument("--today-only", action="store_true", help="현재 시각부터 오늘 23:59 안에서만 예약 생성")
    parser.add_argument("--dry-run", action="store_true", help="실제 발행 없이 흐름만 테스트")
    parser.add_argument("--print-plan", action="store_true", help="오늘 랜덤 발행 시간표만 출력")
    parser.add_argument("--reset-today", action="store_true", help="오늘 스케줄/상태 파일 초기화")
    parser.add_argument("--install", action="store_true", help="Windows 작업 스케줄러에 매일 00:05 실행 등록")
    parser.add_argument("--uninstall", action="store_true", help="Windows 작업 스케줄러 등록 삭제")
    parser.add_argument("--start-time", default="00:05", help="--install 시 시작 시간, 기본 00:05")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.print_plan:
        validate_environment()
        print_plan(max_posts=args.max_posts)
        sys.exit(0)

    schedule_lock = acquire_schedule_register_lock()
    try:
        if args.uninstall:
            uninstall_windows_task()
            sys.exit(0)

        if args.install:
            install_windows_task(start_time=args.start_time)
            sys.exit(0)

        if args.reset_today:
            reset_today_state()

        run_scheduler(
            max_posts=args.max_posts,
            dry_run=args.dry_run,
            today_only=args.today_only,
            golf_posts=args.golf_posts,
            health_posts=args.health_posts,
        )
    finally:
        release_schedule_register_lock(schedule_lock)
