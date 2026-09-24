/**
 * @file    app_mode_control.h
 * @brief   模式控制模块（自动/手动 x 静音/非静音 正交叠加状态机）
 *
 * 对应状态图 docs/flow/app_mode_control_state.md：
 *  AUTO ↔ MANUAL（模式键切换），任一模式下可独立叠加静音（静音键切换）。
 * 对外显示收敛为三值（AUTO/MANUAL/MUTED，静音优先）。
 */
#ifndef APP_MODE_CONTROL_H
#define APP_MODE_CONTROL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 运行模式。 */
typedef enum {
    APP_MODE_AUTO = 0,   /* 自动模式：执行器由温度告警联动 */
    APP_MODE_MANUAL,     /* 手动模式：执行器由手动开关控制 */
} app_mode_t;

/** 复位状态（上电 AUTO / 非静音）。 */
void app_mode_control_init(void);

/** 模式键事件（AUTO ↔ MANUAL 切换，静音叠加态跟随保持）。 */
void app_mode_control_on_key_mode(void);

/** 静音键事件（静音 ↔ 非静音 切换，模式保持）。 */
void app_mode_control_on_key_mute(void);

/** 当前运行模式。 */
app_mode_t app_mode_control_get_mode(void);

/** 静音标志（1=静音：告警蜂鸣被门控）。 */
uint8_t app_mode_control_is_muted(void);

/** 显示收敛值："AUTO" / "MANUAL" / "MUTED"（静音优先）。 */
const char *app_mode_control_get_display(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_MODE_CONTROL_H */
