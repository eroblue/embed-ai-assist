#!/usr/bin/env python
"""S5a hardware-initializer 第 3 段：validate（rule 轨）。

三段式执行模型的确定性校验段：
  1. [rule]  prepare.py   → outputs/s5a/generation_brief.md，state.s5a = running
  2. [agent] Agent 生成    → S5a 产物目录（PROJECT_LAYOUT.md 解析，
                            如 Drivers/BSP/{Src,Inc}）的 *.c/h
  3. [rule]  validate.py  → 本脚本

校验内容：必需模块齐全（.c/.h 成对）、总入口汇总调用齐全、
外设实例覆盖、禁止 include 检查；通过后聚合 hardware_capabilities.json
（schema 校验）、输出 IDE 待添加清单、调用公共工具 ide_sync.py 同步
IDE 工程（谁跑完谁同步，失败不中断）、写 state.s5a = done。

产物目录不硬编码：与 prepare 同规则按 PROJECT_LAYOUT.md 解析
（layout_resolver），改布局文档即全局生效。
产物校验失败 → 打印失败项并以退出码 1 结束（state 保持 running，
Agent 修复代码后重跑本脚本）；环境/契约失败 → 写 error 状态。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+（如 Path.write_text(newline=)）
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
import capability_extractor  # noqa: E402
import ide_pending_exporter  # noqa: E402
import layout_resolver  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_PRODUCT_INVALID = 1
EXIT_FAILED = 2
EXIT_CONFIG_ERROR = 3

# 禁止 include 的头文件前缀（app/driver=业务层，port/osal=S5b/S5c 职责）
_FORBIDDEN_INCLUDE = re.compile(r'#\s*include\s+"(app\.h|driver_[\w]*|port_[\w]*|osal_[\w]*)"', re.I)


def _log(msg: str) -> None:
    print(f"[s5a-validate] {msg}", file=sys.stderr)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def expected_modules(usage: dict, rtos: str, power_enabled: bool) -> list[str]:
    mods = ["clock_init", "nvic_init"]
    if usage.get("gpio") or usage.get("fsmc"):
        mods.append("gpio_init")
    for key in ("uart", "spi", "i2c", "adc", "pwm", "fsmc"):
        if usage.get(key):
            mods.append(f"{key}_init")
    if rtos != "none":
        mods.append("rtos_hw_init")
    if power_enabled:
        mods.append("power_init")
    return sorted(set(mods))


def _find_file(dirs: list[Path], name: str) -> Path | None:
    """在多个候选目录中查找文件，返回第一个命中。"""
    for d in dirs:
        p = d / name
        if p.is_file():
            return p
    return None


def check_products(src_dirs: list[Path], inc_dirs: list[Path], usage: dict,
                   rtos: str, power_enabled: bool,
                   architecture: str) -> list[str]:
    """校验 Agent 生成的 S5a 产物（src_dirs=.c 目录集，inc_dirs=.h 目录集）。"""
    errors: list[str] = []
    dirs_hint = ", ".join(str(d.name) + "/" for d in src_dirs + inc_dirs)
    if not any(d.is_dir() for d in src_dirs + inc_dirs):
        return [f"S5a 产物目录不存在（{dirs_hint}，Agent 尚未生成代码）"]

    mods = expected_modules(usage, rtos, power_enabled)
    entry = "board_init" if architecture == "flat" else "hal_init"
    for mod in mods:
        if _find_file(src_dirs, f"{mod}.c") is None:
            errors.append(f"缺少 {mod}.c")
        if _find_file(inc_dirs, f"{mod}.h") is None:
            errors.append(f"缺少 {mod}.h")

    entry_c = _find_file(src_dirs, f"{entry}.c")
    if entry_c is None:
        errors.append(f"缺少总入口 {entry}.c")
    else:
        text = _read(entry_c)
        for mod in mods:
            if f'#include "{mod}.h"' not in text:
                errors.append(f"{entry}.c 缺少 #include \"{mod}.h\"")
            if not re.search(rf"\b{re.escape(mod)}\s*\(", text):
                errors.append(f"{entry}.c 缺少 {mod}() 调用")

    # 外设实例覆盖：usage 中的实例须出现在对应模块文件里
    for key in ("uart", "spi", "i2c", "adc", "pwm"):
        if not usage.get(key):
            continue
        module_c = _find_file(src_dirs, f"{key}_init.c")
        if module_c is None:
            continue
        text = _read(module_c)
        for entry_item in usage[key]:
            inst = entry_item["instance"]
            if inst not in text:
                errors.append(f"{key}_init.c 未覆盖实例 {inst}")

    # 禁止 include / 越界产物
    for d in src_dirs + inc_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.[ch]")):
            m = _FORBIDDEN_INCLUDE.search(_read(f))
            if m:
                errors.append(f"{f.name} 包含禁止头文件: {m.group(1)}")

    return errors


def check_changed_freshness(src_dirs: list[Path], inc_dirs: list[Path],
                            outputs_dir: Path, state: dict) -> list[str]:
    """mtime 守卫：prepare 标记的 CHANGED 模块须在本轮任务书之后被更新过。

    防止 prepare 与 validate 直连（Agent 段被跳过）时，
    未重写的旧文件通过结构校验产生假 done。
    参照时间轴为 generation_brief.md 的写入时间（prepare 段产物，
    不受中途 state 写入影响，假 done 后重跑 validate 仍可拦截）；
    预留 1s 容忍文件系统时间戳精度；changed_modules 为空（无变更）时不检查。
    """
    prev = state.get("s5a") or {}
    changed = prev.get("changed_modules") if isinstance(prev, dict) else None
    if not changed:
        return []
    brief = outputs_dir / "s5a" / "generation_brief.md"
    if not brief.is_file():
        return []
    brief_ts = brief.stat().st_mtime - 1.0
    errors: list[str] = []
    for module in changed:
        stale = [f.name for f in
                 [_find_file(src_dirs, f"{module}.c"),
                  _find_file(inc_dirs, f"{module}.h")]
                 if f is not None and f.stat().st_mtime < brief_ts]
        if stale:
            errors.append(
                f"mtime 守卫：模块 {module} 未在本轮任务书后更新"
                f"（{', '.join(stale)} 仍为旧时间戳），prepare 标记其为 CHANGED，"
                f"请完成 Agent 段重写后再运行 validate")
    return errors


def make_state_payload(status: str, rtos: str, architecture: str, power_enabled: bool,
                       src_dirs: list[Path], inc_dirs: list[Path], workspace: Path,
                       capabilities_rel: str, ide_pending_files: str | None,
                       error: str | None) -> dict:
    def _glob_all(dirs: list[Path], pattern: str) -> list[Path]:
        out: list[Path] = []
        for d in dirs:
            if d.is_dir():
                out.extend(d.glob(pattern))
        return out

    sources = sorted(str(p.relative_to(workspace)).replace("\\", "/")
                     for p in _glob_all(src_dirs, "*.c"))
    headers = sorted(str(p.relative_to(workspace)).replace("\\", "/")
                     for p in _glob_all(inc_dirs, "*.h"))
    entry_name = "board_init" if architecture == "flat" else "hal_init"
    entry_src = next((s for s in sources if entry_name in s), None)
    entry_hdr = next((h for h in headers if entry_name in h), None)
    return {
        "status": status,
        "rtos": rtos,
        "architecture": architecture,
        "power_enabled": power_enabled,
        "init_sources": sources,
        "init_headers": headers,
        "entry_source": entry_src or "",
        "entry_header": entry_hdr or "",
        "rtos_hw_init": next((s for s in sources if "rtos_hw_init" in s), None) if rtos != "none" else None,
        "power_init": next((s for s in sources if "power_init" in s), None) if power_enabled else None,
        "hardware_capabilities": capabilities_rel or "",
        "ide_pending_files": ide_pending_files,
        "error": error,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5a validate: 校验 Agent 产物 + 聚合能力清单 + IDE 清单")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    # 目标工程根（App/BootLoader 双工程）：state/src/outputs 归目标工程
    # （load_context 同规则；config 损坏时按 App 兜底）
    try:
        _cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        _cfg = None
    target_ws = analysis.resolve_target(_cfg, workspace)
    # S5a 产物目录（PROJECT_LAYOUT.md 解析，与 prepare 同规则；改布局即全局生效）
    try:
        _state_for_plan = None
        _sp = target_ws / "state.json"
        if _sp.is_file():
            try:
                _state_for_plan = analysis.load_json(_sp)
            except (json.JSONDecodeError, OSError):
                _state_for_plan = None
        plan = layout_resolver.resolve_layout(workspace, _cfg or {}, _state_for_plan)
        src_dirs = [target_ws / d for d in plan["skill_dirs"]["s5a"]["src"]]
        inc_dirs = [target_ws / d for d in plan["skill_dirs"]["s5a"]["inc"]]
        if not src_dirs or not inc_dirs:
            raise layout_resolver.LayoutError(
                "布局中未解析到 S5a 产物目录（PROJECT_LAYOUT.md 目录树需有带 "
                "S5a 注释的 Src/Inc 目录）")
    except layout_resolver.LayoutError as exc:
        src_dirs, inc_dirs = [], []  # 由 _env_error 收尾
        _layout_error = f"布局解析失败: {exc}"
    else:
        _layout_error = None

    def _env_error(error: str) -> int:
        state_path = target_ws / "state.json"
        payload = make_state_payload("error", "none", "layered", False,
                                     src_dirs, inc_dirs, target_ws, "", None, error)
        try:
            state_store.update_state(state_path, {"s5a": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
        _log(error)
        print(json.dumps({"s5a": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    if _layout_error:
        return _env_error(_layout_error)

    try:
        ctx = analysis.load_context(config_path, workspace)
        usage, clock_cfg, hse_hz, lse_hz, _design_input = analysis.run_usage_analysis(ctx)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return _env_error(str(exc))

    # ---- 1. 产物校验（失败保持 running，Agent 修复后重跑）----
    errors = check_products(src_dirs, inc_dirs, usage, ctx["rtos"],
                            ctx["power_enabled"], ctx["architecture"])
    errors.extend(check_changed_freshness(src_dirs, inc_dirs,
                                          ctx["outputs_dir"], ctx["state"]))
    if errors:
        _log("产物校验失败（state 保持 running，修复后重跑 validate.py）:")
        for e in errors:
            _log(f"  - {e}")
        print(json.dumps({"s5a": {"status": "running", "errors": errors}}, ensure_ascii=False, indent=2))
        return EXIT_PRODUCT_INVALID
    _log(f"产物校验通过: {sum(1 for d in src_dirs if d.is_dir() for _ in d.glob('*.c'))} 个源文件")

    # ---- 2. 硬件能力清单 ----
    mcu = ctx["facts"].get("mcu") or ctx["platform_name"]
    caps = capability_extractor.extract(
        mcu, ctx["platform_name"], ctx["architecture"], ctx["rtos"], ctx["power_enabled"],
        clock_cfg, usage, hse_hz, lse_hz)
    cap_errors = analysis.validate_schema(
        caps, SKILL_DIR / "schemas" / "hardware_capabilities.schema.json", "capabilities")
    if cap_errors:
        return _env_error("hardware_capabilities 校验失败: " + "; ".join(cap_errors))
    analysis.save_json(ctx["outputs_dir"] / "s5a" / "hardware_capabilities.json", caps)

    # ---- 3. IDE 待添加清单（兜底参考；实际同步由公共工具 ide_sync.py 完成）----
    src_rel_base = plan["skill_dirs"]["s5a"]["src"][0]
    sources_rel = sorted(f"{src_rel_base}/{p.name}"
                         for d in src_dirs if d.is_dir() for p in d.glob("*.c"))
    pending_group = src_rel_base.rsplit("/", 1)[0] if "/" in src_rel_base else src_rel_base
    ide_pending_exporter.export(sources_rel, ctx["outputs_dir"],
                                group=pending_group,
                                include_paths=plan["skill_dirs"]["s5a"]["inc"])
    _log("已输出 IDE 待添加清单 outputs/s5a/ide_pending_files.json")

    # ---- 4. state.s5a = done ----
    payload = make_state_payload("done", ctx["rtos"], ctx["architecture"], ctx["power_enabled"],
                                 src_dirs, inc_dirs, target_ws,
                                 "outputs/s5a/hardware_capabilities.json",
                                 "outputs/s5a/ide_pending_files.json", None)
    prev_s5a = ctx["state"].get("s5a") or {}  # 继承 prepare 写入的增量轮次信息
    if isinstance(prev_s5a, dict):
        for key in ("incremental", "changed_modules"):
            if key in prev_s5a:
                payload[key] = prev_s5a[key]
    state_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5a")
    if state_errors:
        return _env_error("s5a 状态契约校验失败: " + "; ".join(state_errors))
    state_store.update_state(ctx["state_path"], {"s5a": payload})

    # ---- 5. IDE 工程同步（公共工具 skills/_shared/scripts/ide_sync.py，失败不中断）----
    try:
        import ide_sync  # noqa: E402（_shared/scripts 已在 sys.path）
        ide_result = ide_sync.sync_project(
            project_root=workspace, target=target_ws.name, quiet=True)
        _log("IDE 同步: " + json.dumps(
            {k: ide_result.get(k) for k in
             ("status", "added_count", "removed_count", "manual_path")},
            ensure_ascii=False))
    except Exception as exc:  # 公共工具任何异常不影响 S5a 产物
        _log(f"IDE 同步异常（不影响 S5a 产物，可手动执行 ide_sync.py）: {exc}")

    _log(f"完成: {len(payload['init_sources'])} 源文件, 外设能力 {len(caps['peripherals'])} 项")
    print(json.dumps({"s5a": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
