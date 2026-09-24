#!/usr/bin/env python
"""S2 spec-reader 第 3 段：validate（rule 轨，终验）。

三段式执行模型的确定性校验段（Agent 按任务书生成产物后运行）：
  1. [rule]  prepare.py   → raw_text.md + generation_brief.md，state.spec = running
  2. [agent] Agent 提取   → spec.json + spec_trace.json + uncovered.json
  3. [rule]  validate.py  → 本脚本

校验内容：三个产物存在且过 schema；引用一致性（REQ-ID 不重复、
features/error_handling/thresholds/business_timing 引用存在、状态机迁移
from/to 合法、每条 REQ 至少归属一个 feature、spec_trace 恰好覆盖全部
REQ-ID、meta.source_file 与 config 一致）；统计 spec_summary。

收口规则（requirement 阶段 C）：
  - 校验通过且无未定项 → status: success
  - 有未定项但 spec 完整 → status: partial
  - 校验失败 → status: failed + error（清理三个 Agent 产物，不留半成品）

产物校验失败 → 退出码 1；环境/契约失败 → 退出码 3（均写 failed）。
"""

from __future__ import annotations

import argparse
import json
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
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_PRODUCT_INVALID = 1
EXIT_CONFIG_ERROR = 3


def _log(msg: str) -> None:
    print(f"[s2-validate] {msg}", file=sys.stderr)


def check_references(spec: dict) -> list[str]:
    """引用一致性校验（requirement 阶段 C 第 12 步的全部规则）。"""
    errors: list[str] = []
    reqs = spec.get("requirements", [])
    req_ids = [r.get("id", "") for r in reqs]
    req_set = set(req_ids)

    # REQ-ID 不重复
    dupes = sorted({rid for rid in req_ids if req_ids.count(rid) > 1})
    if dupes:
        errors.append(f"REQ-ID 重复: {', '.join(dupes)}")

    # F-ID 不重复
    feat_ids = [f.get("id", "") for f in spec.get("features", [])]
    dupes = sorted({fid for fid in feat_ids if feat_ids.count(fid) > 1})
    if dupes:
        errors.append(f"F-ID 重复: {', '.join(dupes)}")

    # features[].requirements 引用存在 + 每条 REQ 至少归属一个 feature
    covered: set[str] = set()
    for feat in spec.get("features", []):
        for rid in feat.get("requirements", []):
            if rid not in req_set:
                errors.append(f"feature {feat.get('id')} 引用了不存在的 {rid}")
            covered.add(rid)
    uncovered_reqs = sorted(req_set - covered)
    if uncovered_reqs:
        errors.append(f"以下 REQ 未归属任何 feature: {', '.join(uncovered_reqs)}")

    # 关联引用存在（timing/error_handling/thresholds）
    for item in spec.get("business_timing", []):
        if item.get("requirement") not in req_set:
            errors.append(f"business_timing '{item.get('name')}' 引用了不存在的 "
                          f"{item.get('requirement')}")
    for item in spec.get("error_handling", []):
        if item.get("requirement") not in req_set:
            errors.append(f"error_handling '{item.get('scenario')}' 引用了不存在的 "
                          f"{item.get('requirement')}")
    for item in spec.get("thresholds", []):
        if item.get("requirement") not in req_set:
            errors.append(f"thresholds '{item.get('name')}' 引用了不存在的 "
                          f"{item.get('requirement')}")

    # 状态机：module_hint 归属 feature；transitions from/to 合法
    feature_names = {f.get("name", "") for f in spec.get("features", [])}
    for sm in spec.get("business_states", []):
        if sm.get("module_hint") not in feature_names:
            errors.append(f"business_states '{sm.get('module_hint')}' 的 module_hint"
                          " 不在 features[].name 中")
        state_names = {s.get("name", "") for s in sm.get("states", [])}
        for tr in sm.get("transitions", []):
            for end in ("from", "to"):
                if tr.get(end) not in state_names:
                    errors.append(f"business_states '{sm.get('module_hint')}' 迁移"
                                  f" {end}='{tr.get(end)}' 不在 states 列表中")
    return errors


def check_trace(spec: dict, trace: dict) -> list[str]:
    """spec_trace 覆盖性校验：恰好覆盖全部 REQ-ID（不多不少）。"""
    errors: list[str] = []
    req_ids = {r.get("id") for r in spec.get("requirements", [])}
    trace_ids = [t.get("requirement", "") for t in trace.get("traces", [])]
    trace_set = set(trace_ids)
    dupes = sorted({tid for tid in trace_ids if trace_ids.count(tid) > 1})
    if dupes:
        errors.append(f"spec_trace 中 REQ-ID 重复: {', '.join(dupes)}")
    missing = sorted(req_ids - trace_set)
    if missing:
        errors.append(f"spec_trace 未覆盖的需求: {', '.join(missing)}")
    extra = sorted(trace_set - req_ids)
    if extra:
        errors.append(f"spec_trace 引用了不存在的需求: {', '.join(extra)}")
    return errors


