/* dht11_init.c - DHT11 单总线 GPIO 初始配置（S5a hardware-initializer 生成，stm32f103zet6） */
#include "dht11_init.h"
#include "stm32f10x.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"

void dht11_init(void)
{
    GPIO_InitTypeDef gpio;

    /* PG11 - DHT11 单总线：初始上拉输入（外部 4.7kΩ 上拉 + 内部上拉）。
       单总线协议时序（起始信号、读位、输入/输出动态切换）归应用层驱动 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_11;
    gpio.GPIO_Mode = GPIO_Mode_IPU;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &gpio);
}
