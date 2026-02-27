from pathlib import Path
import tempfile
import unittest

from openapi_doc_cli.index.build import build_index, parse_items_from_file
from openapi_doc_cli.index.db import connect


class TestIndexBuild(unittest.TestCase):
    def test_build_creates_docs_rows(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        items = parse_items_from_file(fixture)

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "index.sqlite"
            result = build_index(db_path, items)
            self.assertEqual(result.doc_count, 2)
            self.assertGreaterEqual(result.max_update_time_ms, 1700000001000)

            conn = connect(db_path)
            try:
                count = conn.execute("SELECT COUNT(*) AS c FROM docs;").fetchone()["c"]
                self.assertEqual(count, 2)
                row = conn.execute("SELECT id, url FROM docs WHERE id='developer_2';").fetchone()
                self.assertEqual(row["url"], "https://open.feishu.cn/document/server-docs/contact/user")
            finally:
                conn.close()

