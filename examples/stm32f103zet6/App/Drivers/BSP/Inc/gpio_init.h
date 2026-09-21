#ifndef __GPIO_INIT_H
#define __GPIO_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* GPIO 初始化：离散 IO（LED/KEY/调试保留脚）+ UART/SPI2/I2C1/ADC1 复用引脚 */
void gpio_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __GPIO_INIT_H */
