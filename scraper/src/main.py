import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urljoin, unquote

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, field_validator

# ---- Stage 0 (code counterpart): target + politeness config ----
# The classification itself lives in scraper/README.md ("Target classification").
# These constants are its enforcement: what we fetch, who we say we are,
# and how slowly we go. Change scope or politeness here, nowhere else.
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
BASE_URL = "https://books.toscrape.com/catalogue"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/shuakyle21/Week5_Activity)"
REQUEST_DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 5
RETRY_WAIT_SECONDS = 1.0

## SET OUTPUT DIRECTORY
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
RUN_REPORT_FILE = OUTPUT_DIR / "run-report.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---- Stage 5: failure taxonomy ----
# Two names so the caller can decide: retry when the outcome is UNKNOWN
# (timeout / cut connection / 5xx), never retry when the server ANSWERED
# (404 missing, 403 refused, other 4xx). Names carry the policy.
class RetryableFetchError(RuntimeError):
    pass

class TerminalFetchError(RuntimeError):
    pass


## Shared helper (used by Stages 1, 4, 5): ensure a directory exists.
## Check cache directory if exists, if not, create it
def ensure_directory(path: str | Path) -> str | None:
    # Create the directory if it doesn't exist; do nothing if it does.
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise FileExistsError(f"{path} exists but is not a directory")
        return None
    else:
        os.makedirs(path)
        return f"Created directory: {path}"


def slug_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    parts = [p for p in path.split("/") if p and p.lower() != "index.html"]
    return parts[-1] if parts else hashlib.md5(url.encode()).hexdigest()


# ---- Stage 1: fetch once, cache once ----
# Download with an honest User-Agent + timeout, proceed only on HTTP 200,
# save the HTML to cache/, reread the file on later runs (no network, no delay).
# The retry logic inside fetch_page belongs to Stage 5; the caching contract
# described here is unchanged by it.
## Fetch Page with agent
def _request_once(url: str) -> requests.Response:
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    except (requests.Timeout, requests.ConnectionError) as e:
        raise RetryableFetchError(f"Network failure: {url} ({e})") from e

## Stage 1: Fetch the page details
def fetch_page(url: str, stats: dict | None = None):
    # Set the cache file name from the url
    clean_str = slug_from_url(url)
    cache_file = os.path.join(CACHE_DIR, f"catalogue-{clean_str}")  # Final file name

    # Check if cache hit or miss, read from disk
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            html_ = f.read()
            print(f"CACHE HIT 💾: {cache_file}, size={len(html_)}")
            if stats is not None:
                stats["cache_hits"] += 1
            return html_, False

    # Unknown outcome (timeout / connection cut) -> one more knock, then give up.
    try:
        response = _request_once(url)
    except RetryableFetchError:
        print(f"Network failure, retrying once: {url}")
        time.sleep(RETRY_WAIT_SECONDS)
        response = _request_once(url)  # raises again if still failing

    # Client errors (404 missing, 403 refused, and any other 4xx):
    # the server answered — asking again changes nothing. Never retry.
    if 400 <= response.status_code < 500:
        raise TerminalFetchError(f"HTTP {response.status_code}, never retry: {url}")
    # Server errors: outcome unclear, so exactly one retry, then give up.
    if response.status_code >= 500:
        print(f"Server error {response.status_code}, retrying once: {url}")
        time.sleep(RETRY_WAIT_SECONDS)
        response = _request_once(url)
        if response.status_code != 200:
            raise RetryableFetchError(f"Server error persists after retry: {url}: HTTP {response.status_code}")
    if response.status_code != 200:
        raise TerminalFetchError(f"HTTP {response.status_code}, never retry: {url}")

    # Server sends text/html without charset; page is UTF-8 (meta tag).
    # Force detection so response.text doesn't mojibake (Â£ instead of £).
    response.encoding = response.apparent_encoding
    html_ = response.text

    with open(cache_file, "w") as f:
        f.write(html_)
    print(f"FETCH: {url}, size={len(html_)}")
    time.sleep(REQUEST_DELAY_SECONDS)
    if stats is not None:
        stats["pages_fetched"] += 1
    return html_, True


## Stage 2: Discover the catalogue page structure
## Parse catalogue HTML, collect book links (relative -> absolute via urljoin),
## follow the site's own "next" link through page 3, then stop. De-duplicated.
def discover_catalogue_pages(current_page_url: str, page_html: str, stats: dict | None = None):
    source_page_map = {}
    seen_links = set()
    page_number = 1

    while page_number <= 3:
        page = BeautifulSoup(page_html, "html.parser")

        for a in page.select("ol.row li h3 a"):
            ## Get the current page url
            absolute_url = urljoin(current_page_url, a.get("href"))

            if absolute_url not in seen_links:
                seen_links.add(absolute_url)
                source_page_map[absolute_url] = current_page_url

        if page_number == 3:
            print(
                "CHECKPOINT: "
                f"catalogue_pages={page_number}, "
                f"discovered={len(seen_links)}, "
                f"unique_urls={len(seen_links)}"
            )
            break

        next_tag = page.select_one("ul.pager li.next a") ## finds the next link tag

        if next_tag is None:
            print("CHECKPOINT FAILED...")
            break
        else:
            next_url = urljoin(current_page_url, next_tag.get("href"))
            page_html, _ = fetch_page(next_url, stats)
            current_page_url = next_url
            page_number += 1

    return seen_links, source_page_map

