import { useCallback, useEffect, useMemo, useState } from "react";
import { AD_EVENT_STORAGE_KEY, fetchRemoteAdEventSummary, summarizeAdEvents } from "../features/ads/lib/ads";
import {
  MARKET_REPORT_MIN_BROWSERS,
  MARKET_REPORT_MIN_EVENTS,
  buildMarketReportCreateAuditMetadata,
  buildMarketReportCsv,
  buildMarketReportDownloadAuditMetadata,
  createEmptyAnalyticsMarketReportArchive,
  createRemoteAnalyticsMarketReport,
  fetchRemoteAnalyticsDashboardSummary,
  fetchRemoteAnalyticsMarketReportArchive,
  fetchRemoteAnalyticsMarketReportItems,
  formatAnalyticsSummaryKey,
  getMarketReportReadiness,
  trackAnalyticsEvent,
} from "../features/analytics/lib/analytics";
import useAuthSession from "../features/auth/hooks/useAuthSession";
import { PLATFORMS } from "../shared/config/platforms";

const ARTIFACTS = {
  status: "crawl-status.json",
  quality: "data-quality.json",
};

const STATUS_LABELS = {
  running: "실행 중",
  completed: "정상 완료",
  completed_with_errors: "오류 포함 완료",
  blocked: "게이트 차단",
  failed: "실패",
};

const SEVERITY_LABELS = {
  critical: "치명",
  high: "높음",
  medium: "주의",
  low: "낮음",
};

const MARKET_REPORT_TYPE_LABELS = {
  event_type_mix: "행동 유형",
  category_interest: "카테고리 관심",
  region_interest: "지역 관심",
  platform_interest: "플랫폼 관심",
  tab_attention: "탭 관심",
  category_apply_funnel: "카테고리 신청 전환",
  category_region_interest: "카테고리/지역 관심",
};
const MARKET_REPORT_STATUS_LABELS = {
  ready: "저장 완료",
  empty: "표본 부족",
};

function formatDateTime(value) {
  if (!value) return "-";
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return "-";
  return new Intl.DateTimeFormat("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(parsed));
}

function formatDuration(ms) {
  const value = Number(ms);
  if (!Number.isFinite(value) || value < 0) return "-";
  const seconds = Math.round(value / 1000);
  const minutes = Math.floor(seconds / 60);
  const remain = seconds % 60;
  return minutes > 0 ? `${minutes}분 ${remain}초` : `${remain}초`;
}

function formatPercent(value) {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(1)}%` : "-";
}

function formatRate(value) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : "-";
}

async function fetchJsonArtifact(fileName) {
  const response = await fetch(`/${fileName}?t=${Date.now()}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`${fileName} 요청 실패 (${response.status})`);
  return response.json();
}

function getPlatformMeta(platformId) {
  return PLATFORMS.find((platform) => platform.id === platformId) || {
    id: platformId,
    name: platformId,
    color: "#111827",
    emoji: platformId?.slice(0, 2)?.toUpperCase() || "OP",
  };
}

function HealthPill({ status }) {
  const normalized = status || "unknown";
  return (
    <span className={`ops-health-pill ops-health-pill--${normalized}`}>
      {STATUS_LABELS[normalized] || normalized}
    </span>
  );
}

