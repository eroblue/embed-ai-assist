# S5a requirement.md

# S5a hardware-initializer Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：hardware-initializer
- **Skill 用途**：从 S4 输出的硬件事实报告和 S3 输出的芯片数据出发，完成平台相关的硬件底层初始化，包括裸机或 RTOS 硬件初始化、低功耗初始化，并输出硬件能力清单，为 S5c 提供 HAL 支撑。
- **触发时机**：在 S4 和 S3 都执行完成后，S5b 可以并行执行；S5c 需要等待 S5a 和 S5b 都完成后执行。

## 输入

从 `state.json` 读取：

- `circuit.facts.facts_path`：S4 输出的硬件事实报告路径
- `chip.pins_path`：S3 输出的引脚定义 JSON 路径
- `chip.registers_path`：S3 输出的寄存器映射 JSON 路径
- `chip.clock_tree_path`：S3 输出的时钟树 JSON 路径
- `chip.peripherals_path`：S3 输出的外设清单 JSON 路径

从项目级 `config.json`（与全局 `config.json` 合并后）读取：

- `project.target`：MCU 型号
- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.architecture`：`"flat"` / `"layered"` / `"full"`，未配置时由 Agent 推断
- `project.power.enabled`：是否启用低功耗
- `project.rtos`：RTOS 类型（可选，未配置时由 Agent 从 S2 推断）
- `project.rtos_config.*`：RTOS 参数（可选）
- `project.inputs.ide_project`：IDE 项目文件路径（可选，未配置时自动发现）
- `s5a.hal_framework`：HAL 框架（可选）
- `s5a.generate_hal_init`：是否生成 HAL 初始化（可选，默认 true）

可选参考材料（用于初始化代码风格学习）：

- `references/demos/`：demo 程序
- `references/sdk/`：SDK 源码
- `references/existing_project/`：已有项目

## 输出

### 文件拆分原则

S5a 生成的初始化代码**必须按功能模块拆分成多个文件**，**统一输出到 S5a 产物目录**
（由 `docs/PROJECT_LAYOUT.md` 解析确定，32 位 Cortex-M 与 8 位 MCU 均为
`Drivers/BSP/Src/` 下 .c、`Drivers/BSP/Inc/` 下 .h；目录骨架由 prepare 段创建）：

- 每个外设一个初始化模块：`uart_init.c/h`、`i2c_init.c/h`、`spi_init.c/h`、`adc_init.c/h`、`timer_init.c/h`、`pwm_init.c/h` 等。
- 基础模块独立：`clock_init.c/h`、`gpio_init.c/h`、`nvic_init.c/h`、`dma_init.c/h`。
- RTOS 硬件初始化：`rtos_hw_init.c/h`。
- 低功耗初始化：`power_init.c/h`。
- 总入口：`hal_init.c/h` 或 `board_init.c/h`，只做汇总调用，不含具体实现。
- 未被使用的模块不生成。

### 写入 state.json（仅 s5a 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5a.status` | string | `pending` / `running` / `done` / `error` / `skipped` |
| `s5a.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5a.architecture` | string | 本次使用的架构 |
| `s5a.power_enabled` | bool | 是否启用低功耗 |
| `s5a.init_sources` | array | S5a 产物源文件相对路径列表（如 `Drivers/BSP/Src/clock_init.c`） |
| `s5a.init_headers` | array | S5a 产物头文件相对路径列表（如 `Drivers/BSP/Inc/clock_init.h`） |
| `s5a.entry_source` | string | 总入口源文件相对路径，如 `Drivers/BSP/Src/hal_init.c` 或 `Drivers/BSP/Src/board_init.c` |
| `s5a.entry_header` | string | 总入口头文件相对路径 |
| `s5a.rtos_hw_init` | string | `Drivers/BSP/Src/rtos_hw_init.c` 相对路径，裸机时为 null |
| `s5a.power_init` | string | `Drivers/BSP/Src/power_init.c` 相对路径，未启用低功耗时为 null |
| `s5a.hardware_capabilities` | string | `outputs/s5a/hardware_capabilities.json` 相对路径 |
| `s5a.ide_pending_files` | string | `outputs/s5a/ide_pending_files.json` 路径（兜底参考；IDE 同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成） |
| `s5a.error` | string/null | 错误信息 |
| `s5a.updated_at` | string | ISO 时间戳 |

