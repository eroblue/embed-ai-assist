#!/usr/bin/env python
"""ide_sync：IDE 工程同步公共工具（Keil .uvprojx / IAR .ewp）。

把 IDE 工程更新从 S5c 解耦为独立公共工具（任务二·方案 A）：
S5a / S5b / S5c 各自完成代码生成后调用，谁跑完谁同步，互不阻塞。

命令行：
    python skills/_shared/scripts/ide_sync.py --project examples/<project> \
        --target App --ide keil

Python 导入：
    from ide_sync import sync_project
    result = sync_project(project_root="examples/stm32f103zet6", target="App")

行为约定：
- 扫描根 / IDE 工程目录 / include 目标全部来自 PROJECT_LAYOUT.md 解析的
  LayoutPlan（layout_resolver.py，改布局文档即全局生效）：
  扫描根 = plan.scan_roots（如 Drivers/BSP/Src、Drivers/Port/Src、App/Src），
  工程发现目录 = plan.ide_dirs（如 MDK-ARM、IAR、Project），include = plan.include_dirs
- IDE 工程文件由用户手动创建；本工具只把扫描根下的源文件与 include 路径
  增量同步进已有工程（不创建工程）
- 文件锁：锁定工程文件本身（<工程文件>.lock），多 Skill 并发写安全
- 差异比对：增量添加缺失条目、删除已不存在的扫描根条目（只管理扫描根下条目，
  用户手工添加的其他条目不动）；扫描根下的 mocks/（单元测试桩）不加入固件编译，跳过
- 幂等：重复调用不产生重复条目；无变化不写盘（不更新 mtime，避免 IDE 误判重载）
- 备份/回滚：修改前备份 <工程文件>.bak；解析/写入失败从备份恢复，不留半成品
- 失败降级：布局解析失败按内置兜底布局继续；工程文件缺失/为空/解析失败/锁超时等
  任何失败，不中断工作流，输出 <目标工程>/outputs/_shared/ide_sync_manual.md 手动清单

退出码：0=同步成功或无变化；1=已输出手动清单（非致命）；2=参数/环境错误
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+
    print("[ide_sync] 本框架需要 Python 3.10+，"
          "解释器路径见根目录 config.json 的 tool_paths.python", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout_resolver  # noqa: E402

# Keil FileType：1=C 源文件，2=汇编
SOURCE_SUFFIXES = {".c": 1, ".s": 2, ".asm": 2}
# 不同步进固件编译的子目录（单元测试 Mock 桩，避免与真实实现重复符号）
EXCLUDED_SRC_DIRS = {"mocks"}
SUPPORTED_IDES = {"keil": ".uvprojx", "iar": ".ewp"}
LOCK_TIMEOUT_S = 10.0    # 等锁上限（IDE 同步为毫秒级操作，正常无需等待）
LOCK_STALE_S = 120.0     # 陈旧锁判定（超过该时长视为持有者已崩溃）

EXIT_OK = 0
EXIT_MANUAL = 1
EXIT_USAGE = 2


class _ManualError(Exception):
    """需要降级为手动同步清单的失败。"""


class _LockTimeout(Exception):
    """文件锁等待超时。"""


def _log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"[ide_sync] {msg}", file=sys.stderr)


# ---------------------------------------------------------------- 路径工具

def _norm(p: Path | str) -> str:
    """比较用归一化（Windows 大小写不敏感）。"""
    return os.path.normcase(os.path.normpath(str(p)))


def _resolve_ref(ref: str, proj_dir: Path) -> Path:
    """把工程文件内的引用路径（可含 $PROJ_DIR$ 宏、相对路径）解析为绝对路径。"""
    ref = ref.strip()
    for macro in ("$PROJ_DIR$", "$(PROJ_DIR)"):
        if ref.upper().startswith(macro.upper()):
            return (proj_dir / ref[len(macro):].lstrip("\\/")).resolve()
    p = Path(ref)
    return (p if p.is_absolute() else proj_dir / p).resolve()


def _rel_ref(target: Path, base: Path) -> str:
    """target 相对 base 的引用路径（Keil 风格反斜杠）。"""
    return os.path.relpath(target, base)


def _is_under(path: Path, root: Path) -> bool:
    try:
        Path(_norm(path)).relative_to(_norm(root))
        return True
    except ValueError:
        return False


def _is_under_any(path: Path, roots: list[Path]) -> bool:
    return any(_is_under(path, r) for r in roots)


# ---------------------------------------------------------------- 布局扫描

def _scan_layout(target_root: Path, scan_roots: list[tuple[Path, str]],
                 include_dirs: list[tuple[Path, str]]
                 ) -> tuple[list[tuple[Path, str, str]], list[tuple[Path, str]]]:
    """扫描 LayoutPlan 的 Skill 产物目录，返回 (源文件列表, include 目录列表)。

    scan_roots：[(绝对路径, 相对目标工程根的 POSIX 路径)，如
    (…/Drivers/BSP/Src, "Drivers/BSP/Src")]（plan.scan_roots）；
    include_dirs：[(绝对路径, 相对路径)]（plan.include_dirs，已过滤存在性）。

    源文件：[(绝对路径, 相对目标工程根的 POSIX 路径, group 名)]
    group 名 = 扫描根去掉末段（Drivers/BSP/Src → "Drivers/BSP"；App/Src → "App"），
    即 IDE 工程中的分组，完全由布局决定。
    """
    files: list[tuple[Path, str, str]] = []
    seen: set[str] = set()
    for root_abs, root_rel in scan_roots:
        if not root_abs.is_dir():
            continue
        group = root_rel.rsplit("/", 1)[0] if "/" in root_rel else root_rel
        for p in sorted(root_abs.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if any(part in EXCLUDED_SRC_DIRS
                   for part in p.relative_to(root_abs).parts):
                continue  # mocks 等测试桩不进固件编译
            key = _norm(p)
            if key in seen:
                continue
            seen.add(key)
            files.append((p, p.relative_to(target_root).as_posix(), group))
    return files, list(include_dirs)



# ---------------------------------------------------------------- 文件锁

class _ProjectFileLock:
    """锁定 IDE 工程文件本身（<工程文件>.lock），O_EXCL 原子创建。"""

    def __init__(self, project_file: Path, timeout_s: float = LOCK_TIMEOUT_S,
                 stale_s: float = LOCK_STALE_S):
        self.lock_path = Path(str(project_file) + ".lock")
        self.timeout_s = timeout_s
        self.stale_s = stale_s
        self._held = False

    def __enter__(self) -> "_ProjectFileLock":
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {time.time():.0f}".encode("ascii"))
                os.close(fd)
                self._held = True
                return self
            except FileExistsError:
                # 陈旧锁检测：持有者崩溃残留的锁直接清除
                try:
                    if time.time() - self.lock_path.stat().st_mtime > self.stale_s:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    pass  # 锁刚被释放，立即重试
                if time.monotonic() > deadline:
                    raise _LockTimeout(f"文件锁等待超时（{self.timeout_s:.0f}s）: {self.lock_path}")
                time.sleep(0.1)

    def __exit__(self, *exc) -> None:
        if self._held:
            try:
                self.lock_path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- XML 工具

def _child_prefix(parent: ET.Element) -> str:
    """推导 parent 追加子元素时的前导缩进（含换行），失败回退单换行。"""
    if parent.text and "\n" in parent.text:
        return parent.text
    if len(parent):
        tail = list(parent)[-1].tail
        if tail and "\n" in tail:
            return tail
    return "\n"


def _dedent(prefix: str) -> str:
    """缩进串减一级（约 2 空格），用于闭合标签。"""
    base = prefix.rstrip("\n")
    return "\n" + (base[:-2] if len(base) >= 2 else "")


def _append_elem(parent: ET.Element, child: ET.Element) -> ET.Element:
    """按现有兄弟元素的缩进风格追加子元素（保留原文件排版）。"""
    if len(parent):
        prev = list(parent)[-1]
        closing = prev.tail if (prev.tail and "\n" in prev.tail) else "\n"
        prev.tail = _child_prefix(parent)
        child.tail = closing
    else:
        prefix = _child_prefix(parent)
        parent.text = prefix
        child.tail = _dedent(prefix)
    parent.append(child)
    return child


def _serialize(root: ET.Element, eol: str, decl: bytes, had_bom: bool,
               trailing_newline: bool) -> bytes:
    """序列化并按原文件风格归一化（XML 声明/BOM/行尾/末尾换行）。"""
    body = ET.tostring(root, encoding="unicode")
    data = (decl.decode("utf-8", "replace") + "\n" + body).encode("utf-8")
    data = data.replace(b"\r\n", b"\n")
    if eol == "\r\n":
        data = data.replace(b"\n", b"\r\n")
    if trailing_newline:
        data += eol.encode("ascii")
    return (b"\xef\xbb\xbf" + data) if had_bom else data


def _parse_xml(project_file: Path) -> tuple[ET.Element, dict]:
    """解析工程文件，返回 (root, 序列化风格参数)；保留注释节点。"""
    raw = project_file.read_bytes()
    if not raw.strip():
        raise _ManualError("IDE 工程文件内容为空")
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        root = ET.parse(project_file, parser).getroot()
    except ET.ParseError as exc:
        raise _ManualError(f"XML 解析失败: {exc}") from exc
    style = {
        "eol": "\r\n" if raw.count(b"\r\n") * 2 > raw.count(b"\n") else "\n",
        "decl": raw.split(b"\n", 1)[0].strip()
        if raw.lstrip().startswith(b"<?xml") else b'<?xml version="1.0" encoding="UTF-8"?>',
        "had_bom": raw.startswith(b"\xef\xbb\xbf"),
        "trailing_newline": raw.endswith(b"\n"),
    }
    return root, style


# ---------------------------------------------------------------- Keil .uvprojx

def _new_keil_group(groups_el: ET.Element, name: str) -> ET.Element:
    """创建 <Group>（缩进风格借用已有 Group 模板）。"""
    g = ET.Element("Group")
    _append_elem(groups_el, g)
    name_tail, files_text, files_tail = "\n          ", "\n            ", "\n          "
    tmpl = groups_el.find("Group")
    if tmpl is not None:
        tn = tmpl.find("GroupName")
        tf = tmpl.find("Files")
        if tn is not None and tn.tail and "\n" in tn.tail:
            name_tail = tn.tail
        if tf is not None and tf.text and "\n" in tf.text:
            files_text = tf.text
        if tf is not None and tf.tail and "\n" in tf.tail:
            files_tail = tf.tail
    ne = ET.SubElement(g, "GroupName")
    ne.text = name
    ne.tail = name_tail
    fe = ET.SubElement(g, "Files")
    fe.text = files_text
    fe.tail = files_tail
    return g


def _append_keil_file(files_el: ET.Element, fname: str, ftype: int, ref: str) -> None:
    """追加 <File>（FileName/FileType/FilePath，缩进随现有条目）。"""
    f_el = ET.Element("File")
    prefix = _child_prefix(files_el)
    for tag, text in (("FileName", fname), ("FileType", str(ftype)), ("FilePath", ref)):
        sub = ET.SubElement(f_el, tag)
        sub.text = text
        sub.tail = prefix
    f_el[-1].tail = _dedent(prefix)
    _append_elem(files_el, f_el)


def _ensure_chain(parent: ET.Element, names: tuple[str, ...]) -> ET.Element:
    """逐级查找/创建子元素链（IncludePath 兜底用）。"""
    cur = parent
    for name in names:
        nxt = cur.find(name)
        if nxt is None:
            nxt = _append_elem(cur, ET.Element(name))
        cur = nxt
    return cur


def _apply_keil(root: ET.Element, proj_dir: Path, scan, scan_roots: list[Path]) -> dict:
    targets = root.findall("./Targets/Target")
    if not targets:
        raise _ManualError("未找到 <Targets>/<Target>（非标准 Keil .uvprojx 结构）")
    added: list[str] = []
    removed: list[str] = []
    inc_added: set[str] = set()
    src_files, include_dirs = scan

    for target in targets:
        groups_el = target.find("./Groups")
        if groups_el is None:
            groups_el = _append_elem(target, ET.Element("Groups"))
        # 1) 索引 group + 清理失效条目（仅管理扫描根下条目）
        group_by_name: dict[str, ET.Element] = {}
        existing: set[str] = set()
        for g in groups_el.findall("Group"):
            ne = g.find("GroupName")
            gname = (ne.text or "").strip() if ne is not None else ""
            if gname and gname not in group_by_name:
                group_by_name[gname] = g
            files_el = g.find("Files")
            if files_el is None:
                continue
            for f_el in list(files_el.findall("File")):
                pe = f_el.find("FilePath")
                if pe is None or not (pe.text or "").strip():
                    continue
                ref = pe.text.strip()
                resolved = _resolve_ref(ref, proj_dir)
                if _is_under_any(resolved, scan_roots) and not resolved.exists():
                    files_el.remove(f_el)
                    if ref not in removed:
                        removed.append(ref)
                    continue
                existing.add(_norm(resolved))
        # 2) 添加缺失源文件（复用同名 Group，幂等）
        for abs_path, rel_target, group in src_files:
            if _norm(abs_path) in existing:
                continue
            g = group_by_name.get(group)
            if g is None:
                g = _new_keil_group(groups_el, group)
                group_by_name[group] = g
            files_el = g.find("Files")
            if files_el is None:
                files_el = _append_elem(g, ET.Element("Files"))
                files_el.text = _child_prefix(g)
            _append_keil_file(files_el, abs_path.name,
                              SOURCE_SUFFIXES.get(abs_path.suffix.lower(), 1),
                              _rel_ref(abs_path, proj_dir))
            existing.add(_norm(abs_path))
            if rel_target not in added:
                added.append(rel_target)
        # 3) include 路径（<IncludePath> 分号分隔，仅追加缺失项）
        inc_el = target.find(
            "./TargetOption/TargetArmAds/Cads/VariousControls/IncludePath")
        if inc_el is None:
            inc_el = _ensure_chain(
                target, ("TargetOption", "TargetArmAds", "Cads",
                         "VariousControls", "IncludePath"))
        parts = [p.strip() for p in (inc_el.text or "").split(";") if p.strip()]
        have = {_norm(_resolve_ref(p, proj_dir)) for p in parts}
        miss = [d for d in include_dirs if _norm(d[0]) not in have]
        if miss:
            parts.extend(_rel_ref(d[0], proj_dir) for d in miss)
            inc_el.text = ";".join(parts)
            inc_added.update(d[1] for d in miss)
    return {"added": added, "removed": removed, "include_added": sorted(inc_added)}


# ---------------------------------------------------------------- IAR .ewp

def _find_iar_option(cfg: ET.Element, name: str) -> ET.Element | None:
    for opt in cfg.iter("option"):
        ne = opt.find("name")
        if ne is not None and (ne.text or "").strip() == name:
            return opt
    return None


def _new_iar_group(root: ET.Element, name: str) -> ET.Element:
    g = ET.Element("group")
    _append_elem(root, g)
    name_tail, files_text, files_tail = "\n      ", "\n        ", "\n    "
    tmpl = root.find("group")
    if tmpl is not None:
        tn = tmpl.find("name")
        tf = tmpl.find("files")
        if tn is not None and tn.tail and "\n" in tn.tail:
            name_tail = tn.tail
        if tf is not None and tf.text and "\n" in tf.text:
            files_text = tf.text
        if tf is not None and tf.tail and "\n" in tf.tail:
            files_tail = tf.tail
    ne = ET.SubElement(g, "name")
    ne.text = name
    ne.tail = name_tail
    fe = ET.SubElement(g, "files")
    fe.text = files_text
    fe.tail = files_tail
    return g


def _apply_iar(root: ET.Element, proj_dir: Path, scan, scan_roots: list[Path]) -> dict:
    added: list[str] = []
    removed: list[str] = []
    inc_added: set[str] = set()
    src_files, include_dirs = scan

    # 1) 索引 group + 清理失效条目
    group_by_name: dict[str, ET.Element] = {}
    existing: set[str] = set()
    for g in root.findall("group"):
        ne = g.find("name")
        gname = (ne.text or "").strip() if ne is not None else ""
        if gname and gname not in group_by_name:
            group_by_name[gname] = g
        files_el = g.find("files")
        if files_el is None:
            continue
        for f_el in list(files_el.findall("file")):
            ne = f_el.find("name")
            if ne is None or not (ne.text or "").strip():
                continue
            ref = ne.text.strip()
            resolved = _resolve_ref(ref, proj_dir)
            if _is_under_any(resolved, scan_roots) and not resolved.exists():
                files_el.remove(f_el)
                if ref not in removed:
                    removed.append(ref)
                continue
            existing.add(_norm(resolved))
    # 2) 添加缺失源文件（IAR 路径带 $PROJ_DIR$ 前缀）
    for abs_path, rel_target, group in src_files:
        if _norm(abs_path) in existing:
            continue
        g = group_by_name.get(group)
        if g is None:
            g = _new_iar_group(root, group)
            group_by_name[group] = g
        files_el = g.find("files")
        if files_el is None:
            files_el = _append_elem(g, ET.Element("files"))
            files_el.text = _child_prefix(g)
        f_el = ET.Element("file")
        prefix = _child_prefix(files_el)
        ne = ET.SubElement(f_el, "name")
        ne.text = "$PROJ_DIR$\\" + _rel_ref(abs_path, proj_dir)
        ne.tail = _dedent(prefix)
        _append_elem(files_el, f_el)
        existing.add(_norm(abs_path))
        if rel_target not in added:
            added.append(rel_target)
    # 3) include 路径（CCIncludePath2 的 <state>，逐条追加）
    for cfg in root.findall("configuration"):
        opt = _find_iar_option(cfg, "CCIncludePath2")
        if opt is None:
            continue
        have = {_norm(_resolve_ref(st.text.strip(), proj_dir))
                for st in opt.findall("state") if (st.text or "").strip()}
        for d in include_dirs:
            if _norm(d[0]) in have:
                continue
            st = ET.Element("state")
            st.text = "$PROJ_DIR$\\" + _rel_ref(d[0], proj_dir)
            _append_elem(opt, st)
            inc_added.add(d[1])
    return {"added": added, "removed": removed, "include_added": sorted(inc_added)}


# ---------------------------------------------------------------- 单工程文件同步

def _sync_one(project_file: Path, scan, scan_roots: list[Path], dry_run: bool) -> dict:
    """同步单个工程文件（调用方负责持锁）。"""
    root, style = _parse_xml(project_file)
    before = _serialize(root, **style)
    suffix = project_file.suffix.lower()
    if suffix == ".uvprojx":
        stats = _apply_keil(root, project_file.parent, scan, scan_roots)
    elif suffix == ".ewp":
        stats = _apply_iar(root, project_file.parent, scan, scan_roots)
    else:
        raise _ManualError(f"不支持的工程文件格式: {project_file.name}")
    after = _serialize(root, **style)
    if after == before:
        return {"status": "no_change", **stats}
    if dry_run:
        return {"status": "dry_run", **stats}
    # 修改前备份 .bak；写入失败从备份恢复
    bak = Path(str(project_file) + ".bak")
    shutil.copy2(project_file, bak)
    try:
        project_file.write_bytes(after)
    except OSError as exc:
        shutil.copy2(bak, project_file)
        raise _ManualError(f"写入失败，已从备份回滚: {exc}") from exc
    return {"status": "synced", **stats}


# ---------------------------------------------------------------- 手动同步清单

def _write_manual_md(target_root: Path, reason: str, scan,
                     ide_dirs: list[str]) -> Path:
    """输出 <目标工程>/outputs/_shared/ide_sync_manual.md，返回其路径。"""
    out_dir = target_root / "outputs" / "_shared"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ide_sync_manual.md"
    src_files, include_dirs = scan
    ide_hint = "、".join(f"`{d}/`" for d in ide_dirs) or "布局 IDE 目录（见 PROJECT_LAYOUT.md）"
    lines = [
        "# IDE 手动同步清单", "",
        f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 目标工程：{target_root.name}",
        f"- 失败原因：{reason}", "",
        "> 自动同步未完成，请按以下清单手动处理（完成后可重新运行 "
        "`ide_sync.py` 验证）。", "",
    ]
    if src_files:
        lines += ["## 需要添加到 IDE 工程的源文件（按 group 分组）", ""]
        by_group: dict[str, list[str]] = {}
        for _, rel_target, group in src_files:
            by_group.setdefault(group, []).append(rel_target)
        for g in sorted(by_group):
            lines.append(f"### group：{g}")
            lines.extend(f"- `{rel}`" for rel in sorted(by_group[g]))
            lines.append("")
    else:
        lines += ["## 需要添加到 IDE 工程的源文件", "",
                  "-（Skill 产物目录下暂无源文件）", ""]
    if include_dirs:
        lines += ["## 需要添加的 include 路径", ""]
        lines.extend(f"- `{rel}`" for _, rel in include_dirs)
        lines.append("")
    lines += [
        "## 操作指引", "",
        "- **通用（任何 IDE，含 8 位机 IDE）**：在 IDE 中打开/新建工程后，"
        "将上述源文件全部加入工程的编译列表（通常在 Project/Add Files 或"
        "工程树右键菜单），并将上述 include 路径加入编译器的头文件搜索路径"
        "（编译选项中的 Include Directories / 头文件搜索路径）。",
        "- **Keil**：Project 窗口右键 Target → Add Group → 按上述 group 命名 → "
        "右键该 Group → Add Existing Files to Group → 选择对应源文件；"
        "include 路径在 Options for Target → C/C++ → Include Paths 中追加（分号分隔）。",
        "- **IAR**：Workspace 右键 Project → Add → Add Group… → 右键 Group → "
        "Add → Add Files…；include 路径在 Project → Options → C/C++ Compiler → "
        "Preprocessor → Additional include directories 中追加。",
        "- **工程文件不存在时**：请先在 IDE 中手动创建工程（选芯片、编译器等配置"
        "由人工确认更可靠），保存到 `<项目根>/<目标工程>/` 下的 IDE 工程目录"
        f"（{ide_hint}，目录结构见 docs/PROJECT_LAYOUT.md），"
        "再重新运行 `python skills/_shared/scripts/ide_sync.py --project <项目根> "
        "--target <App|BootLoader> --ide <keil|iar>` 即可自动同步"
        "（仅 Keil/IAR 支持自动同步，其他 IDE 按本清单手动处理）。", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------- 主入口

def _discover_project_files(target_root: Path, ide: str | None,
                            configured: str | None,
                            ide_dirs: list[str]) -> list[Path]:
    """发现待同步的工程文件（--project-file / config 显式路径 > 布局 IDE 目录扫描）。"""
    if configured:
        p = Path(configured)
        if not p.is_absolute():
            p = target_root.parent / p
        return [p] if p.is_file() else []
    found: list[Path] = []
    for d in ide_dirs:
        base = target_root / d
        if not base.is_dir():
            continue
        for key, ext in SUPPORTED_IDES.items():
            if ide in (None, key):
                found.extend(base.rglob(f"*{ext}"))
    return sorted({f.resolve() for f in found if f.is_file()})


def _resolve_plan(project_root: Path, cfg: dict) -> dict:
    """解析 LayoutPlan；解析失败按内置兜底布局降级（公共工具失败不中断）。"""
    try:
        return layout_resolver.resolve_layout(project_root, cfg)
    except layout_resolver.LayoutError as exc:
        _log(f"布局解析失败（{exc}），按内置兜底布局处理")
        arch = ((cfg.get("project") or {}).get("architecture") or "layered")
        return layout_resolver.plan_from_builtin(arch)


def sync_project(project_root: str | Path, target: str | None = None,
                 ide: str | None = None, project_file: str | None = None,
                 dry_run: bool = False, quiet: bool = False) -> dict:
    """同步布局 Skill 产物目录到 IDE 工程。返回结果摘要（不抛同步异常）。"""
    project_root = Path(project_root).expanduser().resolve()
    if not project_root.is_dir():
        raise ValueError(f"项目根目录不存在: {project_root}")

    # config 一次加载：build_target / 显式工程文件路径
    try:
        cfg = json.loads((project_root / "config.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    if target is None:
        target = (cfg.get("project") or {}).get("build_target")
    target = target or "App"
    if target not in ("App", "BootLoader"):
        raise ValueError(f"非法 target: {target}（合法值 App / BootLoader）")
    # config 显式工程文件路径（project.inputs.ide_project，相对项目根）
    configured_pf = project_file if project_file else \
        (cfg.get("project", {}).get("inputs") or {}).get("ide_project") or None

    # LayoutPlan：扫描根 / IDE 目录 / include 目标（改布局文档即全局生效）
    plan = _resolve_plan(project_root, cfg)
    target_root = project_root / target
    scan_roots_abs = [(target_root / d, d) for d in plan["scan_roots"]]
    include_dirs = [(target_root / d, d) for d in plan["include_dirs"]
                    if (target_root / d).is_dir()]
    scan = _scan_layout(target_root, scan_roots_abs, include_dirs)
    scan_roots = [p for p, _ in scan_roots_abs]

    project_files = _discover_project_files(target_root, ide, configured_pf,
                                            plan["ide_dirs"])
    if not project_files:
        # 更精确的失败原因：是否只是格式不受支持
        unsupported: set[str] = set()
        for d in plan["ide_dirs"]:
            base = target_root / d
            if base.is_dir():
                unsupported.update(
                    p.suffix for p in base.rglob("*") if p.is_file() and
                    p.suffix.lower() in {".project", ".cproject", ".uvproj",
                                         ".eww", ".ewd"})
        ide_hint = "、".join(plan["ide_dirs"]) or "（见 PROJECT_LAYOUT.md）"
        reason = (f"未发现 IDE 工程文件（布局 IDE 目录 {ide_hint} 下无 "
                  ".uvprojx / .ewp）；IDE 工程由用户手动创建，"
                  "请先创建工程后重新运行本工具"
                  + (f"。发现暂不支持的格式: {', '.join(sorted(unsupported))}"
                     if unsupported else ""))
        manual_path = _write_manual_md(target_root, reason, scan, plan["ide_dirs"])
        _log(reason, quiet)
        _log(f"已输出手动同步清单: {manual_path}", quiet)
        return {"status": "manual", "reason": reason, "target": target,
                "project_files": [], "added_count": 0, "removed_count": 0,
                "include_added_count": 0, "manual_path": str(manual_path)}

    results: list[dict] = []
    for pf in project_files:
        try:
            with _ProjectFileLock(pf):
                r = _sync_one(pf, scan, scan_roots, dry_run)
        except (_ManualError, _LockTimeout) as exc:
            r = {"status": "manual", "reason": str(exc),
                 "added": [], "removed": [], "include_added": []}
        r["project_file"] = str(pf)
        _log(f"{pf.name}: {r['status']}"
             + (f"（{r['reason']}）" if r.get("reason") else
                f"（+{len(r['added'])} 文件, -{len(r['removed'])} 条目, "
                f"+{len(r['include_added'])} include）" if r["status"] != "no_change" else ""),
             quiet)
        results.append(r)

    manuals = [r for r in results if r["status"] == "manual"]
    manual_path = None
    if manuals:
        reason = "; ".join(f"{Path(r['project_file']).name}: {r['reason']}" for r in manuals)
        manual_path = _write_manual_md(target_root, reason, scan, plan["ide_dirs"])
        _log(f"已输出手动同步清单: {manual_path}", quiet)
    synced_any = any(r["status"] in ("synced", "dry_run") for r in results)
    if manuals:
        status = "partial" if synced_any else "manual"
    else:
        status = "synced" if synced_any else "no_change"

    return {
        "status": status,
        "target": target,
        "project_files": [r["project_file"] for r in results],
        "added_count": sum(len(r["added"]) for r in results),
        "removed_count": sum(len(r["removed"]) for r in results),
        "include_added_count": sum(len(set(r["include_added"])) for r in results),
        "manual_path": str(manual_path) if manual_path else None,
        "reason": "; ".join(r["reason"] for r in manuals) or None,
        "results": [{k: v for k, v in r.items() if k != "reason"} | 
                    {"reason": r.get("reason")} for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ide_sync：IDE 工程同步公共工具（S5a/S5b/S5c 完成后调用，"
                    "按 PROJECT_LAYOUT.md 解析的扫描根增量同步源文件与 include "
                    "路径到 Keil/IAR 工程）")
    parser.add_argument("--project", required=True,
                        help="项目根目录（含 config.json，如 examples/stm32f103zet6）")
    parser.add_argument("--target", choices=["App", "BootLoader"], default=None,
                        help="目标工程；缺省读 config.json 的 project.build_target（默认 App）")
    parser.add_argument("--ide", choices=["keil", "iar"], default=None,
                        help="IDE 类型；缺省自动发现布局 IDE 目录（MDK-ARM/IAR/Project 等）"
                             "下全部受支持工程")
    parser.add_argument("--project-file", default=None,
                        help="显式指定工程文件路径（覆盖自动发现，相对项目根或绝对路径）")
    parser.add_argument("--dry-run", action="store_true", help="只报告变更，不写盘")
    parser.add_argument("--quiet", action="store_true", help="抑制日志输出")
    args = parser.parse_args(argv)

    try:
        result = sync_project(args.project, args.target, args.ide,
                              args.project_file, args.dry_run, args.quiet)
    except (ValueError, OSError) as exc:
        print(f"[ide_sync] 参数/环境错误: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK if result["status"] in ("synced", "no_change", "dry_run") else EXIT_MANUAL


if __name__ == "__main__":
    sys.exit(main())
