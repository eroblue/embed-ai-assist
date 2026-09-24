#!/usr/bin/env python
"""S5b diff_range_checker：增量生成后 diff 范围校验（拦截异常重写）。

这是防止 Agent 手抖重写全文件的关键防线（requirement"diff 范围校验"）：
- 基线：prepare 段镜像的 outputs/s5b/code_baseline/（上轮产物副本）+
  code_snapshot.json（sha256/行数索引）
- 预期：增量模块的代码变更行数应与流程图变更点数量成正比
  （每变更点预期 ≤ EXPECTED_LINES_PER_CHANGE 行，超出 3 倍 → 异常）
- 重写特征：删除行数 ≥ 基线行数 80% 且变更点少 → 异常（整文件重写）
- 异常处理：写 outputs/s5b/diff_anomaly.json，state.s5b.status=error，
  退出码 1；当前文件保留现状供人工审核（上轮内容在 code_baseline/ 可对照）

只校验 flow_diffs 中 generation_mode=incremental 的模块（full=新建/重构，
skip=无改动，均不检查）。退出码：0=正常；1=范围异常；2=环境错误。
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import layout_resolver  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_ANOMALY = 1
EXIT_CONFIG_ERROR = 2

# 每个流程图变更点对应的预期代码行数上限；超出 3 倍判异常（requirement 阈值）
EXPECTED_LINES_PER_CHANGE = 15
ANOMALY_FACTOR = 3
REWRITE_RATIO = 0.80  # 删除行 ≥ 基线 80% 判整文件重写特征


def _log(msg: str) -> None:
    print(f"[s5b-diff-range] {msg}", file=sys.stderr)


def _diff_stats(old: str, new: str) -> tuple[int, int]:
    """unified diff 统计（新增行, 删除行）；空行差异不计。"""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    added = removed = 0
    for ln in difflib.unified_diff(old_lines, new_lines, lineterm="", n=0):
        if ln.startswith("+") and not ln.startswith("+++") and ln.strip() != "+":
            added += 1
        elif ln.startswith("-") and not ln.startswith("---") and ln.strip() != "-":
            removed += 1
    return added, removed


def check_module(ctx: dict, module: str, change_count: int,
                 src_dirs: list[Path], inc_dirs: list[Path]) -> dict:
    """校验单模块增量代码的 diff 范围。返回 {module, status, files: [...]}。"""
    baseline_dir = ctx["outputs_dir"] / "s5b" / "code_baseline"
    expected = max(change_count * EXPECTED_LINES_PER_CHANGE, EXPECTED_LINES_PER_CHANGE)
    report = {"module": module, "status": "ok", "files": []}

    # 定位模块代码文件（模块名 = 文件基名）
    targets: list[Path] = []
    for d in src_dirs + inc_dirs:
        if d.is_dir():
            targets.extend(sorted(d.glob(f"{module}.[ch]")))
    if not targets:
        report["status"] = "missing"
        report["detail"] = (f"未找到模块 {module} 的代码文件（{module}.c/h）——"
                            "增量模式要求文件已存在")
        return report

    anomalies: list[str] = []
    for f in targets:
        rel = str(f.resolve().relative_to(ctx["workspace"])).replace("\\", "/")
        base_file = baseline_dir / rel
        if not base_file.is_file():
            report["files"].append({"file": rel, "note": "无基线（本轮新增），不检查"})
            continue
        old = base_file.read_text(encoding="utf-8", errors="replace")
        new = f.read_text(encoding="utf-8", errors="replace")
        if old == new:
            report["files"].append({"file": rel, "added": 0, "removed": 0, "note": "无变更"})
            continue
        added, removed = _diff_stats(old, new)
        old_lines = len(old.splitlines())
        entry = {"file": rel, "added": added, "removed": removed,
                 "baseline_lines": old_lines}
        if added > ANOMALY_FACTOR * expected:
            anomalies.append(
                f"{rel}: 新增 {added} 行，超预期 3 倍（变更点 {change_count} → 预期 ≤ "
                f"{ANOMALY_FACTOR * expected} 行）")
            entry["anomaly"] = "added_overflow"
        if removed >= REWRITE_RATIO * old_lines and change_count * EXPECTED_LINES_PER_CHANGE < old_lines:
            anomalies.append(
                f"{rel}: 删除 {removed}/{old_lines} 行（≥{REWRITE_RATIO:.0%}），"
                "整文件重写特征（增量模式应定点修改）")
            entry["anomaly"] = "rewrite"
        report["files"].append(entry)

    if anomalies:
        report["status"] = "anomaly"
        report["anomalies"] = anomalies
    return report


def run_check(ctx: dict, src_dirs: list[Path], inc_dirs: list[Path],
              module_filter: str | None = None) -> tuple[list[dict], list[dict]]:
    """对全部 incremental 模块执行范围校验。返回 (reports, anomalies)。"""
    diffs_dir = ctx["outputs_dir"] / "s5b" / "flow_diffs"
    reports: list[dict] = []
    anomalies: list[dict] = []
    if not diffs_dir.is_dir():
        return reports, anomalies
    for diff_file in sorted(diffs_dir.glob("*_diff.json")):
        try:
            diff = analysis.load_json(diff_file)
        except (json.JSONDecodeError, OSError):
            continue
        if diff.get("generation_mode") != "incremental":
            continue
        module = diff.get("module", "")
        if module_filter and module != module_filter:
            continue
        report = check_module(ctx, module, int(diff.get("change_count", 0)),
                              src_dirs, inc_dirs)
        reports.append(report)
        if report["status"] == "anomaly":
            anomalies.append(report)
    return reports, anomalies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5b 增量代码 diff 范围校验（增量生成后调用）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    parser.add_argument("--module", default=None, help="只校验指定模块")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    try:
        ctx = analysis.load_context(config_path, workspace)
        plan = layout_resolver.resolve_layout(workspace, ctx["config"], ctx["state"])
        src_dirs = [ctx["workspace"] / d for d in plan["skill_dirs"]["s5b"]["src"]]
        inc_dirs = [ctx["workspace"] / d for d in plan["skill_dirs"]["s5b"]["inc"]]
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError,
            layout_resolver.LayoutError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR

    reports, anomalies = run_check(ctx, src_dirs, inc_dirs, args.module)
    now = datetime.now().isoformat(timespec="seconds")
    analysis.save_json(ctx["outputs_dir"] / "s5b" / "diff_check_result.json",
                       {"reports": reports, "anomaly_count": len(anomalies), "updated_at": now})

    if anomalies:
        anomaly_payload = {
            "anomalies": anomalies,
            "advice": ("增量生成 diff 范围异常，请人工审核：上轮内容见 "
                       "outputs/s5b/code_baseline/，可对照恢复；确认定点修改"
                       "或经用户同意转全量（流程图 version 递增后重走 flow_differ）"),
            "updated_at": now,
        }
        analysis.save_json(ctx["outputs_dir"] / "s5b" / "diff_anomaly.json", anomaly_payload)
        # state.s5b = error（报警处理，requirement）；锁内更新，保留
        # rtos/architecture/power_enabled 等字段（prepare 配置变化检测依赖）
        def _mark_error(st: dict) -> None:
            cur = st.get("s5b") or {}
            cur.update({"status": "error",
                        "error": "增量生成 diff 范围异常（见 outputs/s5b/diff_anomaly.json）",
                        "updated_at": now})
            st["s5b"] = cur
        try:
            state_store.update_state(ctx["state_path"], _mark_error)
        except (OSError, state_store.StateLockTimeout):
            pass
        _log("diff 范围异常（state 已置 error）:")
        for a in anomalies:
            for msg in a.get("anomalies", []):
                _log(f"  - {msg}")
        print(json.dumps({"diff_range_check": {"ok": False, "anomaly_count": len(anomalies)}},
                         ensure_ascii=False, indent=2))
        return EXIT_ANOMALY

    _log(f"diff 范围校验通过（{len(reports)} 个增量模块）")
    print(json.dumps({"diff_range_check": {"ok": True, "checked_modules":
                                           [r["module"] for r in reports]}},
                     ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
