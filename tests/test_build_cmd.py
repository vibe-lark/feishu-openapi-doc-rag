from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openapi_doc_cli.commands.build_cmd import cmd_build


class TestBuildCmd(unittest.TestCase):
    def test_build_creates_index_sqlite(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.json"
        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            out = base_dir / "index.sqlite"
            self.assertFalse(out.exists())
            with patch("builtins.print"):
                rc = cmd_build(base_dir=base_dir, input_path=fixture)
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())

