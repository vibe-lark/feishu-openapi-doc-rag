from __future__ import annotations

import argparse
import sys

from .paths import get_app_paths
from .state import load_state

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openapi-doc", add_help=True)
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Override local data directory (default: ~/.openapi-doc-cli)",
    )
    sub = parser.add_subparsers(dest="command")
    sub.required = False

    tree = sub.add_parser("tree", help="Print directory tree")
    tree.add_argument("path", nargs="*", help="Directory segments to filter to a subtree")
    tree.add_argument("--depth", type=int, default=6, help="Max depth (default: 6)")
    tree.add_argument("--no-counts", action="store_true", help="Hide document counts")

    search = sub.add_parser("search", help="Full-text search")
    search.add_argument("query", help="Query string (FTS syntax when available)")
    search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    search.add_argument("--offset", type=int, default=0, help="Offset for pagination (default: 0)")

    show = sub.add_parser("show", help="Show document metadata (and optionally content)")
    show.add_argument("selector", help="id, url, originalPath, or pathnames_path")
    show.add_argument("--head", type=int, default=0, help="Print first N lines of content")
    show.add_argument("--content", action="store_true", help="Print full content (can be large)")

    op = sub.add_parser("open", help="Open the doc in browser (or print url)")
    op.add_argument("selector", help="id, url, originalPath, or pathnames_path")
    op.add_argument("--print", dest="print_only", action="store_true", help="Only print URL")

    upd = sub.add_parser("update", help="Download and rebuild local index")
    upd.add_argument("--url", default=None, help="Remote JSON URL")
    upd.add_argument("--force", action="store_true", help="Ignore cached ETag/Last-Modified")
    upd.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds (default: 20)")

    bld = sub.add_parser("build", help="Build local index from a local JSON file (offline)")
    bld.add_argument("--input", required=True, help="Path to local larkopenapidoc.json")

    ls = sub.add_parser("ls", help="List directories under a prefix")
    ls.add_argument("path", nargs="*", help="Directory prefix segments")

    fd = sub.add_parser("find", help="Find docs by metadata (path/url)")
    fd.add_argument("query", help="Search term (matched against directory/url/path fields)")
    fd.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")

    cat = sub.add_parser("cat", help="Print a document's content")
    cat.add_argument("selector", help="id, url, originalPath, or pathnames_path")

    gp = sub.add_parser("grep", help="Search docs content (FTS when available)")
    gp.add_argument("pattern", help="Pattern / query")
    gp.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")

    df = sub.add_parser("diff", help="Compute diff vs previous index snapshot (offline)")
    df.add_argument("--prev", default=None, help="Path to previous index.sqlite (default: <base>/index.prev.sqlite)")

    sub.add_parser("help")
    return parser


def _normalize_global_flags(argv: list[str]) -> list[str]:
    """
    Allow global flags like --base-dir to appear after subcommands.

    argparse only accepts top-level options before the subcommand; this
    normalizes a single known global option for better UX.
    """
    if "--base-dir" not in argv:
        return argv
    try:
        idx = argv.index("--base-dir")
    except ValueError:
        return argv
    if idx + 1 >= len(argv):
        return argv
    base_dir = argv[idx + 1]
    # Remove the pair and re-insert right after argv[0] (i.e. before subcommand).
    rest = argv[:idx] + argv[idx + 2 :]
    return ["--base-dir", base_dir] + rest


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    argv = _normalize_global_flags(argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__

        print(__version__)
        return 0

    if args.command == "tree":
        from .commands.tree import cmd_tree

        paths = get_app_paths(args.base_dir)
        # For offline commands we still load state for defaults later; for now it's ok
        # even if state file doesn't exist.
        _ = load_state(paths.state_path, default_url="")
        return cmd_tree(
            index_path=paths.index_path,
            subtree=args.path,
            max_depth=max(0, int(args.depth)),
            show_counts=not bool(args.no_counts),
        )

    if args.command == "search":
        from .commands.search import cmd_search

        paths = get_app_paths(args.base_dir)
        _ = load_state(paths.state_path, default_url="")
        return cmd_search(
            index_path=paths.index_path,
            query=args.query,
            limit=max(1, int(args.limit)),
            offset=max(0, int(args.offset)),
        )

    if args.command == "show":
        from .commands.show import cmd_show

        paths = get_app_paths(args.base_dir)
        _ = load_state(paths.state_path, default_url="")
        return cmd_show(
            index_path=paths.index_path,
            selector=args.selector,
            head=max(0, int(args.head)),
            show_content=bool(args.content),
        )

    if args.command == "open":
        from .commands.open_cmd import cmd_open

        paths = get_app_paths(args.base_dir)
        _ = load_state(paths.state_path, default_url="")
        return cmd_open(
            index_path=paths.index_path,
            selector=args.selector,
            print_only=bool(args.print_only),
        )

    if args.command == "update":
        from .commands.update import DEFAULT_URL, cmd_update

        paths = get_app_paths(args.base_dir)
        url = args.url or DEFAULT_URL
        return cmd_update(
            base_dir=paths.base_dir,
            url=url,
            force=bool(args.force),
            timeout_s=max(1, int(args.timeout)),
        )

    if args.command == "build":
        from pathlib import Path

        from .commands.build_cmd import cmd_build

        paths = get_app_paths(args.base_dir)
        return cmd_build(base_dir=paths.base_dir, input_path=Path(args.input))

    if args.command == "ls":
        from .commands.unix_like import cmd_ls

        paths = get_app_paths(args.base_dir)
        return cmd_ls(index_path=paths.index_path, prefix=args.path)

    if args.command == "find":
        from .commands.unix_like import cmd_find

        paths = get_app_paths(args.base_dir)
        return cmd_find(index_path=paths.index_path, query=args.query, limit=max(1, int(args.limit)))

    if args.command == "cat":
        from .commands.unix_like import cmd_cat

        paths = get_app_paths(args.base_dir)
        return cmd_cat(index_path=paths.index_path, selector=args.selector)

    if args.command == "grep":
        from .commands.unix_like import cmd_grep

        paths = get_app_paths(args.base_dir)
        return cmd_grep(index_path=paths.index_path, pattern=args.pattern, limit=max(1, int(args.limit)))

    if args.command == "diff":
        from pathlib import Path

        from .commands.diff_cmd import cmd_diff

        paths = get_app_paths(args.base_dir)
        prev = Path(args.prev) if args.prev else None
        return cmd_diff(base_dir=paths.base_dir, previous_index_path=prev)

    # Default: show help
    parser.print_help()
    return 0
