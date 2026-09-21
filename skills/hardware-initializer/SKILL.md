---
name: "hardware-initializer"
description: "S5a 硬件初始化，三段式执行模型：rule 脚本 prepare.py 分析 S4 硬件事实/S3 芯片数据/设计输入并输出 Agent 任务书 generation_brief.md，Agent（LLM）按任务书亲自编写 S5a 产物目录（PROJECT_LAYOUT.md 解析，如 Drivers/BSP/{Src,Inc}）初始化代码（时钟/GPIO/NVIC/外设/RTOS/低功耗），rule 脚本 validate.py 校验产物、输出硬件能力清单，并调用公共工具 ide_sync.py 同步 IDE 工程。在 S3、S4 都执行完成后触发，与 S5b 可并行；新增硬件平台无需编写适配脚本。"
---

# hardware-initializer 硬件初始化（S5a）

## 用途

从 S4 输出的硬件事实、S3 输出的芯片数据和用户设计输入出发，完成平台相关的
硬件底层初始化代码生成（裸机或 RTOS、可选低功耗），并输出硬件能力清单，
为 S5c 实现 Port 接口提供 HAL 支撑。

**整体流程层级：S5a，代码生成层（平台相关）**。

- 上游依赖：S3 datasheet-extractor（`chip.*` + `outputs/chip_info/*.json`）、
  S4 circuit-investigator（`circuit.facts` + `outputs/circuit_facts.json`）
- 并行关系：与 **S5b port-contract-and-app 无数据依赖，可并行执行**
- 下游消费：**S5c port-implementer** 只依据 `outputs/s5a/hardware_capabilities.json`
  实现 Port，禁止直接读取 S3/S4 数据
- 架构模式：Ports & Adapters 中的 VENDOR 层（平台相关）

## 执行模型：rule 准备 → Agent 生成 → rule 校验

**策略（用户拍板）**：确定性的规则用本地脚本实现；具体初始化代码（C 代码）
由 Agent（LLM）生成。这样结合两者优势——rule 轨快、稳、零 token，且新增
硬件平台不需要编写平台适配脚本，避免工作流文件量爆炸。

```
[rule]  prepare.py    配置/就绪检查 → usage 分析 → 时钟数值计算
                        → 按 PROJECT_LAYOUT.md 幂等创建目录骨架（ensure_layout）
                        → outputs/s5a/generation_brief.md（任务书）
                        → state.s5a.status = "running"
[agent] Agent 生成代码  读 SKILL.md + 任务书 + init_code_templates.md
                        + SDK 头文件（确认 API/枚举名）
                        → 亲自编写 S5a 产物目录 *.c/h（任务书指定，如
                          Drivers/BSP/{Src,Inc}；增量模式只重写任务书
                          标注 CHANGED 的模块，其余文件不动；
                          批量写入：单轮多文件并行写、组稿与核对分离）
[rule]  validate.py    校验产物（模块齐全/总入口汇总/实例覆盖/禁止 include
                        + mtime 守卫：CHANGED 模块须晚于任务书更新）
                        → hardware_capabilities.json + ide_pending_files.json
                        → state.s5a.status = "done"
                        → 调用公共工具 ide_sync.py 同步 IDE 工程（失败不中断）
```

- validate 失败（退出码 1）→ Agent 按失败报告修复代码，**重跑 validate.py**
  （state 保持 running，不写 error；mtime 守卫失败表示 Agent 段被跳过，
  需先重写任务书标注 CHANGED 的模块）
- 环境/契约失败（退出码 3）→ state 写 error，先解决 S3/S4/config 问题
- **增量模式**（module_snapshot.json 与上轮 diff）：无变更 → 跳过 Agent 段直接
  validate（秒级收尾）；局部变更 → 只重写 CHANGED 模块（1-2 个文件，分钟内）；
  首次运行 / 平台/RTOS/架构/低功耗变化 → 全量重写

## 目录结构

```
hardware-initializer/
├── SKILL.md                          ← 本文件（Agent 操作手册）
├── schemas/
│   ├── input.schema.json             ← 输入契约（S3/S4 就绪性检查）
│   ├── output.schema.json            ← 输出契约（state.json 的 s5a 字段，含 running）
│   └── hardware_capabilities.schema.json ← 硬件能力清单数据契约
├── scripts/                          ← rule 轨（仅确定性契约工作，无代码生成）
│   ├── analysis.py                   ← 共享分析：配置/usage/时钟数值/设计输入
│   ├── prepare.py                    ← 第 1 段：分析 + 输出 Agent 任务书
│   ├── validate.py                   ← 第 3 段：产物校验 + 能力清单 + IDE 清单
│   ├── capability_extractor.py       ← 硬件能力清单聚合
│   └── ide_pending_exporter.py       ← IDE 待添加清单导出（兜底参考；实际同步由公共工具 skills/_shared/scripts/ide_sync.py 完成）
├── references/
│   ├── init_code_templates.md        ← Agent 代码生成规范（平台 API 惯例 + 示例）
│   ├── file_split_guide.md           ← 文件拆分规范
│   ├── ide_project_formats.md        ← IDE 项目文件格式说明
│   └── low_power_strategies.md       ← 低功耗策略参考（Agent 决策依据）
└── assets/
    └── hardware_capabilities_example.json ← 能力清单示例
```

