#!/usr/bin/env python
"""S5b port-contract-and-app 第 1 段：prepare（rule 轨）。

三段式执行模型（与 S5a 同策略：rule 只做确定性契约工作，代码与流程图内容归 Agent）：
  1. [rule]  prepare.py        → 输入就绪检查（S2 可选/S4 可选，缺失降级为
                                 设计输入驱动模式）→ 流程图现状盘点 →
                                 代码基线快照 → outputs/s5b/generation_brief.md
                                 （Agent 任务书），state.s5b = running
  2. [agent] Agent 生成（两阶段）
       阶段 A（80%）：功能拆分 → 逐模块 Mermaid 流程图（draft）→
                     flow_validator.py 校验 → 用户审核（approved）→
                     flow_differ.py diff → 逐模块代码（full/incremental/skip）
                     + Port/OSAL/Power 接口 + manifest
       阶段 B（20%）：顶层连接（app.c/main.c/任务创建/汇总初始化）
                     → traceability.json
       增量生成后调用 diff_range_checker.py 拦截异常重写
  3. [rule]  validate.py       → 终验（流程图规范/产物存在/禁止 include/
                                 schema 校验/mtime 守卫）→ IDE 同步 → state = done

本脚本不生成任何 C 代码与流程图内容；不依赖 S5a 的任何产物（可并行）。
产物目录不硬编码：按 PROJECT_LAYOUT.md 解析（layout_resolver）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
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
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s5b-prepare] {msg}", file=sys.stderr)


def _resolve_workspace(config_path: Path, workspace_arg: str | None) -> Path:
    workspace = Path(workspace_arg or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    return workspace


def _pick_dirs(dirs: list[str], role: str) -> list[str]:
    """从 LayoutPlan 的 s5b 目录中按角色筛选（analysis.classify_rel_path）。"""
    return [d for d in dirs if analysis.classify_rel_path(d) == role]


def snapshot_code_baseline(ctx: dict, src_dirs: list[Path], inc_dirs: list[Path]) -> dict:
    """镜像现有 S5b 产物代码到 outputs/s5b/code_baseline/（增量 diff 范围校验基线）。

    同时写 code_snapshot.json 索引 {rel: {sha256, lines}}；无现有产物时索引为空。
    """
    baseline_dir = ctx["outputs_dir"] / "s5b" / "code_baseline"
    if baseline_dir.exists():
        shutil.rmtree(baseline_dir)  # 每轮 prepare 重建基线
    index: dict[str, dict] = {}
    for d in src_dirs + inc_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.[ch]")):
            rel = str(f.resolve().relative_to(ctx["workspace"])).replace("\\", "/")
            text = f.read_text(encoding="utf-8", errors="replace")
            dst = baseline_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            index[rel] = {
                "sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
                "lines": len(text.splitlines())}
    analysis.save_json(ctx["outputs_dir"] / "s5b" / "code_snapshot.json",
                       {"files": index, "created_at": datetime.now().isoformat(timespec="seconds")})
    return index


def inventory_flows(ctx: dict) -> dict:
    """流程图现状盘点：docs/flow/*.md vs outputs/s5b/flow_index.json。

    返回 {flows: [{module, kind, file, status, version, hash, changed}],
          index_exists, missing_files}。
    changed = 正文 hash 与 index 记录不一致（增量 diff 候选）。
    """
    index_path = ctx["outputs_dir"] / "s5b" / "flow_index.json"
    index: dict = {"flows": []}
    if index_path.is_file():
        try:
            index = analysis.load_json(index_path)
        except (json.JSONDecodeError, OSError):
            index = {"flows": []}
    by_module = {f.get("module"): f for f in index.get("flows", [])}

    flows: list[dict] = []
    for item in analysis.scan_flow_dir(ctx["flow_dir"]):
        text = item["path"].read_text(encoding="utf-8-sig")
        meta, body = analysis.parse_front_matter(text)
        rec = {
            "module": item["module"], "kind": item["kind"],
            "file": analysis.flow_rel_path(ctx["flow_dir"], item["path"]),
            "status": (meta or {}).get("status", ""),
            "version": (meta or {}).get("version", ""),
            "hash": analysis.content_hash(body),
            "changed": False,
        }
        prev = by_module.get(item["module"])
        if prev is not None:
            rec["changed"] = prev.get("hash") != rec["hash"]
        flows.append(rec)
    missing = [f.get("file") for f in index.get("flows", [])
               if f.get("module") not in {x["module"] for x in flows}]
    return {"flows": flows, "index_exists": index_path.is_file(),
            "missing_files": missing}


def build_brief(ctx: dict, plan: dict, design_input: dict | None,
                flow_inv: dict, gap_report: dict | None,
                baseline_count: int, config_changed: list[str]) -> str:
    """构建 generation_brief.md（S5b Agent 任务书）。"""
    app_src = _pick_dirs(plan["skill_dirs"]["s5b"]["src"], "app")
    app_inc = _pick_dirs(plan["skill_dirs"]["s5b"]["inc"], "app")
    drv_src = _pick_dirs(plan["skill_dirs"]["s5b"]["src"], "driver")
    drv_inc = _pick_dirs(plan["skill_dirs"]["s5b"]["inc"], "driver")
    port_inc = _pick_dirs(plan["skill_dirs"]["s5b"]["inc"], "port")
    arch, rtos = ctx["architecture"], ctx["rtos"]
    use_osal = rtos != "none"
    use_power = ctx["power_enabled"] and arch != "flat"
    inputs = ctx["inputs"]
    lines: list[str] = []
    add = lines.append

    add("# S5b 代码生成任务书（generation_brief）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。Agent 按本任务书执行两阶段生成，")
    add("> 操作规范见 `skills/port-contract-and-app/SKILL.md` 与 `references/`。")
    add("> 流程图未 approved 不生成代码；增量只做定点修改，禁止重写全文件。")
    add("")

    # ---- 1. 项目信息 ----
    add("## 1. 项目信息")
    add("")
    mcu = ((ctx["facts"] or {}).get("mcu")) or ctx["config"].get("platform") \
        or ctx["config"].get("project", {}).get("target", "")
    add(f"- MCU（仅参考，Port 不得依赖厂商型号）：{mcu}")
    add(f"- 架构：{arch}；RTOS：{rtos}；低功耗：{'启用' if ctx['power_enabled'] else '未启用'}；语言标准：{ctx['language']}")
    if ctx["port_split"]:
        add(f"- Port 拆分策略（用户指定）：{ctx['port_split']}")
    data_mode = "S2 功能规格书驱动" if ctx["spec_path"] else "**设计输入驱动（降级模式：S2 spec 缺失）**"
    add(f"- 数据来源模式：{data_mode}")
    if rtos != "none" and arch == "flat":
        add("- **注意**：flat + RTOS 组合仍生成 osal.h（OSAL 与外设 Port 层正交），"
            "但任务化 APP 不生成——APP 在主循环中经 osal 调用 RTOS 原语（见 SKILL.md）")
    add("")

    # ---- 2. 输入材料清单 ----
    add("## 2. 输入材料清单（Agent 深查用）")
    add("")
    if ctx["spec_path"]:
        add(f"- S2 功能规格书：`{ctx['spec_path']}`（功能需求/外设需求/性能指标的权威来源）")
    else:
        add("- S2 功能规格书：**缺失**——以设计输入与 S4 硬件事实为主，Agent 按经验推荐方案"
            "（未指定项输出 outputs/s5b/recommendations.json 供用户确认）")
    if ctx["facts_path"]:
        add(f"- S4 硬件事实：`{ctx['facts_path']}`（硬件实际连接，Port 实例映射依据；下面第 3 节为摘要）")
    else:
        add("- S4 硬件事实：**缺失**——Port manifest 的 hw_instance 置 null（hw_source=none），"
            "由 S5c 按 hardware_capabilities 匹配")
    if design_input:
        add(f"- 用户设计输入：`{design_input['path']}`（优先级最高，原文段落见下方）")
    else:
        add("- 用户设计输入：无（docs/s5b_design_input.md 缺失或全部为 none）——"
            "Agent 基于硬件事实与经验自主判断，推荐方案输出 recommendations.json")
    # 维护期（非首跑）：demo/SDK/已有项目属代码风格学习材料，仅首次全量需要；
    # 增量轮次跳过以减小上下文，变更模块沿用已生成代码作为风格锚点
    maintenance = bool(flow_inv.get("index_exists"))
    style_keys = {"demos", "sdk", "existing_project"}
    for key, label in (("software_spec", "软件规格书"),
                       ("demos", "demo 程序"), ("sdk", "SDK 目录"),
                       ("existing_project", "已有项目"), ("ide_project", "IDE 项目文件")):
        val = inputs[key]
        if not val:
            continue
        if maintenance and key in style_keys:
            continue
        add(f"- {label}：`{val}`")
    if maintenance:
        add("- （维护期增量：demo/SDK/已有项目学习材料本轮跳过，仅首次全量读取；"
            "如变更模块涉及新外设 API，按 config.json 中路径自行查阅）")
    add("")
    if design_input:
        add("### 设计输入原文（按段提取）")
        add("")
        for sec, content in design_input["sections"].items():
            add(f"**{sec}**：")
            for ln in content:
                add(f"> {ln}")
            add("")
    if ctx["spec_path"]:
        add("> spec 数据较大不内嵌，Agent 自行读取上述路径；提取要点见"
            " `references/software_spec_guide.md`。")
        add("")

    # ---- 3. 硬件事实摘要 ----
    add("## 3. 硬件事实摘要（S4 facts，Port 实例定义参考）")
    add("")
    hw_lines = analysis.facts_hw_summary(ctx["facts"])
    if hw_lines:
        lines.extend(hw_lines)
    else:
        add("- S4 硬件事实缺失或无已识别外设引脚——Port 实例映射留空（hw_instance=null）")
    add("")

    # ---- 4. 流程图现状 ----
    add("## 4. 流程图现状（docs/flow/）")
    add("")
    if not flow_inv["flows"]:
        add("- 无流程图：首跑全量模式。按功能拆分逐模块新建"
            "（骨架见 `assets/flow_skeletons/`，规范见 `references/mermaid_*_guide.md`）")
    else:
        add("| 模块 | 图类型 | 版本 | 状态 | 本轮是否有修改 |")
        add("|---|---|---|---|---|")
        for f in flow_inv["flows"]:
            add(f"| {f['module']} | {f['kind']} | {f['version'] or '?'} | "
                f"{f['status'] or '?'} | {'是（hash 变化，需 flow_differ 重新 diff）' if f['changed'] else '否'} |")
        for mf in flow_inv["missing_files"]:
            add(f"- **警告**：index 记录的流程图文件已缺失：{mf}")
        add("")
        add("- 修改已有流程图时**以现有文件为锚点做定点修改**，不重新生成；"
            "approved 后修改须将 status 置 dirty，重新审核后 version 递增")
    add("")

    # ---- 5. 能力缺口（rule 机械比对） ----
    add("## 5. 能力缺口（rule 机械比对结果）")
    add("")
    if gap_report is None:
        add("- 未执行机械比对（设计输入无硬件使用段或 S4 缺失）；"
            "Agent 拆分功能时如发现硬件不支持的需求，更新 outputs/s5b/capability_gap.json 并向用户报告")
    elif gap_report["gaps"]:
        add(f"- checked={gap_report['checked']}，发现 {len(gap_report['gaps'])} 个疑似缺口"
            "（详见 outputs/s5b/capability_gap.json，warning 级）：")
        for g in gap_report["gaps"]:
            add(f"  - {g['needed']}：{g['detail']}")
        add("- Agent 应逐条复核（可能是 facts 网络名未识别，非真缺口），确认为真缺口时升级处理")
    else:
        add("- 机械比对无缺口（设计输入引用的外设/引脚均在 S4 事实中）")
    add("")

    # ---- 6. 生成要求 ----
    add("## 6. 生成要求（两阶段：先模块后连接）")
    add("")
    add("### 目录落点（来自 PROJECT_LAYOUT.md 解析，勿写其他目录）")
    add("")
    add(f"- APP 源文件（`app*.c` / `protocol_*.c` / `main.c`）：`{app_src[0] if app_src else 'App/Src'}/`")
    add(f"- APP 头文件：`{app_inc[0] if app_inc else 'App/Inc'}/`")
    add(f"- 设备驱动（`driver_*.c/h`）：`{drv_src[0] if drv_src else 'Drivers/BSP/Src'}/` + `{drv_inc[0] if drv_inc else 'Drivers/BSP/Inc'}/`")
    if port_inc:
        add(f"- Port 接口头文件：`{port_inc[0]}/`（模板见 `assets/port_templates/`，裁剪/扩展后生成）")
    else:
        add("- Port 接口头文件：**flat 架构不生成 Port 层**——APP 直接调用 S5a 的 BSP 初始化接口")
    if use_osal:
        add("- OSAL：生成 `osal.h`（单文件，接口原则见 `references/osal_design_principle.md`）")
    if use_power:
        add("- Power：生成 `power_port.h`（接口命名由设计输入/已有方案决定，见 `references/port_design_principle.md`）")
    add("- 流程图：`docs/flow/<模块>_<state|flow|sequence>.md`（front-matter + Mermaid）")
    add("")
    add("### 命名与拆分规范")
    add("")
    add("- 模块名 = 代码文件基名（如 `app_wifi` → `App/Src/app_wifi.c/h` + `docs/flow/app_wifi_state.md`）")
    add("- APP 功能模块 `app_<功能>.c/h`；任务化 `app_<功能>_task.c/h`（仅 RTOS 且非 flat）；"
        "协议层 `protocol_<名称>.c/h`；驱动 `driver_<设备>.c/h`")
    add("- `app.c/h` 只做初始化汇总与主循环/任务创建；`main.c` 不存在时创建"
        "（只调 S5a 总入口 `board_init/hal_init` 与 `app_init`，不含业务逻辑）")
    add("- 未被使用的模块不生成；文件拆分细则见 `references/file_split_guide.md`")
    add("")
    add("### 数据产物（outputs/s5b/）")
    add("")
    add("- `port_interface_manifest.json`（S5c 实现 Port 的唯一依据，schema 约束，"
        "结构见 `assets/port_interface_manifest_example.json`）")
    add("- `traceability.json`（需求 → 流程图 → 文件 → 函数追踪矩阵）")
    add("- `recommendations.json`（仅当存在 Agent 推荐未定项时）")
    add("- `capability_gap.json`（发现缺口时更新；无缺口删除文件）")
    add("")

    # ---- 7. 增量模式 ----
    add("## 7. 增量模式（本轮生成范围）")
    add("")
    if not flow_inv["index_exists"]:
        add("- 首跑全量：流程图与代码全部新建（无需增量处理）")
    else:
        changed_flows = [f["module"] for f in flow_inv["flows"] if f["changed"]]
        if config_changed:
            add(f"- **配置变化**（{', '.join(config_changed)}）：需相应调整产物"
                "（如 osal.h/任务文件的增删），APP 模块逻辑不需全量重写")
        if changed_flows:
            add(f"- 流程图 hash 变化候选：`{', '.join(changed_flows)}`——审核通过后运行 "
                "flow_differ.py 判定 full/incremental/skip，按 diff 结果定点修改代码")
        else:
            add("- 流程图无变化：对应模块走 skip 分支，不重跑代码生成")
        if baseline_count:
            add(f"- 已有 {baseline_count} 个现有产物文件（基线快照 outputs/s5b/code_baseline/）；"
                "增量修改后必须运行 diff_range_checker.py（变更行数超预期 3 倍即报错）")
    add("")

    # ---- 8. 禁止事项 ----
    add("## 8. 禁止事项（硬约束）")
    add("")
    add("- 所有 APP/Driver/协议层源文件不得 include 任何 HAL 头文件与 RTOS 头文件；RTOS 调用必须过 `osal.h`")
    add("- Port 接口只使用基本类型（stdint.h）和不透明句柄；厂商实例名/引脚号/网络名只进 manifest 数据，不进代码")
    add("- DMA 不暴露给 APP，隐藏在 UART 等实现内")
    add("- 不得把所有 APP 逻辑塞进一个 `app.c`（flat 架构除外）")
    add("- 不得在流程图未 approved 时生成对应模块代码；不得重新生成已有流程图（只做定点修改）")
    add("- 不得在流程图无变更时重跑对应模块代码生成（走 skip）")
    add("- 增量生成禁止重写整个文件（diff 范围校验拦截，超 3 倍报警置 error）")
    add("- 不修改 config.json / S2/S4 产物 / IDE 工程文件；不依赖 S5a 之外的产物"
        "（S5b 与 S5a 并行，Port 实现是 S5c 职责）")
    add("- 换平台/换 RTOS 时本 skill 产物内容哈希必须不变（平台无关性）")
    add("")

    # ---- 9. 执行步骤 ----
    add("## 9. 执行步骤（Agent 操作序列，详见 SKILL.md）")
    add("")
    add("1. 功能拆分：从 spec/设计输入/硬件事实提取功能模块清单（module_list，"
        "含模块名/来源/依赖/需确认点）")
    add("2. 阶段 A：逐模块写流程图（选对图类型：状态迁移→stateDiagram-v2、顺序流程→flowchart TD、"
        "模块交互→sequenceDiagram；骨架在 `assets/flow_skeletons/`）→ 运行 `flow_validator.py` 校验")
    add("3. 用户审核流程图（Agent 不得自行批准；用户确认后代改 status=approved 并填 approved_by）")
    add("4. 运行 `flow_differ.py` 生成各模块 diff 与生成模式 → 按模式生成/修改模块代码"
        "（映射规则 `references/flow_to_code_mapping.md`；增量后运行 `diff_range_checker.py`）")
    add("5. 阶段 A 续：生成 Port/OSAL/Power 头文件 + `port_interface_manifest.json`")
    add("6. 阶段 B：顶层连接（`app.c`/`main.c`/任务文件）+ `traceability.json`")
    add("7. 运行 `validate.py` 终验；失败按报告修复后重跑")
    add("")
    return "\n".join(lines)


def _write_error_state(config_path: Path, workspace: Path, error: str) -> dict:
    payload = {"status": "error", "error": error,
               "updated_at": datetime.now().isoformat(timespec="seconds")}
    try:
        cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        cfg = None
    state_path = analysis.resolve_target(cfg, workspace) / "state.json"
    try:
        state_store.update_state(state_path, {"s5b": payload})
    except (OSError, state_store.StateLockTimeout):
        pass
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5b prepare: 输入检查 + 流程图盘点 + Agent 任务书（不生成代码/流程图）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--arch", choices=["flat", "layered", "full"], default=None,
                        help="覆盖架构（仅本次生效）")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = _resolve_workspace(config_path, args.workspace)
    try:
        ctx = analysis.load_context(config_path, workspace, arch_override=args.arch)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        payload = _write_error_state(config_path, workspace, str(exc))
        _log(str(exc))
        print(json.dumps({"s5b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 目录骨架 + 布局解析（PROJECT_LAYOUT.md 唯一事实来源）----
    try:
        ensure_result = ensure_layout_mod.ensure_layout(
            project_root=ctx["project_root"], config=ctx["config"],
            state=ctx["state"], target=ctx["workspace"].name, quiet=True)
        plan = ensure_result["plan"]
        if not plan["skill_dirs"]["s5b"]["src"] or not plan["skill_dirs"]["s5b"]["inc"]:
            raise layout_resolver.LayoutError(
                "布局中未解析到 S5b 产物目录（PROJECT_LAYOUT.md 目录树需有带 "
                "S5b 注释的 Src/Inc 目录）")
    except layout_resolver.LayoutError as exc:
        payload = _write_error_state(config_path, workspace, f"布局解析失败: {exc}")
        _log(str(payload["error"]))
        print(json.dumps({"s5b": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    for w in plan.get("warnings", []):
        _log(f"布局警告: {w}")
    if ensure_result["created"]:
        _log(f"已创建目录骨架: {', '.join(ensure_result['created'])}")

    # ---- 设计输入 + 能力缺口机械比对 ----
    design_input = analysis.load_design_input(
        ctx["project_root"], ctx["inputs"]["s5b_design_input"])
    gap_report = None
    hw_reqs = analysis.extract_hw_requirements(design_input)
    if hw_reqs or ctx["facts"]:
        gap_report = analysis.check_capability_gaps(hw_reqs, ctx["facts"], ctx["facts_path"])
        gap_report["generated_at"] = datetime.now().isoformat(timespec="seconds")
        if gap_report["gaps"]:
            errs = analysis.validate_schema(
                gap_report, SKILL_DIR / "schemas" / "capability_gap.schema.json", "capability_gap")
            if errs:
                _log("capability_gap 契约校验失败: " + "; ".join(errs))
            else:
                analysis.save_json(ctx["outputs_dir"] / "s5b" / "capability_gap.json", gap_report)
                _log(f"能力缺口机械比对: {len(gap_report['gaps'])} 个疑似缺口已写入 capability_gap.json")

    # ---- 流程图现状盘点 + 代码基线快照 ----
    flow_inv = inventory_flows(ctx)
    ctx["flow_dir"].mkdir(parents=True, exist_ok=True)
    (ctx["flow_dir"] / ".history").mkdir(exist_ok=True)
    src_dirs = [ctx["workspace"] / d for d in plan["skill_dirs"]["s5b"]["src"]]
    inc_dirs = [ctx["workspace"] / d for d in plan["skill_dirs"]["s5b"]["inc"]]
    baseline_index = snapshot_code_baseline(ctx, src_dirs, inc_dirs)
    _log(f"流程图盘点: {len(flow_inv['flows'])} 张（index {'存在' if flow_inv['index_exists'] else '不存在'}）；"
         f"代码基线 {len(baseline_index)} 文件")

    # ---- 配置变化检测（对比上轮 state.s5b）----
    prev = ctx["state"].get("s5b") or {}
    config_changed = []
    if isinstance(prev, dict) and prev.get("status") in ("done", "error"):
        for key, label in (("rtos", "RTOS"), ("architecture", "架构"), ("power_enabled", "低功耗")):
            if key in prev and prev[key] != ctx[key]:
                config_changed.append(label)

    # ---- 输出 Agent 任务书 ----
    brief_rel = "outputs/s5b/generation_brief.md"
    brief_path = ctx["outputs_dir"] / "s5b" / "generation_brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(
        build_brief(ctx, plan, design_input, flow_inv, gap_report,
                    len(baseline_index), config_changed),
        encoding="utf-8", newline="\n")

    # ---- state.s5b = running ----
    payload = {
        "status": "running",
        "rtos": ctx["rtos"],
        "architecture": ctx["architecture"],
        "power_enabled": ctx["power_enabled"],
        "generation_brief": brief_rel,
        "incremental": flow_inv["index_exists"],
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5b")
    if schema_errors:
        _write_error_state(config_path, workspace, "; ".join(schema_errors))
        _log("s5b 状态契约校验失败: " + "; ".join(schema_errors))
        return EXIT_FAILED
    state_store.update_state(ctx["state_path"], {"s5b": payload})

    _log(f"任务书已生成: {brief_path}")
    _log("下一步：Agent 按 SKILL.md 指引 + 任务书执行两阶段生成"
         "（流程图 → 审核 → diff → 代码 → 顶层连接 → validate.py）")
    print(json.dumps({"s5b": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
