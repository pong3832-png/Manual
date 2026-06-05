# CLI Next Session Prompt

다음에 Codex CLI 또는 Claude CLI를 새로 열면 아래 프롬프트를 그대로 복붙해서 시작하세요.

```text
AGENTS.md와 docs/work-log.md가 있으면 먼저 읽고, 현재 git status만 확인해서 이어서 작업해줘.

전체 폴더 재분석은 하지 말고, 오늘 목표에 필요한 파일만 열어.
수정 전에는 어떤 파일을 볼지 짧게 말하고 진행해.
관련 없는 파일이나 사용자 작업물은 건드리지 마.
발행, 배포, 삭제, 스케줄러 등록, 외부 API 대량 호출은 내가 명시적으로 승인하기 전에는 실행하지 마.

오늘 작업 목표:
[
  1. 다음 P0 프로그램은 compliance_pretrade_gate로 진행
     - 근거:
       - reports/institutional_program_stack/institutional_program_stack.md에서 P0 1순위가 COMPLIANCE_PRETRADE_GATE
       - 목적은 매수 허가가 아니라, 모든 매수 전 차단 조건을 한 장으로 합쳐 보여주는 최종 안전 게이트

  2. 먼저 필요한 파일만 확인
     - AGENTS.md
     - docs/work-log.md
     - git status --short -- .
     - reports/institutional_program_stack/institutional_program_stack.md
     - reports/pre_buy_decision/pre_buy_decision.csv
     - reports/decision_gate/decision_gate.csv
     - reports/decision_gate/manual_review_draft.csv
     - reports/decision_gate/manual_review_proposal.csv
     - reports/market_regime/market_regime.csv
     - reports/valuation_data_quality/valuation_data_quality.csv
     - reports/panic_rebound_signal/panic_rebound_signal.csv
     - reports/tactical_watchlist/tactical_watchlist.csv
     - 필요한 경우에만 관련 기존 구현 파일:
       - src/quantum_trainer/pre_buy_decision.py
       - src/quantum_trainer/decision_gate.py
       - src/quantum_trainer/valuation_data_quality.py
       - scripts/run_pre_buy_decision.py

  3. 구현할 새 프로그램
     - 새 모듈: src/quantum_trainer/compliance_pretrade_gate.py
     - 새 CLI: scripts/run_compliance_pretrade_gate.py
     - 새 테스트: tests/test_compliance_pretrade_gate.py
     - 출력:
       - reports/compliance_pretrade_gate/compliance_pretrade_gate.csv
       - reports/compliance_pretrade_gate/compliance_pretrade_gate.md
       - reports/compliance_pretrade_gate/compliance_pretrade_gate_summary.csv

  4. compliance_pretrade_gate가 합칠 게이트
     - market_gate: market/sector RISK_OFF, DEFENSIVE, RECOVERY_WATCH, EXTENDED_UPTREND 여부
     - pre_buy_gate: pre-buy decision WAIT/REJECT/BUY_READY 여부와 blockers
     - manual_gate: decision_gate/manual_review 상태와 actual manual config 적용 여부
     - filing_gate: filing risk summary/HOLD_REVIEW/fatal risk/summary missing 여부
     - valuation_gate: valuation data required, premium review, UNKNOWN 여부
     - rebound_gate: panic_rebound_signal의 READY_REBOUND_REVIEW/CHASE_RISK/WAIT_CONFIRMATION 여부
     - tactical_gate: tactical_watchlist의 READY_MANUAL_REVIEW/PULLBACK_WATCH/MARKET_DEFENSIVE_WAIT 여부
     - order_gate: order_status가 항상 NO_ORDER인지 확인

  5. 출력 컬럼 후보
     - symbol
     - company_name
     - final_compliance_status: BLOCK / WAIT_EVIDENCE / READY_FOR_HUMAN_REVIEW
     - primary_blocker
     - blocker_count
     - market_gate
     - pre_buy_gate
     - manual_gate
     - filing_gate
     - valuation_gate
     - rebound_gate
     - tactical_gate
     - required_next_evidence
     - action_summary
     - external_api_requested
     - order_status
     - broker_order_requested

  6. 판정 원칙
     - 어떤 치명/차단 조건이라도 있으면 BLOCK
     - 증거 부족이면 WAIT_EVIDENCE
     - 모든 로컬 게이트가 통과해도 READY_FOR_HUMAN_REVIEW까지만 표시
     - BUY_READY, READY_REBOUND_REVIEW, READY_MANUAL_REVIEW는 실제 주문 허가가 아님
     - 실제 주문/증권사 API/브라우저 자동 주문은 절대 추가하지 않기

  7. TDD로 진행
     - 먼저 tests/test_compliance_pretrade_gate.py에 실패 테스트 작성
     - 테스트 케이스:
       - 시장 RISK_OFF면 BLOCK
       - filing HOLD_REVIEW면 WAIT_EVIDENCE 또는 BLOCK
       - valuation UNKNOWN이면 WAIT_EVIDENCE
       - 모든 게이트가 로컬 PASS 후보여도 READY_FOR_HUMAN_REVIEW + NO_ORDER
       - 입력 파일이 없으면 DATA_REQUIRED/WAIT_EVIDENCE로 처리하고 외부 API 호출하지 않음
       - 모든 출력은 external_api_requested=NO, order_status=NO_ORDER, broker_order_requested=NO
     - 실패 확인 후 최소 구현
     - 통과 후 실제 로컬 리포트 생성

  8. 금지
     - 외부 API, OpenDART, 가격 갱신 실행 금지
     - configs/manual_review.actual.csv 수정 금지
     - 브로커/주문/API/자동 클릭/스케줄러 추가 금지
     - 기존 사용자 작업물이나 unrelated 파일 수정 금지

  9. 검증
     - .\.venv\Scripts\python.exe -m pytest .\tests\test_compliance_pretrade_gate.py -q
     - .\.venv\Scripts\python.exe -m py_compile .\src\quantum_trainer\compliance_pretrade_gate.py .\scripts\run_compliance_pretrade_gate.py
     - .\.venv\Scripts\python.exe .\scripts\run_compliance_pretrade_gate.py
     - git diff --check -- .
     - git status --short -- .

  10. 작업 후 기록
      - 의미 있는 변경이면 docs/work-log.md에 변경/검증/다음 작업을 짧게 기록
      - 새 안전 규칙이 생기면 AGENTS.md에 최소 추가
]

전략/퀀트/논문/학습 관련 작업이면 먼저 필요한 범위만 아래 파일에서 확인해줘.
- 공개 리서치 백로그 원본: configs/strategy_research_backlog.seed.csv
- 공개 리서치 백로그 리포트: reports/strategy_research_backlog/strategy_research_backlog.md
- 백로그 생성 스크립트: scripts/run_strategy_research_backlog.py
- 백로그 구현 모듈: src/quantum_trainer/strategy_research_backlog.py
- 전략 학습 시스템 문서: docs/strategy-learning-system.md
- 예측 학습 피드백 요약: reports/learning_feedback/learning_feedback_summary.csv
- 예측 스냅샷/실현 오차: reports/learning_feedback/alpha_prediction_snapshots.csv, reports/learning_feedback/alpha_prediction_outcomes.csv
- 학습 피드백 스크립트: scripts/run_learning_feedback.py
- 학습 피드백 구현 모듈: src/quantum_trainer/learning_feedback.py
- 급락 후 반등 감시 리포트: reports/panic_rebound_signal/panic_rebound_signal.md
- 급락 후 반등 감시 CSV: reports/panic_rebound_signal/panic_rebound_signal.csv
- 급락 후 반등 감시 스크립트: scripts/run_panic_rebound_signal.py
- 급락 후 반등 감시 구현 모듈: src/quantum_trainer/panic_rebound_signal.py
- 기관형 프로그램 스택 원본: configs/institutional_program_stack.seed.csv
- 기관형 프로그램 스택 리포트: reports/institutional_program_stack/institutional_program_stack.md
- 기관형 프로그램 스택 CSV: reports/institutional_program_stack/institutional_program_stack.csv
- 기관형 프로그램 스택 스크립트: scripts/run_institutional_program_stack.py
- 기관형 프로그램 스택 구현 모듈: src/quantum_trainer/institutional_program_stack.py

주의:
- 백로그는 매수 목록이나 모델 정책이 아니라 구현 후보 목록이야.
- READY_REBOUND_REVIEW는 매수 신호가 아니라 수급/공시/시장/수동 게이트를 더 확인할 감시 라벨이야.
- 기관형 프로그램 스택은 공개 기능 범주를 우리 로컬 모듈 후보로 매핑한 것이지, 상용/헤지펀드 시스템 복제나 주문 실행 계획이 아니야.
- reports/와 일부 docs/configs 파일은 .gitignore 때문에 git status에 안 보일 수 있으니, 필요한 경우 Test-Path로 존재 여부만 확인해.
- 외부 API, OpenDART, 가격 갱신, ML 라이브러리 설치, 주문 실행은 내가 명시적으로 승인하기 전에는 하지 마.
- 모든 산출물은 external_api_requested=NO, order_status=NO_ORDER, broker_order_requested=NO를 유지해.

작업 방식:
- 먼저 현재 상태를 5줄 이내로 요약해줘.
- 필요한 파일만 읽어.
- 수정 후에는 가능한 가장 작은 검증 명령을 실행해.
- 검증 결과와 변경 파일을 마지막에 요약해줘.
```

