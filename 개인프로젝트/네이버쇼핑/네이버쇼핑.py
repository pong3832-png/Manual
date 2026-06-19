try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import time
import os
import random 
try:
    import pymysql
except ModuleNotFoundError:
    pymysql = None

from naver_product_parser import (
    REVIEW_ITEM_SELECTOR,
    REVIEW_LINK_SELECTOR,
    REVIEW_MORE_BUTTON_SELECTOR,
    parse_product_summary,
    parse_reviews,
)
from naver_product_output import save_detail_review_outputs


DEFAULT_PRODUCT_DETAIL_URL = "https://brand.naver.com/realbarrier/products/13432378854#SELLER"
PRODUCT_DETAIL_READY_SELECTOR = "h3.y67cdgB6Ve, div.cy0UBkueTk h3"
DEFAULT_REVIEW_LIMIT = 100
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "결과 추출")


def _build_chrome_options():
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options


def _print_product_summary(summary):
    _safe_print("[detail] product_name:", summary.product_name)
    _safe_print("[detail] rating:", summary.rating)
    _safe_print("[detail] recent_six_month_rating:", summary.recent_six_month_rating)
    _safe_print("[detail] price_krw:", summary.price_krw)
    _safe_print("[detail] review_count:", summary.review_count)


def _safe_print(*values):
    text = " ".join(str(value) for value in values)
    encoding = sys.stdout.encoding or "utf-8"
    safe_text = text.replace("\u200b", "")
    print(safe_text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def _safe_click(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)


def _expand_visible_review_contents(driver):
    expanded_count = 0
    buttons = driver.find_elements(By.CSS_SELECTOR, REVIEW_MORE_BUTTON_SELECTOR)
    for button in buttons:
        try:
            button_text = button.text.strip()
            if "더보기" not in button_text:
                continue
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(random.uniform(0.1, 0.25))
            _safe_click(driver, button)
            expanded_count += 1
            time.sleep(random.uniform(0.15, 0.35))
        except Exception:
            continue
    return expanded_count


def _scroll_review_page(driver):
    review_items = driver.find_elements(By.CSS_SELECTOR, REVIEW_ITEM_SELECTOR)
    if review_items:
        driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", review_items[-1])
        time.sleep(random.uniform(0.25, 0.45))

    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(1.0, 1.8))


def collect_reviews_from_review_page(driver, review_limit=DEFAULT_REVIEW_LIMIT, max_idle_scrolls=5):
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, REVIEW_ITEM_SELECTOR)))

    reviews_by_id = {}
    idle_scrolls = 0
    previous_count = 0

    while True:
        for review in parse_reviews(driver.page_source):
            reviews_by_id.setdefault(review.review_id, review)

        current_count = len(reviews_by_id)
        print(f"[reviews] loaded={current_count}")

        if review_limit is not None and current_count >= review_limit:
            break

        if current_count == previous_count:
            idle_scrolls += 1
        else:
            idle_scrolls = 0

        if idle_scrolls >= max_idle_scrolls:
            break

        previous_count = current_count
        _scroll_review_page(driver)

    expanded_count = _expand_visible_review_contents(driver)
    print(f"[reviews] expanded={expanded_count}")

    for review in parse_reviews(driver.page_source):
        reviews_by_id[review.review_id] = review

    reviews = list(reviews_by_id.values())
    if review_limit is not None:
        return reviews[:review_limit]
    return reviews


def _print_review_preview(reviews, preview_count=3):
    _safe_print("[reviews] total_collected:", len(reviews))
    for review in reviews[:preview_count]:
        preview = review.content[:120]
        _safe_print(f"[reviews] {review.review_id} rating={review.rating} content={preview}")


def _print_output_paths(paths):
    _safe_print("[save] output_dir:", paths["output_dir"])
    _safe_print("[save] txt:", paths["txt"])
    _safe_print("[save] csv:", paths["csv"])
    _safe_print("[save] xlsx:", paths["xlsx"])


