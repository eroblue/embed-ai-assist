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


def dumps(caps: dict) -> str:
    return json.dumps(caps, ensure_ascii=False, indent=2)
