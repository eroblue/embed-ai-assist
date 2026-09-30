"""capability_extractor：从 usage 分析结果聚合硬件能力清单。

输出 hardware_capabilities.json（S5c 实现 Port 的唯一硬件依据），
结构由 schemas/hardware_capabilities.schema.json 约束。
"""

from __future__ import annotations

import json


def extract(mcu: str, platform_name: str, architecture: str, rtos: str,
            power_enabled: bool, clock_cfg: dict, usage: dict,
            hse_hz: int | None, lse_hz: int | None) -> dict:
    """聚合 hardware_capabilities 字典（写入前由主入口做 schema 校验）。"""
    peripherals: list[dict] = []

    for u in usage.get("uart", []):
        pins = {"tx": u["tx"]["name"]} if u.get("tx") else {}
        if u.get("rx"):
            pins["rx"] = u["rx"]["name"]
        peripherals.append({
            "type": "uart", "instance": u["instance"], "pins": pins, "dma": None,
            "irq": u.get("irq"), "capabilities": [f"{u.get('baud', 115200)}-8N1"],
        })
    for s in usage.get("spi", []):
        capabilities = ["master", "soft-nss"]
        if s.get("remap"):
            capabilities.append("af-remap")
        peripherals.append({
            "type": "spi", "instance": s["instance"],
            "pins": {k: p["name"] for k, p in s.get("pin_map", {}).items()},
            "dma": None, "irq": None, "capabilities": capabilities,
        })
    for i in usage.get("i2c", []):
        peripherals.append({
            "type": "i2c", "instance": i["instance"],
            "pins": {k: p["name"] for k, p in i.get("pin_map", {}).items()},
            "dma": None, "irq": None, "capabilities": ["100kHz-standard"],
        })
    for a in usage.get("adc", []):
        peripherals.append({
            "type": "adc", "instance": a["instance"],
            "pins": {k: p["name"] for k, p in a.get("pin_map", {}).items()},
            "dma": None, "irq": None, "capabilities": ["12bit-right-align"],
        })
    for w in usage.get("pwm", []):
        peripherals.append({
            "type": "pwm", "instance": w["instance"],
            "pins": {"out": w["pin"]["name"]}, "dma": None, "irq": None,
            "capabilities": ["1kHz-default", "50%-default"],
        })
    if usage.get("fsmc"):
        peripherals.append({
            "type": "fsmc", "instance": "FSMC/EXMC",
            "pins": {p["net"]: p["name"] for p in usage["fsmc"]},
            "dma": None, "irq": None, "capabilities": ["lcd-parallel-bus"],
        })
    # gpio 按端口聚合：pins = {引脚名: 模式}
    gpio_by_port: dict[str, dict[str, str]] = {}
    for p in usage.get("gpio", []):
        gpio_by_port.setdefault(p["port"], {})[p["name"]] = p["mode"]
    for port, pins in sorted(gpio_by_port.items()):
        peripherals.append({
            "type": "gpio", "instance": f"GPIO{port[-1]}",
            "pins": pins, "dma": None, "irq": None,
            "capabilities": [f"{len(pins)}-pins"],
        })

    caps = {
        "schema": "embedaiassist.s5a.hardware_capabilities.v1",
        "mcu": mcu,
        "platform": platform_name,
        "rtos": rtos,
        "architecture": architecture,
        "power_enabled": power_enabled,
        "clocks": {
            "sysclk_hz": clock_cfg["sysclk_hz"], "ahb_hz": clock_cfg["ahb_hz"],
            "apb1_hz": clock_cfg["apb1_hz"], "apb2_hz": clock_cfg["apb2_hz"],
            "source": clock_cfg["source"],
            "hse_hz": hse_hz, "lse_hz": lse_hz,
        },
        "peripherals": peripherals,
        "power": {"modes": [], "wakeup_sources": [], "notes": ""} if power_enabled else None,
        "constraints": usage.get("constraints", []),
    }
    return caps


def merge_caps(existing: dict | None, rule_caps: dict) -> dict:
    """把规则轨产出合并进已有能力清单（保留规则推不出的条目）。

    规则轨只从 S4 事实推导能力：数据源退化（如 PDF 网表未吸附导致 usage
    为空）时产出为空，直接覆盖会清空手工补全的能力清单。合并策略：

    - `peripherals`：以 (type, instance) 为键——规则命中的条目被规则值替换
      （规则是权威数值源），规则推不出的已有条目原样保留（手工补全成果）；
    - `constraints`：并集（已有在前，规则新增在后，去重）；
    - 其余字段（mcu/platform/rtos/architecture/power_enabled/clocks/power）
      以规则产出为准（它们来自 config 与确定性数值计算）。

    代价：真正被移除的外设条目不会自动消失，需人工清理。
    """
    if not existing:
        return rule_caps

    def _key(p: dict) -> tuple[str, str]:
        return (str(p.get("type") or "").strip().lower(),
                str(p.get("instance") or "").strip().lower())

    rule_peripherals = list(rule_caps.get("peripherals") or [])
    rule_keys = {_key(p) for p in rule_peripherals}
    kept = [p for p in (existing.get("peripherals") or []) if _key(p) not in rule_keys]

    merged = dict(rule_caps)
    merged["peripherals"] = rule_peripherals + kept
    constraints = list(existing.get("constraints") or [])
    for c in rule_caps.get("constraints") or []:
        if c not in constraints:
            constraints.append(c)
    merged["constraints"] = constraints
    return merged


def dumps(caps: dict) -> str:
    return json.dumps(caps, ensure_ascii=False, indent=2)
