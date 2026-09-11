"""KiCad 原理图适配器：解析 .kicad_sch（S-expression 格式），
推导元件、引脚与网络连通性，输出 EDA 无关的通用网表结构。

纯标准库实现，不依赖第三方 KiCad 解析库。
"""

from __future__ import annotations

import math
import re
from pathlib import Path

# KiCad pin 电气类型 -> 通用 pin_type（对齐 Altium 侧枚举命名）
PIN_TYPE_MAP = {
    "input": "INPUT",
    "output": "OUTPUT",
    "bidirectional": "IO",
    "passive": "PASSIVE",
    "tri_state": "TRISTATE",
    "open_collector": "OPEN_COLLECTOR",
    "open_emitter": "OPEN_EMITTER",
    "power_in": "POWER",
    "power_out": "POWER",
    "unspecified": "PASSIVE",
    "free": "PASSIVE",
    "no_connect": "UNKNOWN",
}

# 坐标合并容差（mm），KiCad 原理图单位即 mm
EPS = 1e-6


# ---------------------------------------------------------------------------
# S-expression 解析
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')


def _tokenize(text: str):
    """把 S-expression 文本切分为 token；字符串保留引号。"""
    return _TOKEN_RE.findall(text)


def _atom(token: str):
    """token 转标量：去引号字符串 / 整数 / 浮点 / 原样字符串。"""
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d*([eE][-+]?\d+)?", token):
        return float(token)
    return token


def parse_sexp(text: str):
    """递归解析 S-expression 为嵌套 list；异常输入抛 ValueError。"""
    tokens = _tokenize(text)
    pos = 0

    def parse_node():
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("unexpected end of s-expression")
        tok = tokens[pos]
        if tok == "(":
            pos += 1
            items = []
            while pos < len(tokens) and tokens[pos] != ")":
                items.append(parse_node())
            if pos >= len(tokens):
                raise ValueError("missing closing parenthesis")
            pos += 1
            return items
        if tok == ")":
            raise ValueError("unexpected closing parenthesis")
        pos += 1
        return _atom(tok)

    nodes = []
    while pos < len(tokens):
        nodes.append(parse_node())
    return nodes[0] if len(nodes) == 1 else nodes


# ---------------------------------------------------------------------------
# S-expression 辅助查询
# ---------------------------------------------------------------------------

def _tag(node) -> str | None:
    """list 节点的标签（首个 atom），如 'wire'。"""
    if isinstance(node, list) and node and isinstance(node[0], str):
        return node[0]
    return None


def _find_all(node, tag: str, out: list):
    """递归收集所有 tag 节点。"""
    if isinstance(node, list):
        if _tag(node) == tag:
            out.append(node)
        for child in node:
            _find_all(child, tag, out)


def _get_prop(node, key: str, pos: int = 1):
    """取 (key value ...) 的 value。"""
    if _tag(node) == key and len(node) > pos:
        return node[pos]
    return None


def _child(node, tag: str):
    """取第一个直接子节点。"""
    if not isinstance(node, list):
        return None
    for child in node[1:]:
        if _tag(child) == tag:
            return child
    return None


def _at_xy(node) -> tuple[float, float, float] | None:
    """解析 (at x y [angle]) -> (x, y, angle)。"""
    at = _child(node, "at")
    if not at or len(at) < 3:
        return None
    angle = at[3] if len(at) > 3 and isinstance(at[3], (int, float)) else 0.0
    return float(at[1]), float(at[2]), float(angle)


# ---------------------------------------------------------------------------
# 符号库（lib_symbols）解析
# ---------------------------------------------------------------------------

