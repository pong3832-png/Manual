import { Fragment, memo, useEffect, useRef } from "react";
import { PLATFORMS } from "../../../shared/config/platforms";
import { getCampaignBenefitLabel, getCampaignDisplayProfile } from "../lib/campaigns";

const PLATFORM_BY_ID = new Map(PLATFORMS.map((item) => [item.id, item]));

function CampaignCard({ c, onSelect, isFav, onFav, onApply, onImpression, impressionContext }) {
  const cardRef = useRef(null);
  const reportedImpressionRef = useRef(false);
  const platform = PLATFORM_BY_ID.get(c.platformId);
  const display = getCampaignDisplayProfile(c);
  const isUrgent = display.isUrgent;
  const compRatio = ((c.applyCount || 0) / (c.selectedCount || 1)).toFixed(1);
  const compRatioValue = Number(compRatio);
  const benefitLabel = getCampaignBenefitLabel(c);
  const externalWindowFeatures = c.platformId === "mrblog" ? "noopener" : "noopener,noreferrer";
  const metaParts = [...new Set([display.locationLabel, display.snsLabel, display.modeLabel].filter(Boolean))];
  const reasonLabel = isUrgent
    ? "마감 임박"
    : compRatioValue < 30
      ? "경쟁 낮음"
      : Number(c.selectedCount || 0) >= 5
        ? "모집 넉넉"
        : "조건 확인";

  useEffect(() => {
    if (!onImpression || reportedImpressionRef.current) return undefined;
    if (typeof IntersectionObserver === "undefined") return undefined;

    const node = cardRef.current;
    if (!node) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting || reportedImpressionRef.current) return;
        reportedImpressionRef.current = true;
        onImpression(c, impressionContext);
        observer.disconnect();
      },
      { rootMargin: "0px 0px -12% 0px", threshold: 0.35 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [c, impressionContext, onImpression]);

  return (
    <article
      ref={cardRef}
      className={`ccard${isUrgent ? " ccard--urgent" : ""}`}
      onClick={() => onSelect(c)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(c); }
      }}
    >
      <div className="ccard-top">
        <span
          className="ccard-platform"
          style={{ color: platform?.color || "var(--text-secondary)" }}
        >
          {platform?.name || c.platform}
        </span>
        <span className="ccard-cat">{c.category}</span>
        <span className="ccard-reason">{reasonLabel}</span>
        <span className={`ccard-dday${isUrgent ? " ccard-dday--urgent" : ""}`}>
          {display.dDayLabel}
        </span>
      </div>

      <div className="ccard-title">{c.title}</div>

      {benefitLabel && (
        <div className="ccard-benefit">
          <span>혜택</span>
          <strong>{benefitLabel}</strong>
        </div>
      )}

      <div className="ccard-meta ccard-meta--primary">
        {metaParts.map((part, index) => (
          <Fragment key={part}>
            {index > 0 && <span className="ccard-dot">·</span>}
            <span className={index === 0 ? "ccard-location" : undefined}>{part}</span>
          </Fragment>
        ))}
      </div>

      <div className="ccard-metrics">
        <span>모집 {c.selectedCount || 0}명</span>
        <span>신청 {c.applyCount || 0}명</span>
        <span className={compRatioValue < 30 ? "ccard-metric-good" : ""}>경쟁 {compRatio}x</span>
      </div>

      <div className="ccard-actions">
        <button
          type="button"
          className={`ccard-save${isFav ? " ccard-save--active" : ""}`}
          aria-label={isFav ? "즐겨찾기 해제" : "즐겨찾기 추가"}
          onClick={(e) => { e.stopPropagation(); onFav(c); }}
        >
          {isFav ? "저장됨" : "저장"}
        </button>
        <button
          type="button"
          className="ccard-orig"
          aria-label={`${platform?.name || c.platform || "원본 플랫폼"}에서 신청 페이지 열기`}
          onClick={(e) => {
            e.stopPropagation();
            if (onApply) {
              onApply(c);
              return;
            }
            window.open(c.url, "_blank", externalWindowFeatures);
          }}
        >
          원본 신청
        </button>
      </div>
    </article>
  );
}

export default memo(CampaignCard);
