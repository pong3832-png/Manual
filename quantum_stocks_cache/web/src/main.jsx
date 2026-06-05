import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  Gauge,
  ListChecks,
  Play,
  RefreshCw,
  Save,
  ShieldAlert,
  ShieldCheck,
  Target
} from 'lucide-react';
import './styles.css';

const statusKo = {
  DONE: '완료',
  NOT_DONE: '준비 중',
  BUY_READY: '매수 검토 가능',
  WAIT: '기다림',
  REJECT: '제외',
  CORE_FOCUS: '핵심 후보',
  WAIT_RISK: '위험 확인',
  PRICE_COVERAGE_READY: '가격 데이터 준비',
  PASS_CANDIDATE: '통과 후보',
  NO_ORDER: '자동 주문 없음',
  NO_TRADE_JOURNAL: '매수 기록 없음',
  WRITE_TRADE_JOURNAL_AFTER_BUY: '매수 후 기록 필요',
  DATA_REQUIRED: '데이터 필요',
  SELL_REVIEW: '매도 검토',
  REDUCE_REVIEW: '비중 축소 검토',
  HOLD_DEFENSIVE: '방어 보유',
  HOLD_REVIEW: '보유 검토',
  LOW_PRIORITY: '낮은 우선순위',
  DOWNTREND: '하락 추세',
  PULLBACK_UPTREND: '상승 중 눌림',
  BEARISH: '약세',
  WATCH_REBOUND: '반등 확인',
  WATCH_PULLBACK: '눌림 대기',
  RISK_OFF: '위험 회피',
  DEFENSIVE: '방어',
  NO_HOLDINGS: '보유 없음',
  ANALYSIS_READY: '분석 가능',
  RESEARCH_CANDIDATE: '연구 후보',
  PRICE_DATA_REQUIRED: '가격 데이터 필요',
  READY: '준비됨',
  MISSING: '데이터 없음',
  QUEUED: '대기 중',
  RUNNING: '실행 중',
  ERROR: '오류'
};

function ko(value) {
  if (!value) return '확인 필요';
  return statusKo[value] || value;
}

