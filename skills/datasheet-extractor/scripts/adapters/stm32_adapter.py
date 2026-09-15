"""STM32 系列手册提取适配器。

数据源：
- datasheet（必需）：引脚定义表（"pin definitions" 章节的跨页大表）、
  封装列头（竖排文本反转得到 LQFP144 等）
- reference manual（可选）：寄存器边界地址表（Table 2 风格）、
  中断向量表（Table 61/63）、寄存器描述章节（"Address offset:" 标准行 +
  位域图坐标对齐）、RCC 位域（时钟树配置要素）

提取是尽力而为（best effort）：无法解析的章节跳过并记入 warnings，
由主入口汇总为 partial 状态，供下游 S4/S5 判断数据可用性。

性能策略：单次顺序扫描（每页仅 extract_text 做文本预筛），
命中页再按需做 extract_tables / extract_words 深度解析。
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

# ST 封装引脚数代码（STM32F103ZET6 → Z=144）
ST_PIN_COUNT_CODE = {
    "F": 20, "G": 28, "K": 32, "T": 36, "C": 48,
    "R": 64, "V": 100, "Z": 144, "I": 176, "B": 208, "N": 216,
}
# ST 封装代码（T=LQFP 等；未知封装回退为仅引脚数）
ST_PACKAGE_CODE = {
    "T": "LQFP", "H": "LFBGA", "U": "UFQFPN", "Y": "WLCSP",
    "I": "VFBGA", "P": "TSSOP",
}

# 总线地址范围（STM32F1 memory map，用于外设总线归属推断）
BUS_RANGES = (
    ("APB1", 0x40000000, 0x4000FFFF),
    ("APB2", 0x40010000, 0x40013FFF),
    ("AHB", 0x40018000, 0x5003FFFF),
)

_HEX_RE = re.compile(r"0[xX][0-9a-fA-F]{2,}")
_BITS_RE = re.compile(r"\d+\s*[:\-]\s*\d+|\b\d{1,2}\b")
_NAME_EN_RE = re.compile(r"^[A-Z][A-Z0-9_]*EN$")
_BITFIELD_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]*\[\d+:\d+\]$")
# CFGR 分频/时钟选择位段
_PRESCALER_FIELDS = ("HPRE", "PPRE1", "PPRE2", "ADCPRE", "USBPRE", "PLLMUL", "PLLSRC", "PLLMUL", "MCO", "SW", "SWS")
# 外设章节标题：如 "9.2 GPIO registers" / "7.3 RCC registers"
_PERIPH_SEC_RE = re.compile(r"^\d+\.\d+\s+(.+?)\s+registers?\b")
# 寄存器小节标题：如 "9.2.1 Port configuration register low (GPIOx_CRL) (x=A..G)"
_REG_SEC_RE = re.compile(r"^\d+\.\d+\.\d+\s+(.*)$")
# 标题括号内寄存器缩写：如 (GPIOx_CRL)
_ABBR_RE = re.compile(r"\(([A-Z][A-Za-z0-9_]{1,24})\)")


def _clean(cell) -> str:
    """单元格清洗：去换行/首尾空白。"""
    if cell is None:
        return ""
    return str(cell).replace("\n", "").strip()


def parse_platform(platform: str) -> tuple[str, str | None, int | None]:
    """从 platform 名解析 (mcu_family, package_hint, pin_count_hint)。

    stm32f103zet6 → ("STM32F1", "LQFP144", 144)
    """
    m = re.match(r"^stm32(f\d)(\w+)", platform.lower())
    family = f"STM32{m.group(1).upper()}" if m else platform.upper()
    package = None
    pin_count = None
    m2 = re.match(r"^stm32f\d{3}(\w)(\w)(\w)\d*$", platform.lower())
    if m2:
        pin_code, pkg_code = m2.group(1).upper(), m2.group(3).upper()
        pin_count = ST_PIN_COUNT_CODE.get(pin_code)
        pkg = ST_PACKAGE_CODE.get(pkg_code)
        if pin_count and pkg:
            package = f"{pkg}{pin_count}"
    return family, package, pin_count


def _bus_of(addr: int) -> str | None:
    for bus, lo, hi in BUS_RANGES:
        if lo <= addr <= hi:
            return bus
    return None


class STM32Adapter:
    """STM32 datasheet / reference manual 提取。"""

    KEY_PREFIX = "stm32"

    def __init__(self, platform: str):
        self.platform = platform

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def extract(
        self,
        datasheet: Path,
        secondary: Path | None,
        scope: str,
        svd: Path | None = None,
        sdk_header: Path | None = None,
    ) -> dict:
        """提取入口。返回统一结构：
        {pins, registers, peripherals, clock_tree, package, pin_count,
         mcu_family, warnings}

        数据源优先级：SVD（含复位值/完整位域）> SDK 头文件（厂商必提供）
        > 参考手册 PDF（兜底）。
        引脚定义始终来自 datasheet PDF（SVD/头文件不含物理引脚表）。
        """
        family, package_hint, pin_count_hint = parse_platform(self.platform)
        result = {
            "mcu_family": family,
            "package": package_hint,
            "pin_count": pin_count_hint,
            "pins": [],
            "registers": [],
            "peripherals": [],
            "clock_tree": None,
            "warnings": [],
        }
        need_pins = scope in ("pins", "all")
        need_chip = scope in ("registers", "clocks", "peripherals", "all")

        if need_pins:
            self._extract_pins(datasheet, result, package_hint)

        if not need_chip:
            return result

        # 优先级 1：SVD（CMSIS-SVD，含复位值与完整位域）
        if svd is not None:
            try:
                from svd_source import parse_svd

                svd_data = parse_svd(svd)
                result["warnings"].extend(svd_data.get("warnings") or [])
                if svd_data.get("peripherals"):
                    result["peripherals"] = svd_data["peripherals"]
                    result["registers"] = svd_data["registers"]
                    result["clock_tree"] = svd_data.get("clock_tree")
                    return result
                result["warnings"].append("SVD 解析无产物，尝试 SDK 头文件")
            except ImportError:
                pass
            except Exception as exc:
                result["warnings"].append(f"SVD 解析异常，尝试 SDK 头文件: {exc}")

        # 优先级 2：SDK 头文件（厂商必提供，寄存器/地址/中断权威，
        # 位域与复位值覆盖视头文件而定，普遍不如 SVD 完整）
        if sdk_header is not None:
            try:
                from sdk_source import parse_sdk_header

                sdk_data = parse_sdk_header(sdk_header)
                result["warnings"].extend(sdk_data.get("warnings") or [])
                if sdk_data.get("peripherals"):
                    result["peripherals"] = sdk_data["peripherals"]
                    result["registers"] = sdk_data["registers"]
                    result["clock_tree"] = sdk_data.get("clock_tree")
                    return result
                result["warnings"].append("SDK 头文件解析无产物，回退参考手册 PDF")
            except ImportError:
                pass
            except Exception as exc:
                result["warnings"].append(f"SDK 头文件解析异常，回退参考手册 PDF: {exc}")

        # 优先级 3：参考手册 PDF（启发式页面选择）
        if secondary is None:
            result["warnings"].append(
                "未提供 SVD（svd_path）/ SDK 头文件（sdk_header_path）/"
                "参考手册（datasheet_secondary_path），寄存器映射/时钟树/外设清单未提取"
            )
            return result

        self._extract_from_rm(secondary, result)
        return result

    # ------------------------------------------------------------------
    # 引脚定义（datasheet）
    # ------------------------------------------------------------------

    def _extract_pins(self, datasheet: Path, result: dict, package_hint: str | None) -> None:
        """提取 "pin definitions" 跨页表格。"""
        try:
            with pdfplumber.open(datasheet) as pdf:
                pin_rows: list[dict] = []
                pkg_col: tuple[int, str] | None = None
                found_pages = 0

                for page in pdf.pages:
                    text = (page.extract_text() or "").lower()
                    if "pin definitions" not in text:
                        continue
                    tables = page.extract_tables()
                    if not tables:
                        continue
                    table = max(tables, key=len)  # 取最大表（引脚表是页内主表）
                    if len(table) < 3 or len(table[0]) < 10:
                        continue
                    found_pages += 1
                    if pkg_col is None:
                        pkg_col = self._detect_package_col(table[1], package_hint)
                        if pkg_col is None:
                            result["warnings"].append(
                                "未能识别封装列（表头无 LQFP 列），跳过引脚提取"
                            )
                            return
                    self._collect_pin_rows(table, pkg_col[0], pin_rows)

                if not found_pages:
                    result["warnings"].append(
                        f"datasheet 中未找到 'pin definitions' 表格: {datasheet}"
                    )
                    return

                # 按引脚号去重排序
                seen: dict[int, dict] = {}
                for row in pin_rows:
                    seen.setdefault(row["pin"], row)
                pins = [seen[k] for k in sorted(seen)]

                # 封装与引脚数交叉确认（PDF 列头优先）
                if pkg_col:
                    result["package"] = pkg_col[1]
                    result["pin_count"] = int(
                        re.sub(r"\D", "", pkg_col[1]) or 0
                    ) or result.get("pin_count")
                result["pins"] = pins
        except Exception as exc:  # PDF 解析异常不能中断其他范围
            result["warnings"].append(f"引脚定义提取失败: {exc}")

    @staticmethod
    def _detect_package_col(header_row, package_hint: str | None) -> tuple[int, str] | None:
        """从封装表头行识别目标封装列。

        表头为竖排文本，反转后形如 LQFP144 / LFBGA144 / WLCSP64。
        优先匹配 platform 推断的封装；匹配不到则取第一个 LQFP 列。
        """
        candidates: list[tuple[int, str]] = []
        for idx, cell in enumerate(header_row[:6]):
            label = _clean(cell)
            if not label:
                continue
            label = label[::-1].upper()  # 竖排反转：441PFQL → LQFP144
            if label.startswith(("LQFP", "BGA", "WLCSP", "UFQFPN")):
                candidates.append((idx, label))
        if not candidates:
            return None
        if package_hint:
            for idx, label in candidates:
                if label == package_hint.upper():
                    return idx, label
        for idx, label in candidates:
            if label.startswith("LQFP"):
                return idx, label
        return candidates[0]

    @staticmethod
    def _collect_pin_rows(table: list, pin_col: int, out: list) -> None:
        """从单个表格页收集引脚行（跳过 2 行表头）。

        列布局（高密度 datasheet Table 5，12 列）：
        0-5 封装引脚位 | 6 pin name | 7 type | 8 io level | 9 main | 10 alt default | 11 alt remap
        """
        for row in table[2:]:
            if not row:
                continue
            raw_no = _clean(row[pin_col]) if pin_col < len(row) else ""
            if not raw_no.isdigit():
                continue
            name = _clean(row[6]) if len(row) > 6 else ""
            if not name:
                continue
            type_raw = _clean(row[7]) if len(row) > 7 else ""
            io_level = _clean(row[8]) if len(row) > 8 else ""
            main_func = _clean(row[9]) if len(row) > 9 else ""
            alt_raw = _clean(row[10]) if len(row) > 10 else ""
            remap_raw = _clean(row[11]) if len(row) > 11 else ""

            out.append(
                {
                    "pin": int(raw_no),
                    "name": name,
                    "pin_type": STM32Adapter._classify_pin(name, type_raw),
                    "pin_type_raw": type_raw,
                    "io_level": io_level,
                    "main_function": main_func,
                    "alternate_functions": [
                        p.strip() for p in alt_raw.split("/") if p.strip()
                    ],
                    "alternate_functions_remap": [
                        p.strip() for p in remap_raw.split("/") if p.strip()
                    ],
                }
            )

    @staticmethod
    def _classify_pin(name: str, type_raw: str) -> str:
        n = name.upper()
        if n.startswith("BOOT"):
            return "BOOT"
        if n == "NRST":
            return "NRST"
        if any(k in n for k in ("VDD", "VSS", "VREF", "VBAT")) or type_raw.strip() == "S":
            return "POWER"
        t = type_raw.strip()
        if t == "I/O":
            return "IO"
        if t == "I":
            return "INPUT"
        if t == "O":
            return "OUTPUT"
        return "UNKNOWN"

    # ------------------------------------------------------------------
    # 参考手册（单次扫描：文本预筛命中页再深度解析）
    # ------------------------------------------------------------------

    @staticmethod
    def _select_target_pages(rm: Path, total: int) -> set[int] | None:
        """启发式页面选择：读 PDF 书签（outline），按关键词定位目标章节页码集合。

        阶段 1（毫秒级）：pypdf 解析书签，匹配 寄存器/存储映射/中断向量/RCC/时钟
        相关章节的页码范围；阶段 2 只深扫目标页。
        书签不可用 / 无匹配时返回 None（退化为全页文本预筛）。
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            return None
        try:
            reader = PdfReader(str(rm))
            flat: list = []

            def _walk(items: list) -> None:
                for it in items:
                    if isinstance(it, list):
                        _walk(it)
                    else:
                        flat.append(it)

            _walk(reader.outline)
            marks: list[tuple[int, str]] = []
            for dest in flat:
                try:
                    marks.append(
                        (reader.get_destination_page_number(dest), str(dest.title).lower())
                    )
                except Exception:
                    continue
            if not marks:
                return None
            marks.sort()
            keywords = (
                "register", "memory map", "memory mapping",
                "vector table", "interrupt", "nvic", "rcc", "clock",
            )
            pages: set[int] = set()
            for i, (start, title) in enumerate(marks):
                if any(k in title for k in keywords):
                    end = marks[i + 1][0] if i + 1 < len(marks) else total - 1
                    pages.update(range(start, min(end, total - 1) + 1))
            return pages or None
        except Exception:
            return None

    def _extract_from_rm(self, rm: Path, result: dict) -> None:
        peripherals: dict[str, dict] = {}
        irq_all: dict[str, int] = {}
        irq_t63: dict[str, int] = {}
        registers: list[dict] = []
        rcc_en: dict[str, str] = {}     # field -> RCC_xxxENR
        rcc_pre: dict[str, str] = {}   # field -> RCC_CFGR
        try:
            with pdfplumber.open(rm) as pdf:
                target = self._select_target_pages(rm, len(pdf.pages))
                if target is not None:
                    result["warnings"].append(
                        f"启发式页面选择: 深扫 {len(target)}/{len(pdf.pages)} 页"
                        f"（书签定位，跳过 {len(pdf.pages) - len(target)} 页）"
                    )
                for idx, page in enumerate(pdf.pages):
                    if target is not None and idx not in target:
                        continue
                    text = page.extract_text() or ""
                    tlow = text.lower()
                    if "boundary address" in tlow and "peripheral" in tlow:
                        self._mem_map_page(page, peripherals)
                    if "vector table" in tlow:
                        self._irq_page(page, text, irq_all, irq_t63)
                    if "address offset" in tlow:
                        self._registers_page(page, text, registers)
                    if "RCC_" in text:
                        self._rcc_scan(text, rcc_en, rcc_pre)
        except Exception as exc:
            result["warnings"].append(f"参考手册提取失败: {exc}")
            return

        # ---- 汇总：IRQ 挂接（优先 Table 63 非 connectivity 版） ----
        irq_map = irq_t63 or irq_all
        for p in peripherals.values():
            key = p["name"].upper().replace(" ", "_")
            for acr, num in irq_map.items():
                au = acr.upper()
                if key.startswith(au) or au.startswith(key):
                    p.setdefault("irqs", []).append({"name": acr, "number": num})
        result["peripherals"] = list(peripherals.values())

        # ---- 汇总：寄存器地址合成（带 x 的通配寄存器不合成） ----
        bases: dict[str, str] = {}
        for p in peripherals.values():
            bases[p["name"].upper()] = p["base_address"]
        for r in registers:
            base = self._lookup_base(bases, r.get("peripheral") or "")
            if base and "x" not in r["name"].lower():
                try:
                    r["address"] = hex(int(base, 16) + int(r["offset"], 16))
                except (ValueError, TypeError):
                    r["address"] = None
            else:
                r["address"] = None
        result["registers"] = registers

        # ---- 汇总：时钟树 ----
        if rcc_en or rcc_pre:
            enables = [
                {
                    "peripheral": self._peripheral_of_en(field[:-2]),
                    "field": field,
                    "register": reg,
                    "bus": self._bus_of_enr(reg),
                }
                for field, reg in rcc_en.items()
            ]
            prescalers = [
                {
                    "bus": {"HPRE": "AHB", "PPRE1": "APB1", "PPRE2": "APB2"}.get(f, "SYSCLK"),
                    "field": f,
                    "register": reg,
                    "division_range": "",
                }
                for f, reg in rcc_pre.items()
            ]
            result["clock_tree"] = {
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

        # ---- warnings 汇总 ----
        if not peripherals:
            result["warnings"].append("参考手册中未找到寄存器边界地址表")
        if not registers:
            result["warnings"].append("参考手册中未提取到寄存器（Address offset 行）")
        if not (rcc_en or rcc_pre):
            result["warnings"].append("未提取到 RCC 位域（时钟树配置要素缺失）")

    # -- memory map 表（Boundary address | Peripheral | Bus | Register map） --

    @staticmethod
    def _mem_map_page(page, peripherals: dict) -> None:
        for table in page.extract_tables():
            if len(table) < 2 or len(table[0]) < 3:
                continue
            header = " ".join(_clean(c) for c in table[0]).lower()
            if "peripheral" not in header:
                continue
            for row in table[1:]:
                cells = list(row) + [None] * max(0, 4 - len(row))
                addr_raw, name, bus = _clean(cells[0]), _clean(cells[1]), _clean(cells[2])
                if not name or name.lower() == "reserved":
                    continue
                addrs = [
                    a.replace(" ", "")
                    for a in re.findall(r"0[xX][0-9a-fA-F][0-9a-fA-F ]*", addr_raw)
                ]
                if len(addrs) < 2:
                    continue
                try:
                    start = int(addrs[0], 16)
                    int(addrs[1], 16)
                except ValueError:
                    continue
                peripherals.setdefault(
                    name,
                    {
                        "name": name,
                        "base_address": addrs[0],
                        "end_address": addrs[1],
                        "bus": bus or _bus_of(start),
                        "irqs": [],
                        "description": "",
                    },
                )

    # -- 中断向量表（Position | Priority | Type | Acronym | Description | Address） --

    @staticmethod
    def _irq_page(page, text: str, irq_all: dict, irq_t63: dict) -> None:
        is_t63 = "other stm32f10xxx" in text.lower()
        for table in page.extract_tables():
            if len(table) < 5:
                continue
            for row in table:
                cells = list(row) + [None] * max(0, 6 - len(row))
                pos, acr = _clean(cells[0]), _clean(cells[3])
                if pos.isdigit() and re.match(r"^[A-Z][A-Za-z0-9_]+$", acr):
                    irq_all[acr] = int(pos)
                    if is_t63:
                        irq_t63[acr] = int(pos)

    # -- 寄存器描述章节（文本状态机 + 位域坐标对齐） --

    @staticmethod
    def _registers_page(page, text: str, registers: list) -> None:
        lines = text.split("\n")
        periph = None
        for i, raw_line in enumerate(lines):
            line = raw_line.strip()
            m = _PERIPH_SEC_RE.match(line)
            if m:
                periph = m.group(1).strip()
                continue
            if not line.startswith("Address offset:"):
                continue
            off_m = re.search(r"0[xX][0-9a-fA-F]+", line)
            if not off_m:
                continue
            offset = off_m.group(0)
            title = STM32Adapter._last_title(lines, i)
            reg_name = STM32Adapter._reg_abbr(title) or (title or "")[:24]
            if not reg_name:
                continue
            # 复位值：offset 行之后 1-3 行内的 "Reset value: 0x..."
            reset = None
            for j in range(i + 1, min(i + 4, len(lines))):
                rm_ = re.search(r"Reset value:.*?(0[xX][0-9a-fA-F ]+)", lines[j])
                if rm_:
                    reset = rm_.group(1).replace(" ", "")
                    break
            bitfields = STM32Adapter._extract_bitfields(page, lines, i)
            registers.append(
                {
                    "peripheral": periph or "",
                    "name": reg_name,
                    "address": None,  # 汇总阶段按外设基地址合成
                    "offset": offset,
                    "access": "rw",
                    "reset_value": reset,
                    "description": title or "",
                    "bitfields": bitfields,
                }
            )

    @staticmethod
    def _last_title(lines: list, idx: int) -> str:
        """向上找最近的 N.N.N 级小节标题。"""
        for j in range(idx - 1, max(idx - 8, -1), -1):
            m = _REG_SEC_RE.match(lines[j].strip())
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _reg_abbr(title: str) -> str:
        """从寄存器小节标题提取括号缩写（如 GPIOx_CRL）。"""
        m = _ABBR_RE.search(title)
        return m.group(1) if m else ""

    @staticmethod
    def _extract_bitfields(page, lines: list, off_idx: int) -> list:
        """提取位域：位名行（NAME[bits] token）与上方位数行坐标对齐。

        对齐失败时 bits 退化为 token 内相对区间。
        """
        bitrow_ids = [
            j
            for j in range(off_idx + 1, min(off_idx + 8, len(lines)))
            if re.search(r"[A-Z][A-Z0-9_]*\[\d+:\d+\]", lines[j])
        ]
        if not bitrow_ids:
            return []
        try:
            words = page.extract_words()
        except Exception:
            words = []
        # words 按行 top 聚组
        rows_by_top: dict[int, list] = {}
        for w in words:
            rows_by_top.setdefault(round(w["top"] / 3), []).append(w)

        def row_words(line_text: str):
            target = line_text.replace(" ", "")
            for _, ws in rows_by_top.items():
                joined = "".join(x["text"] for x in sorted(ws, key=lambda x: x["x0"]))
                if joined == target:
                    return sorted(ws, key=lambda x: x["x0"])
            return None

        result: list[dict] = []
        for j in bitrow_ids:
            name_ws = row_words(lines[j])
            digit_ws = None
            if name_ws:
                # 上方最近的纯位数行
                tops = sorted(rows_by_top)
                cur_top = round(name_ws[0]["top"] / 3)
                for t in reversed(tops):
                    if t >= cur_top:
                        continue
                    ws = sorted(rows_by_top[t], key=lambda x: x["x0"])
                    if len(ws) >= 4 and all(re.fullmatch(r"\d{1,2}", x["text"]) for x in ws):
                        digit_ws = ws
                        break
            for w in name_ws or []:
                if not _BITFIELD_TOKEN_RE.match(w["text"]):
                    continue
                m = re.match(r"([A-Z][A-Z0-9_]*)\[(\d+):(\d+)\]", w["text"])
                bits = f"{m.group(2)}:{m.group(3)}"
                if digit_ws:
                    covered = [
                        int(d["text"])
                        for d in digit_ws
                        if w["x0"] <= (d["x0"] + d["x1"]) / 2 <= w["x1"]
                    ]
                    if covered:
                        bits = f"{max(covered)}:{min(covered)}"
                result.append(
                    {
                        "name": m.group(1),
                        "bits": bits,
                        "access": "rw",
                        "reset_value": None,
                        "description": "",
                    }
                )
        return result

    # -- RCC 位域扫描（使能位 xxxEN / 分频位段） --

    @staticmethod
    def _rcc_scan(text: str, rcc_en: dict, rcc_pre: dict) -> None:
        current = ""
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            m = re.search(r"RCC_([A-Z0-9_]+)", line)
            if m:
                current = f"RCC_{m.group(1)}"
            if not current:
                continue
            # 去括号（U(S)ART1EN → USART1EN）
            norm = line.replace("(", "").replace(")", "")
            for tok in norm.split():
                tok = tok.strip(",;:")
                if current.endswith("ENR") and _NAME_EN_RE.match(tok):
                    rcc_en.setdefault(tok, current)
                if tok in _PRESCALER_FIELDS and current.endswith("CFGR"):
                    rcc_pre.setdefault(tok, current)

    @staticmethod
    def _lookup_base(bases: dict, periph: str) -> str | None:
        """章节短名 → memory map 基地址（精确或前缀匹配）。"""
        key = periph.upper().strip()
        if not key:
            return None
        if key in bases:
            return bases[key]
        for name, base in bases.items():
            if name.startswith(key) or key.startswith(name):
                return base
        return None

    @staticmethod
    def _peripheral_of_en(stem: str) -> str:
        """使能位段名还原外设名：IOPAEN→GPIOA、USART1EN→USART1。"""
        if stem.startswith("IOP"):
            return f"GPIO{stem[3:]}"
        return stem

    @staticmethod
    def _bus_of_enr(reg_name: str) -> str:
        if "AHB" in reg_name:
            return "AHB"
        if "APB1" in reg_name:
            return "APB1"
        return "APB2"


__all__ = ["STM32Adapter"]
