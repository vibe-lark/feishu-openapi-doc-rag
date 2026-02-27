from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ..index.db import connect


@dataclass
class Node:
    name: str
    children: Dict[str, "Node"] = field(default_factory=dict)
    doc_count: int = 0

    def child(self, name: str) -> "Node":
        existing = self.children.get(name)
        if existing is not None:
            return existing
        n = Node(name=name)
        self.children[name] = n
        return n


def _iter_directories(index_path: Path) -> Iterable[List[str]]:
    conn = connect(index_path)
    try:
        for row in conn.execute("SELECT directory_json FROM docs;").fetchall():
            raw = row["directory_json"]
            try:
                arr = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(arr, list) and all(isinstance(v, str) for v in arr):
                yield arr
    finally:
        conn.close()


def _build_tree(directories: Iterable[List[str]]) -> Node:
    root = Node(name="ROOT")
    for dir_parts in directories:
        cur = root
        for seg in dir_parts:
            cur.doc_count += 1
            cur = cur.child(seg)
        cur.doc_count += 1
    return root


def _find_subtree(root: Node, subtree: List[str]) -> Optional[Node]:
    cur = root
    for seg in subtree:
        nxt = cur.children.get(seg)
        if nxt is None:
            return None
        cur = nxt
    return cur


def _render(node: Node, *, max_depth: int, show_counts: bool, prefix: str = "", depth: int = 0) -> List[str]:
    lines: List[str] = []
    if depth >= max_depth:
        return lines
    children = sorted(node.children.values(), key=lambda n: n.name)
    for i, ch in enumerate(children):
        is_last = i == len(children) - 1
        branch = "└─ " if is_last else "├─ "
        label = ch.name
        if show_counts:
            label = f"{label}  (docs={ch.doc_count})"
        lines.append(f"{prefix}{branch}{label}")
        extension = "   " if is_last else "│  "
        lines.extend(_render(ch, max_depth=max_depth, show_counts=show_counts, prefix=prefix + extension, depth=depth + 1))
    return lines


def cmd_tree(*, index_path: Path, subtree: List[str], max_depth: int, show_counts: bool) -> int:
    if not index_path.exists():
        raise SystemExit(f"Index not found: {index_path}. Run `openapi-doc update` first.")
    root = _build_tree(_iter_directories(index_path))
    start = _find_subtree(root, subtree) if subtree else root
    if start is None:
        print("No such path: " + " / ".join(subtree))
        return 1
    header = "ROOT" if not subtree else "ROOT / " + " / ".join(subtree)
    out_lines = [header] + _render(start, max_depth=max_depth, show_counts=show_counts)
    print("\n".join(out_lines))
    return 0
