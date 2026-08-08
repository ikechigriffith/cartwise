import asyncio
import re
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Retailer, RetailerDataSource

PRICE_PATTERNS = [
    re.compile(r"\$\s?\d+[.,]\d{2}"),
    re.compile(r"TTD\s?\d+[.,]\d{2}", re.I),
    re.compile(r"TT\$\s?\d+[.,]\d{2}", re.I),
]

CATALOG_PATTERNS = [
    re.compile(r"add to cart", re.I),
    re.compile(r"shop online", re.I),
    re.compile(r"products?", re.I),
    re.compile(r"categories", re.I),
    re.compile(r"pdp|product-detail|product", re.I),
]

STOCK_PATTERNS = [
    re.compile(r"in stock", re.I),
    re.compile(r"out of stock", re.I),
    re.compile(r"availability", re.I),
]

LOGIN_PATTERNS = [
    re.compile(r"sign in", re.I),
    re.compile(r"log in", re.I),
    re.compile(r"membership", re.I),
]

API_PATTERNS = [
    re.compile(r"graphql", re.I),
    re.compile(r"api", re.I),
    re.compile(r"commercetools", re.I),
    re.compile(r"bloomreach", re.I),
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def has_any(patterns: list[re.Pattern], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def status_from_signals(has_catalog: bool, has_prices: bool, blocked: bool) -> str:
    if blocked:
        return "blocked"
    if has_catalog and has_prices:
        return "candidate_strong"
    if has_catalog:
        return "candidate_likely"
    return "needs_verification"


async def check_source(page, source: RetailerDataSource) -> dict:
    network_urls: list[str] = []

    def capture_response(response):
        url = response.url
        if any(marker in url.lower() for marker in ["api", "graphql", "commercetools", "bloomreach", "search", "product"]):
            network_urls.append(url)

    page.on("response", capture_response)

    result = {
        "source_id": str(source.id),
        "url": source.source_url,
        "status_code": None,
        "title": None,
        "has_product_catalog": False,
        "has_prices": False,
        "has_stock": False,
        "requires_login": False,
        "api_signals": False,
        "blocked": False,
        "network_urls": [],
        "error": None,
    }

    try:
        response = await page.goto(source.source_url, wait_until="networkidle", timeout=45_000)
        result["status_code"] = response.status if response else None
        title = await page.title()
        html = await page.content()
        text = await page.locator("body").inner_text(timeout=10_000)
        combined = f"{title}\n{html}\n{text}"

        result["title"] = title
        result["has_product_catalog"] = has_any(CATALOG_PATTERNS, combined)
        result["has_prices"] = has_any(PRICE_PATTERNS, combined)
        result["has_stock"] = has_any(STOCK_PATTERNS, combined)
        result["requires_login"] = has_any(LOGIN_PATTERNS, combined)
        result["api_signals"] = has_any(API_PATTERNS, combined) or bool(network_urls)
        result["blocked"] = (result["status_code"] in {401, 403, 429}) or "access denied" in combined.lower()
        result["network_urls"] = sorted(set(network_urls))[:20]
    except Exception as exc:  # noqa: BLE001 - script should record failures, not crash entire run
        result["error"] = str(exc)
        result["blocked"] = "timeout" not in str(exc).lower()

    return result


async def main() -> None:
    checked_at = now_utc()
    with SessionLocal() as session:
        sources = session.scalars(
            select(RetailerDataSource).join(Retailer).order_by(Retailer.name)
        ).all()

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        for source in sources:
            page = await context.new_page()
            result = await check_source(page, source)
            await page.close()
            results.append(result)
        await browser.close()

    with SessionLocal() as session:
        for result in results:
            source = session.get(RetailerDataSource, result["source_id"])
            if not source:
                continue
            source.has_product_catalog = result["has_product_catalog"]
            source.has_prices = result["has_prices"]
            source.has_stock = result["has_stock"]
            source.requires_login = result["requires_login"]
            source.scrape_status = status_from_signals(
                result["has_product_catalog"], result["has_prices"], result["blocked"]
            )
            if source.scrape_status == "candidate_strong":
                source.confidence = "high"
            elif source.scrape_status == "candidate_likely":
                source.confidence = "medium"
            elif source.scrape_status == "blocked":
                source.confidence = "low"
            else:
                source.confidence = "unknown"
            source.last_checked_at = checked_at
            source.notes = (
                f"Playwright check. status={result['status_code']} title={result['title']!r} "
                f"api_signals={result['api_signals']} error={result['error']!r} "
                f"network_urls={result['network_urls']}"
            )
        session.commit()

    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
