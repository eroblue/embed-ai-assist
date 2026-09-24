/**
 * @file    app_env_sensor.c
 * @brief   环境采集模块实现（流程图 app_env_sensor_flow.md 的 1:1 映射）
 *
 * 时序：10ms 节拍计数，200 拍（2s）触发一次采集（A[采集周期到达]）。
 * 失败语义：DHT11 读取失败或数据越界均计一次失败（D[失败计数+1 保留上次值]），
 *           连续 5 次（E[达到阈值]）发布一次故障事件并清零计数（F）；
 *           成功且此前故障（J）则发布恢复事件并清故障标志（K）。
 * 光照：mv*100/ref_mv 换算（G[读取光照 ADC 并换算]），越界视为无效保留上次值（N）。
 */
#include "app_env_sensor.h"
#include "app_alarm_control.h"
#include "driver_dht11.h"
#include "adc_port.h"

/* ---------------- 采集参数（设计输入时序表 + spec 阈值） ---------------- */
#define ENV_PERIOD_TICKS    200u   /* 采集周期 2s（10ms x 200） */
#define ENV_FAIL_THRESHOLD    5u   /* 连续失败阈值 fail_threshold=5 */
#define ENV_TEMP_MIN        (-20)  /* 有效范围 -20~60 °C */
#define ENV_TEMP_MAX         60
#define ENV_HUMI_MIN          0u   /* 有效范围 0~100 % */
#define ENV_HUMI_MAX        100u
#define ENV_LIGHT_MAX       100u   /* 光照上限 100% */
#define ENV_REF_MV         3300u   /* 满量程锚点（mv*100/ref_mv = 百分比） */

static const adc_port_cfg_t s_adc_cfg = {
    ADC_PORT_REF_VDD,  /* 基准 = VDD */
    ENV_REF_MV,        /* ref_mv：应用侧百分比换算锚点 */
    8u,                /* 过采样 8 次均值 */
};

static env_data_t s_data;          /* 最近有效数据（失败保留上次值） */
static uint8_t    s_fault;         /* 故障标志 */
static uint16_t   s_tick;          /* 节拍计数 */
static uint8_t    s_fail_count;     /* 连续失败计数 */

int32_t app_env_sensor_init(void)
{
    int32_t r;

    s_data.temp = 0;
    s_data.humi = 0;
    s_data.light = 0;
    s_fault = 0;
    s_tick = 0;
    s_fail_count = 0;

    r = driver_dht11_init();
    if (r != PORT_OK) { return r; }
    return adc_port_init(ADC_PORT_LIGHT, &s_adc_cfg);
}

void app_env_sensor_poll(void)
{
    uint16_t mv = 0;
    int16_t temp;
    uint8_t humi;
    uint8_t fail = 0;

    s_tick++;
    if (s_tick < ENV_PERIOD_TICKS) {
        return; /* 未到采集周期 */
    }
    s_tick = 0;

    /* B[读取 DHT11 温湿度] */
    if (driver_dht11_read(&temp, &humi) == PORT_OK) {
        /* H{数据在有效范围内?} */
        if ((temp < ENV_TEMP_MIN) || (temp > ENV_TEMP_MAX) ||
            (humi < ENV_HUMI_MIN) || (humi > ENV_HUMI_MAX)) {
            fail = 1;
        }
    } else {
        fail = 1;
    }

    if (fail != 0) {
        /* D[失败计数+1 保留上次值] */
        s_fail_count++;
        /* E{连续失败达到阈值?} */
        if (s_fail_count >= ENV_FAIL_THRESHOLD) {
            /* F[发布传感器故障事件 清零失败计数 置故障标志] */
            s_fail_count = 0;
            if (s_fault == 0) {
                s_fault = 1;
                app_alarm_control_on_sensor_fault();
            }
        }
    } else {
        /* I[清零失败计数 更新温湿度] */
        s_fail_count = 0;
        s_data.temp = temp;
        s_data.humi = humi;
        /* J{此前处于故障状态?} → K[发布传感器恢复事件 清故障标志] */
        if (s_fault != 0) {
            s_fault = 0;
            app_alarm_control_on_sensor_recovered();
        }
    }

    /* G[读取光照 ADC 并换算]（成功/故障路径均执行） */
    if (adc_port_sample_mv(ADC_PORT_LIGHT, &mv) != PORT_OK) {
        return; /* N[光照标记无效 保留上次值] */
    }
    s_data.light = (uint8_t)((mv * 100u) / ENV_REF_MV);
    /* L{光照在有效范围内?}（<0 不可能，>100 饱和截断） */
    if (s_data.light > ENV_LIGHT_MAX) {
        s_data.light = ENV_LIGHT_MAX;
    }
    /* M[更新光照数据] → O[本次采集结束] */
}

const env_data_t *app_env_sensor_get_data(void)
{
    return &s_data;
}

uint8_t app_env_sensor_is_fault(void)
{
    return s_fault;
}
