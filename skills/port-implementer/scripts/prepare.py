#!/usr/bin/env python
"""S5c port-implementer 第 1 段：prepare（rule 轨）。

三段式执行模型（与 S5a/S5b 同策略：rule 只做确定性契约工作，适配代码归 Agent）：
  1. [rule]  prepare.py        → S5a/S5b 就绪检查 + 配置一致性检查（防漂移）
                                 → 能力缺口前置检测（manifest 需求 × capabilities
                                 供给，缺口 → capability_gap.json + 终止）
                                 → flat 判定（跳过生成）
                                 → 旧平台/旧 RTOS 残留清理 + 用户修改检测
                                 → outputs/s5c/generation_brief.md（Agent 任务书）
                                 → state.s5c = running
  2. [agent] Agent 生成代码     → 读任务书 + SKILL.md + references/ + manifest +
                                 capabilities + SDK 头文件（核对 API 名）→
                                 按 manifest 接口逐外设编写 port_impl_*.c
  3. [rule]  validate.py       → 产物校验 + 文件哈希 + IDE 同步 → state = done

本脚本不生成任何 C 代码。产物目录不硬编码：按 PROJECT_LAYOUT.md 解析
（layout_resolver，32 位 layered 典型值 Drivers/Port/Src/）。

退出码：0 成功（含 flat skipped）；2 配置/就绪/一致性/能力缺口失败。
"""

from __future__ import annotations

import argparse
import json
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
import ensure_layout as ensure_layout_mod  # noqa: E402
import layout_resolver  # noqa: E402
import port_differ  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s5c-prepare] {msg}", file=sys.stderr)


def _write_error_state(config_path: Path, workspace: Path, error: str,
                       extra: dict | None = None) -> dict:
    payload = {"status": "error", "error": error,
               "updated_at": datetime.now().isoformat(timespec="seconds")}
    if extra:
        payload.update(extra)
    try:
        cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        cfg = None
    state_path = analysis.resolve_target(cfg, workspace) / "state.json"
    try:
        state_store.update_state(state_path, {"s5c": payload})
    except (OSError, state_store.StateLockTimeout):
        pass
    return payload


def _capabilities_summary_lines(caps: dict) -> list[str]:
    """hardware_capabilities 摘要行（任务书第 3 节）。"""
    lines: list[str] = []
    clocks = caps.get("clocks") or {}
    if clocks:
        lines.append(f"- 时钟：SYSCLK {clocks.get('sysclk_hz')} Hz"
                     f"（{clocks.get('source') or '来源未标注'}）")
    periphs = caps.get("peripherals") or []
    if not periphs:
        lines.append("- **能力清单 peripherals 为空（数据退化）**：S1/S4 网表退化时"
                     "S5a 无法登记外设能力——Agent 需对照 S5a init 产物"
                     "（s5a.init_sources）与用户设计输入自行核对，"
                     "并在文件头注释登记实际对接的硬件实例")
    else:
        lines.append(f"- 外设能力 {len(periphs)} 项：")
        lines.append("  | 类型 | 实例 | 引脚 | 中断 | 能力标签 |")
        lines.append("  |---|---|---|---|---|")
        for p in periphs:
            pins = "，".join(f"{k}={v}" for k, v in (p.get("pins") or {}).items()) or "-"
            lines.append(f"  | {p.get('type')} | {p.get('instance')} | {pins} | "
                          f"{p.get('irq') or '-'} | {';'.join(p.get('capabilities') or []) or '-'} |")
    if caps.get("power"):
        pw = caps["power"]
        lines.append(f"- 低功耗：模式 {pw.get('modes')}；唤醒源 {pw.get('wakeup_sources')}")
    for c in caps.get("constraints") or []:
        lines.append(f"- 约束：{c}")
    return lines


