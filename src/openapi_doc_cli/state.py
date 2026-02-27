from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AppState:
    url: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    last_successful_update_at_ms: Optional[int] = None
    doc_count: Optional[int] = None
    max_update_time_ms: Optional[int] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "last_successful_update_at_ms": self.last_successful_update_at_ms,
            "doc_count": self.doc_count,
            "max_update_time_ms": self.max_update_time_ms,
        }

    @staticmethod
    def from_json(data: Dict[str, Any]) -> "AppState":
        url = data.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("state.url must be a non-empty string")
        return AppState(
            url=url,
            etag=data.get("etag") if isinstance(data.get("etag"), str) else None,
            last_modified=data.get("last_modified")
            if isinstance(data.get("last_modified"), str)
            else None,
            last_successful_update_at_ms=data.get("last_successful_update_at_ms")
            if isinstance(data.get("last_successful_update_at_ms"), int)
            else None,
            doc_count=data.get("doc_count") if isinstance(data.get("doc_count"), int) else None,
            max_update_time_ms=data.get("max_update_time_ms")
            if isinstance(data.get("max_update_time_ms"), int)
            else None,
        )


def load_state(path: Path, *, default_url: str) -> AppState:
    if not path.exists():
        return AppState(url=default_url)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("state file must be a JSON object")
    st = AppState.from_json(data)
    if not st.url:
        st.url = default_url
    return st


def save_state_atomic(path: Path, state: AppState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def now_ms() -> int:
    return int(time.time() * 1000)

