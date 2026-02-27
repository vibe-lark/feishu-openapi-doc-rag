from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


@dataclass(frozen=True)
class FetchResult:
    status: int
    body: bytes | None
    etag: str | None
    last_modified: str | None


def fetch(url: str, *, etag: str | None, last_modified: str | None, timeout_s: int) -> FetchResult:
    headers: Dict[str, str] = {"Accept": "application/json"}
    if etag:
        headers["If-None-Match"] = etag
    elif last_modified:
        headers["If-Modified-Since"] = last_modified

    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read()
            return FetchResult(
                status=int(status),
                body=body,
                etag=resp.headers.get("ETag"),
                last_modified=resp.headers.get("Last-Modified"),
            )
    except HTTPError as e:
        if e.code == 304:
            return FetchResult(status=304, body=None, etag=etag, last_modified=last_modified)
        raise
    except URLError:
        raise

