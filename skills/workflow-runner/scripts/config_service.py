"""Project/profile configuration shared by the S12 GUI and agent entry point."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent.parent if FROZEN else Path(__file__).resolve().parents[3]
RESOURCES = Path(sys._MEIPASS) if FROZEN else ROOT
SKILL = RESOURCES / "skills" / "workflow-runner"
VERSION = "0.1.1"

SKILLS = [
    ("S1", "schematic-reader", "原理图解析"),
    ("S2", "spec-reader", "功能规格解析"),
    ("S3", "datasheet-extractor", "芯片资料提取"),
    ("S4", "circuit-investigator", "电路事实核查"),
    ("S5a", "hardware-initializer", "硬件初始化"),
    ("S5b", "port-contract-and-app", "接口与应用生成"),
    ("S5c", "port-implementer", "接口实现"),
    ("S6", "firmware-merger", "固件合并"),
    ("S7a", "toolchain-setup", "工具链配置"),
    ("S7b", "build", "编译构建"),
    ("S8", "unit-test", "单元测试"),
    ("S9", "flash", "固件烧录"),
    ("S10", "serial-monitor", "串口采集"),
    ("S11", "log-analyzer", "日志分析"),
]
CATALOG = {number: (name, purpose) for number, name, purpose in SKILLS}

# (key, label, kind, choices): only options with a verified consumer are editable.
STEP_FIELDS = {
    "S1": [("eda_tool", "EDA 类型", "choice", ["altium", "kicad", "pdf"])],
    "S3": [("scope", "提取范围", "choice", ["pins", "registers", "clocks", "peripherals", "all"])],
    "S5a": [("mode", "执行模式", "choice", ["full", "diff", "code-fix"])],
    "S5b": [("mode", "执行模式", "choice", ["full", "diff", "code-fix"])],
    "S5c": [("mode", "执行模式", "choice", ["full", "diff", "code-fix"])],
    "S7b": [("rebuild", "重新编译", "bool", None)],
    "S8": [("mode", "用例选择模式", "choice", ["budget", "ratio", "explicit", "changed", "all"])],
    "S9": [("firmware", "固件路径", "text", None), ("device", "设备名", "text", None)],
    "S10": [("port", "串口", "text", None), ("baudrate", "波特率", "int", None),
            ("bytesize", "数据位", "choice", ["5", "6", "7", "8"]),
            ("parity", "校验位", "choice", ["N", "E", "O", "M", "S"]),
            ("stopbits", "停止位", "choice", ["1", "1.5", "2"]),
            ("encoding", "编码", "text", None)],
    "S11": [("log_path", "日志文件或会话目录", "text", None),
            ("observation", "观察描述", "text", None)],
}


def read_json(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON 根必须是对象：{path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".s12-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def project_config(path: Path) -> dict:
    path = path.expanduser().resolve()
    data = read_json(path)
    from jsonschema import Draft202012Validator
    root = read_json(ROOT / "config.json")
    merged = dict(root)
    merged.update(data)
    if "project" in root and "project" in data:
        merged["project"] = {**root["project"], **data["project"]}
    errors = list(Draft202012Validator(read_json(RESOURCES / "schemas/config.schema.json")).iter_errors(merged))
    if errors:
        raise ValueError(f"项目配置无效：{errors[0].message}")
    return data


def save_project(path: Path, changes: dict) -> None:
    data = project_config(path)
    project = dict(data.get("project") or {})
    project.update(changes)
    data["project"] = project
    # Validate before replacing the user's file.
    from jsonschema import Draft202012Validator
    root = read_json(ROOT / "config.json")
    merged = {**root, **data, "project": {**root.get("project", {}), **project}}
    errors = list(Draft202012Validator(read_json(RESOURCES / "schemas/config.schema.json")).iter_errors(merged))
    if errors:
        raise ValueError(f"项目设置无效：{errors[0].message}")
    write_json(path, data)


def profile_path(config_path: Path, name: str) -> Path:
    safe = re.sub(r"[^\w\-]+", "-", name.strip(), flags=re.UNICODE).strip("-_")
    if not safe or safe in {".", ".."}:
        raise ValueError("方案名称不能为空")
    return config_path.resolve().parent / "workflows" / f"{safe}.json"


def list_profiles(config_path: Path) -> list[Path]:
    return sorted((config_path.resolve().parent / "workflows").glob("*.json"))


def validate_profile(path: Path, data: dict) -> Path:
    from jsonschema import Draft202012Validator
    errors = list(Draft202012Validator(read_json(SKILL / "schemas/workflow.schema.json")).iter_errors(data))
    if errors:
        raise ValueError(f"方案无效：{errors[0].message}")
    config_path = (path.parent / data["project_config"]).resolve()
    if not config_path.is_file() or config_path.parent / "workflows" != path.parent.resolve():
        raise ValueError("方案必须引用同一项目的 config.json")
    config = project_config(config_path)
    target = (config.get("project") or {}).get("build_target") or "App"
    if target != data["build_target"]:
        raise ValueError(f"目标工程不一致：项目为 {target}，方案为 {data['build_target']}")
    seen = set()
    for step in data["steps"]:
        sid = step["id"]
        if sid in seen or sid not in CATALOG or step["skill"] != CATALOG[sid][0]:
            raise ValueError(f"重复或未知的 Skill：{sid}")
        if step["enabled"] and not (ROOT / "skills" / step["skill"] / "SKILL.md").is_file():
            raise ValueError(f"Skill 尚未实现：{sid}")
        specs = {field[0]: field for field in STEP_FIELDS.get(sid, [])}
        allowed = set(specs)
        if set(step["params"]) - allowed:
            raise ValueError(f"{sid} 包含尚未适配的参数")
        for key, value in step["params"].items():
            _, _, kind, choices = specs[key]
            if kind == "bool" and not isinstance(value, bool):
                raise ValueError(f"{sid}.{key} 应为布尔值")
            if kind == "int" and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise ValueError(f"{sid}.{key} 应为正整数")
            if kind == "choice" and not (str(value) in choices or
                    (key == "stopbits" and isinstance(value, (int, float)) and float(value) in (1, 1.5, 2))):
                raise ValueError(f"{sid}.{key} 不在允许选项中")
            if kind == "text" and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{sid}.{key} 应为非空文本")
        seen.add(sid)
    if not any(s["enabled"] for s in data["steps"]):
        raise ValueError("至少勾选一个 Skill")
    return config_path


def save_profile(config_path: Path, data: dict) -> Path:
    path = profile_path(config_path, data["name"])
    validate_profile(path, data)
    write_json(path, data)
    return path
