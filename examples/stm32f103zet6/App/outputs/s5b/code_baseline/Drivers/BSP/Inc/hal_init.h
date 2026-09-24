/* hal_init.h - 硬件初始化总入口（S5a hardware-initializer 生成） */
#ifndef HAL_INIT_H
#define HAL_INIT_H

/* 汇总调用（顺序见 docs/s5a_design_input.md）：
 * clock_init → nvic_init → gpio_init → tim4_init → adc3_init
 * → fsmc_lcd_init → usart1_init → dht11_init */
void hal_init(void);

#endif /* HAL_INIT_H */
