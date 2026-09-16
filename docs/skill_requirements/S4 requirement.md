# S4 circuit-investigator Skill 需求

> 你现在是一位资深嵌入式开发专家，请帮我编写一个AI Agent Skill。

## 基本信息

- **Skill名称**：circuit-investigator
- **Skill用途**：读取 S1 输出的网表数据和 S3 输出的芯片规格数据，交叉核对引脚连接与芯片定义是否一致，推断每个引脚的功能角色，生成硬件事实报告（circuit.facts），供 S5 生成代码使用。
- **触发时机**：在 S1 和 S3 都执行完成后，需要确认硬件事实、检查引脚冲突、推断引脚功能角色时触发。

## 输入

- 从 state.json 读取 `circuit.*` 字段（S1 的输出）：
  - `circuit.netlist_path`：网表 JSON 文件路径
  - `circuit.component_count`：元件数量
  - `circuit.parse_status`：S1 解析状态
- 从 state.json 读取 `chip.*` 字段（S3 的输出）：
  - `chip.pin_table_path`：引脚定义 JSON 文件路径
  - `chip.registers_path`：寄存器映射 JSON 文件路径
  - `chip.clock_tree_path`：时钟树 JSON 文件路径
  - `chip.peripherals_path`：外设清单 JSON 文件路径
  - `chip.extract_status`：S3 提取状态
- 从 config.json 读取 `project.workspace`（输出目录）
- 可选参数 `verify_scope`：`pins` | `power` | `clocks` | `peripherals` | `all`（默认 `all`）
- 可选参数 `inference_mode`：`rule` | `ai`（默认 `rule`，即规则推断；`ai` 为调用 LLM 辅助推断）

## 输出

### 写入 state.json（仅 circuit.facts 字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| circuit.facts_path | string | 硬件事实报告 JSON 文件路径 |
| circuit.facts_xlsx_path | string | 硬件事实报告 Excel 文件路径（可选） |
| circuit.verified_pin_count | integer | 已验证的引脚数量 |
| circuit.conflict_count | integer | 检测到的冲突数量 |
| circuit.warning_count | integer | 警告数量 |
| circuit.nc_pin_count | integer | 未连接引脚数量（NC） |
| circuit.verify_status | string | success / partial / failed |
| circuit.verify_scope | string | 实际验证的范围 |
| circuit.inference_mode | string | 实际使用的推断模式 |
| circuit.error | string | 失败时的错误信息（成功时为 null） |

### 写入 outputs/

| 产物 | 内容说明 |
|------|----------|
| outputs/circuit_facts.json | 完整硬件事实报告（数据量大，结构由 schemas/circuit_facts.schema.json 约束）<br>包含：每个引脚的最终角色、外设配置、冲突列表、警告列表、电源轨、时钟配置 |
| outputs/circuit_facts.xlsx | 硬件事实报告 Excel（便于人工查阅，可选）<br>列：引脚号、引脚名、网络名、元件位号、推断角色、外设模式、配置说明、状态（正常/冲突/警告）<br>规则：按状态分色——正常=白底、冲突=红底、警告=黄底、NC=灰底 |

### circuit_facts.json 结构示例

