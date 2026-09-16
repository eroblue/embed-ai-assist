#!/usr/bin/env python
"""引脚功能推断（rule 模式）。

按需求文档优先级推断（不依赖引脚电气类型——S1 暂未提取符号电气属性，
后续 S1 扩展后可在优先级 2/3 之间插入电气类型规则）：

| 优先级 | 线索                       | 推断结果                     |
|--------|----------------------------|------------------------------|
| 1      | 网络名与芯片复用功能匹配   | 直接采用复用功能（如 USART1_TX）|
| 2      | 网络名有明确语义           | 按语义推断（KEY/LED/UART/...） |
| 3      | 引脚名有明确语义           | 按引脚名推断（WKUP/OSC/NRST）|
| 4      | 引脚与电源网络相连         | 判定为电源                   |
| 5      | 以上都不匹配               | 留空，标记 warning           |

输出统一为 (role, peripheral, config, note, status)：
- role：中文角色描述（如 串口1发送、按键输入）
- peripheral：外设/模式（与 Excel 颜色分组对应，如 GPIO 输入上拉 / USART1_TX / 电源）
- config：配置说明（推挽输出 / 输入上拉 ...）
- status：ok / warning（推断不出时）
"""

from __future__ import annotations

import re

# ---- 引脚名/信号名清洗：剥 datasheet 脚注标记（如 PC14-OSC32_IN(5)、PC13(6)）----
_FOOTNOTE_RE = re.compile(r"\((\d+)\)\s*$")


def clean_name(name: str | None) -> str:
    """剥掉名称尾部的脚注编号后缀，如 'PC14-OSC32_IN(5)' → 'PC14-OSC32_IN'。"""
    return _FOOTNOTE_RE.sub("", (name or "").strip())


# 纯端口名模式（如 PA2、PD0）——无功能语义，不作为优先级 1 的复用匹配
_PORT_NAME_RE = re.compile(r"^P[A-K]\d+([A-K]\d+)?(_[A-Z0-9]+)?$", re.I)


# ---- 网络名规范化（把常见别名映射到芯片 AF 命名）----
_NET_ALIAS = [
    (re.compile(r"^UART(\d)"), r"USART\1"),   # UART1_TX → USART1_TX
    (re.compile(r"^TXD(\d)"), r"USART\1_TX"),
    (re.compile(r"^RXD(\d)"), r"USART\1_RX"),
    (re.compile(r"SERIAL"), "USART"),
]

# ---- 电源网络模式（优先级 4）----
_POWER_NET_RE = re.compile(
    r"^(\+?\d+(\.\d+)?V.*|GND.*|VDD.*|VSS.*|VBAT.*|VREF.*|AGND.*|VBUS.*|VIN.*|3V3.*|5V.*|"
    r"VBAT_RTC.*|VCCA.*|VDDA.*|-12V.*|\+12V.*|VPP.*|BATT.*|BAT_.*)$",
    re.IGNORECASE,
)

# ---- 引脚名语义模式（优先级 3）----
_PIN_NAME_RULES: list[tuple[re.Pattern, tuple[str, str, str]]] = [
    (re.compile(r"OSC32_IN|OSC32IN", re.I), ("32.768kHz RTC 晶振输入", "LXTAL", "低速晶振")),
    (re.compile(r"OSC32_OUT|OSC32OUT", re.I), ("32.768kHz RTC 晶振输出", "LXTAL", "低速晶振")),
    (re.compile(r"OSC_IN|OSCIN|PD0-OSC", re.I), ("高速晶振输入", "HXTAL", "主时钟晶振")),
    (re.compile(r"OSC_OUT|OSCOUT|PD1-OSC", re.I), ("高速晶振输出", "HXTAL", "主时钟晶振")),
    (re.compile(r"NRST|RESET|\bRST\b", re.I), ("复位", "复位", "低电平有效")),
    (re.compile(r"BOOT0|BOOT1|\bBOOT\b", re.I), ("启动配置", "BOOT", "启动模式选择")),
    (re.compile(r"SWDIO|PA13", re.I), ("SWD 调试数据", "SWD", "调试接口")),
    (re.compile(r"SWCLK|PA14", re.I), ("SWD 调试时钟", "SWD", "调试接口")),
    (re.compile(r"^JTMS|-JTMS$|JTMS$", re.I), ("JTAG 调试模式选择", "JTAG", "调试接口")),
    (re.compile(r"^JTCK|-JTCK$|JTCK$", re.I), ("JTAG 调试时钟", "JTAG", "调试接口")),
    (re.compile(r"^JTDI|-JTDI$|JTDI$", re.I), ("JTAG 调试数据输入", "JTAG", "调试接口")),
    (re.compile(r"^JTDO|-JTDO$|JTDO$", re.I), ("JTAG 调试数据输出", "JTAG", "调试接口")),
    (re.compile(r"NJTRST|JTRST", re.I), ("JTAG 复位", "JTAG", "调试接口")),
    (re.compile(r"TAMPER", re.I), ("RTC 侵入检测", "GPIO 输入", "可作 RTC 侵入检测")),
    (re.compile(r"WKUP|WAKEUP", re.I), ("唤醒输入", "GPIO 输入", "可作唤醒源")),
]

