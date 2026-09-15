# S3 datasheet-extractor Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个AI Agent Skill。

## 基本信息

- **Skill名称**：datasheet-extractor
- **Skill用途**：读取MCU数据手册（Datasheet）和参考手册（Reference Manual）PDF，提取引脚定义、寄存器映射、时钟树、外设信息，输出结构化芯片数据与寄存器映射Excel。
- **触发时机**：当需要为指定MCU生成初始化代码、需要准确的寄存器地址和配置位时触发。

## 输入

- 从config.json读取platform（芯片型号，如stm32f103zet6）
- 从config.json读取project.datasheet_path（数据手册PDF路径）
- 从config.json读取project.datasheet_secondary_path（参考手册PDF路径，可选）
- 从config.json读取project.workspace（输出目录）
- 可选参数extract_scope：pins | registers | clocks | peripherals | all（默认all）

## 输出

### 写入 state.json（仅chip字段）

| 字段 | 说明 |
|------|------|
| chip.datasheet_path | 数据手册源文件路径 |
| chip.datasheet_secondary_path | 参考手册源文件路径（如提供） |
| chip.mcu_family | MCU系列（如STM32F1） |
| chip.package | 封装类型（如LQFP144） |
| chip.pin_count | 引脚总数 |
| chip.registers_path | 寄存器映射JSON文件路径 |
| chip.pin_table_path | 引脚定义JSON文件路径 |
| chip.clock_tree_path | 时钟树JSON文件路径 |
| chip.extract_status | success / partial / failed |
| chip.extract_scope | 实际提取的范围 |
| chip.error | 失败时的错误信息（成功时为null） |

### 写入 outputs/

| 产物 | 内容说明 |
|------|----------|
| outputs/chip_info/pins.json | 完整引脚定义（数据量大，结构由schemas/pins.schema.json约束）<br>每条包含：引脚号、引脚名、类型（电源/IO/复用）、复用功能列表、电气特性 |
| outputs/chip_info/registers.json | 完整寄存器映射（数据量大，结构由schemas/registers.schema.json约束）<br>每条包含：外设名、寄存器名、地址偏移、位域定义、读写权限、复位值 |
| outputs/chip_info/clock_tree.json | 时钟树结构（结构由schemas/clock_tree.schema.json约束）<br>包含：时钟源（HSE/HSI/LSE/LSI）、PLL配置、总线分频（AHB/APB1/APB2）、各外设时钟使能位 |
| outputs/chip_info/peripherals.json | 外设清单（结构由schemas/peripherals.schema.json约束）<br>包含：外设名、基地址、中断向量号、引脚复用映射 |
| outputs/chip_info/register_map.xlsx | 寄存器映射Excel（便于人工查阅）<br>列：外设、寄存器名、地址、位域、功能说明、读写权限<br>规则：按外设分组，每个外设一个sheet；位域用位宽和偏移标注 |
| outputs/chip_info/pin_table.xlsx | 引脚定义Excel（与S1的引脚表格式互补）<br>列：引脚号、引脚名、类型、复用功能、电气特性<br>规则：电源引脚=蓝底、复用功能引脚=黄底、普通IO=白底 |

### 指针/数据分离规则（所有skill统一）

数据量大的产物（引脚定义、寄存器映射、时钟树）真实数据放outputs/chip_info/，
结构由schemas/中对应的`<产物名>.schema.json`约束并在写入前校验；
state.json中chip字段只存**指针（产物路径）与统计计数**，不存数据本体。

## Skill目录结构（标准结构，所有skill统一）