function App() {
  const [status, setStatus] = useState(null);
  const [candidateBoard, setCandidateBoard] = useState(null);
  const [holdingBoard, setHoldingBoard] = useState(null);
  const [symbolAnalysis, setSymbolAnalysis] = useState(null);
  const [stockDetail, setStockDetail] = useState(null);
  const [holdingDrafts, setHoldingDrafts] = useState({});
  const [tradeDraft, setTradeDraft] = useState({
    stock: '',
    side: 'BUY',
    price: '',
    quantity: '',
    notes: ''
  });
  const [stock, setStock] = useState('');
  const [refreshMarketData, setRefreshMarketData] = useState(true);
  const [running, setRunning] = useState(false);
  const [analysisJob, setAnalysisJob] = useState(null);
  const [autoRefreshStarted, setAutoRefreshStarted] = useState(false);
  const [savingHoldings, setSavingHoldings] = useState(false);
  const [savingTrade, setSavingTrade] = useState(false);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [loadingStockDetail, setLoadingStockDetail] = useState(false);
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [resultLines, setResultLines] = useState([]);
  const [error, setError] = useState('');
  const [holdingSaveMessage, setHoldingSaveMessage] = useState('');
  const [tradeMessage, setTradeMessage] = useState('');

  async function loadStatus() {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('상태를 불러오지 못했습니다.');
    setStatus(await response.json());
  }

  async function loadCandidates() {
    setLoadingCandidates(true);
    try {
      const response = await fetch('/api/candidates?limit=12');
      if (!response.ok) throw new Error('후보 보드를 불러오지 못했습니다.');
      setCandidateBoard(await response.json());
    } finally {
      setLoadingCandidates(false);
    }
  }

  async function loadHoldings() {
    setLoadingHoldings(true);
    try {
      const response = await fetch('/api/holdings');
      if (!response.ok) throw new Error('보유종목 보드를 불러오지 못했습니다.');
      const body = await response.json();
      setHoldingBoard(body);
      setHoldingDrafts(makeHoldingDrafts(body.holdings || []));
    } finally {
      setLoadingHoldings(false);
    }
  }

  async function loadSymbolAnalysis(stockText) {
    const keyword = stockText?.trim();
    if (!keyword) {
      setSymbolAnalysis(null);
      return null;
    }
    const response = await fetch(`/api/symbol-analysis?stock=${encodeURIComponent(keyword)}`);
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || '검색 종목 분석을 불러오지 못했습니다.');
    setSymbolAnalysis(body);
    return body;
  }

  async function loadStockDetail(stockText) {
    const keyword = stockText?.trim();
    if (!keyword) {
      setStockDetail(null);
      return null;
    }
    setLoadingStockDetail(true);
    try {
      const response = await fetch(`/api/stock-detail?stock=${encodeURIComponent(keyword)}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '종목 상세 정보를 불러오지 못했습니다.');
      setStockDetail(body);
      return body;
    } finally {
      setLoadingStockDetail(false);
    }
  }

  async function saveHoldings() {
    setSavingHoldings(true);
    setError('');
    setHoldingSaveMessage('');
    try {
      const holdingsPayload = Object.values(holdingDrafts).map((item) => ({
        symbol: item.symbol,
        company_name: item.company_name,
        entry_price: numberOrZero(item.entry_price),
        quantity: numberOrNull(item.quantity),
        notes: item.notes || ''
      }));
      const response = await fetch('/api/holdings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ holdings: holdingsPayload })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '보유종목 저장에 실패했습니다.');
      setHoldingBoard(body);
      setHoldingDrafts(makeHoldingDrafts(body.holdings || []));
      setHoldingSaveMessage('저장됨');
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingHoldings(false);
    }
  }

  async function recordTrade(event) {
    event.preventDefault();
    setSavingTrade(true);
    setError('');
    setTradeMessage('');
    try {
      const response = await fetch('/api/trades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock: tradeDraft.stock.trim(),
          side: tradeDraft.side,
          price: numberOrZero(tradeDraft.price),
          quantity: numberOrZero(tradeDraft.quantity),
          notes: tradeDraft.notes || ''
        })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '체결 기록 저장에 실패했습니다.');
      setHoldingBoard(body);
      setHoldingDrafts(makeHoldingDrafts(body.holdings || []));
      setTradeMessage(`${tradeDraft.side === 'BUY' ? '매수' : '매도'} 반영됨`);
      setTradeDraft((current) => ({ ...current, price: '', quantity: '', notes: '' }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingTrade(false);
    }
  }

  function updateTradeDraft(field, value) {
    setTradeDraft((current) => ({
      ...current,
      [field]: value
    }));
  }

  function updateHoldingDraft(symbol, field, value) {
    setHoldingDrafts((current) => ({
      ...current,
      [symbol]: {
        ...current[symbol],
        [field]: value
      }
    }));
  }

  useEffect(() => {
    loadStatus().catch((err) => setError(err.message));
    loadCandidates().catch((err) => setError(err.message));
    loadHoldings().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (autoRefreshStarted || running) return;
    setAutoRefreshStarted(true);
    startAnalysis(null, true).catch((err) => setError(err.message));
  }, [autoRefreshStarted, running]);

  useEffect(() => {
    const keyword = stock.trim();
    if (!keyword) {
      setSuggestions([]);
      return undefined;
    }

    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(keyword)}`);
        const body = await response.json();
        if (response.ok) {
          setSuggestions(body.candidates || []);
        }
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 180);

    return () => window.clearTimeout(timer);
  }, [stock]);

  function selectCandidate(candidate) {
    setSelectedCandidate(candidate);
    setStock(candidate.company_name);
    setSuggestions([]);
    loadSymbolAnalysis(candidate.symbol).catch(() => {});
    loadStockDetail(candidate.symbol).catch((err) => setError(err.message));
  }

  function openStockDetail(symbol) {
    if (!symbol) return;
    setStock(symbol);
    setSuggestions([]);
    loadStockDetail(symbol).catch((err) => setError(err.message));
    loadSymbolAnalysis(symbol).catch(() => {});
  }

  async function runAnalysis(event) {
    event.preventDefault();
    const requestedStock = selectedCandidate?.symbol || stock.trim() || null;
    await startAnalysis(requestedStock, refreshMarketData);
  }

  async function startAnalysis(requestedStock, shouldRefreshMarketData) {
    setRunning(true);
    setError('');
    setResultLines([]);
    setAnalysisJob(null);
    try {
      const response = await fetch('/api/analyze/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock: requestedStock,
          refresh_market_data: shouldRefreshMarketData,
          cache_market_data: !shouldRefreshMarketData
        })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '분석 작업 생성에 실패했습니다.');
      setAnalysisJob(body);
      await pollAnalysisJob(body.job_id, requestedStock);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  async function pollAnalysisJob(jobId, requestedStock) {
    let current = null;
    for (let attempt = 0; attempt < 240; attempt += 1) {
      const response = await fetch(`/api/analyze/jobs/${jobId}`);
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '분석 작업 상태 확인에 실패했습니다.');
      current = body;
      setAnalysisJob(body);
      if (body.status === 'DONE') {
        setResultLines(body.lines || []);
        if (body.app_status) setStatus(body.app_status);
        await loadCandidates();
        await loadHoldings();
        if (requestedStock) {
          await loadSymbolAnalysis(requestedStock);
          await loadStockDetail(requestedStock);
        }
        return body;
      }
      if (body.status === 'ERROR') {
        throw new Error(body.error || '분석 작업이 실패했습니다.');
      }
      await delay(2000);
    }
    throw new Error(`${analysisStatusText(current)}. 분석 작업이 오래 걸립니다.`);
  }

  const candidate = status?.top_candidate || {};
  const universe = status?.universe || {};
  const tracking = status?.tracking || {};
  const latest = status?.latest_price_date || '-';
  const boardCandidates = candidateBoard?.candidates || [];
  const searchedAnalysis = symbolAnalysis?.analysis || {};
  const detailProfile = stockDetail?.profile || {};
  const detailQuant = stockDetail?.quant || {};
  const investorFlow = stockDetail?.investor_flow || {};
  const holdings = holdingBoard?.holdings || [];
  const holdingSummary = holdingBoard?.summary || {};
  const market = candidateBoard?.market || {};
  const candidateTower = candidateBoard?.control_tower || {};
  const holdingTower = holdingBoard?.control_tower || {};
  const leadCandidate = boardCandidates[0] || {};
  const leadDecision = leadCandidate.decision_summary || {};
  const conclusion = useMemo(() => {
    if (!status) return '상태 확인 중';
    if (candidate.decision === 'BUY_READY') return `${candidate.company_name || '후보'} 매수 검토 가능`;
    if (candidate.decision === 'WAIT') return `${candidate.company_name || '후보'} 대기`;
    return ko(candidate.decision);
  }, [status, candidate]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>퀀트 트레이너</h1>
          <p>{running && !analysisJob?.stock ? '최신 후보 자동 갱신 중' : '오늘 후보와 막힌 이유'}</p>
        </div>
        <span className="safe-pill">
          <ShieldCheck size={16} />
          주문 실행 없음
        </span>
      </header>

      <div className="terminal-layout">
        <aside className="analysis-panel">
      <section className="command-band">
        <form onSubmit={runAnalysis} className="run-form">
          <label>
            <span>종목</span>
            <div className="stock-search">
              <input
                value={stock}
                onChange={(event) => {
                  setSelectedCandidate(null);
                  setStock(event.target.value);
                }}
                placeholder="삼성전자, 현대차, LG화학처럼 입력"
              />
              {selectedCandidate && (
                <span className="selected-stock">
                  {selectedCandidate.company_name} · {selectedCandidate.code}
                </span>
              )}
              {suggestions.length > 0 && (
                <div className="suggestions" role="listbox" aria-label="종목 검색 결과">
                  {suggestions.map((candidate) => (
                    <button
                      type="button"
                      key={candidate.symbol}
                      onClick={() => selectCandidate(candidate)}
                    >
                      <strong>{candidate.company_name}</strong>
                      <span>{candidate.code} · {candidate.market} · {candidate.sector}</span>
                    </button>
                  ))}
                </div>
              )}
              {searching && <span className="search-hint">검색 중...</span>}
            </div>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={refreshMarketData}
              onChange={(event) => setRefreshMarketData(event.target.checked)}
            />
            <span>최신 가격 갱신</span>
          </label>
          <button type="submit" disabled={running}>
            {running ? <RefreshCw size={18} className="spin" /> : <Play size={18} />}
            {analysisButtonLabel(running, analysisJob, refreshMarketData)}
          </button>
        </form>
      </section>

      {analysisJob && (
        <section className="notice progress">
          {analysisJob.status === 'DONE' ? <CheckCircle2 size={18} /> : <RefreshCw size={18} className={running ? 'spin' : ''} />}
          <span>{analysisStatusText(analysisJob)}</span>
          <span className="progress-meta">
            <Clock size={15} />
            {elapsedText(analysisJob)}
          </span>
        </section>
      )}

      {error && (
        <section className="notice error">
          <AlertTriangle size={18} />
          {error}
        </section>
      )}

      <section className="decision-grid">
        <article className="decision-panel">
          <span className="eyebrow">한 줄 운용 판단</span>
          <h2>{leadCandidate.company_name ? `${leadCandidate.company_name}: ${decisionLabelKo(leadDecision.label)}` : conclusion}</h2>
          <p>{leadDecision.reason || candidate.why_not_now || '대시보드에서 최종 검토하세요.'}</p>
          <div className="decision-facts">
            <span>감시가 {formatRange(leadDecision.watch_price_low, leadDecision.watch_price_high)}</span>
            <span>게이트 {ko(leadDecision.market_gate || leadCandidate.final_watch_status)}</span>
            <span>추격 {riskKo(leadDecision.chase_risk || leadCandidate.chase_risk)}</span>
          </div>
          {leadDecision.risk_line && (
            <div className="blocker-line compact">
              <ListChecks size={16} />
              <span>{leadDecision.risk_line}</span>
            </div>
          )}
          <div className="actions">
            <a href="/dashboard" target="_blank" rel="noreferrer">
              <BarChart3 size={18} />
              상세 대시보드
            </a>
            <a href="/api/status" target="_blank" rel="noreferrer">
              <ExternalLink size={18} />
              상태 API
            </a>
          </div>
        </article>
        <aside className="guard-panel">
          <strong>{ko(status?.order_status || 'NO_ORDER')}</strong>
          <span>증권앱에서 직접 확인</span>
        </aside>
      </section>

        </aside>
        <section className="main-canvas">
      <section className="control-tower">
        <article className="tower-main">
          <span className="eyebrow">운용 컨트롤 타워</span>
          <h2>{policyKo(candidateTower.market_entry_policy)}</h2>
          <p>{candidateTower.risk_note || '시장, 후보, 보유 리스크를 확인한 뒤 수동으로 판단합니다.'}</p>
        </article>
        <ControlTile
          icon={<Gauge size={18} />}
          label="시장 레짐"
          value={`${ko(market.regime_status)} / ${ko(market.risk_posture)}`}
        />
        <ControlTile
          icon={<Database size={18} />}
          label="데이터"
          value={`${candidateTower.data_status || 'CACHED_LOCAL'} · ${candidateTower.latest_price_date || latest}`}
        />
        <ControlTile
          icon={<Target size={18} />}
          label="후보 판단"
          value={`${candidateTower.candidate_count || boardCandidates.length}개 · ${candidateTower.wait_review_count || 0}개 대기`}
        />
        <ControlTile
          icon={<ShieldAlert size={18} />}
          label="보유 방어"
          value={`${defenseKo(holdingTower.portfolio_defense_posture)} · ${holdingTower.risk_review_count || 0}개 점검`}
        />
      </section>

      <section className="metric-grid">
        <Metric label="1순위 후보" value={`${candidate.company_name || '-'} ${candidate.symbol || ''}`} />
        <Metric label="판단" value={ko(candidate.decision)} />
        <Metric label="확신 점수" value={candidate.conviction_score ? `${candidate.conviction_score.toFixed(1)}점` : '-'} />
        <Metric label="가격 기준일" value={latest} />
        <Metric label="비교군" value={`${universe.universe_count || 0}개`} />
        <Metric label="가격 데이터" value={ko(universe.price_coverage_status)} />
        <Metric label="운영 상태" value={ko(status?.completion_status)} />
        <Metric label="성과 추적" value={ko(tracking.tracking_status)} />
      </section>

      <section className="rank-board">
        <div className="section-heading">
          <div>
            <span className="eyebrow">실시간 퀀트 랭킹</span>
            <h2>매수 검토 등수</h2>
          </div>
          <div className="market-strip">
            <span>{candidateBoard?.as_of || latest}</span>
            <span>{ko(candidateBoard?.order_status || 'NO_ORDER')}</span>
          </div>
        </div>
        {loadingCandidates && (
          <div className="candidate-empty">
            <RefreshCw size={18} className="spin" />
            퀀트 랭킹 계산 중
          </div>
        )}
        {!loadingCandidates && boardCandidates.length === 0 && (
          <div className="candidate-empty">랭킹 데이터 확인 필요</div>
        )}
        {!loadingCandidates && boardCandidates.length > 0 && (
          <div className="rank-list">
            {boardCandidates.slice(0, 8).map((item, index) => (
              <RankRow key={item.symbol} item={item} rank={index + 1} onSelect={openStockDetail} />
            ))}
          </div>
        )}
      </section>

      {(stockDetail || loadingStockDetail) && (
        <section className="stock-detail-board">
          <div className="section-heading">
            <div>
              <span className="eyebrow">종목 상세 정보</span>
              <h2>{detailProfile.company_name || stock || '종목 상세'}</h2>
            </div>
            <div className="market-strip">
              <span>{detailProfile.symbol || '-'}</span>
              <span>{ko(stockDetail?.order_status || 'NO_ORDER')}</span>
            </div>
          </div>
          {loadingStockDetail && (
            <div className="candidate-empty">
              <RefreshCw size={18} className="spin" />
              종목 상세 정보 갱신 중
            </div>
          )}
          {!loadingStockDetail && stockDetail && (
            <StockDetailCard profile={detailProfile} quant={detailQuant} investorFlow={investorFlow} />
          )}
        </section>
      )}

      {symbolAnalysis && (
        <section className="symbol-analysis-board">
          <div className="section-heading">
            <div>
              <span className="eyebrow">검색 종목 분석</span>
              <h2>{searchedAnalysis.company_name || symbolAnalysis.requested?.company_name || stock || '종목 확인'}</h2>
            </div>
            <div className="market-strip">
              <span>{searchedAnalysis.symbol || symbolAnalysis.requested?.symbol || '-'}</span>
              <span>{ko(searchedAnalysis.order_status || 'NO_ORDER')}</span>
            </div>
          </div>
          {symbolAnalysis.found ? (
            <SymbolAnalysisCard item={searchedAnalysis} />
          ) : (
            <div className="candidate-empty">
              이 종목 전용 분석 결과가 아직 없습니다. 분석 버튼을 누르면 로컬 캐시 기준으로 생성합니다.
            </div>
          )}
        </section>
      )}

      <section className="holding-board">
        <div className="section-heading">
          <div>
            <span className="eyebrow">보유 관리</span>
            <h2>보유종목 방어 보드</h2>
          </div>
          <div className="market-strip">
            <span>
              <ShieldAlert size={16} />
              {holdingBoard?.as_of || latest}
            </span>
            <span>{ko(holdingBoard?.order_status || 'NO_ORDER')}</span>
          </div>
        </div>

        {loadingHoldings && (
          <div className="candidate-empty">
            <RefreshCw size={18} className="spin" />
            보유종목 갱신 중
          </div>
        )}

        {!loadingHoldings && holdings.length === 0 && (
          <div className="candidate-empty">보유종목 입력 확인 필요</div>
        )}

        {!loadingHoldings && holdings.length > 0 && (
          <div className="holding-summary-grid">
            <HoldingKpi label="보유수" value={`${holdingSummary.holding_count || 0}개`} />
            <HoldingKpi
              label="수량 입력"
              value={`${holdingSummary.quantity_known_count || 0}/${holdingSummary.holding_count || 0}`}
            />
            <HoldingKpi label="총 평가액" value={formatPrice(holdingSummary.known_market_value)} />
            <HoldingKpi label="총 손익" value={formatSignedMoney(holdingSummary.known_unrealized_pnl)} />
            <HoldingKpi label="전체 수익률" value={formatPercent(holdingSummary.known_unrealized_return)} />
            <HoldingKpi label="방어 우선" value={ko(holdingSummary.highest_priority_action)} />
          </div>
        )}

        {!loadingHoldings && holdings.length > 0 && (
          <div className="holding-toolbar">
            <span>{holdingSaveMessage || ko(holdingSummary.next_operator_step)}</span>
            <button type="button" onClick={saveHoldings} disabled={savingHoldings}>
              {savingHoldings ? <RefreshCw size={17} className="spin" /> : <Save size={17} />}
              {savingHoldings ? '저장 중' : '수량 저장'}
            </button>
          </div>
        )}

        <form className="trade-entry" onSubmit={recordTrade}>
          <label>
            <span>종목</span>
            <input
              value={tradeDraft.stock}
              onChange={(event) => updateTradeDraft('stock', event.target.value)}
              placeholder="LG전자 또는 066570"
            />
          </label>
          <label>
            <span>구분</span>
            <select value={tradeDraft.side} onChange={(event) => updateTradeDraft('side', event.target.value)}>
              <option value="BUY">매수</option>
              <option value="SELL">매도</option>
            </select>
          </label>
          <label>
            <span>체결가</span>
            <input
              type="number"
              min="0"
              step="1"
              value={tradeDraft.price}
              onChange={(event) => updateTradeDraft('price', event.target.value)}
            />
          </label>
          <label>
            <span>수량</span>
            <input
              type="number"
              min="0"
              step="1"
              value={tradeDraft.quantity}
              onChange={(event) => updateTradeDraft('quantity', event.target.value)}
            />
          </label>
          <button type="submit" disabled={savingTrade}>
            {savingTrade ? <RefreshCw size={17} className="spin" /> : <Save size={17} />}
            {savingTrade ? '반영 중' : '체결 반영'}
          </button>
          <span className="trade-note">{tradeMessage || '실제 주문 아님 · 입력한 체결만 로컬 반영'}</span>
        </form>

        {!loadingHoldings && holdings.length > 0 && (
          <div className="holding-list">
            {holdings.map((item) => (
              <HoldingCard
                key={item.symbol}
                item={item}
                draft={holdingDrafts[item.symbol]}
                onDraftChange={updateHoldingDraft}
              />
            ))}
          </div>
        )}
      </section>

      <section className="candidate-board">
        <div className="section-heading">
          <div>
            <span className="eyebrow">후보 비교</span>
            <h2>오늘 후보 보드</h2>
          </div>
          <div className="market-strip">
            <span>
              <Activity size={16} />
              {ko(market.regime_status)}
            </span>
            <span>{ko(market.risk_posture)}</span>
            <span>{candidateBoard?.as_of || latest}</span>
            <span>{ko(candidateBoard?.order_status || 'NO_ORDER')}</span>
          </div>
        </div>

        {loadingCandidates && (
          <div className="candidate-empty">
            <RefreshCw size={18} className="spin" />
            후보 보드 갱신 중
          </div>
        )}

        {!loadingCandidates && boardCandidates.length === 0 && (
          <div className="candidate-empty">후보 보고서 확인 필요</div>
        )}

        {!loadingCandidates && boardCandidates.length > 0 && (
          <div className="candidate-list">
            {boardCandidates.map((item) => (
              <CandidateCard key={item.symbol} item={item} onSelect={openStockDetail} />
            ))}
          </div>
        )}
      </section>

      {resultLines.length > 0 && (
        <section className="result-panel">
          <h2>실행 결과</h2>
          <ol>
            {resultLines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ol>
        </section>
      )}
        </section>
      </div>
      <footer className="status-footer">
        <span>QSP Terminal · {candidateTower.data_status || 'CACHED_LOCAL'} · {latest}</span>
        <span>{analysisJob?.analysis_mode || 'READY'} · {analysisJob?.external_api_requested || 'NO_EXTERNAL'}</span>
        <span>REVIEW ONLY — {ko(status?.order_status || 'NO_ORDER')}</span>
      </footer>
    </main>
  );
}

