/**
 * @file    app.c
 * @brief   应用总入口实现（初始化汇总 + 10ms 节拍主循环）
 *
 * 调度模型（设计输入时序表）：
 *  timer_port 10ms 周期回调（ISR 置标志）→ 主循环按节拍依次调度：
 *  按键(10ms) → 采集(2s) → 告警评估(10ms) → 显示(200ms) → 上报(5s)。
 * 按键事件路由：MODE/MUTE → app_mode_control，SWITCH → app_alarm_control。
 * LED_RUN 运行指示优先级：
 *  慢闪（OLED 初始化失败）> 快闪（上报持续失败）> 心跳 1Hz。
 */
#include "app.h"
#include "app_mode_control.h"
#include "app_key_handler.h"
#include "app_env_sensor.h"
#include "app_alarm_control.h"
#include "app_oled_display.h"
#include "app_uart_report.h"
#include "gpio_port.h"
#include "timer_port.h"

static volatile uint8_t s_tick_flag; /* ISR 置标志，主循环消费 */

static void app_on_tick(timer_port_id_t id, void *user_data);

int32_t app_init(void)
{
    static const gpio_port_cfg_t cfg_led_run = {
        GPIO_PORT_DIR_OUTPUT, GPIO_PORT_PULL_NONE, GPIO_PORT_LEVEL_HIGH, GPIO_PORT_LEVEL_LOW,
    }; /* LED_RUN：初始灭，激活=低（心跳/故障闪烁） */
    int32_t r;

    /* 纯逻辑模块 */
    app_mode_control_init();

    /* 输入 */
    r = app_key_handler_init();
    if (r != PORT_OK) { return r; }

    /* 采集 + 告警（env_sensor 的恢复/故障事件直接连到 alarm_control） */
    r = app_env_sensor_init();
    if (r != PORT_OK) { return r; }
    r = app_alarm_control_init();
    if (r != PORT_OK) { return r; }

    /* 输出（OLED/UART 初始化失败不阻断启动：软失败由模块就绪标志处理） */
    (void)app_oled_display_init();
    (void)app_uart_report_init();

    /* 运行指示灯 + 系统 10ms 节拍 */
    r = gpio_port_init(GPIO_PORT_LED_RUN, &cfg_led_run);
    if (r != PORT_OK) { return r; }
    r = timer_port_init(TIMER_PORT_TICK_10MS);
    if (r != PORT_OK) { return r; }
    s_tick_flag = 0;
    return timer_port_start_periodic(TIMER_PORT_TICK_10MS, 10u, app_on_tick, 0);
}

void app_loop(void)
{
    app_key_event_t ev;
    uint16_t led_tick = 0;

    for (;;) {
        while (s_tick_flag == 0) {
            /* 等 10ms 节拍（裸机轮询；RTOS 工程此处为 OSAL 延时/信号量） */
        }
        s_tick_flag = 0;

        /* 1. 按键采样 → 事件分发 */
        app_key_handler_poll();
        ev = app_key_handler_get_event();
        while (ev != APP_KEY_EVENT_NONE) {
            switch (ev) {
            case APP_KEY_EVENT_MODE:
                app_mode_control_on_key_mode();
                break;
            case APP_KEY_EVENT_SWITCH:
                app_alarm_control_on_key_switch();
                break;
            case APP_KEY_EVENT_MUTE:
                app_mode_control_on_key_mute();
                break;
            default:
                break;
            }
            ev = app_key_handler_get_event();
        }

        /* 2. 采集 → 告警评估 → 显示 → 上报（各自内部按周期触发） */
        app_env_sensor_poll();
        app_alarm_control_poll();
        app_oled_display_poll();
        app_uart_report_poll();

        /* 3. LED_RUN 运行指示（节拍 200 为公共周期） */
        led_tick++;
        if (app_oled_display_is_ready() == 0) {
            /* 慢闪：亮 1s / 灭 1s（初始化失败，最高优先级） */
            (void)gpio_port_set_active(GPIO_PORT_LED_RUN,
                                       (uint8_t)(((led_tick / 100u) % 2u) == 0u));
        } else if (app_uart_report_is_failing() != 0) {
            /* 快闪：亮 250ms / 灭 250ms（上报持续失败） */
            (void)gpio_port_set_active(GPIO_PORT_LED_RUN,
                                       (uint8_t)(((led_tick / 25u) % 2u) == 0u));
        } else {
            /* 心跳：亮 500ms / 灭 500ms（1Hz） */
            (void)gpio_port_set_active(GPIO_PORT_LED_RUN,
                                       (uint8_t)(((led_tick / 50u) % 2u) == 0u));
        }
        if (led_tick >= 200u) {
            led_tick = 0;
        }
    }
}

/** 10ms 节拍回调（ISR 上下文：只置标志，不做任何耗时处理）。 */
static void app_on_tick(timer_port_id_t id, void *user_data)
{
    (void)id;
    (void)user_data;
    s_tick_flag = 1;
}
