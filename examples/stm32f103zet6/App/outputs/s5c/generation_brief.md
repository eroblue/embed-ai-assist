# S5c Port 实现任务书（generation_brief）

> 由 prepare.py 生成（rule 轨）。Agent 按本任务书实现 Port/OSAL/Power 接口，
> 操作规范见 `skills/port-implementer/SKILL.md` 与 `references/`。
> 接口语义（错误码/超时/线程安全）按 S5b 的 `port-contract-and-app/references/port_design_principle.md` 同一约定。

## 1. 项目信息

- 平台：stm32f103zet6（文件命名后缀 `stm32f103zet6`）
- 架构：layered；RTOS：none；低功耗：未启用
- Port 接口头（S5b 产出，只读）：Drivers/Port/Inc/adc_port.h, Drivers/Port/Inc/gpio_port.h, Drivers/Port/Inc/par_port.h, Drivers/Port/Inc/timer_port.h, Drivers/Port/Inc/uart_port.h
- S5a 总入口：Drivers/BSP/Src/hal_init.c（init 产物 9 个源文件，可对接其初始化成果）
- 实现输出目录（PROJECT_LAYOUT.md 解析）：`Drivers/Port/Src/`

## 2. 用户设计输入（docs/s5c_design_input.md，优先级高于自动推断）

- 无（缺失/为空/全部 none）——Agent 基于 hardware_capabilities 与参考材料自主判断

## 3. S5a 能力清单摘要（实现 Port 的唯一硬件依据）

- 时钟：SYSCLK 72000000 Hz（内部 72MHz 直跑（S4 未发现外部晶振，未启 PLL））
- 外设能力 10 项：
  | 类型 | 实例 | 引脚 | 中断 | 能力标签 |
  |---|---|---|---|---|
  | uart | USART1 | tx=PA9，rx=PA10 | USART1 | 115200-8N1;tx-polling;rx-rxne-int |
  | par | FSMC_Bank1_NE4 | cs=PG12，rs=PG0，backlight=PB0 | - | 16bit-bus;cmd-addr-0x6C000000;data-addr-0x6C000800;mem-mapped-sync-write |
  | gpio | GPIOA | actuator_ctrl=PA4，key_mute_wkup=PA0，uart_tx=PA9，uart_rx=PA10 | - | output-pp;input |
  | gpio | GPIOB | led_exec=PB5，lcd_backlight=PB0，buzzer_pwm=PB8 | - | output-pp |
  | gpio | GPIOE | led_run=PE5，key_switch=PE3，key_mode=PE4，key_reserved=PE2 | - | output-pp;input-pull-up |
  | gpio | GPIOF | light_sensor_ao=PF8 | - | analog-input |
  | gpio | GPIOG | dht11_data=PG11，fsmc_ne4_cs=PG12，fsmc_a10_rs=PG0 | - | input-pull-up;af-pp-50m |
  | adc | ADC3 | in6=PF8 | - | 12bit;soft-trigger;sample-55.5cyc;ref-vdd;right-align |
  | timer | TIM4 | ch3=PB8 | - | pwm-2khz;psc71-arr499;buzzer-pwm-occupied;duty-by-TIM_SetCompare3 |
  | timer | SysTick | - | SysTick | 24bit-downcounter;clk-source-hclk-or-div8;available-for-system-tick;available-for-delay-us |
