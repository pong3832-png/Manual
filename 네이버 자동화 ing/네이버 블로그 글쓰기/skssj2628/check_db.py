import json, csv

# Load skssj2628_db.csv
csv_path = 'skssj2628_db.csv'
rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))

# Load used products
used_path = '자동발행상태기록파일\\coupang_used_products.json'
try:
    with open(used_path, 'r', encoding='utf-8') as f:
        used_products = json.load(f)
except Exception:
    used_products = []

# Count
total = len(rows)
avail = 0

for row in rows:
    # Logic from is_coupang_product_already_used
    title = str(row.get("상품명", "")).strip()
    original_url = str(row.get("상품원본URL") or row.get("쿠팡링크") or "").strip()
    if not title:
        continue
    
    is_used = False
    for used_item in used_products:
        if isinstance(used_item, dict):
            u_title = str(used_item.get("title", "")).strip()
            u_url = str(used_item.get("original_url") or used_item.get("url") or "").strip()
        else:
            # It might be just a string
            u_title = str(used_item).strip()
            u_url = ""

        if u_title == title:
            is_used = True
            break
        if original_url and u_url and original_url == u_url:
            is_used = True
            break

    if not is_used:
        avail += 1

print(f"Total Rows in DB: {total}")
print(f"Total Available (Unused): {avail}")
