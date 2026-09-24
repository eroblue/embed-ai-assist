"""S5b port-contract-and-app 确定性分析共享模块（rule 轨，全脚本共用）。

职责边界（执行策略与 S5a 一致：rule 只做确定性契约工作，代码/流程图内容
生成归 Agent/LLM）：
- 分层配置加载、S2/S4 可选就绪检查（S2 缺失时降级为设计输入驱动模式）、
  设计输入段标记机械解析、S4 硬件事实摘要提取、
  Mermaid 流程图解析（front-matter + 三种图类型节点/边提取）。
- 本模块不生成任何 C 代码，不生成流程图内容，不做功能拆分判断。

S5b 不依赖 S5a 的任何产物（可并行）；port_interface_manifest.json 是
S5c 实现 Port 的唯一依据。
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

# ---------------- JSON / 配置工具（与 S5a analysis 同模式，skill 间不耦合） ----------------

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


# ---------------- S5b 执行上下文 ----------------

def load_context(config_path: Path, workspace: Path | None = None,
                 arch_override: str | None = None) -> dict:
    """加载配置与可选输入（S2 spec / S4 facts），返回 S5b 执行上下文。

    S2/S4 均为可选依赖（requirement：S5b 触发于 S2 完成后，与 S5a 并行）：
    - spec.* 存在且非 failed → spec 驱动；缺失 → 设计输入驱动模式（降级）
    - circuit.facts 存在且非 failed → 提供硬件事实摘要；缺失 → 跳过
    state.json 必须存在（S1 建立的工作区），否则报错。
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

    spec = state.get("spec") or None
    if spec and spec.get("status") == "failed":
        raise RuntimeError("S2 功能规格提取失败（spec.status=failed），无法执行 S5b")
    facts_info = ((state.get("circuit") or {}).get("facts")) or None
    if facts_info and facts_info.get("verify_status") == "failed":
        raise RuntimeError("S4 硬件事实验证失败（circuit.facts.verify_status=failed），无法执行 S5b")

    # spec 驱动 / 设计输入驱动（降级）
    spec_path = None
    if spec and spec.get("spec_path"):
        p = workspace / spec["spec_path"]
        if p.is_file():
            spec_path = str(spec["spec_path"])

    # S4 硬件事实（可选）
    facts = None
    if facts_info and facts_info.get("facts_path"):
        fp = workspace / facts_info["facts_path"]
        if fp.is_file():
            facts = load_json(fp)

    project_cfg = config.get("project") or {}
    architecture = arch_override or project_cfg.get("architecture") or "layered"
    rtos = project_cfg.get("rtos") or "none"
    power_enabled = (project_cfg.get("power") or {}).get("enabled", False)
    s5b_cfg = config.get("s5b") or {}
    inputs_cfg = project_cfg.get("inputs") or {}

    return {
        "config": config,
        "workspace": workspace,          # 目标工程根 <项目根>/<build_target>/
        "project_root": project_root,    # 项目根（docs/ 等共享资源）
        "state_path": state_path,
        "state": state,
        "outputs_dir": workspace / (config.get("output_dir") or "outputs").rstrip("/\\"),
        "architecture": architecture,
        "rtos": rtos,
        "power_enabled": power_enabled,
        "language": s5b_cfg.get("language") or "c99",
        "port_split": s5b_cfg.get("port_split") or "",
        "inputs": {
            "software_spec": inputs_cfg.get("software_spec") or "",
            "s5b_design_input": inputs_cfg.get("s5b_design_input") or "docs/s5b_design_input.md",
            "demos": inputs_cfg.get("demos") or [],
            "sdk": inputs_cfg.get("sdk") or "",
            "existing_project": inputs_cfg.get("existing_project") or "",
            "ide_project": inputs_cfg.get("ide_project") or "",
        },
        "spec_path": spec_path,          # None → 设计输入驱动模式
        "facts": facts,                  # None → 无 S4 硬件事实
        "facts_path": (facts_info or {}).get("facts_path"),
        "flow_dir": workspace / "docs" / "flow",
    }


# ---------------- 用户设计输入（docs/s5b_design_input.md） ----------------

