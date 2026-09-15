#!/usr/bin/env python
"""CMSIS-SVD 解析模块（S3 优先数据源）。

SVD（System View Description）是 ARM CMSIS 标准的机器可读芯片描述（XML），
包含全部外设、寄存器、位域、中断、复位值——相比解析上千页 PDF 参考手册
（尽力而为、覆盖不全），一次 XML 解析即可得到权威完整数据。

本模块将 SVD 转换为 datasheet-extractor 的统一结构：
{peripherals, registers, clock_tree, warnings}

适用于所有 CMSIS-SVD 兼容文件（STM32 / GD32 / 国产带 SVD 的厂商）。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

# 总线地址范围（Cortex-M 通用 memory map，用于外设总线归属推断）
BUS_RANGES = (
    ("APB1", 0x40000000, 0x4000FFFF),
    ("APB2", 0x40010000, 0x40013FFF),
    ("AHB", 0x40018000, 0x5FFFFFFF),
)

# SVD access → 统一读写权限
ACCESS_MAP = {
    "read-write": "rw",
    "read-only": "r",
    "write-only": "w",
    "writeOnce": "w",
    "read-writeOnce": "rw",
}

# CFGR 分频/时钟选择位段 → 总线
_PRESCALER_BUS = {
    "HPRE": "AHB", "PPRE1": "APB1", "PPRE2": "APB2",
    "ADCPRE": "ADC", "USBPRE": "USB",
    "PLLMUL": "SYSCLK", "PLLSRC": "SYSCLK",
    "MCO": "SYSCLK", "SW": "SYSCLK", "SWS": "SYSCLK",
}

_INT_RE = re.compile(r"[+-]?(0[xX][0-9a-fA-F]+|\d+)")


def _to_int(text: str | None, default: int = 0) -> int:
    """SVD 数值解析（支持 0x 十六进制 / 十进制）。"""
    if text is None:
        return default
    m = _INT_RE.search(str(text))
    if not m:
        return default
    s = m.group(0)
    return int(s, 16) if s.lower().startswith(("0x", "-0x", "+0x")) else int(s, 10)


def _hex(value: int) -> str:
    return hex(value)


def _bus_of(addr: int) -> str | None:
    for bus, lo, hi in BUS_RANGES:
        if lo <= addr <= hi:
            return bus
    return None


def _field_bits(field: ET.Element) -> str | None:
    """位域位置：bitOffset/bitWidth、bitRange [msb:lsb]、lsb/msb 三种写法。"""
    br = field.findtext("bitRange")
    if br:
        m = re.match(r"\[(\d+):(\d+)\]", br.strip())
        if m:
            msb, lsb = int(m.group(1)), int(m.group(2))
            return f"{msb}:{lsb}" if msb != lsb else str(msb)
    if field.find("bitOffset") is not None or field.find("bitWidth") is not None:
        off = _to_int(field.findtext("bitOffset"))
        width = _to_int(field.findtext("bitWidth"), 1)
        return f"{off + width - 1}:{off}" if width > 1 else str(off)
    if field.find("lsb") is not None or field.find("msb") is not None:
        lsb = _to_int(field.findtext("lsb"))
        msb = _to_int(field.findtext("msb"))
        return f"{msb}:{lsb}" if msb != lsb else str(msb)
    return None


def _bits_span(bits: str) -> tuple[int, int] | None:
    """'7:4' / '5' → (msb, lsb)。"""
    m = re.match(r"^(\d+)(?::(\d+))?$", bits)
    if not m:
        return None
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) is not None else a
    return (max(a, b), min(a, b))


def _peripheral_of_en(field_name: str) -> str:
    """RCC 使能位段名还原外设名：IOPAEN→GPIOA、USART1EN→USART1。"""
    stem = field_name[:-2] if field_name.upper().endswith("EN") else field_name
    if stem.startswith("IOP"):
        return f"GPIO{stem[3:]}"
    if stem.startswith("USB"):
        return "USB"
    return stem


def _regs_of(peripheral: ET.Element) -> list[ET.Element]:
    """外设下的寄存器元素（含 cluster 展开一层）。"""
    out: list[ET.Element] = []
    regs = peripheral.find("registers")
    if regs is None:
        return out
    for child in regs:
        if child.tag == "register":
            out.append(child)
        elif child.tag == "cluster":
            for sub in child.findall("register"):
                out.append(sub)
    return out


def _iter_peripherals(root: ET.Element) -> list[ET.Element]:
    per = root.find("peripherals")
    if per is None:
        return []
    return [p for p in per if p.tag == "peripheral"]


def parse_svd(svd_path: Path) -> dict:
    """解析 SVD → {peripherals, registers, clock_tree, warnings}。"""
    result: dict = {"peripherals": [], "registers": [], "clock_tree": None, "warnings": []}
    try:
        tree = ET.parse(svd_path)
    except ET.ParseError as exc:
        result["warnings"].append(f"SVD 解析失败（XML 语法错误）: {exc}")
        return result
    root = tree.getroot()
    device_name = root.findtext("name") or svd_path.stem

    # ---- 第一遍：建立无继承外设的寄存器字典（供 derivedFrom 复制） ----
    periph_elements = _iter_peripherals(root)
    reg_cache: dict[str, list[ET.Element]] = {}
    for p in periph_elements:
        name = (p.findtext("name") or "").strip()
        if name and p.get("derivedFrom") is None:
            reg_cache[name] = _regs_of(p)

    peripherals_out: list[dict] = []
    registers_out: list[dict] = []

    for p in periph_elements:
        pname = (p.findtext("name") or "").strip()
        if not pname:
            continue
        desc = (p.findtext("description") or "").strip().split("\n")[0][:200]
        base = _to_int(p.findtext("baseAddress"))

        # derivedFrom：复制源外设的寄存器/中断，基地址用自身（缺省时）
        derived = p.get("derivedFrom")
        reg_elements = (
            reg_cache.get(derived, []) if derived and derived not in reg_cache else None
        )
        if reg_elements is None:
            reg_elements = reg_cache.get(pname) or _regs_of(p)

        # 中断（derivedFrom 外设可能不带中断，自身声明优先）
        irqs: list[dict] = []
        for irq in p.findall("interrupt"):
            iname = (irq.findtext("name") or "").strip()
            ival = irq.findtext("value")
            if iname and ival is not None:
                irqs.append({"name": iname, "number": _to_int(ival)})

        peripherals_out.append(
            {
                "name": pname,
                "base_address": _hex(base),
                "end_address": None,
                "bus": _bus_of(base),
                "irqs": irqs,
                "description": desc,
            }
        )

        # ---- 寄存器 ----
        for reg in reg_elements:
            rname = (reg.findtext("name") or "").strip()
            if not rname:
                continue
            offset = _to_int(reg.findtext("addressOffset"))
            size = _to_int(reg.findtext("size"), 32)
            access = ACCESS_MAP.get((reg.findtext("access") or "").strip(), "rw")
            reset = _to_int(reg.findtext("resetValue"))
            rdesc = (reg.findtext("description") or "").strip().replace("\n", " ")[:200]
            # 全名：外设名 + 寄存器名（RCC + APB2ENR → RCC_APB2ENR）
            full_name = rname if rname.upper().startswith(pname.upper()) else f"{pname}_{rname}"

            bitfields: list[dict] = []
            fields = reg.find("fields")
            if fields is not None:
                for f in fields.findall("field"):
                    fname = (f.findtext("name") or "").strip()
                    bits = _field_bits(f)
                    if not fname or bits is None:
                        continue
                    span = _bits_span(bits)
                    frst: str | None = None
                    # 复位值：优先字段自身声明，否则从寄存器复位值截取位段
                    if f.findtext("resetValue") is not None:
                        frst = _hex(_to_int(f.findtext("resetValue")))
                    elif span and size:
                        frst = _hex((reset >> span[1]) & ((1 << (span[0] - span[1] + 1)) - 1))
                    fdesc = (f.findtext("description") or "").strip().replace("\n", " ")[:160]
                    bitfields.append(
                        {
                            "name": fname,
                            "bits": bits,
                            "access": ACCESS_MAP.get((f.findtext("access") or "").strip(), access),
                            "reset_value": frst,
                            "description": fdesc,
                        }
                    )

            registers_out.append(
                {
                    "peripheral": pname,
                    "name": full_name,
                    "address": _hex(base + offset),
                    "offset": _hex(offset),
                    "access": access,
                    "reset_value": _hex(reset),
                    "description": rdesc,
                    "bitfields": bitfields,
                }
            )

    if not peripherals_out:
        result["warnings"].append(f"SVD 中未解析到外设: {svd_path}")
        return result

    result["peripherals"] = peripherals_out
    result["registers"] = registers_out

    # ---- 时钟树（从 RCC 寄存器位域推导） ----
    clock_tree = _clock_tree_from_svd(peripherals_out, registers_out, device_name)
    if clock_tree:
        result["clock_tree"] = clock_tree
    else:
        result["warnings"].append("SVD 中未找到 RCC 寄存器（时钟树配置要素缺失）")
    return result


def _clock_tree_from_svd(
    peripherals: list[dict], registers: list[dict], device_name: str
) -> dict | None:
    """从 RCC 寄存器位域推导时钟树配置要素。

    - peripheral_clock_enables：AHBENR / APB1ENR / APB2ENR 的使能位段
    - bus_prescalers：CFGR 的分频/时钟选择位段
    - clock_sources / PLL：SVD 不含频率信息，使用平台默认（文档知识）
    """
    rcc_regs = {
        r["name"].upper(): r
        for r in registers
        if r["peripheral"].upper() == "RCC"
    }
    if not rcc_regs:
        return None

    enables: list[dict] = []
    for reg_name, bus in (("AHBENR", "AHB"), ("APB1ENR", "APB1"), ("APB2ENR", "APB2")):
        reg = rcc_regs.get(f"RCC_{reg_name}") or rcc_regs.get(reg_name)
        if not reg:
            continue
        for bf in reg.get("bitfields", []):
            enables.append(
                {
                    "peripheral": _peripheral_of_en(bf["name"]),
                    "field": bf["name"],
                    "register": f"RCC_{reg_name}",
                    "bus": bus,
                }
            )

    prescalers: list[dict] = []
    cfgr = rcc_regs.get("RCC_CFGR") or rcc_regs.get("CFGR")
    if cfgr:
        for bf in cfgr.get("bitfields", []):
            bus = _PRESCALER_BUS.get(bf["name"].upper())
            if bus:
                prescalers.append(
                    {
                        "bus": bus,
                        "field": bf["name"],
                        "register": "RCC_CFGR",
                        "division_range": "",
                    }
                )

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
