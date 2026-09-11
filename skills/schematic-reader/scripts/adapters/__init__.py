"""EDA 适配器注册表：parse.py 根据 eda_tool 选择适配器。"""

from __future__ import annotations

from .altium_adapter import parse as parse_altium
from .kicad_adapter import parse as parse_kicad

ADAPTERS = {
    "altium": parse_altium,
    "kicad": parse_kicad,
}

__all__ = ["ADAPTERS", "parse_altium", "parse_kicad"]
