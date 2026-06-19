const DEFAULT_SEO_SITE_URL = "https://camp-platform-liart.vercel.app";

function normalizeSiteUrl(value) {
  const normalized = String(value || "").trim().replace(/\/+$/, "");
  return normalized || DEFAULT_SEO_SITE_URL;
}

export const SEO_SITE_URL = normalizeSiteUrl(
  process.env.NEXT_PUBLIC_PUBLIC_SITE_URL || process.env.VITE_PUBLIC_SITE_URL,
);
export const SITE_NAME = "CheheomMoa";
export const DEFAULT_SEO_DESCRIPTION =
  "맛집, 카페, 뷰티, 숙박, 생활용품 체험단 캠페인을 한 곳에서 찾고 비교해보세요.";

export function absoluteUrl(path = "/") {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${SEO_SITE_URL}${normalizedPath}`;
}
