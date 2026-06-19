from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random 
import re
from urllib.parse import urlparse

def human_typing(element, text):
    """사람처럼 한 글자씩 랜덤 딜레이로 입력"""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.15))
    time.sleep(random.uniform(0.3, 0.7))

print("=" * 80)
print(" 개인프로젝트 네이버 블로그 자동 서로이웃 추가 프로그램 (검색어 기반 + 무한스크롤)")
print("=" * 80)
print("\n")

# -------------------------------------------------------------
# 1. 사용자 입력 받기
# -------------------------------------------------------------
v_id = input('🔑 네이버 로그인 ID를 입력하세요: ')
v_passwd = input('🔑 네이버 로그인 비밀번호를 입력하세요: ')
search_keyword = input('🔍 검색할 키워드를 입력하세요: ')
target_count = int(input('🎯 몇 명에게 서로이웃을 신청할까요? (숫자만 입력): '))

message_text = "서로이웃해요~블로그 자주 방문하고 소통합시다!"
current_count = 0 

print(f"\n🚀 '{search_keyword}' 검색 후 서로이웃 추가 자동화를 시작합니다!")

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--disable-blink-features=AutomationControlled")

s = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=s, options=options) 

base_url = 'https://www.naver.com/'
driver.get(base_url)
time.sleep(random.uniform(2, 4))
driver.maximize_window()

wait = WebDriverWait(driver, 10)
actions = ActionChains(driver)

