/* clock_init.c - 时钟初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "clock_init.h"

void clock_init(void)
{
    /* HXTAL 16MHz（S4 硬件事实） */
    rcu_osci_on(RCU_HXTAL);
    while (ERROR == rcu_osci_stab_wait(RCU_HXTAL)) { }
    /* PLL: HXTAL x 2 = 32MHz（设计输入目标 32MHz） */
    rcu_pll_config(RCU_PLLSRC_HXTAL, RCU_PLL_MUL2);
    rcu_ahb_clock_config(RCU_CKSYS_DIV1);   /* AHB  = 32MHz */
    rcu_apb1_clock_config(RCU_CKAPB1_DIV1); /* APB1 = 32MHz */
    rcu_apb2_clock_config(RCU_CKAPB2_DIV1); /* APB2 = 32MHz 同 AHB */
    rcu_osci_on(RCU_PLL_CK);
    while (ERROR == rcu_osci_stab_wait(RCU_PLL_CK)) { }
    rcu_system_clock_source_config(RCU_CKSYSSRC_PLL);
    while (rcu_system_clock_source_get() != RCU_SCSS_PLL) { }
    SystemCoreClockUpdate();
    /* LXTAL（RTC 时钟源，S4 硬件事实） */
    rcu_osci_on(RCU_LXTAL);
    while (ERROR == rcu_osci_stab_wait(RCU_LXTAL)) { }
    rcu_rtc_clock_config(RCU_RTCSRC_LXTAL);
}
