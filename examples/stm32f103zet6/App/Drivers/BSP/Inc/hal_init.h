#ifndef __HAL_INIT_H
#define __HAL_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* 硬件初始化总入口：clock → gpio → nvic → uart → spi → i2c → adc */
void hal_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __HAL_INIT_H */