function HoldingCard({ item, draft, onDraftChange }) {
  const activeDraft = draft || {
    entry_price: item.entry_price ? String(item.entry_price) : '',
    quantity: item.quantity_known ? String(item.quantity) : ''
  };
  const summary = item.decision_summary || {};
  return (
    <article className={`holding-card ${holdingClass(item.action_status)}`}>
      <div className="candidate-top">
        <div className="candidate-title">
          <strong>{item.company_name || '-'}</strong>
          <span>{item.symbol} · {ko(item.trend_regime)} · {ko(item.forecast_bias)}</span>
        </div>
        <span className={`status-badge ${statusClass(item.action_status)}`}>
          {ko(item.action_status)}
        </span>
      </div>
      <div className="holding-prices">
        <HoldingKpi label="매수가" value={formatPrice(item.entry_price)} />
        <HoldingKpi label="현재가" value={formatPrice(item.latest_price)} />
        <HoldingKpi label="손익률" value={formatPercent(item.unrealized_return)} />
      </div>
      <div className="candidate-meta">
        <span>수량 {formatQuantity(item.quantity, item.quantity_known)}</span>
        <span>감시 {formatRange(summary.watch_price_low, summary.watch_price_high)}</span>
        <span>주의 {formatPrice(item.risk_stop_price)}</span>
        <span>하드 {formatPrice(item.hard_stop_price)}</span>
        <span>{ko(item.final_watch_status)}</span>
      </div>
      <div className="holding-edit-row">
        <label>
          <span>매수가</span>
          <input
            type="number"
            min="0"
            step="1"
            value={activeDraft.entry_price}
            onChange={(event) => onDraftChange(item.symbol, 'entry_price', event.target.value)}
          />
        </label>
        <label>
          <span>수량</span>
          <input
            type="number"
            min="0"
            step="1"
            value={activeDraft.quantity}
            onChange={(event) => onDraftChange(item.symbol, 'quantity', event.target.value)}
          />
        </label>
      </div>
      <div className="blocker-line">
        <ShieldAlert size={16} />
        <span>{summary.risk_line || item.action_reason || item.action_summary || '수동 검토 필요'}</span>
      </div>
    </article>
  );
}