```json
{
  "mcu": "STM32F103ZET6",
  "package": "LQFP144",
  "verify_status": "success",
  "pins": [
    {
      "pin": "34",
      "pin_name": "PA0-WKUP",
      "net": "PA0",
      "component": "U2",
      "role": "唤醒引脚",
      "peripheral": "GPIO_Input",
      "config": "输入模式，可作唤醒源",
      "status": "warning",
      "note": "网络名无明确语义，建议人工确认用途"
    },
    {
      "pin": "36",
      "pin_name": "PA2",
      "net": "UART2_TX",
      "component": "U2",
      "role": "串口2发送",
      "peripheral": "USART2_TX",
      "config": "复用推挽输出，波特率待定",
      "status": "ok",
      "note": "网络名与芯片复用功能一致"
    }
  ],
  "power": {
    "VDD": "3.3V",
    "VSS": "GND",
    "VDDA": "3.3V",
    "VREF+": "3.3V",
    "VBAT": "3.3V"
  },
  "clocks": {
    "HSE": "8MHz",
    "LSE": "32.768kHz",
    "PLL": "待定",
    "AHB": "待定",
    "APB1": "待定",
    "APB2": "待定"
  },
  "conflicts": [
    {
      "pin": "PB5",
      "issue": "引脚在网络中同时出现 LED1 和 SPI2_MOSI，复用冲突",
      "severity": "error"
    }
  ],
  "warnings": [
    {
      "pin": "PA0-WKUP",
      "issue": "网络名无明确语义，无法推断功能角色",
      "severity": "warning"
    }
  ],
  "nc_pins": ["PE6", "PF0", "PF1"],
  "verified_pin_count": 142,
  "conflict_count": 1,
  "warning_count": 5,
  "nc_pin_count": 3
}
```

### 指针/数据分离规则（所有skill统一）

数据量大的产物（硬件事实报告）真实数据放 outputs/，
结构由 schemas/circuit_facts.schema.json 约束并在写入前校验；
state.json 中 circuit.facts 字段只存**指针（产物路径）与统计计数**，不存数据本体。

## Skill目录结构（标准结构，所有skill统一）

```
circuit-investigator/
├── SKILL.md                     ← 技能说明（给Agent看）
├── schemas/
│   ├── input.schema.json        ← 输入契约（读取的 state.json 字段）
│   ├── output.schema.json       ← 输出契约（state.json 的 circuit.facts 字段，仅指针+统计）
│   └── circuit_facts.schema.json ← 硬件事实报告数据契约（outputs/circuit_facts.json）
├── scripts/
│   ├── investigate.py           ← 主入口（读配置 → 加载 S1/S3 数据 → 交叉验证 → 推断 → 更新state）
│   ├── pin_inferrer.py          ← 引脚功能推断（基于规则或调用 AI）
│   ├── conflict_checker.py      ← 冲突检测（复用冲突、电源缺失、时钟缺失等）
│   └── excel_export.py          ← 生成硬件事实报告 Excel
├── references/
│   ├── inference_rules.md       ← 引脚功能推断规则说明
│   └── excel_format.md          ← Excel输出格式规范
└── assets/
    └── circuit_facts_example.xlsx ← 硬件事实报告 Excel 示例
```

## 执行步骤

1. 从 state.json 读取 `circuit.*` 和 `chip.*` 字段，确认 S1 和 S3 均已成功执行
   - 如果 S1 或 S3 的 status 为 failed，写 `verify_status: failed` 并终止
   - 如果为 partial，继续执行但标记 `verify_status: partial`
2. 加载网表数据（`outputs/circuit_netlist.json`）和芯片数据（`outputs/chip_info/pins.json`、`registers.json`、`clock_tree.json`、`peripherals.json`）
3. 交叉核对：
   - a. 对每个引脚，检查网表中的连接关系与芯片手册中的引脚定义是否一致
   - b. 检查引脚复用冲突（同一引脚被多个外设占用）
   - c. 检查电源引脚是否全部连接（VDD/VSS/VDDA/VREF+/VBAT）
   - d. 检查时钟引脚是否完整（HSE/LSE）
   - e. 检查未连接引脚（NC）
4. 推断每个引脚的功能角色：
   - 基于规则（网络名语义 + 引脚名语义 + 芯片复用功能）
   - 无法推断的标记为 warning，留待人工/AI补充
5. 用 circuit_facts.schema.json 校验硬件事实报告结构
6. 校验通过后写入 outputs/circuit_facts.json
7. 调用 excel_export.py 生成 circuit_facts.xlsx
8. 将路径和统计信息写入 state.json 的 circuit.facts 字段

## 依赖

- Python 3.10+
- jsonschema库（契约校验）
- openpyxl库（Excel生成）
- 可选：openai/anthropic SDK（inference_mode=ai 时使用）

## 禁止事项

