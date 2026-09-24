/* spi_init.c - 外设初始化（S5a hardware-initializer 生成，GD32F205VET6,LQFP100） */
#include "spi_init.h"
#include "gd32f20x.h"

void spi_spi2_init(void)
{
    rcu_periph_clock_enable(RCU_SPI2);
    /* 引脚来自 AF remap（任务书依据 datasheet AF remap 表）：先开 AFIO 时钟再重映射 */
    rcu_periph_clock_enable(RCU_AF);
    gpio_pin_remap_config(GPIO_SPI2_REMAP, ENABLE);
    spi_parameter_struct spi_cfg = {
        .device_mode = SPI_MASTER,
        .trans_mode = SPI_TRANSMODE_FULLDUPLEX,
        .frame_size = SPI_FRAMESIZE_8BIT,
        .nss = SPI_NSS_SOFT,
        .endian = SPI_ENDIAN_MSB,
        .clock_polarity = SPI_CK_PL_LOW,
        .clock_phase = SPI_CK_PH_1EDGE,
        .prescale = SPI_PSC_256,
    };
    spi_i2s_deinit(SPI2);
    spi_init(SPI2, &spi_cfg);  /* 速率 = APB1/256 = 125kHz，按需调整 prescale */
    spi_enable(SPI2);
}

void spi_init(void)
{
    spi_spi2_init();
}
