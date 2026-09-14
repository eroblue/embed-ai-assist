#!/usr/bin/env python
"""从通用网表数据生成引脚配置 Excel（outputs/pin_table.xlsx）。

格式规范见 references/excel_format.md：
- 每个元件一个工作表，命名 "{designator} 引脚配置"
- 列：引脚号 / 引脚名 / 网络名 / 作用 / 外设模式
- 行颜色：电源=蓝、特殊功能=黄、悬空=灰、普通=白
- 作用与外设/模式按关键词自动推断，无法识别的留空待人工/AI 补充
"""

from __future__ import annotations

from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
except ImportError:  # 由调用方处理
    Workbook = None  # type: ignore[assignment]

HEADER = ["引脚号", "引脚名", "网络名", "作用", "外设/模式"]

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
FILL_POWER = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
FILL_SPECIAL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
FILL_FLOATING = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")

ALIGN_CENTER = Alignment(horizontal="center", vertical="center")
COL_WIDTHS = [10, 14, 18, 28, 16]


def infer_role(pin_name: str, net: str | None, pin_type: str) -> tuple[str, str]:
    """按引脚名/网络名/引脚类型推断 (作用, 外设/模式)，无法识别返回空串。"""
    name_l = (pin_name or "").upper()
    net_l = (net or "").upper()

    if pin_type == "POWER" or any(
        k in name_l or k in net_l
        for k in ("VDD", "VSS", "VCC", "GND", "VBAT", "VREF")
    ):
        return ("电源", "电源")
    if any(k in name_l or k in net_l for k in ("SWDIO", "SWCLK", "TMS", "TCK")):
        return ("SWD 调试", "SWD")
    if "BOOT" in name_l or "BOOT" in net_l:
        return ("启动模式配置", "BOOT")
    if any(k in name_l or k in net_l for k in ("NRST", "RESET", "RST")):
        return ("复位", "RESET")
    if any(k in name_l for k in ("OSCI", "OSCO", "XCIN", "XCOUT", "XTAL")):
        return ("晶振", "晶振")
    if net is None:
        return ("未使用（悬空）", "")
    return ("", "")


def _row_fill(role: str, net: str | None) -> PatternFill | None:
    """根据推断结果选择行填充色。"""
    if role == "电源":
        return FILL_POWER
    if role in ("SWD 调试", "启动模式配置", "复位", "晶振"):
        return FILL_SPECIAL
    if net is None:
        return FILL_FLOATING
    return None


def export_pin_table(netlist_doc: dict, excel_path: Path) -> tuple[int, list[str]]:
    """生成引脚配置 Excel，返回 (引脚总行数, 警告列表)。

    netlist_doc: parse.py 生成的网表文档（含 components）
    excel_path: 输出文件路径
    """
    if Workbook is None:
        raise ImportError("openpyxl 未安装: pip install openpyxl")

    warnings: list[str] = []
    components = netlist_doc.get("components", [])
    wb = Workbook()
    wb.remove(wb.active)  # 移除默认 sheet

    total_rows = 0
    for comp in components:
        designator = comp.get("designator") or "?"
        ws = wb.create_sheet(title=f"{designator} 引脚配置")
        ws.append(HEADER)
        for col_idx, width in enumerate(COL_WIDTHS, start=1):
            ws.column_dimensions[chr(64 + col_idx)].width = width
        for cell in ws[1]:
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = ALIGN_CENTER

        for pin in comp.get("pins", []):
            net = pin.get("net")
            role, periph = infer_role(
                pin.get("pin_name", ""), net, pin.get("pin_type", "")
            )
            row = [
                pin.get("pin", ""),
                pin.get("pin_name", ""),
                net if net is not None else "未连接",
                role,
                periph,
            ]
            ws.append(row)
            total_rows += 1
            fill = _row_fill(role, net)
            if fill is not None:
                for cell in ws[ws.max_row]:
                    cell.fill = fill
            ws.cell(row=ws.max_row, column=1).alignment = ALIGN_CENTER

    if total_rows == 0:
        warnings.append("网表无元件引脚，pin_table.xlsx 仅含表头")

    excel_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(excel_path)
    return total_rows, warnings
