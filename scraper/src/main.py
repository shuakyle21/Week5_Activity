import os
from pathlib import Path
from urllib.parse import urlparse, urljoin, unquote
import requests
import hashlib
from bs4 import BeautifulSoup
import time

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
BASE_URL = "https://books.toscrape.com/catalogue"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/shuakyle21/Week5_Activity)"
REQUEST_DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 5


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
def fetch_page(url: str) -> str:
    # Set the cache file name from the url
    clean_str = slug_from_url(url)
    cache_file = os.path.join(CACHE_DIR, f"catalogue-{clean_str}")  # Final file name

    # Check if cache hit or miss, read from disk
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            html_ = f.read()
            print(f"CACHE HIT 💾: {cache_file}, size={len(html_)}")
            return html_

    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch page: {url}: HTTP: {response.status_code}")
    html_ = response.text

    with open(cache_file, "w") as f:
        f.write(html_)
    print(f"FETCH: {url}, size={len(response.text)}")
    time.sleep(REQUEST_DELAY_SECONDS)
    return html_


def slug_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    parts = [p for p in path.split("/") if p and p.lower != "index.html"]
    return parts[-1] if parts else hashlib.md5(url.encode()).hexdigest()


## Stage 2: Discover the catalogue page structure
def discover_catalogue_pages(current_page_url: str, page_html: str):
    seen_links = set()
    page_number = 1

    while page_number <= 3:
        page = BeautifulSoup(page_html, "html.parser")

        for a in page.select("ol.row li h3 a"):
            ## Get the current page url
            absolute_url = urljoin(current_page_url, a.get("href"))

            if absolute_url not in seen_links:
                seen_links.add(absolute_url)

        if page_number == 3:
            print(f"CHECKPOINT ... {len(seen_links)}")
            print(f"Discovered {len(seen_links)} links, Unique URLs Found: {len(seen_links)}")
            break

        next_tag = page.select_one("ul.pager li.next a") ## finds the next link tag

        if next_tag is None:
            print("CHECKPOINT FAILED...")
            break
        else:
            next_url = urljoin(current_page_url, next_tag.get("href"))
            page_html = fetch_page(next_url)
            current_page_url = next_url
            page_number += 1


def main() -> None:
    ## Current url
    current_page_url = BASE_URL + "/page-1.html"

    ## Check if directory exists, else create new cache directory
    ensure_directory(CACHE_DIR)
    html_page = fetch_page(BASE_URL + "/page-1.html")
    discover_catalogue_pages(current_page_url, page_html=html_page)


if __name__ == "__main__":
    main()
