import tkinter as tk
import customtkinter as ctk
import threading
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
import time
import random 
import re
from urllib.parse import urlparse

# UI 테마 설정
ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")


class BlogAutoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("네이버 블로그 서로이웃 자동화 Pro")
        self.geometry("520x680")
        self.resizable(False, False)

        self.create_widgets()
        self.is_running = False

    def create_widgets(self):
        # 헤더 타이틀
        self.title_label = ctk.CTkLabel(
            self, text="서로이웃 자동 신청 프로그램",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_label.pack(pady=20)

        # 입력 영역 프레임
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.id_entry = ctk.CTkEntry(self.frame, placeholder_text="네이버 아이디")
        self.id_entry.pack(pady=10, padx=20, fill="x")

        self.pw_entry = ctk.CTkEntry(self.frame, placeholder_text="네이버 비밀번호", show="*")
        self.pw_entry.pack(pady=10, padx=20, fill="x")

        self.keyword_entry = ctk.CTkEntry(self.frame, placeholder_text="검색 키워드 (예: 일상, 맛집)")
        self.keyword_entry.pack(pady=10, padx=20, fill="x")

        self.count_entry = ctk.CTkEntry(self.frame, placeholder_text="신청 목표 인원수 (숫자만)")
        self.count_entry.pack(pady=10, padx=20, fill="x")

        self.msg_textbox = ctk.CTkTextbox(self.frame, height=80)
        self.msg_textbox.pack(pady=10, padx=20, fill="x")
        self.msg_textbox.insert("0.0", "서로이웃해요~블로그 자주 방문하고 소통합시다!")

        # 제어 버튼 프레임
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.start_btn = ctk.CTkButton(self.btn_frame, text="작업 시작", command=self.start_automation)
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(
            self.btn_frame, text="작업 중지",
            fg_color="red", hover_color="darkred",
            command=self.stop_automation, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)

        # 실시간 상태 로그창
        self.log_box = ctk.CTkTextbox(self, height=180, state="disabled")
        self.log_box.pack(pady=10, padx=20, fill="both")

    def log(self, message):
        """UI 로그창에 메시지 출력"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def stop_automation(self):
        self.is_running = False
        self.log(">> 중지 요청됨. 현재 진행 중인 작업까지 처리 후 종료합니다...")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def start_automation(self):
        v_id = self.id_entry.get().strip()
        v_passwd = self.pw_entry.get().strip()
        keyword = self.keyword_entry.get().strip()
        try:
            target_count = int(self.count_entry.get().strip())
        except ValueError:
            self.log(">> 오류: 목표 인원수는 숫자만 입력해주세요.")
            return
        msg = self.msg_textbox.get("0.0", "end").strip()

        if not all([v_id, v_passwd, keyword, target_count, msg]):
            self.log(">> 오류: 모든 항목을 입력해주세요.")
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log(f">> '{keyword}' 키워드로 자동화를 시작합니다...")

        threading.Thread(
            target=self.run_selenium,
            args=(v_id, v_passwd, keyword, target_count, msg),
            daemon=True
        ).start()

    # ────────────────────────────────────────────────────────────
    # 핵심 Selenium 자동화 로직 (콘솔 스크립트 그대로 이식)
    # ────────────────────────────────────────────────────────────
    def run_selenium(self, v_id, v_passwd, search_keyword, target_count, message_text):
        driver = None
        current_count = 0

        try:
            self.log(">> 크롬 드라이버를 로드합니다...")
            options = Options()
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--disable-blink-features=AutomationControlled")

            try:
                s = Service("C:/py_temp/chromedriver/chromedriver.exe")
                driver = webdriver.Chrome(service=s, options=options)
            except Exception as drv_err:
                self.log(f">> 드라이버 로드 실패: {drv_err}")
                return

            base_url = 'https://www.naver.com/'
            driver.get(base_url)
            time.sleep(random.uniform(2, 4))
            driver.maximize_window()

            wait = WebDriverWait(driver, 10)
            actions = ActionChains(driver)

            # -------------------------------------------------------------
            # 2. 우회 로그인 처리 (사람처럼 한 글자씩 입력)
            # -------------------------------------------------------------
            self.log(">> 다이렉트 접근 및 우회 로그인 시도...")
            driver.get(f"https://blog.naver.com/{v_id}?Redirect=Write")
            time.sleep(3)

            id_element = wait.until(EC.element_to_be_clickable((By.NAME, 'id')))
            id_element.click()
            for char in v_id:
                id_element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(0.5)

            pw_element = driver.find_element(By.NAME, 'pw')
            pw_element.click()
            for char in v_passwd:
                pw_element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.5))
            time.sleep(0.5)

            driver.find_element(By.ID, 'log.login').click()

            # -------------------------------------------------------------
            # 캡차 / 2단계 인증 대기
            # -------------------------------------------------------------
            self.log(">> 🚨 로그인 버튼 클릭 완료! 캡차/2단계 인증 발생 시 브라우저에서 직접 해결해주세요 (최대 5분 대기)")

            WebDriverWait(driver, 300).until(
                lambda d: "nid.naver.com" not in d.current_url
            )

            self.log(">> ✅ 로그인 인증 성공! 작업을 재개합니다.")
            time.sleep(3)

            if not self.is_running:
                return

            # -------------------------------------------------------------
            # 3. 네이버 검색 -> 블로그 탭 이동
            # -------------------------------------------------------------
            self.log(f">> 네이버에서 '{search_keyword}' 검색 시작...")
            driver.get("https://www.naver.com/")
            time.sleep(2)

            # 검색어 입력 (사람처럼 한 글자씩)
            search_input = wait.until(EC.element_to_be_clickable((By.ID, "query")))
            search_input.click()
            time.sleep(0.5)
            for char in search_keyword:
                search_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
            time.sleep(1)

            # 검색 버튼 클릭
            driver.find_element(By.CSS_SELECTOR, "button.btn_search").click()
            time.sleep(random.uniform(2, 4))

            self.log(">> 검색 완료! 블로그 탭으로 이동합니다...")

            # 블로그 탭 클릭
            blog_tab = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href, 'tab.blog') or (contains(@class, 'tab') and .//i[contains(@class, 'ico_nav_blog')])]")
            ))
            blog_tab.click()
            time.sleep(random.uniform(3, 5))

            # 현재 창을 메인 창으로 설정
            main_blog_window = driver.current_window_handle

            self.log(f">> 블로그 검색 결과 진입 완료! '{search_keyword}' 관련 블로그 탐색을 시작합니다.")

            # -------------------------------------------------------------
            # 4. 반복문: 무한스크롤 + 게시글 돌면서 서로이웃 신청
            # -------------------------------------------------------------
            processed_urls = set()
            processed_bloggers = set()
            no_new_post_count = 0
            max_no_new_attempts = 5
            scroll_round = 0

            while current_count < target_count and self.is_running:
                scroll_round += 1
                self.log(f"\n>> ===== [라운드 {scroll_round}] 현재 페이지 게시글 수집 중... =====")

                post_elements = driver.find_elements(By.CSS_SELECTOR,
                    "a[data-heatmap-target='.nblg'][href*='blog.naver.com']"
                )

                post_urls = []
                for elem in post_elements:
                    href = elem.get_attribute("href")
                    if not href or "blog.naver.com" not in href or "ader.naver.com" in href:
                        continue
                    if href in processed_urls:
                        continue

                    try:
                        path_parts = urlparse(href).path.strip('/').split('/')
                        blogger_id = path_parts[0] if path_parts else None
                    except:
                        blogger_id = None

                    if blogger_id and blogger_id in processed_bloggers:
                        continue

                    post_urls.append((href, blogger_id))

                self.log(f"   [i] 새로 발견한 블로거: {len(post_urls)}명 (총 처리 완료 블로거: {len(processed_bloggers)}명)")

                if not post_urls:
                    no_new_post_count += 1
                    self.log(f"   [i] 새로운 블로그 글이 없습니다. 스크롤합니다... ({no_new_post_count}/{max_no_new_attempts})")

                    if no_new_post_count >= max_no_new_attempts:
                        self.log(">> 더 이상 새로운 글을 찾을 수 없습니다. 종료합니다.")
                        break

                    viewport_height = driver.execute_script("return window.innerHeight")
                    current_scroll = driver.execute_script("return window.pageYOffset")
                    driver.execute_script(f"window.scrollTo(0, {current_scroll + viewport_height * 2});")
                    time.sleep(random.uniform(1.5, 2.5))
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(2, 4))
                    continue

                no_new_post_count = 0

                for idx, (url, blogger_id) in enumerate(post_urls, 1):
                    if current_count >= target_count or not self.is_running:
                        break

                    if url in processed_urls:
                        continue
                    if blogger_id and blogger_id in processed_bloggers:
                        continue

                    processed_urls.add(url)
                    if blogger_id:
                        processed_bloggers.add(blogger_id)

                    self.log(f"\n   --- [{idx}/{len(post_urls)}] 블로거 [{blogger_id}] 처리 중...")

                    # 메인 창 핸들을 루프마다 명확히 재확인
                    main_blog_window = driver.current_window_handle

                    driver.execute_script(f"window.open('{url}', '_blank');")
                    time.sleep(1)

                    try:
                        post_windows = [w for w in driver.window_handles if w != main_blog_window]
                        if not post_windows:
                            continue

                        post_window = post_windows[0]
                        driver.switch_to.window(post_window)
                        time.sleep(random.uniform(2, 4))

                        # 프레임 전환
                        driver.switch_to.frame("mainFrame")

                        try:
                            add_buddy_btn = driver.find_element(By.CSS_SELECTOR, "a.btn_buddy")
                        except:
                            self.log("   [-] 이웃추가 버튼이 없습니다. 패스합니다.")
                            continue

                        add_buddy_btn.click()
                        time.sleep(2)

                        # 팝업 창 추적
                        popup_windows = [w for w in driver.window_handles if w not in [main_blog_window, post_window]]
                        if not popup_windows:
                            self.log("   [-] 팝업 창이 뜨지 않았습니다. 패스합니다.")
                            continue

                        popup_window = popup_windows[0]
                        driver.switch_to.window(popup_window)

                        # 상황별 패스
                        if len(driver.find_elements(By.XPATH, "//*[contains(text(), '님과 현재 서로이웃입니다')]")) > 0:
                            self.log("   [-] 이미 서로이웃입니다. 패스합니다.")
                            continue

                        if len(driver.find_elements(By.XPATH, "//*[contains(text(), '서로이웃 신청을 받지 않는 이웃입니다')]")) > 0:
                            self.log("   [-] 서로이웃 신청을 받지 않는 블로거입니다. 패스합니다.")
                            continue

                        if len(driver.find_elements(By.XPATH, "//*[contains(text(), '이미 이웃으로 추가된 블로거입니다')]")) > 0:
                            self.log("   [-] 이미 이웃으로 추가된 블로거입니다. 패스합니다.")
                            continue

                        if len(driver.find_elements(By.XPATH, "//*[contains(text(), '이미 서로이웃 신청')]")) > 0:
                            self.log("   [-] 이미 서로이웃 신청한 블로거입니다. 패스합니다.")
                            continue

                        try:
                            both_buddy_label = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[@for='each_buddy_add']")))
                            both_buddy_label.click()
                        except:
                            continue

                        time.sleep(1)
                        driver.find_element(By.CSS_SELECTOR, "a._buddyAddNext").click()
                        time.sleep(1.5)

                        try:
                            textarea = driver.find_element(By.ID, "message")
                            textarea.clear()

                            for char in message_text:
                                textarea.send_keys(char)
                                time.sleep(random.uniform(0.01, 0.05))

                            time.sleep(1)
                            driver.find_element(By.CSS_SELECTOR, "a._addBothBuddy").click()
                            time.sleep(1.5)
                            driver.find_element(By.CSS_SELECTOR, "a.button_close").click()

                            current_count += 1
                            self.log(f"   [+] ✅ 서로이웃 신청 완료! (현재 진행: {current_count}/{target_count})")

                        except:
                            self.log("   [-] 메시지 창을 찾을 수 없거나 에러 발생. 패스합니다.")

                    except InvalidSessionIdException:
                        self.log("   [!] ⚠️ 브라우저 세션이 만료되었습니다. 프로그램을 종료합니다.")
                        raise

                    except Exception as e:
                        self.log(f"   [!] 포스팅 처리 중 에러 발생, 다음 글로 넘어갑니다. ({type(e).__name__})")

                    finally:
                        # 메인 창만 남기고 싹 다 닫는 불도저 로직
                        try:
                            for handle in driver.window_handles:
                                if handle != main_blog_window:
                                    try:
                                        driver.switch_to.window(handle)
                                        driver.close()
                                    except:
                                        pass
                            driver.switch_to.window(main_blog_window)
                        except (InvalidSessionIdException, WebDriverException):
                            self.log("   [!] ⚠️ 브라우저 세션이 만료되어 정리할 수 없습니다.")
                            break
                        time.sleep(random.uniform(1.5, 3))

                # 현재 수집된 글을 다 처리했으면 스크롤 다운하여 새 글 로딩
                if current_count < target_count and self.is_running:
                    self.log(f"\n>> 🔽 라운드 {scroll_round} 완료! 스크롤하여 새 게시글을 로딩합니다...")

                    last_height = driver.execute_script("return document.body.scrollHeight")

                    # 점진적으로 스크롤 (사람처럼 자연스럽게)
                    for scroll_step in range(3):
                        viewport_height = driver.execute_script("return window.innerHeight")
                        current_scroll = driver.execute_script("return window.pageYOffset")
                        driver.execute_script(f"window.scrollTo(0, {current_scroll + viewport_height});")
                        time.sleep(random.uniform(0.8, 1.5))

                    # 마지막에 맨 아래까지 스크롤
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(3, 5))

                    # 스크롤 후 높이 비교
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        time.sleep(2)
                        new_height = driver.execute_script("return document.body.scrollHeight")

                    if new_height == last_height:
                        no_new_post_count += 1
                        self.log(f"   [i] 새 컨텐츠 로딩 없음 ({no_new_post_count}/{max_no_new_attempts})")
                        if no_new_post_count >= max_no_new_attempts:
                            self.log(">> 더 이상 로딩되는 글이 없습니다. 종료합니다.")
                            break
                    else:
                        no_new_post_count = 0
                        self.log(f"   [i] ✅ 새 컨텐츠 로딩 완료! (페이지 높이: {last_height} → {new_height})")

            if self.is_running and current_count >= target_count:
                self.log(f"\n🎉 모든 신청이 완료되었습니다! (총 {current_count}명)")
            else:
                self.log(f"\n>> 서로이웃 신청을 {current_count}명 완료했습니다.")

        except Exception as e:
            self.log(f">> 치명적 에러 발생: {e}")
        finally:
            if driver:
                driver.quit()
            self.is_running = False
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            self.after(0, lambda: self.stop_btn.configure(state="disabled"))


if __name__ == "__main__":
    app = BlogAutoApp()
    app.mainloop()