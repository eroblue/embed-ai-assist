"""Build the two Windows GUI launchers into tools/*.exe.

Run from any directory with the project's Python environment:
    python tools/build_gui.py s12
    python tools/build_gui.py all
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
BUILD = ROOT / ".build" / "pyinstaller"


def build(which: str) -> None:
    try:
        from PyInstaller.__main__ import run
    except ImportError as exc:
        raise SystemExit("缺少 PyInstaller：python -m pip install pyinstaller") from exc

    skill = "workflow-runner" if which == "s12" else "serial-monitor"
    name = "EmbedAI-S12" if which == "s12" else "EmbedAI-S10"
    script = ROOT / "skills" / skill / "scripts" / ("start_s12.pyw" if which == "s12" else "start_s10.pyw")
    data = [
        (ROOT / "schemas" / "config.schema.json", "schemas"),
        (ROOT / "skills" / skill / "schemas", f"skills/{skill}/schemas"),
    ]
    if which == "s12":
        data.append((ROOT / "skills" / skill / "assets" / "theme.qss", f"skills/{skill}/assets"))
    # Keep unrelated native-tool directories (for example Poppler's ICU DLLs)
    # out of PyInstaller's DLL discovery path.
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    os.environ["PATH"] = os.pathsep.join(str(p) for p in
        [Path(sys.executable).resolve().parent, windows / "System32", windows,
         windows / "System32" / "Wbem"])
    args = [
        "--noconfirm", "--clean", "--onefile", "--windowed", "--noupx",
        "--name", name, "--distpath", str(TOOLS),
        "--workpath", str(BUILD / "work"), "--specpath", str(BUILD / "spec"),
        "--paths", str(ROOT / "skills" / skill / "scripts"),
        "--paths", str(ROOT / "skills" / "_shared" / "scripts"),
    ]
    for source, destination in data:
        args.extend(["--add-data", f"{source};{destination}"])
    args.append(str(script))
    print(f"Building {name} -> {TOOLS / (name + '.exe')}", flush=True)
    run(args)


def main() -> None:
    parser = argparse.ArgumentParser(description="打包 S10/S12 Windows GUI")
    parser.add_argument("target", choices=["s10", "s12", "all"], nargs="?", default="all")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("此打包脚本需在 Windows 上运行")
    for item in (["s10", "s12"] if args.target == "all" else [args.target]):
        build(item)


if __name__ == "__main__":
    main()
