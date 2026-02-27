import json
from pathlib import Path
import tempfile
import unittest

from openapi_doc_cli.commands.build_cmd import cmd_build
from openapi_doc_cli.commands.diff_cmd import cmd_diff, snapshot_index
from openapi_doc_cli.diffing import compute_diff, load_doc_fingerprints


class TestDiff(unittest.TestCase):
    def test_diff_added_removed_changed(self) -> None:
        v1 = Path(__file__).parent / "fixtures" / "sample.json"
        v2 = Path(__file__).parent / "fixtures" / "sample_v2.json"

        with tempfile.TemporaryDirectory() as td:
            base1 = Path(td) / "base1"
            base2 = Path(td) / "base2"
            cmd_build(base_dir=base1, input_path=v1)
            cmd_build(base_dir=base2, input_path=v2)

            old = load_doc_fingerprints(base1 / "index.sqlite")
            new = load_doc_fingerprints(base2 / "index.sqlite")
            diff = compute_diff(old, new)

            self.assertIn("developer_3", diff.added)
            self.assertIn("developer_2", diff.removed)
            self.assertIn("developer_1", diff.changed)

    def test_diff_command_writes_files(self) -> None:
        v1 = Path(__file__).parent / "fixtures" / "sample.json"
        v2 = Path(__file__).parent / "fixtures" / "sample_v2.json"

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            cmd_build(base_dir=base, input_path=v1)
            snapshot_index(base_dir=base)
            cmd_build(base_dir=base, input_path=v2)
            rc = cmd_diff(base_dir=base)
            self.assertEqual(rc, 0)
            self.assertTrue((base / "diff").exists())
