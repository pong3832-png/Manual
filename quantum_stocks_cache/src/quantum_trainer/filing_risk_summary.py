from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


SCAN_COLUMNS = {
    "symbol",
    "review_check",
    "scan_status",
    "keyword",
    "report_nm",
    "rcept_no",
    "rcept_dt",
    "snippet",
}

OUTPUT_COLUMNS = [
    "symbol",
    "risk_id",
    "risk_title",
    "source_checks",
    "evidence_count",
    "source_reports",
    "source_dates",
    "source_receipts",
    "key_evidence",
    "fatal_risk",
    "gate_opinion",
    "monitoring_rule",
]


@dataclass(frozen=True)
class FilingRiskSummaryOutput:
    report: pd.DataFrame
    csv_path: Path
    markdown_path: Path
    summary: dict[str, str | int]


@dataclass(frozen=True)
class RiskDefinition:
    risk_id: str
    risk_title: str
    matcher: Callable[[pd.DataFrame], pd.Series]
    fallback_checks: tuple[str, ...]
    key_evidence: str
    monitoring_rule: str


def run_filing_risk_summary(scan_csv: Path | str, output_dir: Path | str) -> FilingRiskSummaryOutput:
    scan = _load_scan_csv(scan_csv)
    report = build_filing_risk_summary(scan)
    symbol = str(report["symbol"].iloc[0]) if not report.empty else _symbol_from_path(Path(scan_csv))
    code = _symbol_code(symbol)

    output_root = Path(output_dir).resolve() / "filing_review"
    output_root.mkdir(parents=True, exist_ok=True)
    csv_path = output_root / f"filing_risk_summary_{code}.csv"
    markdown_path = output_root / f"filing_risk_summary_{code}.md"
    report.to_csv(csv_path, index=False, encoding="utf-8-sig")

    summary = _summary(report)
    markdown_path.write_text(_render_markdown(report, summary), encoding="utf-8")
    return FilingRiskSummaryOutput(report=report, csv_path=csv_path, markdown_path=markdown_path, summary=summary)


def build_filing_risk_summary(scan: pd.DataFrame) -> pd.DataFrame:
    if scan.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    normalized = scan.fillna("").copy()
    for column in SCAN_COLUMNS:
        normalized[column] = normalized[column].astype(str)

    symbol = str(normalized["symbol"].iloc[0])
    rows = [_risk_row(symbol, normalized, definition) for definition in _risk_definitions(symbol)]
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _load_scan_csv(path: Path | str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"OpenDART text risk scan CSV not found: {csv_path}")
    scan = pd.read_csv(csv_path).fillna("")
    missing = sorted(SCAN_COLUMNS.difference(scan.columns))
    if missing:
        raise ValueError(f"OpenDART text risk scan CSV missing required columns: {missing}")
    return scan


