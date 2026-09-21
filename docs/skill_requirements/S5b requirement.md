# S5b requirement.md

# S5b port-contract-and-app Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：port-contract-and-app
- **Skill 用途**：从功能规格书、软件规格书和参考材料出发，根据架构决定分层程度，定义平台无关的 Port / OSAL / Power 接口，并生成 APP、任务化 APP、协议层、设备驱动代码。
- **触发时机**：在 S2 执行完成后触发，与 S5a 可并行执行。

## 输入

从 `state.json` 读取：

- `spec.*`：S2 输出的功能规格书数据路径

从项目级 `config.json`（与全局 `config.json` 合并后）读取：

- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.architecture`：`"flat"` / `"layered"` / `"full"`，未配置时由 Agent 从 S2 复杂度推断
- `project.power.enabled`：是否启用低功耗
- `project.rtos`：RTOS 类型（可选，未配置时由 Agent 推断）
- `project.rtos_config.max_prio`：最大任务优先级（可选）
- `project.inputs.functional_spec`：功能规格书路径（可选）
- `project.inputs.software_spec`：软件规格书路径（可选）
- `project.inputs.demos`：demo 程序目录列表（可选）
- `project.inputs.sdk`：SDK 目录（可选）
- `project.inputs.existing_project`：已有项目目录（可选）
- `project.inputs.ide_project`：IDE 项目文件路径（可选）
- `s5b.language`：语言标准（可选，默认 `c99`）
- `s5b.port_split`：Port 拆分策略（可选，按应用需求推断）

### 输入材料说明

| 输入 | 用途 |
|---|---|
| 功能规格书 | 提取功能需求、外设需求、性能指标 |
| 软件规格书 | 提取软件开发要求：任务划分、时序约束、通信协议、状态机、错误处理、日志、配置项 |
| demo 程序 | 学习代码风格、初始化写法、外设使用方式 |
| SDK | 学习厂商 API 命名、数据结构、调用约定 |
| 已有项目 | 参考工程结构、代码风格、模块划分 |
| IDE 项目文件 | 了解工程配置、include 路径、已存在的源文件 |

未配置时，Agent 按默认路径自动发现：`docs/software_spec.*`、`references/demos/`、`references/sdk/`、`references/existing_project/`、IDE 工程目录（`MDK-ARM/`/`IAR/`/`Project/`，见 `docs/PROJECT_LAYOUT.md`）。

## 输出

### 文件拆分原则

S5b 生成的代码**必须按功能模块拆分成多个文件**，**统一输出到 `src/` 下的对应目录**：

- Port 接口：`src/port/<外设>_port.h`，按外设拆分。
- OSAL 接口：`src/port/osal_port.h`（单一文件）。
- Power 接口：`src/port/power_port.h`（单一文件）。
- APP 主入口：`src/app/app.c/h`，只做初始化和主循环/任务创建。
- APP 功能模块：`src/app/app_<功能>.c/h`。
- 任务化 APP：`src/app/app_<功能>_task.c/h`。
- 协议层：`src/protocol/protocol_<名称>.c/h`。
- 设备驱动：`src/driver/driver_<设备>.c/h`。
- 主入口：`src/main.c`（如不存在则由 S5b 创建）。
- 未被使用的模块不生成。

### 写入 state.json（仅 s5b 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5b.status` | string | `pending` / `running` / `done` / `error` |
| `s5b.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5b.architecture` | string | 本次使用的架构 |
| `s5b.power_enabled` | bool | 是否启用低功耗 |
| `s5b.port_manifest` | string | `outputs/s5b/port_interface_manifest.json` 相对路径 |
| `s5b.port_headers` | array | `src/port/` 下 Port 头文件相对路径列表 |
| `s5b.osal_header` | string/null | `src/port/osal_port.h` 相对路径，裸机时为 null |
| `s5b.power_header` | string/null | `src/port/power_port.h` 相对路径，未启用低功耗时为 null |
| `s5b.app_sources` | array | `src/app/` 下源文件相对路径列表 |
| `s5b.app_headers` | array | `src/app/` 下头文件相对路径列表 |
| `s5b.app_task_sources` | array | `src/app/` 下任务化源文件列表，裸机时可为空 |
| `s5b.protocol_sources` | array | `src/protocol/` 下源文件相对路径列表 |
| `s5b.driver_sources` | array | `src/driver/` 下源文件相对路径列表 |
| `s5b.driver_headers` | array | `src/driver/` 下头文件相对路径列表 |
| `s5b.main_source` | string | `src/main.c` 相对路径 |
| `s5b.ide_pending_files` | string | `outputs/s5b/ide_pending_files.json` 路径（兜底参考；IDE 同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成） |
| `s5b.error` | string/null | 错误信息 |
| `s5b.updated_at` | string | ISO 时间戳 |

### 写入 src/port/