def _parse_lib_pins(lib_symbol: list) -> list[dict]:
    """解析库符号中所有 (pin ...) 记录。

    多单元符号的引脚可能带 unit 过滤，此处不做过滤，
    由实例侧 unit 匹配决定使用哪些引脚。
    """
    pins = []
    for pin in lib_symbol[1:]:
        if _tag(pin) != "pin":
            continue
        # (pin <electrical> <graphic> (at x y angle) (length L) (name ...) (number ...))
        at = _child(pin, "at")
        length = _get_prop(_child(pin, "length"), "length") or 0.0
        name_node = _child(pin, "name")
        number_node = _child(pin, "number")
        pins.append(
            {
                "electrical": str(pin[1]) if len(pin) > 1 else "passive",
                "x": float(at[1]) if at else 0.0,
                "y": float(at[2]) if at else 0.0,
                "angle": float(at[3]) if at and len(at) > 3 else 0.0,
                "length": float(length) if isinstance(length, (int, float)) else 0.0,
                "name": str(name_node[1]) if name_node and len(name_node) > 1 else "",
                "number": str(number_node[1]) if number_node and len(number_node) > 1 else "",
                "unit": 0,
            }
        )
    return pins


def _parse_lib_units(lib_symbol: list) -> dict[int, list[dict]]:
    """按 unit 拆分库符号引脚。

    顶层 pin 属于 unit 1（单单元符号）；子 (symbol "name_unit_N" ...) 内的 pin
    属于单元 N。symbol 名形如 "xxx_1_1"（风格_unit_单元）。
    """
    units: dict[int, list[dict]] = {}
    top_pins = _parse_lib_pins(lib_symbol)
    if top_pins:
        units[0] = top_pins
    for sub in lib_symbol[1:]:
        if _tag(sub) != "symbol" or len(sub) < 2:
            continue
        name = str(sub[1])
        if len(name) >= 3:
            m = re.search(r"_(\d+)_(\d+)$", name)
            unit_idx = int(m.group(1)) if m else 1
        else:
            unit_idx = 1
        pins = _parse_lib_pins(sub)
        if pins:
            units.setdefault(unit_idx, []).extend(pins)
    return units


# ---------------------------------------------------------------------------
# 实例 pin 坐标变换
# ---------------------------------------------------------------------------

def _pin_world(pin: dict, sx: float, sy: float, rot: float, mirror: str):
    """计算 pin 根部与电气连接点的绝对坐标。

    变换顺序：先镜像、再旋转、最后平移（与 KiCad 符号变换一致，Y 轴向上）。
    """
    px, py, angle = pin["x"], pin["y"], pin["angle"]
    if mirror == "x":
        py = -py
        angle = -angle
    elif mirror == "y":
        px = -px
        angle = 180.0 - angle
    r = math.radians(rot)
    cos_r, sin_r = math.cos(r), math.sin(r)
    wx = px * cos_r - py * sin_r
    wy = px * sin_r + py * cos_r
    angle = (angle + rot) % 360.0
    root = (sx + wx, sy + wy)
    rad = math.radians(angle)
    tip = (root[0] + pin["length"] * math.cos(rad), root[1] + pin["length"] * math.sin(rad))
    return root, tip


# ---------------------------------------------------------------------------
# 连通性（并查集 + 几何吸附）
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self):
        self.parent: dict[tuple, tuple] = {}

    def find(self, p: tuple):
        self.parent.setdefault(p, p)
        while self.parent[p] != p:
            self.parent[p] = self.parent[self.parent[p]]
            p = self.parent[p]
        return p

    def union(self, a: tuple, b: tuple):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra

    def groups(self) -> dict[tuple, list[tuple]]:
        out: dict[tuple, list[tuple]] = {}
        for p in self.parent:
            out.setdefault(self.find(p), []).append(p)
        return out


def _point_on_segment(p: tuple, a: tuple, b: tuple, tol: float = 1e-3) -> bool:
    """点 p 是否落在线段 ab 上（含端点）。"""
    (px, py), (ax, ay), (bx, by) = p, a, b
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    if abs(cross) > tol * max(1.0, math.hypot(bx - ax, by - ay)):
        return False
    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -tol:
        return False
    if dot > (bx - ax) ** 2 + (by - ay) ** 2 + tol:
        return False
    return True


def _round_pt(p: tuple) -> tuple:
    """坐标归一化（容差内同点合并）。"""
    return (round(p[0], 4), round(p[1], 4))


