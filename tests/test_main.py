import unittest
from io import StringIO
from unittest.mock import patch
from contextlib import redirect_stdout

from scraper.src.main import extract_book_details, main


class DiscoverCataloguePagesTests(unittest.TestCase):
    def test_main_passes_html_to_catalogue_discovery(self):
        page_url = "https://example.test/catalogue/page-1.html"
        page_html = """
        <ol class="row">
          <li><h3><a href="book.html">Book</a></h3></li>
        </ol>
        """

        with (
            patch("scraper.src.main.BASE_URL", "https://example.test/catalogue"),
            patch("scraper.src.main.ensure_directory"),
            patch("scraper.src.main.fetch_page", return_value=(page_html, False)),
            patch("scraper.src.main.discover_catalogue_pages") as discover,
        ):
            discover.return_value = (set(), {})
            main()

        discover.assert_called_once_with(
            page_url,
            page_html,
            {"pages_fetched": 0, "cache_hits": 0},
        )

    def test_report_prints_one_full_raw_record(self):
        first_url = "https://example.test/catalogue/first/index.html"
        second_url = "https://example.test/catalogue/second/index.html"
        first_record = {"title": "First", "product_url": first_url}
        second_record = {"title": "Second", "product_url": second_url}

        with (
            patch("scraper.src.main.BASE_URL", "https://example.test/catalogue"),
            patch("scraper.src.main.ensure_directory"),
            patch(
                "scraper.src.main.fetch_page",
                return_value=("<html></html>", False),
            ),
            patch("scraper.src.main.discover_catalogue_pages") as discover,
            patch(
                "scraper.src.main.extract_book_details",
                side_effect=[first_record, second_record],
            ),
        ):
            discover.return_value = (
                {second_url, first_url},
                {first_url: "source", second_url: "source"},
            )
            output = StringIO()
            with redirect_stdout(output):
                main()

        report = output.getvalue()
        self.assertIn("detail_pages = 2", report)
        self.assertIn('"title": "First"', report)
        self.assertIn('"product_url": "https://example.test/catalogue/first/index.html"', report)
        self.assertNotIn('"title": "Second"', report)


class ExtractBookDetailsTests(unittest.TestCase):
    def test_extracts_details_from_product_main_not_related_book_card(self):
        product_html = """
        <article class="product_pod">
          <h3>Related book</h3>
        </article>
        <div class="product_main">
          <h1>Test Book</h1>
          <p class="price_color">£12.34</p>
          <div id="product_description"></div>
          <p>Book description.</p>
        </div>
        """

        with patch(
            "scraper.src.main.fetch_page",
            return_value=(product_html, False),
        ):
            details = extract_book_details(
                "https://example.test/catalogue/test-book/index.html",
                "https://example.test/catalogue/page-1.html",
            )

        self.assertEqual(
            details,
            {
                "title": "Test Book",
                "product_url": "https://example.test/catalogue/test-book/index.html",
                "price_text": "£12.34",
                "availability_text": None,
                "rating_text": None,
                "description": "Book description.",
                "source_page": "https://example.test/catalogue/page-1.html",
                "fetched_at": details["fetched_at"],
            },
        )
        self.assertEqual(list(details), [
            "title",
            "product_url",
            "price_text",
            "availability_text",
            "rating_text",
            "description",
            "source_page",
            "fetched_at",
        ])


if __name__ == "__main__":
    unittest.main()
