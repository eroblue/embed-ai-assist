#!/usr/bin/env python
"""S9 flash 第 4 段：validate（rule 轨）。

产物验证 + state 收口（与 S7b validate 同模式）：
  - flash_result.json 存在且契约合法
  - release/ 发布文件齐备（本次固件副本 + flash_info.json；jlink 时含 flash_cmd.jlink）
  - 成功分支：verify_passed 非 false（verify 开启时必须 true）、firmware_sha256 存在
    → state.s9 = done
  - 失败分支：error_analysis.md 已由 Agent（阶段 C）产出 → state.s9 = error
    （缺失则报错，提示先进入 analyze）
  - GUI 机制（五期）：gui_flash_log.md 必须存在

退出码：0 验证通过（state 收口 done/error）；2 产物缺失 / 契约不符 / 流程未走完。
"""

from __future__ import annotations

import argparse
import json
import sys
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
EXIT_VALIDATION_FAILED = 2


def _log(msg: str) -> None:
    print(f"[s9-validate] {msg}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="S9 flash validate：产物验证 + state 收口（rule 轨）")
    parser.add_argument("--config", required=True, help="项目级 config.json 路径")
    parser.add_argument("--workspace", default=None,
                        help="工作区根（缺省为 --config 所在目录）")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve() if args.workspace else None

    try:
        ctx = analysis.load_flash_context(config_path, workspace, require_s7b=False)
    except Exception as exc:
        _log(f"[错误] S9 上下文加载失败: {exc}")
        return EXIT_VALIDATION_FAILED

    s9 = ctx["state"].get("s9") or {}
    if s9.get("status") not in ("running", "done", "error"):
        _log(f"[错误] state.s9.status = {s9.get('status')!r} 非法——请先运行 prepare.py 与 flash.py")
        return EXIT_VALIDATION_FAILED

    errors: list[str] = []

    # ---- 1. flash_result.json 存在 + 契约 ----
    result_path = ctx["s9_outputs"] / "flash_result.json"
    if not result_path.is_file():
        _log("[错误] 缺失 outputs/s9/flash_result.json——flash.py 未执行或产物被清理")
        return EXIT_VALIDATION_FAILED
    result = analysis.load_json(result_path)
    errors += analysis.validate_schema(
        result, SKILL_DIR / "schemas" / "flash_result.schema.json", "flash_result")

    # ---- 2. release/ 发布文件齐备 ----
    firmware_abs = ctx["project_root"] / result["firmware_path"]
    if not firmware_abs.is_file():
        errors.append(f"release 固件副本缺失: {result['firmware_path']}")
    info_path = ctx["release_dir"] / "flash_info.json"
    if not info_path.is_file():
        errors.append("release/flash_info.json 缺失（发布清单，成败均写）")
    else:
        info = analysis.load_json(info_path)
        errors += analysis.validate_schema(
            info, SKILL_DIR / "schemas" / "flash_info.schema.json", "flash_info")
        # 发布清单 hash 与烧录固件一致性（现场计算比对——不信任清单记录值）
        if firmware_abs.is_file():
            if analysis.sha256_file(firmware_abs) != result.get("firmware_sha256"):
                errors.append("release 固件副本 SHA256 与 flash_result 记录不一致"
                              "——副本在烧录后被外部改动")
    if result.get("flash_tool") == "jlink" and not (ctx["release_dir"] / "flash_cmd.jlink").is_file():
        errors.append("release/flash_cmd.jlink 缺失（jlink 复烧脚本）")
    if not (ctx["s9_outputs"] / "flash.log").is_file():
        errors.append("outputs/s9/flash.log 缺失")

    # ---- 3. 成败分支校验 ----
    success = bool(result.get("success"))
    if success:
        if result.get("verify") and result.get("verify_passed") is not True:
            errors.append("烧录标记成功但 verify 开启时校验结果非 true"
                          "（verify 失败不算烧录成功）")
        if not result.get("firmware_sha256"):
            errors.append("缺少 firmware_sha256（无法追溯烧录的固件指纹）")
    else:
        error_analysis_rel = analysis.rel_posix(ctx["s9_outputs"] / "error_analysis.md",
                                                ctx["workspace"])
        if not (ctx["s9_outputs"] / "error_analysis.md").is_file():
            errors.append("烧录失败但 error_analysis.md 未产出——请先由 Agent 进入"
                          f"阶段 C（依据 {result['flash_log']} 产出 "
                          f"{error_analysis_rel}）再运行 validate")
    if result.get("flash_mode") == "gui" and not (
            ctx["s9_outputs"] / "gui_flash_log.md").is_file():
        errors.append("GUI 烧录机制缺少 gui_flash_log.md（Agent 操作记录）")

    if errors:
        for e in errors:
            _log(f"[错误] {e}")
        return EXIT_VALIDATION_FAILED

    # ---- 4. state 收口（成功 done / 失败 error）----
    state_payload = dict(s9)
    state_payload.update({
        "status": "done" if success else "error",
        "firmware_path": result["firmware_path"],
        "firmware_format": result["firmware_format"],
        "firmware_source": result["firmware_source"],
        "firmware_size": result.get("firmware_size"),
        "firmware_sha256": result.get("firmware_sha256"),
        "device": result["device"],
        "interface": result["interface"],
        "target_address": result.get("target_address"),
        "verify": result["verify"],
        "verify_passed": result.get("verify_passed"),
        "reset_done": bool(result.get("reset_done")),
        "chip_erase": bool(result.get("chip_erase")),
        "duration_sec": result.get("duration_sec"),
        "flash_log": result["flash_log"],
        "flash_result": analysis.rel_posix(result_path, ctx["workspace"]),
        "release_dir": analysis.rel_posix(ctx["release_dir"], ctx["project_root"]),
        "release_manifest": analysis.rel_posix(info_path, ctx["project_root"]),
        "error_analysis": (analysis.rel_posix(ctx["s9_outputs"] / "error_analysis.md",
                                              ctx["workspace"])
                           if not success else s9.get("error_analysis")),
        "error": result.get("error") if not success else None,
        "updated_at": analysis.now_iso(),
    })
    schema_errors = analysis.validate_schema(
        state_payload, SKILL_DIR / "schemas" / "output.schema.json", "s9")
    if schema_errors:
        for e in schema_errors:
            _log(f"[错误] state.s9 契约校验失败: {e}")
        return EXIT_VALIDATION_FAILED
    state_store.update_state(ctx["state_path"], {"s9": state_payload})

    if success:
        _log(f"验证通过：烧录 done（固件 {result['firmware_path']}，"
             f"SHA256 {str(result.get('firmware_sha256'))[:16]}…，"
             f"verify_passed={result.get('verify_passed')}，"
             f"reset_done={result.get('reset_done')}）")
        _log(f"交付目录: {ctx['release_dir']}（含 flash_info.json 与复烧脚本）")
    else:
        _log("验证完成：烧录失败已收口 error（error_analysis.md 已产出，"
             "请按其中的处置建议手动恢复后重跑 S9）")
    print(json.dumps({"s9": {k: state_payload[k] for k in (
        "status", "flash_tool", "firmware_path", "firmware_sha256", "verify_passed",
        "reset_done", "release_manifest", "error")}}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