# Stage 3: extract the raw records (one book page -> 8-key dict + provenance)
# Selectors stay scoped to div.product_main, never the whole document.
# Missing description -> None (never invented).
# Stage 3 extract book details
def extract_book_details(
    product_url: str, source_page: str | None, stats: dict | None = None
) -> dict[str, Any]:
    html, _ = fetch_page(product_url, stats)
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
        (class_name for class_name in rating_classes if class_name != "star-rating"),
        None,
    )

    return {
        "title": title_tag.get_text(strip=True) if title_tag else None,
        "product_url": product_url,
        "price_text": price_tag.get_text(strip=True) if price_tag else None,
        "availability_text": (
            availability_tag.get_text(" ", strip=True)
            if availability_tag
            else None
        ),
        "rating_text": rating_text,
        "description": (
            description_tag.get_text(" ", strip=True)
            if description_tag
            else None
        ),
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


# ---- Stage 4: normalize (raw text -> clean number, raw kept alongside) ----
def normalize_price(price_text: str | None) -> float:
    if not price_text:
        raise ValueError("price_text is missing")

    cleaned = price_text.strip()
    cleaned = cleaned.replace("£", "").replace(",", "")

    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", cleaned):
        raise ValueError(f"invalid price: {price_text!r}")

    return float(cleaned)

## BOOK MODEL
## Stage 4: schema = the recipe. Every record is checked against Book BEFORE
## storage; only description is optional. Failures never reach books.json.
class Book(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: datetime
    price_gbp : float

    @field_validator("product_url")
    @classmethod
    def validate_product_url(cls, value: str) -> str:
        parsed = urlparse(value)

        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("product_url must be an absolute HTTPS URL")
        return value


# ---- Stage 4: store (validate -> de-dupe by canonical URL -> overwrite) ----
# Overwrite (never append) books.json so reruns stay at 60, not 120.
# Returns (valid books, errors) so the Stage 5 report can count both.
def clean_data(records_list: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Clean the data in the record list. Returns (valid books, errors)."""
    ensure_directory(OUTPUT_DIR)
    valid_records = []
    errors = []

    for raw_record in records_list:
        try:
            normalized_record = {
                **raw_record,
                "price_gbp": normalize_price(raw_record.get("price_text")),
            }

            book = Book.model_validate(normalized_record)
            valid_records.append(book.model_dump(mode="json"))
        except (ValueError) as e:
            errors.append({
                "product_url": raw_record.get("product_url"),
                "reason": str(e),
            })

    unique_records = {
        record["product_url"]: record
        for record in valid_records
    }

    books = list(unique_records.values())

    BOOKS_FILE.write_text(
        json.dumps(books, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    ERRORS_FILE.write_text(
        json.dumps(errors, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return books, errors

# ---- Stage 5: survive failures, report the run ----
# Bulkhead loop: each detail page is isolated (fail -> failed_pages, continue).
# Counters (fetched vs cache hits) flow in via stats; the run always ends by
# writing output/run-report.json, even with failures.
def main() -> None:
    ## Current url
    current_page_url = BASE_URL + "/page-1.html"
    start_time = datetime.now(timezone.utc)
    stats = {"pages_fetched": 0, "cache_hits": 0}

    ## Check if directory exists, else create new cache directory
    ensure_directory(CACHE_DIR)

    html_page, _ = fetch_page(BASE_URL + "/page-1.html", stats)

    links, source_page_map = discover_catalogue_pages(current_page_url, html_page, stats)

    ## Scrape each detail page independently: one failure is logged
    ## and skipped, the rest of the run survives.
    records = []
    failed_pages = []
    for product_url in sorted(links):
        try:
            records.append(
                extract_book_details(product_url, source_page_map.get(product_url), stats)
            )
        except (RetryableFetchError, TerminalFetchError, ValueError) as e:
            failed_pages.append({
                "product_url": product_url,
                "reason": f"{type(e).__name__}: {e}",
            })
            print(f"SKIP {product_url}: {e}")

    print(f"CHECKPOINT: detail_pages = {len(records)}")
    if records:
        print("RAW RECORD (first):")
        print(json.dumps(records[0], indent=2, ensure_ascii=False))
    else:
        print("raw_record = None")

    books, errors = clean_data(records)
    print(f"CHECKPOINT: books.json records = {len(books)}")

    end_time = datetime.now(timezone.utc)
    run_report = {
        "start_time": start_time.isoformat(),
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "catalogue_pages": 3,
        "detail_pages_attempted": len(links),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(books),
        "invalid_records": len(errors),
        "failed_pages": failed_pages,
        "failed_pages_count": len(failed_pages),
    }
    RUN_REPORT_FILE.write_text(
        json.dumps(run_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"CHECKPOINT: failed_pages = {len(failed_pages)}")
    print(f"CHECKPOINT: run_report:")
    print(json.dumps(run_report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
