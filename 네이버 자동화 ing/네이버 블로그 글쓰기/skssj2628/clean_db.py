import sys
import os
import csv
import time

sys.path.insert(0, 'c:\\Users\\itwill\\자동화 공부\\네이버 자동화 ing\\네이버 블로그 글쓰기\\skssj2628')
import skssj2628

csv_path = 'c:\\Users\\itwill\\자동화 공부\\네이버 자동화 ing\\네이버 블로그 글쓰기\\skssj2628\\skssj2628_db.csv'
rows, fields, encoding = skssj2628.load_csv_rows(csv_path)

used_products = skssj2628.migrate_used_rows_to_state(rows)
available_rows = [r for r in rows if not skssj2628.is_coupang_product_already_used(r, used_products)]

print(f"Total Available Rows before cleanup: {len(available_rows)}")

successful_rows = []

for idx, row in enumerate(available_rows):
    original_url = skssj2628.get_product_field(row, "상품원본URL", "쿠팡링크")
    
    if not original_url:
        continue
        
    try:
        shorten_url = skssj2628.generate_coupang_deeplink(original_url)
        if shorten_url and shorten_url != original_url:
            successful_rows.append(row)
    except Exception as e:
        pass
        
    time.sleep(0.5)

print(f"Cleanup complete. Total successful rows kept: {len(successful_rows)}")

# Write back to CSV
with open(csv_path, 'w', newline='', encoding=encoding) as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for row in successful_rows:
        writer.writerow(row)
print("CSV overwritten with successful items only.")
