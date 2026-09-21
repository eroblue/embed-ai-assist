#!/usr/bin/env python
"""circuit-investigator 主入口。

执行步骤：
1. 分层加载配置（根 config.json → 项目 config.json → 深合并，只读）
2. 读 state.json 的 circuit（S1）/ chip（S3）字段，确认均已执行：
   failed → 写 verify_status=failed 终止；partial → 继承 partial
3. 加载网表（outputs/circuit_netlist.json）与芯片引脚定义（outputs/chip_info/pins.json）
4. 识别主控元件（value 匹配 platform）
5. 交叉核对（conflict_checker）：引脚定义一致性 / 电源 / 时钟 / 外设复用冲突
6. 推断每个引脚功能角色（pin_inferrer，rule 模式）
7. 组装 circuit_facts.json → circuit_facts.schema.json 校验 → 写 outputs/
8. 生成 circuit_facts.xlsx（GD32 示例风格）
9. 将指针与统计写入 state.json 的 circuit.facts 字段

禁止事项：不修改 config.json；不读写其他 Skill 的字段；不修改 S1/S3 产物文件。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+（如 Path.write_text(newline=)）
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
ROOT_DIR = SKILL_DIR.parent.parent

sys.path.insert(0, str(SCRIPT_DIR))

import conflict_checker  # noqa: E402
import pin_inferrer  # noqa: E402
from excel_export import export_facts_xlsx  # noqa: E402

SCHEMA_ID = "embedaiassist.circuit.facts.v1"
GENERATOR = "circuit-investigator"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2

VALID_SCOPES = ("pins", "power", "clocks", "peripherals", "all")


def _log(msg: str) -> None:
    print(f"[circuit-investigator] {msg}", file=sys.stderr)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _validate(instance: dict, schema_path: Path, label: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        _log("jsonschema 未安装，跳过校验: pip install jsonschema")
        return []
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    notes: list[str] = []
    root_cfg: dict = {}
    root_config_path = ROOT_DIR / "config.json"
    if root_config_path.is_file():
        root_cfg = _load_json(root_config_path)
        notes.append(f"已加载全局配置: {root_config_path}")
    else:
        notes.append(f"未找到全局配置 {root_config_path}，跳过")
    if not project_config_path.is_file():
        raise FileNotFoundError(f"项目配置不存在: {project_config_path}")
    proj_cfg = _load_json(project_config_path)
    notes.append(f"已加载项目配置: {project_config_path}")
    return _deep_merge(root_cfg, proj_cfg), notes


def _update_state_facts(state_path: Path, facts: dict) -> None:
    """只更新 state.json 的 circuit.facts 字段（在 S1 已写入的 circuit 内追加）。"""
    state = {}
    if state_path.exists():
        try:
            state = _load_json(state_path)
        except (json.JSONDecodeError, OSError) as exc:
            _log(f"state.json 读取失败，将重建: {exc}")
    circuit = state.get("circuit") or {}
    if not isinstance(circuit, dict):
        circuit = {}
    circuit["facts"] = facts
    state["circuit"] = circuit
    _save_json(state_path, state)


def _find_mcu_component(components: list[dict], platform: str) -> dict | None:
    """主控元件识别：designator U* 且 value 含平台名（如 STM32F103ZET6）。

    系列名通配：platform 尾部 X 为通配（FT61F14X 匹配 FT61F143A-RB 等具体型号）。
    """
    plat = platform.upper().replace("-", "").replace("_", "")
    prefix = plat[:-1] if plat.endswith("X") and len(plat) > 3 else None
    for comp in components:
        value = str(comp.get("value") or "").upper().replace("-", "").replace("_", "").replace(" ", "")
        if value and (plat in value or (prefix and value.startswith(prefix))):
            return comp
    return None


def investigate(
    workspace: Path,
    platform: str,
    scope: str,
    inference_mode: str,
) -> tuple[dict, str]:
    """核心流程：返回 (facts_payload_for_state, verify_status)。"""
    state = _load_json(workspace / "state.json")
    circuit_state = state.get("circuit") or {}
    chip_state = state.get("chip") or {}

    # ---- 前置：S1/S3 状态 ----
    s1_status = circuit_state.get("parse_status")
    s3_status = chip_state.get("extract_status")
    netlist_rel = circuit_state.get("netlist_path")
    chip_pins_rel = chip_state.get("pins_path")
    netlist_path = workspace / netlist_rel if netlist_rel else None
    chip_pins_path = workspace / chip_pins_rel if chip_pins_rel else None

    problems: list[str] = []
    if s1_status == "failed":
        problems.append(f"S1 网表解析失败（circuit.parse_status={s1_status}）")
    if s3_status == "failed":
        problems.append(f"S3 芯片数据提取失败（chip.extract_status={s3_status}）")
    if netlist_path is None or not netlist_path.is_file():
        problems.append(f"网表文件不存在: {netlist_path}")
    if chip_pins_path is None or not chip_pins_path.is_file():
        problems.append(f"芯片引脚定义文件不存在: {chip_pins_path}")
    if problems:
        return _failed_payload(workspace, "; ".join(problems)), "failed"

    inherited_partial = "partial" if (s1_status == "partial" or s3_status == "partial") else None

    # ---- 加载数据 ----
    netlist = _load_json(netlist_path)
    chip_pins = _load_json(chip_pins_path)
    components = netlist.get("components") or []
    mcu = _find_mcu_component(components, platform)
    if mcu is None:
        return _failed_payload(
            workspace, f"网表中未找到主控元件（platform={platform}，按 value 匹配）"
        ), "failed"

    mcu_pins = [p for p in (mcu.get("pins") or []) if p is not None]
    chip_pin_list = chip_pins.get("pins") or []
    chip_by_no = {str(p.get("pin")): p for p in chip_pin_list}

    # ---- 交叉核对 ----
    conflicts: list[dict] = []
    warnings: list[dict] = []
    if scope in ("pins", "all"):
        for issue in conflict_checker.check_pins_defined(mcu_pins, chip_pins):
            (conflicts if issue["severity"] == "error" else warnings).append(issue)
    if scope in ("power", "all"):
        for issue in conflict_checker.check_power(mcu_pins):
            (conflicts if issue["severity"] == "error" else warnings).append(issue)
    if scope in ("clocks", "all"):
        for issue in conflict_checker.check_clocks(mcu_pins):
            (conflicts if issue["severity"] == "error" else warnings).append(issue)
    if scope in ("peripherals", "all"):
        for issue in conflict_checker.check_peripheral_conflict(mcu_pins, chip_pins):
            (conflicts if issue["severity"] == "error" else warnings).append(issue)

    # ---- 引脚角色推断 + 逐引脚状态 ----
    pins_out: list[dict] = []
    warn_pins: set[str] = set()
    conflict_pins: set[str] = set()
    for issue in conflicts:
        conflict_pins.add(str(issue.get("pin")))
    for np in sorted(mcu_pins, key=lambda p: int(p["pin"]) if str(p.get("pin", "")).isdigit() else 0):
        no = str(np.get("pin") or "")
        name = (np.get("pin_name") or "").strip()
        net = (np.get("net") or "").strip() or None
        chip_pin = chip_by_no.get(no) or {}
        inferred = pin_inferrer.infer_pin(
            net, name,
            chip_pin.get("main_function"),
            chip_pin.get("alternate_functions") or [],
            chip_pin_name=str(chip_pin.get("name") or "") or None,
        )
        # 引脚名一致性问题（剥脚注后缀、忽略 -/_ 分隔符差异比较，
        # 如 PC14-OSC32_IN(5) ≡ PC14-OSC32_IN、OSC_IN ≡ OSCIN）
        chip_name = str(chip_pin.get("name") or "")
        name_mismatch = bool(
            chip_name
            and name
            and pin_inferrer.clean_name(name).upper().replace("-", "").replace("_", "")
            != pin_inferrer.clean_name(chip_name).upper().replace("-", "").replace("_", "")
        )
        status = inferred["status"]
        if no in conflict_pins or name in conflict_pins:
            status = "conflict"
        elif status == "ok" and name_mismatch:
            status = "warning"
            warnings.append({
                "pin": no,
                "issue": f"网表引脚名 {name} 与芯片定义 {chip_name} 不一致",
                "severity": "warning",
            })
        if status == "warning":
            warn_pins.add(no)
        pins_out.append({
            "pin": no,
            "pin_name": name,
            "net": net,
            "component": mcu.get("designator"),
            "role": inferred["role"],
            "peripheral": inferred["peripheral"],
            "config": inferred["config"],
            "status": status,
            "note": inferred["note"] + (f"；网表引脚名 {name} ≠ 芯片定义 {chip_name}" if name_mismatch else ""),
        })

    # 无语义网络名的引脚 → warnings 列表
    for p in pins_out:
        if p["status"] == "warning" and p["net"] and p["peripheral"] == "":
            warnings.append({
                "pin": p["pin"],
                "issue": f"网络名 {p['net']} 无明确语义，无法推断功能角色",
                "severity": "warning",
            })

    nc_pins = [p["pin_name"] for p in pins_out if p["status"] == "nc"]
    hse, lse = conflict_checker.extract_crystal_freq(components, mcu_pins)

    if inherited_partial:
        verify_status = "partial"
    elif conflicts:
        verify_status = "partial"
    else:
        verify_status = "success"

    facts = {
        "schema": SCHEMA_ID,
        "mcu": str(mcu.get("value") or platform),
        "package": chip_pins.get("package"),
        "platform": platform,
        "verify_status": verify_status,
        "verify_scope": scope,
        "inference_mode": inference_mode,
        "pins": pins_out,
        "power": conflict_checker.build_power_map(mcu_pins),
        "clocks": {
            "HSE": hse or "未连接" if scope in ("clocks", "all") else None,
            "LSE": lse or "未连接" if scope in ("clocks", "all") else None,
            "PLL": "待定",
            "AHB": "待定",
            "APB1": "待定",
            "APB2": "待定",
        },
        "conflicts": conflicts,
        "warnings": warnings,
        "nc_pins": nc_pins,
        "verified_pin_count": sum(1 for p in pins_out if p["status"] in ("ok", "warning", "conflict")),
        "conflict_count": len(conflicts),
        "warning_count": len(warnings),
        "nc_pin_count": len(nc_pins),
        "source": {
            "netlist": str(netlist_path.resolve()),
            "chip_pins": str(chip_pins_path.resolve()),
            "investigated_at": datetime.now().isoformat(timespec="seconds"),
        },
    }
    return facts, verify_status


def _failed_payload(workspace: Path, error: str) -> dict:
    now = datetime.now().isoformat(timespec="seconds")
    outputs_dir = workspace / "outputs"
    return {
        "facts_path": (outputs_dir / "circuit_facts.json").as_posix(),
        "facts_xlsx_path": None,
        "verified_pin_count": 0,
        "conflict_count": 0,
        "warning_count": 0,
        "nc_pin_count": 0,
        "verify_status": "failed",
        "verify_scope": "all",
        "inference_mode": "rule",
        "error": error,
        "updated_at": now,
    }


def _state_payload(
    facts: dict, facts_json: Path, facts_xlsx: Path | None, status: str,
    scope: str, mode: str, error: str | None,
) -> dict:
    return {
        "facts_path": facts_json.as_posix(),
        "facts_xlsx_path": facts_xlsx.as_posix() if facts_xlsx else None,
        "verified_pin_count": facts.get("verified_pin_count", 0),
        "conflict_count": facts.get("conflict_count", 0),
        "warning_count": facts.get("warning_count", 0),
        "nc_pin_count": facts.get("nc_pin_count", 0),
        "verify_status": status,
        "verify_scope": scope,
        "inference_mode": mode,
        "error": error,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="circuit-investigator: 交叉核对 S1 网表与 S3 芯片规格，生成硬件事实报告"
    )
    parser.add_argument(
        "--config", default="config.json",
        help="项目 config.json 路径（自动与根目录全局配置分层合并，只读）",
    )
    parser.add_argument(
        "--scope", choices=list(VALID_SCOPES), default=None,
        help="覆盖 verify_scope（仅本次生效）",
    )
    parser.add_argument(
        "--inference-mode", choices=["rule", "ai"], default=None,
        help="覆盖 inference_mode（ai 失败自动降级 rule；仅本次生效）",
    )
    parser.add_argument(
        "--workspace", default=None,
        help="覆盖项目目录（默认为 --config 所在目录）",
    )
    args = parser.parse_args(argv)

    # ---- 1. 分层加载配置（只读）----
    config_path = Path(args.config).resolve()
    try:
        config, config_notes = _load_layered_config(config_path)
    except FileNotFoundError as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    except json.JSONDecodeError as exc:
        _log(f"config.json 解析失败: {exc}")
        return EXIT_CONFIG_ERROR
    for note in config_notes:
        _log(note)

    # ---- 1b. 合并配置契约校验（根目录 schemas/config.schema.json，全流水线统一拦截）----
    cfg_errors = _validate(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        _log("配置契约校验失败: " + "; ".join(cfg_errors))
        return EXIT_CONFIG_ERROR

    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    # 目标工程根（App/BootLoader 双工程）：state/outputs 归目标工程（project.build_target，缺省 App）
    workspace = workspace / ((config.get("project") or {}).get("build_target") or "App")

    platform = (config.get("platform") or "").strip()
    scope = (args.scope or config.get("verify_scope") or "all").strip().lower()
    mode = (args.inference_mode or config.get("inference_mode") or "rule").strip().lower()
    if not platform:
        payload = _failed_payload(workspace, "配置中 platform 未配置")
        _update_state_facts(workspace / "state.json", payload)
        _log("配置中 platform 未配置")
        print(json.dumps({"circuit": {"facts": payload}}, ensure_ascii=False, indent=2))
        return EXIT_FAILED

    # ---- 2~6. 核心流程 ----
    if mode == "ai":
        _log("inference_mode=ai：当前版本 LLM 调用未接入，自动降级 rule 模式")
        mode = "rule"

    outputs_dir = workspace / (config.get("output_dir") or "outputs").rstrip("/\\")
    facts, status = investigate(workspace, platform, scope, mode)

    if status == "failed":
        _update_state_facts(workspace / "state.json", facts)
        _log(f"验证失败: {facts.get('error')}")
        print(json.dumps({"circuit": {"facts": facts}}, ensure_ascii=False, indent=2))
        return EXIT_FAILED

    # ---- 7. schema 校验 + 写入 ----
    input_errors = _validate(
        {
            "circuit": {"parse_status": "success", "netlist_path": "x"},
            "chip": {"extract_status": "success", "pins_path": "x"},
            "platform": platform, "verify_scope": scope, "inference_mode": mode,
        },
        SKILL_DIR / "schemas" / "input.schema.json",
        "input",
    )
    fact_errors = _validate(
        facts, SKILL_DIR / "schemas" / "circuit_facts.schema.json", "circuit_facts"
    )
    errors = input_errors + fact_errors
    if errors:
        for e in errors:
            _log(e)
        payload = _state_payload(facts, outputs_dir / "circuit_facts.json", None, "failed", scope, mode, "; ".join(errors))
        _update_state_facts(workspace / "state.json", payload)
        return EXIT_FAILED

    facts_json = outputs_dir / "circuit_facts.json"
    _save_json(facts_json, facts)

    # ---- 8. Excel ----
    facts_xlsx: Path | None = None
    try:
        facts_xlsx = outputs_dir / "circuit_facts.xlsx"
        export_facts_xlsx(facts, facts_xlsx)
    except ImportError:
        _log("openpyxl 未安装，跳过 Excel: pip install openpyxl")
        facts_xlsx = None
    except Exception as exc:
        _log(f"Excel 生成失败（不影响 JSON 产物）: {exc}")
        facts_xlsx = None

    # ---- 9. 更新 state ----
    payload = _state_payload(facts, facts_json, facts_xlsx, status, scope, mode, None)
    _update_state_facts(workspace / "state.json", payload)

    _log(
        f"验证完成: status={status} scope={scope} mode={mode} | "
        f"已验证 {payload['verified_pin_count']} 脚 / 冲突 {payload['conflict_count']} / "
        f"警告 {payload['warning_count']} / NC {payload['nc_pin_count']}"
    )
    print(json.dumps({"circuit": {"facts": payload}}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
