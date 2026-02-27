from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..diffing import compute_diff, load_doc_fingerprints


def _today_ymd() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def cmd_diff(*, base_dir: Path, previous_index_path: Path | None = None) -> int:
    index_path = base_dir / "index.sqlite"
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}")

    prev = previous_index_path or (base_dir / "index.prev.sqlite")
    if not prev.exists():
        print(f"No previous index snapshot found at {prev}. Nothing to diff yet.")
        return 0

    old = load_doc_fingerprints(prev)
    new = load_doc_fingerprints(index_path)
    diff = compute_diff(old, new)

    out_dir = base_dir / "diff"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _today_ymd()
    json_path = out_dir / f"{stamp}.json"
    summary_path = out_dir / f"{stamp}.summary.txt"

    json_path.write_text(json.dumps(asdict(diff), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_lines = [
        f"date: {stamp}",
        f"added: {len(diff.added)}",
        f"removed: {len(diff.removed)}",
        f"changed: {len(diff.changed)}",
        "",
    ]
    if diff.added:
        summary_lines.append("added (first 20):")
        summary_lines.extend(diff.added[:20])
        summary_lines.append("")
    if diff.removed:
        summary_lines.append("removed (first 20):")
        summary_lines.extend(diff.removed[:20])
        summary_lines.append("")
    if diff.changed:
        summary_lines.append("changed (first 20):")
        summary_lines.extend(diff.changed[:20])
        summary_lines.append("")

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {summary_path}")
    return 0


def snapshot_index(*, base_dir: Path) -> Path:
    """
    Copy current index.sqlite to index.prev.sqlite (atomic replace).
    """
    cur = base_dir / "index.sqlite"
    if not cur.exists():
        raise SystemExit(f"Index not found: {cur}")
    prev = base_dir / "index.prev.sqlite"
    tmp = base_dir / "index.prev.sqlite.tmp"
    tmp.write_bytes(cur.read_bytes())
    os.replace(tmp, prev)
    return prev

