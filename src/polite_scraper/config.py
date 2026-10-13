"""Runtime configuration. Single place to change scope or politeness."""

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_USER_AGENT = (
    "PoliteScraper/1.0 (+https://github.com/shuakyle21/the-polite-scraper)"
)


@dataclass
class ScraperConfig:
    base_url: str = "https://books.toscrape.com/catalogue"
    catalogue_pages: int = 3
    request_delay_seconds: float = 0.5
    timeout_seconds: float = 5.0
    retry_wait_seconds: float = 1.0
    user_agent: str = DEFAULT_USER_AGENT
    cache_dir: Path = field(default_factory=lambda: Path("data/cache"))
    output_dir: Path = field(default_factory=lambda: Path("data/output"))
    no_cache: bool = False

    @property
    def books_file(self) -> Path:
        return self.output_dir / "books.json"

    @property
    def errors_file(self) -> Path:
        return self.output_dir / "errors.json"

    @property
    def run_report_file(self) -> Path:
        return self.output_dir / "run-report.json"

    def ensure_dirs(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