| 产物 | 内容说明 |
|---|---|
| `src/port/uart_port.h` | UART Port 接口（如有使用） |
| `src/port/i2c_port.h` | I2C Port 接口（如有使用） |
| `src/port/spi_port.h` | SPI Port 接口（如有使用） |
| `src/port/gpio_port.h` | GPIO Port 接口（如有使用） |
| `src/port/adc_port.h` | ADC Port 接口（如有使用） |
| `src/port/timer_port.h` | Timer Port 接口（如有使用） |
| `src/port/pwm_port.h` | PWM Port 接口（如有使用） |
| `src/port/osal_port.h` | OSAL 接口（如启用 RTOS 且非 flat） |
| `src/port/power_port.h` | Power 接口（如启用低功耗且非 flat） |

### 写入 src/app/

| 产物 | 内容说明 |
|---|---|
| `src/app/app.c/h` | APP 主入口，只做汇总 |
| `src/app/app_<功能>.c/h` | APP 功能模块 |
| `src/app/app_<功能>_task.c/h` | 任务化 APP（如启用 RTOS） |

### 写入 src/protocol/

| 产物 | 内容说明 |
|---|---|
| `src/protocol/protocol_<名称>.c/h` | 协议层模块 |

### 写入 src/driver/

| 产物 | 内容说明 |
|---|---|
| `src/driver/driver_<设备>.c/h` | 设备驱动模块 |

### 写入 src/

| 产物 | 内容说明 |
|---|---|
| `src/main.c` | 主入口（如不存在） |

### 写入 outputs/s5b/

| 产物 | 内容说明 |
|---|---|
| `outputs/s5b/port_interface_manifest.json` | 接口契约，结构由 `schemas/port_interface_manifest.schema.json` 约束 |
| `outputs/s5b/mocks/` | 可选，Mock Port 实现 |
| `outputs/s5b/tests/` | 可选，单元测试 |

### APP 主入口示例

```c
/* src/app/app.c 只做初始化和主循环/任务创建 */
#include "app.h"
#include "app_led.h"
#include "app_wifi.h"
#include "osal_port.h"

void app_init(void)
{
    app_led_init();
    app_wifi_init();
}

void app_start(void)
{
    osal_task_create(app_led_task, "led", 256, PRIO_LOW);
    osal_task_create(app_wifi_task, "wifi", 512, PRIO_NORMAL);
}
```

### 指针/数据分离规则

- 代码放 `src/` 下对应目录，数据产物放 `outputs/s5b/`。
- `state.json` 中只存指针与统计计数，不存数据本体，不存代码本体。

## Skill 目录结构（标准结构）

```text
port-contract-and-app/
├── SKILL.md
├── schemas/
│   ├── input.schema.json
│   ├── output.schema.json
│   └── port_interface_manifest.schema.json
├── scripts/
│   ├── generate.py                  # 主入口
│   ├── input_learner.py             # 输入材料学习（软件规格书、demo、SDK、已有项目）
│   ├── port_contract_generator.py   # Port 接口定义生成
│   ├── osal_contract_generator.py   # OSAL 接口生成
│   ├── power_contract_generator.py  # Power 接口生成
│   ├── app_generator.py             # APP 主入口生成
│   ├── app_module_generator.py      # APP 功能模块生成
│   ├── task_generator.py            # 任务化 APP 生成
│   ├── protocol_generator.py        # 协议层生成
│   ├── driver_generator.py          # 设备驱动生成
│   ├── main_generator.py            # main.c 生成
│   └── ide_pending_exporter.py     # IDE 待添加清单导出（实际同步由公共工具 skills/_shared/scripts/ide_sync.py 完成）
├── references/
│   ├── port_design_principle.md     # Port 设计原则
│   ├── osal_design_principle.md     # OSAL 设计原则
│   ├── file_split_guide.md          # 文件拆分规范
│   ├── software_spec_guide.md       # 软件规格书解析指南
│   └── ide_project_formats.md       # IDE 项目文件格式说明
└── assets/
    └── port_interface_manifest_example.json
```

## 执行步骤

1. 从 `state.json` 读取 `spec.*` 字段，确认 S2 已成功执行。
2. 读取项目级 `config.json`，与全局 `config.json` 合并。
3. **读取输入材料**：
   - 功能规格书（S2 已解析，从 `spec.*` 读取）。
   - 软件规格书：解析软件开发要求。
   - demo 程序：学习代码风格和写法。
   - SDK：学习 API 命名和调用约定。
   - 已有项目：参考工程结构和模块划分。
   - IDE 项目文件：了解工程配置和 include 路径。
4. 综合分析输入材料，识别所需外设、业务功能、协议、设备。
5. 根据 `project.architecture`（未配置时自动推断）决定是否生成 Port 层：
   - `flat`：不生成 `src/port/`，APP 直接访问寄存器或厂商库。
   - 非 `flat`：按外设列表生成多个 `src/port/<外设>_port.h`。
6. 根据 `project.rtos` 判断是否生成 OSAL 接口：
   - `none` 或 `flat`：不生成 `osal_port.h`，APP 可为裸机主循环。
   - 非 `none` 且非 `flat`：生成 `src/port/osal_port.h`。
