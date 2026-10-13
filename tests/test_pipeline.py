"""Pipeline tests. Network is always mocked; no test hits the real site."""

from pathlib import Path

import pytest
import requests

from polite_scraper import discover, extract, fetch, models, pipeline
from polite_scraper.config import ScraperConfig
from polite_scraper.errors import RetryableFetchError, TerminalFetchError


@pytest.fixture
def config(tmp_path):
    return ScraperConfig(cache_dir=tmp_path / "cache", output_dir=tmp_path / "out")


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"


def test_normalize_price():
    assert models.normalize_price("£51.77") == 51.77
    with pytest.raises(ValueError):
        models.normalize_price(None)
    with pytest.raises(ValueError):
        models.normalize_price("priceless")


def test_book_rejects_non_https_url():
    with pytest.raises(ValueError):
        models.Book.model_validate({
            "title": "T",
            "product_url": "http://example.test/x",
            "price_text": "£1.00",
            "price_gbp": 1.0,
            "availability_text": "In stock",
            "rating_text": "Three",
            "description": None,
            "source_page": "https://example.test/",
            "fetched_at": "2026-01-01T00:00:00+00:00",
        })


def test_discover_follows_next_through_configured_pages(monkeypatch, config):
    page1 = """
    <ol class="row"><li><h3><a href="book-one.html">Book One</a></h3></li></ol>
    <ul class="pager"><li class="next"><a href="page-2.html">next</a></li></ul>
    """
    page2 = """
    <ol class="row"><li><h3><a href="book-two.html">Book Two</a></h3></li></ol>
    <ul class="pager"><li class="next"><a href="page-3.html">next</a></li></ul>
    """
    page3 = """
    <ol class="row"><li><h3><a href="book-three.html">Book Three</a></h3></li></ol>
    """
    pages = {
        "https://example.test/catalogue/page-2.html": page2,
        "https://example.test/catalogue/page-3.html": page3,
    }
    monkeypatch.setattr(
        discover, "fetch_page",
        lambda url, cfg, stats=None: (pages[url], False),
    )
    links, source = discover.discover_catalogue_pages(
        "https://example.test/catalogue/page-1.html", page1, config
    )
    assert len(links) == 3
    assert set(source.values()) == {
        "https://example.test/catalogue/page-1.html",
        "https://example.test/catalogue/page-2.html",
        "https://example.test/catalogue/page-3.html",
    }


def test_extract_scoped_to_product_main(monkeypatch):
    html = """
    <article class="product_pod"><h3>Related book</h3></article>
    <div class="product_main">
      <h1>Test Book</h1>
      <p class="price_color">£12.34</p>
      <div id="product_description"></div>
      <p>Book description.</p>
    </div>
    """
    monkeypatch.setattr(
        extract, "fetch_page", lambda url, cfg, stats=None: (html, False)
    )
    details = extract.extract_book_details(
        "https://example.test/x", "https://example.test/", ScraperConfig()
    )
    assert details["title"] == "Test Book"
    assert details["price_text"] == "£12.34"
    assert details["description"] == "Book description."
    assert set(details) == {
        "title", "product_url", "price_text", "availability_text",
        "rating_text", "description", "source_page", "fetched_at",
    }


def test_fetch_retries_transient_once(monkeypatch, config, tmp_path):
    config.ensure_dirs()
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise requests.ConnectionError("cut")
        return FakeResponse("<html></html>")

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)
    html, from_network = fetch.fetch_page("https://example.test/p", config)
    assert from_network and html == "<html></html>" and calls["n"] == 2


def test_fetch_never_retries_client_errors(monkeypatch, config):
    config.ensure_dirs()
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        return FakeResponse(status_code=404)

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    with pytest.raises(TerminalFetchError):
        fetch.fetch_page("https://example.test/missing", config)
    assert calls["n"] == 1


def test_clean_data_dedupes_and_splits_errors(config):
    config.ensure_dirs()
    good = {
        "title": "T",
        "product_url": "https://example.test/b",
        "price_text": "£10.00",
        "availability_text": "In stock",
        "rating_text": "One",
        "description": None,
        "source_page": "https://example.test/",
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }
    books, errors = pipeline.clean_data([good, dict(good), {**good, "price_text": "??"}],
                                        config)
    assert len(books) == 1  # overwrite-style dedupe by canonical URL
    assert len(errors) == 1
    assert config.books_file.exists() and config.errors_file.exists()


def test_cli_parses_flags():
    from polite_scraper.cli import build_parser

    ns = build_parser().parse_args(["--pages", "2", "--no-cache", "--delay", "0"])
    assert ns.pages == 2 and ns.no_cache is True and ns.delay == 0
