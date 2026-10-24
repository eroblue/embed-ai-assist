---
name: flash
description: "S9 flash 烧录技能。触发时机：S7b build done 之后（或 S6 firmware-merger done 之后烧合并固件），由 S12 workflow-runner 编排或用户手动执行。当用户要求'烧录固件/下载程序/flash/download/复烧'时使用本技能。四段式：rule prepare → rule flash（CLI）→ agent analyze（仅失败）→ rule validate。"
---

# S9 flash Skill

调用烧录工具将固件写入目标 MCU Flash 并校验复位（**烧录部署**层）。

- **双烧录机制**：**CLI 机制**（J-Link Commander / J-Flash / STM32CubeProgrammer CLI /
  OpenOCD / pyOCD，纯 rule）与 **GUI 机制**（`vendor_ide`：厂家 IDE 无 CLI 时 Agent 按
  vendor 指南操作下载按钮，五期演进项）。**一期仅实现 jlink 全链路**。
- **烧的即发布的**：烧录前将固件聚合**发布**到 `<项目根>/release/`（用户唯一需要
  关注的固件交付目录），并**从该目录副本执行烧录**；S9 是 release/ 的唯一写者。
- **flash_offset 唯一权威**：烧录目标地址按 `project.flash_offset`（config）计算，
  与 S5b 向量重定位、S7b 链接脚本、S6 bin 拼接共用同一 config 值。
- **失败不猜**：失败时 Agent 产出 `error_analysis.md`（连接 / 芯片 / 固件 / 工具四类
  根因），**不自动重试、不自动解锁**；工具缺失**不自动安装**（完全用户自管理）。
- **执行策略**：直接执行烧录，不请求人工确认（开发迭代场景；verify 缺省开启兜底，
  prepare 任务书完整展示固件/地址/设备/探针信息供追溯）。

## 目录结构

```
skills/flash/
├── SKILL.md                     # 本文件
├── schemas/
│   ├── input.schema.json        # S9 就绪契约（state.s7b done + hex/bin ≥1；--firmware 跳过）
│   ├── output.schema.json       # state.s9 字段契约
│   ├── flash_result.schema.json # outputs/s9/flash_result.json 契约
│   └── flash_info.schema.json   # release/flash_info.json 发布清单契约
├── scripts/
│   ├── analysis.py              # 共享分析（复用 S7b：配置加载/uvprojx 解析/平台惯例/日志解码）
│   ├── prepare.py               # 第 1 段 [rule]：就绪检查 + 计划 + release 发布 + jlink 脚本
│   ├── flash.py                 # 第 2 段 [rule]：执行烧录 + 日志解析 + 产物落盘
│   └── validate.py              # 第 4 段 [rule]：产物验证 + state 收口
├── references/
│   ├── jlink_flash_guide.md     # J-Link Commander 指南（设备名映射表/命令/日志特征/下载渠道）
│   ├── flash_log_parse_rules.md # 日志特征行映射表（jlink 详写；其余工具演进期占位）
│   ├── stlink_flash_guide.md    # STM32CubeProgrammer CLI（三期演进项，占位）
│   ├── openocd_flash_guide.md   # OpenOCD（三期演进项，占位）
│   ├── pyocd_flash_guide.md     # pyOCD（四期演进项，占位）
│   ├── jflash_flash_guide.md    # J-Flash CLI + .jflash 决策流程（二期演进项，占位）
│   └── vendor_flash/
│       └── _template.md         # 厂家 IDE GUI 烧录指南模板（五期）
└── assets/
    └── flash_example.md         # jlink 全链路使用示例
```

## 执行步骤（四段式）

**阶段 A [rule] `prepare.py`**（退出码 0 / 2 / 3[二期]）

1. `--config` 加载项目配置（与全局 config 深合并，只读）；`--firmware` 显式时跳过
   state 就绪检查，否则校验 `s7b.status = done` 且 hex/bin 至少一个非空
2. 平台与机制判定：`arch_family = mcu8` → 必须显式配置 flash_tool（不推断）；
   Cortex-M 时 `vendor_ide` 报错（GUI 仅 8 位）
3. 烧录工具判定：显式 `project.flash_tool` 优先；`null` 时智能推断
   （uvoptx `<pMon>` 调试器证据 > tool_paths 可用性+平台惯例；多/零候选/证据工具
   不可用 → 报错列出证据，不猜）；**一期范围门：非 jlink → 报错提示配置 jlink**