- 不要修改config.json，不要读写其他Skill的字段
- 不要修改 S1/S3 产出的文件（netlist.json、chip_info/*.json）
- 不要修改 outputs/ 中非本Skill产出的文件
- 推断失败时不要留半成品文件，应删除并写failed状态
- 冲突检测到 error 时，不要自动修改网表或芯片数据，只记录到冲突列表

## 补充说明

### 与 S1/S3 的分工

- S1 负责提取"外部连接关系"（网表）
- S3 负责提取"芯片内部规格"（引脚定义、寄存器、时钟、外设）
- S4 负责将两者交叉核对，推断每个引脚的功能角色，输出硬件事实报告
- S4 是质量门禁：确认硬件事实无误后，S5 才开始生成代码

### 引脚功能推断规则（rule 模式）

按以下优先级推断：

| 优先级 | 线索 | 推断结果 |
|--------|------|----------|
| 1 | 网络名与芯片复用功能匹配（如 UART2_TX → PA2） | 直接采用复用功能 |
| 2 | 网络名有明确语义（如 KEY、LED、SWD、BOOT） | 按语义推断 GPIO 输入/输出 |
| 3 | 引脚名有明确语义（如 PA0-WKUP 中的 WKUP、OSC_IN、NRST） | 按引脚名推断特殊功能 |
| 4 | 引脚与电源网络相连（如 3V3、GND、VDD） | 判定为电源 |
| 5 | 以上都不匹配 | 留空，标记 warning |

**当前版本不依赖引脚电气类型**。原因：S1 目前只提取网表，未提取原理图符号的电气类型（Input/Output/Power）。等后续 S1 扩展后，可以在优先级 2 和 3 之间插入一条规则：

| 优先级 | 线索 | 推断结果 |
|--------|------|----------|
| （未来） | 引脚电气类型为 Input / Output / Power | 直接按电气类型推断 |

### 网络名语义推断参考表

| 网络名关键词 | 推断角色 | 典型外设 |
|--------------|----------|----------|
| KEY、BTN、SW | 按键输入 | GPIO_Input |
| LED、LAMP | LED 指示 | GPIO_Output |
| UART、TX、RX | 串口通信 | USART |
| SPI、MOSI、MISO、SCK、CS | SPI 通信 | SPI |
| I2C、SCL、SDA | I2C 通信 | I2C |
| ADC、AIN | 模拟输入 | ADC |
| PWM | 脉冲输出 | TIMER |
| SWD、SWCLK、SWDIO | 调试接口 | SWD |
| JTAG、TMS、TCK、TDI、TDO | 调试接口 | JTAG |
| BOOT | 启动配置 | BOOT |
| RESET、NRST | 复位 | RESET |
| OSC、XTAL | 晶振 | HXTAL / LXTAL |
| 4G、WIFI、BUS | 模块通信 | USART（需人工确认） |

**推断不出的网络名（如 PA0、PE6、NetU1_47）**：留空，标记 warning，供人工/AI补充。

### 降级机制

- S1 或 S3 的 status 为 partial：S4 继续执行，但 verify_status 写 partial
- 网表中缺少 component 字段（S1 未扩展时）：跳过依赖元件位号的推断，只按网络名推断
- inference_mode=rule 时无法推断的引脚：标记 warning，不中断主流程
- inference_mode=ai 时调用 LLM 辅助推断：如果 LLM 调用失败，降级到 rule 模式

### verify_scope 参数说明

| 值 | 验证内容 |
|----|----------|
| pins | 只验证引脚连接与定义 |
| power | 只验证电源轨 |
| clocks | 只验证时钟配置 |
| peripherals | 只验证外设复用映射 |
| all | 全部验证（默认） |

### 冲突严重程度

| 级别 | 含义 | 示例 |
|------|------|------|
| error | 必须修复，否则代码无法正常工作 | 同一引脚被两个外设占用、电源引脚未连接 |
| warning | 建议确认，可能不影响基本功能 | 网络名无明确语义、时钟未明确配置 |
| info | 提示信息，无需处理 | 未连接引脚（NC）列表 |