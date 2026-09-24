/* uart_init.c - USART1 上位机通信初始化：115200-8N1（S5a hardware-initializer 生成，stm32f103zet6） */
#include "uart_init.h"
#include "stm32f10x.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"
#include "stm32f10x_usart.h"

void usart1_init(void)
{
    GPIO_InitTypeDef gpio;
    USART_InitTypeDef usart;

    /* PA9 - USART1_TX（复用推挽）；PA10 - USART1_RX（浮空输入）；
       板载 CH340 转 USB 连接 PC */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_USART1, ENABLE);

    gpio.GPIO_Pin = GPIO_Pin_9;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);

    gpio.GPIO_Pin = GPIO_Pin_10;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &gpio);

    /* 115200-8N1，无流控，异步模式（docs/s5a_design_input.md）；
       发送轮询（应用层决定），接收中断 */
    usart.USART_BaudRate = 115200;
    usart.USART_WordLength = USART_WordLength_8b;
    usart.USART_StopBits = USART_StopBits_1;
    usart.USART_Parity = USART_Parity_No;
    usart.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    usart.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART1, &usart);

    /* 外设级接收中断使能；NVIC 通道使能须在应用层注册
       USART1_IRQHandler 后进行（见 nvic_init.c 使能建议：抢占 2 / 子 0）。
       不使用 DMA */
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);

    USART_Cmd(USART1, ENABLE);
}
