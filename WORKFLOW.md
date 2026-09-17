# W5 · A9 — The Polite Scraper: Workflow

Source: `W5 - The polite scraper.pdf` (FlyRank Internship, Backend Track, Week 5, Assignment A9).
This is a reference map of the assignment, not a build order to copy-paste — work each stage yourself,
checkpoint it, then commit.

## 1. Stage roadmap (the 7 stages + bonus)

Each stage box lists its **checkpoint** (how you prove it works) and its **commit message**.

```mermaid
flowchart TD
    S0["Stage 0 — Check before you collect\nClassify the target + robots.txt"]
    S1["Stage 1 — Fetch once, cache once\nUser-agent, timeout, status check, cache"]
    S2["Stage 2 — Find all three pages\nParse + urljoin + follow 'next' + dedupe"]
    S3["Stage 3 — Extract the raw records\n8 raw fields per book, scoped selectors"]
    S4["Stage 4 — Clean it, check it, store it\nNormalize, schema-validate, books.json"]
    S5["Stage 5 — Survive failures, report\nSkip bad pages, retry rules, run-report.json"]
    S6["Stage 6 — Publish the evidence\nPublic repo, README, sample output"]
    B["Bonus — AI rematch\nPrompt from memory, ai-version/, diff vs hand-built"]

    S0 -->|"Commit: Stage 0: classify scraping target"| S1
    S1 -->|"Commit: Stage 1: fetch and cache HTML"| S2
    S2 -->|"Commit: Stage 2: discover three catalogue pages"| S3
    S3 -->|"Commit: Stage 3: extract book details"| S4
    S4 -->|"Commit: Stage 4: validate normalized records"| S5
    S5 -->|"Commit: Stage 5: survive failures, report the run"| S6
    S6 -->|"Commit: Stage 6: publish scraper evidence"| Done(["Done — submit"])
    S6 -.optional.-> B
    B -.->|"Commit: Bonus: AI vs me"| Done

    classDef required fill:#1f6f4a,stroke:#0d3b26,color:#fff;
    classDef optional fill:#3a3a3a,stroke:#1f1f1f,color:#fff,stroke-dasharray: 4 3;
    class S0,S1,S2,S3,S4,S5,S6,Done required;
    class B optional;
```

| Stage | Checkpoint (proves it works) |
| --- | --- |
| 0 | README names target, 3-page scope, robots result, and the "won't reuse without checking" sentence |
| 1 | Run twice: 1st prints `FETCH` + creates file, 2nd prints `CACHE HIT`; both report response size |
| 2 | Prints `catalogue_pages=3, discovered=60, unique_urls=60`; rerun matches, mostly cache |
| 3 | Prints one full raw record (all 8 keys) + `detail_pages=60` |
| 4 | `books.json` = exactly 60 records, all `price_gbp` numeric, all URLs `https://`; stable on rerun |
| 5 | With one fake URL injected: run still finishes, 60 good records survive, `run-report.json` shows `failed_pages: 1` |
| 6 | Stranger clones repo → one command → `books.json` + `run-report.json` in <5 min; `git log --oneline` shows 7+ commits |

## 2. The data pipeline itself (what runs each time)

This is the "big idea in 60 seconds" table from the PDF, drawn as the actual per-page control flow —
what Stages 1–5 build up into.

```mermaid
flowchart TD
    Start(["Run scraper"]) --> Classify{{"Stage 0 done once:\ntarget classified,\nrobots.txt checked"}}
    Classify --> Fetch["Fetch page\n(user-agent + timeout)"]

    Fetch --> CacheCheck{"Cached copy\nexists?"}
    CacheCheck -- yes --> ReadCache["Read from cache/\n(no network, no delay)"]
    CacheCheck -- no --> HttpGet["HTTP GET the real site"]

    HttpGet --> StatusCheck{"status == 200?"}
    StatusCheck -- no --> ClassifyErr{"404 or 403?"}
    ClassifyErr -- yes --> LogSkip["Log + skip page\n(never retry)"]
    ClassifyErr -- no --> RetryOnce["Wait, retry once\n(timeout / 5xx only)"]
    RetryOnce --> StatusCheck2{"status == 200\non retry?"}
    StatusCheck2 -- no --> LogSkip
    StatusCheck2 -- yes --> SaveCache

    StatusCheck -- yes --> SaveCache["Save HTML to cache/\n(this is the proof of fetch)"]
    SaveCache --> Delay["Wait >=500ms\n(politeness delay)"]
    Delay --> ReadCache

    ReadCache --> Extract["Extract raw fields\n(title, price_text, availability_text,\nrating_text, description, product_url,\nsource_page, fetched_at)"]

    Extract --> MorePages{"More catalogue\npages / book links\nto visit?"}
    MorePages -- yes --> Fetch
    MorePages -- no --> Normalize["Normalize\nprice_text -> price_gbp (number)\nrelative -> absolute URL (urljoin)"]

    Normalize --> Validate{"Passes schema?\n(Zod / Pydantic)"}
    Validate -- no --> Errors["Append to errors.json\nwith reason"]
    Validate -- yes --> Dedupe["De-dupe by\ncanonical product_url"]

    Dedupe --> Store["Write output/books.json\n(idempotent: rerun stays at 60)"]
    Errors --> Report
    Store --> Report["Write output/run-report.json\nstart time, duration, pages fetched,\ncache hits, valid/invalid, failed pages"]
    LogSkip --> Report

    Report --> End(["Run complete"])
```

## 3. Key rules to keep visible while building

- **Politeness, every real request:** honest `User-Agent`, a `timeout`, a `>=500ms` delay, a status-code
  check before parsing — cached reads skip all of this.
- **Never invent data.** Missing `description` -> `null`. Never guess a field that wasn't on the page.
- **Retry policy:** retry once on timeout/`5xx`. Never retry `404` (won't exist) or `403` (site said no).
- **Idempotency:** rerunning the whole pipeline must still produce exactly 60 records in `books.json` —
  not 120. Identity = canonical (absolute) `product_url`.
- **Provenance:** every record keeps `source_page` and `fetched_at` — never overwritten.
- **`cache/` is gitignored** — only code + one sample output gets committed, per Stage 6.

## 4. Glossary quick-reference

| Term | One-line meaning |
| --- | --- |
| Sandbox | A site built for people to practice scraping on — your permission source |
| Cache | A saved local copy, read instead of re-requesting the live site during dev |
| Relative / Absolute URL | Partial link vs. full `https://...` link (convert with `urljoin`, never string concat) |
| Provenance | Where + when a fact came from, kept on every record |
| Canonical URL | The one address chosen as a record's stable identity |
| Idempotency | Running the job twice gives the same result, not duplicates |
| Schema validator | Checks a record has the right fields/types before storage (Zod / Pydantic) |
| Exponential backoff | Wait longer after each failed retry (1s, 2s, 4s...) |
| Retry-After | Server-specified wait time header — obey it instead of guessing |
