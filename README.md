# embed-ai-assist

嵌入式软件开发 AI 辅助开发框架：从原理图、MCU 数据手册、功能规格书，到代码生成、编译、
固件合并、烧录、串口测试的全流程 Skill 编排。

## 目录结构

- `skills/`：所有 AI Skill 的定义（每个 Skill 是一个独立目录）
- `platforms/`：芯片平台资料库（数据手册、标准库、CMSIS 等，只读共享）
- `examples/`：验证和演示工程（每个示例自包含）
- `projects/`：实际项目工作区（每个项目自包含）
- `config.json`：全局配置（工具路径等）

每个示例和项目都有独立的 `config.json` 与 App / BootLoader 双工程结构
（`state.json` / 源码目录 / `outputs` / IDE 工程目录位于 `<项目根>/<build_target>/`，
`build_target` 缺省 `App`；`docs/` / `references/` 等共享资源在项目根），
通过分层配置机制与根目录的全局配置协同工作。详见「配置加载规则」。

### 详细目录树

```
embed-ai-assist/
├── skills/                              # 所有 Skill
│   ├── schematic-reader/                # S1 原理图解析（参考实现）
│   ├── spec-reader/                     # S2 规格书阅读器（md/docx/pdf → spec.json 结构化需求）
│   ├── datasheet-extractor/             # S3 芯片手册提取（SVD > SDK 头文件 > PDF；8 位平台走单手册 PDF 适配器）
│   ├── circuit-investigator/            # S4 电路侦查（S1×S3 交叉验证 → 硬件事实）
│   ├── hardware-initializer/            # S5a 硬件初始化（时钟/GPIO/NVIC/外设 → Drivers/BSP/）
│   ├── port-contract-and-app/           # S5b Port 契约 + APP（已实现，rule/Agent 三段式 + 流程图驱动增量）
│   └── port-implementer/                # S5c Port 实现（规划中，SKILL.md 为实现规格）
├── platforms/                           # 共享的芯片资料库（只读）
│   ├── stm32f103zet6/
│   │   ├── datasheets/                  # PDF 手册（人类阅读）
│   │   │   ├── STM32F103ZET6.pdf        #   数据手册
│   │   │   └── STM32F10x_Reference_Manual.pdf  # 参考手册
│   │   ├── svd/                         # CMSIS-SVD（机器可读，S3 优先数据源）
│   │   │   └── STM32F103xx.svd
│   │   ├── sdk/                         # 厂商 SDK（机器可读）
│   │   │   ├── cmsis/                  #   core_cm3.h / stm32f10x.h / system_stm32f10x.*
│   │   │   ├── startup/                #   启动文件（arm / gcc_ride7）
│   │   │   └── std_periph_lib/         #   标准外设库（inc/ + src/）
│   │   ├── schematics/                  # 参考原理图（WarShip SCH.pdf）
│   │   ├── linker_scripts/              # 链接脚本（待填充）
│   │   └── templates/                   # 工程模板（待填充）
│   ├── gd32f205vet6/
│   │   ├── datasheets/                  # GD32F205xx 数据手册 + GD32F20x 用户手册
│   │   ├── svd/                         # GD32F20x.svd
│   │   ├── sdk/                         # 厂商 SDK（机器可读）
│   │   │   ├── cmsis/                  #   gd32f20x.h / system_gd32f20x.h / core_*.h
│   │   │   └── std_periph_lib/         #   标准外设库（inc/ + src/）
│   │   ├── schematics/                  # 参考原理图（待填充）
│   │   ├── linker_scripts/              # 链接脚本（待填充）
│   │   └── templates/                   # 工程模板（待填充）
│   └── ft61f14x/                        # 8 位 MCU 平台（FT61F14X）
│       └── datasheets/                  # 中文数据手册（单手册模式：无 SVD/SDK，S3 以 PDF 为唯一数据源）
├── examples/                            # 验证/演示工程
│   ├── stm32f103zet6/
│   │   ├── config.json                  # 本示例的配置（项目层，含 build_target）
│   │   ├── docs/                        # 输入文档（功能/软件规格书，S2/S5b 读取）
│   │   ├── references/                  # 参考材料（demos/ sdk/ existing_project/）
│   │   ├── schematic/                   # 本示例的原理图
│   │   ├── outputs/                     # 跨工程产物（合并固件等）
│   │   ├── App/                         # 目标工程（build_target 缺省 App）
│   │   │   ├── state.json               # 运行时状态（每目标独立）
│   │   │   ├── MDK-ARM/                 # IDE 工程目录（IAR 为 IAR/，8 位为 Project/）
│   │   │   ├── Core/                    # 内核相关（main.c 等，用户/CubeMX）
│   │   │   ├── Drivers/                 # BSP（S5a+S5b）/ Port（S5b 接口+S5c 实现）/ CMSIS / HAL
│   │   │   ├── App/                     # 应用逻辑（S5b 输出）
│   │   │   └── outputs/                 # 本目标输出（网表/Excel/硬件事实/s5a/s5b 等）
│   │   └── BootLoader/                  # 目标工程（结构同 App）
│   ├── gd32f205vet6/                    # 结构同上（App + BootLoader 双工程）
│   └── ft61f14x/                        # 8 位 MCU 示例（arch_family=mcu8 / flat：无 Core/CMSIS/HAL_Driver，
│                                        #   IDE 目录为 Project/，S5a SFR 直访生成 board_init 等 5 模块）
├── projects/                           # 实际项目工作区
│   └── my_project/                     # 结构同 examples（App/ + BootLoader/ 双工程）
├── schemas/                             # 全局契约（config/state schema）
├── workflows/                           # 工作流定义
├── docs/                                # 文档（skill 模板等）
├── config.json                          # 全局配置（工具路径等）
└── README.md
```

