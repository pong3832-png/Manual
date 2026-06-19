from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "제미나이웹.py"


def extract_block(text, start_marker, end_marker):
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def main():
    text = TARGET.read_text(encoding="utf-8")
    category_block = extract_block(text, "DAILY_CATEGORY_BANK = [", "DAILY_SEARCH_INTENT_BANK = {")
    prompt_block = extract_block(text, "[skssj2627 블로그 방향]", "[절대 금지]")

    required_categories = [
        "월세계약",
        "이사입주",
        "인터넷통신",
        "생활비공과금",
    ]
    excluded_categories = [
        "보험보증",
        "자동차정비",
        "렌탈설치",
    ]
    weak_categories = [
        "장마습기",
        "냉방전기세",
        "환기공기질",
        "빨래냄새",
        "집안냄새곰팡이",
        "생활가전체크",
    ]

    missing = [item for item in required_categories if item not in category_block]
    remaining_weak = [item for item in weak_categories if item in category_block]
    remaining_excluded = [item for item in excluded_categories if item in category_block]
    prompt_terms = [
        "월세 계약",
        "전입신고",
        "확정일자",
        "인터넷 약정",
        "이사 체크리스트",
        "관리비 고지서",
        "전기요금 자동이체",
        "공과금",
        "공식 안내와 계약서를 기준으로 다시 확인",
        "월세·이사·통신·공과금",
        "주제 적합도",
        "경험 정보",
        "정보의 충실성",
        "독창성",
        "적시성",
        "관심사 집중도",
        "AI 브리핑",
        "한 문장 답",
        "동일한 문장 구조 반복",
    ]
    missing_prompt_terms = [item for item in prompt_terms if item not in prompt_block]

    assert not missing, f"missing adpost categories: {missing}"
    assert not remaining_weak, f"weak categories still in rotation: {remaining_weak}"
    assert not remaining_excluded, f"excluded categories still in rotation: {remaining_excluded}"
    assert not missing_prompt_terms, f"missing prompt terms: {missing_prompt_terms}"

    print("adpost topic rotation check passed")


if __name__ == "__main__":
    main()
