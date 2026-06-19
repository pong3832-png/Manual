##########################################################################
# 인스타그램 해시태그 크롤러 GUI  (원본 로직 + GUI 통합)
##########################################################################

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys
import os
import re
import io
import time
import math
import random
import unicodedata
import urllib.parse
import pandas as pd
import pymysql
import pyautogui
from datetime import datetime
from pathlib import Path

# ── Selenium
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# bmp 이모지 처리
bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xFFFF)

# ──────────────────────────────────────────────────────────────────────
#  색상 / 폰트 상수
# ──────────────────────────────────────────────────────────────────────
C_BG        = "#0F0F17"   # 전체 배경 (딥 네이비)
C_PANEL     = "#1A1A2E"   # 패널 배경
C_CARD      = "#16213E"   # 카드 배경
C_ACCENT    = "#E91E8C"   # 메인 핑크 (인스타)
C_ACCENT2   = "#F9A825"   # 옐로우 포인트
C_GREEN     = "#00E676"   # 성공 초록
C_RED       = "#FF5252"   # 에러 빨강
C_TEXT      = "#ECEFF4"   # 본문 텍스트
C_SUBTLE    = "#8892A4"   # 서브 텍스트
C_BORDER    = "#2D3561"   # 테두리
C_ENTRY     = "#0D0D1A"   # 입력창 배경

FONT_TITLE  = ("Malgun Gothic", 18, "bold")
FONT_HEAD   = ("Malgun Gothic", 11, "bold")
FONT_BODY   = ("Malgun Gothic", 10)
FONT_MONO   = ("Consolas", 9)
FONT_BTN    = ("Malgun Gothic", 11, "bold")


# ──────────────────────────────────────────────────────────────────────
#  stdout → GUI 콘솔 리다이렉터
# ──────────────────────────────────────────────────────────────────────
class GUIConsole(io.TextIOBase):
    """print() 출력을 GUI 텍스트 위젯으로 보내는 래퍼"""

    def __init__(self, widget: scrolledtext.ScrolledText, tag_fn=None):
        self.widget  = widget
        self.tag_fn  = tag_fn  # 태그 결정 콜백 (line → tag_name)

    def write(self, text):
        if not text:
            return
        tag = self._pick_tag(text)
        self.widget.configure(state="normal")
        self.widget.insert("end", text, tag)
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass

    @staticmethod
    def _pick_tag(text):
        t = text.strip()
        if "✅" in t or "완료" in t or "성공" in t or "짝짝" in t:
            return "ok"
        if "⚠️" in t or "경고" in t or "Warning" in t:
            return "warn"
        if "에러" in t or "실패" in t or "Error" in t or "오류" in t:
            return "err"
        if "🚀" in t:
            return "step"
        if t.startswith("="):
            return "sep"
        return "info"


