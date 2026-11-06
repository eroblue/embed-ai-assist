"""Shared RX-only serial capture engine used by the GUI and CLI."""
from __future__ import annotations

import base64
import codecs
import json
import threading
import time
from pathlib import Path
from typing import Callable

import analysis


class CaptureService:
    def __init__(self, context: dict, options: dict, duration_sec: float | None = None,
                 on_event: Callable[[dict], None] | None = None, output_root: Path | None = None):
        self.context = context
        self.options = analysis.validate_serial_options(options)
        self.duration_sec = float(duration_sec) if duration_sec is not None else None
        self.output_root = Path(output_root).resolve() if output_root else None
        if self.output_root is not None:
            try:
                self.output_root.relative_to(context["target_root"].resolve())
            except ValueError as exc:
                raise analysis.S10Error("--output-dir 必须位于当前目标工程目录内，确保 state 路径可追溯。") from exc
        if self.duration_sec is not None and self.duration_sec <= 0:
            raise analysis.S10Error("采集时长必须大于 0 秒。")
        self.on_event = on_event or (lambda _event: None)
        self._stop = threading.Event()
        self._stop_reason = "user_stop"
        self.session_dir: Path | None = None
        self.manifest: dict | None = None
        self.result: dict | None = None
        self.ui_dropped = 0

    def emit(self, kind: str, **payload) -> None:
        try:
            self.on_event({"type": kind, **payload})
        except Exception:
            # A UI observer must never interrupt the durable capture path.
            self.ui_dropped += 1

    def request_stop(self, reason: str = "user_stop") -> None:
        self._stop_reason = reason
        self._stop.set()

    @staticmethod
    def _open_serial(options: dict):
        try:
            import serial
        except ImportError as exc:
            raise analysis.S10Error("缺少 pyserial。请使用当前 Python 安装 pyserial 后重试。") from exc
        parity = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD,
                  "M": serial.PARITY_MARK, "S": serial.PARITY_SPACE}[options["parity"]]
        bytesize = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}[options["bytesize"]]
        stopbits = {1.0: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2.0: serial.STOPBITS_TWO}[options["stopbits"]]
        try:
            return serial.Serial(
                port=options["port"], baudrate=options["baudrate"], bytesize=bytesize,
                parity=parity, stopbits=stopbits,
                timeout=options["read_timeout_ms"] / 1000.0,
                write_timeout=0.2, xonxoff=False, rtscts=False, dsrdtr=False,
            )
        except Exception as exc:
            raise analysis.S10Error(
                f"無法打開串口 {options['port']}（{options['baudrate']}, "
                f"{options['bytesize']}{options['parity']}{options['stopbits']:g}）：{exc}"
            ) from exc

    def _write_manifest(self) -> None:
        assert self.session_dir is not None and self.manifest is not None
        analysis.save_json_atomic(self.session_dir / "session.json", self.manifest)

    def run(self) -> dict:
        analysis.check_no_active_session(self.context)
        self.emit("status", status="connecting", port=self.options["port"])
        port = self._open_serial(self.options)
        try:
            self.session_dir, self.manifest = analysis.create_session(
                self.context, self.options, self.duration_sec, self.output_root)
        except Exception:
            port.close()
            raise

        self.emit("status", status="capturing", port=self.options["port"],
                  session_dir=str(self.session_dir), baudrate=self.options["baudrate"],
                  bytesize=self.options["bytesize"], parity=self.options["parity"],
                  stopbits=self.options["stopbits"])
        started_mono = time.monotonic()
        last_flush = started_mono
        decoder = codecs.getincrementaldecoder(self.options["encoding"])(errors="replace")
        output_error: Exception | None = None
        error_reason = "write_error"
        try:
            with (self.session_dir / "capture.bin").open("wb") as raw_file, \
                    (self.session_dir / "capture.log").open("w", encoding="utf-8", newline="\n") as log_file:
                header = {
                    "record_type": "header", "session_id": self.manifest["session_id"],
                    "timestamp_semantics": "host_receive_time", "encoding": self.options["encoding"],
                    "created_at": analysis.now_iso(),
                }
                log_file.write(json.dumps(header, ensure_ascii=False) + "\n")
                log_file.flush()
                while not self._stop.is_set():
                    if self.duration_sec is not None and time.monotonic() - started_mono >= self.duration_sec:
                        self._stop_reason = "duration_reached"
                        break
                    try:
                        data = port.read(4096)
                    except Exception as exc:
                        output_error = exc
                        error_reason = "serial_disconnected"
                        break
                    if data:
                        timestamp = analysis.now_iso()
                        raw_file.write(data)
                        self.manifest["bytes_received"] += len(data)
                        self.manifest["chunks_received"] += 1
                        text = decoder.decode(data, final=False)
                        self.manifest["encoding_errors"] += text.count("\ufffd")
                        record = {
                            "record_type": "rx", "ts_host": timestamp,
                            "data_b64": base64.b64encode(data).decode("ascii"), "text": text,
                        }
                        log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                        self.emit("data", timestamp=timestamp, text=text, bytes=len(data))
                    now = time.monotonic()
                    if now - last_flush >= 0.5:
                        raw_file.flush()
                        log_file.flush()
                        self._write_manifest()
                        last_flush = now
                tail = decoder.decode(b"", final=True)
                if tail:
                    timestamp = analysis.now_iso()
                    self.manifest["encoding_errors"] += tail.count("\ufffd")
                    log_file.write(json.dumps({
                        "record_type": "decode_tail", "ts_host": timestamp,
                        "data_b64": "", "text": tail,
                    }, ensure_ascii=False) + "\n")
                    self.emit("data", timestamp=timestamp, text=tail, bytes=0)
        except KeyboardInterrupt:
            self._stop_reason = "user_interrupt"
            self._stop.set()
        except Exception as exc:
            output_error = exc
        finally:
            try:
                port.close()
            except Exception as exc:
                output_error = output_error or exc

        ended = time.monotonic()
        try:
            raw_path = self.session_dir / "capture.bin"
            if raw_path.is_file():
                self.manifest["bytes_received"] = raw_path.stat().st_size
        except OSError:
            pass
        self.manifest["ended_at"] = analysis.now_iso()
        self.manifest["duration_sec"] = round(ended - started_mono, 3)
        if output_error:
            self.manifest.update(status="error", stop_reason=error_reason, error=str(output_error))
        else:
            self.manifest["stop_reason"] = self._stop_reason
            self.manifest["status"] = "completed" if self._stop_reason == "duration_reached" else "stopped"
        self._write_manifest()
        schema_errors = analysis.validate_schema(
            self.manifest, analysis.SKILL_DIR / "schemas" / "session.schema.json", "session")
        if schema_errors:
            contract_error = "会话契约校验失败：" + "; ".join(schema_errors)
            self.manifest.update(status="error", stop_reason="write_error", error=contract_error)
            output_error = output_error or analysis.S10Error(contract_error)
            self._write_manifest()
        try:
            analysis.update_state_if_present(self.context, self.manifest, self.session_dir)
        except Exception as exc:
            output_error = output_error or exc
        self.result = {
            "session_dir": self.session_dir,
            "manifest": self.manifest,
            "error": str(output_error) if output_error else None,
        }
        self.emit("finished", **self.result)
        return self.result
