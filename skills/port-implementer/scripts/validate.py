#!/usr/bin/env python
"""S5c port-implementer 第 3 段：validate（rule 轨，终验）。

三段式执行模型的确定性校验段（Agent 完成 Port/OSAL/Power 实现后运行）：
  1. [rule]  prepare.py        → 任务书，state.s5c = running
  2. [agent] Agent 生成代码     → port_impl_<外设>_<平台>.c / osal / power 实现
  3. [rule]  validate.py       → 本脚本

校验内容：manifest 接口全覆盖（每个接口函数在对应实现文件中有定义）、
实现文件存在且 include 对应 Port 头、禁止 include 应用层头（app*/protocol_*/
driver_*，向上依赖）、ISR 回调调用点前置判空抽查、mtime 守卫（本轮生成文件
须晚于任务书，用户跳过文件豁免）；通过后记录文件哈希（skip-if-modified
依据，用户手改文件保留旧基线）、调用公共工具 ide_sync.py 同步 IDE 工程
（失败不中断）、写 state.s5c = done。

退出码：0 成功（含 flat skipped）；1 产物校验失败（state 保持 running，
Agent 修复后重跑）；2 环境/契约失败（state 写 error）。
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
import layout_resolver  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_PRODUCT_INVALID = 1
EXIT_CONFIG_ERROR = 2

# ---- 禁止 include：Port 实现是适配层，禁止向上依赖 APP/Driver 层 ----
# （HAL/RTOS 头在本层是允许的——这正是 Adapter 的职责；与 S5b 的黑名单方向相反）
_FORBIDDEN_UPWARD = re.compile(
    r'#\s*include\s*[<"](?:app[\w]*\.h|protocol_\w+\.h|driver_\w+\.h)[>"]', re.I)

# ---- C 注释剥离（接口定义检查用）----
_C_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.S)


def _log(msg: str) -> None:
    print(f"[s5c-validate] {msg}", file=sys.stderr)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_comments(text: str) -> str:
    return _C_COMMENT.sub("", text)


def check_isr_callback_guards(files: list[Path]) -> list[str]:
    """ISR 回调判空抽查（requirement 阶段 C 步骤 17）。

    识别形如 `x->cb(...)` / `x.cb(...)` 的函数指针调用点，要求其上方 8 行
    （含本行）内存在引用同一回调成员的判空保护——支持常见写法：
    `if (ctx->cb != NULL)` / `if (!ctx->cb) return;` / `if (ctx->cb)`。
    未发现保护即报错（实现规范见 references/isr_safety_rules.md）。
    """
    errors: list[str] = []
    call_re = re.compile(
        r"\b([A-Za-z_]\w*(?:->|\.)\s*([A-Za-z_]\w*(?:cb|Cb|CB|callback|Callback)\w*))\s*\(")
    for f in files:
        rel = f.name
        lines = _read(f).splitlines()
        stripped = [_strip_comments(ln) for ln in lines]
        for idx, ln in enumerate(stripped):
            for m in call_re.finditer(ln):
                member = m.group(2)
                guard = re.compile(
                    rf"\bif\s*\(\s*!?\s*[\w.\]\[\->]*\b{re.escape(member)}\b"
                    rf"|[^;]\b{re.escape(member)}\b[^;\n]*?(?:!=\s*(?:NULL|0)\b|==\s*NULL\b)")
                window = "\n".join(stripped[max(0, idx - 8):idx + 1])
                if not guard.search(window):
                    errors.append(
                        f"{rel}: 回调调用点 '{m.group(1)}(...)' 前置 8 行内未发现判空保护"
                        "——ISR 内调用回调前必须判断函数指针非 NULL（未注册时清除中断标志直接返回）")
    return errors


def check_products(ctx: dict, src_paths: list[Path]) -> tuple[list[str], dict]:
    """产物校验。返回 (errors, collected)：collected 供 state 收口。"""
    errors: list[str] = []
    ws = ctx["workspace"]
    platform_token, rtos = ctx["platform_token"], ctx["rtos"]
    manifest = ctx["manifest"]

    # ---- 0. 用户修改检测（豁免 mtime 守卫；哈希保留旧基线）----
    # 判定时机修正：prepare 之后被修改的 current 文件是本轮 Agent 的正常产出
    # （mtime ≥ 任务书），不得误判为用户手改——否则哈希不更新、下轮 prepare
    # 会把该文件永久当作"用户手改"跳过重写。只有"任务书生成之前就与上轮记录
    # 不一致"的 current 文件才是真正的用户手改（prepare 已在任务书中标注）。
    recorded = analysis.load_file_hashes(ctx["outputs_dir"] / "s5c")
    impl_scan = analysis.scan_impl_files(ws, src_paths, platform_token, rtos, recorded)
    brief = ctx["outputs_dir"] / "s5c" / "generation_brief.md"
    brief_ts = brief.stat().st_mtime - 1.0 if brief.is_file() else None
    current_set = set(impl_scan["current"])
    skipped = [rel for rel in impl_scan["user_modified"]
               if brief_ts is not None and rel in current_set
               and (ws / rel).stat().st_mtime < brief_ts]

    # ---- 1. 期望文件存在 + 接口全覆盖 ----
    by_periph: dict[str, list[Path]] = {}
    for h in analysis.manifest_peripheral_headers(manifest):
        periph = analysis.slug_token(h.get("peripheral") or "")
        name = analysis.impl_file_name(periph, platform_token)
        path = next((p for p in src_paths if p.is_dir() and (p / name).is_file()), None)
        impl = path / name if path else None
        if impl is None:
            errors.append(f"缺少 Port 实现文件: {name}（manifest 外设 {periph}，"
                          f"落点 {'/'.join(str(d.relative_to(ws)) for d in src_paths)}）")
            continue
        by_periph[periph] = [impl]
        text = _strip_comments(_read(impl))
        for fn in [i.get("function") for i in h.get("interfaces", []) if i.get("function")]:
            if not re.search(rf"\b{re.escape(fn)}\s*\(", text):
                errors.append(f"{impl.name}: manifest 接口 `{fn}` 未实现"
                              f"（外设 {periph} 的全部接口须在对应实现文件中定义）")
        # 实现文件须 include 对应 Port 头（S5b 接口头）
        port_header = Path(h.get("file") or "").name
        if port_header and f'"{port_header}"' not in _read(impl) \
                and f"<{port_header}>" not in _read(impl):
            errors.append(f"{impl.name}: 未 include 对应 Port 头 {port_header}"
                          "（实现文件必须 include S5b 的接口头）")

    # ---- 2. OSAL / Power 实现存在 ----
    osal_impl = None
    if rtos != "none":
        name = analysis.osal_impl_file_name(rtos)
        p = next((d / name for d in src_paths if d.is_dir() and (d / name).is_file()), None)
        if p is None:
            errors.append(f"缺少 OSAL 实现文件: {name}（rtos={rtos}）")
        else:
            osal_impl = str(p.resolve().relative_to(ws)).replace("\\", "/")
    power_impl = None
    if ctx["power_enabled"] and ctx["architecture"] != "flat":
        name = analysis.power_impl_file_name(platform_token)
        p = next((d / name for d in src_paths if d.is_dir() and (d / name).is_file()), None)
        if p is None:
            errors.append(f"缺少 Power 实现文件: {name}（power_enabled=true）")
        else:
            power_impl = str(p.resolve().relative_to(ws)).replace("\\", "/")

    # ---- 3. 禁止 include 应用层头（向上依赖）----
    impl_files: list[Path] = []
    for d in src_paths:
        if d.is_dir():
            impl_files.extend(sorted(d.glob("port_impl_*.c")))
    for f in impl_files:
        rel = str(f.resolve().relative_to(ws)).replace("\\", "/")
        for m in _FORBIDDEN_UPWARD.finditer(_read(f)):
            errors.append(f"{rel}: 禁止 include 应用层头文件（{m.group(0).strip()}）"
                          "——Port 实现是适配层，不得向上依赖 APP/Driver")

    # ---- 4. ISR 回调判空抽查 ----
    errors.extend(check_isr_callback_guards(impl_files))

    # ---- 5. mtime 守卫：本轮生成文件须晚于任务书（用户跳过文件豁免）----
    if brief_ts is not None:
        for f in impl_files:
            rel = str(f.resolve().relative_to(ws)).replace("\\", "/")
            if rel in skipped or rel not in current_set:
                continue
            if recorded.get(rel) == analysis.file_sha256(f):
                continue  # 内容与上轮一致（未重写的现有实现）
            if f.stat().st_mtime < brief_ts:
                errors.append(f"mtime 守卫：{f.name} 未在本轮任务书后更新"
                              "（旧时间戳），请完成 Agent 生成段后再运行 validate")

    # ---- 6. 残留能力缺口报告存在即拦截（正常应已被 prepare 阻断）----
    gap_path = ctx["outputs_dir"] / "s5c" / "capability_gap.json"
    if gap_path.is_file():
        try:
            gap = analysis.load_json(gap_path)
            if any(g.get("severity") == "error" for g in gap.get("gaps", [])):
                errors.append("capability_gap.json 存在 error 级缺口"
                              "（prepare 应已阻断；修复 S5a/S5b 后重跑 prepare）")
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"capability_gap.json 解析失败: {exc}")

    port_impl_sources = []
    for f in impl_files:
        info = analysis.classify_impl_file(f.name, platform_token, rtos)
        if info and info["current"] and info["kind"] == "peripheral":
            port_impl_sources.append(
                str(f.resolve().relative_to(ws)).replace("\\", "/"))
    port_impl_sources.sort()
    collected = {
        "port_impl_sources": port_impl_sources,
        "osal_impl": osal_impl,
        "power_impl": power_impl,
        "skipped_files": skipped,
        "capability_gap": "outputs/s5c/capability_gap.json" if gap_path.is_file() else None,
    }
    return errors, collected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5c validate: 产物校验 + 文件哈希 + IDE 同步 + state 收口")
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
            state_store.update_state(state_path, {"s5c": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
        _log(error)
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        return _env_error(str(exc))

    # ---- 布局解析（与 prepare 同规则）----
    try:
        plan = layout_resolver.resolve_layout(
            ctx["project_root"], ctx["config"], ctx["state"])
    except layout_resolver.LayoutError as exc:
        return _env_error(f"布局解析失败: {exc}")

    # ---- flat：幂等保持 skipped ----
    if ctx["architecture"] == "flat":
        payload = {"status": "skipped", "rtos": ctx["rtos"], "architecture": "flat",
                   "power_enabled": ctx["power_enabled"], "error": None,
                   "updated_at": datetime.now().isoformat(timespec="seconds")}
        state_store.update_state(ctx["state_path"], {"s5c": payload})
        _log("flat 架构：S5c 跳过生成（status=skipped）")
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_OK

    src_paths = [ctx["workspace"] / d for d in plan["skill_dirs"]["s5c"]["src"]]
    if not src_paths:
        return _env_error("布局中未解析到 S5c 产物目录（PROJECT_LAYOUT.md 目录树"
                          "需有带 S5c 注释的 Src 目录）")

    # ---- 1. 产物校验（失败保持 running，Agent 修复后重跑）----
    errors, collected = check_products(ctx, src_paths)
    if errors:
        _log("产物校验失败（state 保持 running，修复后重跑 validate.py）:")
        for e in errors:
            _log(f"  - {e}")
        print(json.dumps({"s5c": {"status": "running", "errors": errors}},
                         ensure_ascii=False, indent=2))
        return EXIT_PRODUCT_INVALID
    _log("产物校验通过")

    # ---- 2. 记录文件哈希（skip-if-modified 依据；用户手改文件保留旧基线）----
    recorded = analysis.load_file_hashes(ctx["outputs_dir"] / "s5c")
    for rel in collected["port_impl_sources"] + \
            [x for x in (collected["osal_impl"], collected["power_impl"]) if x]:
        f = ctx["workspace"] / rel
        if rel in collected["skipped_files"]:
            continue  # 用户改过的文件保留旧基线（下次 prepare 仍判定为已修改）
        recorded[rel] = analysis.file_sha256(f)
    analysis.save_file_hashes(ctx["outputs_dir"] / "s5c", recorded)

    # ---- 3. state.s5c = done ----
    payload = {
        "status": "done",
        "rtos": ctx["rtos"],
        "architecture": ctx["architecture"],
        "power_enabled": ctx["power_enabled"],
        "generation_brief": "outputs/s5c/generation_brief.md",
        "port_impl_sources": collected["port_impl_sources"],
        "osal_impl": collected["osal_impl"],
        "power_impl": collected["power_impl"],
        "skipped_files": collected["skipped_files"],
        "capability_gap": collected["capability_gap"],
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    state_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5c")
    if state_errors:
        return _env_error("s5c 状态契约校验失败: " + "; ".join(state_errors))
    state_store.update_state(ctx["state_path"], {"s5c": payload})

    # ---- 4. IDE 工程同步（公共工具，失败不中断）----
    try:
        import ide_sync  # noqa: E402（_shared/scripts 已在 sys.path）
        ide_result = ide_sync.sync_project(
            project_root=ctx["project_root"], target=ctx["workspace"].name, quiet=True)
        _log("IDE 同步: " + json.dumps(
            {k: ide_result.get(k) for k in
             ("status", "added_count", "removed_count", "manual_path")},
            ensure_ascii=False))
    except Exception as exc:  # 公共工具任何异常不影响 S5c 产物
        _log(f"IDE 同步异常（不影响 S5c 产物，可手动执行 ide_sync.py）: {exc}")

    _log(f"完成: Port 实现 {len(payload['port_impl_sources'])} 个源文件"
         f"（OSAL {'有' if payload['osal_impl'] else '无'}，"
         f"Power {'有' if payload['power_impl'] else '无'}，"
         f"用户跳过 {len(payload['skipped_files'])}）")
    print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