4. 工具就绪检查：`tool_paths.jlink` 显式 > 从 `tool_paths.jflash` 同目录探测
   JLink.exe；缺失报错并附手动指引（**不自动安装**）
5. 固件定位：`--firmware` > S6 合并固件（state.firmware done）> s7b hex > s7b bin
   （`--format` 强制 3/4 的选择；**release/ 永不作为发现来源**）；格式校验
   （hex 解析失败/大小 0 报错）
6. 地址计算：s7b hex 不传地址（防御性起址校验：`flash_offset>0` 时起址应为
   flash_base+offset，等于裸基址 → 警告"疑似未偏移固件"）；s7b bin =
   flash_base + flash_offset；S6 bin = 合并基址（S6 state 优先）；manual bin 必须
   `--address`。Flash 基址/容量来源链（**复用 S7b makefile_gen，禁止两套规则**）：
   uvprojx IROM > .ld ORIGIN > 平台惯例；越界报错、offset 非 512 对齐警告
7. release/ 发布同步：已定位的全部格式（hex+bin）复制到 `release/`，
   **SHA256 现场计算比对**（一致复用、不一致覆盖——重编译后旧副本自动刷新）
8. 生成 `release/flash_cmd.jlink`（自包含：loadfile → verify → r → g → qc；
   `--chip-erase` 加 erase 行、`--no-verify` 去 verify、`--no-reset` 去 r+g）
9. 写 `outputs/s9/generation_brief.md` 任务书（烧录信息清单）→ `state.s9 = running`

**阶段 B [rule] `flash.py`**（退出码 0 / 1 / 2；GUI 机制为 agent + `--collect`，五期）

1. 默认严格消费 prepare 计划（state.s9 + release/flash_cmd.jlink）；传入任一计划
   参数则重算计划并重新生成脚本（幂等）
2. 执行 J-Link Commander：`JLink.exe -device <名> -if SWD -speed 4000 -autoconnect 1
   -CommandFile flash_cmd.jlink`（cwd=release/，脚本内固件相对引用——**烧的即发布的**）
3. 日志多编码解码（UTF-8→GBK→replace）落 `outputs/s9/flash.log`；成功判定 =
   退出码 0 + Downloading + Programming/Writing 特征 + 无失败特征 + verify 开启时
   校验通过（**verify 失败不算成功**）；`--timeout` 缺省 300s（超时按失败），
   `--retry` 缺省 0
4. 落盘 `outputs/s9/flash_result.json` + `release/flash_info.json`（发布清单，
   成败均写）；state 收口：成功 `done`，失败 `running` + error（进入阶段 C）

**阶段 C [agent] analyze**（仅 flash.py 退出码 1 时）

1. 读 flash.log / flash_result.json（key_lines）+ generation_brief.md
2. 按 `references/flash_log_parse_rules.md` 特征行四类根因定位：
   **连接**（探针未插/驱动）/ **芯片**（供电、SWD 引脚、读保护锁定）/ **固件**
   （越界、起址不符、verify 不匹配）/ **工具**（设备名错、版本过旧）
3. 产出 `outputs/s9/error_analysis.md`（结论 + **用户手动**处置建议；不自动修复）
4. 运行 validate.py 收口

**阶段 D [rule] `validate.py`**（退出码 0 / 2）

1. flash_result.json 存在且契约合法；release/ 发布文件齐备（固件副本 +
   flash_info.json + flash_cmd.jlink[jlink]），副本 SHA256 与烧录记录一致
2. 成功：verify_passed 非 false（verify 开启必须 true）、firmware_sha256 存在
   → `state.s9 = done`；失败：error_analysis.md 必须存在 → `state.s9 = error`

## 输入

- **state.json**（就绪检查）：`s7b.status = done` 且 hex/bin ≥1 非空；S6 firmware
  字段可选（done 时优先消费）
- **项目级 config.json**：`project.flash_tool`（**新增**：jlink/jflash/stlink/
  openocd/pyocd/vendor_ide/null，缺省 null 推断）、`project.flash_config`（**新增**：
  .jflash 路径，二期）、`project.flash_offset`（地址唯一权威）、`project.arch_family`、
  `project.vendor_ide`、`project.inputs.ide_project`、`platform`
