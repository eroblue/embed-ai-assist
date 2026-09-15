#!/usr/bin/env python
"""CMSIS 设备头文件解析模块（S3 第二优先数据源）。

厂商必然提供设备头文件（如 stm32f10x.h——没有头文件无法用 C 编程），
其中包含外设基地址、寄存器结构体、中断号、位域掩码，数据权威
（编译器直接使用）。覆盖 SVD 缺失的芯片（多数国产 MCU）。

数据源优先级：SVD（含复位值/完整位域）> SDK 头文件 > 参考手册 PDF。

解析内容（CMSIS 设备头标准形式）：
- #define XXX_BASE (PERIPH_BASE + 0xNNNN)   → 外设基地址（表达式递归求值）
- typedef struct { __IO uint32_t REG; ... } XXX_TypeDef; → 寄存器成员偏移（C 对齐规则）
- #define GPIOA ((GPIO_TypeDef *) GPIOA_BASE) → 外现实例 → 寄存器全名展开
- XXX_IRQn = N                                → 中断向量号
- #define RCC_APB2ENR_IOPAEN ((uint32_t)0x4)  → 位域掩码（反推 bit 位置）

8 位机 SFR 风格（sfr P0 = 0x80）待接入样本后扩展。
"""

from __future__ import annotations

import re
from pathlib import Path

from svd_source import BUS_RANGES, _hex, _peripheral_of_en

# 成员限定符 → 访问权限
_MEMBER_ACCESS = {"__I": "r", "__O": "w", "__IO": "rw"}

# 成员类型 → 字节宽度（C 自然对齐）
_TYPE_WIDTH = {
    "uint32_t": 4, "int32_t": 4, "uint8_t": 1, "int8_t": 1,
    "uint16_t": 2, "int16_t": 2, "int": 4, "unsigned int": 4,
    "u32": 4, "u16": 2, "u8": 1, "vu32": 4, "vu16": 2, "vu8": 1,
    "unsigned long": 4, "long": 4,
}

# CFGR 分频/时钟选择位域 → 总线（与 svd_source 一致）
_PRESCALER_BUS = {
    "HPRE": "AHB", "PPRE1": "APB1", "PPRE2": "APB2",
    "ADCPRE": "ADC", "USBPRE": "USB",
    "PLLMUL": "SYSCLK", "PLLSRC": "SYSCLK",
    "MCO": "SYSCLK", "SW": "SYSCLK", "SWS": "SYSCLK",
}

_DEFINE_RE = re.compile(r"^#define\s+(\w+)\s+(.+)$", re.M)
_TYPEDEF_RE = re.compile(
    r"typedef\s+struct\s*\{([^}]+)\}\s*(\w+)\s*;",
    re.S,
)
_MEMBER_RE = re.compile(
    r"(__IO|__I|__O|volatile\s+const|const\s+volatile|volatile)?\s*"
    r"(uint32_t|int32_t|uint16_t|int16_t|uint8_t|int8_t|u32|u16|u8|vu32|vu16|vu8|"
    r"unsigned\s+int|unsigned\s+long|long|int)\s+(\w+)\s*;"
)
_INSTANCE_RE = re.compile(r"^#define\s+(\w+)\s*\(\s*\(\s*(\w+)_TypeDef\s*\*\s*\)\s*(\w+)\s*\)", re.M)
_IRQ_RE = re.compile(r"(\w+)_IRQn\s*=\s*(-?\d+)")
_MASK_RE = re.compile(r"^#define\s+([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\s+\(\s*\(\s*(?:uint32_t|uint16_t|uint8_t)\s*\)\s*(0[xX][0-9A-Fa-f]+|\d+)\s*\)", re.M)

_TOKEN_RE = re.compile(r"\(|\)|\+|\-|\*|~|0[xX][0-9A-Fa-f]+|\d+|[A-Za-z_]\w*")