작업이 끝나면 아래 프롬프트를 복붙하세요.

```text
오늘 변경사항, 검증 결과, 다음 세션에서 이어갈 작업을 docs/work-log.md에 짧게 정리해줘.
새로 생긴 운영 규칙이나 주의사항이 있으면 AGENTS.md에도 반영해줘.
불필요한 장문 요약은 하지 말고, 다음 CLI 세션이 바로 이어서 작업할 수 있게 핵심만 남겨줘.
```

AGENTS.md가 아직 없다면 먼저 아래 프롬프트를 사용하세요.

```text
이 저장소를 분석해서 AGENTS.md를 만들어줘.
다음 CLI 세션에서 AI가 이 파일만 읽고도 안전하게 작업을 이어갈 수 있게 작성해.

포함할 내용:
- 프로젝트 목적
- 주요 폴더와 핵심 파일
- 실행 명령
- 검증 명령
- 환경변수 이름과 용도
- 데이터/로그/세션 파일 위치
- 절대 하면 안 되는 작업
- 사용자 승인 없이 실행하면 안 되는 명령
- 자주 깨지는 부분
- 다음 작업자가 먼저 확인할 파일

규칙:
- 실제 파일을 확인하고 작성해.
- 비밀키 값은 절대 쓰지 말고 변수명만 적어.
- 발행, 배포, 삭제, 외부 API 호출은 위험 작업으로 분리해.
- 문서는 한국어로 작성하고 명령어와 경로는 원문 그대로 유지해.
```
