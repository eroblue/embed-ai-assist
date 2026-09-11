# EmbedAIAssist

嵌入式软件开发 AI 辅助开发框架：从原理图、MCU 数据手册、功能规格书，到代码生成、编译、
固件合并、烧录、串口测试的全流程 Skill 编排。

## 目录结构

```
EmbedAIAssist/
├── config.json                          全局配置（路径、工具链选择等，Skill 只读）
├── state.json                           运行时状态（各 Skill 读写自己负责的字段）
├── schemas/
│   ├── state.schema.json                全局 state.json 契约
│   └── config.schema.json               全局 config.json 契约
├── workflows/
│   └── stm32_full_flow.json             用户配置的工作流（示例）
├── outputs/                             大块数据存放区
│   └── circuit_netlist.json             完整网表（schematic-reader 生成）
├── skills/
│   └── schematic-reader/                S1 原理图解析
│       ├── SKILL.md                     技能说明（给 Agent 看）
│       ├── schemas/
│       │   ├── input.schema.json        输入契约
│       │   └── output.schema.json       输出契约（通用电路网表）
│       └── scripts/
│           ├── parse.py                 主入口，根据 eda_tool 分发
│           └── adapters/
│               ├── altium_adapter.py    Altium 解析适配器
│               └── kicad_adapter.py     KiCad 解析适配器
└── README.md                            项目说明
```

## Skill 清单（规划）

| 编号 | Skill | 层 | 职责 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| S1 | schematic-reader | 数据输入 | 解析原理图，输出通用网表 | 已实现 |
| S2 | spec-reader | 数据输入 | 解析功能规格书，输出需求摘要 | 规划中 |
| S3 | datasheet-extractor | 数据输入 | 提取 MCU 手册引脚/寄存器/时钟信息 | 规划中 |
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

## 环境要求

- Python 3.10+（推荐使用本机 `C:\Python314\python.exe`）
- 依赖：`pip install altium-monkey jsonschema`

## 快速开始

```bash
# 1. 在 config.json 中配置 project.schematic_path（原理图路径）

# 2. 运行 schematic-reader
python skills/schematic-reader/scripts/parse.py --config config.json

# 3. 查看结果
#    state.json        -> circuit 字段（网表路径与统计）
#    outputs/circuit_netlist.json -> 完整网表
```
