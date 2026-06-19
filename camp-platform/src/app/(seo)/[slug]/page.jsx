import Link from "next/link";
import { notFound } from "next/navigation";
import { SEO_LANDING_PAGES, getLandingPage } from "../../../seo/landingPages";
import { getCampaignsForLanding, getSnapshotUpdatedAt } from "../../../seo/seoCampaignData";
import { absoluteUrl } from "../../../seo/siteConfig";

export function generateStaticParams() {
  return SEO_LANDING_PAGES.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const page = getLandingPage(slug);
  if (!page) return {};

  return {
    title: page.title,
    description: page.description,
    alternates: {
      canonical: absoluteUrl(`/${page.slug}`),
    },
    openGraph: {
      title: page.title,
      description: page.description,
      url: absoluteUrl(`/${page.slug}`),
    },
  };
}

export default async function SeoLandingPage({ params }) {
  const { slug } = await params;
  const page = getLandingPage(slug);
  if (!page) notFound();

  const campaigns = getCampaignsForLanding(page, 12);
  const updatedAt = getSnapshotUpdatedAt();
  const relatedPages = page.relatedSlugs.map((relatedSlug) => getLandingPage(relatedSlug)).filter(Boolean);

  return (
    <main className="seo-page">
      <nav className="seo-breadcrumb" aria-label="breadcrumb">
        <Link href="/">체험모아</Link>
        <span>{page.h1}</span>
      </nav>
      <section className="seo-hero">
        <h1>{page.h1}</h1>
        <p>{page.intro}</p>
        <Link className="primary-action" href={`/app${page.appQuery}`}>
          사이트에서 조건별로 보기
        </Link>
      </section>
      <section className="seo-section" aria-labelledby="campaign-list-title">
        <h2 id="campaign-list-title">관련 캠페인</h2>
        <p className="seo-muted">최근 업데이트: {updatedAt}. 모집 조건은 원문 신청 페이지에서 최종 확인하세요.</p>
        <ul className="seo-campaign-list">
          {campaigns.map((campaign) => (
            <li key={campaign.id}>
              <strong>{campaign.title}</strong>
              <span>{[campaign.platform, campaign.category, campaign.province, campaign.city].filter(Boolean).join(" · ")}</span>
              {campaign.reward ? <small>{campaign.reward}</small> : null}
              {campaign.dDay !== null ? <small>D-{campaign.dDay}</small> : null}
            </li>
          ))}
        </ul>
        {!campaigns.length ? (
          <p className="seo-muted">현재 이 조건에 맞는 공개 캠페인이 적습니다. 전체 탐색에서 조건을 넓혀 확인하세요.</p>
        ) : null}
      </section>
      <section className="seo-section" aria-labelledby="related-title">
        <h2 id="related-title">같이 보면 좋은 체험단 검색</h2>
        <div className="seo-link-grid">
          {relatedPages.map((related) => (
            <Link key={related.slug} href={`/${related.slug}`}>
              {related.h1}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