def run_product_detail_mode(
    product_url=DEFAULT_PRODUCT_DETAIL_URL,
    keep_open=False,
    review_limit=DEFAULT_REVIEW_LIMIT,
):
    driver = webdriver.Chrome(options=_build_chrome_options())
    driver.maximize_window()

    try:
        driver.get(product_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, PRODUCT_DETAIL_READY_SELECTOR)))

        summary = parse_product_summary(driver.page_source)
        _print_product_summary(summary)

        review_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, REVIEW_LINK_SELECTOR)))
        _safe_click(driver, review_link)
        print("[detail] clicked review link.")
        reviews = collect_reviews_from_review_page(driver, review_limit=review_limit)
        _print_review_preview(reviews)
        output_paths = save_detail_review_outputs(summary, reviews, DEFAULT_OUTPUT_DIR)
        _print_output_paths(output_paths)

        if keep_open:
            input("[detail] Press Enter to close browser...")

        return summary, reviews, output_paths
    finally:
        driver.quit()


def _product_url_from_args(args):
    if "--product-url" not in args:
        return DEFAULT_PRODUCT_DETAIL_URL
    index = args.index("--product-url")
    try:
        return args[index + 1]
    except IndexError as exc:
        raise SystemExit("--product-url requires a URL value") from exc


def _review_limit_from_args(args):
    if "--review-limit" not in args:
        return DEFAULT_REVIEW_LIMIT

    index = args.index("--review-limit")
    try:
        value = args[index + 1].strip().lower()
    except IndexError as exc:
        raise SystemExit("--review-limit requires a number or 'all'") from exc

    if value == "all":
        return None

    try:
        review_limit = int(value)
    except ValueError as exc:
        raise SystemExit("--review-limit requires a number or 'all'") from exc

    if review_limit <= 0:
        raise SystemExit("--review-limit must be greater than 0")
    return review_limit


def _run_product_detail_cli(args):
    if "--detail" not in args and "--product-url" not in args:
        return False
    run_product_detail_mode(
        product_url=_product_url_from_args(args),
        keep_open="--keep-open" in args,
        review_limit=_review_limit_from_args(args),
    )
    return True


if _run_product_detail_cli(sys.argv[1:]):
    raise SystemExit(0)

print("=" *80)
print(" 개인프로젝트 네이버 쇼핑 수집 (최종 완벽본)")
print("=" *80)
print("\n")

# -------------------------------------------------------------
# 1. 자동 로그인을 위한 네이버 ID/PW 및 파라미터 입력
# -------------------------------------------------------------
v_id = input('🔑 네이버 로그인 ID를 입력하세요: ')
v_passwd = input('🔑 네이버 로그인 비밀번호를 입력하세요: ')

query_txt = input('1. 검색할 네이버 쇼핑 키워드는 무엇입니까?: ').replace('"','')
cnt = int(input('2. 수집할 상품은 총 몇 건입니까?(예: 30): '))
# page_cnt는 네이버 쇼핑에서 쓰이지 않아 삭제했습니다.

f_dir = input("3. 파일을 저장할 폴더명만 쓰세요 [엔터시 네이버쇼핑\\결과 추출 적용]:")
if f_dir=='' :
    f_dir=DEFAULT_OUTPUT_DIR

print("\n🚀 데이터 수집을 시작합니다. 브라우저가 열리면 잠시 지켜봐주세요!")

# 실행시간 측정 시작
s_time = time.time()

# 폴더 설정 로직
n = time.localtime()
s = '%04d-%02d-%02d-%02d-%02d-%02d' % (n.tm_year, n.tm_mon, n.tm_mday, n.tm_hour, n.tm_min, n.tm_sec)
output_dir = os.path.join(f_dir, s+'-'+query_txt)
os.makedirs(output_dir, exist_ok=True)
os.chdir(output_dir)
ff_name = os.path.join(output_dir, s+'-'+query_txt+'.txt')
fc_name = os.path.join(output_dir, s+'-'+query_txt+'.csv')
fx_name = os.path.join(output_dir, s+'-'+query_txt+'.xls')

# -------------------------------------------------------------
# 2. 크롬 드라이버 셋팅
# -------------------------------------------------------------
options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options) 
driver.maximize_window()

