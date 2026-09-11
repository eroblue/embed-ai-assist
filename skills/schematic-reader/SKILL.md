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

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `project.schematic_path` | `config.json` | string | 是 | 原理图文件路径（`.SchDoc` / `.kicad_sch`） |
| `project.workspace` | `config.json` | string | 是 | 输出目录（`outputs/`、`state.json` 相对此目录） |
| `eda_tool` | 可选参数 | string | 否 | `altium` \| `kicad`，默认 `altium`，也可从 `config.json` 的 `eda.tool` 读取 |

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
| `error` | string \| null | 失败/部分失败时的错误信息 |

输出契约见 [schemas/output.schema.json](schemas/output.schema.json)。

### 写入 outputs/

`outputs/circuit_netlist.json`：完整网表数据（通用格式，可能几 MB），结构：

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

## 执行步骤

1. 从 `config.json` 读取 `project.schematic_path` 与 `project.workspace`，检查原理图文件是否存在
2. 根据扩展名和 `eda_tool` 参数选择适配器（`adapters/altium_adapter.py` / `adapters/kicad_adapter.py`）
3. 调用适配器解析原理图，得到 EDA 无关的通用网表数据
4. 将网表写入 `outputs/circuit_netlist.json`
5. 将路径和统计信息写入 `state.json` 的 `circuit` 字段
6. 用 `jsonschema` 依据 `schemas/output.schema.json` 校验输出后，向 stdout 打印结果摘要

## 使用方法

```bash
# 默认（读 config.json，eda_tool 取 config.json 的 eda.tool 或 altium）
python skills/schematic-reader/scripts/parse.py --config config.json

# 显式指定 EDA 工具
python skills/schematic-reader/scripts/parse.py --config config.json --eda-tool kicad

# 命令行覆盖原理图路径（不修改 config.json）
python skills/schematic-reader/scripts/parse.py --config config.json --schematic path/to/demo.SchDoc
```

参数说明：

- `--config`：`config.json` 路径，默认脚本工作目录下的 `config.json`
- `--eda-tool`：`altium` | `kicad`，覆盖 `config.json` 中 `eda.tool`
- `--schematic`：覆盖 `config.json` 中 `project.schematic_path`（仅本次生效，不回写）
- `--workspace`：覆盖 `config.json` 中 `project.workspace`（仅本次生效，不回写）

## 依赖

- Python 3.10+（本机使用 `C:\Python314\python.exe`）
- `altium-monkey`（Altium 适配器，解析 `.SchDoc` OLE 复合文档）
- `jsonschema`（输出契约校验）

安装：`python -m pip install altium-monkey jsonschema`

## 禁止事项

- **不要修改 `config.json`**（只读）
- **不要读写 `state.json` 中其他 Skill 的字段**（只写 `circuit` 字段）
- 不要在解析失败时留下半成品 `circuit_netlist.json`（失败时删除并写 `parse_status: failed`）
