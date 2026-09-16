"""GD32 系列手册提取适配器。

数据源：
- datasheet（必需）：引脚定义表（"GD32F2xxVx LQFP100 pin definitions" 章节锚点，
  逐引脚块 5 列结构：Pin Name | Pins | Type | Level | Default/Alternate/Remap）
- SVD（优先）：寄存器/外设/中断（复用 svd_source 通用 CMSIS-SVD 解析）
- SDK 头文件（回退）：gd32f20x.h 等设备头（复用 sdk_source 通用 CMSIS 解析）
- 参考手册 PDF（兜底）：GD32 用户手册章节结构与 ST 不同，不做深度解析，告警提示

GD32 与 STM32 的关键差异（本适配器处理）：
- 时钟控制器叫 RCU（非 RCC）：RCU_AHB1EN/AHB2EN/APB1EN/APB2EN（无 R 后缀）
- 分频位段叫 AHBPSC/APB1PSC/APB2PSC/SCS/PLLMF（非 HPRE/PPRE1/SW/PLLMUL）
- GPIO 时钟使能位为 PAEN/PBEN/...（非 IOPAEN）
- 引脚表为逐引脚块结构（Default/Alternate/Remap 多行单元格），非跨页宽表

提取是尽力而为（best effort）：无法解析的章节跳过并记入 warnings，
由主入口汇总为 partial 状态，供下游 S4/S5 判断数据可用性。
"""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

# GD32 引脚数代码（gd32f205vet6 → V=100）
GD32_PIN_COUNT_CODE = {
    "G": 28, "K": 32, "T": 36, "C": 48,
    "R": 64, "V": 100, "Z": 144, "I": 176, "B": 216,
}
# GD32 封装代码（T=LQFP 等；未知封装回退为仅引脚数）
GD32_PACKAGE_CODE = {
    "T": "LQFP", "H": "LQFP", "U": "QFN", "Y": "BGA", "P": "TSSOP",
}

# RCU 使能寄存器 → 总线（GD32F20x：AHB 分 AHB1/AHB2，寄存器无 R 后缀）
RCU_EN_REGS = (
    ("AHB1EN", "AHB1"), ("AHB2EN", "AHB2"),
    ("APB1EN", "APB1"), ("APB2EN", "APB2"),
    ("ADDAPB1EN", "APB1"), ("ADDAPB2EN", "APB2"),
)
# CFG0 分频/时钟选择位段 → 总线（支持带 _n_n 后缀的拆分段，如 PLLMF_3_0）
RCU_CFG0_PRESCALER_BUS = {
    "SCS": "SYSCLK", "SCSS": "SYSCLK",
    "AHBPSC": "AHB", "APB1PSC": "APB1", "APB2PSC": "APB2",
    "ADCPSC": "ADC", "USBFSPSC": "USB",
    "PLLSEL": "SYSCLK", "PLLMF": "SYSCLK", "PREDV0": "SYSCLK",
    "CKOUT0SEL": "SYSCLK",
}

# 引脚定义章节锚点：正文标题 "2.6.2. GD32F205Vx LQFP100 pin definitions"
# （目录条目后跟点线 "....."，需排除）
_ANCHOR_RE = re.compile(r"(\w+)\s+LQFP(\d+)\s+pin\s+definitions", re.I)
# 功能单元格按 Default:/Alternate:/Remap: 分段
_FUNC_SPLIT_RE = re.compile(r"(Default|Alternate|Remap)\s*:")


def _clean(cell) -> str:
    """单元格清洗：去换行/首尾空白。"""
    if cell is None:
        return ""
    return str(cell).replace("\n", "").strip()


