##########################################################################
# 네이버 쇼핑 자동화 크롤러 GUI (주피터 원본 로직 + 다크모드 GUI 통합)
##########################################################################

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import sys
import os
import io
import time
import random
import pandas as pd
import pymysql

# ── Selenium
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ──────────────────────────────────────────────────────────────────────
#  색상 / 폰트 상수 (네이버 테마 적용)
# ──────────────────────────────────────────────────────────────────────
C_BG        = "#0F0F17"   # 전체 배경 (딥 네이비)
C_PANEL     = "#1A1A2E"   # 패널 배경
C_CARD      = "#16213E"   # 카드 배경
C_ACCENT    = "#03C75A"   # 메인 컬러 (네이버 그린)
C_ACCENT2   = "#2DB400"   # 서브 포인트 컬러
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
        if "에러" in t or "실패" in t or "Error" in t or "오류" in t or "🚨" in t:
            return "err"
        if "🚀" in t or ">>" in t:
            return "step"
        if t.startswith("="):
            return "sep"
        return "info"


# ──────────────────────────────────────────────────────────────────────
#  크롤링 로직 (사용자 주피터 노트북 원본 코드)
# ──────────────────────────────────────────────────────────────────────
def run_crawl(params: dict, stop_event: threading.Event, progress_cb):
    query_txt   = params["query_txt"]
    cnt         = params["cnt"]
    f_dir       = params["f_dir"]

    print("=" *80)
    print(" 개인프로젝트 네이버 쇼핑 수집 (GUI 구동)")
    print("=" *80)
    print("\n🚀 데이터 수집을 시작합니다. 브라우저가 열리면 잠시 지켜봐주세요!\n")

    s_time = time.time()

    # 폴더 설정 로직
    n = time.localtime()
    s = '%04d-%02d-%02d-%02d-%02d-%02d' % (n.tm_year, n.tm_mon, n.tm_mday, n.tm_hour, n.tm_min, n.tm_sec)
    save_dir = os.path.join(f_dir, f"{s}-{query_txt}")
    os.makedirs(save_dir, exist_ok=True)
    os.chdir(save_dir)
    
    ff_name = os.path.join(save_dir, f"{s}-{query_txt}.txt")
    fc_name = os.path.join(save_dir, f"{s}-{query_txt}.csv")
    fx_name = os.path.join(save_dir, f"{s}-{query_txt}.xls")

    # 크롬 드라이버 셋팅 (인스타 코드 참조)
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    try:
        from selenium.webdriver.chrome.service import Service
        s_srv  = Service("c:/py_temp/chromedriver.exe")
        driver = webdriver.Chrome(service=s_srv, options=options)
    except Exception:
        driver = webdriver.Chrome(options=options)
        
    driver.maximize_window()
    wait = WebDriverWait(driver, 10)

    try:
        # 네이버 쇼핑으로 바로 접속!
        print("\n네이버 쇼핑 접속 중...")
        driver.get("https://shopping.naver.com/ns/home")
        time.sleep(3) 
        
        # 최신 네이버 쇼핑 검색창 속성에 맞게 수정
        search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[title="검색어 입력"]')))
        
        search_input.click()
        search_input.clear()
        
        for a in query_txt:
            search_input.send_keys(a)
            time.sleep(random.uniform(0.1, 0.35))
            
        time.sleep(1) 
        search_input.send_keys(Keys.ENTER) 
        
        print(f">> 네이버 쇼핑 '{query_txt}' 단어 타자 입력 & 검색 완료! 결과창 렌더링 대기...")
        time.sleep(4) 

    except Exception as e:
        print(f"\n[접속 에러 발생] 진행 도중 문제가 생겼습니다: {e}")
        driver.quit()
        return

    # ==========================================================
    # 크롤링 영역 (원본 로직 유지)
    # ==========================================================
    product_names = []   
    prices = []          
    discounts = []       
    stars = []           
    review_cnts = []     
    total_count = 0  

    print('\n상품 정보를 수집합니다. 잠시만 기다려 주세요~~~~~~~~')
    time.sleep(2) 

    seen_products = set()

    while total_count < cnt:
        if stop_event.is_set():
            print("\n⚠️ 사용자에 의해 수집이 강제 중단되었습니다.")
            break

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        items = soup.find_all('li', class_='composite_card_container')
        
        if len(items) == 0:
            print("🚨 화면에서 상품을 찾지 못했습니다. 클래스명이 맞는지 다시 확인해주세요!")
            
        for item in items:
            if total_count >= cnt or stop_event.is_set():
                break
                
            # 1. 제품 이름
            try:
                name_node = item.find('strong', class_='productCardTitle_product_card_title__eQupA')
                name = name_node.get_text(strip=True) if name_node else "이름 없음"
            except:
                name = "이름 없음"

            # 중복 체크
            if name in seen_products or name == "이름 없음":
                continue
                
            seen_products.add(name)
            total_count += 1
            progress_cb(total_count, cnt) # GUI 진행률 업데이트
            
            print(f"🚀 총 {cnt}건 중 {total_count}번째 상품 수집 중 =========")
            f = open(ff_name, 'a', encoding='UTF-8')
            f.write("\n")
            f.write(f"[{total_count} 번째 상품 정보]====\n")
            f.write("1.제품의 이름: " + name + "\n")
            product_names.append(name)
            
            # 2. 가격
            try:
                price_node = item.find('span', class_='priceTag_price__hGtfm')
                price = price_node.get_text(strip=True) if price_node else "0"
            except:
                price = "0"
                
            f.write("2.제품 판매가: " + price + "원\n")
            prices.append(price)

            # 3. 할인율
            try:
                dc_node = item.find('span', class_='priceTag_discount_ratio__VE866')
                discount = dc_node.get_text(strip=True).replace("할인", "").replace("%", "") if dc_node else "0"
            except:
                discount = "0"
                
            f.write("3.할인율: " + discount + "%\n")
            discounts.append(discount)

            # 4. 리뷰 별점
            try:
                star_node = item.find('span', class_='productCardReview_star__7iHNO')
                star = star_node.get_text(strip=True).replace("별점", "") if star_node else "0"
            except:
                star = "0"
                
            f.write("4.리뷰 별점: " + star + "\n")
            stars.append(star)

            # 5. 리뷰 개수
            try:
                review_nodes = item.find_all('span', class_='productCardReview_text__A9N9N')
                review_cnt = "0"
                for r_node in review_nodes:
                    r_text = r_node.get_text(strip=True)
                    if "리뷰" in r_text:
                        review_cnt = r_text.replace("리뷰", "").strip()
                        break
            except:
                review_cnt = "0"
                
            f.write("5.리뷰 개수: " + review_cnt + "\n")
            review_cnts.append(review_cnt)

            f.close()
            time.sleep(0.1)

        if total_count >= cnt or stop_event.is_set():
            if total_count >= cnt:
                print(f"\n✅ 수집 목표량({cnt}건) 달성 완료!")
            break
        else:
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(2)

    # ==========================================================
    # xls 형태와 csv 형태로 저장하기
    # ==========================================================
    news_reple = pd.DataFrame()
    news_reple['제품의 이름'] = pd.Series(product_names)
    news_reple['제품 판매가'] = pd.Series(prices)
    news_reple['할인율'] = pd.Series(discounts)
    news_reple['리뷰 별점'] = pd.Series(stars)
    news_reple['리뷰 개수'] = pd.Series(review_cnts)

    try:
        news_reple.to_csv(fc_name, encoding="utf-8-sig", index=False)
        news_reple.to_excel(fx_name, index=False, engine='openpyxl')
    except Exception as e:
        print(f"⚠️ 파일 저장 경고: {e}")

    # ==========================================================
    # 수집한 정보를 통째로 MySQL DB에 넣기!
    # ==========================================================
    if params.get("use_db"):
        try:
            conn = pymysql.connect(
                host=params["db_host"],         
                user=params["db_user"],              
                password=params["db_pass"],  
                db=params["db_name"],  
                charset='utf8mb4',        
                cursorclass=pymysql.cursors.DictCursor
            )
            with conn.cursor() as cursor:
                create_table_sql = """
                CREATE TABLE IF NOT EXISTS naver_shopping_products (
                    id INT AUTO_INCREMENT PRIMARY KEY, 
                    product_name VARCHAR(255),         
                    price VARCHAR(50),                 
                    discount VARCHAR(50),
                    star VARCHAR(50),
                    review_cnt VARCHAR(50)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                cursor.execute(create_table_sql)
                
                insert_sql = """
                INSERT INTO naver_shopping_products (product_name, price, discount, star, review_cnt) 
                VALUES (%s, %s, %s, %s, %s)
                """
                for i in range(len(product_names)):
                    cursor.execute(insert_sql, (
                        product_names[i], 
                        prices[i], 
                        discounts[i],
                        stars[i],
                        review_cnts[i]
                    ))
                conn.commit()
                print(f"\n🎉 짝짝짝! 네이버 쇼핑 DB 저장까지 완벽하게 완료되었습니다!")
                
        except Exception as e:
            print(f"\n🚨 [DB 에러] DB 저장 중 에러가 발생했습니다: {e}")
        finally:
            try:
                conn.close()
            except:
                pass

    # ==========================================================
    # 요약 정보 출력하기
    # ==========================================================
    e_time = time.time()
    t_time = e_time - s_time

    print("\n" + "=" *80)
    print(f"1. 모든 작업 종료. 수집된 전체 상품 수는 {total_count} 건 입니다.")
    print("2. 총 소요시간은 %s 초 입니다 " %round(t_time,1))
    print("3. 파일 저장 완료: txt 파일명 : %s " %ff_name)
    print("4. 파일 저장 완료: csv 파일명 : %s " %fc_name)
    print("5. 파일 저장 완료: xls 파일명 : %s " %fx_name)
    print("=" *80)

    driver.quit() 
    progress_cb(cnt, cnt)


# ──────────────────────────────────────────────────────────────────────
#  GUI 앱 구조
# ──────────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("네이버 쇼핑 데이터 수집기")
        self.geometry("940x760")
        self.resizable(True, True)
        self.configure(bg=C_BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._stop_event  = threading.Event()
        self._worker      = None
        self._orig_stdout = sys.stdout

        self._build_ui()
        self._redirect_stdout()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=C_BG, pady=10)
        hdr.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(
            hdr, text="🛒", font=("Segoe UI Emoji", 26),
            bg=C_BG, fg=C_ACCENT
        ).pack(side="left")
        tk.Label(
            hdr, text="  네이버 쇼핑 자동화 크롤러",
            font=FONT_TITLE, bg=C_BG, fg=C_TEXT
        ).pack(side="left")
        tk.Label(
            hdr, text="v1.0", font=("Malgun Gothic", 9),
            bg=C_BG, fg=C_SUBTLE
        ).pack(side="left", padx=(6, 0), pady=(6, 0))

        tk.Frame(self, bg=C_ACCENT, height=2).pack(fill="x", padx=20, pady=(8, 0))

        body = tk.Frame(self, bg=C_BG)
        body.pack(fill="both", expand=True, padx=20, pady=12)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left  = tk.Frame(body, bg=C_BG)
        right = tk.Frame(body, bg=C_BG)
        left.grid( row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_form(left)
        self._build_console(right)

    def _build_form(self, parent):
        self._card(parent, "🔍  수집 설정", [
            ("검색 키워드",    "query_txt",    False, "예: 런닝화"),
            ("수집할 상품 수", "cnt",          False, "예: 30"),
        ])

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

        self.f_dir = tk.StringVar(value="c:\\py_temp\\네이버쇼핑\\")
        row_f = tk.Frame(save_inner, bg=C_CARD)
        row_f.pack(fill="x")
        self._styled_entry(row_f, self.f_dir).pack(side="left", fill="x", expand=True)
        tk.Button(
            row_f, text="📁", font=("Segoe UI Emoji", 11),
            bg=C_BORDER, fg=C_TEXT,
            activebackground=C_ACCENT2, activeforeground=C_BG,
            relief="flat", bd=0, cursor="hand2", padx=8,
            command=self._browse_dir,
        ).pack(side="left", padx=(6, 0))

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
        return tk.Entry(
            parent, textvariable=textvariable, show=show,
            bg=C_ENTRY, fg=C_TEXT, insertbackground=C_ACCENT,
            relief="flat", bd=0, font=FONT_BODY,
            highlightthickness=1, highlightbackground=C_BORDER,
            highlightcolor=C_ACCENT,
        )

    def _build_db_card(self, parent):
        self._db_open = tk.BooleanVar(value=False)
        self.use_db   = tk.BooleanVar(value=False)

        tog_bar = tk.Frame(parent, bg=C_CARD, cursor="hand2")
        tog_bar.pack(fill="x", pady=(0, 10))
        tog_bar.bind("<Button-1>", lambda e: self._toggle_db())

        tk.Label(
            tog_bar, text="  🗄  MySQL DB 연동 (선택)",
            font=FONT_HEAD, bg=C_CARD, fg=C_ACCENT2,
            padx=10, pady=6
        ).pack(side="left")
        self._db_arrow = tk.Label(tog_bar, text="▶", font=FONT_BODY, bg=C_CARD, fg=C_SUBTLE)
        self._db_arrow.pack(side="right", padx=10)

        self._db_frame = tk.Frame(parent, bg=C_CARD)
        db_inner = tk.Frame(self._db_frame, bg=C_CARD, padx=10, pady=8)
        db_inner.pack(fill="x")

        tk.Checkbutton(
            db_inner, text="데이터베이스 자동 저장 활성화", variable=self.use_db,
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

    def _build_console(self, parent):
        prog_frame = tk.Frame(parent, bg=C_BG)
        prog_frame.pack(fill="x", pady=(0, 6))

        tk.Label(prog_frame, text="수집 진행률", font=FONT_BODY, bg=C_BG, fg=C_SUBTLE).pack(side="left")

        self._prog_label = tk.Label(prog_frame, text="0 / 0", font=("Malgun Gothic", 9), bg=C_BG, fg=C_ACCENT2)
        self._prog_label.pack(side="right")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "naver.Horizontal.TProgressbar",
            troughcolor=C_ENTRY, background=C_ACCENT,
            lightcolor=C_ACCENT, darkcolor=C_ACCENT,
            bordercolor=C_BORDER, thickness=14,
        )
        self._prog = ttk.Progressbar(
            parent, style="naver.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate", maximum=100,
        )
        self._prog.pack(fill="x", pady=(0, 10))

        tk.Label(parent, text="시스템 로그", font=FONT_HEAD, bg=C_BG, fg=C_SUBTLE).pack(anchor="w")

        self.console = scrolledtext.ScrolledText(
            parent, bg=C_ENTRY, fg=C_TEXT, font=FONT_MONO, relief="flat", bd=0,
            state="disabled", highlightthickness=1, highlightbackground=C_BORDER,
        )
        self.console.pack(fill="both", expand=True, pady=(4, 10))

        self.console.tag_config("ok",   foreground=C_GREEN)
        self.console.tag_config("err",  foreground=C_RED)
        self.console.tag_config("warn", foreground=C_ACCENT2)
        self.console.tag_config("step", foreground="#64B5F6")
        self.console.tag_config("sep",  foreground=C_BORDER)
        self.console.tag_config("info", foreground=C_TEXT)

        btn_row = tk.Frame(parent, bg=C_BG)
        btn_row.pack(fill="x")

        self.btn_start = tk.Button(
            btn_row, text="▶  크롤링 시작",
            font=FONT_BTN, bg=C_ACCENT, fg="#FFFFFF",
            activebackground="#029F48", activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=20, pady=10,
            cursor="hand2", command=self._start,
        )
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_stop = tk.Button(
            btn_row, text="■  강제 중단",
            font=FONT_BTN, bg=C_BORDER, fg=C_SUBTLE,
            activebackground=C_RED, activeforeground="#FFFFFF",
            relief="flat", bd=0, padx=14, pady=10,
            cursor="hand2", command=self._stop, state="disabled",
        )
        self.btn_stop.pack(side="left")

        tk.Button(
            btn_row, text="🗑  화면 지우기",
            font=("Malgun Gothic", 9), bg=C_CARD, fg=C_SUBTLE,
            activebackground=C_BORDER, activeforeground=C_TEXT,
            relief="flat", bd=0, padx=10, pady=10,
            cursor="hand2", command=self._clear_console,
        ).pack(side="right")

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.f_dir.set(d + os.sep)

    def _validate_inputs(self) -> dict | None:
        errors = []
        if not self.query_txt.get().strip(): errors.append("검색 키워드를 입력하세요.")
        
        try:
            cnt = int(self.cnt.get())
            assert cnt > 0
        except:
            errors.append("수집 상품 수는 1 이상의 정수여야 합니다.")
            cnt = 0

        if errors:
            self._log_err("\n".join(f"⚠️ {e}" for e in errors))
            return None

        return {
            "query_txt":  self.query_txt.get().strip(),
            "cnt":        cnt,
            "f_dir":      self.f_dir.get().strip() or "c:\\py_temp\\",
            "use_db":     self.use_db.get(),
            "db_host":    self.db_host.get(),
            "db_user":    self.db_user.get(),
            "db_pass":    self.db_pass.get(),
            "db_name":    self.db_name.get(),
        }

    def _start(self):
        params = self._validate_inputs()
        if not params: return

        self._stop_event.clear()
        self.btn_start.config(state="disabled", text="⏳  수집 중...")
        self.btn_stop.config(state="normal", bg=C_RED, fg="#FFFFFF")
        self._prog["value"] = 0
        self._prog_label.config(text=f"0 / {params['cnt']}")
        self._clear_console()

        self._worker = threading.Thread(target=self._crawl_thread, args=(params,), daemon=True)
        self._worker.start()

    def _crawl_thread(self, params):
        try:
            run_crawl(params, self._stop_event, self._update_progress)
        except Exception as e:
            print(f"\n🚨 시스템 에러 발생: {e}")
        finally:
            self.after(0, self._on_done)

    def _stop(self):
        self._stop_event.set()
        self.btn_stop.config(state="disabled", text="중단 처리 중...")
        print("\n⚠️ 수집 중단 명령이 전달되었습니다. 현재 작업을 마무리 후 종료합니다.")

    def _on_done(self):
        self.btn_start.config(state="normal", text="▶  크롤링 시작")
        self.btn_stop.config(state="disabled", bg=C_BORDER, fg=C_SUBTLE, text="■  강제 중단")

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

    def _redirect_stdout(self):
        sys.stdout = GUIConsole(self.console)

    def _on_close(self):
        sys.stdout = self._orig_stdout
        if self._worker and self._worker.is_alive():
            self._stop_event.set()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()