```
datasheet-extractor/
├── SKILL.md                     ← 技能说明（给Agent看）
├── schemas/
│   ├── input.schema.json        ← 输入契约
│   ├── output.schema.json       ← 输出契约（state.json的chip字段，仅指针+统计）
│   ├── pins.schema.json         ← 引脚定义数据契约（outputs/chip_info/pins.json）
│   ├── registers.schema.json    ← 寄存器映射数据契约（outputs/chip_info/registers.json）
│   ├── clock_tree.schema.json   ← 时钟树数据契约（outputs/chip_info/clock_tree.json）
│   └── peripherals.schema.json  ← 外设清单数据契约（outputs/chip_info/peripherals.json）
├── scripts/                     ← 可执行脚本
│   ├── extract.py               ← 主入口（读配置 → 分发 → 提取 → 校验 → 更新state）
│   ├── adapters/                ← 按芯片厂商分发的适配器
│   │   ├── stm32_adapter.py     ← STM32系列提取适配器
│   │   ├── gd32_adapter.py      ← GD32系列提取适配器
│   │   └── fm32_adapter.py      ← 辉芒微系列提取适配器（后续扩展）
│   └── excel_export.py          ← 生成引脚表/寄存器映射Excel
├── references/                  ← 参考文档
│   ├── pdf_extract_strategy.md  ← PDF提取策略说明（如何定位章节、如何解析表格）
│   └── excel_format.md          ← Excel输出格式规范
└── assets/                      ← 资源文件
    ├── register_map_example.xlsx ← 寄存器映射Excel示例
    └── pin_table_example.xlsx   ← 引脚定义Excel示例
```

## 执行步骤

1. 从config.json读取platform、datasheet_path、datasheet_secondary_path，
   检查PDF文件是否存在
2. 根据platform选择适配器（stm32_adapter.py / gd32_adapter.py / fm32_adapter.py）
3. 调用适配器提取数据：
   - a. 从数据手册提取引脚定义、封装信息
   - b. 从参考手册提取寄存器映射、时钟树、外设清单
   - c. 合并引脚定义与复用功能映射
4. 分别用pins.schema.json、registers.schema.json、clock_tree.schema.json、
   peripherals.schema.json校验四类数据
5. 校验通过后，分别写入outputs/chip_info/下的对应JSON文件
6. 调用excel_export.py生成register_map.xlsx和pin_table.xlsx
7. 将路径和统计信息写入state.json的chip字段

## 依赖

- Python 3.10+
- pdfplumber库（PDF文本/表格提取）
- PyPDF2库（PDF分页）
- jsonschema库（契约校验）
- openpyxl库（Excel生成）

## 禁止事项

- 不要修改config.json，不要读写其他Skill的字段
- 不要修改outputs/中非本Skill产出的文件
- 提取失败时不要留半成品文件，应删除并写failed状态

## 补充说明

### PDF提取的"尽力而为"原则

- PDF提取是"尽力而为"，无法保证100%准确。对于无法识别的章节或表格，
  应写partial状态并在chip.error中记录未提取的部分，供下游S4/S5判断是否可用
- 如果只提供数据手册未提供参考手册，寄存器映射可能不完整，
  此时extract_scope退化为pins，状态写partial
- 提取结果应与S1输出的网表交叉验证（该工作在S4 circuit-investigator中完成），
  本Skill只负责从手册提取原始数据，不做与原理图的比对

### 适配器选择规则

主入口 extract.py 从 config.json 读取 platform 字段，
用前缀匹配选择适配器（stm32* → stm32_adapter，gd32* → gd32_adapter，
fm32* → fm32_adapter）。前缀映射表维护在主入口中，新增厂商时只需加一行。

### 提取范围

提取芯片手册中的**全部引脚、全部寄存器、全部外设、完整时钟树**，
不做"只提取已用到部分"的裁剪。理由是：

- S4 circuit-investigator 需要完整引脚列表来检查未连接引脚；
- S5a code-generator 可能用到任何外设；
- 芯片数据可跨项目复用，一次提取多次使用；
- 数据量可控（144 脚芯片的完整 JSON 约 10–50 KB）。

### 与 S1 的分工

S1 提取"项目相关"的连接关系，S3 提取"芯片相关"的完整规格。