# 支持的段标记（requirement"输入材料说明"+示例项目实际段落）
_KNOWN_SECTIONS = ("功能规格", "状态机", "时序", "错误处理", "硬件使用", "功能映射",
                   "协议", "任务划分")


def load_design_input(project_root: Path, rel_path: str = "docs/s5b_design_input.md") -> dict | None:
    """读取 s5b_design_input.md，按二级标题拆段。

    返回 {path, sections: {段名: [行]}, has_content}；文件不存在、内容为空或
    全部为 none → None（Agent 按经验自主判断，项目记忆约束）。
    段名匹配放宽：标题前缀命中已知标记即可（如"任务划分（如启用 RTOS）"）。
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


def extract_hw_requirements(design_input: dict | None) -> list[dict]:
    """从设计输入"硬件使用"段机械提取外设引用（capability gap 比对用）。

    行格式示例：UART0：WiFi 模块，115200-8N1 / GPIO：LED 指示（PC13）
    返回 [{peripheral, instance, pins, raw}]；无法解析的行忽略。
    """
    if not design_input:
        return []
    out: list[dict] = []
    for ln in design_input.get("sections", {}).get("硬件使用", []):
        text = ln.strip().lstrip("-")
        m = re.match(r"\s*(UART|USART|SPI|I2C|ADC|PWM|TIMER|GPIO)\s*(\d*)\s*[：:]\s*(.+)", text, re.I)
        if not m:
            continue
        periph = m.group(1).upper()
        if periph in ("USART",):
            periph = "UART"
        pins = re.findall(r"\bP[A-H](?:\d{1,2})\b", m.group(3))
        out.append({"peripheral": periph, "instance": m.group(2) or "",
                    "pins": pins, "raw": text.strip()})
    return out


def facts_hw_summary(facts: dict | None) -> list[str]:
    """S4 硬件事实摘要（供任务书：Port 实例定义参考）。

    按外设类型分组输出"实例/引脚/网络"行；facts 为 None 返回空列表。
    """
    if not facts:
        return []
    by_periph: dict[str, list[str]] = {}
    for pin in facts.get("pins", []):
        if pin.get("nc"):
            continue
        periph = (pin.get("peripheral") or "").strip()
        if not periph or periph in {"电源", "HXTAL", "LXTAL", "NRST", "SWD", "JTAG", "BOOT", "ISP"}:
            continue
        desc = f"{pin.get('pin_name') or '?'}（net {pin.get('net') or '?'}，role {pin.get('role') or '-'}）"
        by_periph.setdefault(periph, []).append(desc)
    lines: list[str] = []
    for periph in sorted(by_periph):
        lines.append(f"- {periph}：{'；'.join(by_periph[periph])}")
    return lines


def check_capability_gaps(hw_reqs: list[dict], facts: dict | None,
                          facts_rel: str | None) -> dict:
    """机械能力缺口检测：设计输入硬件使用段 vs S4 facts。

    S4 缺失 → checked=false（Agent 按经验评估）；引脚/外设找不到 → gap 条目。
    """
    if not facts:
        return {"checked": False, "checked_against": None, "gaps": []}
    gaps: list[dict] = []
    # 精确 token 集合匹配（大写归一）：避免子串误命中（PA1 不得匹配 PA10、
    # UART1 不得匹配 UART10 导致缺口漏报）
    fact_tokens: set[str] = set()
    for p in facts.get("pins", []):
        if p.get("nc"):
            continue
        for field in ("pin_name", "net", "peripheral"):
            val = (p.get(field) or "").strip().upper()
            if val:
                fact_tokens.add(val)
    for req in hw_reqs:
        if req["pins"]:
            for pn in req["pins"]:
                if pn.upper() not in fact_tokens:
                    gaps.append({
                        "requirement": req["raw"], "peripheral": req["peripheral"].lower(),
                        "needed": pn, "available": False,
                        "detail": f"设计输入引用引脚 {pn} 未出现在 S4 硬件事实中（引脚号/网络名不匹配或未连接）",
                        "severity": "warning", "source": "rule"})
        elif req["instance"]:
            inst = f"{req['peripheral']}{req['instance']}"
            if inst.upper() not in fact_tokens and req["peripheral"] != "GPIO":
                gaps.append({
                    "requirement": req["raw"], "peripheral": req["peripheral"].lower(),
                    "needed": inst, "available": False,
                    "detail": f"设计输入引用实例 {inst} 未出现在 S4 硬件事实中",
                    "severity": "warning", "source": "rule"})
    return {"checked": True, "checked_against": facts_rel, "gaps": gaps}


# ---------------- Mermaid 流程图解析（flow_validator / flow_differ 共用） ----------------

FLOW_STATUSES = ("draft", "review", "approved", "dirty", "deprecated")
# 文件名后缀 ↔ 图类型 ↔ 图首行声明（图类型由系统定，不由 Agent 选；
# flow 方向约定：TD（竖向）推荐、LR（横向）历史兼容，实际校验在 flow_validator.py）
FLOW_KIND_MAP = {
    "state": ("stateDiagram-v2", "stateDiagram-v2"),
    "flow": ("flowchart", "flowchart TD|LR"),
    "sequence": ("sequenceDiagram", "sequenceDiagram"),
}


def parse_front_matter(text: str) -> tuple[dict | None, str]:
    """解析 YAML front-matter（--- key: value ---），返回 (meta, 正文)。无则 (None, text)。"""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, flags=re.S)
    if not m:
        return None, text
    meta: dict = {}
    for ln in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_][\w]*)\s*:\s*(.*?)\s*$", ln)
        if kv:
            val = kv.group(2).strip().strip("'\"")
            if val.lower() == "null":
                val = None
            meta[kv.group(1)] = val
    return meta, m.group(2)


def content_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _strip_mermaid_comments(body: str) -> list[str]:
    """正文行清洗：去 %% 注释、空行；返回有效行。"""
    out = []
    for ln in body.splitlines():
        ln = re.sub(r"%%.*$", "", ln).strip()
        if ln:
            out.append(ln)
    return out


def _parse_state_diagram(body: str) -> dict:
    """stateDiagram-v2 → 节点（状态名）+ 边（from/to/event）。

    语法子集：`A --> B : evt / action`、`[*] --> A`、`A --> [*]`、
    `state "desc" as A`（只取 A）、`A : description`（状态描述，不算边）。
    """
    nodes: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    for ln in _strip_mermaid_comments(body):
        if ln.startswith("state ") and " as " in ln:
            nodes.add(ln.rsplit(" as ", 1)[1].strip())
            continue
        if re.match(r"^[A-Za-z_][\w]*\s*:", ln):  # 状态描述行
            nodes.add(ln.split(":", 1)[0].strip())
            continue
        m = re.match(r"^(\[\*\]|[A-Za-z_][\w]*)\s*-+->\s*(\[\*\]|[A-Za-z_][\w]*)\s*(?::\s*(.+))?$", ln)
        if m:
            frm, to, label = m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()
            edges.add((frm, to, label))
            if frm != "[*]":
                nodes.add(frm)
            if to != "[*]":
                nodes.add(to)
    return {"nodes": sorted(nodes), "edges": sorted(edges)}


def _parse_flowchart(body: str) -> dict:
    """flowchart → 节点（id, label）+ 边（from/to/label）。

    语法子集：`A[Label]`/`A(Label)`/`A{Label}`/`A[[Label]]`、
    `A --> B`、`A -->|cond| B`、`A -- text --> B`、`A --- B`。
    """
    node_re = re.compile(r"\b([A-Za-z_][\w]*)\s*(\[\[|\(|\[|\{)([^\]\}\)]*)(\]\]|\)|\]|\})")
    edge_re = re.compile(
        r"([A-Za-z_][\w]*)\s*(-{2,3}>|={2,}>|-\.->)\s*(?:\|([^|]*)\|\s*)?([A-Za-z_][\w]*)"
        r"|(?:([A-Za-z_][\w]*)\s*--\s*([^-\s][^-]*?)\s*-->\s*([A-Za-z_][\w]*))")
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str, str]] = set()

    def _reg(id_: str, label: str = "") -> None:
        if id_ not in nodes or (label and not nodes[id_]):
            nodes[id_] = label or id_

    for ln in _strip_mermaid_comments(body):
        if ln.startswith(("flowchart", "graph", "subgraph", "end", "direction")):
            continue
        for m in node_re.finditer(ln):
            _reg(m.group(1), m.group(3).strip())
        m = edge_re.search(ln)
        if m:
            if m.group(1):  # A -->|cond| B / A --> B
                frm, to = m.group(1), m.group(4)
                label = (m.group(3) or "").strip()
                edges.add((frm, to, label))
                _reg(frm)
                _reg(to)
            else:           # A -- text --> B
                edges.add((m.group(5), m.group(7), (m.group(6) or "").strip()))
                _reg(m.group(5))
                _reg(m.group(7))
        else:
            m2 = re.match(r"^([A-Za-z_][\w]*)\s*$", ln)  # 独立节点定义
            if m2:
                _reg(m2.group(1))
    return {"nodes": sorted(nodes), "node_labels": dict(nodes), "edges": sorted(edges)}


def _parse_sequence_diagram(body: str) -> dict:
    """sequenceDiagram → 节点（参与者）+ 边（from/to/msg）。

    语法子集：`participant X [as Name]`、`A->>B: msg`、`A-->>B: msg`、
    `A->B: msg`、`A--)B: msg`；activate/deactivate/Note/loop/alt/opt 忽略。
    """
    nodes: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    for ln in _strip_mermaid_comments(body):
        m = re.match(r"^(?:participant|actor)\s+([A-Za-z_][\w]*)", ln)
        if m:
            nodes.add(m.group(1))
            continue
        m = re.match(r"^([A-Za-z_][\w]*)\s*(?:-->>|->>|->|--|-\))\s*([A-Za-z_][\w]*)\s*:\s*(.+)$", ln)
        if m:
            edges.add((m.group(1), m.group(2), m.group(3).strip()))
            nodes.add(m.group(1))
            nodes.add(m.group(2))
    return {"nodes": sorted(nodes), "edges": sorted(edges)}


def parse_mermaid(body: str, graph_type: str) -> dict:
    """按图类型解析 Mermaid 正文 → {nodes: [...], edges: [...], node_labels: {...}}。"""
    if graph_type == "stateDiagram-v2":
        return _parse_state_diagram(body)
    if graph_type == "flowchart":
        return _parse_flowchart(body)
    if graph_type == "sequenceDiagram":
        return _parse_sequence_diagram(body)
    raise ValueError(f"未知图类型: {graph_type}")


def scan_flow_dir(flow_dir: Path) -> list[dict]:
    """扫描 docs/flow/*.md → [{module, kind, path}]；文件名须为 <模块>_<state|flow|sequence>.md。

    .history/ 子目录跳过。命名不合规的文件跳过（flow_validator 负责报告）。
    """
    out: list[dict] = []
    if not flow_dir.is_dir():
        return out
    for p in sorted(flow_dir.glob("*.md")):
        m = re.match(r"^(.+?)_(state|flow|sequence)\.md$", p.name)
        if m:
            out.append({"module": m.group(1), "kind": m.group(2), "path": p})
    return out


def flow_rel_path(flow_dir: Path, path: Path) -> str:
    """流程图文件 → 工作区相对 POSIX 路径（state.json 指针用）。"""
    return str(path.resolve().relative_to(flow_dir.parents[1])).replace("\\", "/")


# ---------------- S5b 产物路径角色判定（目录来自 PROJECT_LAYOUT.md 解析） ----------------

def classify_rel_path(rel: str) -> str:
    """按路径段判定 S5b 产物角色：port / driver / app。

    与 PROJECT_LAYOUT.md 布局树对应：路径含 Port/ → port；含 BSP/ → driver；
    其余（App/...）→ app。路径不依赖具体前缀层级，布局树怎么变都成立。
    """
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if "Port" in parts:
        return "port"
    if "BSP" in parts:
        return "driver"
    return "app"
