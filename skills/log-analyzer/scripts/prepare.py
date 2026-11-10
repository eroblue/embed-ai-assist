"""Prepare a compact S11 evidence index and Agent analysis brief."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

import analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="S11：建立日志证据索引与分析任务书")
    parser.add_argument("sources", nargs="+", type=Path, help="文本日志路径或 S10 会话目录")
    parser.add_argument("--encoding", default="utf-8", help="普通文本日志编码，默认 utf-8")
    parser.add_argument("--project-config", type=Path, help="项目 config.json；用于确定输出位置并收口已有 state")
    parser.add_argument("--output-dir", type=Path, help="本次分析目录；传入完整的 analysis 输出目录")
    parser.add_argument("--observation", help="用户观察描述，作为用户陈述提供给 Agent")
    args = parser.parse_args()

    try:
        request = {
            "sources": [str(path) for path in args.sources],
            "encoding": args.encoding,
            "project_config": str(args.project_config) if args.project_config else None,
            "output_dir": str(args.output_dir) if args.output_dir else None,
            "observation": args.observation,
        }
        errors = analysis.schema_errors(request, analysis.SKILL_DIR / "schemas" / "input.schema.json", "input")
        if errors:
            raise analysis.S11Error("输入契约无效：" + "; ".join(errors))
        sources = analysis.resolve_sources(args.sources)
        analysis_id = analysis.utc_now().replace("-", "").replace(":", "").replace("+", "")[:15] + "-" + uuid.uuid4().hex[:8]

        config_path = args.project_config.expanduser().resolve() if args.project_config else None
        if config_path:
            if not config_path.is_file():
                raise analysis.S11Error(f"项目 config.json 不存在：{config_path}")
            config = analysis.load_json(config_path)
            if not isinstance(config, dict):
                raise analysis.S11Error("项目 config.json 顶层必须是 JSON object。")
            project = config.get("project") or {}
            if not isinstance(project, dict):
                raise analysis.S11Error("项目 config.json 中的 project 必须是 JSON object。")
            target = project.get("build_target") or "App"
            if target not in ("App", "BootLoader"):
                raise analysis.S11Error(f"project.build_target 必须为 App 或 BootLoader，当前为：{target!r}")
            output_dir = config_path.parent / target / "outputs" / "s11" / analysis_id
        elif args.output_dir:
            output_dir = args.output_dir.expanduser().resolve()
        else:
            first_log, first_manifest = sources[0]
            parent = first_log.parent
            if first_manifest and parent.name != "s10" and parent.parent.name == "s10":
                parent = parent.parent.parent.parent
                output_dir = parent / "outputs" / "s11" / analysis_id
            else:
                output_dir = first_log.parent / "s11_analysis" / analysis_id
        index: dict = {"schema_version": "1.0", "analysis_id": analysis_id, "sources": [], "warnings": []}
        for number, (log_path, manifest_path) in enumerate(sources, start=1):
            source_id = f"SRC{number:02d}"
            is_s10 = log_path.name.lower() == "capture.log"
            if is_s10:
                evidence, _, warnings = analysis.read_s10_log(log_path, source_id)
                encoding = "utf-8"
                fmt = "s10_capture_log"
            else:
                evidence, warnings = analysis.read_text_log(log_path, source_id, args.encoding)
                encoding = args.encoding
                fmt = "text"
            context, context_warnings = analysis.session_context(manifest_path)
            warnings.extend(context_warnings)
            try:
                digest = analysis.sha256(log_path)
            except OSError as exc:
                digest = None
                warnings.append(f"无法计算日志 SHA256：{exc}")
            source = {
                "source_id": source_id,
                "path": str(log_path),
                "sha256": digest,
                "format": fmt,
                "encoding": encoding,
                "session_context": context,
                "evidence": evidence,
                "warnings": warnings,
            }
            index["sources"].append(source)
            index["warnings"].extend(f"{source_id}: {warning}" for warning in warnings)

        errors = analysis.schema_errors(index, analysis.SKILL_DIR / "schemas" / "source_index.schema.json", "source_index")
        if errors:
            raise analysis.S11Error("证据索引契约无效：" + "; ".join(errors))
        output_dir.mkdir(parents=True, exist_ok=False)
        analysis.save_json(output_dir / "source_index.json", index)
        brief = analysis.make_brief(index)
        if args.observation:
            brief = brief.replace("只整理日志事实和可说明的归纳；不要读代码、推断根因或选择修复 Skill。",
                                  "只整理日志事实和可说明的归纳；不要读代码、推断根因或选择修复 Skill。\n\n用户观察：\n" + args.observation)
        (output_dir / "analysis_brief.md").write_text(brief, encoding="utf-8", newline="\n")
        skeleton = {
            "schema_version": "1.0",
            "analysis_id": analysis_id,
            "summary": "",
            "user_observation": args.observation,
            "findings": [],
            "limitations": [],
        }
        analysis.save_json(output_dir / "analysis.json", skeleton)
        context = {
            "analysis_id": analysis_id,
            "output_dir": str(output_dir),
            "project_config": str(config_path) if config_path else None,
            "target_root": str(config_path.parent / target) if config_path else None,
        }
        analysis.save_json(output_dir / "prepare_context.json", context)
        print(f"S11 分析目录：{output_dir}")
        print(f"来源：{len(index['sources'])} 个；证据：{sum(len(s['evidence']) for s in index['sources'])} 条；解析警告：{len(index['warnings'])} 条")
        print("下一步：Agent 阅读 analysis_brief.md 与 references/analysis_rules.md，填写 analysis.json 和 report.md；然后运行 validate.py。")
        return 0
    except (analysis.S11Error, OSError, json.JSONDecodeError) as exc:
        print(f"[S11 错误] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
