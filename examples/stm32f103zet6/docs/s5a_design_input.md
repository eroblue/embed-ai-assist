# s5a_design_input.md - SmartEnvGuard 硬件初始化设计输入

> 本文档告诉 S5a 本次初始化使用哪些硬件接口、参数是什么。
> 不用到的外设一律不初始化，保持 S5a 产物简洁。
> 引脚映射请对照 S4 输出的 circuit_facts.json 确认，本文档给出的是建议方案。

## 系统时钟

- 时钟源：HSE 外部晶振 8MHz
- PLL：×9，SYSCLK = 72MHz
- AHB 分频：1，HCLK = 72MHz
- APB1 分频：2，PCLK1 = 36MHz
- APB2 分频：1，PCLK2 = 72MHz
- FLASH 等待周期：2WS（72MHz 必须）
- 说明：不使用 HSI，不启用 MCO 时钟输出

## 使用的外设

### GPIO - 指示灯（输出）

| 引脚 | 用途 | 初始状态 |
|---|---|---|
| PB5 | 运行指示灯（板载 DS0） | 灭 |
| PE5 | 执行指示灯（板载 DS1） | 灭 |

### GPIO - 执行器控制（输出）

| 引脚 | 用途 | 初始状态 |
|---|---|---|
| PA4 | 执行器控制（继电器/MOS 驱动） | 关 |

说明：输出低电平为关，高电平为开。硬件接线为板载空闲引脚，需用户自行焊接驱动电路。

### GPIO - 按键（输入）

| 引脚 | 用途 | 模式 | 说明 |
|---|---|---|---|
| PE2 | 按键 3（板载 KEY0，静音切换） | 上拉 | 按下为低电平，下降沿有效 |
| PE3 | 按键 1（板载 KEY1，模式切换） | 上拉 | 同上 |
| PE4 | 按键 2（板载 KEY2，执行器开关） | 上拉 | 同上 |

说明：硬件去抖不启用，软件去抖由应用层（app_key_handler）按 50ms 处理。

### TIM4 - 蜂鸣器 PWM

- 实例：TIM4_CH3
- 引脚：PB8（板载 BEEP）
- 用途：告警蜂鸣，1s 响 / 1s 停
- 频率：2kHz
- 占空比：响时为 50%，停时为 0%
- 分频与计数：PSC = 71（计数时钟 1MHz）、ARR = 499（2kHz）
- 说明：本层只初始化 PWM；启停由应用层控制

### ADC3 - 光照采集

- 实例：ADC3_IN6（ADC3 通道 6）
- 引脚：PF8（板载光敏电阻分压）
- 分辨率：12 位
- 采样时间：55.5 周期
- 转换模式：单次（软件触发）
- 基准：VDD（3.3V）
- 说明：本层只初始化 ADC；采样触发由应用层按 2s 周期调度

### FSMC - LCD 显示（TFT_LCD 通用接口，16 位并口）

**模块接口说明**：板载 TFT_LCD 为通用液晶模块接口，支持 ALIENTEK 全系列 TFTLCD 模块（2.4 寸、2.8 寸、3.5 寸、4.3 寸、7 寸等），通过 FSMC 总线连接 MCU，显著提高刷屏速度。

**FSMC 配置**：

- 类型：FSMC Bank1 NOR/SRAM 区域 4（NE4）
- 片选：FSMC_NE4（PG12）
- 寄存器选择：FSMC_A10（PG0）——作为 RS 信号，低=命令、高=数据
- 数据总线：FSMC_D0 ~ FSMC_D15（16 位）
  - D0=PD14，D1=PD15，D2=PD0，D3=PD1
  - D4=PE7，D5=PE8，D6=PE9，D7=PE10
  - D8=PE11，D9=PE12，D10=PE13，D11=PE14，D12=PE15
  - D13=PD8，D14=PD9，D15=PD10
- 控制线：FSMC_NOE（PD4，读使能）、FSMC_NWE（PD5，写使能）
- 数据宽度：16 位
- 时序模式：Mode B（SRAM 异步，读写独立时序）
- 地址映射：命令地址 0x6C000000，数据地址 0x6C0007FE（A10 偏移）
- 时序参数（ILI9341 类典型值，待按实际 LCD 手册微调）：
  - AddressSetupTime = 0
  - AddressHoldTime = 0
  - DataSetupTime = 15
  - BusTurnAroundTime = 0
  - CLKDivision = 2
  - DataLatency = 2

**背光控制**：

- 引脚：PB0（LCD_BL）
- 方式：GPIO 输出（高电平点亮背光，低电平熄灭）
- 说明：本版本不使用 PWM 调光，如需调节亮度可后续改为 TIM3_CH3 PWM 输出

**复位**：

- LCD 复位信号与开发板复位按钮共用复位电路，MCU 不单独控制
- S5a 无需为 LCD 复位分配 GPIO 或初始化操作

**触摸屏（本版本不使用）**：

- 触摸信号已在板上连接：T_MISO=PB2、T_MOSI=PF9、T_PEN=PF10、T_SCK=PB1、T_CS=PF11
- 支持的触摸方式：电阻屏（XPT2046 类）或电容屏
- **本版本 SmartEnvGuard 不使用触摸功能**：这些引脚保持复位默认状态（浮空输入），S5a 不配置它们

**职责边界**：

- 本层（S5a）只初始化 FSMC 控制器、数据/控制线 GPIO、背光 GPIO
- **LCD 初始化序列**（厂商寄存器配置、Gamma 校正、显示方向设置等）属于设备驱动层，由 S5b 的 `driver_lcd` 实现
- S5a 保证"总线通了"，S5b 保证"屏幕亮了"

### USART1 - 上位机通信

- 实例：USART1
- 引脚：PA9(TX) / PA10(RX)
- 参数：115200-8N1，无流控
- 模式：异步
- 中断：启用接收中断（USART1_IRQn）
- 发送：轮询（应用层决定）
- DMA：不使用
- 说明：通过板载 CH340 转 USB 连接 PC

### DHT11 - 温湿度采集（单总线）

- 类型：单总线
- 引脚：PG11（**待确认**，请对照 S4 facts 输出）
- 配置：GPIO 动态切换输入/输出
- 上拉：外部 4.7kΩ 上拉（或用内部上拉）
- 说明：本层只配置 GPIO；单总线协议时序由应用层驱动实现

## 中断配置

| 中断源 | 抢占优先级 | 子优先级 | 用途 |
|---|---|---|---|
| USART1_IRQn | 2 | 0 | 上位机指令接收 |

NVIC 分组：PriorityGroup_2（2 位抢占 + 2 位子优先级）。

其他外设使用轮询方式，不启用中断。

## DMA 配置

本版本不使用 DMA。所有外设数据搬运由应用层轮询或中断方式处理。

## 低功耗

不启用（project.power.enabled = false）。

## 初始化顺序

`board_init()` 按以下顺序调用：

1. `clock_init()`：配置 HSE + PLL，SYSCLK = 72MHz
2. `nvic_init()`：配置中断优先级分组
3. `gpio_init()`：配置所有 GPIO（指示灯、按键、执行器）
4. `tim4_init()`：配置蜂鸣器 PWM
5. `adc3_init()`：配置光照采集
6. `fsmc_lcd_init()`：配置 FSMC 控制器、LCD 数据/控制线、背光 GPIO
7. `usart1_init()`：配置上位机通信
8. `dht11_init()`：配置 DHT11 单总线 GPIO

