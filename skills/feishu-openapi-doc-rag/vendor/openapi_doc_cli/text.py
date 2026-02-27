from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


_CJK_STOPWORDS = {
    "的",
    "了",
    "和",
    "与",
    "及",
    "在",
    "对",
    "把",
    "将",
    "用",
    "使用",
    "如何",
    "怎么",
    "一个",
    "我们",
    "你",
    "我",
}

_DOMAIN_PHRASES = [
    # Product nouns
    "多维表格",
    "飞书词典",
    "云文档",
    "日程",
    "日历",
    "语音",
    "音频",
    # Common actions
    "写入",
    "创建",
    "新增",
    "添加",
    "发送",
    "上传",
    "下载",
    "删除",
    "更新",
    "获取",
    "查询",
    "搜索",
]


def _is_cjk(ch: str) -> bool:
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= o <= 0x4DBF  # Extension A
        or 0x3040 <= o <= 0x30FF  # Japanese kana
        or 0xAC00 <= o <= 0xD7AF  # Hangul
    )


def smart_tokens(query: str) -> List[str]:
    """
    Best-effort tokenization for mixed Chinese/English queries without external deps.

    Strategy:
    - Split on whitespace/punctuation
    - Further split CJK runs by common particles like "的"
    - Remove very short tokens and stopwords
    - Deduplicate while keeping order
    """
    q = query.strip()
    if not q:
        return []

    rough = [t for t in re.split(r"[\\s\\t\\r\\n\\-_/,:;，。！？()（）]+", q) if t]
    tokens: List[str] = []
    for t in rough:
        # If the token is a concatenated Chinese phrase (no delimiters), extract
        # known domain phrases first (e.g. "多维表格写入" -> "多维表格" + "写入").
        if any(_is_cjk(ch) for ch in t):
            for phrase in sorted(_DOMAIN_PHRASES, key=len, reverse=True):
                if phrase in t and phrase not in _CJK_STOPWORDS:
                    tokens.append(phrase)

        # split on common CJK connectors inside the token
        parts = re.split(r"[的与和及在对把将]+", t)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if p in _CJK_STOPWORDS:
                continue
            # Drop single-char CJK tokens (too noisy)
            if len(p) == 1 and _is_cjk(p):
                continue
            tokens.append(p)

    # de-dupe preserve order
    seen = set()
    out: List[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out
