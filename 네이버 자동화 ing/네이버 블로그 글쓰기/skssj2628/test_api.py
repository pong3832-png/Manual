import sys
import os
import csv
import time

sys.path.insert(0, 'c:\\Users\\itwill\\자동화 공부\\네이버 자동화 ing\\네이버 블로그 글쓰기\\skssj2628')
import skssj2628

csv_path = 'skssj2628_db.csv'
rows, _, _ = skssj2628.load_csv_rows(csv_path)

used_products = skssj2628.migrate_used_rows_to_state(rows)
available_rows = [r for r in rows if not skssj2628.is_coupang_product_already_used(r, used_products)]

print(f"Total Available Rows: {len(available_rows)}")

success_count = 0
fail_count = 0

print("Testing Coupang API for available rows (testing up to 82 items)...")

for idx, row in enumerate(available_rows):
    original_url = skssj2628.get_product_field(row, "상품원본URL", "쿠팡링크")
    title = skssj2628.get_product_field(row, "상품명")
    
    if not original_url:
        continue
        
    try:
        shorten_url = skssj2628.generate_coupang_deeplink(original_url)
        if shorten_url and shorten_url != original_url:
            success_count += 1
            print(f"[{idx+1}] 성공: {title[:20]}... -> {shorten_url}")
        else:
            fail_count += 1
            # print(f"[{idx+1}] 실패: {title[:20]}...")
    except Exception as e:
        fail_count += 1
        # print(f"[{idx+1}] 오류 ({e}): {title[:20]}...")
        
    time.sleep(0.5) # rate limit protection

print("-" * 30)
print(f"Total Tested: {len(available_rows)}")
print(f"Success: {success_count}")
print(f"Failed: {fail_count}")
