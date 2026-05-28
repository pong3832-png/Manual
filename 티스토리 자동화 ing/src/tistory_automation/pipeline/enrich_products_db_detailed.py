import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = PROJECT_ROOT / "data" / "products" / "products_db_category.csv"

FIELDS = [
    "카테고리",
    "상품군",
    "계절태그",
    "대상독자",
    "사용장소",
    "문제상황",
    "장점1",
    "장점2",
    "장점3",
    "주의점",
    "글관점",
    "제목시드",
    "썸네일프롬프트",
    "CTA문구",
]

GROUP_RULES = [
    ("전기포트", ["전기포트", "전기 주전자", "포트", "주전자포트"]),
    ("건조대", ["건조대", "빨래건조"]),
    ("선풍기", ["선풍기", "서큘레이터", "써큘레이터", "테이블팬", "bldc"]),
    ("에어컨", ["에어컨", "무풍"]),
    ("냉풍기", ["냉풍기"]),
    ("제습기", ["제습기"]),
    ("가습기", ["가습기"]),
    ("모기퇴치", ["모기", "모기퇴치", "리퀴드", "벌레퇴치"]),
    ("화장지", ["화장지", "롤화장지", "휴지"]),
    ("물티슈", ["물티슈"]),
    ("키친타올", ["키친타올"]),
    ("세탁세제", ["세제", "세탁세제", "캡슐세제", "액체세제", "가루세제"]),
    ("섬유유연제", ["섬유유연제", "유연제"]),
    ("청소포", ["청소포", "정전기포", "물걸레포"]),
    ("배수구청소", ["배수구", "배수구청소", "싱크대클리너"]),
    ("핸드워시", ["핸드워시", "핸드솝"]),
    ("치약", ["치약"]),
    ("염색약", ["염색", "염색약"]),
    ("바디워시", ["바디워시", "바디클렌저"]),
    ("칫솔", ["칫솔"]),
    ("지퍼백", ["지퍼백", "비닐백"]),
    ("옷걸이", ["옷걸이"]),
    ("막대걸레", ["막대걸레", "밀대"]),
    ("테이프", ["테이프"]),
    ("세탁망", ["세탁망"]),
    ("분무기", ["분무기"]),
    ("행주", ["행주"]),
    ("수세미", ["수세미", "스펀지"]),
]

DEFAULT_META = {
    "카테고리": "생활용품",
    "계절태그": "사계절",
    "대상독자": "생활 동선을 조금 더 편하게 만들고 싶은 사람",
    "사용장소": "집, 사무실, 개인 공간",
    "문제상황": "사소하지만 반복되는 불편을 줄이고 싶은 상황",
    "장점1": "일상에서 자주 체감되는 편의 차이가 있음",
    "장점2": "가볍게 도입해 생활 만족도를 높이기 좋음",
    "장점3": "생활 습관과 잘 맞으면 만족도가 크게 올라감",
    "주의점": "실제 사용하는 공간과 빈도를 먼저 생각하고 고르는 편이 좋음",
    "글관점": "생활 문제 해결형 후기",
    "제목시드": "실제로 써보며 느낀 기준 제목",
    "썸네일프롬프트": "집 안에서 제품을 자연스럽게 사용하는 생활 장면",
    "CTA문구": "실제 생활 동선에 맞는 제품인지 먼저 확인해보는 편이 좋다",
}

GROUP_META = {
    "전기포트": {
        "카테고리": "주방가전",
        "계절태그": "사계절",
        "대상독자": "원룸이나 자취 생활을 하는 사람",
        "사용장소": "원룸 주방, 탕비실",
        "문제상황": "물을 자주 끓이는데 냄비로 하기는 번거롭고 빠른 주방 루틴이 필요한 상황",
        "장점1": "바쁜 일상에서 물 끓이는 시간을 줄이기 좋음",
        "장점2": "작은 주방에서도 부담 없이 두기 좋은 제품이 많음",
        "장점3": "자취 초반 만족도가 높은 대표 주방가전임",
        "주의점": "용량과 세척 편의, 뚜껑 구조를 같이 봐야 함",
        "글관점": "자취 실사용형 후기",
        "제목시드": "자취 전기포트를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "작은 주방에서 전기포트를 사용하는 생활 장면",
        "CTA문구": "자취 주방 가전을 찾는다면 용량과 세척 편의부터 같이 보면 좋다",
    },
    "건조대": {
        "카테고리": "생활용품",
        "계절태그": "사계절",
        "대상독자": "원룸이나 자취 생활을 하는 사람",
        "사용장소": "원룸, 작은 방, 베란다",
        "문제상황": "빨래를 널 공간이 부족하거나 동선이 불편해 생활 스트레스가 생기는 상황",
        "장점1": "한정된 공간에서도 활용도를 높이기 좋음",
        "장점2": "접이식, 이동성 같은 생활 편의 차이가 큼",
        "장점3": "매일 쓰는 생활용품이라 만족도 차이가 분명함",
        "주의점": "펼쳤을 때 크기와 이동 동선을 같이 봐야 함",
        "글관점": "자취 실사용형 후기",
        "제목시드": "원룸 빨래건조대를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "좁은 공간에서 건조대를 사용하는 자연스러운 생활 장면",
        "CTA문구": "작은 공간에서 쓸 제품이라면 펼쳤을 때 크기부터 확인해보는 편이 좋다",
    },
}


def get_text(row, key):
    return str(row.get(key, "") or "").strip()


def infer_group(name, keyword):
    text = f"{name} {keyword}".lower()
    for group, needles in GROUP_RULES:
        if any(needle.lower() in text for needle in needles):
            return group
    return "기타 생활용품"


def build_meta(row):
    name = get_text(row, "상품명")
    keyword = get_text(row, "키워드")
    group = infer_group(name, keyword)
    base = dict(DEFAULT_META)
    if group in GROUP_META:
        base.update(GROUP_META[group])

    return {
        "카테고리": base["카테고리"],
        "상품군": group,
        "계절태그": base["계절태그"],
        "대상독자": base["대상독자"],
        "사용장소": base["사용장소"],
        "문제상황": base["문제상황"],
        "장점1": base["장점1"],
        "장점2": base["장점2"],
        "장점3": base["장점3"],
        "주의점": base["주의점"],
        "글관점": base["글관점"],
        "제목시드": f"{keyword} 관련 {base['제목시드']}",
        "썸네일프롬프트": base["썸네일프롬프트"],
        "CTA문구": base["CTA문구"],
    }


def main():
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []

    for field in FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    updated = 0
    for row in rows:
        meta = build_meta(row)
        touched = False
        for field in FIELDS:
            if not get_text(row, field):
                row[field] = meta[field]
                touched = True
        if touched:
            updated += 1

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"updated_rows={updated}")


if __name__ == "__main__":
    main()