- **全局 config.json `tool_paths`**：`jlink`（JLink.exe；未配置时从 `jflash` 同目录
  探测）、`jflash`、`stlink_cli`（STM32_Programmer_CLI.exe）、`openocd`、`pyocd`

## 输出

- **state.json `s9`**：status/flash_tool/flash_mode/firmware_{path,format,source,size,
  sha256}/device/interface/target_address/verify{,_passed}/reset{,_done}/chip_erase/
  duration_sec/flash_log/flash_result/release_dir/release_manifest/error_analysis/error
- **outputs/s9/**：generation_brief.md（任务书）、flash.log、flash_result.json、
  error_analysis.md（仅失败）
- **release/**（项目根，S9 唯一写者）：固件副本（hex+bin）、flash_cmd.jlink
  （自包含复烧脚本）、flash_info.json（发布清单：指纹/地址/设备/verify/复烧命令）

## 使用方法

```bash
# 标准 CLI 机制（本机 J-Link 探针；uvoptx 为 ST-Link 证据但实际用 J-Link 时需显式配置）
# 项目 config.json 显式配置："project": { "flash_tool": "jlink", ... }
python skills/flash/scripts/prepare.py --config examples/stm32f103zet6/config.json
python skills/flash/scripts/flash.py    --config examples/stm32f103zet6/config.json
python skills/flash/scripts/validate.py --config examples/stm32f103zet6/config.json

# 固件格式/地址强制（重算计划并重新生成脚本）
python skills/flash/scripts/prepare.py --config examples/stm32f103zet6/config.json --format bin
python skills/flash/scripts/flash.py    --config examples/stm32f103zet6/config.json --firmware App/outputs/s6/merged.bin --address 0x08000000

# 常用选项：--device <名>（映射失败兜底） --interface JTAG --no-verify --no-reset
#           --chip-erase（破坏性） --retry 3 --timeout 600
```

烧录失败（flash.py 退出码 1）→ Agent 按阶段 C 产出 error_analysis.md → validate.py。

## 智能推断（flash_tool = null，仅 Cortex-M）

| 优先级 | 证据 | 说明 |
|---|---|---|
| 1 | IDE 工程调试器配置 | Keil uvoptx `<pMon>`：ST-LINKIII-KEIL_SWO.dll→stlink、JL2CM3.dll→jlink、CMSIS_AGDI.dll→openocd；未识别 DLL → 报错列出（不猜）；**证据工具 CLI 不可用 → 报错**（提示：实际探针与 IDE 配置不符时显式配置，如本机示例 uvoptx 为 STLink 证据但实际用 J-Link → 配置 flash_tool="jlink"） |
| 2 | tool_paths 可用性 + 平台惯例 | 已配置且存在的 CLI 按惯例选：STM32 → stlink > jlink > openocd > pyocd；其余 → jlink > openocd > pyocd；零候选报错 |

> 探针 ≠ 工具：枚举的是软件 CLI；探针差异由工具内部 interface 配置消化
> （GD-Link/DAPLink 等 CMSIS-DAP → openocd/pyocd，无需逐探针适配）。

## 依赖与演进路径

- **上游**：S7b（hex/bin 产物，必须 done）；可选 S6（合并固件，优先消费）。
  与 S7a 仅通过 `tool_paths` 解耦——**不读 s7a.status、不自动触发 S7a、不自动安装**。
- **下游**：S10 serial-monitor 由用户手动启动（S9 不自动触发）。
- **演进路径**：1) 一期 jlink CLI 全链路（本文件）→ 2) jflash + `.jflash`
  决策流程（--jflash-project/--gen-jflash/退出码 3）→ 3) stlink/openocd →
  4) pyocd → 5) vendor_ide GUI 机制（8 位 MCU，--collect 收口）。
  演进期工具在本版 prepare 直接报错并提示配置 jlink。

## 禁止事项

- 烧录工具**不自动下载安装**（探针偏好/版本兼容/设备数据库支持因人而异）
- 失败**不自动重试**（--retry 缺省 0）、**不自动解锁**芯片（读写保护属用户决策）
- **不修改** config.json / 工程文件 / 固件源文件；release/ 之外不发布任何副本
- release/ **永不作为固件发现来源**（防烧旧固件；发现只走 state 指针）
- Flash 基址/容量**必须复用 S7b 来源链**（import makefile_gen，禁止两套规则）
- 无符号量不得写下界比较（工程约定：范围校验只写上界）
