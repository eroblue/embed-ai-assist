/**
 * @file    timer_port.h
 * @brief   Timer Port 接口（平台无关）
 *
 * 逻辑定时器按用途命名：TIMER_PORT_TICK_10MS（系统 10ms 节拍，
 * 软轮询调度用）。本工程 RTOS=none，各 APP 模块按节拍计数自行计时。
 *
 * [扩展] delay_us：微秒级忙等短延时（DHT11 单总线位时序需要，
 * 26~70µs 量级）；仅任务上下文调用，禁止在 ISR 内使用。
 *
 * 单次延时 / now_ms / elapsed_ms 本工程未使用，已裁剪。
 */
#ifndef TIMER_PORT_H
#define TIMER_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 统一错误码（各 Port 头同名共享，值域一致） */
#ifndef PORT_ERR_T_DEFINED
#define PORT_ERR_T_DEFINED
typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,   /* period 为 0 / id 越界 */
    PORT_ERR_STATE = -2,   /* 已启动 / 未 init */
    PORT_ERR_TIMEOUT = -3,
    PORT_ERR_BUSY = -4,    /* 硬件定时器资源耗尽 */
} port_err_t;
#endif /* PORT_ERR_T_DEFINED */

/* 逻辑定时器（用途命名） */
typedef enum {
    TIMER_PORT_TICK_10MS = 0,  /* 系统 10ms 节拍（软轮询调度用） */
    TIMER_PORT_COUNT
} timer_port_id_t;

/**
 * 周期到期回调。
 * @context isr —— 定时器中断直接调用：只做置标志/计数，长逻辑投主循环。
 */
typedef void (*timer_port_cb_t)(timer_port_id_t id, void *user_data);

int32_t timer_port_init(timer_port_id_t id);
int32_t timer_port_deinit(timer_port_id_t id);

/**
 * 启动周期定时（重复触发；同一 id 重复启动返回 PORT_ERR_STATE）。
 */
int32_t timer_port_start_periodic(timer_port_id_t id, uint32_t period_ms,
                                  timer_port_cb_t cb, void *user_data);

/** 停止定时（未启动时返回 PORT_OK，幂等）。 */
int32_t timer_port_stop(timer_port_id_t id);

/** [扩展] 微秒级忙等延时（位时序用；仅任务上下文）。 */
int32_t timer_port_delay_us(uint32_t delay_us);

#ifdef __cplusplus
}
#endif

#endif /* TIMER_PORT_H */
