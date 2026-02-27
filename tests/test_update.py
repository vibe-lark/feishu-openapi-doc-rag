from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openapi_doc_cli.commands.update import cmd_update
from openapi_doc_cli.index.db import connect


class TestUpdate(unittest.TestCase):
    def test_update_builds_index_and_uses_etag(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        body = fixture.read_bytes()

        calls = {"count": 0, "if_none_match": []}

        def fake_fetch(url: str, *, etag=None, last_modified=None, timeout_s: int = 0):
            calls["count"] += 1
            calls["if_none_match"].append(etag)
            # First call returns 200 with ETag, second returns 304 when etag provided.
            if calls["count"] == 1:
                return type(
                    "FetchResult",
                    (),
                    {"status": 200, "body": body, "etag": '"v1"', "last_modified": None},
                )()
            return type(
                "FetchResult",
                (),
                {"status": 304, "body": None, "etag": '"v1"', "last_modified": None},
            )()

        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            with patch("openapi_doc_cli.commands.update.fetch", side_effect=fake_fetch):
                with patch("builtins.print"):
                    rc = cmd_update(base_dir=base_dir, url="http://example", force=False, timeout_s=5)
            self.assertEqual(rc, 0)

            index_path = base_dir / "index.sqlite"
            self.assertTrue(index_path.exists())
            conn = connect(index_path)
            try:
                c = conn.execute("SELECT COUNT(*) AS c FROM docs;").fetchone()["c"]
            finally:
                conn.close()
            self.assertEqual(c, 2)

            with patch("openapi_doc_cli.commands.update.fetch", side_effect=fake_fetch):
                with patch("builtins.print"):
                    rc = cmd_update(base_dir=base_dir, url="http://example", force=False, timeout_s=5)
            self.assertEqual(rc, 0)
            # second call should receive etag from state
            self.assertIn('"v1"', calls["if_none_match"])
