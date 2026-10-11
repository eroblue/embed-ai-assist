"""S7b build 确定性分析共享模块（rule 轨，prepare/build/validate 共用）。

职责边界（S7b 是纯 rule + Agent 分析形态，无代码生成）：
- 分层配置加载、S5 系列就绪检查
- 构建系统智能推断（递归扫描，vendor_ide 不参与推断）——**S7a toolchain-setup
  复用本模块的推断与工具探测函数，禁止两套规则**
- 构建配置（target/configuration）推断（"不猜"原则：多候选报错）
- 工具链探测（fromelf/ielftool/objcopy 的推导规则）
- 编译日志多编码解码与解析（错误/警告/产物路径提取）

实现依据：S7b requirement §输入/§智能推断通道/§执行步骤。
本模块不生成任何 C 代码，不修改工程文件。
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

BUILD_SYSTEMS = ("keil", "iar", "gcc_make", "gcc_cmake", "vendor_ide")
CLI_SYSTEMS = ("keil", "iar", "gcc_make", "gcc_cmake")

# ---------------- JSON / 配置工具（与 S5 系列 analysis 同模式，skill 间不耦合） ----------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    """根目录 config.json → 项目 config.json 深合并（只读，不回写）。"""
    notes: list[str] = []
    root_cfg: dict = {}
    root_config_path = ROOT_DIR / "config.json"
    if root_config_path.is_file():
        root_cfg = load_json(root_config_path)
        notes.append(f"已加载全局配置: {root_config_path}")
    if not project_config_path.is_file():
        raise FileNotFoundError(f"项目配置不存在: {project_config_path}")
    proj_cfg = load_json(project_config_path)
    notes.append(f"已加载项目配置: {project_config_path}")
    return deep_merge(root_cfg, proj_cfg), notes


def validate_schema(instance: dict, schema_path: Path, label: str) -> list[str]:
    """jsonschema 校验，返回错误列表（未安装 jsonschema 时跳过并提示）。"""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema 未安装，跳过校验: pip install jsonschema"]
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def resolve_target(config: dict | None, project_root: Path) -> Path:
    """目标工程根（App/BootLoader 双工程）：project.build_target 决定（缺省 App）。"""
    target = ((config or {}).get("project") or {}).get("build_target") or "App"
    return project_root / str(target)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel_posix(path: Path, base: Path) -> str:
    """工作区内相对 POSIX 路径（统一规则 10）。"""
    try:
        return str(path.resolve().relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# ---------------- 构建系统智能推断（S7a 复用，禁止两套规则） ----------------

class BuildDetectError(RuntimeError):
    """构建系统/构建配置无法判定（多候选/零候选/工程文件缺失）。"""


# 递归扫描排除目录（编译中间产物与本框架输出）
SCAN_EXCLUDE_DIRS = {"outputs", "listings", "objects", ".history", "rte", "debugconfig"}
_SCAN_DEPTH = 3


def _is_backup_dir(name: str) -> bool:
    low = name.lower()
    return ("backup" in low or low.endswith("_bak") or low.endswith(".bak")
            or low.endswith("_old") or low.endswith("_backup"))


def scan_build_evidence(target_root: Path) -> dict[str, list[Path]]:
    """递归扫描目标工程根（深度 3，排除 outputs/Listings/Objects/.history/备份目录）。

    返回 {build_system: [文件路径]}，只含命中的系统（vendor_ide 不参与推断）。
    """
    evidence: dict[str, list[Path]] = {"keil": [], "iar": [], "gcc_make": [], "gcc_cmake": []}
    if not target_root.is_dir():
        return evidence

    def _scan(dir_path: Path, depth: int) -> None:
        if depth > _SCAN_DEPTH:
            return
        try:
            entries = sorted(dir_path.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                low = entry.name.lower()
                if low in SCAN_EXCLUDE_DIRS or _is_backup_dir(entry.name):
                    continue
                _scan(entry, depth + 1)
            else:
                low = entry.name.lower()
                if low.endswith(".uvprojx"):
                    evidence["keil"].append(entry)
                elif low.endswith(".ewp"):
                    evidence["iar"].append(entry)
                elif low in ("makefile", "gnumakefile"):
                    evidence["gcc_make"].append(entry)
                elif entry.name == "CMakeLists.txt":
                    evidence["gcc_cmake"].append(entry)

    _scan(target_root, 1)
    return {k: v for k, v in evidence.items() if v}


def infer_build_system(target_root: Path, ide_project: str = "") -> tuple[str, Path]:
    """推断构建系统与工程文件：返回 (build_system, 工程文件路径)。

    - 多个系统同时有候选文件 → BuildDetectError（要求显式配置 build_system）
    - 零候选 → BuildDetectError
    - 单系统多个工程文件 → 优先 project.inputs.ide_project 指定者，否则报错
    """
    evidence = scan_build_evidence(target_root)
    hits = {k: v for k, v in evidence.items() if v}
    if len(hits) > 1:
        found = "、".join(f"{k}({', '.join(p.name for p in v)})" for k, v in hits.items())
        raise BuildDetectError(
            f"目标工程根发现多种构建系统工程文件：{found}——请在 config 显式指定 project.build_system")
    if not hits:
        raise BuildDetectError(
            f"目标工程根未发现任何构建系统工程文件（*.uvprojx / *.ewp / Makefile / "
            f"CMakeLists.txt）：{target_root}——请创建工程文件或显式配置 project.build_system")
    system, files = next(iter(hits.items()))
    if len(files) > 1:
        if ide_project:
            wanted = (target_root / ide_project).resolve()
            for f in files:
                if f.resolve() == wanted and f.is_file():
                    return system, f
        names = "、".join(str(f.relative_to(target_root)) for f in files)
        raise BuildDetectError(
            f"发现多个 {'工程文件' if system != 'gcc_make' else 'Makefile'}（{names}）——"
            f"请在 project.inputs.ide_project 指定其一")
    return system, files[0]


# ---------------- 构建配置（target/configuration）推断 ----------------

def parse_uvprojx_targets(uvprojx: Path) -> list[str]:
    """解析 .uvprojx 的 <TargetName> 列表（build_config 推断，XML 浅解析即可）。"""
    text = uvprojx.read_text(encoding="utf-8", errors="replace")
    return [m.group(1).strip() for m in re.finditer(r"<TargetName>(.*?)</TargetName>", text)]


def parse_ewp_configurations(ewp: Path) -> list[str]:
    """解析 .ewp 的 <configuration><name> 列表。"""
    text = ewp.read_text(encoding="utf-8", errors="replace")
    names = re.findall(r"<configuration>.*?<name>(.*?)</name>", text, re.S)
    return [n.strip() for n in names]


def infer_build_config(build_system: str, project_file: Path) -> str | None:
    """build_config 推断（"不猜"原则：多候选报错，无 config 概念返回 None）。

    gcc_make 无 config 概念；gcc_cmake 缺省 Debug（无法确定时报错由调用方处理）。
    """
    if build_system == "vendor_ide":
        return None
    if build_system == "keil":
        targets = parse_uvprojx_targets(project_file)
        if not targets:
            raise BuildDetectError(f"未从 {project_file.name} 解析到 <TargetName>")
        if len(targets) > 1:
            raise BuildDetectError(
                f"{project_file.name} 含多个 target（{'、'.join(targets)}）——"
                f"请在 config 显式指定 project.build_config")
        return targets[0]
    if build_system == "iar":
        configs = parse_ewp_configurations(project_file)
        if not configs:
            raise BuildDetectError(f"未从 {project_file.name} 解析到 configuration")
        if len(configs) > 1:
            raise BuildDetectError(
                f"{project_file.name} 含多个 configuration（{'、'.join(configs)}）——"
                f"请在 config 显式指定 project.build_config")
        return configs[0]
    if build_system == "gcc_make":
        return None
    if build_system == "gcc_cmake":
        # CMake 无显式 config 时通常为空（单配置生成器）；有 build 目录时取已配置值
        build_dir = project_file.parent / "build"
        cache = build_dir / "CMakeCache.txt"
        if cache.is_file():
            m = re.search(r"CMAKE_BUILD_TYPE:STRING=(\S+)", cache.read_text(encoding="utf-8", errors="replace"))
            if m:
                return m.group(1)
        return "Debug"
    raise BuildDetectError(f"未知构建系统: {build_system}")


# ---------------- 工具链探测（S7a 复用） ----------------

def detect_fromelf(keil_exe: str | None) -> Path | None:
    """从 tool_paths.keil 推导 fromelf：<Keil 根>/ARM/ARMCLANG|ARMCC/bin/fromelf.exe。

    多份时 ARMCLANG 优先。keil 未配置或探测失败返回 None。
    """
    if not keil_exe:
        return None
    keil = Path(keil_exe)
    if not keil.is_file():
        return None
    root = keil.parent.parent  # <Keil 根>/UV4/UV4.exe → <Keil 根>
    for sub in ("ARM/ARMCLANG/bin", "ARM/ARMCC/bin"):
        cand = root / sub / "fromelf.exe"
        if cand.is_file():
            return cand
    return None


def detect_ielftool(iarbuild_exe: str | None) -> Path | None:
    """从 tool_paths.iar 推导 ielftool：IarBuild 同目录 common/bin/ielftool.exe。"""
    if not iarbuild_exe:
        return None
    iar = Path(iarbuild_exe)
    if not iar.is_file():
        return None
    cand = iar.parent / "common" / "bin" / "ielftool.exe"
    return cand if cand.is_file() else None


def detect_objcopy(gcc_exe: str | None) -> Path | None:
    """从 tool_paths.gcc 同目录探测 arm-none-eabi-objcopy。"""
    if not gcc_exe:
        return None
    gcc = Path(gcc_exe)
    if not gcc.is_file():
        return None
    cand = gcc.parent / "arm-none-eabi-objcopy.exe"
    if cand.is_file():
        return cand
    cand = gcc.parent / "arm-none-eabi-objcopy"
    return cand if cand.is_file() else None


def resolve_tool_paths(config: dict, build_system: str) -> dict:
    """按构建系统解析实际工具路径（显式配置优先，缺省推导）。

    返回 {工具名: {"path": str|None, "configured": bool, "derived": bool}}。
    编译必需工具与 bin/hex 转换工具分开（后者缺失仅警告）。
    """
    tool_paths = config.get("tool_paths") or {}
    gcc = tool_paths.get("gcc") or None
    result: dict[str, dict] = {}

    def _put(name: str, explicit: str | None, derived: Path | None = None) -> None:
        if explicit and Path(explicit).is_file():
            result[name] = {"path": str(Path(explicit)), "configured": True, "derived": False}
        elif derived and derived.is_file():
            result[name] = {"path": str(derived), "configured": False, "derived": True}
        else:
            result[name] = {"path": (str(Path(explicit)) if explicit else None),
                            "configured": bool(explicit), "derived": False}

    if build_system == "keil":
        _put("keil", tool_paths.get("keil"))
        _put("keil_fromelf", tool_paths.get("keil_fromelf"),
             detect_fromelf(tool_paths.get("keil")))
    elif build_system == "iar":
        _put("iar", tool_paths.get("iar"))
        _put("iar_ielftool", tool_paths.get("iar_ielftool"),
             detect_ielftool(tool_paths.get("iar")))
    elif build_system in ("gcc_make", "gcc_cmake"):
        _put("gcc", tool_paths.get("gcc"))
        _put("gcc_objcopy", tool_paths.get("gcc_objcopy"), detect_objcopy(gcc))
        _put("make", tool_paths.get("make"))
        _put("cmake", tool_paths.get("cmake"))
    elif build_system == "vendor_ide":
        _put("vendor_ide", tool_paths.get("vendor_ide"))
    return result


def compile_tools_required(build_system: str) -> list[str]:
    """构建系统 → 编译必需工具（缺失报错，提示运行 S7a）。"""
    return {
        "keil": ["keil"],
        "iar": ["iar"],
        "gcc_make": ["gcc", "make"],
        "gcc_cmake": ["gcc", "cmake"],
        "vendor_ide": ["vendor_ide"],
    }[build_system]


def bin_tools(build_system: str) -> list[str]:
    """构建系统 → bin/hex 转换工具（缺失仅警告，intelhex 兜底）。"""
    return {
        "keil": ["keil_fromelf"],
        "iar": ["iar_ielftool"],
        "gcc_make": ["gcc_objcopy"],
        "gcc_cmake": ["gcc_objcopy"],
        "vendor_ide": [],
    }[build_system]


def intelhex_available() -> bool:
    try:
        import intelhex  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------- 日志解码与解析 ----------------

def decode_log(data: bytes) -> str:
    """多编码解码：UTF-8 → GBK → replace（Keil 在中文 Windows 上日志常为 GBK）。"""
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


# 各构建系统错误/警告行特征（见 references/log_parse_rules.md）
_LOG_PATTERNS = {
    "keil": {
        # armcc/armclang 编译错误 "...(12): error: #20: ..."；链接错误 "Error: L6218E"
        "error": re.compile(r"(?i)\berror\b\s*:\s*(?:[#Ll]|\d)|\*\*\*\s*error", re.I),
        "warning": re.compile(r"(?i)\bwarning\s*:\s*#"),
        "summary": re.compile(r"(\d+)\s+Error\(s\),\s*(\d+)\s+Warning\(s\)"),
    },
    "iar": {
        "error": re.compile(r"Error\[|Fatal Error\[", re.I),
        "warning": re.compile(r"Warning\[", re.I),
        "summary": re.compile(r"(\d+)\s+errors?,\s*(\d+)\s+warnings?", re.I),
    },
    "gcc_make": {
        "error": re.compile(r"(?<![A-Za-z])error:", re.I),
        "warning": re.compile(r"(?<![A-Za-z])warning:", re.I),
        "summary": None,
    },
    "gcc_cmake": {
        "error": re.compile(r"(?<![A-Za-z])error:", re.I),
        "warning": re.compile(r"(?<![A-Za-z])warning:", re.I),
        "summary": None,
    },
    "vendor_ide": {
        "error": re.compile(r"(?i)\berror\b|\b失败\b"),
        "warning": re.compile(r"(?i)\bwarning\b|\b警告\b"),
        "summary": None,
    },
}

_DETAIL_RE = re.compile(
    r"^(?P<file>[^()\s][^()]*?)?\(?(?P<line>\d+)?\)?\s*[:：]?\s*(?P<msg>.*)$")


def parse_log(build_system: str, text: str) -> dict:
    """解析编译日志 → {error_count, warning_count, errors, warnings}。

    error/warning 条目：{file, line, message}。计数优先取日志尾部汇总行
    （Keil "N Error(s), M Warning(s)" / IAR "N errors, M warnings"），
    无汇总行时按匹配行数计。
    """
    pats = _LOG_PATTERNS.get(build_system, _LOG_PATTERNS["gcc_make"])
    errors: list[dict] = []
    warnings: list[dict] = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if pats["error"].search(line):
            m = _DETAIL_RE.match(line)
            errors.append({"file": (m.group("file") or "").strip() or None,
                           "line": int(m.group("line")) if m and m.group("line") else None,
                           "message": line.strip()})
            continue
        if pats["warning"].search(line):
            warnings.append({"file": None, "line": None, "message": line.strip()})

    error_count, warning_count = len(errors), len(warnings)
    if pats["summary"]:
        for m in pats["summary"].finditer(text):
            error_count, warning_count = int(m.group(1)), int(m.group(2))
        # 汇总行计数与明细行数不一致时取大者（防漏匹配明细）
        error_count = max(error_count, len(errors))
        warning_count = max(warning_count, len(warnings))
    return {"error_count": error_count, "warning_count": warning_count,
            "errors": errors, "warnings": warnings}


# ---------------- 编译命令与退出码语义 ----------------

def build_commands(build_system: str, tool_exe: str, project_file: Path,
                   build_config: str | None, log_path: Path, rebuild: bool) -> list[list[str]]:
    """构造 CLI 编译命令序列（完整 argv；vendor_ide 返回 [] 走 GUI 机制）。

    gcc_make --rebuild 时为 [make clean, make] 两步。
    """
    if build_system == "keil":
        return [[tool_exe, "-r" if rebuild else "-b", str(project_file),
                 "-j0", "-o", str(log_path)]]
    if build_system == "iar":
        return [[tool_exe, str(project_file), "-build", str(build_config or ""),
                 "-log", "info"]]
    if build_system == "gcc_make":
        cmds = [[tool_exe, "clean"]] if rebuild else []
        cmds.append([tool_exe, "-j4"])
        return cmds
    if build_system == "gcc_cmake":
        args = [tool_exe, "--build", str(project_file.parent / "build")]
        if build_config:
            args.append("--config")
            args.append(build_config)
        if rebuild:
            args.append("--clean-first")
        args.extend(["--", "-j4"])
        return [args]
    return []


def exit_code_success(build_system: str, exit_code: int | None,
                      parsed_error_count: int) -> bool:
    """退出码 → 成功判定（UV4：0=成功无警告，1=成功有警告，≥2=失败；其余非 0 即失败）。"""
    if exit_code is None:
        return False
    if build_system == "keil":
        return exit_code in (0, 1) and parsed_error_count == 0
    return exit_code == 0 and parsed_error_count == 0


# ---------------- 产物定位 ----------------

def locate_artifacts(build_system: str, project_file: Path, build_config: str | None,
                     log_text: str = "") -> dict:
    """定位主调试产物与 hex（优先日志解析，缺省按约定路径推断）。

    返回 {artifact: Path|None, artifact_format: str|None, hex: Path|None}。
    路径不存在时仍返回推断值（由调用方判存在性）；完全无法推断 → None。
    """
    result: dict = {"artifact": None, "artifact_format": None, "hex": None}
    if build_system == "keil":
        objects = project_file.parent / "Objects"
        name = build_config or ""
        result["artifact_format"] = "axf"
        result["artifact"] = objects / f"{name}.axf"
        result["hex"] = objects / f"{name}.hex"
    elif build_system == "iar":
        exe_dir = project_file.parent.parent / (build_config or "") / "Exe"
        # .ewp 常在 <root>/<proj>.ewp，产物在 <root>/<config>/Exe/（注意非 Obj/）
        if not exe_dir.is_dir():
            exe_dir = project_file.parent / (build_config or "") / "Exe"
        result["artifact_format"] = "out"
        cands = sorted(exe_dir.glob("*.out")) if exe_dir.is_dir() else []
        result["artifact"] = cands[0] if cands else None
        hexes = sorted(exe_dir.glob("*.hex")) if exe_dir.is_dir() else []
        result["hex"] = hexes[0] if hexes else None
    elif build_system in ("gcc_make", "gcc_cmake"):
        base = project_file.parent / "build"
        if build_system == "gcc_cmake" and build_config:
            base = base / build_config
        result["artifact_format"] = "elf"
        # 优先从日志链接命令 -o 提取（最准确）
        m = re.search(r"-o\s+(\S+\.(?:elf|out|axf))", log_text)
        if m:
            result["artifact"] = project_file.parent / m.group(1) \
                if not Path(m.group(1)).is_absolute() else Path(m.group(1))
        else:
            elfs = sorted(base.glob("*.elf")) if base.is_dir() else []
            result["artifact"] = elfs[0] if elfs else None
        hexes = sorted(base.glob("*.hex")) if base.is_dir() else []
        result["hex"] = hexes[0] if hexes else None
    return result


# ---------------- S7b 执行上下文 ----------------

def load_build_context(config_path: Path, workspace: Path | None = None) -> dict:
    """加载配置 + S5 系列就绪检查，返回 S7b 执行上下文。

    抛 RuntimeError：state 缺失 / S5a/S5b/S5c 未完成 / 配置契约非法。
    """
    config, _notes = load_layered_config(config_path)
    cfg_errors = validate_schema(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        raise RuntimeError("配置契约校验失败: " + "; ".join(cfg_errors))
    if workspace is None:
        workspace = config_path.parent
    project_root = workspace
    target_root = resolve_target(config, project_root)
    state_path = target_root / "state.json"
    if not state_path.exists():
        raise RuntimeError(f"state.json 不存在: {state_path}（先执行 S1 建立工作区）")
    state = load_json(state_path)

    input_errors = validate_schema(state, SKILL_DIR / "schemas" / "input.schema.json", "state")
    if input_errors:
        raise RuntimeError("S5 就绪检查失败: " + "; ".join(input_errors)
                           + "——S7b 需 S5a/S5b done 且 S5c done 或 skipped（flat）")

    project_cfg = config.get("project") or {}
    inputs_cfg = project_cfg.get("inputs") or {}
    outputs_dir = target_root / (config.get("output_dir") or "outputs").rstrip("/\\")
    return {
        "config": config,
        "project_root": project_root,
        "workspace": target_root,          # 目标工程根 <项目根>/<build_target>/
        "state_path": state_path,
        "state": state,
        "outputs_dir": outputs_dir,
        "s7b_outputs": outputs_dir / "s7b",
        "build_target": project_cfg.get("build_target") or "App",
        "build_system_cfg": project_cfg.get("build_system"),
        "build_config_cfg": project_cfg.get("build_config"),
        "vendor_ide": project_cfg.get("vendor_ide"),
        "vendor_ide_output_dir": project_cfg.get("vendor_ide_output_dir"),
        "arch_family": project_cfg.get("arch_family") or "cortex_m",
        "ide_project": inputs_cfg.get("ide_project") or "",
    }


def run_tool(cmd: list[str], timeout: float, cwd: Path | None = None,
             env: dict | None = None) -> dict:
    """执行外部工具（带超时控制）：返回 {exit_code, stdout, stderr, timed_out}。

    env 为 None 时继承当前进程环境；传入时为完整环境 dict（调用方基于 os.environ 构造）。
    """
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, timeout=timeout,
            capture_output=True, env=env)
        return {"exit_code": proc.returncode,
                "stdout": proc.stdout or b"",
                "stderr": proc.stderr or b"",
                "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": None,
                "stdout": (exc.stdout or b"") if isinstance(exc.stdout, bytes) else b"",
                "stderr": (exc.stderr or b"") if isinstance(exc.stderr, bytes) else b"",
                "timed_out": True}
    except FileNotFoundError:
        return {"exit_code": None, "stdout": b"", "stderr": "工具可执行文件不存在".encode("utf-8"),
                "timed_out": False}
