# 原理图引脚表 Excel 输出格式规范

参考样例：`原理图网络表.png`（GD32F205VET 引脚配置表）。

## 文件位置

- 输出路径：`outputs/pin_table.xlsx`
- 数据来源：`outputs/circuit_netlist.json`（由 parse.py 解析原理图生成）

## 工作表（Sheet）结构

所有元件放在**同一个工作表**（命名 `引脚配置`），便于通读和筛选。
每个元件一个**区块**，自上而下依次排列：

```
C1（0.1uF）— 2 引脚          ← 元件标题行（合并 A:E 单元格，蓝底加粗）
引脚号 | 引脚名 | 网络名 | 作用 | 外设/模式    ← 表头行（深蓝底白字）
1      | 1      | VCC    | ...  | ...
2      | 2      | GND    | ...  | ...
                              ← 空行分隔
C2（0.1uF）— 2 引脚
...
```

元件区块按网表中元件顺序排列。

## 列定义

| 列 | 表头 | 数据来源 | 说明 |
|----|------|---------|------|
| A | 引脚号 | netlist `components[].pins[].pin` | 元件引脚编号 |
| B | 引脚名 | netlist `components[].pins[].pin_name` | 如 PA0、VBAT |
| C | 网络名 | netlist `components[].pins[].net` | 悬空引脚显示"未连接" |
| D | 作用 | 自动推断 + 人工补充 | 见下方推断规则 |
| E | 外设/模式 | 自动推断 + 人工补充 | 见下方推断规则 |

表头样式：蓝底白字加粗。

## 「作用 / 外设/模式」自动推断规则

从引脚名、网络名、引脚类型推断，无法识别的留空供人工/AI 补充：

| 识别条件（引脚名或网络名，大小写不敏感） | 作用 | 外设/模式 |
|------------------------------------------|------|----------|
| VDD / VSS / VCC / GND / VBAT / VREF，或 pin_type=POWER | 电源 | 电源 |
| 网络名整体形如 3V3 / 5V / 12V / +3V3 / 3.3V | 电源 | 电源 |
| SWDIO / SWCLK / TMS / TCK | SWD 调试 | SWD |
| JTDI / JTDO / JTRST | JTAG 调试 | JTAG |
| BOOT | 启动模式配置 | BOOT |
| NRST / RESET / RST | 复位 | RESET |
| OSCI / OSCO / XCIN / XCOUT / XTAL（引脚名），或网络名含 OSC | 晶振 | 晶振 |
| KEY / BTN / BUTTON | 按键输入 | GPIO 输入 |
| LED | LED 指示 | GPIO 输出 |
| SCL / SDA / I2C | I2C 通信 | I2C |
| MOSI / MISO / SPI | SPI 通信 | SPI |
| CAN | CAN 通信 | CAN |
| UART / USART | 串口通信 | UART |
| 网络 net 为 null | 未使用（悬空） | （空） |
| 其他 | （空，待补充） | （空，待补充） |

> 说明：原理图只存电气连接，"按键/LED/串口"等用途语义来自**网络名**；
> 引脚级精确复用映射（如 PA9 = USART1_TX）需 datasheet 引脚复用表，
> 由 S3 datasheet-extractor + S4 circuit-investigator 完成深度标注。

## 行颜色编码

参考样例图的视觉分组规则：

| 行类别 | 填充色 | 说明 |
|--------|--------|------|
| 电源引脚 | 蓝色 `D9E1F2` | VDD/VSS/VBAT 等 |
| 特殊功能引脚 | 黄色 `FFF2CC` | SWD / BOOT / NRST / 晶振 |
| 悬空引脚 | 灰色 `E7E6E6` | 未连接任何网络 |
| 普通引脚 | 白色（无填充） | GPIO / 外设引脚 |

## 依赖

- Python 库：`openpyxl`（缺失时 parse.py 记录警告并跳过 Excel 导出，不影响网表主流程）
