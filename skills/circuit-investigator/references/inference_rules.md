# 引脚功能推断规则（rule 模式）

> S4 circuit-investigator 的推断引擎说明。当前版本不依赖引脚电气类型——
> S1 只提取网表，未提取原理图符号的电气属性（Input/Output/Power）。
> S1 扩展后可在优先级 2/3 之间插入电气类型规则。

## 推断优先级

| 优先级 | 线索 | 推断结果 |
|--------|------|----------|
| 1 | 网络名与芯片复用功能匹配（如 UART2_TX → PA2 的 AF） | 直接采用复用功能（如 USART2_TX） |
| 2 | 网络名有明确语义（KEY、LED、SWD、BOOT、UART…） | 按语义推断 GPIO 输入/输出/通信外设 |
| 3 | 引脚名有明确语义（WKUP、OSC_IN、NRST、BOOT0、SWDIO） | 按引脚名推断特殊功能 |
| 4 | 引脚与电源网络相连（3V3、GND、VDD、12V…） | 判定为电源 |
| 5 | 以上都不匹配 | 留空，标记 warning，供人工/AI 补充 |

### 优先级 1 的网络名规范化

网络名与芯片 AF 名直接比对前先规范化（`normalize_net`）：

| 网络名写法 | 规范化为 | 匹配的 AF |
|-----------|---------|-----------|
| `UART1_TX` | `USART1_TX` | PA9 的 `USART1_TX` |
| `TXD2` | `USART2_TX` | `PA2` 的 `USART2_TX` |
| `SPI2_MOSI` | 原样 | PB15 的 `SPI2_MOSI` |

规范化规则：大写、`-`/空格 → `_`、`UART` → `USART`、`TXD/RXD` → `USARTn_TX/RX`。

## 网络名语义推断参考表（优先级 2）

| 网络名关键词 | 推断角色 | 外设/模式（Excel 类别色） |
|--------------|----------|--------------------------|
| KEY、BTN、SW、ROT、LC、ENC | 按键/开关输入 | GPIO 输入上拉（绿） |
| LED、LAMP、BACKLIGHT | LED 指示 | GPIO 输出（浅蓝） |
| UART、TX、RX、COM、4G、WIFI、DEBUG | 串口通信（需人工确认具体外设） | USART（浅蓝） |
| SPI、MOSI、MISO、SCK、CS | SPI 通信 | SPI（紫） |
| I2C、SCL、SDA、EEPROM | I2C 通信 | I2C（紫） |
| ADC、AIN、VOLTAGE、CURRENT | 模拟输入 | ADC（橙） |
| PWM、TIM、CH、ENCODER | 定时器/脉冲输出 | TIMER PWM（粉红） |
| SWD、SWCLK、SWDIO、JTAG、TRACE | 调试接口 | SWD（黄） |
| BOOT | 启动配置 | BOOT（黄） |
| RESET、NRST、RST | 复位 | 复位（黄） |
| OSC、XTAL、32K、MCO | 晶振/时钟 | HXTAL/LXTAL（黄） |
| CAN | CAN 通信 | CAN |
| USB、DM、DP | USB 接口 | USB |
| SDIO、SD、TF | SD 卡接口 | SDIO |
| FSMC、EXMC、LCD | 并口/LCD | FSMC（灰） |
| 3V3、5V、GND、VDD、VBAT、12V… | 电源 | 电源（浅蓝） |

**推断不出的网络名**（如 `PA0`、`NetU1_47`）：role/peripheral 留空，
标记 warning，供人工/AI 补充。

## 引脚名语义规则（优先级 3）

| 引脚名模式 | 推断 |
|-----------|------|
| `OSC32_IN` / `OSC32_OUT` / `PC14-OSC32IN` | LXTAL（32.768kHz RTC 晶振） |
| `OSC_IN` / `OSC_OUT` / `PD0-OSC_IN` | HXTAL（主时钟晶振） |
| `NRST` | 复位（低电平有效） |
| `BOOT0` / `BOOT1` | 启动配置 |
| `PA13` / `PA14`、`SWDIO` / `SWCLK` | SWD 调试 |
| `JTMS/JTCK/JTDI/JTDO` | JTAG 调试 |
| `*-WKUP` | 唤醒输入 |

## 冲突检测规则

| 检查项 | 严重程度 | 说明 |
|--------|---------|------|
| 网表引脚号在芯片定义中不存在 | error | 引脚号越界 |
| VDD/VSS 电源引脚未连接 | error | 必须连接 |
| VBAT/VDDA/VREF 未连接 | warning | 常见悬空设计，建议确认 |
| HSE 晶振引脚未连接 | warning | 可用 HSI 替代 |
| LSE 晶振引脚未连接 | warning | 不用 RTC 可忽略 |
| 网络名暗示外设与引脚 AF 不符（如 UART3_TX 接到无 USART3_TX 的脚） | error | 复用冲突 |
| 网表引脚名与芯片定义引脚名不一致 | warning | 数据同步问题 |
| 网络名无明确语义 | warning | 无法推断 |

## ai 模式（预留）

`inference_mode=ai` 调用 LLM 对 warning 引脚补充推断；LLM 调用失败自动降级
rule 模式（当前版本未接入 SDK，直接降级）。
