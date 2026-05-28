import argparse
import csv
import os
from collections import Counter


TEMPLATE_FIELDS = [
    "상품명",
    "키워드",
    "쿠팡링크",
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
    "검색의도점수",
    "제목품질점수",
    "가격적합점수",
    "기본점수",
    "광고추천점수",
    "추천등급",
    "추천사유",
]

PRICE_KEYS = ("가격", "판매가", "productPrice")
RANK_KEYS = ("검색순위", "rank")
ROCKET_KEYS = ("로켓정보", "로켓여부", "isRocket")
FREE_SHIPPING_KEYS = ("무료배송여부", "isFreeShipping")

NOISE_WORDS = {
    "공식수입",
    "공식",
    "정품",
    "무료배송",
    "개별포장",
    "대용량",
    "대용량",
    "쇼핑백",
    "1개",
    "2개",
    "3개",
}

INTENT_WORDS = {
    "추천",
    "가성비",
    "원룸",
    "자취",
    "정리",
    "수납",
    "청소",
    "냄새",
    "제거",
    "건강",
    "비타민",
}

GROUP_PRICE_RULES = {
    "선풍기": (30000, 150000),
    "에어컨": (300000, 1500000),
    "냉풍기": (70000, 300000),
    "제습기": (120000, 500000),
    "가습기": (30000, 200000),
    "모기퇴치": (5000, 50000),
    "건조대": (20000, 90000),
    "전기포트": (20000, 80000),
    "기타 생활용품": (8000, 70000),
}

GROUP_RULES = [
    ("선풍기", ["선풍기", "서큘레이터", "써큘레이터", "테이블팬", "bldc"]),
    ("에어컨", ["에어컨", "무풍"]),
    ("냉풍기", ["냉풍기"]),
    ("제습기", ["제습기"]),
    ("가습기", ["가습기"]),
    ("모기퇴치", ["모기", "모기퇴치", "벌레퇴치", "리퀴드"]),
    ("건조대", ["건조대", "빨래건조"]),
    ("전기포트", ["전기포트", "전기 주전자", "주전자포트", "포트"]),
    ("기타 생활용품", []),
]

