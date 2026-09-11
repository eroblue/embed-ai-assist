"""Altium Designer 原理图适配器：基于 altium-monkey 库解析 .SchDoc，
输出 EDA 无关的通用网表结构。
"""

from __future__ import annotations

import re
from pathlib import Path

PIN_TYPE_FALLBACK = "UNKNOWN"


def _natural_key(s: str):
    """数字感知排序键：'2' < '10'。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def parse(schematic_path: str) -> dict:
    """解析 .SchDoc，返回通用网表中间结构（components / nets / warnings）。

    依赖：altium-monkey（AltiumDesign / Netlist 数据模型）。
    """
    from altium_monkey import AltiumDesign, AltiumSchDoc

    design = AltiumDesign.from_schdoc(schematic_path)
    netlist = design.to_netlist()

    warnings: list[str] = []

    # 1. 元件表
    components: dict[str, dict] = {}
    for comp in netlist.components:
        designator = comp.designator
        if not designator:
            warnings.append("component with empty designator skipped")
            continue
        components[designator] = {
            "designator": designator,
            "value": comp.value,
            "footprint": comp.footprint,
            "library_ref": comp.library_ref,
            "description": comp.description,
            "parameters": dict(comp.parameters or {}),
            "pins": [],
        }

    # 2. 网络（把 terminal 反填到元件引脚）
    nets: list[dict] = []
    for net in netlist.nets:
        terminals = []
        for term in net.terminals:
            pin_type = getattr(term.pin_type, "name", PIN_TYPE_FALLBACK)
            terminals.append(
                {
                    "designator": term.designator,
                    "pin": str(term.pin),
                    "pin_name": term.pin_name or "",
                    "pin_type": pin_type,
                }
            )
            comp = components.get(term.designator)
            if comp is not None:
                comp["pins"].append(
                    {
                        "pin": str(term.pin),
                        "pin_name": term.pin_name or "",
                        "pin_type": pin_type,
                        "net": net.name,
                    }
                )
        terminals.sort(key=lambda t: (t["designator"], _natural_key(t["pin"])))
        nets.append(
            {
                "name": net.name,
                "auto_named": bool(net.auto_named),
                "source_sheets": sorted(set(net.source_sheets or [])) or [Path(schematic_path).name],
                "terminals": terminals,
            }
        )

    # 3. 补充悬空引脚（未连接任何网络的引脚，net 置 null）
    connected: dict[str, set[str]] = {
        d: {p["pin"] for p in c["pins"]} for d, c in components.items()
    }
    for schdoc in design.schdocs:
        for comp_info in schdoc.get_components():
            designator = getattr(comp_info, "designator", "")
            comp = components.get(designator)
            if comp is None:
                continue
            for pin in comp_info.pins:
                pin_no = str(getattr(pin, "designator", ""))
                if not pin_no or pin_no in connected.get(designator, ()):
                    continue
                comp["pins"].append(
                    {
                        "pin": pin_no,
                        "pin_name": getattr(pin, "name", "") or "",
                        "pin_type": getattr(getattr(pin, "electrical", None), "name", PIN_TYPE_FALLBACK),
                        "net": None,
                    }
                )
                connected.setdefault(designator, set()).add(pin_no)

    for comp in components.values():
        comp["pins"].sort(key=lambda p: _natural_key(p["pin"]))

    nets.sort(key=lambda n: n["name"])
    return {
        "components": sorted(components.values(), key=lambda c: _natural_key(c["designator"])),
        "nets": nets,
        "warnings": warnings,
    }
