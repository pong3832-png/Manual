# Daily Operating Checklist

목적: 매일 같은 순서로 보고, 같은 금지선을 지키고, 같은 산출물만 갱신한다. 이 문서는 주문 지시서가 아니며 모든 기본 상태는 `NO_ORDER`다.

## 0. 시작 2분 체크

```powershell
git status --short -- .
Get-Content -Encoding UTF8 -LiteralPath .\docs\work-log.md -TotalCount 80
```

확인할 것:

- 오늘 작업 범위가 `quantum_stocks_cache` 안인지 확인한다.
- 직전 결론이 `WAIT / NO_ORDER`인지 확인한다.
- 작업 전부터 있던 변경 파일과 오늘 새로 만질 파일을 구분한다.
- 전체 폴더 재분석은 하지 않고, 목표 파일만 연다.

## 1. 안전 상태

반드시 유지:

- 주문 실행: `NO_ORDER`
- 브로커/API 주문: 없음
- `configs/manual_review.actual.csv`: 사용자 최종 승인 전 수정 금지
- 외부 API, OpenDART, 가격 갱신: 사용자 승인 전 실행 금지
- git add/commit/push/stash/reset/clean: 사용자 승인 전 실행 금지

즉시 멈추고 승인 요청:

- `run_today_pipeline.py --refresh-market-data`
- `fetch_opendart_*`
- `fetch_pykrx_universe.py`
- `update_market_data.py`
- `run_manual_review_apply_plan.py --confirm-final-review I_CONFIRM_MANUAL_REVIEW`
- 실제 자본 기반 주문 수량 확정, broker/order 기능, trade journal actual 입력

## 2. 오늘 1순위 후보 확인

먼저 볼 로컬 파일:

```text
reports/pre_buy_decision/pre_buy_decision.csv
reports/dashboard/index.html
reports/decision_gate/manual_review_proposal.csv
reports/event_adjusted_ranking/event_adjusted_ranking.csv
```

현재 기준 코미코 상태:

```text
symbol = 183300.KQ
company = 코미코
filing_review = PASS 후보
valuation_review = UNKNOWN
manual_proposal_status = INCOMPLETE_DRAFT
decision = WAIT
order_status = NO_ORDER
```

해석:

- 코미코가 1순위 후보여도 바로 매수하지 않는다.
- `WAIT_PULLBACK`은 추격 금지 신호다.
- `valuation_review=UNKNOWN`이 해소되기 전까지 실제 매수 준비 상태가 아니다.

## 3. 증거 게이트 순서

항상 이 순서로 본다:

1. `filing_review`: 치명 공시 리스크, HOLD_REVIEW 원인, 수동 해소 여부
2. `earnings_review`: 실적 개선 근거, 마진 훼손, 다음 실적 확인 필요성
3. `business_driver_review`: 사업 촉매가 실제 매출/이익으로 이어지는지
4. `valuation_review`: PER/PBR/ROE/부채비율/시가총액
5. `loss_rule_review`: SMA20, -7%, -10%, conviction 60 미만
6. `capital_plan_review`: 첫 tranche 30%, 추가 30%, 최종 40%

PASS로 올릴 수 없는 경우:

- 공식/로컬 근거가 부족한 경우
- 프리미엄 PER/PBR인데 실적 정당화 근거가 약한 경우
- 공시 요약이 없거나 `HOLD_REVIEW`가 남은 경우
- manual proposal만 있고 actual config가 적용되지 않은 경우

## 4. 비교 후보 확인

현재 비교 후보:

```text
085910.KQ 네오티스
331920.KQ 셀레믹스
087010.KQ 펩트론
083450.KQ GST
006260.KS LS
064400.KS LG CNS
```

비교 기준:

- 정량 점수와 기대수익률
- 추격위험
- PER/PBR/ROE
- 공시 리스크
- 이벤트 촉매
- 코미코 대비 사업 thesis 일관성

현재 판단:

- 네오티스: 공시는 PASS 후보지만 코미코보다 thesis/정량 우위가 약함
- 셀레믹스/펩트론: `HOLD_REVIEW`가 남아 후순위
- GST/LS: 현재 risk review 또는 low priority
- LG CNS: 이벤트는 강해도 이격이 커서 `WAIT_PULLBACK`

## 5. 산출물 갱신 순서

증거를 바꾼 뒤에만 아래 순서로 로컬 보고서를 갱신한다.

```powershell
.\.venv\Scripts\python.exe .\scripts\run_manual_review_draft.py
.\.venv\Scripts\python.exe .\scripts\run_manual_review_proposal.py
.\.venv\Scripts\python.exe .\scripts\run_pre_buy_decision.py
.\.venv\Scripts\python.exe .\scripts\run_dashboard.py --reports-dir .\reports
```

기대 결과:

```text
actual_config_written=NO
top_symbol=183300.KQ
decision_gate_status=WAITING_MANUAL_EVIDENCE
order_status=NO_ORDER
```

## 6. 완료 전 검증

문서만 바꿨을 때:

```powershell
rg "NO_ORDER|WAIT / NO_ORDER|actual_config_written=NO" .\docs .\reports\pre_buy_decision .\reports\decision_gate
```

코드나 테스트를 바꿨을 때:

```powershell
.\.venv\Scripts\python.exe -m pytest .\tests\test_pre_buy_decision.py .\tests\test_manual_review_draft.py .\tests\test_dashboard.py -q
.\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\pre_buy_decision.py .\src\quantum_trainer\manual_review_draft.py
```

대시보드 갱신 후:

```powershell
rg "코미코|183300\.KQ|자동 주문 없음|눌림 대기" .\reports\dashboard\index.html
```

## 7. work-log 기록 형식

의미 있는 변경을 했다면 `docs/work-log.md` 맨 위에 짧게 남긴다.

```text
## YYYY-MM-DD - Short Title

- Changed:
  - file/path
- Result:
  - current decision
  - order_status
- Verification:
  - command -> result
- Next:
  - next blocker or approval needed
```

## 8. 오늘 멈춤 조건

아래 중 하나라도 있으면 실제 매수 관련 판단을 멈춘다.

- `valuation_review=UNKNOWN`
- `filing_review=UNKNOWN` 또는 `HOLD_REVIEW`
- `manual_proposal_status=INCOMPLETE_DRAFT`
- `decision_gate_status`가 `READY_FOR_SIZING_REVIEW`가 아님
- `order_status`가 `NO_ORDER`가 아닌 산출물이 생김
- 외부 데이터 최신성이 판단을 좌우하지만 승인받지 않음
- 사용자가 실제 자본/계좌 상태를 제공하지 않음

현재 결론: 코미코는 1순위 후보지만 `WAIT / NO_ORDER`다.
