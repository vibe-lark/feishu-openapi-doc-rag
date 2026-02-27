from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

from ..index.db import connect
from .show import resolve_doc
from .search import search as fulltext_search


@dataclass(frozen=True)
class DocHit:
    id: str
    directory_path: str
    url: str


def ls_dirs(*, index_path: Path, prefix: Sequence[str]) -> List[str]:
    """
    List child directory segment names under the given directory prefix.
    """
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc build` or `openapi-doc update` first.")
    conn = connect(index_path)
    try:
        rows = conn.execute("SELECT directory_path FROM docs;").fetchall()
    finally:
        conn.close()

    prefix_path = " / ".join(prefix)
    children = set()
    for r in rows:
        path = r["directory_path"]
        if prefix_path:
            if not path.startswith(prefix_path + " / "):
                continue
            rest = path[len(prefix_path) + 3 :]
        else:
            rest = path
        segs = [s.strip() for s in rest.split(" / ") if s.strip()]
        if not segs:
            continue
        children.add(segs[0])
    return sorted(children)


def find_docs(*, index_path: Path, query: str, limit: int = 20) -> List[DocHit]:
    """
    Find docs by matching directory/url/path fields (metadata-only best effort).
    """
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc build` or `openapi-doc update` first.")
    conn = connect(index_path)
    try:
        like = f"%{query}%"
        rows = conn.execute(
            """
            SELECT id, directory_path, url
            FROM docs
            WHERE directory_path LIKE ? OR url LIKE ? OR pathnames_path LIKE ? OR original_path LIKE ?
            ORDER BY update_time_ms DESC
            LIMIT ?;
            """,
            (like, like, like, like, limit),
        ).fetchall()
        return [DocHit(id=r["id"], directory_path=r["directory_path"], url=r["url"]) for r in rows]
    finally:
        conn.close()


def cat_doc(*, index_path: Path, selector: str) -> str:
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc build` or `openapi-doc update` first.")
    conn = connect(index_path)
    try:
        doc = resolve_doc(conn, selector)
        if doc is None:
            raise SystemExit("Not found: " + selector)
        return doc.content
    finally:
        conn.close()


def grep_docs(*, index_path: Path, pattern: str, limit: int = 20) -> List[DocHit]:
    """
    Search content with FTS when available; otherwise best-effort LIKE.
    """
    results = fulltext_search(index_path=index_path, query=pattern, limit=limit, offset=0)
    return [DocHit(id=r.id, directory_path=r.directory_path, url=r.url) for r in results]


def cmd_ls(*, index_path: Path, prefix: List[str]) -> int:
    for name in ls_dirs(index_path=index_path, prefix=prefix):
        print(name)
    return 0


def cmd_find(*, index_path: Path, query: str, limit: int) -> int:
    for h in find_docs(index_path=index_path, query=query, limit=limit):
        print(f"{h.directory_path}\n  {h.url}\n  id={h.id}\n")
    return 0


def cmd_cat(*, index_path: Path, selector: str) -> int:
    print(cat_doc(index_path=index_path, selector=selector))
    return 0


def cmd_grep(*, index_path: Path, pattern: str, limit: int) -> int:
    for h in grep_docs(index_path=index_path, pattern=pattern, limit=limit):
        print(f"{h.directory_path}\n  {h.url}\n  id={h.id}\n")
    return 0

