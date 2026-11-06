"""Validate and close an S10 session, including abandoned running sessions."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="S10 会话校验与 state 收口")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--session-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        context = analysis.load_context(args.config)
        session_dir = args.session_dir.expanduser().resolve()
        manifest_path = session_dir / "session.json"
        if not manifest_path.is_file():
            raise analysis.S10Error(f"会话清单不存在：{manifest_path}")
        manifest = analysis.load_json(manifest_path)
        errors = analysis.validate_schema(manifest, analysis.SKILL_DIR / "schemas" / "session.schema.json", "session")
        if errors:
            raise analysis.S10Error("会话清单不合法：" + "; ".join(errors))
        bin_path, log_path = session_dir / "capture.bin", session_dir / "capture.log"
        if not bin_path.is_file() or not log_path.is_file():
            if manifest["status"] in ("completed", "stopped"):
                raise analysis.S10Error("已收口会话缺少 capture.bin 或 capture.log。")
        state_manifest = copy.deepcopy(manifest)
        actual_bytes = bin_path.stat().st_size if bin_path.is_file() else 0
        count_mismatch = actual_bytes != manifest["bytes_received"]
        if count_mismatch and manifest["status"] != "running":
            raise analysis.S10Error(
                f"原始文件字节数与清单不符：文件 {actual_bytes}，清单 {manifest['bytes_received']}。"
            )
        if count_mismatch:
            state_manifest["bytes_received"] = actual_bytes
        if manifest["status"] == "running":
            state_manifest["status"] = "interrupted"
            state_manifest["stop_reason"] = "process_interrupted"
            state_manifest["error"] = "进程未正常收口；会话数据为部分采集。"
        analysis.update_state_if_present(context, state_manifest, session_dir)
        print(f"校验完成：{manifest['status']}；{manifest['bytes_received']} bytes")
        print(f"原始数据：{bin_path}")
        print(f"可读日志：{log_path}")
        if manifest["status"] == "running":
            print("注意：会话仍为 running，说明进程被强制中断；未修改 session.json 以保留现场。")
            if count_mismatch:
                print(f"state 摘要按 capture.bin 实际大小记录 {actual_bytes} bytes；session.json 保留现场计数。")
            return 1
        return 0
    except (analysis.S10Error, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"S10 validate 失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
