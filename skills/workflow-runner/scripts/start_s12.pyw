"""Double-click S12 launcher."""
from pathlib import Path
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import gui
    raise SystemExit(gui.main(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
except Exception:
    error = traceback.format_exc()
    path = Path.home() / "AppData" / "Roaming" / "embed-ai-assist" / "s12-startup-error.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(error, encoding="utf-8")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(None, "S12 启动失败", f"{error}\n日志：{path}")
    except Exception:
        pass
