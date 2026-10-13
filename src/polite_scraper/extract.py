"""Detail extraction: one book page -> raw record dict + provenance.
Selectors stay scoped to div.product_main, never the whole document.
Missing description -> None (never invented)."""

from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from .config import ScraperConfig
from .fetch import fetch_page


def extract_book_details(
    product_url: str,
    source_page: str | None,
    config: ScraperConfig,
    stats: dict | None = None,
) -> dict[str, Any]:
    html, _ = fetch_page(product_url, config, stats)
    soup = BeautifulSoup(html, "html.parser")
    main_tag = soup.select_one("div.product_main")

    title_tag = main_tag.select_one("h1") if main_tag else None
    price_tag = main_tag.select_one("p.price_color") if main_tag else None
    availability_tag = (
        main_tag.select_one("p.instock.availability") if main_tag else None
    )
    rating_tag = main_tag.select_one("p.star-rating") if main_tag else None
    description_tag = soup.select_one("#product_description + p")

    rating_classes = rating_tag.get("class", []) if rating_tag else []
    rating_text = next(
        (c for c in rating_classes if c != "star-rating"),
        None,
    )

    return {
        "title": title_tag.get_text(strip=True) if title_tag else None,
        "product_url": product_url,
        "price_text": price_tag.get_text(strip=True) if price_tag else None,
        "availability_text": (
            availability_tag.get_text(" ", strip=True) if availability_tag else None
        ),
        "rating_text": rating_text,
        "description": (
            description_tag.get_text(" ", strip=True) if description_tag else None
        ),
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
