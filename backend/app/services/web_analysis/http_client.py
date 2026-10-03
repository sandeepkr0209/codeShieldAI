"""
Controlled HTTPX client for dynamic analysis.

Every request goes through here so redirect limits, timeouts, and
rate limiting are enforced in exactly one place. Never follows
redirects outside scope, and caps total redirects per request.
"""
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.web_analysis.scope import ScanScope

logger = logging.getLogger(__name__)


@dataclass
class ProbeResult:
    url: str
    method: str
    status_code: int | None
    headers: dict[str, str]
    cookies: list[str]  # cookie NAMES only — values are never stored
    body_snippet: str  # truncated, for reflection checks — never logged with secrets
    elapsed_ms: float
    error: str | None = None


# Headers that must never be persisted verbatim (may carry secrets).
_SENSITIVE_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "proxy-authorization", "x-api-key"}

MAX_BODY_SNIPPET_CHARS = 2000


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        k: ("[REDACTED]" if k.lower() in _SENSITIVE_HEADER_NAMES else v)
        for k, v in headers.items()
    }


class ControlledHttpClient:
    def __init__(self, scope: ScanScope):
        self.scope = scope
        self.request_count = 0
        client_kwargs = {
            "timeout": scope.request_timeout_seconds,
            "follow_redirects": False,
            "verify": False,
        }
        if scope.auth:
            if scope.auth.cookies:
                client_kwargs["cookies"] = scope.auth.cookies
            if scope.auth.headers:
                client_kwargs["headers"] = scope.auth.headers
        
        self._client = httpx.Client(**client_kwargs)

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, url: str, **kwargs) -> ProbeResult:
        if not self.scope.is_url_in_scope(url):
            return ProbeResult(url=url, method=method, status_code=None, headers={}, cookies=[], body_snippet="", elapsed_ms=0, error="out_of_scope")
        if self.request_count >= self.scope.max_requests:
            return ProbeResult(url=url, method=method, status_code=None, headers={}, cookies=[], body_snippet="", elapsed_ms=0, error="request_limit_reached")

        redirects_followed = 0
        current_url = url
        start = time.monotonic()

        while True:
            self.request_count += 1
            time.sleep(self.scope.rate_limit_delay_seconds)
            try:
                response = self._client.request(method, current_url, **kwargs)
            except httpx.HTTPError as exc:
                return ProbeResult(url=url, method=method, status_code=None, headers={}, cookies=[], body_snippet="", elapsed_ms=(time.monotonic() - start) * 1000, error=str(exc)[:300])

            if response.is_redirect and redirects_followed < self.scope.max_redirects:
                next_url = response.headers.get("location", "")
                next_url = httpx.URL(current_url).join(next_url).human_repr()
                if not self.scope.is_url_in_scope(next_url):
                    break  # do not follow a redirect out of scope
                current_url = next_url
                redirects_followed += 1
                continue
            break

        elapsed_ms = (time.monotonic() - start) * 1000
        cookie_names = list(response.cookies.keys())
        return ProbeResult(
            url=current_url,
            method=method,
            status_code=response.status_code,
            headers=redact_headers(dict(response.headers)),
            cookies=cookie_names,
            body_snippet=response.text[:MAX_BODY_SNIPPET_CHARS],
            elapsed_ms=elapsed_ms,
        )

    def get(self, url: str, **kwargs) -> ProbeResult:
        return self.request("GET", url, **kwargs)
