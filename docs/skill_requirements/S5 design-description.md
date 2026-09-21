# S5设计说明.md

# EmbedAIAssist S5 设计说明

> **文档定位（历史设计输入）**：本文档是 S5a / S5b / S5c 的早期设计说明，
> 保留作背景参考。**实现以三个 Skill 的 SKILL.md 为权威**（三段式执行模型、
> 三配置项 config 显式值、skip-if-modified 再生策略等均为后续演进决策），
> 两者冲突时以 SKILL.md 为准。

## 1. 文档目的

本文档是 S5a / S5b / S5c 三个 Skill 的顶层设计说明，用于指导 TRAE Agent 理解并实现这三个 Skill。文档涵盖整体架构、输入材料、Skill 职责划分、目录结构、配置设计、执行流程、低功耗策略、RTOS 处理、文件拆分规范、数据契约、换平台与换 RTOS 流程、验收标准等核心内容。

S5a / S5b / S5c 是整个 EmbedAIAssist 工作流的核心，负责从硬件事实和功能需求生成可直接编译烧录的嵌入式代码。

## 2. 整体架构

S5 采用 Ports & Adapters 模式，将平台无关的应用逻辑与平台相关的硬件实现分离：

```text
USER 层（平台无关）
  APP → Protocol Layer → Device Driver / BSP → Port 接口
VENDOR 层（平台相关）
  Port 实现 → HAL / 厂商 SDK / RTOS
```

三个 Skill 的职责如下：

| Skill | 名称 | 核心职责 | 是否平台相关 | 依赖 |
|---|---|---|---|---|
| S5a | hardware-initializer | 硬件初始化与硬件能力提取 | 是 | 不依赖 S5b |
| S5b | port-contract-and-app | 定义 Port 契约，生成 APP 与 Driver | 否 | 不依赖 S5a |
| S5c | port-implementer | 实现 Port 接口，适配具体 HAL / RTOS | 是 | 依赖 S5a、S5b |

## 3. 项目目录结构

### 3.1 项目根目录约定

每个项目位于 `examples/<project>/`（演示工程）或 `projects/<project>/`（实际项目），目录结构约定如下：

```text
examples/<project>/
├── config.json                # 项目级配置（含 project.build_target）
├── docs/                      # 输入文档（项目根共享）
│   ├── functional_spec.*      # 功能规格书（S2 读取）
│   ├── software_spec.*        # 软件规格书（S5b 读取）
│   └── ...
├── references/                # 参考材料（项目根共享）
│   ├── demos/                 # demo 程序（供 Agent 学习）
│   ├── sdk/                   # SDK 源码与头文件
│   └── existing_project/      # 已有项目（供 Agent 参考）
├── outputs/                   # 跨工程产物（合并固件等）
├── App/                       # 目标工程（build_target = "App"，缺省）
│   ├── state.json             # 运行时状态总线（每目标独立）
│   ├── MDK-ARM/               # IDE 工程目录（32 位 Keil；IAR 为 IAR/，8 位为 Project/，
│   │   └── project.uvprojx    #   完整布局见 docs/PROJECT_LAYOUT.md，骨架由 S5 自动创建）
│   ├── Core/                  # 内核相关（CubeMX 生成 / 用户手动放）
│   ├── Drivers/
│   │   ├── CMSIS/             # ARM 内核支持包（用户手动放）
│   │   ├── HAL_Driver/        # 厂商 HAL 库（用户手动放）
│   │   ├── BSP/               # S5a 初始化 + S5b 器件驱动
│   │   │   ├── Src/           # .c
│   │   │   └── Inc/           # .h
│   │   └── Port/              # Ports & Adapters 核心层
│   │       ├── Inc/           # S5b：Port 接口（平台无关）
│   │       └── Src/           # S5c：Port 实现（平台相关）
│   ├── App/                   # S5b 输出：应用逻辑 + 协议层
│   │   ├── Src/
│   │   └── Inc/
│   └── outputs/               # 数据产物（JSON / Excel）
│       ├── circuit_netlist.json
│       ├── chip_info/
│       ├── s5a/
│       ├── s5b/
│       └── s5c/
└── BootLoader/                # 目标工程（build_target = "BootLoader"，结构同 App）
```

