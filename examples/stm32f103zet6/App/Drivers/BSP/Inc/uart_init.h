#ifndef __UART_INIT_H
#define __UART_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* USART1 初始化：TX=PA9 / RX=PA10，9600-8N1，无流控（挂 APB2） */
void uart1_init(void);

/* USART2 初始化：TX=PA2 / RX=PA3，115200-8N1，无流控（挂 APB1） */
void uart2_init(void);

/* UART4 初始化：TX=PC10 / RX=PC11，115200-8N1，无流控（挂 APB1） */
void uart4_init(void);

/* 串口模块汇总初始化：依次初始化 USART1 / USART2 / UART4 */
void uart_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __UART_INIT_H */