def _manifest_inventory_lines(manifest: dict, platform_token: str, rtos: str) -> list[str]:
    """manifest 接口清单（任务书第 4 节）：逐外设的实例/接口/回调/落点文件。"""
    lines: list[str] = []
    for h in analysis.manifest_peripheral_headers(manifest):
        periph = analysis.slug_token(h.get("peripheral") or "")
        lines.append(f"### {h.get('file')}（外设 {periph}）")
        lines.append("")
        lines.append(f"- 说明：{h.get('description') or '-'}")
        lines.append(f"- **实现落点：`{analysis.impl_file_name(periph, platform_token)}`**"
                     f"（include 对应 Port 头，只实现本外设接口）")
        for inst in h.get("logical_instances", []):
            lines.append(f"- 逻辑实例 `{inst.get('name')}`：{inst.get('description') or '-'}")
            lines.append(f"  - hw_instance：{inst.get('hw_instance') if inst.get('hw_instance') is not None else '**null（Agent 按 capabilities/设计输入选定，并在文件头注释登记）**'}"
                         f"（来源 {inst.get('hw_source') or '-'}）；config：{inst.get('config')}")
        lines.append("- 接口：")
        for i in h.get("interfaces", []):
            isr = "（isr_safe）" if i.get("isr_safe") else ""
            cb = f"（回调经 {i.get('callback')}）" if i.get("callback") else ""
            lines.append(f"  - `{i['function']}`：{i.get('signature')}{isr}{cb}"
                         f" —— {i.get('description') or '-'}")
        for cb in h.get("callbacks", []):
            lines.append(f"- 回调约定：`{cb.get('name')}` = {cb.get('signature')}"
                         f"（上下文 {cb.get('context')}）—— {cb.get('description') or '-'}")
        for n in h.get("notes", []):
            lines.append(f"- 注：{n}")
        lines.append("")
    return lines