### 写入 S5a 产物目录（.c → `Drivers/BSP/Src/`，.h → `Drivers/BSP/Inc/`）

| 产物 | 内容说明 |
|---|---|
| `clock_init.c/h` | 时钟初始化 |
| `gpio_init.c/h` | GPIO 初始化 |
| `nvic_init.c/h` | 中断优先级初始化 |
| `dma_init.c/h` | DMA 初始化（如有使用） |
| `uart_init.c/h` | UART 初始化（如有使用） |
| `i2c_init.c/h` | I2C 初始化（如有使用） |
| `spi_init.c/h` | SPI 初始化（如有使用） |
| `adc_init.c/h` | ADC 初始化（如有使用） |
| `timer_init.c/h` | Timer 初始化（如有使用） |
| `pwm_init.c/h` | PWM 初始化（如有使用） |
| `rtos_hw_init.c/h` | RTOS 硬件初始化（如启用 RTOS） |
| `power_init.c/h` | 低功耗初始化（如启用低功耗） |
| `hal_init.c/h` | 总入口，汇总调用各模块（`layered` / `full`） |
| `board_init.c/h` | `flat` 架构下替代 `hal_init.c/h` |

### 写入 outputs/s5a/

| 产物 | 内容说明 |
|---|---|
| `outputs/s5a/hardware_capabilities.json` | 硬件能力清单，结构由 `schemas/hardware_capabilities.schema.json` 约束 |
| `outputs/s5a/capability_gap.json` | 可选，当需求与硬件能力冲突时输出 |

### 总入口文件示例

```c
/* Drivers/BSP/Src/hal_init.c 只做汇总调用，不含具体实现 */
#include "hal_init.h"
#include "clock_init.h"
#include "gpio_init.h"
#include "nvic_init.h"
#include "uart_init.h"
#include "i2c_init.h"

void hal_init(void)
{
    clock_init();
    gpio_init();
    nvic_init();
    uart_init();
    i2c_init();
}
```

### 指针/数据分离规则

- 代码放 S5a 产物目录（`Drivers/BSP/{Src,Inc}`），数据产物放 `outputs/s5a/`。
- `state.json` 中只存指针与统计计数，不存数据本体，不存代码本体。

## Skill 目录结构（标准结构）

```text
hardware-initializer/
├── SKILL.md
├── schemas/
│   ├── input.schema.json
│   ├── output.schema.json
│   └── hardware_capabilities.schema.json
├── scripts/
│   ├── initialize.py                # 主入口
│   ├── clock_init_generator.py      # 时钟初始化代码生成
│   ├── gpio_init_generator.py       # GPIO 初始化代码生成
│   ├── nvic_init_generator.py       # NVIC 初始化代码生成
│   ├── dma_init_generator.py        # DMA 初始化代码生成
│   ├── peripheral_init_generator.py # 外设初始化代码生成（uart/i2c/spi/adc/timer/pwm）
│   ├── rtos_hw_init_generator.py    # RTOS 硬件初始化生成
│   ├── power_init_generator.py      # 低功耗初始化生成
│   ├── entry_generator.py           # 总入口文件生成
│   ├── capability_extractor.py      # 硬件能力清单提取
│   └── ide_pending_exporter.py     # IDE 待添加清单导出（实际同步由公共工具 skills/_shared/scripts/ide_sync.py 完成）
├── references/
│   ├── init_code_templates.md       # 初始化代码模板
│   ├── file_split_guide.md          # 文件拆分规范
│   ├── ide_project_formats.md       # IDE 项目文件格式说明
│   └── low_power_strategies.md      # 低功耗策略参考
└── assets/
    └── hardware_capabilities_example.json
```

## 执行步骤

1. 从 `state.json` 读取 `circuit.*` 和 `chip.*` 字段，确认 S4 和 S3 均已成功执行。
2. 读取项目级 `config.json`，与全局 `config.json` 合并。
3. 读取参考材料（可选）：`references/demos/`、`references/sdk/`、`references/existing_project/`，学习代码风格和初始化写法。
4. 根据 `project.architecture`（未配置时自动推断）决定生成混合初始化还是分层初始化：
   - `flat`：生成 `Drivers/BSP/{Src,Inc}/board_init.c/h` 作为总入口。
   - 非 `flat`：生成 `Drivers/BSP/{Src,Inc}/hal_init.c/h` 作为总入口。