> `project.build_target` 决定 S1–S5 各 Skill 的目标工程根（缺省 `App`）：
> `state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`；
> `docs/` / `references/` / 原理图等项目根共享资源不随目标切换。
> 目录布局的唯一事实来源是 `docs/PROJECT_LAYOUT.md`（项目级可覆盖），
> S5a/S5b/S5c 执行时先按其解析并幂等创建目录骨架，产物路径不硬编码在脚本里。

### 3.2 代码输出目录约定

**所有生成的代码必须放在 `docs/PROJECT_LAYOUT.md` 约定的源码目录下
（如 `Drivers/BSP/`、`Drivers/Port/`、`App/`），不得放在 `outputs/` 中。**

- 源码目录用于编译、烧录；具体位置由 PROJECT_LAYOUT.md 解析（layout_resolver），
  32 位 Cortex-M 与 8 位 MCU 两套骨架、flat/layered/full 三种架构自动适配。
- `outputs/` 只放数据产物（JSON、Excel、报告）。
- `state.json` 中只存代码文件的相对路径，不存代码本体。

### 3.3 目标工程内部结构

```text
<目标工程>/                        # App/ 或 BootLoader/，布局由 docs/PROJECT_LAYOUT.md 定义
├── Core/                          # 内核相关（用户/CubeMX，S 不生成）
│   ├── Src/main.c                 # 主入口（main 函数）
│   └── ...
├── Drivers/
│   ├── CMSIS/                     # ARM 内核支持包（用户手动放）
│   ├── HAL_Driver/                # 厂商 HAL 库（用户手动放）
│   ├── BSP/                       # 板级支持包
│   │   ├── Src/                   # S5a 初始化 .c + S5b 器件驱动 .c
│   │   │   ├── hal_init.c         # 或 board_init.c（flat 架构）
│   │   │   ├── clock_init.c、gpio_init.c、nvic_init.c、uart_init.c ...
│   │   │   └── driver_<设备>.c    # S5b：设备驱动
│   │   └── Inc/                   # 对应 .h
│   └── Port/                      # Ports & Adapters 核心层
│       ├── Inc/                   # S5b：Port 接口（uart_port.h、gpio_port.h、
│       │                          #   osal_port.h、power_port.h ...）
│       └── Src/                   # S5c：Port 实现
│           ├── port_impl_uart_<平台>.c、port_impl_i2c_<平台>.c
│           ├── port_impl_gpio_<平台>.c、port_impl_osal_<rtos>.c
│           └── port_impl_power_<平台>.c
├── App/                           # S5b 输出：应用逻辑 + 协议层
│   ├── Src/
│   │   ├── app.c                  # 主入口，只做汇总
│   │   ├── app_<功能>.c           # 功能模块
│   │   ├── app_<功能>_task.c      # 任务化模块（RTOS）
│   │   └── protocol_<名称>.c      # 协议层
│   └── Inc/
├── MDK-ARM/                       # IDE 工程目录（用户创建；IAR/、Project/ 同义）
└── outputs/                       # 数据产物
```

> 8 位 MCU 无 `Core/`、`CMSIS/`、`HAL_Driver/`，IDE 目录为 `Project/`；
> `flat` 架构无 `Drivers/Port/`（S5c 跳过）。详见 `docs/PROJECT_LAYOUT.md`。

`flat` 架构下，不生成 `Drivers/Port/`；`App/Src/` 内直接访问寄存器或厂商库。

## 4. 输入材料

### 4.1 S2 输入（功能规格书）

- S2 读取 `docs/functional_spec.*`，输出 `outputs/s2/spec.json`。
- S5b 从 `state.json` 的 `spec.*` 字段读取。

### 4.2 S5b 额外输入

除了 S2 功能规格书，S5b 还需要以下输入材料：

