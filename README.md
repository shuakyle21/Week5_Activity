# The Polite Scraper

**FlyRank Internship · Backend Track · Week 5 · Assignment A9**

A lightweight, fault-tolerant web scraping pipeline that collects book data from [Books to Scrape](https://books.toscrape.com/), extracts and normalizes HTML content, validates records using Pydantic, and generates structured JSON outputs and execution reports.

The scraper processes the first three catalogue pages and their 60 associated book detail pages. It supports local HTML caching, duplicate prevention, request throttling, validation error tracking, and failure reporting.

## Table of Contents

* [Project Overview](#project-overview)
* [Technology Stack](#technology-stack)
* [Target and Scraping Scope](#target-and-scraping-scope)
* [Installation and Usage](#installation-and-usage)
* [Pipeline Architecture](#pipeline-architecture)
* [Data Schema](#data-schema)
* [Output Files](#output-files)
* [Request Handling and Politeness](#request-handling-and-politeness)
* [Error Handling and Resilience](#error-handling-and-resilience)
* [Execution Report](#execution-report)
* [Known Limitations](#known-limitations)
* [Ethical Use](#ethical-use)

## Project Overview

The Polite Scraper demonstrates a structured approach to web scraping, from target assessment and HTML retrieval to data validation and persistent output.

**Key features:**

* Sequential discovery of three catalogue pages.
* Extraction of 60 book detail records.
* HTTP status verification and request timeouts.
* Local HTML caching to minimize repeated network requests.
* Data normalization and Pydantic schema validation.
* Duplicate prevention using canonical product URLs.
* Per-page error isolation and controlled retries.
* JSON outputs for valid records, validation errors, and run statistics.

## Technology Stack

| Technology       | Purpose                                       |
| ---------------- | --------------------------------------------- |
| Python 3.10+     | Core implementation                           |
| Requests         | HTTP requests and response handling           |
| Beautiful Soup 4 | HTML parsing and data extraction              |
| Pydantic         | Data validation and schema enforcement        |
| JSON             | Structured data storage and execution reports |

A browser, database, or proxy is not required because the target's data is available in the server-delivered HTML.

## Target and Scraping Scope

| Property               | Description                                    |
| ---------------------- | ---------------------------------------------- |
| Target                 | [Books to Scrape](https://books.toscrape.com/) |
| Site classification    | Practice sandbox for web scraping              |
| Catalogue scope        | First three catalogue pages                    |
| Detail pages           | 60 book product pages                          |
| Expected valid records | 60                                             |
| Data format            | JSON                                           |
| Deduplication key      | Canonical `product_url`                        |

### Authorization Assessment

Books to Scrape describes itself as a fictional bookstore designed for practicing web scraping and validating scraping tools. This stated purpose makes it suitable for the assignment's training use case.

On **September 5, 2026**, a request to `https://books.toscrape.com/robots.txt` returned HTTP `404 Not Found`. No robots.txt file was available at the time of that check. The absence of this file is not, by itself, authorization; the target's stated purpose and applicable site policies must also be considered.

I will not reuse this code on another site without checking its rules and terms first.

### Data Collection Scope

Each book record contains the following information:

* Title and product URL
* Original price text and normalized GBP price
* Availability and rating text
* Product description, when available
* Source catalogue page and extraction timestamp

The scraper is restricted to the defined catalogue and product pages. It does not intentionally collect personal information.

## Installation and Usage

### Prerequisites

* Python 3.10 or later
* Internet access for uncached HTTP requests

### Install dependencies

From the repository root, run:

```bash
python -m pip install -r scraper/requirements.txt
```

### Run the scraper

Execute the module from the repository root:

```bash
python -m scraper.src.main
```

The scraper retrieves uncached pages, reads cached HTML where available, processes the book records, and writes the resulting JSON files.

### Verify caching

Run the scraper twice.

1. **First run:** Uncached pages are requested and their HTML responses are saved locally.
2. **Subsequent runs:** Existing cached pages are reused when available, reducing network requests.

The console output identifies fetch operations and cache hits without printing entire HTML documents.

## Pipeline Architecture

The pipeline follows six stages:

| Stage                     | Operation                                             | Expected Result                                   |
| ------------------------- | ----------------------------------------------------- | ------------------------------------------------- |
| 1. Classify               | Assess target suitability and collection scope        | Documented target and permissions assessment      |
| 2. Fetch                  | Retrieve HTML and verify HTTP responses               | Cached HTML files and validated response status   |
| 3. Discover               | Follow catalogue pagination and collect product links | 3 catalogue pages and 60 unique product URLs      |
| 4. Extract                | Parse product-specific HTML elements                  | Raw records containing source data and provenance |
| 5. Normalize and validate | Convert values and apply the Pydantic schema          | Valid records and recorded validation errors      |
| 6. Store and report       | Write JSON outputs and execution statistics           | Book dataset, error log, and run report           |

### Stage 1: Fetch and Cache

The scraper sends HTTP requests using an identifiable User-Agent and a configured timeout. It verifies the response status before parsing the HTML.

Successful responses are cached locally. Subsequent executions can reuse saved HTML rather than downloading the same pages again.

The response encoding is set using `response.apparent_encoding` to help preserve characters such as the pound sign (`£`) when the server does not provide an explicit charset.

### Stage 2: Discover Catalogue Pages

The scraper starts at the first catalogue page and follows the website's own `next` link until it reaches the third page.

Book links are extracted using the CSS selector:

```css
ol.row li h3 a
```

Relative URLs are resolved using `urljoin`, and a set is used to remove duplicate URLs.

**Expected checkpoint:**

```text
catalogue_pages = 3
discovered = 60
unique_urls = 60
```

### Stage 3: Extract Book Details

Each discovered product URL is fetched or loaded from cache. The parser focuses on the product content rather than processing the entire document.

The raw record contains eight fields: `title`, `product_url`, `price_text`, `availability_text`, `rating_text`, `description`, `source_page`, and `fetched_at`.

The description is extracted from the product description section when present. Missing descriptions are retained as `null` rather than fabricated.

**Expected checkpoint:** 60 detail pages attempted, with one extracted raw record available for inspection.

### Stage 4: Normalize and Validate

The normalization step converts the original price text into a numeric GBP value.

For example:

```text
Input:  £51.77
Output: 51.77
```

The `normalize_price` function raises a `ValueError` when the price cannot be converted. Records are validated against the `Book` Pydantic model before being included in the final dataset.

Invalid records are written to `scraper/output/errors.json`. Valid records are deduplicated using `product_url`.

The books dataset is overwritten on each run rather than appended to, preventing duplicates from accumulating across executions.

**Expected checkpoint:** 60 valid records, numeric `price_gbp` values, and absolute HTTPS product URLs.

### Stage 5: Handle Failures and Report Results

Product-page failures are recorded individually so that one failed detail page does not stop the remaining pages from being processed.

The scraper writes a run report containing timing information, fetch and cache statistics, validation counts, and page-level failures.

**Expected checkpoint:** A failed product page is recorded in the report while the scraper continues processing other products.

## Data Schema

The `Book` model is defined in `scraper/src/main.py` using Pydantic.

| Field               | Type          | Required | Description                                        |
| ------------------- | ------------- | -------- | -------------------------------------------------- |
| `title`             | `str`         | Yes      | Book title extracted from `div.product_main h1`    |
| `product_url`       | `str`         | Yes      | Absolute HTTPS product URL; used for deduplication |
| `price_text`        | `str`         | Yes      | Original price string, such as `£51.77`            |
| `price_gbp`         | `float`       | Yes      | Normalized numeric price in GBP                    |
| `availability_text` | `str`         | Yes      | Original availability text                         |
| `rating_text`       | `str`         | Yes      | Rating label, such as `Three`                      |
| `description`       | `str \| None` | No       | Product description; `null` when unavailable       |
| `source_page`       | `str`         | Yes      | Catalogue URL where the product was discovered     |
| `fetched_at`        | `datetime`    | Yes      | UTC timestamp associated with extraction           |

The normalized schema contains nine fields. The raw extraction record contains eight fields; `price_gbp` is added during normalization.

## Output Files

The scraper produces the following artifacts:

| File                             | Purpose                                               |
| -------------------------------- | ----------------------------------------------------- |
| `scraper/cache`                 | Stores cached HTML responses for reuse                |
| `scraper/output/books.json`      | Contains validated and deduplicated book records      |
| `scraper/output/errors.json`     | Contains invalid records and validation reasons       |
| `scraper/output/run-report.json` | Contains execution statistics and failed-page details |

Cached HTML is excluded from version control so that local development runs do not unnecessarily commit downloaded page content.

### Validation Errors

Each invalid record is logged with its product URL and validation reason. Only records that pass validation are included in `books.json`.

### Idempotent Output

The scraper rebuilds the output dataset on each execution instead of appending records. For an unchanged dataset, the record contents should remain consistent apart from fields such as `fetched_at`.

## Request Handling and Politeness

The scraper applies the following controls to real network requests:

| Control                | Implementation                                                   |
| ---------------------- | ---------------------------------------------------------------- |
| User-Agent             | `FlyRankInternshipA9/1.0 (+https://github.com/shuakyle21/the-polite-scraper)` |
| Request timeout        | 5 seconds                                                        |
| Inter-request delay    | At least 500 milliseconds                                        |
| HTTP status validation | Only HTTP `200 OK` responses proceed to parsing                  |
| Retry behavior         | One retry for eligible transient failures                        |
| Local cache            | Reuses saved HTML when available                                 |
| Character encoding     | Uses `response.apparent_encoding` when setting response encoding |

The User-Agent is configured through `USER_AGENT`, the timeout through `TIMEOUT_SECONDS`, and the request delay through `REQUEST_DELAY_SECONDS` in `scraper/src/main.py`.

Only real network requests incur the configured request delay; cache reads do not.

## Error Handling and Resilience

The scraper distinguishes between transient request failures, HTTP errors, and data validation failures.

* **Timeouts and connection errors:** Retried once after a one-second delay.
* **HTTP 5xx responses:** Retried once after a one-second delay.
* **HTTP 4xx responses:** Not retried. These responses are recorded as failures.
* **Validation errors:** Recorded in `errors.json` without including invalid records in the final dataset.
* **Product-page failures:** Recorded with the affected URL and failure reason; processing continues for other detail pages.
* **Catalogue-page failures:** Can abort the run because catalogue discovery is required to identify product URLs.

A `403 Forbidden` response is respected as an access restriction and is not bypassed.

## Execution Report

At the end of each run, the scraper writes `scraper/output/run-report.json`.

### Report fields

| Field                    | Description                                             |
| ------------------------ | ------------------------------------------------------- |
| `start_time`             | Run start timestamp in UTC                              |
| `duration_seconds`       | Total execution time                                    |
| `catalogue_pages`        | Number of catalogue pages processed                     |
| `detail_pages_attempted` | Number of product detail pages attempted                |
| `pages_fetched`          | Number of pages successfully retrieved from the network |
| `cache_hits`             | Number of pages served from local cache                 |
| `valid_records`          | Number of valid records written                         |
| `invalid_records`        | Number of records rejected by validation                |
| `failed_pages`           | Details of page-level failures                          |
| `failed_pages_count`     | Total number of recorded page failures                  |

### Sample Report

The following report is from a completed run in which all 63 pages were served from the local cache.

```json
{
  "start_time": "2026-10-12T09:07:44.464786+00:00",
  "duration_seconds": 1.13,
  "catalogue_pages": 3,
  "detail_pages_attempted": 60,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": [],
  "failed_pages_count": 0
}
```

This run produced 60 valid records, no validation errors, and no failed pages. Since the HTML was already cached, no network fetches were required.

## Known Limitations

The current implementation is designed for a controlled training assignment rather than production-scale scraping.

* Retries are limited to one attempt with a fixed one-second delay.
* Exponential backoff and `Retry-After` header handling are not implemented.
* Structured application logging is not yet available.
* A failed catalogue page can interrupt the run, although individual product-page failures are isolated.
* Cache freshness and expiration are not automatically managed.

These areas are candidates for future improvements as part of the next development stage.

## Ethical Use

* Scrape only authorized environments and websites that permit it.
* Prefer official APIs whenever available.
* Never bypass authentication, paywalls, rate limits, or access restrictions. Respect HTTP `403 Forbidden` responses.
* Minimize data collection and use reasonable request intervals.
* Review the target website's terms, policies, and permissions before reusing or deploying this code elsewhere.

**Disclaimer:** Users are responsible for ensuring that all scraping activities comply with applicable laws, contractual obligations, and website policies.