- 约束：58 个已连接引脚网络名无语义（如 PE2），未生成 GPIO 配置，待 AI/人工补充
- 约束：ADC 差异：S5b manifest 写 ADC1_IN1(PA1)，S5a 实际初始化 ADC3_IN6(PF8)（战舰板光敏电阻真实接法）；S5c 实现按实际硬件 ADC3/PF8 对接
- 约束：蜂鸣器差异：S5b manifest 按简单 GPIO 建模（PB8 active_level=1），S5a 实际配置 TIM4_CH3 PWM（2kHz）；S5c 的 gpio_port_set_active(buzzer) 应映射 TIM_SetCompare3(TIM4, 250=响/0=停) 而非直写 PB8
- 约束：10ms 节拍载体：TIM4 已被蜂鸣器 PWM 占用，timer_port 的 system_tick 实例应使用 SysTick（见 REC-005）
- 约束：key_mute(PA0/WK_UP)：S5a gpio_init 未配置 PA0（S5b 设计输入指定），S5c gpio 实现需自行补配 PA0 下拉输入（按 manifest config pull=down）
- 约束：PE2 已被 S5a 配置为按键输入但 S5b manifest 未使用（保留）
- 约束：FSMC 数据线 D0~D15 分布在 PD/PE 口（复用推挽 50MHz），由 S5a fsmc_init 统一配置，S5c 不重复配置

## 4. S5b manifest 接口清单（实现 Port 的唯一接口依据）

### Drivers/Port/Inc/uart_port.h（外设 uart）

- 说明：UART Port 接口：环境数据 JSON 上报 + 上位机指令接收通道
- **实现落点：`port_impl_uart_stm32f103zet6.c`**（include 对应 Port 头，只实现本外设接口）
- 逻辑实例 `report_uart`：5s 周期 JSON 环境数据上报 + 上位机指令接收（USART1_IRQn 接收中断，抢占2/子0），115200-8N1；S4 facts 引脚未吸附，按设计输入硬件表映射
  - hw_instance：USART1（PA9=TX / PA10=RX）（来源 design_input）；config：{'baudrate': 115200, 'data_bits': 8, 'parity': 0, 'stop_bits': 1}
- 接口：
  - `uart_port_init`：int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg) —— 绑定逻辑实例与配置（对接 S5a uart_init 成果）
  - `uart_port_write`：int32_t uart_port_write(uart_port_id_t id, const uint8_t *buf, uint16_t len)（isr_safe） —— 同步拷贝语义发送，返回发送字节数；失败重试由调用方处理
  - `uart_port_set_rx_cb`：int32_t uart_port_set_rx_cb(uart_port_id_t id, uart_port_rx_cb_t cb, void *user_data)（回调经 uart_port_rx_cb_t） —— 注册接收回调（cb 为 NULL 取消注册）；未注册时中断仍搬运入环形缓冲，仅不通知
  - `uart_port_read`：int32_t uart_port_read(uart_port_id_t id, uint8_t *buf, uint16_t len)（isr_safe） —— 非阻塞读环形缓冲中可用数据（0=暂无数据），返回实际读取字节数
  - `uart_port_deinit`：int32_t uart_port_deinit(uart_port_id_t id) —— 释放实例全部资源
- 回调约定：`uart_port_rx_cb_t` = void (*)(uart_port_id_t id, const uint8_t *data, uint16_t len, void *user_data)（上下文 isr）—— 接收数据回调：本工程 RTOS=none，实现层在 USART1 接收中断内直接调用；只做置标志/短拷贝，data 仅回调期间有效
- 注：write 同步拷贝（返回后 buf 可复用）
- 注：接收中断驱动：ISR 搬运入环形缓冲 + 通知回调；read 非阻塞取数据（两种方式可并用）
- 注：指令协议未定义，本期只打通接收通道，APP 侧不消费（不注册回调、不读）
- 注：hw_instance 由设计输入硬件表映射；换板只改本 manifest，不改代码

### Drivers/Port/Inc/par_port.h（外设 par）

- 说明：16 位并行总线 Port 接口：TFT_LCD 显存写入通道
- **实现落点：`port_impl_par_stm32f103zet6.c`**（include 对应 Port 头，只实现本外设接口）
- 逻辑实例 `lcd_bus`：TFT_LCD（ILI9341 类 240x320）显存总线；命令/数据由地址线区分（对接 S5a fsmc_lcd_init 总线成果）；竖屏方向与 Gamma 序列由 driver_lcd 承载
  - hw_instance：FSMC Bank1-NE4（命令 0x6C000000 / 数据 0x6C000800，PG12=CS、PG0=RS，背光 PB0）（来源 design_input）；config：{'bus_width_bits': 16}
