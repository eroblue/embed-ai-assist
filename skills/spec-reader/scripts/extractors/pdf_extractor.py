"""PDF 提取器：pdfplumber 逐页提取文本与表格。

- 每页文本前插入 `<!-- page N -->` 页码注释（供 REQ 来源定位）
- 表格 → Markdown 表格，跟随所在页文本输出
- 未安装 pdfplumber 时报错退出（不降级）
"""

from __future__ import annotations

from pathlib import Path


def _table_to_markdown(table) -> str:
    rows = []
    for row in table:
        cells = [" ".join((c or "").split()) for c in row]
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
        import pdfplumber
    except ImportError:
        raise RuntimeError(
            "pdfplumber 未安装，无法提取 .pdf 规格书: pip install pdfplumber"
            "（不降级为乱码提取）") from None

    parts: list[str] = []
    total_text = 0
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            tables_md = [_table_to_markdown(t) for t in (page.extract_tables() or [])]
            tables_md = [t for t in tables_md if t]
            if not page_text and not tables_md:
                parts.append(f"<!-- page {i} -->\n（本页无可提取文本，可能为图片页）")
                continue
            block = [f"<!-- page {i} -->"]
            if page_text:
                block.append(page_text)
                total_text += len(page_text)
            block.extend(tables_md)
            parts.append("\n\n".join(block))
    if total_text == 0:
        raise RuntimeError(
            f"PDF 规格书未提取到任何文本: {path}（可能为扫描件，需要 OCR，本工具不支持）")
    return {"text": "\n\n".join(parts), "source_type": "pdf", "pages": len(parts)}
