#!/usr/bin/env python
"""ensure_layout：按 PROJECT_LAYOUT.md 幂等创建目录骨架（只建目录不建文件）。

PROJECT_LAYOUT.md 7.2 行为约束：
  - 只创建目录，不创建文件；目录已存在则跳过，不覆盖用户内容
  - 不修改用户已有的任何文件；不自动创建 IDE 工程文件

调用时机：S5a/S5b prepare 段（骨架必须先于 Agent 代码生成；
S5b 与 S5a 使用同一骨架，并行执行时幂等安全）。

命令行：
    python skills/_shared/scripts/ensure_layout.py --project examples/<proj> --target App

Python 导入：
    from ensure_layout import ensure_layout
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+
    print("[ensure_layout] 本框架需要 Python 3.10+，"
          "解释器路径见根目录 config.json 的 tool_paths.python", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import layout_resolver  # noqa: E402


def _log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"[ensure_layout] {msg}", file=sys.stderr)


def ensure_layout(project_root: str | Path, config: dict | None = None,
                  state: dict | None = None, target: str | None = None,
                  arch_override: str | None = None, quiet: bool = False) -> dict:
    """解析布局并幂等创建 <项目根>/<build_target>/ 目录骨架。

    返回 {target, target_root, layout_source, arch_family, architecture,
    created, plan}；解析失败抛 layout_resolver.LayoutError。
    """
    project_root = Path(project_root).expanduser().resolve()
    config = config or {}
    plan = layout_resolver.resolve_layout(project_root, config, state, arch_override)

    build_target = target or (config.get("project") or {}).get("build_target") or "App"
    if build_target not in ("App", "BootLoader"):
        raise layout_resolver.LayoutError(f"非法 build_target: {build_target}（合法值 App/BootLoader）")
    target_root = project_root / build_target

    created: list[str] = []
    for rel in plan["skeleton_dirs"]:
        d = target_root / rel
        if not d.is_dir():
            d.mkdir(parents=True, exist_ok=True)
            created.append(rel)

    if not quiet:
        for w in plan["warnings"]:
            _log(f"警告: {w}")
        _log(f"骨架就绪: {target_root.name}/ 新建 {len(created)} 个目录"
             f"（布局来源 {plan['layout_source']}，{plan['arch_family']}/{plan['architecture']}）")
    return {"target": build_target, "target_root": str(target_root),
            "layout_source": plan["layout_source"],
            "arch_family": plan["arch_family"],
            "architecture": plan["architecture"],
            "created": created, "plan": plan}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ensure_layout：按 PROJECT_LAYOUT.md 幂等创建目录骨架（只建目录不建文件）")
    parser.add_argument("--project", required=True,
                        help="项目根目录（含 config.json）")
    parser.add_argument("--target", choices=["App", "BootLoader"], default=None,
                        help="目标工程；缺省读 config.json 的 project.build_target（默认 App）")
    parser.add_argument("--arch", choices=["flat", "layered", "full"], default=None,
                        help="覆盖 architecture（仅本次生效）")
    parser.add_argument("--arch-family", choices=["cortex_m", "mcu8"], default=None,
                        help="覆盖 arch_family（仅本次生效，调试用）")
    parser.add_argument("--quiet", action="store_true", help="抑制日志输出")
    args = parser.parse_args(argv)

    project_root = Path(args.project).expanduser().resolve()
    try:
        cfg = json.loads((project_root / "config.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    state = None
    tgt = args.target or (cfg.get("project") or {}).get("build_target") or "App"
    state_path = project_root / tgt / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            state = None

    try:
        result = ensure_layout(project_root, cfg, state, args.target,
                               args.arch, args.quiet)
    except layout_resolver.LayoutError as exc:
        print(f"[ensure_layout] 布局解析失败: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: v for k, v in result.items() if k != "plan"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
