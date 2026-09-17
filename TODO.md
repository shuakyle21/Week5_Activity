# TODO — Week 5 (A9: The polite scraper)

Lane: Python 3.10+ · Requests · Beautiful Soup · Pydantic
Target: https://books.toscrape.com/ (see `scraper/README.md` for Stage 0 classification, already done)

## Stage 0 — Check before you collect ✅ done
- [x] `scraper/` folder, README, `.gitignore`, `src/main.py`
- [x] Target classification + robots.txt result in README
- Commit: `Stage 0: classify scraping target`

## Stage 1 — Fetch once, cache once
- [x] Download catalogue page 1 with an honest `User-Agent` (e.g. `FlyRankInternshipA9/1.0 (+repo-link)`)
- [x] Set a request timeout
- [x] Check status code — only `200` proceeds
- [x] Save HTML to `cache/catalogue-page-1.html`; read from cache on subsequent runs
- [ ] Checkpoint: run twice — first prints `FETCH` + creates file, second prints `CACHE HIT`; both report response size, neither dumps full HTML
- Commit: `Stage 1: fetch and cache HTML`

## Stage 2 — Find all three pages
- [ ] Parse cached page with Beautiful Soup
- [ ] Collect every book link on page 1, convert relative → absolute URLs via `urljoin` (never string concat)
- [ ] Follow the site's own "next" link through page 2 → page 3, then stop
- [ ] ≥500ms delay between real (non-cached) requests
- [ ] De-duplicate links
- [ ] Checkpoint: prints `catalogue_pages=3`, `discovered=60`, `unique_urls=60`; rerun matches, mostly from cache
- Commit: `Stage 2: discover three catalogue pages`

## Stage 3 — Extract the raw records
- [ ] For each of the 60 book pages, fetch/cache with same politeness (user-agent, timeout, status check, delay)
- [ ] Extract: `title`, `product_url`, `price_text`, `availability_text`, `rating_text`, `description`, `source_page`, `fetched_at`
- [ ] Selectors scoped to the product area, not the whole doc
- [ ] Missing description → `null` (never invented)
- [ ] Checkpoint: print one full raw record (all 8 keys) + `detail_pages=60`
- Commit: `Stage 3: extract book details`

## Stage 4 — Clean it, check it, store it
- [ ] Normalize `price_text` → numeric `price_gbp`, keep raw text alongside
- [ ] Use absolute `product_url` as canonical identity (de-dupe)
- [ ] Define record schema with Pydantic (required fields, types, `description` optional)
- [ ] Validate every record before storing; failures → `errors.json` with reason
- [ ] Write valid records to `output/books.json`; rerun must stay at 60 (idempotent, not 120)
- [ ] Checkpoint: exactly 60 records, all `price_gbp` numeric, all URLs `https://`, stable after rerun
- Commit: `Stage 4: validate normalized records`

## Stage 5 — One bad page must not kill the run
- [ ] Handle each page independently — one failure logged & skipped, doesn't stop the run
- [ ] Retry once on timeout/5xx; never retry 404 or 403
- [ ] Write `output/run-report.json`: start time, duration, pages fetched, cache hits, valid/invalid records, failed pages
- [ ] Prove it: add one deliberately fake book URL, rerun, confirm `books.json` still has 60 good records and `run-report.json` shows `failed_pages: 1`
- Commit: `Stage 5: survive failures, report the run`

## Stage 6 — Publish the evidence (required)
- [ ] Push to public GitHub repo; `cache/` gitignored, one sample output committed
- [ ] Finish README: target classification, run command, lane/install steps, record schema, politeness rules, one honest limitation
- [ ] Paste a real `run-report.json` into README + one sentence on why no browser was needed
- [ ] Add a short ethics note (official APIs first, never bypass logins/paywalls/blocks, collect only what's needed)
- [ ] Checkpoint: stranger can clone → one command → `books.json` + `run-report.json` in <5 min; `git log --oneline` shows 7+ stage commits
- Commit: `Stage 6: publish scraper evidence` — then push everything

## Requirements checklist (must all pass)
- [ ] One command → exactly 3 catalogue pages → 60 unique book URLs
- [ ] Every detail page has all 8 raw fields + numeric `price_gbp`
- [ ] Schema validation before storage; failures in `errors.json` with reason
- [ ] `output/books.json` = exactly 60 unique records, stable across reruns
- [ ] Every real request: user-agent, timeout, ≥500ms delay, status check; dev reads cache
- [ ] README documents target classification + robots result
- [ ] One deliberately broken URL logged/skipped without killing the run
- [ ] `output/run-report.json` reports counts, failures, cache hits, duration
- [ ] Public repo, 7+ meaningful commits, 5-minute-runnable README

## Optional — pick any/none
- [ ] Stretch: browser cost comparison (`quotes.toscrape.com/js` via plain HTTP vs Playwright)
- [ ] Parser tests: 5+ unit tests (price normalization, relative→absolute URL, missing description, duplicate URL, malformed fixture)
- [ ] CSV export (`books.csv`)
- [ ] Changed-since-last-run diffing (hash records: new/changed/unchanged/gone)
- [ ] Tiny local dashboard (record count, price range, failures, freshness)
- [ ] Selector fixtures for missing description / extra whitespace
- [ ] Real retry rules: exponential backoff + `Retry-After`, structured logs
- [ ] Background execution w/ concurrency cap + idempotent writes (if A7 done)
- [ ] Local AI enrichment via Ollama (category + summary, schema-forced, kept separate from scraped facts)
- [ ] **Bonus — AI rematch**: write your own prompt (no peeking at spec), generate in `ai-version/` or separate branch, run against your checkpoints, write "AI vs me" README section (3+ concrete diffs), one rematch iteration. Commit: `Bonus: AI vs me`

## Notes
- Don't gold-plate Stage 5 — next week (A16) builds the production retry/backoff/structured-logging version.
- Keep raw text and cleaned values side by side (provenance matters).
