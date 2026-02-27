from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openapi_doc_cli.commands.build_cmd import cmd_build
from openapi_doc_cli.commands.unix_like import cat_doc, find_docs, grep_docs, ls_dirs


class TestUnixCommands(unittest.TestCase):
    def test_ls_dirs_returns_top_level(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            with patch("builtins.print"):
                cmd_build(base_dir=base_dir, input_path=fixture)
            out = ls_dirs(index_path=base_dir / "index.sqlite", prefix=[])
            self.assertIn("开发指南", out)
            self.assertIn("服务端 API", out)

    def test_find_docs_by_directory_keyword(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            with patch("builtins.print"):
                cmd_build(base_dir=base_dir, input_path=fixture)
            hits = find_docs(index_path=base_dir / "index.sqlite", query="通讯录", limit=10)
            self.assertTrue(any(h.id == "developer_2" for h in hits))

    def test_cat_outputs_content(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            with patch("builtins.print"):
                cmd_build(base_dir=base_dir, input_path=fixture)
            text = cat_doc(index_path=base_dir / "index.sqlite", selector="developer_1")
            self.assertIn("欢迎使用开放平台", text)

    def test_grep_returns_matching_doc(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            with patch("builtins.print"):
                cmd_build(base_dir=base_dir, input_path=fixture)
            hits = grep_docs(index_path=base_dir / "index.sqlite", pattern="获取用户信息", limit=10)
            self.assertTrue(any(h.id == "developer_2" for h in hits))
