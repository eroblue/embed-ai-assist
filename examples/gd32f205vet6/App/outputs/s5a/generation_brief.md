# S5a 代码生成任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书在 `Drivers/BSP/Src/` 写 .c、`Drivers/BSP/Inc/` 写 .h，
> 生成规范见 `skills/hardware-initializer/references/init_code_templates.md`。
> 引脚/实例/时钟数值均已从 S3/S4 事实确定，直接采用，不要自行改推。

## 1. 项目信息

- MCU：GD32F205VET6,LQFP100（platform: gd32f205vet6）
- 架构：layered；RTOS：none；低功耗：未启用
- 标准外设库：`E:\skills\EmbedSoftAutomaticProject\embed-ai-assist\platforms\gd32f205vet6\sdk\std_periph_lib`（来源 config.stdperiph_lib_path）——生成前读其头文件确认 API/枚举名
- 平台主头文件：`gd32f20x.h`（外设模块 .c 需 include）
- 用户设计输入：`docs/s5a_design_input.md`（DMA 模式/特殊引脚等语义按原文校正，rule 轨只消费了波特率/主频）

## 2. 时钟配置（已计算，直接采用）

- HSE：16MHz（来源 S4 硬件事实）
- SYSCLK：32MHz = HSE × PLL2
- AHB：32MHz；APB1：32MHz；APB2：32MHz
- LSE：32.768kHz（RTC 时钟源，clock_init 中使能并选为 RTC 时钟）

## 3. 外设使用清单（引脚来自 S4 facts + S3 AF 表）

### UART
- USART5：TX=PC6（net DEBUG-TXD），RX=未连接（仅 TX），115200-8N1，中断：USART5

### SPI
- SPI2（主模式，8bit，软 NSS）：MISO=PC11，MOSI=PC12，NSS=PA15，SCK=PC10；**引脚来自 AF remap，需使能 AFIO 时钟并做重映射**

### PWM
- TIMER0 TIMER_CH0：输出 PA8（net LCD-PWM），定时器时钟 32MHz，默认 1kHz/50% 占空比

### FSMC/EXMC（LCD 并口）
- 数据宽度：8 位（按数据线网络名判定）；bank 建议 NE1（基址 0x60000000）
- 引脚：PE7（LCD_DB4），PE8（LCD_DB5），PE9（LCD_DB6），PE10（LCD_DB7），PD14（LCD_DB0），PD15（LCD_DB1），PD0（LCD_DB2），PD1（LCD_DB3），PD7（LCD_CS）
- 时序取保守默认值（慢速，保证点亮），代码中注释标注需按 LCD 驱动手册调整

### GPIO（按端口分组）
- PA0：`IN_FLOATING`（net NetU1_23）
- PD0：`AF_PP`（net LCD_DB2 - FSMC/EXMC）
- PD1：`AF_PP`（net LCD_DB3 - FSMC/EXMC）
- PD7：`AF_PP`（net LCD_CS - FSMC/EXMC）
- PD14：`AF_PP`（net LCD_DB0 - FSMC/EXMC）
- PD15：`AF_PP`（net LCD_DB1 - FSMC/EXMC）
- PE7：`AF_PP`（net LCD_DB4 - FSMC/EXMC）
- PE8：`AF_PP`（net LCD_DB5 - FSMC/EXMC）
- PE9：`AF_PP`（net LCD_DB6 - FSMC/EXMC）
- PE10：`AF_PP`（net LCD_DB7 - FSMC/EXMC）

### 中断：USART5, SPI2（只做 NVIC 分组，不使能具体 IRQ，注释给使能建议）

### 跳过的引脚（晶振/电源/调试/无语义）：PE2, PE3, PE4, PE5, PE6, VBAT(), PC13-RTC_AF1, PC14-OSC32IN, PC15-OSC32OUT, VSS_5(GND-T), VDD_5(+3.3V-T), OSC_IN(16M-IN), OSC_OUT(16M-OUT), NRST(NRST), VSSA(GND-T), VREF-(GND-T), VREF+(+3.3V-T), VDDA(+3.3V-T), PA3, VSS_4(GND-T)...

## 4. 生成要求

### 文件清单（Drivers/BSP/Src/ 下 .c + Drivers/BSP/Inc/ 下 .h，每模块成对）

`clock_init, fsmc_init, gpio_init, nvic_init, pwm_init, spi_init, uart_init` + 总入口 `hal_init`（只做汇总调用）

### 增量模式（本轮生成范围）

- **无变更模块**：本轮输入与上轮一致，无需生成代码，直接运行 validate.py 收尾

### 硬性规则

1. 落盘位置：`.c` 写入 `Drivers/BSP/Src/`，`.h` 写入 `Drivers/BSP/Inc/`（目录已由 prepare 创建，路径来自 docs/PROJECT_LAYOUT.md，勿写其他目录）
2. 命名：`<module>_init.c/h`；每实例一个函数（如 `uart_usart5_init`），模块级 `<module>_init()` 汇总调用
3. 头文件带 include guard；.c 首行注释 `/* <module>_init.c - <说明>（S5a hardware-initializer 生成，<MCU>） */`
4. 调用顺序：`clock_init() → gpio_init() → nvic_init() → 各外设 init() → rtos_hw_init()/power_init()（如有）`
5. 中断：只做 NVIC 优先级分组，不使能具体 IRQ（避免未注册 handler 落入默认死循环），使能建议以注释生成
6. 平台 API 以标准外设库头文件为准（宏/枚举名逐一核对），不确定的留 TODO 注释，不臆造 API
7. FSMC 引脚复用（AF_PP）在 gpio_init.c 完成，fsmc_init.c 只有 bank/时序本体
8. 批量写入：单轮响应内并行发出多个文件的写入调用（建议 4 文件/轮，即 2 模块的 .c/.h），
   全部模块写完后统一核对与校验——组稿与核对分离，避免逐文件"写→等结果→再写"的往返开销

## 5. 禁止事项

- 不 include `app.h` / `driver_*.h` / `port_*.h` / `osal_*.h`，不含任何应用业务逻辑
- 不定义 Port/OSAL 接口（S5b 职责），不生成 `port_impl_*.c`（S5c 职责）
- 不修改 IDE 工程文件（.uvprojx/.ewp 等）——同步由公共工具 skills/_shared/scripts/ide_sync.py 完成
- 不把代码写进 outputs/，不把数据写进 src/；不修改 S3/S4 产物与 config.json
- 不把所有初始化塞进单文件；引脚/时钟/DMA/中断不得冲突

## 6. 数据来源（需要深查时再读）

- S4 硬件事实：`E:/skills/EmbedSoftAutomaticProject/embed-ai-assist/examples/gd32f205vet6/App/outputs/circuit_facts.json`
- S3 芯片引脚：`outputs/chip_info/pins.json`；外设：`outputs/chip_info/peripherals.json`
- SDK CMSIS 头：`platforms/gd32f205vet6/sdk/cmsis/gd32f20x.h`
- SVD（寄存器/中断名核对）：`platforms/gd32f205vet6/svd/GD32F20x.svd`

生成完成后运行 `validate.py` 校验；失败按报告修复后重跑。