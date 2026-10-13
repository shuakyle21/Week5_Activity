"""Catalogue discovery: parse catalogue HTML, collect book links
(relative -> absolute via urljoin), follow the site's own "next" link
through the configured page count, then stop. De-duplicated."""

import logging
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .config import ScraperConfig
from .fetch import fetch_page

logger = logging.getLogger(__name__)


def discover_catalogue_pages(
    current_page_url: str,
    page_html: str,
    config: ScraperConfig,
    stats: dict | None = None,
) -> tuple[set[str], dict[str, str]]:
    source_page_map: dict[str, str] = {}
    seen_links: set[str] = set()
    page_number = 1

    while page_number <= config.catalogue_pages:
        page = BeautifulSoup(page_html, "html.parser")

        for a in page.select("ol.row li h3 a"):
            absolute_url = urljoin(current_page_url, a.get("href"))
            if absolute_url not in seen_links:
                seen_links.add(absolute_url)
                source_page_map[absolute_url] = current_page_url

        if page_number == config.catalogue_pages:
            logger.info(
                "CHECKPOINT: catalogue_pages=%d, discovered=%d, unique_urls=%d",
                page_number,
                len(seen_links),
                len(seen_links),
            )
            break

        next_tag = page.select_one("ul.pager li.next a")
        if next_tag is None:
            logger.warning("CHECKPOINT FAILED: no next link on %s", current_page_url)
            break
        next_url = urljoin(current_page_url, next_tag.get("href"))
        page_html, _ = fetch_page(next_url, config, stats)
        current_page_url = next_url
        page_number += 1

    return seen_links, source_page_map
