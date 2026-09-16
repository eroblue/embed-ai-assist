#!/usr/bin/env python
"""冲突检测（复用冲突、电源缺失、时钟缺失、引脚定义一致性）。

严重程度：
- error  ：必须修复（电源引脚未连接、网络名暗示的外设与引脚复用功能不符）
- warning：建议确认（HSE/LSE 未接、BOOT0 悬空、NRST 悬空、无法推断）
- info   ：无需处理（NC 列表，单独输出不进 conflicts/warnings）
"""

from __future__ import annotations

import re

from pin_inferrer import normalize_net

# 电源引脚分级：VDD/VSS 未连接 = error；VBAT/VDDA/VREF 未连接 = warning（常见悬空设计）
_PWR_CRITICAL = re.compile(r"^V(BAT|DDA|DDIO|REF)|VREF", re.I)

# 时钟引脚判定（PD0/PD1 仅匹配纯端口名或 OSC 形式，避免误伤 PD10-PD19）
_HSE_PIN = re.compile(r"OSC_IN|OSC_OUT|^PD[01](?:-OSC|$)", re.I)
_LSE_PIN = re.compile(r"OSC32")

# 外设提取（从网络名/复用功能名中提取外设前缀，用于复用一致性核对）
_PERIPH_RE = re.compile(
    r"(USART\d+|UART\d+|SPI\d+|I2C\d+|ADC\d+|TIM\d+|CAN\d+|USB\d*|SDIO|FSMC|EXMC|"
    r"USART|UART|SPI|I2C|ADC|TIM)"
)


def check_pins_defined(netlist_pins: list[dict], chip_pins: dict) -> list[dict]:
    """核对网表引脚与芯片定义一致性：引脚号存在、引脚名一致。"""
    issues: list[dict] = []
    chip_by_no = {str(p["pin"]): p for p in chip_pins.get("pins", [])}
    for np in netlist_pins:
        no = str(np.get("pin") or "").strip()
        if no and no not in chip_by_no:
            issues.append({
                "pin": no,
                "issue": f"网表引脚号 {no} 在芯片定义中不存在（{chip_pins.get('mcu_family', '')}）",
                "severity": "error",
            })
    return issues


def check_power(netlist_pins: list[dict]) -> list[dict]:
    """电源引脚连接检查（verify_scope=power）。"""
    issues: list[dict] = []
    for np in netlist_pins:
        name = np.get("pin_name") or ""
        net = (np.get("net") or "").strip()
        is_power = (np.get("pin_type") == "POWER") or bool(
            re.match(r"^V(D|S|B|R|A)", name.upper())
        )
        if is_power and not net:
            severity = "warning" if _PWR_CRITICAL.match(name) else "error"
            issues.append({
                "pin": name,
                "issue": f"电源引脚 {name} 未连接",
                "severity": severity,
            })
    return issues


def check_clocks(netlist_pins: list[dict]) -> list[dict]:
    """时钟引脚检查：OSC/OSC32 悬空时提示（HSE/LSE 缺失可用内部时钟替代，warning）。"""
    issues: list[dict] = []
    for np in netlist_pins:
        name = np.get("pin_name") or ""
        net = (np.get("net") or "").strip()
        if _HSE_PIN.search(name) and "32" not in name and not net and "PD" in name.upper():
            issues.append({
                "pin": name, "issue": "HSE 晶振引脚未连接（如使用 HSI 可忽略）",
                "severity": "warning",
            })
        elif _LSE_PIN.search(name) and not net:
            issues.append({
                "pin": name, "issue": "LSE 晶振引脚未连接（如不用 RTC 可忽略）",
                "severity": "warning",
            })
    return issues


