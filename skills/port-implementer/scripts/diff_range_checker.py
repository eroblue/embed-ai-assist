#!/usr/bin/env python
"""S5c diff_range_checker：增量生成后 diff 范围校验（拦截异常重写）。

这是防止 Agent 手抖重写全文件的关键防线（requirement 阶段 C 步骤 20）：
- 基线：prepare 段镜像的 `outputs/s5c/code_baseline/`（上轮产物副本）+
  `code_snapshot.json`（sha256/行数索引）
- 预期：incremental 单元的代码变更行数应与接口变更点数成正比
  （每变更点预期 ≤ EXPECTED_LINES_PER_CHANGE 行，超出 3 倍 → 异常）
- 重写特征：删除行数 ≥ 基线行数 80% 且变更点少 → 异常（整文件重写）
- 异常处理：写 `outputs/s5c/diff_anomaly.json`，`state.s5c.status=error`，
  退出码 1；当前文件保留现状供人工审核（上轮内容在 code_baseline/ 可对照）

只校验 `port_diffs/*_diff.json` 中 `generation_mode=incremental` 的单元
（full=新建/重构、skip=无改动、blocked/deprecated 均不检查）。

阈值与 S5b `port-contract-and-app/scripts/diff_range_checker.py` 一致
（requirement：判定机制对标 S5b；建议后续提升到 `_shared` 共用，未提升前
本期在 S5c 内独立实现，接受轻度重复）。

退出码：0=正常；1=范围异常；2=环境错误。
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
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_ANOMALY = 1
EXIT_CONFIG_ERROR = 2

# 每个接口变更点对应的预期代码行数上限；超出 3 倍判异常（与 S5b 同阈值）
EXPECTED_LINES_PER_CHANGE = 15
ANOMALY_FACTOR = 3
REWRITE_RATIO = 0.80  # 删除行 ≥ 基线 80% 判整文件重写特征


def _log(msg: str) -> None:
    print(f"[s5c-diff-range] {msg}", file=sys.stderr)


def _diff_stats(old: str, new: str) -> tuple[int, int]:
    """unified diff 统计（新增行, 删除行）；空行差异不计。"""
    added = removed = 0
    for ln in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                   lineterm="", n=0):
        if ln.startswith("+") and not ln.startswith("+++") and ln.strip() != "+":
            added += 1
        elif ln.startswith("-") and not ln.startswith("---") and ln.strip() != "-":
            removed += 1
    return added, removed


def check_unit(ctx: dict, unit_key: str, change_count: int,
               baseline_dir: Path, file_rel: str | None) -> dict:
    """校验单单元增量代码的 diff 范围。返回 {peripheral, status, files: [...]}。"""
    expected = max(change_count * EXPECTED_LINES_PER_CHANGE, EXPECTED_LINES_PER_CHANGE)
    report = {"peripheral": unit_key, "status": "ok", "files": []}

    if not file_rel:
        report["status"] = "missing"
        report["detail"] = (f"增量单元 {unit_key} 未解析到实现文件路径——"
                            "增量模式要求文件已存在（首次生成应为 full）")
        return report
    f = ctx["workspace"] / file_rel
    base_file = baseline_dir / file_rel
    if not f.is_file():
        report["status"] = "missing"
        report["detail"] = f"增量单元 {unit_key} 的实现文件不存在: {file_rel}"
        return report
    if not base_file.is_file():
        report["files"].append({"file": file_rel, "note": "无基线（本轮新增），不检查"})
        return report

    old = base_file.read_text(encoding="utf-8", errors="replace")
    new = f.read_text(encoding="utf-8", errors="replace")
    if old == new:
        report["files"].append({"file": file_rel, "added": 0, "removed": 0,
                                "note": "无变更"})
        return report

    added, removed = _diff_stats(old, new)
    old_lines = len(old.splitlines())
    entry = {"file": file_rel, "added": added, "removed": removed,
             "baseline_lines": old_lines}
    anomalies: list[str] = []
    if added > ANOMALY_FACTOR * expected:
        anomalies.append(
            f"{file_rel}: 新增 {added} 行，超预期 3 倍（变更点 {change_count} → "
            f"预期 ≤ {ANOMALY_FACTOR * expected} 行）")
        entry["anomaly"] = "added_overflow"
    if removed >= REWRITE_RATIO * old_lines \
            and change_count * EXPECTED_LINES_PER_CHANGE < old_lines:
        anomalies.append(
            f"{file_rel}: 删除 {removed}/{old_lines} 行（≥{REWRITE_RATIO:.0%}），"
            "整文件重写特征（增量模式应定点修改）")
        entry["anomaly"] = "rewrite"
    report["files"].append(entry)
    if anomalies:
        report["status"] = "anomaly"
        report["anomalies"] = anomalies
    return report


def run_check(ctx: dict, baseline_dir: Path,
              unit_filter: str | None = None) -> tuple[list[dict], list[dict]]:
    """对全部 incremental 单元执行范围校验。返回 (reports, anomalies)。"""
    diffs_dir = ctx["outputs_dir"] / "s5c" / "port_diffs"
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
        unit_key = diff.get("peripheral", "")
        if unit_filter and unit_key != unit_filter:
            continue
        report = check_unit(ctx, unit_key, int(diff.get("change_count", 0)),
                            baseline_dir, diff.get("file"))
        reports.append(report)
        if report["status"] in ("anomaly", "missing"):
            anomalies.append(report)
    return reports, anomalies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5c 增量代码 diff 范围校验（增量生成后调用）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    parser.add_argument("--unit", default=None, help="只校验指定实现单元")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR

    baseline_dir = ctx["outputs_dir"] / "s5c" / "code_baseline"
    reports, anomalies = run_check(ctx, baseline_dir, args.unit)
    now = datetime.now().isoformat(timespec="seconds")
    analysis.save_json(ctx["outputs_dir"] / "s5c" / "diff_check_result.json",
                       {"reports": reports, "anomaly_count": len(anomalies),
                        "updated_at": now})

    if anomalies:
        analysis.save_json(ctx["outputs_dir"] / "s5c" / "diff_anomaly.json", {
            "anomalies": anomalies,
            "advice": ("增量生成 diff 范围异常，请人工审核：上轮内容见 "
                       "outputs/s5c/code_baseline/，可对照恢复；确认定点修改"
                       "或经用户同意转全量（重跑 prepare 后该单元将判为 full）。"
                       "处置规则见 references/incremental_generation_rules.md 第四节。"),
            "updated_at": now,
        })

        def _mark_error(st: dict) -> None:
            cur = st.get("s5c") or {}
            cur.update({"status": "error",
                        "error": "增量生成 diff 范围异常（见 outputs/s5c/diff_anomaly.json）",
                        "updated_at": now})
            st["s5c"] = cur

        try:
            state_store.update_state(ctx["state_path"], _mark_error)
        except (OSError, state_store.StateLockTimeout):
            pass
        _log("diff 范围异常（state 已置 error）:")
        for a in anomalies:
            for msg in a.get("anomalies", []) or [a.get("detail", "")]:
                _log(f"  - {msg}")
        print(json.dumps({"diff_range_check": {"ok": False,
                                               "anomaly_count": len(anomalies)}},
                         ensure_ascii=False, indent=2))
        return EXIT_ANOMALY

    _log(f"diff 范围校验通过（{len(reports)} 个增量单元）")
    print(json.dumps({"diff_range_check": {
        "ok": True, "checked_units": [r["peripheral"] for r in reports]}},
        ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())