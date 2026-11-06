"""Double-click launcher for the S10 Windows GUI (runs via pythonw)."""
from pathlib import Path
import sys
import traceback

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import gui
    project_config = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else None
    gui.main(project_config)
except Exception as exc:
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("S10 启动失败", f"{exc}\n\n详细信息已写入启动日志。")
        root.destroy()
    except Exception:
        pass
    log_path = Path.home() / "AppData" / "Roaming" / "embed-ai-assist" / "s10-startup-error.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(traceback.format_exc(), encoding="utf-8")
