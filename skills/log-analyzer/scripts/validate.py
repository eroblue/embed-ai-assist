"""Validate S11 Agent output and update an existing project state when requested."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import analysis


def update_state(target_root: Path, output_dir: Path, index: dict, result: dict) -> None:
    state_path = target_root / "state.json"
    if not state_path.is_file():
        print("未发现 state.json；本次分析独立完成，未创建 state。")
        return
    try:
        state = analysis.load_json(state_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise analysis.S11Error(f"无法读取 state.json：{exc}") from exc
    def relative(path: Path) -> str:
        try:
            return path.resolve().relative_to(target_root.resolve()).as_posix()
        except ValueError:
            return str(path.resolve()).replace("\\", "/")
    summary = {
        "status": "done",
        "analysis_id": result["analysis_id"],
        "source_count": len(index["sources"]),
        "finding_count": len(result["findings"]),
        "source_index_path": relative(output_dir / "source_index.json"),
        "analysis_path": relative(output_dir / "analysis.json"),
        "report_path": relative(output_dir / "report.md"),
        "updated_at": analysis.utc_now(),
        "error": None,
    }
    errors = analysis.schema_errors(summary, analysis.SKILL_DIR / "schemas" / "output.schema.json", "s11")
    if errors:
        raise analysis.S11Error("state.s11 契约无效：" + "; ".join(errors))
    state["s11"] = summary
    analysis.save_json(state_path, state)
    print(f"已更新 {state_path} 的 s11 字段。")


def main() -> int:
    parser = argparse.ArgumentParser(description="S11：校验证据引用并收口分析结果")
    parser.add_argument("--analysis-dir", required=True, type=Path, help="prepare.py 输出的分析目录")
    args = parser.parse_args()
    output_dir = args.analysis_dir.expanduser().resolve()
    try:
        index_path = output_dir / "source_index.json"
        result_path = output_dir / "analysis.json"
        report_path = output_dir / "report.md"
        context_path = output_dir / "prepare_context.json"
        for path in (index_path, result_path, report_path, context_path):
            if not path.is_file():
                raise analysis.S11Error(f"缺少必需产物：{path.name}")
        index = analysis.load_json(index_path)
        result = analysis.load_json(result_path)
        context = analysis.load_json(context_path)
        errors = analysis.schema_errors(index, analysis.SKILL_DIR / "schemas" / "source_index.schema.json", "source_index")
        errors += analysis.schema_errors(result, analysis.SKILL_DIR / "schemas" / "analysis.schema.json", "analysis")
        if errors:
            raise analysis.S11Error("契约校验失败：" + "; ".join(errors))
        if result["analysis_id"] != index["analysis_id"] or result["analysis_id"] != context["analysis_id"]:
            raise analysis.S11Error("analysis_id 在结果、索引和准备上下文中不一致。")
        if not result["summary"].strip():
            raise analysis.S11Error("analysis.json 的 summary 不能为空。")
        if not report_path.read_text(encoding="utf-8").strip():
            raise analysis.S11Error("report.md 不能为空。")
        valid_ids = {row["evidence_id"] for source in index["sources"] for row in source["evidence"]}
        bad_refs = [(finding["finding_id"], evidence_id)
                    for finding in result["findings"]
                    for evidence_id in finding["evidence_ids"]
                    if evidence_id not in valid_ids]
        if bad_refs:
            details = ", ".join(f"{finding} → {evidence}" for finding, evidence in bad_refs)
            raise analysis.S11Error(f"发现无效 evidence ID：{details}")
        project_config = context.get("project_config")
        if project_config:
            target_root = Path(context["target_root"])
            update_state(target_root, output_dir, index, result)
        else:
            print("未提供项目 config；未修改任何 state.json。")
        print(f"S11 校验通过：{len(result['findings'])} 条 finding，{len(valid_ids)} 条证据。")
        print(f"报告：{report_path}")
        return 0
    except (analysis.S11Error, OSError, json.JSONDecodeError) as exc:
        print(f"[S11 校验失败] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
