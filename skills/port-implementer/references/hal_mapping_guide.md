# HAL 映射指南（厂商 API ↔ Port 接口）

> S5c Agent 实现 Port 接口时的映射规范。接口语义（错误码/超时/线程安全）
> 按 S5b 的 `skills/port-contract-and-app/references/port_design_principle.md`
> 同一约定，本指南不重复定义。

## 1. 映射总则

1. **manifest 是唯一接口依据**：实现哪些函数、绑定哪些逻辑实例，全部读
   `outputs/s5b/port_interface_manifest.json`，**禁止硬解析 C 头文件**。
2. **hardware_capabilities 是唯一硬件依据**（含 hw_instance=null 时的实例选定）；
   **禁止直接读取 S3/S4 数据**。
3. **厂商实例名/引脚号/地址只进文件头注释**（登记 hw_instance 映射），不进
   接口签名；换板/换平台只改 manifest 与实现文件，Port 头与 APP/Driver 不动。
4. **不臆造 API**：写代码前先读 SDK 头文件核对函数名/枚举名/时钟使能宏；
   不确定的留 `/* TODO: */` 注释（写明"查 xxx 手册章节"），编译验证归 S7。
5. **不重复 HAL 初始化**：S5a 已完成时钟使能、GPIO 复用、外设基础配置
   （`s5a.init_sources`，如 `uart_init.c` 的 `usart1_init()`）。Port 实现只做
   **逻辑实例绑定 + 读写下层操作**，必要时调用 S5a init 头文件声明的函数。
6. 时钟节拍换算（如 µs 延时、周期计算）以 `hardware_capabilities.clocks`
   的实际频率为准，不假设 72MHz。

## 2. STM32F10x 标准外设库映射表（hal_framework=std_periph）

错误码映射：`port_err_t` ← HAL 返回值。0/成功 → `PORT_OK`；
非法参数 → `PORT_ERR_PARAM`；时序未就绪/忙 → `PORT_ERR_BUSY`；
等待超时 → `PORT_ERR_TIMEOUT`；状态错误（未初始化等）→ `PORT_ERR_STATE`。

### 2.1 UART（uart_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `uart_port_init(id, cfg)` | 逻辑 id → USARTx 绑定（static 数组记录句柄/回调）；波特率等已由 S5a init 配置，此处仅校验绑定，可选择性调用 S5a 的 `usartX_init()` |
| `uart_port_write(id, buf, len)` | 轮询：`USART_GetFlagStatus(USARTx, USART_FLAG_TXE)` 等待 → `USART_SendData()`；同步拷贝语义（发送完成或拷入缓冲后返回） |
| `uart_port_deinit(id)` | `USART_Cmd(USARTx, DISABLE)` + 清 ctx（不动 S5a 的引脚/时钟配置） |
| 接收回调 | ISR：`USARTx_IRQHandler` 中 `USART_GetITStatus(USART_FLAG_RXNE)` → **判空回调** → `USART_ReceiveData()` |

### 2.2 GPIO（gpio_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `gpio_port_init(id, cfg)` | 逻辑 id → GPIOx+Pin 绑定（manifest config 的 active_level 固化进 ctx）；S5a 已配置方向/上下拉 |
| `gpio_port_write(id, level)` | `GPIO_WriteBit(GPIOx, pin, level)`（或 BSRR/BRR 直写） |
| `gpio_port_read(id, *level)` | `GPIO_ReadInputDataBit()` / 输出回读 `GPIO_ReadOutputDataBit()` |
| `gpio_port_toggle(id)` | `GPIO_WriteBit(GPIOx, pin, !GPIO_ReadOutputDataBit())` |
| `gpio_port_set_dir(id, dir)` | 单总线换向（DHT11）：重配 `GPIO_Init`（仅换向场景；普通引脚返回 `PORT_ERR_STATE`） |
| `gpio_port_set_active / read_active` | 按 ctx 的 active_level 做电平语义转换 |

### 2.3 ADC（adc_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `adc_port_init(id, cfg)` | 逻辑通道 → ADCx 绑定；S5a 已配采样时间/规则通道 |
| `adc_port_sample_mv(id, *raw_mv)` | `ADC_SoftwareStartConvCmd()` → 轮询 `ADC_GetFlagStatus(ADC_FLAG_EOC)` → `ADC_GetConversionValue()`；按 cfg.avg_count 均值；`raw = val * ref_mv / 4095` |

### 2.4 Timer（timer_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `timer_port_init(id)` | 逻辑 id → 定时器/SysTick 绑定 |
| `timer_port_start_periodic(id, period_ms, cb, user)` | `TIM_TimeBaseInit()` 装载值 = `period_ms * tick_hz / (psc+1)`（按 clocks 实算）→ `TIM_ITConfig(TIM_IT_Update)` → `TIM_Cmd(ENABLE)`；回调存 ctx |
| `timer_port_stop(id)` | `TIM_Cmd(DISABLE)`（幂等） |
| `timer_port_delay_us(us)` | SysTick 忙等：`SysTick_Config(us * sysclk_hz / 8e6)`（HCLK/8 或全速按实际）→ 等待 COUNTFLAG → 复位；禁止在中断内调用 |
| ISR | `TIMx_IRQHandler` / `SysTick_Handler`：清标志 → **判空回调** → `ctx->cb(id, ctx->user_data)` |

