"""S9 flash 确定性分析共享模块（rule 轨，prepare/flash/validate 共用）。

职责边界（S9 是纯 rule + Agent 分析形态，无代码生成）：
- 分层配置加载、S7b/S6 就绪检查（--firmware 显式时跳过 state 检查）
- 烧录工具判定：显式配置优先；null 时智能推断（uvoptx pMon 调试器证据 +
  tool_paths 可用性/平台惯例；多候选/零候选/证据工具不可用报错，不猜）
- 烧录工具路径探测（jlink 未配置时从既存 tool_paths.jflash 同目录推导）
- 固件选择通道：--firmware > S6 合并固件 > s7b hex > s7b bin（release/ 永不作为
  发现来源，state 指针为唯一权威）
- Flash 基址/容量来源链（复用 S7b makefile_gen：uvprojx IROM / .ld ORIGIN /
  PLATFORM_FALLBACK——禁止两套规则）
- 烧录地址计算（flash_offset 唯一权威）+ 越界/对齐/起址防御性校验
- J-Link 设备名映射（一期校准平台表，映射失败报错要求 --device，不猜）
- release/ 发布同步（SHA256 现场计算比对：一致复用、不一致覆盖，不信任清单记录值）
- J-Link Commander 脚本生成（flash_cmd.jlink，自包含可交付）
- 烧录日志解析（成功/失败特征行映射表见 references/flash_log_parse_rules.md）

实现依据：S9 requirement §输入/§智能推断通道/§固件选择通道/§烧录地址规则/§执行步骤。
本模块不生成任何 C 代码，不修改工程文件与固件文件。
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent
S7B_SCRIPTS_DIR = SKILL_DIR.parent / "build" / "scripts"

# ---------------- S7b 模块复用（importlib 加载避免与本模块同名冲突） ----------------


def _load_s7b_module(basename: str, alias: str):
    """从 S7b build 技能加载模块（alias 避免与本模块或已加载模块同名冲突）。"""
    spec = importlib.util.spec_from_file_location(
        alias, S7B_SCRIPTS_DIR / f"{basename}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_s7b = _load_s7b_module("analysis", "s7b_analysis_shared")          # skills/build/scripts/analysis.py
_makefile_gen = _load_s7b_module("makefile_gen", "s7b_makefile_gen_shared")  # skills/build/scripts/makefile_gen.py

# 通用工具直接复用 S7b 实现（单一事实来源）
load_json = _s7b.load_json
save_json = _s7b.save_json
deep_merge = _s7b.deep_merge
load_layered_config = _s7b.load_layered_config
validate_schema = _s7b.validate_schema
resolve_target = _s7b.resolve_target
now_iso = _s7b.now_iso
rel_posix = _s7b.rel_posix
decode_log = _s7b.decode_log
run_tool = _s7b.run_tool
intelhex_available = _s7b.intelhex_available

# Flash 内存布局来源链复用 S7b makefile_gen（禁止两套规则）
PLATFORM_FALLBACK = _makefile_gen.PLATFORM_FALLBACK
PROJECT_DISCOVER_EXCLUDE = _makefile_gen.PROJECT_DISCOVER_EXCLUDE
parse_uvprojx = _makefile_gen.parse_uvprojx

# ---------------- 常量 ----------------

FLASH_TOOLS = ("jlink", "jflash", "stlink", "openocd", "pyocd", "vendor_ide")

# tool_paths 键映射（requirement §输入"从全局 config.json 读取"表）
TOOL_PATHS_KEY = {
    "jlink": "jlink",
    "jflash": "jflash",
    "stlink": "stlink_cli",
    "openocd": "openocd",
    "pyocd": "pyocd",
    "vendor_ide": "vendor_ide",
}

# J-Link 设备库命名映射表（与 references/jlink_flash_guide.md 的表保持同步；
# 一期实测校准两个已有平台。规则：剥离封装/温度等级尾码（如 ZET6 → ZE）。
# 映射失败 → 报错要求 --device 显式指定，不猜）
JLINK_DEVICE_MAP = {
    "stm32f103zet6": "STM32F103ZE",
    "gd32f205vet6": "GD32F205VE",
}

# 智能推断：uvoptx <pMon> 调试器 DLL → 烧录工具（证据 1；顺序敏感，先匹配具体名）
_PMON_MAP = (
    ("st-linkiii-keil_swo", "stlink"),
    ("stlink", "stlink"),
    ("jl2cm3", "jlink"),
    ("segger", "jlink"),
    ("cmsis_agdi", "openocd"),  # CMSIS-DAP → openocd（cmsis-dap 接口 cfg）
)

# 平台惯例（证据 2 排序）：STM32 家族 stlink 优先，其余 jlink 优先
_PLATFORM_TOOL_ORDER_STM32 = ("stlink", "jlink", "openocd", "pyocd")
_PLATFORM_TOOL_ORDER_DEFAULT = ("jlink", "openocd", "pyocd")


class FlashDetectError(RuntimeError):
    """烧录工具无法判定（多候选/零候选/证据工具不可用/未识别调试器 DLL）。"""


class FlashPlanError(RuntimeError):
    """烧录计划非法（配置/固件/地址/设备/工具错误，prepare 阶段报错即拦截）。"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- 执行上下文 ----------------


