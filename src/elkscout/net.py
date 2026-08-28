"""HTTP client: retries with backoff, timeouts, proxy/CA env passthrough,
cache-first reads, and a hard --offline mode.

All sources go through Net so a primed cache makes the whole pipeline
reproducible without network access.
"""

from __future__ import annotations

import json
import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import Cache

log = logging.getLogger("elkscout.net")

USER_AGENT = "elkscout/0.1 (elk habitat research pipeline)"


class OfflineError(RuntimeError):
    """Raised in offline mode when a request has no cached response."""

    def __init__(self, url: str, source: str):
        super().__init__(
            f"offline mode: no cached response for {source} request {url}. "
            "Run `elkscout fetch` on a network-connected machine (see README)."
        )


class Net:
    def __init__(self, cache: Cache, offline: bool = False, timeout: float = 90.0, max_retries: int = 4):
        self.cache = cache
        self.offline = offline
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers["User-Agent"] = USER_AGENT
        # requests honors HTTPS_PROXY / REQUESTS_CA_BUNDLE env vars natively.

    def fetch_bytes(
        self,
        url: str,
        params: dict | None = None,
        *,
        source: str,
        ext: str,
        method: str = "GET",
        data: dict | str | None = None,
        min_interval_s: float = 0.0,
    ) -> bytes:
        """Cache-first fetch. `source` scopes the cache dir; `ext` names the payload type."""
        body = None
        if data is not None:
            body = data if isinstance(data, str) else json.dumps(data, sort_keys=True)
        key = Cache.key(method, url, params, body)
        cached = self.cache.get(source, key, ext)
        if cached is not None:
            return cached
        if self.offline:
            raise OfflineError(url, source)
        if min_interval_s > 0:
            time.sleep(min_interval_s)
        log.info("fetch %s %s", source, url)
        if method.upper() == "POST":
            resp = self.session.post(url, params=params, data=data, timeout=self.timeout)
        else:
            resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.content
        self.cache.put(source, key, ext, payload, url, params)
        return payload

    def fetch_json(self, url: str, params: dict | None = None, **kw) -> dict:
        kw.setdefault("ext", "json")
        raw = self.fetch_bytes(url, params, **kw)
        out = json.loads(raw)
        # ArcGIS servers return HTTP 200 with an error body; surface those.
        if isinstance(out, dict) and "error" in out and "features" not in out:
            raise RuntimeError(f"server error from {url}: {out['error']}")
        return out
