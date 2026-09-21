# S5a 初始化代码生成规范（Agent 用）

Agent 依据 `outputs/s5a/generation_brief.md`（任务书）编写 S5a 产物目录
（PROJECT_LAYOUT.md 解析，如 `Drivers/BSP/Src/` 下 .c、`Drivers/BSP/Inc/` 下 .h）代码时
遵守本规范。风格与厂商标准外设库（StdPeriph）官方 demo 一致；数值（引脚/
实例/时钟/波特率）**直接采用任务书**，不自行改推；平台 API 以标准外设库
头文件为准，不确定的留 TODO 注释，不臆造 API。

## 1. 通用结构

```c
/* <module>_init.c - <说明>（S5a hardware-initializer 生成，<MCU>） */
#include "<module>_init.h"
#include "<平台头>"        /* gd32f20x.h / stm32f10x.h，按任务书 */

void <module>_init(void)
{
    /* 时钟使能 → 反初始化 → 配置 → 使能 */
}
```

```c
/* <module>_init.h - <说明>（S5a hardware-initializer 生成） */
#ifndef <MODULE>_INIT_H
#define <MODULE>_INIT_H

void <module>_init(void);

#endif /* <MODULE>_INIT_H */
```

- 每模块 `.c` + `.h` 成对；每实例一个函数（如 `uart_usart5_init`），
  模块级 `<module>_init()` 汇总调用
- 总入口 `hal_init`（layered/full）或 `board_init`（flat）只做汇总调用，
  顺序：`clock_init() → gpio_init() → nvic_init() → 各外设 init() →
  rtos_hw_init()/power_init()（如有）`

## 2. 时钟初始化

数值全部来自任务书第 2 节（PLL 倍频、总线分频、FLASH 等待周期已算好）。
LSE 存在时使能并选为 RTC 时钟源；无 HSE 时按内部 8MHz 直跑。

| 平台 | 关键 API |
|---|---|
| GD32F20x | `rcu_osci_on` / `rcu_pll_config` / `rcu_ahb_clock_config` / `rcu_apb1_clock_config` / `rcu_apb2_clock_config` / `rcu_system_clock_source_config` / `SystemCoreClockUpdate` |
| STM32F10x | `RCC_HSEConfig` / `FLASH_PrefetchBufferCmd` / `FLASH_SetLatency` / `RCC_PLLConfig` / `RCC_SYSCLKConfig` / `RCC_HCLKConfig` / `RCC_PCLK1Config` / `RCC_PCLK2Config` / `SystemCoreClockUpdate` |

GD32F20x 已验证示例（HXTAL 16MHz × 2 = 32MHz，LSE 供 RTC）：

```c
void clock_init(void)
{
    /* HXTAL 16MHz（S4 硬件事实） */
    rcu_osci_on(RCU_HXTAL);
    while (ERROR == rcu_osci_stab_wait(RCU_HXTAL)) { }
    /* PLL: HXTAL x 2 = 32MHz（设计输入目标 32MHz） */
    rcu_pll_config(RCU_PLLSRC_HXTAL, RCU_PLL_MUL2);
    rcu_ahb_clock_config(RCU_CKSYS_DIV1);   /* AHB  = 32MHz */
    rcu_apb1_clock_config(RCU_CKAPB1_DIV1); /* APB1 = 32MHz */
    rcu_apb2_clock_config(RCU_CKAPB2_DIV1); /* APB2 = 32MHz */
    rcu_osci_on(RCU_PLL_CK);
    while (ERROR == rcu_osci_stab_wait(RCU_PLL_CK)) { }
    rcu_system_clock_source_config(RCU_CKSYSSRC_PLL);
    while (rcu_system_clock_source_get() != RCU_SCSS_PLL) { }
    SystemCoreClockUpdate();
    /* LXTAL（RTC 时钟源，S4 硬件事实） */
    rcu_osci_on(RCU_LXTAL);
    while (ERROR == rcu_osci_stab_wait(RCU_LXTAL)) { }
    rcu_rtc_clock_config(RCU_RTCSRC_LXTAL);
}
```

