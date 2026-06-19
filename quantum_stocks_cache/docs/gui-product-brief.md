# Quant Stock Program GUI Product Brief

## 1. Purpose

This document describes the current GUI shape of the local quant stock program and proposes the next product direction for team review.

The GUI is a local-only review tool. It helps the operator:

- Search a stock by name or code.
- Run quick cached analysis for a single stock.
- Review today's candidate board.
- Review current holdings and defensive risk levels.
- Open the generated dashboard.

The GUI must not place orders, connect to a broker, auto-click a trading app, or imply execution permission. Every output remains review-only with `order_status=NO_ORDER`.

## 2. Current Implementation

### Frontend

- Path: `web/src/main.jsx`
- Style: `web/src/styles.css`
- Build tool: Vite + React
- Build command: `npm.cmd run build`
- Dev command: `npm.cmd run dev`

The frontend is a single-page React app. It renders:

- Overall operating status
- Stock search and analysis form
- Analysis progress state
- Candidate board
- Holding defense board
- Summary metrics and safety notices

### Backend

- Path: `src/quantum_trainer/web_api.py`
- Run script: `scripts/run_web_app.py`
- Default URL: `http://127.0.0.1:8766`

The backend is a FastAPI app. It serves the built React app from `web/dist` and exposes local APIs.

Main APIs:

| API | Method | Purpose |
|---|---|---|
| `/api/status` | GET | Reads local reports and returns current operating summary. |
| `/api/search?q=` | GET | Searches local stock universe and aliases. No external lookup. |
| `/api/candidates?limit=12` | GET | Builds today's local candidate board. |
| `/api/holdings` | GET | Builds holding defense board from user-provided holdings. |
| `/api/holdings` | POST | Saves local holding watch inputs. |
| `/api/analyze/jobs` | POST | Starts background analysis job. |
| `/api/analyze/jobs/{job_id}` | GET | Polls analysis progress/result. |
| `/dashboard` | GET | Opens generated HTML dashboard if available. |
| `/health` | GET | Health check. |

## 3. Current User Flow

