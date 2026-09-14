---
name: "schematic-reader"
description: "读取 Altium Designer / KiCad 原理图文件，提取元件、网络、引脚信息并输出通用网表。当用户需要分析硬件原理图、获取电路连接关系或为后续电路验证提供网表数据时触发。"
---

# schematic-reader 原理图解析

## 用途

读取 Altium Designer 原理图文件（`.SchDoc`）或 KiCad 原理图文件（`.kicad_sch`），
提取元件（Component）、网络（Net）、引脚（Pin）信息，转换为 EDA 无关的通用网表，
写入 `outputs/circuit_netlist.json`，并把路径和统计信息写入 `state.json` 的 `circuit` 字段。

在整体流程中属于 **数据输入层（S1）**，输出被 `circuit-investigator`（S4，电路覆盖门禁）依赖。

## 目录结构

```
schematic-reader/
├── SKILL.md                     ← 本文件（给 Agent 看）
├── schemas/
│   ├── input.schema.json        ← 输入契约
│   ├── output.schema.json       ← 输出契约（state.json 的 circuit 字段，仅指针+统计）
│   └── netlist.schema.json      ← 网表数据契约（outputs/circuit_netlist.json 完整结构）
├── scripts/
│   ├── parse.py                 ← 主入口：读配置 → 选适配器 → 生成网表/Excel → 更新 state
│   ├── excel_export.py          ← 引脚配置 Excel 导出（outputs/pin_table.xlsx）
│   └── adapters/
│       ├── altium_adapter.py    ← Altium 解析适配器
│       └── kicad_adapter.py     ← KiCad 解析适配器
├── references/                  ← 参考文档（格式规范、领域知识）
│   └── excel_format.md          ← 引脚表 Excel 格式规范
└── assets/                      ← 资源文件（示例输出、样例数据）
    └── pin_table_example.xlsx   ← Excel 输出示例
```

**指针/数据分离规则**：网表数据量大（可能几 MB），真实数据放 `outputs/circuit_netlist.json`
（结构由 netlist.schema.json 约束并在写入前校验），state.json 的 `circuit` 字段只存指针
（`netlist_path`）与统计计数，不存网表数据本体。

## 输入

配置采用**分层加载机制**（详见根目录 README.md）：

```
第 1 步：加载根目录 config.json       → 得到全局默认值（tool_paths 等）
第 2 步：加载项目/示例 config.json    → 覆盖或补充
第 3 步：深合并                        → 最终生效的配置
```

| 参数 | 来源 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `schematic_path` | 项目 `config.json` | string | 是 | 原理图路径（`.SchDoc` / `.kicad_sch`，相对项目目录） |
| `output_dir` | 项目 `config.json` | string | 否 | 输出目录（默认 `outputs/`，相对项目目录） |
| `eda_tool` | 项目 `config.json` 或命令行 | string | 否 | `altium` \| `kicad`；缺省按扩展名自动判断（默认 `altium`） |

工作区 = 项目 config.json 所在目录：`state.json` 与 `outputs/` 均位于该目录。

输入契约见 [schemas/input.schema.json](schemas/input.schema.json)。

## 输出

### 写入 state.json（仅 `circuit` 字段）

```json
{
  "circuit": {
    "netlist_path": "outputs/circuit_netlist.json",
    "component_count": 57,
    "net_count": 84,
    "pin_count": 312,
    "parse_status": "success",
    "eda_tool": "altium",
    "source_file": "E:\\project\\power.SchDoc",
    "excel_path": "outputs/pin_table.xlsx",
    "error": null
  }
}
```

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `netlist_path` | string | 网表 JSON 文件路径 |
| `component_count` | integer | 元件数量 |
| `net_count` | integer | 网络数量 |
| `pin_count` | integer | 引脚数量（网表中引脚连接总数） |
| `parse_status` | string | `success` / `partial` / `failed` |
| `eda_tool` | string | 实际使用的适配器 |
| `source_file` | string | 被解析的原理图绝对路径 |
| `excel_path` | string \| null | 引脚配置 Excel 路径（导出失败或跳过时为 null） |
| `error` | string \| null | 失败/部分失败时的错误信息 |

输出契约见 [schemas/output.schema.json](schemas/output.schema.json)。

### 写入 outputs/

