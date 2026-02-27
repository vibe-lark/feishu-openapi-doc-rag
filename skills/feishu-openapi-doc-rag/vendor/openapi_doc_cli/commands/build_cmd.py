from __future__ import annotations

import os
from pathlib import Path

from ..index.build import build_index, parse_items_from_file
from ..state import AppState, now_ms, save_state_atomic


def cmd_build(*, base_dir: Path, input_path: Path) -> int:
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    base_dir.mkdir(parents=True, exist_ok=True)
    index_build_path = base_dir / "index.new.sqlite"
    index_path = base_dir / "index.sqlite"

    if index_build_path.exists():
        index_build_path.unlink()

    items = parse_items_from_file(input_path)
    result = build_index(index_build_path, items)
    os.replace(index_build_path, index_path)
    # Record minimal local state for offline workflows.
    st = AppState(url=str(input_path))
    st.last_successful_update_at_ms = now_ms()
    st.doc_count = result.doc_count
    st.max_update_time_ms = result.max_update_time_ms
    save_state_atomic(base_dir / "state.json", st)

    print(f"Indexed {result.doc_count} docs from {input_path}.")
    return 0
