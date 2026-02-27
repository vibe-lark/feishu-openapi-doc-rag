#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Node:
    name: str
    children: Dict[str, "Node"] = field(default_factory=dict)
    leaf_count: int = 0
    item_count: int = 0

    def child(self, name: str) -> "Node":
        existing = self.children.get(name)
        if existing is not None:
            return existing
        n = Node(name=name)
        self.children[name] = n
        return n


def _safe_str(x: Any) -> Optional[str]:
    if isinstance(x, str):
        return x
    return None


def _safe_str_list(x: Any) -> Optional[List[str]]:
    if not isinstance(x, list):
        return None
    if not all(isinstance(v, str) for v in x):
        return None
    return list(x)


def load_items(path: Path) -> List[Dict[str, Any]]:
    with path.open("rb") as f:
        root = json.load(f)
    if not isinstance(root, dict):
        raise ValueError("Expected root JSON object")
    data = root.get("data")
    if not isinstance(data, list):
        raise ValueError("Expected root.data to be an array")
    items: List[Dict[str, Any]] = []
    for i, it in enumerate(data):
        if not isinstance(it, dict):
            raise ValueError(f"Expected data[{i}] to be an object")
        items.append(it)
    return items


def build_tree(items: List[Dict[str, Any]]) -> Node:
    root = Node(name="ROOT")
    for it in items:
        directory = _safe_str_list(it.get("directory")) or []
        # Some docs may have empty directory; keep them under ROOT.
        cur = root
        for seg in directory:
            cur = cur.child(seg)
        cur.item_count += 1
        cur.leaf_count += 1
    # Roll up counts.
    def roll(node: Node) -> Tuple[int, int]:
        leaf = node.leaf_count
        item = node.item_count
        for ch in node.children.values():
            l, i = roll(ch)
            leaf += l
            item += i
        node.leaf_count = leaf
        node.item_count = item
        return leaf, item

    roll(root)
    return root


def render_tree(
    node: Node,
    *,
    max_depth: int,
    max_children: int,
    show_counts: bool,
    prefix: str = "",
    depth: int = 0,
) -> List[str]:
    lines: List[str] = []
    if depth > max_depth:
        return lines

    children = sorted(node.children.values(), key=lambda n: n.name)
    if max_children > 0 and len(children) > max_children:
        children = children[:max_children]
        truncated = True
    else:
        truncated = False

    for idx, ch in enumerate(children):
        is_last = idx == len(children) - 1 and not truncated
        branch = "└─ " if is_last else "├─ "
        label = ch.name
        if show_counts:
            label = f"{label}  (docs={ch.item_count})"
        lines.append(f"{prefix}{branch}{label}")
        if depth < max_depth:
            extension = "   " if is_last else "│  "
            lines.extend(
                render_tree(
                    ch,
                    max_depth=max_depth,
                    max_children=max_children,
                    show_counts=show_counts,
                    prefix=prefix + extension,
                    depth=depth + 1,
                )
            )

    if truncated:
        lines.append(f"{prefix}└─ … (+{len(node.children) - max_children} more)")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a directory tree from larkopenapidoc.json (root.data[*].directory)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("larkopenapidoc.json"),
        help="Input JSON path (default: larkopenapidoc.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi_doc_tree.txt"),
        help="Output text path (default: openapi_doc_tree.txt)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=6,
        help="Max directory depth to render (default: 6)",
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=0,
        help="Limit children per node; 0 means unlimited (default: 0)",
    )
    parser.add_argument(
        "--no-counts",
        action="store_true",
        help="Do not show docs count per node",
    )
    args = parser.parse_args()

    items = load_items(args.input)
    tree = build_tree(items)

    header = [
        f"Input: {args.input}",
        f"Docs: {len(items)}",
        "",
        "ROOT",
    ]
    lines = header + render_tree(
        tree,
        max_depth=max(0, args.max_depth),
        max_children=max(0, args.max_children),
        show_counts=not args.no_counts,
    )
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

