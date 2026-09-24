"""state_store：state.json 原子字段更新（多 Skill 并发写安全）。

背景：S5a 与 S5b 可并行执行，两者都写同一个 state.json（各写各的顶层字段）。
无锁的 load → 修改 → save 会整体覆盖，后写者抹掉先写者的字段。

机制（与 ide_sync.py 的 _ProjectFileLock 同模式）：
- 锁文件 <state.json>.lock，O_EXCL 原子创建；等待超时抛错
- 陈旧锁检测：持有者崩溃残留的锁（超过 stale_s）直接清除
- 锁内重新 load 最新 state → 应用更新 → tmp+replace 原子写盘
- state.json 不存在时从 {} 开始（保持各 Skill 原有容错语义）

用法：
    import state_store
    # 顶层字段整体覆盖（最常见：state["s5b"] = payload）
    state_store.update_state(state_path, {"s5b": payload})
    # 或回调就地修改（保留旧字段、部分更新）
    state_store.update_state(state_path, lambda st: st["s5b"].update({...}))
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

LOCK_TIMEOUT_S = 10.0   # 等锁超时（state 写入是毫秒级操作，10s 足够宽裕）
LOCK_STALE_S = 30.0     # 陈旧锁判定：锁文件存活超过该时长视为崩溃残留


class StateLockTimeout(RuntimeError):
    """文件锁等待超时。"""


class _StateFileLock:
    """state.json 专用文件锁（O_EXCL 原子创建 + 陈旧锁清除）。"""

    def __init__(self, state_path: Path):
        self.lock_path = Path(str(state_path) + ".lock")
        self._held = False

    def __enter__(self) -> "_StateFileLock":
        deadline = time.monotonic() + LOCK_TIMEOUT_S
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {time.time():.0f}".encode("ascii"))
                os.close(fd)
                self._held = True
                return self
            except FileExistsError:
                try:
                    if time.time() - self.lock_path.stat().st_mtime > LOCK_STALE_S:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    pass  # 锁刚被释放，立即重试
                if time.monotonic() > deadline:
                    raise StateLockTimeout(f"state 文件锁等待超时（{LOCK_TIMEOUT_S:.0f}s）: {self.lock_path}")
                time.sleep(0.1)

    def __exit__(self, *exc) -> None:
        if self._held:
            try:
                self.lock_path.unlink()
            except OSError:
                pass


def update_state(state_path: Path, updates) -> None:
    """锁内原子更新 state.json。

    updates:
    - dict：顶层字段覆盖（如 {"s5b": {...}}，等价于 state["s5b"] = ...）
    - callable：接收 state dict 就地修改（用于保留旧字段的部分更新）

    锁内重新读取最新内容再修改，避免基于脚本启动时的陈旧快照覆盖
    并行 Skill 期间写入的字段。
    """
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with _StateFileLock(state_path):
        state: dict = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                state = {}
        if callable(updates):
            updates(state)
        elif isinstance(updates, dict):
            state.update(updates)
        tmp = state_path.with_suffix(state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(state_path)
