/**
 * @file    timer_port.h.tpl
 * @brief   Timer Port 接口模板（平台无关）
 *
 * 用法：挑选 → 裁剪 → 扩展（见 references/port_design_principle.md）。
 * 用途命名逻辑定时器（TICK_10MS / BUZZER_PWM），硬件定时器映射在 manifest。
 * 注意：RTOS 工程下 osal.h 的延时接口优先（内部走 RTOS 软定时器），
 *       本模板的周期回调适合硬实时（1ms 级、抖动敏感）场景。
 */
#ifndef TIMER_PORT_H
#define TIMER_PORT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    PORT_OK = 0,
    PORT_ERR_PARAM = -1,   /* period 为 0 / id 越界 */
    PORT_ERR_STATE = -2,   /* 已启动 / 未 init */
    PORT_ERR_BUSY = -4,    /* 硬件定时器资源耗尽 */
} port_err_t;

/* 逻辑定时器（用途命名） */
typedef enum {
    TIMER_PORT_TICK_10MS = 0,  /* 系统 10ms 节拍（软轮询调度用） */
    TIMER_PORT_KEY_SCAN = 1,   /* 按键扫描 20ms */
    TIMER_PORT_COUNT
} timer_port_id_t;

/**
 * 定时到期回调。
 * @context isr —— 定时器中断直接调用：只做置事件/计数，长逻辑投任务。
 */
typedef void (*timer_port_cb_t)(timer_port_id_t id, void *user_data);

int32_t timer_port_init(timer_port_id_t id);
int32_t timer_port_deinit(timer_port_id_t id);

/**
 * 启动周期定时（重复触发；同一 id 重复启动返回 PORT_ERR_STATE）。
 */
int32_t timer_port_start_periodic(timer_port_id_t id, uint32_t period_ms,
                                  timer_port_cb_t cb, void *user_data);

/**
 * 启动单次延时（触发一次后自动停止；常用于看门狗喂狗、超时保护）。
 */
int32_t timer_port_start_oneshot(timer_port_id_t id, uint32_t delay_ms,
                                 timer_port_cb_t cb, void *user_data);

/** 停止定时（未启动时返回 PORT_OK，幂等）。 */
int32_t timer_port_stop(timer_port_id_t id);

/**
 * 读取自由运行计数（毫秒基准；实现层保证单调递增、溢出回绕安全）。
 * 用于 elapsed 计算：`timer_port_elapsed_ms(t0, t1)`。
 */
int32_t timer_port_now_ms(uint32_t *now_ms);

/** 计算时间差（处理 32 位回绕）：t1 相对 t0 经过的毫秒数。 */
uint32_t timer_port_elapsed_ms(uint32_t t0_ms, uint32_t t1_ms);

/* [扩展] PWM 输出（timer_port_pwm_start，占空比百分比）、输入捕获等按需扩展；
 * PWM 场景也可独立成 pwm_port.h（若 PWM 通道多）。 */

#ifdef __cplusplus
}
#endif

#endif /* TIMER_PORT_H */
