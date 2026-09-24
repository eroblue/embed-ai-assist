/* hal_init.c - 硬件初始化总入口（S5a hardware-initializer 生成，stm32f103zet6） */
#include "hal_init.h"
#include "clock_init.h"
#include "nvic_init.h"
#include "gpio_init.h"
#include "tim_init.h"
#include "adc_init.h"
#include "fsmc_init.h"
#include "uart_init.h"
#include "dht11_init.h"

/* 初始化顺序按 docs/s5a_design_input.md：
 * 时钟 → 中断分组 → GPIO → 蜂鸣器 PWM → 光照 ADC → FSMC LCD → 串口 → DHT11 */
void hal_init(void)
{
    clock_init();
    nvic_init();
    gpio_init();
    tim4_init();
    adc3_init();
    fsmc_lcd_init();
    usart1_init();
    dht11_init();
}
