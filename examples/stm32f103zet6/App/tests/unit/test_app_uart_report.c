#include <string.h>
#include "app_uart_report.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "app_alarm_control.h"
#include "uart_port.h"
#include "s8_case.h"

static env_data_t env = {25, 60, 75};
static char frame[128];
static int writes;
static int fail_write;
const env_data_t *app_env_sensor_get_data(void) { return &env; }
app_mode_t app_mode_control_get_mode(void) { return APP_MODE_AUTO; }
const char *app_alarm_control_get_name(void) { return "NORMAL"; }
int32_t uart_port_init(uart_port_id_t id, const uart_port_cfg_t *cfg)
{
    (void)id; return cfg->baudrate == 115200u && cfg->data_bits == 8u ? PORT_OK : PORT_ERR_PARAM;
}
int32_t uart_port_write(uart_port_id_t id, const uint8_t *data, uint16_t len)
{
    (void)id;
    writes++;
    if (fail_write) return PORT_ERR_TIMEOUT;
    if (len >= sizeof(frame)) return PORT_ERR_PARAM;
    memcpy(frame, data, len); frame[len] = '\0';
    return len;
}
static void poll_n(int n) { while (n-- > 0) app_uart_report_poll(); }

int main(void)
{
    int fail = 0;
    fail += s8_case("uart_init_ready", app_uart_report_init() == PORT_OK && app_uart_report_is_ready());
    poll_n(499);
    fail += s8_case("before_period_no_write", writes == 0);
    poll_n(1);
    fail += s8_case("json_frame", writes == 1 &&
                    strcmp(frame, "{\"temp\":25,\"humi\":60,\"light\":75,\"mode\":\"AUTO\",\"alarm\":\"NORMAL\"}\r\n") == 0);
    fail_write = 1;
    poll_n(1500);
    fail += s8_case("three_failed_cycles", app_uart_report_is_failing() && writes == 10);
    fail_write = 0;
    poll_n(500);
    fail += s8_case("success_clears_fault", !app_uart_report_is_failing() && writes == 11);
    return fail ? 1 : 0;
}