## 配置加载规则（config.json 分层机制）

配置分两层：**根目录全局配置** + **项目/示例配置**，Skill 启动时按以下顺序加载：

```
第 1 步：加载根目录 config.json       → 得到全局默认值
第 2 步：加载项目/示例 config.json    → 覆盖或补充
第 3 步：合并结果                      → 最终生效的配置
```

合并规则：深合并（dict 递归合并），项目配置的值覆盖全局配置的同名项，全局独有的字段保留。

### 根目录 config.json（全局默认）

```json
{
  "tool_paths": {
    "keil": "C:/Keil_v5/UV4/UV4.exe",
    "jflash": "C:/Program Files/SEGGER/JLink/JFlash.exe",
    "python": "C:/Python314/python.exe"
  },
  "platforms_root": "platforms/",
  "skills_root": "skills/"
}
```

### 项目 config.json（项目特有，如 examples/stm32f103zet6/config.json）

```json
{
  "platform": "stm32f103zet6",
  "project": {
    "build_target": "App",
    "architecture": "layered",
    "rtos": "none",
    "power": { "enabled": false }
  },
  "schematic_path": "schematic/STM32F103ZET6_MinSystem/STM32F103ZET6_MinSystem.SchDoc",
  "datasheet_path": "platforms/stm32f103zet6/datasheets/STM32F103ZET6.pdf",
  "datasheet_secondary_path": "platforms/stm32f103zet6/datasheets/STM32F10x_Reference_Manual.pdf",
  "svd_path": "platforms/stm32f103zet6/svd/STM32F103xx.svd",
  "sdk_header_path": "platforms/stm32f103zet6/sdk/cmsis/stm32f10x.h",
  "stdperiph_lib_path": "platforms/stm32f103zet6/sdk/std_periph_lib",
  "output_dir": "outputs/"
}
```

### 工程选项（project 段）

以下工程级开关决定目标工程与 S5 代码生成形态：`build_target` 由 S1–S5 全部 Skill
消费（决定 `state.json` / 源码目录 / `outputs` / IDE 工程目录所在的目标工程根）；
其余由 S5a 读取校验后写入 `state.json`，S5b/S5c 消费（S5c 校验三者一致性）。
枚举值填错时，任一 Skill 加载配置即报错并列出合法值——
契约统一由根目录 `schemas/config.schema.json` 定义，字段名拼错也会被拦截。

