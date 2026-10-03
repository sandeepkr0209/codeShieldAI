"""
Playwright-based crawler for dynamic reconnaissance.

Discovers pages, links, and forms within scope, respecting the scan's
ScanScope limits (max pages, timeouts, same-origin restriction).

Uses Playwright's synchronous API. The async web scan pipeline runs this
crawler in a worker thread using asyncio.to_thread(), which avoids the
Windows/Uvicorn event-loop subprocess limitation.

Requires:
    pip install playwright
    playwright install chromium
"""

import logging
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from app.services.web_analysis.scope import ScanScope

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredForm:
    action_url: str
    method: str
    input_names: list[str] = field(default_factory=list)


@dataclass
class DiscoveredPage:
    url: str
    title: str | None
    status_code: int | None
    forms: list[DiscoveredForm] = field(default_factory=list)
    links: list[str] = field(default_factory=list)


@dataclass
class CrawlResult:
    pages: list[DiscoveredPage] = field(default_factory=list)
    js_resources: set[str] = field(default_factory=set)
    truncated: bool = False


def is_playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False


def crawl(scope: ScanScope) -> CrawlResult:
    """
    Crawl an authorized web application using Playwright's synchronous API.

    This function is intentionally synchronous. The async web scan pipeline
    runs it in a worker thread using asyncio.to_thread().
    """

    result = CrawlResult()

    if not is_playwright_available():
        logger.warning(
            "Playwright not installed — skipping dynamic reconnaissance"
        )
        return result

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning(
            "Playwright sync API import failed — skipping dynamic reconnaissance"
        )
        return result

    visited: set[str] = set()
    queue: list[str] = [scope.target_url]
    start_time = time.monotonic()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context_kwargs = {"ignore_https_errors": True}
            if scope.auth:
                if scope.auth.cookies:
                    parsed = urlparse(scope.target_url)
                    context_kwargs["storage_state"] = {
                        "cookies": [
                            {
                                "name": name,
                                "value": value,
                                "domain": parsed.hostname,
                                "path": "/",
                            }
                            for name, value in scope.auth.cookies.items()
                        ],
                        "origins": [],
                    }
                if scope.auth.headers:
                    context_kwargs["extra_http_headers"] = scope.auth.headers
            
            context = browser.new_context(**context_kwargs)

            page = context.new_page()

            page.set_default_timeout(
                scope.request_timeout_seconds * 1000
            )

            while queue and len(result.pages) < scope.max_pages:

                # ---------------------------------------------
                # Global crawl timeout
                # ---------------------------------------------
                if (
                    time.monotonic() - start_time
                    > scope.crawl_timeout_seconds
                ):
                    result.truncated = True
                    break

                url = queue.pop(0)

                if url in visited:
                    continue

                if not scope.is_url_in_scope(url):
                    continue

                visited.add(url)

                # ---------------------------------------------
                # Load page
                # ---------------------------------------------
                try:
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.info(
                        "Crawler: failed to load %s (%s)",
                        url,
                        exc,
                    )
                    continue

                # ---------------------------------------------
                # Rate limiting
                # ---------------------------------------------
                if scope.rate_limit_delay_seconds > 0:
                    time.sleep(
                        scope.rate_limit_delay_seconds
                    )

                # ---------------------------------------------
                # Page information
                # ---------------------------------------------
                try:
                    title = page.title()
                except Exception:  # noqa: BLE001
                    title = None

                discovered = DiscoveredPage(
                    url=url,
                    title=title,
                    status_code=(
                        response.status
                        if response
                        else None
                    ),
                )

                # ---------------------------------------------
                # Links
                # ---------------------------------------------
                try:
                    hrefs = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.href)",
                    )
                except Exception:  # noqa: BLE001
                    hrefs = []

                for href in hrefs or []:
                    if not href:
                        continue

                    absolute = urljoin(url, href)

                    if (
                        scope.is_url_in_scope(absolute)
                        and absolute not in visited
                    ):
                        discovered.links.append(absolute)

                        if absolute not in queue:
                            queue.append(absolute)

                # ---------------------------------------------
                # Forms
                # ---------------------------------------------
                try:
                    forms_raw = page.eval_on_selector_all(
                        "form",
                        """
                        els => els.map(f => ({
                            action: f.action,
                            method: (f.method || 'get').toUpperCase(),
                            inputs: Array.from(f.elements)
                                .map(i => i.name)
                                .filter(Boolean)
                        }))
                        """,
                    )
                except Exception:  # noqa: BLE001
                    forms_raw = []

                for form in forms_raw or []:
                    discovered.forms.append(
                        DiscoveredForm(
                            action_url=urljoin(
                                url,
                                form.get("action") or url,
                            ),
                            method=form.get("method", "GET"),
                            input_names=form.get("inputs", []),
                        )
                    )

                # ---------------------------------------------
                # JavaScript resources
                # ---------------------------------------------
                try:
                    scripts = page.eval_on_selector_all(
                        "script[src]",
                        "els => els.map(e => e.src)",
                    )
                except Exception:  # noqa: BLE001
                    scripts = []

                for src in scripts or []:
                    if src:
                        result.js_resources.add(
                            urljoin(url, src)
                        )

                result.pages.append(discovered)

            # ---------------------------------------------
            # Cleanup
            # ---------------------------------------------
            context.close()
            browser.close()

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Crawler failed to start or complete: %s",
            exc,
        )

    if queue and len(result.pages) >= scope.max_pages:
        result.truncated = True

    return result