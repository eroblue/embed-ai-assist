/* clock_init.h - 系统时钟初始化（S5a hardware-initializer 生成，FT61F143A-RB） */
#ifndef CLOCK_INIT_H
#define CLOCK_INIT_H

/* FT61F14X：无 PLL/总线分频，HIRC 16MHz 直跑（S4 未发现外部晶振） */
#define CLOCK_SYSCLK_HZ   16000000UL

void clock_init(void);

#endif /* CLOCK_INIT_H */
