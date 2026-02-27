from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..index.db import connect, fts5_available
from ..text import smart_tokens


@dataclass(frozen=True)
class SearchResult:
    id: str
    directory_path: str
    url: str


def search(*, index_path: Path, query: str, limit: int = 20, offset: int = 0) -> List[SearchResult]:
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc update` first.")
    conn = connect(index_path)
    try:
        tokens = smart_tokens(query)
        # For FTS: treat whitespace as AND between tokens by default.
        fts_query = query if not tokens else " ".join(tokens)
        fts_query_quoted = query if not tokens else " ".join(_fts_phrase(t) for t in tokens)
        use_fts = fts5_available(conn) and _table_exists(conn, "docs_fts")
        if use_fts:
            try:
                rows = conn.execute(
                    """
                    SELECT d.id, d.directory_path, d.url, bm25(docs_fts) AS score
                    FROM docs_fts f
                    JOIN docs d ON d.id = f.id
                    WHERE docs_fts MATCH ?
                    ORDER BY score ASC
                    LIMIT ? OFFSET ?;
                    """,
                    (fts_query, limit, offset),
                ).fetchall()
            except Exception:
                rows = conn.execute(
                    """
                    SELECT d.id, d.directory_path, d.url, bm25(docs_fts) AS score
                    FROM docs_fts f
                    JOIN docs d ON d.id = f.id
                    WHERE docs_fts MATCH ?
                    ORDER BY score ASC
                    LIMIT ? OFFSET ?;
                    """,
                    (fts_query_quoted, limit, offset),
                ).fetchall()
            # CJK tokenization can make "natural" substring queries miss. If FTS
            # yields no results, fall back to LIKE for a best-effort experience.
            if not rows:
                like = f"%{query}%"
                # Also allow token-wise LIKE when the phrase doesn't appear contiguously.
                token_likes = [f"%{t}%" for t in tokens] if tokens else []
                where = "directory_path LIKE ? OR url LIKE ? OR content LIKE ?"
                params: List[object] = [like, like, like]
                if token_likes:
                    for _ in token_likes:
                        where += " OR content LIKE ?"
                    params.extend(token_likes)
                rows = conn.execute(
                    """
                    SELECT
                      id,
                      directory_path,
                      url,
                      CASE
                        WHEN directory_path LIKE ? THEN 3
                        WHEN url LIKE ? THEN 2
                        WHEN content LIKE ? THEN 1
                        ELSE 0
                      END AS score,
                      instr(directory_path, ?) AS dir_pos,
                      instr(url, ?) AS url_pos,
                      instr(content, ?) AS content_pos
                    FROM docs
                    WHERE """
                    + where
                    + """
                    ORDER BY
                      score DESC,
                      (dir_pos = 0) ASC, dir_pos ASC,
                      (url_pos = 0) ASC, url_pos ASC,
                      (content_pos = 0) ASC, content_pos ASC,
                      update_time_ms DESC
                    LIMIT ? OFFSET ?;
                    """,
                    tuple(
                        [
                            like,
                            like,
                            like,
                            query,
                            query,
                            query,
                        ]
                        + params
                        + [limit, offset]
                    ),
                ).fetchall()
        else:
            like = f"%{query}%"
            token_likes = [f"%{t}%" for t in tokens] if tokens else []
            where = "directory_path LIKE ? OR url LIKE ? OR content LIKE ?"
            params: List[object] = [like, like, like]
            if token_likes:
                for _ in token_likes:
                    where += " OR content LIKE ?"
                params.extend(token_likes)
            rows = conn.execute(
                """
                SELECT
                  id,
                  directory_path,
                  url,
                  CASE
                    WHEN directory_path LIKE ? THEN 3
                    WHEN url LIKE ? THEN 2
                    WHEN content LIKE ? THEN 1
                    ELSE 0
                  END AS score,
                  instr(directory_path, ?) AS dir_pos,
                  instr(url, ?) AS url_pos,
                  instr(content, ?) AS content_pos
                FROM docs
                WHERE """
                + where
                + """
                ORDER BY
                  score DESC,
                  (dir_pos = 0) ASC, dir_pos ASC,
                  (url_pos = 0) ASC, url_pos ASC,
                  (content_pos = 0) ASC, content_pos ASC,
                  update_time_ms DESC
                LIMIT ? OFFSET ?;
                """,
                tuple([like, like, like, query, query, query] + params + [limit, offset]),
            ).fetchall()
        return [SearchResult(id=r["id"], directory_path=r["directory_path"], url=r["url"]) for r in rows]
    finally:
        conn.close()


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? LIMIT 1;",
        (name,),
    ).fetchone()
    return row is not None


def _fts_phrase(token: str) -> str:
    # Use FTS phrase query syntax to treat the token literally.
    return '"' + token.replace('"', '""') + '"'


def cmd_search(*, index_path: Path, query: str, limit: int, offset: int) -> int:
    results = search(index_path=index_path, query=query, limit=limit, offset=offset)
    for r in results:
        print(f"{r.directory_path}\n  {r.url}\n  id={r.id}\n")
    return 0