- 接口：
  - `par_port_init`：int32_t par_port_init(par_port_id_t id) —— 绑定逻辑实例（对接 S5a fsmc_lcd_init 总线成果）
  - `par_port_write_cmd`：int32_t par_port_write_cmd(par_port_id_t id, uint16_t cmd)（isr_safe） —— 写一个命令字（16 位并口下低 8 位有效按器件协议）
  - `par_port_write_data`：int32_t par_port_write_data(par_port_id_t id, uint16_t data)（isr_safe） —— 写一个数据字
  - `par_port_write_data_block`：int32_t par_port_write_data_block(par_port_id_t id, const uint16_t *buf, uint32_t len)（isr_safe） —— 数据字块流式写（同步拷贝语义，返回后 buf 可复用；像素流用）
  - `par_port_deinit`：int32_t par_port_deinit(par_port_id_t id) —— 释放实例全部资源
- 注：存储器映射同步写直达，无缓冲/DMA 语义暴露
- 注：命令/数据地址映射只登记在 manifest 数据侧，换板/换平台只改本 manifest 与 S5a 成果

### Drivers/Port/Inc/gpio_port.h（外设 gpio）

- 说明：GPIO Port 接口：指示灯/蜂鸣器/按键/DHT11 单总线（7 个逻辑引脚）
- **实现落点：`port_impl_gpio_stm32f103zet6.c`**（include 对应 Port 头，只实现本外设接口）
- 逻辑实例 `led_exec`：执行器指示灯（亮=执行器开）；LED0，低电平点亮
  - hw_instance：PB5（来源 design_input）；config：{'dir': 'output', 'pull': 'none', 'init_level': 1, 'active_level': 0}
- 逻辑实例 `led_run`：运行指示灯（心跳/快闪/慢闪）；LED1，低电平点亮
  - hw_instance：PE5（来源 design_input）；config：{'dir': 'output', 'pull': 'none', 'init_level': 1, 'active_level': 0}
- 逻辑实例 `buzzer`：告警蜂鸣器（1s 响/1s 停，静音门控）；高电平导通
  - hw_instance：PB8（来源 design_input）；config：{'dir': 'output', 'pull': 'none', 'init_level': 0, 'active_level': 1}
- 逻辑实例 `key_mode`：模式切换按键（KEY0，外部上拉，按下=低）
  - hw_instance：PE4（来源 design_input）；config：{'dir': 'input', 'pull': 'up', 'init_level': 0, 'active_level': 0}
- 逻辑实例 `key_switch`：手动开关按键（KEY1，外部上拉，按下=低）
  - hw_instance：PE3（来源 design_input）；config：{'dir': 'input', 'pull': 'up', 'init_level': 0, 'active_level': 0}
- 逻辑实例 `key_mute`：静音切换按键（WK_UP，外部下拉，按下=高）
  - hw_instance：PA0（来源 design_input）；config：{'dir': 'input', 'pull': 'down', 'init_level': 1, 'active_level': 1}
- 逻辑实例 `dht11_data`：DHT11 单总线数据（外部上拉；运行时 set_dir 换向）
  - hw_instance：PG11（来源 design_input）；config：{'dir': 'input', 'pull': 'none', 'init_level': 0, 'active_level': 1}