5. 分析 S4 facts 和 S3 chip data，确定实际使用的外设列表。
6. 按外设列表逐个生成初始化模块文件到 S5a 产物目录（`Drivers/BSP/{Src,Inc}`）：
   - 基础模块：`clock_init.c/h`、`gpio_init.c/h`、`nvic_init.c/h`、`dma_init.c/h`（如使用）。
   - 外设模块：`uart_init.c/h`、`i2c_init.c/h`、`spi_init.c/h`、`adc_init.c/h`、`timer_init.c/h`、`pwm_init.c/h`（按需）。
7. 根据 `project.rtos` 判断是否生成 RTOS 硬件初始化：
   - `none`：不生成。
   - 非 `none`：生成 `Drivers/BSP/{Src,Inc}/rtos_hw_init.c/h`。
8. 若 `project.power.enabled == true`：
   - 根据 MCU 资料和参考材料自主决定低功耗初始化策略。
   - `architecture != "flat"` 时生成 `Drivers/BSP/{Src,Inc}/power_init.c/h`。
   - `architecture == "flat"` 时可合入 `board_init.c/h`。
9. 生成总入口文件，汇总调用各模块。
10. 输出 `outputs/s5a/hardware_capabilities.json`，描述可用外设实例、引脚、DMA、中断和能力。
11. 若 `project.power.enabled == true`，在 `hardware_capabilities.json` 中增加 `power` 段。
12. 用 `hardware_capabilities.schema.json` 校验输出结构。
13. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程（S5a 产物源文件与 include 路径自动入工程；失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单）。
14. 更新 `state.json` 的 `s5a` 字段。

## 依赖

- Python 3.10+
- jsonschema 库
- xml.etree（IDE 工程同步公共工具 `skills/_shared/scripts/ide_sync.py` 解析工程文件）
- 可选：openai/anthropic SDK（用于低功耗策略辅助决策）

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- 不要修改 S4/S3 产出的文件。
- 不要修改 `outputs/` 中非本 Skill 产出的文件。
- 不得包含任何应用业务逻辑。
- 不得 include `app.h` 或 `driver_<设备>.h`。
- 不得定义 Port 接口，不得定义 OSAL 接口。
- 不得生成 `port_impl_*.c` 或 `port_impl_osal_*.c`。
- 不得把所有初始化代码塞进一个文件，必须按模块拆分。
- 不得把代码放在 `outputs/` 中，必须放在 S5a 产物目录（`Drivers/BSP/{Src,Inc}`）。
- 引脚、时钟、DMA、中断不得冲突。
- 不依赖 S5b 的任何产物。

## 补充说明

### 低功耗策略自主决策

当 `project.power.enabled == true` 时，Agent 应根据以下资料自主决定最优低功耗实现策略：

- MCU 头文件（低功耗寄存器、位定义）
- 数据手册（低功耗模式、电流、唤醒时间）
- 用户手册（进入/退出流程、时钟切换）
- 厂商 demo（官方推荐写法）
- 联网搜索（已知坑、社区最佳实践）
- S2 功能需求（何时该睡、什么事件唤醒）
- S3 chip data（外设时钟门控、唤醒源能力）
- S4 circuit facts（实际接了哪些唤醒引脚）

不需要用户配置唤醒源、模式选择、Tickless 等细节。

### 与 S5c 的契约

S5a 生成的 `hardware_capabilities.json` 是 S5c 实现 Port 的唯一硬件依据。S5c 只根据该文件映射 Port 接口到硬件外设，禁止直接读取 S3/S4 数据。

### IDE 工程同步格式示例（公共工具 ide_sync.py 写入）

Keil `.uvprojx` 文件中的 `<Groups>` 节点需要添加新的源文件：

```xml
<Group>
  <GroupName>Drivers/BSP</GroupName>
  <Files>
    <File>
      <FileName>clock_init.c</FileName>
      <FileType>1</FileType>
      <FilePath>..\Drivers\BSP\Src\clock_init.c</FilePath>
    </File>
    <File>
      <FileName>gpio_init.c</FileName>
      <FileType>1</FileType>
      <FilePath>..\Drivers\BSP\Src\gpio_init.c</FilePath>
    </File>
    <!-- 更多文件 -->
  </Files>
</Group>
```

同时在 `<IncludePath>` 中添加 `..\Drivers\BSP\Inc`。

