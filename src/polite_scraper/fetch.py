"""Fetch once, cache once. Download with an honest User-Agent + timeout,
proceed only on HTTP 200, save HTML to the cache dir, reread the file on
later runs (no network, no delay)."""

import hashlib
import logging
import time

import requests

from .config import ScraperConfig
from .errors import RetryableFetchError, TerminalFetchError

logger = logging.getLogger(__name__)


def _request_once(url: str, config: ScraperConfig) -> requests.Response:
    try:
        return requests.get(
            url,
            headers={"User-Agent": config.user_agent},
            timeout=config.timeout_seconds,
        )
    except (requests.Timeout, requests.ConnectionError) as e:
        raise RetryableFetchError(f"Network failure: {url} ({e})") from e
    finally:
        time.sleep(config.request_delay_seconds)


def fetch_page(
    url: str, config: ScraperConfig, stats: dict | None = None
) -> tuple[str, bool]:
    """Return (html, fetched_from_network). Updates stats counters in place."""
    cache_file = config.cache_dir / f"catalogue-{hashlib.sha256(url.encode()).hexdigest()}"

    if not config.no_cache and cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
        logger.info("CACHE HIT: %s, size=%d", cache_file, len(html))
        if stats is not None:
            stats["cache_hits"] += 1
        return html, False

    # Unknown outcome (timeout / connection cut) -> one more knock, then give up.
    try:
        response = _request_once(url, config)
    except RetryableFetchError:
        logger.info("Network failure, retrying once: %s", url)
        time.sleep(config.retry_wait_seconds)
        response = _request_once(url, config)  # raises again if still failing

    # Client errors: the server answered — asking again changes nothing.
    if 400 <= response.status_code < 500:
        raise TerminalFetchError(
            f"HTTP {response.status_code}, never retry: {url}",
            status_code=response.status_code,
        )
    # Server errors: outcome unclear, so exactly one retry, then give up.
    if response.status_code >= 500:
        logger.info("Server error %s, retrying once: %s", response.status_code, url)
        time.sleep(config.retry_wait_seconds)
        response = _request_once(url, config)
        if response.status_code != 200:
            raise RetryableFetchError(
                f"Server error persists after retry: {url}: HTTP {response.status_code}"
            )
    if response.status_code != 200:
        raise TerminalFetchError(
            f"HTTP {response.status_code}, never retry: {url}",
            status_code=response.status_code,
        )

    # Server sends text/html without charset; page is UTF-8 (meta tag).
    # Force detection so text doesn't mojibake (Â£ instead of £).
    response.encoding = response.apparent_encoding
    html = response.text

    cache_file.write_text(html, encoding="utf-8")
    logger.info("FETCH: %s, size=%d", url, len(html))
    if stats is not None:
        stats["pages_fetched"] += 1
    return html, True
