from __future__ import annotations

import re
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

    rough = [t for t in re.split(r"[\s\t\r\n\-_/,:;，。！？()（）]+", q) if t]
    tokens: List[str] = []
    for t in rough:
        if any(_is_cjk(ch) for ch in t):
            tokens.extend(_tokenize_cjk_run(t))
            continue

        p = t.strip()
        if p:
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


def _tokenize_cjk_run(token: str) -> List[str]:
    out: List[str] = []
    i = 0
    buf = ""
    phrases = sorted(_DOMAIN_PHRASES, key=len, reverse=True)
    connectors = set("的与和及在对把将")

    def flush_buffer() -> None:
        nonlocal buf
        buf = buf.strip()
        if not buf or buf in _CJK_STOPWORDS:
            buf = ""
            return
        for piece in _split_cjk_piece(buf):
            if piece not in _CJK_STOPWORDS:
                out.append(piece)
        buf = ""

    while i < len(token):
        ch = token[i]
        if ch in connectors:
            flush_buffer()
            i += 1
            continue

        phrase = next((p for p in phrases if token.startswith(p, i)), None)
        if phrase is not None:
            flush_buffer()
            out.append(phrase)
            i += len(phrase)
            continue

        buf += ch
        i += 1

    flush_buffer()
    return [p for p in out if not (len(p) == 1 and _is_cjk(p))]


def _split_cjk_piece(piece: str) -> List[str]:
    if not piece:
        return []
    if all(_is_cjk(ch) for ch in piece) and len(piece) >= 4 and len(piece) % 2 == 0:
        return [piece[i : i + 2] for i in range(0, len(piece), 2)]
    return [piece]
