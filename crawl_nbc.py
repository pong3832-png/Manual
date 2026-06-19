import asyncio
import sys
from crawl4ai import AsyncWebCrawler


TARGET_URL = "https://www.nbcnews.com/business"


async def main():
    print("=" * 80)
    print("[환경 확인]")
    print(f"Python: {sys.version}")
    print(f"URL: {TARGET_URL}")
    print("=" * 80)

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=TARGET_URL)

            print("\n" + "=" * 80)
            print("[크롤링 결과 - Markdown]")
            print("=" * 80)

            markdown = getattr(result, "markdown", None)

            if markdown:
                print(markdown)
            else:
                print("[경고] markdown 결과가 비어 있습니다.")
                print("[디버그] result 객체:")
                print(result)

    except Exception as e:
        print("\n" + "=" * 80)
        print("[에러 발생]")
        print("=" * 80)
        print(f"에러 타입: {type(e).__name__}")
        print(f"에러 내용: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())