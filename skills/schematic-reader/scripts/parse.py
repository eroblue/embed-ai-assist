#!/usr/bin/env python
"""schematic-reader 主入口。

执行步骤：
1. 分层加载配置：根目录 config.json（全局默认）→ 项目 config.json（覆盖/补充）→ 深合并
2. 从合并配置读取 schematic_path / output_dir，检查文件存在
3. 根据 eda_tool / schematic_format / 扩展名选择适配器
   （adapters/altium_adapter.py / kicad_adapter.py / pdf_adapter.py）
4. 调用适配器解析原理图，得到通用网表数据（PDF 输入附带连接级置信度 pdf_meta）
5. 将网表写入项目 outputs/circuit_netlist.json，生成引脚 Excel；
   PDF 输入时额外生成 outputs/pdf_review.md 人工核对清单
6. 将路径和统计信息写入项目 state.json 的 circuit 字段（不触碰其他 Skill 字段；
   PDF 输入时追加 source_format / confidence / low_confidence_count / review_path
   四个可选字段，源文件输入输出与 v1.0 完全一致）

禁止事项：不修改 config.json；不读写 state.json 中其他 Skill 的字段。
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
ROOT_DIR = SKILL_DIR.parent.parent  # embed-ai-assist/（根目录，含全局 config.json）

# 使 scripts/adapters 可导入
sys.path.insert(0, str(SCRIPT_DIR))

from adapters import ADAPTERS  # noqa: E402

NETLIST_SCHEMA_ID = "embedaiassist.netlist.v1"
GENERATOR = "schematic-reader"

EXT_TOOL_MAP = {
    ".schdoc": "altium",
    ".kicad_sch": "kicad",
    ".sch": "kicad",
    ".pdf": "pdf",
}

# schematic_format（输入格式，更精确）→ 解析器名
FORMAT_TOOL_MAP = {
    "schdoc": "altium",
    "prjpcb": "altium",
    "kicad_sch": "kicad",
    "pdf": "pdf",
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


def _deep_merge(base: dict, override: dict) -> dict:
    """深合并：override 的值覆盖 base 的同名项，dict 递归合并。"""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    """分层加载配置：
    第 1 步：加载根目录 config.json（全局默认）
    第 2 步：加载项目/示例 config.json（覆盖或补充）
    第 3 步：深合并得到最终生效的配置
    返回 (合并后的配置, 加载日志列表)。
    """
    notes: list[str] = []
    root_config_path = ROOT_DIR / "config.json"
    root_cfg: dict = {}
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


def _rel_path(path: Path, workspace: Path) -> str:
    """工作区内路径转相对 POSIX 路径，工作区外转绝对路径。"""
    resolved = path.resolve()
    if resolved.is_relative_to(workspace.resolve()):
        return resolved.relative_to(workspace.resolve()).as_posix()
    return str(resolved)


def _make_circuit_payload(
    netlist_path: Path,
    workspace: Path,
    stats: dict,
    parse_status: str,
    eda_tool: str,
    source_file: Path,
    error: str | None,
    excel_path: Path | None = None,
    pdf_meta: dict | None = None,
    review_path: Path | None = None,
) -> dict:
    """构造 state.json 的 circuit 字段。

    pdf_meta 仅 PDF 输入时传入：追加 source_format / confidence /
    low_confidence_count / review_path 四个可选字段（v1.1 契约）；
    源文件输入时不传，输出与 v1.0 完全一致。
    """
    payload = {
        "netlist_path": _rel_path(netlist_path, workspace),
        "component_count": stats["component_count"],
        "net_count": stats["net_count"],
        "pin_count": stats["pin_count"],
        "parse_status": parse_status,
        "eda_tool": eda_tool,
        "source_file": str(source_file.resolve()) if str(source_file) not in ("", ".") else "",
        "excel_path": _rel_path(excel_path, workspace) if excel_path is not None else None,
        "error": error,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if pdf_meta is not None:
        payload["source_format"] = pdf_meta.get("source_format", "pdf")
        payload["confidence"] = pdf_meta.get("confidence", 0.0)
        payload["low_confidence_count"] = pdf_meta.get("low_confidence_count", 0)
        payload["review_path"] = (
            _rel_path(review_path, workspace) if review_path is not None else None
        )
    return payload


def _write_pdf_review(
    pdf_meta: dict, source_file: Path, stats: dict, review_path: Path
) -> None:
    """生成人工核对清单 outputs/pdf_review.md（仅 PDF 输入）。

    低置信度（< 0.7）连接全部列出，不得静默丢弃；中置信度（0.7 ~ 0.95）
    作为 S4 阶段重点核对参考一并给出。
    """
    lines = [
        "# PDF 原理图人工核对清单",
        "",
        f"- 源文件：`{source_file}`",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 整体置信度：**{pdf_meta.get('confidence', 0.0)}**",
        f"- 元件数：{stats['component_count']}，网络数：{stats['net_count']}，"
        f"引脚连接数：{stats['pin_count']}",
        "",
        "> PDF 提取不保证 100% 精确（矢量图形 + 文字推断的技术本质决定）。",
        "> 置信度分级：≥ 0.95 高可信直接使用；0.7 ~ 0.95 中可信（S4 重点核对）；",
        "> < 0.7 低可信（本清单，必须人工核对）。",
        "",
    ]
    low = pdf_meta.get("review_low", [])
    mid = pdf_meta.get("review_mid", [])

    lines.append(f"## 一、需要人工核对的连接（置信度 < 0.7，共 {len(low)} 条）")
    lines.append("")
    if low:
        lines.append("| 引脚 | 推断网络 | 推断目标 | 置信度 | 建议 |")
        lines.append("|---|---|---|---|---|")
        for r in low:
            pin_disp = f"{r['pin']}（{r['pin_name']}）" if r["pin_name"] else r["pin"]
            lines.append(
                f"| {pin_disp} | {r['net']} | {r['target']} | {r['confidence']} | {r['suggestion']} |"
            )
    else:
        lines.append("无低置信度连接。")
    lines.append("")

    lines.append(f"## 二、建议核对的连接（置信度 0.7 ~ 0.95，共 {len(mid)} 条，S4 阶段重点核对）")
    lines.append("")
    if mid:
        lines.append("| 引脚 | 推断网络 | 推断目标 | 置信度 | 判定依据 |")
        lines.append("|---|---|---|---|---|")
        for r in mid[:80]:  # 中置信度数量可能较多，最多列 80 条
            pin_disp = f"{r['pin']}（{r['pin_name']}）" if r["pin_name"] else r["pin"]
            lines.append(
                f"| {pin_disp} | {r['net']} | {r['target']} | {r['confidence']} | {r['note']} |"
            )
        if len(mid) > 80:
            lines.append(f"| … | … | … | … | 其余 {len(mid) - 80} 条见网表 confidence 字段 |")
    else:
        lines.append("无中置信度连接。")
    lines.append("")

    lines.append("## 核对说明")
    lines.append("")
    lines.append("1. 核对后在网表 `outputs/circuit_netlist.json` 中直接修正错误连接的 `net` 字段，")
    lines.append("   并将 `confidence` 更新为 1.0（人工确认后视为可信）。")
    lines.append("2. `method` 字段记录判定依据：line_intersection=线交点；net_label=网络标号；")
    lines.append("   pin_name_match=引脚名匹配；llm_assisted=LLM 辅助校验。")
    lines.append("3. 工程师花 10 分钟核对低置信度连接，通常比重新绘制原理图快得多。")

    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="schematic-reader: 解析原理图（.SchDoc / .kicad_sch），输出通用网表"
    )
    parser.add_argument(
        "--config", default="config.json",
        help="项目 config.json 路径（自动与根目录全局 config.json 分层合并，只读）",
    )
    parser.add_argument(
        "--eda-tool", choices=["altium", "kicad", "pdf"], default=None,
        help="EDA 工具/解析器类型（pdf 对应 PDF 原理图），覆盖配置中的 eda_tool / schematic_format（仅本次生效）",
    )
    parser.add_argument(
        "--schematic", default=None,
        help="覆盖配置中的 schematic_path（仅本次生效，不回写）",
    )
    parser.add_argument(
        "--workspace", default=None,
        help="覆盖项目目录（默认为 --config 所在目录，仅本次生效）",
    )
    args = parser.parse_args(argv)

    # ---- 1. 分层加载配置（只读，禁止修改）----
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

    schematic_raw = args.schematic or config.get("schematic_path") or ""
    schematic_path = Path(schematic_raw).expanduser()
    # 工作区 = 项目目录（--config 所在目录）；--workspace 可覆盖
    workspace = Path(args.workspace or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    # 目标工程根（App/BootLoader 双工程）：state/outputs 归目标工程（project.build_target，缺省 App）
    workspace = workspace / ((config.get("project") or {}).get("build_target") or "App")
    state_path = workspace / "state.json"
    outputs_dir_name = (config.get("output_dir") or "outputs").rstrip("/\\")
    outputs_dir = workspace / outputs_dir_name
    netlist_path = outputs_dir / "circuit_netlist.json"

    # ---- 2. 确定 eda_tool：命令行 > config.schematic_format > config.eda_tool > 按扩展名 > altium ----
    ext_tool = EXT_TOOL_MAP.get(schematic_path.suffix.lower())
    fmt = config.get("schematic_format")
    fmt_tool = FORMAT_TOOL_MAP.get(fmt) if fmt else None
    if fmt and fmt_tool is None:
        _log(f"警告: 配置中 schematic_format={fmt} 无法识别，忽略")
    eda_tool = args.eda_tool or fmt_tool or config.get("eda_tool")
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
            "配置中 schematic_path 未配置",
        )
        _update_state(state_path, circuit)
        _log("配置中 schematic_path 未配置")
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
    # PDF 输入：提取置信度元数据（源文件适配器无 pdf_meta，保持 v1.0 行为）
    pdf_meta = None
    if eda_tool == "pdf":
        pdf_meta = result.get("pdf_meta") or {
            "source_format": "pdf", "confidence": 0.0,
            "low_confidence_count": 0, "review_low": [], "review_mid": [],
        }
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

    # ---- 6. 校验网表结构并写入 outputs/circuit_netlist.json ----
    netlist_errors = _validate(
        netlist_doc, SKILL_DIR / "schemas" / "netlist.schema.json", "netlist.schema"
    )
    if netlist_errors:
        circuit = _make_circuit_payload(
            netlist_path, workspace, stats, "failed", eda_tool, schematic_path,
            "网表结构校验失败: " + "; ".join(netlist_errors),
        )
        _update_state(state_path, circuit)
        _log("网表结构校验失败: " + "; ".join(netlist_errors))
        return EXIT_FAILED
    _save_json(netlist_path, netlist_doc)

    # ---- 6.5 生成引脚配置 Excel（outputs/pin_table.xlsx，格式见 references/excel_format.md）----
    excel_path = outputs_dir / "pin_table.xlsx"
    try:
        from excel_export import export_pin_table

        _, excel_warnings = export_pin_table(netlist_doc, excel_path)
        for w in excel_warnings:
            _log(f"警告: {w}")
    except ImportError as exc:
        excel_path = None
        _log(f"Excel 导出跳过: {exc}")
    except Exception as exc:  # noqa: BLE001
        excel_path = None
        _log(f"Excel 导出失败: {type(exc).__name__}: {exc}")

    # ---- 6.6 生成人工核对清单（outputs/pdf_review.md，仅 PDF 输入）----
    review_path: Path | None = None
    if pdf_meta is not None:
        review_path = outputs_dir / "pdf_review.md"
        try:
            _write_pdf_review(pdf_meta, schematic_path, stats, review_path)
            _log(f"人工核对清单已生成: {review_path}")
        except Exception as exc:  # noqa: BLE001
            review_path = None
            _log(f"人工核对清单生成失败: {type(exc).__name__}: {exc}")

    # ---- 7. 写入 state.json 的 circuit 字段并校验 ----
    circuit = _make_circuit_payload(
        netlist_path, workspace, stats, parse_status, eda_tool, schematic_path,
        "; ".join(warnings) if warnings else None, excel_path,
        pdf_meta=pdf_meta, review_path=review_path,
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