# ──────────────────────────────────────────────────────────────────────
#  크롤링 로직
# ──────────────────────────────────────────────────────────────────────
def run_crawl(params: dict, stop_event: threading.Event, progress_cb):
    """
    params 키:
        v_id, v_passwd, query_txt, cnt, comment_cnt, f_dir,
        use_db, db_host, db_user, db_pass, db_name
    """
    v_id        = params["v_id"]
    v_passwd    = params["v_passwd"]
    query_txt   = params["query_txt"].replace("#", "").strip()
    cnt         = params["cnt"]
    comment_cnt = params["comment_cnt"]
    f_dir       = params["f_dir"]

    # ── 폴더 / 파일명 설정
    s_time = time.time()
    now    = time.localtime()
    s      = "%04d-%02d-%02d-%02d-%02d-%02d" % (
        now.tm_year, now.tm_mon, now.tm_mday,
        now.tm_hour, now.tm_min, now.tm_sec
    )
    save_dir = os.path.join(f_dir, f"{s}-{query_txt}")
    os.makedirs(save_dir, exist_ok=True)

    ff_name = os.path.join(save_dir, f"{s}-{query_txt}.txt")
    fc_name = os.path.join(save_dir, f"{s}-{query_txt}.csv")
    fx_name = os.path.join(save_dir, f"{s}-{query_txt}.xls")

    # ── 드라이버 초기화
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        s_srv  = Service("c:/py_temp/chromedriver.exe")
        driver = webdriver.Chrome(service=s_srv, options=options)
    except Exception:
        driver = webdriver.Chrome(options=options)

    driver.get("https://www.instagram.com/")
    time.sleep(random.randrange(1, 5))
    driver.maximize_window()

    wait = WebDriverWait(driver, 10)

    # ── 로그인
    print("\n인스타그램 로그인 중...")
    try:
        try:
            eid = wait.until(EC.element_to_be_clickable((By.NAME, "username")))
            for a in v_id:
                eid.send_keys(a)
                time.sleep(0.3)
            epwd = driver.find_element(By.NAME, "password")
            for b in v_passwd:
                epwd.send_keys(b)
                time.sleep(0.5)
            epwd.send_keys(Keys.ENTER)
            time.sleep(random.randrange(1, 5))
        except Exception:
            eid = driver.find_element(By.NAME, "email")
            for a in v_id:
                eid.send_keys(a)
                time.sleep(0.3)
            epwd = driver.find_element(By.NAME, "pass")
            for b in v_passwd:
                epwd.send_keys(b)
                time.sleep(0.5)
            driver.find_element(
                By.XPATH, '//*[@id="login_form"]/div/div[1]/div/div[3]/div/div/div'
            ).click()
            time.sleep(random.randrange(1, 5))

        print("✅ 로그인 성공! 팝업 처리 중...")

        for xpath in [
            "//*[text()='나중에 하기']",
            "//button[text()='나중에 하기']",
            "//*[text()='사용하지 않음']",
        ]:
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                btn.click()
                time.sleep(3)
            except Exception:
                pass

        # ── 해시태그 페이지 이동
        element = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//a[.//svg[@aria-label='검색' or @aria-label='Search']"
            " or .//span[text()='검색' or text()='Search']]"
        )))
        element.click()
        time.sleep(2)

        selector = (
            "input[type='text'][placeholder='검색'],"
            "input[type='text'][aria-label*='검색'],"
            "[role='textbox'][aria-label*='검색']"
        )
        search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        for c in query_txt:
            search_box.send_keys(c)
            time.sleep(0.2)
        time.sleep(3)

        encoded = urllib.parse.quote(query_txt)
        driver.get(f"https://www.instagram.com/explore/tags/{encoded}/")
        time.sleep(6)

    except Exception as e:
        print(f"에러: 로그인/검색 실패 → {e}")
        driver.quit()
        return

    # ── 데이터 컨테이너
    post_no, post_board_no = [], []
    post_authors, post_contents = [], []
    post_comments, post_likes, post_hashtags = [], [], []

    total_count = 0
    row_count   = 0

    print("\n게시글 수집 시작!\n")

    try:
        first_post = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href^="/p/"]'))
        )
        first_post.click()
        time.sleep(3)
    except Exception as e:
        print(f"첫 게시글 접근 실패: {e}")
        driver.quit()
        return

    while total_count < cnt:
        if stop_event.is_set():
            print("\n⚠️ 사용자가 수집을 중단했습니다.")
            break

        total_count += 1
        progress_cb(total_count, cnt)
        print(f"\n🚀 [{total_count}/{cnt}] 게시글 수집 중 ─────────────────")

        f = open(ff_name, "a", encoding="UTF-8")
        f.write(f"\n[{total_count} 번째 게시글 정보]====\n")

        # 댓글 스크롤 로직
        scroll_attempts        = 0
        no_new_comments_count  = 0
        prev_comment_count     = 0

        while scroll_attempts < 30:
            if stop_event.is_set():
                break

            temp_html  = driver.page_source
            temp_soup  = BeautifulSoup(temp_html, "html.parser")

            try:
                t_cn  = temp_soup.select_one(
                    "h1._ap3a._aaco._aacu._aacx._aad7._aade"
                )
                t_txt = t_cn.get_text(separator=" ", strip=True) if t_cn else ""
            except Exception:
                t_txt = ""

            t_c_nodes = temp_soup.select('div.xt0psk2 span[dir="auto"]')
            cur_valid  = [
                c.get_text(separator=" ", strip=True)
                for c in t_c_nodes
                if c.get_text(separator=" ", strip=True) and
                c.get_text(separator=" ", strip=True) not in t_txt
            ]
            cur_cnt = len(cur_valid)

            if cur_cnt == prev_comment_count:
                no_new_comments_count += 1
            else:
                no_new_comments_count = 0
            prev_comment_count = cur_cnt

            if scroll_attempts > 0:
                print(f"   💬 댓글 {cur_cnt} / 목표 {comment_cnt}")

            if cur_cnt >= comment_cnt:
                print("   ✅ 목표 댓글 수 도달!")
                break
            if no_new_comments_count >= 3:
                print("   ⚠️ 더 불러올 댓글 없음. 수집 완료.")
                break

            try:
                dom_cs = driver.find_elements(
                    By.CSS_SELECTOR, 'div.xt0psk2 span[dir="auto"]'
                )
                if dom_cs:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center',behavior:'smooth'});",
                        dom_cs[-1],
                    )
                time.sleep(1.0)

                more_btns = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div._abm0 svg[aria-label='댓글 더 읽어들이기'],"
                    "div._abm0 svg[aria-label='더 보기']",
                )
                if more_btns:
                    driver.execute_script(
                        """
                        var t = arguments[0].closest('div._abm0') || arguments[0];
                        t.dispatchEvent(new MouseEvent('click',
                            {bubbles:true,cancelable:true,view:window}));
                        """,
                        more_btns[0],
                    )
                    time.sleep(1.5)
                else:
                    txt_btns = driver.find_elements(
                        By.XPATH,
                        "//*[text()='댓글 더 보기' or text()='답글 더 보기']",
                    )
                    if txt_btns:
                        driver.execute_script("arguments[0].click();", txt_btns[0])
                        time.sleep(1.5)
            except Exception:
                time.sleep(1.5)

            scroll_attempts += 1

        # ── 최종 파싱
        html  = driver.page_source
        soup  = BeautifulSoup(html, "html.parser")

        # 작성자
        try:
            an = soup.select_one(
                "span.x1lliihq.x1plvlek.xryxfnj.x1n2onr6.xyejjpt"
                ".x15dsfln.x193iq5w.xeuugli.x1fj9vlw.x13faqbe"
                ".x1vvkbs.x1s928wv.xhkezso.x1gmr53x.x1cpjm7i"
                ".x1fgarty.x1943h6x.x1i0vuye.xvs91rp.x1s688f"
                ".x5n08af.x10wh9bi.xpm28yp.x8viiok.x1o7cslx"
            )
            if not an:
                an = soup.select_one("header h2 span[dir='auto'], h2 a")
            author = an.get_text(strip=True) if an else "작성자 없음"
        except Exception:
            author = "작성자 없음"

        # 본문
        try:
            cn     = soup.select_one("h1._ap3a._aaco._aacu._aacx._aad7._aade")
            content = cn.get_text(separator=" ", strip=True) if cn else "내용 없음"
        except Exception:
            content = "내용 없음"

        # 댓글
        try:
            cnodes = soup.select('div.xt0psk2 span[dir="auto"]')
            comments_texts = []
            for c in cnodes:
                ct = c.get_text(separator=" ", strip=True)
                if ct and ct not in content:
                    comments_texts.append(ct)
                if len(comments_texts) >= comment_cnt:
                    break
        except Exception:
            comments_texts = []

        # 좋아요
        try:
            lnodes = soup.select(
                "span.xdj266r.x14z9mp.xat24cr.x1lziwak.xexx8yu"
                ".xyri2b.x18d9i69.x1c1uobl.x1hl2dhg.x16tdsg8.x1vvkbs"
            )
            likes = "좋아요 없음"
            for node in lnodes:
                t = node.get_text(strip=True)
                if t.replace(",", "").isdigit():
                    likes = t
                    break
            if likes == "좋아요 없음":
                fb = soup.find(string=re.compile(r"좋아요[\s]*[\d,]+개|여러 명"))
                if fb:
                    likes = fb.strip()
        except Exception:
            likes = "좋아요 없음"

        # 해시태그
        try:
            hnodes = soup.select('a[href*="/explore/tags/"]')
            hlist  = []
            for h in hnodes:
                ht = h.get_text(strip=True)
                if ht.startswith("#") and ht not in hlist:
                    hlist.append(ht)
            hashtags = " ".join(hlist) if hlist else "해시태그 없음"
        except Exception:
            hashtags = "해시태그 없음"

        # 저장
        f.write("1.작성자: " + author + "\n")
        f.write("2.본문 내용: " + content + "\n")

        if not comments_texts:
            f.write("3.댓글: 댓글 없음\n")
            row_count += 1
            post_no.append(row_count);      post_board_no.append(total_count)
            post_authors.append(author);    post_contents.append(content)
            post_comments.append("댓글 없음"); post_likes.append(likes)
            post_hashtags.append(hashtags)
        else:
            for idx, ct in enumerate(comments_texts):
                f.write(f"3.댓글({idx+1}): {ct}\n")
                row_count += 1
                post_no.append(row_count);  post_board_no.append(total_count)
                post_authors.append(author); post_contents.append(content)
                post_comments.append(ct);   post_likes.append(likes)
                post_hashtags.append(hashtags)

        f.write("4.좋아요 수: " + likes + "\n")
        f.write("5.해쉬태그: " + hashtags + "\n")
        f.close()

        print(f"   → @{author} | 좋아요:{likes} | 댓글:{len(comments_texts)}개")

        if total_count >= cnt:
            print(f"\n✅ 수집 완료! {cnt}건 달성!")
            break

        # 다음 게시물
        try:
            nb = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'svg[aria-label="다음"]')
            ))
            driver.execute_script("arguments[0].closest('button').click();", nb)
            time.sleep(random.uniform(1.8, 3.2))
        except Exception:
            try:
                webdriver.ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
                time.sleep(random.uniform(1.8, 3.2))
            except Exception:
                print("다음 게시물 화살표를 찾을 수 없습니다. 종료.")
                break

    # ── DataFrame 저장
    df = pd.DataFrame({
        "번호":       post_no,
        "게시글 번호": post_board_no,
        "작성자":      post_authors,
        "본문 내용":   post_contents,
        "댓글":        post_comments,
        "좋아요 수":   post_likes,
        "해쉬태그":    post_hashtags,
    })
    try:
        df.to_csv(fc_name,  encoding="utf-8-sig", index=False)
        df.to_excel(fx_name, index=False, engine="openpyxl")
    except Exception as e:
        print(f"⚠️ 파일 저장 경고: {e}")

    # ── DB 저장 (옵션)
    if params.get("use_db"):
        print("\nDB 저장 중...")
        try:
            conn = pymysql.connect(
                host     = params["db_host"],
                user     = params["db_user"],
                password = params["db_pass"],
                db       = params["db_name"],
                charset  = "utf8mb4",
                cursorclass = pymysql.cursors.DictCursor,
            )
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS insta_posts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        post_no INT, post_board_no INT,
                        author VARCHAR(255), content TEXT,
                        comments TEXT, likes VARCHAR(50), hashtags TEXT
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                sql = """
                    INSERT INTO insta_posts
                        (post_no, post_board_no, author, content,
                         comments, likes, hashtags)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """
                for i in range(len(post_authors)):
                    cur.execute(sql, (
                        post_no[i], post_board_no[i],
                        post_authors[i], post_contents[i],
                        post_comments[i], post_likes[i], post_hashtags[i],
                    ))
                conn.commit()
            conn.close()
            print("🎉 DB 저장 완료!")
        except Exception as e:
            print(f"에러: DB 저장 실패 → {e}")

    # ── 요약
    e_time = time.time()
    t_time = round(e_time - s_time, 1)
    print("\n" + "="*60)
    print(f"✅ 완료! 수집 게시글: {total_count}건 / 전체 행: {row_count}개")
    print(f"⏱  소요 시간: {t_time}초")
    print(f"📄 TXT  → {ff_name}")
    print(f"📄 CSV  → {fc_name}")
    print(f"📄 XLSX → {fx_name}")
    print("="*60)

    driver.quit()
    progress_cb(cnt, cnt)


