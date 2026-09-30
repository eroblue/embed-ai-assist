/**
 * @file    wdt_port.h
 * @brief   Watchdog Port 接口（平台无关）
 *
 * 逻辑看门狗实例：WDT_PORT_SYSTEM（整个固件的存活监测）。
 *
 * 层次划分：**超时窗口是应用策略**，由调用方在 `wdt_port_init(id, timeout_ms)`
 * 给定（APP 决定"多久未喂狗即复位"）；S5a 只提供硬件事实（IWDG 的 LSI
 * ≈40kHz、预分频档位/重装载位宽，见 hardware_capabilities），不固化超时；
 * 本层按 timeout_ms 换算预分频/重装载并启动，`wdt_port_feed` 负责喂狗。
 *
 * 注意：独立看门狗一旦启动不可关闭，故不提供 deinit。
 * 本工程接入方式：app_init 以 APP_WDT_TIMEOUT_MS(1000ms) 启动，
 * app_loop 每 10ms 喂狗。
 */
#ifndef WDT_PORT_H
#define WDT_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,   /* id 越界 / 出参为 NULL */
    PORT_ERR_STATE = -2,   /* 重复 init / 未 init */
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑看门狗实例（用途命名） */
typedef enum {
    WDT_PORT_SYSTEM = 0,   /* 系统看门狗：整个固件的存活监测 */
    WDT_PORT_COUNT
} wdt_port_id_t;

/**
 * 启动看门狗。
 * @param timeout_ms 超时窗口（毫秒）：**应用策略，由调用方决定**——
 *   "多久未喂狗即复位"；须大于实际喂狗间隔（本工程 10ms）。超出 IWDG
 *   可表达量程（约 0.1ms ~ 26.2s）返回 PORT_ERR_PARAM。
 * @note 独立看门狗一旦启动不可关闭；重复调用返回 PORT_ERR_STATE。
 * @context task
 */
int32_t wdt_port_init(wdt_port_id_t id, uint32_t timeout_ms);

/**
 * 喂狗（刷新计数）。须在 timeout_ms 窗口内周期调用，否则触发复位。
 * @context isr/task 均可——只写硬件 Key 寄存器，无阻塞、无锁。
 */
int32_t wdt_port_feed(wdt_port_id_t id);

/**
 * 查询上次复位是否由看门狗引起（读并清复位标志）。
 * @param caused 出参：1=是，0=否（启动自检/日志用）
 * @context task
 */
int32_t wdt_port_reset_caused(wdt_port_id_t id, uint8_t *caused);

#ifdef __cplusplus
}
#endif

#endif /* WDT_PORT_H */
