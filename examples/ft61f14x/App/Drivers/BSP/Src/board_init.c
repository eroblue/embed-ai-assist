/* board_init.c - 板级初始化总入口（S5a hardware-initializer 生成，FT61F143A-RB）
 *
 * 调用顺序（任务书规则 4；本项目无独立 gpio_init 模块，
 * GPIO 方向在各自外设 init 内配置）：
 *   clock_init → nvic_init → uart_init → pwm_init
 */
#include "board_init.h"
#include "clock_init.h"
#include "nvic_init.h"
#include "uart_init.h"
#include "pwm_init.h"

void board_init(void)
{
    clock_init();   /* SYSCLK 16MHz HIRC + 外设时钟（TIM1/USART） */
    nvic_init();    /* 全局中断框架（GIE 关闭，具体中断由应用按需使能） */
    uart_init();    /* USART 115200-8N1：TX=PA6 / RX=PA7 */
    pwm_init();     /* TIM1 CH1 PWM 1kHz/50%：PA0 */
}
