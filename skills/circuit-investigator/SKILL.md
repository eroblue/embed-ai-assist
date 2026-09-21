---
name: "circuit-investigator"
description: "读取 S1 网表与 S3 芯片规格，交叉核对引脚连接与芯片定义一致性，推断每个引脚的功能角色，生成硬件事实报告（circuit_facts.json/xlsx）。在 S1 和 S3 都执行完成后，需要确认硬件事实、检查引脚冲突时触发。"
---

# circuit-investigator 电路侦查

## 用途

读取 S1 输出的网表数据和 S3 输出的芯片规格数据，交叉核对引脚连接与芯片定义
是否一致，推断每个引脚的功能角色，生成硬件事实报告（circuit.facts），
供 S5 生成代码使用。

**整体流程层级：S4，验证层（质量门禁）**。

- 上游依赖：S1 schematic-reader（`circuit.*` 字段 + `outputs/circuit_netlist.json`）、
  S3 datasheet-extractor（`chip.*` 字段 + `outputs/chip_info/pins.json`）
- 下游消费：**S5 code-generator** 用 `circuit_facts.json` 的引脚角色/外设模式
  生成初始化代码；S4 是质量门禁——确认硬件事实无误后 S5 才开始生成代码
- 分工：S1 提取"外部连接关系"，S3 提取"芯片内部规格"，S4 将两者交叉核对

## 目录结构

```
circuit-investigator/
├── SKILL.md                     ← 本文件
├── schemas/
│   ├── input.schema.json        ← 输入契约（S1/S3 就绪性检查）
│   ├── output.schema.json       ← 输出契约（state.json 的 circuit.facts 字段）
│   └── circuit_facts.schema.json ← 硬件事实报告数据契约（outputs/circuit_facts.json）
├── scripts/
│   ├── investigate.py           ← 主入口（读配置 → 加载 S1/S3 → 交叉验证 → 更新state）
│   ├── pin_inferrer.py          ← 引脚功能推断（rule 模式：5 级优先级）
│   ├── conflict_checker.py      ← 冲突检测（引脚一致性/电源/时钟/复用冲突/晶振频率）
│   └── excel_export.py          ← 硬件事实报告 Excel（GD32 示例风格）
├── references/
│   ├── inference_rules.md       ← 引脚功能推断规则说明
│   └── excel_format.md          ← Excel 输出格式规范
└── assets/
    └── circuit_facts_example.xlsx ← 硬件事实报告 Excel 示例
```

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| circuit.* | state.json（S1 写入） | object | 是 | `netlist_path` / `parse_status` |
| chip.* | state.json（S3 写入） | object | 是 | `pins_path` / `extract_status` |
| platform | config.json（项目层） | string | 是 | 芯片平台名，用于识别主控元件（value 匹配） |
| workspace | config.json（项目层） | string | 是 | 目标工程根 = 项目根 / `project.build_target`（缺省 App），state.json 与 outputs/ 所在；docs/references 共享于项目根 |
| verify_scope | config.json 或 --scope | enum | 否 | pins / power / clocks / peripherals / all（默认 all） |
| inference_mode | config.json 或 --inference-mode | enum | 否 | rule / ai（默认 rule；ai 未接入自动降级 rule） |

命令行覆盖参数（仅本次生效，不回写 config.json）：`--scope` / `--inference-mode` / `--workspace`。

## 输出

### 写入 state.json（仅 circuit.facts 字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| circuit.facts.facts_path | string | 硬件事实报告 JSON 路径（相对 workspace） |
| circuit.facts.facts_xlsx_path | string\|null | Excel 路径（openpyxl 缺失时为 null） |
| circuit.facts.verified_pin_count | integer | 已验证的引脚数量 |
| circuit.facts.conflict_count | integer | 冲突数量（severity=error） |
| circuit.facts.warning_count | integer | 警告数量 |
| circuit.facts.nc_pin_count | integer | 未连接引脚数量（NC） |
| circuit.facts.verify_status | string | success / partial / failed |
| circuit.facts.verify_scope | string | 实际验证的范围 |
| circuit.facts.inference_mode | string | 实际使用的推断模式 |
| circuit.facts.error | string\|null | 失败时的错误信息（成功时为 null） |

状态判定：S1/S3 partial 继承 partial；存在 error 级冲突 → partial（数据可用但有问题）；
仅本流程自身失败才 failed。

### 写入 outputs/

| 产物 | 内容说明 |
|------|----------|
| outputs/circuit_facts.json | 完整硬件事实报告（结构由 circuit_facts.schema.json 约束）<br>包含：每个引脚的最终角色（role/peripheral/config/status/note）、电源轨、时钟配置（HSE/LSE 频率来自晶振元件）、冲突列表、警告列表、NC 引脚 |
| outputs/circuit_facts.xlsx | 硬件事实报告 Excel（格式见 references/excel_format.md）<br>6 列：引脚号、引脚名、网络、作用、外设/模式、状态<br>按外设类别分色（电源/晶振/调试=黄、数字输入=绿、ADC=橙、输出/UART=浅蓝、SPI/I2C=紫、PWM=粉红、FSMC=灰、NC=无填充）+ 图例 sheet |

指针/数据分离：报告本体写 outputs/，state.json 只存指针与统计。

## 执行步骤

1. 分层加载配置（根 config.json → 项目 config.json → 深合并，只读）
2. 读 state.json 的 circuit（S1）/ chip（S3）字段：
   - 任一 failed → 写 `verify_status: failed` 并终止
   - partial → 继续执行，最终状态继承 partial
3. 加载网表（`outputs/circuit_netlist.json`）与芯片引脚定义（`outputs/chip_info/pins.json`），
   按 platform（value 匹配）识别主控元件
4. 交叉核对（按 verify_scope）：
   - a. 引脚号在芯片定义中存在、引脚名一致
   - b. 复用一致性（网络名暗示外设 vs 引脚 AF 表，如 UART3_TX 接错脚）
   - c. 电源引脚全部连接（VDD/VSS 空=error；VBAT/VDDA 空=warning）
   - d. 时钟引脚完整（HSE/LSE 悬空=warning）
   - e. 未连接引脚（NC 列表，info 级）
5. 推断每个引脚功能角色（5 级优先级，见 references/inference_rules.md）；
   推断不出的标记 warning，不中断主流程
6. 组装 circuit_facts → circuit_facts.schema.json 校验通过后写入
   outputs/circuit_facts.json
7. 生成 outputs/circuit_facts.xlsx（openpyxl 缺失时降级跳过）
8. 将指针和统计写入 state.json 的 circuit.facts 字段

## 使用方法

```bash
# 前置：S1、S3 已在同一项目执行
python skills/circuit-investigator/scripts/investigate.py --config examples/stm32f103zet6/config.json

# 只验证引脚连接
python skills/circuit-investigator/scripts/investigate.py --config examples/stm32f103zet6/config.json --scope pins
```

## 依赖

- Python 3.10+
- jsonschema（契约校验）
- openpyxl（Excel 生成，缺失时降级跳过）

## 禁止事项

- 不要修改 config.json，不要读写其他 Skill 的字段
- 不要修改 S1/S3 产出的文件（circuit_netlist.json、chip_info/*.json）
- 不要修改 outputs/ 中非本 Skill 产出的文件
- 推断失败时不要留半成品文件，应删除并写 failed 状态
- 冲突检测到 error 时，不要自动修改网表或芯片数据，只记录到冲突列表
