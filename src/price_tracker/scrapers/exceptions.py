class ScraperError(Exception):
    """Base exception. All scraper errors must inherit it."""

    def __init__(self, url: str, message: str | None = None):
        self.url = url

        msg = message or f"{self.__class__.__name__} failed at {url}"
        super().__init__(msg)


class ScraperTimeout(ScraperError):
    """Raised when the server takes too long to respond."""


class ScraperConnectionError(ScraperError):
    """Raised on physical network failures (DNS, broken pipe)."""


class ScraperServerError(ScraperError):
    """Raised on 5xx status codes. The target server crashed."""


class ScraperBlocked(ScraperError):
    """Raised on 401, 403, or Cloudflare blocks."""


class ScraperRateLimit(ScraperError):
    """Raised on 429 Too Many Requests."""

    def __init__(
        self, url: str, message: str | None = None, retry_after: float | None = None
    ):
        self.retry_after = retry_after
        super().__init__(url, message)


class ScraperParseError(ScraperError):
    """Raised when the HTML structure changes and parsing fails."""


class ScraperNotFound(ScraperError):
    """Raised on 404 or 410."""