STM32F10x 已验证要点：`FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable)`
+ `FLASH_SetLatency(FLASH_Latency_N)`（**等待周期随主频联动：≤24MHz 0WS、
≤48MHz 1WS、≤72MHz 2WS，勿遗漏**）；切换 SYSCLK 后用
`RCC_GetSYSCLKSource() != 0x08` 等待生效。

## 3. GPIO 初始化

模式映射（任务书 GPIO 清单的 `mode` 列 → 平台枚举）：

| 用途 | GD32 模式 | STM32F1 模式 |
|---|---|---|
| 复用输出（TX/SCK/MOSI/FSMC） | `GPIO_MODE_AF_PP` | `GPIO_Mode_AF_PP` |
| 复用开漏（I2C） | `GPIO_MODE_AF_OD` | `GPIO_Mode_AF_OD` |
| 推挽输出（LED） | `GPIO_MODE_OUT_PP` | `GPIO_Mode_Out_PP` |
| 按键输入 | `GPIO_MODE_IPU` | `GPIO_Mode_IPU` |
| 浮空输入 | `GPIO_MODE_IN_FLOATING` | `GPIO_Mode_IN_FLOATING` |
| 模拟输入 | `GPIO_MODE_AIN` | `GPIO_Mode_AIN` |

- GD32：先 `rcu_periph_clock_enable(RCU_GPIOx)`（端口时钟），再
  `gpio_init(GPIOx, 模式, GPIO_OSPEED_50MHZ, GPIO_PIN_n)`，行尾注释标注
  `/* 网络名 - 复用功能 */`
- STM32F1：GPIO 时钟在 APB2（`RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOx, ENABLE)`），
  复用结构体逐项赋值后 `GPIO_Init`；**重映射时需先使能 AFIO 时钟**
  （`RCC_APB2Periph_AFIO`）再 `GPIO_PinRemapConfig`
- 晶振脚由 clock_init 配置；BOOT/NRST/SWD/电源脚不配置（任务书"跳过的引脚"）

GD32F20x 已验证示例（FSMC 数据/控制脚，按端口分组、同端口只使能一次时钟）：

```c
void gpio_init(void)
{
    rcu_periph_clock_enable(RCU_GPIOE);
    gpio_init(GPIOE, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_7);  /* LCD_DB4 - FSMC/EXMC */
    ...
    rcu_periph_clock_enable(RCU_GPIOD);
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_14); /* LCD_DB0 - FSMC/EXMC */
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_7);  /* LCD_CS - FSMC/EXMC */
    ...
}
```

## 4. 外设初始化

- UART：波特率/引脚来自任务书；GD32 用 `usart_baudrate_set` /
  `usart_word_length_set` / `usart_stop_bit_set` / ... / `usart_enable`；
  STM32 用 `USART_InitTypeDef` + `USART_Init` + `USART_Cmd`；RX 未连接时注释
  标注"仅 TX"
- SPI：主模式 8bit、软 NSS；速率 = PCLK/prescale（默认保守分频并注释"按需
  调整"）。任务书标注 remap 的实例：先使能 AFIO 时钟再重映射
  （GD32 `gpio_pin_remap_config(GPIO_SPI2_REMAP, ENABLE)`）
- I2C：100kHz 标准模式，开漏复用；GD32 `i2c_clock_config`，STM32
  `I2C_InitTypeDef.I2C_ClockSpeed = 100000`
- ADC：12bit 右对齐；通道/采样时间按 S5b 用例确定，留 TODO；
  STM32 需 `RCC_ADCCLKConfig(RCC_PCLK2_Div6)`（ADCCLK ≤ 14MHz）与校准流程
