/* tim_init.h - TIM4 蜂鸣器 PWM 初始化（S5a hardware-initializer 生成） */
#ifndef TIM_INIT_H
#define TIM_INIT_H

/* TIM4_CH3 / PB8，2kHz（PSC=71，ARR=499，定时器时钟 72MHz）；
 * 初始占空比 0（停），启停由应用层经 TIM_SetCompare3(TIM4, x) 控制
 * （响 50% = 250，停 = 0） */
void tim4_init(void);

#endif /* TIM_INIT_H */