GROUP_DEFAULTS = {
    "선풍기": {
        "카테고리": "여름가전",
        "계절태그": "여름",
        "대상독자": "원룸이나 자취 생활을 하는 사람",
        "사용장소": "원룸, 침대 옆, 책상 주변",
        "문제상황": "더운 날씨에 실내 공기가 답답하고 바로 바람이 필요한 상황",
        "장점1": "작은 공간에서도 시원함을 챙기기 좋음",
        "장점2": "책상이나 침대 옆에 두고 쓰기 좋은 제품이 많음",
        "장점3": "여름철 체감 만족도가 높은 대표 가전임",
        "주의점": "바람 세기와 소음, 회전 범위를 같이 보고 고르는 편이 좋음",
        "글관점": "자취 실사용형 후기",
        "제목시드": "선풍기를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "작은 방이나 책상 주변에서 선풍기를 사용하는 자연스러운 여름 장면",
        "CTA문구": "좁은 공간에서 쓸 제품이라면 크기와 소음부터 같이 확인해보는 편이 좋다",
    },
    "에어컨": {
        "카테고리": "여름가전",
        "계절태그": "여름",
        "대상독자": "무더위에 실내 냉방 제품을 찾는 사람",
        "사용장소": "원룸, 침실, 거실",
        "문제상황": "무더운 날씨에 선풍기만으로는 부족해 냉방 성능이 더 필요한 상황",
        "장점1": "더운 시간대 체감 온도를 빠르게 낮추기 좋음",
        "장점2": "공간 크기에 맞게 고르면 만족도가 높음",
        "장점3": "여름철 체감 차이가 가장 큰 대표 가전임",
        "주의점": "설치 조건과 공간 크기, 전력 사용량을 같이 봐야 함",
        "글관점": "계절 대비형 후기",
        "제목시드": "원룸 에어컨을 고를 때 먼저 따져보게 되는 기준",
        "썸네일프롬프트": "여름철 실내에서 냉방 중인 생활 공간 장면",
        "CTA문구": "설치 환경과 냉방 범위를 같이 보면 실패 확률이 줄어든다",
    },
    "냉풍기": {
        "카테고리": "여름가전",
        "계절태그": "여름",
        "대상독자": "에어컨 보조 냉방 제품이 필요한 사람",
        "사용장소": "거실, 책상 주변, 작업 공간",
        "문제상황": "에어컨만으로는 아쉽거나 특정 자리만 시원하게 만들고 싶은 상황",
        "장점1": "특정 공간에 시원한 바람을 보조적으로 보내기 좋음",
        "장점2": "설치 부담이 적어 비교적 간단하게 쓰기 좋음",
        "장점3": "보조 냉방용으로 만족도가 높은 편임",
        "주의점": "에어컨 대체보다 보조 용도로 기대치를 잡는 편이 좋음",
        "글관점": "비교 정리형 후기",
        "제목시드": "냉풍기를 고를 때 에어컨과 다르게 봐야 하는 기준",
        "썸네일프롬프트": "여름철 실내에서 냉풍기를 사용하는 생활 장면",
        "CTA문구": "보조 냉방이 필요한 상황이라면 공간 크기와 사용 목적부터 같이 보면 좋다",
    },
    "제습기": {
        "카테고리": "계절가전",
        "계절태그": "여름,장마",
        "대상독자": "장마철 습기와 빨래 냄새가 고민인 사람",
        "사용장소": "원룸, 침실, 세탁실",
        "문제상황": "실내 습도가 높아 빨래 건조와 꿉꿉함이 스트레스가 되는 상황",
        "장점1": "실내 습도를 관리해 체감 공기를 쾌적하게 만듦",
        "장점2": "빨래 냄새나 눅눅함을 줄이는 데 도움 됨",
        "장점3": "장마철 만족도가 높은 대표 가전임",
        "주의점": "물통 크기와 배수 방식, 소음 수준을 같이 봐야 함",
        "글관점": "생활 문제 해결형 후기",
        "제목시드": "장마철 제습기를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "실내 습기를 관리하는 제습기와 생활 공간 장면",
        "CTA문구": "습도 관리가 필요한 시기라면 배수 방식과 소음부터 같이 확인해보는 편이 좋다",
    },
    "가습기": {
        "카테고리": "계절가전",
        "계절태그": "겨울,환절기",
        "대상독자": "건조한 계절에 실내 환경을 관리하고 싶은 사람",
        "사용장소": "침실, 책상, 거실",
        "문제상황": "실내 공기가 건조해 목이나 피부 컨디션이 불편한 상황",
        "장점1": "건조한 실내 환경을 보완하는 데 도움 됨",
        "장점2": "책상이나 침대 옆에서 쓰기 좋은 제품이 많음",
        "장점3": "환절기 체감 만족도가 높은 계절가전임",
        "주의점": "세척 편의성과 물통 관리 난이도를 같이 봐야 함",
        "글관점": "생활 문제 해결형 후기",
        "제목시드": "가습기를 고를 때 실제로 보게 되는 생활 기준",
        "썸네일프롬프트": "침실이나 책상 옆에서 가습기를 사용하는 포근한 장면",
        "CTA문구": "매일 쓰는 제품이라면 세척 편의와 물통 관리부터 같이 보는 편이 좋다",
    },
    "모기퇴치": {
        "카테고리": "생활용품",
        "계절태그": "여름",
        "대상독자": "여름철 벌레나 모기가 신경 쓰이는 사람",
        "사용장소": "침실, 거실, 주방",
        "문제상황": "모기나 벌레 때문에 숙면이나 생활 리듬이 자주 깨지는 상황",
        "장점1": "반복되는 생활 스트레스를 줄이는 데 도움 됨",
        "장점2": "집 안에서 바로 체감하기 쉬운 생활용품임",
        "장점3": "여름철 꾸준히 찾는 대표 생활용품군임",
        "주의점": "사용 공간과 방식에 맞는 제품인지 먼저 확인하는 편이 좋음",
        "글관점": "생활 문제 해결형 후기",
        "제목시드": "모기퇴치 제품을 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "실내에서 모기퇴치 제품을 사용하는 여름 생활 장면",
        "CTA문구": "비슷해 보여도 사용 공간과 방식이 달라서 먼저 확인해보는 편이 좋다",
    },
    "건조대": {
        "카테고리": "생활용품",
        "계절태그": "사계절",
        "대상독자": "원룸이나 자취 생활을 하는 사람",
        "사용장소": "원룸, 작은 방, 베란다",
        "문제상황": "빨래를 널 공간이 부족하거나 동선이 불편한 상황",
        "장점1": "한정된 공간에서도 활용도를 높이기 좋음",
        "장점2": "접이식, 이동성 같은 생활 편의 차이가 큼",
        "장점3": "매일 쓰는 생활용품이라 만족도 차이가 분명함",
        "주의점": "펼쳤을 때 크기와 이동 동선을 같이 봐야 함",
        "글관점": "자취 실사용형 후기",
        "제목시드": "원룸 빨래건조대를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "좁은 공간에서 건조대를 사용하는 자연스러운 생활 장면",
        "CTA문구": "작은 공간에서 쓸 제품이라면 펼쳤을 때 크기부터 확인해보는 편이 좋다",
    },
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
        "글관점": "가성비 입문형 후기",
        "제목시드": "자취 전기포트를 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "작은 주방에서 전기포트를 사용하는 자연스러운 생활 장면",
        "CTA문구": "자취 주방 가전을 찾는다면 용량과 세척 편의부터 같이 보면 좋겠다",
    },
    "기타 생활용품": {
        "카테고리": "생활용품",
        "계절태그": "사계절",
        "대상독자": "생활 동선을 조금 더 편하게 만들고 싶은 사람",
        "사용장소": "집, 사무실, 개인 공간",
        "문제상황": "작지만 반복되는 생활 불편을 줄이고 싶은 상황",
        "장점1": "일상에서 자주 체감되는 편의 차이가 있음",
        "장점2": "가볍게 도입해 생활 만족도를 높이기 좋음",
        "장점3": "생활 루틴과 맞으면 만족도가 크게 올라감",
        "주의점": "실제 생활 공간과 습관에 맞는지 먼저 생각하고 고르는 편이 좋음",
        "글관점": "생활 문제 해결형 후기",
        "제목시드": "생활용품을 고를 때 실제로 보게 되는 기준",
        "썸네일프롬프트": "집 안에서 생활용품을 자연스럽게 사용하는 장면",
        "CTA문구": "실제 생활 동선에 맞는 제품인지 먼저 확인해보는 편이 좋다",
    },
}