def parse_platform(platform: str) -> tuple[str, str | None, int | None]:
    """从 platform 名解析 (mcu_family, package_hint, pin_count_hint)。

    gd32f205vet6 → ("GD32F205xx", "LQFP100", 100)
    """
    m = re.match(r"^gd32f(\d)(\d{2})", platform.lower())
    family = f"GD32F{m.group(1)}{m.group(2)}xx".upper() if m else platform.upper()
    package = None
    pin_count = None
    m2 = re.match(r"^gd32f\d{3}(\w)(\w)(\w)\d*$", platform.lower())
    if m2:
        pin_count = GD32_PIN_COUNT_CODE.get(m2.group(1).upper())
        pkg = GD32_PACKAGE_CODE.get(m2.group(3).upper())
        if pin_count and pkg:
            package = f"{pkg}{pin_count}"
    return family, package, pin_count


class GD32Adapter:
    """GD32 datasheet / SVD / SDK 头文件提取。"""

    KEY_PREFIX = "gd32"

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
        > 参考手册 PDF（GD32 结构差异大，不做深度解析）。
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
            self._extract_pins(datasheet, result, pin_count_hint)

        if not need_chip:
            return result

        # 优先级 1：SVD（CMSIS-SVD，含复位值与完整位域）
        if svd is not None:
            try:
                from svd_source import parse_svd

                svd_data = parse_svd(svd)
                if svd_data.get("peripherals"):
                    result["peripherals"] = svd_data["peripherals"]
                    result["registers"] = svd_data["registers"]
                    self._apply_rcu_clock_tree(result)
                    result["warnings"].extend(
                        w for w in (svd_data.get("warnings") or [])
                        if "RCC" not in w  # 通用模块按 RCC 查找未果的告警，由 RCU 推导替代
                    )
                    return result
                result["warnings"].extend(svd_data.get("warnings") or [])
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
                if sdk_data.get("peripherals"):
                    result["peripherals"] = sdk_data["peripherals"]
                    result["registers"] = sdk_data["registers"]
                    self._apply_rcu_clock_tree(result)
                    result["warnings"].extend(
                        w for w in (sdk_data.get("warnings") or [])
                        if "RCC" not in w
                    )
                    return result
                result["warnings"].extend(sdk_data.get("warnings") or [])
                result["warnings"].append("SDK 头文件解析无产物")
            except ImportError:
                pass
            except Exception as exc:
                result["warnings"].append(f"SDK 头文件解析异常: {exc}")

        # 优先级 3：参考手册 PDF（GD32 用户手册章节结构与 ST 不同，不深度解析）
        if secondary is not None:
            result["warnings"].append(
                "GD32 参考手册 PDF 深度解析未实现，请优先配置 svd_path / sdk_header_path"
            )
        else:
            result["warnings"].append(
                "未提供 SVD（svd_path）/ SDK 头文件（sdk_header_path），"
                "寄存器映射/时钟树/外设清单未提取"
            )
        return result

    # ------------------------------------------------------------------
    # 引脚定义（datasheet：逐引脚块表格）
    # ------------------------------------------------------------------

    def _extract_pins(self, datasheet: Path, result: dict, pin_count_hint: int | None) -> None:
        """提取目标封装的 "pin definitions" 章节表（GD32 逐引脚块结构）。

        章节锚点形如 "2.6.2. GD32F205Vx LQFP100 pin definitions"；
        同一 datasheet 含多封装章节（LQFP144/100/64），按 pin_count_hint 选取。
        """
        try:
            with pdfplumber.open(datasheet) as pdf:
                anchors = self._locate_sections(pdf)  # [(page_idx, pin_count, package)]
                if not anchors:
                    result["warnings"].append(
                        f"datasheet 中未找到 pin definitions 章节锚点: {datasheet}"
                    )
                    return

                start, end, package = self._select_section(anchors, pin_count_hint)
                if start is None:
                    result["warnings"].append(
                        f"datasheet 中未找到 LQFP{pin_count_hint} 引脚封装章节"
                        f"（现有: {[f'LQFP{a[1]}' for a in anchors]}）"
                        if pin_count_hint
                        else "datasheet 中未找到引脚定义章节"
                    )
                    return

                pin_rows: dict[int, dict] = {}
                for page in pdf.pages[start:end]:
                    for table in page.extract_tables():
                        self._collect_pin_rows(table, pin_rows)

                if not pin_rows:
                    result["warnings"].append(
                        f"pin definitions 章节未解析到引脚行（LQFP 章节 page {start}-{end - 1}）"
                    )
                    return

                result["pins"] = [pin_rows[k] for k in sorted(pin_rows)]
                result["package"] = package
                result["pin_count"] = int(re.sub(r"\D", "", package) or 0) or len(pin_rows)
        except Exception as exc:  # PDF 解析异常不能中断其他范围
            result["warnings"].append(f"引脚定义提取失败: {exc}")

    @staticmethod
    def _locate_sections(pdf) -> list[tuple[int, int, str]]:
        """全文扫描章节锚点，排除目录点线条目。

        返回 [(页号, 引脚数, 封装名)]，按页号升序、同页去重。
        """
        anchors: list[tuple[int, int, str]] = []
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            for m in _ANCHOR_RE.finditer(text):
                after = text[m.end():m.end() + 80]
                if ".." in after:  # 目录条目（标题后跟点线 + 页码）
                    continue
                pkg = f"LQFP{m.group(2)}"
                entry = (i, int(m.group(2)), pkg)
                if entry not in anchors:
                    anchors.append(entry)
        return anchors

    @staticmethod
    def _select_section(
        anchors: list[tuple[int, int, str]], pin_count_hint: int | None
    ) -> tuple[int | None, int | None, str | None]:
        """按引脚数选章节，返回 (起始页, 结束页, 封装名)。

        匹配不到时回退第一个封装章节（best effort）。
        """
        target_idx = 0
        if pin_count_hint:
            for idx, a in enumerate(anchors):
                if a[1] == pin_count_hint:
                    target_idx = idx
                    break
            else:
                return None, None, None
        start, _n, pkg = anchors[target_idx]
        end = anchors[target_idx + 1][0] if target_idx + 1 < len(anchors) else None
        return start, end, pkg

    @staticmethod
    def _collect_pin_rows(table: list, out: dict[int, dict]) -> None:
        """从逐引脚块表格收集引脚行。

        列布局：0 Pin Name | 1 Pins | 2 Type | 3 Level | 4 Functions description
        功能单元格含多行：Default: ... / Alternate: ... / Remap: ...
        """
        for row in table:
            if not row:
                continue
            cells = list(row) + [None] * max(0, 5 - len(row))
            no = _clean(cells[1])
            name = _clean(cells[0])
            if not no.isdigit() or not name:
                continue
            pin = int(no)
            if pin in out:
                continue
            type_raw = _clean(cells[2])
            io_level = _clean(cells[3])
            funcs_raw = str(cells[4] or "")
            main, alts, remaps = GD32Adapter._parse_functions(funcs_raw)
            # 引脚名列内换行拼接（如 "PC14-\nOSC32IN"）
            name = re.sub(r"\s+", "", name)
            out[pin] = {
                "pin": pin,
                "name": name,
                "pin_type": GD32Adapter._classify_pin(name, type_raw),
                "pin_type_raw": type_raw,
                "io_level": io_level,
                "main_function": main or name,
                "alternate_functions": alts,
                "alternate_functions_remap": remaps,
            }

    @staticmethod
    def _parse_functions(funcs_text: str) -> tuple[str, list[str], list[str]]:
        """解析功能单元格：Default: / Alternate: / Remap: 分段。

        返回 (主功能, 复用功能列表, 重映射功能列表)。
        段内换行视为续行（功能名与逗号列表项均不含空格）。
        """
        main = ""
        alts: list[str] = []
        remaps: list[str] = []
        parts = _FUNC_SPLIT_RE.split(funcs_text)
        # parts 形如 ['', 'Default', ' PE2', 'Alternate', ' TRACECK, EXMC_A23', ...]
        for j in range(1, len(parts) - 1, 2):
            kind, body = parts[j], parts[j + 1]
            items = [re.sub(r"\s+", "", p) for p in body.split(",") if p.strip()]
            if kind == "Default":
                main = items[0] if items else ""
            elif kind == "Alternate":
                alts.extend(items)
            elif kind == "Remap":
                remaps.extend(items)
        return main, alts, remaps

    @staticmethod
    def _classify_pin(name: str, type_raw: str) -> str:
        n = name.upper()
        if n.startswith("BOOT"):
            return "BOOT"
        if n == "NRST":
            return "NRST"
        if any(k in n for k in ("VDD", "VSS", "VREF", "VBAT")) or type_raw in ("P", "S"):
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
    # 时钟树（GD32 差异：RCU 而非 RCC）
    # ------------------------------------------------------------------

    def _apply_rcu_clock_tree(self, result: dict) -> None:
        """从 RCU 寄存器位域推导时钟树（SVD / SDK 两数据源同构）。

        覆盖通用模块按 RCC 推导未果的空缺（GD32 命名：AHB1EN/APB2EN/CFG0）。
        """
        registers = result.get("registers") or []
        rcu = {
            r["name"].upper(): r
            for r in registers
            if (r.get("peripheral") or "").upper() == "RCU"
        }
        if not rcu:
            result["warnings"].append("SVD/SDK 中未找到 RCU 寄存器（时钟树配置要素缺失）")
            return

        enables: list[dict] = []
        for reg_name, bus in RCU_EN_REGS:
            reg = rcu.get(f"RCU_{reg_name}") or rcu.get(reg_name)
            for bf in (reg or {}).get("bitfields", []):
                fn = bf["name"]
                if not fn.upper().endswith("EN"):
                    continue
                enables.append(
                    {
                        "peripheral": self._peripheral_of_en(fn),
                        "field": fn,
                        "register": f"RCU_{reg_name}",
                        "bus": bus,
                    }
                )

        prescalers: list[dict] = []
        cfg0 = rcu.get("RCU_CFG0") or rcu.get("CFG0")
        for bf in (cfg0 or {}).get("bitfields", []):
            name_u = bf["name"].upper()
            for field, bus in RCU_CFG0_PRESCALER_BUS.items():
                if name_u == field or name_u.startswith(field + "_"):
                    prescalers.append(
                        {
                            "bus": bus,
                            "field": bf["name"],
                            "register": "RCU_CFG0",
                            "division_range": "",
                        }
                    )
                    break

        if not enables and not prescalers:
            result["warnings"].append("RCU 位域中未提取到时钟配置要素（时钟树缺失）")
            return

        result["clock_tree"] = {
            "clock_sources": [
                {"name": "HXTAL", "frequency_range": "4-32 MHz", "typical": "8 MHz", "notes": ""},
                {"name": "IRC8M", "frequency_range": "8 MHz", "typical": "8 MHz", "notes": "出厂校准"},
                {"name": "LXTAL", "frequency_range": "32.768 kHz", "typical": "32.768 kHz", "notes": ""},
                {"name": "IRC40K", "frequency_range": "40 kHz", "typical": "40 kHz", "notes": "低功耗内部 RC"},
            ],
            "pll": {"source": "HXTAL/IRC8M", "multiplier_field": "PLLMF", "multiplier_range": "x2..x32"},
            "bus_prescalers": prescalers,
            "peripheral_clock_enables": enables,
        }

    @staticmethod
    def _peripheral_of_en(field_name: str) -> str:
        """RCU 使能位段名还原外设名：PAEN→GPIOA、TIMER0EN→TIMER0、DMA0EN→DMA0。"""
        stem = field_name[:-2] if field_name.upper().endswith("EN") else field_name
        m = re.match(r"^P([A-Z])$", stem)
        if m:  # GPIO 端口使能（PAEN/PBEN/PCEN...）
            return f"GPIO{m.group(1)}"
        if stem == "AF":  # 复用功能 IO 时钟
            return "AF"
        return stem


__all__ = ["GD32Adapter"]
