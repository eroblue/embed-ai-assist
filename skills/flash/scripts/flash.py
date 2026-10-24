#!/usr/bin/env python
"""S9 flash 第 2 段：flash（CLI 机制为 rule 轨；GUI 机制为 agent 轨——五期演进项）。

执行 prepare 已生成的烧录计划（release/flash_cmd.jlink——烧的即发布的）：
  - 默认严格消费 state.s9 计划；传入任一计划参数（--firmware/--format/--address/
    --device/--interface/--no-verify/--no-reset/--chip-erase）时按新参数重算计划并
    重新生成脚本（幂等：release 副本 hash 一致复用、不一致覆盖）
  - J-Link Commander：cwd = release/，脚本内固件为相对引用（自包含可交付）
  - 成功判定 = 退出码 0 + 日志特征（Downloading + Programming/Writing）+ 无失败
    特征 + verify 开启时校验通过（verify 失败不算成功——state 标 error）
  - 超时杀进程按失败处理（退出码 1）；--retry 缺省 0 不自动重试（靠 analyze 闭环）
  - 结束落盘：outputs/s9/flash.log + flash_result.json；release/flash_info.json
    （发布清单，成败均写）；state.s9 收口（成功 done / 失败 running 待 analyze）

退出码：0 烧录成功；1 烧录失败（连接/芯片/固件/verify，进入阶段 C analyze）；
        2 配置错误 / 无法调用烧录工具 / state.s9 非 running（超时按 1 处理）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
EXIT_FLASH_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s9-flash] {msg}", file=sys.stderr)


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"非法数值: {value!r}（支持 0x 十六进制）")


def _write_error_state(ctx: dict | None, error: str, tool: str | None = None) -> dict:
    payload = {"status": "error",
               "flash_tool": tool,
               "flash_mode": "cli",
               "error": error,
               "updated_at": datetime.now().isoformat(timespec="seconds")}
    if ctx is not None:
        try:
            state_store.update_state(ctx["state_path"], {"s9": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
    return payload


def _inherit_opts(ctx: dict, s9: dict, args) -> dict:
    """计划参数解析：CLI 参数覆盖 > state.s9 继承 > 文档缺省。

    manual 固件来源在 flash.py 重放时以 release 副本为源（hash 与原始文件一致，
    sync_release 幂等复用），bin 地址继承 s9.target_address。
    """
    firmware_arg = args.firmware
    if firmware_arg is None and s9.get("firmware_source") == "manual" \
            and s9.get("firmware_path"):
        firmware_arg = str((ctx["project_root"] / s9["firmware_path"]).resolve())
    address_arg = args.address
    if address_arg is None and firmware_arg is not None \
            and s9.get("firmware_format") == "bin" \
            and isinstance(s9.get("target_address"), int):
        address_arg = s9["target_address"]
    return {
        "firmware": firmware_arg,
        "format": args.format or s9.get("firmware_format"),
        "address": address_arg,
        "device": args.device or s9.get("device"),
        "interface": args.interface or s9.get("interface") or "SWD",
        "verify": False if args.no_verify else bool(s9.get("verify", True)),
        "reset": False if args.no_reset else bool(s9.get("reset", True)),
        "chip_erase": True if args.chip_erase else bool(s9.get("chip_erase", False)),
    }


def _run_with_retry(plan: dict, timeout: float, retry: int) -> tuple[dict, str, int, float]:
    """执行 J-Link Commander（含重试）。返回 (最终解析, 全量日志, 尝试次数, 总耗时)。"""
    attempts = 1 + max(0, retry)
    log_parts: list[str] = []
    parsed: dict = {}
    used = 0
    start = time.monotonic()
    for attempt in range(1, attempts + 1):
        used = attempt
        try:
            proc = analysis.run_tool(plan["cmd"], timeout=timeout, cwd=plan["cmd_cwd"])
        except OSError as exc:
            log_parts.append(f"===== 尝试 {attempt}/{attempts} =====\n"
                             f"无法调用烧录工具: {exc}")
            parsed = {"success": False, "verify_passed": None, "reset_done": False,
                      "failure_lines": [f"无法调用烧录工具: {exc}"], "key_lines": []}
            break
        text = analysis.decode_log(proc["stdout"]) + analysis.decode_log(proc["stderr"])
        log_parts.append(f"===== 尝试 {attempt}/{attempts} =====\n{text.rstrip()}")
        parsed = analysis.parse_jlink_log(
            text, proc["exit_code"], proc["timed_out"],
            plan["verify"], plan["reset"])
        parsed["tool_exit_code"] = proc["exit_code"]
        parsed["timed_out"] = proc["timed_out"]
        if parsed["success"] or attempt == attempts:
            break
        _log(f"第 {attempt} 次烧录失败，" + ("重试中..." if attempt < attempts
                                            else "停止（--retry 已用尽）"))
    return parsed, "\n\n".join(log_parts) + "\n", used, time.monotonic() - start


def _flash_info_payload(ctx: dict, plan: dict, parsed: dict, success: bool,
                        duration: float) -> dict:
    fw = plan["firmware"]
    files = [e["name"] for e in plan["published"]]
    files += ["flash_cmd.jlink", "flash_info.json"]
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "flash_tool": plan["flash_tool"],
        "device": plan["device"],
        "interface": plan["interface"],
        "firmware": {
            "name": fw["name"],
            "format": fw["format"],
            "source": fw["source"],
            "size": fw["size"],
            "sha256": fw["sha256"],
            "release_path": fw["release_path"],
        },
        "target_address": fw["target_address"],
        "verify": plan["verify"],
        "verify_passed": parsed.get("verify_passed"),
        "success": success,
        "duration_sec": round(duration, 3),
        "repro_command": f"cd {plan['cmd_cwd']} && " + " ".join(plan["cmd"]),
        "release_files": files,
        "error": None if success else ("; ".join(parsed.get("failure_lines")[:5]) or None),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="S9 flash：执行烧录（CLI 机制，rule 轨；从 release/ 副本烧录——烧的即发布的）")
    parser.add_argument("--config", required=True, help="项目级 config.json 路径")
    parser.add_argument("--workspace", default=None,
                        help="工作区根（缺省为 --config 所在目录）")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="烧录超时秒数（缺省 300，超时杀进程按失败处理）")
    parser.add_argument("--retry", type=int, default=0,
                        help="失败自动重试次数（缺省 0 不重试，靠 analyze 闭环；连接抖动场景）")
    parser.add_argument("--collect", action="store_true",
                        help="GUI 机制收口模式（flash_tool=vendor_ide 时 Agent 操作后调用；五期演进项）")
    # ---- 计划参数（传入任一则重算计划并重新生成脚本；缺省严格消费 prepare 计划）----
    parser.add_argument("--firmware", default=None, help="显式固件路径（bin 时需 --address）")
    parser.add_argument("--format", choices=["hex", "bin"], default=None, help="强制固件格式")
    parser.add_argument("--address", type=_parse_int, default=None, help="显式烧录地址")
    parser.add_argument("--device", default=None, help="显式设备名")
    parser.add_argument("--interface", choices=["SWD", "JTAG"], default=None, help="探针接口")
    parser.add_argument("--no-verify", action="store_true", help="跳过烧录后校验")
    parser.add_argument("--no-reset", action="store_true", help="烧录后不复位运行")
    parser.add_argument("--chip-erase", action="store_true", help="全片擦除（破坏性）")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None

    ctx: dict | None = None
    try:
        ctx = analysis.load_flash_context(
            config_path, workspace, require_s7b=not args.firmware)
    except Exception as exc:
        _write_error_state(ctx, f"S9 上下文加载失败: {exc}")
        _log(f"[错误] {exc}")
        return EXIT_CONFIG_ERROR

    s9 = (ctx["state"].get("s9") or {})
    if not s9 or s9.get("status") not in ("running", "done", "error"):
        _write_error_state(ctx, "state.s9 缺失或状态非法——请先运行 prepare.py")
        _log("[错误] state.s9 缺失或状态非法——请先运行 prepare.py")
        return EXIT_CONFIG_ERROR
    if args.collect:
        _write_error_state(ctx, "--collect 仅用于 GUI 机制（flash_tool=vendor_ide，五期演进项）；"
                                "CLI 机制由本脚本直接执行烧录", s9.get("flash_tool"))
        _log("[错误] --collect 仅用于 GUI 机制（五期演进项）")
        return EXIT_CONFIG_ERROR

    try:
        plan = analysis.plan_flash(ctx, _inherit_opts(ctx, s9, args))
    except (analysis.FlashPlanError, analysis.FlashDetectError) as exc:
        _write_error_state(ctx, f"烧录计划非法: {exc}", s9.get("flash_tool"))
        _log(f"[错误] 烧录计划非法: {exc}")
        return EXIT_CONFIG_ERROR

    for w in plan["warnings"]:
        _log(f"[警告] {w}")
    _log(f"烧录中: {' '.join(plan['cmd'])}（cwd={plan['cmd_cwd']}）")
    parsed, log_text, attempts_used, duration = _run_with_retry(
        plan, args.timeout, args.retry)
    success = bool(parsed.get("success"))

    # ---- 产物落盘（flash.log / flash_result.json / release/flash_info.json）----
    ctx["s9_outputs"].mkdir(parents=True, exist_ok=True)
    log_path = ctx["s9_outputs"] / "flash.log"
    log_path.write_text(log_text, encoding="utf-8", errors="replace")

    fw = plan["firmware"]
    result_payload = {
        "success": success,
        "flash_tool": plan["flash_tool"],
        "flash_mode": plan["flash_mode"],
        "flash_target": ctx["build_target"],
        "firmware_path": fw["release_path"],
        "firmware_format": fw["format"],
        "firmware_source": fw["source"],
        "firmware_size": fw["size"],
        "firmware_sha256": fw["sha256"],
        "device": plan["device"],
        "interface": plan["interface"],
        "target_address": fw["target_address"],
        "verify": plan["verify"],
        "verify_passed": parsed.get("verify_passed"),
        "reset": plan["reset"],
        "reset_done": parsed.get("reset_done"),
        "chip_erase": plan["chip_erase"],
        "duration_sec": round(duration, 3),
        "tool_exit_code": parsed.get("tool_exit_code"),
        "timed_out": bool(parsed.get("timed_out")),
        "retries": attempts_used - 1,
        "key_lines": parsed.get("key_lines", []),
        "flash_log": analysis.rel_posix(log_path, ctx["workspace"]),
        "release_manifest": analysis.rel_posix(ctx["release_dir"] / "flash_info.json",
                                               ctx["project_root"]),
        "error": None if success else (
            ("烧录超时（{}s），已终止烧录进程".format(int(args.timeout))
             if parsed.get("timed_out") else "")
            + ("; ".join(parsed.get("failure_lines")[:5])
               or "日志无显式失败特征行，请查看完整日志")),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    info_payload = _flash_info_payload(ctx, plan, parsed, success, duration)
    errors = analysis.validate_schema(
        result_payload, SKILL_DIR / "schemas" / "flash_result.schema.json", "flash_result")
    errors += analysis.validate_schema(
        info_payload, SKILL_DIR / "schemas" / "flash_info.schema.json", "flash_info")
    if errors:
        _log("[错误] 产物契约校验失败: " + "; ".join(errors))
        return EXIT_CONFIG_ERROR
    analysis.save_json(ctx["s9_outputs"] / "flash_result.json", result_payload)
    analysis.save_json(ctx["release_dir"] / "flash_info.json", info_payload)

    # ---- state 收口：成功 done；失败 running（进入阶段 C：Agent analyze）----
    state_payload = dict(s9)
    state_payload.update({
        "status": "done" if success else "running",
        "flash_tool": plan["flash_tool"],
        "flash_mode": plan["flash_mode"],
        "firmware_path": fw["release_path"],
        "firmware_format": fw["format"],
        "firmware_source": fw["source"],
        "firmware_size": fw["size"],
        "firmware_sha256": fw["sha256"],
        "device": plan["device"],
        "interface": plan["interface"],
        "target_address": fw["target_address"],
        "verify": plan["verify"],
        "verify_passed": parsed.get("verify_passed"),
        "reset": plan["reset"],
        "reset_done": bool(parsed.get("reset_done")),
        "chip_erase": plan["chip_erase"],
        "duration_sec": round(duration, 3),
        "flash_log": result_payload["flash_log"],
        "flash_result": analysis.rel_posix(ctx["s9_outputs"] / "flash_result.json",
                                           ctx["workspace"]),
        "release_dir": analysis.rel_posix(ctx["release_dir"], ctx["project_root"]),
        "release_manifest": result_payload["release_manifest"],
        "error": result_payload["error"],
        "updated_at": analysis.now_iso(),
    })
    errors = analysis.validate_schema(
        state_payload, SKILL_DIR / "schemas" / "output.schema.json", "s9")
    if errors:
        _log("[错误] state.s9 契约校验失败: " + "; ".join(errors))
        return EXIT_CONFIG_ERROR
    state_store.update_state(ctx["state_path"], {"s9": state_payload})

    if success:
        _log(f"烧录成功（{duration:.1f}s，"
             f"verify={'O.K.' if parsed.get('verify_passed') else '未开启'}，"
             f"已复位运行={bool(parsed.get('reset_done'))}）")
        _log(f"发布清单: {ctx['release_dir'] / 'flash_info.json'}")
        print(json.dumps({"s9": {k: state_payload[k] for k in (
            "status", "flash_tool", "firmware_path", "target_address", "verify_passed",
            "reset_done", "duration_sec", "release_manifest")}}, ensure_ascii=False))
        return EXIT_OK
    _log(f"烧录失败（退出码 {parsed.get('tool_exit_code')}，"
         f"尝试 {attempts_used} 次）——进入阶段 C：Agent 依据 flash.log 产出 error_analysis.md")
    print(json.dumps({"s9": {"status": "running", "error": result_payload["error"],
                             "flash_log": result_payload["flash_log"],
                             "flash_result": state_payload["flash_result"]}},
                     ensure_ascii=False, indent=2))
    return EXIT_FLASH_FAILED


if __name__ == "__main__":
    sys.exit(main())
