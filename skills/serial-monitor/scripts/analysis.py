"""S10 configuration, paths, schemas, and state helpers."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent
SHARED_DIR = SKILL_DIR.parent / "_shared" / "scripts"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))
import state_store  # noqa: E402

DEFAULT_SERIAL = {
    "port": None,
    "baudrate": 115200,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "encoding": "utf-8",
    "read_timeout_ms": 200,
}


class S10Error(RuntimeError):
    """User-facing S10 error."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def load_json(path: Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def save_json_atomic(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def validate_schema(instance: dict, schema_path: Path, label: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise S10Error("缺少 jsonschema 依赖，请安装项目依赖后重试。") from exc
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    return [f"{label}.{'.'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors]


def load_context(config_path: Path) -> dict:
    config_path = Path(config_path).expanduser().resolve()
    if not config_path.is_file():
        raise S10Error(f"项目 config.json 不存在：{config_path}")
    project_config = load_json(config_path)
    root_config_path = ROOT_DIR / "config.json"
    global_config = load_json(root_config_path) if root_config_path.is_file() else {}
    config = deep_merge(global_config, project_config)
    errors = validate_schema(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if errors:
        raise S10Error("配置契约校验失败：" + "; ".join(errors))
    project_root = config_path.parent
    project = config.get("project") or {}
    target = project.get("build_target") or "App"
    target_root = project_root / target
    state_path = target_root / "state.json"
    state = load_json(state_path) if state_path.is_file() else {}
    if not isinstance(state, dict):
        raise S10Error(f"state.json 根对象必须为 JSON object：{state_path}")
    serial_cfg = dict(DEFAULT_SERIAL)
    serial_cfg.update(project.get("serial") or {})
    serial_cfg["port"] = serial_cfg.get("port") or ""
    context = {
        "config": config,
        "project_config_path": config_path,
        "project_root": project_root,
        "target": target,
        "target_root": target_root,
        "state_path": state_path,
        "state": state,
        "serial": serial_cfg,
        "outputs_root": target_root / (config.get("output_dir") or "outputs").rstrip("/\\") / "s10",
    }
    input_errors = validate_schema(state, SKILL_DIR / "schemas" / "input.schema.json", "state")
    if input_errors:
        raise S10Error("S10 可选状态上下文校验失败：" + "; ".join(input_errors))
    return context


def validate_serial_options(options: dict) -> dict:
    result = dict(options)
    port = str(result.get("port") or "").strip()
    if not port:
        raise S10Error("请选择串口端口。")
    try:
        result["baudrate"] = int(result["baudrate"])
        result["bytesize"] = int(result["bytesize"])
        result["stopbits"] = float(result["stopbits"])
        result["read_timeout_ms"] = int(result["read_timeout_ms"])
    except (TypeError, ValueError) as exc:
        raise S10Error("串口波特率、数据位、停止位和读取超时必须是有效数字。") from exc
    if result["baudrate"] <= 0:
        raise S10Error("波特率必须大于 0。")
    if result["bytesize"] not in (5, 6, 7, 8):
        raise S10Error("数据位必须是 5、6、7 或 8。")
    if str(result.get("parity", "N")).upper() not in ("N", "E", "O", "M", "S"):
        raise S10Error("校验位必须是 N、E、O、M 或 S。")
    if result["stopbits"] not in (1.0, 1.5, 2.0):
        raise S10Error("停止位必须是 1、1.5 或 2。")
    if not 10 <= result["read_timeout_ms"] <= 5000:
        raise S10Error("读取超时必须在 10–5000 ms 之间。")
    encoding = str(result.get("encoding") or "utf-8").strip()
    try:
        "".encode(encoding)
    except LookupError as exc:
        raise S10Error(f"Python 不认识字符编码 {encoding!r}。") from exc
    result.update(port=port, parity=str(result.get("parity", "N")).upper(), encoding=encoding)
    return result


def list_ports() -> list[dict]:
    try:
        from serial.tools import list_ports as serial_list_ports
    except ImportError as exc:
        raise S10Error("缺少 pyserial。请使用当前 Python 安装 pyserial 后重试。") from exc
    return [
        {"device": item.device, "description": item.description or "", "hwid": item.hwid or ""}
        for item in serial_list_ports.comports()
    ]


def project_relative(path: Path, target_root: Path) -> str:
    try:
        return path.resolve().relative_to(target_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def check_no_active_session(context: dict, session_dir: Path | None = None) -> None:
    state_path = context["state_path"]
    current_state = load_json(state_path) if state_path.is_file() else {}
    context["state"] = current_state
    latest = current_state.get("s10") or {}
    if latest.get("status") == "running":
        active_dir = latest.get("session_dir")
        if not session_dir or not active_dir:
            raise S10Error("state.json 记录了未收口的 S10 会话；请先用 validate.py 收口后再开始新会话。")
        existing = (context["target_root"] / active_dir).resolve()
        if existing != session_dir.resolve():
            raise S10Error(f"已有 S10 会话尚未收口：{existing}。请先验证该会话。")


def state_payload(context: dict, manifest: dict, session_dir: Path) -> dict:
    status_map = {"running": "running", "completed": "done", "stopped": "done", "error": "error"}
    result = {
        "status": status_map.get(manifest["status"], "interrupted"),
        "session_id": manifest["session_id"],
        "session_dir": project_relative(session_dir, context["target_root"]),
        "capture_bin": project_relative(session_dir / "capture.bin", context["target_root"]),
        "capture_log": project_relative(session_dir / "capture.log", context["target_root"]),
        "session_manifest": project_relative(session_dir / "session.json", context["target_root"]),
        "port": manifest["port"],
        "started_at": manifest["started_at"],
        "ended_at": manifest["ended_at"],
        "bytes_received": manifest["bytes_received"],
        "stop_reason": manifest["stop_reason"],
        "error": manifest["error"],
        "updated_at": now_iso(),
    }
    errors = validate_schema(result, SKILL_DIR / "schemas" / "output.schema.json", "s10")
    if errors:
        raise S10Error("S10 输出契约校验失败：" + "; ".join(errors))
    return result


def update_state_if_present(context: dict, manifest: dict, session_dir: Path) -> None:
    if not context["state_path"].is_file():
        return
    payload = state_payload(context, manifest, session_dir)
    state_store.update_state(context["state_path"], {"s10": payload})


def save_project_serial(config_path: Path, serial_options: dict) -> None:
    """Explicit GUI opt-in only: atomically update project.project.serial."""
    config_path = Path(config_path)
    project_config = load_json(config_path)
    project = project_config.setdefault("project", {})
    project["serial"] = {
        key: serial_options[key]
        for key in ("port", "baudrate", "bytesize", "parity", "stopbits", "encoding", "read_timeout_ms")
    }
    errors = validate_schema(deep_merge(load_json(ROOT_DIR / "config.json") if (ROOT_DIR / "config.json").is_file() else {}, project_config), ROOT_DIR / "schemas" / "config.schema.json", "config")
    if errors:
        raise S10Error("保存的串口配置不符合契约：" + "; ".join(errors))
    save_json_atomic(config_path, project_config)


def create_session(context: dict, serial_options: dict, duration_sec: float | None,
                   output_root: Path | None = None) -> tuple[Path, dict]:
    check_no_active_session(context)
    session_id = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + os.urandom(4).hex()
    session_dir = (output_root or context["outputs_root"]) / session_id
    session_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": "1.0",
        "session_id": session_id,
        "status": "running",
        "target": context["target"],
        "port": serial_options["port"],
        "serial": {key: serial_options[key] for key in ("baudrate", "bytesize", "parity", "stopbits", "encoding", "read_timeout_ms")},
        "started_at": now_iso(),
        "ended_at": None,
        "duration_sec": None,
        "duration_limit_sec": duration_sec,
        "stop_reason": None,
        "bytes_received": 0,
        "chunks_received": 0,
        "capture_bin": "capture.bin",
        "capture_log": "capture.log",
        "encoding_errors": 0,
        "s9_context": None,
        "error": None,
    }
    s9 = context["state"].get("s9")
    if isinstance(s9, dict):
        manifest["s9_context"] = {key: s9.get(key) for key in ("status", "firmware_path", "firmware_sha256", "updated_at") if key in s9}
    errors = validate_schema(manifest, SKILL_DIR / "schemas" / "session.schema.json", "session")
    if errors:
        raise S10Error("新會話不符合 session schema：" + "; ".join(errors))
    save_json_atomic(session_dir / "session.json", manifest)
    (session_dir / "generation_brief.md").write_text(
        "# S10 串口采集会话\n\n"
        f"- 会话 ID：`{session_id}`\n- 目标：`{context['target']}`\n"
        f"- 端口：`{serial_options['port']}`\n- 参数：{serial_options['baudrate']}, {serial_options['bytesize']}{serial_options['parity']}{serial_options['stopbits']}\n"
        f"- 计划时长：{duration_sec if duration_sec is not None else '不限时'} 秒\n"
        "- 模式：RX-only；时间戳为主机接收时间。\n",
        encoding="utf-8",
    )
    update_state_if_present(context, manifest, session_dir)
    return session_dir, manifest