| 输入 | 位置 | 用途 |
|---|---|---|
| 软件规格书 | `docs/software_spec.*` | 软件开发相关内容要求：任务划分、时序约束、通信协议、状态机、错误处理、日志、配置项 |
| demo 程序 | `references/demos/` | 官方或参考 demo，供 Agent 学习代码风格、初始化写法、外设使用方式 |
| SDK | `references/sdk/` | 厂商 SDK 源码与头文件，供 Agent 学习 API 命名、数据结构、调用约定 |
| 已有项目 | `references/existing_project/` | 已有项目代码，供 Agent 参考工程结构、代码风格、模块划分 |
| IDE 项目文件 | `MDK-ARM/` / `IAR/` / `Project/` | Keil / IAR 等 IDE 的初始工程文件（32 位 Keil 为 `MDK-ARM/`、IAR 为 `IAR/`、8 位为 `Project/`，见 `docs/PROJECT_LAYOUT.md`），后续生成的代码由公共工具 ide_sync.py 自动添加到工程文件中 |

### 4.3 配置项

在项目级 `config.json` 中增加输入路径配置：

| 配置路径 | 类型 | 说明 | 必填 | 默认值 |
|---|---|---|---|---|
| `project.inputs.functional_spec` | string | 功能规格书路径 | 否 | `docs/functional_spec.*` |
| `project.inputs.software_spec` | string | 软件规格书路径 | 否 | `docs/software_spec.*` |
| `project.inputs.demos` | array | demo 程序目录列表 | 否 | `references/demos/` |
| `project.inputs.sdk` | string | SDK 目录 | 否 | `references/sdk/` |
| `project.inputs.existing_project` | string | 已有项目目录 | 否 | `references/existing_project/` |
| `project.inputs.ide_project` | string | IDE 项目文件路径 | 否 | 按 IDE 工程目录（`MDK-ARM/`/`IAR/`/`Project/`）自动发现 |

未配置时，Agent 按默认路径自动发现。

## 5. 配置设计

### 5.1 配置分层

- 全局 `config.json` 保持现有结构：`tool_paths`、`platforms_root`、`skills_root`。
- 项目级配置位于 `Examples/<project>/config.json`，与全局 `config.json` 合并后使用。
- 合并优先级：项目级 > 全局默认。

### 5.2 新增配置项

在已有配置基础上，**仅新增以下项目级配置项**：

| 配置路径 | 类型 | 取值 | 默认值 | 说明 |
|---|---|---|---|---|
| `project.build_target` | string | `"App"` / `"BootLoader"` | `"App"` | 目标工程：`state.json` / 源码目录 / `outputs/` / IDE 工程目录位于 `<项目根>/<build_target>/` |
| `project.architecture` | string | `"flat"` / `"layered"` / `"full"` | Agent 自动推断 | 控制分层程度 |
| `project.power.enabled` | bool | `true` / `false` | `false` | 是否启用低功耗设计 |

其余细节（如低功耗模式、唤醒源、Tickless、RTOS 选型等）由 Agent 根据 MCU 资料自主决策，**不暴露给用户配置**。

### 5.3 已有配置项

以下配置项沿用之前的设计，不新增：

| 配置路径 | 类型 | 说明 |
|---|---|---|
| `project.target` | string | MCU 型号 |
| `project.rtos` | string | 可选，`"none"` / `"FreeRTOS"` 等，未配置时由 Agent 从 S2 推断 |
| `project.rtos_config.*` | object | 可选，RTOS 参数 |
| `project.inputs.*` | object | 输入材料路径 |
| `s5a.hal_framework` | string | 可选，HAL 框架 |
| `s5b.language` | string | 可选，默认 `c99` |
| `s5b.port_split` | array | 可选，Port 拆分 |
| `s5c.platform` | string | 可选 |

## 6. 文件拆分原则

### 6.1 总原则

**所有代码按功能模块拆分成多个文件，禁止把所有内容塞进一个文件。**

拆分维度：
- 按外设类型拆分（uart / i2c / spi / gpio / adc / timer / pwm / dma / nvic）
- 按业务功能拆分（app_led / app_wifi / app_sensor）
- 按协议拆分（protocol_xxx）
- 按设备拆分（driver_xxx）

每个模块一个 `.c` 文件和一个 `.h` 文件，命名保持一致。

### 6.2 命名规范

