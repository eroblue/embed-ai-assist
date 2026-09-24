#!/usr/bin/env python
"""S5a hardware-initializer 第 1 段：prepare（rule 轨）。

三段式执行模型（用户拍板：rule 只做确定性契约工作，C 代码生成归 Agent）：
  1. [rule]  prepare.py   → 分析硬件事实 + 计算时钟数值，输出 Agent 任务书
                            outputs/s5a/generation_brief.md，state.s5a = running
  2. [agent] Agent 生成    → 按 SKILL.md 指引 + 任务书 + references/
                            init_code_templates.md 亲自编写 S5a 产物目录
                            （PROJECT_LAYOUT.md 解析，如 Drivers/BSP/{Src,Inc}）
                            的 *.c/h
  3. [rule]  validate.py  → 校验产物、聚合 hardware_capabilities.json、
                            输出 IDE 待添加清单，state.s5a = done

本脚本不生成任何 C 代码；新增硬件平台无需编写适配脚本。
产物目录不硬编码：prepare 段先按 PROJECT_LAYOUT.md 解析布局
（layout_resolver）并幂等创建目录骨架（ensure_layout），
任务书中的产物路径全部来自解析结果——改布局文档即全局生效。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.version_info < (3, 10):  # 版本守卫：本框架需 3.10+（如 Path.write_text(newline=)）
    import json as _json
    from pathlib import Path as _Path
    try:
        _root_cfg = _json.loads(
            (_Path(__file__).resolve().parents[3] / "config.json").read_text(encoding="utf-8"))
        _py = _root_cfg.get("tool_paths", {}).get("python", "")
    except Exception:
        _py = ""
    print(f"[错误] 本框架需要 Python 3.10+，当前解释器为 {sys.version.split()[0]}。"
          + (f"请使用项目配置的解释器：{_py}" if _py
             else "项目配置的解释器见根目录 config.json 的 tool_paths.python"),
          file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SKILL_DIR.parent / "_shared" / "scripts"))

import analysis  # noqa: E402
import ensure_layout as ensure_layout_mod  # noqa: E402
import layout_resolver  # noqa: E402
import state_store  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2


def _log(msg: str) -> None:
    print(f"[s5a-prepare] {msg}", file=sys.stderr)


def _fmt_hz(hz: int | None) -> str:
    if not hz:
        return "未使用"
    if hz % 1_000_000 == 0:
        return f"{hz // 1_000_000}MHz"
    return f"{hz / 1000:g}kHz"


def _resolve_workspace(config_path: Path, workspace_arg: str | None) -> Path:
    workspace = Path(workspace_arg or ".").expanduser()
    if not workspace.is_absolute():
        workspace = (config_path.parent / workspace).resolve()
    return workspace


def collect_modules(ctx: dict, usage: dict) -> list[str]:
    """本轮应生成的模块清单（build_brief 与增量快照共用，不含总入口）。"""
    modules = ["clock_init", "nvic_init"]
    if usage["gpio"] or usage["fsmc"]:
        modules.append("gpio_init")
    for key in ("uart", "spi", "i2c", "adc", "pwm", "fsmc"):
        if usage[key]:
            modules.append(f"{key}_init")
    if ctx["rtos"] != "none":
        modules.append("rtos_hw_init")
    if ctx["power_enabled"]:
        modules.append("power_init")
    return sorted(set(modules))


def build_snapshot(ctx: dict, usage: dict, clock_cfg: dict, hse_hz, lse_hz, modules) -> dict:
    """模块级数值快照（增量 diff 依据；只含影响生成内容的确定性数值）。"""
    def _norm(obj):
        return json.loads(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str))
    return {
        "platform": ctx["platform_name"], "rtos": ctx["rtos"],
        "architecture": ctx["architecture"], "power": ctx["power_enabled"],
        "modules": modules,
        "domains": {
            "clock": {"sysclk_hz": clock_cfg["sysclk_hz"], "hse_hz": hse_hz, "lse_hz": lse_hz,
                      "ahb_hz": clock_cfg["ahb_hz"], "apb1_hz": clock_cfg["apb1_hz"],
                      "apb2_hz": clock_cfg["apb2_hz"]},
            "gpio": _norm(usage["gpio"]), "uart": _norm(usage["uart"]),
            "spi": _norm(usage["spi"]), "i2c": _norm(usage["i2c"]),
            "adc": _norm(usage["adc"]), "pwm": _norm(usage["pwm"]),
            "fsmc": _norm(usage["fsmc"]), "irq_names": _norm(usage.get("irq_names", [])),
        },
    }


# 域 → 受影响模块（值域必须落在 collect_modules 产出的模块名上）
_DOMAIN_MODULES = {
    "clock": ["clock_init"], "gpio": ["gpio_init"],
    "uart": ["uart_init"], "spi": ["spi_init"], "i2c": ["i2c_init"], "adc": ["adc_init"],
    "pwm": ["pwm_init"], "fsmc": ["fsmc_init", "gpio_init"],
    "rtos": ["rtos_hw_init"], "power": ["power_init"],
}


def diff_modules(prev: dict | None, curr: dict, entry: str) -> tuple[list[str], list[str]]:
    """对比上轮快照，返回 (changed, unchanged)。

    无上轮快照 / 平台/RTOS/架构/低功耗任一变化 → 全量重写；
    域级变化 → 按映射表扩散；模块集合变化 → 总入口重写。
    """
    all_modules = sorted(set(curr["modules"]) | {entry})
    if prev is None:
        return all_modules, []
    if any(prev.get(k) != curr.get(k) for k in ("platform", "rtos", "architecture", "power")):
        return all_modules, []
    changed: set[str] = set()
    prev_domains = prev.get("domains", {})
    for domain, mods in _DOMAIN_MODULES.items():
        if prev_domains.get(domain) != curr["domains"].get(domain):
            changed.update(m for m in mods if m in all_modules)
    if prev_domains.get("irq_names") != curr["domains"].get("irq_names"):
        changed.add("nvic_init")
    if prev.get("modules") != curr.get("modules"):
        changed.add(entry)
    changed = {m for m in changed if m in all_modules}
    unchanged = [m for m in all_modules if m not in changed]
    return sorted(changed), unchanged


def build_brief(ctx: dict, usage: dict, clock_cfg: dict, hse_hz: int | None,
                lse_hz: int | None, design_input: dict | None,
                plan: dict,
                changed: list[str] | None = None, unchanged: list[str] | None = None,
                incremental: bool = False) -> str:
    """构建 generation_brief.md（Agent 代码生成的结构化任务书）。"""
    platform = ctx["platform_name"]
    info, registered = analysis.get_platform_info(platform)
    mcu = ctx["facts"].get("mcu") or platform
    s5a_src = plan["skill_dirs"]["s5a"]["src"][0]
    s5a_inc = plan["skill_dirs"]["s5a"]["inc"][0]
    lines: list[str] = []
    add = lines.append

    add("# S5a 代码生成任务书（generation_brief）")
    add("")
    add(f"> 由 prepare.py 生成（rule 轨）。Agent 按本任务书在 `{s5a_src}/` 写 .c、"
        f"`{s5a_inc}/` 写 .h，")
    add("> 生成规范见 `skills/hardware-initializer/references/init_code_templates.md`。")
    add("> 引脚/实例/时钟数值均已从 S3/S4 事实确定，直接采用，不要自行改推。")
    add("")

    # ---- 1. 项目信息 ----
    add("## 1. 项目信息")
    add("")
    add(f"- MCU：{mcu}（platform: {platform}）")
    add(f"- 架构：{ctx['architecture']}；RTOS：{ctx['rtos']}；低功耗：{'启用' if ctx['power_enabled'] else '未启用'}")
    lib_path, lib_src = analysis.resolve_stdperiph_lib(ctx)
    if lib_path:
        add(f"- 标准外设库：`{lib_path}`（来源 {lib_src}）——生成前读其头文件确认 API/枚举名")
    else:
        add("- 标准外设库：**未找到**——依据 `sdk_header_path` 指向的 CMSIS 头与 datasheet 确认 API")
    if info["include"]:
        add(f"- 平台主头文件：`{info['include']}`（外设模块 .c 需 include）")
    else:
        add("- 平台主头文件：从 SDK 目录确认（平台未登记）")
    if design_input:
        add(f"- 用户设计输入：`{design_input['path']}`（DMA 模式/特殊引脚等语义按原文校正，rule 轨只消费了波特率/主频）")
    else:
        add("- 用户设计输入：无——外设使用模式由你（Agent）基于下列硬件事实自主判断")
    add("")

    # ---- 2. 时钟配置 ----
    add("## 2. 时钟配置（已计算，直接采用）")
    add("")
    add(f"- HSE：{_fmt_hz(hse_hz) if hse_hz else '未发现（按内部 RC 直跑，频率见 SYSCLK）'}（来源 S4 硬件事实）")
    if hse_hz:
        add(f"- SYSCLK：{_fmt_hz(clock_cfg['sysclk_hz'])} = HSE × PLL{clock_cfg['pll_mul']}")
    else:
        add(f"- SYSCLK：{_fmt_hz(clock_cfg['sysclk_hz'])}（内部 RC）")
    add(f"- AHB：{_fmt_hz(clock_cfg['ahb_hz'])}；APB1：{_fmt_hz(clock_cfg['apb1_hz'])}；APB2：{_fmt_hz(clock_cfg['apb2_hz'])}")
    if lse_hz:
        add(f"- LSE：{_fmt_hz(lse_hz)}（RTC 时钟源，clock_init 中使能并选为 RTC 时钟）")
    if clock_cfg.get("flash_latency_ws") is not None:
        add(f"- FLASH 等待周期：{clock_cfg['flash_latency_ws']}WS（主频联动，勿遗漏）")
    if clock_cfg.get("sysclk_note"):
        add(f"- **回退说明**：{clock_cfg['sysclk_note']}（已记入 capabilities.constraints）")
    for note in clock_cfg.get("notes", []):
        add(f"- **注意**：{note}")
    add("")

    # ---- 3. 外设使用清单 ----
    add("## 3. 外设使用清单（引脚来自 S4 facts + S3 AF 表）")
    add("")
    if usage["uart"]:
        add("### UART")
        for u in usage["uart"]:
            tx = f"{u['tx']['name']}（net {u['tx']['net']}）" if u.get("tx") else "未连接"
            rx = f"{u['rx']['name']}（net {u['rx']['net']}）" if u.get("rx") else "未连接（仅 TX）"
            irq = u.get("irq") or "（SDK 头文件确认 IRQn 名）"
            add(f"- {u['instance']}：TX={tx}，RX={rx}，{u.get('baud', 115200)}-8N1，中断：{irq}")
        add("")
    if usage["spi"]:
        add("### SPI")
        for s in usage["spi"]:
            pins = "，".join(f"{k.upper()}={p['name']}" for k, p in sorted(s["pin_map"].items()))
            remap = "；**引脚来自 AF remap，需使能 AFIO 时钟并做重映射**" if s.get("remap") else ""
            add(f"- {s['instance']}（主模式，8bit，软 NSS）：{pins}{remap}")
        add("")
    if usage["i2c"]:
        add("### I2C")
        for i in usage["i2c"]:
            pins = "，".join(f"{k.upper()}={p['name']}" for k, p in sorted(i["pin_map"].items()))
            add(f"- {i['instance']}（100kHz 标准模式，开漏复用）：{pins}")
        add("")
    if usage["adc"]:
        add("### ADC")
        for a in usage["adc"]:
            pins = "，".join(f"{k}={p['name']}" for k, p in sorted(a["pin_map"].items()))
            add(f"- {a['instance']}（12bit 右对齐，通道/采样时间待 S5b 用例确定，留 TODO）：{pins}")
        add("")
    if usage["pwm"]:
        add("### PWM")
        for w in usage["pwm"]:
            add(f"- {w['instance']} {w['channel']}：输出 {w['pin']['name']}（net {w['pin']['net']}），"
                f"定时器时钟 {_fmt_hz(w['pclk_hz'])}，默认 1kHz/50% 占空比")
        add("")
    if usage["fsmc"]:
        width = analysis.fsmc_data_width(usage)
        add("### FSMC/EXMC（LCD 并口）")
        add(f"- 数据宽度：{width} 位（按数据线网络名判定）；bank 建议 NE1（基址 0x60000000）")
        pins_desc = "，".join(f"{p['name']}（{p['net']}）" for p in usage["fsmc"])
        add(f"- 引脚：{pins_desc}")
        add("- 时序取保守默认值（慢速，保证点亮），代码中注释标注需按 LCD 驱动手册调整")
        add("")
    if usage["gpio"]:
        add("### GPIO（按端口分组）")
        by_port: dict[str, list] = {}
        for p in usage["gpio"]:
            by_port.setdefault(p["port"], []).append(p)
        for port in sorted(by_port):
            for p in sorted(by_port[port], key=lambda x: x["pin_no"]):
                af = f" - {p['af']}" if p.get("af") else ""
                add(f"- {p['name']}：`{p['mode']}`（net {p['net']}{af}）")
        add("")
    if usage.get("irq_names"):
        add(f"### 中断：{', '.join(usage['irq_names'])}（只做 NVIC 分组，不使能具体 IRQ，注释给使能建议）")
        add("")
    if usage.get("gpio_skipped"):
        add(f"### 跳过的引脚（晶振/电源/调试/无语义）：{', '.join(usage['gpio_skipped'][:20])}"
            f"{'...' if len(usage['gpio_skipped']) > 20 else ''}")
        add("")

    # ---- 4. 生成要求 ----
    add("## 4. 生成要求")
    add("")
    modules = collect_modules(ctx, usage)
    entry = "board_init" if ctx["architecture"] == "flat" else "hal_init"
    add(f"### 文件清单（{s5a_src}/ 下 .c + {s5a_inc}/ 下 .h，每模块成对）")
    add("")
    add(f"`{', '.join(modules)}` + 总入口 `{entry}`（只做汇总调用）")
    add("")
    if changed is not None:
        add("### 增量模式（本轮生成范围）")
        add("")
        if incremental:
            if changed:
                add(f"- **CHANGED（重写 .c/.h）**：`{', '.join(changed)}`")
                if unchanged:
                    add(f"- UNCHANGED（保持现有文件不动，勿重写）：`{', '.join(unchanged)}`")
                add("- 数值依据仍以本任务书第 2/3 节为准；仅重写 CHANGED 模块，其余文件不得改动")
            else:
                add("- **无变更模块**：本轮输入与上轮一致，无需生成代码，直接运行 validate.py 收尾")
        else:
            add(f"- 全量模式（首次运行/配置大变）：重写全部模块 `{', '.join(sorted(set(modules) | {entry}))}`")
        add("")
    add("### 硬性规则")
    add("")
    add(f"1. 落盘位置：`.c` 写入 `{s5a_src}/`，`.h` 写入 `{s5a_inc}/`"
        "（目录已由 prepare 创建，路径来自 docs/PROJECT_LAYOUT.md，勿写其他目录）")
    add("2. 命名：`<module>_init.c/h`；每实例一个函数（如 `uart_usart5_init`），模块级 `<module>_init()` 汇总调用")
    add("3. 头文件带 include guard；.c 首行注释 `/* <module>_init.c - <说明>（S5a hardware-initializer 生成，<MCU>） */`")
    add("4. 调用顺序：`clock_init() → gpio_init() → nvic_init() → 各外设 init() → rtos_hw_init()/power_init()（如有）`")
    add("5. 中断：只做 NVIC 优先级分组，不使能具体 IRQ（避免未注册 handler 落入默认死循环），使能建议以注释生成")
    add("6. 平台 API 以标准外设库头文件为准（宏/枚举名逐一核对），不确定的留 TODO 注释，不臆造 API")
    add("7. FSMC 引脚复用（AF_PP）在 gpio_init.c 完成，fsmc_init.c 只有 bank/时序本体")
    add("8. 批量写入：单轮响应内并行发出多个文件的写入调用（建议 4 文件/轮，即 2 模块的 .c/.h），")
    add("   全部模块写完后统一核对与校验——组稿与核对分离，避免逐文件\"写→等结果→再写\"的往返开销")
    add("")

    # ---- 5. 禁止事项 ----
    add("## 5. 禁止事项")
    add("")
    add("- 不 include `app.h` / `driver_*.h` / `port_*.h` / `osal_*.h`，不含任何应用业务逻辑")
    add("- 不定义 Port/OSAL 接口（S5b 职责），不生成 `port_impl_*.c`（S5c 职责）")
    add("- 不修改 IDE 工程文件（.uvprojx/.ewp 等）——同步由公共工具 skills/_shared/scripts/ide_sync.py 完成")
    add("- 不把代码写进 outputs/，不把数据写进 src/；不修改 S3/S4 产物与 config.json")
    add("- 不把所有初始化塞进单文件；引脚/时钟/DMA/中断不得冲突")
    add("")

    # ---- 6. 数据来源（Agent 深查用） ----
    add("## 6. 数据来源（需要深查时再读）")
    add("")
    state = ctx["state"]
    chip = state.get("chip") or {}
    facts_info = (state.get("circuit") or {}).get("facts") or {}
    add(f"- S4 硬件事实：`{facts_info.get('facts_path')}`")
    add(f"- S3 芯片引脚：`{chip.get('pins_path')}`；外设：`{chip.get('peripherals_path')}`")
    if ctx["config"].get("sdk_header_path"):
        add(f"- SDK CMSIS 头：`{ctx['config']['sdk_header_path']}`")
    if ctx["config"].get("svd_path"):
        add(f"- SVD（寄存器/中断名核对）：`{ctx['config']['svd_path']}`")
    add("")
    add("生成完成后运行 `validate.py` 校验；失败按报告修复后重跑。")
    return "\n".join(lines)


def _write_error_state(config_path: Path, workspace: Path, error: str) -> dict:
    payload = {"status": "error", "error": error, "updated_at": datetime.now().isoformat(timespec="seconds")}
    # 尽力解析目标工程根（config 损坏时按 App 兜底）
    try:
        cfg = analysis.load_layered_config(config_path)[0]
    except Exception:
        cfg = None
    state_path = analysis.resolve_target(cfg, workspace) / "state.json"
    try:
        state_store.update_state(state_path, {"s5a": payload})
    except (OSError, state_store.StateLockTimeout):
        pass
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="S5a prepare: 确定性分析 + 生成 Agent 任务书（不生成 C 代码）")
    parser.add_argument("--config", default="config.json", help="项目 config.json 路径")
    parser.add_argument("--arch", choices=["flat", "layered", "full"], default=None,
                        help="覆盖架构（仅本次生效）")
    parser.add_argument("--workspace", default=None, help="覆盖项目目录（默认 --config 所在目录）")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    workspace = _resolve_workspace(config_path, args.workspace)
    try:
        ctx = analysis.load_context(config_path, workspace, arch_override=args.arch)
        usage, clock_cfg, hse_hz, lse_hz, design_input = analysis.run_usage_analysis(ctx)
    except (RuntimeError, FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        payload = _write_error_state(config_path, workspace, str(exc))
        _log(str(exc))
        print(json.dumps({"s5a": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR

    # ---- 目录骨架 + 布局解析（骨架先于 Agent 代码生成；PROJECT_LAYOUT.md 唯一事实来源）----
    try:
        ensure_result = ensure_layout_mod.ensure_layout(
            project_root=ctx["project_root"], config=ctx["config"],
            state=ctx["state"], target=ctx["workspace"].name, quiet=True)
        plan = ensure_result["plan"]
        if not plan["skill_dirs"]["s5a"]["src"] or not plan["skill_dirs"]["s5a"]["inc"]:
            raise layout_resolver.LayoutError(
                "布局中未解析到 S5a 产物目录（PROJECT_LAYOUT.md 目录树需有带 "
                "S5a 注释的 Src/Inc 目录）")
    except layout_resolver.LayoutError as exc:
        payload = _write_error_state(config_path, workspace, f"布局解析失败: {exc}")
        _log(str(payload["error"]))
        print(json.dumps({"s5a": payload}, ensure_ascii=False, indent=2))
        return EXIT_CONFIG_ERROR
    for w in plan.get("warnings", []):
        _log(f"布局警告: {w}")
    if ensure_result["created"]:
        _log(f"已创建目录骨架: {', '.join(ensure_result['created'])}")

    # ---- 增量 diff：模块数值快照 vs 上轮 ----
    modules = collect_modules(ctx, usage)
    entry = "board_init" if ctx["architecture"] == "flat" else "hal_init"
    snapshot = build_snapshot(ctx, usage, clock_cfg, hse_hz, lse_hz, modules)
    snap_path = ctx["outputs_dir"] / "s5a" / "module_snapshot.json"
    prev_snapshot = None
    if snap_path.exists():
        try:
            prev_snapshot = analysis.load_json(snap_path)
        except (json.JSONDecodeError, OSError):
            prev_snapshot = None
    changed, unchanged = diff_modules(prev_snapshot, snapshot, entry)
    incremental = prev_snapshot is not None
    _log(("增量模式" if incremental else "全量模式") +
         (f"：CHANGED = {', '.join(changed)}" if changed else "：无变更模块，可直接 validate"))

    # ---- 输出 Agent 任务书 ----
    brief_rel = "outputs/s5a/generation_brief.md"
    brief_path = ctx["outputs_dir"] / "s5a" / "generation_brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(
        build_brief(ctx, usage, clock_cfg, hse_hz, lse_hz, design_input, plan,
                    changed=changed, unchanged=unchanged, incremental=incremental),
        encoding="utf-8", newline="\n")
    analysis.save_json(snap_path, snapshot)

    # ---- state.s5a = running（等待 Agent 生成代码）----
    payload = {
        "status": "running",
        "rtos": ctx["rtos"],
        "architecture": ctx["architecture"],
        "power_enabled": ctx["power_enabled"],
        "generation_brief": brief_rel,
        "incremental": incremental,
        "changed_modules": changed,
        "error": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    schema_errors = analysis.validate_schema(
        payload, SKILL_DIR / "schemas" / "output.schema.json", "s5a")
    if schema_errors:
        _write_error_state(config_path, workspace, "; ".join(schema_errors))
        _log("s5a 状态契约校验失败: " + "; ".join(schema_errors))
        return EXIT_FAILED
    state_store.update_state(ctx["state_path"], {"s5a": payload})

    _log(f"任务书已生成: {brief_path}")
    _log(f"下一步：Agent 按 SKILL.md 指引 + 任务书 + references/init_code_templates.md "
         f"在 {plan['skill_dirs']['s5a']['src'][0]}/ 与 {plan['skill_dirs']['s5a']['inc'][0]}/ 编写代码")
    print(json.dumps({"s5a": payload}, ensure_ascii=False, indent=2))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
