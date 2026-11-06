"""S10 non-invasive preflight and port listing (does not create a session)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="S10 串口监控预检查")
    parser.add_argument("--config", required=True, type=Path, help="项目 config.json")
    parser.add_argument("--list-ports", action="store_true", help="枚举串口并退出")
    parser.add_argument("--port", help="覆盖默认端口")
    args = parser.parse_args()
    try:
        if args.list_ports:
            ports = analysis.list_ports()
            if not ports:
                print("未发现可用串口。请连接设备后点击 GUI 刷新，或检查驱动。")
            for item in ports:
                print(f"{item['device']}\t{item['description']}\t{item['hwid']}")
            return 0
        context = analysis.load_context(args.config)
        options = dict(context["serial"])
        if args.port:
            options["port"] = args.port
        options = analysis.validate_serial_options(options)
        analysis.check_no_active_session(context)
        print("配置与串口参数有效。")
        print(f"项目：{context['project_config_path']}")
        print(f"目标：{context['target']}；端口：{options['port']}；波特率：{options['baudrate']}")
        print("此预检查不打开端口、不创建会话。普通用户请双击 start_s10.pyw 使用图形界面。")
        return 0
    except (analysis.S10Error, OSError, ValueError) as exc:
        print(f"S10 预检查失败：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
