/* uart_init.c - 串口初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "uart_init.h"

/**
 * @brief USART1 初始化：TX=PA9 / RX=PA10，9600-8N1，无流控
 */
void uart1_init(void)
{
    USART_InitTypeDef USART_InitStructure;

    /* USART1 挂 APB2 总线（32MHz），使能外设时钟 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1, ENABLE);

    /* 波特率 9600 */
    USART_InitStructure.USART_BaudRate = 9600;
    /* 数据字长 8 位 */
    USART_InitStructure.USART_WordLength = USART_WordLength_8b;
    /* 停止位 1 位 */
    USART_InitStructure.USART_StopBits = USART_StopBits_1;
    /* 无奇偶校验 */
    USART_InitStructure.USART_Parity = USART_Parity_No;
    /* 收发模式（Mode_Rx | Mode_Tx） */
    USART_InitStructure.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    /* 无硬件流控 */
    USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;

    USART_Init(USART1, &USART_InitStructure);
    USART_Cmd(USART1, ENABLE);
}

/**
 * @brief USART2 初始化：TX=PA2 / RX=PA3，115200-8N1，无流控
 */
void uart2_init(void)
{
    USART_InitTypeDef USART_InitStructure;

    /* USART2 挂 APB1 总线（32MHz），使能外设时钟 */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_USART2, ENABLE);

    /* 波特率 115200 */
    USART_InitStructure.USART_BaudRate = 115200;
    /* 数据字长 8 位 */
    USART_InitStructure.USART_WordLength = USART_WordLength_8b;
    /* 停止位 1 位 */
    USART_InitStructure.USART_StopBits = USART_StopBits_1;
    /* 无奇偶校验 */
    USART_InitStructure.USART_Parity = USART_Parity_No;
    /* 收发模式（Mode_Rx | Mode_Tx） */
    USART_InitStructure.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    /* 无硬件流控 */
    USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;

    USART_Init(USART2, &USART_InitStructure);
    USART_Cmd(USART2, ENABLE);
}

/**
 * @brief UART4 初始化：TX=PC10 / RX=PC11，115200-8N1，无流控
 */
void uart4_init(void)
{
    USART_InitTypeDef USART_InitStructure;

    /* UART4 挂 APB1 总线（32MHz），使能外设时钟 */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_UART4, ENABLE);

    /* 波特率 115200 */
    USART_InitStructure.USART_BaudRate = 115200;
    /* 数据字长 8 位 */
    USART_InitStructure.USART_WordLength = USART_WordLength_8b;
    /* 停止位 1 位 */
    USART_InitStructure.USART_StopBits = USART_StopBits_1;
    /* 无奇偶校验 */
    USART_InitStructure.USART_Parity = USART_Parity_No;
    /* 收发模式（Mode_Rx | Mode_Tx） */
    USART_InitStructure.USART_Mode = USART_Mode_Rx | USART_Mode_Tx;
    /* 无硬件流控 */
    USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;

    USART_Init(UART4, &USART_InitStructure);
    USART_Cmd(UART4, ENABLE);
}

/**
 * @brief 串口模块汇总初始化：USART1 / USART2 / UART4
 */
void uart_init(void)
{
    /* USART1：TX=PA9 / RX=PA10 */
    uart1_init();
    /* USART2：TX=PA2 / RX=PA3 */
    uart2_init();
    /* UART4：TX=PC10 / RX=PC11 */
    uart4_init();
}
