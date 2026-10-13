"""Command-line interface. Single place where logging is configured."""

import argparse
import json
import logging
from pathlib import Path

from . import __version__
from .config import ScraperConfig
from .pipeline import run


def build_parser() -> argparse.ArgumentParser:
    defaults = ScraperConfig()
    p = argparse.ArgumentParser(
        description="Politely scrape book data into validated JSON."
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--base-url", default=defaults.base_url,
                   help="Catalogue root URL")
    p.add_argument("--pages", type=int, default=defaults.catalogue_pages,
                   help="Catalogue pages to process")
    p.add_argument("--delay", type=float, default=defaults.request_delay_seconds,
                   help="Seconds between real requests")
    p.add_argument("--timeout", type=float, default=defaults.timeout_seconds,
                   help="Per-request timeout in seconds")
    p.add_argument("--no-cache", action="store_true",
                   help="Bypass the local HTML cache")
    p.add_argument("--output-dir", type=Path, default=defaults.output_dir,
                   help="Directory for books.json, errors.json, run-report.json")
    p.add_argument("--cache-dir", type=Path, default=defaults.cache_dir,
                   help="Directory for cached HTML")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=args.log_level, format="%(levelname)s: %(message)s")
    config = ScraperConfig(
        base_url=args.base_url,
        catalogue_pages=args.pages,
        request_delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
        no_cache=args.no_cache,
    )
    report = run(config)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
