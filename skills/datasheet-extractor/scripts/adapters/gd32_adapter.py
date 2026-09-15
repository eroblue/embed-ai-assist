"""GD32 系列适配器（占位：暂未实现）。

GD32 手册结构与 ST 相近但章节编号/表头不同，待接入真实手册后实现。
触发时抛 NotImplementedError，由主入口转为 failed 状态。
"""

from __future__ import annotations

from pathlib import Path


class GD32Adapter:
    KEY_PREFIX = "gd32"

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
            "GD32 系列手册提取适配器暂未实现（待接入 GD32 手册样本后开发）"
        )


__all__ = ["GD32Adapter"]
