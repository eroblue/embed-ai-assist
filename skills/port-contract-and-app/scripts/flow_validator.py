#!/usr/bin/env python
"""S5b flow_validator：Mermaid 流程图规范校验（rule 轨，Agent 写完流程图后调用）。

校验内容（确定性部分；图的内容质量由用户审核把关）：
- front-matter：必填字段（name/status/version）、status 枚举、name 与文件名一致
- 图类型契约：文件名后缀 ↔ 图类型（<模块>_state.md → stateDiagram-v2、
  <模块>_flow.md → flowchart TD|LR、<模块>_sequence.md → sequenceDiagram），
  图类型和布局方向由系统定，不由 Agent 选择（requirement"流程图中间层"）
- 语法要点：mermaid 围栏存在、stateDiagram 必须标注 [*] 初始态/终态
- 审核一致性：approved 必须有 approved_at；同一模块只允许一张图
- 命名风格：状态名大写、事件名小写（警告级，不拦截）

退出码：0=全部通过（可有警告）；1=存在错误。
validate.py 终验时复用本模块的 validate_flows()。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 1


def _log(msg: str) -> None:
    print(f"[s5b-flow-validator] {msg}", file=sys.stderr)


_MERMAID_FENCE = re.compile(r"```mermaid\s*\n(.*?)```", re.S)
_REQUIRED_META = ("name", "status", "version")


def validate_flow_file(path: Path, flow_dir: Path) -> tuple[list[str], list[str], dict]:
    """校验单个流程图文件，返回 (errors, warnings, info)。"""
    errors: list[str] = []
    warnings: list[str] = []
    fname = path.name
    m = re.match(r"^(.+?)_(state|flow|sequence)\.md$", fname)
    if not m:
        return [f"{fname}: 文件名须为 <模块>_<state|flow|sequence>.md"], [], {}
    module, kind = m.group(1), m.group(2)
    info = {"module": module, "kind": kind, "path": path, "file": analysis.flow_rel_path(flow_dir, path)}

    text = path.read_text(encoding="utf-8-sig")
    meta, body = analysis.parse_front_matter(text)
    if meta is None:
        errors.append(f"{fname}: 缺少 YAML front-matter（--- name/status/version/... ---）")
        meta = {}
    for key in _REQUIRED_META:
        if not meta.get(key):
            errors.append(f"{fname}: front-matter 缺少必填字段 {key}")
    status = str(meta.get("status") or "")
    if status and status not in analysis.FLOW_STATUSES:
        errors.append(f"{fname}: 非法 status '{status}'（合法值 {'/'.join(analysis.FLOW_STATUSES)}）")
    if meta.get("name") and meta["name"] not in (module, path.stem):
        errors.append(f"{fname}: front-matter name '{meta['name']}' 与文件名不一致"
                      f"（应为 '{path.stem}'，也接受模块名 '{module}'）")
    if status == "approved" and not meta.get("approved_at"):
        errors.append(f"{fname}: status=approved 但 approved_at 为空")
    if status == "approved" and not meta.get("approved_by"):
        warnings.append(f"{fname}: status=approved 但 approved_by 为空（建议记录审核人）")
    if status == "dirty":
        errors.append(f"{fname}: status=dirty（已定稿后被修改）——请重新审核："
                      "用户确认后置 approved、version 递增")

    fence = _MERMAID_FENCE.search(body)
    if not fence:
        errors.append(f"{fname}: 缺少 ```mermaid 围栏代码块（front-matter 之后）")
        return errors, warnings, info
    diagram = fence.group(1)
    lines = [ln.strip() for ln in diagram.splitlines() if ln.strip()
             and not ln.strip().startswith("%%")]

    graph_type, first_line = analysis.FLOW_KIND_MAP[kind]
    if not lines:
        errors.append(f"{fname}: mermaid 图内容为空")
        return errors, warnings, info
    if not lines[0].startswith(graph_type.split()[0]):
        errors.append(f"{fname}: 图类型须为 {graph_type}（文件名后缀 _{kind} 决定，"
                      f"实际首行 '{lines[0]}'）")
        return errors, warnings, info
    if kind == "flow" and not re.match(r"^flowchart\s+(TD|LR)\b", lines[0]):
        errors.append(f"{fname}: 顺序流程图首行须为 flowchart TD（竖向，兼容历史 LR），实际 '{lines[0]}'")
    if kind == "state":
        if "[*]" not in diagram:
            errors.append(f"{fname}: stateDiagram-v2 必须标注 [*] 初始态/终态")
        parsed = analysis._parse_state_diagram(diagram)
        bad = [n for n in parsed["nodes"] if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", n)]
        if bad:
            warnings.append(f"{fname}: 状态名应全大写下划线（如 LED_ON），"
                            f"不合规：{', '.join(bad[:5])}")
    if kind == "sequence":
        parsed = analysis._parse_sequence_diagram(diagram)
        if not parsed["nodes"]:
            errors.append(f"{fname}: sequenceDiagram 未解析到任何参与者/消息")
    info["status"] = status
    info["version"] = meta.get("version")
    return errors, warnings, info


def validate_flows(flow_dir: Path) -> tuple[list[str], list[str], list[dict]]:
    """校验 docs/flow/ 全部流程图 + 同模块多图检查。返回 (errors, warnings, infos)。"""
    errors: list[str] = []
    warnings: list[str] = []
    infos: list[dict] = []
    files = analysis.scan_flow_dir(flow_dir)
    # 命名不合规的文件也要报告（scan_flow_dir 跳过的）
    for p in sorted(flow_dir.glob("*.md")) if flow_dir.is_dir() else []:
        if not re.match(r"^(.+?)_(state|flow|sequence)\.md$", p.name):
            errors.append(f"{p.name}: 文件名须为 <模块>_<state|flow|sequence>.md（无法解析，已跳过）")
    modules: dict[str, int] = {}
    for item in files:
        e, w, info = validate_flow_file(item["path"], flow_dir)
        errors.extend(e)
        warnings.extend(w)
        infos.append(info)
        modules[item["module"]] = modules.get(item["module"], 0) + 1
    for module, count in modules.items():
        if count > 1:
            errors.append(f"模块 {module} 有 {count} 张流程图（一个模块只允许一张主图；"
                          "复合逻辑请拆子模块，如图类型确实不同请并入模块名，如 app_wifi_seq）")
    return errors, warnings, infos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S5b 流程图规范校验")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    parser.add_argument("--file", default=None, help="只校验指定流程图文件（调试用）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        return 2

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = workspace / args.file
        errors, warnings, _ = validate_flow_file(path, ctx["flow_dir"])
    else:
        errors, warnings, _ = validate_flows(ctx["flow_dir"])

    for w in warnings:
        _log(f"警告: {w}")
    if errors:
        _log(f"流程图校验失败（{len(errors)} 项错误，Agent 修正后重跑）:")
        for e in errors:
            _log(f"  - {e}")
        print(json.dumps({"flow_validation": {"ok": False, "errors": errors,
                                              "warnings": warnings}}, ensure_ascii=False, indent=2))
        return EXIT_INVALID
    _log(f"流程图校验通过（{len(warnings)} 条警告）")
    print(json.dumps({"flow_validation": {"ok": True, "errors": [],
                                          "warnings": warnings}}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
