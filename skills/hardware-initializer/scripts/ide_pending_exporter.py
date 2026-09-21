"""ide_pending_exporter：输出 IDE 待添加清单（机器可读的兜底参考）。

IDE 工程同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成
（validate 段自动调用，谁跑完谁同步，文件锁防并发覆盖）；
本清单作为同步失败时的补充参考（手动清单见
`<目标工程>/outputs/_shared/ide_sync_manual.md`）。
"""

from __future__ import annotations

import json
from pathlib import Path


def export(sources: list[str], outputs_dir: Path, group: str,
           include_paths: list[str]) -> Path:
    """输出 outputs/s5a/ide_pending_files.json，返回清单绝对路径。

    sources 为相对目标工程目录的源文件路径（如 Drivers/BSP/Src/clock_init.c）；
    group / include_paths 由调用方按 PROJECT_LAYOUT.md 解析结果传入
    （validate.py 从 layout_resolver 的 LayoutPlan 取值）。
    """
    pending = {
        "note": ("IDE 工程由公共工具 skills/_shared/scripts/ide_sync.py 自动同步"
                 "（validate 段调用）；同步失败时见 "
                 "outputs/_shared/ide_sync_manual.md，可按本清单一并手动处理"),
        "group": group,
        "source_files": sources,
        "include_paths": include_paths,
    }
    s5a_dir = outputs_dir / "s5a"
    s5a_dir.mkdir(parents=True, exist_ok=True)
    path = s5a_dir / "ide_pending_files.json"
    path.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