hw_instance=null 时（典型如 10ms 系统节拍）：优先 SysTick（不占通用定时器），
在文件头注释登记选定结果；delay_us 可基于同一定时器计数。

### 2.5 PWM（pwm_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `pwm_port_set_freq(id, hz)` | ARR = timer_clk / (psc·hz) 重装（按 clocks 实算） |
| `pwm_port_set_duty(id, permille)` | `TIM_SetCompareX(TIMx, channel, ARR * permille / 1000)` |

### 2.6 Watchdog（wdt_port）

| Port 接口 | 典型 HAL 序列 |
|---|---|
| `wdt_port_init(id, timeout_ms)` | 按 `timeout_ms` 换算预分频/重装载 → `IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable)` → `IWDG_SetPrescaler()` → `IWDG_SetReload()` → `IWDG_ReloadCounter()` → `IWDG_Enable()`；已启动返回 `PORT_ERR_STATE`，超量程返回 `PORT_ERR_PARAM` |
| `wdt_port_feed(id)` | `IWDG_ReloadCounter()`（只写 Key 寄存器，无阻塞 → `isr_safe`，可在 ISR 调用） |
| `wdt_port_reset_caused(id, *caused)` | `RCC_GetFlagStatus(RCC_FLAG_IWDGRST)` → `RCC_ClearFlag()`（RCC 无单标志清除位，清即清整组复位标志），`*caused = 1/0` |

IWDG 超时换算（STM32F1，LSI 标称 40kHz，PR ∈ 4/8/16/32/64/128/256、RLR 12 位）：
`T = (4 × 2^PR) × (RLR + 1) / F_LSI`；取**最小的预分频**使 RLR 落进 12 位
（精度最高），量程约 0.1ms ~ 26.2s，超出返回 `PORT_ERR_PARAM`。
换算基（时钟源频率、档位、位宽）以 `hardware_capabilities` 的 wdt 能力标签为准，
不硬编码假设。

- **超时由调用方给定**（应用策略）：实现层不设默认值、不读 manifest config
  （同 timer 周期归调用方）。
- 看门狗**硬件侧准备**（时钟门控、独立 RC 振荡器使能等）若平台需要，由 S5a 的
  `wdt_init` 提供（可选）；**超时（PR/RLR）一律不归 S5a**。
- 独立看门狗多数**一旦启动不可关闭** → 无 `deinit`；复位原因查询属上电状态
  查询，可在 `wdt_port_init` 之前调用（启动自检场景）。
- MCU 无看门狗硬件时**报能力缺口**（`capability_gap`），不得用软件计数假装实现。

### 2.7 并行总线 par（FSMC 存储器映射，LCD 类器件）

16 位并口走 FSMC Bank1 NE 区，命令/数据地址映射已由 S5a `fsmc_init.c`
配置（命令/数据各一个地址），manifest 数据侧登记（如命令 0x6C000000 /
数据 0x6C000800）。实现要点：

```c
#define LCD_CMD_ADDR  (*(__IO uint16_t *)0x6C000000u)  /* 地址来自 manifest，仅注释引用 */
#define LCD_DATA_ADDR (*(__IO uint16_t *)0x6C000800u)
/* par_port_write_cmd  → LCD_CMD_ADDR = cmd;     （同步写直达，无需等待） */
/* par_port_write_data → LCD_DATA_ADDR = data;    */
/* par_port_write_data_block → 循环写 DATA_ADDR（同步拷贝语义）；高频像素流
   可后续换 DMA，但语义对调用方不变（DMA 隐藏在实现内） */
```

注意：地址值在本文件中出现是**实现层数据登记**（Port 头与 APP 不感知），
文件头注释标明"来自 manifest lcd_bus 实例，换板改 manifest + 本文件"。

## 3. 与 S5a init 产物的对接

- S5a init 函数（`*_init.h`）通常无返回值、无参数（如 `void usart1_init(void)`），
  Port init 若需保证硬件就绪可调用；重复调用需幂等或由 S5a 保证。
- 若 S5a 未覆盖某外设的初始化（manifest hw_source=design_input 场景），
  Port 实现自行补齐**该实例的操作前提**（如使能外设时钟），但完整的
  GPIO 复用配置仍归 S5a——发现缺口报给用户，不在 Port 内越俎代庖。

## 4. hw_instance=null 的实例选定流程

1. 读 manifest 该实例的 description/config（如 par 的 `bus_width_bits: 16`；
   周期/超时这类**由调用方或 S5a 决定的数值**不在 manifest 登记）；
2. 在 hardware_capabilities.peripherals 中按类型筛选未被占用的实例
   （对照其余逻辑实例已绑定的 hw_instance，避免冲突）；
3. 参考用户设计输入（docs/s5c_design_input.md）与 S5a init 产物（哪个定时器
   已被 tim_init.c 配置）；
4. 选定后在实现文件头注释登记：`/* TIMER_PORT_TICK_10MS → SysTick（选定依据：REC-005 / 未占用） */`，
   并写入 outputs/s5c/recommendations.json（prepare 已登记的项补充选定结果）。

## 5. 8 位 MCU（mcu8）注意

- SFR 模型：寄存器直写（`TXREG = data`）为主，无 HAL 库函数；
- 静态数组按 instance id 索引同样适用；位操作用位掩码不用 bit-banding；
- 中断标志清零顺序（先读后清等）以手册为准，不确定留 `/* TODO: */`。