- 接口：
  - `gpio_port_init`：int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg) —— 绑定逻辑引脚与配置（含有效电平 active_level）
  - `gpio_port_deinit`：int32_t gpio_port_deinit(gpio_port_id_t id) —— 释放逻辑引脚资源
  - `gpio_port_read`：int32_t gpio_port_read(gpio_port_id_t id, gpio_port_level_t *level)（isr_safe） —— 读输入电平（输出引脚读回实际输出）
  - `gpio_port_write`：int32_t gpio_port_write(gpio_port_id_t id, gpio_port_level_t level)（isr_safe） —— 写输出电平
  - `gpio_port_toggle`：int32_t gpio_port_toggle(gpio_port_id_t id)（isr_safe） —— 翻转输出
  - `gpio_port_set_dir`：int32_t gpio_port_set_dir(gpio_port_id_t id, gpio_port_dir_t dir) —— [扩展] 运行时切换方向（DHT11 单总线时序）
  - `gpio_port_set_active`：int32_t gpio_port_set_active(gpio_port_id_t id, uint8_t active)（isr_safe） —— [扩展] 按有效电平写（active!=0 激活）
  - `gpio_port_read_active`：int32_t gpio_port_read_active(gpio_port_id_t id, uint8_t *active)（isr_safe） —— [扩展] 按有效电平读（激活=1）
- 注：有效电平语义：active_level 由实例 config 固化到实现，APP/Driver 只用 active 语义
- 注：按键为 10ms 轮询去抖，无 EXTI（边沿中断接口已裁剪）
- 注：DHT11_DATA 需运行时换向：起始信号输出拉低 18ms 后切回输入读响应

### Drivers/Port/Inc/adc_port.h（外设 adc）

- 说明：ADC Port 接口：光照传感器模拟量
- **实现落点：`port_impl_adc_stm32f103zet6.c`**（include 对应 Port 头，只实现本外设接口）
- 逻辑实例 `light_sensor`：光照分压网络采样（光敏电阻模块 AO）；APP 侧 light% = raw_mv*100/ref_mv
  - hw_instance：ADC1_IN1（PA1）（来源 design_input）；config：{'ref': 'vdd', 'ref_mv': 3300, 'avg_count': 8}
- 接口：
  - `adc_port_init`：int32_t adc_port_init(adc_port_id_t id, const adc_port_cfg_t *cfg) —— 绑定逻辑通道与配置（对接 S5a adc_init 成果）
  - `adc_port_sample_mv`：int32_t adc_port_sample_mv(adc_port_id_t id, uint16_t *raw_mv) —— 同步单次采样（含 avg_count 次过采样均值），输出毫伏值
  - `adc_port_deinit`：int32_t adc_port_deinit(adc_port_id_t id) —— 释放逻辑通道资源
- 注：基准换算在 Port 内完成，APP 不感知分辨率/通道号
- 注：过采样均值：8 次（去抖动）

### Drivers/Port/Inc/timer_port.h（外设 timer）

- 说明：Timer Port 接口：系统 10ms 节拍 + µs 级短延时
- **实现落点：`port_impl_timer_stm32f103zet6.c`**（include 对应 Port 头，只实现本外设接口）
- 逻辑实例 `system_tick`：10ms 周期节拍（主循环软轮询调度）；delay_us 供 DHT11 位时序与 LCD 上电延时
  - hw_instance：**null（Agent 按 capabilities/设计输入选定，并在文件头注释登记）**（来源 design_input）；config：{'period_ms': 10}
- 接口：
  - `timer_port_init`：int32_t timer_port_init(timer_port_id_t id) —— 绑定逻辑定时器
  - `timer_port_start_periodic`：int32_t timer_port_start_periodic(timer_port_id_t id, uint32_t period_ms, timer_port_cb_t cb, void *user_data)（回调经 timer_port_cb_t） —— 启动周期定时（重复触发；重复启动返回 PORT_ERR_STATE）
  - `timer_port_stop`：int32_t timer_port_stop(timer_port_id_t id) —— 停止定时（幂等）
  - `timer_port_delay_us`：int32_t timer_port_delay_us(uint32_t delay_us) —— [扩展] 微秒级忙等延时（DHT11 位时序 26~70µs / LCD 上电延时 120ms、20ms）；仅任务上下文
  - `timer_port_deinit`：int32_t timer_port_deinit(timer_port_id_t id) —— 释放逻辑定时器资源