# ──────────────────────────────────────────────────────────────────────
#  GUI 앱
# ──────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("인스타그램 해시태그 크롤러")
        self.geometry("940x760")
        self.resizable(True, True)
        self.configure(bg=C_BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._stop_event  = threading.Event()
        self._worker      = None
        self._orig_stdout = sys.stdout

        self._build_ui()
        self._redirect_stdout()

    # ── UI 구성 ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── 타이틀 헤더
        hdr = tk.Frame(self, bg=C_BG, pady=10)
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(
            hdr, text="📸", font=("Segoe UI Emoji", 26),
            bg=C_BG, fg=C_ACCENT
        ).pack(side="left")
        tk.Label(
            hdr, text="  인스타그램 해시태그 크롤러",
            font=FONT_TITLE, bg=C_BG, fg=C_TEXT
        ).pack(side="left")
        tk.Label(
            hdr, text="v2.0", font=("Malgun Gothic", 9),
            bg=C_BG, fg=C_SUBTLE
        ).pack(side="left", padx=(6, 0), pady=(6, 0))

        # ── 구분선
        tk.Frame(self, bg=C_ACCENT, height=2).pack(fill="x", padx=20, pady=(8, 0))

        # ── 본문 2열 레이아웃
        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left  = tk.Frame(body, bg=C_BG)
        right = tk.Frame(body, bg=C_BG)
        left.grid( row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ── 왼쪽: 입력 폼
        self._build_form(left)

        # ── 오른쪽: 콘솔 + 버튼
        self._build_console(right)

    # ── 입력 폼 ───────────────────────────────────────────────────────
    def _build_form(self, parent):
        # 로그인 카드
        self._card(parent, "🔐  로그인 정보", [
            ("아이디 (이메일)", "v_id",     False),
            ("비밀번호",        "v_passwd",  True),
        ])

        # 수집 설정 카드
        self._card(parent, "🔍  수집 설정", [
            ("검색 해시태그",    "query_txt",    False, "예: 강남맛집"),
            ("수집 게시글 수",   "cnt",          False, "예: 20"),
            ("게시글당 댓글 수", "comment_cnt",  False, "예: 5"),
        ])

        # 저장 경로 카드
        save_card = tk.LabelFrame(
            parent, text="  💾  저장 경로  ",
            bg=C_CARD, fg=C_ACCENT, font=FONT_HEAD,
            bd=1, relief="solid",
            highlightbackground=C_BORDER, highlightthickness=1,
            labelanchor="nw"
        )
        save_card.pack(fill="x", pady=(0, 10))
        save_inner = tk.Frame(save_card, bg=C_CARD, padx=10, pady=8)
        save_inner.pack(fill="x")

        self.f_dir = tk.StringVar(value="c:\\py_temp\\")
        row_f = tk.Frame(save_inner, bg=C_CARD)
        row_f.pack(fill="x")
        self._styled_entry(row_f, self.f_dir).pack(
            side="left", fill="x", expand=True
        )
        tk.Button(
            row_f, text="📁", font=("Segoe UI Emoji", 11),
            bg=C_BORDER, fg=C_TEXT,
            activebackground=C_ACCENT2, activeforeground=C_BG,
            relief="flat", bd=0, cursor="hand2", padx=8,
            command=self._browse_dir,
        ).pack(side="left", padx=(6, 0))

        # DB 설정 카드 (접기/펼치기)
        self._build_db_card(parent)

    def _card(self, parent, title, fields):
        card = tk.LabelFrame(
            parent, text=f"  {title}  ",
            bg=C_CARD, fg=C_ACCENT, font=FONT_HEAD,
            bd=1, relief="solid",
            highlightbackground=C_BORDER, highlightthickness=1,
            labelanchor="nw",
        )
        card.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(card, bg=C_CARD, padx=10, pady=8)
        inner.pack(fill="x")

        for field in fields:
            label, var_name, is_pw = field[0], field[1], field[2]
            hint = field[3] if len(field) > 3 else ""
            self._form_row(inner, label, var_name, is_pw, hint)

    def _form_row(self, parent, label, var_name, is_pw=False, hint=""):
        row = tk.Frame(parent, bg=C_CARD)
        row.pack(fill="x", pady=3)

        tk.Label(
            row, text=label, font=FONT_BODY,
            bg=C_CARD, fg=C_SUBTLE, width=14, anchor="w"
        ).pack(side="left")

        sv = tk.StringVar()
        setattr(self, var_name, sv)

        entry = self._styled_entry(row, sv, show="●" if is_pw else "")
        entry.pack(side="left", fill="x", expand=True)

        if hint:
            tk.Label(
                row, text=hint, font=("Malgun Gothic", 8),
                bg=C_CARD, fg=C_BORDER
            ).pack(side="left", padx=(6, 0))

    def _styled_entry(self, parent, textvariable, show=""):
        e = tk.Entry(
            parent,
            textvariable=textvariable,
            show=show,
            bg=C_ENTRY, fg=C_TEXT,
            insertbackground=C_ACCENT,
            relief="flat", bd=0,
            font=FONT_BODY,
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_ACCENT,
        )
        return e

    def _build_db_card(self, parent):
        self._db_open = tk.BooleanVar(value=False)
        self.use_db   = tk.BooleanVar(value=False)

        tog_bar = tk.Frame(parent, bg=C_CARD, cursor="hand2")
        tog_bar.pack(fill="x", pady=(0, 10))
        tog_bar.bind("<Button-1>", lambda e: self._toggle_db())

        tk.Label(
            tog_bar, text="  🗄  MySQL DB 저장 (선택)",
            font=FONT_HEAD, bg=C_CARD, fg=C_ACCENT2,
            padx=10, pady=6
        ).pack(side="left")
        self._db_arrow = tk.Label(
            tog_bar, text="▶", font=FONT_BODY,
            bg=C_CARD, fg=C_SUBTLE
        )
        self._db_arrow.pack(side="right", padx=10)

        self._db_frame = tk.Frame(parent, bg=C_CARD)
        db_inner = tk.Frame(self._db_frame, bg=C_CARD, padx=10, pady=8)
        db_inner.pack(fill="x")

        tk.Checkbutton(
            db_inner, text="DB 저장 활성화", variable=self.use_db,
            bg=C_CARD, fg=C_TEXT, selectcolor=C_ENTRY,
            activebackground=C_CARD, font=FONT_BODY,
        ).pack(anchor="w", pady=(0, 6))

        for label, var_name, hint in [
            ("호스트",    "db_host",  "localhost"),
            ("사용자",    "db_user",  "root"),
            ("비밀번호",  "db_pass",  ""),
            ("DB 이름",   "db_name",  "youtube_db"),
        ]:
            self._form_row(db_inner, label, var_name, var_name == "db_pass", hint)
            if hint:
                getattr(self, var_name).set(hint)

    def _toggle_db(self):
        if self._db_open.get():
            self._db_frame.pack_forget()
            self._db_arrow.config(text="▶")
            self._db_open.set(False)
        else:
            self._db_frame.pack(fill="x", pady=(0, 10))
            self._db_arrow.config(text="▼")
            self._db_open.set(True)

    # ── 콘솔 패널 ──────────────────────────────────────────────────────
    def _build_console(self, parent):
        # 프로그레스 바
        prog_frame = tk.Frame(parent, bg=C_BG)
        prog_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            prog_frame, text="진행률", font=FONT_BODY,
            bg=C_BG, fg=C_SUBTLE
        ).pack(side="left")

        self._prog_label = tk.Label(
            prog_frame, text="0 / 0", font=("Malgun Gothic", 9),
            bg=C_BG, fg=C_ACCENT2
        )
        self._prog_label.pack(side="right")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "pink.Horizontal.TProgressbar",
            troughcolor=C_ENTRY, background=C_ACCENT,
            lightcolor=C_ACCENT, darkcolor=C_ACCENT,
            bordercolor=C_BORDER, thickness=14,
        )
        self._prog = ttk.Progressbar(
            parent, style="pink.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate", maximum=100,
        )
        self._prog.pack(fill="x", pady=(0, 10))

        # 콘솔 텍스트
        tk.Label(
            parent, text="실행 로그", font=FONT_HEAD,
            bg=C_BG, fg=C_SUBTLE
        ).pack(anchor="w")

        self.console = scrolledtext.ScrolledText(
            parent, bg=C_ENTRY, fg=C_TEXT,
            font=FONT_MONO, relief="flat", bd=0,
            state="disabled",
            highlightthickness=1, highlightbackground=C_BORDER,
        )
        self.console.pack(fill="both", expand=True, pady=(4, 10))

        # 태그 색상
        self.console.tag_config("ok",   foreground=C_GREEN)
        self.console.tag_config("err",  foreground=C_RED)
        self.console.tag_config("warn", foreground=C_ACCENT2)
        self.console.tag_config("step", foreground="#64B5F6")
        self.console.tag_config("sep",  foreground=C_BORDER)
        self.console.tag_config("info", foreground=C_TEXT)

        # 버튼 행
        btn_row = tk.Frame(parent, bg=C_BG)
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row,
            text="▶  크롤링 시작",
            font=FONT_BTN, bg=C_ACCENT, fg="#FFFFFF",
            activebackground="#C2185B", activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2", command=self._start,
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_stop = tk.Button(
            btn_row,
            text="■  중단",
            font=FONT_BTN, bg=C_BORDER, fg=C_SUBTLE,
            activebackground=C_RED, activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=14, pady=10,
            cursor="hand2", command=self._stop,
            state="disabled",
        )
        self.btn_stop.pack(side="left")

        tk.Button(
            btn_row,
            text="🗑  로그 지우기",
            font=("Malgun Gothic", 9), bg=C_CARD, fg=C_SUBTLE,
            activebackground=C_BORDER, activeforeground=C_TEXT,
            relief="flat", bd=0, padx=10, pady=10,
            cursor="hand2", command=self._clear_console,
        ).pack(side="right")

    # ── 이벤트 핸들러 ──────────────────────────────────────────────────
    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.f_dir.set(d + os.sep)

    def _validate_inputs(self) -> dict | None:
        errors = []
        if not self.v_id.get().strip():
            errors.append("인스타그램 아이디를 입력하세요.")
        if not self.v_passwd.get().strip():
            errors.append("비밀번호를 입력하세요.")
        if not self.query_txt.get().strip():
            errors.append("검색 해시태그를 입력하세요.")
        try:
            cnt = int(self.cnt.get())
            assert cnt > 0
        except Exception:
            errors.append("수집 게시글 수는 양수 정수여야 합니다.")
            cnt = 0
        try:
            comment_cnt = int(self.comment_cnt.get())
            assert comment_cnt >= 0
        except Exception:
            errors.append("댓글 수는 0 이상 정수여야 합니다.")
            comment_cnt = 0

        if errors:
            self._log_err("\n".join(f"⚠️ {e}" for e in errors))
            return None

        return {
            "v_id":       self.v_id.get().strip(),
            "v_passwd":   self.v_passwd.get(),
            "query_txt":  self.query_txt.get().strip(),
            "cnt":        cnt,
            "comment_cnt": comment_cnt,
            "f_dir":      self.f_dir.get().strip() or "c:\\py_temp\\",
            "use_db":     self.use_db.get(),
            "db_host":    self.db_host.get(),
            "db_user":    self.db_user.get(),
            "db_pass":    self.db_pass.get(),
            "db_name":    self.db_name.get(),
        }

    def _start(self):
        params = self._validate_inputs()
        if not params:
            return

        self._stop_event.clear()
        self.btn_start.config(state="disabled", text="⏳  수집 중...")
        self.btn_stop.config(state="normal", bg=C_RED, fg="#FFFFFF")
        self._prog["value"] = 0
        self._prog_label.config(text=f"0 / {params['cnt']}")

        self._clear_console()
        print(f"{'='*55}")
        print(f"  크롤링 시작: #{params['query_txt']}  |  목표 {params['cnt']}건")
        print(f"{'='*55}\n")

        self._worker = threading.Thread(
            target=self._crawl_thread,
            args=(params,), daemon=True,
        )
        self._worker.start()

    def _crawl_thread(self, params):
        try:
            run_crawl(params, self._stop_event, self._update_progress)
        except Exception as e:
            print(f"\n에러: {e}")
        finally:
            self.after(0, self._on_done)

    def _stop(self):
        self._stop_event.set()
        self.btn_stop.config(state="disabled", text="중단 중...")
        print("\n⚠️ 중단 요청 전송됨...")

    def _on_done(self):
        self.btn_start.config(state="normal", text="▶  크롤링 시작")
        self.btn_stop.config(
            state="disabled", bg=C_BORDER,
            fg=C_SUBTLE, text="■  중단"
        )

    def _update_progress(self, current, total):
        pct = int(current / total * 100) if total > 0 else 0
        self.after(0, lambda: (
            self._prog.configure(value=pct),
            self._prog_label.configure(text=f"{current} / {total}"),
        ))

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def _log_err(self, msg):
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n", "err")
        self.console.see("end")
        self.console.configure(state="disabled")

    # ── stdout 리다이렉트 ──────────────────────────────────────────────
    def _redirect_stdout(self):
        sys.stdout = GUIConsole(self.console)

    def _on_close(self):
        sys.stdout = self._orig_stdout
        if self._worker and self._worker.is_alive():
            self._stop_event.set()
        self.destroy()


# ──────────────────────────────────────────────────────────────────────
#  진입점
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
