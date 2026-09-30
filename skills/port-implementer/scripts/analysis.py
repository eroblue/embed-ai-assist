"""S5c port-implementer 确定性分析共享模块（rule 轨，全脚本共用）。

职责边界（与 S5a/S5b 同策略：rule 只做确定性契约工作，Port/OSAL/Power
适配代码生成归 Agent/LLM）：
- 分层配置加载、S5a/S5b 就绪与一致性检查（防漂移）、设计输入段解析、
  能力缺口机械比对（manifest 需求 × hardware_capabilities 供给）、
  旧平台/旧 RTOS 残留检测（skip-if-modified 哈希比对）、
  manifest 接口索引提取（validate 接口全覆盖检查用）。
- 本模块不生成任何 C 代码。

实现依据：S5c requirement §输入/§输出/§执行步骤。硬件只依据
outputs/s5a/hardware_capabilities.json，接口只依据
outputs/s5b/port_interface_manifest.json（禁止硬解析 C 头文件、
禁止直接读取 S3/S4 数据）。
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

# ---------------- JSON / 配置工具（与 S5a/S5b analysis 同模式，skill 间不耦合） ----------------

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


# ---------------- 命名规范化 ----------------

def slug_token(name: str) -> str:
    """平台/外设标识 → 文件命名 token：小写，非 [a-z0-9] 字符去除。"""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def rtos_token(rtos: str) -> str:
    """RTOS → 文件命名 token：全小写、连字符/空格/下划线去除。

    FreeRTOS→freertos；RT-Thread→rtthread；Zephyr→zephyr（requirement 命名规范）。
    """
    return slug_token(rtos)


def impl_file_name(peripheral: str, platform_token: str) -> str:
    return f"port_impl_{slug_token(peripheral)}_{platform_token}.c"


def osal_impl_file_name(rtos: str) -> str:
    return f"port_impl_osal_{rtos_token(rtos)}.c"


def power_impl_file_name(platform_token: str) -> str:
    return f"port_impl_power_{platform_token}.c"


# port_impl 文件分类（残留清理 / 状态收集共用）
_IMPL_RE = re.compile(r"^port_impl_(osal|power|[a-z0-9]+?)_([a-z0-9]+)\.c$")


def classify_impl_file(name: str, platform_token: str, rtos: str) -> dict | None:
    """port_impl 文件名 → {kind, token, current}；非 port_impl_*.c 返回 None。

    kind：peripheral=外设实现；osal=OSAL 实现；power=低功耗实现
    token：外设名 / rtos token / 平台 token
    current：是否属于当前平台/当前 RTOS（False = 换平台/换 RTOS 残留，清理候选）
    """
    m = _IMPL_RE.match(name)
    if not m:
        return None
    kind_a, token = m.group(1), m.group(2)
    if kind_a == "osal":
        return {"kind": "osal", "token": token,
                "current": token == rtos_token(rtos)}
    if kind_a == "power":
        return {"kind": "power", "token": token,
                "current": token == platform_token}
    return {"kind": "peripheral", "peripheral": kind_a, "token": token,
            "current": token == platform_token}


# ---------------- 文件哈希（skip-if-modified） ----------------

def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_file_hashes(s5c_outputs_dir: Path) -> dict:
    """读 outputs/s5c/file_hashes.json → {rel: sha256}；不存在返回空 dict。"""
    path = s5c_outputs_dir / "file_hashes.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
        return data.get("files") or {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_file_hashes(s5c_outputs_dir: Path, files: dict) -> None:
    save_json(s5c_outputs_dir / "file_hashes.json",
              {"files": files,
               "generated_at": datetime.now().isoformat(timespec="seconds")})


# ---------------- S5c 执行上下文 ----------------

def load_context(config_path: Path, workspace: Path | None = None) -> dict:
    """加载配置 + S5a/S5b 就绪与一致性检查，返回 S5c 执行上下文。

    抛 RuntimeError（prepare/validate 转为 state error，退出码 2）：
    - state.json / s5a / s5b 缺失，或 S5a/S5b 未完成
    - s5a 与 s5b 的 rtos/architecture/power_enabled 不一致（防漂移）
    - manifest / hardware_capabilities 缺失（S5c 的两个唯一依据）
    """
    config, _notes = load_layered_config(config_path)
    cfg_errors = validate_schema(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        raise RuntimeError("配置契约校验失败: " + "; ".join(cfg_errors))
    if workspace is None:
        workspace = config_path.parent
    project_root = workspace
    workspace = resolve_target(config, project_root)
    state_path = workspace / "state.json"
    if not state_path.exists():
        raise RuntimeError(f"state.json 不存在: {state_path}（先执行 S1 建立工作区）")
    state = load_json(state_path)

    input_errors = validate_schema(state, SKILL_DIR / "schemas" / "input.schema.json", "state")
    if input_errors:
        raise RuntimeError("输入契约校验失败: " + "; ".join(input_errors))

    s5a = state.get("s5a") or {}
    s5b = state.get("s5b") or {}

    # ---- 就绪检查：S5a 与 S5b 都完成后触发 ----
    if s5a.get("status") != "done":
        raise RuntimeError(f"S5a 未完成（s5a.status={s5a.get('status', 'missing')}），"
                           "先执行 S5a hardware-initializer")
    if s5b.get("status") != "done":
        raise RuntimeError(f"S5b 未完成（s5b.status={s5b.get('status', 'missing')}），"
                           "先执行 S5b port-contract-and-app")

    # ---- 一致性检查（防漂移，requirement 阶段 A 步骤 3）----
    consistency_errors: list[str] = []
    for key, label in (("rtos", "RTOS"), ("architecture", "架构"),
                       ("power_enabled", "低功耗")):
        va, vb = s5a.get(key), s5b.get(key)
        if va is not None and vb is not None and va != vb:
            consistency_errors.append(
                f"{label}不一致：s5a={va!r}，s5b={vb!r}"
                "——有 Skill 是旧配置跑的，重跑其中一方使配置对齐")
    if consistency_errors:
        raise RuntimeError("S5a/S5b 配置一致性检查失败: " + "; ".join(consistency_errors))

    # ---- 当前 config 与 state 的漂移（警告不终止，任务书登记）----
    project_cfg = config.get("project") or {}
    drift_warnings: list[str] = []
    for key, cur, label in (
            ("rtos", project_cfg.get("rtos") or "none", "RTOS"),
            ("architecture", project_cfg.get("architecture") or "layered", "架构"),
            ("power_enabled", (project_cfg.get("power") or {}).get("enabled", False), "低功耗")):
        if key in s5b and s5b[key] != cur:
            drift_warnings.append(
                f"{label}漂移：当前 config={cur!r}，S5a/S5b state={s5b[key]!r}"
                "——本 Skill 按 state 生成；如需切换配置请重跑 S5a/S5b/S5c")

    # ---- 两个唯一依据：manifest + hardware_capabilities ----
    outputs_dir = workspace / (config.get("output_dir") or "outputs").rstrip("/\\")
    manifest_rel = s5b.get("port_manifest") or "outputs/s5b/port_interface_manifest.json"
    manifest_path = workspace / manifest_rel
    if not manifest_path.is_file():
        raise RuntimeError(f"S5b 接口契约不存在: {manifest_rel}（重跑 S5b）")
    caps_rel = s5a.get("hardware_capabilities") or "outputs/s5a/hardware_capabilities.json"
    caps_path = workspace / caps_rel
    if not caps_path.is_file():
        raise RuntimeError(f"S5a 硬件能力清单不存在: {caps_rel}（重跑 S5a）")

    # ---- 平台标识（文件命名后缀）：s5c.platform > platform > project.target ----
    s5c_cfg = config.get("s5c") or {}
    platform_raw = (s5c_cfg.get("platform")
                    or config.get("platform")
                    or project_cfg.get("target") or "")
    if not platform_raw:
        raise RuntimeError("平台标识缺失：config 需有 s5c.platform 或 platform"
                          "（用于 port_impl_<外设>_<平台>.c 文件命名）")
    platform_token = slug_token(platform_raw)

    inputs_cfg = project_cfg.get("inputs") or {}
    return {
        "config": config,
        "workspace": workspace,          # 目标工程根 <项目根>/<build_target>/
        "project_root": project_root,    # 项目根（docs/ 等共享资源）
        "state_path": state_path,
        "state": state,
        "outputs_dir": outputs_dir,
        "architecture": s5b.get("architecture") or "layered",
        "rtos": s5b.get("rtos") or "none",
        "power_enabled": bool(s5b.get("power_enabled")),
        "language": (config.get("project") or {}).get("language") or "c99",
        "platform": platform_raw,
        "platform_token": platform_token,
        "hal_framework": s5c_cfg.get("hal_framework") or "",
        "manifest": load_json(manifest_path),
        "manifest_path": manifest_path,
        "manifest_rel": manifest_rel,
        "capabilities": load_json(caps_path),
        "capabilities_path": caps_path,
        "capabilities_rel": caps_rel,
        "design_input": load_design_input(
            project_root, inputs_cfg.get("s5c_design_input") or "docs/s5c_design_input.md"),
        "inputs": {
            "s5c_design_input": inputs_cfg.get("s5c_design_input") or "docs/s5c_design_input.md",
            "demos": inputs_cfg.get("demos") or [],
            "sdk": inputs_cfg.get("sdk") or "",
            "existing_project": inputs_cfg.get("existing_project") or "",
            "ide_project": inputs_cfg.get("ide_project") or "",
        },
        "s5a": s5a,
        "s5b": s5b,
        "drift_warnings": drift_warnings,
    }


# ---------------- 用户设计输入（docs/s5c_design_input.md） ----------------

_KNOWN_SECTIONS = ("低功耗方案", "已有实现")


def design_input_file_hash(project_root: Path,
                           rel_path: str = "docs/s5c_design_input.md") -> str | None:
    """设计输入文件的 sha256（不存在返回 None）。

    作为 port_differ 的**第三个判定维度**：设计输入不参与 manifest 签名 diff，
    但会影响实现约束（缓冲大小/命名风格等），变化时需提示用户确认受影响单元。
    """
    path = project_root / rel_path
    if not path.is_file():
        return None
    return file_sha256(path)


def load_design_input(project_root: Path, rel_path: str = "docs/s5c_design_input.md") -> dict | None:
    """读取 s5c_design_input.md，按二级标题拆段。

    返回 {path, sections: {段名: [行]}, has_content}；文件不存在、内容为空或
    全部为 none → None（Agent 基于 hardware_capabilities 与参考材料自主判断）。
    """
    path = project_root / rel_path
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if m:
            title = m.group(1)
            current = None
            for known in _KNOWN_SECTIONS:
                if title.startswith(known):
                    current = known
                    sections.setdefault(current, [])
                    break
            continue
        if current is not None and line.strip():
            sections[current].append(line.rstrip())
    has_content = any(
        any(not re.fullmatch(r"-\s*none", ln.strip(), re.I) for ln in lines)
        for lines in sections.values())
    if not has_content:
        return None
    return {"path": rel_path, "sections": sections, "has_content": True}


# ---------------- manifest 接口索引 ----------------

def manifest_peripheral_headers(manifest: dict) -> list[dict]:
    """manifest 中 kind=peripheral 的头条目（每个外设一个 port_impl 文件）。"""
    return [h for h in manifest.get("headers", []) if h.get("kind") == "peripheral"]


def manifest_interface_index(manifest: dict) -> dict[str, list[str]]:
    """{peripheral: [接口函数名]}（validate 接口全覆盖检查用）。

    peripheral 取头条目的 peripheral 字段（manifest 数据侧，不硬解析 C 头）。
    """
    index: dict[str, list[str]] = {}
    for h in manifest_peripheral_headers(manifest):
        periph = slug_token(h.get("peripheral") or "")
        if not periph:
            continue
        fns = [i.get("function") for i in h.get("interfaces", []) if i.get("function")]
        index.setdefault(periph, []).extend(fns)
    return index


# ---------------- 能力缺口机械比对（requirement 阶段 A 步骤 4） ----------------

def check_capability_gaps(manifest: dict, capabilities: dict,
                          capabilities_rel: str) -> dict:
    """manifest 硬件需求 × hardware_capabilities 供给 的机械比对。

    - 外设类型级比对：manifest 每个外设 Port 的类型（uart/gpio/adc/...）
      须出现在 capabilities.peripherals[].type 中，否则 error 级缺口
      （S5c prepare 输出 capability_gap.json 并终止，退出码 2）。
    - 低功耗：power_enabled 且 capabilities.power 缺失 → error 级缺口。
    - hw_instance=null 的实例：类型级通过即不报缺（实例选定是 Agent 职责，
      见 manifest notes "由 S5c 按 hardware_capabilities 匹配"）。
    """
    gaps: list[dict] = []
    supply_types: set[str] = set()
    for p in capabilities.get("peripherals") or []:
        t = slug_token(p.get("type") or "")
        if t:
            supply_types.add(t)
    supply_degraded = not supply_types

    for h in manifest_peripheral_headers(manifest):
        periph = slug_token(h.get("peripheral") or "")
        if not periph:
            continue
        req = f"manifest {h.get('file')}（{h.get('description') or ''}）"
        if periph in supply_types:
            continue
        instances = [i.get("name") for i in h.get("logical_instances", [])]
        detail = (f"能力清单 peripherals 为空/未提供该类型（数据退化？），"
                  f"manifest 需要 {periph} 类型能力" if supply_degraded
                  else f"能力清单提供的类型为 {sorted(supply_types)}，不含 {periph}")
        gaps.append({
            "requirement": req,
            "peripheral": periph,
            "needed": f"{periph} 类型能力（逻辑实例: {', '.join(x for x in instances if x) or '-'}）",
            "available": False,
            "detail": detail + "——修复回 S5a（补全 hardware_capabilities.json）或 S5b（调整 manifest），不得降级实现",
            "severity": "error",
            "source": "rule",
        })

    if capabilities.get("power") is None and capabilities.get("power_enabled") is True:
        gaps.append({
            "requirement": "manifest/配置启用低功耗，S5c 需生成 port_impl_power 实现",
            "peripheral": "power",
            "needed": "低功耗能力段（modes/wakeup_sources）",
            "available": False,
            "detail": "power_enabled=true 但能力清单未提供 power 能力段"
                      "——重跑 S5a（power_init + capabilities.power）",
            "severity": "error",
            "source": "rule",
        })
    return {"checked": True, "checked_against": capabilities_rel, "gaps": gaps}


# ---------------- 残留清理与用户修改检测（requirement 阶段 A 步骤 6） ----------------

def scan_impl_files(workspace: Path, src_dirs: list[Path], platform_token: str,
                    rtos: str, recorded_hashes: dict) -> dict:
    """扫描 S5c 产物目录的 port_impl 文件，分类残留/用户修改。

    返回 {current: [...], stale: [...], user_modified: [...], foreign: [...]}
    （rel 路径，POSIX 分隔，相对目标工程根）
    - current：当前平台/RTOS 的实现文件（保留；其中哈希 != 上轮记录 = 用户改过）
    - stale：非当前平台/RTOS 的 port_impl 残留且未被用户修改（prepare 删除）
    - user_modified：current 且 sha256 与上轮记录不一致（任务书标注跳过重写）
    - foreign：port_impl_* 之外或不可解析命名的 .c 文件（不动，交用户处理）
    首跑（无记录）全部视为"未改过"（正常清理/正常重生成）。
    """
    current: list[str] = []
    stale: list[str] = []
    user_modified: list[str] = []
    foreign: list[str] = []

    def _rel(p: Path) -> str:
        return str(p.resolve().relative_to(workspace)).replace("\\", "/")

    for d in src_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.c")):
            rel = _rel(f)
            info = classify_impl_file(f.name, platform_token, rtos)
            if info is None:
                if f.name.startswith("port_impl_"):
                    foreign.append(rel)
                continue
            if not info["current"]:
                recorded = recorded_hashes.get(rel)
                if recorded is not None and recorded != file_sha256(f):
                    user_modified.append(rel)  # 残留文件但被用户改过：保留并跳过
                else:
                    stale.append(rel)
            else:
                current.append(rel)
                recorded = recorded_hashes.get(rel)
                if recorded is not None and recorded != file_sha256(f):
                    user_modified.append(rel)
    return {"current": current, "stale": stale, "user_modified": user_modified,
            "foreign": foreign}


# ================= per-peripheral 增量机制（requirement"生成模式总览"） =================

# 变化率阈值（对标 S5b flow_differ：> 60% 判大重构走全量）
FULL_RATIO_THRESHOLD = 0.60


def manifest_units(manifest: dict) -> dict[str, dict]:
    """manifest → {实现单元键: {kind, header}}。

    单元键：peripheral 外设取 slug(peripheral)；osal / power 按 kind 取同名键
    （一个单元 = 一个 port_impl 文件 = 一次 per-peripheral 判定）。
    """
    units: dict[str, dict] = {}
    for h in manifest.get("headers", []):
        kind = h.get("kind") or "peripheral"
        if kind == "peripheral":
            key = slug_token(h.get("peripheral") or "")
        else:
            key = kind
        if not key:
            continue
        units[key] = {"kind": kind, "header": h}
    return units


def manifest_unit_file(unit_key: str, kind: str, platform_token: str, rtos: str) -> str:
    """实现单元 → 期望实现文件名。"""
    if kind == "osal":
        return osal_impl_file_name(rtos)
    if kind == "power":
        return power_impl_file_name(platform_token)
    return impl_file_name(unit_key, platform_token)


def unit_fields(header: dict, kind: str) -> list[str]:
    """manifest 单元 → 规范化原子字段集（签名 diff 与变化率的计算粒度）。

    原子格式 `类别:名称|属性`（集合语义，顺序无关）：
      instance:<名>|<描述> / hw:<名>|<hw_instance> / config:<名>.<键>=<值>
      iface:<函数名>|<签名> / iface_isr|iface_cb|iface_desc:<函数名>|<属性>
      callback|callback_ctx|callback_desc:<回调名>|<属性>
      note:<文本>
    """
    fields: list[str] = []
    for inst in header.get("logical_instances") or []:
        nm = inst.get("name") or ""
        fields.append(f"instance:{nm}|{inst.get('description') or ''}")
        hw = inst.get("hw_instance")
        fields.append(f"hw:{nm}|{hw if hw is not None else ''}")
        cfg = inst.get("config") or {}
        for k in sorted(cfg):
            fields.append(f"config:{nm}.{k}={cfg[k]}")
    for i in header.get("interfaces") or []:
        fn = i.get("function") or ""
        fields.append(f"iface:{fn}|{i.get('signature') or ''}")
        fields.append(f"iface_isr:{fn}|{1 if i.get('isr_safe') else 0}")
        fields.append(f"iface_cb:{fn}|{i.get('callback') or ''}")
        fields.append(f"iface_desc:{fn}|{i.get('description') or ''}")
    for cb in header.get("callbacks") or []:
        nm = cb.get("name") or ""
        fields.append(f"callback:{nm}|{cb.get('signature') or ''}")
        fields.append(f"callback_ctx:{nm}|{cb.get('context') or ''}")
        fields.append(f"callback_desc:{nm}|{cb.get('description') or ''}")
    for n in header.get("notes") or []:
        fields.append(f"note:{n}")
    return sorted(set(fields))


def unit_signature(header: dict, kind: str) -> dict:
    """单元签名摘要（port_manifest_snapshot.json 的条目结构）。"""
    fields = unit_fields(header, kind)
    return {
        "kind": kind,
        "signature_hash": hashlib.sha256("\n".join(fields).encode("utf-8")).hexdigest(),
        "instances": [i.get("name") for i in (header.get("logical_instances") or [])
                      if i.get("name")],
        "interface_count": len(header.get("interfaces") or []),
        "callback_count": len(header.get("callbacks") or []),
        "fields": fields,
    }


def _atom_key(atom: str) -> tuple[str, str]:
    """原子字段 → (变化类别, 名称)，用于 add/remove 配对成 modified。"""
    head, _, _detail = atom.partition("|")
    cat, _, name = head.partition(":")
    if cat in ("iface", "iface_isr", "iface_cb", "iface_desc"):
        return "interface", name
    if cat in ("callback", "callback_ctx", "callback_desc"):
        return "callback", name
    if cat in ("instance", "hw"):
        return "instance", name
    if cat == "config":
        # config 原子独立成类：与 instance 同键会把"删一个 config 键"误报为
        # instance_removed（逻辑实例其实还在），误导 Agent 删实例
        return "config", name.split(".")[0]
    if cat == "note":
        return "note", ""
    return "other", name


def diff_unit_fields(prev_fields: list[str], curr_fields: list[str]) -> dict:
    """原子字段集 diff → {changes, change_count, change_rate, added, removed}。

    配对：同类别同名的原子若一方 added、一方 removed → 归为 *_modified
    （避免"签名改一个字段"被算成删+增两个变更点）。

    change_count：配对后的**变更点数**（任务书展示 + 增量范围校验的预期基数）。
    change_rate：按 requirement 口径 —— **有增/删/改的字段数 ÷ 当前字段总数**
    （字段=原子属性；阈值见 FULL_RATIO_THRESHOLD，> 60% 判 full）。
    """
    prev_set, curr_set = set(prev_fields or []), set(curr_fields or [])
    added = sorted(curr_set - prev_set)
    removed = sorted(prev_set - curr_set)

    add_by: dict[tuple[str, str], list[str]] = {}
    for a in added:
        add_by.setdefault(_atom_key(a), []).append(a)
    rem_by: dict[tuple[str, str], list[str]] = {}
    for r in removed:
        rem_by.setdefault(_atom_key(r), []).append(r)

    changes: list[dict] = []
    for key in sorted(set(add_by) | set(rem_by)):
        cat, name = key
        a_list, r_list = add_by.get(key, []), rem_by.get(key, [])
        if cat == "config":
            keys = sorted({x.partition("|")[0].split(":", 1)[-1].split("=")[0]
                           .split(".", 1)[-1] for x in a_list + r_list})
            changes.append({"type": "config_changed", "name": name or None,
                            "field": "/".join(f"config.{k}" for k in keys),
                            "detail": f"{len(r_list)} 项旧配置 → {len(a_list)} 项新配置"})
        elif cat == "note":
            changes.append({"type": "note_changed", "name": None, "field": None,
                            "detail": f"{len(a_list) + len(r_list)} 条说明变化"})
        elif cat == "other":
            changes.append({"type": "other", "name": name or None, "field": None,
                            "detail": None})
        elif a_list and r_list:
            fields_changed = sorted({x.partition("|")[0].partition(":")[0]
                                     for x in a_list + r_list})
            changes.append({"type": f"{cat}_modified", "name": name or None,
                            "field": "/".join(fields_changed),
                            "detail": f"{len(r_list)} 项旧属性 → {len(a_list)} 项新属性"})
        elif a_list:
            changes.append({"type": f"{cat}_added", "name": name or None,
                            "field": None, "detail": None})
        else:
            changes.append({"type": f"{cat}_removed", "name": name or None,
                            "field": None, "detail": None})
    return {
        "changes": changes,
        "change_count": len(changes),
        # 变化率按 requirement 口径：有增/删/改的字段数 ÷ 当前字段总数
        "change_rate": round((len(added) + len(removed)) / max(len(curr_set), 1), 4),
        "added": len(added),
        "removed": len(removed),
    }


def load_manifest_snapshot(s5c_outputs_dir: Path) -> dict | None:
    """读 outputs/s5c/port_manifest_snapshot.json；不存在/损坏返回 None（首跑）。"""
    path = s5c_outputs_dir / "port_manifest_snapshot.json"
    if not path.is_file():
        return None
    try:
        return load_json(path)
    except (json.JSONDecodeError, OSError):
        return None


def save_manifest_snapshot(s5c_outputs_dir: Path, snapshot: dict) -> None:
    """写 manifest 快照（下轮 diff 基线）；**manifest 真变了**才把旧版追加到
    `*_history/` 保留回溯（同 hash 重复写入不产生历史堆积）。

    requirement：不修改历史版本（只追加新版本）。
    """
    path = s5c_outputs_dir / "port_manifest_snapshot.json"
    if path.is_file():
        try:
            old = load_json(path)
            if old.get("manifest_hash") != snapshot.get("manifest_hash"):
                stamp = re.sub(r"[^0-9A-Za-z]", "",
                               str(old.get("captured_at") or "unknown"))
                hist_dir = s5c_outputs_dir / "port_manifest_snapshot_history"
                hist_dir.mkdir(parents=True, exist_ok=True)
                hist = hist_dir / f"{stamp or 'unknown'}.json"
                if not hist.is_file():
                    save_json(hist, old)
        except (json.JSONDecodeError, OSError):
            pass
    save_json(path, snapshot)


def mirror_code_baseline(s5c_outputs_dir: Path, workspace: Path,
                         src_dirs: list[Path]) -> dict:
    """镜像本轮开始时的实现文件到 outputs/s5c/code_baseline/（增量范围校验基线）。

    与 S5b 同模式：prepare 段在 Agent 修改前镜像，供 diff_range_checker 对照。
    返回 {rel: {sha256, lines}} 并写 code_snapshot.json；首跑无产物时索引为空。
    """
    baseline_dir = s5c_outputs_dir / "code_baseline"
    if baseline_dir.exists():
        shutil.rmtree(baseline_dir)
    index: dict[str, dict] = {}
    for d in src_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.c")):
            rel = str(f.resolve().relative_to(workspace)).replace("\\", "/")
            dst = baseline_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            index[rel] = {
                "sha256": file_sha256(f),
                "lines": len(f.read_text(encoding="utf-8", errors="replace").splitlines()),
            }
    save_json(s5c_outputs_dir / "code_snapshot.json",
              {"files": index,
               "created_at": datetime.now().isoformat(timespec="seconds")})
    return index
