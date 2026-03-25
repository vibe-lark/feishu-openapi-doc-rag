from pathlib import Path
import io
import tempfile
import unittest
from contextlib import redirect_stdout

from openapi_doc_cli.commands.search import search
from openapi_doc_cli.commands.unix_like import cmd_grep
from openapi_doc_cli.index.build import build_index, parse_items_from_file
from openapi_doc_cli.text import smart_tokens


class TestSearch(unittest.TestCase):
    def _approval_items(self) -> list[dict]:
        return [
            {
                "id": "developer_target",
                "originId": "target",
                "type": "developer",
                "directory": ["服务端 API", "考勤打卡", "假勤审批", "写入审批结果"],
                "pathnames": ["document", "server-docs", "attendance-v1", "user_approval", "create"],
                "url": "https://open.feishu.cn/document/server-docs/attendance-v1/user_approval/create",
                "value": "用于把假勤审批状态同步回系统。",
                "updateTime": 1700000005000,
            },
            {
                "id": "developer_noise_phrase",
                "originId": "noise_phrase",
                "type": "developer",
                "directory": ["服务端 API", "飞书人事", "入职", "流转入职任务"],
                "pathnames": ["document", "server-docs", "corehr-v2", "pre_hire", "task"],
                "url": "https://open.feishu.cn/document/server-docs/corehr-v2/pre_hire/task",
                "value": "当审批结果变更时，系统会继续后续流程。",
                "updateTime": 1700000004000,
            },
            {
                "id": "developer_noise_write",
                "originId": "noise_write",
                "type": "developer",
                "directory": ["服务端 API", "组织架构", "员工管理", "更新员工信息"],
                "pathnames": ["document", "directory-v1", "employee", "patch"],
                "url": "https://open.feishu.cn/document/directory-v1/employee/patch",
                "value": "写入员工资料字段。",
                "updateTime": 1700000003000,
            },
        ]

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

    def test_search_ranks_partial_cjk_title_match_first(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, self._approval_items())

            results = search(index_path=db_path, query="审批结果", limit=10, offset=0)

            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].id, "developer_target")

    def test_search_supports_out_of_order_cjk_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, self._approval_items())

            results = search(index_path=db_path, query="审批 写入", limit=10, offset=0)

            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].id, "developer_target")

    def test_smart_tokens_split_whitespace_separated_cjk_terms(self) -> None:
        self.assertEqual(smart_tokens("审批 写入"), ["审批", "写入"])

    def test_smart_tokens_extract_key_parts_from_compound_cjk_query(self) -> None:
        self.assertEqual(smart_tokens("审批结果写入"), ["审批", "结果", "写入"])

    def test_cmd_grep_prints_explicit_no_results_message(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            build_index(db_path, items)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                rc = cmd_grep(index_path=db_path, pattern="不存在的接口", limit=10)

            self.assertEqual(rc, 0)
            self.assertIn('0 results found for "不存在的接口"', stdout.getvalue())
