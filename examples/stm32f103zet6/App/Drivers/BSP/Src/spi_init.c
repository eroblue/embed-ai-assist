/* spi_init.c - SPI 初始化（S5a hardware-initializer 生成，STM32F103ZET6） */

#include "stm32f10x.h"
#include "spi_init.h"

/**
 * @brief SPI2 初始化：主模式，8bit，软 NSS
 *        MISO=PB14 / MOSI=PB15 / NSS=PB12 / SCK=PB13（引脚复用在 gpio_init.c 配置）
 *        PCLK1 32MHz / 16 = 2MHz；CPOL=0、CPHA=1（模式 0）；MSB 先行，无 CRC 硬件校验
 */
void spi2_init(void)
{
    SPI_InitTypeDef SPI_InitStructure;

    /* SPI2 挂 APB1 总线，使能外设时钟 */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_SPI2, ENABLE);

    /* 双线全双工 */
    SPI_InitStructure.SPI_Direction = SPI_Direction_2Lines_FullDuplex;
    /* 主模式 */
    SPI_InitStructure.SPI_Mode = SPI_Mode_Master;
    /* 数据帧 8 位 */
    SPI_InitStructure.SPI_DataSize = SPI_DataSize_8b;
    /* 时钟极性 0（空闲低电平） */
    SPI_InitStructure.SPI_CPOL = SPI_CPOL_Low;
    /* 第 1 个时钟边沿采样（模式 0） */
    SPI_InitStructure.SPI_CPHA = SPI_CPHA_1Edge;
    /* NSS 软件控制（PB12 由 GPIO 驱动） */
    SPI_InitStructure.SPI_NSS = SPI_NSS_Soft;
    /* 波特率预分频 16：2MHz */
    SPI_InitStructure.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_16;
    /* 高位在前 */
    SPI_InitStructure.SPI_FirstBit = SPI_FirstBit_MSB;
    /* CRC 多项式（未启用硬件 CRC） */
    SPI_InitStructure.SPI_CRCPolynomial = 7;

    SPI_Init(SPI2, &SPI_InitStructure);
    SPI_Cmd(SPI2, ENABLE);
}

/**
 * @brief SPI 模块汇总初始化：SPI2
 */
void spi_init(void)
{
    spi2_init();
}
