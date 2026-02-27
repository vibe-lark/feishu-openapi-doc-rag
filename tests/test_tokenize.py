import unittest

from openapi_doc_cli.text import smart_tokens


class TestTokenize(unittest.TestCase):
    def test_splits_concatenated_domain_phrases(self) -> None:
        self.assertIn("多维表格", smart_tokens("多维表格写入"))
        self.assertIn("写入", smart_tokens("多维表格写入"))
        self.assertIn("发送", smart_tokens("发送语音"))
        self.assertIn("语音", smart_tokens("发送语音"))

