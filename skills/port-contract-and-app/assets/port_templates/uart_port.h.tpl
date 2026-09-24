/**
 * @file    uart_port.h.tpl
 * @brief   UART Port 接口模板（平台无关）
 *
 * 用法：挑选 → 裁剪 → 扩展，不是机械填充（见 references/port_design_principle.md）。
 *  - 逻辑实例按应用需求定（单外设多场景用逻辑名区分，不按硬件实例拆）
 *  - 不确定硬件映射时 hw_instance 置 null（manifest 数据侧），头文件代码不含硬件信息
 *  - 裁剪规则：未用的回调/接口整段删除；扩展在文件尾部标注 [扩展]
 *
 * 硬约束：<stdint.h> 类型；不 include HAL/RTOS/app/driver 头；无 DMA 字样；
 *         write 同步拷贝语义；read 非阻塞；接收由回调驱动（模板默认约定）。
 *
 * manifest 登记：本头文件的逻辑实例/接口/回调须同步写入
 *               outputs/s5b/port_interface_manifest.json（示例见 assets/ 示例 JSON）。
 */
#ifndef UART_PORT_H
#define UART_PORT_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- 统一错误码（各 Port 头同名枚举，值域一致） ---------------- */
typedef enum {
    PORT_OK = 0,          /* 成功 */
    PORT_ERR_PARAM = -1,  /* 参数非法（id 越界 / buf 为空 / len 为 0） */
    PORT_ERR_STATE = -2,  /* 状态错误（未 init / 已 open） */
    PORT_ERR_TIMEOUT = -3,/* 同步等待超时（poll_wait 模式） */
    PORT_ERR_BUSY = -4,   /* 资源忙（上次发送未完成且不支持排队） */
} port_err_t;

/* ---------------- 逻辑实例（不透明句柄：只暴露 ID，不暴露任何硬件细节） ----------------
 * 按应用场景命名；UART_PORT_COUNT 必须放最后。
 * 示例：板载 WiFi 模块 + 调试口 → 两个逻辑实例。
 */
typedef enum {
    UART_PORT_WIFI = 0,   /* WiFi 模块 AT 通道，115200-8N1 */
    UART_PORT_DEBUG = 1,  /* 调试输出通道，115200-8N1 */
    UART_PORT_COUNT
} uart_port_id_t;

/* ---------------- 配置结构体（应用语义字段，无硬件语义） ---------------- */
typedef struct {
    uint32_t baudrate;    /* 波特率，如 115200 */
    uint8_t  data_bits;   /* 数据位：7 / 8 */
    uint8_t  parity;      /* 校验：0=无 1=偶 2=奇 */
    uint8_t  stop_bits;   /* 停止位：1 / 2 */
} uart_port_cfg_t;

/* ---------------- 回调（上下文约定：S5c 实现与 APP 注册都必须遵守） ---------------- */

/**
 * 接收回调。
 * @context task —— 实现层保证在任务上下文调用（ISR 内完成搬运后投递到任务）；
 *                 回调内禁止阻塞、禁止调用非 ISR 安全接口。
 * 若实现层只能 ISR 直接调用，必须在头文件与 manifest 中改为 isr 并全项目公告。
 */
typedef void (*uart_port_rx_cb_t)(uart_port_id_t id, const uint8_t *data,
                                  uint16_t len, void *user_data);

/**
 * 发送完成回调（write 的异步完成通知；write 本身为同步拷贝语义，可不注册）。
 * @context isr —— 典型由 TX 完成中断直接调用，处理须短小。
 */
typedef void (*uart_port_tx_done_cb_t)(uart_port_id_t id, void *user_data);

/* ---------------- 生命周期：init → (open → 使用 → close)* → deinit ---------------- */

/** 绑定逻辑实例与配置（实现层对接 S5a 的外设初始化成果）。 */
int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg);

/** 可选：申请缓冲/使能中断（无资源诉求的实例可不调用）。 */
int32_t uart_port_open(uart_port_id_t id);

/** 注册接收回调（user_data 在回调时透传）。 */
int32_t uart_port_set_rx_cb(uart_port_id_t id, uart_port_rx_cb_t cb, void *user_data);

/** 注册发送完成回调。 */
int32_t uart_port_set_tx_done_cb(uart_port_id_t id, uart_port_tx_done_cb_t cb, void *user_data);

/**
 * 发送数据（同步拷贝语义：返回时 buf 可安全复用/释放）。
 * @return 成功返回发送字节数；负值为 port_err_t。
 */
int32_t uart_port_write(uart_port_id_t id, const uint8_t *buf, uint16_t len);

/**
 * 非阻塞读：拷走接收缓冲中当前可用数据。
 * @return 成功返回读取字节数（0=暂无数据）；负值为 port_err_t。
 */
int32_t uart_port_read(uart_port_id_t id, uint8_t *buf, uint16_t len);

/** 关闭实例（与 open 配对；停止中断、保留配置）。 */
int32_t uart_port_close(uart_port_id_t id);

/** 反初始化：释放该实例全部资源。 */
int32_t uart_port_deinit(uart_port_id_t id);

/* [扩展] 应用特有接口（如协议层需要的 flush / break / 波特率热切换）加在此处，
 * 命名保持 uart_port_<动词>，同步登记 manifest。 */

#ifdef __cplusplus
}
#endif

#endif /* UART_PORT_H */
