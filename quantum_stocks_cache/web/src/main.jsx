import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  ExternalLink,
  Play,
  RefreshCw,
  ShieldCheck
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
  WRITE_TRADE_JOURNAL_AFTER_BUY: '매수 후 기록 필요'
};

function ko(value) {
  if (!value) return '확인 필요';
  return statusKo[value] || value;
}

function App() {
  const [status, setStatus] = useState(null);
  const [stock, setStock] = useState('');
  const [refreshMarketData, setRefreshMarketData] = useState(false);
  const [running, setRunning] = useState(false);
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [resultLines, setResultLines] = useState([]);
  const [error, setError] = useState('');

  async function loadStatus() {
    const response = await fetch('/api/status');
    if (!response.ok) throw new Error('상태를 불러오지 못했습니다.');
    setStatus(await response.json());
  }

  useEffect(() => {
    loadStatus().catch((err) => setError(err.message));
  }, []);

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
  }

  async function runAnalysis(event) {
    event.preventDefault();
    setRunning(true);
    setError('');
    setResultLines([]);
    try {
      const requestedStock = selectedCandidate?.symbol || stock.trim() || null;
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stock: requestedStock,
          refresh_market_data: refreshMarketData
        })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || '분석 실행에 실패했습니다.');
      setResultLines(body.lines || []);
      setStatus(body.status);
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }

  const candidate = status?.top_candidate || {};
  const universe = status?.universe || {};
  const tracking = status?.tracking || {};
  const latest = status?.latest_price_date || '-';
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
          <p>오늘 후보와 막힌 이유</p>
        </div>
        <span className="safe-pill">
          <ShieldCheck size={16} />
          주문 실행 없음
        </span>
      </header>

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
            {running ? '실행 중' : '오늘 분석'}
          </button>
        </form>
      </section>

      {error && (
        <section className="notice error">
          <AlertTriangle size={18} />
          {error}
        </section>
      )}

      <section className="decision-grid">
        <article className="decision-panel">
          <span className="eyebrow">오늘 결론</span>
          <h2>{conclusion}</h2>
          <p>{candidate.why_not_now || '대시보드에서 최종 검토하세요.'}</p>
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
    </main>
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

createRoot(document.getElementById('root')).render(<App />);