try:
    # -------------------------------------------------------------
    # 2. 우회 로그인 처리
    # -------------------------------------------------------------
    print(">> 다이렉트 접근 및 우회 로그인 시도...")
    driver.get(f"https://blog.naver.com/{v_id}?Redirect=Write")
    time.sleep(3)

    id_element = driver.find_element(By.NAME, 'id')
    id_element.click()
    time.sleep(0.3)
    human_typing(id_element, v_id)
    time.sleep(1)

    pw_element = driver.find_element(By.NAME, 'pw')
    pw_element.click()
    time.sleep(0.3)
    human_typing(pw_element, v_passwd)
    time.sleep(1)

    driver.find_element(By.ID, 'log.login').click()  
    
    # -------------------------------------------------------------
    # 💡 캡차(영수증) / 2단계 인증 대기
    # -------------------------------------------------------------
    print(">> 🚨 로그인 버튼 클릭 완료! 인증창(캡차/2단계) 발생 여부를 확인합니다...")
    print(">> 만약 캡차가 떴다면 브라우저에서 직접 마우스로 해제해주세요 (최대 5분 대기)")
    
    WebDriverWait(driver, 300).until(
        lambda d: "nid.naver.com" not in d.current_url
    )
    
    print(">> ✅ 로그인이 최종 승인되었습니다! 자동화 작업을 다시 재개합니다.")
    time.sleep(3)  
    
    # -------------------------------------------------------------
    # 3. 네이버 검색 -> 블로그 탭 이동
    # -------------------------------------------------------------
    print(f">> 네이버에서 '{search_keyword}' 검색 시작...")
    driver.get("https://www.naver.com/")
    time.sleep(2)
    
    # 검색어 입력
    search_input = wait.until(EC.presence_of_element_located((By.ID, "query")))
    search_input.click()
    time.sleep(0.5)
    human_typing(search_input, search_keyword)
    time.sleep(1)
    
    # 검색 버튼 클릭
    driver.find_element(By.CSS_SELECTOR, "button.btn_search").click()
    time.sleep(random.uniform(2, 4))
    
    print(">> 검색 완료! 블로그 탭으로 이동합니다...")
    
    # 블로그 탭 클릭
    blog_tab = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[contains(@href, 'tab.blog') or (contains(@class, 'tab') and .//i[contains(@class, 'ico_nav_blog')])]")
    ))
    blog_tab.click()
    time.sleep(random.uniform(3, 5))
    
    # 현재 창을 메인 창으로 설정
    main_blog_window = driver.current_window_handle
    
    print(f">> 블로그 검색 결과 진입 완료! '{search_keyword}' 관련 블로그 탐색을 시작합니다.")

    # -------------------------------------------------------------
    # 4. 반복문: 무한스크롤 + 게시글 돌면서 서로이웃 신청
    # -------------------------------------------------------------
    processed_urls = set()      # 이미 처리한 URL 중복 방지
    processed_bloggers = set()  # 이미 처리한 블로거 ID 중복 방지 (핵심!)
    no_new_post_count = 0       # 새 글이 없는 스크롤 횟수 카운터
    max_no_new_attempts = 5     # 연속으로 새 글이 없으면 종료
    scroll_round = 0            # 스크롤 라운드 카운터
    
    while current_count < target_count:
        scroll_round += 1
        print(f"\n>> ===== [라운드 {scroll_round}] 현재 페이지 게시글 수집 중... =====")
        
        # ----------------------------------------------------------
        # 현재 페이지에 있는 블로그 글 제목 링크 수집 (광고 제외)
        # 💡 핵심 패턴: data-heatmap-target=".nblg" → 실제 블로그 글
        # 💡 href에 "blog.naver.com" 포함 → 진짜 블로그 포스트
        # 💡 data-heatmap-target=".tit" / ader.naver.com → 광고 → 제외
        # ----------------------------------------------------------
        # ✅ 안정적 선택자: 클래스명은 변할 수 있으므로 속성 기반으로 수집
        post_elements = driver.find_elements(By.CSS_SELECTOR, 
            "a[data-heatmap-target='.nblg'][href*='blog.naver.com']"
        )
        
        # blog.naver.com URL만 필터링 (광고 ader.naver.com 제외)
        # ✅ 핵심: 같은 블로거의 여러 게시글이 있어도 블로거당 1개만 수집!
        post_urls = []
        for elem in post_elements:
            href = elem.get_attribute("href")
            if not href or "blog.naver.com" not in href or "ader.naver.com" in href:
                continue
            if href in processed_urls:
                continue
            
            # URL에서 블로거 ID 추출: https://blog.naver.com/블로거ID/글번호
            try:
                path_parts = urlparse(href).path.strip('/').split('/')
                blogger_id = path_parts[0] if path_parts else None
            except:
                blogger_id = None
            
            # 이미 처리한 블로거는 건너뛰기 (같은 사람 글 여러 개 나와도 1번만)
            if blogger_id and blogger_id in processed_bloggers:
                continue
            
            post_urls.append((href, blogger_id))
        
        print(f"   [i] 새로 발견한 블로거: {len(post_urls)}명 (총 처리 완료 블로거: {len(processed_bloggers)}명)")
        
        if not post_urls:
            no_new_post_count += 1
            print(f"   [i] 새로운 블로그 글이 없습니다. 스크롤합니다... ({no_new_post_count}/{max_no_new_attempts})")
            
            if no_new_post_count >= max_no_new_attempts:
                print(">> 더 이상 새로운 글을 찾을 수 없습니다. 프로그램을 종료합니다.")
                break
            
            # 점진적 스크롤 다운 (한 번에 뷰포트 높이만큼 → 더 자연스러움)
            viewport_height = driver.execute_script("return window.innerHeight")
            current_scroll = driver.execute_script("return window.pageYOffset")
            driver.execute_script(f"window.scrollTo(0, {current_scroll + viewport_height * 2});")
            time.sleep(random.uniform(1.5, 2.5))
            # 맨 아래까지 한번 더 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(2, 4))
            continue
        
        # 새 글을 찾았으면 카운터 리셋
        no_new_post_count = 0
        
        for idx, (url, blogger_id) in enumerate(post_urls, 1):
            if current_count >= target_count:
                break
            
            # 이미 처리한 URL/블로거는 건너뛰기
            if url in processed_urls:
                continue
            if blogger_id and blogger_id in processed_bloggers:
                continue
            
            processed_urls.add(url)
            if blogger_id:
                processed_bloggers.add(blogger_id)
            
            print(f"\n   --- [{idx}/{len(post_urls)}] 블로거 [{blogger_id}] 처리 중: {url[:70]}...")
            
            # 메인 창 핸들을 루프마다 명확히 재확인
            main_blog_window = driver.current_window_handle
            
            driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(1)
            
            try:
                # 인덱스가 아닌 창의 고유 ID(Handle)로 절대 추적
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
                    print("   [-] 이웃추가 버튼이 없습니다. 패스합니다.")
                    continue

                add_buddy_btn.click()
                time.sleep(2)
                
                # 팝업 창 추적
                popup_windows = [w for w in driver.window_handles if w not in [main_blog_window, post_window]]
                if not popup_windows:
                    print("   [-] 팝업 창이 뜨지 않았습니다. 패스합니다.")
                    continue
                    
                popup_window = popup_windows[0]
                driver.switch_to.window(popup_window)
                
                # 상황별 패스
                if len(driver.find_elements(By.XPATH, "//*[contains(text(), '님과 현재 서로이웃입니다')]")) > 0:
                    print("   [-] 이미 서로이웃입니다. 패스합니다.")
                    continue
                
                if len(driver.find_elements(By.XPATH, "//*[contains(text(), '서로이웃 신청을 받지 않는 이웃입니다')]")) > 0:
                    print("   [-] 서로이웃 신청을 받지 않는 블로거입니다. 패스합니다.")
                    continue

                # 이미 이웃 신청 중인 경우
                if len(driver.find_elements(By.XPATH, "//*[contains(text(), '이미 이웃으로 추가된 블로거입니다')]")) > 0:
                    print("   [-] 이미 이웃으로 추가된 블로거입니다. 패스합니다.")
                    continue
                
                if len(driver.find_elements(By.XPATH, "//*[contains(text(), '이미 서로이웃 신청')]")) > 0:
                    print("   [-] 이미 서로이웃 신청한 블로거입니다. 패스합니다.")
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
                    print(f"   [+] ✅ 서로이웃 신청 완료! (현재 진행: {current_count}/{target_count})")
                    
                except:
                    print("   [-] 메시지 창을 찾을 수 없거나 에러 발생. 패스합니다.")
                
            except InvalidSessionIdException:
                print("   [!] ⚠️ 브라우저 세션이 만료되었습니다. 프로그램을 종료합니다.")
                raise  # 치명적 에러이므로 바깥 try-except로 전파
                
            except Exception as e:
                print(f"   [!] 포스팅 처리 중 에러 발생, 다음 글로 넘어갑니다. ({type(e).__name__})")
                
            finally:
                # 어떤 창이 꼬이더라도 무조건 '메인 창'만 남기고 싹 다 닫는 불도저 로직
                try:
                    for handle in driver.window_handles:
                        if handle != main_blog_window:
                            try:
                                driver.switch_to.window(handle)
                                driver.close()
                            except:
                                pass
                    # 안전하게 다시 메인 창으로 복귀
                    driver.switch_to.window(main_blog_window)
                except (InvalidSessionIdException, WebDriverException):
                    print("   [!] ⚠️ 브라우저 세션이 만료되어 정리할 수 없습니다.")
                    break
                time.sleep(random.uniform(1.5, 3))
        
        # 현재 수집된 글을 다 처리했으면 스크롤 다운하여 새 글 로딩
        if current_count < target_count:
            print(f"\n>> 🔽 라운드 {scroll_round} 완료! 스크롤하여 새 게시글을 로딩합니다...")
            
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
            
            # 스크롤 후 높이 비교 (더 이상 로딩 안 되면 종료)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # 한번 더 시도 (로딩 지연 대비)
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                
            if new_height == last_height:
                no_new_post_count += 1
                print(f"   [i] 새 컨텐츠 로딩 없음 ({no_new_post_count}/{max_no_new_attempts})")
                if no_new_post_count >= max_no_new_attempts:
                    print(">> 더 이상 로딩되는 글이 없습니다. 프로그램을 종료합니다.")
                    break
            else:
                no_new_post_count = 0
                print(f"   [i] ✅ 새 컨텐츠 로딩 완료! (페이지 높이: {last_height} → {new_height})")

    print(f"\n🎉 서로이웃 신청을 {current_count}명 완료했습니다! 프로그램을 종료합니다.")
    time.sleep(5)

except Exception as e:
    print("\n[치명적 에러 발생] 프로그램 실행 도중 문제가 발생했습니다:", e)

finally:
    driver.quit()