function Metric({ label, value, tone = "default" }) {
  return (
    <div className={`ops-metric ops-metric--${tone}`}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function createEmptyRemoteAdSummary() {
  return {
    totalEvents: 0,
    impressions: 0,
    clicks: 0,
    rows: [],
    error: "",
  };
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function getAnalyticsEventCount(summary, eventType) {
  return summary.eventRows.find((row) => row.eventType === eventType)?.count || 0;
}



function formatMarketReportType(type) {
  return MARKET_REPORT_TYPE_LABELS[type] || type || "-";
}

function formatMarketMetric(item) {
  if (/rate/i.test(item.metricName)) return formatRate(item.metricValue);
  if (Number.isInteger(item.metricValue)) return formatInteger(item.metricValue);
  return Number.isFinite(item.metricValue) ? item.metricValue.toLocaleString("ko-KR") : "-";
}

function formatReportPeriod(report) {
  if (!report?.periodStart || !report?.periodEnd) return "-";
  return `${formatDateTime(report.periodStart)} - ${formatDateTime(report.periodEnd)}`;
}

function downloadMarketReportCsv(report, items = []) {
  if (!report) return;
  const dateKey = String(report.generatedAt || new Date().toISOString()).slice(0, 10);
  const blob = new Blob([buildMarketReportCsv(report, items)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `analytics-market-report-${dateKey}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function SourceBar({ sources = {} }) {
  const entries = Object.entries(sources)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 4);

  if (!entries.length) return <span className="ops-muted">출처 없음</span>;

  return (
    <div className="ops-source-list">
      {entries.map(([source, count]) => (
        <span key={source} className="ops-source-chip">
          {source} <strong>{count}</strong>
        </span>
      ))}
    </div>
  );
}

function IssueList({ title, issues = [] }) {
  const visible = issues.slice(0, 8);

  return (
    <section className="ops-panel">
      <div className="ops-panel-head">
        <div>
          <span className="ops-kicker">Issue Sample</span>
          <h3>{title}</h3>
        </div>
        <span className="ops-count">{issues.length}개 샘플</span>
      </div>
      {visible.length === 0 ? (
        <div className="ops-empty">확인된 샘플이 없습니다.</div>
      ) : (
        <div className="ops-issue-list">
          {visible.map((issue) => (
            <div key={`${title}-${issue.id}`} className="ops-issue-row">
              <div>
                <strong>{issue.title || issue.id}</strong>
                <span>{issue.platformId} · {issue.coordinateSource || "source 없음"}</span>
                {issue.address && <p>{issue.address}</p>}
              </div>
              {issue.url && (
                <a href={issue.url} target="_blank" rel="noreferrer">
                  원문
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function AnalyticsSummaryTable({ title, rows = [], emptyText = "아직 집계된 이벤트가 없습니다." }) {
  return (
    <div className="ops-analytics-block">
      <div className="ops-analytics-block-title">{title}</div>
      {rows.length === 0 ? (
        <div className="ops-empty ops-empty--compact">{emptyText}</div>
      ) : (
        <div className="ops-analytics-table">
          <div className="ops-analytics-row ops-analytics-row--head">
            <span>항목</span>
            <span>이벤트</span>
            <span>브라우저</span>
            <span>최근</span>
          </div>
          {rows.map((row) => (
            <div key={`${row.type}-${row.key}-${row.eventType}`} className="ops-analytics-row">
              <strong>{formatAnalyticsSummaryKey(row)}</strong>
              <span>{formatInteger(row.count)}</span>
              <span>{formatInteger(row.uniqueBrowsers)}</span>
              <span>{formatDateTime(row.lastEventAt)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MarketReportPreviewTable({ rows = [] }) {
  if (!rows.length) {
    return (
      <div className="ops-empty">
        아직 판매용 리포트 기준을 넘은 항목이 없습니다. 이벤트와 고유 브라우저가 더 쌓이면 이 영역에 후보가 표시됩니다.
      </div>
    );
  }

  return (
    <div className="ops-market-table">
      <div className="ops-market-row ops-market-row--head">
        <span>리포트 단위</span>
        <span>항목</span>
        <span>이벤트</span>
        <span>브라우저</span>
        <span>최근</span>
      </div>
      {rows.map((row) => (
        <div key={`${row.groupLabel}-${row.type}-${row.key}`} className="ops-market-row">
          <span>{row.groupLabel}</span>
          <strong>{row.displayKey}</strong>
          <span>{formatInteger(row.count)}</span>
          <span>{formatInteger(row.uniqueBrowsers)}</span>
          <span>{formatDateTime(row.lastEventAt)}</span>
        </div>
      ))}
    </div>
  );
}

function StoredMarketReportTable({ report, items = [] }) {
  if (!report) {
    return <div className="ops-empty">저장된 시장 리포트가 없습니다.</div>;
  }

  if (!items.length) {
    return <div className="ops-empty">표본 기준을 통과한 저장 항목이 없습니다.</div>;
  }

  return (
    <div className="ops-market-stored-table">
      <div className="ops-market-stored-row ops-market-stored-row--head">
        <span>순위</span>
        <span>리포트 단위</span>
        <span>항목</span>
        <span>지표</span>
        <span>값</span>
        <span>이벤트</span>
        <span>브라우저</span>
      </div>
      {items.map((item) => (
        <div
          key={`${item.reportId}-${item.rankPosition}-${item.reportType}-${item.dimensionKey}-${item.metricName}`}
          className="ops-market-stored-row"
        >
          <span>{item.rankPosition}</span>
          <span>{formatMarketReportType(item.reportType)}</span>
          <strong>{item.dimensionKey}</strong>
          <span>{item.metricName}</span>
          <span>{formatMarketMetric(item)}</span>
          <span>{formatInteger(item.eventCount)}</span>
          <span>{formatInteger(item.uniqueBrowsers)}</span>
        </div>
      ))}
    </div>
  );
}

function StoredMarketReportPanel({
  archive,
  action,
  selectedReport,
  onGenerate,
  onSelect,
  onDownload,
}) {
  const canDownload = Boolean(selectedReport);

  return (
    <section className="ops-panel">
      <div className="ops-panel-head">
        <div>
          <span className="ops-kicker">Report Archive</span>
          <h3>저장된 시장 리포트</h3>
        </div>
        <span className="ops-count">{archive.reports.length ? `${archive.reports.length}개 보관` : "보관 없음"}</span>
      </div>
      {archive.error && (
        <div className="ops-alert ops-alert--neutral">
          {archive.error}
        </div>
      )}
      <div className="ops-market-actions">
        <button type="button" onClick={onGenerate} disabled={Boolean(action)}>
          {action === "generating" ? "생성 중" : "새 리포트 생성"}
        </button>
        <button type="button" onClick={onDownload} disabled={!canDownload}>
          CSV 다운로드
        </button>
      </div>
      {archive.reports.length > 0 && (
        <div className="ops-market-report-list">
          {archive.reports.map((report) => (
            <button
              key={report.id}
              type="button"
              className={`ops-market-report-button ${report.id === archive.selectedReportId ? "is-active" : ""}`}
              onClick={() => onSelect(report.id)}
              disabled={action === "loading"}
            >
              <strong>{report.title}</strong>
              <span>
                {MARKET_REPORT_STATUS_LABELS[report.status] || report.status}
                {" · "}
                {formatInteger(report.rowCount)}개 항목
                {" · "}
                {formatDateTime(report.generatedAt)}
              </span>
            </button>
          ))}
        </div>
      )}
      {selectedReport && (
        <div className="ops-run-list ops-run-list--market">
          <div><span>상태</span><strong>{MARKET_REPORT_STATUS_LABELS[selectedReport.status] || selectedReport.status}</strong></div>
          <div><span>저장 항목</span><strong>{formatInteger(selectedReport.rowCount)}</strong></div>
          <div><span>전체 이벤트</span><strong>{formatInteger(selectedReport.totalEventCount)}</strong></div>
          <div><span>고유 브라우저</span><strong>{formatInteger(selectedReport.totalUniqueBrowsers)}</strong></div>
          <div><span>표본 기준</span><strong>{selectedReport.minEvents} / {selectedReport.minBrowsers}</strong></div>
          <div><span>기간</span><strong>{formatReportPeriod(selectedReport)}</strong></div>
        </div>
      )}
      <StoredMarketReportTable report={selectedReport} items={archive.items} />
    </section>
  );
}

function OpsPage() {
  const { user } = useAuthSession();
  const [status, setStatus] = useState(null);
  const [quality, setQuality] = useState(null);
  const [adSummary, setAdSummary] = useState(() => summarizeAdEvents());
  const [remoteAdSummary, setRemoteAdSummary] = useState(createEmptyRemoteAdSummary);
  const [marketReportArchive, setMarketReportArchive] = useState(createEmptyAnalyticsMarketReportArchive);
  const [marketReportAction, setMarketReportAction] = useState("");
  const [analyticsSummary, setAnalyticsSummary] = useState(() => ({
    totalEvents: 0,
    uniqueUsers: 0,
    uniqueBrowsers: 0,
    lastEventAt: "",
    eventRows: [],
    categoryRows: [],
    regionRows: [],
    platformRows: [],
    tabRows: [],
    identityRows: [],
    applyCampaignRows: [],
    openCampaignRows: [],
    error: "",
  }));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextStatus, nextQuality] = await Promise.all([
        fetchJsonArtifact(ARTIFACTS.status),
        fetchJsonArtifact(ARTIFACTS.quality),
      ]);
      const nextRemoteAdSummary = await fetchRemoteAdEventSummary(30);
      const nextAnalyticsSummary = await fetchRemoteAnalyticsDashboardSummary(30, { user });
      const nextMarketReportArchive = await fetchRemoteAnalyticsMarketReportArchive({ user, limit: 8 });
      setStatus(nextStatus);
      setQuality(nextQuality);
      setAdSummary(summarizeAdEvents());
      setRemoteAdSummary(nextRemoteAdSummary);
      setAnalyticsSummary(nextAnalyticsSummary);
      setMarketReportArchive(nextMarketReportArchive);
    } catch (loadError) {
      setError(loadError.message || "운영 데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const platformRows = useMemo(() => {
    return [...(quality?.platforms || [])].sort((left, right) => (
      Number(left.coordinateCompletenessPct || 0) - Number(right.coordinateCompletenessPct || 0)
      || String(left.platformId).localeCompare(String(right.platformId))
    ));
  }, [quality]);

  const warnings = quality?.warnings || [];
  const totals = quality?.totals || status?.totals || {};
  const statusLabel = status?.status || (loading ? "running" : "unknown");
  const qualityGate = quality?.qualityGate || status?.qualityGate || null;
  const gateRules = qualityGate?.rules || [];
  const failedGateRules = gateRules.filter((rule) => !rule.passed);
  const adCtr = adSummary.impressions > 0 ? adSummary.clicks / adSummary.impressions : 0;
  const remoteAdCtr = remoteAdSummary.impressions > 0
    ? remoteAdSummary.clicks / remoteAdSummary.impressions
    : 0;
  const performanceRows = remoteAdSummary.rows.length ? remoteAdSummary.rows : adSummary.rows;
  const performanceSource = remoteAdSummary.rows.length ? "Supabase 30일" : "브라우저 로컬";
  const analyticsApplyClicks = getAnalyticsEventCount(analyticsSummary, "apply_click");
  const analyticsCampaignOpens = getAnalyticsEventCount(analyticsSummary, "campaign_open");
  const analyticsSearchEvents = getAnalyticsEventCount(analyticsSummary, "search_filter");
  const analyticsFilterEvents = [
    "category_filter",
    "region_filter",
    "preset_filter",
    "sort_filter",
    "filter_reset",
  ].reduce((sum, eventType) => sum + getAnalyticsEventCount(analyticsSummary, eventType), 0);
  const marketReportReadiness = useMemo(
    () => getMarketReportReadiness(analyticsSummary, { formatKey: formatAnalyticsSummaryKey }),
    [analyticsSummary],
  );
  const selectedMarketReport = useMemo(
    () => marketReportArchive.reports.find((report) => report.id === marketReportArchive.selectedReportId) || null,
    [marketReportArchive.reports, marketReportArchive.selectedReportId],
  );

  const handleMarketReportSelect = useCallback(async (reportId) => {
    if (!reportId || reportId === marketReportArchive.selectedReportId) return;
    setMarketReportAction("loading");
    const nextItems = await fetchRemoteAnalyticsMarketReportItems(reportId, { user });
    setMarketReportArchive((current) => ({
      ...current,
      selectedReportId: reportId,
      items: nextItems.items,
      error: nextItems.error,
    }));
    setMarketReportAction("");
  }, [marketReportArchive.selectedReportId, user]);

  const handleMarketReportGenerate = useCallback(async () => {
    setMarketReportAction("generating");
    try {
      const result = await createRemoteAnalyticsMarketReport({
        user,
        lookbackDays: 30,
        minEvents: MARKET_REPORT_MIN_EVENTS,
        minBrowsers: MARKET_REPORT_MIN_BROWSERS,
        title: `시장 리포트 ${new Intl.DateTimeFormat("ko-KR", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
        }).format(new Date())}`,
      });
      const nextArchive = await fetchRemoteAnalyticsMarketReportArchive({ user, limit: 8 });
      const selectedItems = result.id
        ? await fetchRemoteAnalyticsMarketReportItems(result.id, { user })
        : { items: [], error: "" };
      trackAnalyticsEvent("market_report_create", {
        slotId: "market_report",
        metadata: buildMarketReportCreateAuditMetadata(result, {
          lookbackDays: 30,
          minEvents: MARKET_REPORT_MIN_EVENTS,
          minBrowsers: MARKET_REPORT_MIN_BROWSERS,
          selectedItems: selectedItems.items,
        }),
      }, user);
      setMarketReportArchive({
        ...nextArchive,
        selectedReportId: result.id || nextArchive.selectedReportId,
        items: selectedItems.items.length ? selectedItems.items : nextArchive.items,
        error: selectedItems.error || nextArchive.error,
      });
    } catch (actionError) {
      setMarketReportArchive((current) => ({
        ...current,
        error: actionError.message || "시장 리포트 생성 실패",
      }));
    } finally {
      setMarketReportAction("");
    }
  }, [user]);

  const handleMarketReportDownload = useCallback(() => {
    if (selectedMarketReport) {
      trackAnalyticsEvent("market_report_download", {
        slotId: "market_report",
        metadata: buildMarketReportDownloadAuditMetadata(selectedMarketReport, marketReportArchive.items),
      }, user);
    }
    downloadMarketReportCsv(selectedMarketReport, marketReportArchive.items);
  }, [marketReportArchive.items, selectedMarketReport, user]);

  return (
    <div className="page ops-page">
      <section className="ops-header">
        <div>
          <div className="command-eyebrow">Operations</div>
          <h1 className="ops-title">데이터 품질 관리</h1>
          <p className="ops-sub">
            크롤링 성공 여부, 좌표 완성률, 주소 누락, 낮은 신뢰도 좌표를 한 화면에서 확인합니다.
          </p>
        </div>
        <div className="ops-header-actions">
          <HealthPill status={statusLabel} />
          <button type="button" className="ops-refresh" onClick={load} disabled={loading}>
            {loading ? "갱신 중" : "새로고침"}
          </button>
        </div>
      </section>

      {error && <div className="ops-alert">{error}</div>}

      {!loading && !status && !quality && !error && (
        <div className="ops-alert ops-alert--neutral">
          아직 운영 리포트가 없습니다. 크롤링을 한 번 실행하면 `public/crawl-status.json`과 `public/data-quality.json`이 생성됩니다.
        </div>
      )}

      <section className="ops-metrics-grid">
        <Metric label="전체 캠페인" value={totals.campaigns ?? 0} />
        <Metric label="좌표 완성률" value={formatPercent(totals.coordinateCompletenessPct)} tone="map" />
        <Metric label="주소 완성률" value={formatPercent(totals.addressCompletenessPct)} tone="address" />
        <Metric label="실패 사이트" value={totals.failedPlatforms ?? 0} tone={(totals.failedPlatforms ?? 0) > 0 ? "danger" : "default"} />
        <Metric label="중복 숨김" value={totals.hiddenDuplicates ?? 0} />
        <Metric label="오래된 숨김" value={totals.hiddenStaleCampaigns ?? 0} tone={(totals.hiddenStaleCampaigns ?? 0) > 0 ? "danger" : "default"} />
        <Metric label="마감 추정 숨김" value={totals.hiddenExpiredCampaigns ?? 0} />
        <Metric
          label="품질 게이트"
          value={qualityGate?.status || "-"}
          tone={qualityGate?.canPublish === false ? "danger" : "default"}
        />
      </section>

      <section className="ops-panel">
        <div className="ops-panel-head">
          <div>
            <span className="ops-kicker">User Behavior</span>
            <h3>사용자 행동 분석</h3>
          </div>
          <span className="ops-count">Supabase 30일</span>
        </div>
        {analyticsSummary.error && (
          <div className="ops-alert ops-alert--neutral">
            {analyticsSummary.error}
          </div>
        )}
        <div className="ops-run-list ops-run-list--analytics">
          <div><span>전체 이벤트</span><strong>{formatInteger(analyticsSummary.totalEvents)}</strong></div>
          <div><span>고유 브라우저</span><strong>{formatInteger(analyticsSummary.uniqueBrowsers)}</strong></div>
          <div><span>로그인 사용자</span><strong>{formatInteger(analyticsSummary.uniqueUsers)}</strong></div>
          <div><span>상세 열기</span><strong>{formatInteger(analyticsCampaignOpens)}</strong></div>
          <div><span>신청 버튼</span><strong>{formatInteger(analyticsApplyClicks)}</strong></div>
          <div><span>검색/필터</span><strong>{formatInteger(analyticsSearchEvents + analyticsFilterEvents)}</strong></div>
        </div>
        <div className="ops-analytics-grid">
          <AnalyticsSummaryTable title="행동 유형" rows={analyticsSummary.eventRows} />
          <AnalyticsSummaryTable title="탭 사용" rows={analyticsSummary.tabRows} />
          <AnalyticsSummaryTable title="인기 카테고리" rows={analyticsSummary.categoryRows} />
          <AnalyticsSummaryTable title="인기 지역" rows={analyticsSummary.regionRows} />
          <AnalyticsSummaryTable title="로그인/비로그인" rows={analyticsSummary.identityRows} />
          <AnalyticsSummaryTable title="신청 클릭 캠페인" rows={analyticsSummary.applyCampaignRows} emptyText="아직 신청 클릭 이벤트가 없습니다." />
        </div>
      </section>

      <section className="ops-panel">
        <div className="ops-panel-head">
          <div>
            <span className="ops-kicker">Market Report</span>
            <h3>판매용 리포트 준비 상태</h3>
          </div>
          <span className={`ops-count ${marketReportReadiness.isReady ? "ops-count--ready" : ""}`}>
            {marketReportReadiness.isReady ? "생성 가능" : "표본 대기"}
          </span>
        </div>
        <div className="ops-run-list ops-run-list--market">
          <div>
            <span>현재 이벤트</span>
            <strong>{formatInteger(analyticsSummary.totalEvents)} / {MARKET_REPORT_MIN_EVENTS}</strong>
          </div>
          <div>
            <span>고유 브라우저</span>
            <strong>{formatInteger(analyticsSummary.uniqueBrowsers)} / {MARKET_REPORT_MIN_BROWSERS}</strong>
          </div>
          <div>
            <span>부족 이벤트</span>
            <strong>{formatInteger(marketReportReadiness.missingEvents)}</strong>
          </div>
          <div>
            <span>부족 브라우저</span>
            <strong>{formatInteger(marketReportReadiness.missingBrowsers)}</strong>
          </div>
          <div>
            <span>생성 가능 항목</span>
            <strong>{formatInteger(marketReportReadiness.readySegmentCount)}</strong>
          </div>
          <div>
            <span>기준 기간</span>
            <strong>최근 30일</strong>
          </div>
        </div>
        <div className={`ops-market-status ${marketReportReadiness.isReady ? "is-ready" : ""}`}>
          <strong>{marketReportReadiness.isReady ? "판매용 집계 후보가 준비됐습니다." : "아직 판매용 리포트 기준에는 부족합니다."}</strong>
          <span>
            원본 이벤트가 아니라 기준을 넘은 집계 항목만 리포트 후보로 봅니다. 작은 표본 segment는 외부 제공 대상에서 제외됩니다.
          </span>
        </div>
        <MarketReportPreviewTable rows={marketReportReadiness.candidateRows} />
      </section>

      <StoredMarketReportPanel
        archive={marketReportArchive}
        action={marketReportAction}
        selectedReport={selectedMarketReport}
        onGenerate={handleMarketReportGenerate}
        onSelect={handleMarketReportSelect}
        onDownload={handleMarketReportDownload}
      />

      <section className="ops-panel">
        <div className="ops-panel-head">
          <div>
            <span className="ops-kicker">Ad Performance</span>
            <h3>광고 성과</h3>
          </div>
          <span className="ops-count">{performanceSource}</span>
        </div>
        <div className="ops-run-list">
          <div><span>Supabase 노출</span><strong>{remoteAdSummary.impressions}</strong></div>
          <div><span>Supabase 클릭</span><strong>{remoteAdSummary.clicks}</strong></div>
          <div><span>Supabase CTR</span><strong>{formatRate(remoteAdCtr)}</strong></div>
          <div><span>로컬 이벤트</span><strong>{adSummary.totalEvents}</strong></div>
          <div><span>로컬 CTR</span><strong>{formatRate(adCtr)}</strong></div>
        </div>
        {remoteAdSummary.error && (
          <div className="ops-alert ops-alert--neutral">
            Supabase 광고 집계는 아직 사용할 수 없습니다. {remoteAdSummary.error}
          </div>
        )}
        {performanceRows.length === 0 ? (
          <div className="ops-empty">아직 기록된 광고 이벤트가 없습니다. 로컬 저장소 키는 `{AD_EVENT_STORAGE_KEY}`입니다.</div>
        ) : (
          <div className="ops-platform-table ops-platform-table--ads">
            <div className="ops-platform-row ops-platform-row--head">
              <span>슬롯</span>
              <span>노출</span>
              <span>클릭</span>
              <span>CTR</span>
              <span>제공자</span>
              <span>최근 이벤트</span>
            </div>
            {performanceRows.map((row) => (
              <div key={row.slotId} className="ops-platform-row">
                <strong>{row.slotId}</strong>
                <span>{row.impressions}</span>
                <span>{row.clicks}</span>
                <span>{formatRate(row.ctr)}</span>
                <span>{row.providers.join(", ") || "-"}</span>
                <span>{formatDateTime(row.lastEventAt)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="ops-run-grid">
        <div className="ops-panel">
          <div className="ops-panel-head">
            <div>
              <span className="ops-kicker">Latest Crawl</span>
              <h3>실행 상태</h3>
            </div>
          </div>
          <div className="ops-run-list">
            <div><span>시작</span><strong>{formatDateTime(status?.startedAt)}</strong></div>
            <div><span>갱신</span><strong>{formatDateTime(status?.updatedAt)}</strong></div>
            <div><span>소요</span><strong>{formatDuration(status?.durationMs)}</strong></div>
            <div><span>Supabase</span><strong>{status?.supabaseSync?.status || "-"}</strong></div>
            <div><span>Publish</span><strong>{qualityGate?.canPublish === false ? "blocked" : qualityGate?.status || "-"}</strong></div>
          </div>
        </div>

        <div className="ops-panel">
          <div className="ops-panel-head">
            <div>
              <span className="ops-kicker">Warnings</span>
              <h3>운영 경고</h3>
            </div>
            <span className="ops-count">{warnings.length}</span>
          </div>
          {warnings.length === 0 ? (
            <div className="ops-empty">현재 경고가 없습니다.</div>
          ) : (
            <div className="ops-warning-list">
              {warnings.slice(0, 8).map((warning, index) => (
                <div key={`${warning.platformId}-${index}`} className={`ops-warning ops-warning--${warning.severity}`}>
                  <span>{SEVERITY_LABELS[warning.severity] || warning.severity}</span>
                  <strong>{warning.platformId}</strong>
                  <p>{warning.message}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="ops-panel">
          <div className="ops-panel-head">
            <div>
              <span className="ops-kicker">Publish Gate</span>
              <h3>서비스 반영 보호</h3>
            </div>
            <span className="ops-count">{qualityGate?.mode || "-"}</span>
          </div>
          {!qualityGate ? (
            <div className="ops-empty">아직 품질 게이트 결과가 없습니다.</div>
          ) : (
            <div className="ops-gate-list">
              <div>
                <span>상태</span>
                <strong>{qualityGate.status}</strong>
              </div>
              <div>
                <span>신규 좌표</span>
                <strong>{formatPercent(qualityGate.totals?.fresh?.coordinateCompletenessPct)}</strong>
              </div>
              <div>
                <span>서비스 후보 좌표</span>
                <strong>{formatPercent(qualityGate.totals?.candidate?.coordinateCompletenessPct)}</strong>
              </div>
              <div>
                <span>차단 규칙</span>
                <strong>{failedGateRules.length}</strong>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="ops-panel ops-platform-panel">
        <div className="ops-panel-head">
          <div>
            <span className="ops-kicker">Platform Quality</span>
            <h3>사이트별 품질</h3>
          </div>
          <span className="ops-count">{platformRows.length}개 사이트</span>
        </div>

        <div className="ops-platform-table">
          <div className="ops-platform-row ops-platform-row--head">
            <span>사이트</span>
            <span>캠페인</span>
            <span>좌표</span>
            <span>정확 좌표</span>
            <span>주소</span>
            <span>좌표 출처</span>
          </div>
          {platformRows.map((platform) => {
            const meta = getPlatformMeta(platform.platformId);
            const coordinatePct = Number(platform.coordinateCompletenessPct || 0);
            return (
              <div key={platform.platformId} className="ops-platform-row">
                <div className="ops-platform-name">
                  <span style={{ background: meta.color }}>{meta.emoji}</span>
                  <strong>{meta.name || platform.platformId}</strong>
                  <small>{platform.platformId}</small>
                </div>
                <span>{platform.total}</span>
                <div className="ops-progress-cell">
                  <div className="ops-progress-track">
                    <div
                      className={`ops-progress-fill ${coordinatePct < 85 ? "is-risk" : ""}`}
                      style={{ width: `${Math.max(0, Math.min(100, coordinatePct))}%` }}
                    />
                  </div>
                  <strong>{formatPercent(coordinatePct)}</strong>
                </div>
                <span>{formatPercent(platform.exactCoordinatePct)}</span>
                <span>{formatPercent(platform.addressCompletenessPct)}</span>
                <SourceBar sources={platform.coordinateSources} />
              </div>
            );
          })}
        </div>
      </section>

      <div className="ops-issue-grid">
        <IssueList title="좌표 누락" issues={quality?.issues?.missingCoordinates || []} />
        <IssueList title="주소 누락" issues={quality?.issues?.missingAddress || []} />
        <IssueList title="낮은 신뢰도 좌표" issues={quality?.issues?.lowConfidenceCoordinates || []} />
        <IssueList title="중복 대표 캠페인" issues={quality?.issues?.duplicateCampaigns || []} />
        <IssueList title="오래된 보존 캠페인" issues={quality?.issues?.staleCampaigns || []} />
      </div>
    </div>
  );
}

export default OpsPage;
