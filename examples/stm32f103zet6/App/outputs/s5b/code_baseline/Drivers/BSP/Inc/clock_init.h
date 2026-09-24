/* clock_init.h - 系统时钟初始化（S5a hardware-initializer 生成） */
#ifndef CLOCK_INIT_H
#define CLOCK_INIT_H

/* 时钟树（docs/s5a_design_input.md）：
 *   HSE 8MHz + PLL×9 → SYSCLK 72MHz
 *   AHB /1 = 72MHz（HCLK）
 *   APB1/2 = 36MHz（PCLK1，定时器倍频后 72MHz）
 *   APB2/1 = 72MHz（PCLK2）
 *   FLASH 2WS，不使用 HSI/MCO */
void clock_init(void);

#endif /* CLOCK_INIT_H */