ANGLE_BY_GROUP = {
    "선풍기": "자취 실사용형 후기",
    "에어컨": "계절 대비형 후기",
    "냉풍기": "비교 정리형 후기",
    "제습기": "생활 문제 해결형 후기",
    "가습기": "생활 문제 해결형 후기",
    "모기퇴치": "생활 문제 해결형 후기",
    "건조대": "자취 실사용형 후기",
    "전기포트": "가성비 입문형 후기",
    "기타 생활용품": "생활 문제 해결형 후기",
}


def parse_args():
    parser = argparse.ArgumentParser(description="products_db.csv 메타 초안 자동 생성")
    parser.add_argument(
        "--csv-path",
        default=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "data",
            "products",
            "products_db_category.csv",
        ),
        help="대상 CSV 경로",
    )
    return parser.parse_args()


def load_csv_rows(csv_path):
    last_error = None
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                return list(reader), list(reader.fieldnames or []), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"CSV 인코딩을 읽지 못했습니다: {csv_path}") from last_error


def normalize_fieldnames(fieldnames):
    normalized = list(fieldnames)
    for field in TEMPLATE_FIELDS:
        if field not in normalized:
            normalized.append(field)
    return normalized


def get_text(row, *keys, default=""):
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def parse_int(value, default=0):
    text = str(value or "").strip()
    if not text:
        return default
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else default


