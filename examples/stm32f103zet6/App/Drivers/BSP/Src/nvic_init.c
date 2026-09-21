/* nvic_init.c - NVIC 中断优先级配置（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "nvic_init.h"

/**
 * @brief NVIC 全局优先级分组
 *        分组 2：2 位抢占（0-3）+ 2 位响应（0-3）
 *        只做分组，不使能具体 IRQ——handler 未注册前使能会落入默认死循环
 */
void nvic_init(void)
{
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);

    /* 使能建议（各驱动注册 handler 后按需开启，按紧急程度分配抢占 0-3）：
       USART1 / USART2 / UART4：串口收发中断，建议抢占 1
       SPI2：数据收发中断，建议抢占 2 */
}