| 配置项 | 枚举值 | 缺省 | 作用 |
|-------|--------|------|------|
| `project.build_target` | `App` / `BootLoader` | `App` | 目标工程：S1–S5 的 `state.json` / 源码目录 / `outputs` / IDE 工程目录均位于 `<项目根>/<build_target>/`（`docs/` / `references/` 共享于项目根） |
| `project.arch_family` | `cortex_m` / `mcu8` | `cortex_m` | MCU 家族：`mcu8` 触发 8 位形态——S3 单手册提取（无 SVD/SDK，PDF 为唯一数据源）、S5a SFR 直访生成、目录骨架无 Core/CMSIS/HAL_Driver、IDE 目录为 `Project/` |
| `project.architecture` | `flat` / `layered` / `full` | `layered`（32 位惯例） | 软件分层程度：`flat` 单层平铺（8 位 MCU，`board_init.c`，无 Port 层）；`layered` HAL+APP（`hal_init.c`）；`full` HAL+Port+APP 全分层 |
| `project.rtos` | `none` / `FreeRTOS` / `RT-Thread` / `Zephyr` | `none`（裸机） | RTOS 类型：决定 S5b 的 main.c 骨架（裸机 `while(1)` / RTOS `osal_kernel_start`）与 S5c 的 OSAL 移植层；`flat` + RTOS 仍生成 `osal_port.h`（OSAL 与 Port 正交） |
| `project.power.enabled` | `true` / `false` | `false` | 是否启用低功耗设计：S5a 据此生成低功耗初始化代码（策略见 S5a `references/low_power_strategies.md`） |

> 更换 MCU 时：`layered` / `full` 的 S5b 产物（APP/Port）保持不变，仅重跑 S5a/S5c；
> `flat` 架构因产物与平台耦合，需重跑 S5b。

### 相对路径解析规则

| 路径字段 | 解析基准 |
|---------|---------|
| `schematic_path`、`src` 等项目文件路径 | 项目 config.json 所在目录（项目根） |
| `output_dir` | 目标工程根（`<项目根>/<build_target>/`，缺省 `App`） |
| 以 `platforms/` 开头的路径（如 `datasheet_path`、`svd_path`） | 根目录（embed-ai-assist/） |

### 运行时状态

每个目标工程有自己的 `state.json`（位于 `<项目根>/<build_target>/`），各 Skill 只读写自己负责的字段；
数据量大的产物（网表等）写入目标工程 `outputs/`，state.json 只存指针与统计（指针/数据分离）。

## Skill 清单（规划）

| 编号 | Skill | 层 | 职责 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| S1 | schematic-reader | 数据输入 | 解析原理图，输出通用网表 | 已实现 |
| S2 | spec-reader | 数据输入 | 功能规格书（md/docx/pdf）→ 结构化需求 spec.json（三段式，S5b 消费） | 已实现 |
| S3 | datasheet-extractor | 数据输入 | 提取 MCU 手册引脚/寄存器/时钟信息 | 已实现 |
| S4 | circuit-investigator | 验证 | 电路覆盖门禁，输出硬件事实 | 已实现 |
| S5a | hardware-initializer | 核心处理 | 平台相关硬件初始化 + 硬件能力清单 | 已实现 |
| S5b | port-contract-and-app | 核心处理 | Port 契约 + APP/协议/驱动（平台无关；S2/S4 均可选降级） | 已实现 |
| S5c | port-implementer | 核心处理 | Port 实现（依赖 S5a 能力清单 + S5b 契约） | 规划中 |
| S6 | firmware-merger | 编译构建 | 固件合并（Boot + App、多核、OTA 包等） | 规划中 |
| S7 | build | 编译构建 | 调用工具链编译工程 | 规划中 |
| S8 | unit-test | 编译构建 | 单元测试 | 规划中 |
| S9 | flash | 烧录部署 | 烧录固件（J-Link/OpenOCD 等） | 规划中 |
| S10 | serial-monitor | 调试监控 | 串口日志采集 | 规划中 |
| S11 | log-analyzer | 调试监控 | 日志分析，闭环反馈 | 规划中 |
| S12 | workflow-runner | 编排 | 工作流执行器 | 规划中 |