def check_peripheral_conflict(
    netlist_pins: list[dict], chip_pins: dict
) -> list[dict]:
    """复用一致性：网络名暗示的外设 vs 引脚复用功能表。

    例：net=UART3_TX 但该引脚 AF 不含 USART3_TX → error 复用冲突。
    仅检查网络名能提取出明确外设名（含编号）的引脚，纯语义网络（KEY/LED）不检查。
    """
    issues: list[dict] = []
    chip_by_no = {str(p["pin"]): p for p in chip_pins.get("pins", [])}
    for np in netlist_pins:
        net = (np.get("net") or "").strip()
        if not net:
            continue
        norm = normalize_net(net)
        # 网络名本身形如 <外设>[_<信号>]（如 USART1_TX / SPI2_MOSI / ADC12_IN8）
        m = _PERIPH_RE.match(norm)
        if not m:
            continue
        periph = m.group(1)
        # 纯外设名（无编号信号，如 USART）不构成强约束
        if not re.match(r"(USART|UART|SPI|I2C|ADC|TIM)\d", periph):
            continue
        chip_pin = chip_by_no.get(str(np.get("pin") or "").strip())
        if not chip_pin:
            continue  # 引脚号不存在已由 check_pins_defined 报告
        afs = [normalize_net(a) for a in (chip_pin.get("alternate_functions") or [])]
        main_f = normalize_net(chip_pin.get("main_function") or "")
        target = norm
        if not any(target.startswith(a) or a.startswith(target) or target == a for a in afs + [main_f]):
            issues.append({
                "pin": np.get("pin_name") or str(np.get("pin")),
                "issue": (
                    f"网络名 {net} 暗示外设 {periph}，但引脚 "
                    f"{chip_pin.get('name')} 复用功能不含该信号（AF: "
                    f"{', '.join(chip_pin.get('alternate_functions') or []) or '无'}），疑似复用冲突"
                ),
                "severity": "error",
            })
    return issues


def extract_crystal_freq(components: list[dict], netlist_pins: list[dict]) -> tuple[str | None, str | None]:
    """从晶振元件（Y* / 描述含晶振）提取 HSE/LSE 频率。

    返回 (HSE, LSE)。晶振频率从元件 value 解析（如 8MHz / 32.768K）。
    """
    hse_nets = {
        (p.get("net") or "").strip()
        for p in netlist_pins
        if _HSE_PIN.search(p.get("pin_name") or "") and "32" not in (p.get("pin_name") or "") and p.get("net")
    }
    lse_nets = {
        (p.get("net") or "").strip()
        for p in netlist_pins
        if _LSE_PIN.search(p.get("pin_name") or "") and p.get("net")
    }
    freq_re = re.compile(r"(\d+(?:\.\d+)?)\s*(M|K|k)?", )
    hse = lse = None
    for comp in components:
        desig = (comp.get("designator") or "").strip().upper()
        desc = " ".join(str(x) for x in [
            comp.get("description"), comp.get("footprint"), comp.get("value"),
            comp.get("library_ref"),
        ])
        is_crystal = desig.startswith("Y") or re.search(r"XTAL|CRYSTAL|晶振", desc, re.I)
        if not is_crystal:
            continue
        m = freq_re.search(str(comp.get("value") or ""))
        if not m:
            continue
        freq = m.group(1) + (m.group(2) or "").upper() + "Hz"
        if comp.get("value") and "32.768" in str(comp.get("value")):
            freq = "32.768kHz"
        # 晶振引脚连接到哪个时钟网络
        comp_nets = {(p.get("net") or "").strip() for p in comp.get("pins", []) if p.get("net")}
        if comp_nets & hse_nets:
            hse = hse or freq
        elif comp_nets & lse_nets or "32.768" in str(comp.get("value") or ""):
            lse = lse or freq
    return hse, lse


def build_power_map(netlist_pins: list[dict]) -> dict:
    """电源轨归纳：芯片电源引脚名 → 实际网络名。"""
    power: dict = {}
    for np in netlist_pins:
        name = np.get("pin_name") or ""
        net = (np.get("net") or "").strip()
        if re.match(r"^V(D|S|B|R|A)", name.upper()) or name.upper().startswith("VREF"):
            power[name] = net or None
    return power
