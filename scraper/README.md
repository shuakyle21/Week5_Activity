# The Polite Scraper

FlyRank Internship · Backend Track · Week 5 · Assignment A9

A small, polite scraping pipeline. It downloads the first three catalogue pages of
[Books to Scrape](https://books.toscrape.com/), visits all 60 book pages, turns messy HTML into
clean, schema-checked JSON, survives a broken page without crashing, and ends every run with an
honest report.

**Lane:** Python 3.10+ · Requests · Beautiful Soup · Pydantic

---

## The Pipeline
| Step | Question it answers | Proof |
| --- | --- | --- |
| Classify | May I automate this site? | this README section |
| Fetch | Did the page really arrive? | found in cache/*.html + status code 200 |
| Extract | Which parts of the page do I need? | raw text fields |
| Normalize | How does "£51.77" become a number? | clean values, absolute URLs |
| Validate | Is every record safe to store? | Pydantic schema check; bad records in `output/errors.json` |
| Store | Can another program use this? | `output/books.json` (60 records, idempotent) |


## Stage 0 — Target classification

| Question | Answer |
| --- | --- |
| **Which site?** | `https://books.toscrape.com/` — the Books sandbox of the [ToScrape](https://toscrape.com/) project. |
| **Why is it appropriate?** | It is a practice sandbox that exists for exactly this purpose. Its own home page describes it as *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."* That sentence is the permission this assignment relies on. |
| **How much?** | The **first 3 catalogue pages only** (`page-1` -> `page-2` -> `page-3`, followed via the site's own "next" link), plus the 60 book detail pages they link to. Nothing else, ever. |
| **What data?** | Per book: title, product URL, price text, availability text, rating text, description, plus provenance (`source_page`, `fetched_at`). No personal data is collected -- this is a fictional catalogue. |
| **robots.txt result** | Requested `https://books.toscrape.com/robots.txt` once on 2026-09-05. The server answered **HTTP 404 Not Found** (nginx, 153 bytes) -- **no robots file found**. 

## Stage 1 - Fetch and cache
This stage fetches catalogue page 1 over the network with an honest User-Agent identifying the project (e.g. FlyRankInternshipA9/1.0 (+repo-link)) 
and a request timeout, verifies that the HTTP status is 200 before doing anything else, and saves the response body to cache/catalogue-page-1.html; on subsequent runs the scraper reads that file from cache instead of re-downloading. The checkpoint is to run the script twice — the first run prints FETCH and creates the cache file, the second prints CACHE HIT — with both runs reporting the response size and neither dumping the full HTML. The stage is committed as Stage 1: fetch and cache HTML.
> I will not reuse this code on another site without checking its rules and terms first.

---

## Run

```bash
# from the repo root (Python 3.12+, deps in requirements.txt)
python -m scraper.src.main
```

Install: `pip install -r scraper/requirements.txt` (`requests`, `beautifulsoup4`, `pydantic`).
No database, proxy, or browser needed — the data is already in the HTML the server sends.

## Record schema (`Book`, Pydantic — `scraper/src/main.py`)

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | `str` | yes | from `div.product_main h1` |
| `product_url` | `str` | yes | absolute `https://…` URL, canonical identity for de-dupe |
| `price_text` | `str` | yes | raw, e.g. `"£51.77"` — kept alongside the clean value |
| `price_gbp` | `float` | yes | normalized via `normalize_price` (`£` stripped, `float(...)`) |
| `availability_text` | `str` | yes | e.g. `"In stock (22 available)"` |
| `rating_text` | `str` | yes | e.g. `"Three"`, from the `star-rating` class |
| `description` | `str \| None` | no | `#product_description + p`; `null` when the page has none — never invented |
| `source_page` | `str` | yes | catalogue page URL the book was discovered from (provenance) |
| `fetched_at` | `datetime` | yes | UTC timestamp of extraction (provenance) |

Records failing validation go to `scraper/output/errors.json` with `product_url` + reason; only valid records reach `scraper/output/books.json`.

## Politeness rules (every real request)

- Honest `User-Agent`: `FlyRankInternshipA9/1.0 (+repo-link)` (`USER_AGENT` in `scraper/src/main.py`)
- `timeout=5`s on every request (`TIMEOUT_SECONDS`) — never wait forever
- Status check: only `200` proceeds; anything else is a failed fetch, not HTML to parse
- `≥500ms` delay between real (non-cached) requests (`REQUEST_DELAY_SECONDS`); cache reads take no delay
- `cache/` holds saved HTML and is gitignored — dev reruns read from disk
- Server omits the charset header, so `response.encoding = response.apparent_encoding` is set before reading text (page is UTF-8, otherwise `£` mojibakes to `Â£`)

## Stage 2 — Discover three catalogue pages

Parses cached pages with Beautiful Soup, collects every book link (`ol.row li h3 a`), converts relative → absolute with `urljoin` (never string concat), follows the site's own "next" link page 1 → 2 → 3, then stops. De-dupes via a set.
Checkpoint: `catalogue_pages=3, discovered=60, unique_urls=60`; rerun matches, mostly from cache.

## Stage 3 — Extract the raw records

Fetches/caches each of the 60 detail pages with the same politeness, parses scoped to the product area (`div.product_main`, not the whole doc), and builds the 8-key raw record (`title`, `product_url`, `price_text`, `availability_text`, `rating_text`, `description`, `source_page`, `fetched_at`).
Checkpoint: one full raw record printed + `detail_pages = 60`.

## Stage 4 — Validate normalized records

`normalize_price` turns `price_text` into numeric `price_gbp` (missing/garbage → `ValueError` → `errors.json`); every record is validated against the `Book` schema before storage; output is de-duped by canonical `product_url` and **overwritten** (not appended) so reruns stay at 60.
Checkpoint: `books.json records = 60`, all `price_gbp` numeric, all URLs `https://`, content identical across reruns apart from fresh `fetched_at` timestamps.

## Honest limitation

No failure survival yet: a single bad page currently crashes the run instead of being logged and skipped, and there is no retry or `run-report.json` — that is Stage 5.