def check_meta(spec: dict, ctx: dict) -> list[str]:
    """meta.source_file 与 config 的 functional_spec 一致。"""
    errors: list[str] = []
    src = (spec.get("meta") or {}).get("source_file")
    if src != ctx["spec_file"]:
        errors.append(f"spec.meta.source_file='{src}' 与 config 的 "
                      f"project.inputs.functional_spec='{ctx['spec_file']}' 不一致")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S2 validate: spec.json 校验 + 引用一致性 + state 收口")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()

    try:
        ctx = analysis.load_context(config_path, workspace)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        _log(str(exc))
        payload = {"status": "failed", "spec_path": None, "error": str(exc),
                   "updated_at": datetime.now().isoformat(timespec="seconds")}
        try:
            cfg = analysis.load_layered_config(config_path)[0]
        except Exception:
            cfg = None
        try:
            state_store.update_state(
                analysis.resolve_target(cfg, workspace) / "state.json", {"spec": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # S2 必须先跑 prepare（state.spec 存在）
    if not isinstance(ctx["state"].get("spec"), dict):
        _log("state.spec 不存在：先运行 prepare.py 生成任务书")
        print(json.dumps({"spec": {"status": "failed", "spec_path": None,
              "error": "state.spec 不存在（先运行 prepare.py）"}}, ensure_ascii=False))
        return EXIT_CONFIG_ERROR

    def _fail(error: str, exit_code: int) -> int:
        """failed 收口：清理三个 Agent 产物（不留半成品），state 写 failed。"""
        for name in ("spec.json", "spec_trace.json", "uncovered.json"):
            (ctx["outputs_dir"] / "s2" / name).unlink(missing_ok=True)
        payload = {"status": "failed", "spec_path": None, "error": error,
                   "updated_at": datetime.now().isoformat(timespec="seconds")}
        try:
            state_store.update_state(ctx["state_path"], {"spec": payload})
        except (OSError, state_store.StateLockTimeout):
            pass
        _log(error)
        print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
        return exit_code

    s2_dir = ctx["outputs_dir"] / "s2"

    # ---- 1. 产物存在 + schema 校验 ----
    errors: list[str] = []
    products: dict[str, dict] = {}
    for name, schema in (("spec.json", "spec.schema.json"),
                         ("spec_trace.json", "spec_trace.schema.json"),
                         ("uncovered.json", "uncovered.schema.json")):
        path = s2_dir / name
        if not path.is_file():
            errors.append(f"缺少 outputs/s2/{name}（Agent 按任务书生成）")
            continue
        try:
            data = analysis.load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{name} 解析失败: {exc}")
            continue
        products[name] = data
        errors.extend(analysis.validate_schema(
            data, SKILL_DIR / "schemas" / schema, name))

    # ---- 2. 引用一致性（spec 完整时才做交叉校验）----
    if "spec.json" in products:
        spec = products["spec.json"]
        errors.extend(check_meta(spec, ctx))
        errors.extend(check_references(spec))
        if "spec_trace.json" in products:
            errors.extend(check_trace(spec, products["spec_trace.json"]))

    if errors:
        _log("校验失败（已清理无效产物，Agent 修复后重新生成再跑 validate.py）:")
        for e in errors:
            _log(f"  - {e}")
        return _fail("spec 校验失败: " + "; ".join(errors), EXIT_PRODUCT_INVALID)

    # ---- 3. 统计 + state 收口 ----
    spec = products["spec.json"]
    uncovered = products["uncovered.json"]
    summary = {
        "total_requirements": len(spec.get("requirements", [])),
        "feature_count": len(spec.get("features", [])),
        "uncovered_count": len(uncovered.get("items", [])),
    }
    status = "partial" if summary["uncovered_count"] > 0 else "success"
    payload = {
        "status": status,
        "spec_path": "outputs/s2/spec.json",
        "software_spec_path": ctx["software_spec"],
        "spec_summary": summary,
        "source_file": ctx["spec_file"],
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "spec")
    if schema_errors:
        return _fail("spec 状态契约校验失败: " + "; ".join(schema_errors), EXIT_CONFIG_ERROR)
    state_store.update_state(ctx["state_path"], {"spec": payload})

    if status == "partial":
        _log(f"完成（partial）: {summary['total_requirements']} 条需求 / "
             f"{summary['feature_count']} 个功能域 / {summary['uncovered_count']} 个未定项待用户确认")
        _log("未定项清单: outputs/s2/uncovered.json")
    else:
        _log(f"完成（success）: {summary['total_requirements']} 条需求 / "
             f"{summary['feature_count']} 个功能域，无未定项")
    print(json.dumps({"spec": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
