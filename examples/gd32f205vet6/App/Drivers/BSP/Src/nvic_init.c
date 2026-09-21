/* nvic_init.c - NVIC 初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "nvic_init.h"
#include "gd32f20x.h"

void nvic_init(void)
{
    nvic_priority_group_set(NVIC_PRIGROUP_PRE2_SUB2);

    /* 建议在注册中断服务函数后使能: nvic_irq_enable(USART5_IRQn, 1U, 0U);（默认不使能，避免未注册 handler 落入默认死循环） */
    /* 建议在注册中断服务函数后使能: nvic_irq_enable(SPI2_IRQn, 1U, 0U);（默认不使能，避免未注册 handler 落入默认死循环） */
}
