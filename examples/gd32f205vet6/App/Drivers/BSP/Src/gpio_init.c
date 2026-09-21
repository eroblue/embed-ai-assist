/* gpio_init.c - GPIO 初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "gpio_init.h"

#include "gd32f20x.h"

void gpio_init(void)
{
    rcu_periph_clock_enable(RCU_GPIOA);
    gpio_init(GPIOA, GPIO_MODE_IN_FLOATING, GPIO_OSPEED_50MHZ, GPIO_PIN_0);  /* NetU1_23 */
    gpio_init(GPIOA, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_15);  /* JTDI - SPI2_NSS（软 NSS，按需改普通输出） */
    rcu_periph_clock_enable(RCU_GPIOC);
    gpio_init(GPIOC, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_6);   /* DEBUG-TXD - USART5_TX */
    gpio_init(GPIOC, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_10);  /* SPI2_SCK（remap） */
    gpio_init(GPIOC, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_11);  /* SPI2_MISO（remap） */
    gpio_init(GPIOC, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_12);  /* SPI2_MOSI（remap） */
    rcu_periph_clock_enable(RCU_GPIOD);
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_0);   /* LCD_DB2 - FSMC/EXMC */
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_1);   /* LCD_DB3 - FSMC/EXMC */
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_7);   /* LCD_CS - FSMC/EXMC */
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_14);  /* LCD_DB0 - FSMC/EXMC */
    gpio_init(GPIOD, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_15);  /* LCD_DB1 - FSMC/EXMC */
    rcu_periph_clock_enable(RCU_GPIOE);
    gpio_init(GPIOE, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_7);   /* LCD_DB4 - FSMC/EXMC */
    gpio_init(GPIOE, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_8);   /* LCD_DB5 - FSMC/EXMC */
    gpio_init(GPIOE, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_9);   /* LCD_DB6 - FSMC/EXMC */
    gpio_init(GPIOE, GPIO_MODE_AF_PP, GPIO_OSPEED_50MHZ, GPIO_PIN_10);  /* LCD_DB7 - FSMC/EXMC */
    /* 以下引脚保持默认状态（PE2-PE6, PC13-PC15, VBAT...）：晶振脚由 clock_init 配置；BOOT/NRST/SWD/电源脚不配置 */
}
