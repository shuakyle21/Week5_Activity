import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
import hashlib
import json
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

import re
from pydantic import BaseModel, field_validator

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
BASE_URL = "https://books.toscrape.com/catalogue"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/shuakyle21/Week5_Activity)"
REQUEST_DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 5

## SET OUTPUT DIRECTORY
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOOKS_FILE = OUTPUT_DIR / "books.json"
ERRORS_FILE = OUTPUT_DIR / "errors.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def normalize_price(price_text: str | None) -> float:
    if not price_text:
        raise ValueError("price_text is missing")

    cleaned = price_text.strip()
    cleaned = cleaned.replace("£", "").replace(",", "")

    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", cleaned):
        raise ValueError(f"invalid price: {price_text!r}")

    return float(cleaned)

## BOOK MODEL
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


## Fetch Page with agent
def fetch_page(url: str):
    # Set the cache file name from the url
    clean_str = slug_from_url(url)
    cache_file = os.path.join(CACHE_DIR, f"catalogue-{clean_str}")  # Final file name

    # Check if cache hit or miss, read from disk
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            html_ = f.read()
            print(f"CACHE HIT 💾: {cache_file}, size={len(html_)}")
            return html_, False

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch page: {url}: HTTP: {response.status_code}")
    # Server sends text/html without charset; page is UTF-8 (meta tag).
    # Force detection so response.text doesn't mojibake (Â£ instead of £).
    response.encoding = response.apparent_encoding
    html_ = response.text

    with open(cache_file, "w") as f:
        f.write(html_)
    print(f"FETCH: {url}, size={len(response.text)}")
    time.sleep(REQUEST_DELAY_SECONDS)
    return html_, True


def slug_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    parts = [p for p in path.split("/") if p and p.lower() != "index.html"]
    return parts[-1] if parts else hashlib.md5(url.encode()).hexdigest()


## Stage 2: Discover the catalogue page structure
def discover_catalogue_pages(current_page_url: str, page_html: str):
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
            page_html, _ = fetch_page(next_url)
            current_page_url = next_url
            page_number += 1

    return seen_links, source_page_map

# Stage 3 extract book details
def extract_book_details(
    product_url: str, source_page: str | None
) -> dict[str, Any]:
    html, _ = fetch_page(product_url)
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


def clean_data(records_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Clean the data in the record list."""
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

    return books

def main() -> None:
    ## Current url
    current_page_url = BASE_URL + "/page-1.html"

    ## Check if directory exists, else create new cache directory
    ensure_directory(CACHE_DIR)
    html_page, _ = fetch_page(BASE_URL + "/page-1.html")
    links, source_page_map = discover_catalogue_pages(current_page_url, html_page)

    records = [
        extract_book_details(product_url, source_page_map.get(product_url))
        for product_url in sorted(links)
    ]

    print(f"CHECKPOINT: detail_pages = {len(records)}")
    if records:
        print("RAW RECORD (first):")
        print(json.dumps(records[0], indent=2, ensure_ascii=False))
    else:
        print("raw_record = None")

    books = clean_data(records)
    print(f"CHECKPOINT: books.json records = {len(books)}")

if __name__ == "__main__":
    main()
