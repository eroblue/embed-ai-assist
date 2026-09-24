#!/usr/bin/env python
"""S2 spec-reader 第 1 段：prepare（rule 轨）。

三段式执行模型（与 S5a/S5b 同策略：rule 只做确定性契约工作，需求条目内容归 Agent）：
  1. [rule]  prepare.py   → 输入就绪检查（S1 工作区 + functional_spec 必选）
                            → 提取原始文本到 outputs/s2/raw_text.md
                            → 生成任务书 outputs/s2/generation_brief.md（Agent 任务书）
                            → state.spec.status = running
  2. [agent] Agent 按任务书提取需求 → outputs/s2/spec.json + spec_trace.json
                            + uncovered.json
  3. [rule]  validate.py  → schema 校验 + 引用一致性 → 统计 → state 收口

本脚本不解析规格书内容、不生成需求条目；state.json 写入统一走 state_store
（文件锁，与 S5a/S5b 并行安全）。失败时 status=failed 且清理 outputs/s2/
（不留半成品）。
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(SCRIPT_DIR / "extractors"))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import state_store  # noqa: E402
from extractors import extract_text  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 3


def _log(msg: str) -> None:
    print(f"[s2-prepare] {msg}", file=sys.stderr)


def _resolve_workspace(config_path: Path, workspace_arg: str | None) -> Path:
    workspace = Path(workspace_arg or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    return workspace


def _write_error_state(config_path: Path, workspace: Path, error: str,
                       clean_products: bool = True) -> dict:
    """写 state.spec = failed；clean_products 时清理 outputs/s2/（不留半成品）。"""
    payload = {"status": "failed", "spec_path": None, "error": error,
               "updated_at": datetime.now().isoformat(timespec="seconds")}
    try:
        cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        cfg = None
    state_path = analysis.resolve_target(cfg, workspace) / "state.json"
    if clean_products:
        s2_dir = state_path.parent / "outputs" / "s2"
        if s2_dir.is_dir():
            shutil.rmtree(s2_dir)
    try:
        state_store.update_state(state_path, {"spec": payload})
    except (OSError, state_store.StateLockTimeout):
        pass
    return payload


def _text_stats(text: str) -> dict:
    """原文摘要统计：字符数 / 章节数（# 标题）/ 表格行数。"""
    sections = [ln for ln in text.splitlines() if ln.startswith("#")]
    table_rows = sum(1 for ln in text.splitlines() if ln.strip().startswith("|"))
    return {"chars": len(text), "sections": len(sections), "table_rows": table_rows}


