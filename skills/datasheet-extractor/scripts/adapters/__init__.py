"""datasheet-extractor 适配器注册表。

主入口按 platform 前缀匹配选择适配器；新增厂商时在 ADAPTER_PREFIXES 加一行。
"""

from __future__ import annotations

from .stm32_adapter import STM32Adapter
from .gd32_adapter import GD32Adapter
from .fm32_adapter import FM32Adapter
from .ft61_adapter import FT61Adapter

ADAPTER_PREFIXES = {
    "stm32": STM32Adapter,
    "gd32": GD32Adapter,
    "fm32": FM32Adapter,
    "ft61": FT61Adapter,
}

__all__ = ["ADAPTER_PREFIXES"]
