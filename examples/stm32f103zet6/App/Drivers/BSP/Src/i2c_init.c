/* i2c_init.c - I2C 初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "i2c_init.h"

/**
 * @brief I2C1 初始化：100kHz 标准模式
 *        SCL=PB6 / SDA=PB7（开漏复用，总线外部上拉，gpio_init.c 配置）
 *        7 位寻址，使能 ACK
 */
void i2c1_init(void)
{
    I2C_InitTypeDef I2C_InitStructure;

    /* I2C1 挂 APB1 总线，使能外设时钟 */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_I2C1, ENABLE);

    /* 时钟频率 100kHz（标准模式） */
    I2C_InitStructure.I2C_ClockSpeed = 100000;
    /* I2C 模式 */
    I2C_InitStructure.I2C_Mode = I2C_Mode_I2C;
    /* 占空比 Tlow/Thigh = 2（标准模式不使用快速模式占空比） */
    I2C_InitStructure.I2C_DutyCycle = I2C_DutyCycle_2;
    /* 自身地址 0（不响应主模式寻址） */
    I2C_InitStructure.I2C_OwnAddress1 = 0x00;
    /* 接收后应答 ACK */
    I2C_InitStructure.I2C_Ack = I2C_Ack_Enable;
    /* 应答地址 7 位 */
    I2C_InitStructure.I2C_AcknowledgedAddress = I2C_AcknowledgedAddress_7bit;

    I2C_Init(I2C1, &I2C_InitStructure);
    I2C_Cmd(I2C1, ENABLE);
}

/**
 * @brief I2C 模块汇总初始化：I2C1
 */
void i2c_init(void)
{
    i2c1_init();
}
