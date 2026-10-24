#!/usr/bin/env python
"""S9 flash 第 1 段：prepare（rule 轨）。

四段式执行模型（与 S7b 相同；CLI 烧录是确定性操作不需要 Agent）：
  1. [rule]  prepare.py   → S7b/S6 就绪检查（--firmware 显式时跳过 state 检查）
                            → 平台/烧录机制判定（mcu8 不推断；一期仅 jlink 全链路）
                            → 烧录工具判定（显式优先；null 智能推断：uvoptx pMon 证据
                              + tool_paths 可用性/平台惯例；多/零候选/证据工具不可用报错）
                            → 工具就绪检查（JLink.exe 缺失报错并附手动指引，不自动安装）
                            → 固件定位（--firmware > S6 > s7b hex > s7b bin）+ 格式校验
                            → 地址计算（flash_offset 唯一权威）+ 越界/对齐/起址防御校验
                            → release/ 发布同步（SHA256 现场比对：一致复用/不一致覆盖）
                            → release/flash_cmd.jlink 生成（自包含复烧脚本）
                            → outputs/s9/generation_brief.md 任务书 → state.s9 = running
  2. [rule]  flash.py     → 执行 J-Link Commander 烧录（从 release/ 副本——烧的即发布的）
  3. [agent] analyze      → 仅烧录失败时产出 error_analysis.md（连接/芯片/固件/工具
                            四类根因；不自动重试、不自动解锁）
  4. [rule]  validate.py  → 产物验证 + state 收口（done/error）

本脚本不生成任何 C 代码，不修改工程文件与固件源文件。
容忍并覆盖陈旧的 s9.status = running（重跑 prepare 幂等）。

退出码：0 就绪检查通过（state.s9=running）；
        2 配置错误 / S7b 未完成 / 工具缺失 / 固件或地址非法 / 演进项工具；
        3 .jflash 缺失时的用户决策口（二期，flash_tool=jflash；一期 jlink 流程不产生）。
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
EXIT_JFLASH_DECISION = 3


def _log(msg: str) -> None:
    print(f"[s9-prepare] {msg}", file=sys.stderr)


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"非法数值: {value!r}（支持 0x 十六进制）")


def _write_error_state(ctx: dict | None, error: str, tool: str | None = None) -> dict:
    """prepare 失败时写 state.s9 = error（退出码 2；state 写入失败不遮蔽原错误）。"""
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


def _brief(ctx: dict, plan: dict) -> list[str]:
    """阶段 A 任务书：烧录信息清单（供追溯与失败分析；烧录由 flash.py 纯 rule 执行）。"""
    fw = plan["firmware"]
    lines: list[str] = []
    add = lines.append
    add("# S9 flash 任务书（CLI 机制）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。烧录由 `flash.py` 纯 rule 执行；")
    add("> 本任务书完整展示本次烧录决策供追溯，并为**烧录失败后的 Agent 分析路径**准备。")
    add("")
    add("## 1. 烧录信息清单")
    add("")
    add("| 项 | 值 |")
    add("|---|---|")
    add(f"| 目标工程 | `{ctx['build_target']}`（工程根 `{analysis.rel_posix(ctx['workspace'], ctx['project_root'])}`） |")
    add(f"| 固件来源 | `{fw['source']}`（s7b 产物 / S6 合并固件 / manual=--firmware 显式） |")
    add(f"| 固件格式 | `{fw['format']}` |")
    add(f"| 固件源路径 | `{fw['path']}` |")
    add(f"| 烧录执行体 | `{plan['cmd_cwd'].name}/{fw['name']}`（release/ 副本——**烧的即发布的**） |")
    add(f"| 固件大小 | {fw['size']} 字节 |")
    add(f"| 固件 SHA256 | `{fw['sha256']}` |")
    add(f"| 目标地址 | " + (f"`0x{fw['target_address']:08X}`"
                          + ("（hex 自带地址，不传给工具）" if fw["format"] == "hex"
                             else "（flash_base + flash_offset）")
                          if fw["target_address"] is not None else "`null`") + " |")
    add(f"| flash_offset | `0x{ctx['flash_offset']:X}`（config 唯一权威，已含在目标地址内） |")
    add(f"| 设备名 | `{plan['device']}`（J-Link 设备库命名） |")
    add(f"| 探针接口 | `{plan['interface']}` |")
    add(f"| 烧录工具 | `{plan['flash_tool']}`（{plan['tool_note']}） |")
    add(f"| verify | {'开启（烧录后校验，失败不算成功）' if plan['verify'] else '关闭（--no-verify）'} |")
    add(f"| 复位运行 | {'开启（r + g）' if plan['reset'] else '关闭（--no-reset，烧后不复位）'} |")
    add(f"| 全片擦除 | {'开启（--chip-erase，破坏性）' if plan['chip_erase'] else '关闭（按固件范围擦除）'} |")
    add("")
    add("## 2. 完整命令")
    add("")
    add("```bash")
    add(f"cd {plan['cmd_cwd']}")
    add(" ".join(plan["cmd"]))
    add("```")
    add("")
    add(f"命令脚本 `{plan['script_path']}`（release/ 内，自包含可复烧）：")
    add("")
    add("```")
    add(plan["script_abs"].read_text(encoding="utf-8").rstrip())
    add("```")
    add("")
    add("## 3. release/ 发布文件")
    add("")
    add("| 文件 | 大小 | SHA256（前 16 位） | 状态 |")
    add("|---|---|---|---|")
    for e in plan["published"]:
        add(f"| `{plan['cmd_cwd'].name}/{e['name']}` | {e['size']} | "
            f"`{e['sha256'][:16]}…` | {'复用（hash 一致）' if e['reused'] else '覆盖复制'} |")
    add(f"| `{plan['script_path']}` | — | — | 每次按当前选项重新生成 |")
    add("")
    add("## 4. 执行策略与禁止事项")
    add("")
    add("- **直接执行烧录，不请求人工确认**（开发迭代场景；verify 缺省开启兜底，")
    add("  完整信息以本任务书为准供追溯）")
    add("- 失败**不自动重试**（`--retry` 缺省 0，连接抖动场景可显式开启）、")
    add("  **不自动解锁**芯片（读保护/写保护状态属用户决策）")
    add("- 烧录工具完全由用户自管理：**不自动下载安装任何烧录工具**（探针偏好、")
    add("  版本兼容、设备数据库支持因人而异）；缺失时仅报错并附手动指引")
    add("- `--timeout` 缺省 300s（flash.py 执行参数），超时杀进程按失败处理")
    add("- `release/` 永不作为固件发现来源（发现只走 state 指针，防烧旧固件）")
    add("")
    add("## 5. 烧录失败时的 Agent 分析路径（阶段 C）")
    add("")
    add("> 仅 flash.py 以退出码 1 结束时进入；产出 `outputs/s9/error_analysis.md`，")
    add("> 按四类根因（连接 / 芯片 / 固件 / 工具）定位，不自动修复。")
    add("")
    add("1. 读 `outputs/s9/flash.log` 与 `outputs/s9/flash_result.json`（key_lines 已提取）")
    add("2. 按日志特征行分类（特征映射表见 `references/flash_log_parse_rules.md`）：")
    add("   连接类（`Connecting...FAILED` / 探针未插）、芯片类（`Cannot connect to target`、")
    add("   供电/复位电路、读保护锁定）、固件类（越界/起址不符/verify 失败）、")
    add("   工具类（`Unknown device` 设备名错、版本过旧不支持该芯片）")
    add("3. 结合本任务书的地址/设备名/工具版本信息给出结论与**用户手动**处置建议")
    add("")
    if plan["warnings"]:
        add("## 6. 防御性校验警告（不阻断，请核对）")
        add("")
        for w in plan["warnings"]:
            add(f"- {w}")
        add("")
    add(f"> 任务书生成于 {datetime.now().isoformat(timespec='seconds')}，"
        "每次 prepare 按当前选项重新生成。")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="S9 flash prepare：烧录就绪检查 + release 发布 + jlink 脚本生成（rule 轨）")
    parser.add_argument("--config", required=True, help="项目级 config.json 路径")
    parser.add_argument("--workspace", default=None,
                        help="工作区根（缺省为 --config 所在目录）")
    parser.add_argument("--firmware", default=None,
                        help="显式固件路径（跳过 state 检查；bin 时需配合 --address）")
    parser.add_argument("--format", choices=["hex", "bin"], default=None,
                        help="强制固件格式（覆盖 s7b hex 优先的选择）")
    parser.add_argument("--address", type=_parse_int, default=None,
                        help="显式烧录地址（--firmware + bin 时必填；正常流程无需提供）")
    parser.add_argument("--device", default=None,
                        help="显式烧录器设备名（J-Link 设备名，映射失败时兜底）")
    parser.add_argument("--jflash-project", default=None,
                        help="显式 .jflash 工程文件（flash_tool=jflash，二期）")
    parser.add_argument("--gen-jflash", action="store_true",
                        help="自动生成 release/flash.jflash（flash_tool=jflash 决策流程，二期）")
    parser.add_argument("--interface", choices=["SWD", "JTAG"], default="SWD",
                        help="探针接口（缺省 SWD）")
    parser.add_argument("--no-verify", action="store_true", help="跳过烧录后校验")
    parser.add_argument("--no-reset", action="store_true", help="烧录后不复位运行")
    parser.add_argument("--chip-erase", action="store_true",
                        help="全片擦除（破坏性，显式 opt-in；缺省按固件范围擦除）")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None
    if args.gen_jflash or args.jflash_project:
        _log("提示: --gen-jflash/--jflash-project 仅在 flash_tool=jflash（二期）时生效，"
             "本期 jlink 流程忽略")

    ctx: dict | None = None
    try:
        ctx = analysis.load_flash_context(
            config_path, workspace, require_s7b=not args.firmware)
    except Exception as exc:
        _write_error_state(ctx, f"S9 就绪检查失败: {exc}")
        _log(f"[错误] S9 就绪检查失败: {exc}")
        return EXIT_CONFIG_ERROR

    opts = {
        "firmware": args.firmware,
        "format": args.format,
        "address": args.address,
        "device": args.device,
        "interface": args.interface,
        "verify": not args.no_verify,
        "reset": not args.no_reset,
        "chip_erase": args.chip_erase,
    }
    try:
        plan = analysis.plan_flash(ctx, opts)
    except (analysis.FlashPlanError, analysis.FlashDetectError) as exc:
        _write_error_state(ctx, f"烧录计划非法: {exc}")
        _log(f"[错误] 烧录计划非法: {exc}")
        return EXIT_CONFIG_ERROR

    # 任务书（schema 校验 state 前先落盘，失败分析需要它）
    ctx["s9_outputs"].mkdir(parents=True, exist_ok=True)
    brief_path = ctx["s9_outputs"] / "generation_brief.md"
    brief_path.write_text("\n".join(_brief(ctx, plan)) + "\n", encoding="utf-8")

    payload = {
        "status": "running",
        "flash_tool": plan["flash_tool"],
        "flash_mode": plan["flash_mode"],
        "firmware_path": plan["firmware"]["release_path"],
        "firmware_format": plan["firmware"]["format"],
        "firmware_source": plan["firmware"]["source"],
        "firmware_size": plan["firmware"]["size"],
        "firmware_sha256": plan["firmware"]["sha256"],
        "device": plan["device"],
        "jflash_project": None,
        "interface": plan["interface"],
        "target_address": plan["firmware"]["target_address"],
        "verify": plan["verify"],
        "verify_passed": None,
        "reset": plan["reset"],
        "reset_done": False,
        "chip_erase": plan["chip_erase"],
        "duration_sec": None,
        "flash_log": analysis.rel_posix(ctx["s9_outputs"] / "flash.log", ctx["workspace"]),
        "flash_result": analysis.rel_posix(ctx["s9_outputs"] / "flash_result.json", ctx["workspace"]),
        "release_dir": analysis.rel_posix(ctx["release_dir"], ctx["project_root"]),
        "release_manifest": analysis.rel_posix(ctx["release_dir"] / "flash_info.json",
                                               ctx["project_root"]),
        "error_analysis": None,
        "gui_flash_log": None,
        "error": None,
        "updated_at": analysis.now_iso(),
    }
    errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s9")
    if errors:
        _log("[错误] state.s9 契约校验失败: " + "; ".join(errors))
        return EXIT_CONFIG_ERROR
    state_store.update_state(ctx["state_path"], {"s9": payload})

    for w in plan["warnings"]:
        _log(f"[警告] {w}")
    _log(f"任务书: {brief_path}")
    _log(f"复烧脚本: {plan['script_abs']}")
    _log(f"固件: {plan['firmware']['release_path']}（{plan['firmware']['size']} 字节，"
         f"目标 0x{plan['firmware']['target_address']:X}）"
         if plan["firmware"]["target_address"] is not None
         else f"固件: {plan['firmware']['release_path']}（{plan['firmware']['size']} 字节）")
    print(json.dumps({"s9": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