平台数值约束（主频上限/PLL 倍频范围/实例编号惯例）收敛在
`analysis.py` 的 `PLATFORM_INFO` 小表；**未登记平台不报错**——按保守缺省
计算并在任务书中提示 Agent 依据参考手册/SDK 头文件复核（零脚本适配）。

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| chip.* | state.json（S3 写入） | object | 是 | `pins_path`/`peripherals_path`/`clock_tree_path` |
| circuit.facts | state.json（S4 写入） | object | 是 | `facts_path`（含每引脚 role/peripheral/config） |
| platform | config.json（项目层） | string | 是 | 芯片平台名（主控识别 + 数值表前缀路由） |
| project.build_target | config.json（项目层） | enum | 否 | `App` / `BootLoader`，缺省 App——目标工程根（state.json / 源码目录 / outputs / IDE 工程目录所在）；docs / references 共享于项目根 |
| project.architecture | config.json（项目层） | enum | 否 | `flat` / `layered` / `full`，缺省 layered（32 位惯例） |
| project.rtos | config.json（项目层） | enum | 否 | `none` / `FreeRTOS` / `RT-Thread` / `Zephyr`，缺省 none（裸机） |
| project.power.enabled | config.json（项目层） | bool | 否 | `true` / `false`，缺省 false |
| s5a.uart_baudrate | config.json（项目层） | int | 否 | 缺省 115200 |
| stdperiph_lib_path | config.json（项目层） | string | 否 | 标准外设库路径；回退根目录 `platforms/<platform>/std_periph_lib/` |
| docs/s5a_design_input.md | 项目 docs/ 目录 | markdown | 否 | **用户设计输入**，见下 |

> 配置契约（含 `project` 段全部枚举值）统一由根目录 `schemas/config.schema.json` 定义；
> S2/S3/S4/S5a 加载合并配置时统一拦截，填错立即报错并列出合法值。

### 用户设计输入（docs/s5a_design_input.md）

用户向 Agent 传达设计意图的输入通道，**优先级高于自动推断**。**文件不存在、
内容为空或全部为 `none` 时，改由 Agent（LLM）基于 S4 硬件事实与 S3 芯片数据
自主判断**——任务书中的自动推断结果作为基线，Agent 应复核并校正（如调整外设
配置模式、补充特殊引脚语义）。填写示例见项目 `docs/demo/s5a_design_input_demo.md`：

```markdown
# s5a设计输入， 告诉 Agent 外设怎么用.

## 时钟
- 主频：120 MHz，使用 HSE 8MHz + PLL

## 外设使用
- UART0：使用 DMA 收发，波特率 115200
- SPI0：使用 DMA，模式 0

## 特殊引脚
- PA0：作为 EXTI0 唤醒源
```

三级语义：**设计输入 > Agent（LLM）判断 > rule 自动推断**。消费方式分两轨：

- **rule 轨（脚本机械解析，进任务书数值）**：UART 波特率按实例号覆盖；
  主频目标可达则精确采用，不可达回退并记入 `capabilities.constraints`。
- **agent 轨（Agent 结合原文校正）**：DMA 使用方式、特殊引脚用途（如 EXTI
  唤醒源）、低功耗策略等无法机械解析的内容，Agent 生成代码时读原文校正。

命令行覆盖参数（仅本次生效）：`--arch` / `--workspace`。

## 输出

### 写入 S5a 产物目录（Agent 生成的代码，编译烧录用）

> 目录由 `docs/PROJECT_LAYOUT.md` 解析（prepare 段已创建骨架，任务书给出确切路径）：
> 32 位 Cortex-M 为 `Drivers/BSP/Src/`（.c）+ `Drivers/BSP/Inc/`（.h）；
> 改布局文档即全局生效，不硬编码在脚本里。

| 产物 | 生成条件 |
|------|----------|
| `clock_init.c/h` | 总是（HSE/PLL/总线分频/LSE/FLASH 等待周期） |
| `gpio_init.c/h` | 存在已配置 GPIO（含 FSMC 复用引脚） |
| `nvic_init.c/h` | 总是（分组 + IRQ 使能建议注释） |
| `uart_init.c/h`、`spi_init.c/h`、`i2c_init.c/h`、`adc_init.c/h`、`pwm_init.c/h`、`fsmc_init.c/h` | 按任务书外设使用清单实际使用的外设逐个生成。fsmc 为 EXMC/FSMC bank/时序本体（引脚复用在 gpio_init），时序取保守默认值并注释标注 |
| `rtos_hw_init.c/h` | `project.rtos != "none"` |
| `power_init.c/h` | `project.power.enabled == true` |
| `hal_init.c/h` / `board_init.c/h` | 总入口，只做汇总调用（layered/full 用前者） |

