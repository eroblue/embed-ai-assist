#!/usr/bin/env python
"""S7b build 第 4 段：validate（rule 轨）。

产物验证 + state 收口：
  - build_result.json 存在且 schema 合法
  - 编译成功：主调试产物存在；bin_path 非空（除非 bin 转换工具缺失且已警告）
  - 编译失败：error_analysis.md 存在（Agent 阶段 C 产出；尚未产出时提示先分析）
  - GUI 机制：gui_build_log.md 存在（无论成败）
  - state 收口：成功 done / 失败 error

退出码：0 校验通过；2 配置错误 / 产物缺失 / 校验失败。
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

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s7b-validate] {msg}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7b validate: 产物验证 + state 收口")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    def _fail(msg: str) -> int:
        _log(msg)
        print(json.dumps({"s7b": {"status": "error", "error": msg,
                                   "updated_at": datetime.now().isoformat(timespec="seconds")}},
                         ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    try:
        ctx = analysis.load_build_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return _fail(str(exc))

    target_root = ctx["workspace"]
    s7b_out = ctx["s7b_outputs"]
    state = ctx["state"]
    s7b = state.get("s7b") or {}
    if s7b.get("status") not in ("running", "done", "error"):
        return _fail(f"state.s7b.status={s7b.get('status', 'missing')!r}——请先运行 prepare.py 与 build.py")

    # ---- 1. build_result.json 存在且 schema 合法 ----
    result_path = s7b_out / "build_result.json"
    if not result_path.is_file():
        return _fail("outputs/s7b/build_result.json 不存在——请先运行 build.py")
    result = analysis.load_json(result_path)
    schema_errors = analysis.validate_schema(
        result, SKILL_DIR / "schemas" / "build_result.schema.json", "build_result")
    if schema_errors:
        return _fail("build_result 契约校验失败: " + "; ".join(schema_errors))

    # ---- 2. 日志存在 ----
    if not (s7b_out / "build.log").is_file():
        return _fail("outputs/s7b/build.log 不存在——请先运行 build.py")

    # ---- 3. 按成败分支校验 ----
    problems: list[str] = []
    if result["success"]:
        if result.get("artifact_path"):
            if not (target_root / result["artifact_path"]).is_file():
                problems.append(f"主调试产物不存在: {result['artifact_path']}")
        if result.get("bin_path") is None and not result.get("bin_warning"):
            problems.append("bin_path 为 null 但无 bin_warning（bin 为 S6 合并必需产物）")
        if result.get("bin_path") and not (target_root / result["bin_path"]).is_file():
            problems.append(f"bin 产物不存在: {result['bin_path']}")
    else:
        err_analysis = s7b_out / "error_analysis.md"
        if not err_analysis.is_file():
            return _fail("编译失败但 outputs/s7b/error_analysis.md 不存在——"
                         "请先由 Agent 进入 analyze 阶段（读 build.log 产出分析报告），"
                         "再运行本脚本收口")
    if result.get("build_mode") == "gui":
        if not (s7b_out / "gui_build_log.md").is_file():
            problems.append("GUI 机制要求 outputs/s7b/gui_build_log.md 存在（无论成败）")

    if problems:
        return _fail("产物验证失败: " + "; ".join(problems))

    # ---- 4. state 收口 ----
    if result["success"]:
        payload = {
            "status": "done",
            "build_system": result["build_system"],
            "build_mode": result["build_mode"],
            "build_config": result.get("build_config"),
            "build_target": result["build_target"],
            "artifact_path": result.get("artifact_path"),
            "artifact_format": result.get("artifact_format"),
            "hex_path": result.get("hex_path"),
            "bin_path": result.get("bin_path"),
            "error_count": result["error_count"],
            "warning_count": result["warning_count"],
            "build_log": result["build_log"],
            "build_result": "outputs/s7b/build_result.json",
            "error_analysis": None,
            "gui_build_log": result.get("gui_build_log"),
            "bin_warning": result.get("bin_warning"),
            "error": None,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    else:
        payload = {
            "status": "error",
            "build_system": result["build_system"],
            "build_mode": result["build_mode"],
            "build_config": result.get("build_config"),
            "build_target": result["build_target"],
            "artifact_path": result.get("artifact_path"),
            "artifact_format": result.get("artifact_format"),
            "hex_path": result.get("hex_path"),
            "bin_path": result.get("bin_path"),
            "error_count": result["error_count"],
            "warning_count": result["warning_count"],
            "build_log": result["build_log"],
            "build_result": "outputs/s7b/build_result.json",
            "error_analysis": "outputs/s7b/error_analysis.md",
            "gui_build_log": result.get("gui_build_log"),
            "bin_warning": result.get("bin_warning"),
            "error": (f"编译失败：错误 {result['error_count']} 个"
                      "（根因分析与修复建议见 error_analysis.md）"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s7b")
    if schema_errors:
        return _fail("s7b 状态契约校验失败: " + "; ".join(schema_errors))
    state_store.update_state(ctx["state_path"], {"s7b": payload})

    _log(f"校验通过：status={payload['status']}，"
         f"bin={payload['bin_path'] or 'null（S6 需手动提供）'}")
    _log("下游：S6 firmware-merger 消费 bin；S9 flash 消费 hex/bin（由 S12 或用户编排）")
    print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
