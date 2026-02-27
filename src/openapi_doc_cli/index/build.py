from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .db import connect, fts5_available, init_fts, init_schema


@dataclass(frozen=True)
class BuildResult:
    doc_count: int
    max_update_time_ms: int
    fts_enabled: bool


def _require_str(x: Any, name: str) -> str:
    if not isinstance(x, str) or not x:
        raise ValueError(f"{name} must be a non-empty string")
    return x


def _require_int(x: Any, name: str) -> int:
    if not isinstance(x, int):
        raise ValueError(f"{name} must be an integer")
    return x


def _require_str_list(x: Any, name: str) -> List[str]:
    if not isinstance(x, list) or not all(isinstance(v, str) for v in x):
        raise ValueError(f"{name} must be an array of strings")
    return list(x)


def parse_items_from_file(json_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root JSON must be an object")
    items = data.get("data")
    if not isinstance(items, list):
        raise ValueError("root.data must be an array")
    out: List[Dict[str, Any]] = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValueError(f"data[{i}] must be an object")
        out.append(it)
    return out


def normalize_item(it: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    doc_id = _require_str(it.get("id"), "id")
    origin_id = _require_str(it.get("originId"), "originId")
    url = _require_str(it.get("url"), "url")
    directory = _require_str_list(it.get("directory"), "directory")
    pathnames = _require_str_list(it.get("pathnames"), "pathnames")
    update_time_ms = _require_int(it.get("updateTime"), "updateTime")
    content = _require_str(it.get("value"), "value")
    original_path = it.get("originalPath") if isinstance(it.get("originalPath"), str) else None

    directory_path = " / ".join(directory)
    pathnames_path = "/".join(pathnames)
    row = {
        "id": doc_id,
        "origin_id": origin_id,
        "url": url,
        "directory_json": json.dumps(directory, ensure_ascii=False),
        "directory_path": directory_path,
        "pathnames_json": json.dumps(pathnames, ensure_ascii=False),
        "pathnames_path": pathnames_path,
        "original_path": original_path,
        "update_time_ms": update_time_ms,
        "content": content,
    }
    return doc_id, row


def build_index(db_path: Path, items: Iterable[Dict[str, Any]]) -> BuildResult:
    conn = connect(db_path)
    try:
        init_schema(conn)
        enable_fts = fts5_available(conn)
        if enable_fts:
            init_fts(conn)

        conn.execute("BEGIN;")
        doc_count = 0
        max_update_time_ms = 0

        insert_sql = (
            """
            INSERT INTO docs(
              id, origin_id, url, directory_json, directory_path,
              pathnames_json, pathnames_path, original_path, update_time_ms, content
            ) VALUES (
              :id, :origin_id, :url, :directory_json, :directory_path,
              :pathnames_json, :pathnames_path, :original_path, :update_time_ms, :content
            );
            """
        )
        if enable_fts:
            insert_fts = (
                """
                INSERT INTO docs_fts(id, directory_path, pathnames_path, original_path, url, content)
                VALUES (:id, :directory_path, :pathnames_path, :original_path, :url, :content);
                """
            )

        for it in items:
            _, row = normalize_item(it)
            conn.execute(insert_sql, row)
            if enable_fts:
                conn.execute(insert_fts, row)
            doc_count += 1
            if row["update_time_ms"] > max_update_time_ms:
                max_update_time_ms = row["update_time_ms"]

        conn.execute("COMMIT;")
        return BuildResult(
            doc_count=doc_count, max_update_time_ms=max_update_time_ms, fts_enabled=enable_fts
        )
    except Exception:
        try:
            conn.execute("ROLLBACK;")
        except sqlite3.DatabaseError:
            pass
        raise
    finally:
        conn.close()