### 写入 outputs/s5a/（rule 轨数据）

| 产物 | 内容说明 |
|------|----------|
| `generation_brief.md` | Agent 任务书（prepare 段）：项目信息/时钟数值/外设清单/生成要求/禁止事项/数据来源，含"增量模式"节（CHANGED/UNCHANGED 模块清单） |
| `module_snapshot.json` | 模块数值快照（prepare 段）：增量 diff 依据，域级数值（时钟/GPIO/各外设/中断）与上轮比对得出 CHANGED 模块 |
| `hardware_capabilities.json` | 硬件能力清单（mcu/rtos/architecture/clocks/peripherals[]/power/constraints），S5c 实现 Port 的唯一硬件依据 |
| `ide_pending_files.json` | IDE 待添加清单（源文件 + group + include 路径，兜底参考）。IDE 工程同步由公共工具 `skills/_shared/scripts/ide_sync.py` 完成：validate 段自动调用（谁跑完谁同步，全局文件锁防并行冲突），失败不中断并输出 `outputs/_shared/ide_sync_manual.md` 手动清单 |

### 写入 state.json（仅 s5a 字段）

`status`（running/done/error/skipped）、`rtos`、`architecture`、`power_enabled`、
`generation_brief`（任务书路径）、`incremental`（增量/全量标记）、
`changed_modules`（本轮需重写的模块清单）、
`init_sources`/`init_headers`（相对路径列表）、
`entry_source`/`entry_header`、`rtos_hw_init`/`power_init`（null 表示未生成）、
`hardware_capabilities`、`ide_pending_files`、`error`、`updated_at`。

指针/数据分离：代码在 S5a 产物目录（如 `Drivers/BSP/{Src,Inc}`），数据在
`outputs/s5a/`，state.json 只存指针。

## 执行步骤（Agent 操作手册）

1. [rule] 运行 prepare（配置分层加载 → S3/S4 就绪检查 → usage 分析 →
   时钟数值计算 → 任务书）：
   ```bash
   python skills/hardware-initializer/scripts/prepare.py --config <项目>/config.json
   ```
2. [agent] 读 `outputs/s5a/generation_brief.md`，通读本文件与
   `references/init_code_templates.md`
3. [agent] 读标准外设库头文件（任务书第 1 节给出的路径），核对将要用到的
   API 函数名/枚举名/时钟使能宏——**不确定的留 TODO 注释，不臆造 API**
4. [agent] 按任务书逐模块编写 S5a 产物目录 *.c/h（任务书第 4 节指定确切路径）：数值（引脚/实例/时钟/波特率）
   **直接采用任务书**，不要自行改推；设计输入原文中的 agent 轨语义
   （DMA 模式、EXTI 唤醒源等）在此步校正进代码。
   **增量模式**：任务书"增量模式"节标注 CHANGED 时**只重写这些模块**
   （其余文件保持现状不动）；标注"无变更模块"时跳过本步直接执行第 5 步。
   **批量写入**：单轮响应内并行发出多个文件的写入调用（建议 4 文件/轮，
   即 2 模块的 .c/.h），全部模块写完后统一核对与校验（第 5 步）——
   组稿与核对分离，避免逐文件"写→等结果→再写"的往返开销
5. [rule] 运行校验：
   ```bash
   python skills/hardware-initializer/scripts/validate.py --config <项目>/config.json
   ```
   （validate 内部最后自动调用公共工具 `skills/_shared/scripts/ide_sync.py`
   同步 IDE 工程：src/ 差异同步 + 全局文件锁；工程文件缺失或同步失败时
   输出 `outputs/_shared/ide_sync_manual.md` 手动清单，不影响 S5a 产物）
6. [agent] 校验失败（退出码 1）→ 按失败报告修代码，重跑第 5 步，直到通过
   （state 变为 done）

## 依赖

- Python 3.10+，jsonschema（契约校验）
- Agent 生成代码需可访问任务书指定的标准外设库/SDK 头文件

## 禁止事项

**rule 脚本侧**：不要修改 config.json；不要读写其他 Skill 的 state.json 字段；
不要修改 S3/S4 产出的文件；不要生成任何 C 代码。

**Agent 侧**：
- 不 include `app.h` / `driver_*.h` / `port_*.h` / `osal_*.h`，不含任何应用业务逻辑
- 不定义 Port/OSAL 接口（S5b 职责），不生成 `port_impl_*.c`（S5c 职责）
- 不修改 IDE 项目工程文件（.uvprojx/.ewp 等）——同步由公共工具 skills/_shared/scripts/ide_sync.py 完成
- 不把代码放在 outputs/，不把数据放在 src/；不把所有初始化塞进单文件
- 引脚、时钟、DMA、中断不得冲突（发现冲突记入 capabilities.constraints）
- 不依赖 S5b 的任何产物
