/* pwm_init.c - 外设初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "pwm_init.h"
#include "gd32f20x.h"

void pwm_timer0_ch0_init(void)
{
    rcu_periph_clock_enable(RCU_TIMER0);
    timer_deinit(TIMER0);
    timer_parameter_struct tps = {
        .prescaler = 31U,          /* 计数时钟 32MHz/32 = 1MHz */
        .alignedmode = TIMER_COUNTER_EDGE,
        .counterdirection = TIMER_COUNTER_UP,
        .period = 999U,            /* PWM 1MHz/(999+1) = 1kHz */
        .clockdivision = TIMER_CKDIV_DIV1,
        .repetitioncounter = 0U,
    };
    timer_init(TIMER0, &tps);
    timer_oc_parameter_struct tocs;
    timer_channel_output_struct_para_init(&tocs);
    tocs.ocmode = TIMER_OC_MODE_PWM0;
    tocs.ocpolarity = TIMER_OC_POLARITY_HIGH;
    timer_channel_output_config(TIMER0, TIMER_CH0, &tocs);
    timer_channel_output_pulse_value_config(TIMER0, TIMER_CH0, 500U);  /* 50% */
    timer_channel_output_mode_config(TIMER0, TIMER_CH0, TIMER_OC_MODE_PWM0);
    timer_channel_output_shadow_config(TIMER0, TIMER_CH0, TIMER_OC_SHADOW_DISABLE);
    timer_auto_reload_shadow_enable(TIMER0);
    timer_enable(TIMER0);
}

void pwm_init(void)
{
    pwm_timer0_ch0_init();
}
