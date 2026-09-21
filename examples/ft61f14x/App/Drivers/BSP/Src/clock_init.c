/* clock_init.c - 系统时钟初始化（S5a hardware-initializer 生成，FT61F143A-RB）
 *
 * 时钟方案（任务书第 2 节，直接采用）：
 * - HSE：未发现（无外部晶振）
 * - SYSCLK：16MHz（HIRC 内部高速振荡器直跑，无 PLL）
 * - AHB/APB1/APB2：16MHz（8 位机 SFR 直访，无总线分频概念）
 *
 * FT61F 上电默认时钟源即 HIRC，此处不做时钟源切换（避免触发双速启动/OST 时序），
 * 仅使能本项目使用的外设时钟（TIM1 / USART，见 PCKEN）。
 */
#include "clock_init.h"
#include "ft61f14x_sfr.h"

void clock_init(void)
{
    /* HIRC 16MHz：复位默认即 HIRC 直跑，无需写 OSCCON（TUN 仅用于出厂校准微调） */

    /* 外设时钟使能：TIM1（PWM CH1）+ USART（115200 调试口）
     * PCKEN 复位值 0（外设时钟全关），须在配置外设寄存器前打开 */
    PCKEN = PCKEN_TIM1EN | PCKEN_UARTEN;

    /* TIM1 时钟源选 HIRC（手册 10.3 T1CKSRC 编码，示例代码 H'01=HIRC） */
    TCKSRC = T1CKSRC_HIRC;
}