def build_brief(ctx: dict, extraction: dict, stats: dict) -> str:
    """构建 generation_brief.md（S2 Agent 任务书）。"""
    strict = ctx["strict_mode"]
    lines: list[str] = []
    add = lines.append

    add("# S2 规格书需求提取任务书（generation_brief）")
    add("")
    add("> 由 prepare.py 生成（rule 轨）。Agent 按本任务书把原始规格书转成结构化需求，")
    add("> 操作规范见 `skills/spec-reader/SKILL.md` 与 `references/`（提取要点")
    add("> spec_extraction_guide.md、分类规范 requirement_taxonomy.md、字段规范")
    add("> spec_json_format.md）。只提取'产品要什么'，不提取'技术上怎么实现'。")
    add("")

    # ---- 1. 项目信息 ----
    add("## 1. 项目信息")
    add("")
    add(f"- 目标工程（build_target）：{ctx['workspace'].name}")
    add(f"- 输出语言：{ctx['language']}（仅影响描述字段语言）")
    add(f"- 严格模式：{'启用（模糊描述写入 uncovered，不臆断）' if strict else '关闭（可合理假设默认值，同时登记 uncovered）'}")
    add(f"- 功能规格书：`{ctx['spec_file']}`（格式：{ctx['source_type']}）")
    if ctx["software_spec"]:
        add(f"- 软件规格书：`{ctx['software_spec']}`（**仅登记指针，禁止解析内容**——技术细节归 S5b）")
    else:
        add("- 软件规格书：未配置（无需处理）")
    add("")

    # ---- 2. 原文摘要 ----
    add("## 2. 原文摘要")
    add("")
    pages = extraction.get("pages")
    page_note = f"，共 {pages} 页（页码以 `<!-- page N -->` 注释标记）" if pages else ""
    add(f"- 提取文本约 {stats['chars']} 字符，{stats['sections']} 个标题章节"
        f"{page_note}，{stats['table_rows']} 行表格内容")
    add(f"- 提取文本已存档：`outputs/s2/raw_text.md`（人工核对与追溯用）")
    add("")

    # ---- 3. 输出要求 ----
    add("## 3. 输出要求（三个产物，写入 outputs/s2/）")
    add("")
    add("1. `spec.json` —— 结构化需求（**核心产物**，S5b 消费）：")
    add("   - `meta`（source_file/source_type/extracted_at/spec_version）、`title`、`summary`")
    add("   - `requirements[]`：需求条目（`REQ-001` 起顺序编号不跳号），每条含")
    add("     id/title/description/priority(must|should|could)/")
    add("     category(functional|interface|performance|constraint)/source{section,page?}/acceptance?")
    add("   - `features[]`：业务域分组（`F-001` 起），每条含 id/name/description/requirements[]")
    add("   - `business_states[]`：业务级状态机（module_hint + states[] + transitions[]）")
    add("   - `business_timing[]`：业务级时序（period_ms 或 pattern + requirement 引用）")
    add("   - `error_handling[]`：业务级错误处理策略（scenario/strategy/requirement）")
    add("   - `thresholds[]`：业务阈值（name/value/unit/condition/requirement）")
    add("   - 结构契约：`skills/spec-reader/schemas/spec.schema.json`（写入前须通过校验）")
    add("   - 完整示例：`skills/spec-reader/assets/spec_example.json`")
    add("2. `spec_trace.json` —— 需求追溯：每条 REQ 一条记录（requirement/section/page?/quote 原文引用），")
    add("   须覆盖全部 REQ-ID，契约 `schemas/spec_trace.schema.json`")
    add("3. `uncovered.json` —— 未定项清单（模糊描述、缺失项）：items[] 可为空数组但文件必须存在，")
    add("   契约 `schemas/uncovered.schema.json`")
    add("")

    # ---- 4. 需求条目化规范 ----
    add("## 4. 需求条目化规范")
    add("")
    add("- **REQ 粒度 = 可独立验收的功能点**，不是规格书每句话一条：")
    add("  - 同一功能行为的不同侧面（如'采集 + 采集失败处理'）合并为一条")
    add("  - 能独立验收、且验收标准不同的功能点分开")
    add("  - 中等复杂度项目典型 10~20 条")
    add("- **category 判定**：functional=功能行为（默认）；interface=功能级接口/外设需求")
    add("  （'需要串口与上位机通信'，非波特率/引脚等技术细节）；performance=性能指标")
    add("  （响应时间/精度/吞吐量）；constraint=系统级约束（无动态内存/24h 连续可用）")
    add("- **来源标注**：`source.section` 填可定位的章节标题（如'2.1 环境采集'）；")
    add("  PDF 源填 `source.page`（对应 `<!-- page N -->` 标记）")
    add("- **验收标准**：`acceptance` 原文有则摘录，无则根据描述总结；纯约束类可留 null")
    add("- **feature 划分**：明显特征清楚即可，不追求完美；一条 REQ 至少归属一个 feature；")
    add("  横切关注点（工作状态管理/初始化与容错/系统约束）独立成 feature")
    add("")

    # ---- 5. 未定项处理原则 ----
    add("## 5. 未定项处理原则（strict_mode 行为）")
    add("")
    if strict:
        add("- **严格模式已启用**：遇到模糊描述（如'定期采集'未给周期、'异常告警'未给阈值）")
        add("  一律写入 `uncovered.json`（UNC-001 起编号，含 question），**不得臆断默认值**")
    else:
        add("- 遇到模糊描述可采取合理默认假设（按行业惯例），但**必须**同时登记")
        add("  `uncovered.json`：description 写原文怎么说的，assumption 写采用的默认值，")
        add("  question 写需用户确认的问题")
    add("- 全文缺失的关键信息（如无错误处理章节）也登记 uncovered（source.section 为 null）")
    add("- uncovered 非空 → validate 收口为 `partial`，需用户确认后修订")
    add("")

    # ---- 6. 禁止事项 ----
    add("## 6. 禁止事项（硬约束）")
    add("")
    add("- 不提取技术实现细节：帧格式、命令码、波特率、校验方式、引脚映射、DMA、")
    add("  外设选择、消抖/调度/心跳实现方式——这些归 S5b 从 `s5b_design_input.md` 读取")
    add("- 不生成 `module_list.json`、不做 feature → module 映射（S5b 职责）")
    add("- 不解析 software_spec 内容（只登记路径）")
    add("- `spec.json` 中不内联'如何实现'的描述，只写'要什么'")
    add("- 不修改 config.json / state.json 其他字段")
    add("")

    # ---- 7. 原始文本 ----
    add("## 7. 原始文本（分章节，已 Markdown 化）")
    add("")
    add("```markdown")
    add(extraction["text"].rstrip())
    add("```")
    add("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S2 prepare: 提取规格书原始文本 + 生成 Agent 任务书（不生成需求条目）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = _resolve_workspace(config_path, args.workspace)
    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        payload = _write_error_state(config_path, workspace, str(exc))
        _log(str(exc))
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 提取原始文本（失败 → failed + 清理半成品）----
    try:
        extraction = extract_text(ctx["spec_abs"], ctx["source_type"])
    except (RuntimeError, OSError) as exc:
        payload = _write_error_state(config_path, workspace, f"规格书提取失败: {exc}")
        _log(str(payload["error"]))
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    stats = _text_stats(extraction["text"])
    if stats["chars"] == 0:
        payload = _write_error_state(config_path, workspace,
                                     f"规格书内容为空: {ctx['spec_file']}")
        _log(str(payload["error"]))
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 写产物：raw_text.md + generation_brief.md ----
    s2_dir = ctx["outputs_dir"] / "s2"
    try:
        s2_dir.mkdir(parents=True, exist_ok=True)
        raw_path = s2_dir / "raw_text.md"
        raw_path.write_text(extraction["text"].rstrip() + "\n", encoding="utf-8", newline="\n")

        brief = build_brief(ctx, extraction, stats)
        brief_path = s2_dir / "generation_brief.md"
        brief_path.write_text(brief, encoding="utf-8", newline="\n")
    except OSError as exc:
        payload = _write_error_state(config_path, workspace, f"产物写入失败: {exc}")
        _log(str(payload["error"]))
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    _log(f"原始文本已提取: {raw_path}（{stats['chars']} 字符 / {stats['sections']} 章节）")
    _log(f"任务书已生成: {brief_path}")

    # ---- state.spec = running ----
    payload = {
        "status": "running",
        "spec_path": None,
        "software_spec_path": ctx["software_spec"],
        "spec_summary": None,
        "source_file": ctx["spec_file"],
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "spec")
    if schema_errors:
        payload = _write_error_state(config_path, workspace,
                                     "spec 状态契约校验失败: " + "; ".join(schema_errors))
        _log(str(payload["error"]))
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_FAILED
    state_store.update_state(ctx["state_path"], {"spec": payload})

    _log("下一步：Agent 按任务书提取需求 → outputs/s2/spec.json + spec_trace.json"
         " + uncovered.json → 运行 validate.py 终验")
    print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
