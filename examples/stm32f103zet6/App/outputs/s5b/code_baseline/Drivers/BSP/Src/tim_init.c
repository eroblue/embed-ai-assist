/* tim_init.c - TIM4 蜂鸣器 PWM 初始化：2kHz，初始占空比 0（S5a hardware-initializer 生成，stm32f103zet6） */
#include "tim_init.h"
#include "stm32f10x.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"
#include "stm32f10x_tim.h"

void tim4_init(void)
{
    GPIO_InitTypeDef gpio;
    TIM_TimeBaseInitTypeDef tim_base;
    TIM_OCInitTypeDef tim_oc;

    /* PB8 - BEEP 板载蜂鸣器（TIM4_CH3，复用推挽输出） */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_8;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);

    /* TIM4 时钟：APB1 36MHz × 2（APB1 分频 ≠ 1 时定时器内部倍频）= 72MHz
       PSC = 71 → 计数时钟 1MHz；ARR = 499 → PWM 频率 2kHz（docs/s5a_design_input.md） */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM4, ENABLE);
    tim_base.TIM_Prescaler = 71;
    tim_base.TIM_CounterMode = TIM_CounterMode_Up;
    tim_base.TIM_Period = 499;
    tim_base.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseInit(TIM4, &tim_base);

    /* CH3 PWM1 模式，初始 CCR = 0（占空比 0%，蜂鸣器停）。
       启停归应用层：响（50%）= TIM_SetCompare3(TIM4, 250)；
       停（0%）  = TIM_SetCompare3(TIM4, 0) */
    tim_oc.TIM_OCMode = TIM_OCMode_PWM1;
    tim_oc.TIM_OutputState = TIM_OutputState_Enable;
    tim_oc.TIM_Pulse = 0;
    tim_oc.TIM_OCPolarity = TIM_OCPolarity_High;
    TIM_OC3Init(TIM4, &tim_oc);

    TIM_OC3PreloadConfig(TIM4, TIM_OCPreload_Enable);
    TIM_ARRPreloadConfig(TIM4, ENABLE);
    TIM_Cmd(TIM4, ENABLE);
}
