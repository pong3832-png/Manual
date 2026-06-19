# Coupang Partners Env

This project keeps Coupang Partners credentials in the local `.env` file only.
Do not paste real keys into chat, frontend code, `public/`, or any `VITE_` variable.

Add these values to `.env`:

```env
COUPANG_PARTNERS_ACCESS_KEY=your-coupang-partners-access-key
COUPANG_PARTNERS_SECRET_KEY=your-coupang-partners-secret-key
COUPANG_PARTNERS_SUB_ID=cheheommoa
COUPANG_PARTNERS_BASE_URL=https://api-gateway.coupang.com
COUPANG_PARTNERS_API_BASE_PATH=/v2/providers/affiliate_open_api/apis/openapi/v1
COUPANG_PARTNERS_DISCLOSURE=쿠팡 파트너스 활동의 일환으로 이에 따른 일정액의 수수료를 제공받습니다.

COUPANG_AD_KEYWORDS=리뷰 촬영 장비,촬영 조명,휴대폰 삼각대,블루투스 마이크,보조배터리,소품 촬영 배경
COUPANG_AD_CATEGORY_KEYWORDS=맛집=휴대폰 거치대|보조배터리|미니 삼각대;카페=소품 촬영 배경|미니 조명|휴대폰 삼각대;뷰티=LED 거울|촬영 조명|화장품 정리함;숙박=여행 파우치|멀티 충전기|보조배터리;생활=생활용품 정리함|무선 청소기|수납 바구니;서비스=노트북 거치대|블루투스 마이크|보조배터리
COUPANG_AD_CATEGORY_SLOTS=explore_inline
COUPANG_AD_CATEGORY_PER_SLOT=1
COUPANG_AD_SLOTS=home_top,explore_top,explore_inline
COUPANG_AD_PRODUCT_LIMIT=6
COUPANG_AD_PER_SLOT=3
COUPANG_AD_IMAGE_SIZE=512x512
COUPANG_AD_REPLACE_EXISTING=1
```

What to fill in:

- `COUPANG_PARTNERS_ACCESS_KEY`: Coupang Partners Open API access key.
- `COUPANG_PARTNERS_SECRET_KEY`: Coupang Partners Open API secret key.
- `COUPANG_PARTNERS_SUB_ID`: optional tracking ID. Keep `cheheommoa` first, then later split by slot like `home_top` or `map_bottom` if needed.
- `COUPANG_PARTNERS_BASE_URL`: keep the default unless Coupang changes the API host.
- `COUPANG_PARTNERS_API_BASE_PATH`: keep the default unless Coupang changes the Open API path.
- `COUPANG_PARTNERS_DISCLOSURE`: disclosure text shown near Coupang partner ads.
- `COUPANG_AD_KEYWORDS`: comma-separated keywords used when generating Coupang ad candidates.
- `COUPANG_AD_CATEGORY_KEYWORDS`: semicolon-separated category keyword map. Use `카테고리=키워드|키워드;카테고리=키워드` format.
- `COUPANG_AD_CATEGORY_SLOTS`: slots that should receive category-targeted Coupang candidates. Keep `explore_inline` first because the explore page has category context.
- `COUPANG_AD_CATEGORY_PER_SLOT`: maximum generated category-targeted ads per category and slot.
- `COUPANG_AD_SLOTS`: ad slots that Coupang ads can fill.
- `COUPANG_AD_PRODUCT_LIMIT`: maximum product count requested for each keyword.
- `COUPANG_AD_PER_SLOT`: maximum generated ads per slot. Use `3` or more so the frontend can rotate candidates instead of repeating one product.
- `COUPANG_AD_IMAGE_SIZE`: requested Coupang product image size.
- `COUPANG_AD_REPLACE_EXISTING`: keep `1` to replace old Coupang placeholder ads. Set `0` only after manually managed Coupang ads are marked with `managedBy: "manual"` or `preserve: true`.

Operational rules:

- Never prefix Coupang secret values with `VITE_`.
- Never commit the real `.env` file.
- Use `.env.example` only as a template.
- Check the env with `npm run ads:check:coupang`.
- Sync ads with `npm run ads:sync:coupang`.
