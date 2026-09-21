/* clock_init.c - 系统时钟初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "clock_init.h"

/**
 * @brief 系统时钟配置
 *        HSE 8MHz × PLL 4 = 32MHz（PLLMul_4 / SRC_HSE / XTPRE_DIV1）
 *        AHB = 32MHz；APB1 = 32MHz（Div1，TIM2-7 时钟同频不 ×2）；APB2 = 32MHz
 *        ADCCLK = PCLK2/4 = 8MHz；FLASH 1 等待周期 + 预取使能
 *        LSE 32.768kHz → RTC（PWR 备份域解锁序列）
 */
void clock_init(void)
{
    /* FLASH：32MHz 需 1 个等待周期，使能预取缓冲区 */
    FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
    FLASH_SetLatency(FLASH_Latency_1);

    /* 使能 HSE（板载 8MHz 晶振）并等待启动完成 */
    RCC_HSEConfig(RCC_HSE_ON);
    if (RCC_WaitForHSEStartUp() == SUCCESS)
    {
        /* PLL：时钟源 HSE 不分频（XTPRE_DIV1），倍频 ×4 = 32MHz */
        RCC_PLLConfig(RCC_PLLSource_HSE_Div1, RCC_PLLMul_4);
        /* 使能 PLL */
        RCC_PLLCmd(ENABLE);
        /* 等待 PLL 锁定 */
        while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET)
        {
        }

        /* SYSCLK 切换到 PLL（32MHz），等待切换生效（0x08 = PLL 已作系统时钟） */
        RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
        while (RCC_GetSYSCLKSource() != 0x08)
        {
        }

        /* AHB 分频 1：HCLK = SYSCLK = 32MHz */
        RCC_HCLKConfig(RCC_SYSCLK_Div1);

        /* APB1 分频 1：PCLK1 = 32MHz（TIM2-7 挂 APB1，分频为 1 时时钟不 ×2） */
        RCC_PCLK1Config(RCC_HCLK_Div1);

        /* APB2 分频 1：PCLK2 = 32MHz */
        RCC_PCLK2Config(RCC_HCLK_Div1);

        /* ADCCLK = PCLK2/4 = 8MHz（ADC 时钟上限 14MHz） */
        RCC_ADCCLKConfig(RCC_PCLK2_Div4);
    }
    else
    {
        /* HSE 启动失败：回退 HSI 8MHz（复位默认系统时钟）继续运行，
           不使能 PLL、不切换 SYSCLK，外设波特率需按 HSI 8MHz 重新计算 */
    }

    /* 使能 PWR/BKP 外设时钟（APB1） */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_PWR | RCC_APB1Periph_BKP, ENABLE);
    /* PWR 备份域解锁：允许写 RTC 与 RCC_BDCR */
    PWR_BackupAccessCmd(ENABLE);

    /* 使能 LSE 32.768kHz 并等待稳定 */
    RCC_LSEConfig(RCC_LSE_ON);
    while (RCC_GetFlagStatus(RCC_FLAG_LSERDY) == RESET)
    {
    }

    /* RTC 时钟源选择 LSE（备份域已解锁） */
    RCC_RTCCLKConfig(RCC_RTCCLKSource_LSE);
    /* 使能 RTC */
    RCC_RTCCLKCmd(ENABLE);
}
