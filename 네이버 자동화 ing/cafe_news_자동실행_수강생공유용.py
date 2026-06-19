import pandas as pd
import time
import subprocess
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import math
import urllib.request
import urllib
import requests
import pyautogui

#2.Telegram Bot API 설정
bot_token = '이곳에 텔레그램 토큰 쓰세요'
base_url = f'https://api.telegram.org/bot{bot_token}'
chatid_s1 = '이곳에 채팅 ID 쓰세요'

#####################################################################################################
#1. 텔레그램 메시지 보내는 함수
def send_message(chat_id, text):
    send_message_url = f'{base_url}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': text
    }
    response = requests.post(send_message_url, data=data)
    return response.json()
####################################################################################################

# 암호화폐 뉴스 수집하기
def get_bitcoin_news():
    # ------------------------------
    # 1. 크롬 드라이버 설정 및 시작
    # ------------------------------
    s = Service("c:/py_temp/chromedriver.exe")  # chromedriver.exe 경로 설정
    driver = webdriver.Chrome(service=s)

    # URL 접근
    base_url = 'https://www.coinreaders.com/sub.html?section=sc21'
    driver.get(base_url)
    time.sleep(2)
    driver.maximize_window()

    # 기사 수와 필요한 페이지 수 설정
    cnt = 20  # 수집할 기사 건수
    page_cnt = math.ceil(cnt / 10)  # 페이지 당 기사 10개로 가정

    # 스크롤을 내려주는 보조 함수
    def scroll_down(driver_instance):
        driver_instance.execute_script("window.scrollBy(0,1100);")
        time.sleep(2)

    # 결과를 담을 리스트
    title_list = []
    content_list = []
    url_list = []

    # 기사 번호 카운터
    no = 1

    # ------------------------------
    # 2. 페이지 순회하며 기사 데이터 수집
    # ------------------------------
    for page in range(1, page_cnt + 1):
        # 페이지 내에서 여러 번 스크롤
        for _ in range(2):  # 2번 스크롤
            scroll_down(driver)

        # 현재 페이지의 HTML 파싱
        html_2 = driver.page_source
        soup_2 = BeautifulSoup(html_2, 'html.parser')

        # 기사 목록 추출(필요에 따라 클래스/태그 구조가 바뀔 수 있으니 확인 필요)
        # Breaking news 카테고리 수집
        content_2 = soup_2.select('div.sub_read_list_box')

        for b in content_2:
            # 기사 제목이 있는 div만 처리
            try:
                title = b.find('dt').get_text().strip()
            except:
                # 제목이 없는 경우 패스
                continue
            else:
                # 1) 기사 제목
                title_list.append(title)

                # 2) 요약 내용(없을 수도 있으므로 예외처리 추가 가능)
                content = b.find('dd','sbody').get_text()
                content_list.append(content)

                # 3) 기사 원문 URL
                sub_url = b.find('a')['href']
                full_url = 'https://www.coinreaders.com' + sub_url
                url_list.append(full_url)

                # 현재 기사 번호 출력(로그용)
                print(f'{no} 번째 기사를 수집합니다================')
                print('1.기사제목:', title)
                print('2.요약내용:', content)
                print('3.URL:', full_url)
                print()

            # 수집 기사 수가 목표(cnt)를 초과하면 중단
            if no >= cnt:
                break

            no += 1
            time.sleep(1)

        # 목표 개수 초과 시, 바깥 for 루프도 중단
        if no >= cnt:
            break

        # 다음 페이지 버튼 클릭
        next_page = page + 1
        try:
            # 다음 페이지 번호가 있으면 그 번호로 이동
            driver.find_element(By.LINK_TEXT, str(next_page)).click()
        except:
            # 만약 다음 페이지 번호가 없으면 '다음' 버튼 클릭
            try:
                driver.find_element(By.LINK_TEXT, '다음').click()
            except:
                # 둘 다 안 되면(마지막 페이지 등) 종료
                break

    # 모든 작업 완료 후 드라이버 종료
    driver.close()

    # ------------------------------
    # 3. 수집한 기사 데이터 반환
    # ------------------------------
    # 필요에 따라 리스트/데이터프레임 등 원하는 형태로 반환
    # 여기서는 (제목, 요약내용, URL)을 묶어서 하나의 리스트로 반환
    news_list = list(zip(title_list, url_list, content_list))
    return news_list