try:
    # -------------------------------------------------------------
    # 3. 네이버 자동 로그인 (자바스크립트 주입 기법이 가장 안전합니다!)
    # -------------------------------------------------------------
    driver.get("https://nid.naver.com/nidlogin.login")
    time.sleep(2)

    driver.execute_script(f"document.getElementsByName('id')[0].value='{v_id}'")
    driver.execute_script(f"document.getElementsByName('pw')[0].value='{v_passwd}'")
    time.sleep(1)
    
    driver.find_element(By.XPATH,'//*[@id="log.login"]').click()  
    print(">> 성공적으로 네이버 로그인 시도 중...")
    time.sleep(3) 

    # -------------------------------------------------------------
    # 4. 로그인 완료 후 네이버 쇼핑으로 이동!
    # -------------------------------------------------------------
    driver.get("https://shopping.naver.com/ns/home")
    time.sleep(3) 
    
    wait = WebDriverWait(driver, 10)
    search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="상품명 또는 브랜드 입력"]')))
    
    search_input.click()
    search_input.clear()
    
    # 여기서는 검색어이므로 봇 탐지를 피하기 위해 사람처럼 한 글자씩 칩니다!
    for a in query_txt:
        search_input.send_keys(a)
        time.sleep(random.uniform(0.1, 0.35))
        
    time.sleep(2) 
    search_input.send_keys(Keys.ENTER) 
    
    print(f">> 네이버 쇼핑 '{query_txt}' 단어 타자 입력 & 검색 완료! 결과창 렌더링 대기...")
    time.sleep(3) 

except Exception as e:
    print("\n[접속 에러 발생] 진행 도중 문제가 생겼습니다:", e)


# ==========================================================
# 5. 크롤링 영역 (find 함수 사용 버전 기준)
# ==========================================================
product_names = []   
prices = []          
discounts = []       
stars = []           
review_cnts = []     
total_count = 0  

print('\n상품 정보를 수집합니다. 잠시만 기다려 주세요~~~~~~~~')
time.sleep(3) 

seen_products = set()

while total_count < cnt:
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # 바둑판형(Grid) 상품들을 감싸고 있는 전체 li를 찾습니다.
    # 선생님이 주신 HTML에서 'composite_card_container' 클래스는 고정되어 변하지 않는 이름표입니다.
    items = soup.find_all('li', class_='composite_card_container')
    
    if len(items) == 0:
        print("🚨 화면에서 상품을 찾지 못했습니다. 클래스명이 맞는지 다시 확인해주세요!")
    
    start_count = total_count 
        
    for item in items:
        if total_count >= cnt:
            break
            
        # 1. 제품 이름
        try:
            name_node = item.find('strong', class_='productCardTitle_product_card_title__eQupA')
            if name_node:
                name = name_node.get_text(strip=True)
            else:
                name = "이름 없음"
        except:
            name = "이름 없음"

        # 중복 체크 (수집했던 상품이면 패스)
        if name in seen_products or name == "이름 없음":
            continue
            
        seen_products.add(name)
        total_count += 1
        
        print(f"🚀 총 {cnt}건 중 {total_count}번째 상품 수집 중 =========")
        f = open(ff_name, 'a', encoding='UTF-8')
        f.write("\n")
        f.write(f"[{total_count} 번째 상품 정보]====\n")
        f.write("1.제품의 이름: " + name + "\n")
        product_names.append(name)
        
        # 2. 가격
        try:
            price_node = item.find('span', class_='priceTag_price__hGtfm')
            if price_node:
                price = price_node.get_text(strip=True)
            else:
                price = "0"
        except:
            price = "0"
            
        # 선생님 요청대로 뒤에 "원"을 붙여서 기록합니다.
        f.write("2.제품 판매가: " + price + "원\n")
        prices.append(price)

        # 3. 할인율
        try:
            dc_node = item.find('span', class_='priceTag_discount_ratio__VE866')
            if dc_node:
                # "31% 할인" -> "31" 로 숫자만 깔끔하게 남깁니다.
                discount = dc_node.get_text(strip=True).replace("할인", "").replace("%", "")
            else:
                discount = "0"
        except:
            discount = "0"
            
        f.write("3.할인율: " + discount + "%\n")
        discounts.append(discount)

        # 4. 리뷰 별점
        try:
            star_node = item.find('span', class_='productCardReview_star__7iHNO')
            if star_node:
                # "별점4.74" -> "4.74" 로 변경
                star = star_node.get_text(strip=True).replace("별점", "")
            else:
                star = "0"
        except:
            star = "0"
            
        f.write("4.리뷰 별점: " + star + "\n")
        stars.append(star)

        # 5. 리뷰 개수
        try:
            # "productCardReview_text__A9N9N" 클래스를 가진 span이 별점에도 있어서 여러 개일 수 있습니다.
            # 전부 찾아서 반복문으로 "리뷰" 글자가 포함된 태그만 쏙 빼옵니다!
            review_nodes = item.find_all('span', class_='productCardReview_text__A9N9N')
            review_cnt = "0"
            for r_node in review_nodes:
                r_text = r_node.get_text(strip=True)
                if "리뷰" in r_text:
                    # "리뷰 10,611" -> "10,611"
                    review_cnt = r_text.replace("리뷰", "").strip()
                    break
        except:
            review_cnt = "0"
            
        f.write("5.리뷰 개수: " + review_cnt + "\n")
        review_cnts.append(review_cnt)

        f.close()
        time.sleep(0.1)

    if total_count >= cnt:
        print(f"\n✅ 수집 목표량({cnt}건) 달성 완료!")
        break
    else:
        # 새로 추가할 상품 로딩을 위한 사람다운 페이지 다운 스크롤
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
        time.sleep(1)
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.PAGE_DOWN)
        time.sleep(2)


