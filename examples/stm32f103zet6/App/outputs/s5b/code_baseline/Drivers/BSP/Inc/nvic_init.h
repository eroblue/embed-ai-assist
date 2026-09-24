/* nvic_init.h - NVIC 中断优先级分组（S5a hardware-initializer 生成） */
#ifndef NVIC_INIT_H
#define NVIC_INIT_H

/* 分组：PriorityGroup_2（2 位抢占 + 2 位子优先级）；
 * 具体 IRQ 使能建议见 nvic_init.c 注释（USART1_IRQn 抢占 2 / 子 0） */
void nvic_init(void);

#endif /* NVIC_INIT_H */
