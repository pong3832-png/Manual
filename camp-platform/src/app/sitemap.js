import { SEO_LANDING_PAGES } from "../seo/landingPages.js";
import { getSnapshotUpdatedAt } from "../seo/seoCampaignData.js";
import { absoluteUrl } from "../seo/siteConfig.js";

function sitemapUrl(path) {
  return encodeURI(absoluteUrl(path));
}

export default function sitemap() {
  const parsedUpdatedAt = Date.parse(getSnapshotUpdatedAt());
  const lastModified = new Date(Number.isFinite(parsedUpdatedAt) ? parsedUpdatedAt : Date.now());
  const routes = [
    { url: sitemapUrl("/"), priority: 1 },
    { url: sitemapUrl("/app"), priority: 0.8 },
    ...SEO_LANDING_PAGES.map((page) => ({
      url: sitemapUrl(`/${page.slug}`),
      priority: page.slug === "체험단" ? 0.9 : 0.75,
    })),
  ];

  return routes.map((route) => ({
    url: route.url,
    lastModified,
    changeFrequency: "daily",
    priority: route.priority,
  }));
}
