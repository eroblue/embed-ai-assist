"""ide_pending_exporter：输出 S5b IDE 待添加清单（机器可读的兜底参考）。

IDE 工程同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成
（validate 段自动调用，谁跑完谁同步，文件锁防并发覆盖）；
本清单作为同步失败时的补充参考（手动清单见
`<目标工程>/outputs/_shared/ide_sync_manual.md`）。

S5b 产物跨多个目录（App/Src、Drivers/BSP/Src 的 driver、Port 头不参与编译），
按目录角色分组输出。
"""

from __future__ import annotations

import json
from pathlib import Path


def export(groups: dict[str, list[str]], outputs_dir: Path,
           include_paths: list[str]) -> Path:
    """输出 outputs/s5b/ide_pending_files.json，返回清单绝对路径。

    groups: {组名: [源文件相对路径]}（如 {"App": ["App/Src/app.c", ...],
    "Drivers/BSP": ["Drivers/BSP/Src/driver_eeprom.c", ...]}）
    include_paths: include 路径列表（相对目标工程目录）
    """
    pending = {
        "note": ("IDE 工程由公共工具 skills/_shared/scripts/ide_sync.py 自动同步"
                 "（validate 段调用）；同步失败时见 "
                 "outputs/_shared/ide_sync_manual.md，可按本清单一并手动处理"),
        "groups": [{"group": name, "source_files": sorted(files)}
                   for name, files in sorted(groups.items())],
        "include_paths": include_paths,
    }
    s5b_dir = outputs_dir / "s5b"
    s5b_dir.mkdir(parents=True, exist_ok=True)
    path = s5b_dir / "ide_pending_files.json"
    path.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
