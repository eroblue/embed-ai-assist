/**
 * @file    app_uart_report.c
 * @brief   串口上报模块实现（时序图 app_uart_report_sequence.md 的 1:1 映射）
 *
 * 帧格式（REQ：上报环境数据 + 模式 + 告警状态）：
 *   {"temp":25,"humi":60,"light":75,"mode":"AUTO","alarm":"NORMAL"}\r\n
 * 失败重试 retry_max=2；连续失败周期计数 ≥3（fail_threshold=3）置故障标志。
 */
#include "app_uart_report.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "app_alarm_control.h"
#include "uart_port.h"
#include <stdio.h>

#define REPORT_PERIOD_TICKS  500u  /* 上报周期 5s / 10ms */
#define REPORT_RETRY_MAX       2u  /* 失败重试次数 */
#define REPORT_FAIL_THRESHOLD  3u   /* 连续失败周期阈值 */
#define REPORT_FRAME_MAX      96u   /* 帧缓冲上限 */

static const uart_port_cfg_t s_uart_cfg = {
    115200u, /* baudrate */
    8u,      /* data_bits */
    0u,      /* parity: 无 */
    1u,      /* stop_bits */
};

static uint8_t  s_ready;        /* 就绪标志 */
static uint16_t s_tick;         /* 上报周期计数 */
static uint8_t  s_fail_cycles;  /* 连续失败周期计数 */
static uint8_t  s_failing;      /* 上报故障标志 */
static char     s_frame[REPORT_FRAME_MAX];

int32_t app_uart_report_init(void)
{
    int32_t r = uart_port_init(UART_PORT_REPORT, &s_uart_cfg);
    s_ready = (r == PORT_OK) ? 1u : 0u;
    s_tick = 0;
    s_fail_cycles = 0;
    s_failing = 0;
    return r;
}

void app_uart_report_poll(void)
{
    const env_data_t *env;
    const char *mode_name;
    const char *alarm_name;
    int32_t sent;
    uint8_t attempt;
    int32_t len;

    if (s_ready == 0) {
        return;
    }
    s_tick++;
    if (s_tick < REPORT_PERIOD_TICKS) {
        return; /* 未到上报周期 */
    }
    s_tick = 0;

    /* 读取共享数据并组 JSON 帧 */
    env = app_env_sensor_get_data();
    mode_name = (app_mode_control_get_mode() == APP_MODE_AUTO) ? "AUTO" : "MANUAL";
    alarm_name = app_alarm_control_get_name();
    len = snprintf(s_frame, sizeof(s_frame),
                   "{\"temp\":%d,\"humi\":%u,\"light\":%u,\"mode\":\"%s\","
                   "\"alarm\":\"%s\"}\r\n",
                   (int)env->temp, (unsigned int)env->humi,
                   (unsigned int)env->light, mode_name, alarm_name);
    if ((len <= 0) || (len >= (int32_t)sizeof(s_frame))) {
        s_fail_cycles++;
        goto fail_check;
    }

    /* 发送：PORT_OK（同步拷贝语义）/ 失败重试 retry_max=2 */
    for (attempt = 0; attempt <= REPORT_RETRY_MAX; attempt++) {
        sent = uart_port_write(UART_PORT_REPORT,
                               (const uint8_t *)s_frame, (uint16_t)len);
        if (sent == len) {
            s_fail_cycles = 0;
            s_failing = 0; /* 任一成功清零故障标志 */
            return;
        }
    }

    /* 连续失败周期计数+1 → 达到阈值置上报故障标志 */
    s_fail_cycles++;
fail_check:
    if (s_fail_cycles >= REPORT_FAIL_THRESHOLD) {
        s_fail_cycles = REPORT_FAIL_THRESHOLD;
        s_failing = 1;
    }
}

uint8_t app_uart_report_is_ready(void)
{
    return s_ready;
}

uint8_t app_uart_report_is_failing(void)
{
    return s_failing;
}
