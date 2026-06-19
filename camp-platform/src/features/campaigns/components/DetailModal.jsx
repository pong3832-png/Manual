import { PLATFORMS } from "../../../shared/config/platforms";
import { getCampaignBenefitLabel, getCampaignDisplayProfile } from "../lib/campaigns";

function DetailModal({ c, onClose, onApply, isFav, onFav, hasApplicationMessage = false }) {
  const platform = PLATFORMS.find((item) => item.id === c.platformId);
  const display = getCampaignDisplayProfile(c);
  const isUrgent = display.isUrgent;
  const showLocationInfo = display.locationLabel && display.locationLabel !== display.modeLabel;
  const benefitLabel = getCampaignBenefitLabel(c, { maxLength: 180 });

  const infoRows = [
    showLocationInfo ? ["위치", display.locationLabel] : null,
    display.snsLabel ? ["SNS", display.snsLabel] : null,
    ["방식", display.modeLabel],
    ["마감", display.dDayLabel],
    ["지원/모집", `${c.applyCount || 0} / ${c.selectedCount || 0}명`],
    ["경쟁률", `${((c.applyCount || 0) / (c.selectedCount || 1)).toFixed(1)}x`],
  ].filter(Boolean);

  return (
    <div className="dmodal-backdrop" onClick={onClose}>
      <div className="dmodal-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="dmodal-handle-bar" />

        <div className="dmodal-body">
          <div className="dmodal-header">
            <div className="dmodal-pills">
              <span
                className="dmodal-pill dmodal-pill--platform"
                style={{ background: platform?.color || "var(--color-text-primary)" }}
              >
                {platform?.name || c.platform}
              </span>
              <span className="dmodal-pill">{c.category}</span>
              {display.locationLabel !== display.modeLabel && (
                <span className="dmodal-pill">{display.locationLabel}</span>
              )}
              {isUrgent && <span className="dmodal-pill dmodal-pill--urgent">{display.dDayLabel} 마감</span>}
            </div>
            <button
              type="button"
              className="dmodal-close"
              aria-label="닫기"
              onClick={onClose}
            >
              <span className="dmodal-close-icon" aria-hidden="true" />
            </button>
          </div>

          <h2 className="dmodal-title">{c.title}</h2>

          {benefitLabel && (
            <div className="dmodal-provision">
              <span className="dmodal-provision-label">제공 내역</span>
              <span className="dmodal-provision-value">{benefitLabel}</span>
            </div>
          )}

          <div className="dmodal-info-grid">
            {infoRows.map(([label, value]) => (
              <div key={label} className="dmodal-info-cell">
                <div className="dmodal-info-label">{label}</div>
                <div className="dmodal-info-value">{value}</div>
              </div>
            ))}
          </div>

          <div className="dmodal-actions">
            <button
              type="button"
              className="dmodal-btn-apply"
              onClick={() => onApply(c)}
            >
              {hasApplicationMessage ? "멘트 복사 후 원본으로 이동" : "원본 플랫폼에서 신청하기"}
            </button>
            <button
              type="button"
              className={`dmodal-btn-fav${isFav ? " dmodal-btn-fav--active" : ""}`}
              aria-label={isFav ? "즐겨찾기 해제" : "즐겨찾기 추가"}
              aria-pressed={isFav}
              onClick={() => onFav(c)}
            >
              <span className="dmodal-heart" aria-hidden="true">{isFav ? "♥" : "♡"}</span>
            </button>
          </div>

          <p className="dmodal-hint">CAMP는 캠페인을 모아 보여주며, 실제 신청은 원본 플랫폼에서 진행됩니다</p>
        </div>
      </div>
    </div>
  );
}

export default DetailModal;
