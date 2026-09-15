---
name: "datasheet-extractor"
description: "按数据源优先级 SVD > SDK 头文件 > 参考手册 PDF 提取引脚定义、寄存器映射、时钟树、外设清单到 outputs/chip_info/ 并生成 Excel。当需要芯片引脚复用信息、寄存器地址与配置位（生成初始化代码、核对引脚用途）时触发。"
---

# datasheet-extractor 芯片手册提取

## 用途

从芯片资料提取结构化数据（JSON + Excel）：引脚定义（datasheet PDF）、
寄存器映射 / 时钟树配置要素 / 外设清单 / 中断向量。

**数据源优先级：SVD > SDK 头文件 > 参考手册 PDF**（机器可读优先，人类文档兜底）：

| 优先级 | 数据源 | 位置 | 用途 | 质量 |
|--------|--------|------|------|------|
| 1 | CMSIS-SVD（`svd_path`） | `platforms/<chip>/svd/` | 寄存器/位域/中断/复位值/时钟树 | 权威完整（STM32F103 实测 449 寄存器全量，含复位值与完整位域） |
| 2 | 厂商 SDK 设备头文件（`sdk_header_path`） | `platforms/<chip>/sdk/cmsis/` | 寄存器/地址/中断/时钟树 | 权威（编译器直接使用），厂商必提供、覆盖无 SVD 的芯片；位域/复位值视头文件而定（F1 位域集中于 RCC）；实例级展开（STM32F103 实测 1314 寄存器/72 外设） |
| 3 | 参考手册 PDF（`datasheet_secondary_path`） | `platforms/<chip>/datasheets/` | 同上（兜底） | 尽力而为（启发式页面选择，~200 寄存器） |
| — | 数据手册 PDF（`datasheet_path`） | `platforms/<chip>/datasheets/` | 引脚定义（SVD/头文件均不含物理引脚表） | 跨页表格解析 |

**整体流程层级：S3，数据输入层**。

- 上游依赖：`platforms/<chip>/` 下的 svd / sdk / datasheets（由 config.json 的
  `svd_path` / `sdk_header_path` / `datasheet_path` / `datasheet_secondary_path` 指定）
- 下游消费：
  - **S4 circuit-investigator**：用 pins.json 的完整引脚表与 S1 网表交叉验证
    （未连接引脚检查、复用功能确认）
  - **S5 code-generator**：用 registers.json / clock_tree.json / peripherals.json
    生成初始化代码（寄存器地址、时钟使能位、分频配置）
- 与 S1 的分工：S1 提取**项目相关**的连接关系，S3 提取**芯片相关**的完整规格

## 目录结构

```
datasheet-extractor/
├── SKILL.md                     ← 本文件
├── schemas/
│   ├── input.schema.json        ← 输入契约（config 输入字段）
│   ├── output.schema.json       ← 输出契约（state.json 的 chip 字段，仅指针+统计）
│   ├── pins.schema.json         ← 引脚定义数据契约（outputs/chip_info/pins.json）
│   ├── registers.schema.json    ← 寄存器映射数据契约
│   ├── clock_tree.schema.json    ← 时钟树数据契约
│   └── peripherals.schema.json  ← 外设清单数据契约
├── scripts/
│   ├── extract.py               ← 主入口
│   ├── svd_source.py            ← CMSIS-SVD 解析（数据源优先级 1，厂商通用）
│   ├── sdk_source.py            ← SDK 设备头文件解析（数据源优先级 2，厂商通用）
│   ├── excel_export.py         ← pin_table.xlsx / register_map.xlsx 生成
│   └── adapters/
│       ├── stm32_adapter.py     ← STM32 系列（datasheet 引脚 + SVD/SDK/RM 数据源融合）
│       ├── gd32_adapter.py      ← GD32 系列（占位，待接入手册样本）
│       └── fm32_adapter.py      ← 辉芒微 FM32（占位，后续扩展）
├── references/
│   ├── pdf_extract_strategy.md ← PDF 提取策略（启发式页面选择/表格解析/partial 判定）
│   └── excel_format.md          ← Excel 输出格式规范
└── assets/
    ├── pin_table_example.xlsx   ← 引脚定义 Excel 示例
    └── register_map_example.xlsx ← 寄存器映射 Excel 示例
```

## 输入

| 参数 | 来源 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| platform | config.json（项目层） | string | 是 | 芯片平台名，前缀决定适配器：stm32\* / gd32\* / fm32\* |
| datasheet_path | config.json（项目层） | string | 是 | 数据手册 PDF（引脚定义来源）；`platforms/` 开头相对根目录，否则相对项目目录 |
| svd_path | config.json（项目层） | string | 否（推荐） | CMSIS-SVD 文件；**数据源优先级 1**，寄存器/位域/中断/复位值/时钟树从此提取 |
| sdk_header_path | config.json（项目层） | string | 否 | 厂商 SDK 设备头文件（如 stm32f10x.h）；**数据源优先级 2**（无 SVD 时使用，覆盖无 SVD 的芯片） |
| datasheet_secondary_path | config.json（项目层） | string | 否 | 参考手册 PDF；**数据源优先级 3**（无 SVD 且无 SDK 时解析 PDF） |
| workspace | config.json（项目层） | string | 是 | 输出目录（项目目录，state.json 与 outputs/ 所在） |
| extract_scope | config.json 或 --scope | enum | 否 | pins / registers / clocks / peripherals / all（默认 all） |