| 层级 | 命名格式 | 示例 |
|---|---|---|
| S5a 初始化模块 | `<模块>_init.c/h` | `clock_init.c/h`、`uart_init.c/h` |
| S5a 总入口 | `hal_init.c/h` 或 `board_init.c/h` | 只做汇总调用，不含具体实现 |
| S5b Port 接口 | `<外设>_port.h` | `uart_port.h`、`i2c_port.h` |
| S5b OSAL 接口 | `osal_port.h` | 单一文件 |
| S5b Power 接口 | `power_port.h` | 单一文件 |
| S5b APP 主入口 | `app.c/h` | 只做初始化和主循环/任务创建 |
| S5b APP 模块 | `app_<功能>.c/h` | `app_led.c/h`、`app_wifi.c/h` |
| S5b 协议层 | `protocol_<名称>.c/h` | `protocol_at.c/h`、`protocol_modbus.c/h` |
| S5b 设备驱动 | `driver_<设备>.c/h` | `driver_esp32c2.c/h`、`driver_eeprom.c/h` |
| S5b 任务化 APP | `app_<功能>_task.c/h` | `app_wifi_task.c/h` |
| S5c Port 实现 | `port_impl_<外设>_<平台>.c` | `port_impl_uart_gd32.c` |
| S5c OSAL 实现 | `port_impl_osal_<rtos>.c` | `port_impl_osal_freertos.c` |
| S5c Power 实现 | `port_impl_power_<平台>.c` | `port_impl_power_gd32.c` |

### 6.3 总入口文件的职责

`hal_init.c/h`、`board_init.c/h`、`app.c/h` 只做汇总，不写具体实现：

```c
/* hal_init.c 只做汇总调用 */
void hal_init(void)
{
    clock_init();
    gpio_init();
    nvic_init();
    uart_init();
    i2c_init();
}
```

### 6.4 何时拆、何时合并

- 一个外设对应一个模块，必须拆。
- 业务功能独立，必须拆。
- 协议有多个，按协议拆。
- 设备有多个，按设备拆。
- 简单项目（`flat` 架构）可以合并部分小模块，但外设初始化仍建议分文件。
- 总入口文件必须保留，方便上层调用。

## 7. IDE 工程同步（公共工具 ide_sync.py）

### 7.1 目的

生成的代码需要被添加到 IDE 项目文件（Keil `.uvprojx`、IAR `.ewp` 等）中，才能参与编译。

### 7.2 同步职责（方案 A：公共工具 + 全局锁）

IDE 工程同步由独立公共工具 `skills/_shared/scripts/ide_sync.py` 完成，
**S5a/S5b/S5c 各自 validate 段结束后自动调用**（谁跑完谁同步，不再由 S5c 统一汇聚）：

```bash
# 各 Skill validate 自动调用；也可单独手动运行
python skills/_shared/scripts/ide_sync.py --project examples/<项目> --target App --ide keil
```

| Skill | 同步时机 |
|---|---|
| S5a | validate 段（`Drivers/BSP/Src/` 源文件 + include 路径入工程） |
| S5b | validate 段（`App/Src/`、`Drivers/BSP/Src/` 等源文件入工程） |
| S5c | validate 段（`Drivers/Port/Src/` 源文件入工程） |

- **并发安全**：全局文件锁（`<工程文件>.lock`），S5a/S5b 并行完成时互不覆盖
- **幂等**：重复调用不产生重复条目；无变化不写盘（不改 mtime）
- **备份/回滚**：修改前备份 `<工程文件>.bak`，写盘失败自动恢复原文件
- **失败不中断**：任何失败不影响 Skill 产物，输出 `outputs/_shared/ide_sync_manual.md` 手动清单

### 7.3 同步方式

