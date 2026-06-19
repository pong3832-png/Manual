import asyncio
import re
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler


TARGET_URL = "https://www.nbcnews.com/business"


ALLOWED_BUSINESS_PATH_PREFIXES = (
    "/business/",
    "/data-graphics/",
)

ALLOWED_TECH_AI_PATH_PREFIXES = (
    "/tech/tech-news/",
    "/business/markets/",
)


def is_business_article_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()

    if parsed.netloc not in {"www.nbcnews.com", "nbcnews.com"}:
        return False

    if not re.search(r"rcna\d+", path):
        return False

    if path.startswith(ALLOWED_BUSINESS_PATH_PREFIXES):
        return True

    if path.startswith(ALLOWED_TECH_AI_PATH_PREFIXES):
        return True

    return False


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = title.replace("FORSUBSCRIBERS", "").strip()
    return title


def extract_article_links(markdown: str):
    pattern = re.compile(
        r"## \[([^\]]+)\]\((https?://(?:www\.)?nbcnews\.com/[^\)]+)\)"
    )

    seen = set()
    articles = []

    for title, url in pattern.findall(markdown):
        title = clean_title(title)
        url = url.strip()

        if not title:
            continue

        if not is_business_article_url(url):
            continue

        if url in seen:
            continue

        seen.add(url)
        articles.append(
            {
                "title": title,
                "url": url,
            }
        )

    return articles


async def main():
    print("=" * 80)
    print("[NBC Business 관련 기사 링크 추출 시작]")
    print(f"URL: {TARGET_URL}")
    print("=" * 80)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=TARGET_URL)

    markdown = getattr(result, "markdown", "") or ""
    articles = extract_article_links(markdown)

    print(f"\n[추출 기사 수] {len(articles)}개\n")

    for idx, article in enumerate(articles, start=1):
        print(f"{idx}. {article['title']}")
        print(f"   {article['url']}")

    if not articles:
        print("[경고] 기사 링크를 찾지 못했습니다.")
        print("[디버그] Markdown 앞부분 3000자:")
        print(markdown[:3000])


if __name__ == "__main__":
    asyncio.run(main())