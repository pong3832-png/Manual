import "../index.css";
import "./compact-ui.css";
import "./App.css";
import "./seo.css";
import { DEFAULT_SEO_DESCRIPTION, SEO_SITE_URL, SITE_NAME } from "../seo/siteConfig";

export const metadata = {
  metadataBase: new URL(SEO_SITE_URL),
  applicationName: SITE_NAME,
  title: {
    default: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    template: `%s | ${SITE_NAME}`,
  },
  description: DEFAULT_SEO_DESCRIPTION,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: SITE_NAME,
    url: SEO_SITE_URL,
    title: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    description: DEFAULT_SEO_DESCRIPTION,
  },
  twitter: {
    card: "summary",
    title: `${SITE_NAME} | 전국 체험단 캠페인 모음`,
    description: DEFAULT_SEO_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#C1440E",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