- 扫描布局解析出的各 Skill 源码目录（`layout_plan.scan_roots`，如 `Drivers/BSP/Src`、`Drivers/Port/Src`、`App/Src`）全部源文件，与工程条目差异比对：新增的添加、已删除的移除；各扫描根下的 `mocks/` 排除（单元测试 Mock 桩不参与固件编译）。
- 解析项目文件结构（Keil `.uvprojx` / IAR `.ewp` 为 XML）。
- 按扫描根去末段分 group（如 `Drivers/BSP/Src` → `Drivers/BSP`），优先复用同名 group。
- 保留原有工程配置（编译器选项、宏定义、include 路径等）。
- include 路径缺失时追加（`layout_plan.include_dirs`，保留原值）。
- IDE 工程在 IDE 工程目录（`MDK-ARM/`/`IAR/`/`Project/`）中自动发现，由用户手动创建（选芯片/编译器等配置人工确认更可靠），工具只做增量同步；工程文件不存在时不写入，输出手动清单。

### 7.4 IDE 适配

| IDE | 项目文件 | 解析方式 |
|---|---|---|
| Keil MDK | `.uvprojx` | XML 解析 |
| IAR EWARM | `.ewp` | XML 解析 |
| STM32CubeIDE | `.project` / `.cproject` | XML 解析 |
| 其他 | — | 由 Agent 根据项目文件格式自主处理 |

如果项目文件格式无法解析，工具不修改原文件，输出 `outputs/_shared/ide_sync_manual.md` 手动清单（源文件列表 + group 建议 + include 路径 + 操作指引）。

## 8. 三种架构的执行流程与策略

### 8.1 架构定义

| 架构 | 适用场景 | 分层程度 |
|---|---|---|
| `flat` | 8 位 MCU（辉芒微、和泰等）、资源极少、项目简单 | 无 Port 层，APP 与 HAL 混合 |
| `layered` | 32 位 MCU、资源有限、需求中等 | Port 层存在，不强制拆分 Protocol 层 |
| `full` | 32 位 MCU、多外设、多平台、复杂项目 | 完整 Ports & Adapters 分层 |

### 8.2 各架构执行流程

```text
architecture == "flat":
  S2 → S5b → S5a → 编译/烧录/测试
  （S5c 跳过；S5a/S5b 各自 validate 后由公共工具 ide_sync.py 自动同步 IDE 工程）

architecture == "layered":
  S2 → S5b
  S3 + S4 → S5a
  S5a + S5b → S5c → 编译/烧录/测试
  （S5a/S5b/S5c 各自 validate 后由公共工具 ide_sync.py 自动同步 IDE 工程）

architecture == "full": 同 layered
```

### 8.3 各架构下 Skill 行为差异

| Skill | `flat` | `layered` | `full` |
|---|---|---|---|
| S5a | 生成 `Drivers/BSP/` 下 `board_init.c/h` + 各外设 `*_init.c/h` | 生成 `Drivers/BSP/` 下 `hal_init.c/h` + 各外设 `*_init.c/h` + capabilities | 同 `layered`，外加 `rtos_hw_init.c/h`、`power_init.c/h` |
| S5b | 生成 `App/Src/` 下的 APP，混合结构，无 Port 层 | 生成 `Drivers/Port/Inc/<外设>_port.h` + `App/Src/` + `Drivers/BSP/` 器件驱动 | 同 `layered`，外加 `Drivers/Port/Inc/osal_port.h`、`power_port.h` |
| S5c | **跳过**，状态置 `skipped` | 生成 `Drivers/Port/Src/port_impl_<外设>_<平台>.c` | 同 `layered`，外加 `port_impl_osal_<rtos>.c`、`port_impl_power_<平台>.c` |

### 8.4 架构推断规则（当用户未配置 `project.architecture` 时）

- 8 位 MCU 或 Flash < 16KB → `flat`
- 32 位 MCU 且需求简单 → `layered`
- 32 位 MCU 且多外设、多平台 → `full`

## 9. 低功耗执行策略

### 9.1 总原则

- 用户仅声明 `project.power.enabled = true`，具体策略由 Agent 自主决策。
- Agent 决策依据：MCU 头文件、数据手册、用户手册、厂商 demo、联网搜索、S2 功能需求、S3 chip data、S4 circuit facts。
- Agent 自主决定：低功耗模式选择、唤醒源配置、时钟恢复、RTOS tickless 启用等。
- 这些细节**不出现在 config.json 中**。

### 9.2 各架构下低功耗实现方式

