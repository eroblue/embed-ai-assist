#!/usr/bin/env python
"""S5b flow_differ：流程图 diff 与生成模式判定（rule 轨，流程图 approved 后调用）。

增量生成的核心：没有 diff，每次改动就会重跑整个模块，代码全变。

机制（requirement"流程图 diff 机制"）：
- 基线：docs/flow/.history/<模块>/<版本>.md 快照（flow_differ 自动维护，
  不依赖 git；git 提交历史为首选长期方案，.history 为本工具的确定性基线）
- diff 粒度：stateDiagram（状态/迁移/动作）、flowchart（节点/边/条件，
  含按 label 匹配的重命名检测）、sequenceDiagram（参与者/消息/返回）
- 模式判定：首次无基线 → full；变化率 > 60% → full（大重构，提示确认）；
  ≤ 60% → incremental；无变更 → skip；未 approved → blocked（不生成代码）
- dirty 拦截：approved 流程图内容被修改但 version 未递增 → blocked，
  要求重新审核（status 置 dirty → 用户确认 → version+1 → 再 approved）
- 产物：outputs/s5b/flow_diffs/<模块>_diff.json（schema 校验）+
  更新 outputs/s5b/flow_index.json（approved/deprecated 流程图登记）

退出码：0=完成；1=diff 结果契约校验失败；2=环境错误。
validate.py 终验复用本模块的 diff_all()。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_CONFIG_ERROR = 2

# 变化率阈值（requirement：> 60% 判大重构走全量）
FULL_RATIO_THRESHOLD = 0.60


def _log(msg: str) -> None:
    print(f"[s5b-flow-differ] {msg}", file=sys.stderr)


def _edge_str(edge: tuple[str, str, str]) -> str:
    return f"{edge[0]} -> {edge[1]}" + (f" [{edge[2]}]" if edge[2] else "")


def _version_le(a, b) -> bool:
    """版本号比较（'1.0'/'1.1'/'2'），解析失败按字符串比较。"""

    def _key(v):
        try:
            return tuple(int(x) for x in str(v).split("."))
        except ValueError:
            return (str(v),)

    try:
        return _key(a) <= _key(b)
    except TypeError:
        return str(a) <= str(b)


def _norm_edges(edges: set[tuple[str, str, str]],
                rename: dict[str, str]) -> set[tuple[str, str, str]]:
    """对旧边集合应用重命名映射（旧名 → 新名），便于 renamed 后的边比对。"""
    if not rename:
        return set(edges)
    return {(rename.get(f, f), rename.get(t, t), lbl) for f, t, lbl in edges}


def diff_graph(prev: dict, curr: dict, graph_type: str) -> dict:
    """两张同类型图的节点/边 diff（prev/curr 为 parse_mermaid 输出）。

    flowchart 按 label 匹配检测重命名；stateDiagram/sequenceDiagram 节点名即
    身份，重命名报为 remove+add（renamed 置空）。
    """
    prev_nodes = set(prev["nodes"])
    curr_nodes = set(curr["nodes"])
    added_nodes = sorted(curr_nodes - prev_nodes)
    removed_nodes = sorted(prev_nodes - curr_nodes)
    renamed: list[dict] = []
    rename_map: dict[str, str] = {}

    if graph_type == "flowchart":
        prev_labels = prev.get("node_labels") or {}
        curr_labels = curr.get("node_labels") or {}
        removed_left = list(removed_nodes)
        for add in list(added_nodes):
            label = curr_labels.get(add)
            for rem in removed_left:
                if prev_labels.get(rem) == label and label:
                    renamed.append({"from": rem, "to": add})
                    rename_map[rem] = add
                    added_nodes.remove(add)
                    removed_left.remove(rem)
                    break
        removed_nodes = removed_left

    prev_edges = _norm_edges(set(prev["edges"]), rename_map)
    curr_edges = set(curr["edges"])
    added_edges = sorted(_edge_str(e) for e in curr_edges - prev_edges)
    removed_edges = sorted(_edge_str(e) for e in prev_edges - curr_edges)
    # 起止点相同但标签变化的边 → modified
    prev_by_pair = {(f, t): lbl for f, t, lbl in prev_edges}
    modified_edges = []
    for f, t, lbl in curr_edges:
        if (f, t) in prev_by_pair and prev_by_pair[(f, t)] != lbl:
            modified_edges.append(_edge_str((f, t, lbl)))
    modified_edges.sort()

    change_count = (len(added_nodes) + len(removed_nodes) + len(renamed)
                    + len(added_edges) + len(removed_edges) + len(modified_edges))
    total = len(curr_nodes) + len(curr_edges)
    ratio = change_count / max(total, 1)
    return {
        "nodes": {"total": len(curr_nodes), "added": added_nodes,
                  "removed": removed_nodes, "renamed": renamed},
        "edges": {"total": len(curr_edges), "added": added_edges,
                  "removed": removed_edges, "modified": modified_edges},
        "change_count": change_count,
        "change_ratio": round(ratio, 4),
    }


def diff_one(item: dict, index_entry: dict | None, flow_dir: Path) -> tuple[dict, dict | None]:
    """单模块 diff。返回 (diff_result, index_entry_new)。

    index_entry_new 为 None 表示不登记进 flow_index（draft/review/dirty/blocked）。
    """
    module, kind, path = item["module"], item["kind"], item["path"]
    graph_type, _ = analysis.FLOW_KIND_MAP[kind]
    text = path.read_text(encoding="utf-8-sig")
    meta, body = analysis.parse_front_matter(text)
    status = str((meta or {}).get("status") or "draft")
    version = (meta or {}).get("version")
    h = analysis.content_hash(body)
    now = datetime.now().isoformat(timespec="seconds")
    file_rel = analysis.flow_rel_path(flow_dir, path)

    result = {
        "module": module, "file": file_rel, "graph_type": graph_type,
        "base_version": None, "current_version": version, "status": status,
        "nodes": {"total": 0, "added": [], "removed": [], "renamed": []},
        "edges": {"total": 0, "added": [], "removed": [], "modified": []},
        "change_count": 0, "change_ratio": 0.0,
        "generation_mode": "blocked", "baseline_source": None,
        "change_summary": None, "updated_at": now,
    }

    if status == "deprecated":
        result["generation_mode"] = "deprecated"
        result["change_summary"] = "流程图已废弃：对应代码应由 Agent 移除（含 IDE 工程引用）"
        return result, _index_entry(module, file_rel, graph_type, version,
                                    (meta or {}).get("base_version"), status, h,
                                    result["nodes"]["total"], result["edges"]["total"], now)

    if status in ("draft", "review", "dirty"):
        result["change_summary"] = (
            f"status={status}，未定稿：不生成代码"
            + ("（approved 后被修改，需重新审核并 version 递增）" if status == "dirty" else ""))
        return result, None

    # ---- approved ----
    parsed = analysis.parse_mermaid(_mermaid_body(body), graph_type)
    result["nodes"]["total"] = len(parsed["nodes"])
    result["edges"]["total"] = len(parsed["edges"])

    if index_entry is None:
        # 首次登记（无上轮生成记录）→ full
        result["generation_mode"] = "full"
        result["change_summary"] = "首次生成（flow_index 无记录），全量生成模块代码"
    elif index_entry.get("hash") == h:
        result["generation_mode"] = "skip"
        result["change_summary"] = "流程图与上轮一致，跳过代码生成"
    else:
        prev_version = index_entry.get("version")
        if version is not None and prev_version is not None and _version_le(version, prev_version):
            result["status"] = "dirty"
            result["generation_mode"] = "blocked"
            if str(version) == str(prev_version):
                # 同版本号但内容变了 → dirty（应重新审核 + version 递增）
                result["change_summary"] = (
                    f"approved 流程图内容被修改但 version 未递增（仍为 {version}）："
                    "请将 status 置 dirty，重新审核后 version+1 再 approved")
            else:
                # 版本回退（如 1.2 → 1.1）→ 需人工确认回退意图
                result["change_summary"] = (
                    f"流程图版本回退（{prev_version} → {version}）："
                    "请人工确认回退意图，重新审核后递增 version 再 approved")
            return result, None
        baseline_path = flow_dir / ".history" / module / f"{prev_version}.md"
        if baseline_path.is_file():
            b_text = baseline_path.read_text(encoding="utf-8-sig")
            _, b_body = analysis.parse_front_matter(b_text)
            # 基线完整性：index 记录的 hash 应与基线快照正文一致
            #（.history 或 flow_index 被手工修改时告警，避免 diff 基于错误基线）
            if analysis.content_hash(b_body) != index_entry.get("hash"):
                _log(f"[warn] {module}: 基线快照 {baseline_path.name} 正文与 flow_index"
                     " 记录的 hash 不一致（可能被手工修改），diff 结果可能失真，建议核对")
                result["baseline_mismatch"] = True
            prev_parsed = analysis.parse_mermaid(_mermaid_body(b_body), graph_type)
            diff = diff_graph(prev_parsed, parsed, graph_type)
            result.update(diff)
            result["base_version"] = str(prev_version)
            result["baseline_source"] = str(baseline_path.resolve().relative_to(
                flow_dir.parents[1])).replace("\\", "/")
            if result["change_count"] == 0:
                result["generation_mode"] = "skip"
                result["change_summary"] = "内容变化但节点/边无实质变更，跳过代码生成"
            elif result["change_ratio"] > FULL_RATIO_THRESHOLD:
                result["generation_mode"] = "full"
                result["change_summary"] = (
                    f"变化率 {result['change_ratio']:.0%} > {FULL_RATIO_THRESHOLD:.0%}（大重构），"
                    "全量生成（建议提示工程师确认）")
            else:
                result["generation_mode"] = "incremental"
                added = result["nodes"]["added"] + result["edges"]["added"][:2]
                result["change_summary"] = (
                    f"变化率 {result['change_ratio']:.0%}，变更 {result['change_count']} 处"
                    + (f"（如 {', '.join(added[:3])}）" if added else ""))
        else:
            result["generation_mode"] = "full"
            result["change_summary"] = (
                f"基线快照缺失（.history/{module}/{prev_version}.md），按全量生成")

    entry = _index_entry(module, file_rel, graph_type, version,
                         (meta or {}).get("base_version"), status, h,
                         result["nodes"]["total"], result["edges"]["total"], now)
    # 保存当前版本快照（供下轮 diff 基线）
    if result["generation_mode"] in ("full", "incremental", "skip"):
        snap_dir = flow_dir / ".history" / module
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap = snap_dir / f"{version}.md"
        if not snap.is_file():
            snap.write_text(text, encoding="utf-8", newline="\n")
    return result, entry


def _index_entry(module, file_rel, graph_type, version, base_version, status,
                 h, nodes, edges, now) -> dict:
    return {"module": module, "file": file_rel, "graph_type": graph_type,
            "version": version, "base_version": base_version, "status": status,
            "hash": h, "nodes": nodes, "edges": edges, "updated_at": now}


def _mermaid_body(body: str) -> str:
    """提取 mermaid 围栏内容（无围栏时按原文解析，兼容手写文件）。"""
    import re
    m = re.search(r"```mermaid\s*\n(.*?)```", body, re.S)
    return m.group(1) if m else body


def diff_all(ctx: dict, module_filter: str | None = None) -> tuple[dict, list[dict]]:
    """对 docs/flow/ 全部（或指定模块）流程图执行 diff。

    返回 (flow_index_new, diff_results)；flow_diffs/*.json 与 flow_index.json
    已写盘（schema 校验失败抛 RuntimeError）。
    """
    flow_dir = ctx["flow_dir"]
    index_path = ctx["outputs_dir"] / "s5b" / "flow_index.json"
    index: dict = {"flows": [], "updated_at": ""}
    if index_path.is_file():
        try:
            index = analysis.load_json(index_path)
        except (json.JSONDecodeError, OSError):
            index = {"flows": [], "updated_at": ""}
    by_module = {f.get("module"): f for f in index.get("flows", [])}
    # 上轮已废弃的登记保留（Agent 移除代码后 validate 收口）
    keep_entries = {m: e for m, e in by_module.items() if e.get("status") == "deprecated"}

    results: list[dict] = []
    new_entries: dict[str, dict] = dict(keep_entries)
    for item in analysis.scan_flow_dir(flow_dir):
        if module_filter and item["module"] != module_filter:
            continue
        result, entry = diff_one(item, by_module.get(item["module"]), flow_dir)
        results.append(result)
        if entry is not None:
            new_entries[result["module"]] = entry
        elif item["module"] in by_module:
            # 未定稿（draft/review/dirty/blocked）：沿用上轮登记——dirty 恢复
            # （version 递增再 approved）后仍能 diff 到旧基线，保持增量语义
            new_entries[item["module"]] = by_module[item["module"]]
        errs = analysis.validate_schema(
            result, SKILL_DIR / "schemas" / "flow_diff.schema.json", f"flow_diff({result['module']})")
        if errs:
            raise RuntimeError("; ".join(errs))
        out = ctx["outputs_dir"] / "s5b" / "flow_diffs" / f"{result['module']}_diff.json"
        analysis.save_json(out, result)
        _log(f"{result['module']}: {result['generation_mode']}"
             + (f"（{result['change_summary']}）" if result["change_summary"] else ""))

    # 已从 docs/flow/ 消失的非废弃登记 → 报告（文件被删，代码应清理）
    for m, e in by_module.items():
        if m not in new_entries and e.get("status") != "deprecated":
            _log(f"警告: 模块 {m} 的流程图文件已不存在（{e.get('file')}），"
                 f"对应代码 {m}.c/h 应由 Agent 移除")

    index_new = {"flows": sorted(new_entries.values(), key=lambda x: x["module"]),
                 "updated_at": datetime.now().isoformat(timespec="seconds")}
    errs = analysis.validate_schema(
        index_new, SKILL_DIR / "schemas" / "flow_index.schema.json", "flow_index")
    if errs:
        raise RuntimeError("flow_index 契约校验失败: " + "; ".join(errs))
    analysis.save_json(index_path, index_new)
    return index_new, results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5b 流程图 diff + 生成模式判定（approved 后调用）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    parser.add_argument("--module", default=None, help="只 diff 指定模块（缺省全部）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    try:
        ctx = analysis.load_context(config_path, workspace)
        index, results = diff_all(ctx, args.module)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR if "契约校验" not in str(exc) else EXIT_INVALID

    modes = {r["module"]: r["generation_mode"] for r in results}
    _log(f"flow_index 已更新（{len(index['flows'])} 条登记）")
    print(json.dumps({"flow_diffs": modes,
                      "flow_count": len(results)}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
