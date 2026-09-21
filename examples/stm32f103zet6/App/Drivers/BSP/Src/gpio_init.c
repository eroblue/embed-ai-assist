/* gpio_init.c - GPIO 引脚模式初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "gpio_init.h"

/**
 * @brief GPIO 初始化：离散 IO + 全部外设复用引脚
 *        离散：PA0/PA15(JTDI)/PB3(JTDO)/PC13/PC14(OSC32_IN)/PC15(OSC32_OUT) 浮空输入；
 *              PB5(LED1)/PE5(LED2) 推挽输出；PE2(KEY2)/PE3(KEY1)/PE4(KEY0) 上拉输入
 *        复用：UART（TX 复用推挽 / RX 浮空）、SPI2（SCK/MOSI 复用推挽、MISO 浮空、
 *              NSS 软件控制推挽输出）、I2C1（开漏复用）、ADC1（模拟输入）
 */
void gpio_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    /* 端口与 AFIO 时钟 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB
                           | RCC_APB2Periph_GPIOC | RCC_APB2Periph_GPIOE
                           | RCC_APB2Periph_AFIO, ENABLE);

    /* ---- 离散 IO ---- */

    /* PA0：浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    /* PA15（JTDI）：浮空输入（调试保留脚） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_15;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    /* PB3（JTDO）：浮空输入（调试保留脚） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* PB5（LED1）：推挽输出 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_5;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* PC13：浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    /* PC14（OSC32_IN）/ PC15（OSC32_OUT）：浮空输入（LSE 晶振脚） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    /* PE2（KEY2）/ PE3（KEY1）/ PE4（KEY0）：上拉输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOE, &GPIO_InitStructure);

    /* PE5（LED2）：推挽输出 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_5;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOE, &GPIO_InitStructure);

    /* ---- UART 复用引脚 ---- */

    /* USART1：PA9 TX 复用推挽，PA10 RX 浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    /* USART2：PA2 TX 复用推挽，PA3 RX 浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    /* UART4：PC10 TX 复用推挽，PC11 RX 浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOC, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_11;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOC, &GPIO_InitStructure);

    /* ---- SPI2 复用引脚 ---- */

    /* PB13 SCK / PB15 MOSI：复用推挽 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13 | GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* PB14 MISO：浮空输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* PB12 NSS：软件 NSS，推挽输出并置高（空闲不选片） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_Init(GPIOB, &GPIO_InitStructure);
    GPIO_SetBits(GPIOB, GPIO_Pin_12);

    /* ---- I2C1 复用引脚 ---- */

    /* PB6 SCL / PB7 SDA：复用开漏（总线外部上拉） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_OD;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    /* ---- ADC1 模拟引脚 ---- */

    /* PA1（stm_adc）：模拟输入 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_1;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_Init(GPIOA, &GPIO_InitStructure);
}
