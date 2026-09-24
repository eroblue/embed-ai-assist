/**
 * @file    app_key_handler.c
 * @brief   按键处理模块实现（状态图 app_key_handler_state.md 的 1:1 映射）
 *
 * 去抖窗口 50ms（5 个 10ms 采样拍），长按阈值 1s（100 拍）。
 * 有效电平差异（上拉/下拉、按下=低/高）由 manifest 实例的 active_level
 * 固化在 S5c 实现，本模块只调用 read_active（激活=按下）。
 */
#include "app_key_handler.h"
#include "gpio_port.h"

#define KEY_DEBOUNCE_TICKS   5u    /* 去抖 50ms / 10ms */
#define KEY_HOLD_TICKS       100u  /* 长按判定 1s / 10ms */
#define KEY_COUNT            3u

typedef enum {
    KEY_ST_RELEASED = 0,      /* 释放态 */
    KEY_ST_DEBOUNCE_PRESS,    /* 按下去抖窗口 */
    KEY_ST_PRESSED,           /* 稳定按下 */
    KEY_ST_DEBOUNCE_RELEASE,  /* 释放去抖窗口 */
} key_state_t;

typedef struct {
    key_state_t state;
    uint8_t  stable_cnt;   /* 去抖窗口内连续同电平拍数 */
    uint16_t hold_cnt;     /* 稳定按下持续拍数 */
    uint8_t  long_pressed; /* 长按标志（释放时不发短按事件） */
} key_ctx_t;

static const gpio_port_id_t s_key_ids[KEY_COUNT] = {
    GPIO_PORT_KEY_MODE,   /* → APP_KEY_EVENT_MODE */
    GPIO_PORT_KEY_SWITCH, /* → APP_KEY_EVENT_SWITCH */
    GPIO_PORT_KEY_MUTE,   /* → APP_KEY_EVENT_MUTE */
};

static key_ctx_t s_keys[KEY_COUNT];
static uint8_t   s_pending; /* 待处理事件位域：bit0=MODE bit1=SWITCH bit2=MUTE */

static void key_scan(uint8_t idx, uint8_t pressed);

int32_t app_key_handler_init(void)
{
    static const gpio_port_cfg_t cfg_mode = {
        GPIO_PORT_DIR_INPUT, GPIO_PORT_PULL_UP,   GPIO_PORT_LEVEL_LOW, GPIO_PORT_LEVEL_LOW,
    };
    static const gpio_port_cfg_t cfg_switch = {
        GPIO_PORT_DIR_INPUT, GPIO_PORT_PULL_UP,   GPIO_PORT_LEVEL_LOW, GPIO_PORT_LEVEL_LOW,
    };
    static const gpio_port_cfg_t cfg_mute = {
        GPIO_PORT_DIR_INPUT, GPIO_PORT_PULL_DOWN, GPIO_PORT_LEVEL_HIGH, GPIO_PORT_LEVEL_HIGH,
    };
    static const gpio_port_cfg_t *cfgs[KEY_COUNT] = {
        &cfg_mode, &cfg_switch, &cfg_mute,
    };
    uint8_t i;
    int32_t r;

    for (i = 0; i < KEY_COUNT; i++) {
        s_keys[i].state = KEY_ST_RELEASED;
        s_keys[i].stable_cnt = 0;
        s_keys[i].hold_cnt = 0;
        s_keys[i].long_pressed = 0;
        r = gpio_port_init(s_key_ids[i], cfgs[i]);
        if (r != PORT_OK) { return r; }
    }
    s_pending = 0;
    return PORT_OK;
}

void app_key_handler_poll(void)
{
    uint8_t i;
    uint8_t pressed;

    for (i = 0; i < KEY_COUNT; i++) {
        if (gpio_port_read_active(s_key_ids[i], &pressed) == PORT_OK) {
            key_scan(i, pressed);
        }
    }
}

app_key_event_t app_key_handler_get_event(void)
{
    if ((s_pending & 0x01u) != 0) {
        s_pending &= (uint8_t)~0x01u;
        return APP_KEY_EVENT_MODE;
    }
    if ((s_pending & 0x02u) != 0) {
        s_pending &= (uint8_t)~0x02u;
        return APP_KEY_EVENT_SWITCH;
    }
    if ((s_pending & 0x04u) != 0) {
        s_pending &= (uint8_t)~0x04u;
        return APP_KEY_EVENT_MUTE;
    }
    return APP_KEY_EVENT_NONE;
}

/** 单键状态推进（on_key_down_sampled / on_key_up_sampled / on_hold_timeout_1s）。 */
static void key_scan(uint8_t idx, uint8_t pressed)
{
    key_ctx_t *k = &s_keys[idx];

    switch (k->state) {
    case KEY_ST_RELEASED:
        /* RELEASED → DEBOUNCE_PRESS : on_key_down_sampled */
        if (pressed != 0) {
            k->state = KEY_ST_DEBOUNCE_PRESS;
            k->stable_cnt = 1;
        }
        break;

    case KEY_ST_DEBOUNCE_PRESS:
        if (pressed != 0) {
            k->stable_cnt++;
            /* DEBOUNCE_PRESS → PRESSED : on_stable_pressed / confirm_press */
            if (k->stable_cnt >= KEY_DEBOUNCE_TICKS) {
                k->state = KEY_ST_PRESSED;
                k->hold_cnt = 0;
                k->long_pressed = 0;
            }
        } else {
            /* DEBOUNCE_PRESS → RELEASED : on_key_up_sampled（抖动，回退） */
            k->state = KEY_ST_RELEASED;
            k->stable_cnt = 0;
        }
        break;

    case KEY_ST_PRESSED:
        if (pressed != 0) {
            k->hold_cnt++;
            /* PRESSED → PRESSED : on_hold_timeout_1s / mark_long_press */
            if (k->hold_cnt >= KEY_HOLD_TICKS) {
                k->long_pressed = 1;
            }
        } else {
            /* PRESSED → DEBOUNCE_RELEASE : on_key_up_sampled */
            k->state = KEY_ST_DEBOUNCE_RELEASE;
            k->stable_cnt = 1;
        }
        break;

    case KEY_ST_DEBOUNCE_RELEASE:
        if (pressed == 0) {
            k->stable_cnt++;
            if (k->stable_cnt >= KEY_DEBOUNCE_TICKS) {
                /* DEBOUNCE_RELEASE → RELEASED：
                 * on_release_confirm_short / emit_key_event（仅短按发事件）
                 * on_release_confirm_long（长按不发事件） */
                if (k->long_pressed == 0) {
                    s_pending |= (uint8_t)(1u << idx);
                }
                k->state = KEY_ST_RELEASED;
                k->stable_cnt = 0;
                k->hold_cnt = 0;
                k->long_pressed = 0;
            }
        } else {
            /* DEBOUNCE_RELEASE → PRESSED : on_key_down_sampled（抖动，回退） */
            k->state = KEY_ST_PRESSED;
            k->stable_cnt = 0;
        }
        break;

    default:
        k->state = KEY_ST_RELEASED;
        break;
    }
}