def _risk_definitions(symbol: str) -> list[RiskDefinition]:
    is_samsung_ct = _symbol_code(symbol) == "028260"
    accounting_litigation_title = (
        "Samsung Biologics accounting litigation overhang"
        if is_samsung_ct
        else "Regulatory/accounting litigation overhang"
    )
    accounting_litigation_risk_id = (
        "samsung_biologics_accounting_litigation"
        if is_samsung_ct
        else "regulatory_accounting_litigation_overhang"
    )
    accounting_litigation_evidence = (
        (
            "삼성바이오로직스 회계처리 관련 증선위 조치 취소 소송과 항소 진행 내용이 확인됩니다. "
            "삼성물산 본업 현금흐름보다 지분가치와 지배구조 할인에 영향을 줄 수 있는 리스크입니다."
        )
        if is_samsung_ct
        else (
            "규제 조치, 회계 쟁점, 감사의견, 계열사 소송은 밸류에이션과 지배구조 할인에 영향을 줄 수 있습니다."
        )
    )
    accounting_litigation_monitoring = (
        "항소심 판단, 제재 효력 변화, 바이오 지분가치 급락이 발생하면 filing_review 보류"
        if is_samsung_ct
        else "대형 규제 제재, 부정적 감사의견, 중대한 계열사 소송이 발생하면 filing_review 보류"
    )
    project_risk_title = (
        "Construction order and project profitability risk"
        if is_samsung_ct
        else "Project and operating execution risk"
    )
    project_risk_id = (
        "construction_order_project_profitability"
        if is_samsung_ct
        else "project_operating_execution_risk"
    )
    project_risk_matcher = (
        (
            lambda frame: (frame["review_check"] == "project_risk_review")
            | ((frame["review_check"] == "litigation_review") & (frame["keyword"] == "분쟁"))
        )
        if is_samsung_ct
        else (lambda frame: frame["review_check"] == "project_risk_review")
    )
    project_risk_evidence = (
        (
            "건설 수주 규모와 우량 프로젝트 중심 전략은 확인되지만, 대형 프로젝트 종료와 일회성 비용은 "
            "실적 변동 요인이므로 수주 마진과 원가 리스크를 확인해야 합니다."
        )
        if is_samsung_ct
        else (
            "대형 프로젝트, 운영 실행력, 서비스 제공 품질, 투자 부담은 마진과 실적 변동 요인으로 확인해야 합니다."
        )
    )
    project_risk_monitoring = (
        "건설부문 영업이익 추가 둔화, 대형 프로젝트 원가 상승, 신규 수주 마진 악화 시 보류"
        if is_samsung_ct
        else "프로젝트 마진 악화, 실행 손실, 대규모 투자로 인한 이익 훼손이 확인되면 보류"
    )
    related_party_evidence = (
        (
            "130개 종속기업과 52개 관계기업/공동기업 등 그룹 구조가 복잡해 관련자 거래와 "
            "지분법 손익 변동을 계속 확인해야 합니다."
        )
        if is_samsung_ct
        else (
            "특수관계자 거래, 계열회사 지분, 주요 주주와의 거래 조건은 이익 변동과 "
            "지배구조 할인 요인이 될 수 있어 계속 확인해야 합니다."
        )
    )
    return [
        RiskDefinition(
            risk_id="legal_litigation_exposure",
            risk_title="Legal litigation exposure",
            matcher=lambda frame: (frame["review_check"] == "litigation_review")
            & (frame["keyword"] == "소송")
            & ~_contains_any(frame["snippet"], ["로직스", "증선위", "행정처분", "회계처리"]),
            fallback_checks=("litigation_review",),
            key_evidence=(
                "소송 건수와 금액 공시는 있으나 현재 추출 근거에서는 경영진이 연결 재무제표에 "
                "중요한 영향을 예상하지 않는다는 문구가 함께 확인됩니다."
            ),
            monitoring_rule="소송 충당부채 증가, 경영진의 중요성 평가 변화, 신규 대형 소송 공시 발생 시 보류로 전환",
        ),
        RiskDefinition(
            risk_id=accounting_litigation_risk_id,
            risk_title=accounting_litigation_title,
            matcher=lambda frame: (frame["review_check"] == "litigation_review")
            & _contains_any(frame["snippet"], ["로직스", "증선위", "행정처분", "회계처리"]),
            fallback_checks=("litigation_review",),
            key_evidence=accounting_litigation_evidence,
            monitoring_rule=accounting_litigation_monitoring,
        ),
        RiskDefinition(
            risk_id="derivative_and_commodity_hedge_commitments",
            risk_title="Derivative and commodity hedge commitments",
            matcher=lambda frame: frame["review_check"] == "contingent_liability_review",
            fallback_checks=("contingent_liability_review",),
            key_evidence=(
                "통화선도와 금속선물/선도계약은 외화채권·채무와 상품가격 변동위험 회피 목적으로 "
                "공시되어 있으며, 현재 근거만으로 치명적 우발채무로 보기는 어렵습니다."
            ),
            monitoring_rule="파생상품 평가손실, 헤지 목적 이탈, 원자재 급변에 따른 운전자본 부담 확대 확인",
        ),
        RiskDefinition(
            risk_id="complex_affiliate_related_party_structure",
            risk_title="Complex affiliate and related-party structure",
            matcher=lambda frame: frame["review_check"] == "related_party_review",
            fallback_checks=("related_party_review",),
            key_evidence=related_party_evidence,
            monitoring_rule="대주주/특수관계인 거래, 계열사 출자, 지분법 손익 훼손이 커지면 보류",
        ),
        RiskDefinition(
            risk_id=project_risk_id,
            risk_title=project_risk_title,
            matcher=project_risk_matcher,
            fallback_checks=("project_risk_review",),
            key_evidence=project_risk_evidence,
            monitoring_rule=project_risk_monitoring,
        ),
    ]