- 回调约定：`timer_port_cb_t` = void (*)(timer_port_id_t id, void *user_data)（上下文 isr）—— 周期到期回调：只做置标志/计数，长逻辑投主循环（app_on_tick 仅置标志）
- 注：hw_instance=null：设计输入仅约定 10ms 主循环节拍，未指定硬件定时器，S5c 按 hardware_capabilities 匹配（建议 SysTick 或空闲通用定时器，见 REC-005）
- 注：delay_us 实现基于定时器计数（SysTick/总线时钟皆可），禁止在中断内调用

## 5. 待生成文件清单（按外设一文件，跳过'用户已修改'文件）

- `port_impl_uart_stm32f103zet6.c`
- `port_impl_par_stm32f103zet6.c`
- `port_impl_gpio_stm32f103zet6.c`
- `port_impl_adc_stm32f103zet6.c`
- `port_impl_timer_stm32f103zet6.c`

## 6. 映射要点与规范引用

- HAL API ↔ Port 接口：`references/hal_mapping_guide.md`（**核对将要用到的 API 函数名/枚举名/时钟使能宏，不确定的留 `/* TODO: */` 注释，不臆造 API**）
- 实现模式（状态管理/环形缓冲/错误码映射/DMA 骨架）：`references/port_impl_pattern.md`
- 中断安全规范（**ISR 内回调调用前必须判空**）：`references/isr_safety_rules.md`
- 实现示例：`assets/port_impl_example.c`
- S5a init 产物清单（对接其初始化成果，不重复 HAL 初始化）：
  - `Drivers/BSP/Inc/adc_init.h`
  - `Drivers/BSP/Inc/clock_init.h`
  - `Drivers/BSP/Inc/dht11_init.h`
  - `Drivers/BSP/Inc/fsmc_init.h`
  - `Drivers/BSP/Inc/gpio_init.h`
  - `Drivers/BSP/Inc/hal_init.h`
  - `Drivers/BSP/Inc/nvic_init.h`
  - `Drivers/BSP/Inc/tim_init.h`
  - `Drivers/BSP/Inc/uart_init.h`

## 7. 禁止事项（硬约束）

- 不修改 S5a/S5b 产出的任何文件（含 `*_port.h` / `osal.h` / `power_port.h` 接口定义）
- 不写任何应用业务逻辑；不生成 HAL 初始化代码（S5a 职责，Port 实现只做绑定与读写操作）
- 必须依据 manifest 数据侧实现，不得硬解析 C 头文件；硬件只依据 hardware_capabilities（及设计输入/S5a init 产物核对），禁止直接读取 S3/S4 数据
- 不得把所有 Port 实现塞进一个文件（按外设拆分）；代码只写入任务书给定的产物目录
- ISR 内调用回调前必须判断函数指针非 NULL（未注册时清标志直接返回）；DMA 隐藏在 Port 实现内
- 实例状态用文件内 static 数组按 instance id 索引，不动态分配
- **不重写'用户已修改'清单中的文件**（skip-if-modified）

## 8. 执行步骤（详见 SKILL.md）

1. 通读 SKILL.md 与上述 references/；读 SDK 头文件核对 API 名（`/* TODO: */` 标注不确定项）
2. 按第 5 节清单逐文件编写实现（每文件只实现对应外设接口，include S5b 的 Port 头）
4. 运行 validate.py 终验；失败按报告修复后重跑

## 9. 待用户确认项（recommendations.json）

- REC-001（system_tick 硬件实例未指定）：manifest 中 system_tick 的 hw_instance=null（10ms 周期节拍（主循环软轮询调度）；delay_us 供 DHT11 位时序与 LCD 上电延时） → 核对 Agent 选定的实例并在 s5c_design_input.md 登记，固化选择
