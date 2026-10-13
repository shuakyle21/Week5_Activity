"""Pipeline: validate -> de-dupe by canonical URL -> overwrite.
Overwrite (never append) books.json so reruns stay at 60, not 120."""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from .config import ScraperConfig
from .discover import discover_catalogue_pages
from .errors import RetryableFetchError, TerminalFetchError
from .extract import extract_book_details
from .fetch import fetch_page
from .models import Book, normalize_price

logger = logging.getLogger(__name__)


def clean_data(
    records: list[dict[str, Any]], config: ScraperConfig
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate records, write books/errors JSON. Returns (books, errors)."""
    valid_records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for raw in records:
        try:
            book = Book.model_validate({**raw, "price_gbp": normalize_price(raw.get("price_text"))})
            valid_records.append(book.model_dump(mode="json"))
        except (ValueError, ValidationError) as e:
            errors.append({"product_url": raw.get("product_url"), "reason": str(e)})

    books = list({r["product_url"]: r for r in valid_records}.values())

    config.books_file.write_text(
        json.dumps(books, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    config.errors_file.write_text(
        json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return books, errors


def run(config: ScraperConfig) -> dict[str, Any]:
    """Execute the full pipeline. Returns the run report dict."""
    config.ensure_dirs()
    start_time = datetime.now(timezone.utc)
    stats = {"pages_fetched": 0, "cache_hits": 0}

    first_url = config.base_url + "/page-1.html"
    html_page, _ = fetch_page(first_url, config, stats)
    links, source_page_map = discover_catalogue_pages(
        first_url, html_page, config, stats
    )

    # Bulkhead loop: each detail page is isolated (fail -> failed_pages, continue).
    records: list[dict[str, Any]] = []
    failed_pages: list[dict[str, Any]] = []
    for product_url in sorted(links):
        try:
            records.append(
                extract_book_details(
                    product_url, source_page_map.get(product_url), config, stats
                )
            )
        except (RetryableFetchError, TerminalFetchError, ValueError) as e:
            failed_pages.append({
                "product_url": product_url,
                "reason": f"{type(e).__name__}: {e}",
            })
            logger.warning("SKIP %s: %s", product_url, e)

    logger.info("CHECKPOINT: detail_pages = %d", len(records))
    books, errors = clean_data(records, config)
    logger.info("CHECKPOINT: books.json records = %d", len(books))

    report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": round(
            (datetime.now(timezone.utc) - start_time).total_seconds(), 2
        ),
        "catalogue_pages": config.catalogue_pages,
        "detail_pages_attempted": len(links),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": failed_pages,
        "failed_pages_count": len(failed_pages),
    }
    config.run_report_file.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("CHECKPOINT: failed_pages = %d", len(failed_pages))
    return report
