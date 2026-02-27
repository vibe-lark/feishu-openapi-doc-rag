from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    base_dir: Path

    @property
    def state_path(self) -> Path:
        return self.base_dir / "state.json"

    @property
    def index_path(self) -> Path:
        return self.base_dir / "index.sqlite"

    @property
    def index_build_path(self) -> Path:
        return self.base_dir / "index.new.sqlite"

    @property
    def download_tmp_path(self) -> Path:
        return self.base_dir / "download.json.tmp"


def default_base_dir() -> Path:
    home = Path(os.path.expanduser("~"))
    return home / ".openapi-doc-cli"


def get_app_paths(base_dir: str | None = None) -> AppPaths:
    base = Path(base_dir) if base_dir else default_base_dir()
    return AppPaths(base_dir=base)

