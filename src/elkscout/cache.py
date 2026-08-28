"""Request-level disk cache.

Every network response is cached under data/cache/<source>/<sha256>.<ext> with a
manifest line recording the URL, params, and fetch time — so re-runs are fast,
reproducible, and possible fully offline once primed.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)

    @staticmethod
    def key(method: str, url: str, params: dict | None, body: str | bytes | None) -> str:
        canon = {
            "method": method.upper(),
            "url": url,
            "params": sorted((str(k), str(v)) for k, v in (params or {}).items()),
            "body": body.decode("utf-8", "replace") if isinstance(body, bytes) else (body or ""),
        }
        return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()

    def path(self, source: str, key: str, ext: str) -> Path:
        return self.root / source / f"{key}.{ext}"

    def get(self, source: str, key: str, ext: str) -> bytes | None:
        p = self.path(source, key, ext)
        return p.read_bytes() if p.exists() else None

    def put(self, source: str, key: str, ext: str, data: bytes, url: str, params: dict | None) -> Path:
        p = self.path(source, key, ext)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        manifest = p.parent / "manifest.jsonl"
        with open(manifest, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "key": key,
                        "ext": ext,
                        "url": url,
                        "params": {str(k): str(v) for k, v in (params or {}).items()},
                        "bytes": len(data),
                        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                )
                + "\n"
            )
        return p
