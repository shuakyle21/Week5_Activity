# The Polite Scraper

A small, fault-tolerant web scraping pipeline. It collects book data from
[Books to Scrape](https://books.toscrape.com/) — a sandbox built for
practicing scraping — extracts and normalizes each record, validates it with
Pydantic, and writes structured JSON output plus a per-run execution report.

Built during a FlyRank backend internship; maintained as a standalone project.

## Features

- Catalogue discovery across paginated listings with link deduplication
- Local HTML caching — reruns reuse saved pages instead of re-downloading
- Request politeness: identifiable User-Agent, timeouts, 500 ms inter-request
  delay, single retry for transient failures only
- Pydantic schema validation with invalid records quarantined to `errors.json`
- Per-page error isolation: one failed detail page never aborts the run
- Machine-readable `run-report.json` with timings, cache stats, and failures
- Idempotent output: reruns overwrite, never duplicate

## Quickstart

Requires Python 3.10+ and `uv`.

```sh
uv sync
uv run polite-scraper
```

Options:

| Flag | Default | Purpose |
| :--- | :--- | :--- |
| `--pages` | `3` | Catalogue pages to process |
| `--delay` | `0.5` | Seconds between real requests |
| `--timeout` | `5.0` | Per-request timeout in seconds |
| `--no-cache` | off | Bypass the local HTML cache |
| `--output-dir` | `data/output` | Destination for JSON outputs |
| `--cache-dir` | `data/cache` | HTML cache location |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

Run the tests (network is always mocked):

```sh
uv run pytest
```

## How it works

```
fetch (cache-aware) → discover (paginate + dedupe) → extract (scoped selectors)
  → normalize + validate (Pydantic) → store (overwrite) + report
```

- **Fetch**: proceeds only on HTTP 200. Timeouts, connection errors, and 5xx
  get exactly one retry; 4xx is terminal and recorded, never retried.
- **Discover**: follows the site's own `next` link; relative URLs resolved
  with `urljoin`; duplicates removed by set.
- **Extract**: selectors scoped to `div.product_main`. Missing descriptions
  stay `null`, never invented.
- **Validate**: price text normalized to numeric GBP (`£51.77 → 51.77`);
  records checked against the `Book` model; failures land in `errors.json`
  with product URL and reason.

Outputs in the output directory:

| File | Contents |
| :--- | :--- |
| `books.json` | Validated, deduplicated book records |
| `errors.json` | Rejected records with validation reasons |
| `run-report.json` | Timings, fetch/cache counts, failed pages |

## Ethical use

- Scrape only sites that permit it; prefer official APIs where available.
- Never bypass authentication, paywalls, rate limits, or access controls —
  HTTP 403 is treated as a stop sign, not an obstacle.
- Check the target's current rules and terms before reusing this code
  anywhere else. A prior `robots.txt` check returned 404 (no file served),
  which alone is not authorization.

## Project structure

```
src/polite_scraper/
  cli.py        # argument parsing, logging setup, entry point
  config.py     # all tunables in one dataclass
  fetch.py      # HTTP + HTML cache
  discover.py   # catalogue pagination
  extract.py    # detail-page parsing
  models.py     # Pydantic schema + normalization
  pipeline.py   # orchestration + run report
  errors.py     # retryable vs terminal failure taxonomy
tests/          # pytest suite, fully mocked
```

## License

MIT — see `LICENSE`.
