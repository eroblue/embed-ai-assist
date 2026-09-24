# S1 schematic-reader Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个AI Agent Skill。

## 基本信息

- **Skill名称**：schematic-reader
- **Skill用途**：读取 Altium Designer / KiCad 原理图源文件（.SchDoc / .PrjPcb / .kicad_sch）或 PDF 原理图，提取元件、网络、引脚信息，输出通用网表与引脚配置 Excel。
- **触发时机**：当用户需要分析硬件原理图时触发。

## 输入

- 从config.json读取`project.schematic_path`（原理图文件路径）
- 从config.json读取`project.workspace`（输出目录）
- 可选参数`eda_tool`：`altium` | `kicad` | `pdf`（默认按文件扩展名自动识别）

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
| circuit.source_format | schdoc / prjpcb / kicad_sch / pdf（可选） |
| circuit.confidence | 整体置信度，PDF 输入时为 0~1；源文件输入时为 1.0（可选） |
| circuit.low_confidence_count | 低置信度连接数量，PDF 输入时有效（可选） |
| circuit.review_path | 人工核对清单路径，PDF 输入时有效（可选） |

### 写入 outputs/

| 产物 | 内容说明 |
|------|----------|
| outputs/circuit_netlist.json | 完整网表数据（数据量大，结构由schemas/netlist.schema.json约束） |
| outputs/pin_table.xlsx | 引脚配置Excel（参考"原理图网络表.png"样式）<br>列：引脚编号、引脚名称、网络名、作用、外设/模式<br>规则：前三列来自网表；作用、外设/模式按关键词自动推断（电源/SWD/BOOT/复位/晶振/悬空），无法识别的留空待人工/AI补充；行颜色编码：电源=蓝、特殊功能=黄、悬空=灰、普通=白 |
| outputs/pdf_review.md | 人工核对清单（仅 PDF 输入时生成，列出低置信度的连接，供工程师核对） |

### 指针/数据分离规则（所有skill统一）

数据量大的产物（网表、芯片手册提取结果、日志等）真实数据放outputs/，
结构由schemas/中对应的`<产物名>.schema.json`约束并在写入前校验；
state.json中对应字段只存**指针（产物路径）与统计计数**，不存数据本体。

## Skill目录结构（标准结构，所有skill统一）

```
schematic-reader/
├── SKILL.md                     ← 技能说明（给Agent看）
├── schemas/
│   ├── input.schema.json        ← 输入契约（本次增量扩展）
│   ├── output.schema.json       ← 输出契约（state.json的circuit字段，本次增量扩展）
│   └── netlist.schema.json      ← 网表数据契约（本次增量扩展）
├── scripts/                     ← 可执行脚本
│   ├── parse.py                 ← 主入口
│   └── adapters/                ← 按EDA/工具类型分发的适配器
│       ├── altium_adapter.py    ← .SchDoc / .PrjPcb 解析
│       ├── kicad_adapter.py     ← .kicad_sch 解析
│       └── pdf_adapter.py       ← .pdf 解析（新增）
├── references/                  ← 参考文档（格式规范、领域知识）
│   ├── excel_format.md          ← 引脚表Excel格式规范
│   └── pdf_extraction_guide.md  ← PDF 提取原理与置信度说明（新增）
└── assets/                      ← 资源文件（示例输出、样例数据）
    ├── pin_table_example.xlsx   ← Excel输出示例
    └── pdf_review_example.md    ← PDF 核对清单示例（新增）
```

## 执行步骤

1. 从config.json读取原理图路径，检查文件是否存在
2. 根据文件扩展名或`eda_tool`参数选择适配器：
   - `.SchDoc` / `.PrjPcb` → `altium_adapter.py`
   - `.kicad_sch` → `kicad_adapter.py`
   - `.pdf` → `pdf_adapter.py`
3. 调用适配器解析原理图，得到通用网表数据
4. 用netlist.schema.json校验网表结构后写入outputs/circuit_netlist.json
5. 调用excel_export.py生成引脚配置Excel到outputs/pin_table.xlsx
6. **（PDF 专用）** 若使用 pdf_adapter，同时生成 outputs/pdf_review.md，列出低置信度连接
7. 将路径和统计信息写入state.json

## 依赖

- Python 3.10+
- altium-monkey库
- jsonschema库（契约校验）
- openpyxl库（Excel生成）
- pdfplumber 或 PyMuPDF（PDF 解析，PDF 输入时必需）
- 可选：openai/anthropic SDK（PDF 低置信度连接辅助校验）

## 禁止事项

- 不要修改config.json，不要读写其他Skill的字段
- PDF Adapter 不得声称100%精度，必须输出每个连接的置信度
- 置信度 < 0.7 的连接必须写入pdf_review.md，不得静默丢弃

## 补充说明

### PDF 原理图支持

#### 为什么支持 PDF

实际工程中，很多原理图只有 PDF 版本：

- 开发板厂商（正点原子、野火、安富莱等）通常只提供 PDF 原理图
- 老项目的源文件可能已丢失，只留 PDF
- 客户交付的图纸常为 PDF

**不支持 PDF，S1 会丢掉一大块实际场景。**

#### PDF 与源文件的精度差异

| 格式 | 精度 | 说明 |
|---|---|---|
| SchDoc / PrjPcb / kicad_sch | 100% | 元件、连线、网络标号都是结构化对象 |
| PDF | 85~95% | 从矢量图形 + 文字推断，需要置信度标注 |

**PDF 提取不保证 100% 精确，这是技术本质决定的，不是实现问题。** 应对方式：输出置信度 + 人工审核。

#### PDF Adapter 的技术路线

