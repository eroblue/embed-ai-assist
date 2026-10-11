#!/usr/bin/env python
"""S7b build 第 2 段（rule 轨）。

机制一 CLI（keil/iar/gcc_make/gcc_cmake，纯 rule）：
  调用工具链编译 → 多编码收集日志 → 退出码/日志双判定 → 生成 bin（必须）+
  补生成 hex → build_result.json → state.s7b（成功 done / 失败 running 待 analyze）

机制二 GUI（vendor_ide，Agent 编译 + rule 收口）：
  Agent 按 vendor 指南操作厂家 IDE（B1–B6）后，本脚本 `--collect` 收口：
  产物检测（mtime > T0）→ intelhex hex→bin → build_result.json → state

退出码：0 编译成功（含 bin 生成失败但已警告）；1 编译失败（CLI 日志与
build_result.json 已产出；GUI 无新产物/超时；提示进入 analyze 阶段）；
2 配置错误 / 无法调用工具链（超时按 1 处理）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
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
EXIT_BUILD_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s7b-build] {msg}", file=sys.stderr)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _save_state(ctx: dict, payload: dict) -> None:
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s7b")
    if schema_errors:
        _log("s7b 状态契约校验失败: " + "; ".join(schema_errors))
    state_store.update_state(ctx["state_path"], {"s7b": payload})


def _base_payload(ctx: dict, parsed: dict) -> dict:
    return {
        "build_system": ctx["build_system"],
        "build_mode": ctx["build_mode"],
        "build_config": ctx["build_config"],
        "build_target": ctx["build_target"],
        "error_count": parsed["error_count"],
        "warning_count": parsed["warning_count"],
        "build_log": "outputs/s7b/build.log",
        "build_result": "outputs/s7b/build_result.json",
        "error_analysis": None,
        "gui_build_log": "outputs/s7b/gui_build_log.md" if ctx["build_mode"] == "gui" else None,
        "error": None,
        "updated_at": _now(),
    }


def _tool_exe(ctx: dict, build_system: str) -> str | None:
    """编译工具可执行文件路径（按构建系统选择主工具）。"""
    tools = ctx["tools"]
    key = {"keil": "keil", "iar": "iar", "gcc_make": "make",
           "gcc_cmake": "cmake", "vendor_ide": "vendor_ide"}[build_system]
    return tools.get(key, {}).get("path")


# ---------------- bin / hex 生成 ----------------

def _hex_to_bin_intelhex(hex_path: Path, bin_path: Path) -> str | None:
    """intelhex hex→bin 转换（工具链无关；失败返回错误信息）。"""
    try:
        from intelhex import IntelHex
    except ImportError:
        return "intelhex 未安装（pip install intelhex）"
    try:
        ih = IntelHex(str(hex_path))
        ih.tofile(str(bin_path), format="bin")
        return None
    except Exception as exc:  # intelhex 抛出类型不固定
        return f"intelhex 转换失败: {exc}"


def _generate_bin_hex(ctx: dict, artifacts: dict, parsed: dict) -> tuple[dict, list[str]]:
    """编译成功后生成 bin（必须）并补生成 hex，返回 (更新后 artifacts, warnings)。"""
    build_system = ctx["build_system"]
    tools = ctx["tools"]
    target_root = ctx["workspace"]
    warnings: list[str] = []

    artifact = artifacts.get("artifact")
    hex_path = artifacts.get("hex")
    hex_ok = hex_path is not None and hex_path.is_file()
    bin_path: Path | None = None

    # bin 生成：按构建系统选择工具；工具缺失时降级 intelhex（hex 已有）
    bin_tool_key = {"keil": "keil_fromelf", "iar": "iar_ielftool",
                    "gcc_make": "gcc_objcopy", "gcc_cmake": "gcc_objcopy"}.get(build_system)
    bin_tool = tools.get(bin_tool_key or "", {}).get("path") if bin_tool_key else None

    if artifact is not None and artifact.is_file():
        bin_path = artifact.with_suffix(".bin")
        if bin_tool:
            if build_system in ("keil", "iar"):
                cmd = ([bin_tool, "--bin", f"--output={bin_path}", str(artifact)]
                       if build_system == "keil" else
                       [bin_tool, "--bin", str(artifact), str(bin_path)])
            else:
                cmd = [bin_tool, "-O", "binary", str(artifact), str(bin_path)]
            ret = analysis.run_tool(cmd, timeout=120)
            if ret["exit_code"] != 0 or not bin_path.is_file():
                warnings.append(f"bin 生成失败（{Path(bin_tool).name} 退出码 "
                                f"{ret['exit_code']}）: {analysis.decode_log(ret['stderr'])[:200]}")
                bin_path = None
        else:
            # bin 工具缺失：intelhex 兜底（hex 已生成时）
            if hex_ok:
                err = _hex_to_bin_intelhex(hex_path, bin_path)
                if err:
                    warnings.append(f"bin 转换工具缺失且 intelhex 兜底失败: {err}")
                    bin_path = None
                else:
                    warnings.append("bin 转换工具缺失，已用 intelhex 从 hex 降级转换")
            else:
                warnings.append("bin 转换工具缺失且无 hex 可兜底——bin_path=null，"
                                "S6 合并时需用户手动提供 bin")
                bin_path = None

    # hex 补生成（S7b 禁止修改工程文件，不能依赖工程内勾选项）
    if not hex_ok and artifact is not None and artifact.is_file():
        hex_path = artifact.with_suffix(".hex")
        if bin_tool:
            if build_system in ("keil", "iar"):
                cmd = ([bin_tool, "--i32", f"--output={hex_path}", str(artifact)]
                       if build_system == "keil" else
                       [bin_tool, "--ihex", str(artifact), str(hex_path)])
            else:
                cmd = [bin_tool, "-O", "ihex", str(artifact), str(hex_path)]
            ret = analysis.run_tool(cmd, timeout=120)
            if ret["exit_code"] != 0 or not hex_path.is_file():
                warnings.append(f"hex 补生成失败（退出码 {ret['exit_code']}）")
                hex_path = None
        else:
            hex_path = None
            warnings.append("hex 转换工具缺失，hex 未补生成（S9 烧录可消费 bin/axf）")

    artifacts["hex"] = hex_path if (hex_path and hex_path.is_file()) else None
    artifacts["bin"] = bin_path if (bin_path and bin_path.is_file()) else None
    return artifacts, warnings


# ---------------- 机制一：CLI 编译 ----------------

def _make_env(ctx: dict, make_exe: str) -> dict:
    """构造 gcc_make 执行环境：PATH 前置 gcc/make 所在目录；探测同目录 sh.exe。

    返回的环境 dict 含内部键 _shell（调用方 pop 后使用，不进入 subprocess）。
    """
    import os
    env = dict(os.environ)
    path_dirs: list[str] = []
    tools = ctx.get("tools") or {}
    for key in ("gcc", "gcc_objcopy", "make"):
        p = (tools.get(key) or {}).get("path")
        if p:
            d = str(Path(p).parent)
            if d not in path_dirs:
                path_dirs.append(d)
    if path_dirs:
        env["PATH"] = os.pathsep.join(path_dirs) + os.pathsep + env.get("PATH", "")
    shell = ""
    sh_cand = Path(make_exe).parent / "sh.exe"
    if sh_cand.is_file():
        shell = sh_cand.as_posix()
    env["_shell"] = shell
    return env


def cli_build(ctx: dict, rebuild: bool, timeout: float) -> int:
    build_system = ctx["build_system"]
    build_config = ctx["build_config"]
    project_file = ctx["project_file"]
    tools = ctx["tools"]
    s7b_out = ctx["s7b_outputs"]
    s7b_out.mkdir(parents=True, exist_ok=True)
    log_path = s7b_out / "build.log"

    tool_exe = _tool_exe(ctx, build_system)
    if not tool_exe:
        _log(f"编译工具不可用（{build_system}）——重跑 prepare.py 检查工具链")
        return EXIT_CONFIG_ERROR

    build_start = datetime.now()
    cmds = analysis.build_commands(build_system, tool_exe, project_file,
                                   build_config, log_path, rebuild)
    # gcc_make：MSYS make 的 POSIX recipe 需要 sh；make 同目录有 sh.exe 时经 SHELL 变量注入，
    # 并把 gcc/make 所在目录加入 PATH（Makefile 内 CC 等按 bare 名引用）
    make_env = None
    if build_system == "gcc_make":
        make_env = _make_env(ctx, tool_exe)
        shell_exe = make_env.pop("_shell")
        if shell_exe:
            for c in cmds:
                c.append(f"SHELL={shell_exe}")
    _log(f"编译命令: {' && '.join(' '.join(c) for c in cmds)}")

    # 清除上次残留日志（Keil 由 UV4 -o 重写；其余系统由 stdout 收集——
    # 残留旧日志会混入本次解析，曾导致跨构建系统的结果误判）
    log_path.unlink(missing_ok=True)

    exit_code: int | None = None
    stdout_parts: list[bytes] = []
    stderr_parts: list[bytes] = []
    timed_out = False
    for cmd in cmds:
        ret = analysis.run_tool(cmd, timeout=timeout, cwd=project_file.parent,
                                env=make_env)
        stdout_parts.append(ret["stdout"])
        stderr_parts.append(ret["stderr"])
        exit_code = ret["exit_code"]
        timed_out = timed_out or ret["timed_out"]
        is_clean = build_system == "gcc_make" and cmd[1:] == ["clean"]
        if ret["timed_out"]:
            break
        if ret["exit_code"] not in (0, None) and not is_clean:
            break  # make clean 允许失败（首次构建无产物可清）

    # ---- 日志收集（UV4 -o 已写文件；其余工具取 stdout/stderr）----
    log_text = ""
    if log_path.is_file():
        log_text = analysis.decode_log(log_path.read_bytes())
    if any(stdout_parts) or any(stderr_parts):
        extra = analysis.decode_log(b"\n".join(p for p in stdout_parts if p))
        extra_err = analysis.decode_log(b"\n".join(p for p in stderr_parts if p))
        log_text = (log_text + ("\n" if log_text else "")
                    + ("[stdout]\n" + extra if extra.strip() else "")
                    + ("\n[stderr]\n" + extra_err if extra_err.strip() else ""))
    if not log_text.strip():
        log_text = f"(无编译输出——工具退出码 {exit_code}，超时={timed_out})"
    log_path.write_text(log_text, encoding="utf-8", newline="\n")

    # ---- 判定：退出码语义 + 日志解析双条件 ----
    parsed = analysis.parse_log(build_system, log_text)
    success = (not timed_out) and analysis.exit_code_success(
        build_system, exit_code, parsed["error_count"])
    if timed_out:
        _log(f"编译超时（>{timeout:.0f}s），按失败处理")

    # ---- 产物定位 + bin/hex 生成（仅成功时） ----
    artifacts: dict = {"artifact": None, "artifact_format": None,
                       "hex": None, "bin": None}
    warnings: list[str] = list(ctx.get("warnings") or [])
    if success:
        artifacts = analysis.locate_artifacts(build_system, project_file,
                                              build_config, log_text)
        if artifacts["artifact"] is None or not artifacts["artifact"].is_file():
            # 日志/推断均未定位到主产物（Keil axf 按约定路径应存在）
            warnings.append("主调试产物未能定位（artifact_path=null，由 S9 flash 阶段再定位）")
        else:
            artifacts, bin_warnings = _generate_bin_hex(ctx, artifacts, parsed)
            warnings.extend(bin_warnings)

    target_root = ctx["workspace"]
    result = {
        "success": success,
        "build_system": build_system,
        "build_mode": "cli",
        "build_config": build_config,
        "build_target": ctx["build_target"],
        "artifact_path": (analysis.rel_posix(artifacts["artifact"], target_root)
                          if artifacts.get("artifact") and artifacts["artifact"].is_file() else None),
        "artifact_format": artifacts.get("artifact_format")
                            if artifacts.get("artifact") else None,
        "hex_path": analysis.rel_posix(artifacts["hex"], target_root)
                    if artifacts.get("hex") and artifacts["hex"].is_file() else None,
        "bin_path": analysis.rel_posix(artifacts["bin"], target_root)
                    if artifacts.get("bin") and artifacts["bin"].is_file() else None,
        "error_count": parsed["error_count"],
        "warning_count": parsed["warning_count"],
        "errors": parsed["errors"],
        "warnings": parsed["warnings"],
        "bin_warning": ("; ".join(warnings) if warnings else None),
        "build_log": "outputs/s7b/build.log",
        "gui_build_log": None,
        "tool_exit_code": exit_code,
        "timed_out": timed_out,
        "generated_at": _now(),
    }
    schema_errors = analysis.validate_schema(
        result, SKILL_DIR / "schemas" / "build_result.schema.json", "build_result")
    if schema_errors:
        _log("build_result 契约校验失败: " + "; ".join(schema_errors))
    analysis.save_json(s7b_out / "build_result.json", result)

    # ---- state：成功 done；失败 running（待 Agent analyze，validate 收口为 error） ----
    payload = _base_payload(ctx, parsed)
    payload.update({
        "status": "done" if success else "running",
        "artifact_path": result["artifact_path"],
        "artifact_format": result["artifact_format"],
        "hex_path": result["hex_path"],
        "bin_path": result["bin_path"],
        "bin_warning": result["bin_warning"],
        "error": None if success else (
            f"编译失败：退出码 {exit_code}，错误 {parsed['error_count']} 个"
            + ("，超时" if timed_out else "")
            + "——进入 analyze 阶段（Agent 读 build.log 产出 error_analysis.md）"),
    })
    _save_state(ctx, payload)

    if success:
        _log(f"编译成功：错误 {parsed['error_count']}，警告 {parsed['warning_count']}；"
             f"bin={result['bin_path'] or 'null（见警告）'}")
        _log("下一步：运行 validate.py 收口")
        print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
        return EXIT_OK
    _log(payload["error"] or "编译失败")
    _log("下一步：Agent 读 outputs/s7b/build.log + build_result.json 产出 "
         "error_analysis.md（不自动修复），再运行 validate.py 收口")
    print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
    return EXIT_BUILD_FAILED


# ---------------- 机制二：GUI 收口（--collect） ----------------

def gui_collect(ctx: dict) -> int:
    build_system = ctx["build_system"]
    assert build_system == "vendor_ide"
    target_root = ctx["workspace"]
    s7b_out = ctx["s7b_outputs"]
    log_path = s7b_out / "build.log"
    gui_log = s7b_out / "gui_build_log.md"

    # gui_session.json 由 prepare 写入（T0 / 输出目录）
    session_path = s7b_out / "gui_session.json"
    if not session_path.is_file():
        _log("outputs/s7b/gui_session.json 不存在——请先运行 prepare.py（GUI 机制）")
        return EXIT_CONFIG_ERROR
    session = analysis.load_json(session_path)
    t0 = datetime.fromisoformat(session["t0"])
    out_dir = target_root / session["output_dir"]
    if not out_dir.is_dir():
        _log(f"厂家 IDE 输出目录不存在: {out_dir}")
        return EXIT_CONFIG_ERROR

    # ---- 产物检测：mtime > T0 的 hex/bin ----
    candidates = [f for f in list(out_dir.glob("*.hex")) + list(out_dir.glob("*.bin"))
                  if datetime.fromtimestamp(f.stat().st_mtime) > t0]
    if not candidates:
        parsed = {"error_count": -1, "warning_count": -1, "errors": [], "warnings": []}
        result = _gui_result(ctx, parsed, None, None, None,
                             "无新产物（输出目录无 mtime > T0 的 hex/bin）")
        analysis.save_json(s7b_out / "build_result.json", result)
        payload = _base_payload(ctx, parsed)
        payload.update({"status": "running",
                        "bin_warning": None,
                        "error": "GUI 编译失败：无新产物（超时或快捷键未生效）——"
                                 "进入 analyze 阶段（读 build.log + gui_build_log.md）"})
        _save_state(ctx, payload)
        _log(payload["error"])
        return EXIT_BUILD_FAILED

    newest = max(candidates, key=lambda f: f.stat().st_mtime)
    hex_path = newest if newest.suffix.lower() == ".hex" else None
    bin_path = newest if newest.suffix.lower() == ".bin" else None

    # bin 生成：仅有 hex 时用 intelhex 转 bin（工具链无关）
    warnings: list[str] = []
    if bin_path is None and hex_path is not None:
        bin_path = hex_path.with_suffix(".bin")
        err = _hex_to_bin_intelhex(hex_path, bin_path)
        if err:
            warnings.append(f"intelhex hex→bin 失败: {err}——bin_path=null，"
                            "S6 合并时需用户手动提供 bin")
            bin_path = None

    # 日志解析（B5 Agent 抄录的 build.log；缺失时错误数 -1）
    parsed: dict
    if log_path.is_file():
        parsed = analysis.parse_log(build_system,
                                    analysis.decode_log(log_path.read_bytes()))
    else:
        parsed = {"error_count": -1, "warning_count": -1, "errors": [], "warnings": []}
    success = parsed["error_count"] in (0, -1) and not parsed["errors"]

    result = _gui_result(ctx, parsed, hex_path, bin_path, gui_log,
                         "; ".join(warnings) if warnings else None)
    analysis.save_json(s7b_out / "build_result.json", result)
    payload = _base_payload(ctx, parsed)
    payload.update({
        "status": "done" if success else "running",
        "artifact_path": None, "artifact_format": None,
        "hex_path": analysis.rel_posix(hex_path, target_root) if hex_path else None,
        "bin_path": analysis.rel_posix(bin_path, target_root) if bin_path else None,
        "bin_warning": result["bin_warning"],
        "error": None if success else (
            f"GUI 编译失败：抄录错误 {len(parsed['errors'])} 条"
            "——进入 analyze 阶段（读 build.log + gui_build_log.md，区分编译失败与 GUI 操作失败）"),
    })
    _save_state(ctx, payload)
    if success:
        _log(f"GUI 编译成功：hex={payload['hex_path']}，bin={payload['bin_path']}")
        print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
        return EXIT_OK
    _log(payload["error"] or "GUI 编译失败")
    print(json.dumps({"s7b": payload}, ensure_ascii=False, indent=2))
    return EXIT_BUILD_FAILED


def _gui_result(ctx: dict, parsed: dict, hex_path: Path | None, bin_path: Path | None,
                gui_log: Path | None, bin_warning: str | None) -> dict:
    target_root = ctx["workspace"]
    return {
        "success": parsed["error_count"] in (0, -1) and not parsed["errors"],
        "build_system": "vendor_ide",
        "build_mode": "gui",
        "build_config": None,
        "build_target": ctx["build_target"],
        "artifact_path": None, "artifact_format": None,
        "hex_path": analysis.rel_posix(hex_path, target_root) if hex_path else None,
        "bin_path": analysis.rel_posix(bin_path, target_root) if bin_path else None,
        "error_count": parsed["error_count"],
        "warning_count": parsed["warning_count"],
        "errors": parsed["errors"],
        "warnings": parsed["warnings"],
        "bin_warning": bin_warning,
        "build_log": "outputs/s7b/build.log",
        "gui_build_log": ("outputs/s7b/gui_build_log.md" if gui_log else None),
        "tool_exit_code": None,
        "timed_out": False,
        "generated_at": _now(),
    }


# ---------------- 主流程 ----------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S7b build: CLI 机制编译（纯 rule）/ GUI 机制 --collect 收口")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    parser.add_argument("--rebuild", action="store_true",
                        help="全量重编（keil -r / make clean / cmake --clean-first）")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="编译超时秒数（缺省 600，超时杀进程按失败处理）")
    parser.add_argument("--collect", action="store_true",
                        help="GUI 收口模式（vendor_ide：产物检测 mtime>T0 / intelhex 转 bin / 结果落盘）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    try:
        ctx = analysis.load_build_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        print(json.dumps({"s7b": {"status": "error", "error": str(exc),
                                   "updated_at": _now()}},
                         ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 恢复 prepare 判定结果（构建系统/配置/工程文件/工具链）----
    state = ctx["state"]
    s7b_state = state.get("s7b") or {}
    if s7b_state.get("status") not in ("running", "done", "error"):
        _log("state.s7b.status 非 running——请先运行 prepare.py")
        return EXIT_CONFIG_ERROR
    ctx["build_system"] = s7b_state.get("build_system")
    ctx["build_mode"] = s7b_state.get("build_mode") or "cli"
    ctx["build_config"] = s7b_state.get("build_config")
    if not ctx["build_system"]:
        _log("state.s7b 缺少 build_system——请先运行 prepare.py")
        return EXIT_CONFIG_ERROR
    ctx["tools"] = analysis.resolve_tool_paths(ctx["config"], ctx["build_system"])
    ctx["warnings"] = [s7b_state["bin_warning"]] if s7b_state.get("bin_warning") else []

    if ctx["build_system"] == "vendor_ide":
        if not args.collect:
            _log("build_system=vendor_ide（GUI 机制）：编译由 Agent 按 vendor 指南操作 IDE"
                 "完成（见 outputs/s7b/generation_brief.md），之后运行本脚本 --collect 收口")
            return EXIT_CONFIG_ERROR
        return gui_collect(ctx)

    if args.collect:
        _log("--collect 仅用于 vendor_ide（GUI 机制）")
        return EXIT_CONFIG_ERROR

    # CLI 机制：定位工程文件（与 prepare 同规则）
    try:
        system, project_file = (analysis.infer_build_system(ctx["workspace"], ctx["ide_project"])
                                 if not ctx["build_system"] else (ctx["build_system"], None))
        if project_file is None:
            evidence = analysis.scan_build_evidence(ctx["workspace"])
            files = evidence.get(ctx["build_system"], [])
            if len(files) == 1:
                project_file = files[0]
            elif ctx["ide_project"]:
                project_file = (ctx["workspace"] / ctx["ide_project"]).resolve()
        if project_file is None or not project_file.is_file():
            raise analysis.BuildDetectError(
                f"{ctx['build_system']} 工程文件未找到——重跑 prepare.py")
    except analysis.BuildDetectError as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    ctx["project_file"] = project_file

    return cli_build(ctx, rebuild=args.rebuild, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
