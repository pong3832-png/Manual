import Link from "next/link";
import { SEO_LANDING_PAGES, getLandingPage } from "../seo/landingPages";
import {
  countCampaignsForLanding,
  formatSnapshotUpdatedAt,
  getCampaignsForLanding,
  getSnapshotUpdatedAt,
} from "../seo/seoCampaignData";
import { absoluteUrl, DEFAULT_SEO_DESCRIPTION, SITE_NAME } from "../seo/siteConfig";

export const metadata = {
  title: "전국 체험단 캠페인 모아보기",
  description: DEFAULT_SEO_DESCRIPTION,
  alternates: {
    canonical: absoluteUrl("/"),
  },
};

const FEATURED_SECTIONS = [
  {
    id: "home-deadline",
    label: "마감 임박",
    title: "오늘 마감 체험단",
    href: "/오늘마감-체험단",
    appHref: "/app?tab=explore&preset=deadline",
    description: "신청 기한이 가까운 캠페인을 먼저 확인해 놓치기 쉬운 모집글을 빠르게 고릅니다.",
    landingSlug: "오늘마감-체험단",
  },
  {
    id: "home-seoul-food",
    label: "지역 추천",
    title: "서울 맛집 체험단",
    href: "/서울-맛집-체험단",
    appHref: "/app?tab=explore&province=서울&category=맛집",
    description: "서울 지역 맛집 방문형 캠페인을 지역, 마감일, 제공내역 기준으로 살펴봅니다.",
    landingSlug: "서울-맛집-체험단",
  },
  {
    id: "home-platforms",
    label: "플랫폼별",
    title: "디너의여왕 체험단",
    href: "/디너의여왕-체험단",
    appHref: "/app?tab=explore&platform=dinner",
    description: "디너의여왕 캠페인을 제공내역과 모집 상태 중심으로 확인합니다.",
    landingSlug: "디너의여왕-체험단",
  },
];

const SEARCH_ENTRY_LINKS = [
  { label: "전체 체험단", href: "/체험단" },
  { label: "블로그 체험단", href: "/블로그체험단" },
  { label: "인스타 체험단", href: "/인스타체험단" },
  { label: "맛집 체험단", href: "/맛집체험단" },
  { label: "카페 체험단", href: "/카페체험단" },
  { label: "뷰티 체험단", href: "/뷰티체험단" },
  { label: "레뷰 체험단", href: "/레뷰-체험단" },
  { label: "미블 체험단", href: "/미블-체험단" },
  { label: "강남 맛집 체험단", href: "/강남-맛집-체험단" },
  { label: "부산 카페 체험단", href: "/부산-카페-체험단" },
  { label: "배송형 체험단", href: "/배송형-체험단" },
  { label: "제품 체험단", href: "/제품-체험단" },
];

function countOpenCampaigns(page) {
  return countCampaignsForLanding(page);
}

function getSectionCampaigns(section) {
  const page = getLandingPage(section.landingSlug);
  return {
    page,
    campaigns: page ? getCampaignsForLanding(page, 3) : [],
    count: page ? countOpenCampaigns(page) : 0,
  };
}

