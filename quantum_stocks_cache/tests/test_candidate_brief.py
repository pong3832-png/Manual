from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.candidate_brief import run_candidate_briefs


def test_candidate_briefs_write_priority_company_briefs_and_index() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        research_filter_csv = root / "research_filter.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "company_name": "Samsung C&T",
                    "filter_status": "PRIORITY_RESEARCH",
                    "research_score": 88.5,
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "buy_case": "alpha timing이 BUY_READY입니다; 20일 모멘텀이 32.0%입니다",
                    "wait_reason": "대기 사유는 크지 않지만 사업/공시 수동 확인 필요",
                    "exclusion_condition": "decision이 AVOID로 바뀌면 제외",
                    "next_action": "사업 구조와 최근 공시를 수동 확인",
                    "expected_20d_return": 0.15,
                    "upside_probability": 0.78,
                    "return_20d": 0.32,
                    "ma20_gap": 0.08,
                    "drawdown_20d": -0.04,
                    "per": 18.4,
                    "pbr": 1.25,
                    "debt_ratio": 0.50,
                    "fundamental_score": 48.7,
                },
                {
                    "symbol": "005930.KS",
                    "company_name": "Samsung Electronics",
                    "filter_status": "PRIORITY_RESEARCH",
                    "research_score": 87.5,
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_NEUTRAL",
                    "buy_case": "alpha timing이 BUY_READY입니다; 상승 확률이 86.4%입니다",
                    "wait_reason": "대기 사유는 크지 않지만 사업/공시 수동 확인 필요",
                    "exclusion_condition": "SMA20 이탈 시 제외",
                    "next_action": "실적 컨퍼런스콜과 투자 계획을 확인",
                    "expected_20d_return": 0.19,
                    "upside_probability": 0.86,
                    "return_20d": 0.45,
                    "ma20_gap": 0.18,
                    "drawdown_20d": 0.0,
                    "per": 41.9,
                    "pbr": 4.34,
                    "debt_ratio": 0.30,
                    "fundamental_score": 46.3,
                },
                {
                    "symbol": "005380.KS",
                    "company_name": "Hyundai Motor",
                    "filter_status": "WATCH_FOR_CONFIRMATION",
                    "research_score": 82.9,
                    "decision": "BUY_READY",
                    "fundamental_view": "FUNDAMENTAL_WEAK",
                    "buy_case": "alpha timing이 BUY_READY입니다",
                    "wait_reason": "재무 점수 보강 확인 필요",
                    "exclusion_condition": "decision이 AVOID로 바뀌면 제외",
                    "next_action": "재무 점수 회복 여부를 관찰",
                    "expected_20d_return": 0.12,
                    "upside_probability": 0.86,
                    "return_20d": 0.33,
                    "ma20_gap": 0.10,
                    "drawdown_20d": -0.03,
                    "per": 13.5,
                    "pbr": 1.09,
                    "debt_ratio": 1.88,
                    "fundamental_score": 34.8,
                },
            ]
        ).to_csv(research_filter_csv, index=False)

        output = run_candidate_briefs(
            research_filter_csv=research_filter_csv,
            output_dir=output_dir,
            statuses=("PRIORITY_RESEARCH",),
        )

        assert output.csv_path.exists()
        assert output.index_path.exists()
        assert len(output.brief_paths) == 2
        assert output.report["symbol"].tolist() == ["028260.KS", "005930.KS"]

        first_brief = output.brief_paths[0].read_text(encoding="utf-8")
        assert "# 028260.KS Samsung C&T" in first_brief
        assert "## 핵심 데이터" in first_brief
        assert "## 투자 논리" in first_brief
        assert "## 매수 보류 조건" in first_brief
        assert "실제 주문 실행 문서가 아닙니다" in first_brief

        index = output.index_path.read_text(encoding="utf-8")
        assert "# Candidate Brief Index" in index
        assert "028260.KS Samsung C&T" in index
        assert "005380.KS" not in index