# ---------------------------------------------------------------------------
# 主解析入口
# ---------------------------------------------------------------------------

def parse(schematic_path: str) -> dict:
    """解析 .kicad_sch，返回通用网表中间结构（components / nets / warnings）。"""
    path = Path(schematic_path)
    text = path.read_text(encoding="utf-8", errors="replace")
    root = parse_sexp(text)

    warnings: list[str] = []

    # 1. 库符号引脚定义
    lib_units: dict[str, dict[int, list[dict]]] = {}
    lib_symbols_node = _child(root, "lib_symbols")
    if lib_symbols_node:
        for sym in lib_symbols_node[1:]:
            if _tag(sym) != "symbol" or len(sym) < 2:
                continue
            lib_units[str(sym[1])] = _parse_lib_units(sym)

    # 2. 图纸上的 symbol 实例
    instances = []
    for node in root[1:] if isinstance(root, list) else []:
        if _tag(node) != "symbol":
            continue
        lib_id = _get_prop(_child(node, "lib_id"), "lib_id")
        if not lib_id:
            continue
        at = _at_xy(node) or (0.0, 0.0, 0.0)
        mirror = ""
        mirror_node = _child(node, "mirror")
        if mirror_node and len(mirror_node) > 1:
            mirror = str(mirror_node[1])
        unit = 1
        unit_node = _child(node, "unit")
        if unit_node and len(unit_node) > 1 and isinstance(unit_node[1], int):
            unit = unit_node[1]
        props = {}
        for prop in node[1:]:
            if _tag(prop) == "property" and len(prop) >= 3:
                props[str(prop[1])] = str(prop[2])
        instances.append(
            {
                "lib_id": str(lib_id),
                "x": at[0],
                "y": at[1],
                "rot": at[2],
                "mirror": mirror,
                "unit": unit,
                "properties": props,
            }
        )

    # 3. 导线 / 标签 / 电源口
    wires = []
    _find_all(root, "wire", wires)
    wire_segments = []
    for wire in wires:
        pts_node = _child(wire, "pts")
        if not pts_node:
            continue
        pts = [
            (float(p[1]), float(p[2]))
            for p in pts_node[1:]
            if _tag(p) == "xy" and len(p) >= 3
        ]
        for i in range(len(pts) - 1):
            wire_segments.append((pts[i], pts[i + 1]))

    labels = []  # (name, (x, y))
    _collect_labels(root, labels)

    # 4. 并查集连通性
    uf = _UnionFind()
    for a, b in wire_segments:
        uf.union(_round_pt(a), _round_pt(b))

    # 引脚连接点 / 标签点也作为图节点
    pin_terms: list[dict] = []  # {designator, pin, pin_name, pin_type, key}
    components: dict[str, dict] = {}

    for inst in instances:
        ref = inst["properties"].get("Reference", "")
        is_power = ref.startswith("#PWR") or inst["lib_id"].startswith("power:")
        units = lib_units.get(inst["lib_id"])
        if units is None:
            warnings.append(f"symbol {inst['lib_id']} not found in lib_symbols")
            continue
        pins = units.get(inst["unit"]) or units.get(0) or []
        for pin in pins:
            root_pt, tip = _pin_world(pin, inst["x"], inst["y"], inst["rot"], inst["mirror"])
            key = _round_pt(tip)
            uf.find(key)
            if is_power:
                # 电源口：Value 作为网络名锚点
                net_name = inst["properties"].get("Value") or inst["lib_id"].split(":")[-1]
                pin_terms.append(
                    {
                        "designator": ref,
                        "pin": pin["number"] or "1",
                        "pin_name": pin["name"],
                        "pin_type": PIN_TYPE_MAP.get(pin["electrical"], "UNKNOWN"),
                        "key": key,
                        "power_net": net_name,
                    }
                )
            else:
                pin_terms.append(
                    {
                        "designator": ref,
                        "pin": pin["number"],
                        "pin_name": pin["name"],
                        "pin_type": PIN_TYPE_MAP.get(pin["electrical"], "UNKNOWN"),
                        "key": key,
                    }
                )

    label_anchors: list[tuple[str, tuple]] = []
    for name, pt in labels:
        key = _round_pt(pt)
        uf.find(key)
        label_anchors.append((name, key))

    # 引脚端点吸附到导线端点或导线线段上
    for term in pin_terms:
        key = term["key"]
        for seg_a, seg_b in wire_segments:
            if _point_on_segment(key, seg_a, seg_b):
                uf.union(key, _round_pt(seg_a))
                break

    # 标签锚点吸附到导线
    for _, key in label_anchors:
        for seg_a, seg_b in wire_segments:
            if _point_on_segment(key, seg_a, seg_b):
                uf.union(key, _round_pt(seg_a))
                break

    # 5. 生成网络
    label_by_group: dict[tuple, str] = {}
    for name, key in label_anchors:
        g = uf.find(key)
        label_by_group.setdefault(g, name)
    power_by_group: dict[tuple, str] = {}
    for term in pin_terms:
        if "power_net" in term:
            g = uf.find(term["key"])
            power_by_group.setdefault(g, term["power_net"])

    nets: dict[str, dict] = {}
    group_net: dict[tuple, str] = {}
    for term in pin_terms:
        if not term["designator"] or term["designator"].startswith("#"):
            continue
        g = uf.find(term["key"])
        if g not in group_net:
            if g in label_by_group:
                net_name = label_by_group[g]
            elif g in power_by_group:
                net_name = power_by_group[g]
            else:
                net_name = f"Net{term['designator']}_{term['pin']}"
            group_net[g] = net_name
            nets[net_name] = {
                "name": net_name,
                "auto_named": g not in label_by_group and g not in power_by_group,
                "source_sheets": [path.name],
                "terminals": [],
            }
        net_name = group_net[g]
        nets[net_name]["terminals"].append(term)

    # 汇总元件（按 designator 合并多单元实例）
    for inst in instances:
        ref = inst["properties"].get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        comp = components.setdefault(
            ref,
            {
                "designator": ref,
                "value": inst["properties"].get("Value", ""),
                "footprint": inst["properties"].get("Footprint", ""),
                "library_ref": inst["lib_id"],
                "description": inst["properties"].get("Description", ""),
                "parameters": dict(inst["properties"]),
                "pins": [],
            },
        )
    for net in nets.values():
        for term in net["terminals"]:
            comp = components.get(term["designator"])
            if comp is None:
                continue
            comp["pins"].append(
                {
                    "pin": term["pin"],
                    "pin_name": term["pin_name"],
                    "pin_type": term["pin_type"],
                    "net": net["name"],
                }
            )

    for comp in components.values():
        comp["pins"].sort(key=lambda p: _natural_key(p["pin"]))
        # 去重（多单元重复引脚）
        seen = set()
        deduped = []
        for p in comp["pins"]:
            k = (p["pin"], p["net"])
            if k not in seen:
                seen.add(k)
                deduped.append(p)
        comp["pins"] = deduped

    net_list = sorted(nets.values(), key=lambda n: n["name"])
    for net in net_list:
        net["terminals"] = [
            {
                "designator": t["designator"],
                "pin": t["pin"],
                "pin_name": t["pin_name"],
                "pin_type": t["pin_type"],
            }
            for t in sorted(net["terminals"], key=lambda t: (t["designator"], _natural_key(t["pin"])))
        ]

    return {
        "components": sorted(components.values(), key=lambda c: _natural_key(c["designator"])),
        "nets": net_list,
        "warnings": warnings,
    }


def _collect_labels(root, out: list):
    """收集 (label "NAME" (at x y ...)) 与 (global_label ...) 节点。"""
    for tag in ("label", "global_label", "hierarchical_label"):
        found = []
        _find_all(root, tag, found)
        for node in found:
            name = node[1] if len(node) > 1 else ""
            at = _at_xy(node)
            if at:
                out.append((str(name), (at[0], at[1])))


def _natural_key(s: str):
    """数字感知排序键：'2' < '10'。"""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]
