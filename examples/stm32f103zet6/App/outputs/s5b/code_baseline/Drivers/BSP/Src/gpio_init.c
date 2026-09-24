/* gpio_init.c - 板载 GPIO 初始化：LED/执行器/按键/LCD 背光/FSMC 总线（S5a hardware-initializer 生成，stm32f103zet6） */
#include "gpio_init.h"
#include "stm32f10x.h"
#include "stm32f10x_gpio.h"
#include "stm32f10x_rcc.h"

static void gpio_led_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB | RCC_APB2Periph_GPIOE, ENABLE);

    /* PB5 - DS0 运行指示灯（低电平点亮，初始输出高 = 灭） */
    gpio.GPIO_Pin = GPIO_Pin_5;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);
    GPIO_SetBits(GPIOB, GPIO_Pin_5);

    /* PE5 - DS1 执行指示灯（低电平点亮，初始输出高 = 灭） */
    gpio.GPIO_Pin = GPIO_Pin_5;
    GPIO_Init(GPIOE, &gpio);
    GPIO_SetBits(GPIOE, GPIO_Pin_5);
}

static void gpio_actuator_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);

    /* PA4 - 执行器控制（继电器/MOS 驱动，低 = 关 / 高 = 开，初始输出低 = 关） */
    gpio.GPIO_Pin = GPIO_Pin_4;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);
    GPIO_ResetBits(GPIOA, GPIO_Pin_4);
}

static void gpio_key_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOE, ENABLE);

    /* PE2/PE3/PE4 - 按键 3（静音切换）/按键 1（模式切换）/按键 2（执行器开关）
       上拉输入，按下为低电平；硬件去抖不启用，软件去抖（50ms）归应用层 */
    gpio.GPIO_Pin = GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4;
    gpio.GPIO_Mode = GPIO_Mode_IPU;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOE, &gpio);
}

static void gpio_lcd_backlight_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);

    /* PB0 - LCD 背光（高电平点亮，初始输出高 = 亮；
       本版本不做 PWM 调光，如需可后续改 TIM3_CH3） */
    gpio.GPIO_Pin = GPIO_Pin_0;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOB, &gpio);
    GPIO_SetBits(GPIOB, GPIO_Pin_0);
}

static void gpio_fsmc_bus_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOD | RCC_APB2Periph_GPIOE |
                           RCC_APB2Periph_GPIOG, ENABLE);

    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;

    /* FSMC 数据线 D2/D3（GPIOD） */
    gpio.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1;
    GPIO_Init(GPIOD, &gpio);
    /* FSMC 读/写使能 NOE/NWE（GPIOD） */
    gpio.GPIO_Pin = GPIO_Pin_4 | GPIO_Pin_5;
    GPIO_Init(GPIOD, &gpio);
    /* FSMC 数据线 D13/D14/D15（GPIOD） */
    gpio.GPIO_Pin = GPIO_Pin_8 | GPIO_Pin_9 | GPIO_Pin_10;
    GPIO_Init(GPIOD, &gpio);
    /* FSMC 数据线 D0/D1（GPIOD） */
    gpio.GPIO_Pin = GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_Init(GPIOD, &gpio);

    /* FSMC 数据线 D4~D12（GPIOE） */
    gpio.GPIO_Pin = GPIO_Pin_7 | GPIO_Pin_8 | GPIO_Pin_9 | GPIO_Pin_10 |
                    GPIO_Pin_11 | GPIO_Pin_12 | GPIO_Pin_13 | GPIO_Pin_14 |
                    GPIO_Pin_15;
    GPIO_Init(GPIOE, &gpio);

    /* FSMC_A10（LCD RS）/ FSMC_NE4（LCD 片选，GPIOG） */
    gpio.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_12;
    GPIO_Init(GPIOG, &gpio);
}

void gpio_init(void)
{
    gpio_led_init();
    gpio_actuator_init();
    gpio_key_init();
    gpio_lcd_backlight_init();
    gpio_fsmc_bus_init();
}
