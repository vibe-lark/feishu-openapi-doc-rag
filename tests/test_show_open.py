from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openapi_doc_cli.commands.open_cmd import cmd_open
from openapi_doc_cli.commands.show import cmd_show
from openapi_doc_cli.index.build import build_index, parse_items_from_file


class TestShowOpen(unittest.TestCase):
    def test_show_by_id(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            with patch("builtins.print") as p:
                rc = cmd_show(index_path=db_path, selector="developer_1", head=0, show_content=False)
            self.assertEqual(rc, 0)
            printed = "\n".join(str(c.args[0]) for c in p.call_args_list if c.args)
            self.assertIn("url=https://open.feishu.cn/document/client-docs", printed)

    def test_open_print_only(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            with patch("builtins.print") as p:
                rc = cmd_open(index_path=db_path, selector="developer_2", print_only=True)
            self.assertEqual(rc, 0)
            printed = " ".join(str(c.args[0]) for c in p.call_args_list if c.args)
            self.assertIn("https://open.feishu.cn/document/server-docs/contact/user", printed)

