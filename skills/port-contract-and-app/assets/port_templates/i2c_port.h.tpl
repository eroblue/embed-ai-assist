/**
 * @file    i2c_port.h.tpl
 * @brief   I2C Port 接口模板（平台无关，主模式；从模式按需扩展）
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md）。
 * 硬约束：同 uart_port.h.tpl（stdint/无 HAL 依赖/DMA 隐藏/统一错误码）。
 * 语义约定：transfer 为同步阻塞（超时保护）；异步事件由完成回调通知。
 */
#ifndef I2C_PORT_H
#define I2C_PORT_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,
    PORT_ERR_TIMEOUT = -3,   /* 总线超时（含 NACK / 时钟拉伸超限） */
    PORT_ERR_BUSY = -4,      /* 总线被占用 */
} port_err_t;

/* 逻辑实例：按挂载的器件/总线命名（一条总线一个实例，不按 I2C 控制器拆） */
typedef enum {
    I2C_PORT_SENSOR = 0,     /* 板载传感器总线 400kHz */
    I2C_PORT_CODEC = 1,      /* 音频codec 总线 100kHz */
    I2C_PORT_COUNT
} i2c_port_id_t;

typedef struct {
    uint32_t speed_hz;       /* 总线速率：100000 / 400000 */
    uint8_t  pullup_internal;/* 内部上拉：0=外部上拉 1=启用内部（能上拉的才有效） */
} i2c_port_cfg_t;

/**
 * 传输完成回调（异步通知，仅异步接口使用）。
 * @context task —— ISR 投递后任务上下文回调。
 */
typedef void (*i2c_port_xfer_cb_t)(i2c_port_id_t id, int32_t result, void *user_data);

int32_t i2c_port_init(i2c_port_id_t id, const i2c_port_cfg_t *cfg);
int32_t i2c_port_open(i2c_port_id_t id);
int32_t i2c_port_close(i2c_port_id_t id);
int32_t i2c_port_deinit(i2c_port_id_t id);

/**
 * 寄存器写（同步阻塞）：向器件 dev_addr 的 reg_addr 写 len 字节。
 * 典型实现 = start + dev_addr+W + reg_addr + data... + stop。
 * @return PORT_OK 或负值错误码。
 */
int32_t i2c_port_write_reg(i2c_port_id_t id, uint8_t dev_addr, uint8_t reg_addr,
                           const uint8_t *data, uint16_t len);

/**
 * 寄存器读（同步阻塞）：从器件 dev_addr 的 reg_addr 读 len 字节到 data。
 * 典型实现 = start + dev_addr+W + reg_addr + restart + dev_addr+R + data... + stop。
 * @return PORT_OK 或负值错误码。
 */
int32_t i2c_port_read_reg(i2c_port_id_t id, uint8_t dev_addr, uint8_t reg_addr,
                          uint8_t *data, uint16_t len);

/**
 * 原始写（无寄存器地址段；OLED 等 commanded 器件用）。
 */
int32_t i2c_port_write_raw(i2c_port_id_t id, uint8_t dev_addr,
                           const uint8_t *data, uint16_t len);

/**
 * 原始读（无寄存器地址段）。
 */
int32_t i2c_port_read_raw(i2c_port_id_t id, uint8_t dev_addr,
                          uint8_t *data, uint16_t len);

/**
 * 异步寄存器读（发起后立即返回，完成回调通知；缓冲 data 归调用方，
 * 回调触发前不得复用）。不需要异步的工程整段裁剪。
 */
int32_t i2c_port_read_reg_async(i2c_port_id_t id, uint8_t dev_addr, uint8_t reg_addr,
                                uint8_t *data, uint16_t len,
                                i2c_port_xfer_cb_t cb, void *user_data);

/* [扩展] 从模式 / SMBus / 10bit 地址等按需扩展，命名 i2c_port_<动词>。 */

#ifdef __cplusplus
}
#endif

#endif /* I2C_PORT_H */
