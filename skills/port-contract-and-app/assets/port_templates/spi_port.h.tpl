/**
 * @file    spi_port.h.tpl
 * @brief   SPI Port 接口模板（平台无关，主模式）
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md）。
 * 硬约束：同 uart_port.h.tpl；片选（CS）归 Port 层管（逻辑片选映射），
 *         APP/Driver 不直接操作片选 GPIO。
 * 语义约定：transfer 全双工同步（tx/rx 各 len 字节；rx 允许 NULL=只发）。
 */
#ifndef SPI_PORT_H
#define SPI_PORT_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,
    PORT_ERR_STATE = -2,
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,      /* 上次传输未完成 */
} port_err_t;

/* 逻辑实例：按挂载的器件命名（一条总线可多器件共享，靠逻辑片选区分） */
typedef enum {
    SPI_PORT_FLASH = 0,      /* 板载 NOR Flash，模式0，20MHz */
    SPI_PORT_LCD = 1,        /* LCD 屏，模式3，40MHz（与 Flash 共线，片选隔离） */
    SPI_PORT_COUNT
} spi_port_id_t;

typedef enum {
    SPI_PORT_MODE_0 = 0,     /* CPOL=0 CPHA=0 */
    SPI_PORT_MODE_3 = 3,     /* CPOL=1 CPHA=1 */
} spi_port_mode_t;

typedef struct {
    uint32_t        freq_hz;      /* 时钟速率 */
    spi_port_mode_t mode;         /* 时钟模式 */
    uint8_t         msb_first;    /* 1=MSB first（绝大多数器件） */
} spi_port_cfg_t;

/**
 * 传输完成回调（异步接口用）。
 * @context isr —— DMA/中断完成时直接调用，处理须短小。
 */
typedef void (*spi_port_xfer_cb_t)(spi_port_id_t id, int32_t result, void *user_data);

int32_t spi_port_init(spi_port_id_t id, const spi_port_cfg_t *cfg);
int32_t spi_port_open(spi_port_id_t id);   /* 含拉低/释放逻辑片选前的总线就绪 */
int32_t spi_port_close(spi_port_id_t id);
int32_t spi_port_deinit(spi_port_id_t id);

/**
 * 全双工同步传输（含片选自动管理：传输期间拉低、完成释放）。
 * @param tx 发送缓冲（NULL = 只收，发 0x00/0xFF 填充由实现层定）
 * @param rx 接收缓冲（NULL = 只发）
 * @return 成功返回传输字节数；负值为错误码。返回时 tx/rx 均可复用。
 */
int32_t spi_port_transfer(spi_port_id_t id, const uint8_t *tx, uint8_t *rx, uint16_t len);

/**
 * 多段传输（片选保持连续：命令+地址+数据 一气呵成，Flash 页编程/屏刷场景）。
 * segments 为 (buf, len) 对；tx 为 NULL 的段只收。不需要的工程整段裁剪。
 */
typedef struct {
    const uint8_t *tx;
    uint8_t       *rx;
    uint16_t       len;
} spi_port_seg_t;

int32_t spi_port_transfer_segs(spi_port_id_t id, const spi_port_seg_t *segs, uint8_t seg_count);

/**
 * 异步全双工传输（发起即返回；回调前 tx/rx 不得复用）。
 * @context isr 回调。
 */
int32_t spi_port_transfer_async(spi_port_id_t id, const uint8_t *tx, uint8_t *rx,
                                uint16_t len, spi_port_xfer_cb_t cb, void *user_data);

/* [扩展] 从模式 / Quad-SPI 命令序列等按需扩展，命名 spi_port_<动词>。 */

#ifdef __cplusplus
}
#endif

#endif /* SPI_PORT_H */
