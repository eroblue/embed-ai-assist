"""S7a toolchain-setup 确定性分析共享模块（rule 轨，prepare/validate 共用）。

职责边界：
- 工具检测（路径存在性 / 可执行 / 版本探测）
- 构建系统判定复用 S7b build/scripts/analysis.py 的共享函数（**禁止两套规则**）
- 开源工具白名单与最低版本要求；商业工具（Keil/IAR/厂家 IDE）只检测不安装

实现依据：S7a requirement §输入/§商业工具红线/§执行步骤。
本模块不修改 config.json（回填由 Agent 在用户确认后执行，rule 只检测与复验）。
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

# 复用 S7b 构建系统推断与工具探测（禁止两套规则）。
# 两个 skill 的共享模块同名 analysis.py，按路径加载避免模块名冲突。
_S7B_ANALYSIS = SKILL_DIR.parent / "build" / "scripts" / "analysis.py"
_spec = importlib.util.spec_from_file_location("s7b_build_analysis", _S7B_ANALYSIS)
build_analysis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_analysis)


# ---------------- 开源工具白名单与最低版本 ----------------

# 开源工具最低版本（requirement §商业工具红线）
OPEN_TOOL_MIN_VERSIONS: dict[str, tuple[int, int] | None] = {
    "gcc": (10, 0),
    "gcc_objcopy": (10, 0),
    "make": (4, 0),
    "cmake": (3, 20),
}

# 商业工具（不自动安装，缺失给手动指引）
COMMERCIAL_TOOLS = {"keil", "keil_fromelf", "iar", "iar_ielftool", "vendor_ide"}

# 构建系统 → 检查清单（requirement 阶段 A 步骤 2）
CHECKLISTS: dict[str, list[str]] = {
    "keil": ["keil", "keil_fromelf"],
    "iar": ["iar", "iar_ielftool"],
    "gcc_make": ["gcc", "gcc_objcopy", "make"],
    "gcc_cmake": ["gcc", "gcc_objcopy", "cmake"],
    "vendor_ide": ["vendor_ide"],
}

# 工具显示名（install_plan / 报告用）
TOOL_LABELS = {
    "gcc": "ARM GNU Toolchain（arm-none-eabi-gcc）",
    "gcc_objcopy": "arm-none-eabi-objcopy（随 ARM GNU Toolchain 安装）",
    "make": "GNU Make",
    "cmake": "CMake",
    "keil": "Keil MDK（UV4 + fromelf）",
    "keil_fromelf": "Keil fromelf（随 Keil MDK 安装）",
    "iar": "IAR EWARM（IarBuild）",
    "iar_ielftool": "IAR ielftool（随 IAR 安装）",
    "vendor_ide": "厂家 IDE",
}


def checklist_for(build_system: str) -> list[str]:
    return CHECKLISTS.get(build_system, [])


# ---------------- 工具路径解析（显式优先，缺省推导——与 S7b 同一规则） ----------------

def resolve_tool_path(config: dict, tool_name: str) -> dict:
    """单个工具路径解析：tool_paths 显式配置优先，否则按 S7b 推导规则。

    返回 {path, configured, derived}（path 为实际可用路径或配置值或 None）。
    """
    tool_paths = config.get("tool_paths") or {}
    explicit = tool_paths.get(tool_name) or None
    derived: Path | None = None
    if tool_name == "keil_fromelf":
        derived = build_analysis.detect_fromelf(tool_paths.get("keil"))
    elif tool_name == "iar_ielftool":
        derived = build_analysis.detect_ielftool(tool_paths.get("iar"))
    elif tool_name == "gcc_objcopy":
        derived = build_analysis.detect_objcopy(tool_paths.get("gcc"))

    if explicit and Path(explicit).is_file():
        return {"path": str(Path(explicit)), "configured": True, "derived": False}
    if derived and derived.is_file():
        return {"path": str(derived), "configured": False, "derived": True}
    return {"path": str(Path(explicit)) if explicit else None,
            "configured": bool(explicit), "derived": False}


# ---------------- 版本探测 ----------------

_VERSION_ARGS = {
    "gcc": ["--version"],
    "gcc_objcopy": ["--version"],
    "make": ["--version"],
    "cmake": ["--version"],
}


def probe_version(tool_name: str, tool_path: str | None) -> str | None:
    """执行 `<tool> --version` 探测版本（商业工具/失败返回 None，不作为就绪判据）。"""
    if not tool_path or tool_name not in _VERSION_ARGS:
        return None
    try:
        proc = subprocess.run([tool_path] + _VERSION_ARGS[tool_name],
                              capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", errors="replace") \
        or proc.stderr.decode("utf-8", errors="replace")
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return m.group(0) if m else None


def version_ok(tool_name: str, version: str | None) -> bool | None:
    """版本是否满足最低要求（None=无最低要求或无法探测，不作判据）。"""
    minimum = OPEN_TOOL_MIN_VERSIONS.get(tool_name)
    if minimum is None or version is None:
        return None
    m = re.match(r"(\d+)\.(\d+)", version)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2))) >= minimum


# ---------------- 检测主入口 ----------------

def detect_tools(config: dict, build_system: str) -> dict:
    """按构建系统检查清单逐项检测。

    返回 toolchain_check.json 的数据体：
    {build_system, checked_at, tools: [...], intelhex_available, all_present,
     missing, open_missing, commercial_missing, warnings}
    """
    tools: list[dict] = []
    for name in checklist_for(build_system):
        info = resolve_tool_path(config, name)
        present = bool(info["path"]) and Path(info["path"]).is_file()
        version = probe_version(name, info["path"]) if present else None
        tools.append({
            "name": name,
            "label": TOOL_LABELS.get(name, name),
            "path": info["path"],
            "configured": info["configured"],
            "derived": info["derived"],
            "present": present,
            "version": version,
            "min_version": (".".join(map(str, OPEN_TOOL_MIN_VERSIONS[name]))
                             if name in OPEN_TOOL_MIN_VERSIONS else None),
            "version_ok": version_ok(name, version),
            "commercial": name in COMMERCIAL_TOOLS,
        })

    intelhex_ok = build_analysis.intelhex_available()
    warnings: list[str] = []
    # vendor_ide 的 hex→bin 依赖 intelhex（开源依赖，缺失列入安装清单）
    if build_system == "vendor_ide" and not intelhex_ok:
        warnings.append("Python intelhex 包未安装（vendor_ide hex→bin 依赖）："
                        "pip install intelhex")
    for t in tools:
        if t["present"] and t["version_ok"] is False:
            warnings.append(f"{t['label']} 版本 {t['version']} 低于最低要求 "
                            f"{t['min_version']}——警告不终止，建议升级")

    missing = [t["name"] for t in tools if not t["present"]]
    return {
        "build_system": build_system,
        "checked_at": build_analysis.now_iso(),
        "tools": tools,
        "intelhex_available": intelhex_ok,
        "all_present": (not missing
                        and (intelhex_ok if build_system == "vendor_ide" else True)),
        "missing": missing,
        "open_missing": [n for n in missing if n not in COMMERCIAL_TOOLS],
        "commercial_missing": [n for n in missing if n in COMMERCIAL_TOOLS],
        "warnings": warnings,
    }


def determine_build_system(config: dict, project_root: Path) -> tuple[str, str]:
    """构建系统判定：显式配置优先，否则 S7b 共享推断。

    返回 (build_system, 依据描述)；无法判定抛 build_analysis.BuildDetectError。
    """
    project_cfg = config.get("project") or {}
    explicit = project_cfg.get("build_system")
    target_root = build_analysis.resolve_target(config, project_root)
    if explicit:
        return explicit, f"显式配置 project.build_system={explicit}"
    system, project_file = build_analysis.infer_build_system(
        target_root, (project_cfg.get("inputs") or {}).get("ide_project") or "")
    return system, f"扫描推断（依据 {project_file.name}）"
