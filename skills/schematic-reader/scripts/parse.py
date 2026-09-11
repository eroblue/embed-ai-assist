#!/usr/bin/env python
"""schematic-reader 主入口。

执行步骤：
1. 从 config.json 读取 project.schematic_path / project.workspace，检查文件存在
2. 根据 eda_tool 选择适配器（adapters/altium_adapter.py / kicad_adapter.py）
3. 调用适配器解析原理图，得到通用网表数据
4. 将网表写入 outputs/circuit_netlist.json
5. 将路径和统计信息写入 state.json 的 circuit 字段（不触碰其他 Skill 字段）

禁止事项：不修改 config.json；不读写 state.json 中其他 Skill 的字段。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# 使 scripts/adapters 可导入
sys.path.insert(0, str(SCRIPT_DIR))

from adapters import ADAPTERS  # noqa: E402

NETLIST_SCHEMA_ID = "embedaiassist.netlist.v1"
GENERATOR = "schematic-reader"

EXT_TOOL_MAP = {
    ".schdoc": "altium",
    ".kicad_sch": "kicad",
    ".sch": "kicad",
}

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[schematic-reader] {msg}", file=sys.stderr)


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
    """用 jsonschema 校验，返回错误列表（库缺失时跳过校验并告警）。"""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        _log("jsonschema 未安装，跳过校验: pip install jsonschema")
        return []
    schema = _load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def _update_state(state_path: Path, circuit: dict) -> None:
    """只更新 state.json 的 circuit 字段，保留其他字段。"""
    state = {}
    if state_path.exists():
        try:
            state = _load_json(state_path)
        except (json.JSONDecodeError, OSError) as exc:
            _log(f"state.json 读取失败，将重建: {exc}")
    state["circuit"] = circuit
    _save_json(state_path, state)


def _make_circuit_payload(
    netlist_path: Path,
    workspace: Path,
    stats: dict,
    parse_status: str,
    eda_tool: str,
    source_file: Path,
    error: str | None,
) -> dict:
    return {
        "netlist_path": netlist_path.resolve().relative_to(workspace.resolve()).as_posix()
        if netlist_path.resolve().is_relative_to(workspace.resolve())
        else str(netlist_path.resolve()),
        "component_count": stats["component_count"],
        "net_count": stats["net_count"],
        "pin_count": stats["pin_count"],
        "parse_status": parse_status,
        "eda_tool": eda_tool,
        "source_file": str(source_file.resolve()) if str(source_file) not in ("", ".") else "",
        "error": error,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="schematic-reader: 解析原理图（.SchDoc / .kicad_sch），输出通用网表"
    )
    parser.add_argument("--config", default="config.json", help="config.json 路径（只读）")
    parser.add_argument(
        "--eda-tool", choices=["altium", "kicad"], default=None,
        help="EDA 工具类型，覆盖 config.json 的 eda.tool",
    )
    parser.add_argument(
        "--schematic", default=None,
        help="覆盖 config.json 的 project.schematic_path（仅本次生效，不回写）",
    )
    parser.add_argument(
        "--workspace", default=None,
        help="覆盖 config.json 的 project.workspace（仅本次生效，不回写）",
    )
    args = parser.parse_args(argv)

    # ---- 1. 读取 config.json（只读，禁止修改）----
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        _log(f"config.json 不存在: {config_path}")
        return EXIT_CONFIG_ERROR
    try:
        config = _load_json(config_path)
    except json.JSONDecodeError as exc:
        _log(f"config.json 解析失败: {exc}")
        return EXIT_CONFIG_ERROR

    project = config.get("project") or {}
    schematic_raw = args.schematic or project.get("schematic_path") or ""
    schematic_path = Path(schematic_raw).expanduser()
    workspace = Path(args.workspace or project.get("workspace") or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    state_path = workspace / "state.json"
    outputs_dir = workspace / "outputs"
    netlist_path = outputs_dir / "circuit_netlist.json"

    # ---- 2. 确定 eda_tool：命令行 > config.eda.tool > 按扩展名 > altium ----
    eda_tool = args.eda_tool or (config.get("eda") or {}).get("tool")
    ext_tool = EXT_TOOL_MAP.get(schematic_path.suffix.lower())
    if eda_tool is None:
        eda_tool = ext_tool or "altium"
    elif ext_tool and ext_tool != eda_tool:
        _log(
            f"警告: 指定 eda_tool={eda_tool} 与文件扩展名 {schematic_path.suffix} 不符，"
            f"按扩展名切换为 {ext_tool}"
        )
        eda_tool = ext_tool

    # ---- 3. 检查原理图文件存在 ----
    if not schematic_raw:
        circuit = _make_circuit_payload(
            netlist_path, workspace,
            {"component_count": 0, "net_count": 0, "pin_count": 0},
            "failed", eda_tool, Path(""),
            "config.json 中 project.schematic_path 未配置",
        )
        _update_state(state_path, circuit)
        _log("config.json 中 project.schematic_path 未配置")
        print(json.dumps({"circuit": circuit}, ensure_ascii=False, indent=2))
        return EXIT_FAILED
    if not schematic_path.is_absolute():
        schematic_path = (config_path.parent / schematic_path).resolve()
    if not schematic_path.is_file():
        circuit = _make_circuit_payload(
            netlist_path, workspace,
            {"component_count": 0, "net_count": 0, "pin_count": 0},
            "failed", eda_tool, schematic_path,
            f"原理图文件不存在或未配置: {schematic_path}",
        )
        _update_state(state_path, circuit)
        _log(f"原理图文件不存在或未配置: {schematic_path}")
        print(json.dumps({"circuit": circuit}, ensure_ascii=False, indent=2))
        return EXIT_FAILED

    # ---- 4. 调用适配器解析 ----
    adapter = ADAPTERS[eda_tool]
    try:
        result = adapter(str(schematic_path))
    except ImportError as exc:
        circuit = _make_circuit_payload(
            netlist_path, workspace,
            {"component_count": 0, "net_count": 0, "pin_count": 0},
            "failed", eda_tool, schematic_path, f"缺少依赖库: {exc}",
        )
        _update_state(state_path, circuit)
        _log(f"缺少依赖库: {exc}")
        return EXIT_FAILED
    except Exception as exc:  # noqa: BLE001
        circuit = _make_circuit_payload(
            netlist_path, workspace,
            {"component_count": 0, "net_count": 0, "pin_count": 0},
            "failed", eda_tool, schematic_path, f"{type(exc).__name__}: {exc}",
        )
        _update_state(state_path, circuit)
        _log(f"解析失败: {type(exc).__name__}: {exc}")
        return EXIT_FAILED

    components = result.get("components", [])
    nets = result.get("nets", [])
    warnings = result.get("warnings", [])
    stats = {
        "component_count": len(components),
        "net_count": len(nets),
        "pin_count": sum(len(n.get("terminals", [])) for n in nets),
    }

    # ---- 5. 解析状态判定 ----
    parse_status = "success"
    if not components or not nets:
        parse_status = "partial"
        warnings.append("netlist 为空：可能是文件不包含电气对象")
    if warnings:
        parse_status = "partial" if parse_status != "partial" else parse_status
        for w in warnings[:10]:
            _log(f"警告: {w}")

    netlist_doc = {
        "schema": NETLIST_SCHEMA_ID,
        "generator": GENERATOR,
        "eda_tool": eda_tool,
        "source_file": str(schematic_path.resolve()),
        "parse_status": parse_status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "statistics": stats,
        "warnings": warnings,
        "components": components,
        "nets": nets,
    }

    # ---- 6. 写入 outputs/circuit_netlist.json ----
    _save_json(netlist_path, netlist_doc)

    # ---- 7. 写入 state.json 的 circuit 字段并校验 ----
    circuit = _make_circuit_payload(
        netlist_path, workspace, stats, parse_status, eda_tool, schematic_path,
        "; ".join(warnings) if warnings else None,
    )
    errors = _validate(
        {"circuit": circuit}, SKILL_DIR / "schemas" / "output.schema.json", "output.schema"
    )
    if errors:
        _log("输出契约校验失败: " + "; ".join(errors))
        return EXIT_FAILED

    _update_state(state_path, circuit)

    # ---- 8. stdout 输出结果摘要 ----
    print(json.dumps({"circuit": circuit}, ensure_ascii=False, indent=2))
    return EXIT_OK if parse_status != "failed" else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
