"""辉芒微 FM32 系列适配器（占位：暂未实现）。

触发时抛 NotImplementedError，由主入口转为 failed 状态。
"""

from __future__ import annotations

from pathlib import Path


class FM32Adapter:
    KEY_PREFIX = "fm32"

    def __init__(self, platform: str):
        self.platform = platform

    def extract(
        self,
        datasheet: Path,
        secondary: Path | None,
        scope: str,
        svd: Path | None = None,
        sdk_header: Path | None = None,
    ) -> dict:
        raise NotImplementedError(
            "FM32 系列手册提取适配器暂未实现（后续扩展）"
        )


__all__ = ["FM32Adapter"]