def _strip_comments(text: str) -> str:
    """去 C 注释（块/行），保留换行结构。"""
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _eval_macro(expr: str, macros: dict[str, str], depth: int = 0) -> int | None:
    """宏表达式求值：PERIPH_BASE + 0x10000 / ((uint32_t)0x4) / 0x40000000。"""
    expr = expr.strip()
    expr = re.sub(r"\(\s*(?:uint32_t|uint16_t|uint8_t|__IO|__I|__O|const|volatile)\s*\)", " ", expr)
    if depth > 20:
        return None
    tokens = _TOKEN_RE.findall(expr)
    if not tokens:
        return None
    parts: list[str] = []
    for tok in tokens:
        if re.match(r"^[A-Za-z_]", tok):
            if tok in macros:
                val = _eval_macro(macros[tok], macros, depth + 1)
                if val is None:
                    return None
                parts.append(f"({val})")
            elif tok in ("U", "L", "UL", "u", "l", "ull"):  # 数值后缀已并入数字
                parts.append("")
            else:
                return None  # 函数宏/未知标识符
        else:
            parts.append(tok)
    py = " ".join(p for p in parts if p)
    if not re.fullmatch(r"[\d\s\(\)\+\-\*~xXa-fA-F]+", py):
        return None
    try:
        return int(eval(py, {"__builtins__": {}}, {}))  # noqa: S307（输入为本地头文件，已白名单校验）
    except Exception:
        return None


def _parse_structs(text: str) -> dict[str, list[tuple[str, str, int, str]]]:
    """typedef struct → {类型名: [(成员名, 访问, 偏移, 类型)], ...}（C 自然对齐）。"""
    out: dict[str, list[tuple[str, str, int, str]]] = {}
    for m in _TYPEDEF_RE.finditer(text):
        body, type_name = m.group(1), m.group(2)
        members: list[tuple[str, str, int, str]] = []
        offset = 0
        for sm in _MEMBER_RE.finditer(body):
            quals, ctype, name = sm.group(1) or "", sm.group(2), sm.group(3)
            width = _TYPE_WIDTH.get(ctype.replace(" ", " "), 4)
            quals_c = quals.replace(" ", "")
            access = _MEMBER_ACCESS.get(quals_c, "rw")
            offset = (offset + width - 1) // width * width  # 成员对齐
            members.append((name, access, offset, ctype))
            offset += width
        if members:
            out[type_name] = members
    return out


def _bus_of(addr: int) -> str | None:
    for bus, lo, hi in BUS_RANGES:
        if lo <= addr <= hi:
            return bus
    return None


def _bits_from_mask(mask: int) -> str | None:
    """连续位掩码 → 'msb:lsb' / 'n'；非连续/空掩码返回 None。"""
    if mask <= 0:
        return None
    lsb = (mask & -mask).bit_length() - 1
    width = bin(mask).count("1")
    if (1 << width) - 1 << lsb != mask:  # 非连续
        return None
    msb = lsb + width - 1
    return f"{msb}:{lsb}" if msb != lsb else str(msb)


