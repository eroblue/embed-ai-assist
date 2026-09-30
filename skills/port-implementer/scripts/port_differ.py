#!/usr/bin/env python
"""S5c port_differ：per-peripheral 生成模式判定（rule 轨，prepare 阶段调用）。

对标 S5b `flow_differ.py` 的增量机制，diff 粒度改为 manifest 的 per-peripheral 签名。

机制（requirement"生成模式总览"）：
- 两个正交维度：
  * **用户手改**：文件当前 sha256 vs `outputs/s5c/file_hashes.json` 基线
  * **接口变化**：本轮 manifest 该单元签名 vs `outputs/s5c/port_manifest_snapshot.json`
- 交叉判定（per-peripheral 判定矩阵，7 种结果）：
  | 文件 hash | 单元签名 | 判定 |
  |---|---|---|
  | 一致 | 一致 | skip |
  | 一致 | 变化率 ≤ 60% | incremental |
  | 一致 | 变化率 > 60% / 快照缺失 | full |
  | 不一致（手改） | 一致 | skip（+标注接口漂移） |
  | 不一致（手改） | 变化 | blocked（报告用户） |
  | 文件不存在 | manifest 有该单元 | full（新单元） |
  | 文件存在 | manifest 已删除该单元 | deprecated |
- 变化率算法见 `analysis.diff_unit_fields`（字段级原子集 diff）。
- 首次执行（无 snapshot）→ 全部 full，任务书标注"建立基线"。

一个"单元"= 一个 port_impl 文件 = 一次判定（外设取 slug(peripheral)；
OSAL/Power 取同名键，用 kind 区分）。

产物：`outputs/s5c/port_diffs/<单元>_diff.json`（schema 校验）。
退出码：0=完成；1=diff 结果契约校验失败；2=环境错误。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import layout_resolver  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s5c-port-differ] {msg}", file=sys.stderr)


def judge_unit(unit_key: str, curr_fields: list[str], snap_entry: dict | None,
               file_exists: bool, hash_changed: bool,
               snapshot_missing: bool) -> tuple[str, str, str | None, dict]:
    """单单元判定（per-peripheral 判定矩阵）。

    判定顺序（短路）：
      1. 实现文件不存在 → `full`（新单元首次生成）
      2. 用户手改（hash 与上轮基线不一致）→ **优先保护**（skip-if-modified 硬约束，
         不得被"首次执行全 full"覆盖）：接口未变 → `skip`+漂移标注；
         接口变化 → `blocked`；无签名基线 → `skip`
      3. 无签名基线（快照缺失 / 该单元无记录）→ `full`（建立/重建基线）
      4. 签名未变 → `skip`
      5. 变化率 > 60% → `full`；否则 `incremental`

    返回 (generation_mode, reason, drift_warning, diff_detail)。
    """
    empty = {"changes": [], "change_count": 0, "change_rate": 0.0}
    drift = ("⚠️ 接口漂移风险：该文件由用户维护，不接收上游变化；"
             "删除该文件即恢复自动生成")

    if not file_exists:
        return ("full", f"新单元 {unit_key}（实现文件不存在），首次生成", None, empty)

    if hash_changed:
        if snapshot_missing or snap_entry is None:
            return ("skip", "用户手改且无上轮签名基线（首次执行/新增单元），保留手改",
                    drift, empty)
        d = analysis.diff_unit_fields(snap_entry.get("fields") or [], curr_fields)
        if d["change_count"] > 0:
            return ("blocked",
                    f"用户手改与上游接口变化冲突（接口变化率 {d['change_rate']:.0%}）"
                    "——须报告用户：保留手改还是接受上游变更后重新生成", None, d)
        return ("skip", "用户手改且上游接口未变，保留手改（该实现已与 manifest 脱钩）",
                drift, d)

    if snapshot_missing:
        return ("full", "首次执行（无 port_manifest_snapshot.json），"
                        "全量生成建立基线", None, empty)
    if snap_entry is None:
        return ("full", f"快照无 {unit_key} 记录（新增外设或基线丢失），全量重建该文件",
                None, empty)

    d = analysis.diff_unit_fields(snap_entry.get("fields") or [], curr_fields)
    if d["change_count"] == 0:
        return ("skip", "接口签名与文件哈希均未变，跳过该文件", None, d)
    if d["change_rate"] > analysis.FULL_RATIO_THRESHOLD:
        return ("full",
                f"接口签名变化率 {d['change_rate']:.0%} > "
                f"{analysis.FULL_RATIO_THRESHOLD:.0%}（大改），全量重生成", None, d)
    return ("incremental",
            f"接口签名变化率 {d['change_rate']:.0%} ≤ "
            f"{analysis.FULL_RATIO_THRESHOLD:.0%}（变更 {d['change_count']} 处），定点修改",
            None, d)


def diff_all(ctx: dict, plan: dict, recorded: dict,
             snapshot: dict | None) -> list[dict]:
    """逐单元判定并写 port_diffs/<单元>_diff.json，返回结果列表。"""
    ws = ctx["workspace"]
    platform_token, rtos = ctx["platform_token"], ctx["rtos"]
    src_dirs = [ws / d for d in plan["skill_dirs"]["s5c"]["src"]]
    units = analysis.manifest_units(ctx["manifest"])
    snap_units = (snapshot or {}).get("units") or {}
    snapshot_missing = snapshot is None
    now = datetime.now().isoformat(timespec="seconds")
    # 第三维度：设计输入（s5c_design_input.md）变化——不参与 manifest 签名 diff，
    # 但会改变实现约束；只做提示（任务书标注），不自动改文件（用户确认后触发）。
    di_rel = ctx["inputs"].get("s5c_design_input") or "docs/s5c_design_input.md"
    di_hash = analysis.design_input_file_hash(ctx["project_root"], di_rel)
    design_input_changed = bool(not snapshot_missing
                                and (snapshot or {}).get("design_input_hash") != di_hash)
    if design_input_changed:
        _log("⚠️ 设计输入（s5c_design_input.md）相对上轮快照已变化"
             "——本轮不自动改文件，请确认受影响单元")

    results: list[dict] = []
    # 遍历 manifest ∪ 上轮快照（后者多出的键 = 外设已删除 → deprecated）
    for key in sorted(set(units) | set(snap_units)):
        kind = ((units.get(key) or {}).get("kind")
                or (snap_units.get(key) or {}).get("kind") or "peripheral")
        header = (units.get(key) or {}).get("header")
        fname = analysis.manifest_unit_file(key, kind, platform_token, rtos)
        fpath = next((d / fname for d in src_dirs
                      if d.is_dir() and (d / fname).is_file()), None)
        rel = (str(fpath.resolve().relative_to(ws)).replace("\\", "/")
               if fpath is not None else None)
        file_exists = rel is not None
        hash_changed = bool(file_exists and recorded.get(rel) is not None
                            and recorded[rel] != analysis.file_sha256(fpath))

        if header is None:
            # 外设已从 manifest 删除（仅存于上轮快照）→ deprecated
            result = {
                "peripheral": key, "kind": kind, "file": rel,
                "file_exists": file_exists, "generation_mode": "deprecated",
                "signature_changed": False, "snapshot_missing": snapshot_missing,
                "change_rate": 0.0, "change_count": 0,
                "file_hash_changed": hash_changed, "changes": [],
                "reason": f"单元 {key} 已从 manifest 删除（仅存于上轮快照），"
                          "移除对应实现文件（IDE 引用由 ide_sync 收口）",
                "drift_warning": None, "updated_at": now,
            }
        else:
            curr_fields = analysis.unit_fields(header, kind)
            mode, reason, drift, d = judge_unit(
                key, curr_fields, snap_units.get(key), file_exists,
                hash_changed, snapshot_missing)
            result = {
                "peripheral": key, "kind": kind, "file": rel,
                "file_exists": file_exists, "generation_mode": mode,
                "signature_changed": d["change_count"] > 0,
                "snapshot_missing": snapshot_missing,
                "change_rate": d["change_rate"], "change_count": d["change_count"],
                "file_hash_changed": hash_changed, "changes": d["changes"],
                "reason": reason, "drift_warning": drift, "updated_at": now,
            }

        result["design_input_changed"] = design_input_changed
        errs = analysis.validate_schema(
            result, SKILL_DIR / "schemas" / "port_diff.schema.json",
            f"port_diff({key})")
        if errs:
            raise RuntimeError("; ".join(errs))
        analysis.save_json(
            ctx["outputs_dir"] / "s5c" / "port_diffs" / f"{key}_diff.json", result)
        _log(f"{key}: {result['generation_mode']}（{reason}）")
        results.append(result)
    return results


def build_snapshot(ctx: dict) -> dict:
    """本轮 manifest 的 per-peripheral 签名快照（validate 成功后写盘，作下轮基线）。

    同时记录 `design_input_hash`（设计输入维度基线，见 diff_all 的第三维度）。
    """
    units = analysis.manifest_units(ctx["manifest"])
    snap_units = {key: analysis.unit_signature(u["header"], u["kind"])
                  for key, u in units.items()}
    di_rel = ctx["inputs"].get("s5c_design_input") or "docs/s5c_design_input.md"
    return {
        "manifest_hash": analysis.file_sha256(ctx["manifest_path"]),
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "design_input_hash": analysis.design_input_file_hash(ctx["project_root"], di_rel),
        "units": snap_units,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5c per-peripheral diff + 生成模式判定（prepare 阶段调用）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    parser.add_argument("--unit", default=None, help="只 diff 指定实现单元（调试用）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    try:
        ctx = analysis.load_context(config_path, workspace)
        plan = layout_resolver.resolve_layout(
            ctx["project_root"], ctx["config"], ctx["state"])
        recorded = analysis.load_file_hashes(ctx["outputs_dir"] / "s5c")
        snapshot = analysis.load_manifest_snapshot(ctx["outputs_dir"] / "s5c")
        results = diff_all(ctx, plan, recorded, snapshot)
    except (RuntimeError, FileNotFoundError) as exc:
        _log(str(exc))
        return EXIT_INVALID if "契约校验" in str(exc) else EXIT_CONFIG_ERROR
    except (layout_resolver.LayoutError, OSError) as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR

    if args.unit:
        results = [r for r in results if r["peripheral"] == args.unit]
    print(json.dumps(
        {"port_diffs": {r["peripheral"]: r["generation_mode"] for r in results},
         "unit_count": len(results)}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())