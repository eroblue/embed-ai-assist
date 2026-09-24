# S5a 代码生成任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书在 `Drivers/BSP/Src/` 写 .c、`Drivers/BSP/Inc/` 写 .h，
> 生成规范见 `skills/hardware-initializer/references/init_code_templates.md`。
> 引脚/实例/时钟数值均已从 S3/S4 事实确定，直接采用，不要自行改推。

## 1. 项目信息

- MCU：stm32f103zet6（platform: stm32f103zet6）
- 架构：layered；RTOS：none；低功耗：未启用
- 标准外设库：`E:\skills\EmbedSoftAutomaticProject\embed-ai-assist\platforms\stm32f103zet6\sdk\std_periph_lib`（来源 config.stdperiph_lib_path）——生成前读其头文件确认 API/枚举名
- 平台主头文件：`stm32f10x.h`（外设模块 .c 需 include）
- 用户设计输入：`docs/s5a_design_input.md`（DMA 模式/特殊引脚等语义按原文校正，rule 轨只消费了波特率/主频）

## 2. 时钟配置（已计算，直接采用）

- HSE：未发现（按内部 RC 直跑，频率见 SYSCLK）（来源 S4 硬件事实）
- SYSCLK：72MHz（内部 RC）
- AHB：72MHz；APB1：72MHz；APB2：72MHz

## 3. 外设使用清单（引脚来自 S4 facts + S3 AF 表）

### 跳过的引脚（晶振/电源/调试/无语义）：(PE2), (PE3), (PE4), (PE5), (PE6), VBAT(), A(SDIO_SCK), A(Y132.768K), A(), (PF0), (PF0), (PF2), (PF3), (PF4), (PF5), (PF6), (PF7), (PF8), (PF9), (PF10)...

## 4. 生成要求

### 文件清单（Drivers/BSP/Src/ 下 .c + Drivers/BSP/Inc/ 下 .h，每模块成对）

`clock_init, nvic_init` + 总入口 `hal_init`（只做汇总调用）

### 增量模式（本轮生成范围）

- 全量模式（首次运行/配置大变）：重写全部模块 `clock_init, hal_init, nvic_init`

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

- S4 硬件事实：`E:/skills/EmbedSoftAutomaticProject/embed-ai-assist/examples/stm32f103zet6/App/outputs/circuit_facts.json`
- S3 芯片引脚：`outputs/chip_info/pins.json`；外设：`outputs/chip_info/peripherals.json`
- SDK CMSIS 头：`platforms/stm32f103zet6/sdk/cmsis/stm32f10x.h`
- SVD（寄存器/中断名核对）：`platforms/stm32f103zet6/svd/STM32F103xx.svd`

生成完成后运行 `validate.py` 校验；失败按报告修复后重跑。