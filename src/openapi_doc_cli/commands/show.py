from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..index.db import connect


@dataclass(frozen=True)
class Doc:
    id: str
    origin_id: str
    url: str
    directory_path: str
    pathnames_path: str
    original_path: Optional[str]
    update_time_ms: int
    content: str


def resolve_doc(conn, selector: str) -> Optional[Doc]:
    if selector.startswith("http://") or selector.startswith("https://"):
        row = conn.execute(
            """
            SELECT id, origin_id, url, directory_path, pathnames_path, original_path, update_time_ms, content
            FROM docs
            WHERE url = ?
            LIMIT 1;
            """,
            (selector,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, origin_id, url, directory_path, pathnames_path, original_path, update_time_ms, content
            FROM docs
            WHERE id = ? OR original_path = ? OR pathnames_path = ?
            LIMIT 1;
            """,
            (selector, selector, selector),
        ).fetchone()
    if row is None:
        return None
    return Doc(
        id=row["id"],
        origin_id=row["origin_id"],
        url=row["url"],
        directory_path=row["directory_path"],
        pathnames_path=row["pathnames_path"],
        original_path=row["original_path"],
        update_time_ms=row["update_time_ms"],
        content=row["content"],
    )


def cmd_show(*, index_path: Path, selector: str, head: int = 0, show_content: bool = False) -> int:
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc update` first.")
    conn = connect(index_path)
    try:
        doc = resolve_doc(conn, selector)
    finally:
        conn.close()
    if doc is None:
        print("Not found: " + selector)
        return 1

    print(f"{doc.directory_path}")
    print(f"url={doc.url}")
    print(f"id={doc.id}")
    print(f"originId={doc.origin_id}")
    if doc.original_path:
        print(f"originalPath={doc.original_path}")
    print(f"pathnames={doc.pathnames_path}")
    print(f"updateTime={doc.update_time_ms}")

    if show_content or head > 0:
        text = doc.content
        if head > 0:
            text = "\n".join(text.splitlines()[:head])
        print("")
        print(text)

    return 0

