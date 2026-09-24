/**
 * @file    app_alarm_control.h
 * @brief   告警控制模块（阈值评估 + 优先级仲裁 + 执行器/蜂鸣联动）
 *
 * 对应状态图 docs/flow/app_alarm_control_state.md：
 *  NORMAL / HIGH_TEMP / LOW_TEMP / LOW_LIGHT / SENSOR_FAULT 五态，
 *  阈值高温 30°C 开执行器、低温 10°C 关执行器（仅自动模式，其余保持），
 *  手动模式执行器由 KEY_SWITCH 手动翻转；蜂鸣 1s 响/1s 停（静音门控）。
 */
#ifndef APP_ALARM_CONTROL_H
#define APP_ALARM_CONTROL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 告警状态。 */
typedef enum {
    APP_ALARM_NORMAL = 0,
    APP_ALARM_HIGH_TEMP,   /* 温度 > 30°C */
    APP_ALARM_LOW_TEMP,    /* 温度 < 10°C */
    APP_ALARM_LOW_LIGHT,   /* 光照 < 20% */
    APP_ALARM_SENSOR_FAULT,/* 传感器连续采集失败 */
} app_alarm_t;

/** 初始化执行器/蜂鸣 GPIO 与状态机复位。 */
int32_t app_alarm_control_init(void);

/** 10ms 节拍：阈值评估（自动模式）+ 蜂鸣节奏推进。 */
void app_alarm_control_poll(void);

/** 手动开关按键事件（手动模式翻转执行器；自动模式忽略）。 */
void app_alarm_control_on_key_switch(void);

/** 传感器故障事件（来自 app_env_sensor，进入 SENSOR_FAULT 态）。 */
void app_alarm_control_on_sensor_fault(void);

/** 传感器恢复事件（来自 app_env_sensor，SENSOR_FAULT → NORMAL）。 */
void app_alarm_control_on_sensor_recovered(void);

/** 当前告警状态。 */
app_alarm_t app_alarm_control_get_alarm(void);

/** 显示短名（OLED 行宽受限）："NORMAL"/"HIGH_T"/"LOW_T"/"LOW_L"/"FAULT"。 */
const char *app_alarm_control_get_display(void);

/** 完整名（上报 JSON 用）："NORMAL"/"HIGH_TEMP"/"LOW_TEMP"/"LOW_LIGHT"/"SENSOR_FAULT"。 */
const char *app_alarm_control_get_name(void);

/** 执行器当前状态（1=开启，供上报/显示查询）。 */
uint8_t app_alarm_control_is_actuator_on(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_ALARM_CONTROL_H */
