/* hal_init.c - 总入口，只做汇总调用（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "hal_init.h"
#include "clock_init.h"
#include "fsmc_init.h"
#include "gpio_init.h"
#include "nvic_init.h"
#include "pwm_init.h"
#include "spi_init.h"
#include "uart_init.h"

void hal_init(void)
{
    clock_init();
    gpio_init();
    nvic_init();
    fsmc_init();
    pwm_init();
    spi_init();
    uart_init();
}
