import { useEffect, useRef } from "react";
import useAds from "../hooks/useAds";
import { trackAdEvent } from "../lib/ads";
import { SITE_NAME } from "../../../shared/config/site";

function getProviderLabel(provider) {
  if (provider === "coupang") return "Coupang";
  if (provider === "internal") return SITE_NAME;
  return provider || "Sponsor";
}

function AdBanner({ slotId, context = {}, variant = "default" }) {
  const ad = useAds(slotId, context);
  const bannerRef = useRef(null);
  const impressedRef = useRef("");
  const isExternalTarget = /^https?:\/\//i.test(ad?.targetUrl || "") || /^mailto:/i.test(ad?.targetUrl || "");

  useEffect(() => {
    if (!ad || !bannerRef.current || impressedRef.current === ad.id) return undefined;

    const node = bannerRef.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        impressedRef.current = ad.id;
        trackAdEvent(ad, slotId, "impression", { context, variant });
        observer.disconnect();
      },
      { threshold: 0.35 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [ad, context, slotId, variant]);

  if (!ad) return null;

  return (
    <aside
      ref={bannerRef}
      className={`ad-banner ad-banner--${variant} ad-banner--${ad.provider}`}
      aria-label={`${ad.label}: ${ad.title}`}
    >
      <a
        className="ad-banner-link"
        href={ad.targetUrl}
        target={isExternalTarget ? "_blank" : undefined}
        rel={isExternalTarget ? "sponsored noopener noreferrer" : undefined}
        onClick={() => trackAdEvent(ad, slotId, "click", { context, variant })}
      >
        {ad.imageUrl && (
          <span className="ad-banner-media">
            <img src={ad.imageUrl} alt="" loading="lazy" />
          </span>
        )}
        <span className="ad-banner-body">
          <span className="ad-banner-topline">
            <span className="ad-banner-label">{ad.label}</span>
            <span className="ad-banner-provider">{ad.sponsorName || getProviderLabel(ad.provider)}</span>
          </span>
          <strong>{ad.title}</strong>
          {ad.description && <span className="ad-banner-description">{ad.description}</span>}
          {ad.disclosure && <span className="ad-banner-disclosure">{ad.disclosure}</span>}
        </span>
        <span className="ad-banner-cta">{ad.cta}</span>
      </a>
    </aside>
  );
}

export default AdBanner;
