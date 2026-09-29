/**
 * @file    uart_port.h
 * @brief   UART Port 接口（平台无关）
 *
 * 逻辑实例：UART_PORT_REPORT（环境数据 JSON 上报 + 上位机指令接收通道，115200-8N1）。
 * 发送：write 同步拷贝语义，返回后 buf 可安全复用。
 * 接收：中断驱动——实现层 ISR 搬运字节入环形缓冲并通知回调；
 *       read 非阻塞取走缓冲数据（0=暂无数据），两种方式可并用。
 *       上位机指令协议未定义，本层只提供接收通道，不含协议解析。
 *
 * 硬约束：<stdint.h> 基本类型；不 include HAL/RTOS/app/driver 头；
 *         无 DMA 字样（实现细节归 S5c）。
 * 硬件映射（逻辑名 → 厂商实例/引脚）只登记在
 *         outputs/s5b/port_interface_manifest.json 数据侧。
 */
#ifndef UART_PORT_H
#define UART_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- 统一错误码（各 Port 头同名共享，值域一致） ----------------
 * 多个 Port 头被同一文件 include 时由首个头定义（防护宏保证不重复）。 */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,           /* 成功 */
    PORT_ERR_PARAM = -1,   /* 参数非法（id 越界 / cfg 为空） */
    PORT_ERR_STATE = -2,   /* 状态错误（未 init / 已 init） */
    PORT_ERR_TIMEOUT = -3, /* 同步等待超时 */
    PORT_ERR_BUSY = -4,    /* 资源忙 */
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* ---------------- 逻辑实例（不透明句柄：只暴露 ID，无硬件细节） ---------------- */
typedef enum {
    UART_PORT_REPORT = 0,  /* 环境数据 JSON 上报通道，115200-8N1 */
    UART_PORT_COUNT
} uart_port_id_t;

/* ---------------- 配置结构体（应用语义字段，无硬件语义） ---------------- */
typedef struct {
    uint32_t baudrate;     /* 波特率，如 115200 */
    uint8_t  data_bits;    /* 数据位：7 / 8 */
    uint8_t  parity;       /* 校验：0=无 1=偶 2=奇 */
    uint8_t  stop_bits;     /* 停止位：1 / 2 */
} uart_port_cfg_t;

/* ---------------- 回调（上下文约定：实现层与 APP 注册都须遵守） ---------------- */

/**
 * 接收数据回调。
 * @context isr —— 本工程 RTOS=none，实现层在 USART1 接收中断内直接调用：
 *          回调内只做置标志/短拷贝，禁止阻塞与长逻辑（长逻辑投主循环）。
 *          data 仅在回调执行期间有效，需要留存须自行拷贝。
 */
typedef void (*uart_port_rx_cb_t)(uart_port_id_t id, const uint8_t *data,
                                  uint16_t len, void *user_data);

/* ---------------- 生命周期：init → 使用 → deinit ---------------- */

/** 绑定逻辑实例与配置（实现层对接 S5a 的外设初始化成果）。 */
int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg);

/**
 * 发送数据（同步拷贝语义：返回时 buf 可安全复用/释放）。
 * @return 成功返回发送字节数；负值为 port_err_t。
 */
int32_t uart_port_write(uart_port_id_t id, const uint8_t *buf, uint16_t len);

/**
 * 注册接收回调（user_data 在回调时透传；cb 传 NULL 取消注册）。
 * @note 未注册时中断仍搬运入环形缓冲，仅不通知（数据可由 read 取走）。
 */
int32_t uart_port_set_rx_cb(uart_port_id_t id, uart_port_rx_cb_t cb,
                            void *user_data);

/**
 * 非阻塞读：取走接收环形缓冲中当前可用数据（最多 len 字节）。
 * @return 实际读取字节数（0=暂无数据）；负值为 port_err_t。
 */
int32_t uart_port_read(uart_port_id_t id, uint8_t *buf, uint16_t len);

/** 反初始化：释放该实例全部资源。 */
int32_t uart_port_deinit(uart_port_id_t id);

#ifdef __cplusplus
}
#endif

#endif /* UART_PORT_H */
