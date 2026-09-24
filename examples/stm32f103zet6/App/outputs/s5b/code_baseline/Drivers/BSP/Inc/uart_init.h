/* uart_init.h - USART1 上位机通信初始化（S5a hardware-initializer 生成） */
#ifndef UART_INIT_H
#define UART_INIT_H

/* USART1：PA9(TX) / PA10(RX)，115200-8N1，无流控；
 * 接收中断（外设级 RXNE 已使能，NVIC 使能建议见 nvic_init.c）；
 * 发送轮询，不使用 DMA */
void usart1_init(void);

#endif /* UART_INIT_H */