- PWM：按任务书定时器时钟算 prescaler（1MHz 计数）与 period（默认 1kHz），
  50% 占空比；GD32 `timer_parameter_struct` + `timer_oc_parameter_struct`，
  STM32 `TIM_TimeBaseInitTypeDef` + `TIM_OCxInit`
- FSMC/EXMC（LCD 并口）：引脚复用（AF_PP）在 gpio_init.c 完成，本模块只有
  bank/时序本体；bank 用 NE1（基址 0x60000000），数据宽度按任务书，
  时序取保守默认值并注释"请按 LCD 驱动手册调整 setup 时间"

GD32F20x FSMC 已验证示例（8 位，EXMC Bank0 子bank0）：

```c
void fsmc_lcd_init(void)
{
    rcu_periph_clock_enable(RCU_EXMC);
    /* Bank1 子bank0（NE1，基址 0x60000000）—— LCD 并口
       时序为保守默认值（慢速），请按 LCD 驱动手册调整 setup 时间 */
    exmc_norsram_parameter_struct exmc_norsram_init_struct;
    exmc_norsram_timing_parameter_struct rw_timing;
    rw_timing.asyn_address_setuptime = 0x0FU;
    rw_timing.asyn_data_setuptime = 0xFFU;
    rw_timing.bus_latency = 0x0FU;
    exmc_norsram_init_struct.norsram_number = EXMC_BANK0_NORSRAM_REGION0;
    exmc_norsram_init_struct.write_mode = ENABLE;
    exmc_norsram_init_struct.asyn_wait = DISABLE;
    exmc_norsram_init_struct.norsram_signal = EXMC_NORSRAM_ASYNC_NORSRAM;
    exmc_norsram_init_struct.databus_width = EXMC_NOR_DATABUS_WIDTH_8B;
    exmc_norsram_init_struct.read_write_timing = rw_timing;
    exmc_norsram_init(&exmc_norsram_init_struct);
    exmc_norsram_enable(EXMC_BANK0_NORSRAM_REGION0);
}
```

STM32F1 FSMC 对应：`RCC_AHBPeriphClockCmd(RCC_AHBPeriph_FSMC, ENABLE)` +
`FSMC_NORSRAMInitTypeDef`（Bank1_NORSRAM1，`FSMC_MemoryDataWidth_8b`，
AccessMode_A）+ `FSMC_NORSRAMCmd`。

## 5. NVIC / RTOS / 低功耗

- 中断原则：只做全局优先级分组（GD32
  `nvic_priority_group_set(NVIC_PRIGROUP_PRE2_SUB2)`；STM32
  `NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2)`），**不使能具体 IRQ**
  （避免未注册 handler 落入默认死循环）；任务书列出的中断以注释给出使能
  建议（如 `nvic_irq_enable(USART5_IRQn, 1U, 0U)`）
- RTOS（`project.rtos != none`）：tick 源与 PendSV/SVC 由 port 层配置
  （port.c/portasm.s），`rtos_hw_init` 只做全局 NVIC 优先级分组
  （RTOS 要求全抢占优先级位，如 `NVIC_PRIGROUP_PRE4_SUB0` /
  `NVIC_PriorityGroup_4`），任务创建前调用
- 低功耗（`project.power.enabled`）：使能 PMU/PWR 时钟，模式与唤醒源由
  Agent 按 S2/S3/S4 决策（策略参考同目录 `low_power_strategies.md`）；
  深睡/STOP 唤醒后需重配系统时钟（HXTAL/PLL 会停振），注释指向 clock_init()

## 6. 禁止事项

- 不 include `app.h` / `driver_*.h` / `port_*.h` / `osal_*.h`
- 不含任何应用业务逻辑；不定义 Port/OSAL 接口；不生成 `port_impl_*.c`
- 不修改 IDE 工程文件（公共工具 ide_sync.py 职责）；代码只写 S5a 产物目录（任务书指定）
- 引脚、时钟、DMA、中断不得冲突；发现任务书数值可疑时在代码注释中标注
  并记入后续 capabilities.constraints（交由 validate 汇总）
