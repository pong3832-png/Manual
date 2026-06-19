import { SEO_SITE_URL } from "../seo/siteConfig.js";

export default function robots() {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: [
      `${SEO_SITE_URL}/sitemap.xml`,
      `${SEO_SITE_URL}/sitemap-pages.xml`,
    ],
  };
}