def parse_sdk_header(header_path: Path) -> dict:
    """解析 CMSIS 设备头文件 → {peripherals, registers, clock_tree, warnings}。"""
    result: dict = {"peripherals": [], "registers": [], "clock_tree": None, "warnings": []}
    try:
        raw = header_path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        result["warnings"].append(f"头文件读取失败: {exc}")
        return result
    text = _strip_comments(raw.replace("\\\r\n", " ").replace("\\\n", " "))

    # ---- 1. 宏收集与求值 ----
    macros: dict[str, str] = {m.group(1): m.group(2).strip() for m in _DEFINE_RE.finditer(text)}
    base_values: dict[str, int] = {}
    for name, expr in macros.items():
        if name.endswith("_BASE"):
            val = _eval_macro(expr, macros)
            if val is not None:
                base_values[name] = val

    # ---- 2. 结构体 → 成员偏移 ----
    structs = _parse_structs(text)

    # ---- 3. 外现实例 → 外设清单 + 寄存器展开 ----
    peripherals_out: list[dict] = []
    registers_out: list[dict] = []
    reg_full_names: dict[str, dict] = {}  # 全名 → 寄存器 dict（位域挂接用）
    for m in _INSTANCE_RE.finditer(text):
        inst, type_name, base_macro = m.group(1), m.group(2) + "_TypeDef", m.group(3)
        members = structs.get(type_name)
        if not members or base_macro not in base_values:
            continue
        base = base_values[base_macro]
        peripherals_out.append(
            {
                "name": inst,
                "base_address": _hex(base),
                "end_address": None,
                "bus": _bus_of(base),
                "irqs": [],
                "description": f"实例化自 {type_name}（{header_path.name}）",
            }
        )
        for reg_name, access, offset, _ctype in members:
            reg = {
                "peripheral": inst,
                "name": f"{inst}_{reg_name}",
                "address": _hex(base + offset),
                "offset": _hex(offset),
                "access": access,
                "reset_value": None,
                "description": "",
                "bitfields": [],
            }
            registers_out.append(reg)
            reg_full_names[reg["name"].upper()] = reg

    if not peripherals_out:
        result["warnings"].append(f"头文件中未解析到外现实例: {header_path}")
        return result
    result["peripherals"] = peripherals_out
    result["registers"] = registers_out

    # ---- 4. IRQn → 外设挂接（前缀匹配；条件编译分支会产生重复定义，去重）----
    seen_irq: set[tuple[str, int]] = set()
    for im in _IRQ_RE.finditer(text):
        iname, num = im.group(1), int(im.group(2))
        if num < 0 or (iname, num) in seen_irq:  # Cortex-M 内核异常 / 重复定义
            continue
        seen_irq.add((iname, num))
        for p in peripherals_out:
            if iname.upper().startswith(p["name"].upper()):
                p["irqs"].append({"name": iname, "number": num})
                break

    # ---- 5. 位域掩码 → 挂接到寄存器 ----
    #    过滤规则：同寄存器前缀下，若位域名以「另一个更短位域名_」开头，
    #    视为枚举值/位分量（如 SW_HSI、SW_0），丢弃
    fields_by_reg: dict[str, dict[str, dict]] = {}  # reg 全名 → field 名 → {bits, desc}
    for bm in _MASK_RE.finditer(text):
        macro_name, mask_val = bm.group(1), int(bm.group(2), 0)
        bits = _bits_from_mask(mask_val)
        if bits is None:
            continue
        # 最长寄存器前缀匹配
        upper = macro_name.upper()
        matched_reg = ""
        for full in reg_full_names:
            if upper.startswith(full + "_") and len(full) > len(matched_reg):
                matched_reg = full
        if not matched_reg:
            continue
        field_name = upper[len(matched_reg) + 1:]
        fields_by_reg.setdefault(matched_reg, {})[field_name] = {"bits": bits, "mask": mask_val}

    for reg_upper, fields in fields_by_reg.items():
        keep = [
            (fname, info)
            for fname, info in fields.items()
            if not any(other != fname and fname.startswith(other + "_") for other in fields)
        ]
        for fname, info in keep:
            reg_full_names[reg_upper]["bitfields"].append(
                {"name": fname, "bits": info["bits"], "access": reg_full_names[reg_upper]["access"],
                 "reset_value": None, "description": ""}
            )

    # ---- 6. 时钟树（从 RCC 位域掩码推导）----
    result["clock_tree"] = _clock_tree_from_sdk(reg_full_names)
    if result["clock_tree"] is None:
        result["warnings"].append("头文件中未找到 RCC 位域掩码（时钟树配置要素缺失）")
    return result


def _clock_tree_from_sdk(reg_full_names: dict[str, dict]) -> dict | None:
    """从 RCC 寄存器位域推导时钟树配置要素（与 svd_source 同构）。"""
    enables: list[dict] = []
    for reg_name, bus in (("RCC_AHBENR", "AHB"), ("RCC_APB1ENR", "APB1"), ("RCC_APB2ENR", "APB2")):
        reg = reg_full_names.get(reg_name)
        if not reg or not reg.get("bitfields"):
            continue
        for bf in reg["bitfields"]:
            enables.append(
                {
                    "peripheral": _peripheral_of_en(bf["name"]),
                    "field": bf["name"],
                    "register": reg_name,
                    "bus": bus,
                }
            )
    prescalers: list[dict] = []
    cfgr = reg_full_names.get("RCC_CFGR")
    if cfgr:
        for bf in cfgr.get("bitfields", []):
            bus = _PRESCALER_BUS.get(bf["name"].upper())
            if bus:
                prescalers.append(
                    {"bus": bus, "field": bf["name"], "register": "RCC_CFGR", "division_range": ""}
                )
    if not enables and not prescalers:
        return None
    return {
        "clock_sources": [
            {"name": "HSE", "frequency_range": "4-16 MHz", "typical": "8 MHz", "notes": ""},
            {"name": "HSI", "frequency_range": "8 MHz", "typical": "8 MHz", "notes": "出厂校准"},
            {"name": "LSE", "frequency_range": "32.768 kHz", "typical": "32.768 kHz", "notes": ""},
            {"name": "LSI", "frequency_range": "40 kHz", "typical": "40 kHz", "notes": "低功耗内部 RC"},
        ],
        "pll": {"source": "HSE/HSI", "multiplier_field": "PLLMUL", "multiplier_range": "x2..x16"},
        "bus_prescalers": prescalers,
        "peripheral_clock_enables": enables,
    }
