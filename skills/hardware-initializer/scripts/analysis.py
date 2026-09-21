"""S5a 确定性分析共享模块（rule 轨，prepare.py / validate.py 共用）。

职责边界（执行策略：rule 只做确定性契约工作，C 代码生成归 Agent/LLM）：
- 分层配置加载、S3/S4 就绪检查、外设使用分析（usage）、
  时钟数值计算（纯数值，不含代码行）、设计输入机械解析。
- 本模块不生成任何 C 代码——Agent 依据 outputs/s5a/generation_brief.md
  + references/init_code_templates.md 编写 S5a 产物目录代码
  （PROJECT_LAYOUT.md 解析，如 Drivers/BSP/{Src,Inc}）。

平台数值约束收敛在 PLATFORM_INFO 小表（仅数值/命名惯例，无代码模板）；
未登记平台不报错：按保守缺省计算并在任务书中提示 Agent 复核，
实现“新增硬件平台零脚本适配”。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ROOT_DIR = SKILL_DIR.parent.parent

# platform 前缀 → 数值约束/命名惯例（新增平台仅登记数值，无需写适配脚本）
PLATFORM_INFO: dict[str, dict] = {
    "gd32f20": {
        "label": "GD32F20x 标准外设库",
        "include": "gd32f20x.h",
        "sysclk_max_hz": 120_000_000,
        "apb1_max_hz": 60_000_000,
        "apb2_max_hz": 120_000_000,
        "target_sysclk_hz": 120_000_000,
        "pll_mul_max": 32,
        "flash_latency": None,  # GD32F20x 无需按主频软件配 FLASH 等待周期
        "default_uart": "USART0",  # GD32 实例号从 0 起
        "default_adc": "ADC0",
        "apb2_timers": {"TIMER0", "TIMER8", "TIMER9", "TIMER10", "TIMER11"},
    },
    "stm32f10": {
        "label": "STM32F10x 标准外设库 V3.5",
        "include": "stm32f10x.h",
        "sysclk_max_hz": 72_000_000,
        "apb1_max_hz": 36_000_000,
        "apb2_max_hz": 72_000_000,
        "target_sysclk_hz": 72_000_000,
        "pll_mul_max": 16,
        "flash_latency": [(24_000_000, 0), (48_000_000, 1), (None, 2)],
        "default_uart": "USART1",  # STM32 实例号从 1 起
        "default_adc": "ADC1",
        "apb2_timers": {"TIM1", "TIM8"},
    },
    "ft61f14": {
        "label": "FT61F14X（8 位机，SFR 直访，无标准外设库——按 datasheet 寄存器生成）",
        "include": None,  # 无 SDK 设备头文件，include 依据 datasheet 寄存器名
        "sysclk_max_hz": 16_000_000,  # HIRC 16MHz
        "apb1_max_hz": None,  # 无总线分层（SFR 直访）
        "apb2_max_hz": None,
        "target_sysclk_hz": 16_000_000,  # 无 HSE 时 HIRC 直跑基准
        "pll_mul_max": 1,  # 无 PLL
        "flash_latency": None,
        "default_uart": "USART",  # 单 UART 实例
        "default_adc": "ADC",  # 单 ADC 模块（通道 AN0..AN6）
        "apb2_timers": set(),
    },
}

_GENERIC_INFO: dict = {
    "label": None,
    "include": None,
    "sysclk_max_hz": None,
    "apb1_max_hz": None,
    "apb2_max_hz": None,
    "target_sysclk_hz": None,
    "pll_mul_max": 32,
    "flash_latency": None,
    "default_uart": "USART0",
    "default_adc": "ADC0",
    "apb2_timers": set(),
}


def get_platform_info(platform: str) -> tuple[dict, bool]:
    """按前缀匹配平台数值表；未登记返回保守缺省（registered=False）。"""
    for prefix, info in PLATFORM_INFO.items():
        if (platform or "").lower().startswith(prefix):
            return info, True
    return dict(_GENERIC_INFO, apb2_timers=set()), False


# ---------------- JSON / 配置工具 ----------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_layered_config(project_config_path: Path) -> tuple[dict, list[str]]:
    """根目录 config.json → 项目 config.json 深合并（只读，不回写）。"""
    notes: list[str] = []
    root_cfg: dict = {}
    root_config_path = ROOT_DIR / "config.json"
    if root_config_path.is_file():
        root_cfg = load_json(root_config_path)
        notes.append(f"已加载全局配置: {root_config_path}")
    if not project_config_path.is_file():
        raise FileNotFoundError(f"项目配置不存在: {project_config_path}")
    proj_cfg = load_json(project_config_path)
    notes.append(f"已加载项目配置: {project_config_path}")
    return deep_merge(root_cfg, proj_cfg), notes


def validate_schema(instance: dict, schema_path: Path, label: str) -> list[str]:
    """jsonschema 校验，返回错误列表（未安装 jsonschema 时跳过并提示）。"""
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ["jsonschema 未安装，跳过校验: pip install jsonschema"]
    schema = load_json(schema_path)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    return [f"{label}: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def resolve_target(config: dict | None, project_root: Path) -> Path:
    """目标工程根（App/BootLoader 双工程）：project.build_target 决定（缺省 App）。

    项目根 = config.json 所在目录（docs/schematic/references 共享）；
    目标根 = 项目根/<build_target>（state.json/源码目录/outputs/IDE 工程目录归属）。
    """
    target = ((config or {}).get("project") or {}).get("build_target") or "App"
    return project_root / str(target)


# ---------------- 频率 / 引脚工具 ----------------

def freq_hz(text: str) -> int | None:
    """从 '16MHz' / '32.768kHz' / '未连接' 提取频率 Hz。"""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Mm]", text)
    if m:
        return int(float(m.group(1)) * 1_000_000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Kk]", text)
    if m:
        return int(float(m.group(1)) * 1_000)
    return None


def find_mcu_designator(netlist: dict, platform: str) -> str | None:
    """从网表元件 value 匹配平台关键词，返回主控 designator（对齐 S4 识别逻辑）。

    系列名通配：platform 尾部 x 为通配（ft61f14x 匹配 FT61F143A-RB 等具体型号）。
    """
    plat = re.sub(r"[^a-z0-9]", "", platform.lower())
    key = plat[:8]
    prefix = plat[:-1] if plat.endswith("x") and len(plat) > 3 else None
    best = None
    for comp in netlist.get("components", []):
        value = re.sub(r"[^a-zA-Z0-9]", "", str(comp.get("value") or "")).lower()
        if value and (key and key in value or prefix and value.startswith(prefix)):
            if best is None or len(comp.get("pins", [])) > len(best.get("pins", [])):
                best = comp
    return best["designator"] if best else None


def af_lookup(chip_pins_by_no: dict, pin: str, pattern: str) -> str | None:
    """在芯片引脚 AF（含 remap）中找匹配 pattern 的功能名。"""
    pdef = chip_pins_by_no.get(pin) or chip_pins_by_no.get(str(pin))
    if not pdef:
        return None
    afs = list(pdef.get("alternate_functions") or []) + list(pdef.get("alternate_functions_remap") or [])
    for af in afs:
        if re.match(pattern, af):
            return af
    return None


def parse_port_pin(name: str) -> tuple[str, int] | None:
    """'PC6' / 'PC6/USART5_TX' → ('PC', 6)。"""
    m = re.match(r"^P([A-G])(\d+)", str(name or ""))
    return (f"P{m.group(1)}", int(m.group(2))) if m else None


# ---------------- 用户设计输入（docs/s5a_design_input.md） ----------------

def load_design_input(workspace: Path) -> dict | None:
    """读取 docs/s5a_design_input.md（用户设计输入，可选）。

    设计输入优先级高于自动推断：rule 轨仅机械解析可消费子集
    （UART 波特率、主频目标），其余内容（DMA 模式、特殊引脚用途等）
    由 Agent 在生成代码时结合原文校正。
    文件不存在或全部为 none → None（纯自动推断，Agent 自主判断）。
    """
    path = workspace / "docs" / "s5a_design_input.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    body = [ln.strip() for ln in text.splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
    if all(re.fullmatch(r"-\s*none", ln, re.I) for ln in body):
        return None
    result: dict = {"path": "docs/s5a_design_input.md", "uart_baud": {}}
    m = re.search(r"(?:主频|系统时钟|sysclk)[：:]\s*(\d+(?:\.\d+)?)\s*MHz", text, re.I)
    if m:
        result["sysclk_mhz"] = float(m.group(1))
    for inst, baud in re.findall(r"(?:UART|USART)(\d+)[^\n]*?波特率\s*(\d+)", text, re.I):
        result["uart_baud"][int(inst)] = int(baud)
    return result


def apply_design_input(usage: dict, design_input: dict | None, clock_cfg: dict) -> None:
    """设计输入 rule 轨消费：UART 波特率覆盖 + 主频回退说明记入约束。

    agent 轨内容（DMA 模式、EXTI 唤醒源等）由 Agent 读原文校正，不在此处。
    """
    if not design_input:
        return
    for num, baud in design_input.get("uart_baud", {}).items():
        for u in usage.get("uart", []):
            if u["instance"].upper().endswith(str(num)):
                u["baud"] = baud
    want_mhz = design_input.get("sysclk_mhz")
    got_hz = clock_cfg.get("sysclk_hz")
    if want_mhz and got_hz and abs(got_hz / 1e6 - want_mhz) > 0.01:
        note = clock_cfg.get("sysclk_note") or (
            f"设计输入主频 {want_mhz:g}MHz，当前时钟方案 {got_hz / 1e6:g}MHz")
        usage["constraints"].append(note)


# ---------------- 外设使用分析 ----------------

# S4 peripheral 值 → 跳过 GPIO 配置的类别（clock_init 处理晶振，其余保持默认）
_SKIP_PERIPHERALS = {"电源", "HXTAL", "LXTAL", "NRST", "SWD", "JTAG", "BOOT", "CAN", "USB", "ISP"}


def analyze_usage(facts: dict, netlist: dict, chip_pins: dict, peripherals: list[dict],
                  platform: str, baudrate: int) -> dict:
    """从 S4 facts 分析外设使用清单（Agent 代码生成的唯一引脚/实例依据）。"""
    info, _registered = get_platform_info(platform)
    usage: dict = {"gpio": [], "uart": [], "spi": [], "i2c": [], "adc": [], "pwm": [],
                   "timer": [], "fsmc": [], "dma": [], "gpio_skipped": [],
                   "constraints": [], "irq_names": []}
    mcu_designator = find_mcu_designator(netlist, platform)
    if mcu_designator is None:
        raise RuntimeError(f"网表中未找到平台 {platform} 对应的主控元件")

    chip_pins_by_no: dict = {}
    for p in chip_pins:
        chip_pins_by_no[str(p.get("pin"))] = p
    # 引脚名索引（8 位小封装脚号与网表错位时兜底，如 FT61F143A-16脚 vs 芯片表 FT61F145-20脚）
    chip_pins_by_name: dict = {str(p.get("name")): p for p in chip_pins if p.get("name")}
    irq_map = {p["name"]: (p.get("irqs") or [{}])[0].get("name") for p in peripherals if p.get("name")}

    def _af_lookup_pin(pin_no: str, port_name: str, pattern: str) -> str | None:
        """AF 查找：脚号优先，失配时按端口名兜底（跨封装脚号错位场景）。"""
        af = af_lookup(chip_pins_by_no, pin_no, pattern)
        if af:
            return af
        pdef = chip_pins_by_name.get(port_name)
        if not pdef:
            return None
        afs = list(pdef.get("alternate_functions") or []) + list(pdef.get("alternate_functions_remap") or [])
        for a in afs:
            if re.match(pattern, a):
                return a
        return None

    def _pininfo(pin: dict) -> dict | None:
        pp = parse_port_pin(pin.get("pin_name") or "")
        if pp is None:
            return None
        return {"pin": pin["pin"], "name": pp[0] + str(pp[1]), "port": pp[0], "pin_no": pp[1],
                "net": pin.get("net") or "", "role": pin.get("role") or ""}

    for pin in facts.get("pins", []):
        if pin.get("component") != mcu_designator or pin.get("nc"):
            continue
        periph = pin.get("peripheral") or ""
        role = pin.get("role") or ""
        net = pin.get("net") or ""
        name = pin.get("pin_name") or ""
        pp = parse_port_pin(name)
        if pp is None:
            usage["gpio_skipped"].append(f"{name}({net})")
            continue

        if periph in _SKIP_PERIPHERALS:
            usage["gpio_skipped"].append(name)
            continue

        # UART：实例号优先取 pin_name 携带的 AF（如 PC6/USART5_TX / USART2_TX(8)）
        m = re.search(r"(USART|UART)(\d+)", name)
        if periph.startswith("USART") or periph == "UART":
            if m:
                instance = f"{m.group(1)}{m.group(2)}"
            else:
                # 8 位单实例（FT61F：UART_TX 无编号）允许 \d*，实例名取 AF 前缀
                af = af_lookup(chip_pins_by_no, str(pin["pin"]), r"(?:USART|UART)\d*")
                instance = af.split("_")[0] if af else info["default_uart"]
                if not re.fullmatch(r"(?:USART|UART)\d*", instance):
                    mm = re.match(r"(?:USART|UART)\d*", instance)
                    instance = mm.group(0) if mm else info["default_uart"]
            entry = next((u for u in usage["uart"] if u["instance"] == instance), None)
            if entry is None:
                entry = {"instance": instance, "tx": None, "rx": None, "baud": baudrate,
                         "irq": irq_map.get(instance)}
                usage["uart"].append(entry)
                if irq_map.get(instance):
                    usage["irq_names"].append(irq_map[instance])
            pinfo = _pininfo(pin)
            # 方向判定：pin_name/peripheral 携带的 AF（USART2_RX）优先，net 名（UART2_RX）次之
            m_dir = (re.search(r"(?:USART|UART)\d+_(TX|RX)", name)
                     or re.search(r"(?:USART|UART)\d+_(TX|RX)", periph))
            if m_dir:
                is_rx = m_dir.group(1) == "RX"
            else:
                is_rx = "RX" in name.upper() or bool(re.search(r"(?:^|_)RX(?:D)?(?:$|_)", net.upper()))
            if is_rx:
                entry["rx"] = pinfo
            else:
                entry["tx"] = pinfo
            continue

        if periph == "SPI" or re.fullmatch(r"SPI\d+(_\w+)?", periph):
            af = af_lookup(chip_pins_by_no, str(pin["pin"]), r"SPI\d+")
            instance = af.split("_")[0] if af else "SPI0"
            # remap 引脚（AF 来自 alternate_functions_remap 列表）需 AFIO 重映射
            entry = next((s for s in usage["spi"] if s["instance"] == instance), None)
            if entry is None:
                entry = {"instance": instance, "pin_map": {}, "remap": False}
                usage["spi"].append(entry)
                if irq_map.get(instance):
                    usage["irq_names"].append(irq_map[instance])
            pdef = chip_pins_by_no.get(str(pin["pin"]))
            if pdef and af in (pdef.get("alternate_functions_remap") or []):
                entry["remap"] = True
            # 信号角色归一（兼容 GD32 "SPI-CLK"/"SPI-DO" 与 STM32 "SPI2_SCK"/"F_CS" 等网络命名）
            net_u = net.upper()
            if net_u == "CS" or re.search(r"NSS|CS\d?$", net_u):
                role_key = "nss"
            elif re.search(r"SCK|CLK", net_u):
                role_key = "sck"
            elif re.search(r"MISO|SDO|\bDO\b", net_u):
                role_key = "miso"
            elif re.search(r"MOSI|SDI|\bDI\b", net_u):
                role_key = "mosi"
            else:
                role_key = re.sub(r"SPI\d*[-_]", "", net_u).lower()
            entry["pin_map"][role_key] = _pininfo(pin)
            continue

        if periph == "I2C":
            af = af_lookup(chip_pins_by_no, str(pin["pin"]), r"I2C\d+")
            instance = af.split("_")[0] if af else "I2C0"
            entry = next((i for i in usage["i2c"] if i["instance"] == instance), None)
            if entry is None:
                entry = {"instance": instance, "pin_map": {}}
                usage["i2c"].append(entry)
            key = "scl" if re.search(r"SCL|CLK", net, re.I) else "sda"
            entry["pin_map"][key] = _pininfo(pin)
            continue

        if periph == "ADC" or "模拟" in role:
            af = af_lookup(chip_pins_by_no, str(pin["pin"]), r"ADC\d+")
            instance = af.split("_")[0] if af else info["default_adc"]
            if not re.fullmatch(r"ADC\d+", instance):
                mm = re.match(r"ADC\d+", instance)
                instance = mm.group(0) if mm else info["default_adc"]
            entry = next((a for a in usage["adc"] if a["instance"] == instance), None)
            if entry is None:
                entry = {"instance": instance, "pin_map": {}}
                usage["adc"].append(entry)
            entry["pin_map"][net.lower()] = _pininfo(pin)
            continue

        if periph == "TIMER PWM":
            # 8 位缩写（FT61F 芯片侧 T1_CH1 / 32 位 TIM1_CH1、TIMER1_CH1）统一兼容
            pinfo = _pininfo(pin)
            af = _af_lookup_pin(str(pin["pin"]), pinfo["name"] if pinfo else "",
                                r"(?:T(?:IMER|IM)?\d+)_CH\d+N?")
            if af:
                mm = re.match(r"((?:T(?:IMER|IM)?)\d+)_CH(\d+N?)", af)
                instance, channel = mm.group(1), f"CH{mm.group(2)}"
                ch = f"TIMER_{channel}" if instance.startswith("TIMER") else channel
                usage["pwm"].append({"instance": instance, "channel": ch, "pclk_hz": 0,
                                     "pin": pinfo})
            else:
                usage["constraints"].append(f"PWM 引脚 {name}({net}) 无法定位定时器实例")
            continue

        if periph == "FSMC" or "并口/LCD" in role:
            usage["fsmc"].append(_pininfo(pin))
            usage["gpio"].append({**_pininfo(pin), "mode": "AF_PP", "af": "FSMC/EXMC"})
            continue

        # 通用 GPIO：无语义引脚（NetU1_xx 类）跳过，不臆测配置
        pinfo = _pininfo(pin)
        if not periph and not role:
            continue
        if not net:
            usage["gpio_skipped"].append(name)
            continue
        if periph == "GPIO 输入上拉" or "上拉" in (pin.get("config") or ""):
            pinfo["mode"] = "IPU"
        elif periph == "GPIO 输出" or "输出" in role or "LED" in role:
            pinfo["mode"] = "OUT_PP"
        elif "模拟" in role:
            pinfo["mode"] = "AIN"
        else:
            pinfo["mode"] = "IN_FLOATING"
        pinfo["af"] = None
        usage["gpio"].append(pinfo)

    # 未识别语义的引脚（NetU1_xx 类）记入约束，不臆测配置
    unclassified = [p for p in facts.get("pins", [])
                    if p.get("component") == mcu_designator and not p.get("nc")
                    and not (p.get("peripheral") or "").strip() and not (p.get("role") or "").strip()]
    if unclassified:
        usage["constraints"].append(
            f"{len(unclassified)} 个已连接引脚网络名无语义（如 {unclassified[0].get('net')}），未生成 GPIO 配置，待 AI/人工补充")
    return usage


def backfill_pwm_pclk(usage: dict, platform: str, clock_cfg: dict) -> None:
    """按平台 APB2 定时器集合回填 PWM 实例的时钟频率（brief 供 Agent 计算分频）。"""
    info, _ = get_platform_info(platform)
    for w in usage.get("pwm", []):
        w["pclk_hz"] = clock_cfg["apb2_hz"] if w["instance"].upper() in info["apb2_timers"] \
            else clock_cfg["apb1_hz"]


def fsmc_data_width(usage: dict) -> int:
    """按数据线网络名（DB0..DBn）判定 FSMC/EXMC 数据宽度。"""
    db_count = sum(1 for p in usage.get("fsmc", [])
                   if re.search(r"(?:DB|D)\d+", str(p.get("net", "")), re.I))
    return 16 if db_count >= 16 else 8


# ---------------- 时钟数值计算（纯数值，不生成代码） ----------------

def extract_osc_facts(facts: dict) -> tuple[int | None, int | None]:
    """从 S4 facts 提取 HSE/LSE 频率；HSE 缺失时从 OSC_IN 网络名兜底。"""
    hse_hz = freq_hz(facts.get("clocks", {}).get("HSE", ""))
    if hse_hz is None:
        for p in facts.get("pins", []):
            if "OSC_IN" in (p.get("pin_name") or "") and p.get("net"):
                hse_hz = freq_hz(p["net"])
                break
    lse_hz = freq_hz(facts.get("clocks", {}).get("LSE", ""))
    return hse_hz, lse_hz


def compute_clock(platform: str, hse_hz: int | None, lse_used: bool,
                  sysclk_target_hz: int | None = None) -> dict:
    """时钟数值计算（Agent 直接采用，不自行推导）。

    策略：HSE × 最大整数倍频（主频上限内）；设计输入目标可达则精确采用，
    否则回退并记 sysclk_note。AHB=SYSCLK，APB1=AHB/2（超上限时），
    APB2=AHB。STM32F1x 联动 FLASH 等待周期（≤24MHz 0WS/≤48MHz 1WS/其余 2WS）。
    未登记平台按保守缺省（HSE 直跑/目标倍频建议）并在 notes 提示 Agent 复核。
    """
    info, registered = get_platform_info(platform)
    cfg = {"sysclk_hz": hse_hz or 8_000_000, "ahb_hz": 0, "apb1_hz": 0, "apb2_hz": 0,
           "pll_mul": 1, "source": "", "sysclk_note": None,
           "flash_latency_ws": None, "notes": []}
    notes: list[str] = []
    if not registered:
        notes.append(f"平台 {platform} 未登记时钟数值约束：以下方案为保守建议，"
                     "Agent 须依据参考手册/SDK 头文件核对主频上限、PLL 倍频范围与总线分频")
    if not hse_hz:
        # 无外部晶振：内部 RC 直跑（8 位机 HIRC 等平台基准由 target_sysclk_hz 提供）
        base = info["target_sysclk_hz"] or 8_000_000
        src_desc = f"内部 {base / 1_000_000:g}MHz 直跑（S4 未发现外部晶振，未启 PLL）"
        cfg.update(sysclk_hz=base, ahb_hz=base, apb1_hz=base, apb2_hz=base, pll_mul=1,
                   source=src_desc, notes=notes)
        return cfg

    mul_max = info["pll_mul_max"]
    if info["target_sysclk_hz"]:
        mul = max(2, min(mul_max, info["target_sysclk_hz"] // hse_hz))
        fallback_desc = "主频上限内最大整数倍频"
    else:
        mul = 1
        fallback_desc = "HSE 直跑（平台未登记上限）"
    if sysclk_target_hz:
        mul_t = sysclk_target_hz // hse_hz
        if (sysclk_target_hz % hse_hz == 0 and 2 <= mul_t <= mul_max
                and (info["sysclk_max_hz"] is None or sysclk_target_hz <= info["sysclk_max_hz"])):
            mul = mul_t
        else:
            cfg["sysclk_note"] = (f"目标 {sysclk_target_hz // 1_000_000}MHz 不可达"
                                  f"（HSE 整数倍频/主频上限约束），回退{fallback_desc}")
    sysclk = hse_hz * mul
    apb1_div = 2 if (info["apb1_max_hz"] and sysclk > info["apb1_max_hz"]) else 1
    latency_ws = None
    for max_hz, ws in (info["flash_latency"] or []):
        if max_hz is None or sysclk <= max_hz:
            latency_ws = ws
            break
    cfg.update(sysclk_hz=sysclk, ahb_hz=sysclk, apb1_hz=sysclk // apb1_div,
               apb2_hz=sysclk, pll_mul=mul, flash_latency_ws=latency_ws,
               source=f"HSE {hse_hz / 1_000_000:g}MHz × {mul}", notes=notes)
    return cfg


# ---------------- S3/S4 执行上下文（prepare/validate 共用） ----------------

def load_context(config_path: Path, workspace: Path | None = None,
                 arch_override: str | None = None) -> dict:
    """加载配置与 S3/S4 数据，返回执行上下文。

    抛出 RuntimeError（含可读错误信息）——由调用方决定写 error 状态。
    返回：config/workspace/state_path/outputs_dir/platform_name/architecture/
    rtos/power_enabled/baudrate/state/facts/chip_pins/peripherals/netlist。
    """
    config, _notes = load_layered_config(config_path)
    # 合并配置契约校验：根目录 schemas/config.schema.json（S2/S3/S4/S5a 同一权威来源，
    # project.architecture/rtos/power.enabled 枚举等；填错立即报错，prepare 写 state error）
    cfg_errors = validate_schema(config, ROOT_DIR / "schemas" / "config.schema.json", "config")
    if cfg_errors:
        raise RuntimeError("配置契约校验失败: " + "; ".join(cfg_errors))
    if workspace is None:
        workspace = config_path.parent
    # 目标工程根（App/BootLoader 双工程）：state/src/outputs 归目标工程，
    # docs/ 等共享资源留在项目根
    project_root = workspace
    workspace = resolve_target(config, project_root)
    state_path = workspace / "state.json"
    if not state_path.exists():
        raise RuntimeError(f"state.json 不存在: {state_path}（先执行 S1/S3/S4）")
    state = load_json(state_path)

    chip = state.get("chip") or {}
    facts_info = (state.get("circuit") or {}).get("facts") or {}
    input_errors = validate_schema(state, SKILL_DIR / "schemas" / "input.schema.json", "state")
    if input_errors:
        raise RuntimeError("输入契约校验失败: " + "; ".join(input_errors))
    if chip.get("extract_status") == "failed":
        raise RuntimeError("S3 提取失败，无法执行 S5a")
    if facts_info.get("verify_status") == "failed":
        raise RuntimeError("S4 验证失败，无法执行 S5a")

    facts = load_json(workspace / facts_info["facts_path"])
    chip_pins_doc = load_json(workspace / chip["pins_path"])
    chip_pins = chip_pins_doc.get("pins", chip_pins_doc) if isinstance(chip_pins_doc, dict) else chip_pins_doc
    peripherals_doc = load_json(workspace / chip["peripherals_path"])
    peripherals = peripherals_doc.get("peripherals", []) if isinstance(peripherals_doc, dict) else peripherals_doc
    netlist = load_json(workspace / (state.get("circuit") or {}).get("netlist_path", "outputs/circuit_netlist.json"))

    platform_name = config.get("platform") or config.get("project", {}).get("target", "")
    if not platform_name:
        raise RuntimeError("config 缺少 platform / project.target")

    project_cfg = config.get("project") or {}
    architecture = arch_override or project_cfg.get("architecture") or "layered"
    rtos = project_cfg.get("rtos") or "none"
    power_enabled = (project_cfg.get("power") or {}).get("enabled", False)
    return {
        "config": config,
        "workspace": workspace,
        "project_root": project_root,
        "state_path": state_path,
        "state": state,
        "outputs_dir": workspace / (config.get("output_dir") or "outputs").rstrip("/\\"),
        "platform_name": platform_name,
        "architecture": architecture,
        "rtos": rtos,
        "power_enabled": power_enabled,
        "baudrate": int((config.get("s5a") or {}).get("uart_baudrate", 115200)),
        "facts": facts,
        "chip_pins": chip_pins,
        "peripherals": peripherals,
        "netlist": netlist,
    }


def run_usage_analysis(ctx: dict) -> tuple[dict, dict, int | None, int | None, dict | None]:
    """完整确定性分析：usage + 设计输入 + 时钟数值（prepare/validate 共用）。

    返回 (usage, clock_cfg, hse_hz, lse_hz, design_input)。
    """
    usage = analyze_usage(ctx["facts"], ctx["netlist"], ctx["chip_pins"],
                          ctx["peripherals"], ctx["platform_name"], ctx["baudrate"])
    design_input = load_design_input(ctx.get("project_root") or ctx["workspace"])
    hse_hz, lse_hz = extract_osc_facts(ctx["facts"])
    sysclk_target_hz = (int(design_input["sysclk_mhz"] * 1_000_000)
                        if design_input and design_input.get("sysclk_mhz") else None)
    clock_cfg = compute_clock(ctx["platform_name"], hse_hz, bool(lse_hz), sysclk_target_hz)
    apply_design_input(usage, design_input, clock_cfg)
    backfill_pwm_pclk(usage, ctx["platform_name"], clock_cfg)
    return usage, clock_cfg, hse_hz, lse_hz, design_input


def resolve_stdperiph_lib(ctx: dict) -> tuple[Path | None, str]:
    """定位标准外设库：config.stdperiph_lib_path 优先（按约定，
    'platforms/' 开头的相对路径相对根目录，其余相对项目目录），
    回退根目录 platforms/<platform>/std_periph_lib/ 惯例。"""
    rel = (ctx["config"].get("stdperiph_lib_path") or "").strip()
    candidates: list[Path] = []
    if rel:
        cand = Path(rel)
        if cand.is_absolute():
            candidates.append(cand)
        elif rel.replace("\\", "/").startswith("platforms/"):
            candidates.append(ROOT_DIR / rel)
        else:
            candidates.append((ctx.get("project_root") or ctx["workspace"]) / rel)
    candidates.append(ROOT_DIR / "platforms" / ctx["platform_name"] / "std_periph_lib")
    for idx, cand in enumerate(candidates):
        if cand.is_dir():
            if idx < len(candidates) - 1:
                return cand, "config.stdperiph_lib_path"
            return cand, f"根目录惯例 platforms/{ctx['platform_name']}/std_periph_lib"
    return None, "未找到标准外设库目录"
