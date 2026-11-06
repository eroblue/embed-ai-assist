"""Optional CLI entry point for S10; GUI users should use gui.py/start_s10.pyw."""
from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

import analysis
from capture_service import CaptureService


def main() -> int:
    parser = argparse.ArgumentParser(description="S10 串口采集（高级 CLI）")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--port")
    parser.add_argument("--baudrate", type=int)
    parser.add_argument("--bytesize", type=int)
    parser.add_argument("--parity")
    parser.add_argument("--stopbits", type=float)
    parser.add_argument("--encoding")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--output-dir", type=Path, help="会话目录的父目录；相对项目根解析")
    args = parser.parse_args()
    try:
        context = analysis.load_context(args.config)
        options = dict(context["serial"])
        for key in ("port", "baudrate", "bytesize", "parity", "stopbits", "encoding"):
            value = getattr(args, key)
            if value is not None:
                options[key] = value
        output_root = args.output_dir
        if output_root is not None and not output_root.is_absolute():
            output_root = context["project_root"] / output_root
        service = CaptureService(context, options, args.duration, on_event=_print_event,
                                 output_root=output_root)
        def stop_on_signal(_signum, _frame):
            service.request_stop("user_interrupt")

        signal.signal(signal.SIGINT, stop_on_signal)
        if hasattr(signal, "SIGBREAK"):
            signal.signal(signal.SIGBREAK, stop_on_signal)
        result = service.run()
        print(f"采集结束：{result['session_dir']}")
        print(f"接收 {result['manifest']['bytes_received']} bytes；状态 {result['manifest']['status']}。")
        if result.get("error"):
            print(f"采集异常，已保存已接收的数据：{result['error']}", file=sys.stderr)
            return 1
        return 0
    except analysis.S10Error as exc:
        print(f"S10：{exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"S10：{exc}", file=sys.stderr)
        return 2


def _print_event(event: dict) -> None:
    if event["type"] == "status":
        print(f"[{event['status']}] {event.get('port', '')}", flush=True)
    elif event["type"] == "data" and event.get("text"):
        print(event["text"], end="", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