function CandidateCard({ item, onSelect }) {
  const summary = item.decision_summary || {};
  const note = item.operator_action || item.key_reason || item.next_check || '수동 검토 대기';
  const blockers = item.readiness_blockers || item.buy_ban_reasons || item.next_check || '게이트 확인 필요';
  return (
    <article
      className={item.chase_risk === 'YES' ? 'candidate-card risk clickable-card' : 'candidate-card clickable-card'}
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(item.symbol)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') onSelect?.(item.symbol);
      }}
    >
      <div className="candidate-top">
        <div className="candidate-title">
          <strong>{item.company_name || '-'}</strong>
          <span>{item.symbol} · {item.sector || '섹터 확인 필요'}</span>
        </div>
        <span className={`status-badge ${statusClass(item.decision_status)}`}>
          {decisionLabelKo(summary.label) || ko(item.decision_status)}
        </span>
      </div>
      <div className="candidate-meta">
        <span>현재가 {formatPrice(item.latest_price)}</span>
        <span>감시 {formatRange(summary.watch_price_low || item.entry_price_low, summary.watch_price_high || item.entry_price_high)}</span>
        <span>추격 {riskKo(item.chase_risk)}</span>
        <span>{ko(item.final_watch_status)}</span>
      </div>
      <p>{summary.reason || note}</p>
      <div className="blocker-line">
        {item.decision_status === 'BUY_READY' ? <CheckCircle2 size={16} /> : <ListChecks size={16} />}
        <span>{summary.risk_line || blockers}</span>
      </div>
    </article>
  );
}

