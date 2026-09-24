/**
 * @file    app_mode_control.c
 * @brief   模式控制模块实现（状态图 app_mode_control_state.md 的 1:1 映射）
 *
 * 正交叠加实现：mode 位（AUTO/MANUAL）与 muted 位独立翻转，
 * 与状态图的 4 个组合态（AUTO/AUTO_MUTED/MANUAL/MANUAL_MUTED）一一对应。
 * 显示收敛：静音时统一显示 "MUTED"（对外呈现三值）。
 */
#include "app_mode_control.h"

static app_mode_t s_mode;   /* AUTO / MANUAL */
static uint8_t    s_muted;  /* 静音叠加位 */

void app_mode_control_init(void)
{
    s_mode = APP_MODE_AUTO;
    s_muted = 0;
}

void app_mode_control_on_key_mode(void)
{
    /* AUTO --> MANUAL / MANUAL --> AUTO : on_key_mode_pressed */
    s_mode = (s_mode == APP_MODE_AUTO) ? APP_MODE_MANUAL : APP_MODE_AUTO;
}

void app_mode_control_on_key_mute(void)
{
    /* AUTO --> AUTO_MUTED / AUTO_MUTED --> AUTO 等 4 条迁移 : on_key_mute_pressed */
    s_muted = (s_muted == 0) ? 1u : 0u;
}

app_mode_t app_mode_control_get_mode(void)
{
    return s_mode;
}

uint8_t app_mode_control_is_muted(void)
{
    return s_muted;
}

const char *app_mode_control_get_display(void)
{
    if (s_muted != 0) {
        return "MUTED";
    }
    return (s_mode == APP_MODE_AUTO) ? "AUTO" : "MANUAL";
}