export default function HomeSeoPage() {
  const allCampaignPage = getLandingPage("체험단") || SEO_LANDING_PAGES[0];
  const allCampaigns = countOpenCampaigns(allCampaignPage);
  const updatedAt = getSnapshotUpdatedAt();
  const displayUpdatedAt = formatSnapshotUpdatedAt(updatedAt);
  const sections = FEATURED_SECTIONS.map((section) => ({
    ...section,
    ...getSectionCampaigns(section),
  }));
  const visibleSections = sections.filter((section) => section.count > 0 && section.campaigns.length > 0);
  const deadlineCount = sections.find((section) => section.id === "home-deadline")?.count || 0;
  const dinnerqueenCount = sections.find((section) => section.id === "home-platforms")?.count || 0;

  return (
    <main className="seo-page home-page">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero-copy">
          <p className="seo-eyebrow">{SITE_NAME}</p>
          <h1 id="home-title">체험단 캠페인을 한 곳에서 비교하고 바로 확인하세요</h1>
          <p>
            맛집, 카페, 뷰티, 생활 캠페인의 마감일과 제공내역, 지역, 경쟁률을 한 화면에서 비교하고
            원문 신청 페이지로 이동할 수 있습니다.
          </p>
          <div className="home-actions" aria-label="주요 이동">
            <Link className="primary-action" href="/app?tab=explore">
              캠페인 검색하기
            </Link>
            <Link className="secondary-action" href="/오늘마감-체험단">
              오늘 마감 보기
            </Link>
          </div>
        </div>
        <div className="home-summary" aria-label="캠페인 현황">
          <div>
            <strong>{allCampaigns.toLocaleString("ko-KR")}</strong>
            <span>확인 가능한 공개 캠페인</span>
          </div>
          <div>
            <strong>{deadlineCount.toLocaleString("ko-KR")}</strong>
            <span>마감 임박 후보</span>
          </div>
          <div>
            <strong>{dinnerqueenCount.toLocaleString("ko-KR")}</strong>
            <span>디너의여왕 캠페인</span>
          </div>
          <p>최근 업데이트: {displayUpdatedAt}</p>
        </div>
      </section>

      <section className="seo-section home-section" aria-labelledby="search-entry-title">
        <div className="section-heading">
          <p className="seo-eyebrow">검색 의도별 입구</p>
          <h2 id="search-entry-title">자주 찾는 체험단 주제로 바로 이동</h2>
        </div>
        <div className="seo-link-grid home-link-grid">
          {SEARCH_ENTRY_LINKS.map((entry) => (
            <Link key={entry.href} href={entry.href}>
              {entry.label}
            </Link>
          ))}
        </div>
      </section>

      {visibleSections.length > 0 && (
        <section className="seo-section home-section" aria-labelledby="featured-title">
          <div className="section-heading">
            <p className="seo-eyebrow">추천 경로</p>
            <h2 id="featured-title">데이터가 확인된 캠페인부터 보기</h2>
          </div>
          <div className="home-feature-grid">
            {visibleSections.map((section) => (
              <article className="home-feature-card" id={section.id} key={section.id}>
                <div className="feature-card-head">
                  <span>{section.label}</span>
                  <strong>{section.count.toLocaleString("ko-KR")}건</strong>
                </div>
                <h3>{section.title}</h3>
                <p>{section.description}</p>
                <ul>
                  {section.campaigns.map((campaign) => (
                    <li key={campaign.id}>
                      <strong>{campaign.title}</strong>
                      <span>{[campaign.platform, campaign.province, campaign.city].filter(Boolean).join(" · ")}</span>
                    </li>
                  ))}
                </ul>
                <div className="feature-card-actions">
                  <Link href={section.href}>랜딩 보기</Link>
                  <Link href={section.appHref}>앱에서 필터 보기</Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="seo-section home-section home-process" aria-labelledby="process-title">
        <div className="section-heading">
          <p className="seo-eyebrow">사용 흐름</p>
          <h2 id="process-title">첫 화면에서 검색 앱까지 끊기지 않게 연결</h2>
        </div>
        <ol>
          <li>
            <strong>관심 주제 선택</strong>
            <span>마감 임박, 지역, 플랫폼, 채널별 랜딩에서 후보를 좁힙니다.</span>
          </li>
          <li>
            <strong>검색 앱에서 비교</strong>
            <span>기존 앱의 필터, 지도, 상세 모달로 조건을 더 구체화합니다.</span>
          </li>
          <li>
            <strong>신청 전 최종 확인</strong>
            <span>제공내역과 모집 조건은 원문 신청 페이지에서 마지막으로 확인합니다.</span>
          </li>
        </ol>
      </section>
    </main>
  );
}
