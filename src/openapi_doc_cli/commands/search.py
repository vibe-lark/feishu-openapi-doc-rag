from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

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
        query = query.strip()
        tokens = smart_tokens(query)
        if _contains_cjk(query):
            rows = _search_cjk(conn=conn, query=query, tokens=tokens, limit=limit, offset=offset)
            return [SearchResult(id=r["id"], directory_path=r["directory_path"], url=r["url"]) for r in rows]
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


def _search_cjk(*, conn, query: str, tokens: List[str], limit: int, offset: int):
    rows = conn.execute(
        """
        SELECT id, directory_path, url, content, update_time_ms
        FROM docs;
        """
    ).fetchall()
    scored = []
    for row in rows:
        searchable = "\n".join((row["directory_path"], row["url"], row["content"]))
        exact_hits = {
            "directory_path": query in row["directory_path"],
            "url": query in row["url"],
            "content": query in row["content"],
        }
        token_hits = [t for t in tokens if t and t in searchable]

        if not any(exact_hits.values()) and (not tokens or len(token_hits) != len(tokens)):
            continue

        score = 0
        if exact_hits["directory_path"]:
            score += 4000
            if row["directory_path"].split(" / ")[-1] == query:
                score += 1000
        if exact_hits["url"]:
            score += 2500
        if exact_hits["content"]:
            score += 2000

        score += len(token_hits) * 250
        directory_token_hits = sum(1 for t in tokens if t in row["directory_path"])
        content_token_hits = sum(1 for t in tokens if t in row["content"])
        score += directory_token_hits * 300
        score += content_token_hits * 100
        if tokens and directory_token_hits == len(tokens):
            score += 800
        elif tokens and content_token_hits == len(tokens):
            score += 300

        exact_pos = _first_nonzero(
            row["directory_path"].find(query),
            row["url"].find(query),
            row["content"].find(query),
        )
        scored.append((score, exact_pos, row["update_time_ms"], row))

    scored.sort(key=lambda item: (-item[0], item[1], -item[2]))
    return [row for _, _, _, row in scored[offset : offset + limit]]


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=? LIMIT 1;",
        (name,),
    ).fetchone()
    return row is not None


def _fts_phrase(token: str) -> str:
    # Use FTS phrase query syntax to treat the token literally.
    return '"' + token.replace('"', '""') + '"'


def _contains_cjk(text: str) -> bool:
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def _first_nonzero(*positions: int) -> int:
    normalized = [p for p in positions if p >= 0]
    return min(normalized) if normalized else 10**9


def cmd_search(*, index_path: Path, query: str, limit: int, offset: int) -> int:
    results = search(index_path=index_path, query=query, limit=limit, offset=offset)
    if not results:
        print(f'0 results found for "{query}". Please try shorter keywords or English API paths.')
        return 0
    for r in results:
        print(f"{r.directory_path}\n  {r.url}\n  id={r.id}\n")
    return 0