命令行覆盖参数（仅本次生效，不回写 config.json）：
`--platform` / `--datasheet` / `--secondary` / `--svd` / `--sdk` / `--scope`。

## 输出

### 写入 state.json（仅 chip 字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| datasheet_path | string | 数据手册绝对路径 |
| svd_path | string\|null | CMSIS-SVD 绝对路径（未提供为 null；数据源优先级 1） |
| sdk_header_path | string\|null | 厂商设备头文件绝对路径（未提供为 null；数据源优先级 2） |
| datasheet_secondary_path | string\|null | 参考手册绝对路径（未提供为 null；数据源优先级 3） |
| mcu_family | string | MCU 系列（如 STM32F1） |
| package | string\|null | 封装类型（如 LQFP144） |
| pin_count | integer | 封装引脚总数 |
| pin_defined_count | integer | 已提取定义的引脚数 |
| register_count | integer | 已提取寄存器条目数 |
| peripheral_count | integer | 已提取外设条目数 |
| pins_path / registers_path / clock_tree_path / peripherals_path | string\|null | 产物指针（相对工作区） |
| pin_table_excel_path / register_map_excel_path | string\|null | Excel 产物指针 |
| extract_status | string | success / partial / failed |
| extract_scope | string | 实际成功提取的范围（如 pins 或 all） |
| error | string\|null | 失败/降级原因（完整成功为 null） |
| updated_at | string | ISO 8601 时间戳 |

### 写入 outputs/（指针/数据分离：数据本体在 outputs/chip_info/）

| 文件 | 内容 | 契约 |
|------|------|------|
| outputs/chip_info/pins.json | 完整引脚定义：引脚号/名称/类型（POWER\|IO\|BOOT\|NRST…）/复用功能（默认+重映射）/电气特性 | pins.schema.json |
| outputs/chip_info/registers.json | 寄存器映射：外设/寄存器名/地址/偏移/位域/读写权限/复位值 | registers.schema.json |
| outputs/chip_info/clock_tree.json | 时钟配置要素：时钟源/PLL/总线分频位段/外设时钟使能位 | clock_tree.schema.json |
| outputs/chip_info/peripherals.json | 外设清单：名称/基地址/结束地址/总线/中断向量 | peripherals.schema.json |
| outputs/chip_info/pin_table.xlsx | 引脚定义 Excel（单表平铺；电源=蓝底、复用=黄底） | references/excel_format.md |
| outputs/chip_info/register_map.xlsx | 寄存器映射 Excel（每外设一个 sheet） | references/excel_format.md |

## 执行步骤

1. 分层加载配置（根 config.json → 项目 config.json → 深合并），读取
   platform / datasheet_path / svd_path / sdk_header_path / datasheet_secondary_path / extract_scope
2. 检查文件存在（datasheet 不存在则写 failed 状态退出；SVD/SDK 不存在仅告警忽略）
3. 按 platform 前缀选择适配器（stm32 / gd32 / fm32）
4. 调用适配器提取（数据源优先级：SVD > SDK 头文件 > 参考手册 PDF）：
   - 引脚定义：datasheet PDF（定位 "pin definitions" 章节，封装列头竖排文本反转识别）
   - 寄存器/外设/中断/时钟树：
     - 优先级 1 SVD（`svd_source.py` 一次 XML 解析，含 derivedFrom 继承展开；
       时钟树从 RCC 寄存器位域推导）
     - 优先级 2 SDK 头文件（`sdk_source.py` 解析 CMSIS 设备头：
       基地址宏表达式递归求值、结构体成员 C 对齐累加偏移、
       `#define XXX ((XXX_TypeDef *) XXX_BASE)` 实例展开、
       位域掩码反推 bit 位置并过滤枚举值/位分量）
     - 优先级 3 参考手册 PDF 兜底——**启发式页面选择**两阶段扫描
       （阶段 1 pypdf 读书签定位寄存器/向量表/存储映射章节页码，阶段 2 只深扫目标页）
5. 逐产物用对应 schema 校验，全部通过才写入 outputs/chip_info/（不留半成品）
6. 生成 pin_table.xlsx 与 register_map.xlsx（openpyxl 缺失时降级跳过）
7. 将指针与统计写入项目 state.json 的 chip 字段

## 使用方法

```bash
# 标准用法（项目 config.json 已配置 platform / datasheet_path / svd_path）
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json

# 仅提取引脚定义
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json --scope pins

# 临时指定 SVD / SDK 头文件 / 参考手册（不回写 config.json）
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json \
  --svd platforms/stm32f103zet6/svd/STM32F103xx.svd
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json \
  --sdk platforms/stm32f103zet6/sdk/cmsis/stm32f10x.h
python skills/datasheet-extractor/scripts/extract.py --config examples/stm32f103zet6/config.json \
  --secondary platforms/stm32f103zet6/datasheets/STM32F10x_Reference_Manual.pdf
```