新 Skill 按 `docs/skill_template.md` 模板生成。

## S5 三分架构（Ports & Adapters）

S5 拆分为三个 Skill，将平台无关的应用逻辑与平台相关的硬件实现分离：

| Skill | 名称 | 平台相关性 | 依赖 |
| :--- | :--- | :--- | :--- |
| S5a | hardware-initializer | 平台相关 | S3 + S4（不依赖 S5b，可并行） |
| S5b | port-contract-and-app | 平台无关 | S2 / S4（均可选降级；不依赖 S5a，可并行） |
| S5c | port-implementer | 平台相关 | S5a + S5b（需两者都完成） |

- **代码/数据分离**：S5a 生成的初始化代码放 `Drivers/BSP/{Src,Inc}`（布局由
  `docs/PROJECT_LAYOUT.md` 解析），硬件能力清单等数据产物放
  `outputs/s5a/`，state.json 只存指针与统计。
- **hardware_capabilities.json**：S5a 输出、S5c 实现 Port 的唯一硬件依据
  （S5c 禁止直接读 S3/S4 数据）。
- **架构分级**：`flat`（8 位 MCU，无 Port 层，`board_init.c`）/ `layered`
  （32 位默认，`hal_init.c`）/ `full`（完整分层）。
- **执行模型（S5a）**：rule 准备 → Agent 生成 → rule 校验。prepare.py 分析硬件事实
  输出任务书 `outputs/s5a/generation_brief.md`（并按 `docs/PROJECT_LAYOUT.md` 创建
  目录骨架），Agent 按任务书亲自编写 `Drivers/BSP/{Src,Inc}` 代码
  （平台 API 从标准外设库头文件确认），validate.py 校验产物并输出能力清单。
  新增硬件平台无需编写适配脚本（数值约束收敛在 `analysis.py` 的 `PLATFORM_INFO`）。

## 环境要求

- Python 3.10+（本机 `C:/Python314/python.exe`，路径配置在根 config.json 的 `tool_paths.python`）
- 依赖：`pip install altium-monkey jsonschema openpyxl pdfplumber pypdf`（.docx 规格书另需 `python-docx`）

## 芯片资料获取（PDF 不入库）

`platforms/` 下的 SVD 与 SDK 头文件随仓库提供，克隆后即可跑通 S1 → S5a 全链路。
**芯片手册 PDF（数据手册/参考手册）因厂商版权不纳入版本库**（见 `.gitignore`）：

- `STM32F10x_Reference_Manual.pdf`、`GD32F20x 用户手册.pdf` 需自行从 ST / GD 官网下载，
  放回 `platforms/<平台>/datasheets/` 原路径
- 这两个 PDF 对应 config 的 `datasheet_secondary_path`（S3 的兜底数据源）；
  SVD 存在时 S3 优先走 SVD，PDF 缺失不影响主流程
- 8 位平台 `ft61f14x` 为单手册模式（无 SVD/SDK），数据手册 PDF 即 S3 唯一数据源，
  需自行获取后放回 `platforms/ft61f14x/datasheets/`，缺失则 S3 无法提取

## 快速开始

