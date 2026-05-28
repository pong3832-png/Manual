# products_db_category

사용자가 직접 고른 쿠팡 상품을 카테고리별로 보관하는 폴더입니다.

초기 권장 파일 구조:

```text
products_db_category/
  생활가전.csv
  주방용품.csv
  계절상품.csv
  육아용품.csv
  건강관리.csv
```

각 CSV는 최소한 아래 컬럼을 갖는 것을 권장한다.

```text
category,product_name,coupang_url,price_range,key_strength,weakness,recommended_for,comparison_point,seasonality,memo
```
