/* clock_init.c - 系统时钟初始化：HSE 8MHz + PLL×9 → SYSCLK 72MHz（S5a hardware-initializer 生成，stm32f103zet6） */
#include "clock_init.h"
#include "stm32f10x.h"
#include "stm32f10x_flash.h"
#include "stm32f10x_rcc.h"

void clock_init(void)
{
    /* FLASH 等待周期：72MHz 需 2WS，须先于主频切换配置（docs/s5a_design_input.md） */
    FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
    FLASH_SetLatency(FLASH_Latency_2);

    /* HSE 外部晶振 8MHz（板载） */
    RCC_HSEConfig(RCC_HSE_ON);
    if (RCC_WaitForHSEStartUp() != SUCCESS)
    {
        /* HSE 未起振：保持复位默认 HSI 8MHz 直跑，避免死等。
           此时按 72MHz 计算的外设参数（波特率/PWM）将失准，需检查晶振电路 */
        return;
    }

    /* PLL：HSE × 9 = 72MHz */
    RCC_PLLConfig(RCC_PLLSource_HSE_Div1, RCC_PLLMul_9);

    /* 总线分频：AHB/1 = 72MHz；APB1/2 = 36MHz；APB2/1 = 72MHz
       （APB1 分频 ≠ 1 时 TIM2~7 内部 ×2，定时器时钟仍为 72MHz） */
    RCC_HCLKConfig(RCC_HCLK_Div1);
    RCC_PCLK1Config(RCC_HCLK_Div2);
    RCC_PCLK2Config(RCC_HCLK_Div1);

    RCC_PLLCmd(ENABLE);
    while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET) { }

    RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
    while (RCC_GetSYSCLKSource() != 0x08) { }  /* 0x08 = PLL 已作为 SYSCLK */

    SystemCoreClockUpdate();
}
