"""Small CLI for Agent-to-S12 GUI progress events; never runs a Skill."""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from config_service import ROOT, SKILL, project_config, read_json, validate_profile


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def events_path(profile: Path, target: str, run_id: str) -> Path:
    config_path = (profile.parent / read_json(profile)["project_config"]).resolve()
    output_dir = (project_config(config_path).get("output_dir") or "outputs").rstrip("/\\")
    return config_path.parent / target / output_dir / "s12" / run_id / "events.jsonl"


def read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append(path: Path, run_id: str, event: str, **fields) -> dict:
    rows = read_events(path)
    if rows and rows[-1]["event"] == "run_finished":
        raise ValueError("运行已经结束")
    item = {"seq": len(rows) + 1, "run_id": run_id, "event": event,
            "ts_host": now(), "monotonic_ns": time.monotonic_ns(), **fields}
    from jsonschema import Draft202012Validator
    Draft202012Validator(read_json(SKILL / "schemas/progress_event.schema.json")).validate(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description="S12 运行进度记录")
    parser.add_argument("event", choices=["start", "step-start", "wait-start", "wait-end", "heartbeat", "step-end", "finish", "abandon", "show"])
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--step-id")
    parser.add_argument("--status", default="done")
    parser.add_argument("--message", default="")
    args = parser.parse_args()
    profile = args.profile.expanduser().resolve()
    data = read_json(profile)
    validate_profile(profile, data)
    target = data["build_target"]
    root = events_path(profile, target, "").parent
    if args.event == "start":
        for other in root.glob("*/events.jsonl"):
            rows = read_events(other)
            if rows and rows[-1]["event"] != "run_finished":
                raise ValueError(f"目标工程已有未结束的 S12 运行：{other.parent.name}")
        run_id = datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        path = events_path(profile, target, run_id)
        append(path, run_id, "run_started", profile_path=str(profile))
        print(run_id)
        return 0
    if not args.run_id:
        parser.error("此操作需要 --run-id")
    path = events_path(profile, target, args.run_id)
    rows = read_events(path)
    if not rows:
        raise ValueError(f"运行不存在：{args.run_id}")
    if args.event == "show":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    event_map = {"step-start": "step_started", "wait-start": "wait_started", "wait-end": "wait_ended",
                 "step-end": "step_finished", "finish": "run_finished", "heartbeat": "heartbeat"}
    fields = {}
    if args.step_id:
        if args.step_id not in {s["id"] for s in data["steps"] if s["enabled"]}:
            raise ValueError("步骤不在已启用列表中")
        fields["step_id"] = args.step_id
    elif args.event.startswith(("step", "wait")):
        raise ValueError("步骤事件需要 --step-id")
    if args.event in ("step-end", "finish", "abandon"):
        fields["status"] = "unknown" if args.event == "abandon" else args.status
    if args.message:
        fields["message"] = args.message
    if args.event in ("step-end", "finish", "abandon"):
        start_type = "step_started" if args.event == "step-end" else "run_started"
        start = next((r for r in reversed(rows) if r["event"] == start_type and
                      (not args.step_id or r.get("step_id") == args.step_id)), None)
        if not start:
            raise ValueError("找不到对应的开始事件")
        fields["duration_s"] = max(0, (time.monotonic_ns() - start["monotonic_ns"]) / 1e9)
    if args.event == "step-start" and any(r["event"] == "step_started" and r.get("step_id") == args.step_id for r in rows):
        raise ValueError("该步骤已开始")
    if args.event == "step-end" and any(r["event"] == "step_finished" and r.get("step_id") == args.step_id for r in rows):
        raise ValueError("该步骤已结束")
    if args.event in ("wait-end",) and not any(r["event"] == "wait_started" and r.get("step_id") == args.step_id for r in rows):
        raise ValueError("找不到等待开始事件")
    item = append(path, args.run_id, "run_finished" if args.event == "abandon" else event_map[args.event], **fields)
    print(json.dumps(item, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"S12：{exc}")