| 架构 | `power.enabled = true` 时的行为 |
|---|---|
| `flat` | S5a 在 `Drivers/BSP/` 下 `board_init.c/h` 和 `power_init.c/h` 中生成低功耗初始化；S5b 在 `App/Src/` 中直接内联低功耗进入/退出逻辑；不生成 `power_port.h` |
| `layered` | S5a 生成 `Drivers/BSP/` 下 `power_init.c/h`，capabilities 增加 `power` 段；S5b 生成 `Drivers/Port/Inc/power_port.h`；S5c 生成 `Drivers/Port/Src/port_impl_power_<平台>.c` |
| `full` | 同 `layered`，并且 RTOS 场景下由 S5c 的 `port_impl_osal_<rtos>.c` 对接 tickless idle hook |

## 10. RTOS 处理

### 10.1 RTOS 配置

- `project.rtos` 可放在项目级 `config.json`，也可由 Agent 从 S2 功能需求推断。
- 若存在 `project.rtos_config.*`，则作为 RTOS 硬件初始化的输入。

### 10.2 各 Skill 与 RTOS 的关系

- **S5a**：生成 `Drivers/BSP/Src/rtos_hw_init.c/h`，配置 SysTick、NVIC 优先级分组、PendSV / SVC 等。
- **S5b**：生成 `Drivers/Port/Inc/osal_port.h` 和任务化 APP（`App/Src/app_<功能>_task.c/h`），所有 RTOS 调用通过 `osal_port.h`，不直接 include RTOS 头文件。
- **S5c**：生成 `Drivers/Port/Src/port_impl_osal_<rtos>.c`，将 `osal_*` 翻译为具体 RTOS API。

### 10.3 换 RTOS 影响

- 只重跑 S5a 和 S5c 的 RTOS 相关部分。
- S5b 的 `osal_port.h`、`app.c/h`、`app_<功能>_task.c/h`、`driver_<设备>.c/h` 不变。

## 11. 跨 Skill 数据契约

### 11.1 port_interface_manifest.json（S5b 输出，S5c 输入）

S5b 必须输出机器可读的接口契约，S5c 只认该契约，禁止硬解析 C 头文件。

需要包含的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `version` | string | 契约版本 |
| `rtos` | string | 生成时使用的 RTOS，裸机为 `"none"` |
| `architecture` | string | 生成时使用的架构 |
| `power_enabled` | bool | 是否启用低功耗 |
| `interfaces` | array | 接口列表 |
| `interfaces[].name` | string | 接口名，如 `uart_port`、`osal_port`、`power_port` |
| `interfaces[].header` | string | 头文件名 |
| `interfaces[].functions` | array | 函数列表 |
| `interfaces[].functions[].name` | string | 函数名 |
| `interfaces[].functions[].return` | string | 返回类型 |
| `interfaces[].functions[].args` | array | 参数类型列表 |

### 11.2 hardware_capabilities.json（S5a 输出，S5c 输入）

S5a 必须输出硬件能力清单，S5c 据此实现 Port。

需要包含的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `mcu` | string | MCU 型号 |
| `rtos` | string | 生成时使用的 RTOS，裸机为 `"none"` |
| `architecture` | string | 生成时使用的架构 |
| `power_enabled` | bool | 是否启用低功耗 |
| `clocks` | object | 时钟配置 |
| `peripherals` | array | 外设能力列表 |
| `peripherals[].type` | string | 外设类型，如 `uart`、`i2c`、`gpio` |
| `peripherals[].instance` | string | 实例名，如 `USART0` |
| `peripherals[].pins` | object | 引脚映射 |
| `peripherals[].dma` | object | DMA 映射 |
| `peripherals[].irq` | string | 中断号 |
| `peripherals[].capabilities` | array | 能力标签 |
| `power` | object | 低功耗能力（可选） |
| `constraints` | array | 约束条件 |

### 11.3 数据分离规则

- 大块数据产物放在 `outputs/` 目录。
- 所有生成的代码放在 `src/` 目录。
- `state.json` 只存指针和统计计数，不存数据本体，不存代码本体。
- 所有输出结构必须由对应的 JSON Schema 约束，写入前校验。