退出码：0=成功（含 partial）、1=失败（无任何产物）、2=配置错误。

## 依赖

- Python 3.10+
- `pdfplumber`（PDF 文本/表格提取）
- `pypdf`（参考手册兜底路径的书签解析，启发式页面选择）
- `jsonschema`（契约校验）
- `openpyxl`（Excel 生成；缺失时降级跳过 Excel，主流程不受影响）

```bash
pip install pdfplumber pypdf jsonschema openpyxl
```

## 禁止事项

- 不修改 config.json；命令行覆盖参数仅本次生效
- 只读写 state.json 的 `chip` 字段，不触碰其他 Skill 字段
- 不修改 outputs/ 中非本 Skill 产出的文件
- 提取失败不留半成品文件（校验通过才写入，失败产物丢弃）
- 本 Skill 只从手册提取原始数据，**不做与原理图的比对**（交叉验证是 S4 的职责）

## 国产 MCU / 8 位机兼容策略

国产 MCU（特别是 8 位机：STC、辉芒微、中颖、松翰等）的手册与 ST 差异较大，
本 Skill 通过**适配器吸收差异、契约放宽兜底**来兼容：

| 差异点 | 兼容方式 |
|--------|---------|
| **有 SVD 文件**（GD32、沁恒、华大等多数国产 ARM 核厂商提供 CMSIS-SVD） | 首选：`svd_path` 指向 SVD 文件，`svd_source.py` 通用解析（CMSIS 标准），寄存器数据权威完整，无需针对厂商手册做 PDF 解析 |
| **无 SVD 但有 SDK 头文件**（厂商必然提供，8 位机也有 sfr/寄存器定义头文件） | 次选：`sdk_header_path` 指向设备头文件，`sdk_source.py` 解析 CMSIS 风格定义（基地址宏/结构体/实例宏/IRQn/位域掩码）；8 位机 sfr 风格待接入样本后扩展 |
| **单本手册**（datasheet 兼作参考手册，寄存器直接写在 datasheet 里） | `datasheet_secondary_path` 本就可选；适配器自行决定提取来源——STM32 适配器在无 RM 时降级 partial，8 位机适配器可直接从 datasheet 提取全部内容（单手册模式），此时产物 `source.reference_manual` 为 null |
| **SFR 寄存器模型**（无外设基地址/偏移，单字节地址 + 位寻址） | `peripherals.base_address` 允许 null；`registers.address` 的 hex 模式兼容 SFR 地址（如 0x80），`offset` 可空 |
| **固定引脚复用**（无 AFIO remap） | `pins.alternate_functions_remap` 留空数组即可 |
| **极简时钟**（无 PLL/APB 总线） | `clock_tree` 各数组允许空数组，按实际手册内容填充 |
| **中文手册**（章节标题为"引脚定义""寄存器描述"） | 提取关键词支持中英双语（见 references/pdf_extract_strategy.md） |

**新增厂商流程**（与统一规则一致）：

1. `scripts/adapters/` 下新增 `<vendor>_adapter.py`，按该厂商手册风格实现
   `extract(datasheet, secondary, scope, svd)` 统一接口
2. 在 `adapters/__init__.py` 的 `ADAPTER_PREFIXES` 注册前缀（一行）
3. 按需补充 `references/pdf_extract_strategy.md` 中该厂商的章节定位关键词
4. 用真实手册样本联调后移除 NotImplementedError 占位

> 厂商有 SVD 文件时（GD32 等多数 ARM 核厂商提供），直接复用
> `svd_source.py`（CMSIS 标准解析）即可获得完整寄存器数据，无需 PDF 解析。

> 8 位机的编译/烧录差异（Keil C51、ISP 烧录等）不属于本 Skill 职责，
> 由后续 build/flash 相关 Skill 的适配器处理。

## 已知限制

- PDF 兜底提取为尽力而为：启发式页面选择按书签定位章节（约深扫一半页数），
  无法解析的章节记入 `chip.error` 并置 partial，供下游 S4/S5 判断数据可用性
- SVD 与 SDK 头文件均不含引脚定义与频率信息（HSE 范围等文档知识）：
  引脚来自 datasheet PDF；时钟源频率使用平台默认值
- SDK 头文件的位域与复位值覆盖视厂商而定（STM32F1 的 stm32f10x.h 位域
  集中于 RCC 等，多数外设寄存器位域为空；复位值普遍缺失）——
  SVD 优先级高于 SDK 即因此故
- STM32 手册分离（datasheet 无寄存器章节）：无 SVD/SDK 且只提供 datasheet 时
  寄存器/时钟树/外设不提取，scope 退化为 pins，状态 partial；
  8 位机单手册模式见上方兼容策略
- GD32 / FM32 适配器为占位（NotImplementedError → failed），待接入手册样本后实现
