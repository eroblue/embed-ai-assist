/* nvic_init.c - NVIC 中断优先级分组（S5a hardware-initializer 生成，stm32f103zet6） */
#include "nvic_init.h"
#include "stm32f10x.h"
#include "misc.h"

void nvic_init(void)
{
    /* 只做全局优先级分组：PriorityGroup_2（2 位抢占 + 2 位子优先级）。
       本层不使能具体 IRQ——未注册 handler 前使能会落入默认死循环。 */
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);

    /* 使能建议（应用层注册 USART1_IRQHandler 后执行）：
     *   NVIC_InitTypeDef NVIC_InitStructure;
     *   NVIC_InitStructure.NVIC_IRQChannel = USART1_IRQn;
     *   NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 2;
     *   NVIC_InitStructure.NVIC_IRQChannelSubPriority = 0;
     *   NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
     *   NVIC_Init(&NVIC_InitStructure);
     * （docs/s5a_design_input.md 中断配置表：USART1_IRQn 抢占 2 / 子 0，
     *  用于上位机指令接收；其余外设均轮询，无中断） */
}
