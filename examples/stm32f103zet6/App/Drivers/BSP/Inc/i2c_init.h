#ifndef __I2C_INIT_H
#define __I2C_INIT_H

#ifdef __cplusplus
extern "C" {
#endif

/* I2C1 初始化：100kHz 标准模式（SCL=PB6 / SDA=PB7，开漏复用，7 位寻址） */
void i2c1_init(void);

/* I2C 模块汇总初始化：依次初始化 I2C1 */
void i2c_init(void);

#ifdef __cplusplus
}
#endif

#endif /* __I2C_INIT_H */
