/* hal_init.c - 硬件初始化总入口（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "hal_init.h"
#include "clock_init.h"
#include "gpio_init.h"
#include "nvic_init.h"
#include "uart_init.h"
#include "spi_init.h"
#include "i2c_init.h"
#include "adc_init.h"

/**
 * @brief 硬件初始化总入口（layered 架构）：按依赖顺序汇总调用各模块
 *        时钟先行（其余模块依赖总线频率），引脚次之（外设需要复用引脚就绪），
 *        再做 NVIC 分组，最后逐个初始化外设
 */
void hal_init(void)
{
    /* 1. 系统时钟：HSE 8MHz×PLL4=32MHz */
    clock_init();
    /* 2. 引脚模式：离散 IO + UART/SPI2/I2C1/ADC1 复用引脚 */
    gpio_init();
    /* 3. NVIC 优先级分组（不使能具体 IRQ） */
    nvic_init();
    /* 4. 串口：USART1(9600) / USART2(115200) / UART4(115200) */
    uart_init();
    /* 5. SPI：SPI2 主模式 2MHz */
    spi_init();
    /* 6. I2C：I2C1 100kHz */
    i2c_init();
    /* 7. ADC：ADC1 12bit */
    adc_init();
}