function RankRow({ item, rank, onSelect }) {
  const summary = item.decision_summary || {};
  const score = Number(item.priority_score || item.final_rank_score || 0);
  const label = decisionLabelKo(summary.label) || ko(item.decision_status);
  const reason = summary.reason || item.operator_action || item.key_reason || item.next_check || '검토 사유 확인 필요';
  return (
    <article
      className={`rank-row rank-${rank <= 3 ? rank : 'base'}`}
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(item.symbol)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') onSelect?.(item.symbol);
      }}
    >
      <div className="rank-number">
        <span>{rank}</span>
      </div>
      <div className="rank-main">
        <div className="rank-title">
          <strong>{item.company_name || '-'}</strong>
          <span>{item.symbol} · {item.sector || '섹터 확인 필요'}</span>
        </div>
        <p>{reason}</p>
      </div>
      <div className="rank-metrics">
        <strong>{score.toFixed(1)}</strong>
        <span>점수</span>
      </div>
      <div className="rank-meta">
        <span className={`status-badge ${statusClass(item.decision_status)}`}>{label}</span>
        <span>{formatPrice(item.latest_price)}</span>
        <span>{ko(item.final_watch_status)}</span>
      </div>
    </article>
  );
}

function SymbolAnalysisCard({ item }) {
  const ready = item.analysis_status === 'ANALYSIS_READY';
  const blocker = item.blocking_reason || item.next_step || '수동 검토 필요';
  return (
    <article className={`symbol-analysis-card ${ready ? 'ready' : 'risk'}`}>
      <div className="candidate-top">
        <div className="candidate-title">
          <strong>{item.company_name || '-'}</strong>
          <span>{item.symbol} · {item.market || '-'} · {item.sector || '섹터 확인 필요'}</span>
        </div>
        <span className={`status-badge ${ready ? 'ready' : 'wait'}`}>
          {ko(item.analysis_status)}
        </span>
      </div>
      <div className="holding-summary-grid compact-grid">
        <HoldingKpi label="현재가" value={formatPrice(item.latest_price)} />
        <HoldingKpi label="기준일" value={item.latest_price_date || '-'} />
        <HoldingKpi label="점수" value={item.research_score ? `${Number(item.research_score).toFixed(1)}점` : '-'} />
        <HoldingKpi label="가격 데이터" value={`${ko(item.price_data_status)} · ${item.price_rows || 0}일`} />
      </div>
      <div className="candidate-meta">
        <span>판단 {ko(item.decision)}</span>
        <span>관점 {ko(item.research_view)}</span>
        <span>순위 {item.company_research_rank || '-'}</span>
        <span>{ko(item.local_pipeline_ready === 'YES' ? 'READY' : 'DATA_REQUIRED')}</span>
      </div>
      <p>{item.why_summary || '검색 종목의 로컬 분석 요약을 확인하세요.'}</p>
      <div className="blocker-line">
        {ready ? <CheckCircle2 size={16} /> : <ListChecks size={16} />}
        <span>{blocker}</span>
      </div>
    </article>
  );
}

