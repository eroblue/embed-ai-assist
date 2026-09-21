# S5c requirement.md

# S5c port-implementer Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个 AI Agent Skill。

## 基本信息

- **Skill 名称**：port-implementer
- **Skill 用途**：实现 Port / OSAL / Power 接口，将平台无关的调用翻译为具体 HAL / RTOS / 低功耗操作，扮演 Ports & Adapters 中的 Adapter 角色。`flat` 架构下跳过。
- **触发时机**：在 S5a 和 S5b 都完成后触发。

## 输入

从 `state.json` 读取：

- `s5a.init_sources`：S5a 输出的产物源文件列表（`Drivers/BSP/Src/` 下）
- `s5a.init_headers`：S5a 输出的产物头文件列表（`Drivers/BSP/Inc/` 下）
- `s5a.entry_source`：S5a 输出的总入口源文件路径
- `s5a.rtos_hw_init`：S5a 输出的 RTOS 硬件初始化文件路径（可选）
- `s5a.power_init`：S5a 输出的低功耗初始化文件路径（可选）
- `s5a.hardware_capabilities`：S5a 输出的硬件能力清单路径
- `s5a.architecture`：本次使用的架构
- `s5a.power_enabled`：是否启用低功耗
- `s5b.port_manifest`：S5b 输出的接口契约路径
- `s5b.port_headers`：`src/port/` 下 Port 头文件路径列表
- `s5b.osal_header`：OSAL 头文件路径（可选）
- `s5b.power_header`：Power 头文件路径（可选）
- `s5b.architecture`：本次使用的架构
- `s5b.power_enabled`：是否启用低功耗

从项目级 `config.json`（与全局 `config.json` 合并后）读取：

- `project.target`：MCU 型号
- `project.build_target`：目标工程（`"App"` / `"BootLoader"`，缺省 `"App"`）——`state.json` / 源码目录 / `outputs/` / IDE 工程目录均位于 `<项目根>/<build_target>/`，`docs/` 与 `references/` 为项目根共享
- `project.rtos`：RTOS 类型
- `project.architecture`：架构
- `project.power.enabled`：是否启用低功耗
- `project.inputs.ide_project`：IDE 项目文件路径（可选）
- `s5c.platform`：平台标识
- `s5c.hal_framework`：HAL 框架

可选参考材料：

- `references/demos/`：demo 程序
- `references/sdk/`：SDK 源码
- `references/existing_project/`：已有项目

## 输出

### 文件拆分原则

S5c 生成的 Port 实现**必须按外设拆分成多个文件**，**统一输出到 `src/port_impl/` 目录**：

- 每个外设一个实现文件：`port_impl_uart_<平台>.c`、`port_impl_i2c_<平台>.c`、`port_impl_spi_<平台>.c`、`port_impl_gpio_<平台>.c`、`port_impl_adc_<平台>.c`、`port_impl_timer_<平台>.c`、`port_impl_pwm_<平台>.c` 等。
- OSAL 实现：`port_impl_osal_<rtos>.c`（单一文件）。
- Power 实现：`port_impl_power_<平台>.c`（单一文件）。
- 每个实现文件对应一个头文件（如需要），或直接 include S5b 的 Port 头文件。
- 未被使用的外设不生成。

### 写入 state.json（仅 s5c 字段）

| 字段 | 类型 | 说明 |
|---|---|---|
| `s5c.status` | string | `pending` / `running` / `done` / `error` / `skipped` |
| `s5c.rtos` | string | 本次生成使用的 RTOS 配置 |
| `s5c.architecture` | string | 本次使用的架构 |
| `s5c.power_enabled` | bool | 是否启用低功耗 |
| `s5c.port_impl_sources` | array | `src/port_impl/` 下源文件相对路径列表 |
| `s5c.osal_impl` | string/null | `src/port_impl/port_impl_osal_<rtos>.c` 相对路径，裸机时为 null |
| `s5c.power_impl` | string/null | `src/port_impl/port_impl_power_<平台>.c` 相对路径，未启用低功耗时为 null |
| `s5c.compile_status` | string | `passed` / `failed` / `skipped` |
| `s5c.error` | string/null | 错误信息 |
| `s5c.updated_at` | string | ISO 时间戳 |

### 写入 src/port_impl/

| 产物 | 内容说明 |
|---|---|
| `src/port_impl/port_impl_uart_<平台>.c` | UART Port 实现（如有使用） |
| `src/port_impl/port_impl_i2c_<平台>.c` | I2C Port 实现（如有使用） |
| `src/port_impl/port_impl_spi_<平台>.c` | SPI Port 实现（如有使用） |
| `src/port_impl/port_impl_gpio_<平台>.c` | GPIO Port 实现（如有使用） |
| `src/port_impl/port_impl_adc_<平台>.c` | ADC Port 实现（如有使用） |
| `src/port_impl/port_impl_timer_<平台>.c` | Timer Port 实现（如有使用） |
| `src/port_impl/port_impl_pwm_<平台>.c` | PWM Port 实现（如有使用） |
| `src/port_impl/port_impl_osal_<rtos>.c` | OSAL 实现（如启用 RTOS） |
| `src/port_impl/port_impl_power_<平台>.c` | Power 实现（如启用低功耗） |

