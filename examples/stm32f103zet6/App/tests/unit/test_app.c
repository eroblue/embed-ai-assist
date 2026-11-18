#include <string.h>
#include "app.h"
#include "app_mode_control.h"
#include "app_key_handler.h"
#include "app_env_sensor.h"
#include "app_alarm_control.h"
#include "app_lcd_display.h"
#include "app_uart_report.h"
#include "gpio_port.h"
#include "timer_port.h"
#include "wdt_port.h"
#include "s8_case.h"

static char calls[32];
static int call_count;
static int env_result;
static int uart_result;
static int lcd_result;
static uint32_t wdt_timeout;
static void add(char c) { calls[call_count++] = c; calls[call_count] = 0; }
int32_t timer_port_init(timer_port_id_t id) { (void)id; add('T'); return PORT_OK; }
int32_t timer_port_start_periodic(timer_port_id_t id, uint32_t ms, timer_port_cb_t cb, void *user)
{ (void)id; (void)user; add('S'); return ms == 10 && cb != 0 ? PORT_OK : PORT_ERR_PARAM; }
void app_mode_control_init(void) { add('M'); }
int32_t app_key_handler_init(void) { add('K'); return PORT_OK; }
int32_t app_alarm_control_init(void) { add('A'); return PORT_OK; }
int32_t app_env_sensor_init(void) { add('E'); return env_result; }
int32_t app_uart_report_init(void) { add('U'); return uart_result; }
int32_t app_lcd_display_init(void) { add('L'); return lcd_result; }
int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg)
{ (void)id; (void)cfg; add('G'); return PORT_OK; }
int32_t wdt_port_init(wdt_port_id_t id, uint32_t ms)
{ (void)id; add('W'); wdt_timeout = ms; return PORT_OK; }
/* app_loop is not called, but its referenced interfaces must link. */
int32_t wdt_port_feed(wdt_port_id_t id) { (void)id; return PORT_OK; }
void app_key_handler_poll(void) { }
app_key_event_t app_key_handler_get_event(void) { return APP_KEY_EVENT_NONE; }
void app_mode_control_on_key_mode(void) { }
void app_mode_control_on_key_mute(void) { }
void app_alarm_control_on_key_switch(void) { }
void app_env_sensor_poll(void) { }
void app_alarm_control_poll(void) { }
void app_lcd_display_poll(void) { }
void app_uart_report_poll(void) { }
uint8_t app_lcd_display_is_ready(void) { return 1; }
uint8_t app_lcd_display_diag_code(void) { return 0; }
uint8_t app_uart_report_is_failing(void) { return 0; }
int32_t gpio_port_set_active(gpio_port_id_t id, uint8_t active)
{ (void)id; (void)active; return PORT_OK; }

int main(void)
{
    int fail = 0;
    call_count = 0; calls[0] = 0;
    fail += s8_case("app_init_order", app_init() == PORT_OK &&
                    strcmp(calls, "TSMKAEULGW") == 0 && wdt_timeout == 1000u);
    call_count = 0; calls[0] = 0; uart_result = lcd_result = PORT_ERR_STATE;
    fail += s8_case("output_soft_failure", app_init() == PORT_OK &&
                    strcmp(calls, "TSMKAEULGW") == 0);
    call_count = 0; calls[0] = 0; env_result = PORT_ERR_TIMEOUT;
    fail += s8_case("sensor_init_failure", app_init() == PORT_ERR_TIMEOUT &&
                    strcmp(calls, "TSMKAE") == 0);
    return fail ? 1 : 0;
}
