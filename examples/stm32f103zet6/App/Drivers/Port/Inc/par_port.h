/**
 * @file    par_port.h
 * @brief   16 位并行总线 Port 接口（平台无关，LCD 显存写入通道）
 *
 * 逻辑实例：PAR_PORT_LCD（TFT_LCD 显存总线）。
 * 语义：写命令字 / 写数据字 / 数据字块流式写（同步写直达，返回后即可复用 buf）。
 * 器件初始化序列（厂商寄存器）由 driver_lcd 承载，本层只提供总线原语；
 * 总线控制器初始化（FSMC 等）与命令/数据地址映射由 S5a 成果 + manifest 数据侧承载，
 * 换平台只改 manifest 的 hw_instance 映射，不改代码。
 */
#ifndef PAR_PORT_H
#define PAR_PORT_H

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
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑实例：按挂载的器件命名（一条总线一个实例） */
typedef enum {
    PAR_PORT_LCD = 0,     /* TFT_LCD 显存总线（16 位并口） */
    PAR_PORT_COUNT
} par_port_id_t;

/** 绑定逻辑实例（实现层调 S5a 总线初始化成果；地址映射见 manifest 数据侧）。 */
int32_t par_port_init(par_port_id_t id);

/** 写一个命令字。 */
int32_t par_port_write_cmd(par_port_id_t id, uint16_t cmd);

/** 写一个数据字（16 位并口下低 8 位有效时按器件协议理解）。 */
int32_t par_port_write_data(par_port_id_t id, uint16_t data);

/**
 * 数据字块流式写（同步拷贝语义：返回后 buf 可复用；用于像素流）。
 * @return PORT_OK 或负值错误码。
 */
int32_t par_port_write_data_block(par_port_id_t id, const uint16_t *buf,
                                  uint32_t len);

/** 反初始化（总线交还底层管理）。 */
int32_t par_port_deinit(par_port_id_t id);

#ifdef __cplusplus
}
#endif

#endif /* PAR_PORT_H */
