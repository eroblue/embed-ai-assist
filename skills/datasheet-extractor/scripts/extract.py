#!/usr/bin/env python
"""datasheet-extractor 主入口（S3，数据输入层）。

执行步骤：
1. 分层加载配置：根目录 config.json（全局默认）→ 项目 config.json（覆盖/补充）→ 深合并
2. 读取 platform / datasheet_path / datasheet_secondary_path / svd_path / extract_scope
3. 按 platform 前缀选择适配器（stm32* / gd32* / fm32*）
4. 调用适配器提取：引脚定义（datasheet PDF）+
   寄存器/时钟树/外设（优先 SVD，无 SVD 时回退参考手册 PDF 解析）
5. 逐产物用对应 schema 校验，全部通过后才写入 outputs/chip_info/（不留半成品）
6. 生成 pin_table.xlsx 与 register_map.xlsx（openpyxl 缺失时降级跳过）
7. 将指针与统计信息写入项目 state.json 的 chip 字段（不触碰其他 Skill 字段）

禁止事项：不修改 config.json；不读写 state.json 中其他 Skill 的字段；
不修改 outputs/ 中非本 Skill 产出的文件。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent  # embed-ai-assist/（根目录）

sys.path.insert(0, str(SCRIPT_DIR))

from adapters import ADAPTER_PREFIXES  # noqa: E402

GENERATOR = "datasheet-extractor"
SCOPES = ("pins", "registers", "clocks", "peripherals", "all")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[datasheet-extractor] {msg}", file=sys.stderr)


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


def _update_state(state_path: Path, chip: dict) -> None:
    """只更新 state.json 的 chip 字段，保留其他字段。"""
    state = {}
    if state_path.exists():
        try:
            state = _load_json(state_path)
        except (json.JSONDecodeError, OSError) as exc:
            _log(f"state.json 读取失败，将重建: {exc}")
    state["chip"] = chip
    _save_json(state_path, state)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    """分层加载：根目录 config.json（全局默认）→ 项目 config.json → 深合并。"""
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


def _resolve_path(raw: str, project_dir: Path) -> Path:
    """路径解析：platforms/ 开头相对根目录，否则相对项目目录。"""
    raw = (raw or "").strip()
    p = Path(raw)
    if p.is_absolute():
        return p
    if raw.replace("\\", "/").startswith("platforms/"):
        return (ROOT_DIR / p).resolve()
    return (project_dir / p).resolve()


def _make_chip_payload(
    data: dict,
    written: dict,
    workspace: Path,
    chip_dir: Path,
    status: str,
    scope_done: str,
    error: str | None,
) -> dict:
    """组装 state.json 的 chip 字段（仅指针与统计）。"""
    rel = lambda name: _rel_path(chip_dir / name, workspace)
    return {
        "datasheet_path": str(data.get("_datasheet_abs", "") or "") or None,
        "datasheet_secondary_path": (
            str(data.get("_secondary_abs")) if data.get("_secondary_abs") else None
        ),
        "svd_path": str(data.get("_svd_abs")) if data.get("_svd_abs") else None,
        "sdk_header_path": str(data.get("_sdk_abs")) if data.get("_sdk_abs") else None,
        "mcu_family": data.get("mcu_family") or "",
        "package": data.get("package"),
        "pin_count": data.get("pin_count") or 0,
        "pin_defined_count": len(data.get("pins") or []),
        "register_count": len(data.get("registers") or []),
        "peripheral_count": len(data.get("peripherals") or []),
        "pins_path": rel("pins.json") if written.get("pins") else None,
        "registers_path": rel("registers.json") if written.get("registers") else None,
        "clock_tree_path": rel("clock_tree.json") if written.get("clock_tree") else None,
        "peripherals_path": rel("peripherals.json") if written.get("peripherals") else None,
        "pin_table_excel_path": rel("pin_table.xlsx") if written.get("pin_excel") else None,
        "register_map_excel_path": rel("register_map.xlsx") if written.get("reg_excel") else None,
        "extract_status": status,
        "extract_scope": scope_done,
        "error": error,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="datasheet-extractor: 从 MCU 手册 PDF 提取引脚/寄存器/时钟树/外设数据"
    )
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径（只读）")
    parser.add_argument("--platform", default=None, help="覆盖 platform（仅本次生效）")
    parser.add_argument("--datasheet", default=None, help="覆盖 datasheet_path（仅本次生效）")
    parser.add_argument("--secondary", default=None, help="覆盖 datasheet_secondary_path（仅本次生效）")
    parser.add_argument("--svd", default=None, help="覆盖 svd_path（仅本次生效；CMSIS-SVD 优先数据源）")
    parser.add_argument("--sdk", default=None, help="覆盖 sdk_header_path（仅本次生效；厂商设备头文件，第二优先数据源）")
    parser.add_argument("--scope", choices=list(SCOPES), default=None, help="覆盖 extract_scope（仅本次生效）")
    args = parser.parse_args(argv)

    # ---- 1. 分层加载配置 ----
    config_path = Path(args.config).resolve()
    try:
        config, notes = _load_layered_config(config_path)
    except FileNotFoundError as exc:
        _log(str(exc))
        return EXIT_CONFIG_ERROR
    for note in notes:
        _log(note)

    # 命令行覆盖（仅本次生效，不回写 config.json）
    if args.platform:
        config["platform"] = args.platform
    if args.datasheet:
        config["datasheet_path"] = args.datasheet
    if args.secondary is not None:
        config["datasheet_secondary_path"] = args.secondary
    if args.svd is not None:
        config["svd_path"] = args.svd
    if args.sdk is not None:
        config["sdk_header_path"] = args.sdk
    if args.scope:
        config["extract_scope"] = args.scope

    project_dir = config_path.parent
    workspace = project_dir
    state_path = workspace / "state.json"

    # ---- 2. 输入契约校验 ----
    platform = (config.get("platform") or "").strip()
    datasheet_raw = (config.get("datasheet_path") or "").strip()
    secondary_raw = (config.get("datasheet_secondary_path") or "").strip()
    svd_raw = (config.get("svd_path") or "").strip()
    sdk_raw = (config.get("sdk_header_path") or "").strip()
    scope_req = (config.get("extract_scope") or "all").strip().lower()

    input_errors = _validate(
        {
            "platform": platform,
            "datasheet_path": datasheet_raw,
            "datasheet_secondary_path": secondary_raw or None,
            "svd_path": svd_raw or None,
            "sdk_header_path": sdk_raw or None,
            "workspace": str(workspace),
            "extract_scope": scope_req,
        },
        SKILL_DIR / "schemas" / "input.schema.json",
        "input",
    )
    if not platform or not datasheet_raw:
        _log("config.json 缺少 platform 或 datasheet_path")
        return EXIT_CONFIG_ERROR
    if input_errors:
        for e in input_errors:
            _log(e)
        return EXIT_CONFIG_ERROR

    datasheet_path = _resolve_path(datasheet_raw, project_dir)
    secondary_path = _resolve_path(secondary_raw, project_dir) if secondary_raw else None
    svd_path = _resolve_path(svd_raw, project_dir) if svd_raw else None
    if svd_path is not None and not svd_path.is_file():
        _log(f"SVD 文件不存在，忽略 svd_path: {svd_path}")
        svd_path = None
    sdk_path = _resolve_path(sdk_raw, project_dir) if sdk_raw else None
    if sdk_path is not None and not sdk_path.is_file():
        _log(f"SDK 头文件不存在，忽略 sdk_header_path: {sdk_path}")
        sdk_path = None
    if not datasheet_path.is_file():
        chip = {
            "datasheet_path": None, "datasheet_secondary_path": None, "svd_path": None,
            "sdk_header_path": None,
            "mcu_family": "", "package": None, "pin_count": 0,
            "pin_defined_count": 0, "register_count": 0, "peripheral_count": 0,
            "pins_path": None, "registers_path": None, "clock_tree_path": None,
            "peripherals_path": None, "pin_table_excel_path": None,
            "register_map_excel_path": None,
            "extract_status": "failed", "extract_scope": "",
            "error": f"数据手册不存在或未配置: {datasheet_path}",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        _update_state(state_path, chip)
        print(json.dumps({"chip": chip}, ensure_ascii=False, indent=2))
        return EXIT_FAILED

    # ---- 3. 选择适配器（前缀映射） ----
    adapter_cls = None
    for prefix, cls in ADAPTER_PREFIXES.items():
        if platform.lower().startswith(prefix):
            adapter_cls = cls
            break
    if adapter_cls is None:
        _log(f"不支持的 platform: {platform}（已注册前缀: {', '.join(ADAPTER_PREFIXES)}）")
        return EXIT_CONFIG_ERROR

    # ---- 4. 提取（数据源优先级：SVD > SDK 头文件 > 参考手册 PDF）----
    _log(f"使用适配器 {adapter_cls.__name__}（platform={platform}, scope={scope_req}）")
    if svd_path is not None:
        _log(f"数据源优先级 1（SVD）: {svd_path}")
    if sdk_path is not None:
        _log(f"数据源优先级 2（SDK 头文件）: {sdk_path}")
    try:
        data = adapter_cls(platform).extract(
            datasheet_path, secondary_path, scope_req, svd_path, sdk_path
        )
    except NotImplementedError as exc:
        _log(str(exc))
        return EXIT_FAILED
    except Exception as exc:
        _log(f"提取异常: {exc}")
        return EXIT_FAILED
    data["_datasheet_abs"] = str(datasheet_path.resolve())
    data["_secondary_abs"] = str(secondary_path.resolve()) if secondary_path else None
    data["_svd_abs"] = str(svd_path.resolve()) if svd_path else None
    data["_sdk_abs"] = str(sdk_path.resolve()) if sdk_path else None

    warnings: list[str] = list(data.get("warnings") or [])
    for w in warnings:
        _log(f"警告: {w}")

    # ---- 5. 逐产物校验并写入（校验失败的不写，不留半成品） ----
    output_dir_raw = (config.get("output_dir") or "outputs/").strip()
    output_dir = (project_dir / output_dir_raw).resolve()
    chip_dir = output_dir / "chip_info"
    now = datetime.now().isoformat(timespec="seconds")

    docs: dict[str, dict] = {}
    secondary_abs = str(secondary_path.resolve()) if secondary_path else None
    svd_abs = data.get("_svd_abs")
    sdk_abs = data.get("_sdk_abs")
    if data.get("pins"):
        docs["pins"] = {
            "schema": "embedaiassist.chip.pins.v1",
            "mcu_family": data.get("mcu_family"),
            "package": data.get("package"),
            "pin_count": data.get("pin_count") or len(data["pins"]),
            "source": {"datasheet": str(datasheet_path.resolve()), "extracted_at": now},
            "pins": data["pins"],
        }
    if data.get("registers"):
        docs["registers"] = {
            "schema": "embedaiassist.chip.registers.v1",
            "mcu_family": data.get("mcu_family"),
            "source": {
                "svd": svd_abs,
                "sdk_header": sdk_abs,
                "reference_manual": secondary_abs,
                "extracted_at": now,
            },
            "registers": data["registers"],
        }
    if data.get("peripherals"):
        docs["peripherals"] = {
            "schema": "embedaiassist.chip.peripherals.v1",
            "mcu_family": data.get("mcu_family"),
            "source": {
                "svd": svd_abs,
                "sdk_header": sdk_abs,
                "reference_manual": secondary_abs,
                "extracted_at": now,
            },
            "peripherals": data["peripherals"],
        }
    if data.get("clock_tree"):
        ct = data["clock_tree"]
        ct["schema"] = "embedaiassist.chip.clocktree.v1"
        ct["mcu_family"] = data.get("mcu_family")
        ct["source"] = {
            "svd": svd_abs,
            "sdk_header": sdk_abs,
            "reference_manual": secondary_abs,
            "datasheet": str(datasheet_path.resolve()),
            "extracted_at": now,
        }
        docs["clock_tree"] = ct

    schema_file = {
        "pins": "pins.schema.json",
        "registers": "registers.schema.json",
        "peripherals": "peripherals.schema.json",
        "clock_tree": "clock_tree.schema.json",
    }
    written: dict[str, bool] = {}
    for key, doc in docs.items():
        errors = _validate(doc, SKILL_DIR / "schemas" / schema_file[key], key)
        if errors:
            for e in errors:
                _log(f"校验失败，不写入 {key}: {e}")
            warnings.append(f"{key} 校验失败未写入")
            continue
        _save_json(chip_dir / f"{key}.json", doc)
        written[key] = True

    # ---- 6. Excel 导出（降级：openpyxl 缺失跳过） ----
    if written.get("pins"):
        try:
            from excel_export import export_pin_table

            _, excel_warnings = export_pin_table(docs["pins"], chip_dir / "pin_table.xlsx")
            written["pin_excel"] = True
            warnings.extend(excel_warnings)
        except ImportError as exc:
            _log(f"openpyxl 未安装，跳过引脚 Excel: {exc}")
            warnings.append("pin_table.xlsx 未生成（openpyxl 缺失）")
        except Exception as exc:
            _log(f"引脚 Excel 生成失败: {exc}")
            warnings.append(f"pin_table.xlsx 生成失败: {exc}")
    if written.get("registers"):
        try:
            from excel_export import export_register_map

            _, excel_warnings = export_register_map(docs["registers"], chip_dir / "register_map.xlsx")
            written["reg_excel"] = True
            warnings.extend(excel_warnings)
        except ImportError as exc:
            _log(f"openpyxl 未安装，跳过寄存器 Excel: {exc}")
            warnings.append("register_map.xlsx 未生成（openpyxl 缺失）")
        except Exception as exc:
            _log(f"寄存器 Excel 生成失败: {exc}")
            warnings.append(f"register_map.xlsx 生成失败: {exc}")

    # ---- 7. 汇总状态与 scope ----
    completed = []
    if written.get("pins"):
        completed.append("pins")
    if written.get("registers"):
        completed.append("registers")
    if written.get("clock_tree"):
        completed.append("clocks")
    if written.get("peripherals"):
        completed.append("peripherals")

    requested = (
        ["pins", "registers", "clocks", "peripherals"]
        if scope_req == "all"
        else [scope_req]
    )
    if not completed:
        status = "failed"
        scope_done = ""
    else:
        missing = [s for s in requested if s not in completed]
        status = "success" if not missing else "partial"
        scope_done = "all" if len(completed) == 4 else ",".join(completed)

    if status == "success":
        error = None
    elif status == "partial":
        missing = [s for s in requested if s not in completed]
        parts = [f"未完成: {', '.join(missing)}"] + warnings
        error = "; ".join(dict.fromkeys(parts))
    else:
        error = "; ".join(warnings) or "提取失败（无产物）"

    chip = _make_chip_payload(data, written, workspace, chip_dir, status, scope_done, error)
    state_errors = _validate(chip, SKILL_DIR / "schemas" / "output.schema.json", "output")
    if state_errors:
        for e in state_errors:
            _log(e)

    _update_state(state_path, chip)
    _log(
        f"提取完成: status={status}, scope={scope_done}, "
        f"pins={chip['pin_defined_count']}, registers={chip['register_count']}, "
        f"peripherals={chip['peripheral_count']}"
    )
    print(json.dumps({"chip": chip}, ensure_ascii=False, indent=2))

    return EXIT_OK if status in ("success", "partial") else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