7. 根据 `project.power.enabled` 判断是否生成 Power 接口：
   - `true` 且非 `flat`：生成 `src/port/power_port.h`。
   - `flat` 且 `true`：低功耗逻辑直接写在 APP 内，不生成 `power_port.h`。
8. 从功能规格书和软件规格书出发定义 Port 接口，按应用能力拆分，不按 MCU 外设拆分。
9. 生成 `outputs/s5b/port_interface_manifest.json`，包含 Port、OSAL、Power 接口契约。
10. 生成 APP 主入口 `src/app/app.c/h`，只做初始化和主循环/任务创建。
11. 按功能模块生成 `src/app/app_<功能>.c/h`。
12. 如启用 RTOS，生成 `src/app/app_<功能>_task.c/h`。
13. 按协议生成 `src/protocol/protocol_<名称>.c/h`。
14. 按设备生成 `src/driver/driver_<设备>.c/h`。
15. 生成或更新 `src/main.c`。
16. 确保所有 APP / Driver / 协议层源文件不 include 任何 HAL 头文件和 RTOS 头文件。
17. 用 Schema 校验输出结构。
18. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程（`src/` 下源文件与 include 路径自动入工程；失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单）。
19. 更新 `state.json` 的 `s5b` 字段。

## 依赖

- Python 3.10+
- jsonschema 库
- xml.etree（IDE 工程同步公共工具 `skills/_shared/scripts/ide_sync.py` 解析工程文件）
- 可选：openai/anthropic SDK（用于软件规格书解析和代码风格学习）

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- 不要修改 S2 产出的文件。
- 不得依赖 S5a 的任何产物。
- 所有 APP / Driver / 协议层源文件不得 include 任何 HAL 头文件。
- 所有 APP / Driver / 协议层源文件不得 include 任何 RTOS 头文件。
- RTOS 相关调用必须通过 `osal_port.h`。
- Port 接口只使用基本类型和不透明句柄。
- DMA 不得单独暴露给 APP，应隐藏在 UART 等实现中。
- 不得把所有 APP 逻辑塞进一个 `app.c`，必须按功能模块拆分。
- 不得把所有 Port 接口塞进一个 `port.h`，必须按外设拆分。
- 不得把代码放在 `outputs/` 中，必须放在 `src/` 下。
- 换平台时，S5b 产物哈希必须保持不变。
- 换 RTOS 时，S5b 产物哈希必须保持不变。

## 补充说明

### Port 接口设计原则

- 从应用需求出发定义接口，不从硬件外设出发。
- 可按应用需求拆分为 `uart_port.h`、`gpio_port.h` 等。
- 只使用平台无关类型：基本类型、不透明句柄。
- 错误码统一。
- 生命周期明确：init / open / close / deinit。
- 回调上下文明确：中断上下文可调用什么，不可调用什么。

### OSAL 接口设计原则

- 只使用平台无关类型。
- 不出现 `FreeRTOS.h`、`xTaskCreate`、`osThreadNew` 等 RTOS API。
- 统一错误码。
- 提供任务、队列、互斥锁、信号量、事件、时间等抽象。
- 提供 ISR 安全接口，如 `osal_sem_give_from_isr`。

### Power 接口设计原则

- 只使用平台无关类型。
- 只暴露少量原语，如 `power_port_enter_sleep`、`power_port_enter_stop`、`power_port_enter_standby`、`power_port_get_wakeup_reason`。
- 不暴露唤醒源、模式选择等细节，这些由 Agent 在 S5c 中自主决定。

### 软件规格书解析

软件规格书应包含以下内容，Agent 需要从中提取：

- 任务划分与优先级
- 时序约束与实时性要求
- 通信协议（帧格式、命令码、校验方式）
- 状态机定义
- 错误处理策略
- 日志与调试要求
- 配置项与默认值

### 输入材料学习策略

- **代码风格**：从 demo 和已有项目学习命名规范、注释风格、错误处理方式。
- **API 使用**：从 SDK 学习厂商 API 命名、数据结构、调用约定。
- **工程结构**：从已有项目学习模块划分、目录结构、头文件组织。
- **工程配置**：从 IDE 项目文件学习 include 路径、宏定义、编译选项。

### 文件拆分示例

一个使用 UART + ESP32C2 WiFi 模块、I2C + EEPROM、LED 指示的 GD32F205 项目，S5b 输出示例：

```text
src/
├── main.c
├── port/
│   ├── uart_port.h
│   ├── i2c_port.h
│   ├── gpio_port.h
│   ├── osal_port.h
│   └── power_port.h
├── app/
│   ├── app.c/h
│   ├── app_led.c/h
│   ├── app_wifi.c/h
│   └── app_wifi_task.c/h
├── protocol/
│   └── protocol_at.c/h
└── driver/
    ├── driver_esp32c2.c/h
    └── driver_eeprom.c/h
```

