/**
 * @file    app_oled_display.c
 * @brief   OLED 显示模块实现（流程图 app_oled_display_flow.md 的 1:1 映射）
 *
 * 画面（4 行 ASCII，8x16 字体）：
 *   L0: ENV MONITOR
 *   L1: T:25C H:60%
 *   L2: L:75%
 *   L3: M:AUTO A:NORMAL   （告警闪烁相位隐藏）
 * 刷新周期 200ms（20 拍），告警闪烁 1Hz（相邻刷新相位取反）。
 */
#include "app_oled_display.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "app_alarm_control.h"
#include "driver_oled.h"

#define DISP_PERIOD_TICKS   20u   /* 刷新周期 200ms / 10ms */

static uint8_t  s_ready;       /* B{OLED 就绪?} */
static uint16_t  s_tick;        /* 刷新周期计数 */
static uint8_t  s_blink_on;    /* 告警闪烁相位（1Hz：每次刷新取反） */
static uint8_t  s_fail_count;  /* K[显示失败计数+1] */
static char     s_line[DRIVER_OLED_LINE_CHARS + 1u];

static uint16_t disp_copy(char *dst, const char *src);
static uint16_t disp_len(const char *s);
static uint16_t disp_append_int(char *dst, int32_t value);

int32_t app_oled_display_init(void)
{
    int32_t r = driver_oled_init(); /* 内含 I2C init + 上电序列 + 清屏 */
    s_ready = (r == PORT_OK) ? 1u : 0u;
    s_tick = 0;
    s_blink_on = 0;
    s_fail_count = 0;
    return r;
}

void app_oled_display_poll(void)
{
    const env_data_t *env;
    app_alarm_t alarm;
    uint16_t len;
    int32_t r;

    if (s_ready == 0) {
        return; /* B{OLED 就绪?} → Z[跳过本次刷新] */
    }
    s_tick++;
    if (s_tick < DISP_PERIOD_TICKS) {
        return; /* A[刷新周期到达 period_ms=200] */
    }
    s_tick = 0;

    /* C[读取共享数据] */
    env = app_env_sensor_get_data();
    alarm = app_alarm_control_get_alarm();

    /* D{告警激活?} → F{闪烁相位为亮? blink_hz=1}（相邻刷新相位取反） */
    if (alarm != APP_ALARM_NORMAL) {
        s_blink_on = (uint8_t)(s_blink_on == 0);
    } else {
        s_blink_on = 1; /* 无告警时保持显示 */
    }

    /* E[渲染 4 行完整画面] → H[经 I2C 写入 OLED] */
    (void)disp_copy(s_line, "ENV MONITOR");
    r = driver_oled_show_line(0u, s_line);

    len = disp_copy(s_line, "T:");
    len += disp_append_int(s_line + len, env->temp);
    len += disp_copy(s_line + len, "C H:");
    len += disp_append_int(s_line + len, env->humi);
    (void)disp_copy(s_line + len, "%");
    if (r == PORT_OK) { r = driver_oled_show_line(1u, s_line); }

    len = disp_copy(s_line, "L:");
    len += disp_append_int(s_line + len, env->light);
    (void)disp_copy(s_line + len, "%");
    if (r == PORT_OK) { r = driver_oled_show_line(2u, s_line); }

    /* G[渲染画面且告警行隐藏]（闪烁暗相位） */
    if ((alarm != APP_ALARM_NORMAL) && (s_blink_on == 0)) {
        s_line[0] = (char)0;
    } else {
        len = disp_copy(s_line, "M:");
        len += disp_copy(s_line + len, app_mode_control_get_display());
        len += disp_copy(s_line + len, " A:");
        (void)disp_copy(s_line + len, app_alarm_control_get_display());
    }
    if (r == PORT_OK) { r = driver_oled_show_line(3u, s_line); }

    /* I{写入成功?} → J[刷新完成] / K[显示失败计数+1] */
    if (r != PORT_OK) {
        s_fail_count++;
    }
}

uint8_t app_oled_display_is_ready(void)
{
    return s_ready;
}

/** 拷贝字符串到行缓冲（含终止符），返回长度。 */
static uint16_t disp_copy(char *dst, const char *src)
{
    uint16_t i = 0;
    while ((src[i] != (char)0) && (i < DRIVER_OLED_LINE_CHARS)) {
        dst[i] = src[i];
        i++;
    }
    dst[i] = (char)0;
    return i;
}

/** 字符串长度。 */
static uint16_t disp_len(const char *s)
{
    uint16_t n = 0;
    while (s[n] != (char)0) {
        n++;
    }
    return n;
}

/** 在字符串末尾追加整数（支持负号），返回追加后的长度。 */
static uint16_t disp_append_int(char *dst, int32_t value)
{
    char tmp[8];
    uint8_t n = 0;
    uint16_t pos = disp_len(dst);
    uint32_t v;

    v = (value < 0) ? (uint32_t)(-value) : (uint32_t)value;
    do {
        tmp[n++] = (char)('0' + (v % 10u));
        v /= 10u;
    } while ((v > 0u) && (n < (sizeof(tmp) - 1u)));
    if (value < 0) {
        tmp[n++] = '-';
    }
    while ((n > 0u) && (pos < DRIVER_OLED_LINE_CHARS)) {
        n--;
        dst[pos++] = tmp[n];
    }
    dst[pos] = (char)0;
    return pos;
}
