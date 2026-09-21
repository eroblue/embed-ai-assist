#ifndef __SPI_INIT_H
#define __SPI_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* SPI2 初始化：主模式 8bit 软 NSS（MISO=PB14/MOSI=PB15/NSS=PB12/SCK=PB13，2MHz 模式 0） */
void spi2_init(void);

/* SPI 模块汇总初始化：依次初始化 SPI2 */
void spi_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __SPI_INIT_H */