```bash
# 1. 运行 schematic-reader 解析示例工程原理图
python skills/schematic-reader/scripts/parse.py --config examples/stm32f103zet6/config.json

# 2. 运行 datasheet-extractor 提取芯片数据（数据源优先级：SVD > SDK 头文件 > 参考手册 PDF）
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json

# 3. 运行 circuit-investigator 交叉验证（S1 网表 × S3 芯片规格 → 硬件事实报告）
python skills/circuit-investigator/scripts/investigate.py --config examples/stm32f103zet6/config.json

# 3b. 运行 S2 规格书阅读器（可选，与 S3/S4/S5a 可并行；为 S5b 提供 spec 驱动数据。
#     需在项目 config 配置 project.inputs.functional_spec，已配置示例见 gd32f205vet6）
python skills/spec-reader/scripts/prepare.py --config examples/gd32f205vet6/config.json
#    → Agent 按 outputs/s2/generation_brief.md 生成 spec.json + spec_trace.json + uncovered.json
python skills/spec-reader/scripts/validate.py --config examples/gd32f205vet6/config.json
#    （产物：App/state.json 的 spec 字段 + App/outputs/s2/；S5b 消费须后于 S2 收口）

# 4. 运行 S5a prepare（S4 硬件事实 + S3 芯片数据 → Agent 任务书）
python skills/hardware-initializer/scripts/prepare.py --config examples/stm32f103zet6/config.json
#    → Agent 按 outputs/s5a/generation_brief.md 编写 Drivers/BSP/{Src,Inc} 代码（见 S5a SKILL.md）
# 5. 运行 S5a validate（校验 Agent 产物 + 能力清单 + IDE 清单）
python skills/hardware-initializer/scripts/validate.py --config examples/stm32f103zet6/config.json

# 6. 运行 S5b prepare（S2/S4 均可选；输出 Agent 任务书）
python skills/port-contract-and-app/scripts/prepare.py --config examples/stm32f103zet6/config.json
#    → Agent 按 outputs/s5b/generation_brief.md：模块清单确认 → docs/flow/ 流程图
#      → 用户审核 approved → flow_differ 判定 full/incremental/skip → 生成代码
#    （中间校验 flow_validator / flow_differ / diff_range_checker，见 S5b SKILL.md）

# 7. 运行 S5b 终验（产物校验 + state 收口 + IDE 待添加清单，随后 Agent 修复重跑）
python skills/port-contract-and-app/scripts/validate.py --config examples/stm32f103zet6/config.json

# 8. 查看结果
#    examples/stm32f103zet6/App/state.json   -> circuit 字段（S1/S4）/ chip 字段（S3）/ s5a 字段（S5a）/ s5b 字段（S5b）
#    examples/stm32f103zet6/App/outputs/      -> circuit_netlist.json + pin_table.xlsx
#                                                + circuit_facts.json + circuit_facts.xlsx
#    examples/stm32f103zet6/App/outputs/chip_info/ -> pins/registers/clock_tree/peripherals
#                                                 .json + pin_table/register_map.xlsx
#    examples/stm32f103zet6/App/Drivers/BSP/{Src,Inc}/ -> clock/gpio/nvic/uart/... _init.c/h + hal_init.c/h
#    examples/stm32f103zet6/App/outputs/s5a/  -> hardware_capabilities.json（S5c 的唯一硬件依据）
#    examples/stm32f103zet6/App/outputs/s5b/  -> generation_brief.md + port_interface_manifest.json
#                                                + traceability.json + flow_index.json
#    examples/stm32f103zet6/App/docs/flow/    -> Mermaid 流程图（含 .history/ 版本基线）
#    examples/stm32f103zet6/App/App/Src/      -> app_*.c/h + protocol_*.c/h + main.c（S5b 应用层）
```

> 按步骤 1–7 顺序执行即可生成上述结果文件（`examples/` 的产物按 `.gitignore`
> 现行策略随仓库提供，可对照参考；S5b 步骤 6 需 Agent 参与流程图审核，见 S5b SKILL.md）。

## 工作流（workflows/）

`workflows/stm32_full_flow.json` 是**全流程目标态的设计示例**，包含尚未实现的
skill（S2 / S5b / S5c / S6–S12，见 Skill 清单状态列）。待 S12 workflow-runner
实现后由其解析编排执行；当前请按「快速开始」手动逐个执行已实现的 skill。

## 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
