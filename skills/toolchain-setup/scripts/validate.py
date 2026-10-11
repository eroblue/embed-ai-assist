#!/usr/bin/env python
"""S7a toolchain-setup 第 3 段：validate（rule 轨，复验 + 收口）。

复验 tool_paths（含 Agent 新写入的路径）：路径存在且 --version 可执行、版本满足
最低要求（低于最低版本**警告不终止**）。与 prepare 的检测结果对照得出本轮实际
安装的工具；写 install_report.md（如有安装动作）；state 收口（done / error）。

不修改 config.json，不触发 S7b（由用户或 S12 决定下一步）。

退出码：0 全部就绪/安装成功（done）；1 安装失败或用户拒绝（仍有开源工具缺失）；
2 配置错误。
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
EXIT_INSTALL_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s7a-validate] {msg}", file=sys.stderr)


def _build_report(check: dict, installed: list[str], config_updated: bool,
                  status: str, reason: str | None) -> str:
    lines: list[str] = []
    add = lines.append
    add("# S7a 工具链安装结果报告（install_report）")
    add("")
    add(f"- 构建系统：`{check['build_system']}`")
    add(f"- 结论：**{status}**" + (f"——{reason}" if reason else ""))
    add("")
    add("## 复验结果")
    add("")
    add("| 工具 | 路径 | 状态 | 版本 | 本轮安装 |")
    add("|---|---|---|---|---|")
    for t in check["tools"]:
        status_str = "✅ 就绪" if t["present"] else "❌ 缺失"
        ver = t["version"] or "-"
        if t["version_ok"] is False:
            ver += f"（⚠️ 低于 {t['min_version']}，建议升级）"
        add(f"| {t['label']} | `{t['path'] or '-'}` | {status_str} | {ver} "
            f"| {'是' if t['name'] in installed else '-'} |")
    add(f"- Python intelhex 包：{'✅ 可用' if check['intelhex_available'] else '❌ 未安装'}")
    add("")
    if installed:
        add("## 本轮安装")
        add("")
        for name in installed:
            t = next((x for x in check["tools"] if x["name"] == name), None)
            label = analysis.TOOL_LABELS.get(name, name)
            add(f"- {label}：{t['version'] if t and t['version'] else '版本未知'}"
                f"（{t['path'] if t else '-'}）")
        add("")
        if config_updated:
            add("- 已回填全局 config.json 的 tool_paths（Agent 在用户确认后写入）")
        else:
            add("- ⚠️ 工具已就绪但未回填 config.json 的 tool_paths（下次检测可能仍靠推导）")
        add("")
    commercial_missing = check["commercial_missing"]
    if commercial_missing:
        add("## 商业工具说明")
        add("")
        for name in commercial_missing:
            add(f"- {analysis.TOOL_LABELS.get(name, name)} 需手动安装"
                "（S7a 不自动安装商业软件，指引见 install_plan.md）")
        add("")
    if check["warnings"]:
        add("## 警告")
        add("")
        for w in check["warnings"]:
            add(f"- {w}")
        add("")
    add("## 下一步")
    add("")
    add("- 工具链就绪后运行 S7b build（prepare → build → validate）——本 skill 不自动触发")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7a validate: 工具链复验 + state 收口")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    # ---- 1. 配置与 state（prepare 必须已运行） ----
    try:
        config, _notes = build_analysis.load_layered_config(config_path)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    target_root = build_analysis.resolve_target(config, workspace)
    state_path = target_root / "state.json"
    state: dict = {}
    if state_path.is_file():
        try:
            state = build_analysis.load_json(state_path)
        except (json.JSONDecodeError, OSError):
            state = {}
    s7a = state.get("s7a") or {}
    if s7a.get("status") not in ("running", "done", "skipped"):
        _log(f"state.s7a.status={s7a.get('status', 'missing')!r}——请先运行 prepare.py")
        return EXIT_CONFIG_ERROR

    # ---- 2. 复验（用当前 config，含 Agent 回填的 tool_paths） ----
    build_system = s7a.get("build_system") or ""
    if not build_system:
        _log("state.s7a 缺少 build_system——重跑 prepare.py")
        return EXIT_CONFIG_ERROR
    check = analysis.detect_tools(config, build_system)
    schema_errors = build_analysis.validate_schema(
        check, SKILL_DIR / "schemas" / "toolchain_check.schema.json", "toolchain_check")
    if schema_errors:
        _log("toolchain_check 契约校验失败: " + "; ".join(schema_errors))
        return EXIT_CONFIG_ERROR

    outputs_dir = target_root / (config.get("output_dir") or "outputs").rstrip("/\\")
    s7a_out = outputs_dir / "s7a"
    s7a_out.mkdir(parents=True, exist_ok=True)
    check_rel = "outputs/s7a/toolchain_check.json"
    build_analysis.save_json(s7a_out / "toolchain_check.json", check)

    # ---- 3. 与 prepare 快照对照：本轮实际安装的工具 ----
    before = {t["name"]: t["present"] for t in (s7a.get("checked_tools") or [])}
    installed = [t["name"] for t in check["tools"]
                 if before.get(t["name"]) is False and t["present"]]
    config_updated = bool(installed)  # 工具路径经 config 回填（或本就推导可用）

    # ---- 4. 收口判定 ----
    # done 条件：编译清单全部就绪（商业工具缺失视为"仅需手动指引"，见 requirement 步骤 11）
    open_missing = check["open_missing"] + (["intelhex"] if (
        build_system == "vendor_ide" and not check["intelhex_available"]) else [])
    commercial_missing = check["commercial_missing"]

    if not open_missing:
        status = "done"
        reason = (f"商业工具 {'、'.join(commercial_missing)} 需手动安装"
                  "（指引见 install_plan.md）" if commercial_missing else None)
        exit_code = EXIT_OK
    else:
        status = "error"
        reason = (f"开源工具仍缺失: {'、'.join(open_missing)}"
                  "（安装失败或用户拒绝——手动安装指引见 install_plan.md 与 "
                  "references/install_guides.md）")
        exit_code = EXIT_INSTALL_FAILED

    report_rel = None
    if installed or commercial_missing or status == "error":
        report_rel = "outputs/s7a/install_report.md"
        (s7a_out / "install_report.md").write_text(
            _build_report(check, installed, config_updated, status, reason),
            encoding="utf-8", newline="\n")
    elif s7a.get("status") == "skipped":
        status = "skipped"  # prepare 即全部就绪，无安装动作
        config_updated = False

    payload = {
        "status": status,
        "build_system": build_system,
        "checked_tools": [{"name": t["name"], "path": t["path"],
                           "present": t["present"], "version": t["version"]}
                          for t in check["tools"]],
        "installed_tools": installed,
        "config_updated": config_updated,
        "check_result": check_rel,
        "install_report": report_rel,
        "error": reason if status == "error" else None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = build_analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s7a")
    if schema_errors:
        _log("s7a 状态契约校验失败: " + "; ".join(schema_errors))
        return EXIT_CONFIG_ERROR
    state_store.update_state(state_path, {"s7a": payload})

    _log(f"复验完成：status={status}"
         + (f"，本轮安装 {', '.join(installed)}" if installed else ""))
    for w in check["warnings"]:
        _log(f"警告: {w}")
    _log("下一步：工具链就绪后运行 S7b build（本 skill 不自动触发）")
    print(json.dumps({"s7a": payload}, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
