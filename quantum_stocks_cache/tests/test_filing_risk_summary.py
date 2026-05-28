from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_filing_risk_summary_compresses_text_hits_into_five_core_risks() -> None:
    module = importlib.import_module("quantum_trainer.filing_risk_summary")

    with TemporaryDirectory(dir=PROJECT_ROOT) as tmp_dir:
        root = Path(tmp_dir)
        scan_csv = root / "opendart_text_risk_scan_028260.csv"
        output_dir = root / "reports"
        pd.DataFrame(
            [
                {
                    "symbol": "028260.KS",
                    "review_check": "litigation_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "분쟁",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "미국-이란 분쟁과 환율 변동은 원재료 가격 상승을 유발할 수 있음",
                },
                {
                    "symbol": "028260.KS",
                    "review_check": "litigation_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "소송",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "소송 건수 206 56 소송 금액 274,584 293,756 경영진은 중요한 영향을 미치지 아니할 것으로 예상",
                },
                {
                    "symbol": "028260.KS",
                    "review_check": "litigation_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "소송",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "로직스 증선위 조치 관련 취소 소송은 서울고등법원에서 진행 중",
                },
                {
                    "symbol": "028260.KS",
                    "review_check": "contingent_liability_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "약정",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "외화채권·채무 환율 위험회피 목적으로 통화선도계약과 금속선물/선도계약 체결",
                },
                {
                    "symbol": "028260.KS",
                    "review_check": "related_party_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "관계기업",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "130개 종속기업과 52개 관계기업 및 공동기업을 연결/지분법 대상으로 작성",
                },
                {
                    "symbol": "028260.KS",
                    "review_check": "project_risk_review",
                    "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                    "keyword": "수주",
                    "report_nm": "분기보고서 (2026.03)",
                    "rcept_no": "20260515001895",
                    "rcept_dt": "20260515",
                    "snippet": "건설부문 국내 수주 4.6조원, 해외 수주 2.9억 달러",
                },
            ]
        ).to_csv(scan_csv, index=False)

        output = module.run_filing_risk_summary(scan_csv=scan_csv, output_dir=output_dir)

        assert output.csv_path.exists()
        assert output.markdown_path.exists()
        assert len(output.report) == 5
        assert output.summary["symbol"] == "028260.KS"
        assert output.summary["core_risk_count"] == 5
        assert output.summary["fatal_risk_count"] == 0
        assert output.summary["overall_opinion"] == "PASS_CANDIDATE_WITH_MONITORING"

        titles = set(output.report["risk_title"])
        assert "Legal litigation exposure" in titles
        assert "Samsung Biologics accounting litigation overhang" in titles
        assert "Derivative and commodity hedge commitments" in titles
        assert "Complex affiliate and related-party structure" in titles
        assert "Construction order and project profitability risk" in titles
        assert set(output.report["gate_opinion"]) == {"PASS_CANDIDATE_WITH_MONITORING"}
        legal = output.report.loc[output.report["risk_id"] == "legal_litigation_exposure"].iloc[0]
        project = output.report.loc[output.report["risk_id"] == "construction_order_project_profitability"].iloc[0]
        assert "분쟁" not in legal["key_evidence"]
        assert "분쟁" in project["key_evidence"]

        markdown = output.markdown_path.read_text(encoding="utf-8")
        assert "Fatal risk: NO" in markdown
        assert "PASS_CANDIDATE_WITH_MONITORING" in markdown
        assert "Do not copy this into configs/manual_review.actual.csv automatically." in markdown


def test_filing_risk_summary_uses_generic_titles_for_non_samsung_ct_symbols() -> None:
    module = importlib.import_module("quantum_trainer.filing_risk_summary")

    scan = pd.DataFrame(
        [
            {
                "symbol": "003550.KS",
                "review_check": "litigation_review",
                "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                "keyword": "lawsuit",
                "report_nm": "Quarterly report",
                "rcept_no": "20260515002383",
                "rcept_dt": "20260515",
                "snippet": "Pending litigation exists but management does not expect material impact.",
            },
            {
                "symbol": "003550.KS",
                "review_check": "contingent_liability_review",
                "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                "keyword": "guarantee",
                "report_nm": "Quarterly report",
                "rcept_no": "20260515002383",
                "rcept_dt": "20260515",
                "snippet": "Contingent commitments and guarantees are disclosed for monitoring.",
            },
            {
                "symbol": "003550.KS",
                "review_check": "related_party_review",
                "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                "keyword": "affiliate",
                "report_nm": "Quarterly report",
                "rcept_no": "20260515002383",
                "rcept_dt": "20260515",
                "snippet": "Affiliate holdings and related-party transactions require monitoring.",
            },
            {
                "symbol": "003550.KS",
                "review_check": "project_risk_review",
                "scan_status": "TEXT_HIT_REVIEW_REQUIRED",
                "keyword": "project",
                "report_nm": "Quarterly report",
                "rcept_no": "20260515002383",
                "rcept_dt": "20260515",
                "snippet": "Large operating projects and IT service execution may affect margins.",
            },
        ]
    )

    report = module.build_filing_risk_summary(scan)

    titles = set(report["risk_title"])
    risk_ids = set(report["risk_id"])
    assert "Samsung Biologics accounting litigation overhang" not in titles
    assert "Construction order and project profitability risk" not in titles
    assert "samsung_biologics_accounting_litigation" not in risk_ids
    assert "construction_order_project_profitability" not in risk_ids
    assert "regulatory_accounting_litigation_overhang" in risk_ids
    assert "project_operating_execution_risk" in risk_ids
    assert "Regulatory/accounting litigation overhang" in titles
    assert "Project and operating execution risk" in titles

    combined_text = " ".join(
        report["risk_title"].astype(str).tolist()
        + report["key_evidence"].astype(str).tolist()
        + report["monitoring_rule"].astype(str).tolist()
    )
    assert "Samsung Biologics" not in combined_text
    assert "Construction order" not in combined_text