def load_flash_context(config_path: Path, workspace: Path | None = None,
                       require_s7b: bool = True) -> dict:
    """加载配置 + S7b/S6 就绪检查，返回 S9 执行上下文。

    require_s7b=False 时跳过 s7b 就绪检查（--firmware 显式指定时；
    state.json 缺失时从 {} 容错开始，state_store 会按需创建）。

    抛 RuntimeError：配置契约非法 / state 缺失 / S7b 未完成。
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
    state: dict = {}
    if state_path.is_file():
        state = load_json(state_path)
    elif require_s7b:
        raise RuntimeError(f"state.json 不存在: {state_path}（先执行 S1 建立工作区）")

    if require_s7b:
        input_errors = validate_schema(
            state, SKILL_DIR / "schemas" / "input.schema.json", "state")
        if input_errors:
            raise RuntimeError(
                "S9 就绪检查失败: " + "; ".join(input_errors)
                + "——S9 需 s7b.status=done 且 hex/bin 至少一个非空"
                  "（或用 --firmware 显式指定固件跳过检查）")

    project_cfg = config.get("project") or {}
    outputs_dir = target_root / (config.get("output_dir") or "outputs").rstrip("/\\")
    return {
        "config": config,
        "project_root": project_root,
        "workspace": target_root,          # 目标工程根 <项目根>/<build_target>/
        "state_path": state_path,
        "state": state,
        "outputs_dir": outputs_dir,
        "s9_outputs": outputs_dir / "s9",
        "release_dir": project_root / "release",
        "build_target": project_cfg.get("build_target") or "App",
        "flash_tool_cfg": project_cfg.get("flash_tool"),
        "flash_config_cfg": project_cfg.get("flash_config"),
        "flash_offset": int(project_cfg.get("flash_offset") or 0),
        "arch_family": project_cfg.get("arch_family") or "cortex_m",
        "vendor_ide": project_cfg.get("vendor_ide"),
        "ide_project": (project_cfg.get("inputs") or {}).get("ide_project") or "",
        "platform": config.get("platform") or "",
        "mcu_family": (state.get("chip") or {}).get("mcu_family") or "",
    }


# ---------------- 工程文件发现（与 S7b makefile_gen 同排除规则） ----------------


def find_project_file(target_root: Path, ide_project: str, suffix: str) -> Path | None:
    """按后缀发现工程文件（ide_project 显式优先；排除 outputs/objects 等目录）。"""
    if ide_project:
        p = (target_root / ide_project).resolve()
        if p.is_file() and p.suffix.lower() == suffix:
            return p
    for p in sorted(target_root.rglob(f"*{suffix}")):
        if not ({q.lower() for q in p.relative_to(target_root).parts[:-1]}
                & PROJECT_DISCOVER_EXCLUDE):
            return p
    return None


# ---------------- 智能推断（flash_tool == null 时，仅 Cortex-M） ----------------


def probe_uvoptx_evidence(target_root: Path, ide_project: str) -> tuple[str, str] | None:
    """证据 1：解析 Keil *.uvoptx 的 <pMon> 调试器 DLL → (tool, 证据描述)。

    - uvoptx 定位：uvprojx 同目录（IDE 目录），优先同 stem，其次唯一/首个
    - 未识别的厂家调试器 DLL → FlashDetectError（列出 DLL 名，要求显式配置，不猜）
    - 无 uvoptx / 无 pMon → None（证据缺失，走证据 2）
    - IAR .ewd 调试器选择：一期未实现（本机无 IAR 实例可校准，演进项）
    """
    uvprojx = find_project_file(target_root, ide_project, ".uvprojx")
    if uvprojx is None:
        return None
    optx_candidates = sorted(uvprojx.parent.glob("*.uvoptx"))
    if not optx_candidates:
        return None
    uvoptx = next((p for p in optx_candidates if p.stem == uvprojx.stem), None)
    if uvoptx is None:
        if len(optx_candidates) == 1:
            uvoptx = optx_candidates[0]
        else:
            uvoptx = optx_candidates[0]  # 多份时取首个并列出，不阻断证据解析
    text = uvoptx.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<pMon>\s*([^<]+?)\s*</pMon>", text)
    if not m or not m.group(1).strip():
        return None
    pmon = m.group(1).strip()
    low = pmon.lower()
    for key, tool in _PMON_MAP:
        if key in low:
            return tool, f"{uvoptx.name} <pMon>={pmon}"
    raise FlashDetectError(
        f"uvoptx 调试器 DLL 未识别: {pmon}（{uvoptx.name}）——不猜，"
        f"请在项目 config.json 显式配置 project.flash_tool（该探针可能为厂家专用驱动）")


def resolve_flash_tool_path(config: dict, flash_tool: str) -> dict:
    """按 flash_tool 解析烧录工具路径。

    返回 {path: str|None, configured: bool, derived: bool, note: str}。
    jlink：显式 tool_paths.jlink > 从既存 tool_paths.jflash 同目录探测 JLink.exe
    （两 exe 同在 SEGGER 安装目录，如 C:/Program Files/SEGGER/JLink/）。
    其余工具直接消费对应键，无推导（缺失报错由调用方处理，不自动安装）。
    """
    tool_paths = config.get("tool_paths") or {}
    key = TOOL_PATHS_KEY.get(flash_tool, flash_tool)
    explicit = tool_paths.get(key) or None

    if flash_tool == "jlink":
        if explicit and Path(explicit).is_file():
            return {"path": str(Path(explicit)), "configured": True, "derived": False,
                    "note": f"显式配置 tool_paths.{key}"}
        jflash = tool_paths.get("jflash") or None
        if jflash:
            cand = Path(jflash).parent / "JLink.exe"
            if cand.is_file():
                return {"path": str(cand), "configured": False, "derived": True,
                        "note": f"从 tool_paths.jflash 同目录探测（{cand.parent}）"}
        return {"path": str(Path(explicit)) if explicit else None,
                "configured": bool(explicit), "derived": False,
                "note": f"tool_paths.{key} 未配置且 jflash 同目录未探测到 JLink.exe"}

    if explicit and Path(explicit).is_file():
        return {"path": str(Path(explicit)), "configured": True, "derived": False,
                "note": f"显式配置 tool_paths.{key}"}
    return {"path": str(Path(explicit)) if explicit else None,
            "configured": bool(explicit), "derived": False,
            "note": f"tool_paths.{key} 未配置"}


def _platform_tool_order(ctx: dict) -> tuple[str, ...] | None:
    """平台惯例排序（证据 2）：已知家族返回排序，未知返回 None（多候选不猜）。"""
    family = (ctx["mcu_family"] or "").upper()
    platform = (ctx["platform"] or "").lower()
    if family.startswith("STM32") or platform.startswith("stm32"):
        return _PLATFORM_TOOL_ORDER_STM32
    if family or platform:
        return _PLATFORM_TOOL_ORDER_DEFAULT
    return None


def infer_flash_tool(ctx: dict) -> tuple[str, list[str]]:
    """智能推断通道（flash_tool=null，仅 Cortex-M）。

    证据 1（uvoptx pMon）最强：指向的工具 CLI 不可用 → 报错（不回落证据 2，
    防止探针证据与可用工具错配烧坏流程；提示显式配置，如实际探针为 J-Link）。
    证据 2：已配置且存在的 CLI 工具按平台惯例排序选；零候选报错；
    无平台惯例且多候选报错（不猜）。
    返回 (tool, evidence_notes)；抛 FlashDetectError。
    """
    notes: list[str] = []
    ev = probe_uvoptx_evidence(ctx["workspace"], ctx["ide_project"])
    if ev is not None:
        tool, evdesc = ev
        info = resolve_flash_tool_path(ctx["config"], tool)
        if not info["path"]:
            raise FlashDetectError(
                f"uvoptx 调试器证据指向 {tool}（{evdesc}），但对应 CLI 工具不可用"
                f"（{info['note']}）——不猜。若实际探针与 IDE 工程配置不符"
                f"（如实际使用 J-Link 探针），请在项目 config.json 显式配置 "
                f"project.flash_tool（如 \"jlink\"）；或安装对应工具后重跑")
        notes.append(f"证据1（IDE 调试器配置）: {evdesc} → {tool}")
        return tool, notes

    order = _platform_tool_order(ctx)
    available: list[tuple[str, dict]] = []
    for t in (order or _PLATFORM_TOOL_ORDER_DEFAULT):
        info = resolve_flash_tool_path(ctx["config"], t)
        if info["path"]:
            available.append((t, info))
    if not available:
        raise FlashDetectError(
            "零候选：未从 uvoptx 解析到调试器证据，且无任何已配置可用的烧录 CLI"
            f"（候选: {' > '.join(order or _PLATFORM_TOOL_ORDER_DEFAULT)}）——"
            "请安装烧录工具并在全局 config.json 配置 tool_paths，"
            "或在项目 config.json 显式配置 project.flash_tool")
    if len(available) > 1 and order is None:
        cands = "、".join(f"{t}({i['note']})" for t, i in available)
        raise FlashDetectError(
            f"多候选且无平台惯例可排序: {cands}——不猜，"
            "请在项目 config.json 显式配置 project.flash_tool")
    tool, info = available[0]
    if len(available) > 1:
        notes.append("多工具可用，按平台惯例取最高优先级: "
                     + " > ".join(t for t, _ in available))
    notes.append(f"证据2（tool_paths 可用性 + 平台惯例）: {info['note']} → {tool}")
    return tool, notes


def determine_flash_tool(ctx: dict) -> tuple[str, list[str]]:
    """烧录工具判定（显式配置优先；null 时推断）。返回 (tool, evidence_notes)。"""
    tool = ctx["flash_tool_cfg"]
    if tool is not None:
        return tool, [f"显式配置 project.flash_tool = {tool!r}"]
    return infer_flash_tool(ctx)


# ---------------- Flash 内存布局来源链（复用 S7b，禁止两套规则） ----------------

_LD_FLASH_RE = re.compile(
    r"FLASH\b[^=\n]{0,80}?ORIGIN\s*=\s*(0x[0-9A-Fa-f]+)[\s\S]{0,120}?LENGTH\s*=\s*([^\s,}]+)",
    re.I)


def _parse_ld_length(s: str) -> int:
    s = s.strip()
    low = s.lower()
    if low.endswith("k"):
        return int(s[:-1], 0) * 1024
    if low.endswith("m"):
        return int(s[:-1], 0) * 1024 * 1024
    return int(s, 0)


def resolve_flash_layout(ctx: dict) -> tuple[tuple[int, int], str, list[str]] | None:
    """Flash 基址/容量来源链（与 S7b 链接脚本生成一致）：
    1. uvprojx IROM（复用 S7b makefile_gen.parse_uvprojx）
    2. 工程内 .ld 的 FLASH ORIGIN/LENGTH（无 uvprojx 时；ORIGIN 可能已含偏移，
       flash_offset>0 时由调用方警告）
    3. 平台惯例（makefile_gen.PLATFORM_FALLBACK，按 mcu_family）
    均无 → None（bin 需 --address，hex 跳过越界校验）。
    返回 ((base, size), 来源描述, warnings)。
    """
    target_root = ctx["workspace"]
    warnings: list[str] = []

    uvprojx = find_project_file(target_root, ctx["ide_project"], ".uvprojx")
    if uvprojx is not None:
        try:
            irom = parse_uvprojx(uvprojx, target_root).get("irom")
        except Exception as exc:  # makefile_gen 抛错类型不固定，降级下一来源
            warnings.append(f"uvprojx 解析失败（{exc}），降级 .ld/平台惯例")
            irom = None
        if irom:
            return (tuple(irom), f"uvprojx IROM（{uvprojx.name}）", warnings)

    for p in sorted(target_root.rglob("*.ld")):
        if {q.lower() for q in p.relative_to(target_root).parts[:-1]} & PROJECT_DISCOVER_EXCLUDE:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        m = _LD_FLASH_RE.search(text)
        if m:
            try:
                base, size = int(m.group(1), 16), _parse_ld_length(m.group(2))
            except ValueError:
                continue
            return (base, size), f".ld FLASH ORIGIN/LENGTH（{p.name}）", warnings

    plat = PLATFORM_FALLBACK.get(ctx["mcu_family"] or "")
    if plat:
        return tuple(plat["irom"]), f"平台惯例 PLATFORM_FALLBACK（{ctx['mcu_family']}）", warnings
    return None


# ---------------- hex 解析（intelhex 优先，内置解析器兜底） ----------------


def _parse_hex_records(hex_path: Path) -> dict[int, int] | None:
    """内置最小 Intel HEX 解析器：返回 {绝对地址: 字节值}。
    支持 00/01/04/05 记录类型（04 扩展线性地址累积）；校验和失败返回 None。
    """
    data_map: dict[int, int] = {}
    ext_base = 0
    try:
        text = hex_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(":"):
            if line:
                return None  # 非 hex 行 → 格式非法
            continue
        try:
            data = bytes.fromhex(line[1:])
        except ValueError:
            return None
        if len(data) < 5 or sum(data) & 0xFF:
            return None  # 校验和失败
        count, offset, rtype = data[0], (data[1] << 8) | data[2], data[3]
        payload = data[4:4 + count]
        if len(payload) != count:
            return None
        if rtype == 0x04:
            ext_base = int.from_bytes(payload, "big") << 16
        elif rtype == 0x00:
            for i, b in enumerate(payload):
                data_map[ext_base + offset + i] = b
        elif rtype == 0x01:
            break
        # 05（起始线性地址）/其他类型跳过
    return data_map or None


def _parse_hex_builtin(hex_path: Path) -> tuple[int, int] | None:
    """(首地址, 数据字节数)；_parse_hex_records 的指纹视图。"""
    data_map = _parse_hex_records(hex_path)
    if not data_map:
        return None
    return min(data_map), len(data_map)


def hex_image(hex_path: Path) -> tuple[int, bytes]:
    """hex → (基址, 连续镜像 bytes；间隙 0xFF 填充)。verifybin 校验镜像用
    （V7.54 Commander 无 verify 命令，hex 固件借 bin 镜像校验 flash 内容）。"""
    if intelhex_available():
        try:
            from intelhex import IntelHex
            ih = IntelHex(str(hex_path))
            addrs = ih.addresses()
            if addrs:
                return min(addrs), ih.tobinstr()  # tobinstr 缺省 0xFF 填充间隙
        except Exception:
            pass
    data_map = _parse_hex_records(hex_path)
    if not data_map:
        raise FlashPlanError(f"hex 文件解析失败（格式非法或校验和错误）: {hex_path}")
    base, end = min(data_map), max(data_map)
    return base, bytes(data_map.get(a, 0xFF) for a in range(base, end + 1))


def hex_fingerprint(hex_path: Path) -> tuple[int, int]:
    """hex 首地址与数据量：intelhex 优先（严格全文件校验），缺失时内置解析器兜底。

    返回 (首地址, 数据字节数)；两者均失败 → FlashPlanError（格式与内容不符）。
    """
    if intelhex_available():
        try:
            from intelhex import IntelHex
            ih = IntelHex(str(hex_path))
            addrs = ih.addresses()
            if addrs:
                first = min(addrs)
                return first, max(addrs) - first + 1
        except Exception:
            pass  # intelhex 解析失败 → 内置解析器再判
    fp = _parse_hex_builtin(hex_path)
    if fp is None:
        raise FlashPlanError(
            f"hex 文件解析失败（格式非法或校验和错误）: {hex_path}")
    return fp


# ---------------- 固件选择通道 ----------------

# S6 firmware-merger 产物字段探测（S6 未实现，字段名待 S6 落地校准；
# 语义：firmware.status == done 且下列任一路径字段指向存在文件时优先消费）
_S6_PATH_KEYS = ("merged_path", "firmware_path", "hex_path", "bin_path")
_S6_BASE_KEYS = ("merged_base_address", "base_address")


def _resolve_state_path(target_root: Path, value) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = target_root / p
    return p if p.is_file() else None


def locate_firmware(ctx: dict, opts: dict) -> dict:
    """固件选择通道：--firmware > S6 合并固件 > s7b hex > s7b bin（--format 强制）。

    release/ 永不作为发现来源——只走 state 指针与显式参数。
    返回 {source, format, path(源绝对路径), available: {hex: Path|None, bin: Path|None},
          s6_base: int|None}；抛 FlashPlanError（文件不存在/格式不符/参数缺失）。
    """
    state = ctx["state"]
    target_root = ctx["workspace"]
    available: dict[str, Path | None] = {"hex": None, "bin": None}

    def _fmt_of(p: Path) -> str:
        return p.suffix.lower().lstrip(".")

    # ---- 优先级 1：--firmware 显式（跳过 state 检查由调用方负责）----
    if opts.get("firmware"):
        p = Path(opts["firmware"]).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.is_file():
            raise FlashPlanError(f"--firmware 固件不存在: {p}")
        fmt = opts.get("format") or _fmt_of(p)
        if fmt not in ("hex", "bin"):
            raise FlashPlanError(f"无法判定固件格式（{p.name}，请用 --format hex|bin 指定）")
        if _fmt_of(p) not in ("hex", "bin", fmt):
            raise FlashPlanError(f"--format {fmt} 与文件后缀不符: {p.name}")
        if fmt == "hex":
            hex_fingerprint(p)  # 格式校验（非法即报错）
        return {"source": "manual", "format": fmt, "path": p,
                "available": {"hex": p if fmt == "hex" else None,
                              "bin": p if fmt == "bin" else None},
                "s6_base": None}

    # ---- 优先级 2：S6 合并固件（state.firmware done 时优先消费）----
    fw = state.get("firmware")
    if isinstance(fw, dict) and fw.get("status") == "done":
        for key in _S6_PATH_KEYS:
            p = _resolve_state_path(target_root, fw.get(key))
            if p is not None:
                fmt = opts.get("format") or _fmt_of(p)
                if fmt not in ("hex", "bin") or _fmt_of(p) != fmt:
                    raise FlashPlanError(
                        f"--format {fmt!r} 与 S6 固件格式不符: {p.name}")
                if fmt == "hex":
                    hex_fingerprint(p)
                s6_base = next((int(fw[k]) for k in _S6_BASE_KEYS
                                if isinstance(fw.get(k), int)), None)
                return {"source": "s6", "format": fmt, "path": p,
                        "available": {"hex": p if fmt == "hex" else None,
                                      "bin": p if fmt == "bin" else None},
                        "s6_base": s6_base}

    # ---- 优先级 3/4：s7b 产物（hex 优先，bin 兜底）----
    s7b = state.get("s7b") or {}
    hex_p = _resolve_state_path(target_root, s7b.get("hex_path"))
    bin_p = _resolve_state_path(target_root, s7b.get("bin_path"))
    fmt = opts.get("format") or ("hex" if hex_p else "bin")
    if fmt == "hex" and hex_p is not None:
        hex_fingerprint(hex_p)
        path = hex_p
    elif fmt == "bin" and bin_p is not None:
        path = bin_p
    else:
        want = {"hex": s7b.get("hex_path"), "bin": s7b.get("bin_path")}
        raise FlashPlanError(
            f"固件不可得：期望 {fmt} 格式，但 s7b.{fmt}_path = {want.get(fmt)!r}"
            "（不存在或为 null）——请重跑 S7b 或改用另一格式")
    return {"source": "s7b", "format": fmt, "path": path,
            "available": {"hex": hex_p, "bin": bin_p}, "s6_base": None}


# ---------------- release/ 发布同步（S9 是唯一写者） ----------------


def sync_release(ctx: dict, located: dict) -> dict:
    """已定位的全部格式发布同步到 release/（SHA256 现场计算比对）。

    副本 hash 与源一致 → 跳过复制记录"复用"；不一致或缺失 → 覆盖复制
    （重编译后旧副本自动刷新，杜绝旧固件残留）。不信任 flash_info.json 记录值。
    返回 {published: [{name, format, release_path(rel), release_abs, sha256, size,
    reused}], primary_release_abs, primary_release_rel, primary_sha256, primary_size}。
    """
    release_dir = ctx["release_dir"]
    release_dir.mkdir(parents=True, exist_ok=True)
    primary = located["path"]
    published: list[dict] = []
    for fmt in ("hex", "bin"):
        src = (located.get("available") or {}).get(fmt)
        if src is None:
            continue
        sha = sha256_file(src)
        size = src.stat().st_size
        dst = release_dir / src.name
        reused = False
        if dst.is_file():
            try:
                reused = sha256_file(dst) == sha
            except OSError:
                reused = False
        if not reused:
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
        published.append({
            "name": src.name, "format": fmt,
            "release_path": rel_posix(dst, ctx["project_root"]),
            "release_abs": dst, "sha256": sha, "size": size, "reused": reused,
        })
    primary_entry = next(e for e in published if e["release_abs"].name == primary.name)
    return {"published": published,
            "primary_release_abs": primary_entry["release_abs"],
            "primary_release_rel": primary_entry["release_path"],
            "primary_sha256": primary_entry["sha256"],
            "primary_size": primary_entry["size"]}


# ---------------- J-Link Commander 脚本与命令 ----------------


def render_jlink_script(device: str, interface: str, firmware_name: str,
                        address: int | None, verify: bool, reset: bool,
                        chip_erase: bool, verify_name: str | None,
                        verify_address: int | None) -> str:
    """渲染 release/flash_cmd.jlink（自包含：与固件同目录，相对引用，可交付复烧）。

    J-Link Commander V7.54 实测校准（命令表详见 references/jlink_flash_guide.md §3.2）：
    - CommandFile 不支持 '#' 注释行（逐行报 Unknown command）——脚本只含纯命令
    - 首行 connect 前置：吸收首次 USB 瞬态连接失败（实测无 connect 时首次连接
      FAILED、到后续命令才重试成功；connect 失败时后续命令同样会重试连接）
    - 无 verify 命令（裸/带参均 Unknown）——校验用 verifybin <bin> 0x<地址>，
      hex 固件由 plan_flash 派生 <stem>_verify.bin 镜像，bin 固件用自身
    命令序列（requirement §阶段 B 表）：connect → erase（--chip-erase 显式
    opt-in）→ loadfile <hex>（自带地址）/ loadfile <bin> <0x地址> → verifybin →
    r（复位）→ g（运行）→ qc（退出）。--no-verify 去 verifybin 行；--no-reset
    去 r+g（烧后不复位运行）。
    """
    if verify and (verify_name is None or verify_address is None):
        raise FlashPlanError("verifybin 校验需要镜像名与地址（plan_flash 派生，不应缺省）")
    lines = ["connect"]
    if chip_erase:
        lines.append("erase")
    if address is not None:  # bin：无地址信息，必须显式传
        lines.append(f"loadfile {firmware_name} 0x{address:08X}")
    else:                    # hex：自带地址与校验和，不传地址不易错位
        lines.append(f"loadfile {firmware_name}")
    if verify:
        lines.append(f"verifybin {verify_name} 0x{verify_address:08X}")
    if reset:
        lines.extend(["r", "g"])
    lines.append("qc")
    return "\n".join(lines) + "\n"


def build_jlink_command(jlink_exe: str, device: str, interface: str) -> list[str]:
    """J-Link Commander 命令行（cwd 必须为 release/，脚本内固件为相对引用）。"""
    return [jlink_exe, "-device", device, "-if", interface, "-speed", "4000",
            "-autoconnect", "1", "-CommandFile", "flash_cmd.jlink"]


# ---------------- 烧录日志解析（映射表见 references/flash_log_parse_rules.md） ----------------

_JLINK_LOG = {
    # 失败特征（V7.54 实测校准）：USB/目标连接失败、脚本命令错误、设备名错误、
    # 校验失败、通用错误。首次 USB 连接可能瞬态失败（connect 前置吸收重试），
    # 日志后文出现 USB O.K. 时连接失败行按瞬态降级不计致命（见 parse_jlink_log）。
    "failure": re.compile(
        r"(?i)cannot connect to j-link|cannot connect to target"
        r"|connecting to target[^\n]*failed|unknown command|unknown device"
        r"|device is unsupported|device name is ambiguous"
        r"|verification failed|verify[^\n]*failed|\berror\b|\bfailed\b"),
    # V7.54 实测：loadfile 打印 "Downloading file [xxx.hex]..."，随后打印
    # "J-Link: Flash download: Bank 0 @ 0x08000000: ..."（写入与
    # "Skipped. Contents already match" 跳过均打印该段头）
    "download": re.compile(r"(?i)downloading file \["),
    "program": re.compile(r"(?i)J-Link: Flash download: Bank \d+"),
    # V7.54 verifybin 实测成功输出（精确匹配）
    "verify_ok": re.compile(r"Verify successful\."),
    "verify_fail": re.compile(
        r"(?i)verify[^\n]*failed|verification failed|contents differ|data mismatch"),
    "usb_ok": re.compile(r"Connecting to J-Link via USB\.\.\.O\.K\."),
    "transient_usb": re.compile(
        r"(?i)connecting to j-link via usb\.\.\.failed|cannot connect to j-link"),
}
_JLINK_KEY_LINE = re.compile(
    r"(?i)downloading|writing|programming|comparing|verif|reset|connect"
    r"|flash download|already match|skipped|unknown command|\bfailed\b|\berror\b"
    r"|o\.k\.|script processing|unknown device|device\b.*selected")


def parse_jlink_log(text: str, exit_code: int | None, timed_out: bool,
                    verify: bool, reset_requested: bool) -> dict:
    """J-Link 成功判定（V7.54 实测校准；退出码 + 日志特征双条件——Commander 对
    脚本错误也可能退 0，日志特征是主判据）：
    成功 = 未超时 且 退出码 0 且 含 Downloading file 且 含 Flash download Bank 段
    且 无失败特征 且（verify 开启时含 Verify successful. 且无校验失败特征——
    verify 失败不算烧录成功）。
    瞬态处理：connect 前置后 USB 连接仍可能先失败后成功（后续命令重试连接），
    日志后文含 "Connecting to J-Link via USB...O.K." 时连接失败行不计致命。
    """
    failure_hits = [ln.strip() for ln in text.splitlines()
                    if _JLINK_LOG["failure"].search(ln)]
    if _JLINK_LOG["usb_ok"].search(text):
        failure_hits = [ln for ln in failure_hits
                        if not _JLINK_LOG["transient_usb"].search(ln)]
    has_download = bool(_JLINK_LOG["download"].search(text))
    has_program = bool(_JLINK_LOG["program"].search(text))
    verify_passed: bool | None = None
    if verify:
        verify_passed = bool(_JLINK_LOG["verify_ok"].search(text)) \
            and not bool(_JLINK_LOG["verify_fail"].search(text))
    success = (not timed_out) and exit_code == 0 and has_download and has_program \
        and not failure_hits and (verify_passed is not False)
    key_lines: list[str] = []
    for ln in text.splitlines():
        s = ln.rstrip()
        if s and _JLINK_KEY_LINE.search(s) and s not in key_lines:
            key_lines.append(s)
    return {
        "success": success,
        "verify_passed": verify_passed,
        # r 为 Commander 内建命令，脚本跑通即已执行（复位输出与 connect 后的
        # 初始化复位同段，无法从日志行严格区分——以成功+请求收口）
        "reset_done": bool(success and reset_requested),
        "failure_lines": failure_hits[:20],
        "key_lines": key_lines[:50],
    }


# ---------------- 设备名映射 ----------------


def map_jlink_device(platform: str) -> str | None:
    """platform 目录名 → J-Link 设备库命名（表与 references/jlink_flash_guide.md 同步；
    映射失败返回 None——报错要求 --device 显式指定，不猜）。"""
    return JLINK_DEVICE_MAP.get((platform or "").strip().lower())


# ---------------- 烧录计划（prepare / flash 共用单一实现） ----------------


def plan_flash(ctx: dict, opts: dict) -> dict:
    """完整烧录计划（单一实现，prepare.py 与 flash.py 共用）。

    opts: {firmware, format, address, device, interface, verify, reset, chip_erase}
    （firmware/format/address/device 为 None 表示按通道/映射缺省）。
    返回计划 dict（字段见实现尾部）；抛 FlashPlanError / FlashDetectError。
    """
    warnings: list[str] = []
    config = ctx["config"]
    offset = ctx["flash_offset"]

    # ---- 1. 平台与机制判定（mcu8 不推断；cortex_m 拒绝 vendor_ide）----
    if ctx["arch_family"] == "mcu8":
        raise FlashPlanError(
            "8 位平台（arch_family=mcu8）不自动推断烧录工具（厂家烧录器格式各异）"
            "——请显式配置 project.flash_tool（vendor_ide 或厂家烧录器 CLI 值；"
            "GUI 烧录机制为五期演进项）")
    if ctx["flash_tool_cfg"] == "vendor_ide":
        raise FlashPlanError(
            "flash_tool=vendor_ide 仅用于厂家自研 IDE 无 CLI 的 8 位平台（GUI 机制，"
            "五期演进项）；Cortex-M 的 J-Link/ST-Link/OpenOCD/pyOCD 均有 CLI")

    # ---- 2. 烧录工具判定（显式优先；null 推断）+ 一期范围门（仅 jlink 全链路）----
    tool, evidence = determine_flash_tool(ctx)
    warnings.extend(evidence)
    if tool != "jlink":
        raise FlashPlanError(
            f"flash_tool={tool!r} 为演进项（一期仅支持 jlink 全链路）——"
            f"请在项目 config.json 显式配置 project.flash_tool = \"jlink\""
            f"（jflash .jflash 决策流程为二期；stlink/openocd/pyocd 为三/四期；"
            f"vendor_ide GUI 机制为五期）")
    tool_info = resolve_flash_tool_path(config, "jlink")
    if not tool_info["path"]:
        raise FlashPlanError(
            "烧录工具 JLink.exe 缺失：" + tool_info["note"]
            + "——烧录工具完全由用户自管理（S9 不自动安装），请参考 "
            "skills/flash/references/jlink_flash_guide.md 手动安装"
            "（SEGGER 官网 https://www.segger.com/downloads/jlink/）"
            "并在全局 config.json 配置 tool_paths.jlink（或 tool_paths.jflash，"
            "本技能会从其同目录探测 JLink.exe）")

    interface = opts.get("interface") or "SWD"
    if interface not in ("SWD", "JTAG"):
        raise FlashPlanError(f"非法接口 {interface!r}（可选 SWD/JTAG）")

    # ---- 3. 固件定位 + 格式校验 + 指纹 ----
    located = locate_firmware(ctx, opts)
    fw_path = located["path"]
    fw_size = fw_path.stat().st_size
    if fw_size == 0:
        raise FlashPlanError(f"固件大小为 0: {fw_path}")
    if located["format"] == "bin":
        fw_first: int | None = None
        fw_span = fw_size
    else:
        fw_first, fw_span = hex_fingerprint(fw_path)

    # ---- 4. Flash 布局 + 目标地址（flash_offset 唯一权威）----
    layout = resolve_flash_layout(ctx)
    base = cap = None
    if layout is not None:
        (base, cap), lsource, lnotes = layout
        warnings.extend(lnotes)
        if offset > 0:
            plat = PLATFORM_FALLBACK.get(ctx["mcu_family"] or "")
            if plat and base != plat["irom"][0]:
                warnings.append(
                    f"Flash 基址 0x{base:08X}（来源：{lsource}）已非平台惯例基址 "
                    f"0x{plat['irom'][0]:08X}，且 flash_offset=0x{offset:X}——"
                    "请确认未对同一偏移重复叠加（疑似双重偏移）")
            if ".ld" in lsource:
                warnings.append(
                    f"Flash 基址来自 .ld ORIGIN（{lsource}）——链接脚本可能已含偏移，"
                    "请核对目标地址未重复叠加 flash_offset")
    else:
        warnings.append("Flash 基址/容量无法从工程文件与平台惯例解析——"
                        "跳过越界校验（bin 需 --address 显式指定）")
    if offset % 0x200 != 0:
        warnings.append(
            f"flash_offset=0x{offset:X} 非 512 字节对齐——Cortex-M VTOR 通常要求"
            "向量表 512 字节对齐（M3）或 128 字节（M4），未对齐将导致中断异常"
            "（与 S7b 同判据）")

    addr_override = opts.get("address")
    source, fmt = located["source"], located["format"]
    address_arg: int | None = None   # 传给烧录工具的地址（hex 为 None：自带地址）
    target_address: int | None = fw_first

    if fmt == "hex":
        # hex 自带地址（S7b 链接已偏移），不传地址；防御性起址校验
        if offset > 0 and base is not None:
            expected = base + offset
            if fw_first == base:
                warnings.append(
                    f"hex 首地址 0x{fw_first:08X} 等于裸 Flash 基址，但 flash_offset="
                    f"0x{offset:X}——疑似未偏移固件（S7b 链接脚本未应用偏移？），"
                    "请核对后重跑 S7b")
            elif fw_first != expected:
                warnings.append(
                    f"hex 首地址 0x{fw_first:08X} 与期望 flash_base+offset="
                    f"0x{expected:08X} 不一致——请核对固件链接布局")
    else:
        # bin：显式地址必填/按规则计算
        if source == "manual":
            if addr_override is None:
                raise FlashPlanError("--firmware 指定 bin 固件时必须配合 --address <0x...>"
                                     "（无来源信息，用户负责地址）")
            address_arg = addr_override
        elif source == "s6":
            if addr_override is not None:
                address_arg = addr_override
            elif located.get("s6_base") is not None:
                address_arg = located["s6_base"]  # S6 state 记录的合并基址优先
            elif base is not None:
                address_arg = base  # 合并固件从基址起含 Boot，不应用 flash_offset
            else:
                raise FlashPlanError("S6 合并 bin 无法确定烧录基址（无 --address、"
                                     "S6 state 基址与 Flash 布局均缺失）")
        else:  # s7b 单 App 固件：flash_base + flash_offset
            if addr_override is not None:
                address_arg = addr_override
            elif base is not None:
                address_arg = base + offset
            else:
                raise FlashPlanError(
                    "s7b bin 烧录地址无法计算（Flash 基址来源链均无：uvprojx IROM / "
                    ".ld ORIGIN / 平台惯例）——请修复工程文件或用 --address 显式指定")
        target_address = address_arg

    # 越界校验（flash_base + flash_offset + 固件大小 ≤ Flash 容量；报错即拦截）
    if base is not None and cap is not None and target_address is not None:
        end = target_address + fw_span
        if target_address < base:
            warnings.append(f"烧录地址 0x{target_address:08X} 低于 Flash 基址 "
                            f"0x{base:08X}——请核对地址")
        if end > base + cap:
            raise FlashPlanError(
                f"固件越界：目标地址 0x{target_address:08X} + 大小 0x{fw_span:X} = "
                f"0x{end:08X} 超出 Flash 末尾 0x{base + cap:08X}（容量 0x{cap:X}，"
                f"flash_offset=0x{offset:X}）——请检查 flash_offset 配置或固件")

    # ---- 5. 设备名推断（--device 兜底；映射失败不猜）----
    device = opts.get("device") or map_jlink_device(ctx["platform"])
    if not device:
        raise FlashPlanError(
            f"平台 {ctx['platform']!r} 无法映射为 J-Link 设备名（映射表见 "
            f"references/jlink_flash_guide.md，一期校准 {'/'.join(JLINK_DEVICE_MAP)}）"
            "——请用 --device 显式指定（J-Link 设备库命名，如 STM32F103ZE）")

    # ---- 6. release/ 发布同步（SHA256 现场比对）----
    rel = sync_release(ctx, located)
    for e in rel["published"]:
        action = "复用（hash 一致）" if e["reused"] else "覆盖复制（hash 不一致或首次发布）"
        warnings.append(f"release/{e['name']}: {action}")

    # ---- 6.5 verifybin 校验镜像（V7.54 无 verify 命令，hex 需派生 bin 镜像）----
    verify = bool(opts.get("verify", True))
    verify_name: str | None = None
    verify_address: int | None = None
    verify_image_abs: Path | None = None
    if verify:
        if fmt == "bin":
            verify_name = rel["primary_release_abs"].name   # bin 自身即校验镜像
            verify_address = address_arg                    # bin 烧录地址必非 None
        else:
            img_base, img_bytes = hex_image(rel["primary_release_abs"])
            verify_name = rel["primary_release_abs"].stem + "_verify.bin"
            verify_image_abs = ctx["release_dir"] / verify_name
            verify_image_abs.write_bytes(img_bytes)
            verify_address = img_base
            warnings.append(
                f"release/{verify_name}: 由 hex 派生校验镜像（{len(img_bytes)} 字节 "
                f"@ 0x{img_base:08X}；间隙按 0xFF 比对，hex 含空洞且残留数据时会"
                "校验失败——可加 --chip-erase 全片擦除后再烧）")

    # ---- 7. flash_cmd.jlink 脚本生成（每次按当前选项覆盖）----
    script_abs = ctx["release_dir"] / "flash_cmd.jlink"
    script_abs.write_text(
        render_jlink_script(device, interface, rel["primary_release_abs"].name,
                            address_arg, verify, opts.get("reset", True),
                            opts.get("chip_erase", False), verify_name,
                            verify_address),
        encoding="utf-8", newline="\n")

    return {
        "flash_tool": "jlink",
        "flash_mode": "cli",
        "tool_path": tool_info["path"],
        "tool_note": tool_info["note"],
        "firmware": {
            "source": source, "format": fmt,
            "path": str(fw_path),
            "release_path": rel["primary_release_rel"],
            "release_abs": rel["primary_release_abs"],
            "name": rel["primary_release_abs"].name,
            "size": rel["primary_size"],
            "sha256": rel["primary_sha256"],
            "target_address": target_address,
            "address_arg": address_arg,
        },
        "published": rel["published"],
        "device": device,
        "interface": interface,
        "verify": verify,
        "verify_image": None if not verify else {
            "name": verify_name,
            "address": verify_address,
            "path": None if verify_image_abs is None
                    else rel_posix(verify_image_abs, ctx["project_root"]),
        },
        "reset": bool(opts.get("reset", True)),
        "chip_erase": bool(opts.get("chip_erase", False)),
        "script_path": rel_posix(script_abs, ctx["project_root"]),
        "script_abs": script_abs,
        "cmd": build_jlink_command(tool_info["path"], device, interface),
        "cmd_cwd": ctx["release_dir"],
        "warnings": warnings,
    }
