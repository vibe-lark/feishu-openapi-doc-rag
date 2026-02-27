from pathlib import Path
import tempfile
import unittest

from openapi_doc_cli.commands.search import search
from openapi_doc_cli.index.build import build_index, parse_items_from_file


class TestSearch(unittest.TestCase):
    def test_search_finds_by_content(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            results = search(index_path=db_path, query="欢迎使用", limit=10, offset=0)
            self.assertTrue(any(r.id == "developer_1" for r in results))

    def test_search_finds_by_directory_path(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            results = search(index_path=db_path, query="服务端", limit=10, offset=0)
            self.assertTrue(any(r.id == "developer_2" for r in results))

    def test_search_orders_fts_by_relevance(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            # Query should rank the doc containing the token higher.
            results = search(index_path=db_path, query="开放平台", limit=10, offset=0)
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].id, "developer_1")

    def test_search_fallback_orders_by_simple_relevance(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            # Force fallback by using a query that is likely to produce 0 FTS hits
            # but is present as a substring (CJK). The fallback should rank the
            # matching doc first.
            results = search(index_path=db_path, query="获取用户信息", limit=10, offset=0)
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].id, "developer_2")

    def test_search_splits_chinese_query_into_tokens(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            # Even if the full phrase doesn't appear, tokenized query should match.
            results = search(index_path=db_path, query="开放平台的使用", limit=10, offset=0)
            self.assertTrue(any(r.id == "developer_1" for r in results))

    def test_search_handles_literal_dots(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            # Should not crash on FTS syntax; should fall back gracefully.
            _ = search(index_path=db_path, query="msg_type.*audio", limit=10, offset=0)
