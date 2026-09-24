"""Markdown / 纯文本提取器：直接读取（文本本身已是 Markdown 结构）。

.md 与 .txt 统一处理：utf-8-sig 容错读取（兼容 BOM），统一换行符。
"""

from __future__ import annotations

from pathlib import Path


def extract(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = path.read_text(encoding="gbk", errors="replace")
    # 统一换行符（CRLF/CR → LF），便于 Agent 分章节处理
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return {"text": text, "source_type": "markdown", "pages": None}
