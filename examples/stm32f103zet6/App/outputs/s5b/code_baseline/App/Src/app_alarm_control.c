/**
 * @file    app_alarm_control.c
 * @brief   告警控制模块实现（状态图 app_alarm_control_state.md 的 1:1 映射）
 *
 * 阈值（spec）：高温 30°C、低温 10°C、低光照 20%。
 * 执行器语义（设计输入优先）：高温开、低温关、其他迁移保持（恢复告警不自动关），
 * 联动仅自动模式；手动模式 KEY_SWITCH 翻转。
 * 蜂鸣节奏：任何非 NORMAL 态 1s 响/1s 停，静音键门控。
 * 硬件有效电平（LED 低有效/蜂鸣高有效）由 manifest 实例 active_level 固化在 S5c。
 */
#include "app_alarm_control.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "gpio_port.h"

#define ALARM_TEMP_HIGH       30   /* 高温阈值 °C */
#define ALARM_TEMP_LOW        10   /* 低温阈值 °C */
#define ALARM_LIGHT_LOW       20u  /* 低光照阈值 % */
#define BUZZER_HALF_TICKS    100u  /* 蜂鸣半周期 1s（10ms x 100） */

static app_alarm_t s_state;       /* 当前告警状态 */
static uint8_t     s_actuator_on; /* 执行器状态跟踪 */
static uint16_t    s_buzz_tick;   /* 蜂鸣节奏节拍计数 */

static void actuator_apply(uint8_t on);

int32_t app_alarm_control_init(void)
{
    static const gpio_port_cfg_t cfg_led_exec = {
        GPIO_PORT_DIR_OUTPUT, GPIO_PORT_PULL_NONE, GPIO_PORT_LEVEL_HIGH, GPIO_PORT_LEVEL_LOW,
    }; /* LED 执行器：初始灭（高电平），激活=低 */
    static const gpio_port_cfg_t cfg_buzzer = {
        GPIO_PORT_DIR_OUTPUT, GPIO_PORT_PULL_NONE, GPIO_PORT_LEVEL_LOW, GPIO_PORT_LEVEL_HIGH,
    }; /* 蜂鸣器：初始静（低电平），激活=高 */
    int32_t r;

    s_state = APP_ALARM_NORMAL;
    s_actuator_on = 0;
    s_buzz_tick = 0;
    actuator_apply(0);

    r = gpio_port_init(GPIO_PORT_LED_EXEC, &cfg_led_exec);
    if (r != PORT_OK) { return r; }
    return gpio_port_init(GPIO_PORT_BUZZER, &cfg_buzzer);
}

void app_alarm_control_poll(void)
{
    const env_data_t *env;
    app_alarm_t next;

    if (s_state == APP_ALARM_SENSOR_FAULT) {
        /* SENSOR_FAULT：不做阈值评估（保留上次数据不可信），蜂鸣节奏继续 */
        next = APP_ALARM_SENSOR_FAULT;
    } else {
        env = app_env_sensor_get_data();
        /* 优先级仲裁：HIGH_TEMP > LOW_TEMP > LOW_LIGHT > NORMAL */
        if (env->temp > ALARM_TEMP_HIGH) {
            next = APP_ALARM_HIGH_TEMP;
        } else if (env->temp < ALARM_TEMP_LOW) {
            next = APP_ALARM_LOW_TEMP;
        } else if (env->light < ALARM_LIGHT_LOW) {
            next = APP_ALARM_LOW_LIGHT;
        } else {
            next = APP_ALARM_NORMAL;
        }
    }

    if (next != s_state) {
        /* 迁移动作（仅自动模式联动执行器；其他迁移保持） */
        if (app_mode_control_get_mode() == APP_MODE_AUTO) {
            if (next == APP_ALARM_HIGH_TEMP) {
                actuator_apply(1);  /* 进入 HIGH_TEMP：/ actuator_on */
            } else if (next == APP_ALARM_LOW_TEMP) {
                actuator_apply(0);  /* 进入 LOW_TEMP：/ actuator_off */
            }
        }
        s_state = next;
    }

    /* 蜂鸣节奏：非 NORMAL 态 1s 响/1s 停；静音（任意模式叠加）门控 */
    s_buzz_tick++;
    if (s_buzz_tick >= BUZZER_HALF_TICKS) {
        s_buzz_tick = 0;
    }
    if ((s_state != APP_ALARM_NORMAL) &&
        (app_mode_control_is_muted() == 0)) {
        (void)gpio_port_set_active(GPIO_PORT_BUZZER,
                                   (uint8_t)((s_buzz_tick < (BUZZER_HALF_TICKS / 2u)) ? 1u : 0u));
    } else {
        (void)gpio_port_set_active(GPIO_PORT_BUZZER, 0u);
    }
}

void app_alarm_control_on_key_switch(void)
{
    if (app_mode_control_get_mode() == APP_MODE_MANUAL) {
        /* 手动模式：翻转执行器 */
        actuator_apply((uint8_t)(s_actuator_on == 0));
    }
    /* 自动模式：忽略（执行器由温度告警联动） */
}

void app_alarm_control_on_sensor_fault(void)
{
    s_state = APP_ALARM_SENSOR_FAULT; /* 任意态 → SENSOR_FAULT */
}

void app_alarm_control_on_sensor_recovered(void)
{
    if (s_state == APP_ALARM_SENSOR_FAULT) {
        s_state = APP_ALARM_NORMAL; /* SENSOR_FAULT → NORMAL：on_sensor_recovered */
    }
}

app_alarm_t app_alarm_control_get_alarm(void)
{
    return s_state;
}

const char *app_alarm_control_get_display(void)
{
    switch (s_state) {
    case APP_ALARM_HIGH_TEMP:    return "HIGH_T";
    case APP_ALARM_LOW_TEMP:     return "LOW_T";
    case APP_ALARM_LOW_LIGHT:    return "LOW_L";
    case APP_ALARM_SENSOR_FAULT: return "FAULT";
    default:                     return "NORMAL";
    }
}

const char *app_alarm_control_get_name(void)
{
    switch (s_state) {
    case APP_ALARM_HIGH_TEMP:    return "HIGH_TEMP";
    case APP_ALARM_LOW_TEMP:     return "LOW_TEMP";
    case APP_ALARM_LOW_LIGHT:    return "LOW_LIGHT";
    case APP_ALARM_SENSOR_FAULT: return "SENSOR_FAULT";
    default:                     return "NORMAL";
    }
}

uint8_t app_alarm_control_is_actuator_on(void)
{
    return s_actuator_on;
}

/** 执行器状态跟踪 + 输出（LED_EXEC 与执行器语义同点同灭）。 */
static void actuator_apply(uint8_t on)
{
    s_actuator_on = on;
    (void)gpio_port_set_active(GPIO_PORT_LED_EXEC, on);
}
