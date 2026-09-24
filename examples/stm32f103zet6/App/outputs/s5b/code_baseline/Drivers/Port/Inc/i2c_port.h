/**
 * @file    i2c_port.h
 * @brief   I2C Port 接口（平台无关，主模式）
 *
 * 逻辑实例：I2C_PORT_OLED（OLED 显示总线）。
 * OLED（SSD1306，commanded 器件）只写不读、无寄存器地址段——
 * 寄存器读写 / 原始读 / 异步接口均已裁剪，仅保留 write_raw。
 * transfer 同步阻塞语义（超时保护归 S5c 实现）。
 */
#ifndef I2C_PORT_H
#define I2C_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,
    PORT_ERR_TIMEOUT = -3,   /* 总线超时（含 NACK / 时钟拉伸超限） */
    PORT_ERR_BUSY = -4,      /* 总线被占用 */
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑实例：按挂载的器件命名（一条总线一个实例） */
typedef enum {
    I2C_PORT_OLED = 0,     /* OLED 显示总线 400kHz */
    I2C_PORT_COUNT
} i2c_port_id_t;

typedef struct {
    uint32_t speed_hz;        /* 总线速率：100000 / 400000 */
    uint8_t  pullup_internal; /* 内部上拉：0=外部上拉 1=启用内部（能上拉的才有效） */
} i2c_port_cfg_t;

/** 绑定逻辑实例与配置。 */
int32_t i2c_port_init(i2c_port_id_t id, const i2c_port_cfg_t *cfg);

/**
 * 原始写（无寄存器地址段；OLED 等 commanded 器件用）。
 * @return PORT_OK 或负值错误码。
 */
int32_t i2c_port_write_raw(i2c_port_id_t id, uint8_t dev_addr,
                           const uint8_t *data, uint16_t len);

/** 反初始化。 */
int32_t i2c_port_deinit(i2c_port_id_t id);

#ifdef __cplusplus
}
#endif

#endif /* I2C_PORT_H */
