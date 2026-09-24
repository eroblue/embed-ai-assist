/**
 * @file    app_env_sensor.h
 * @brief   环境采集模块（DHT11 温湿度 + 光照 ADC，2s 周期）
 *
 * 对应流程图 docs/flow/app_env_sensor_flow.md：
 * 采集 → 有效性判定 → 失败计数/故障发布 → 光照换算，失败保留上次值。
 * 故障/恢复事件直接通知告警模块（app_alarm_control）。
 */
#ifndef APP_ENV_SENSOR_H
#define APP_ENV_SENSOR_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 最近一次有效环境数据（显示/上报共用）。 */
typedef struct {
    int16_t temp;   /* 温度 °C */
    uint8_t humi;   /* 相对湿度 % */
    uint8_t light;  /* 光照 % */
} env_data_t;

/** 初始化 DHT11 与光照 ADC（数据清零，故障标志复位）。 */
int32_t app_env_sensor_init(void);

/** 10ms 节拍轮询：内部按 2s 周期触发一次采集。 */
void app_env_sensor_poll(void);

/** 读共享数据指针（实时快照，调用方不得修改）。 */
const env_data_t *app_env_sensor_get_data(void);

/** 传感器故障标志（连续 5 次采集失败置位，恢复事件清零）。 */
uint8_t app_env_sensor_is_fault(void);

#ifdef __cplusplus
}
#endif

#endif /* APP_ENV_SENSOR_H */
