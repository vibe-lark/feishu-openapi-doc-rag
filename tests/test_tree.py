from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openapi_doc_cli.commands.tree import cmd_tree
from openapi_doc_cli.index.build import build_index, parse_items_from_file


class TestTree(unittest.TestCase):
    def test_tree_runs_and_filters_subtree(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            # full tree should succeed
            with patch("builtins.print"):
                rc = cmd_tree(index_path=db_path, subtree=[], max_depth=6, show_counts=True)
            self.assertEqual(rc, 0)

            # subtree that exists should succeed
            with patch("builtins.print"):
                rc = cmd_tree(index_path=db_path, subtree=["开发指南"], max_depth=6, show_counts=False)
            self.assertEqual(rc, 0)

            # subtree that does not exist should return non-zero
            with patch("builtins.print"):
                rc = cmd_tree(index_path=db_path, subtree=["不存在"], max_depth=6, show_counts=False)
            self.assertEqual(rc, 1)