# ---- 网络名语义规则（优先级 2）----
# (正则, (角色模板, 外设/模式, 配置说明), 是否需人工确认)
_NET_RULES: list[tuple[re.Pattern, tuple[str, str, str], bool]] = [
    (re.compile(r"^(KEY|BTN|SW\d|SWITCH|ROT|LC\d|ENC)", re.I),
     ("按键/开关输入", "GPIO 输入上拉", "输入模式，内部上拉"), False),
    (re.compile(r"LED|LAMP|BACKLIGHT|BL_", re.I),
     ("LED 指示", "GPIO 输出", "推挽输出"), False),
    (re.compile(r"UART|USART|COM\d|TXD?_|_TXD?|\bTX\b|RXD?_|_RXD?|\bRX\b|DEBUG|4G|WIFI|GSM|LPUART", re.I),
     ("串口通信", "USART", "复用推挽输出"), True),
    (re.compile(r"PWM|TIM|CH\d|CAPTURE|ENCODER", re.I),
     ("定时器/脉冲输出", "TIMER PWM", "复用推挽输出"), False),
    (re.compile(r"FSMC|EXMC|LCD_|LCD|TFT", re.I), ("并口/LCD 接口", "FSMC", "复用推挽输出"), False),
    (re.compile(r"SPI|MOSI|MISO|SCK|_CS\b|NCS|NSS", re.I),
     ("SPI 通信", "SPI", "复用推挽输出"), False),
    (re.compile(r"I2C|SCL|SDA|EEPROM", re.I),
     ("I2C 通信", "I2C", "复用开漏输出"), False),
    (re.compile(r"ADC|AIN|VBAT_DET|VREF|CURRENT|VOLTAGE|_AI\b|ANALOG", re.I),
     ("模拟输入", "ADC", "模拟输入模式"), False),
    (re.compile(r"SWD|SWCLK|SWDIO|TMS|TCK|TDI|TDO|JTAG|TRACE|JTRST|NJTRST", re.I),
     ("调试接口", "SWD", "调试接口"), False),
    (re.compile(r"BOOT", re.I), ("启动配置", "BOOT", "启动模式选择"), False),
    (re.compile(r"RESET|NRST|_RST", re.I), ("复位", "复位", "低电平有效"), False),
    (re.compile(r"32K|OSC32|LSE|LXTAL", re.I),
     ("32.768kHz RTC 晶振", "LXTAL", "低速晶振"), False),
    (re.compile(r"OSC|XTAL|CRYSTAL|MCO|8M|HSE|HXTAL", re.I),
     ("晶振/时钟", "HXTAL", "时钟"), False),
    (re.compile(r"CAN|CANH|CANL", re.I), ("CAN 通信", "CAN", "复用推挽输出"), False),
    (re.compile(r"USB|(?<![A-Za-z0-9])(DM|DP)(?![A-Za-z0-9])|^D[+-]$", re.I),
     ("USB 接口", "USB", "USB"), False),
    (re.compile(r"SDIO|SD_|SDIO_|SDCARD|TF", re.I), ("SD 卡接口", "SDIO", "SDIO"), False),
]

# ---- 外设模式 → Excel 颜色类别（与 GD32 示例图例一致）----
# 类别：电源/地/参考=浅蓝；复位/晶振/BOOT/调试=黄；数字输入=绿；模拟输入=橙；
#       GPIO 输出与 UART=浅蓝；SPI 与 I2C=紫；定时器 PWM=粉红；FSMC/EXMC=灰
_COLOR_BY_PERIPHERAL = [
    (re.compile(r"^电源$|电源"), "power"),
    (re.compile(r"^复位$|HXTAL|LXTAL|^BOOT$|^SWD$|^JTAG$"), "special"),
    (re.compile(r"GPIO 输入"), "digital_in"),
    (re.compile(r"^ADC|模拟"), "analog"),
    (re.compile(r"USART|^GPIO 输出$|^UART$"), "output_uart"),
    (re.compile(r"^SPI|^I2C"), "spi_i2c"),
    (re.compile(r"TIMER|PWM"), "pwm"),
    (re.compile(r"FSMC|EXMC"), "exmc"),
]


