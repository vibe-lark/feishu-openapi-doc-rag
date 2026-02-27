#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from urllib.request import urlopen


DEFAULT_CDN_URL = "https://lf3-static.bytednsdoc.com/obj/eden-cn/oaleh7nupthpqbe/larkopenapidoc.json"


def download(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    with urlopen(url, timeout=60) as resp:
        tmp.write_bytes(resp.read())
    os.replace(tmp, out_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Download Feishu OpenAPI doc index JSON from CDN and build local index.")
    ap.add_argument("--url", default=DEFAULT_CDN_URL, help="CDN URL for larkopenapidoc.json")
    ap.add_argument(
        "--base-dir",
        type=Path,
        default=Path(os.path.expanduser("~/.openapi-doc-cli")),
        help="Where to store index.sqlite/state.json (default: ~/.openapi-doc-cli)",
    )
    args = ap.parse_args()

    json_path = args.base_dir / "larkopenapidoc.json"
    print(f"Downloading: {args.url}")
    download(args.url, json_path)
    print(f"Downloaded to: {json_path}")

    # Run using the vendored module shipped with this skill.
    skill_dir = Path(__file__).resolve().parents[1]
    vendor_dir = skill_dir / "vendor"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(vendor_dir)
    cmd = [
        sys.executable,
        "-m",
        "openapi_doc_cli",
        "build",
        "--input",
        str(json_path),
        "--base-dir",
        str(args.base_dir),
    ]
    print("Building index: " + " ".join(cmd))
    rc = os.spawnve(os.P_WAIT, sys.executable, cmd, env)
    if rc != 0:
        raise SystemExit(rc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
