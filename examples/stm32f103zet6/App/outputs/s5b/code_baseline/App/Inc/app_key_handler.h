/**
 * @file    app_key_handler.h
 * @brief   按键处理模块（3 键去抖状态机，10ms 轮询）
 *
 * 对应状态图 docs/flow/app_key_handler_state.md：
 *  RELEASED → DEBOUNCE_PRESS → PRESSED → DEBOUNCE_RELEASE → RELEASED
 *  去抖 50ms，长按判定 1s（长按不发短按事件，防误触）。
 * 状态图为单键模型，本模块为 3 个物理键各持一份上下文。
 */
#ifndef APP_KEY_HANDLER_H
#define APP_KEY_HANDLER_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 按键事件（短按产生；MODE=模式切换键，SWITCH=手动开关键，MUTE=静音键）。 */
typedef enum {
    APP_KEY_EVENT_NONE = 0,
    APP_KEY_EVENT_MODE,
    APP_KEY_EVENT_SWITCH,
    APP_KEY_EVENT_MUTE,
} app_key_event_t;

/** 初始化 3 个按键的 GPIO 与去抖上下文。 */
int32_t app_key_handler_init(void);

/** 10ms 节拍轮询：采样 + 去抖状态推进。 */
void app_key_handler_poll(void);

/** 取出一条待处理事件（优先级 MODE > SWITCH > MUTE；取完返回 NONE）。 */
app_key_event_t app_key_handler_get_event(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_KEY_HANDLER_H */
