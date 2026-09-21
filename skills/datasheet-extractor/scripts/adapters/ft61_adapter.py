"""辉芒微 FT61F 系列适配器（8 位机，单手册模式）。

数据源：datasheet PDF（必需）——FT61F 无 SVD/CMSIS SDK，手册兼作参考手册
（单手册模式，产物 source.reference_manual 为 null，寄存器为 SFR 模型：
peripherals.base_address=null、registers.offset=null、address=单字节地址）。

手册结构（ft61f14x_ds_rev1p0x_cn.pdf，中文）：
- 目录在前 14 页（条目带点线页码，需跳过）
- 1.2 管脚描述：表头 [TSSOP20, Pin name, Type, INT, -, -, Main func., Default AF]，
  引脚行首列为引脚号，说明行首列为空；Pin name 以 "/" 分隔复用功能，[xxx] 为重映射
- 寄存器详情：标题 "6.5.1. INTCON 寄存器，地址 0x0B"（多地址取第一个）；
  同页位域表 4 行（Bit/Name/Reset/Type × 8 列，bit7..bit0）
  + 说明表（Bit/Name/Function）
- 章节号 → 外设映射（中断6/EEPROM8/ADC9/TIM1=10/TIM2=11/TIM4=12/USART13/GPIO14/WDT15...）

提取尽力而为（best effort）：位域表缺失/解析失败的寄存器保留名+地址，
位域留空并记 warnings。
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

# 章节号 → 外设（FT61F14X 手册固定章节结构）
_CHAPTER_PERIPH = {
    "4": "RSTC", "5": "OSC", "6": "INTC", "7": "SLEEP", "8": "EEPROM",
    "9": "ADC", "10": "TIM1", "11": "TIM2", "12": "TIM4", "13": "USART",
    "14": "GPIO", "15": "WDT", "16": "MSCK",
}

# 寄存器详情标题三种变体（全兼容）：
#   6.5.1. INTCON 寄存器，地址 0x0B（带"寄存器"）
#   10.4.9. TIM1CR1，地址：0x211（无"寄存器"+全角冒号）
#   9.4.6. ADDLY/LEBPRL，地址 0x1F（斜杠双名，保留全名）
_REG_TITLE_RE = re.compile(
    r"(\d+(?:\.\d+)*)\.?\s+([A-Z][A-Z0-9_/]*[A-Z0-9])\s*(?:寄存器)?\s*，\s*地址[：:]?\s*(0x[0-9A-Fa-f]+)")

# 时钟源（手册 5.x：HIRC 16M / LIRC 32K|256K / XT 32.768k 音叉 / EC 外部灌入）
_CLOCK_SOURCES = [
    {"name": "HIRC", "typical": "16 MHz", "frequency_range": "16 MHz",
     "notes": "内部高速精准振荡器，上电默认时钟源"},
    {"name": "LIRC", "typical": "32 kHz / 256 kHz", "frequency_range": "32 kHz / 256 kHz",
     "notes": "内部低速低功耗振荡器，双档可选"},
    {"name": "HXTAL", "typical": "外部输入，未限定", "frequency_range": "外部时钟/晶体，未限定",
     "notes": "EC 模式外部时钟灌入 / XT 模式外部晶体（OSCCON.SCS 选择）"},
    {"name": "LXTAL", "typical": "32.768 kHz", "frequency_range": "32.768 kHz",
     "notes": "XT 模式音叉式晶振（手表晶振）"},
]


def _clean(cell) -> str:
    return str(cell).replace("\n", "").strip() if cell is not None else ""


def _norm_access(txt: str) -> str:
    """手册访问类型 → schema 枚举：RW→rw、RO(-x)→r、WO→w、RC*→rc_w1，其余空。"""
    t = (txt or "").upper().rstrip("-01")
    if t == "RW":
        return "rw"
    if t.startswith("RO"):
        return "r"
    if t == "W":
        return "w"
    if t.startswith("WO"):
        return "w"
    if t.startswith("RC"):
        return "rc_w1"
    return ""


class FT61Adapter:
    """FT61F datasheet 单手册提取（引脚 / SFR 寄存器 / 外设 / 极简时钟树）。"""

    KEY_PREFIX = "ft61"

    def __init__(self, platform: str):
        self.platform = platform

    def extract(
        self,
        datasheet: Path,
        secondary: Path | None,
        scope: str,
        svd: Path | None = None,
        sdk_header: Path | None = None,
    ) -> dict:
        warnings: list[str] = []
        if svd is not None or sdk_header is not None:
            warnings.append("FT61F 无 SVD/CMSIS SDK 数据源，全部来自 datasheet 单手册模式")

        result: dict = {
            "mcu_family": "FT61F14X",
            "package": None,
            "pin_count": 0,
            "pins": [], "registers": [], "peripherals": [], "clock_tree": {},
            "warnings": warnings,
        }
        if scope in ("pins", "all"):
            self._extract_pins(pdfplumber.open(datasheet), result, warnings)
        if scope in ("registers", "peripherals", "clocks", "all"):
            self._extract_registers(pdfplumber.open(datasheet), result, warnings)
            self._build_peripherals(result)
        if scope in ("clocks", "all"):
            self._build_clock_tree(result)
        return result

    # ------------------------------------------------------------------
    # 引脚：1.2 管脚描述表（跨页合并）
    # ------------------------------------------------------------------

    def _extract_pins(self, pdf, result: dict, warnings: list[str]) -> None:
        pages = []
        in_section = False
        for page in pdf.pages[14:]:  # 跳过目录（前 14 页）
            text = page.extract_text() or ""
            if "管脚描述" in text:
                in_section = True
            if in_section and "程序存储器" in text:
                break
            if in_section:
                pages.append(page)
        if not pages:
            warnings.append("未定位 '管脚描述' 章节，引脚未提取")
            return

        pins: list[dict] = []
        package = None
        for page in pages:
            for table in page.extract_tables():
                if not table or _clean(table[0][1]) != "Pin name":
                    continue
                if package is None:
                    package = _clean(table[0][0]) or None
                for row in table[1:]:
                    num, name_full, type_raw = _clean(row[0]), _clean(row[1]), _clean(row[2])
                    if not num.isdigit() or not name_full:
                        continue
                    segs = [s.strip() for s in name_full.split("/") if s.strip()]
                    name = segs[0]
                    alt, remap = [], []
                    for seg in segs[1:]:
                        m = re.match(r"^\[(.+)\]$", seg)
                        (remap if m else alt).append(m.group(1) if m else seg)
                    default_af = _clean(row[7]) if len(row) > 7 else ""
                    if default_af and default_af not in alt and default_af != name:
                        alt.append(default_af)
                    pins.append({
                        "pin": int(num),
                        "name": name,
                        "pin_type": "IO" if type_raw.upper() == "IO" else "POWER",
                        "pin_type_raw": type_raw,
                        "main_function": _clean(row[6]) if len(row) > 6 else name,
                        "alternate_functions": alt,
                        "alternate_functions_remap": remap,
                    })
        if not pins:
            warnings.append("管脚描述表解析为空，引脚未提取")
            return
        pins.sort(key=lambda p: p["pin"])
        result["pins"] = pins
        result["package"] = package
        result["pin_count"] = max(p["pin"] for p in pins)

    # ------------------------------------------------------------------
    # 寄存器：全篇扫标题 + 同页位域表
    # ------------------------------------------------------------------

    def _extract_registers(self, pdf, result: dict, warnings: list[str]) -> None:
        regs: dict[tuple[str, str], dict] = {}  # (name, address) -> entry
        for page in pdf.pages[14:]:  # 跳过目录
            text = page.extract_text() or ""
            titles: list[tuple[str, str, str]] = []  # (chapter, name, address)
            for ln in text.splitlines():
                if "..." in ln:  # 目录点线（保险）
                    continue
                m = _REG_TITLE_RE.search(ln)
                if m:
                    titles.append((m.group(1), m.group(2), m.group(3)))
            if not titles:
                continue
            tables = page.extract_tables()
            for chapter, name, address in titles:
                key = (name, address)
                if key in regs:
                    continue
                periph = _CHAPTER_PERIPH.get(chapter.split(".")[0], "SYSTEM")
                entry = {
                    "peripheral": periph, "name": name, "address": address,
                    "offset": None, "access": "", "description": f"章节 {chapter}",
                    "bitfields": [],
                }
                bf = self._parse_bitfields(tables)
                if bf:
                    entry["bitfields"] = bf["fields"]
                    entry["access"] = bf["access"]
                else:
                    warnings.append(f"寄存器 {name}({address}) 位域表未解析")
                regs[key] = entry
        result["registers"] = list(regs.values())

    def _parse_bitfields(self, tables: list) -> dict | None:
        """识别位域表（首行首列 Bit，第二行 Name）+ 说明表（Bit/Name/Function）。"""
        bf_table = desc_table = None
        for t in tables:
            head = [_clean(c) for c in (t[0] if t else [])]
            if head[:2] == ["Bit", "Name"] and len(head) >= 3:
                desc_table = t
            elif head and head[0] == "Bit" and len(t) >= 3:
                bf_table = t
        if not bf_table:
            return None

        bit_row = [_clean(c) for c in bf_table[0]]
        names_row = [_clean(c) for c in bf_table[1]] if len(bf_table) > 1 else []
        reset_row = [_clean(c) for c in bf_table[2]] if len(bf_table) > 2 else []
        type_row = [_clean(c) for c in bf_table[3]] if len(bf_table) > 3 else []
        n = len(bit_row) - 1  # 位宽（bit7..bit0 或 bit15..bit0）
        if n <= 0 or len(names_row) - 1 != n:
            return None

        func_by_name: dict[str, str] = {}
        if desc_table:
            for row in desc_table[1:]:
                bits_txt, nm, fn = _clean(row[0]), _clean(row[1]), _clean(row[2])
                if nm and nm not in func_by_name and fn:
                    func_by_name[nm] = f"{fn[:60]}（bit {bits_txt}）" if fn else ""

        fields, access = [], None
        i = 1  # bit_row[1..n] 从 MSB 到 LSB
        while i <= n:
            nm = names_row[i] if i < len(names_row) else ""
            bit_no = bit_row[i]
            if nm in ("—", "-", "", "N/A"):  # 未实现位 / 跨列段延续位
                i += 1
                continue
            j = i
            while j + 1 <= n and (names_row[j + 1] if j + 1 < len(names_row) else "") == "":
                j += 1  # 空列延续（跨列位段，如 T1CMS[1:0] 占 bit6:5）
            base = re.sub(r"\[\d+:\d+\]$", "", nm) or nm
            fields.append({
                "name": base,
                "bits": bit_row[i] if i == j else f"{bit_row[j]}:{bit_row[i]}",
                "access": _norm_access(type_row[i] if i < len(type_row) else ""),
                "reset_value": (reset_row[i] if i < len(reset_row) else "") or None,
                "description": func_by_name.get(base, ""),
            })
            if not access and i < len(type_row) and type_row[i]:
                access = _norm_access(type_row[i])
            i = j + 1
        fields.reverse()  # 按位号升序输出
        return {"fields": fields, "access": access or ""}

    # ------------------------------------------------------------------
    # 外设清单（章节映射，SFR 模型 base_address=null）
    # ------------------------------------------------------------------

    def _build_peripherals(self, result: dict) -> None:
        periph_regs: dict[str, list[dict]] = {}
        for r in result["registers"]:
            periph_regs.setdefault(r["peripheral"], []).append(r)
        peripherals = []
        for name in sorted(periph_regs):
            if name == "SYSTEM":
                continue
            peripherals.append({
                "name": name, "base_address": None, "end_address": None,
                "bus": None, "irqs": [],
                "description": f"SFR 模型，含 {len(periph_regs[name])} 个寄存器",
            })
        result["peripherals"] = peripherals

    # ------------------------------------------------------------------
    # 时钟树（极简：HIRC/LIRC/XT/EC + MCKCF 频率选择）
    # ------------------------------------------------------------------

    def _build_clock_tree(self, result: dict) -> None:
        regs = {r["name"]: r for r in result["registers"]}
        osccon = regs.get("OSCCON")
        result["clock_tree"] = {
            "clock_sources": [dict(cs) for cs in _CLOCK_SOURCES],
            "bus_prescalers": [],
            "peripheral_clock_enables": [],
            "notes": "8 位机 SFR 直访，无总线分频/外设时钟门控；"
                     "系统时钟源与频率由 OSCCON.MCKCF 位段选择"
                     + (f"（地址 {osccon['address']}）" if osccon else ""),
        }


__all__ = ["FT61Adapter"]
