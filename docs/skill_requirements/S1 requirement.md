# S1 schematic-reader Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个AI Agent Skill。

## 基本信息

- **Skill名称**：schematic-reader
- **Skill用途**：读取Altium Designer / KiCad原理图文件（.SchDoc / .kicad_sch），提取元件、网络、引脚信息，输出通用网表与引脚配置Excel。
- **触发时机**：当用户需要分析硬件原理图时触发。

## 输入

- 从config.json读取project.schematic_path（原理图文件路径）
- 从config.json读取project.workspace（输出目录）
- 可选参数eda_tool：altium | kicad（默认altium）

## 输出

### 写入 state.json（仅circuit字段）

| 字段 | 说明 |
|------|------|
| circuit.netlist_path | 网表JSON文件路径 |
| circuit.component_count | 元件数量 |
| circuit.net_count | 网络数量 |
| circuit.pin_count | 引脚数量 |
| circuit.parse_status | success / partial / failed |
| circuit.excel_path | 引脚配置Excel文件路径 |

### 写入 outputs/

| 产物 | 内容说明 |
|------|----------|
| outputs/circuit_netlist.json | 完整网表数据（数据量大，结构由schemas/netlist.schema.json约束） |
| outputs/pin_table.xlsx | 引脚配置Excel（参考"原理图网络表.png"样式）<br>列：引脚编号、引脚名称、网络名、作用、外设/模式<br>规则：前三列来自网表；作用、外设/模式按关键词自动推断（电源/SWD/BOOT/复位/晶振/悬空），无法识别的留空待人工/AI补充；行颜色编码：电源=蓝、特殊功能=黄、悬空=灰、普通=白 |

### 指针/数据分离规则（所有skill统一）

数据量大的产物（网表、芯片手册提取结果、日志等）真实数据放outputs/，
结构由schemas/中对应的`<产物名>.schema.json`约束并在写入前校验；
state.json中对应字段只存**指针（产物路径）与统计计数**，不存数据本体。

## Skill目录结构（标准结构，所有skill统一）

```
schematic-reader/
├── SKILL.md                     ← 技能说明（给Agent看）
├── schemas/
│   ├── input.schema.json        ← 输入契约
│   ├── output.schema.json       ← 输出契约（state.json的circuit字段，仅指针+统计）
│   └── netlist.schema.json      ← 网表数据契约（outputs/circuit_netlist.json完整结构）
├── scripts/                     ← 可执行脚本
│   ├── parse.py                 ← 主入口
│   └── adapters/                ← 按EDA/工具类型分发的适配器
├── references/                  ← 参考文档（格式规范、领域知识）
│   └── excel_format.md          ← 引脚表Excel格式规范
└── assets/                      ← 资源文件（示例输出、样例数据）
    └── pin_table_example.xlsx   ← Excel输出示例
```

## 执行步骤

1. 从config.json读取原理图路径，检查文件是否存在
2. 根据eda_tool选择适配器（altium_adapter.py / kicad_adapter.py）
3. 调用适配器解析原理图，得到通用网表数据
4. 用netlist.schema.json校验网表结构后写入outputs/circuit_netlist.json
5. 调用excel_export.py生成引脚配置Excel到outputs/pin_table.xlsx
6. 将路径和统计信息写入state.json

## 依赖

- Python 3.10+
- altium-monkey库
- jsonschema库（契约校验）
- openpyxl库（Excel生成）

## 禁止事项

- 不要修改config.json，不要读写其他Skill的字段

## 补充说明

### Schema 与模板要求

- 输入输出JSON Schema格式参考项目根目录文件：input.schema.json、output.schema.json，
  重新定义合理的JSON Schema，并写入到对应的skill目录里面
- skill通用模板已提取到 `EmbedAIAssist/docs/skill_template.md`，后续skill清单中的
  13个skill都按该模板生成（标准目录结构：SKILL.md + schemas/ + scripts/ +
  references/ + assets/）

### 配置分层加载机制

根目录的config.json和examples/projects目录下的config.json采用分层加载机制：

1. 第 1 步：加载根目录 config.json → 得到全局默认值
2. 第 2 步：加载项目/示例 config.json → 覆盖或补充
3. 第 3 步：合并结果 → 最终生效的配置

示例——根目录 config.json（全局默认）：

```json
{
  "tool_paths": {
    "keil": "C:/Keil_v5/UV4/UV4.exe",
    "jflash": "C:/Program Files/SEGGER/JLink/JFlash.exe",
    "python": "C:/Python311/python.exe"
  },
  "platforms_root": "platforms/",
  "skills_root": "skills/"
}
```

示例——项目 examples/stm32f103zet6-min-system/config.json（项目特有）：

```json
{
  "platform": "stm32f103zet6",
  "schematic_path": "schematic/STM32F103ZET6_MinSystem.PrjPcb",
  "datasheet_path": "platforms/stm32f103zet6/datasheets/STM32F103ZET6.pdf",
  "output_dir": "outputs/"
}
```

### 项目目录结构（S1 落地时的约束）

```
embed-ai-assist/
├── skills/                              # 所有 Skill
├── platforms/                           # 共享的芯片资料库（只读）
│   └── stm32f103zet6/
│       ├── datasheets/
│       ├── schematics/
│       ├── std_periph_lib/
│       ├── cmsis/
│       ├── linker_scripts/
│       └── templates/
├── examples/                            # 验证/演示工程
│   └── stm32f103zet6-min-system/
│       ├── config.json                  # 本示例的配置
│       ├── state.json                   # 本示例的运行时状态
│       ├── outputs/                     # 本示例的输出
│       ├── schematic/                   # 本示例的原理图
│       │   ├── STM32F103ZET6_MinSystem.PrjPcb
│       │   └── STM32F103ZET6_MinSystem.SchDoc
│       └── src/                         # 本示例的源码
├── projects/                            # 实际项目工作区
│   └── my_project/
│       ├── config.json
│       ├── state.json
│       ├── outputs/
│       ├── schematic/
│       └── src/
├── config.json                          # 全局配置（工具路径等）
└── README.md
```