function StockDetailCard({ profile, quant, investorFlow }) {
  const summary = quant.decision_summary || {};
  const investorRows = investorFlow.recent || [];
  return (
    <article className="stock-detail-card">
      <div className="candidate-top">
        <div className="candidate-title">
          <strong>{profile.company_name || '-'}</strong>
          <span>{profile.symbol || '-'} · {profile.market || '-'} · {profile.sector || '섹터 확인 필요'}</span>
        </div>
        <span className={`status-badge ${statusClass(quant.decision)}`}>
          {ko(quant.decision || 'UNKNOWN')}
        </span>
      </div>

      <div className="stock-detail-grid">
        <HoldingKpi label="현재가" value={formatPrice(profile.latest_price)} />
        <HoldingKpi label="기준일" value={profile.latest_price_date || '-'} />
        <HoldingKpi label="퀀트 점수" value={quant.priority_score ? `${Number(quant.priority_score).toFixed(1)}점` : '-'} />
        <HoldingKpi label="최종 순위점수" value={quant.final_rank_score ? `${Number(quant.final_rank_score).toFixed(1)}점` : '-'} />
        <HoldingKpi label="20일 수익률" value={formatPercent(quant.return_20d)} />
        <HoldingKpi label="60일 수익률" value={formatPercent(quant.return_60d)} />
        <HoldingKpi label="상승 확률" value={formatPercent(quant.upside_probability)} />
        <HoldingKpi label="예상 20일" value={formatPercent(quant.expected_20d_return)} />
      </div>

      <div className="candidate-meta">
        <span>추세 {ko(quant.trend_regime)}</span>
        <span>전망 {ko(quant.forecast_bias)}</span>
        <span>감시 {formatRange(summary.watch_price_low || quant.entry_price_low, summary.watch_price_high || quant.entry_price_high)}</span>
        <span>{ko(quant.final_watch_status)}</span>
        <span>{ko(quant.entry_watch_status)}</span>
      </div>

      <div className="detail-columns">
        <section>
          <h3>퀀트 판단</h3>
          <p>{summary.reason || quant.operator_action || quant.key_reason || quant.buy_reasons || '로컬 분석 사유를 확인하세요.'}</p>
          <div className="blocker-line compact">
            <ListChecks size={16} />
            <span>{summary.risk_line || quant.readiness_blockers || quant.buy_ban_reasons || quant.stop_loss_rule || '추가 차단 조건 없음'}</span>
          </div>
        </section>
        <section>
          <h3>거래원 / 수급</h3>
          <p>{investorFlow.summary || '기관/외국인 수급 데이터 확인 필요'}</p>
          {investorRows.length > 0 ? (
            <div className="flow-table">
              <div className="flow-row head">
                <span>일자</span>
                <span>기관</span>
                <span>외국인</span>
                <span>개인</span>
              </div>
              {investorRows.slice(-5).reverse().map((row, index) => (
                <div className="flow-row" key={`${row.date}-${index}`}>
                  <span>{row.date || '-'}</span>
                  <span>{formatSignedCompact(row.institution)}</span>
                  <span>{formatSignedCompact(row.foreign)}</span>
                  <span>{formatSignedCompact(row.individual)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="data-required-line">{ko(investorFlow.data_status || 'DATA_REQUIRED')}</div>
          )}
        </section>
      </div>
    </article>
  );
}

function ControlTile({ icon, label, value }) {
  return (
    <article className="control-tile">
      <span className="tile-icon">{icon}</span>
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </article>
  );
}

function HoldingKpi({ label, value }) {
  return (
    <div className="holding-kpi">
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value || '-'}</strong>
    </article>
  );
}

function formatPrice(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return '-';
  return `${number.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원`;
}

function formatRange(low, high) {
  const lowNumber = Number(low);
  const highNumber = Number(high);
  const hasLow = Number.isFinite(lowNumber) && lowNumber > 0;
  const hasHigh = Number.isFinite(highNumber) && highNumber > 0;
  if (!hasLow && !hasHigh) return '-';
  if (hasLow && hasHigh) return `${formatPrice(lowNumber)}-${formatPrice(highNumber)}`;
  return hasLow ? `${formatPrice(lowNumber)} 이상` : `${formatPrice(highNumber)} 이하`;
}

function formatPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return '-';
  return `${(number * 100).toLocaleString('ko-KR', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  })}%`;
}

function formatSignedMoney(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return '-';
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원`;
}

function formatSignedCompact(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return '-';
  const sign = number > 0 ? '+' : '';
  return `${sign}${number.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}`;
}

function formatQuantity(value, known) {
  const number = Number(value);
  if (!known || !Number.isFinite(number) || number <= 0) return '입력 필요';
  return `${number.toLocaleString('ko-KR', { maximumFractionDigits: 4 })}주`;
}

function makeHoldingDrafts(holdings) {
  return holdings.reduce((acc, item) => {
    acc[item.symbol] = {
      symbol: item.symbol,
      company_name: item.company_name || '',
      entry_price: item.entry_price ? String(item.entry_price) : '',
      quantity: item.quantity_known ? String(item.quantity) : '',
      notes: item.notes || ''
    };
    return acc;
  }, {});
}

function numberOrZero(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function analysisButtonLabel(running, job, refreshMarketData) {
  if (running) return ko(job?.status || 'RUNNING');
  return refreshMarketData ? '최신 분석' : '캐시 분석';
}

function analysisStatusText(job) {
  if (!job) return '분석 상태 확인 중';
  const mode = job.analysis_mode === 'QUICK_STOCK' ? '빠른 종목 분석' : job.refresh_market_data ? '최신 갱신' : '캐시';
  if (job.status === 'DONE') return `${mode} 분석 완료`;
  if (job.status === 'ERROR') return job.error || '분석 오류';
  if (job.status === 'QUEUED') return `${mode} 분석 대기 중`;
  if (job.status === 'RUNNING') return `${mode} 분석 실행 중`;
  return `${mode} 분석 ${ko(job.status)}`;
}

function elapsedText(job) {
  if (!job?.started_at) return '대기';
  const started = new Date(job.started_at.replace(' ', 'T'));
  const finished = job.finished_at ? new Date(job.finished_at.replace(' ', 'T')) : new Date();
  if (Number.isNaN(started.getTime()) || Number.isNaN(finished.getTime())) return '시간 확인';
  const seconds = Math.max(0, Math.round((finished.getTime() - started.getTime()) / 1000));
  if (seconds < 60) return `${seconds}초`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}분 ${rest}초`;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function decisionLabelKo(value) {
  const labels = {
    BUY_REVIEW: '매수 검토',
    WAIT_REVIEW: '대기 검토',
    MARKET_WAIT: '시장 대기',
    WAIT_PULLBACK: '눌림 대기',
    AVOID_FOR_NOW: '지금은 제외',
    REDUCE_REVIEW: '일부 축소 검토',
    SELL_REVIEW: '매도 검토',
    HOLD_DEFENSIVE: '방어 보유',
    HOLD_REVIEW: '보유 점검',
    DATA_REQUIRED: '데이터 필요'
  };
  return labels[value] || ko(value);
}

function policyKo(value) {
  const labels = {
    DEFENSIVE_REVIEW: '방어 우선 운용',
    SELECTIVE_BUY_REVIEW: '선별 진입 검토',
    SELECTIVE_REVIEW: '선별 관찰'
  };
  return labels[value] || '운용 상태 확인';
}

function defenseKo(value) {
  const labels = {
    DEFENSE_FIRST: '방어 우선',
    NO_HOLDINGS: '보유 없음',
    MONITOR: '점검 유지'
  };
  return labels[value] || '점검';
}

function riskKo(value) {
  if (value === 'YES') return '주의';
  if (value === 'NO') return '낮음';
  return ko(value);
}

function statusClass(value) {
  if (value === 'BUY_READY') return 'ready';
  if (value === 'WAIT' || value === 'HOLD_REVIEW' || value === 'HOLD_DEFENSIVE') return 'wait';
  if (value === 'REJECT' || value === 'FAIL' || value === 'SELL_REVIEW' || value === 'REDUCE_REVIEW') return 'reject';
  return 'unknown';
}

function holdingClass(value) {
  if (value === 'SELL_REVIEW' || value === 'REDUCE_REVIEW') return 'risk';
  if (value === 'HOLD_DEFENSIVE') return 'watch';
  return '';
}

createRoot(document.getElementById('root')).render(<App />);