def tokenize(text):
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in (text or "").lower())
    return [token for token in cleaned.split() if token]


def get_price(row):
    for key in PRICE_KEYS:
        if key in row:
            price = parse_int(row.get(key))
            if price > 0:
                return price
    return 0


def get_rank(row):
    for key in RANK_KEYS:
        if key in row:
            rank = parse_int(row.get(key))
            if rank > 0:
                return rank
    return 0


def is_truthy_field(row, keys):
    for key in keys:
        value = str(row.get(key, "") or "").strip().lower()
        if value in {"y", "yes", "true", "1", "로켓배송", "로켓", "무료배송"}:
            return True
    return False


def score_search_intent(name, keyword):
    name_tokens = set(tokenize(name))
    keyword_tokens = tokenize(keyword)
    if not keyword_tokens:
        return 45

    overlap = sum(1 for token in keyword_tokens if token in name_tokens)
    exact_bonus = 25 if keyword and keyword.lower() in name.lower() else 0
    token_score = int((overlap / len(keyword_tokens)) * 55)
    intent_bonus = sum(4 for token in keyword_tokens if token in INTENT_WORDS)
    return max(0, min(100, 20 + token_score + exact_bonus + min(intent_bonus, 20)))


def score_title_quality(name):
    score = 65
    length = len(name)
    if 12 <= length <= 45:
        score += 15
    elif length <= 8 or length >= 70:
        score -= 20
    else:
        score += 5

    comma_count = name.count(",")
    if comma_count >= 3:
        score -= 10
    elif comma_count == 2:
        score -= 5

    noise_hits = sum(1 for word in NOISE_WORDS if word in name)
    score -= min(noise_hits * 4, 20)
    return max(0, min(100, score))


def score_price_fit(group_name, price):
    if price <= 0:
        return 55

    min_price, max_price = GROUP_PRICE_RULES.get(group_name, GROUP_PRICE_RULES["기타 생활용품"])
    if min_price <= price <= max_price:
        return 90
    if price < min_price:
        gap = max(1, min_price - price)
        penalty = min(35, int(gap / max(1, min_price) * 60))
        return max(25, 80 - penalty)
    gap = price - max_price
    penalty = min(40, int(gap / max(1, max_price) * 60))
    return max(20, 78 - penalty)


def score_basic(row, name, has_link):
    score = 55
    rank = get_rank(row)
    if rank > 0:
        if rank <= 3:
            score += 25
        elif rank <= 10:
            score += 18
        elif rank <= 30:
            score += 10
        else:
            score += 4
    if is_truthy_field(row, ROCKET_KEYS) or "로켓" in name:
        score += 10
    if is_truthy_field(row, FREE_SHIPPING_KEYS):
        score += 5
    if has_link:
        score += 5
    return max(0, min(100, score))


def build_score_fields(row, name, keyword, group_name, link):
    intent_score = score_search_intent(name, keyword)
    title_score = score_title_quality(name)
    price_score = score_price_fit(group_name, get_price(row))
    basic_score = score_basic(row, name, bool(link))
    final_score = int(
        round(
            intent_score * 0.40
            + title_score * 0.30
            + price_score * 0.15
            + basic_score * 0.15
        )
    )

    if final_score >= 78:
        grade = "A"
    elif final_score >= 62:
        grade = "B"
    else:
        grade = "C"

    reasons = []
    if intent_score >= 80:
        reasons.append("키워드 일치도가 높음")
    if title_score >= 75:
        reasons.append("제목 품질이 무난함")
    if price_score >= 80:
        reasons.append("가격대가 적정 범위")
    if basic_score >= 75:
        reasons.append("기본 신호가 양호함")
    if not reasons:
        reasons.append("추가 검토가 필요한 후보")

    return {
        "검색의도점수": str(intent_score),
        "제목품질점수": str(title_score),
        "가격적합점수": str(price_score),
        "기본점수": str(basic_score),
        "광고추천점수": str(final_score),
        "추천등급": grade,
        "추천사유": ", ".join(reasons[:2]),
    }


