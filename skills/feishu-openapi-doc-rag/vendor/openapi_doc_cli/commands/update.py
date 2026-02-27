from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from ..http import fetch
from ..index.build import build_index, parse_items_from_file
from ..paths import AppPaths
from ..state import AppState, load_state, now_ms, save_state_atomic


DEFAULT_URL = "https://lf3-static.bytednsdoc.com/obj/eden-cn/oaleh7nupthpqbe/larkopenapidoc.json"


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def cmd_update(*, base_dir: Path, url: str, force: bool, timeout_s: int) -> int:
    paths = AppPaths(base_dir=base_dir)
    state = load_state(paths.state_path, default_url=url or DEFAULT_URL)
    if url:
        state.url = url
    if force:
        state.etag = None
        state.last_modified = None

    try:
        res = fetch(
            state.url,
            etag=state.etag,
            last_modified=state.last_modified,
            timeout_s=timeout_s,
        )
    except Exception as e:
        raise SystemExit(f"Failed to download: {e}")
    if res.status == 304:
        print("Up to date (304 Not Modified).")
        return 0

    if res.body is None:
        raise SystemExit("Empty response body")

    _write_bytes_atomic(paths.download_tmp_path, res.body)

    # Validate JSON before indexing.
    try:
        _ = json.loads(res.body.decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"Downloaded JSON is invalid: {e}")

    # Build into index.new.sqlite, then swap.
    if paths.index_build_path.exists():
        paths.index_build_path.unlink()
    result = build_index(paths.index_build_path, parse_items_from_file(paths.download_tmp_path))

    os.replace(paths.index_build_path, paths.index_path)

    state.etag = res.etag or state.etag
    state.last_modified = res.last_modified or state.last_modified
    state.last_successful_update_at_ms = now_ms()
    state.doc_count = result.doc_count
    state.max_update_time_ms = result.max_update_time_ms
    save_state_atomic(paths.state_path, state)

    print(f"Indexed {result.doc_count} docs. maxUpdateTime={result.max_update_time_ms}.")
    return 0
