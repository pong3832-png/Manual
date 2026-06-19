import { publicEnv } from "./publicEnv.js";

const fallbackOrigin = typeof window !== "undefined" ? window.location.origin : "";

export const SITE_NAME = publicEnv.publicSiteName || "CheheomMoa";
export const PUBLIC_SITE_URL = publicEnv.publicSiteUrl || fallbackOrigin;
export const PUBLIC_CONTACT_EMAIL = String(publicEnv.publicContactEmail || "").trim();
export const PUBLIC_OPERATOR_NAME = String(publicEnv.publicOperatorName || "").trim();
export const LEGAL_UPDATED_AT = "2026-05-13";

export function getContactMailto(subject = `${SITE_NAME} 문의`) {
  if (!PUBLIC_CONTACT_EMAIL) return "";
  return `mailto:${PUBLIC_CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}`;
}
