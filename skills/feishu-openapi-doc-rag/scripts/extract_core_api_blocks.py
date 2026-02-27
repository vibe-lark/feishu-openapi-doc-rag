#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class CoreBlock:
    id: str
    url: str
    directory_path: str
    title: str | None
    http_url: str | None
    http_method: str | None


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_doc(conn: sqlite3.Connection, selector: str) -> Optional[sqlite3.Row]:
    if selector.startswith("http://") or selector.startswith("https://"):
        row = conn.execute(
            "SELECT id, url, directory_path, content FROM docs WHERE url=? LIMIT 1;", (selector,)
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, url, directory_path, content
            FROM docs
            WHERE id=? OR original_path=? OR pathnames_path=?
            LIMIT 1;
            """,
            (selector, selector, selector),
        ).fetchone()
    return row


def _extract_title(content: str) -> Optional[str]:
    # Prefer first markdown H1.
    for line in content.splitlines()[:80]:
        line = line.lstrip("\ufeff").strip()
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None


def _extract_http_url_method(content: str) -> Tuple[Optional[str], Optional[str]]:
    # Prefer markdown table rows if present.
    m_url = re.search(r"^HTTP URL\s*\|\s*(https?://\S+)\s*$", content, re.M)
    m_method = re.search(r"^HTTP Method\s*\|\s*([A-Z]+)\s*$", content, re.M)
    http_url = m_url.group(1).strip() if m_url else None
    http_method = m_method.group(1).strip() if m_method else None

    if http_url and http_method:
        return http_url, http_method

    # Fallback to "HTTP URL: ..." formats
    if http_url is None:
        m_url = re.search(r"^HTTP URL\s*[:：]\s*(https?://\S+)\s*$", content, re.M)
        if m_url:
            http_url = m_url.group(1).strip()
    if http_method is None:
        m_method = re.search(r"^HTTP Method\s*[:：]\s*([A-Z]+)\s*$", content, re.M)
        if m_method:
            http_method = m_method.group(1).strip()

    return http_url, http_method


def _extract_request_block(content: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract HTTP URL and Method from the "请求" table.
    Handles common markdown table formats:
      - "HTTP URL | https://..."
      - "HTTP Method | POST"
    """
    lines = content.splitlines()
    # Prefer a window after the "## 请求" header if present.
    for i, line in enumerate(lines):
        if line.strip().startswith("## 请求"):
            window = lines[i : i + 200]
            u, m = _extract_http_url_method("\n".join(window))
            if u or m:
                return u, m
    # Fallback: scan the whole doc.
    return _extract_http_url_method(content)


def extract_core_block(conn: sqlite3.Connection, selector: str) -> CoreBlock:
    row = _fetch_doc(conn, selector)
    if row is None:
        raise SystemExit(f"Not found: {selector}")
    content = row["content"] or ""
    title = _extract_title(content)
    http_url, http_method = _extract_request_block(content)
    return CoreBlock(
        id=row["id"],
        url=row["url"],
        directory_path=row["directory_path"],
        title=title,
        http_url=http_url,
        http_method=http_method,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract core API blocks from openapi_doc_cli index.sqlite")
    ap.add_argument("--db", type=Path, required=True, help="Path to index.sqlite")
    ap.add_argument("selectors", nargs="+", help="doc id/url/originalPath/pathnames_path")
    args = ap.parse_args()

    conn = _connect(args.db)
    try:
        for sel in args.selectors:
            blk = extract_core_block(conn, sel)
            print(f"[{blk.id}] {blk.title or '(no title)'}")
            print(f"dir: {blk.directory_path}")
            print(f"url: {blk.url}")
            if blk.http_url and blk.http_method:
                print(f"request: {blk.http_method} {blk.http_url}")
            else:
                print("request: (not found in first pass)")
            print("")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