def infer_group(name, keyword):
    text = f"{name} {keyword}".lower()
    for group_name, keywords in GROUP_RULES:
        if any(item.lower() in text for item in keywords):
            return group_name
    return "기타 생활용품"


def infer_target_reader(keyword, group_name):
    keyword = keyword or ""
    if "원룸" in keyword or "자취" in keyword:
        return "원룸이나 자취 생활을 하는 사람"
    if "사무실" in keyword:
        return "책상 주변이나 사무실에서 바로 쓸 제품을 찾는 사람"
    if "업소" in keyword:
        return "넓은 공간이나 업장 환경에서 사용할 제품을 찾는 사람"
    defaults = GROUP_DEFAULTS.get(group_name, GROUP_DEFAULTS["기타 생활용품"])
    return defaults["대상독자"]


def infer_usage_place(keyword, group_name):
    keyword = keyword or ""
    if "원룸" in keyword:
        return "원룸, 작은 방"
    if "사무실" in keyword:
        return "사무실, 책상 주변"
    if "가정용" in keyword:
        return "거실, 주방, 침실"
    if "업소" in keyword:
        return "매장, 업무 공간, 넓은 실내"
    defaults = GROUP_DEFAULTS.get(group_name, GROUP_DEFAULTS["기타 생활용품"])
    return defaults["사용장소"]


def build_metadata(row):
    name = get_text(row, "상품명")
    keyword = get_text(row, "키워드")
    link = get_text(row, "쿠팡링크")
    group_name = infer_group(name, keyword)
    defaults = GROUP_DEFAULTS.get(group_name, GROUP_DEFAULTS["기타 생활용품"])
    target_reader = infer_target_reader(keyword, group_name)
    usage_place = infer_usage_place(keyword, group_name)
    angle_name = ANGLE_BY_GROUP.get(group_name, "생활 문제 해결형 후기")

    metadata = {
        "상품명": name,
        "키워드": keyword,
        "쿠팡링크": link,
        "카테고리": defaults["카테고리"],
        "상품군": group_name,
        "계절태그": defaults["계절태그"],
        "대상독자": target_reader,
        "사용장소": usage_place,
        "문제상황": defaults["문제상황"],
        "장점1": defaults["장점1"],
        "장점2": defaults["장점2"],
        "장점3": defaults["장점3"],
        "주의점": defaults["주의점"],
        "글관점": angle_name,
        "제목시드": f"{keyword} 관련 {defaults['제목시드']}",
        "썸네일프롬프트": defaults["썸네일프롬프트"],
        "CTA문구": defaults["CTA문구"],
    }
    metadata.update(build_score_fields(row, name, keyword, group_name, link))
    return metadata


def enrich_rows(rows, fieldnames):
    filled_counter = Counter()
    for row in rows:
        metadata = build_metadata(row)
        for field, value in metadata.items():
            if field in {
                "검색의도점수",
                "제목품질점수",
                "가격적합점수",
                "기본점수",
                "광고추천점수",
                "추천등급",
                "추천사유",
            }:
                if get_text(row, field) != str(value):
                    row[field] = value
                    filled_counter[field] += 1
                continue
            if not get_text(row, field):
                row[field] = value
                filled_counter[field] += 1
    return rows, normalize_fieldnames(fieldnames), filled_counter


def write_rows(csv_path, rows, fieldnames, encoding):
    with open(csv_path, "w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {field: row.get(field, "") for field in fieldnames}
            writer.writerow(normalized)


def main():
    args = parse_args()
    rows, fieldnames, encoding = load_csv_rows(args.csv_path)
    rows, fieldnames, filled_counter = enrich_rows(rows, fieldnames)
    write_rows(args.csv_path, rows, fieldnames, encoding)

    print(f"메타 초안 자동 생성 완료: {args.csv_path}")
    if filled_counter:
        print("채운 필드 수:")
        for field, count in filled_counter.most_common():
            print(f"- {field}: {count}")


if __name__ == "__main__":
    main()