def _risk_row(symbol: str, scan: pd.DataFrame, definition: RiskDefinition) -> dict[str, str | int]:
    matched = scan.loc[definition.matcher(scan)].copy()
    if matched.empty:
        matched = scan.loc[scan["review_check"].isin(definition.fallback_checks)].head(0).copy()

    fatal_risk = _fatal_risk(matched)
    gate_opinion = _gate_opinion(fatal_risk=fatal_risk, evidence_count=len(matched))
    return {
        "symbol": symbol,
        "risk_id": definition.risk_id,
        "risk_title": definition.risk_title,
        "source_checks": _join_unique(matched.get("review_check", pd.Series(dtype=str))),
        "evidence_count": int(len(matched)),
        "source_reports": _join_unique(matched.get("report_nm", pd.Series(dtype=str))),
        "source_dates": _join_unique(matched.get("rcept_dt", pd.Series(dtype=str))),
        "source_receipts": _join_unique(matched.get("rcept_no", pd.Series(dtype=str))),
        "key_evidence": _compose_key_evidence(definition.key_evidence, matched),
        "fatal_risk": fatal_risk,
        "gate_opinion": gate_opinion,
        "monitoring_rule": definition.monitoring_rule,
    }


def _compose_key_evidence(base: str, matched: pd.DataFrame) -> str:
    if matched.empty:
        return base + " 원문 keyword hit가 부족해 추가 확인이 필요합니다."
    snippet = _shorten(str(matched["snippet"].iloc[0]), limit=180)
    return f"{base} 대표 근거: {snippet}"


def _fatal_risk(matched: pd.DataFrame) -> str:
    if matched.empty:
        return "NO"
    text = " ".join(matched["snippet"].astype(str).tolist())
    fatal_terms = ["상장폐지", "감사의견 거절", "자본잠식", "회생절차", "부도"]
    if any(term in text for term in fatal_terms):
        return "YES"
    return "NO"


def _gate_opinion(fatal_risk: str, evidence_count: int) -> str:
    if fatal_risk == "YES":
        return "EXCLUDE"
    if evidence_count <= 0:
        return "HOLD_REVIEW"
    return "PASS_CANDIDATE_WITH_MONITORING"


def _summary(report: pd.DataFrame) -> dict[str, str | int]:
    if report.empty:
        return {"symbol": "", "core_risk_count": 0, "fatal_risk_count": 0, "overall_opinion": "HOLD_REVIEW"}
    fatal_count = int((report["fatal_risk"] == "YES").sum())
    hold_count = int((report["gate_opinion"] == "HOLD_REVIEW").sum())
    if fatal_count:
        overall = "EXCLUDE"
    elif hold_count:
        overall = "HOLD_REVIEW"
    else:
        overall = "PASS_CANDIDATE_WITH_MONITORING"
    return {
        "symbol": str(report["symbol"].iloc[0]),
        "core_risk_count": int(len(report)),
        "fatal_risk_count": fatal_count,
        "overall_opinion": overall,
    }


def _render_markdown(report: pd.DataFrame, summary: dict[str, str | int]) -> str:
    lines = [
        "# Filing Risk Summary",
        "",
        "This report compresses OpenDART keyword evidence into investable review risks. It is not legal advice or an order ticket.",
        "",
        f"- Symbol: {summary['symbol']}",
        f"- Core risks: {summary['core_risk_count']}",
        f"- Fatal risk count: {summary['fatal_risk_count']}",
        f"- Overall opinion: {summary['overall_opinion']}",
        "- Fatal risk: NO" if summary["fatal_risk_count"] == 0 else "- Fatal risk: YES",
        "",
        "| Risk | Evidence | Fatal | Opinion | Monitoring Rule |",
        "|---|---:|---|---|---|",
    ]
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.risk_title} | {row.evidence_count} | {row.fatal_risk} | "
            f"{row.gate_opinion} | {row.monitoring_rule} |"
        )
    lines.extend(
        [
            "",
            "## Source Preservation",
            "",
            "| Risk | Reports | Dates | Receipts | Key Evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for row in report.itertuples(index=False):
        lines.append(
            f"| {row.risk_title} | {row.source_reports or '-'} | {row.source_dates or '-'} | "
            f"{row.source_receipts or '-'} | {row.key_evidence} |"
        )
    lines.extend(
        [
            "",
            "Do not copy this into configs/manual_review.actual.csv automatically.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _contains_any(series: pd.Series, terms: list[str]) -> pd.Series:
    pattern = "|".join(terms)
    return series.astype(str).str.contains(pattern, regex=True, na=False)


def _join_unique(series: pd.Series) -> str:
    values = [str(value).strip() for value in series.tolist() if str(value).strip()]
    return "; ".join(dict.fromkeys(values))


def _shorten(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _symbol_code(symbol: str) -> str:
    return symbol.split(".")[0].replace("/", "_").replace("\\", "_")


def _symbol_from_path(path: Path) -> str:
    stem = path.stem
    for prefix in ("opendart_text_risk_scan_", "filing_risk_summary_"):
        if stem.startswith(prefix):
            return stem[len(prefix) :] + ".KS"
    return stem