def build_brief(ctx: dict, plan: dict, impl_scan: dict, recommendations: list[dict],
                diff_results: list[dict] | None = None,
                snapshot_missing: bool = False) -> str:
    """构建 generation_brief.md（S5c Agent 任务书）。

    diff_results：port_differ 的 per-peripheral 判定结果（None=未执行，兜底全部 full）。
    """
    platform_token = ctx["platform_token"]
    rtos, arch = ctx["rtos"], ctx["architecture"]
    src_dirs = plan["skill_dirs"]["s5c"]["src"]
    lines: list[str] = []
    add = lines.append

    add("# S5c Port 实现任务书（generation_brief）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。Agent 按本任务书实现 Port/OSAL/Power 接口，")
    add("> 操作规范见 `skills/port-implementer/SKILL.md` 与 `references/`。")
    add("> 接口语义（错误码/超时/线程安全）按 S5b 的 `port-contract-and-app/references/port_design_principle.md` 同一约定。")
    add("")

    # ---- 1. 项目信息 ----
    add("## 1. 项目信息")
    add("")
    add(f"- 平台：{ctx['platform']}（文件命名后缀 `{platform_token}`）")
    if ctx["hal_framework"]:
        add(f"- HAL 框架：{ctx['hal_framework']}（定位参考材料用）")
    add(f"- 架构：{arch}；RTOS：{rtos}；低功耗：{'启用' if ctx['power_enabled'] else '未启用'}")
    add(f"- Port 接口头（S5b 产出，只读）：{', '.join(ctx['s5b'].get('port_headers') or []) or '-'}")
    add(f"- S5a 总入口：{ctx['s5a'].get('entry_source')}（init 产物 {len(ctx['s5a'].get('init_sources') or [])} 个源文件，可对接其初始化成果）")
    add(f"- 实现输出目录（PROJECT_LAYOUT.md 解析）：`{src_dirs[0]}/`" if src_dirs
        else "- 实现输出目录：**布局未解析到，禁止生成**")
    for w in ctx["drift_warnings"]:
        add(f"- **漂移警告**：{w}")
    add("")

    # ---- 2. 用户设计输入 ----
    add("## 2. 用户设计输入（docs/s5c_design_input.md，优先级高于自动推断）")
    add("")
    di = ctx["design_input"]
    if di:
        add(f"来源：`{di['path']}`，原文段落：")
        add("")
        for sec, content in di["sections"].items():
            add(f"**{sec}**：")
            for ln in content:
                add(f"> {ln}")
            add("")
        if not ctx["power_enabled"] and "低功耗方案" in di["sections"]:
            add("（注意：低功耗未启用，'低功耗方案' 段本轮不生效）")
            add("")
    else:
        add("- 无（缺失/为空/全部 none）——Agent 基于 hardware_capabilities 与参考材料自主判断")
        for key, label in (("demos", "demo 程序"), ("sdk", "SDK 目录"),
                           ("existing_project", "已有项目")):
            val = ctx["inputs"][key]
            if val:
                add(f"- {label}：`{val}`（学习 API 写法/命名风格）")
        add("")

    # ---- 3. 能力供给 ----
    add("## 3. S5a 能力清单摘要（实现 Port 的唯一硬件依据）")
    add("")
    lines.extend(_capabilities_summary_lines(ctx["capabilities"]))
    add("")

    # ---- 4. manifest 接口清单 ----
    add("## 4. S5b manifest 接口清单（实现 Port 的唯一接口依据）")
    add("")
    lines.extend(_manifest_inventory_lines(ctx["manifest"], platform_token, rtos))
    if rtos != "none":
        osal_h = ctx["s5b"].get("osal_header")
        add(f"### OSAL（{rtos}）")
        add("")
        add(f"- 接口头：{osal_h}（S5b 产出，只读）")
        add(f"- **实现落点：`{analysis.osal_impl_file_name(rtos)}`**"
            "（映射指南 `references/rtos_mapping_guide.md`；ISR 内使用 FromISR 变体）")
        add("")
    if ctx["power_enabled"] and arch != "flat":
        power_h = ctx["s5b"].get("power_header")
        add("### Power（低功耗）")
        add("")
        add(f"- 接口头：{power_h}（S5b 产出，只读）")
        add(f"- **实现落点：`{analysis.power_impl_file_name(platform_token)}`**"
            "（策略以设计输入'低功耗方案'段为准；S5a power_init 见 "
            f"{ctx['s5a'].get('power_init') or '-'}）")
        add("")

    # ---- 5. 生成模式表（per-peripheral 增量判定结果，逐单元处理依据）----
    add("## 5. 生成模式表（逐单元处理依据）")
    add("")
    if snapshot_missing:
        add("- **首次执行（无 `port_manifest_snapshot.json`）**：全部单元按 `full` "
            "建立基线，不跳过任何文件；validate 成功后写入第一份快照。")
        add("")
    if not diff_results:
        add("- 无判定结果（manifest 无实现单元？）")
        add("")
    else:
        add("| 单元 | 类型 | 模式 | 实现文件 | 原因 | 用户手改 | 接口变化 |")
        add("|---|---|---|---|---|---|---|")
        for r in diff_results:
            fname = analysis.manifest_unit_file(
                r["peripheral"], r["kind"], platform_token, rtos)
            fdisp = r["file"] or f"{fname}（待生成）"
            sig = (f"{r['change_count']} 处（{r['change_rate']:.0%}）"
                   if r["signature_changed"] else "无变化")
            add(f"| {r['peripheral']} | {r['kind']} | **{r['generation_mode']}** | "
                f"{fdisp} | {r['reason']} | "
                f"{'是' if r['file_hash_changed'] else '否'} | {sig} |")
        add("")
        add("**处置规则**：`full`=全量重生成该文件；`incremental`=**只做定点修改**"
            "（见 `references/incremental_generation_rules.md`，无权整文件重写）；"
            "`skip`=**绝对不动该文件**（含用户手改与接口未变两类）；"
            "`blocked`=**报告用户**（手改 + 上游变更冲突，不自行处理）；"
            "`deprecated`=移除该实现文件（IDE 引用由 ide_sync 收口）。")
        add("")
        blocked = [r for r in diff_results if r["generation_mode"] == "blocked"]
        if blocked:
            add("### ⚠️ blocked——必须报告用户（不得自行处理）")
            add("")
            for r in blocked:
                add(f"- `{r['peripheral']}`（{r['file'] or '文件缺失'}）：{r['reason']}")
            add("")
        deprecated = [r for r in diff_results if r["generation_mode"] == "deprecated"]
        if deprecated:
            add("### deprecated——移除对应实现文件")
            add("")
            for r in deprecated:
                add(f"- `{r['peripheral']}`：{r['reason']}")
            add("")
        drifted = [r for r in diff_results if r.get("drift_warning")]
        if drifted:
            add("### ⚠️ 用户修改文件清单（跳过重写——接口漂移风险）")
            add("")
            for r in drifted:
                add(f"- `{r['file']}`：{r['drift_warning']}")
            add("")
        if any(r.get("design_input_changed") for r in diff_results):
            add("### ⚠️ 设计输入已变化（需确认受影响单元）")
            add("")
            add("`docs/s5c_design_input.md` 相对上轮快照已变化（**第三判定维度**）。"
                "设计输入变化**不自动触发重生成**——请按第 2 节原文核对哪些实现单元的"
                "约束受影响（如缓冲大小/命名风格/低功耗策略），确认后二选一："
                "删除受影响实现文件（下轮判 `full`）或走 `code-fix` 定点修改。")
            add("")
    if impl_scan["user_modified"]:
        add("### 用户修改检测（skip-if-modified）")
        add("")
        for rel in impl_scan["user_modified"]:
            add(f"- `{rel}`：文件哈希与上轮基线不一致（用户改过）——"
                "按上表模式处置（接口未变=skip 保留手改；接口变化=blocked 报告用户）")
        add("")

    # ---- 6. 映射要点与规范引用 ----
    add("## 6. 映射要点与规范引用")
    add("")
    add("- HAL API ↔ Port 接口：`references/hal_mapping_guide.md`"
        "（**核对将要用到的 API 函数名/枚举名/时钟使能宏，不确定的留 `/* TODO: */` 注释，不臆造 API**）")
    if rtos != "none":
        add("- RTOS API ↔ OSAL 接口：`references/rtos_mapping_guide.md`")
    add("- 实现模式（状态管理/环形缓冲/错误码映射/DMA 骨架）：`references/port_impl_pattern.md`")
    add("- 中断安全规范（**ISR 内回调调用前必须判空**）：`references/isr_safety_rules.md`")
    add("- 实现示例：`assets/port_impl_example.c`")
    add("- S5a init 产物清单（对接其初始化成果，不重复 HAL 初始化）：")
    for f in ctx["s5a"].get("init_headers") or []:
        add(f"  - `{f}`")
    add("")

    # ---- 7. 禁止事项 ----
    add("## 7. 禁止事项（硬约束）")
    add("")
    add("- 不修改 S5a/S5b 产出的任何文件（含 `*_port.h` / `osal.h` / `power_port.h` 接口定义）")
    add("- 不写任何应用业务逻辑；不生成 HAL 初始化代码（S5a 职责，Port 实现只做绑定与读写操作）")
    add("- 必须依据 manifest 数据侧实现，不得硬解析 C 头文件；硬件只依据 hardware_capabilities"
        "（及设计输入/S5a init 产物核对），禁止直接读取 S3/S4 数据")
    add("- 不得把所有 Port 实现塞进一个文件（按外设拆分）；代码只写入任务书给定的产物目录")
    add("- ISR 内调用回调前必须判断函数指针非 NULL（未注册时清标志直接返回）；DMA 隐藏在 Port 实现内")
    add("- 实例状态用文件内 static 数组按 instance id 索引，不动态分配")
    add("- **不重写'用户已修改'清单中的文件**（skip-if-modified）")
    add("")

    # ---- 8. 执行步骤 ----
    add("## 8. 执行步骤（详见 SKILL.md）")
    add("")
    add("1. 通读 SKILL.md 与上述 references/；读 SDK 头文件核对 API 名（`/* TODO: */` 标注不确定项）")
    add("2. 按第 5 节清单逐文件编写实现（每文件只实现对应外设接口，include S5b 的 Port 头）")
    if rtos != "none":
        add(f"3. 实现 OSAL（`{analysis.osal_impl_file_name(rtos)}`）")
    add("4. 运行 validate.py 终验；失败按报告修复后重跑")
    add("")
    if recommendations:
        add("## 9. 待用户确认项（recommendations.json）")
        add("")
        for r in recommendations:
            add(f"- {r['id']}（{r['topic']}）：{r['description']} → {r['suggestion']}")
        add("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5c prepare: 就绪/一致性/能力缺口检查 + 残留清理 + Agent 任务书（不生成代码）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    # ---- 1. 上下文：配置加载 + S5a/S5b 就绪 + 一致性（失败 → state error，退出码 2）----
    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        payload = _write_error_state(config_path, workspace, str(exc))
        _log(str(exc))
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    for w in ctx["drift_warnings"]:
        _log(f"漂移警告: {w}")

    # ---- 2. 目录骨架 + 布局解析（PROJECT_LAYOUT.md 唯一事实来源）----
    try:
        ensure_result = ensure_layout_mod.ensure_layout(
            project_root=ctx["project_root"], config=ctx["config"],
            state=ctx["state"], target=ctx["workspace"].name, quiet=True)
        plan = ensure_result["plan"]
    except layout_resolver.LayoutError as exc:
        payload = _write_error_state(config_path, workspace, f"布局解析失败: {exc}")
        _log(str(payload["error"]))
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    for w in plan.get("warnings", []):
        _log(f"布局警告: {w}")

    # ---- 3. flat 判定：跳过生成（requirement 阶段 A 步骤 5）----
    if ctx["architecture"] == "flat":
        payload = {
            "status": "skipped",
            "rtos": ctx["rtos"],
            "architecture": "flat",
            "power_enabled": ctx["power_enabled"],
            "error": None,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        schema_errors = analysis.validate_schema(
            payload, SKILL_DIR / "schemas" / "output.schema.json", "s5c")
        if schema_errors:
            _write_error_state(config_path, workspace, "; ".join(schema_errors))
            return EXIT_CONFIG_ERROR
        state_store.update_state(ctx["state_path"], {"s5c": payload})
        _log("flat 架构：S5b 已直接对接厂商库，S5c 跳过生成（status=skipped）")
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_OK

    src_dirs = plan["skill_dirs"]["s5c"]["src"]
    if not src_dirs:
        payload = _write_error_state(
            config_path, workspace,
            "布局中未解析到 S5c 产物目录（PROJECT_LAYOUT.md 目录树需有带 S5c 注释的 "
            "Src 目录，如 Drivers/Port/Src/）")
        _log(str(payload["error"]))
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 4. 能力缺口前置检测（缺口 → capability_gap.json + 终止，退出码 2）----
    gap_report = analysis.check_capability_gaps(
        ctx["manifest"], ctx["capabilities"], ctx["capabilities_rel"])
    gap_report["generated_at"] = datetime.now().isoformat(timespec="seconds")
    if gap_report["gaps"]:
        errs = analysis.validate_schema(
            gap_report, SKILL_DIR / "schemas" / "capability_gap.schema.json", "capability_gap")
        if errs:
            _log("capability_gap 契约校验失败: " + "; ".join(errs))
        else:
            analysis.save_json(ctx["outputs_dir"] / "s5c" / "capability_gap.json", gap_report)
            _log(f"能力缺口 {len(gap_report['gaps'])} 项已写入 outputs/s5c/capability_gap.json")
        payload = _write_error_state(
            config_path, workspace,
            f"能力缺口 {len(gap_report['gaps'])} 项（详见 outputs/s5c/capability_gap.json）"
            "——缺口是契约层问题，修复回 S5a/S5b，不得降级实现",
            {"capability_gap": "outputs/s5c/capability_gap.json"})
        _log(payload["error"])
        print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    else:
        gap_file = ctx["outputs_dir"] / "s5c" / "capability_gap.json"
        if gap_file.is_file():
            gap_file.unlink()  # 上轮缺口已修复：清除旧报告
        _log("能力缺口检测：无缺口")

    # ---- 5. 旧文件清理（先用户修改检测，再删非当前平台/RTOS 残留）----
    recorded = analysis.load_file_hashes(ctx["outputs_dir"] / "s5c")
    impl_scan = analysis.scan_impl_files(
        ctx["workspace"], [ctx["workspace"] / d for d in src_dirs],
        ctx["platform_token"], ctx["rtos"], recorded)
    removed_hashes = dict(recorded)
    for rel in impl_scan["stale"]:
        (ctx["workspace"] / rel).unlink()
        removed_hashes.pop(rel, None)
        _log(f"已删除旧平台/旧 RTOS 残留: {rel}")
    for rel in impl_scan["foreign"]:
        _log(f"警告: 不可解析命名的 port_impl 文件，未处理（交用户处理）: {rel}")
    _log(f"实现文件扫描: 当前 {len(impl_scan['current'])}，残留清理 "
         f"{len(impl_scan['stale'])}，用户已修改 {len(impl_scan['user_modified'])}")
    if impl_scan["stale"]:
        analysis.save_file_hashes(ctx["outputs_dir"] / "s5c", removed_hashes)

    # ---- 5b. 代码基线镜像（增量范围校验对照；在 Agent 修改前镜像）----
    baseline = analysis.mirror_code_baseline(
        ctx["outputs_dir"] / "s5c", ctx["workspace"],
        [ctx["workspace"] / d for d in src_dirs])
    _log(f"代码基线已镜像: {len(baseline)} 文件 → outputs/s5c/code_baseline/")

    # ---- 5c. per-peripheral diff（生成模式判定，requirement 阶段 A 步骤 7）----
    snapshot = analysis.load_manifest_snapshot(ctx["outputs_dir"] / "s5c")
    snapshot_missing = snapshot is None
    if snapshot_missing:
        _log("无 manifest 快照（首次执行）→ 全部单元 full 建立基线")
    diff_results = port_differ.diff_all(ctx, plan, removed_hashes, snapshot)
    diff_modes = {r["peripheral"]: r["generation_mode"] for r in diff_results}
    diff_paths = [f"outputs/s5c/port_diffs/{r['peripheral']}_diff.json"
                  for r in diff_results]
    blocked = [r["peripheral"] for r in diff_results
               if r["generation_mode"] == "blocked"]
    if blocked:
        _log(f"⚠️ blocked 单元（须报告用户，不自行处理）: {', '.join(blocked)}")

    # ---- 6. 推荐清单（未指定项）----
    recommendations: list[dict] = []
    rid = 0
    for h in analysis.manifest_peripheral_headers(ctx["manifest"]):
        for inst in h.get("logical_instances", []):
            if inst.get("hw_instance") is None:
                rid += 1
                recommendations.append({
                    "id": f"REC-{rid:03d}",
                    "topic": f"{inst.get('name')} 硬件实例未指定",
                    "description": f"manifest 中 {inst.get('name')} 的 hw_instance=null"
                                   f"（{inst.get('description') or '-'}）",
                    "impact": "Agent 将按 hardware_capabilities/设计输入/S5a init 产物选定实现载体",
                    "suggestion": "核对 Agent 选定的实例并在 s5c_design_input.md 登记，固化选择",
                })
    caps_empty = not (ctx["capabilities"].get("peripherals") or [])
    if caps_empty:
        rid += 1
        recommendations.append({
            "id": f"REC-{rid:03d}",
            "topic": "能力清单退化",
            "description": "hardware_capabilities.json 的 peripherals 为空"
                           "（S1/S4 网表退化导致），类型级比对无法生效",
            "impact": "Agent 依据 S5a init 产物与设计输入自行核对硬件实例，需人工复核",
            "suggestion": "重跑 S1/S4 修复网表吸附后重跑 S5a，恢复能力清单",
        })
    if recommendations:
        analysis.save_json(
            ctx["outputs_dir"] / "s5c" / "recommendations.json",
            {"items": recommendations,
             "generated_at": datetime.now().isoformat(timespec="seconds")})
    else:
        (ctx["outputs_dir"] / "s5c" / "recommendations.json").unlink(missing_ok=True)

    # ---- 7. 生成任务书 ----
    brief_rel = "outputs/s5c/generation_brief.md"
    brief_path = ctx["outputs_dir"] / "s5c" / "generation_brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(build_brief(ctx, plan, impl_scan, recommendations,
                                      diff_results, snapshot_missing),
                          encoding="utf-8", newline="\n")

    # ---- 8. state.s5c = running ----
    payload = {
        "status": "running",
        "rtos": ctx["rtos"],
        "architecture": ctx["architecture"],
        "power_enabled": ctx["power_enabled"],
        "generation_brief": brief_rel,
        "skipped_files": impl_scan["user_modified"],
        "port_manifest_snapshot": "outputs/s5c/port_manifest_snapshot.json"
                                  if not snapshot_missing else None,
        "port_diffs": diff_paths,
        "generation_modes": diff_modes,
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5c")
    if schema_errors:
        _write_error_state(config_path, workspace, "; ".join(schema_errors))
        _log("s5c 状态契约校验失败: " + "; ".join(schema_errors))
        return EXIT_CONFIG_ERROR
    state_store.update_state(ctx["state_path"], {"s5c": payload})

    _log(f"任务书已生成: {brief_path}")
    _log("下一步：Agent 按 SKILL.md 指引 + 任务书实现 Port/OSAL/Power 接口，"
         "完成后运行 validate.py 终验")
    print(json.dumps({"s5c": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
