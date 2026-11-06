"""Windows-first Tkinter front end; serial I/O lives in CaptureService."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import analysis
from capture_service import CaptureService


def settings_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return base / "embed-ai-assist" / "s10-settings.json"


class SerialMonitorApp:
    def __init__(self, root: tk.Tk, config_path: Path | None = None):
        self.root = root
        self.root.title("Embed AI Assist · S10 串口监控")
        self.root.geometry("1040x720")
        self.root.minsize(760, 520)
        self.context: dict | None = None
        self.service: CaptureService | None = None
        self.worker: threading.Thread | None = None
        self.events: queue.Queue = queue.Queue(maxsize=2500)
        self.control_events: queue.SimpleQueue = queue.SimpleQueue()
        self.ui_dropped = 0
        self.closing = False
        self.started_mono: float | None = None
        self.bytes_displayed = 0
        self.is_stopping = False
        self.last_session_dir: Path | None = None
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(80, self._poll_events)
        if config_path:
            self.load_project(config_path)
        else:
            recent = self._read_recent()
            if recent and Path(recent).is_file():
                try:
                    self.load_project(Path(recent))
                except Exception:
                    self.choose_project()
            else:
                self.root.after(250, self.choose_project)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        project = ttk.Frame(outer)
        project.pack(fill="x", pady=(0, 8))
        ttk.Label(project, text="项目配置").pack(side="left")
        self.config_label = ttk.Label(project, text="尚未选择", width=80)
        self.config_label.pack(side="left", padx=8, fill="x", expand=True)
        self.choose_button = ttk.Button(project, text="选择项目…", command=self.choose_project)
        self.choose_button.pack(side="right")

        settings = ttk.LabelFrame(outer, text="串口设置", padding=8)
        settings.pack(fill="x", pady=(0, 8))
        for col, label in enumerate(("端口", "波特率", "数据位", "校验", "停止位", "编码")):
            ttk.Label(settings, text=label).grid(row=0, column=col, sticky="w", padx=4)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(settings, textvariable=self.port_var, width=20, state="readonly")
        self.port_combo.grid(row=1, column=0, sticky="ew", padx=4, pady=3)
        self.baud_var = tk.StringVar(value="115200")
        ttk.Entry(settings, textvariable=self.baud_var, width=12).grid(row=1, column=1, sticky="ew", padx=4, pady=3)
        self.bytesize_var = tk.StringVar(value="8")
        ttk.Combobox(settings, textvariable=self.bytesize_var, values=("5", "6", "7", "8"), width=6, state="readonly").grid(row=1, column=2, sticky="ew", padx=4, pady=3)
        self.parity_var = tk.StringVar(value="N")
        ttk.Combobox(settings, textvariable=self.parity_var, values=("N", "E", "O", "M", "S"), width=6, state="readonly").grid(row=1, column=3, sticky="ew", padx=4, pady=3)
        self.stopbits_var = tk.StringVar(value="1")
        ttk.Combobox(settings, textvariable=self.stopbits_var, values=("1", "1.5", "2"), width=6, state="readonly").grid(row=1, column=4, sticky="ew", padx=4, pady=3)
        self.encoding_var = tk.StringVar(value="utf-8")
        ttk.Entry(settings, textvariable=self.encoding_var, width=14).grid(row=1, column=5, sticky="ew", padx=4, pady=3)
        self.refresh_button = ttk.Button(settings, text="刷新端口", command=self.refresh_ports)
        self.refresh_button.grid(row=1, column=6, padx=(8, 2))
        for col in range(6):
            settings.columnconfigure(col, weight=1)
        self.save_defaults_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings, text="保存本次参数为项目默认值", variable=self.save_defaults_var).grid(
            row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(5, 0))
        self.timeout_var = tk.StringVar(value="200")

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))
        self.start_button = ttk.Button(controls, text="开始采集", command=self.start_capture, state="disabled")
        self.start_button.pack(side="left")
        self.pause_button = ttk.Button(controls, text="暂停显示", command=self.toggle_pause, state="disabled")
        self.pause_button.pack(side="left", padx=6)
        self.clear_button = ttk.Button(controls, text="清空显示", command=self.clear_display, state="disabled")
        self.clear_button.pack(side="left")
        self.open_dir_button = ttk.Button(controls, text="打开日志目录", command=self.open_log_dir, state="disabled")
        self.open_dir_button.pack(side="right")

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(outer, textvariable=self.status_var, anchor="w").pack(fill="x", pady=(0, 5))
        log_frame = ttk.Frame(outer)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="none", state="disabled", font=("Consolas", 10), undo=False)
        yscroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        xscroll = ttk.Scrollbar(outer, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x")
        self.paused = False

    def _read_recent(self) -> str | None:
        try:
            return json.loads(settings_path().read_text(encoding="utf-8")).get("last_config")
        except (OSError, ValueError, AttributeError):
            return None

    def _save_recent(self, config_path: Path) -> None:
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        analysis.save_json_atomic(path, {"last_config": str(config_path.resolve())})

    def choose_project(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root, title="选择项目 config.json",
            filetypes=(("项目配置", "config.json"), ("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if not selected:
            if not self.context:
                self.status_var.set("请选择项目 config.json 后开始")
            return
        try:
            self.load_project(Path(selected))
        except Exception as exc:
            messagebox.showerror("项目配置无效", str(exc), parent=self.root)

    def load_project(self, config_path: Path) -> None:
        context = analysis.load_context(config_path)
        self.context = context
        self.config_label.configure(text=str(context["project_config_path"]))
        values = context["serial"]
        self.port_var.set(values.get("port") or "")
        self.baud_var.set(str(values["baudrate"]))
        self.bytesize_var.set(str(values["bytesize"]))
        self.parity_var.set(str(values["parity"]))
        self.stopbits_var.set(str(values["stopbits"]))
        self.encoding_var.set(str(values["encoding"]))
        self.timeout_var.set(str(values["read_timeout_ms"]))
        self._save_recent(context["project_config_path"])
        self.refresh_ports()
        self.status_var.set(f"已加载项目 · {context['target']} · 未连接")

    def refresh_ports(self) -> None:
        try:
            ports = analysis.list_ports()
            self._port_meta = {item["device"]: item for item in ports}
            values = [
                item["device"] + (f" — {item['description']}" if item["description"] else "")
                for item in ports
            ]
            current = self.port_var.get().strip().split(" — ", 1)[0]
            display_for = {item["device"]: display for item, display in zip(ports, values)}
            self.port_combo.configure(values=values)
            if current in display_for:
                self.port_var.set(display_for[current])
            elif values and not current:
                self.port_var.set(values[0])
            elif current and current not in display_for:
                self.port_var.set("")
            self.status_var.set(f"发现 {len(values)} 个串口 · 选择端口后开始采集")
            self._update_start_enabled()
        except Exception as exc:
            self.status_var.set("无法枚举串口")
            messagebox.showerror("串口枚举失败", str(exc), parent=self.root)

    def _options(self) -> dict:
        if not self.context:
            raise analysis.S10Error("请先选择项目 config.json。")
        options = {
            "port": self.port_var.get().strip().split(" — ", 1)[0], "baudrate": self.baud_var.get(),
            "bytesize": self.bytesize_var.get(), "parity": self.parity_var.get(),
            "stopbits": self.stopbits_var.get(), "encoding": self.encoding_var.get(),
            "read_timeout_ms": self.timeout_var.get(),
        }
        options = analysis.validate_serial_options(options)
        if options["port"] not in getattr(self, "_port_meta", {}):
            raise analysis.S10Error("所选串口当前未枚举到，请刷新端口列表并重新选择。")
        return options

    def _update_start_enabled(self) -> None:
        if self.context and self.port_var.get() and not self.worker:
            self.start_button.configure(state="normal")
        else:
            self.start_button.configure(state="disabled")

    def start_capture(self) -> None:
        try:
            options = self._options()
            if self.save_defaults_var.get():
                if not messagebox.askyesno("保存串口默认值", "将本次串口参数保存到项目 config.json？", parent=self.root):
                    return
                analysis.save_project_serial(self.context["project_config_path"], options)
            self.service = CaptureService(self.context, options, on_event=self._enqueue_event)
            self.worker = threading.Thread(target=self._run_service, name="s10-capture", daemon=False)
            self.started_mono = time.monotonic()
            self.bytes_displayed = 0
            self.is_stopping = False
            self.capture_summary = ""
            self.start_button.configure(text="停止采集", state="normal", command=self.stop_capture)
            self.pause_button.configure(state="normal")
            self.clear_button.configure(state="normal")
            self.status_var.set(f"正在连接 {options['port']}…")
            self.worker.start()
        except Exception as exc:
            messagebox.showerror("无法开始采集", str(exc), parent=self.root)

    def _run_service(self) -> None:
        try:
            self.service.run()
        except Exception as exc:
            session_dir = self.service.session_dir if self.service else None
            self._enqueue_event({"type": "failed", "message": str(exc), "session_dir": session_dir})

    def _enqueue_event(self, event: dict) -> None:
        if event.get("type") == "data":
            try:
                self.events.put_nowait(event)
            except queue.Full:
                self.ui_dropped += 1
            return
        self.control_events.put(event)

    def stop_capture(self) -> None:
        if self.service:
            self.is_stopping = True
            self.service.request_stop("user_stop")
            self.start_button.configure(state="disabled")
            self.status_var.set("正在停止并保存已采集数据…")

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.configure(text="恢复显示" if self.paused else "暂停显示")

    def clear_display(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _append_text(self, text: str) -> None:
        if self.paused:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        if not text.endswith("\n"):
            self.log_text.insert("end", "\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 6000:
            self.log_text.delete("1.0", f"{line_count - 5000}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll_events(self) -> None:
        processed = 0
        while processed < 100:
            try:
                event = self.control_events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
            processed += 1
        while processed < 400:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
            processed += 1
        if self.service and self.started_mono is not None and not self.is_stopping and self.capture_summary:
            elapsed = time.monotonic() - self.started_mono
            received = (self.service.manifest or {}).get("bytes_received", self.bytes_displayed)
            self.status_var.set(
                f"{self.capture_summary} · {elapsed:.1f} 秒 · {received} bytes · {self.last_session_dir}"
            )
        if self.ui_dropped:
            dropped = self.ui_dropped
            self.ui_dropped = 0
            self.status_var.set(f"实时显示过载，界面略过 {dropped} 条更新；完整数据仍写入文件")
        if self.worker and not self.worker.is_alive() and self.closing:
            self.root.destroy()
            return
        self.root.after(80, self._poll_events)

    def _handle_event(self, event: dict) -> None:
        kind = event.get("type")
        if kind == "status":
            if event.get("status") == "connecting":
                self.status_var.set(f"正在连接 {event.get('port')}…")
            elif event.get("status") == "capturing":
                self.last_session_dir = Path(event["session_dir"])
                self.open_dir_button.configure(state="normal")
                self.capture_summary = (
                    f"采集中 · {event['port']} · {event['baudrate']} {event['bytesize']}"
                    f"{event['parity']}{event['stopbits']:g}"
                )
        elif kind == "data":
            self.bytes_displayed += event.get("bytes", 0)
            stamp = event.get("timestamp", "")
            self._append_text(f"[{stamp}] {event.get('text', '')}")
        elif kind == "finished":
            self.last_session_dir = Path(event["session_dir"])
            manifest = event["manifest"]
            self.status_var.set(
                f"{manifest['status']} · {manifest['bytes_received']} bytes · {self.last_session_dir}"
            )
            self.open_dir_button.configure(state="normal")
            if event.get("error"):
                messagebox.showerror(
                    "采集异常，部分日志已保存",
                    f"{event['error']}\n\n已保存目录：{self.last_session_dir}", parent=self.root)
        elif kind == "failed":
            message = event["message"]
            if event.get("session_dir"):
                message += f"\n\n已保存会话目录：{event['session_dir']}"
            else:
                message += "\n\n连接失败时不会创建空会话。"
            messagebox.showerror("串口采集失败", message, parent=self.root)
            self.status_var.set("连接失败 · 检查端口、占用状态和串口参数后重试")
        if kind in ("finished", "failed"):
            self.worker = None
            self.service = None
            self.start_button.configure(text="开始采集", command=self.start_capture)
            self.pause_button.configure(state="disabled")
            self._update_start_enabled()
            self.is_stopping = False

    def open_log_dir(self) -> None:
        if not self.last_session_dir or not self.last_session_dir.is_dir():
            return
        try:
            os.startfile(str(self.last_session_dir))  # Windows shell open
        except Exception as exc:
            messagebox.showerror("无法打开目录", str(exc), parent=self.root)

    def close(self) -> None:
        if self.worker and self.worker.is_alive():
            self.closing = True
            if self.service:
                self.service.request_stop("user_stop")
            self.status_var.set("正在停止并保存，完成后窗口将关闭…")
            self.start_button.configure(state="disabled")
            return
        self.root.destroy()


def main(config_path: Path | None = None) -> None:
    root = tk.Tk()
    SerialMonitorApp(root, config_path)
    root.mainloop()

\n