### 写入 outputs/s5c/

| 产物 | 内容说明 |
|---|---|
| `outputs/s5c/compile_report.json` | 编译结果报告，结构由 `schemas/compile_report.schema.json` 约束 |

### 指针/数据分离规则

- 代码放 `src/port_impl/`，数据产物放 `outputs/s5c/`。
- `state.json` 中只存指针与统计计数，不存数据本体，不存代码本体。

## Skill 目录结构（标准结构）

```text
port-implementer/
├── SKILL.md
├── schemas/
│   ├── input.schema.json
│   ├── output.schema.json
│   └── compile_report.schema.json
├── scripts/
│   ├── implement.py                # 主入口
│   ├── port_impl_generator.py      # Port 实现生成（按外设分发）
│   ├── osal_impl_generator.py      # OSAL 实现生成
│   ├── power_impl_generator.py     # Power 实现生成
│   └── compile_verifier.py         # 编译验证
├── references/
│   ├── hal_mapping_guide.md        # HAL 映射指南
│   ├── rtos_mapping_guide.md       # RTOS 映射指南
│   └── file_split_guide.md         # 文件拆分规范
└── assets/
    └── compile_report_example.json
```

> IDE 工程同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成
> （跨 Skill 共享，S5a/S5b/S5c 各自 validate 段调用）。

## 执行步骤

1. 从 `state.json` 读取 `s5a.*` 和 `s5b.*` 字段，确认 S5a 和 S5b 均已成功执行。
2. 读取项目级 `config.json`，与全局 `config.json` 合并。
3. 检查 `project.architecture`：
   - `flat`：跳过执行，`s5c.status` 置为 `skipped`，终止。
   - 非 `flat`：继续执行。
4. 读取参考材料（可选）：`references/demos/`、`references/sdk/`、`references/existing_project/`。
5. 读取 `outputs/s5b/port_interface_manifest.json`，解析接口契约。
6. 读取 `outputs/s5a/hardware_capabilities.json`，获取硬件能力。
7. 遍历 manifest 中的每个 Port 接口，按外设逐个生成实现文件到 `src/port_impl/`：
   - 每个外设一个 `.c` 文件，如 `port_impl_uart_gd32.c`。
   - 每个文件只实现对应外设的 Port 接口。
8. 若 `project.rtos != "none"`，生成 `src/port_impl/port_impl_osal_<rtos>.c`。
9. 若 `project.power.enabled == true`，生成 `src/port_impl/port_impl_power_<平台>.c`。
10. 如果 S5b 需要的硬件能力在 S5a 中不存在，报告 `capability_gap`。
11. 调用 `compile_verifier.py` 验证生成的代码能否链接完整工程，输出 `outputs/s5c/compile_report.json`。
12. 调用公共工具 `skills/_shared/scripts/ide_sync.py` 同步 IDE 工程（`src/port_impl/` 源文件与 include 路径自动入工程；失败不中断，输出 `outputs/_shared/ide_sync_manual.md` 手动清单）。
13. 更新 `state.json` 的 `s5c` 字段。

## 依赖

- Python 3.10+
- jsonschema 库
- xml.etree（IDE 工程同步公共工具 `skills/_shared/scripts/ide_sync.py` 解析工程文件）
- 交叉编译工具链（用于编译验证）

## 禁止事项

- 不要修改 `config.json`，不要读写其他 Skill 的字段。
- 不要修改 S5a / S5b 产出的文件。
- 不得修改 `port.h`、`osal_port.h` 或 `power_port.h` 接口定义。
- 不得写任何应用业务逻辑。
- 不得生成 HAL 初始化代码。
- 必须优先读取 `port_interface_manifest.json`，不得硬解析 C 头文件。
- 不得把所有 Port 实现塞进一个文件，必须按外设拆分。
- 不得把代码放在 `outputs/` 中，必须放在 `src/port_impl/`。
- 如果 S5b 需要的硬件能力在 S5a 中不存在，必须报 `capability_gap`，不得偷偷改接口。

## 补充说明

### 换平台与换 RTOS 的重跑规则

- 换 MCU：只重跑 S5a 和 S5c，S5b 产物不变。
- 换 RTOS：只重跑 S5a 和 S5c 的 RTOS 相关部分，S5b 产物不变。
- 同时换 MCU 和 RTOS：重跑 S5a 和 S5c，S5b 产物不变。

### 编译验证

生成的 `port_impl_*.c` 必须能链接完整工程并编译通过。`compile_report.json` 需包含编译结果、错误信息和对应的 S2 功能用例映射。

### 能力缺口处理

如果 S5b 定义的 Port 接口需要某硬件能力，但 S5a 的 `hardware_capabilities.json` 中没有提供，S5c 应输出 `capability_gap` 并终止，不得尝试修改接口或降级实现。

### 文件拆分示例

一个使用 UART、I2C、GPIO、ESP32C2 WiFi 模块的 GD32F205 项目，S5c 输出示例：

```text
src/port_impl/
├── port_impl_uart_gd32.c
├── port_impl_i2c_gd32.c
├── port_impl_gpio_gd32.c
├── port_impl_osal_freertos.c
└── port_impl_power_gd32.c
```