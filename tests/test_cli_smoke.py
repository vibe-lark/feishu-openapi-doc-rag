import subprocess
import sys
import unittest


class TestCliSmoke(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "openapi_doc_cli", "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env={**dict(**__import__("os").environ), "PYTHONPATH": "src"},
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("openapi-doc", proc.stdout)

    def test_version_exits_zero(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "openapi_doc_cli", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env={**dict(**__import__("os").environ), "PYTHONPATH": "src"},
        )
        self.assertEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout.strip(), r"^\d+\.\d+\.\d+$")

    def test_base_dir_can_appear_after_subcommand(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "openapi_doc_cli",
                "search",
                "foo",
                "--base-dir",
                "/tmp/openapi-doc-cli-local",
                "--limit",
                "1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env={**dict(**__import__("os").environ), "PYTHONPATH": "src"},
        )
        # It may exit non-zero because index isn't present; the key is argparse accepts the flag.
        self.assertNotIn("unrecognized arguments: --base-dir", proc.stderr)