########################################################################################
# 수집된 뉴스를 네이버 카페의 특정 게시판에 업로드 하기
def login_naver_cafe(driver, username, password):
    driver.get('https://nid.naver.com/nidlogin.login')
    time.sleep(2)
    driver.maximize_window()
    driver.find_element(By.XPATH, '//*[@id="loinid"]/span/span').click()
    time.sleep(2)

    # 로그인 폼에 아이디와 비밀번호 입력
    driver.execute_script("document.getElementsByName('id')[0].value=\'"+username+"\'")
    driver.execute_script("document.getElementsByName('pw')[0].value=\'"+password+"\'")
    driver.find_element(By.XPATH,'//*[@id="log.login"]').click()
    time.sleep(2)

def post_to_gachilabscafe(driver, cafe_url, title, url, content):
    driver.get(cafe_url)
    time.sleep(3)

    # 게시판 선택하기 - 가치랩스
    driver.find_element(By.XPATH,'//*[@id="menuLink41"]').click()
    time.sleep(2)
   
    # 글쓰기 버튼 클릭 (XPath는 상황에 맞게 수정)
    driver.switch_to.frame('cafe_main')
    driver.find_element('xpath', '//*[@id="writeFormBtn"]').click()
    time.sleep(3)

    # 현재 열려 있는 모든 창의 핸들 수집
    window_handles = driver.window_handles
    
    # 첫 번째 핸들은 기존 창, 두 번째 핸들은 새로 열린 창이므로 두 번째 창으로 전환
    driver.switch_to.window(window_handles[-1])
    time.sleep(5)
    
    # 제목과 내용 작성
    title_area = driver.find_element('xpath', '//*[@id="app"]/div/div/section/div/div[2]/div[1]/div[1]/div/div[2]/div/textarea')
    title_area.send_keys(title)
    time.sleep(2)
    urlbtn = pyautogui.locateOnScreen('c:\\py_temp\\images\\urlbtn.png')
    center = pyautogui.center(urlbtn)
    pyautogui.click( center )
    time.sleep(3)
    urlbtn2 = pyautogui.locateOnScreen('c:\\py_temp\\images\\urlbtn2.png')
    center2 = pyautogui.center(urlbtn2)
    pyautogui.click( center2 )
    pyautogui.write(url,interval=0.1)
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(1)
    pyautogui.press('enter')
    time.sleep(2)

    # 본문 내용 작성
    # content_area = driver.find_element('xpath','//*[@id="SE-0124bca8-d70a-4796-8894-bb313df96f46"]')
    # content_area.send_keys(content)
    import pyperclip
    pyperclip.copy(content)
    pyautogui.hotkey('ctrl', 'v')
    
    time.sleep(2)

    # 등록 버튼 클릭
    driver.find_element('xpath', '//*[@id="app"]/div/div/section/div/div[1]/div/a').click()
    time.sleep(3)


# 자동 실행되도록 시간 설정하기
import schedule

def job():
    news = get_bitcoin_news()
    driver = webdriver.Chrome()

    login_naver_cafe(driver, "이곳에 네이버 ID", "이곳에 네이버 비밀번호")
    
    for title, link , content in news:
        post_to_gachilabscafe(driver, "https://cafe.naver.com/gachilabs", title, link , content)

    driver.quit()

schedule.every().day.at("03:55").do(job)
#schedule.every().day.at("07:55").do(job)
schedule.every().day.at("11:55").do(job)
#schedule.every().day.at("15:55").do(job)
schedule.every().day.at("19:55").do(job)
#schedule.every().day.at("23:55").do(job)

while True:
    try :
        schedule.run_pending()
        time.sleep(60) 
    except :
        # 텔레그램으로 메시지보내기
        message_text = '네이버 카페 뉴스 등록 작업에 오류가 발생했습니다~ 2분 뒤 재 시작합니다!!'
        response = send_message(chatid_s1, message_text)
        
        time.sleep(120)
        subprocess.run(['python','c:\\py_temp\\cafe_news_2.py'])
            