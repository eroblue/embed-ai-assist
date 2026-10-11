#!/usr/bin/env python
"""S7a toolchain-setup 第 1 段：prepare（rule 轨，检测 + 计划）。

三段式执行模型：
  1. [rule]  prepare.py   → 构建系统判定（复用 S7b 共享推断）→ 按检查清单逐项检测
                            （路径存在 + --version 版本探测）
                            → 全部就绪：state.s7a = skipped（不做任何安装动作）
                            → 有缺失：outputs/s7a/install_plan.md（Agent 任务书）
                              + state.s7a = running
  2. [agent] install      → 仅开源工具缺失时引导安装（**未经用户确认不得执行任何
                            安装命令**）→ 用户确认后按官方源安装 → 回填全局
                            config.json 的 tool_paths（全项目唯一 config 写入例外，
                            仅限 tool_paths 段、写入前展示 diff 并经用户确认）
  3. [rule]  validate.py  → 复验 + state 收口（done / error）

本脚本不修改 config.json（只读检测），不安装任何软件，不触发 S7b。

退出码：0 全部就绪（skipped）或已生成安装计划（running，待 Agent install）；
2 配置错误（build_system 无法判定等）。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):
    print("[错误] 本框架需要 Python 3.10+，当前解释器为 "
          f"{sys.version.split()[0]}", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import state_store  # noqa: E402
build_analysis = analysis.build_analysis  # S7b 共享模块（经 S7a analysis 按路径加载）

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s7a-prepare] {msg}", file=sys.stderr)


# ---------------- install_plan.md（Agent 任务书） ----------------

_INSTALL_METHODS = {
    "gcc": ("ARM GNU Toolchain（gcc + objcopy）",
            "`winget install Arm.GnuArmEmbeddedToolchain`，或 ARM 官网 `.exe` 安装",
            "Linux/macOS：`apt` / `brew`", "C:/gcc-arm/"),
    "gcc_objcopy": ("arm-none-eabi-objcopy",
                    "随 ARM GNU Toolchain 一起安装（同目录）", "-", "C:/gcc-arm/"),
    "make": ("GNU Make",
             "`winget install MSYS2.MSYS2` 后 `C:/msys64/usr/bin/pacman -S make`",
             "Linux/macOS：`apt` / `brew`", "C:/msys64/"),
    "cmake": ("CMake", "`winget install KitWare.CMake`",
              "Linux/macOS：`apt` / `brew`", "C:/cmake/"),
}

_COMMERCIAL_GUIDES = {
    "keil": ("Keil MDK", "https://www.keil.com/download/",
             "安装后在全局 config.json 的 tool_paths.keil 配置 UV4.exe 路径"),
    "keil_fromelf": ("Keil fromelf（随 Keil MDK 安装）", "https://www.keil.com/download/",
                     "随 Keil MDK 安装于 <Keil 根>/ARM/ARMCLANG|ARMCC/bin/"),
    "iar": ("IAR EWARM", "https://www.iar.com/downloads/",
            "安装后在全局 config.json 的 tool_paths.iar 配置 IarBuild.exe 路径"),
    "iar_ielftool": ("IAR ielftool（随 IAR 安装）", "https://www.iar.com/downloads/",
                     "随 IAR 安装于 IarBuild 同目录 common/bin/"),
    "vendor_ide": ("厂家 IDE", "（见该厂家官网）",
                   "安装后在全局 config.json 的 tool_paths.vendor_ide 配置可执行文件路径"),
}


def build_install_plan(check: dict, basis: str) -> str:
    lines: list[str] = []
    add = lines.append
    add("# S7a 工具链安装计划（install_plan）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。Agent 按本计划引导安装。")
    add(f"> 构建系统：`{check['build_system']}`（{basis}）")
    add("")
    add("## 1. 检测结果")
    add("")
    add("| 工具 | 路径 | 状态 | 版本 |")
    add("|---|---|---|---|")
    for t in check["tools"]:
        status = "✅ 就绪" if t["present"] else "❌ 缺失"
        ver = t["version"] or "-"
        if t["version_ok"] is False:
            ver += f"（⚠️ 低于 {t['min_version']}）"
        add(f"| {t['label']} | `{t['path'] or '-'}` | {status} | {ver} |")
    add(f"- Python intelhex 包：{'✅ 可用' if check['intelhex_available'] else '❌ 未安装'}")
    for w in check["warnings"]:
        add(f"- ⚠️ {w}")
    add("")

    open_missing = check["open_missing"]
    commercial_missing = check["commercial_missing"]

    if open_missing:
        add("## 2. 开源工具缺失项（Agent 引导安装，须用户确认）")
        add("")
        add("**在对话中列出以下安装清单（工具 + 版本 + 来源 + 目标路径），等待用户")
        add("显式确认——未确认前不得执行任何安装命令。**")
        add("")
        add("| 工具 | 最低版本 | Windows 安装方式 | Linux/macOS | 建议目标路径 |")
        add("|---|---|---|---|---|")
        for name in open_missing:
            label, win, ln, dest = _INSTALL_METHODS.get(
                name, (name, "-", "-", "-"))
            minimum = analysis.OPEN_TOOL_MIN_VERSIONS.get(name)
            add(f"| {label} | {'.'.join(map(str, minimum)) if minimum else '-'} "
                f"| {win} | {ln} | {dest} |")
        add("")
        add("安装目标路径默认建议见上表（避免空格与用户目录权限问题），但**须先检测")
        add("可写性**；C 盘不可写时请用户指定路径。")
        add("")
        add("安装完成后**回填全局 config.json 的 tool_paths**（唯一例外，附加约束）：")
        add("- 只允许追加/更新 `tool_paths` 段的工具路径键，禁止修改任何其他字段")
        add("- 写入前在对话中展示将要写入的键值对（diff），经用户确认")
        add("- 不覆盖已有配置键，除非该键指向的路径已失效")
        add("- 只从官方源安装（winget 官方源 / ARM 官网 / MSYS2 官方源 / Kitware 官网）")
        add("")
    else:
        add("## 2. 开源工具缺失项")
        add("")
        add("- 无（开源工具全部就绪，无需安装）")
        add("")

    if commercial_missing:
        add(f"## {'3' if open_missing else '2'}. 商业工具缺失项（需手动安装，S7a 不自动安装）")
        add("")
        for name in commercial_missing:
            label, url, note = _COMMERCIAL_GUIDES.get(name, (name, "", ""))
            add(f"- **{label}**：官网下载 {url}；{note}")
        add("- 商业授权软件一律由用户自行安装与购买许可，S7a 不执行任何安装命令")
        add("- 商业工具缺失但开源工具齐全时，不进入 install 阶段，直接 validate 收口")
        add("")
    if check["build_system"] == "vendor_ide" and not check["intelhex_available"]:
        add("## 开源依赖缺失项")
        add("")
        add("- Python `intelhex` 包：`pip install intelhex`（vendor_ide 机制 hex→bin 依赖，")
        add("  属开源白名单，可随本计划一并安装）")
        add("")
    add("## 禁止事项")
    add("")
    add("- **未经用户确认不得执行任何安装命令**")
    add("- rule 脚本不修改 config.json（回填由 Agent 在用户确认后执行）")
    add("- 不安装任何商业软件（Keil / IAR / 厂家 IDE）")
    add("- 不修改已存在的工具安装（路径存在但版本不匹配时只警告，不覆盖、不重装）")
    add("- 不修改 state.s7a.status（由 validate 收口）；不触发 S7b")
    return "\n".join(lines) + "\n"


# ---------------- 主流程 ----------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7a prepare: 工具链检测 + install_plan 生成（不安装任何软件）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    # ---- 1. 配置加载（只读） ----
    try:
        config, _notes = build_analysis.load_layered_config(config_path)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    cfg_errors = build_analysis.validate_schema(
        config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        _log("配置契约校验失败: " + "; ".join(cfg_errors))
        return EXIT_CONFIG_ERROR

    # ---- 2. 构建系统判定（显式优先，否则 S7b 共享推断） ----
    try:
        build_system, basis = analysis.determine_build_system(config, workspace)
    except build_analysis.BuildDetectError as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    _log(f"构建系统: {build_system}（{basis}）")

    # ---- 3. 逐项检测 ----
    check = analysis.detect_tools(config, build_system)
    schema_errors = build_analysis.validate_schema(
        check, SKILL_DIR / "schemas" / "toolchain_check.schema.json", "toolchain_check")
    if schema_errors:
        _log("toolchain_check 契约校验失败: " + "; ".join(schema_errors))
        return EXIT_CONFIG_ERROR

    # ---- 4. 落盘检测结果 ----
    target_root = build_analysis.resolve_target(config, workspace)
    outputs_dir = target_root / (config.get("output_dir") or "outputs").rstrip("/\\")
    s7a_out = outputs_dir / "s7a"
    s7a_out.mkdir(parents=True, exist_ok=True)
    check_rel = "outputs/s7a/toolchain_check.json"
    build_analysis.save_json(s7a_out / "toolchain_check.json", check)
    for t in check["tools"]:
        _log(f"检测 {t['name']}: {'就绪' if t['present'] else '缺失'}"
             f"（{t['path'] or '-'}）" + (f" 版本 {t['version']}" if t["version"] else ""))

    # ---- 5. state 收口：全部就绪 skipped / 有缺失 running ----
    checked_tools = [{"name": t["name"], "path": t["path"],
                      "present": t["present"], "version": t["version"]}
                     for t in check["tools"]]
    if check["all_present"]:
        payload = {
            "status": "skipped",
            "build_system": build_system,
            "checked_tools": checked_tools,
            "installed_tools": [],
            "config_updated": False,
            "check_result": check_rel,
            "install_report": None,
            "error": None,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        schema_errors = build_analysis.validate_schema(
            payload, SKILL_DIR / "schemas" / "output.schema.json", "s7a")
        if schema_errors:
            _log("s7a 状态契约校验失败: " + "; ".join(schema_errors))
            return EXIT_CONFIG_ERROR
        state_store.update_state(target_root / "state.json", {"s7a": payload})
        _log("全部就绪：status=skipped（不安装任何东西，可直接运行 S7b build）")
        print(json.dumps({"s7a": payload}, ensure_ascii=False, indent=2))
        return EXIT_OK

    plan_rel = "outputs/s7a/install_plan.md"
    (s7a_out / "install_plan.md").write_text(
        build_install_plan(check, basis), encoding="utf-8", newline="\n")
    payload = {
        "status": "running",
        "build_system": build_system,
        "checked_tools": checked_tools,
        "installed_tools": [],
        "config_updated": False,
        "check_result": check_rel,
        "install_report": None,
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = build_analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s7a")
    if schema_errors:
        _log("s7a 状态契约校验失败: " + "; ".join(schema_errors))
        return EXIT_CONFIG_ERROR
    state_store.update_state(target_root / "state.json", {"s7a": payload})
    _log(f"检测到缺失：开源 {check['open_missing'] or '无'}；"
         f"商业 {check['commercial_missing'] or '无'}")
    _log(f"安装计划已生成: {s7a_out / 'install_plan.md'}")
    _log("下一步：Agent 读 install_plan.md + SKILL.md + references/install_guides.md，"
         "与用户确认后安装（开源工具白名单）并回填 tool_paths，再运行 validate.py 复验")
    print(json.dumps({"s7a": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