def normalize_net(net: str) -> str:
    """网络名规范化：UART→USART、TXD→TX 等（用于复用功能匹配）。"""
    s = net.strip().upper().replace("-", "_").replace(" ", "_")
    for pat, repl in _NET_ALIAS:
        s = pat.sub(repl, s)
    return s


def infer_pin(
    net: str | None,
    pin_name: str,
    main_function: str | None,
    alternate_functions: list[str],
    chip_pin_name: str | None = None,
) -> dict:
    """推断单个引脚的功能角色。

    - pin_name：网表侧引脚名
    - chip_pin_name：芯片定义侧引脚名（可能带脚注后缀，会先清洗）
    - main_function / alternate_functions：芯片侧功能名（剥脚注后缀后参与匹配）

    返回 {role, peripheral, config, note, status}；
    status=warning 表示无法推断（网络名无语义），留待人工/AI 补充。
    """
    # NC 判定
    if net is None or not net.strip():
        return {
            "role": "", "peripheral": "NC", "config": "未连接",
            "note": "网表中无连接（NC）", "status": "nc",
        }

    # 芯片侧信号集合（剥脚注后缀，如 'OSC_IN(9)' → 'OSC_IN'）
    candidates = [
        normalize_net(clean_name(s))
        for s in [main_function, *(alternate_functions or [])]
        if s
    ]

    # ---- 优先级 1：网络名与芯片复用功能匹配 ----
    norm = normalize_net(net)
    for af in candidates:
        if af and af == norm and not _PORT_NAME_RE.match(af):
            role_cn = _af_role_cn(af)
            return {
                "role": role_cn,
                "peripheral": af,
                "config": "复用推挽输出" if ("_TX" in af or "_MOSI" in af) else "复用功能",
                "note": f"网络名与芯片复用功能一致（{af}）",
                "status": "ok",
            }

    # ---- 优先级 2：网络名语义 ----
    for pat, (role, peripheral, config), need_confirm in _NET_RULES:
        if pat.search(net):
            note = f"按网络名语义推断（{net}）"
            if need_confirm:
                note += "，疑似串口通信，需人工确认具体外设"
            return {
                "role": role, "peripheral": peripheral, "config": config,
                "note": note, "status": "ok",
            }

    # ---- 优先级 3：引脚名语义（网表名 + 芯片名 + 芯片主/复用功能名）----
    # 芯片侧信号（如 main=OSC_IN）比网表端口名（PD0）语义更完整
    name_sources = [
        pin_name,
        clean_name(chip_pin_name),
        *[s for s in candidates if not _PORT_NAME_RE.match(s)],
    ]
    for pat, (role, peripheral, config) in _PIN_NAME_RULES:
        for src in name_sources:
            if src and pat.search(src):
                return {
                    "role": role, "peripheral": peripheral, "config": config,
                    "note": f"按引脚名语义推断（{src}）", "status": "ok",
                }

    # ---- 优先级 4：电源网络 ----
    if _POWER_NET_RE.match(net):
        return {
            "role": "电源", "peripheral": "电源", "config": "电源连接",
            "note": f"连接到电源网络 {net}", "status": "ok",
        }

    # ---- 优先级 5：无法推断 ----
    return {
        "role": "", "peripheral": "", "config": "",
        "note": f"网络名无明确语义，无法推断功能角色", "status": "warning",
    }


# 常见 AF 的中文角色
_AF_ROLE_MAP = [
    (re.compile(r"_TX$"), "发送"),
    (re.compile(r"_RX$"), "接收"),
    (re.compile(r"USART(\d+)"), "串口"),
    (re.compile(r"SPI(\d*)"), "SPI"),
    (re.compile(r"I2C(\d*)"), "I2C"),
    (re.compile(r"ADC(\d*)"), "模数转换"),
    (re.compile(r"TIM(\d*)"), "定时器"),
    (re.compile(r"CAN"), "CAN"),
    (re.compile(r"^OSC32?_(IN|OUT)$"), "晶振"),
]


def _af_role_cn(af: str) -> str:
    for pat, word in _AF_ROLE_MAP:
        if pat.search(af):
            return f"{word}（{af}）"
    return af
