import os
from pathlib import Path
import time
from urllib.parse import urlparse
import requests
import hashlib


CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
BASE_URL = "https://books.toscrape.com/catalogue/"
USER_AGENT = "FlyRankInternshipA9/1.0 (+https://github.com/shuakyle21/Week5_Activity)"
REQUEST_DELAY_SECONDS = 0.5
TIMEOUT_SECONDS = 5


## Check cache directory if exists, if not, create it
def ensure_directory(path: str | Path) -> str | None:
    # Create the directory if it doesn't exist; do nothing if it does.
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise FileExistsError(f"{path} exists but is not a directory")
        print(f"Directory already exists: {path}")
        return None
    else:
        os.makedirs(path)
        return f"Created directory: {path}"


## Fetch Page with agent
def fetch_page(url: str) -> str:
    # Set the cache file name from the url
    clean_str = slug_from_url(url)
    cache_file = os.path.join(CACHE_DIR, clean_str) # Final file name

    # Check if cache hit or miss, read from disk
    try:
        with open(cache_file, "r") as f:
            return f.read()
    except FileNotFoundError:
        # Request the page from network
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
        with open(cache_file, "w") as f:
            f.write(response.text)

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch page: {url}: HTTP {response.status_code}")
        html = response.text

    # Save the HTML to the cache directory
    with open(cache_file, "w") as f:
        f.write(html)
    time.sleep(0.5)
    return html

def slug_from_url(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p and p != "index.html"]
    return parts[-1] if parts else hashlib.md5(url.encode()).hexdigest()


def main() -> None:
    ## Check if directory exists, else create new cache directory
    ensure_directory(CACHE_DIR)
    fetch_page(BASE_URL + "page-1.html")


if __name__ == "__main__":
    main()