1. User starts the GUI:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\run_web_app.py
   ```

2. User opens:

   ```text
   http://127.0.0.1:8766/
   ```

3. User searches a stock by Korean name or code.

4. User starts analysis.

5. If a stock is provided, the backend uses quick single-stock analysis:

   - Uses cached `data/prices.csv`.
   - Skips full-universe market refresh.
   - Skips full 2,657-symbol pipeline regeneration.
   - Writes symbol-specific analysis under `reports/symbol_analysis/`.
   - Refreshes the dashboard.
   - Keeps `external_api_requested=NO`.
   - Keeps `order_status=NO_ORDER`.

6. User reviews:

   - Candidate score and status
   - Entry range
   - Trend/chase risk
   - Market and sector gate
   - Holding risk status
   - Generated dashboard detail link

## 4. Current Screen Shape

The UI currently behaves like an operator board rather than a consumer trading app.

Primary sections:

| Section | Current Role |
|---|---|
| Header/status | Shows latest local operating state and safety notice. |
| Stock analysis form | Input, search suggestions, refresh option, run button. |
| Progress notice | Shows queued/running/done/error state for background analysis. |
| Holding defense board | Shows entry price, latest price, unrealized return, stop levels, and review labels. |
| Candidate board | Shows today candidate rows, score/status, entry range, blockers, and market gate. |
| Dashboard link | Opens generated static dashboard report. |

## 5. Strengths

- Local-first and safe by design.
- Avoids broker/order integration.
- Single-stock quick analysis reduces waiting time.
- Candidate and holding boards are visible in one place.
- Uses existing local reports instead of duplicating quant logic in the frontend.
- Background jobs prevent the UI from looking frozen during analysis.

## 6. Current Pain Points

### 6.1 User Trust And Clarity

The user still needs clearer answers to:

- Is this stock already too high?
- Is this a new buy, pullback wait, or holding review?
- What price should I watch?
- What changed after analysis finished?

### 6.2 Progress Feedback

The background job states exist, but the user experience can still feel vague when the process stays in `RUNNING`.

Needed improvement:

- Show current stage text.
- Show elapsed time.
- Show whether it is quick stock mode or full daily mode.
- Show whether external refresh is being requested.

### 6.3 Korean Text Encoding And Labels

Some report-derived Korean labels appear garbled in older generated documents and UI text.

Needed improvement:

- Normalize UI-facing labels inside frontend/backend mapping.
- Avoid showing raw internal enum text without translation.
- Keep report files machine-readable but render user-facing text cleanly.

### 6.4 Decision Explanation

The program has many separate reports. The UI should turn them into a short decision sentence.

Example:

```text
네패스는 점수는 높지만 20일선 대비 12.4% 위라 추격보다 눌림 대기입니다.
```

## 7. Proposed Next Version

### 7.1 First Screen Goal

The first screen should answer three questions within 10 seconds:

1. What should I check first today?
2. Is my holding safe to continue holding?
3. If I type a stock, should I buy now, wait for pullback, or avoid?

### 7.2 Recommended Layout

Top to bottom:

1. Market posture bar

   - Market regime
   - Sector posture
   - Latest price date
   - External data status
   - `NO_ORDER` safety flag

2. Stock quick analysis panel

   - Search input
   - Selected stock chip
   - Quick/cached mode indicator
   - Run analysis button
   - Progress stage and elapsed time

3. One-line decision card

   - `BUY_REVIEW`, `WAIT_PULLBACK`, `HOLD_REVIEW`, `AVOID_FOR_NOW`
   - Main reason
   - Watch price
   - Invalid condition

4. Holding defense board

   - Each holding with current return, trend, stop level, next review trigger
   - Summary of risk-review count

5. Candidate board

   - Ranked rows
   - Score
   - Upside probability
   - Entry range
   - Chase risk
   - Market/sector gate

6. Detail drawer

   - Opens when a stock is clicked
   - Shows quant score, trend, event, market gate, pre-buy blockers, and source report links

### 7.3 Suggested UI States

| State | Meaning | User Text |
|---|---|---|
| `QUICK_STOCK` | Single stock cached analysis | 빠른 종목 분석 |
| `FULL_DAILY` | Full local daily pipeline | 전체 후보 갱신 |
| `WAIT_PULLBACK` | Good theme but price stretched | 눌림 대기 |
| `MARKET_WAIT` | Stock is okay but market/sector gate blocks entry | 시장 확인 대기 |
| `HOLD_REVIEW` | Existing holding can be watched | 보유 점검 |
| `REDUCE_REVIEW` | Risk/profit protection review | 일부 축소 검토 |
| `AVOID_FOR_NOW` | Weak or overextended | 지금은 제외 |

## 8. Decision Logic To Surface

The UI should show a compact decision summary built from existing fields.

Recommended inputs:

- `research_score`
- `conviction_score`
- `expected_20d_return`
- `upside_probability`
- `ma20_gap`
- `trend_regime`
- `forecast_bias`
- `chase_risk`
- `market_regime_status`
- `sector_regime_status`
- `entry_price_low`
- `entry_price_high`
- `readiness_blockers`

Recommended output fields:

| Field | Example |
|---|---|
| `decision_label` | 눌림 대기 |
| `decision_sentence` | 점수는 높지만 20일선 대비 과열이라 추격보다 눌림 확인이 유리합니다. |
| `watch_price` | 34,000~36,500 |
| `risk_line` | 20일선 이탈 또는 확신점수 60 미만이면 재검토 |
| `source_flags` | `NO_ORDER`, `external_api_requested=NO` |

## 9. Safety Requirements

Non-negotiable rules:

- No broker API.
- No order button.
- No auto-buy or auto-sell.
- No scheduler registration from the GUI.
- No bulk external API refresh unless the user explicitly approves it.
- All decision labels are review labels only.
- Every API response must include `order_status=NO_ORDER` where relevant.

## 10. Discussion Points For Team

1. Should the first screen prioritize holdings or new candidates?
2. Should quick analysis always use cached prices, or should there be a clearly approved live-refresh path?
3. What is the minimum decision sentence the user needs before acting manually?
4. Should we add a stock detail drawer or a separate detail page?
5. Should the candidate board rank by conviction score, event-adjusted score, or entry-readiness score?
6. Should holding defense have a separate "profit protection" rule after a position is already up 10% or more?
7. Should we add a local job history panel so the user can see the last analysis result without rerunning?

## 11. Suggested Development Backlog

Priority 1:

- Add stage-level progress text to analysis jobs.
- Add one-line decision card after quick stock analysis.
- Add clean Korean label mapping for internal statuses.
- Add elapsed time and analysis mode display.

Priority 2:

- Add stock detail drawer.
- Add source report links per candidate.
- Add holding-specific profit-protection rule display.
- Add local job history for the latest analyses.

Priority 3:

- Add comparison mode for two stocks.
- Add sector heatmap from existing local market-regime reports.
- Add configurable watch price alerts as local review notes only.

## 12. File Map

| File | Role |
|---|---|
| `web/src/main.jsx` | Main React UI and user interaction flow. |
| `web/src/styles.css` | Visual layout and styling. |
| `web/package.json` | Frontend scripts and dependencies. |
| `web/index.html` | Vite HTML entry. |
| `src/quantum_trainer/web_api.py` | FastAPI APIs and local report aggregation. |
| `scripts/run_web_app.py` | Local GUI server entrypoint. |
| `src/quantum_trainer/dashboard.py` | Generated static dashboard report. |
| `reports/dashboard/index.html` | Generated dashboard output. |

## 13. Open Risks

- Some labels come from report files and may still be hard to read without translation.
- Cached prices can be stale if the user assumes real-time data.
- Full daily analysis can still take longer than quick stock analysis.
- Strong event candidates can be overextended; UI must not overstate confidence.
- Existing dirty git state includes many unrelated changes, so implementation should stay tightly scoped.

## 14. Proposed Success Criteria

The next GUI version is successful if:

- A user can type a stock and get a clear review result within a short wait.
- The screen clearly distinguishes buy-review, wait, avoid, and holding-review states.
- The user always knows whether data is cached or refreshed.
- The user can see the key price range and invalidation rule without opening CSV files.
- No UI element can be mistaken for an actual order action.