## 12. 换平台 / 换 RTOS / 切换架构流程

### 12.1 换 MCU

1. 保留 S5b 的 `Drivers/Port/Inc/*.h`、`App/Src/`、`Drivers/BSP/` 器件驱动不变。
2. 重跑 S5a，生成新平台的 `Drivers/BSP/` 下文件、`hardware_capabilities.json`。
3. 重跑 S5c（`flat` 架构跳过），生成新平台的 `Drivers/Port/Src/port_impl_<外设>_<平台>.c` 等。
4. 重跑的 Skill 在 validate 段由公共工具 `ide_sync.py` 自动同步 IDE 工程。
5. 编译、烧录、测试。
6. 校验 S5b 产物哈希不变。

### 12.2 换 RTOS

1. 保留 S5b 产物不变。
2. 更新项目级 `config.json` 中的 `project.rtos` 和 `rtos_config`。
3. 重跑 S5a，生成新 RTOS 的 `Drivers/BSP/Src/rtos_hw_init.c/h`。
4. 重跑 S5c，生成新 RTOS 的 `Drivers/Port/Src/port_impl_osal_<rtos>.c`。
5. 重跑的 Skill 在 validate 段由公共工具 `ide_sync.py` 自动同步 IDE 工程。
6. 编译、烧录、测试。
7. 校验 S5b 产物哈希不变。

### 12.3 切换架构

1. 修改项目级 `config.json` 中的 `project.architecture`。
2. 重跑 S5a、S5b、S5c（`flat` 时 S5c 跳过）。
3. 重跑的 Skill 在 validate 段由公共工具 `ide_sync.py` 自动同步 IDE 工程。
4. 编译、烧录、测试。
5. 架构切换会改变 S5b 产物，S5b 哈希会变化，这是预期行为。

## 13. 集成验收清单

- [ ] 所有生成的代码位于 `docs/PROJECT_LAYOUT.md` 约定的源码目录下，`outputs/` 中无代码文件。
- [ ] S5a 编译通过。
- [ ] S5a 生成的初始化代码按模块拆分，不是单文件。
- [ ] S5a 在 `project.rtos != "none"` 时生成 `Drivers/BSP/Src/rtos_hw_init.c/h` 并编译通过。
- [ ] S5a 在 `project.power.enabled == true` 且 `architecture != "flat"` 时生成 `Drivers/BSP/Src/power_init.c/h` 并编译通过。
- [ ] S5b Mock Port / Mock OSAL 编译通过。
- [ ] S5b 生成的 APP / 协议 / 设备驱动按模块拆分，不是单文件。
- [ ] S5b 读取了软件规格书、demo、SDK、已有项目、IDE 项目文件。
- [ ] S5c 链接完整工程编译通过。
- [ ] S5c 生成的 Port 实现按外设拆分，不是单文件。
- [ ] S5c 在 `project.rtos != "none"` 时生成 `Drivers/Port/Src/port_impl_osal_<rtos>.c` 并编译通过。
- [ ] S5c 在 `project.power.enabled == true` 且 `architecture != "flat"` 时生成 `Drivers/Port/Src/port_impl_power_<平台>.c` 并编译通过。
- [ ] `architecture == "flat"` 时，S5c 正确跳过，产物中无 Port 层。
- [ ] IDE 工程已同步所有生成的源文件（公共工具 `ide_sync.py`），可直接编译。
- [ ] `power.enabled == false` 时，无低功耗相关文件。
- [ ] `power.enabled == true` 时，Agent 自动选择低功耗策略，无需用户配置唤醒源、Tickless 等。
- [ ] 烧录通过。
- [ ] S2 验收用例通过。
- [ ] 换 MCU 只重跑 S5a + S5c，S5b 产物不变。
- [ ] 换 RTOS 只重跑 S5a + S5c（或仅 S5c 的 OSAL 实现），S5b 产物不变。
- [ ] APP / Driver / 协议层源文件 grep 不到 HAL 头。
- [ ] APP / Driver / 协议层源文件 grep 不到 RTOS API。
- [ ] 所有 Skill 只读写自己的 `state.json` 字段。

---