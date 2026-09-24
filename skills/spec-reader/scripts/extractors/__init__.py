"""S2 文本提取器注册（适配器模式，与 S1 schematic-reader adapters 同构）。

按扩展名选择提取器：.md/.txt 直读、.docx 用 python-docx、.pdf 用 pdfplumber。
可选依赖未安装时对应格式直接报错退出（不降级为乱码提取）。

每个提取器统一返回：
    {"text": str, "source_type": "markdown"|"docx"|"pdf", "pages": int|None}
text 为 Markdown 化的纯文本：标题用 # 层级标记，PDF 页码以 <!-- page N -->
注释插入，表格转 Markdown 表格。
"""

from __future__ import annotations

from pathlib import Path

from markdown_extractor import extract as extract_markdown
from docx_extractor import extract as extract_docx
from pdf_extractor import extract as extract_pdf

_EXTRACTORS = {
    "markdown": extract_markdown,
    "docx": extract_docx,
    "pdf": extract_pdf,
}


def get_extractor(source_type: str):
    """按 source_type（analysis.SUPPORTED_SUFFIXES 的值）返回提取函数。"""
    try:
        return _EXTRACTORS[source_type]
    except KeyError:
        raise ValueError(f"未注册的提取器类型: {source_type}") from None


def extract_text(path: Path, source_type: str) -> dict:
    """提取规格书文本（入口）。path 为规格书绝对路径。"""
    return get_extractor(source_type)(path)
