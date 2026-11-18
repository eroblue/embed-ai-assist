"""S12 PyQt6 profile editor and read-only run monitor."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QTabWidget, QTextEdit, QVBoxLayout, QWidget)

from config_service import (CATALOG, ROOT, SKILL, SKILLS, STEP_FIELDS, VERSION,
                            list_profiles, profile_path, project_config, read_json,
                            save_profile, save_project, validate_profile)
from progress import read_events


class Window(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        self.setWindowTitle(f"S12 工作流配置 · {VERSION}")
        self.resize(1080, 760)
        self.config_path = None
        self.profile_file = None
        self.fields = {}
        self.step_widgets = {}
        self.profile_name = QLineEdit()
        self.project_name = QLineEdit()
        self.build_target = QComboBox(); self.build_target.addItems(["App", "BootLoader"])
        self.build_system = QComboBox(); self.build_system.addItems(["自动推断", "keil", "iar", "gcc_make", "gcc_cmake", "vendor_ide"])
        self.build_config = QLineEdit()
        self.flash_tool = QComboBox(); self.flash_tool.addItems(["自动推断", "jlink", "jflash", "stlink", "openocd", "pyocd", "vendor_ide"])
        self.serial_port = QLineEdit()
        self.serial_baud = QSpinBox(); self.serial_baud.setRange(1, 10000000)
        self.serial_bytes = QComboBox(); self.serial_bytes.addItems(["5", "6", "7", "8"])
        self.serial_parity = QComboBox(); self.serial_parity.addItems(["N", "E", "O", "M", "S"])
        self.serial_stop = QComboBox(); self.serial_stop.addItems(["1", "1.5", "2"])
        self.serial_encoding = QLineEdit()
        self.serial_timeout = QSpinBox(); self.serial_timeout.setRange(10, 5000)
        self.global_paths = QTextEdit(); self.global_paths.setReadOnly(True); self.global_paths.setMaximumHeight(130)
        self._saved_project_values = None
        self.project_label = QLabel("未选择项目")
        self.profile_combo = QComboBox()
        self.skill_list = QListWidget()
        self.skill_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.skill_list.currentItemChanged.connect(self._show_step)
        self.parameter_area = QScrollArea(); self.parameter_area.setWidgetResizable(True)
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        self.monitor = QTextEdit(); self.monitor.setReadOnly(True)
        self.command = QLineEdit(); self.command.setReadOnly(True)
        self.tabs = QTabWidget()
        self._build_ui()
        self._build_menu()
        self._create_skill_items()
        style = (SKILL / "assets/theme.qss").read_text(encoding="utf-8")
        self.setStyleSheet(style)
        timer = QTimer(self); timer.timeout.connect(self.refresh_monitor); timer.start(1000)
        if config_path:
            self.open_project(Path(config_path))

    def _build_ui(self):
        shell = QWidget(); outer = QVBoxLayout(shell); self.setCentralWidget(shell)
        row = QHBoxLayout(); row.addWidget(self.project_label, 1)
        pick = QPushButton("选择项目…"); pick.clicked.connect(self.choose_project); row.addWidget(pick)
        outer.addLayout(row)
        self.tabs.addTab(self._project_tab(), "通用配置")
        self.tabs.addTab(self._profile_tab(), "工作流配置")
        self.tabs.addTab(self.monitor, "运行监控")
        outer.addWidget(self.tabs)
        self.statusBar().showMessage("请选择项目 config.json")

    def _project_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); form = QFormLayout()
        for label, widget in [("项目名称", self.project_name), ("目标工程", self.build_target)]:
            form.addRow(label, widget)
        layout.addLayout(form)
        layout.addWidget(QLabel("机器共用工具路径（根目录 config.json，只读）"))
        layout.addWidget(self.global_paths)
        layout.addWidget(QLabel("编译、烧录和串口的项目默认参数，请到工作流配置中对应的 Skill 面板设置。"))
        save = QPushButton("保存项目通用配置"); save.clicked.connect(self.save_project_settings)
        layout.addWidget(save); layout.addStretch()
        return page

    def _profile_tab(self):
        page = QWidget(); layout = QVBoxLayout(page)
        head = QHBoxLayout(); head.addWidget(QLabel("已有方案")); head.addWidget(self.profile_combo, 1)
        open_button = QPushButton("打开"); open_button.clicked.connect(self.open_selected_profile); head.addWidget(open_button)
        layout.addLayout(head)
        name_row = QHBoxLayout(); name_row.addWidget(QLabel("方案名称")); name_row.addWidget(self.profile_name, 1)
        layout.addLayout(name_row)
        middle = QHBoxLayout(); middle.addWidget(self.skill_list, 2); middle.addWidget(self.parameter_area, 3)
        layout.addLayout(middle, 1)
        refresh = QPushButton("预览生效值与顺序"); refresh.clicked.connect(self.refresh_preview)
        layout.addWidget(refresh); layout.addWidget(self.preview, 1)
        buttons = QHBoxLayout()
        save = QPushButton("确定并保存方案"); save.clicked.connect(self.save_current_profile); buttons.addWidget(save)
        copy = QPushButton("复制执行指令"); copy.clicked.connect(lambda: QApplication.clipboard().setText(self.command.text()))
        buttons.addWidget(copy); layout.addLayout(buttons); layout.addWidget(self.command)
        return page

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("文件")
        for label, handler in [("选择项目…", self.choose_project), ("新建方案", self.new_profile),
                               ("打开方案", self.open_selected_profile), ("保存方案", self.save_current_profile),
                               ("另存为", self.save_current_profile), ("退出", self.close)]:
            action = QAction(label, self); action.triggered.connect(handler); file_menu.addAction(action)
        tools = self.menuBar().addMenu("工具")
        for label, handler in [("校验与预览", self.refresh_preview),
                               ("复制执行指令", lambda: QApplication.clipboard().setText(self.command.text()))]:
            action = QAction(label, self); action.triggered.connect(handler); tools.addAction(action)
        help_menu = self.menuBar().addMenu("帮助")
        about = QAction("关于", self); about.triggered.connect(lambda: QMessageBox.about(self, "关于 S12", f"S12 工作流配置\n版本 {VERSION}\n{ROOT}")); help_menu.addAction(about)
        guide = QAction("使用说明", self); guide.triggered.connect(lambda: QMessageBox.information(self, "使用说明", "选择项目，配置项目设置与工作流方案，保存后复制指令到 Agent 对话框。")); help_menu.addAction(guide)

    def _create_skill_items(self):
        for sid, name, purpose in SKILLS:
            item = QListWidgetItem(f"{sid}  {name}  ·  {purpose}")
            item.setData(Qt.ItemDataRole.UserRole, sid)
            item.setToolTip(f"{sid} · {name}\n{purpose}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            if not (ROOT / "skills" / name / "SKILL.md").exists():
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip(item.toolTip() + "\n尚未实现")
            self.skill_list.addItem(item)

    def _show_step(self, item, previous):
        if not item:
            return
        sid = item.data(Qt.ItemDataRole.UserRole)
        if sid in self.step_widgets:
            self.parameter_area.takeWidget()
            self.parameter_area.setWidget(self.step_widgets[sid])
            return
        widget = QWidget(); layout = QVBoxLayout(widget)
        self.step_widgets[sid] = widget
        layout.addWidget(QLabel(f"{sid} · {CATALOG[sid][0]}"))
        layout.addWidget(QLabel(CATALOG[sid][1]))
        project_form = QFormLayout()
        project_widgets = {
            "S7b": [("构建方式", self.build_system), ("构建配置", self.build_config)],
            "S9": [("烧录工具", self.flash_tool)],
            "S10": [("串口", self.serial_port), ("波特率", self.serial_baud),
                    ("数据位", self.serial_bytes), ("校验位", self.serial_parity),
                    ("停止位", self.serial_stop), ("编码", self.serial_encoding),
                    ("读取超时 ms", self.serial_timeout)],
        }
        if sid in project_widgets:
            layout.addWidget(QLabel("项目默认参数 · 保存在项目 config.json"))
            for label, control in project_widgets[sid]:
                project_form.addRow(label, control)
            layout.addLayout(project_form)
            save_defaults = QPushButton("保存项目默认参数")
            save_defaults.clicked.connect(self.save_project_settings)
            layout.addWidget(save_defaults)
        if STEP_FIELDS.get(sid):
            layout.addWidget(QLabel("仅当前方案覆盖（可选，留空使用项目默认值）"))
        form = QFormLayout()
        self.fields.setdefault(sid, {})
        for key, label, kind, choices in STEP_FIELDS.get(sid, []):
            if key not in self.fields[sid]:
                if kind == "bool":
                    control = QCheckBox()
                elif kind == "int":
                    control = QSpinBox(); control.setRange(0, 10000000); control.setSpecialValueText("使用项目默认值")
                elif kind == "choice":
                    control = QComboBox(); control.addItems(["使用项目默认值"] + choices)
                else:
                    control = QLineEdit(); control.setPlaceholderText("留空则使用项目默认值")
                self.fields[sid][key] = control
            form.addRow(label, self.fields[sid][key])
        layout.addLayout(form); layout.addStretch()
        self.parameter_area.takeWidget()
        self.parameter_area.setWidget(widget)

    def choose_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, "选择项目 config.json", "", "JSON (*.json)")
        if filename:
            self.open_project(Path(filename))

    def open_project(self, path):
        try:
            data = project_config(path)
            self.config_path = path.resolve(); self.project_label.setText(str(self.config_path))
            p = data.get("project") or {}; serial = p.get("serial") or {}
            self.project_name.setText(p.get("name") or path.parent.name)
            self._combo(self.build_target, p.get("build_target") or "App")
            self._combo(self.build_system, p.get("build_system") or "自动推断")
            self.build_config.setText(p.get("build_config") or "")
            self._combo(self.flash_tool, p.get("flash_tool") or "自动推断")
            self.serial_port.setText(serial.get("port") or "")
            self.serial_baud.setValue(serial.get("baudrate", 115200))
            self._combo(self.serial_bytes, str(serial.get("bytesize", 8)))
            self._combo(self.serial_parity, serial.get("parity", "N"))
            self._combo(self.serial_stop, str(serial.get("stopbits", 1)))
            self.serial_encoding.setText(serial.get("encoding", "utf-8"))
            self.serial_timeout.setValue(serial.get("read_timeout_ms", 200))
            global_cfg = read_json(ROOT / "config.json")
            self.global_paths.setPlainText(json.dumps(global_cfg.get("tool_paths", {}), ensure_ascii=False, indent=2))
            self._saved_project_values = self._project_values()
            self.reload_profiles(); self.new_profile()
            self.statusBar().showMessage(f"项目：{self.config_path.parent}")
        except Exception as exc:
            QMessageBox.critical(self, "打开项目失败", str(exc))

    @staticmethod
    def _combo(combo, value):
        index = combo.findText(str(value)); combo.setCurrentIndex(max(index, 0))

    def save_project_settings(self):
        if not self.config_path:
            return
        try:
            values = self._project_values()
            save_project(self.config_path, values)
            self._saved_project_values = values
            self.statusBar().showMessage("项目默认参数已保存")
        except Exception as exc:
            QMessageBox.critical(self, "保存项目设置失败", str(exc))

    def _project_values(self):
        old = (project_config(self.config_path).get("project") or {}) if self.config_path else {}
        serial = dict(old.get("serial") or {})
        serial.update({"port": self.serial_port.text().strip() or None,
                       "baudrate": self.serial_baud.value(), "bytesize": int(self.serial_bytes.currentText()),
                       "parity": self.serial_parity.currentText(), "stopbits": float(self.serial_stop.currentText()),
                       "encoding": self.serial_encoding.text().strip(),
                       "read_timeout_ms": self.serial_timeout.value()})
        return {"name": self.project_name.text().strip(), "build_target": self.build_target.currentText(),
                "build_system": None if self.build_system.currentIndex() == 0 else self.build_system.currentText(),
                "build_config": self.build_config.text().strip(),
                "flash_tool": None if self.flash_tool.currentIndex() == 0 else self.flash_tool.currentText(),
                "serial": serial}

    def reload_profiles(self):
        self.profile_combo.clear()
        if self.config_path:
            for path in list_profiles(self.config_path):
                self.profile_combo.addItem(path.stem, path)

    def new_profile(self):
        self.profile_file = None; self.profile_name.clear(); self.command.clear()
        for i in range(self.skill_list.count()):
            self.skill_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        for controls in self.fields.values():
            for control in controls.values():
                if isinstance(control, QLineEdit): control.clear()
                elif isinstance(control, QCheckBox): control.setChecked(False)
                elif isinstance(control, QComboBox): control.setCurrentIndex(0)
                elif isinstance(control, QSpinBox): control.setValue(0)
        self.preview.clear()

    def open_selected_profile(self):
        path = self.profile_combo.currentData()
        if not path:
            return
        try:
            data = read_json(path); validate_profile(path, data)
            self.new_profile(); self.profile_file = path; self.profile_name.setText(data["name"])
            by_id = {s["id"]: s for s in data["steps"]}
            # Restore saved order, followed by the remaining catalog items.
            order = [s["id"] for s in data["steps"]] + [s for s in CATALOG if s not in by_id]
            for position, sid in enumerate(order):
                matches = self.skill_list.findItems(sid + "  ", Qt.MatchFlag.MatchStartsWith)
                if matches:
                    item = self.skill_list.takeItem(self.skill_list.row(matches[0]))
                    self.skill_list.insertItem(position, item)
                    item.setCheckState(Qt.CheckState.Checked if by_id.get(sid, {}).get("enabled") else Qt.CheckState.Unchecked)
                for key, value in by_id.get(sid, {}).get("params", {}).items():
                    self._ensure_fields(sid)
                    control = self.fields[sid].get(key)
                    if isinstance(control, QLineEdit): control.setText(str(value))
                    elif isinstance(control, QCheckBox): control.setChecked(bool(value))
                    elif isinstance(control, QComboBox): self._combo(control, value)
                    elif isinstance(control, QSpinBox): control.setValue(int(value))
            self.command.setText(f"执行 S12，配置文件：{path.resolve()}")
            self.refresh_preview(); self.refresh_monitor()
        except Exception as exc:
            QMessageBox.critical(self, "打开方案失败", str(exc))

    def _ensure_fields(self, sid):
        if sid not in self.fields or not self.fields[sid]:
            for i in range(self.skill_list.count()):
                item = self.skill_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == sid:
                    self._show_step(item, None); break

    def _profile_data(self):
        if not self.config_path:
            raise ValueError("请先选择项目")
        if self._saved_project_values != self._project_values():
            raise ValueError("项目默认参数有未保存的修改，请先在对应 Skill 面板保存")
        target = (project_config(self.config_path).get("project") or {}).get("build_target") or "App"
        if target != self.build_target.currentText():
            raise ValueError("目标工程有未保存修改，请先保存项目设置")
        steps = []
        for i in range(self.skill_list.count()):
            item = self.skill_list.item(i); sid = item.data(Qt.ItemDataRole.UserRole)
            params = {}
            for key, control in self.fields.get(sid, {}).items():
                if isinstance(control, QLineEdit) and control.text().strip(): params[key] = control.text().strip()
                elif isinstance(control, QCheckBox) and control.isChecked(): params[key] = True
                elif isinstance(control, QComboBox) and control.currentIndex() > 0:
                    value = control.currentText()
                    params[key] = int(value) if key == "bytesize" else float(value) if key == "stopbits" else value
                elif isinstance(control, QSpinBox) and control.value() > 0: params[key] = control.value()
            steps.append({"id": sid, "skill": CATALOG[sid][0],
                          "enabled": item.checkState() == Qt.CheckState.Checked, "params": params})
        return {"schema_version": "1.0", "name": self.profile_name.text().strip(),
                "project_config": "../config.json", "build_target": target, "steps": steps}

    def refresh_preview(self):
        try:
            data = self._profile_data()
            path = profile_path(self.config_path, data["name"])
            validate_profile(path, data)
            project = project_config(self.config_path).get("project") or {}
            lines = [f"项目：{project.get('name') or self.config_path.parent.name}", f"目标：{data['build_target']}"]
            for step in data["steps"]:
                if not step["enabled"]: continue
                lines.append(f"{step['id']} {step['skill']}")
                for key, value in step["params"].items(): lines.append(f"    {key}: {value}（方案覆盖）")
                if step["id"] == "S7b": lines.append(f"    build_system: {project.get('build_system') or '自动推断'}（项目默认）")
                if step["id"] == "S10":
                    for key, value in (project.get("serial") or {}).items():
                        if key not in step["params"]: lines.append(f"    {key}: {value}（项目默认）")
            self.preview.setPlainText("\n".join(lines))
            return data
        except Exception as exc:
            self.preview.setPlainText(str(exc)); return None

    def save_current_profile(self):
        data = self.refresh_preview()
        if data is None: return
        try:
            path = profile_path(self.config_path, data["name"])
            if path.exists() and path != self.profile_file:
                answer = QMessageBox.question(self, "更新方案", f"同名方案已存在：{path.name}\n要覆盖吗？")
                if answer != QMessageBox.StandardButton.Yes: return
            self.profile_file = save_profile(self.config_path, data)
            self.command.setText(f"执行 S12，配置文件：{self.profile_file}")
            self.reload_profiles(); self.statusBar().showMessage(f"已保存：{self.profile_file}")
        except Exception as exc:
            QMessageBox.critical(self, "保存方案失败", str(exc))

    def refresh_monitor(self):
        if not self.config_path: return
        config = project_config(self.config_path)
        target = (config.get("project") or {}).get("build_target") or "App"
        output_dir = (config.get("output_dir") or "outputs").rstrip("/\\")
        root = self.config_path.parent / target / output_dir / "s12"
        runs = sorted(root.glob("*/events.jsonl"), reverse=True) if root.exists() else []
        lines = []
        for path in runs[:10]:
            try:
                events = read_events(path)
                if not events: continue
                if self.profile_file and events[0].get("profile_path") != str(self.profile_file.resolve()): continue
                lines.append(f"运行 {path.parent.name} · {events[0]['ts_host']}")
                starts = {}; waiting = {}; wait_total = {}
                for event in events[1:]:
                    sid = event.get("step_id")
                    if event["event"] == "step_started": starts[sid] = event
                    elif event["event"] == "wait_started": waiting[sid] = event
                    elif event["event"] == "wait_ended" and sid in waiting:
                        wait_total[sid] = wait_total.get(sid, 0) + max(0, (event["monotonic_ns"] - waiting.pop(sid)["monotonic_ns"]) / 1e9)
                    elif event["event"] == "step_finished":
                        total = event.get("duration_s", 0)
                        wait = wait_total.get(sid, 0)
                        lines.append(f"  {sid} {CATALOG.get(sid, ('',))[0]} · {event.get('status')} · 总 {total:.1f}s / 执行 {max(0,total-wait):.1f}s / 等待 {wait:.1f}s")
                    elif event["event"] == "run_finished": lines.append(f"  总计 · {event.get('status')} · {event.get('duration_s', 0):.1f}s")
                if events[-1]["event"] != "run_finished":
                    active = next((sid for sid in reversed(list(starts)) if not any(e["event"] == "step_finished" and e.get("step_id") == sid for e in events)), None)
                    last_time = datetime.fromisoformat(events[-1]["ts_host"])
                    age = (datetime.now().astimezone() - last_time).total_seconds()
                    if active:
                        from time import monotonic_ns
                        elapsed = max(0, (monotonic_ns() - starts[active]["monotonic_ns"]) / 1e9)
                        if age > 90:
                            lines.append(f"  当前：{active} · 状态待核实（{age:.0f}s 无进度更新）")
                        else:
                            label = "等待用户" if active in waiting else "运行中"
                            lines.append(f"  当前：{active} {CATALOG[active][0]} · {label} · {elapsed:.1f}s")
                    elif age > 90:
                        lines.append(f"  状态待核实（{age:.0f}s 无进度更新）")
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                lines.append(f"运行记录读取异常：{path}")
        self.monitor.setPlainText("\n".join(lines) or "暂无运行记录")


def main(config_path=None):
    app = QApplication(sys.argv)
    window = Window(config_path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