# ==========================================================
# 6. Step 7. xls 형태와 csv 형태로 저장하기
# ==========================================================
import pandas as pd
news_reple = pd.DataFrame()
news_reple['제품의 이름'] = pd.Series(product_names)
news_reple['제품 판매가'] = pd.Series(prices)
news_reple['할인율'] = pd.Series(discounts)
news_reple['리뷰 별점'] = pd.Series(stars)
news_reple['리뷰 개수'] = pd.Series(review_cnts)

news_reple.to_csv(fc_name, encoding="utf-8-sig", index=False)
news_reple.to_excel(fx_name, index=False, engine='openpyxl')


# ==========================================================
# 7. Step 8. 수집한 5가지 정보를 통째로 MySQL DB에 넣기!
# ==========================================================
try:
    conn = pymysql.connect(
        host='localhost',         
        user='root',              
        password='Jx03151616~~',  
        db='youtube_db',  
        charset='utf8mb4',        
        cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as cursor:
        # DB 구조도 선생님이 원하신 5개 속성에 딱 맞게 생성합니다!
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
        # 수집한 상품 개수만큼 반복하며 DB에 한 줄씩 기록!
        for i in range(len(product_names)):
            cursor.execute(insert_sql, (
                product_names[i], 
                prices[i], 
                discounts[i],
                stars[i],
                review_cnts[i]
            ))
        conn.commit()
        print(f"🎉 짝짝짝! 네이버 쇼핑 DB 저장까지 완벽하게 완료되었습니다!")
        
except Exception as e:
    print(f"\n[DB 에러] DB 저장 중 에러가 발생했습니다: {e}")
finally:
    try:
        conn.close()
    except:
        pass


# ==========================================================
# 8. Step 9. 요약 정보 출력하기
# ==========================================================
e_time = time.time( )
t_time = e_time - s_time

print("\n")
print("=" *120)
print(f"1.모든 작업 종료. 수집된 전체 상품 수는 {total_count} 건 입니다.")
print("2.총 소요시간은 %s 초 입니다 " %round(t_time,1))
print("3.파일 저장 완료: txt 파일명 : %s " %ff_name)
print("4.파일 저장 완료: csv 파일명 : %s " %fc_name)
print("5.파일 저장 완료: xls 파일명 : %s " %fx_name)
print("=" *120)

driver.quit() # 안전하게 창 닫기
