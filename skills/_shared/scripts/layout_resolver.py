#!/usr/bin/env python
"""layout_resolver：解析 PROJECT_LAYOUT.md → LayoutPlan（项目布局唯一事实来源）。

设计原则（用户契约）：代码生成路径不硬编码到脚本——S5a/S5b/S5c 的产物目录、
ide_sync 的扫描根与 IDE 工程目录、include 追加目标，全部按 PROJECT_LAYOUT.md
解析得到；用户改布局文件即全局生效，不改脚本。

读取优先级（PROJECT_LAYOUT.md 2.1）：
  1. <项目根>/docs/PROJECT_LAYOUT.md（项目级，最高优先级）
  2. <框架根>/docs/PROJECT_LAYOUT.md（框架级）
  3. 内置兜底树（框架文件也缺失时使用，附警告）

解析产物 LayoutPlan（路径全部相对 <项目根>/<build_target>/，POSIX 分隔）：
  - skeleton_dirs    目录骨架（含用户目录；ensure_layout 幂等创建）
  - skill_dirs       Skill 产物目录 {s5a|s5b|s5c: {src: [...], inc: [...]}}
  - ide_dirs         IDE 工程目录（ide_sync 工程发现范围）
  - scan_roots       ide_sync 扫描根（全部 Skill src 并集）
  - include_dirs     include 追加目标（全部 Skill inc 并集）

arch_family 判定（PROJECT_LAYOUT.md 2.3 四级）：
  config.project.arch_family > state.chip.arch_family（S3）
  > project.target 前缀映射表（从文档 2.3 表格解析）> 兜底 cortex_m

树解析约定（机器契约，PROJECT_LAYOUT.md 第七节）：
  - 节点名带 "/" 后缀 = 目录；无 = 文件（文件不建骨架，注释仍参与归属推导）
  - 目录名含 <占位符> 或为 xxx → 该节点子树跳过（不建骨架、不参与归属）
  - 注释含 S5a/S5b/S5c → Skill 归属；含 "工程目录" → IDE 工程目录
    （注释中 "也可用 XX/、YY/" 的备选目录名一并收入 ide_dirs）
  - Skill 产物目录必须以 Src/ 或 Inc/ 结尾（目录级注释向子树的 Src/Inc 叶传播，
    文件级注释归属最近的 Src/Inc 祖先目录）
  - architecture = flat → 剔除 Port 层目录与 s5c 归属（2.3 组合规则：flat 无
    Port，S5c 跳过）

命令行（调试/联调用）：
    python skills/_shared/scripts/layout_resolver.py --project examples/<proj>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+
    print("[layout_resolver] 本框架需要 Python 3.10+，"
          "解释器路径见根目录 config.json 的 tool_paths.python", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
FRAMEWORK_DIR = SCRIPT_DIR.parents[2]  # skills/_shared/scripts → embed-ai-assist
LAYOUT_FILENAME = "PROJECT_LAYOUT.md"

ARCH_FAMILIES = ("cortex_m", "mcu8")
VALID_ARCHITECTURES = ("flat", "layered", "full")

# 兜底树（框架级 PROJECT_LAYOUT.md 也缺失时使用；与文档主树同构的极简版）
_BUILTIN_CORTEX_M = """App/
├── Core/
│   ├── Inc/
│   └── Src/
├── Drivers/
│   ├── CMSIS/
│   ├── HAL_Driver/
│   │   ├── Inc/
│   │   └── Src/
│   ├── BSP/                   # S5a 初始化 + S5b 器件驱动
│   │   ├── Inc/
│   │   └── Src/
│   └── Port/
│       ├── Inc/               # S5b：Port 接口
│       └── Src/               # S5c：Port 实现
├── Middlewares/
│   └── Third_Party/
├── App/                       # S5b：应用逻辑
│   ├── Inc/
│   └── Src/
└── MDK-ARM/                   # Keil 工程目录（用户创建，也可用 IAR/、GCC/）
"""

_BUILTIN_MCU8 = """App/
├── App/                       # S5b：应用逻辑 + 协议层
│   ├── Inc/
│   └── Src/
├── Drivers/
│   ├── BSP/                   # S5a 初始化 + S5b 器件驱动
│   │   ├── Inc/
│   │   └── Src/
│   └── Port/                  # Port 抽象
│       ├── Inc/               # S5b：Port 接口
│       └── Src/               # S5c：Port 实现
└── Project/                   # IDE 工程目录（用户创建）
"""

# 兜底前缀映射（框架文件缺失时使用；与文档 2.3 映射表同构）
_BUILTIN_PREFIXES = {
    "STM32": "cortex_m", "GD32": "cortex_m", "AT32": "cortex_m", "APM32": "cortex_m",
    "HC32": "cortex_m", "N32": "cortex_m", "LPC": "cortex_m", "MK": "cortex_m",
    "MKL": "cortex_m",
    "STC8": "mcu8", "STC15": "mcu8", "STC89": "mcu8", "FMD": "mcu8",
    "FT61": "mcu8", "FT62": "mcu8", "HOLTEK": "mcu8", "HT": "mcu8",
    "CMS": "mcu8", "SC8": "mcu8",
}

_SKILL_RE = re.compile(r"\bS5([abc])\b")
_BUILTIN_TREES = {"cortex_m": _BUILTIN_CORTEX_M, "mcu8": _BUILTIN_MCU8}


class LayoutError(RuntimeError):
    """布局解析失败（含可读原因；调用方决定报错或降级）。"""


def _log(msg: str) -> None:
    print(f"[layout] {msg}", file=sys.stderr)


# ---------------------------------------------------------------- 布局文件定位

def _find_layout_file(project_root: Path) -> tuple[Path | None, str]:
    """按 2.1 优先级定位布局文件，返回 (路径|None, 来源)。"""
    p = project_root / "docs" / LAYOUT_FILENAME
    if p.is_file():
        return p, "project"
    f = FRAMEWORK_DIR / "docs" / LAYOUT_FILENAME
    if f.is_file():
        return f, "framework"
    return None, "builtin"


# ---------------------------------------------------------------- 目录树解析

def _parse_tree_line(line: str) -> tuple[int, str] | None:
    """解析一行目录树，返回 (深度, 节点文本)；非树行（根行/说明）返回 None。

    树渲染按 4 字符一组：`│   ` / `    ` / `├── ` / `└── `。
    深度 = 前缀组数 + 1（连接符组）；根行无树字符 → None。
    """
    i, depth = 0, 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch in ("│", " "):
            depth += 1
            i += 4
        elif ch in ("├", "└"):
            depth += 1
            return depth, line[i + 4:]
        else:
            return None
    return None


def _extract_skills(comment: str) -> set[str]:
    return {f"s5{m}" for m in _SKILL_RE.findall(comment or "")}


def _parent_of(rel: str) -> str:
    return rel.rsplit("/", 1)[0] if "/" in rel else ""


def _parse_tree(block: str) -> dict:
    """解析单个目录树代码块。

    返回 {skeleton, incsrc, ide_dirs, warnings}：
      skeleton  目录相对路径列表（含用户目录与 IDE 目录）
      incsrc    {Src/Inc 结尾目录: Skill 集合}（Skill 产物归属）
      ide_dirs  IDE 工程目录（含注释中的备选目录名）
    """
    warnings: list[str] = []
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines or not lines[0].strip().endswith("/"):
        raise LayoutError(
            f"目录树首行应为根目录（以 / 结尾），实际: {lines[:1]!r}")

    skeleton: list[str] = []
    dir_comment: dict[str, str] = {}          # rel → 注释（目录）
    file_owners: list[tuple[str, str]] = []   # (父目录 rel, 文件注释)
    stack: dict[int, str] = {}                # 深度 → 父路径
    skip_depth: int | None = None             # 占位符子树跳过深度

    for line in lines[1:]:
        parsed = _parse_tree_line(line)
        if parsed is None:
            continue
        depth, text = parsed
        if skip_depth is not None and depth > skip_depth:
            continue
        skip_depth = None
        name_part, _, comment = text.partition(" #")
        name = name_part.strip()
        comment = comment.strip()
        if not name:
            continue
        is_dir = name.endswith("/")
        clean = name.rstrip("/")
        if not clean:
            continue
        parent = stack.get(depth - 1, "") if depth > 1 else ""
        rel = f"{parent}/{clean}" if parent else clean
        if is_dir:
            if "<" in clean or ">" in clean or clean == "xxx":
                skip_depth = depth  # 占位符目录：子树跳过（骨架/归属均不管）
                continue
            stack[depth] = rel
            for d in [d for d in stack if d > depth]:
                del stack[d]
            skeleton.append(rel)
            dir_comment[rel] = comment
        else:
            # 文件：不建骨架；带 Skill 注释时参与归属（归属到最近 Src/Inc 祖先）
            file_owners.append((parent, comment))

    # 1) 目录注释的 Skill 标记
    dir_skills = {rel: _extract_skills(c) for rel, c in dir_comment.items()}
    dir_skills = {rel: sk for rel, sk in dir_skills.items() if sk}

    # 2) Src/Inc 结尾目录 = Skill 产物目录（继承祖先链标记）
    incsrc: dict[str, set[str]] = {}
    for rel in skeleton:
        leaf = rel.rsplit("/", 1)[-1].lower()
        if leaf in ("src", "inc", "include"):
            skills = set(dir_skills.get(rel, ()))
            p = _parent_of(rel)
            while p:
                skills |= dir_skills.get(p, set())
                p = _parent_of(p)
            incsrc[rel] = skills

    # 3) 文件注释归属最近的 Src/Inc 祖先目录
    for parent, comment in file_owners:
        skills = _extract_skills(comment)
        if not skills:
            continue
        p = parent
        while p and p not in incsrc:
            p = _parent_of(p)
        if p:
            incsrc[p] |= skills
        else:
            warnings.append(f"带 Skill 注释的文件位于无 Src/Inc 祖先的目录（{parent}/），归属被忽略")

    # 4) IDE 工程目录（注释含 "工程目录"；备选目录名如 IAR/、GCC/ 一并收入）
    ide_dirs: list[str] = []
    for rel, comment in dir_comment.items():
        if "工程目录" not in comment:
            continue
        if rel not in ide_dirs:
            ide_dirs.append(rel)
        for alt in re.findall(r"([A-Za-z][A-Za-z0-9_-]*)/", comment):
            if alt not in ide_dirs and alt != rel.rsplit("/", 1)[-1]:
                ide_dirs.append(alt)

    return {"skeleton": skeleton, "incsrc": incsrc,
            "ide_dirs": ide_dirs, "warnings": warnings}


def _apply_flat(parsed: dict) -> None:
    """flat 组合规则（文档 2.3/4.4）：剔除 Port 层，S5c 跳过。"""

    def _is_port(rel: str) -> bool:
        return "Port" in rel.split("/")

    parsed["skeleton"] = [d for d in parsed["skeleton"] if not _is_port(d)]
    parsed["incsrc"] = {rel: sk - {"s5c"} for rel, sk in parsed["incsrc"].items()
                        if not _is_port(rel)}


# ---------------------------------------------------------------- 章节与表格

def _split_sections(md: str) -> list[tuple[str, str]]:
    """按二级标题分节，返回 [(标题行, 节内容)]。"""
    parts = re.split(r"^## ", md, flags=re.M)
    out = []
    for p in parts[1:]:
        title = p.splitlines()[0] if p.splitlines() else ""
        out.append((title, p))
    return out


def _code_blocks(section: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)```", section, flags=re.S)


def _select_tree_block(md: str, arch_family: str, architecture: str) -> str:
    """按 arch_family 选目录树代码块。

    章节定位不依赖编号：32 位 = 二级标题含 "32 位"/"Cortex"；8 位 = 含 "8 位"。
    8 位 flat：优先取 "flat 模式" 段之后的树；找不到则主树 + 剔除 Port。
    """
    if arch_family == "mcu8":
        secs = [s for t, s in _split_sections(md) if "8" in t and "位" in t]
    else:
        secs = [s for t, s in _split_sections(md)
                if ("32" in t and "位" in t) or "Cortex" in t]
    if not secs:
        kind = "8 位" if arch_family == "mcu8" else "32 位"
        raise LayoutError(
            f"PROJECT_LAYOUT.md 未找到 {kind}布局章节（二级标题需含 '{kind}'）")
    sec = secs[0]
    blocks = _code_blocks(sec)
    if not blocks:
        raise LayoutError("布局章节中未找到目录树代码块（```text 围栏）")
    if arch_family == "mcu8" and architecture == "flat":
        m = re.search(r"flat\s*模式", sec)
        if m:
            tail = _code_blocks(sec[m.start():])
            if tail:
                return tail[0]
    return blocks[0]


def _parse_prefix_map(md: str) -> dict[str, str]:
    """从文档映射表解析 型号前缀 → arch_family（行式表格，第二列为 cortex_m/mcu8）。"""
    table: dict[str, str] = {}
    for line in md.splitlines():
        m = re.match(r"^\|\s*(.+?)\s*\|\s*`?(cortex_m|mcu8)`?\s*\|", line)
        if not m:
            continue
        arch = m.group(2)
        for tok in re.findall(r"`([^`]+)`", m.group(1)):
            tok = tok.strip()
            if tok:
                table[tok] = arch
    return table


# ---------------------------------------------------------------- arch_family 判定

def _resolve_arch_family(config: dict, state: dict | None,
                         prefix_map: dict[str, str]) -> tuple[str, str]:
    """四级判定（文档 2.3）：config 显式 > S3 chip_data > target 前缀 > 兜底。"""
    proj = config.get("project") or {}
    val = str(proj.get("arch_family") or "").strip()
    if val in ARCH_FAMILIES:
        return val, "config"
    chip = ((state or {}).get("chip") or {})
    val = str(chip.get("arch_family") or "").strip()
    if val in ARCH_FAMILIES:
        return val, "chip_data"
    target = str(config.get("platform") or proj.get("target") or "").strip()
    if target:
        for prefix in sorted(prefix_map, key=len, reverse=True):
            if target.upper().startswith(prefix.upper()):
                return prefix_map[prefix], "target_prefix"
    return "cortex_m", "fallback"


# ---------------------------------------------------------------- 主入口

def resolve_layout(project_root: str | Path, config: dict | None = None,
                   state: dict | None = None, arch_override: str | None = None,
                   arch_family_override: str | None = None) -> dict:
    """解析布局计划（LayoutPlan）。project_root = 项目根（找项目级 docs/ 覆盖）。

    config 为已加载的项目 config.json（dict，可空）；state 为目标工程 state.json
    （可选，用于 S3 chip_data.arch_family 判定）。解析失败抛 LayoutError。
    """
    project_root = Path(project_root).expanduser().resolve()
    config = config or {}
    warnings: list[str] = []

    layout_path, source = _find_layout_file(project_root)
    md = None
    if layout_path is not None:
        try:
            md = layout_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            warnings.append(f"布局文件读取失败（{layout_path}）: {exc}，改用内置兜底")
            layout_path, source, md = None, "builtin", None
    if md is None:
        source = "builtin"
        warnings.append("未找到 PROJECT_LAYOUT.md（项目级/框架级），使用内置兜底布局；"
                        "请恢复 embed-ai-assist/docs/PROJECT_LAYOUT.md")

    # arch_family（四级判定）
    if arch_family_override in ARCH_FAMILIES:
        arch_family, af_source = arch_family_override, "override"
    else:
        prefix_map = _parse_prefix_map(md) if md else dict(_BUILTIN_PREFIXES)
        arch_family, af_source = _resolve_arch_family(config, state, prefix_map)

    # architecture（config 未指定时按 layered 全建，建多无害）
    architecture = str(arch_override
                       or (config.get("project") or {}).get("architecture")
                       or "layered").strip()
    if architecture not in VALID_ARCHITECTURES:
        raise LayoutError(f"非法 architecture: {architecture}"
                          f"（合法值 {'/'.join(VALID_ARCHITECTURES)}）")

    # 选树
    if md is not None:
        block = _select_tree_block(md, arch_family, architecture)
        if arch_family == "mcu8" and architecture == "flat" and "Port" in block:
            warnings.append("8 位 flat 未找到独立 flat 树，按主树剔除 Port 层")
    else:
        block = _BUILTIN_TREES[arch_family]

    parsed = _parse_tree(block)
    if architecture == "flat":
        _apply_flat(parsed)
    warnings.extend(parsed.pop("warnings"))

    # skill_dirs 汇总（Skill → {src: [...], inc: [...]}）
    skill_dirs = {k: {"src": [], "inc": []} for k in ("s5a", "s5b", "s5c")}
    for rel in sorted(parsed["incsrc"]):
        leaf = rel.rsplit("/", 1)[-1].lower()
        kind = "src" if leaf == "src" else "inc"
        for skill in sorted(parsed["incsrc"][rel]):
            skill_dirs[skill][kind].append(rel)

    scan_roots = sorted({d for k in skill_dirs for d in skill_dirs[k]["src"]})
    include_dirs = sorted({d for k in skill_dirs for d in skill_dirs[k]["inc"]})

    if not skill_dirs["s5a"]["src"] or not skill_dirs["s5a"]["inc"]:
        warnings.append("S5a 产物目录未解析到（目录树需有带 S5a 注释的 Src/Inc 目录），"
                        "S5a 代码生成将无法定位输出路径")
    if not parsed["ide_dirs"]:
        warnings.append("未解析到 IDE 工程目录（目录树注释需含 '工程目录'）")

    return {
        "layout_file": str(layout_path) if layout_path else None,
        "layout_source": source,
        "arch_family": arch_family,
        "arch_family_source": af_source,
        "architecture": architecture,
        "skeleton_dirs": sorted(set(parsed["skeleton"])),
        "skill_dirs": skill_dirs,
        "ide_dirs": sorted(set(parsed["ide_dirs"])),
        "scan_roots": scan_roots,
        "include_dirs": include_dirs,
        "warnings": warnings,
    }


def plan_from_builtin(architecture: str = "layered",
                      arch_family: str = "cortex_m") -> dict:
    """从内置兜底树直接构造 LayoutPlan（ide_sync 等公共工具的降级路径）。"""
    if arch_family not in ARCH_FAMILIES:
        arch_family = "cortex_m"
    if architecture not in VALID_ARCHITECTURES:
        architecture = "layered"
    parsed = _parse_tree(_BUILTIN_TREES[arch_family])
    if architecture == "flat":
        _apply_flat(parsed)
    parsed.pop("warnings")
    skill_dirs = {k: {"src": [], "inc": []} for k in ("s5a", "s5b", "s5c")}
    for rel in sorted(parsed["incsrc"]):
        leaf = rel.rsplit("/", 1)[-1].lower()
        kind = "src" if leaf == "src" else "inc"
        for skill in sorted(parsed["incsrc"][rel]):
            skill_dirs[skill][kind].append(rel)
    return {
        "layout_file": None,
        "layout_source": "builtin",
        "arch_family": arch_family,
        "arch_family_source": "fallback",
        "architecture": architecture,
        "skeleton_dirs": sorted(set(parsed["skeleton"])),
        "skill_dirs": skill_dirs,
        "ide_dirs": sorted(set(parsed["ide_dirs"])),
        "scan_roots": sorted({d for k in skill_dirs for d in skill_dirs[k]["src"]}),
        "include_dirs": sorted({d for k in skill_dirs for d in skill_dirs[k]["inc"]}),
        "warnings": ["布局文件不可用，已按内置兜底布局处理"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="layout_resolver：解析 PROJECT_LAYOUT.md → LayoutPlan（JSON 输出）")
    parser.add_argument("--project", required=True,
                        help="项目根目录（含 config.json，如 examples/stm32f103zet6）")
    parser.add_argument("--arch", choices=VALID_ARCHITECTURES, default=None,
                        help="覆盖 architecture（仅本次生效）")
    parser.add_argument("--arch-family", choices=ARCH_FAMILIES, default=None,
                        help="覆盖 arch_family（仅本次生效，调试用）")
    args = parser.parse_args(argv)

    project_root = Path(args.project).expanduser().resolve()
    try:
        cfg = json.loads((project_root / "config.json").read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    state = None
    target = (cfg.get("project") or {}).get("build_target") or "App"
    state_path = project_root / target / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            state = None

    try:
        plan = resolve_layout(project_root, cfg, state, args.arch, args.arch_family)
    except LayoutError as exc:
        _log(f"布局解析失败: {exc}")
        return 2
    for w in plan["warnings"]:
        _log(f"警告: {w}")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