1. **文字提取**：用 pdfplumber / PyMuPDF 提取所有文本（元件位号、引脚名、网络名、注释）。
2. **图形元素提取**：提取线条、矩形、圆形，识别元件框和连线。
3. **元件识别**：用矩形框 + 内部文字识别元件。
4. **连接推断**：
   - 线条与元件引脚的交点 → 连接关系
   - Net Label 与线条的连接 → 网络归属
   - 引脚名与物理引脚号的映射（需要配合 S3）
5. **置信度评估**：对每个连接给出置信度。
6. **LLM 辅助校验**（可选）：对低置信度连接，用 LLM 辅助判断。

#### 置信度分级与处理

| 置信度 | 处理 |
|---|---|
| ≥ 0.95 | 高可信，直接使用 |
| 0.7 ~ 0.95 | 中可信，S4 阶段重点核对 |
| < 0.7 | 低可信，写入 pdf_review.md，人工审核 |

#### 网表中的置信度字段

PDF 输入时，netlist.json 中每条连接增加 `confidence` 和 `method` 字段：

```json
{
  "pin": "PA9",
  "net": "USART1_TX",
  "target": "U14.Pin15",
  "confidence": 0.85,
  "method": "line_intersection",
  "note": "线与引脚框的交点明确"
}
```

#### 人工核对清单

S1 输出 `outputs/pdf_review.md`，列出所有低置信度连接：

```markdown
## 需要人工核对的连接

| 引脚 | 推断网络 | 推断目标 | 置信度 | 建议 |
|---|---|---|---|---|
| PD0 | OSC_IN | Y2 | 0.62 | 请人工确认是否连接到 8MHz 晶振 |
| PB6 | I2C1_SCL | U11 | 0.75 | 请确认是否连接到 EEPROM |
```

工程师花 10 分钟核对 20 个低置信度连接，比手动画原理图快 100 倍。

### Schema 与模板要求

S1 的 Schema 保持原有结构，**本次加入 PDF 支持时采用向后兼容的增量扩展**：

- 所有新增字段均为**可选**，源文件输入时行为与原来完全一致。
- Schema 版本号从 `1.0` 升到 `1.1`（minor 版本，向后兼容）。
- S4、S5 等下游 Skill 读取 S1 产物时无需改动。

具体扩展如下：

#### input.schema.json

新增可选字段：

```json
{
  "schematic_format": {
    "type": "string",
    "enum": ["schdoc", "prjpcb", "kicad_sch", "pdf"],
    "description": "可选，显式指定输入格式；未指定时按文件扩展名自动识别"
  }
}
```

#### output.schema.json（state.json 的 circuit 字段）

新增可选字段：

```json
{
  "source_format": {
    "type": "string",
    "enum": ["schdoc", "prjpcb", "kicad_sch", "pdf"]
  },
  "confidence": {
    "type": "number",
    "minimum": 0,
    "maximum": 1
  },
  "low_confidence_count": {
    "type": "integer",
    "minimum": 0
  },
  "review_path": {
    "type": ["string", "null"]
  }
}
```

源文件输入时这些字段不出现或为 null，校验器不强制要求。

#### netlist.schema.json

每条连接新增可选字段：

```json
{
  "confidence": {
    "type": "number",
    "minimum": 0,
    "maximum": 1
  },
  "method": {
    "type": "string",
    "enum": ["line_intersection", "net_label", "pin_name_match", "llm_assisted"]
  },
  "note": {
    "type": "string"
  }
}
```

源文件输入时不出现，PDF 输入时才出现。

**原有工作流（SchDoc / KiCad）不受影响，PDF 输入时多出来的信息才有这些字段。**

- 输入输出JSON Schema格式参考项目根目录文件：input.schema.json、output.schema.json，
  在原有基础上做增量扩展，**不重新定义**。
- skill通用模板已提取到 `EmbedAIAssist/docs/skill_template.md`，后续skill清单中的
  14个skill都按该模板生成（标准目录结构：SKILL.md + schemas/ + scripts/ +
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

示例——项目 examples/stm32f103zet6-min-system/config.json（PDF 原理图）：

```json
{
  "platform": "stm32f103zet6",
  "schematic_path": "schematic/STM32F103ZET6_MinSystem.pdf",
  "schematic_format": "pdf",
  "datasheet_path": "platforms/stm32f103zet6/datasheets/STM32F103ZET6.pdf",
  "output_dir": "outputs/"
}
```

同一示例也可以配置为 Altium 源文件：

```json
{
  "platform": "stm32f103zet6",
  "schematic_path": "schematic/STM32F103ZET6_MinSystem.PrjPcb",
  "datasheet_path": "platforms/stm32f103zet6/datasheets/STM32F103ZET6.pdf",
  "output_dir": "outputs/"
}
```

**通过修改 `schematic_path` 与可选的 `schematic_format` 字段即可切换输入格式，无需新建示例工程。**

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
│       │   ├── STM32F103ZET6_MinSystem.PrjPcb    # Altium 源文件（可选）
│       │   ├── STM32F103ZET6_MinSystem.SchDoc    # Altium 源文件（可选）
│       │   └── STM32F103ZET6_MinSystem.pdf       # PDF 版本（可选）
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

### PDF 提取的降级策略

| 场景 | 处理 |
|---|---|
| pdfplumber / PyMuPDF 未安装 | 警告并降级到提示用户手动提取 |
| 文字层缺失（扫描件） | 提示用户：需要 OCR，当前不支持 |
| 多页原理图 | 逐页提取，跨页网络通过 Net Label 关联 |
| 置信度整体偏低（< 0.7） | 输出警告，要求人工全面核对 |