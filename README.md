# embed-ai-assist

嵌入式软件开发 AI 辅助开发框架：从原理图、MCU 数据手册、功能规格书，到代码生成、编译、
固件合并、烧录、串口测试的全流程 Skill 编排。

## 目录结构

- `skills/`：所有 AI Skill 的定义（每个 Skill 是一个独立目录）
- `platforms/`：芯片平台资料库（数据手册、标准库、CMSIS 等，只读共享）
- `examples/`：验证和演示工程（每个示例自包含）
- `projects/`：实际项目工作区（每个项目自包含）
- `config.json`：全局配置（工具路径等）

每个示例和项目都有独立的 `config.json`、`state.json` 和 `outputs/`，
通过分层配置机制与根目录的全局配置协同工作。详见「配置加载规则」。

### 详细目录树

```
embed-ai-assist/
├── skills/                              # 所有 Skill
│   ├── schematic-reader/                # S1 原理图解析（参考实现）
│   └── datasheet-extractor/             # S3 芯片手册提取（SVD > SDK 头文件 > PDF）
├── platforms/                           # 共享的芯片资料库（只读）
│   └── stm32f103zet6/
│       ├── datasheets/                  # PDF 手册（人类阅读）
│       │   ├── STM32F103ZET6.pdf        #   数据手册
│       │   └── STM32F10x_Reference_Manual.pdf  # 参考手册
│       ├── svd/                         # CMSIS-SVD（机器可读，S3 优先数据源）
│       │   └── STM32F103xx.svd
│       ├── sdk/                         # 厂商 SDK（机器可读）
│       │   ├── cmsis/                  #   core_cm3.h / stm32f10x.h / system_stm32f10x.*
│       │   ├── startup/                #   启动文件（arm / gcc_ride7）
│       │   └── std_periph_lib/         #   标准外设库（inc/ + src/）
│       ├── schematics/                  # 参考原理图（WarShip SCH.pdf）
│       ├── linker_scripts/              # 链接脚本（待填充）
│       └── templates/                   # 工程模板（待填充）
├── examples/                            # 验证/演示工程
│   └── stm32f103zet6/
│       ├── config.json                  # 本示例的配置（项目层）
│       ├── state.json                   # 本示例的运行时状态
│       ├── outputs/                     # 本示例的输出（网表/Excel 等）
│       ├── schematic/                   # 本示例的原理图
│       └── src/                         # 本示例的源码
├── projects/                           # 实际项目工作区
│   └── my_project/
│       ├── config.json
│       ├── state.json
│       ├── outputs/
│       ├── schematic/
│       └── src/
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
  "schematic_path": "schematic/STM32F103ZET6_MinSystem/STM32F103ZET6_MinSystem.SchDoc",
  "datasheet_path": "platforms/stm32f103zet6/datasheets/STM32F103ZET6.pdf",
  "datasheet_secondary_path": "platforms/stm32f103zet6/datasheets/STM32F10x_Reference_Manual.pdf",
  "svd_path": "platforms/stm32f103zet6/svd/STM32F103xx.svd",
  "sdk_header_path": "platforms/stm32f103zet6/sdk/cmsis/stm32f10x.h",
  "stdperiph_lib_path": "platforms/stm32f103zet6/sdk/std_periph_lib",
  "output_dir": "outputs/"
}
```

### 相对路径解析规则

| 路径字段 | 解析基准 |
|---------|---------|
| `schematic_path`、`output_dir`、`src` 等项目文件路径 | 项目 config.json 所在目录 |
| 以 `platforms/` 开头的路径（如 `datasheet_path`、`svd_path`） | 根目录（embed-ai-assist/） |

### 运行时状态

每个项目/示例有自己的 `state.json`（与 config.json 同目录），各 Skill 只读写自己负责的字段；
数据量大的产物（网表等）写入项目 `outputs/`，state.json 只存指针与统计（指针/数据分离）。

## Skill 清单（规划）

| 编号 | Skill | 层 | 职责 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| S1 | schematic-reader | 数据输入 | 解析原理图，输出通用网表 | 已实现 |
| S2 | spec-reader | 数据输入 | 解析功能规格书，输出需求摘要 | 规划中 |
| S3 | datasheet-extractor | 数据输入 | 提取 MCU 手册引脚/寄存器/时钟信息 | 已实现 |
| S4 | circuit-investigator | 验证 | 电路覆盖门禁，输出硬件事实 | 规划中 |
| S5 | code-generator | 核心处理 | 生成 APP/BootLoader 代码 | 规划中 |
| S6 | code-merger | 核心处理 | 源码合并 / 固件合并 | 规划中 |
| S7 | build | 编译构建 | 调用工具链编译工程 | 规划中 |
| S8 | code-merger | 编译构建 | APP+Boot 固件合并 | 规划中 |
| S9 | unit-test | 编译构建 | 单元测试 | 规划中 |
| S10 | flash | 烧录部署 | 烧录固件（J-Link/OpenOCD 等） | 规划中 |
| S11 | serial-monitor | 调试监控 | 串口日志采集 | 规划中 |
| S12 | log-analyzer | 调试监控 | 日志分析，闭环反馈 | 规划中 |
| S13 | workflow-runner | 编排 | 工作流执行器 | 规划中 |

新 Skill 按 `docs/skill_template.md` 模板生成。

## 环境要求

- Python 3.10+（本机 `C:/Python314/python.exe`，路径配置在根 config.json 的 `tool_paths.python`）
- 依赖：`pip install altium-monkey jsonschema openpyxl pdfplumber pypdf`

## 快速开始

```bash
# 1. 运行 schematic-reader 解析示例工程原理图
python skills/schematic-reader/scripts/parse.py --config examples/stm32f103zet6/config.json

# 2. 运行 datasheet-extractor 提取芯片数据（数据源优先级：SVD > SDK 头文件 > 参考手册 PDF）
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json

# 3. 查看结果
#    examples/stm32f103zet6/state.json        -> circuit 字段（S1）/ chip 字段（S3）
#    examples/stm32f103zet6/outputs/          -> circuit_netlist.json + pin_table.xlsx
#    examples/stm32f103zet6/outputs/chip_info/ -> pins/registers/clock_tree/peripherals
#                                                 .json + pin_table/register_map.xlsx
```
