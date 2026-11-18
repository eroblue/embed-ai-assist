#include <string.h>
#include "app_alarm_control.h"
#include "app_env_sensor.h"
#include "app_mode_control.h"
#include "gpio_port.h"
#include "s8_case.h"

static env_data_t env;
static app_mode_t mode;
static uint8_t muted;
static uint8_t actuator;
static uint8_t buzzer;

const env_data_t *app_env_sensor_get_data(void) { return &env; }
app_mode_t app_mode_control_get_mode(void) { return mode; }
uint8_t app_mode_control_is_muted(void) { return muted; }
int32_t gpio_port_init(gpio_port_id_t id, const gpio_port_cfg_t *cfg)
{
    (void)id; (void)cfg; return PORT_OK;
}
int32_t gpio_port_set_active(gpio_port_id_t id, uint8_t active)
{
    if (id == GPIO_PORT_LED_EXEC) actuator = active;
    if (id == GPIO_PORT_BUZZER) buzzer = active;
    return PORT_OK;
}

int main(void)
{
    int fail = 0;
    env.temp = 31; env.light = 50; mode = APP_MODE_AUTO; muted = 0;
    fail += s8_case("alarm_init", app_alarm_control_init() == PORT_OK &&
                    app_alarm_control_get_alarm() == APP_ALARM_NORMAL && actuator == 0);
    app_alarm_control_poll();
    fail += s8_case("high_temp_actuator", app_alarm_control_get_alarm() == APP_ALARM_HIGH_TEMP &&
                    actuator == 1 && buzzer == 1 &&
                    strcmp(app_alarm_control_get_name(), "HIGH_TEMP") == 0);
    env.temp = 9;
    app_alarm_control_poll();
    fail += s8_case("low_temp_actuator", app_alarm_control_get_alarm() == APP_ALARM_LOW_TEMP && actuator == 0);
    app_alarm_control_on_sensor_fault();
    app_alarm_control_poll();
    fail += s8_case("sensor_fault_silent", app_alarm_control_get_alarm() == APP_ALARM_SENSOR_FAULT &&
                    buzzer == 0 && strcmp(app_alarm_control_get_display(), "SENSOR ERR") == 0);
    app_alarm_control_on_sensor_recovered();
    fail += s8_case("sensor_recovered", app_alarm_control_get_alarm() == APP_ALARM_NORMAL);
    return fail ? 1 : 0;
}
