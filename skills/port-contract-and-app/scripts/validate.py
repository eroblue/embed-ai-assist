#!/usr/bin/env python
"""S5b port-contract-and-app 第 3 段：validate（rule 轨，终验）。

三段式执行模型的确定性校验段（Agent 完成两阶段生成后运行）：
  1. [rule]  prepare.py        → 任务书，state.s5b = running
  2. [agent] Agent 两阶段生成   → 流程图（approved）→ diff → 模块代码 →
                                 Port/OSAL/Power + manifest → 顶层连接 +
                                 traceability（增量后经 diff_range_checker）
  3. [rule]  validate.py       → 本脚本

校验内容：流程图规范（复用 flow_validator）与 index 一致性、approved 模块代码
存在、main.c/app.c/manifest/traceability 存在且过 schema、产物引用文件存在、
禁止 include（HAL/RTOS 黑名单 + 分层白名单）、mtime 守卫（full/incremental 模块
代码须晚于任务书）；通过后输出 IDE 待添加清单、调用公共工具 ide_sync.py
同步 IDE 工程（失败不中断）、写 state.s5b = done。

产物校验失败 → 退出码 1（state 保持 running，Agent 修复后重跑）；
环境/契约失败 → 退出码 3（state 写 error）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+
    import json as _json
    from pathlib import Path as _Path
    try:
        _root_cfg = _json.loads(
            (_Path(__file__).resolve().parents[3] / "config.json").read_text(encoding="utf-8"))
        _py = _root_cfg.get("tool_paths", {}).get("python", "")
    except Exception:
        _py = ""
    print(f"[错误] 本框架需要 Python 3.10+，当前解释器为 {sys.version.split()[0]}。"
          + (f"请使用项目配置的解释器：{_py}" if _py
             else "项目配置的解释器见根目录 config.json 的 tool_paths.python"),
          file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import flow_validator  # noqa: E402
import ide_pending_exporter  # noqa: E402
import layout_resolver  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_PRODUCT_INVALID = 1
EXIT_FAILED = 2
EXIT_CONFIG_ERROR = 3

# ---- 禁止 include：黑名单（明确报 HAL/RTOS 违规）----
_FORBIDDEN_HAL_RTOS = re.compile(
    r'#\s*include\s*[<"](?:'
    r'(?:stm32|gd32|ch32|at32|apm32|hc32|n32|lpc|mk|kl|ft6\d|ht|cms|sc8)[a-z0-9_]*\.h'
    r'|[a-z0-9_]*_?hal[a-z0-9_]*\.h|FreeRTOS\.h|FreeRTOSConfig\.h|task\.h|queue\.h'
    r'|semphr\.h|timers\.h|event_groups\.h|cmsis_os[0-9]?\.h|cmsis_compiler\.h'
    r'|rtthread\.h|rthw\.h|rtservice\.h|zephyr\.h|kernel\.h|os_kernel\.h'
    r')[>"]', re.I)

# ---- 分层白名单：include 基名模式（按文件角色）----
_C_STD = r"(?:stdint|stdbool|stddef|stdarg|string|stdio|stdlib|limits|float|math|ctype|assert|time|errno)\.h"
_APP_WHITELIST = re.compile(
    rf"^(?:{_C_STD}|app[\w]*\.h|protocol_\w+\.h|driver_\w+\.h|\w+_port\.h|osal\.h|power_port\.h)$")
_DRIVER_WHITELIST = re.compile(
    rf"^(?:{_C_STD}|driver_\w+\.h|\w+_port\.h|osal\.h|power_port\.h)$")
_PORT_WHITELIST = re.compile(rf"^(?:{_C_STD}|\w+_port\.h|osal\.h|power_port\.h)$")
_S5A_ENTRY = re.compile(r"^(?:board_init|hal_init)\.h$")
_S5A_INIT = re.compile(r"^\w+_init\.h$")


def _log(msg: str) -> None:
    print(f"[s5b-validate] {msg}", file=sys.stderr)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_forbidden_includes(files: list[Path], workspace: Path,
                             architecture: str) -> list[str]:
    """黑名单 + 分层白名单双重检查。

    - app/protocol/main 文件：可 include C 标准库 + 本层 + driver + Port；
      flat 架构额外放行 S5a 初始化头（无 Port 层，APP 直调 BSP），
      layered/full 只放行总入口 board_init/hal_init（main.c 汇总调用）
    - driver 文件：C 标准库 + driver 本层 + Port（不得 include app 层）
    - port 头文件：C 标准库 + Port 本层（最底层，不得向上依赖）
    """
    errors: list[str] = []
    for f in files:
        rel = str(f.resolve().relative_to(workspace)).replace("\\", "/")
        role = analysis.classify_rel_path(rel)
        base = f.name
        is_app_src = role == "app" and (
            base.startswith(("app", "protocol_", "main")))
        if not _read(f).strip():
            continue
        for m in _FORBIDDEN_HAL_RTOS.finditer(_read(f)):
            errors.append(f"{rel}: 禁止 include HAL/RTOS 头文件（{m.group(0).strip()}）"
                          "——RTOS 调用必须过 osal.h，硬件访问必须过 Port")
        inc_names = re.findall(r'#\s*include\s*[<"]([^>"]+)[>"]', _read(f))
        for name in inc_names:
            if _FORBIDDEN_HAL_RTOS.search(f'#include "{name}"'):
                continue  # 已由黑名单报告
            if role == "port":
                ok = bool(_PORT_WHITELIST.match(name))
            elif base.startswith("driver_"):
                ok = bool(_DRIVER_WHITELIST.match(name))
            elif is_app_src:
                ok = bool(_APP_WHITELIST.match(name))
                if not ok and _S5A_ENTRY.match(name):
                    ok = True  # main.c/app.c 汇总调用 S5a 总入口
                elif not ok and architecture == "flat" and _S5A_INIT.match(name):
                    ok = True  # flat 无 Port 层，APP 直调 BSP 初始化
            else:
                ok = True  # 其他文件（如用户自有文件）不做白名单限制
            if not ok:
                errors.append(f"{rel}: 非白名单 include '{name}'（"
                              f"{'Port 头只能依赖 C 标准库与 Port 层' if role == 'port' else '按分层规则 include 本层与 Port 头'}）")
    return errors


def check_products(ctx: dict, src_dirs: list[Path], inc_dirs: list[Path],
                   app_src: list[Path], app_inc: list[Path]) -> list[str]:
    """产物存在性 + 一致性校验。"""
    errors: list[str] = []
    ws = ctx["workspace"]

    # 1. 流程图规范（复用 flow_validator）+ index 一致性
    flow_errors, _warnings, flow_infos = flow_validator.validate_flows(ctx["flow_dir"])
    errors.extend(flow_errors)
    index_path = ctx["outputs_dir"] / "s5b" / "flow_index.json"
    if not index_path.is_file():
        errors.append("缺少 outputs/s5b/flow_index.json（流程图 approved 后须运行 flow_differ.py）")
    else:
        try:
            index = analysis.load_json(index_path)
            by_module = {f.get("module"): f for f in index.get("flows", [])}
            for info in flow_infos:
                entry = by_module.get(info["module"])
                if info.get("status") == "approved" and entry is None:
                    errors.append(f"模块 {info['module']} 流程图已 approved 但未登记进 "
                                  "flow_index（运行 flow_differ.py）")
                elif entry and entry.get("status") == "approved" \
                        and entry.get("hash") != _flow_hash(ctx, info["module"]):
                    errors.append(f"模块 {info['module']} 流程图内容与 flow_index 记录不一致"
                                  "（approved 后被修改？重跑 flow_differ.py，必要时置 dirty 重新审核）")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"flow_index.json 解析失败: {exc}")

    # 2. approved 模块代码存在（模块名 = 文件基名）
    approved_modules: list[str] = []
    for info in flow_infos:
        if info.get("status") == "approved":
            approved_modules.append(info["module"])
            found = any((d / f"{info['module']}.c").is_file() or
                        (d / f"{info['module']}.h").is_file()
                        for d in src_dirs + inc_dirs if d.is_dir())
            if not found:
                errors.append(f"模块 {info['module']} 流程图 approved 但无代码文件"
                              f"（{info['module']}.c/h）")

    # 3. 顶层产物
    if not any((d / "main.c").is_file() for d in app_src if d.is_dir()):
        errors.append("缺少 App/Src/main.c（不存在时由 S5b 创建）")
    if not any((d / "app.c").is_file() for d in app_src if d.is_dir()):
        errors.append("缺少 App/Src/app.c（APP 主入口：只做初始化汇总与主循环/任务创建）")

    # 4. manifest + traceability（schema + 引用文件存在）
    manifest_path = ctx["outputs_dir"] / "s5b" / "port_interface_manifest.json"
    manifest: dict = {}
    if not manifest_path.is_file():
        errors.append("缺少 outputs/s5b/port_interface_manifest.json（S5c 实现 Port 的唯一依据）")
    else:
        try:
            manifest = analysis.load_json(manifest_path)
            errs = analysis.validate_schema(
                manifest, SKILL_DIR / "schemas" / "port_interface_manifest.schema.json",
                "port_interface_manifest")
            errors.extend(errs)
            for h in manifest.get("headers", []):
                if not (ws / h["file"]).is_file():
                    errors.append(f"manifest 引用的头文件不存在: {h['file']}")
            if ctx["rtos"] != "none" \
                    and not any(h.get("kind") == "osal" for h in manifest.get("headers", [])):
                errors.append("启用 RTOS，manifest 须包含 osal.h 条目（含 flat 架构——OSAL 与 Port 层正交）")
            if ctx["power_enabled"] and ctx["architecture"] != "flat" \
                    and not any(h.get("kind") == "power" for h in manifest.get("headers", [])):
                errors.append("启用低功耗且非 flat 架构，manifest 须包含 power_port.h 条目")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"port_interface_manifest.json 解析失败: {exc}")

    trace_path = ctx["outputs_dir"] / "s5b" / "traceability.json"
    if not trace_path.is_file():
        errors.append("缺少 outputs/s5b/traceability.json（需求 → 文件 → 函数追踪矩阵）")
    else:
        try:
            trace = analysis.load_json(trace_path)
            errors.extend(analysis.validate_schema(
                trace, SKILL_DIR / "schemas" / "traceability.schema.json", "traceability"))
            for item in trace.get("items", []):
                for f in item.get("files", []):
                    if not (ws / f).is_file():
                        errors.append(f"traceability 引用的文件不存在: {f}")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"traceability.json 解析失败: {exc}")

    gap_path = ctx["outputs_dir"] / "s5b" / "capability_gap.json"
    if gap_path.is_file():
        try:
            gap = analysis.load_json(gap_path)
            errors.extend(analysis.validate_schema(
                gap, SKILL_DIR / "schemas" / "capability_gap.schema.json", "capability_gap"))
            if any(g.get("severity") == "error" for g in gap.get("gaps", [])):
                errors.append("capability_gap 存在 error 级缺口（需求无法满足），"
                              "须先与用户确认降级方案或调整需求")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"capability_gap.json 解析失败: {exc}")

    # 5. 禁止 include（全部 S5b 产物源/头文件）
    product_files: list[Path] = []
    for d in src_dirs:
        if d.is_dir():
            product_files.extend(sorted(d.glob("*.c")))
    for d in inc_dirs:
        if d.is_dir():
            product_files.extend(sorted(d.glob("*.h")))
    driver_files = [f for f in product_files if f.name.startswith("driver_")]
    app_files = [f for f in product_files
                 if analysis.classify_rel_path(str(f)) == "app"]
    port_files = [f for f in product_files
                  if analysis.classify_rel_path(str(f)) == "port"]
    errors.extend(check_forbidden_includes(
        app_files + driver_files + port_files, ws, ctx["architecture"]))

    # 6. mtime 守卫：本轮 full/incremental 模块代码须晚于任务书
    brief = ctx["outputs_dir"] / "s5b" / "generation_brief.md"
    if brief.is_file():
        brief_ts = brief.stat().st_mtime - 1.0
        diffs_dir = ctx["outputs_dir"] / "s5b" / "flow_diffs"
        if diffs_dir.is_dir():
            for diff_file in sorted(diffs_dir.glob("*_diff.json")):
                try:
                    diff = analysis.load_json(diff_file)
                except (json.JSONDecodeError, OSError):
                    continue
                if diff.get("generation_mode") not in ("full", "incremental"):
                    continue
                module = diff.get("module", "")
                for d in src_dirs + inc_dirs:
                    if not d.is_dir():
                        continue
                    for f in (d / f"{module}.c", d / f"{module}.h"):
                        if f.is_file() and f.stat().st_mtime < brief_ts:
                            errors.append(
                                f"mtime 守卫：模块 {module} 代码未在本轮任务书后更新"
                                f"（{f.name} 为旧时间戳），flow_diff 判定 "
                                f"{diff['generation_mode']}，请完成 Agent 段后再运行 validate")
    return errors


def _flow_hash(ctx: dict, module: str) -> str | None:
    """从 docs/flow/ 读取模块流程图正文 hash（index 一致性检查用）。"""
    for item in analysis.scan_flow_dir(ctx["flow_dir"]):
        if item["module"] == module:
            _meta, body = analysis.parse_front_matter(item["path"].read_text(encoding="utf-8-sig"))
            return analysis.content_hash(body)
    return None


def collect_state_fields(ctx: dict, src_dirs: list[Path], inc_dirs: list[Path],
                         app_src: list[Path], app_inc: list[Path],
                         drv_src: list[Path], drv_inc: list[Path],
                         port_inc: list[Path]) -> dict:
    """从实际产物收集 state.s5b 字段（指针 + 清单，不存数据本体）。"""
    ws = ctx["workspace"]

    def _rel(p: Path) -> str:
        return str(p.resolve().relative_to(ws)).replace("\\", "/")

    def _glob_rel(dirs: list[Path], pattern: str) -> list[str]:
        return sorted(_rel(p) for d in dirs if d.is_dir() for p in d.glob(pattern))

    app_sources_all = _glob_rel(app_src, "*.c")
    main_source = next((s for s in app_sources_all if s.endswith("/main.c")
                        or s == "main.c"), "")
    protocol_sources = [s for s in app_sources_all if Path(s).name.startswith("protocol_")]
    task_sources = [s for s in app_sources_all if s.endswith("_task.c")]
    app_sources = [s for s in app_sources_all
                   if s not in protocol_sources and s not in task_sources
                   and Path(s).name.startswith("app")]
    port_headers = _glob_rel(port_inc, "*.h")
    osal_header = next((h for h in port_headers if Path(h).name == "osal.h"), None)
    power_header = next((h for h in port_headers if Path(h).name == "power_port.h"), None)

    flows = []
    for item in analysis.scan_flow_dir(ctx["flow_dir"]):
        meta, _body = analysis.parse_front_matter(item["path"].read_text(encoding="utf-8-sig"))
        flows.append({"file": analysis.flow_rel_path(ctx["flow_dir"], item["path"]),
                      "module": item["module"],
                      "version": (meta or {}).get("version"),
                      "status": (meta or {}).get("status") or "draft"})

    flow_diffs: dict[str, str] = {}
    diffs_dir = ctx["outputs_dir"] / "s5b" / "flow_diffs"
    if diffs_dir.is_dir():
        for diff_file in sorted(diffs_dir.glob("*_diff.json")):
            try:
                diff = analysis.load_json(diff_file)
                flow_diffs[diff["module"]] = diff["generation_mode"]
            except (json.JSONDecodeError, OSError):
                continue

    gap_path = ctx["outputs_dir"] / "s5b" / "capability_gap.json"
    return {
        "port_headers": port_headers,
        "osal_header": osal_header,
        "power_header": power_header,
        "app_sources": app_sources,
        "app_headers": _glob_rel(app_inc, "*.h"),
        "app_task_sources": task_sources,
        "protocol_sources": protocol_sources,
        "driver_sources": _glob_rel(drv_src, "driver_*.c"),
        "driver_headers": _glob_rel(drv_inc, "driver_*.h"),
        "main_source": main_source,
        "flows": flows,
        "flow_diffs": flow_diffs,
        "capability_gap": "outputs/s5b/capability_gap.json" if gap_path.is_file() else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5b validate: 产物终验 + IDE 清单 + state 收口")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    try:
        _cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        _cfg = None
    target_ws = analysis.resolve_target(_cfg, workspace)

    def _env_error(error: str) -> int:
        state_path = target_ws / "state.json"
        payload = {"status": "error", "error": error,
                   "updated_at": datetime.now().isoformat(timespec="seconds")}
        try:
            state_store.update_state(state_path, {"s5b": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
        _log(error)
        print(json.dumps({"s5b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 布局解析（与 prepare 同规则）----
    try:
        _state_for_plan = None
        _sp = target_ws / "state.json"
        if _sp.is_file():
            try:
                _state_for_plan = analysis.load_json(_sp)
            except (json.JSONDecodeError, OSError):
                _state_for_plan = None
        plan = layout_resolver.resolve_layout(workspace, _cfg or {}, _state_for_plan)
        all_src = [target_ws / d for d in plan["skill_dirs"]["s5b"]["src"]]
        all_inc = [target_ws / d for d in plan["skill_dirs"]["s5b"]["inc"]]
        if not all_src or not all_inc:
            raise layout_resolver.LayoutError(
                "布局中未解析到 S5b 产物目录（PROJECT_LAYOUT.md 目录树需有带 "
                "S5b 注释的 Src/Inc 目录）")
    except layout_resolver.LayoutError as exc:
        return _env_error(f"布局解析失败: {exc}")

    def _pick(dirs: list[Path], role: str) -> list[Path]:
        return [d for d in dirs if analysis.classify_rel_path(str(d.relative_to(target_ws))) == role]

    app_src = _pick(all_src, "app")
    app_inc = _pick(all_inc, "app")
    drv_src = _pick(all_src, "driver")
    drv_inc = _pick(all_inc, "driver")
    port_inc = _pick(all_inc, "port")

    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return _env_error(str(exc))

    # ---- 1. 产物校验（失败保持 running，Agent 修复后重跑）----
    errors = check_products(ctx, all_src, all_inc, app_src, app_inc)
    if errors:
        _log("产物校验失败（state 保持 running，修复后重跑 validate.py）:")
        for e in errors:
            _log(f"  - {e}")
        print(json.dumps({"s5b": {"status": "running", "errors": errors}},
                         ensure_ascii=False, indent=2))
        return EXIT_PRODUCT_INVALID
    _log("产物校验通过")

    # ---- 2. IDE 待添加清单（兜底参考；实际同步由公共工具 ide_sync.py 完成）----
    groups: dict[str, list[str]] = {}
    ws = ctx["workspace"]
    for dirs, name in ((app_src, "App"), (drv_src, "Drivers/BSP")):
        files = sorted(str(p.resolve().relative_to(ws)).replace("\\", "/")
                       for d in dirs if d.is_dir() for p in d.glob("*.c"))
        if files:
            groups[name] = files
    ide_pending_exporter.export(
        groups, ctx["outputs_dir"],
        include_paths=sorted(str(d.resolve().relative_to(ws)).replace("\\", "/")
                             for d in app_inc + drv_inc + port_inc if d.is_dir()))
    _log("已输出 IDE 待添加清单 outputs/s5b/ide_pending_files.json")

    # ---- 3. state.s5b = done ----
    fields = collect_state_fields(ctx, all_src, all_inc, app_src, app_inc,
                                  drv_src, drv_inc, port_inc)
    payload = {
        "status": "done",
        "rtos": ctx["rtos"],
        "architecture": ctx["architecture"],
        "power_enabled": ctx["power_enabled"],
        "port_manifest": "outputs/s5b/port_interface_manifest.json",
        "osal_header": fields["osal_header"],
        "power_header": fields["power_header"],
        "generation_brief": "outputs/s5b/generation_brief.md",
        "incremental": True,  # 完成 validate 后即为已生成轮次（下轮 prepare 重新判定）
        "traceability": "outputs/s5b/traceability.json",
        "capability_gap": fields["capability_gap"],
        "ide_pending_files": "outputs/s5b/ide_pending_files.json",
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    payload.update(fields)
    state_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5b")
    if state_errors:
        return _env_error("s5b 状态契约校验失败: " + "; ".join(state_errors))
    state_store.update_state(ctx["state_path"], {"s5b": payload})

    # ---- 4. IDE 工程同步（公共工具，失败不中断）----
    try:
        import ide_sync  # noqa: E402（_shared/scripts 已在 sys.path）
        ide_result = ide_sync.sync_project(project_root=workspace, target=target_ws.name,
                                           quiet=True)
        _log("IDE 同步: " + json.dumps(
            {k: ide_result.get(k) for k in
             ("status", "added_count", "removed_count", "manual_path")},
            ensure_ascii=False))
    except Exception as exc:  # 公共工具任何异常不影响 S5b 产物
        _log(f"IDE 同步异常（不影响 S5b 产物，可手动执行 ide_sync.py）: {exc}")

    _log(f"完成: APP {len(payload['app_sources'])} 源文件, "
         f"驱动 {len(payload['driver_sources'])}, "
         f"Port 头 {len(payload['port_headers'])}, 流程图 {len(payload['flows'])} 张")
    print(json.dumps({"s5b": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
