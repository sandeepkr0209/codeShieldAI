"""
Scope control for dynamic (web) analysis.

The Security Agent cannot decide to test arbitrary domains — every
dynamic check goes through `ScanScope.is_url_in_scope()` first. Scope
is same-origin-by-default: only the project's own target host (plus
any explicitly allowed subdomains) may be crawled or tested.
"""
from dataclasses import dataclass, field
from urllib.parse import urlparse

# Hard defaults — deliberately conservative for a training/demo tool.
# These are NOT user-configurable via the API in this implementation
# (kept fixed so scope can never be widened by a crafted request).
DEFAULT_MAX_PAGES = 25
DEFAULT_MAX_REQUESTS = 100
DEFAULT_MAX_SCAN_DURATION_SECONDS = 300
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_CRAWL_TIMEOUT_SECONDS = 15
DEFAULT_RATE_LIMIT_DELAY_SECONDS = 0.3  # minimum delay between requests
MAX_REDIRECTS = 3


@dataclass
class AuthConfig:
    """Optional authentication context for authenticated crawling."""
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ScanScope:
    target_url: str
    auth: AuthConfig | None = None
    allowed_hosts: set[str] = field(default_factory=set)
    max_pages: int = DEFAULT_MAX_PAGES
    max_requests: int = DEFAULT_MAX_REQUESTS
    max_duration_seconds: int = DEFAULT_MAX_SCAN_DURATION_SECONDS
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    crawl_timeout_seconds: int = DEFAULT_CRAWL_TIMEOUT_SECONDS
    rate_limit_delay_seconds: float = DEFAULT_RATE_LIMIT_DELAY_SECONDS
    max_redirects: int = MAX_REDIRECTS

    def __post_init__(self) -> None:
        if not self.allowed_hosts:
            parsed = urlparse(self.target_url)
            if parsed.hostname:
                self.allowed_hosts = {parsed.hostname.lower()}

    def is_url_in_scope(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        return host in self.allowed_hosts


class ScopeValidationError(Exception):
    pass


def validate_target(target_url: str) -> ScanScope:
    """Validates the project's target URL is a plausible, safe scan
    target and builds its ScanScope. Rejects non-http(s) schemes and
    obviously-invalid URLs before any request is ever made."""
    parsed = urlparse(target_url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ScopeValidationError(f"Unsupported URL scheme: {parsed.scheme or '(none)'}")
    if not parsed.hostname:
        raise ScopeValidationError("Target URL has no hostname")

    return ScanScope(target_url=target_url.strip())
