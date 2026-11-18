"""Validate S8 results, write a scoped report, update only state.s8."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import SKILL_DIR, context, digest, now, read_json, rel, schema_validate, update_state


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()
    try:
        _, _, target = context(args.config)
        run_dir = Path(args.run_dir).resolve()
        if not run_dir.is_relative_to((target / "outputs" / "s8").resolve()):
            raise ValueError("run-dir must be under target/outputs/s8")
        inv = read_json(run_dir / "unit_inventory.json")
        selection = read_json(run_dir / "selection.json")
        result = read_json(run_dir / "result.json")
        manifest = read_json(run_dir / "run_manifest.json")
        for file, schema in ((inv, "unit_inventory"), (selection, "selection"),
                             (result, "result"), (manifest, "run_manifest")):
            schema_validate(file, SKILL_DIR / "schemas" / f"{schema}.schema.json")
        if result["run_id"] != run_dir.name or manifest["run_id"] != run_dir.name:
            raise ValueError("run ID mismatch")
        if set(selection["planned"]) != set(selection["batch"] + selection["deferred"]):
            raise ValueError("selection accounting mismatch")
        if set(selection["batch"]) != {u["unit_id"] for u in result["units"]}:
            raise ValueError("result does not cover selected batch")
        if selection["candidate_count"] != len(inv["units"]):
            raise ValueError("candidate count mismatch")
        case_passed = sum(c["status"] == "passed" for u in result["units"] for c in u.get("cases", []))
        case_failed = sum(c["status"] == "failed" for u in result["units"] for c in u.get("cases", []))
        if (result["passed_count"], result["failed_count"]) != (case_passed, case_failed):
            raise ValueError("case count mismatch")
        stale = []
        for path, expected in manifest["source_hashes"].items():
            file = (target / path).resolve()
            if not file.is_relative_to(target.resolve()) or not file.is_file() or digest(file) != expected:
                stale.append(path)
        if stale:
            raise ValueError("source changed during run: " + ", ".join(stale))
        units = result["units"]
        passed = sum(u["status"] == "passed" for u in units)
        failed = sum(u["status"] == "failed" for u in units)
        unready = len(units) - passed - failed
        needs_clarification = sum(u["status"] == "needs_clarification" for u in units)
        not_testable = sum(u["status"] == "not_testable_on_host" for u in units)
        skipped = sum(u["status"] == "skipped" for u in units)
        status = "failed" if failed else "partial" if passed and unready else "done" if passed else "blocked"
        status_cn = {"done": "本轮全部通过", "partial": "部分完成", "failed": "测试失败", "blocked": "未能执行"}
        unit_status_cn = {"passed": "通过", "failed": "失败", "needs_clarification": "待补测试计划或预期",
                          "not_testable_on_host": "不适合主机测试", "skipped": "跳过"}
        reason_cn = {"no reviewed test plan": "尚无已复核的测试计划", "test compilation failed": "测试程序编译失败",
                     "test timeout": "测试运行超时"}
        ratio = selection["requested_ratio"]
        ratio_text = f"{ratio:.0%}" if isinstance(ratio, (int, float)) else "未设置"
        report = [f"# S8 单元测试报告：{run_dir.name}", "", f"**本轮状态：{status_cn[status]}（`{status}`）**", "",
                  f"候选源码模块：{selection['candidate_count']} 个；清单边界尚未逐个复核，比例分母为暂定值。",
                  f"选择模式：`{selection['mode']}`；配置比例：{ratio_text}；计划纳入：{len(selection['planned'])} 个；"
                  f"本批选择：{len(selection['batch'])} 个；延期：{len(selection['deferred'])} 个；未选：{len(selection['unselected'])} 个。",
                  f"模块结果：通过 {passed} 个，失败 {failed} 个，待补计划 {needs_clarification} 个，"
                  f"需实机验证 {not_testable} 个，跳过 {skipped} 个。"
                  f"用例结果：通过 {case_passed} 个，失败 {case_failed} 个。", "",
                  "## 本批模块结果", ""]
        report += [f"- `{u['unit_id']}`：{unit_status_cn[u['status']]}" +
                   (f"；原因：{reason_cn.get(u.get('reason', ''), u['reason'])}" if u.get("reason") else "")
                   for u in units]
        report += ["", "## 尚未验证的范围", "",
                   f"延期模块：{', '.join(f'`{x}`' for x in selection['deferred']) or '无'}。",
                   f"未选模块：{', '.join(f'`{x}`' for x in selection['unselected']) or '无'}。",
                   f"需实机验证：{not_testable} 个模块。主机侧 Mock 测试不能证明其寄存器、电气或时序行为。",
                   "源码扫描得到的是候选模块清单；本报告不能作为代码覆盖率或整机验收结论。", "",
                   "## 证据文件", "",
                   "本目录中的 `selection.json`、`run_manifest.json`、`result.json`、`build.log` 和 `test.log` 可用于回查。", ""]
        (run_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
        payload = {"status": status, "run_id": run_dir.name,
                   "result_path": rel(target, run_dir / "result.json"),
                   "report_path": rel(target, run_dir / "report.md"),
                   "selected_unit_count": len(selection["batch"]),
                   "executed_unit_count": passed + failed,
                   "remaining_unit_count": len(selection["deferred"]),
                   "passed_count": result["passed_count"], "failed_count": result["failed_count"],
                   "needs_clarification_count": needs_clarification,
                   "not_testable_on_host_count": not_testable, "skipped_count": skipped,
                   "updated_at": now(),
                   "error": None if status == "done" else "部分模块尚无可执行测试" if status == "partial" else "测试失败或没有可执行用例"}
        schema_validate(payload, SKILL_DIR / "schemas" / "output.schema.json")
        update_state(target / "state.json", {"s8": payload})
        print(run_dir / "report.md")
        return {"done": 0, "failed": 1, "blocked": 2, "partial": 3}[status]
    except (ValueError, OSError, ImportError, KeyError) as exc:
        print(f"S8 validate error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
