from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .show import resolve_doc
from ..index.db import connect


def cmd_open(*, index_path: Path, selector: str, print_only: bool = False) -> int:
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

    if print_only:
        print(doc.url)
        return 0

    if sys.platform == "darwin":
        subprocess.run(["open", doc.url], check=False)
        return 0
    # best-effort fallback: print URL
    print(doc.url)
    return 0

