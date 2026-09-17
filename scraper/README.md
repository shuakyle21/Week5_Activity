# The Polite Scraper

FlyRank Internship · Backend Track · Week 5 · Assignment A9

A small, polite scraping pipeline. It downloads the first three catalogue pages of
[Books to Scrape](https://books.toscrape.com/), visits all 60 book pages, turns messy HTML into
clean, schema-checked JSON, survives a broken page without crashing, and ends every run with an
honest report.

**Lane:** Python 3.10+ · Requests · Beautiful Soup · Pydantic

---

## Stage 0 — Target classification

| Question | Answer |
| --- | --- |
| **Which site?** | `https://books.toscrape.com/` — the Books sandbox of the [ToScrape](https://toscrape.com/) project. |
| **Why is it appropriate?** | It is a practice sandbox that exists for exactly this purpose. Its own home page describes it as *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."* That sentence is the permission this assignment relies on. |
| **How much?** | The **first 3 catalogue pages only** (`page-1` -> `page-2` -> `page-3`, followed via the site's own "next" link), plus the 60 book detail pages they link to. Nothing else, ever. |
| **What data?** | Per book: title, product URL, price text, availability text, rating text, description, plus provenance (`source_page`, `fetched_at`). No personal data is collected -- this is a fictional catalogue. |
| **robots.txt result** | Requested `https://books.toscrape.com/robots.txt` once on 2026-09-05. The server answered **HTTP 404 Not Found** (nginx, 153 bytes) -- **no robots file found**. A missing file is not permission; it is just a missing file. The permission here comes from the sandbox's own stated purpose, and politeness is enforced by this scraper's own limits (3 pages, identifying user-agent, timeout, >=500 ms delay, cache). |

## Stage 1 - Fetch and cache
This stage fetches catalogue page 1 over the network with an honest User-Agent identifying the project (e.g. FlyRankInternshipA9/1.0 (+repo-link)) 
and a request timeout, verifies that the HTTP status is 200 before doing anything else, and saves the response body to cache/catalogue-page-1.html; on subsequent runs the scraper reads that file from cache instead of re-downloading. The checkpoint is to run the script twice — the first run prints FETCH and creates the cache file, the second prints CACHE HIT — with both runs reporting the response size and neither dumping the full HTML. The stage is committed as Stage 1: fetch and cache HTML.
> I will not reuse this code on another site without checking its rules and terms first.
