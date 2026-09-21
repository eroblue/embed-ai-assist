/* pwm_init.c - TIM1 PWM 初始化（S5a hardware-initializer 生成，FT61F143A-RB）
 *
 * 硬件连接（任务书第 3 节，S4 facts）：
 * - TIM1 CH1 输出 = PA0（net NetU1_6）
 * - 定时器时钟 16MHz（HIRC，clock_init 已选 T1CKSRC=HIRC 并开 PCKEN.TIM1EN）
 * - 默认参数：1kHz / 50% 占空比
 *
 * 数值计算：
 * - 预分频 PSC = 15（÷16）→ 计数时钟 16MHz/16 = 1MHz
 * - ARR  = 999  → PWM 频率 1MHz/(999+1) = 1kHz
 * - CCR1 = 499  → 占空比 (499+1)/(999+1) = 50%（PWM 模式 1：CCR1 < CNT 时输出有效）
 */
#include "pwm_init.h"
#include "ft61f14x_sfr.h"

void pwm_tim1_init(void)
{
    /* PA0 输出（TRISA 复位默认全 1=输入，CH1 引脚改输出） */
    TRISA &= ~(1u << 0);   /* TRISA.0 = 0 */

    /* 配置期间先关计数器 */
    TIM1CR1 &= (unsigned char)~TIM1CR1_CEN;

    /* 预分频 16 分频（PSC=15：PSC+1=16）→ 1MHz */
    TIM1PSCRH = 0x00u;
    TIM1PSCRL = 15u;

    /* 自动重载 999（1kHz）+ 比较值 499（50%） */
    TIM1ARRH  = 0x03u;
    TIM1ARRL  = 0xE7u;
    TIM1CCR1H = 0x01u;
    TIM1CCR1L = 0xF3u;

    /* CH1 输出比较：PWM 模式 1 + 预装载使能（T1CC1S=00 输出比较，复位默认） */
    TIM1CCMR1 = TIM1CCMR1_OC1M_PWM1 | TIM1CCMR1_OC1PE;

    /* CH1 输出使能（高电平有效，T1CC1P=0 复位默认） */
    TIM1CCER1 = TIM1CCER1_CC1E;

    /* 主输出使能（高级定时器特有，MOE 关则输出强制为空闲态） */
    TIM1BKR = TIM1BKR_MOE;

    /* 产生更新事件，装载 PSC/ARR/CCR 影子寄存器 */
    TIM1EGR = TIM1EGR_UG;

    /* 启动：ARPE 影子使能 + 计数器使能，边沿对齐向上计数（T1CMS=00 复位默认） */
    TIM1CR1 = TIM1CR1_ARPE | TIM1CR1_CEN;
}

void pwm_init(void)
{
    pwm_tim1_init();
}
