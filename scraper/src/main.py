"""The polite scraper - FlyRank W5 A9.

Stage 0: project skeleton. The pipeline is built up one stage at a time.
"""

import hashlib
from urllib.parse import urlparse


def slug_from_url(url: str) -> str:
    """Derive a filesystem-safe cache key from a book detail page URL.

    Used for Stage 3's 60 book detail pages, whose URLs are unpredictable.
    Catalogue pages (Stage 1/2) don't need this - their filenames are built
    directly from the known page number instead.
    """
    parts = [p for p in urlparse(url).path.split("/") if p and p != "index.html"]
    return parts[-1] if parts else hashlib.md5(url.encode()).hexdigest()


def main() -> None:
    print("polite scraper: stage 0 - target classified, see README.md")


if __name__ == "__main__":
    main()
