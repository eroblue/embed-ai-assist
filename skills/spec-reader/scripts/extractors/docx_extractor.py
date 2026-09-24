"""Word (.docx) 提取器：python-docx 按文档顺序提取段落与表格。

- 标题样式（Heading N / 标题 N）→ Markdown `#`*N 层级
- 表格 → Markdown 表格（首行为表头）
- 未安装 python-docx 时报错退出（不降级）
"""

from __future__ import annotations

from pathlib import Path


def _iter_block_items(doc):
    """按文档顺序迭代段落与表格（python-docx 官方配方）。"""
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def _heading_level(paragraph) -> int | None:
    """识别标题级别：样式名 'Heading N' / '标题 N' → N；'Title' → 1。"""
    style_name = (paragraph.style.name if paragraph.style is not None else "") or ""
    if style_name in ("Title", "文档标题"):
        return 1
    for tok in ("Heading", "标题"):
        if style_name.startswith(tok):
            tail = style_name[len(tok):].strip()
            if tail.isdigit() and 1 <= int(tail) <= 6:
                return int(tail)
    return None


def _table_to_markdown(table) -> str:
    rows = []
    for row in table.rows:
        cells = [" ".join(c.text.split()) for c in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    lines = ["| " + " | ".join(rows[0]) + " |",
             "|" + "|".join(["---"] * len(rows[0])) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def extract(path: Path) -> dict:
    try:
        import docx  # python-docx
    except ImportError:
        raise RuntimeError(
            "python-docx 未安装，无法提取 .docx 规格书: pip install python-docx"
            "（不降级为乱码提取）") from None

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = docx.Document(str(path))
    lines: list[str] = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            level = _heading_level(block)
            lines.append(f"{'#' * level} {text}" if level else text)
        elif isinstance(block, Table):
            md = _table_to_markdown(block)
            if md:
                lines.append(md)
    if not lines:
        raise RuntimeError(f".docx 规格书内容为空: {path}")
    return {"text": "\n\n".join(lines), "source_type": "docx", "pages": None}
