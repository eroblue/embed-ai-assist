/* uart_init.c - 外设初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "uart_init.h"
#include "gd32f20x.h"

void uart_usart5_init(void)
{
    rcu_periph_clock_enable(RCU_USART5);
    usart_deinit(USART5);
    usart_baudrate_set(USART5, 115200U);
    usart_word_length_set(USART5, USART_WL_8BIT);
    usart_stop_bit_set(USART5, USART_STB_1BIT);
    usart_parity_config(USART5, USART_PM_NONE);
    usart_hardware_flow_rts_config(USART5, USART_RTS_DISABLE);
    usart_hardware_flow_cts_config(USART5, USART_CTS_DISABLE);
    usart_receive_config(USART5, USART_RECEIVE_ENABLE);
    usart_transmit_config(USART5, USART_TRANSMIT_ENABLE);
    usart_enable(USART5);  /* RX 未连接，仅 TX（引脚 PC6 AF_PP 已在 gpio_init 配置） */
}

void uart_init(void)
{
    uart_usart5_init();
}
