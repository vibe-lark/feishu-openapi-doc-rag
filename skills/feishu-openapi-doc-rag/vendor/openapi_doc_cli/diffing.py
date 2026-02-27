from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .index.db import connect


@dataclass(frozen=True)
class DocFingerprint:
    id: str
    url: str
    directory_path: str
    update_time_ms: int
    meta_hash: str
    content_hash: str


@dataclass(frozen=True)
class DiffResult:
    added: List[str]
    removed: List[str]
    changed: List[str]


def _sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.encode("utf-8", errors="replace"))
    return h.hexdigest()


def load_doc_fingerprints(index_path: Path) -> Dict[str, DocFingerprint]:
    conn = connect(index_path)
    try:
        rows = conn.execute(
            """
            SELECT id, url, directory_path, update_time_ms, original_path, pathnames_path, content
            FROM docs;
            """
        ).fetchall()
        out: Dict[str, DocFingerprint] = {}
        for r in rows:
            meta_payload = json.dumps(
                {
                    "url": r["url"],
                    "directory_path": r["directory_path"],
                    "original_path": r["original_path"],
                    "pathnames_path": r["pathnames_path"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            meta_hash = _sha256_text(meta_payload)
            content_hash = _sha256_text(r["content"] or "")
            out[r["id"]] = DocFingerprint(
                id=r["id"],
                url=r["url"],
                directory_path=r["directory_path"],
                update_time_ms=int(r["update_time_ms"]),
                meta_hash=meta_hash,
                content_hash=content_hash,
            )
        return out
    finally:
        conn.close()


def compute_diff(old: Dict[str, DocFingerprint], new: Dict[str, DocFingerprint]) -> DiffResult:
    old_ids = set(old.keys())
    new_ids = set(new.keys())

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    changed: List[str] = []
    for doc_id in sorted(old_ids & new_ids):
        a = old[doc_id]
        b = new[doc_id]
        if a.meta_hash != b.meta_hash or a.content_hash != b.content_hash:
            changed.append(doc_id)
    return DiffResult(added=added, removed=removed, changed=changed)

