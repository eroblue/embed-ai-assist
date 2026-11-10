"""Shared rule helpers for S11 log analysis."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


class S11Error(Exception):
    pass


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    temporary.replace(path)


def schema_errors(instance: Any, schema_path: Path, label: str) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise S11Error("缺少 jsonschema 依赖：请安装 jsonschema 后重试。") from exc
    schema = load_json(schema_path)
    errors = Draft202012Validator(schema).iter_errors(instance)
    return [f"{label} / {'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve_sources(values: list[Path]) -> list[tuple[Path, Path | None]]:
    """Return (log path, optional S10 session manifest) pairs."""
    result: list[tuple[Path, Path | None]] = []
    for value in values:
        path = value.expanduser().resolve()
        if path.is_dir():
            log_path = path / "capture.log"
            manifest = path / "session.json"
            if not log_path.is_file():
                raise S11Error(f"目录不是有效的 S10 会话（缺少 capture.log）：{path}")
            result.append((log_path, manifest if manifest.is_file() else None))
        elif path.is_file():
            manifest = path.parent / "session.json"
            result.append((path, manifest if manifest.is_file() else None))
        else:
            raise S11Error(f"输入路径不存在：{path}")
    return result


def read_s10_log(path: Path, source_id: str) -> tuple[list[dict[str, Any]], str | None, list[str]]:
    """Reconstruct logical lines from S10 rx text while retaining record references."""
    warnings: list[str] = []
    segments: list[tuple[int, str | None, str]] = []
    header: str | None = None
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            for record_no, raw in enumerate(f, start=1):
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    warnings.append(f"capture.log 第 {record_no} 行 JSON 无效：{exc.msg}")
                    continue
                kind = record.get("record_type")
                if kind == "header":
                    header = record.get("timestamp_semantics")
                elif kind in ("rx", "decode_tail"):
                    text = record.get("text")
                    if not isinstance(text, str):
                        warnings.append(f"capture.log 第 {record_no} 行缺少文本字段")
                        continue
                    segments.append((record_no, record.get("ts_host"), text))
                else:
                    warnings.append(f"capture.log 第 {record_no} 行记录类型未知：{kind!r}")
    except (OSError, UnicodeError) as exc:
        raise S11Error(f"无法读取 S10 capture.log：{path}: {exc}") from exc

    joined = "".join(segment[2] for segment in segments)
    offsets: list[tuple[int, int, int, str | None]] = []
    cursor = 0
    for record_no, timestamp, text in segments:
        offsets.append((cursor, cursor + len(text), record_no, timestamp))
        cursor += len(text)

    evidence: list[dict[str, Any]] = []
    cursor = 0
    segment_start = 0
    for line_no, text in enumerate(joined.splitlines(keepends=True), start=1):
        end = cursor + len(text)
        while segment_start < len(offsets) and offsets[segment_start][1] <= cursor:
            segment_start += 1
        overlaps = []
        position = segment_start
        while position < len(offsets) and offsets[position][0] < end:
            if offsets[position][1] > cursor:
                overlaps.append(offsets[position])
            position += 1
        evidence.append({
            "evidence_id": f"{source_id}-L{line_no:06d}",
            "line_number": line_no,
            "text": text.rstrip("\r\n"),
            "record_numbers": sorted({item[2] for item in overlaps}),
            "ts_host": next((item[3] for item in overlaps if item[3]), None),
        })
        cursor = end
    if not evidence:
        warnings.append("日志中没有可解析的接收文本记录")
    return evidence, header, warnings


def read_text_log(path: Path, source_id: str, encoding: str) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    try:
        raw = path.read_bytes()
        text = raw.decode(encoding, errors="replace")
    except (OSError, LookupError) as exc:
        raise S11Error(f"无法读取日志或编码名无效：{path}: {exc}") from exc
    replacement_count = text.count("\ufffd")
    if not raw:
        warnings.append("日志文件为空")
    if replacement_count:
        warnings.append(f"解码产生 {replacement_count} 个替代字符（U+FFFD）")
    lines = text.splitlines(keepends=True)
    evidence = [{"evidence_id": f"{source_id}-L{index:06d}",
                 "line_number": index, "text": line.rstrip("\r\n"),
                 "record_numbers": [], "ts_host": None}
                for index, line in enumerate(lines, start=1)]
    return evidence, warnings


def session_context(path: Path | None) -> tuple[dict[str, Any] | None, list[str]]:
    if path is None:
        return None, []
    warnings: list[str] = []
    try:
        manifest = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"S10 session.json 无法解析：{exc}"]
    s9 = manifest.get("s9_context") or {}
    keys = ("session_id", "status", "target", "port", "serial", "started_at",
            "ended_at", "duration_sec", "stop_reason", "bytes_received",
            "chunks_received", "encoding_errors")
    context = {key: manifest[key] for key in keys if key in manifest}
    if s9.get("firmware_sha256"):
        context["firmware_sha256"] = s9["firmware_sha256"]
    return context, warnings


def make_brief(source_index: dict[str, Any], max_lines: int = 180) -> str:
    rows = [row for source in source_index["sources"] for row in source["evidence"]]
    selected = rows
    clipped = False
    repeated = {}
    for row in rows:
        if row["text"].strip():
            repeated.setdefault(row["text"], []).append(row["evidence_id"])
    repeated = {text: ids for text, ids in repeated.items() if len(ids) > 1}
    if len(rows) > max_lines:
        pattern = re.compile(r"error|err\b|fault|fail|warn|assert|panic|init|ready|start|stop|done|success|connected|disconnect|error|失败|错误|异常|告警|初始化|就绪|成功|完成|启动|停止|连接|断开", re.I)
        chosen = {row["evidence_id"]: row for row in rows[:20] + rows[-10:]}
        stride = max(1, len(rows) // 120)
        for row in rows[::stride]:
            chosen[row["evidence_id"]] = row
        for row in rows:
            if pattern.search(row["text"]):
                chosen[row["evidence_id"]] = row
        for ids in repeated.values():
            representative = next((row for row in rows if row["evidence_id"] == ids[0]), None)
            if representative:
                chosen[representative["evidence_id"]] = representative
        selected = list(chosen.values())[:max_lines]
        clipped = len(selected) < len(rows)

    out = ["# S11 分析任务书", "", "请按 `references/analysis_rules.md` 分析日志。每项 finding 必须引用下列 evidence ID。",
           "只整理日志事实和可说明的归纳；不要读代码、推断根因或选择修复 Skill。", "",
           f"输入来源：{len(source_index['sources'])} 个；索引证据：{len(rows)} 条。"]
    for source in source_index["sources"]:
        context = source.get("session_context")
        if context:
            out.extend(["", f"## {source['source_id']} 会话上下文"])
            for key in ("session_id", "status", "started_at", "ended_at", "duration_sec", "stop_reason", "bytes_received", "chunks_received", "encoding_errors", "firmware_sha256"):
                if key in context:
                    out.append(f"- {key}: {context[key]}")
    out.extend(["", "## 日志证据", ""])
    for row in selected:
        where = f"记录 {','.join(map(str, row['record_numbers']))}" if row["record_numbers"] else f"行 {row['line_number']}"
        ts = f" [{row['ts_host']}]" if row.get("ts_host") else ""
        out.append(f"- `{row['evidence_id']}` ({where}){ts}: {row['text'][:500]}")
    if repeated:
        out.extend(["", "## 完全相同记录的重复计数（候选）", ""])
        for text, ids in list(repeated.items())[:40]:
            out.append(f"- {len(ids)} 次；代表记录 `{ids[0]}`；内容：{text[:240]}")
    if clipped:
        out.extend(["", f"> 已从 {len(rows)} 条证据中选取候选片段；完整索引保存在 source_index.json。摘要未展示的行不代表没有相关事件。"])
    if source_index["warnings"]:
        out.extend(["", "## 解析警告", ""])
        out.extend(f"- {warning}" for warning in source_index["warnings"])
    out.extend(["", "## Agent 输出", "", "1. 填写 analysis.json。", "2. 编写 report.md；无错误时仍报告可确认的运行流程。", "3. 运行 validate.py 校验证据引用并收口。"])
    return "\n".join(out) + "\n"