`outputs/circuit_netlist.json`：完整网表数据（通用格式，可能几 MB），
结构契约见 [schemas/netlist.schema.json](schemas/netlist.schema.json)
（`embedaiassist.netlist.v1`），写入前经 jsonschema 校验：

```json
{
  "schema": "embedaiassist.netlist.v1",
  "generator": "schematic-reader",
  "eda_tool": "altium",
  "source_file": "E:\\project\\power.SchDoc",
  "parse_status": "success",
  "statistics": { "component_count": 57, "net_count": 84, "pin_count": 312 },
  "components": [
    {
      "designator": "U1",
      "value": "STM32F103C8T6",
      "footprint": "LQFP-48",
      "library_ref": "STM32F1",
      "description": "ARM Cortex-M3 MCU",
      "parameters": { "Manufacturer": "ST" },
      "pins": [
        { "pin": "1", "pin_name": "VBAT", "pin_type": "POWER", "net": "VBAT" },
        { "pin": "5", "pin_name": "PA0", "pin_type": "IO", "net": null }
      ]
    }
  ],
  "nets": [
    {
      "name": "VCC",
      "auto_named": false,
      "source_sheets": ["power.SchDoc"],
      "terminals": [
        { "designator": "U1", "pin": "1", "pin_name": "VCC", "pin_type": "POWER" }
      ]
    }
  ]
}
```

`outputs/pin_table.xlsx`：引脚配置 Excel（格式规范见 [references/excel_format.md](references/excel_format.md)），
每个元件一个工作表，列为 **引脚号 / 引脚名 / 网络名 / 作用 / 外设/模式**。

- 引脚号、引脚名、网络名来自网表
- 作用、外设/模式按关键词自动推断（电源、SWD、BOOT、复位、晶振、悬空），无法识别的留空待人工/AI 补充
- 行颜色编码：电源=蓝、特殊功能=黄、悬空=灰、普通=白

## 执行步骤

1. 分层加载配置（根目录全局 `config.json` → 项目 `config.json` → 深合并），读取 `schematic_path` 与 `output_dir`，检查原理图文件是否存在
2. 根据扩展名和 `eda_tool` 参数选择适配器（`adapters/altium_adapter.py` / `adapters/kicad_adapter.py`）
3. 调用适配器解析原理图，得到 EDA 无关的通用网表数据
4. 将网表写入 `outputs/circuit_netlist.json`
5. 调用 `scripts/excel_export.py` 生成引脚配置 Excel 到 `outputs/pin_table.xlsx`
6. 将路径和统计信息写入 `state.json` 的 `circuit` 字段
7. 用 `jsonschema` 依据 `schemas/output.schema.json` 校验输出后，向 stdout 打印结果摘要

## 使用方法

```bash
# 解析示例工程（自动分层合并：根 config.json + 示例 config.json）
python skills/schematic-reader/scripts/parse.py --config examples/stm32f103zet6-min-system/config.json

# 解析实际项目
python skills/schematic-reader/scripts/parse.py --config projects/my_project/config.json

# 显式指定 EDA 工具 / 命令行覆盖原理图路径（不修改 config.json）
python skills/schematic-reader/scripts/parse.py --config examples/stm32f103zet6-min-system/config.json --eda-tool kicad --schematic path/to/demo.kicad_sch
```

参数说明：

- `--config`：项目 `config.json` 路径（自动与根目录全局 `config.json` 分层合并），默认当前目录下的 `config.json`
- `--eda-tool`：`altium` | `kicad`，覆盖配置中的 `eda_tool`（仅本次生效）
- `--schematic`：覆盖配置中的 `schematic_path`（仅本次生效，不回写）
- `--workspace`：覆盖项目目录（默认 `--config` 所在目录，仅本次生效）

## 依赖

- Python 3.10+（本机使用 `C:\Python314\python.exe`）
- `altium-monkey`（Altium 适配器，解析 `.SchDoc` OLE 复合文档）
- `jsonschema`（输出契约校验）
- `openpyxl`（引脚配置 Excel 导出，缺失时跳过 Excel 输出，不影响网表主流程）

安装：`python -m pip install altium-monkey jsonschema openpyxl`

## 禁止事项

- **不要修改 `config.json`**（只读）
- **不要读写 `state.json` 中其他 Skill 的字段**（只写 `circuit` 字段）
- 不要在解析失败时留下半成品 `circuit_netlist.json`（失败时删除并写 `parse_status: failed`）
