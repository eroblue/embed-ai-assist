/* gpio_init.h - 板载 GPIO 初始化（S5a hardware-initializer 生成） */
#ifndef GPIO_INIT_H
#define GPIO_INIT_H

/* 配置清单（docs/s5a_design_input.md）：
 *   PB5/PE5 - DS0/DS1 指示灯（推挽输出，初始灭）
 *   PA4     - 执行器控制（推挽输出，初始关 = 低）
 *   PE2/PE3/PE4 - 按键（上拉输入，按下为低）
 *   PB0     - LCD 背光（推挽输出，初始亮）
 *   FSMC 总线（复用推挽 50MHz）：D0~D15、NOE/NWE、A10(RS)、NE4(CS)
 * 外设自身引脚（PB8 蜂鸣器 / PF8 光照 / PA9/PA10 串口 / PG11 DHT11）
 * 分别在 tim_init / adc_init / uart_init / dht11_init 中配置 */
void gpio_init(void);

#endif /* GPIO_INIT_H */
